def estimate(tickets, spikes, manual_minutes: float):
    completed = [t for t in tickets if t.get("status") == "triaged"]
    durations = [t["classified_at"] - t["received_at"] for t in completed]
    return {
        "tickets_triaged": len(completed),
        "avg_seconds_per_ticket": round(sum(durations) / len(durations), 2) if durations else 0,
        "estimated_minutes_saved": round(len(completed) * (manual_minutes - 0.5), 1),
        "minutes_saved_note": "Estimate based on manual triage assumption.",
        "critical_surfaced": sum(t.get("urgency") == "critical" for t in completed),
        "spike_affected": sum(s["count"] for s in spikes),
        "needs_human_count": sum(t.get("needs_human") is True for t in completed),
        "auto_resolvable_count": sum(t.get("needs_human") is False for t in completed),
    }
