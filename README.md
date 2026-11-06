# QZero

A small FastAPI prototype that uses Gemini to classify support tickets, detects repeated themes, and surfaces alerts and estimated impact in a live browser UI.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000. Configuration is read from `.env` with `python-dotenv`; never commit that file. The configured model is checked at startup and falls back to `gemini-2.5-flash` if unavailable. The model actually used is printed at startup and shown in the UI.

Configured model: `gemini-3.1-flash-lite`. Runtime checks availability at every startup and falls back to `gemini-2.5-flash` if necessary.

## Notes

- Storage is in memory only. Reset clears queue/spike/alert/impact state but retains the last evaluation.
- “Minutes saved” is an estimate using `MANUAL_MINUTES_PER_TICKET - 0.5` per triaged ticket.
- Burst messages are explicitly synthetic demo data.
