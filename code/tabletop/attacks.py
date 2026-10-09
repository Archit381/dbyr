"""Evasion attempts for the tabletop exercise.

Each attack takes an honest filing set from scenarios.py and modifies it to hide
one material fact while trying to stay compliant. The source column records who
proposed the evasion: an external reviewer of an earlier draft, an earlier
internal critique, or the authors. The `catch` text is the authors' account of
what, outside the validator, would expose the evasion if the validator does not.

Round 1 scores these against the v0.1 rules, which were fixed before any
evasion was written, so it is a fair test. The v0.2 checks and most evasions
were drawn from the same reviewer critiques by the same authors, so round 2 is
in-sample: it shows the checks work as intended, not that they generalise. One
evasion (T05) survived the first version of the v0.2 checks; the fix was an
explicit run_kind field.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

REVIEW = "External review"
APART = "Apart review"
CRIT = "Earlier critique"
AUTH = "Authors"


@dataclass(frozen=True)
class Attack:
    id: str
    scenario: str
    title: str
    source: str
    conceals: str
    catch: str
    apply: Callable[[dict], None]


def _shift(ts: str, **delta) -> str:
    return (datetime.fromisoformat(ts.replace("Z", "+00:00")) + timedelta(**delta)).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------- modifiers

def vague_topology(f):
    t = f["intent:A"]["egress_topology"]
    t["permitted_paths"][0]["via"] = "standard sandboxing"
    t["permitted_paths"][0].pop("agent_writable")
    t["writable_surfaces"] = []


def dead_comms_criterion(f):
    f["intent:A"]["monitoring_instruments"] = [m for m in f["intent:A"]["monitoring_instruments"]
                                               if m["kind"] not in ("inter_agent_message_monitor", "trajectory_review")]


def all_notify_only(f):
    for c in f["intent:A"]["pause_criteria"]:
        c["required_action"] = "notify_only"


def catch_all_criterion(f):
    f["intent:A"]["pause_criteria"] = [{"criterion_id": "C-any", "matches": ["monitor_alert"], "adjudication": "human",
                                        "authority_role": "R-safe", "required_action": "pause_and_review"}]
    for p in f["closeout:A"]["pause_events"]:
        p["criterion_id"] = "C-any"


def standing_quarterly(f):
    f["intent:A"]["start_window"]["end"] = "2026-11-30"


def comms_permitted_dodge(f):
    i = f["intent:A"]
    i["egress_topology"]["inter_agent_comms_permitted"] = True
    i["pause_criteria"] = [c for c in i["pause_criteria"] if c["criterion_id"] != "C-comms"]
    i["log_retention"]["retained"] = [r for r in i["log_retention"]["retained"] if r != "inter_agent_messages"]
    dead_comms_criterion(f)


def no_monitoring(f):
    f["intent:A"]["monitoring_instruments"] = []


def unenforced_path(f):
    f["intent:A"]["egress_topology"]["permitted_paths"][0]["enforcement"] = "none"


def no_interim_notice(f):
    f.pop("notice:N1")
    f["closeout:A"]["notice_ids"] = []


def late_notification(f):
    n = f["closeout:A"]["third_party_notifications"][0]
    n["notified_at"] = _shift(n["notified_at"], days=20)


def boilerplate_non_notification(f):
    n = f["closeout:A"]["third_party_notifications"][0]
    n.update({"notified": False, "not_notified_reason": "not required"})
    n.pop("notified_at")


def boilerplate_scope_refusal(f):
    s = f["closeout:A"]["scope_requested_vs_granted"][0]
    s["granted"] = {"start": "2026-09-08", "end": "2026-09-14"}
    s["model_access_granted"] = False
    s["refusals"] = [{"at": "2026-09-20T00:00:00Z", "what": "first week; model access",
                      "grounds": "commercial sensitivity", "refused_by_role": "R-lead"}]


def one_run_misdeclares_tenancy(f):
    t = f["intent:B"]["egress_topology"]
    t["writable_surfaces"][0]["tenancy"] = "run_only"
    t["shared_surface_lineage"] = []


def both_runs_misdeclare_tenancy(f):
    # v0.3-aware: the attacker keeps every declaration consistent with the lie, so the only
    # thing wrong is the fact itself (the cache is shared). [isolation and comms flag added in v0.3]
    for k in ("intent:A", "intent:B"):
        t = f[k]["egress_topology"]
        t["writable_surfaces"][0]["tenancy"] = "run_only"
        t["writable_surfaces"][0]["isolation"] = "per_episode"
        t["inter_agent_comms_permitted"] = False
        t["shared_surface_lineage"] = []


def hide_safeguards_off(f):
    # v0.3-aware: the checklist is kept and every item marked "on", which is false but consistent.
    i = f["intent:A"]
    checklist = [{"safeguard": c["safeguard"], "state": "on"} for c in i["safeguards_disabled"].get("checklist", [])]
    i["safeguards_disabled"] = {"disabled": False, **({"checklist": checklist} if checklist else {})}
    i["trigger_basis"] = [t for t in i["trigger_basis"] if t != "T4"]


def split_below_threshold(f):
    for k in ("intent:A", "intent:B"):
        f[k]["trigger_basis"] = [t for t in f[k]["trigger_basis"] if t != "T1"]
        f[k]["compute_band"] = "1e25-1e26"


def lowball_forecast(f):
    i = f["intent:A"]
    i["predicted_capability_band"] = {k: "medium" for k in i["predicted_capability_band"]}
    i["trigger_basis"] = [t for t in i["trigger_basis"] if t != "T3"]


def restart_by_wrong_role(f):
    f["closeout:A"]["pause_events"][0]["restart"]["approved_by_role"] = "R-lead"


def blind_absence(f):
    i, c = f["intent:A"], f["closeout:A"]
    # v0.3-aware: the monitor names an alert source and data source, the incident register and
    # config changes are emptied with the events, and a basis is stated, so only the blindness remains.
    i["monitoring_instruments"] = [{"kind": "access_log_review", "coverage": "on_alert",
                                    "alert_source": "IAM anomaly rule", "data_source": "IAM logs"}]
    c.update({"security_events": [], "pause_events": [], "containment_exceptions": [],
              "third_party_notifications": [], "notice_ids": [], "attested_absence": True,
              "internal_incidents": [], "config_changes": [],
              "absence_basis": "access-log review raised no alerts"})
    f.pop("notice:N1", None)


def silent_scope_narrowing(f):
    s = f["closeout:A"]["scope_requested_vs_granted"][0]
    s["granted"] = {"start": "2026-09-08", "end": "2026-09-14"}


ATTACKS = [
    Attack("T01", "S1", "Vague topology: ``standard sandboxing'', writability omitted, no surfaces", REVIEW,
           "agents can write to a cache shared across runs", "", vague_topology),
    Attack("T02", "S2", "Criterion no declared monitor can trigger", REVIEW,
           "inter-agent communication would go unseen", "", dead_comms_criterion),
    Attack("T03", "S2", "Every criterion only notifies", REVIEW,
           "nothing would pause the run", "", all_notify_only),
    Attack("T04", "S2", "One catch-all criterion on monitor alerts", AUTH,
           "no specific event would pause the run", "", catch_all_criterion),
    Attack("T05", "S2", "Standing quarterly Intent for evaluations", CRIT,
           "individual evaluations are invisible", "", standing_quarterly),
    Attack("T06", "S2", "Declare communication permitted so coordination is never an exception", AUTH,
           "coordination channel unmonitored and unretained", "", comms_permitted_dodge),
    Attack("T07", "S2", "No monitoring under safeguards-off", AUTH,
           "no events can be detected", "", no_monitoring),
    Attack("T08", "S2", "Egress path with no enforcement", AUTH,
           "sandbox is open", "", unenforced_path),
    Attack("T09", "S2", "Exception first reported at the 30-day closeout", REVIEW,
           "an egress event for up to a month", "", no_interim_notice),
    Attack("T10", "S2", "Third party notified 20 days late, no reason", REVIEW,
           "delay in telling a victim", "", late_notification),
    Attack("T11", "S2", "Third party not told; reason ``not required''", AUTH,
           "a victim was never told", "Adjudicator reviews stated reasons; requester right (future work)",
           boilerplate_non_notification),
    Attack("T12", "S2", "Scope narrowed with boilerplate grounds", AUTH,
           "investigators blocked from the first week", "Refusal is on record; adequacy of grounds needs an adjudicator",
           boilerplate_scope_refusal),
    Attack("T13", "S1", "One run declares a shared cache run-only", CRIT,
           "cross-run channel for run B", "", one_run_misdeclares_tenancy),
    Attack("T14", "S1", "Both runs declare a shared cache run-only", CRIT,
           "cross-run channel for both runs", "V1: access logs show cross-run writes", both_runs_misdeclare_tenancy),
    Attack("T15", "S2", "Safeguards-off not declared (T4 omitted)", REVIEW,
           "classifiers were relaxed", "V1: configuration snapshots; whistleblower", hide_safeguards_off),
    Attack("T16", "S1", "Runs split below the compute threshold", REVIEW,
           "true compute", "V2: compute telemetry (research stage)", split_below_threshold),
    Attack("T17", "S1", "Capability forecast lowered to avoid T3", CRIT,
           "expected capability", "Closeout capability results against forecast; external evaluation", lowball_forecast),
    Attack("T18", "S2", "Restart approved by an undeclared approver", AUTH,
           "who authorised the restart", "", restart_by_wrong_role),
    Attack("T19", "S2", "Absence of events attested with blind monitoring", AUTH,
           "events that could not have been seen", "", blind_absence),
    Attack("T20", "S2", "Investigation scope narrowed with no refusal logged", AUTH,
           "investigators blocked from the first week", "", silent_scope_narrowing),
]
