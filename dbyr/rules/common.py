"""Helpers shared by the rules: timestamps, durations, surfaces and monitor coverage."""

from __future__ import annotations

from datetime import datetime

from ..params import MIN_SAMPLE, OBSERVERS


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def months(duration: str) -> float:
    """ISO-8601 duration (PnD, PnM, PnY) or 'indefinite' -> months."""
    if duration == "indefinite":
        return float("inf")
    n, unit = int(duration[1:-1]), duration[-1]
    return {"D": n / 30.4, "M": n, "Y": 12 * n}[unit]


def surfaces(intent: dict) -> dict[str, dict]:
    return {s["surface_id"]: s for s in intent["egress_topology"]["writable_surfaces"]}


def shared_persistent(surface: dict) -> bool:
    return surface["persistence"] in ("cross_run", "permanent") and surface["tenancy"] != "run_only"


def shared_agent_surfaces(topo: dict) -> list[dict]:
    return [s for s in topo["writable_surfaces"]
            if s.get("isolation") == "shared" or s["tenancy"] in ("shared_agents", "shared_runs", "external")]


def effective_monitors(intent: dict) -> set[str]:
    """Monitor kinds that count as observers. A sampled monitor below MIN_SAMPLE, an on-alert
    monitor with no declared alert source, and aggregate reports observe nothing. [R1 S2-E4, S3-E5, S3-E6]"""
    out = set()
    for m in intent["monitoring_instruments"]:
        if m["kind"] == "aggregate_report":
            continue
        if m["coverage"] == "sampled" and m.get("sample_rate", 0) < MIN_SAMPLE:
            continue
        if m["coverage"] == "on_alert" and not m.get("alert_source"):
            continue
        out.add(m["kind"])
    return out


def observable(kind: str, monitors: set[str]) -> bool:
    obs = OBSERVERS.get(kind)
    if obs is None:
        return True
    if obs == "any":
        return bool(monitors)
    return bool(obs & monitors)
