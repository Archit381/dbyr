"""Validation: JSON Schema conformance plus the cross-field rules a schema cannot express.

Findings have a severity:
  error    the filing is defective and cannot be lodged until it is amended
  conduct  the filing lodges, but it truthfully records a breach of the filer's own declared
           commitments (a matched criterion with no pause, a restart approved by the wrong role,
           logs lost below the declared floor, evidence destroyed, a late notice). These are flagged
           for adjudication rather than refused, so that admitting a breach is never costlier than
           hiding it. [v0.3; tabletop round 1, judge headline finding 4]
  warning  the filing lodges; a reconciler should look here
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .schemas import validator_for


@dataclass(frozen=True)
class Finding:
    severity: str  # "error" | "conduct" | "warning"
    code: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.code} at {self.where}: {self.message}"


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def schema_findings(record: dict) -> list[Finding]:
    record_type = record.get("record_type")
    try:
        validator = validator_for(record_type)
    except KeyError:
        return [Finding("error", "unknown_record_type", "/record_type", f"{record_type!r} is not a DBYR record type")]
    findings = []
    for err in sorted(validator.iter_errors(record), key=lambda e: list(e.absolute_path)):
        pointer = "/" + "/".join(str(p) for p in err.absolute_path)
        findings.append(Finding("error", "schema", pointer, err.message))
    return findings


# ---------------------------------------------------------------- single records

def intent_rules(intent: dict) -> list[Finding]:
    out: list[Finding] = []
    role_ids = {r["role_id"] for r in intent.get("roles", [])}

    def need_role(role: str | None, where: str) -> None:
        if role is not None and role not in role_ids:
            out.append(Finding("error", "unknown_role", where, f"role {role!r} is not declared in roles[]"))

    sg = intent.get("safeguards_disabled", {})
    if sg.get("disabled") and "T4" not in intent.get("trigger_basis", []):
        out.append(Finding("error", "t4_missing", "/trigger_basis",
                           "safeguards are disabled, so T4 must be listed as a trigger basis"))
    need_role(sg.get("signer_role"), "/safeguards_disabled/signer_role")

    for i, c in enumerate(intent.get("pause_criteria", [])):
        need_role(c.get("authority_role"), f"/pause_criteria/{i}/authority_role")
    need_role(intent.get("restart_protocol", {}).get("approver_role"), "/restart_protocol/approver_role")
    need_role(intent.get("signer", {}).get("role_id"), "/signer/role_id")

    topo = intent.get("egress_topology", {})
    surfaces = {s["surface_id"]: s for s in topo.get("writable_surfaces", [])}
    for i, link in enumerate(topo.get("shared_surface_lineage", [])):
        if link["surface_id"] not in surfaces:
            out.append(Finding("error", "lineage_unknown_surface", f"/egress_topology/shared_surface_lineage/{i}",
                               f"surface {link['surface_id']!r} is not among writable_surfaces"))
    for sid, s in surfaces.items():
        if s["persistence"] in ("cross_run", "permanent") and s["tenancy"] != "run_only":
            if not any(l["surface_id"] == sid for l in topo.get("shared_surface_lineage", [])):
                out.append(Finding("warning", "shared_surface_without_lineage", "/egress_topology/writable_surfaces",
                                   f"surface {sid!r} persists and is shared but no other run is listed; "
                                   "confirm this is the first run to reach it"))
    if not intent.get("monitoring_instruments"):
        out.append(Finding("warning", "no_monitoring_declared", "/monitoring_instruments",
                           "monitoring is declared absent; closeout attestations of no events carry little weight"))
    if "trajectories" not in intent.get("log_retention", {}).get("retained", []):
        out.append(Finding("warning", "trajectories_not_retained", "/log_retention/retained",
                           "trajectories are not retained, so behavioural events cannot be reconciled at V1"))
    return out


def closeout_rules(closeout: dict) -> list[Finding]:
    out: list[Finding] = []
    events = closeout.get("security_events", [])
    if closeout.get("attested_absence") and events:
        out.append(Finding("error", "absence_contradicted", "/attested_absence",
                           "attested_absence is true but security events are listed"))
    if closeout.get("period_end", "") < closeout.get("period_start", ""):
        out.append(Finding("error", "period_inverted", "/period_end", "period_end precedes period_start"))

    # Every affected external party must be accounted for in third_party_notifications.
    event_ids = {e["event_id"] for e in events}
    notified = {n["party"]: n for n in closeout.get("third_party_notifications", [])}
    for i, e in enumerate(events):
        for party in e.get("affected_parties", []):
            if party not in notified:
                out.append(Finding("error", "affected_party_unaccounted", f"/security_events/{i}/affected_parties",
                                   f"{party!r} was affected by {e['event_id']} but has no notification entry"))
    for i, n in enumerate(closeout.get("third_party_notifications", [])):
        for ref in n["affected_by"]:
            if ref not in event_ids:
                out.append(Finding("error", "notification_unknown_event", f"/third_party_notifications/{i}/affected_by",
                                   f"event {ref!r} is not in security_events"))
        if n.get("notified") and n.get("notified_at"):
            first = min((_ts(e["at"]) for e in events if e["event_id"] in n["affected_by"]), default=None)
            if first and _ts(n["notified_at"]) < first:
                out.append(Finding("error", "notified_before_event", f"/third_party_notifications/{i}/notified_at",
                                   "notification predates the event it reports"))

    for i, x in enumerate(closeout.get("containment_exceptions", [])):
        if not x["declared_surface"]:
            out.append(Finding("warning", "undeclared_surface", f"/containment_exceptions/{i}",
                               f"surface {x['surface_id']!r} was not declared in the Intent "
                               "(the expected completeness failure); amend the Intent"))
        if x["status"] == "closed" and "closed_at" not in x:
            out.append(Finding("error", "closed_without_time", f"/containment_exceptions/{i}", "closed exception needs closed_at"))
    for i, s in enumerate(closeout.get("scope_requested_vs_granted", [])):
        req, gr = s["requested"], s["granted"]
        narrowed = gr["start"] > req["start"] or (req.get("end") or "9999") > (gr.get("end") or "9999")
        if narrowed and not s["refusals"]:
            out.append(Finding("error", "silent_scope_narrowing", f"/scope_requested_vs_granted/{i}",
                               "granted scope is narrower than requested but no refusal is logged"))
    return out


def runtime_rules(record: dict) -> list[Finding]:
    return []


RULES = {
    "TrainingRunIntent": intent_rules,
    "TrainingRunCloseout": closeout_rules,
    "SystemRuntimeRecord": runtime_rules,
    "ExceptionNotice": lambda r: [],
}

PROFILES = ("baseline", "adequacy")
"""baseline: the v0.1 rule set (well-formed, internally consistent).
adequacy: baseline plus the v0.2 minimum-content checks in dbyr.adequacy. The default."""


def _check_profile(profile: str) -> None:
    if profile not in PROFILES:
        raise ValueError(f"profile must be one of {PROFILES}")


def validate_record(record: dict, profile: str = "adequacy") -> list[Finding]:
    _check_profile(profile)
    findings = schema_findings(record)
    if any(f.code in ("schema", "unknown_record_type") for f in findings):
        return findings  # cross-field rules assume a well-formed record
    findings = findings + RULES[record["record_type"]](record)
    if profile == "adequacy":
        from . import adequacy
        extra = {
            "TrainingRunIntent": adequacy.intent_adequacy,
            "TrainingRunCloseout": adequacy.closeout_adequacy,
            "ExceptionNotice": adequacy.notice_rules,
        }.get(record["record_type"])
        if extra:
            findings = findings + extra(record)
    return findings


# ---------------------------------------------------------------- Intent <-> Closeout

def reconcile(intent: dict, closeout: dict, profile: str = "adequacy") -> list[Finding]:
    """Check a Closeout against the Intent it closes. This is the V0 half of a V1 reconciliation:
    it checks the filings agree with each other; a V1 auditor then checks them against retained logs."""
    out: list[Finding] = []
    if intent["run_id"] != closeout["run_id"]:
        return [Finding("error", "run_mismatch", "/run_id", "closeout does not close this intent")]

    role_ids = {r["role_id"] for r in intent["roles"]}
    criteria = {c["criterion_id"]: c for c in intent["pause_criteria"]}
    events = {e["event_id"]: e for e in closeout["security_events"]}
    surfaces = {s["surface_id"] for s in intent["egress_topology"]["writable_surfaces"]}

    # Did any event match a declared criterion without a pause event being recorded?
    triggered = {eid for p in closeout["pause_events"] for eid in p.get("triggering_event_ids", [])}
    for eid, e in events.items():
        matching = [c for c in criteria.values() if e["kind"] in c["matches"]]
        if matching and eid not in triggered:
            out.append(Finding("conduct", "criterion_matched_no_pause_event", f"/security_events/{eid}",
                               f"event kind {e['kind']!r} matches criteria "
                               f"{[c['criterion_id'] for c in matching]} but no pause event cites it"))
        for cls in e["evidence"]:
            if cls not in intent["log_retention"]["retained"]:
                out.append(Finding("warning", "evidence_not_retained", f"/security_events/{eid}/evidence",
                                   f"{cls!r} is cited as evidence but was not declared retained"))

    for i, p in enumerate(closeout["pause_events"]):
        c = criteria.get(p["criterion_id"])
        where = f"/pause_events/{i}"
        if c is None:
            out.append(Finding("error", "unknown_criterion", where, f"{p['criterion_id']!r} is not in the Intent"))
            continue
        if p["triggered_by_role"] not in role_ids:
            out.append(Finding("error", "unknown_role", where, f"{p['triggered_by_role']!r} not declared"))
        if p["action_taken"] != c["required_action"]:
            out.append(Finding("warning", "action_differs", where,
                               f"declared action {c['required_action']!r}, recorded {p['action_taken']!r}"))
        r = p.get("restart")
        if r:
            if r["approved_by_role"] != intent["restart_protocol"]["approver_role"]:
                out.append(Finding("conduct", "restart_wrong_approver", where,
                                   f"restart approved by {r['approved_by_role']!r}, protocol names "
                                   f"{intent['restart_protocol']['approver_role']!r}"))
            if intent["restart_protocol"]["intent_amendment_required"] and not r.get("intent_amended"):
                out.append(Finding("conduct", "restart_without_amendment", where,
                                   "restart protocol requires an Intent amendment"))

    for i, x in enumerate(closeout["containment_exceptions"]):
        if x["declared_surface"] != (x["surface_id"] in surfaces):
            out.append(Finding("error", "declared_flag_wrong", f"/containment_exceptions/{i}/declared_surface",
                               "declared_surface does not match the Intent's writable_surfaces"))

    floor = intent["log_retention"].get("minimum_preserved_pct")
    if floor is not None and closeout["logs_preserved_pct"] < floor:
        out.append(Finding("conduct", "retention_below_floor", "/logs_preserved_pct",
                           f"{closeout['logs_preserved_pct']}% preserved, Intent declared at least {floor}%"))
    _check_profile(profile)
    if profile == "adequacy":
        from .adequacy import reconcile_adequacy
        out += reconcile_adequacy(intent, closeout)
    return out


def errors(findings: Iterable[Finding]) -> list[Finding]:
    """Findings that stop a filing being lodged."""
    return [f for f in findings if f.severity == "error"]


def conduct(findings: Iterable[Finding]) -> list[Finding]:
    """Recorded breaches: the filing lodges and the breach goes to adjudication."""
    return [f for f in findings if f.severity == "conduct"]
