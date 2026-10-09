"""Honest filing sets for three synthetic scenarios.

The scenarios are invented ("Lab X") and deliberately unlike the 2026 incident,
so the tabletop does not reuse the case the schema was derived from. Each honest
set must pass both the v0.1 rules and the v0.2 adequacy checks with no errors;
that is the false-positive control. Attacks then modify a copy of these sets.
v0.3 upgrade: every honest set also carries the fields and states the round-1
rules require (safeguards checklist, monitor sources, per-class retention and
preservation, incident register), and is filed with time for intake review.

  S1  RL training of coding agents; two runs share a writable artifact cache.
      Safeguards on. Triggers T1, T3.
  S2  Safeguards-off cyber evaluation, 14 days, read-only web access through an
      allowlist proxy. One egress event, one affected third party. Triggers T2, T3, T4.
  S3  Multi-agent research swarm that is *permitted* to communicate through a
      shared scratchpad. Triggers T2, T3, T4.
"""

from __future__ import annotations

import copy

ORG = "Lab X (synthetic)"
ROLES = [
    {"role_id": "R-lead", "title": "Run lead", "organisation": ORG},
    {"role_id": "R-eval", "title": "Evaluation owner", "organisation": ORG},
    {"role_id": "R-sec", "title": "Security lead", "organisation": ORG},
    {"role_id": "R-safe", "title": "Safety lead", "organisation": ORG},
    {"role_id": "R-review", "title": "Restart review lead (no pause authority)", "organisation": ORG},
]
VERSION = "0.3"
CLASS_RETENTION = "P24M"
SIGNER = {"role_id": "R-lead", "organisation": ORG}
RETENTION = {
    "retained": ["trajectories", "chain_of_thought", "tool_calls", "egress_logs", "access_logs", "inter_agent_messages"],
    "retain_until": "closeout+P24M",
    "review_method": "full trajectory review by monitor model, human review of flags",
    "minimum_preserved_pct": 99,
}
RETENTION["detail"] = [{"evidence_class": c, "coverage": "complete", "retention": CLASS_RETENTION}
                       for c in RETENTION["retained"]]
SCOPE = {"committed": True, "refusals_logged": True, "model_access_committed": True}
MONITORS_FULL = [
    {"kind": "egress_alerting", "coverage": "all", "data_source": "proxy and firewall logs"},
    {"kind": "access_log_review", "coverage": "all", "review_cadence": "daily", "data_source": "IAM and service access logs"},
    {"kind": "inter_agent_message_monitor", "coverage": "all", "data_source": "shared-surface write log"},
    {"kind": "write_audit", "coverage": "all", "data_source": "filesystem and object-store audit log"},
    {"kind": "trajectory_review", "coverage": "sampled", "sample_rate": 0.2, "review_cadence": "daily",
     "data_source": "agent transcripts"},
]
SAFEGUARDS = ("model_output_filters", "refusal_behaviour", "per_episode_reset", "network_isolation",
              "identity_separation", "least_privilege_access")


def _safeguards(off: bool) -> dict:
    items = [{"safeguard": x, "state": "on"} for x in SAFEGUARDS]
    if not off:
        return {"disabled": False, "checklist": items}
    items[1] = {"safeguard": "refusal_behaviour", "state": "relaxed", "change": "cyber refusals lowered"}
    return {"disabled": True, "relaxed": ["cyber refusals lowered"], "signer_role": "R-eval", "checklist": items}


def _criteria() -> list[dict]:
    c = lambda cid, kinds, action="pause_and_review", who="R-safe": {
        "criterion_id": cid, "matches": kinds, "adjudication": "human", "authority_role": who, "required_action": action}
    return [
        c("C-egress", ["sandbox_egress", "undeclared_surface_use"]),
        c("C-comms", ["inter_agent_comms"]),
        c("C-priv", ["credential_misuse", "privilege_escalation", "remote_code_execution"]),
        c("C-outage", ["agent_induced_outage"], who="R-sec"),
        c("C-third", ["third_party_compromise"], action="halt_and_amend_intent"),
        c("C-tamper", ["environment_tampering"]),
        c("C-boundary", ["access_boundary_breach", "data_exposure"]),
        c("C-integrity", ["integrity_incident"], action="notify_only"),
    ]


