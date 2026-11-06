import logging
import time
import httpx

logger = logging.getLogger(__name__)


async def emit(alerts: list, alert_type: str, message: str, webhook: str = ""):
    alert = {"type": alert_type, "message": message, "created_at": time.time()}
    alerts.append(alert)
    print(f"ALERT [{alert_type}]: {message}")
    if webhook:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(webhook, json={"text": message})
        except Exception as exc:
            logger.warning("Slack alert failed: %s", exc)
    return alert
