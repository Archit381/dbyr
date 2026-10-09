"""Check a whole set of filings the way an intake gate would.

Runs every record-level rule, Closeout-against-Intent reconciliation, notice
timeliness and cross-run lineage over one set of filings, and reports which
filing each finding belongs to.
"""

from __future__ import annotations

import json
from pathlib import Path

from datetime import date, datetime, timedelta

from .adequacy import CLOSEOUT_EVERY_DAYS, MAX_EVAL_DAYS, check_notices
from .lineage import check_lineage
from .validate import Finding, reconcile, validate_record


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _in_force(versions: list[dict], when: str) -> dict:
    """The Intent version in force at a time: the latest filed at or before it (else the first)."""
    filed = [v for v in versions if _ts(v["filed_at"]) <= _ts(when)]
    return (filed or versions)[-1]


def version_rules(run_id: str, versions: list[dict], closeouts: list[dict]) -> list[Finding]:
    """Rules that need every version of a run's Intent and every Closeout. [R1 judge item 9; S3-E2]"""
    out: list[Finding] = []
    kind = versions[-1].get("run_kind")
    starts = [date.fromisoformat(v["start_window"]["start"]) for v in versions]
    ends = [v["start_window"].get("end") for v in versions]
    # A5 across amendments: chaining date-only amendments cannot turn an evaluation into a standing filing.
    if kind in ("evaluation", "internal_deployment") and all(ends):
        span = max(date.fromisoformat(e) for e in ends) - min(starts)
        if span > timedelta(days=MAX_EVAL_DAYS):
            out.append(Finding("error", "standing_intent", run_id,
                               f"versions of this Intent together cover {span.days} days; "
                               f"an evaluation may cover at most {MAX_EVAL_DAYS}"))
    # Closeout cadence and coverage are conduct: a late or missing period is recorded, not refused.
    periods = sorted(closeouts, key=lambda c: c["period_start"])
    for n, c in enumerate(periods):
        ps, pe = date.fromisoformat(c["period_start"]), date.fromisoformat(c["period_end"])
        if (pe - ps).days > CLOSEOUT_EVERY_DAYS:
            out.append(Finding("conduct", "closeout_overdue", f"{run_id} {c['period_start']}",
                               f"one closeout covers {(pe - ps).days} days; closeouts are due every "
                               f"{CLOSEOUT_EVERY_DAYS} days"))
        if n and ps > date.fromisoformat(periods[n - 1]["period_end"]) + timedelta(days=1):
            out.append(Finding("conduct", "closeout_gap", f"{run_id} {c['period_start']}",
                               "no closeout covers the days before this period"))
        intent = _in_force(versions, c["filed_at"])
        win = intent["start_window"]
        if ps < date.fromisoformat(win["start"]) or (win.get("end") and pe > date.fromisoformat(win["end"])):
            out.append(Finding("conduct", "period_outside_window", f"{run_id} {c['period_start']}",
                               "the run operated outside the window declared in the Intent in force"))
    return out


def load_set(paths: list[str | Path]) -> dict[str, dict]:
    """Load filings from files and directories (every *.json in a directory)."""
    out: dict[str, dict] = {}
    for p in map(Path, paths):
        files = sorted(p.glob("*.json")) if p.is_dir() else [p]
        for f in files:
            out[str(f)] = json.loads(f.read_text(encoding="utf-8"))
    return out


def check_set(filings: dict[str, dict], profile: str = "adequacy") -> list[tuple[str, Finding]]:
    out: list[tuple[str, Finding]] = []
    for key, rec in filings.items():
        out += [(key, f) for f in validate_record(rec, profile=profile)]
    good = {k: r for k, r in filings.items() if isinstance(r, dict) and "record_type" in r}
    versions: dict[str, list[dict]] = {}
    for r in good.values():
        if r["record_type"] == "TrainingRunIntent":
            versions.setdefault(r["run_id"], []).append(r)
    for v in versions.values():
        v.sort(key=lambda r: _ts(r["filed_at"]))
    # v0.2 kept one Intent per run_id, whichever loaded last, so amendments were invisible. [R1 judge item 9]
    intents = {run: v[-1] for run, v in versions.items()}
    closeouts = [r for r in good.values() if r["record_type"] == "TrainingRunCloseout"]
    notices = [r for r in good.values() if r["record_type"] == "ExceptionNotice"]
    if profile == "adequacy":
        for run, v in versions.items():
            try:
                out += [("versions", f) for f in version_rules(run, v, [c for c in closeouts if c["run_id"] == run])]
            except (KeyError, TypeError, ValueError) as exc:
                out.append(("versions", Finding("error", "unreconcilable", run, f"{type(exc).__name__}: {exc}")))
    for c in closeouts:
        intent = _in_force(versions[c["run_id"]], c["filed_at"]) if c["run_id"] in versions else None
        if intent is None:
            out.append(("reconcile", Finding("error", "intent_missing", f"{c['run_id']}",
                                             "closeout has no matching Intent in this set")))
            continue
        try:
            out += [("reconcile", f) for f in reconcile(intent, c, profile=profile)]
            if profile == "adequacy":
                out += [("notices", f) for f in check_notices(intent, c, notices)]
        except (KeyError, TypeError, ValueError) as exc:  # malformed records already reported above
            out.append(("reconcile", Finding("error", "unreconcilable", c["run_id"], f"{type(exc).__name__}: {exc}")))
    try:
        out += [("lineage", f) for f in check_lineage(list(intents.values()), closeouts, profile=profile)]
    except (KeyError, TypeError, ValueError) as exc:
        out.append(("lineage", Finding("error", "unreconcilable", "lineage", f"{type(exc).__name__}: {exc}")))
    return out