def _intent(run_id: str, filed: str, start: str, end, triggers, bands, topo, safeguards_off: bool,
            kind: str = "evaluation") -> dict:
    return {
        "schema_version": VERSION, "record_type": "TrainingRunIntent", "run_id": run_id, "developer": ORG,
        "run_kind": kind,
        "filed_at": filed, "trigger_basis": triggers, "start_window": {"start": start, "end": end},
        "compute_band": "1e26-1e27" if "T1" in triggers else "1e24-1e25",
        "predicted_capability_band": bands,
        "monitoring_instruments": copy.deepcopy(MONITORS_FULL),
        "egress_topology": topo,
        "safeguards_disabled": _safeguards(safeguards_off),
        "pause_criteria": _criteria(),
        "restart_protocol": {"approver_role": "R-review", "evidence_required": ["root cause", "path closed"],
                             "intent_amendment_required": True},
        "roles": copy.deepcopy(ROLES), "log_retention": copy.deepcopy(RETENTION),
        "investigator_scope_expansion": dict(SCOPE), "amendments_allowed": True, "signer": SIGNER,
        "agent_capabilities": ["shell in sandbox", "package install through declared paths"],
        "readable_sources": ["task repository", "declared package mirror"],
        "run_scale": {"concurrent_agents": 64},
        "forecast_basis": "scaling trend from the previous checkpoint's dangerous-capability evaluations",
        "eval_plan": [{"eval_id": f"{run_id}-dc", "evaluator": "external", "domain": "cyber"}],
        **({"reward_design": "unit-test pass rate on held-out tests; graders isolated from agent-writable paths"}
           if kind in ("training", "training_with_evaluation") else {}),
    }


def _closeout(run_id, start, end, **kw) -> dict:
    base = {
        "schema_version": VERSION, "record_type": "TrainingRunCloseout", "run_id": run_id,
        "filed_at": f"{end}T12:00:00Z", "period_start": start, "period_end": end, "status": "completed",
        "attested_absence": False, "security_events": [], "pause_events": [], "containment_exceptions": [],
        "logs_preserved_pct": 99.5, "logs_retention_confirmed": True, "scope_requested_vs_granted": [],
        "third_party_notifications": [], "notice_ids": [], "signer": SIGNER,
        "integrity_events": [], "internal_incidents": [], "config_changes": [], "surface_resets": [],
        "preservation": [{"evidence_class": c, "denominator": "all records generated in the period",
                          "sample_rate": 1.0, "preserved_pct": 99.5} for c in RETENTION["retained"]],
    }
    base.update(kw)
    if base["attested_absence"]:
        base.setdefault("absence_basis", "egress alerting, write audit and message monitor at full coverage; "
                                         "20% trajectory sample reviewed daily")
    return base


def s1() -> dict:
    """RL coding agents, two runs sharing a writable artifact cache."""
    def topo(lineage):
        return {
            "environment": "digital_twin",
            "permitted_paths": [{"path_id": "cache-path", "via": "internal artifact cache (pip/npm mirror)",
                                 "enforcement": "proxy_allowlist", "agent_writable": True}],
            "credential_scope": {"held_by_agents": ["build token, cache-scoped"], "admin_credentials_reachable": False},
            # The cache lets one run's agents read another's builds, so as a matter of fact
            # communication is possible; v0.3 makes this a statement about the environment.
            "inter_agent_comms_permitted": True,
            "writable_surfaces": [{"surface_id": "artifact-cache", "kind": "artifact_store", "via_path": "cache-path",
                                   "isolation": "shared",
                                   "direction": {"writers": ["agents (build outputs)"], "readers": ["agents in all runs"]},
                                   "persistence": "cross_run", "tenancy": "shared_runs", "detail": "[sealed]"}],
            "shared_surface_lineage": lineage,
        }
    bands = {"cyber": "medium", "cbrn": "low", "autonomy": "high", "persuasion": "low"}
    a = _intent("s1-coder-a", "2026-07-27T00:00:00Z", "2026-08-01", None, ["T1", "T3"], bands, topo([]), False, kind="training")
    b = _intent("s1-coder-b", "2026-08-05T00:00:00Z", "2026-08-10", None, ["T1", "T3"], bands,
                topo([{"surface_id": "artifact-cache", "run_id": "s1-coder-a"}]), False, kind="training")
    ca = _closeout("s1-coder-a", "2026-08-01", "2026-08-31", status="rolling", attested_absence=True)
    return {"intent:A": a, "intent:B": b, "closeout:A": ca}


