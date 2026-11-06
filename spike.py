import re


def normalize_theme(theme: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", theme.lower()).strip()


def detect(tickets, prior_spikes, threshold: int, window: int, now: float):
    """Return active spikes and the themes newly crossing threshold."""
    recent = [t for t in tickets if t.get("status") == "triaged" and now - t["received_at"] <= window]
    groups = {}
    for ticket in recent:
        groups.setdefault(normalize_theme(ticket["theme"]), []).append(ticket)
    active, new_themes = [], []
    previous = {s["theme"]: s for s in prior_spikes if now - s["first_seen"] <= window}
    for theme, members in groups.items():
        if len(members) < threshold:
            continue
        spike = {"theme": theme, "count": len(members), "first_seen": min(x["received_at"] for x in members), "ticket_ids": [x["id"] for x in members]}
        active.append(spike)
        if theme not in previous:
            new_themes.append(spike)
    return active, new_themes
