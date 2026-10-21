"""Checks on one SystemRuntimeRecord, and on a deployment against the runs it is built on.

  check_runtime     when the record is filed: its roles, monitors, pause criteria, restart protocol
                    and retention (the same checks as an Intent's), what an external deployment must
                    state, and that it was filed before the deployment started
  check_deployment  over the set: every base run is on record, its latest Closeout cleared it for
                    system integration, no problem it reported was still open, and the system gives the
                    model no tool its runs never used

A deployment is the hand-off from a run that was watched to a system people use. These checks make
that hand-off rest on the record: what was cleared, and what was known, when the system went live.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from ..findings import Finding
from .common import criterion_findings, effective_monitors, monitor_findings, restart_findings, retention_findings, ts

EXTERNAL_DUTIES = ("user_exposure", "oversight_mode", "recurring_eval_cadence")


def check_runtime(record: dict) -> list[Finding]:
    out: list[Finding] = []
    role_ids = {r["role_id"] for r in record["roles"]}
    named = [(c["authority_role"], f"/pause_criteria/{i}/authority_role") for i, c in enumerate(record["pause_criteria"])]
    named += [(record["restart_protocol"]["approver_role"], "/restart_protocol/approver_role"),
              (record["signer"]["role_id"], "/signer/role_id")]
    for role, where in named:
        if role not in role_ids:
            out.append(Finding("error", "unknown_role", where, f"role {role!r} is not declared in roles[]"))

    monitors = effective_monitors(record)
    if not record["monitoring_instruments"]:
        out.append(Finding("warning", "no_monitoring_declared", "/monitoring_instruments",
                           "monitoring is declared absent; a Closeout attesting no events carries little weight"))
    out += monitor_findings(record) + criterion_findings(record)
    if record["inter_agent_comms_permitted"]:
        if "inter_agent_messages" not in record["log_retention"]["retained"]:
            out.append(Finding("error", "comms_not_retained", "/log_retention/retained",
                               "instances can read each other's output, so inter_agent_messages must be retained"))
        if not ({"inter_agent_message_monitor", "trajectory_review"} & monitors):
            out.append(Finding("error", "comms_unmonitored", "/monitoring_instruments",
                               "instances can read each other's output but nothing monitors it"))
    out += restart_findings(record) + retention_findings(record)

    # Who uses an external system, and who watches it, must be on record before anyone outside is exposed.
    if record["deployment_context"] == "external":
        for f in EXTERNAL_DUTIES:
            if not record.get(f):
                out.append(Finding("error", "exposure_undeclared", f"/{f}", f"an external deployment must state {f}"))
    if ts(record["filed_at"]).date() > date.fromisoformat(record["deployment_window"]["start"]):
        out.append(Finding("conduct", "runtime_record_late", "/filed_at",
                           "filed after the deployment started; it is due before anyone is exposed"))
    return out


def _deployed_at(record: dict) -> datetime:
    return datetime.fromisoformat(record["deployment_window"]["start"]).replace(tzinfo=timezone.utc)


def check_deployment(runtimes: list[dict], intents: dict[str, dict], closeouts: list[dict],
                     notices: list[dict]) -> list[Finding]:
    """Each SystemRuntimeRecord against what was on record about its base runs when the system was
    deployed. intents maps run_id to the run's latest Intent."""
    out: list[Finding] = []
    for rec in runtimes:
        at = _deployed_at(rec)
        sid = rec["system_id"]
        known = [r for r in rec["base_run_ids"] if r in intents]
        for run in rec["base_run_ids"]:
            where = f"{sid}/base_run_ids/{run}"
            if run not in intents:
                out.append(Finding("error", "base_run_unknown", where, f"run {run!r} has no Intent on record"))
                continue
            before = sorted((c for c in closeouts if c.get("run_id") == run and ts(c["filed_at"]) <= at),
                            key=lambda c: (c["period_end"], c["filed_at"]))
            if not before:
                out.append(Finding("conduct", "deployed_uncleared", where,
                                   f"no Closeout for run {run!r} was on record when the system was deployed"))
            elif before[-1].get("cleared_for_system_integration") is not True:
                out.append(Finding("conduct", "deployed_uncleared", where,
                                   f"the latest Closeout for run {run!r} does not clear it for system integration"))

            # A containment exception is open at deployment if the latest Closeout listing it, among
            # those filed by then, had not closed it.
            latest: dict[str, dict] = {}
            for c in before:
                for x in c["containment_exceptions"]:
                    latest[x["exception_id"]] = x
            for x in latest.values():
                if x["status"] == "open" or ("closed_at" in x and ts(x["closed_at"]) > at):
                    out.append(Finding("conduct", "deployed_over_open_incident", where,
                                       f"containment exception {x['exception_id']!r} on run {run!r} was open when "
                                       "the system was deployed"))
            # A notice is unresolved at deployment if no Closeout filed by then reports its events.
            reported = {e["event_id"] for c in before for e in c["security_events"] + c.get("integrity_events", [])}
            for n in notices:
                if n.get("run_id") == run and ts(n["filed_at"]) <= at and not set(n["event_ids"]) <= reported:
                    out.append(Finding("conduct", "deployed_over_open_incident", where,
                                       f"notice {n['notice_id']!r} on run {run!r} was not yet resolved in a Closeout "
                                       "when the system was deployed"))

        # Tools the runs never had were never seen in use by the runs' monitoring.
        if known:
            used = {c for r in known for c in intents[r].get("agent_capabilities", [])}
            new = [t for t in rec.get("tools_and_scaffolding", []) if t not in used]
            if new:
                out.append(Finding("warning", "untested_tools", f"{sid}/tools_and_scaffolding",
                                   f"{new} were not among any base run's agent_capabilities"))
    return out