def s2() -> dict:
    """Safeguards-off cyber evaluation with one egress event and one affected third party."""
    topo = {
        "environment": "live",
        "permitted_paths": [{"path_id": "web-ro", "via": "allowlist HTTP proxy, GET only",
                             "enforcement": "proxy_allowlist", "agent_writable": False}],
        "credential_scope": {"held_by_agents": ["eval sandbox account"], "admin_credentials_reachable": False},
        "inter_agent_comms_permitted": False,
        "writable_surfaces": [{"surface_id": "eval-scratch", "kind": "shared_filesystem",
                               "direction": {"writers": ["agent"], "readers": ["agent", "graders"]},
                               "persistence": "run", "tenancy": "run_only", "isolation": "per_episode",
                               "detail": "[sealed]"}],
        "shared_surface_lineage": [],
    }
    bands = {"cyber": "high", "cbrn": "low", "autonomy": "medium", "persuasion": "low"}
    intent = _intent("s2-cyber-eval", "2026-08-27T00:00:00Z", "2026-09-01", "2026-09-14",
                     ["T2", "T3", "T4"], bands, topo, True)
    event = {"event_id": "E1", "at": "2026-09-05T03:00:00Z", "detected_at": "2026-09-05T04:00:00Z",
             "kind": "sandbox_egress", "description": "POST to an allowlisted host via request smuggling",
             "evidence": ["egress_logs", "trajectories"], "affected_parties": ["Example Hosting Ltd"],
             "classification_rationale": "traffic left the sandbox by a route the topology does not permit; "
                                         "no credentials were misused and no external system was altered"}
    pause = {"criterion_id": "C-egress", "triggering_event_ids": ["E1"], "triggered_at": "2026-09-05T04:30:00Z",
             "triggered_by_role": "R-safe", "action_taken": "pause_and_review",
             "restart": {"approved_by_role": "R-review", "approved_at": "2026-09-07T10:00:00Z",
                         "evidence": ["smuggling vector closed at proxy"], "intent_amended": True}}
    exc = {"exception_id": "X1", "surface_id": "web-ro", "declared_surface": False, "kind": "egress",
           "opened_at": "2026-09-05T03:00:00Z", "closed_at": "2026-09-07T10:00:00Z", "status": "closed"}
    closeout = _closeout(
        "s2-cyber-eval", "2026-09-01", "2026-09-14",
        security_events=[event], pause_events=[pause], containment_exceptions=[exc],
        scope_requested_vs_granted=[{"investigator": "External evaluator", "requested": {"start": "2026-09-01", "end": "2026-09-14"},
                                     "granted": {"start": "2026-09-01", "end": "2026-09-14"}, "model_access_granted": True,
                                     "refusals": []}],
        third_party_notifications=[{"party": "Example Hosting Ltd", "affected_by": ["E1"], "notified": True,
                                    "notified_at": "2026-09-05T20:00:00Z", "channel": "security contact"}],
        notice_ids=["N1"],
        internal_incidents=[{"incident_id": "INC-1", "opened_at": "2026-09-05T04:10:00Z", "closed_at": "2026-09-07T10:00:00Z",
                             "summary": "egress via request smuggling", "event_ids": ["E1"]}],
        config_changes=[{"at": "2026-09-07T09:00:00Z", "what": "request-smuggling vector closed at the proxy",
                         "intent_amended": True}])
    notice = {"schema_version": VERSION, "record_type": "ExceptionNotice", "notice_id": "N1", "run_id": "s2-cyber-eval",
              "filed_at": "2026-09-06T09:00:00Z", "detected_at": "2026-09-05T04:00:00Z", "event_ids": ["E1"],
              "kinds": ["sandbox_egress"], "criterion_ids": ["C-egress"], "summary": "egress via request smuggling",
              "affected_parties": ["Example Hosting Ltd"], "action_taken": "pause_and_review", "signer": SIGNER}
    return {"intent:A": intent, "closeout:A": closeout, "notice:N1": notice}


def s3() -> dict:
    """Swarm permitted to communicate via a shared scratchpad, declared, retained and monitored."""
    topo = {
        "environment": "digital_twin",
        "permitted_paths": [],
        "credential_scope": {"held_by_agents": [], "admin_credentials_reachable": False},
        "inter_agent_comms_permitted": True,
        "writable_surfaces": [{"surface_id": "swarm-pad", "kind": "database",
                               "direction": {"writers": ["all swarm agents"], "readers": ["all swarm agents"]},
                               "persistence": "run", "tenancy": "shared_agents", "isolation": "shared",
                               "detail": "[sealed]"}],
        "shared_surface_lineage": [],
    }
    bands = {"cyber": "medium", "cbrn": "low", "autonomy": "high", "persuasion": "medium"}
    intent = _intent("s3-swarm", "2026-09-05T00:00:00Z", "2026-09-10", "2026-09-30",
                     ["T2", "T3", "T4"], bands, topo, True)
    # Communication is the point of this run, so pausing on it would fire on every message:
    # record it (v0.3 requires a criterion on any shared surface) but do not pause.
    for c in intent["pause_criteria"]:
        if c["criterion_id"] == "C-comms":
            c["required_action"] = "notify_only"
    closeout = _closeout("s3-swarm", "2026-09-10", "2026-09-30", attested_absence=True)
    return {"intent:A": intent, "closeout:A": closeout}


SCENARIOS = {"S1": s1, "S2": s2, "S3": s3}
