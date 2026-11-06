"""Gemini-backed structured ticket classification with one shared rate limiter."""
import asyncio
import logging
import time
from collections import deque
from typing import Callable, Literal
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)
CATEGORIES = Literal["onboarding", "billing", "failed_payment", "tax_compliance", "refund", "integration_bug", "feature_request", "docs_question", "account_access", "other"]
URGENCIES = Literal["critical", "high", "medium", "low"]

class DailyQuotaExhausted(Exception): pass

class Triage(BaseModel):
    category: CATEGORIES; urgency: URGENCIES; summary: str
    theme: str = Field(pattern=r"^[a-z]+( [a-z]+){2,5}$")
    needs_human: bool; suggested_reply: str = Field(max_length=500); confidence: float = Field(ge=0, le=1)
    @field_validator("suggested_reply")
    @classmethod
    def reply_is_under_eighty_words(cls, value):
        if len(value.split()) >= 80: raise ValueError("suggested_reply must be under 80 words")
        return value
    @field_validator("summary")
    @classmethod
    def summary_is_under_twenty_words(cls, value):
        if len(value.split()) > 20: raise ValueError("summary must be at most 20 words")
        return value

SYSTEM_INSTRUCTION = """You triage customer support tickets. Return only the requested JSON schema. Use category names exactly as provided. Summary has at most 20 words. Theme must be 3 to 6 lowercase words describing the underlying issue; use stable identical wording for identical issues (for example: checkout failing for indian cards). Suggested reply is friendly, under 80 words, and must not invent policies or numbers. needs_human is false only if the suggested reply fully resolves the ticket, mainly documentation questions. Urgency rules: critical is outages, checkouts or logins blocking many customers, or large revenue loss. High is money incorrectly charged or moved, blocked integrations, or tax-filing problems. Medium is normal support needing action. Low is questions and feature requests."""

class GeminiLimiter:
    def __init__(self, rpm_limit: int, daily_limit: int):
        self.rpm_limit, self.daily_limit = rpm_limit, daily_limit
        self.timestamps, self.daily_calls = deque(), 0
        self.lock, self.call_lock = asyncio.Lock(), asyncio.Lock()
    async def acquire(self, on_wait: Callable[[float], None] | None = None):
        async with self.call_lock:
            while True:
                async with self.lock:
                    now = time.monotonic()
                    while self.timestamps and now - self.timestamps[0] >= 60: self.timestamps.popleft()
                    if self.daily_calls >= self.daily_limit: raise DailyQuotaExhausted("Configured Gemini daily limit reached")
                    rpm_wait = max(0, self.timestamps[0] + 60 - now) if len(self.timestamps) >= self.rpm_limit else 0
                    gap_wait = max(0, self.timestamps[-1] + 4.2 - now) if self.timestamps else 0
                    wait = max(rpm_wait, gap_wait)
                    if not wait:
                        self.timestamps.append(now); self.daily_calls += 1; return
                if on_wait: on_wait(wait)
                logger.info("Gemini rate limit wait: %.1fs", wait)
                await asyncio.sleep(wait)

limiter: GeminiLimiter | None = None
def configure_limiter(rpm_limit: int, daily_limit: int):
    global limiter
    limiter = GeminiLimiter(rpm_limit, daily_limit)
def make_client(api_key: str): return genai.Client(api_key=api_key)
def available_model(client, configured: str) -> str:
    try:
        names = {m.name.removeprefix("models/") for m in client.models.list()}
        if configured.removeprefix("models/") in names: return configured.removeprefix("models/")
        logger.warning("Configured Gemini model %s is unavailable; using gemini-2.5-flash", configured)
    except Exception as exc: logger.warning("Could not list Gemini models (%s); using gemini-2.5-flash", exc)
    return "gemini-2.5-flash"
def is_daily_quota(exc: Exception) -> bool:
    text = str(exc).lower()
    return "per day" in text or "daily quota" in text or "requests per day" in text
async def classify(client, model: str, text: str, on_wait=None) -> Triage:
    if limiter is None: raise RuntimeError("Gemini limiter has not been configured")
    for attempt in range(4):
        await limiter.acquire(on_wait)
        try:
            response = await client.aio.models.generate_content(model=model, contents=text, config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Triage, system_instruction=SYSTEM_INSTRUCTION))
            if response.parsed is not None: return Triage.model_validate(response.parsed)
            return Triage.model_validate_json(response.text)
        except Exception as exc:
            status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            if str(status) == "429" and is_daily_quota(exc): raise DailyQuotaExhausted("Gemini daily quota reached") from exc
            if str(status) not in {"429", "503"} or attempt == 3: raise
            delay = 2 ** attempt
            logger.warning("Gemini retry: status=%s reason=%s wait=%ss", status, "per-minute quota" if str(status) == "429" else "service unavailable", delay)
            if on_wait: on_wait(delay)
            await asyncio.sleep(delay)
    raise RuntimeError("unreachable")
