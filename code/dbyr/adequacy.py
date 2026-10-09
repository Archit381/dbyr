"""Adequacy profile (v0.2): minimum-content checks run at intake.

The v0.1 rules check that a filing is well formed and internally consistent. A
filing can pass them and still say nothing: "standard sandboxing", one
catch-all criterion that only notifies, a criterion that no declared monitor
could ever trigger. Filing regimes from environmental impact statements to
model cards have failed this way. These checks set a floor on content. They
were written from reviewers' critiques of an earlier draft and tested in the
tabletop exercise (paper Section 5.2); each cites the tabletop evasion it targets.

They check what a filing commits to, not whether it is true. A false filing
that is specific enough passes; catching it needs V1 reconciliation against
retained logs, or V2 measurement.

Parameters (operator-set, defaults below):
    NOTICE_HOURS        interim ExceptionNotice deadline after detection
    NOTIFY_HOURS        third-party notification deadline after detection
    MAX_EVAL_DAYS       longest window one evaluation Intent may cover
    CORE_KINDS_T4       event kinds a safeguards-off filing must give a pausing criterion
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .validate import Finding

NOTICE_HOURS = 72
NOTIFY_HOURS = 72
MAX_EVAL_DAYS = 31
CORE_KINDS_T4 = ("sandbox_egress", "privilege_escalation", "inter_agent_comms", "third_party_compromise")
PAUSING = ("pause", "pause_and_review", "halt_and_amend_intent")

# v0.3 parameters (tabletop round 1)
SAFEGUARDS = ("model_output_filters", "refusal_behaviour", "per_episode_reset", "network_isolation",
              "identity_separation", "least_privilege_access")
REPORTABLE = ("sandbox_egress", "undeclared_surface_use", "inter_agent_comms", "credential_misuse",
              "privilege_escalation", "remote_code_execution", "agent_induced_outage", "third_party_compromise",
              "environment_tampering", "access_boundary_breach", "data_exposure", "integrity_incident")
MIN_SAMPLE = 0.01          # a sampled monitor below this rate observes nothing for these checks
INTAKE_DAYS = 3            # an Intent must be filed this long before the run starts
RETENTION_FLOOR_MONTHS = 12
CLOSEOUT_EVERY_DAYS = 30

# Which declared monitor kinds can observe which event kinds. An event kind with
# no observer is visible only by accident. Outages and third-party compromises
# are observable without a dedicated monitor (operations alarms; external report).
OBSERVERS = {
    "environment_tampering": {"environment_integrity_check", "write_audit", "reward_seeking_monitor", "trajectory_review"},
    "access_boundary_breach": {"access_log_review", "trajectory_review"},
    "data_exposure": {"access_log_review", "write_audit", "trajectory_review"},
    "integrity_incident": {"write_audit", "trajectory_review"},
    "sandbox_egress": {"egress_alerting", "trajectory_review"},
    "undeclared_surface_use": {"write_audit", "environment_integrity_check", "trajectory_review"},
    "inter_agent_comms": {"inter_agent_message_monitor", "trajectory_review"},
    "credential_misuse": {"access_log_review", "environment_integrity_check"},
    "privilege_escalation": {"access_log_review", "environment_integrity_check"},
    "remote_code_execution": {"environment_integrity_check", "access_log_review", "trajectory_review"},
    "agent_induced_outage": None,  # always observable
    "third_party_compromise": None,  # observable by external report
    "monitor_alert": "any",
}


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def effective_monitors(intent: dict) -> set[str]:
    """Monitor kinds that count as observers. v0.3: a sampled monitor below MIN_SAMPLE, an on-alert
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


# ------------------------------------------------------------------ Intent

def intent_adequacy(intent: dict) -> list[Finding]:
    out: list[Finding] = []
    triggers = set(intent["trigger_basis"])
    t4 = "T4" in triggers
    topo = intent["egress_topology"]
    monitors = effective_monitors(intent)
    criteria = intent["pause_criteria"]

    # A9: a filer that forecasts a high or critical capability must list T3; the forecast and the
    # trigger cannot disagree. (A low forecast that is false is not caught here; see T17.)
    if any(b in ("high", "critical") for b in intent["predicted_capability_band"].values()) and "T3" not in triggers:
        out.append(Finding("error", "t3_missing", "/trigger_basis",
                           "a high or critical capability is forecast, so T3 must be listed"))

    # A2: no monitoring under safeguards-off. [tabletop T07]
    if t4 and not monitors:
        out.append(Finding("error", "no_monitoring_t4", "/monitoring_instruments",
                           "a safeguards-off run must declare at least one monitor"))

    # A8: no enforcement on an egress path under safeguards-off. [T08]
    for n, p in enumerate(topo["permitted_paths"]):
        if t4 and p["enforcement"] == "none":
            out.append(Finding("error", "unenforced_path_t4", f"/egress_topology/permitted_paths/{n}",
                               "a safeguards-off run cannot declare an unenforced egress path"))

    # A3: path writability must be declared, and a writable path needs a surface behind it. [T01]
    via = {s.get("via_path") for s in topo["writable_surfaces"]}
    for n, p in enumerate(topo["permitted_paths"]):
        where = f"/egress_topology/permitted_paths/{n}"
        if "agent_writable" not in p:
            out.append(Finding("error", "writability_undeclared", where,
                               f"path {p['path_id']!r} must state whether agents can write through it"))
        elif p["agent_writable"] and p["path_id"] not in via:
            out.append(Finding("error", "writable_path_without_surface", where,
                               f"path {p['path_id']!r} is writable but no writable surface names it as via_path"))

    # A1: dead criteria. A criterion none of whose event kinds any declared monitor can observe
    # cannot fire except by accident. [T02; worked example DP1, DP3]
    for n, c in enumerate(criteria):
        seen = [k for k in c["matches"] if observable(k, monitors)]
        where = f"/pause_criteria/{n}"
        if not seen:
            out.append(Finding("error", "dead_criterion", where,
                               f"no declared monitor can observe {c['matches']}; criterion {c['criterion_id']!r} cannot fire"))
        elif len(seen) < len(c["matches"]):
            blind = sorted(set(c["matches"]) - set(seen))
            out.append(Finding("warning", "partly_blind_criterion", where,
                               f"criterion {c['criterion_id']!r} cannot observe {blind}"))

    # A4/A2: core coverage under safeguards-off. Each core kind needs a live criterion that pauses. [T03, T04]
    if t4:
        for kind in CORE_KINDS_T4:
            if kind == "inter_agent_comms" and topo["inter_agent_comms_permitted"]:
                continue  # handled by A6
            live = [c for c in criteria
                    if kind in c["matches"] and c["required_action"] in PAUSING and observable(kind, monitors)]
            if not live:
                out.append(Finding("error", "core_kind_uncovered", "/pause_criteria",
                                   f"safeguards-off run has no observable, pausing criterion for {kind!r}"))

    # A6: permitting inter-agent communication is allowed, but then the channel must be declared,
    # retained and watched, so coordination stays visible. [T06]
    if topo["inter_agent_comms_permitted"]:
        shared = [s for s in topo["writable_surfaces"] if s["tenancy"] in ("shared_agents", "shared_runs")]
        if not shared:
            out.append(Finding("error", "comms_channel_undeclared", "/egress_topology/inter_agent_comms_permitted",
                               "inter-agent communication is permitted but no shared surface carries it"))
        if "inter_agent_messages" not in intent["log_retention"]["retained"]:
            out.append(Finding("error", "comms_not_retained", "/log_retention/retained",
                               "inter-agent communication is permitted, so inter_agent_messages must be retained"))
        if not ({"inter_agent_message_monitor", "trajectory_review"} & monitors):
            out.append(Finding("error", "comms_unmonitored", "/monitoring_instruments",
                               "inter-agent communication is permitted but nothing monitors it"))

    # A5: one evaluation Intent per evaluation, not a standing quarterly filing. [T05]
    # A first version inferred "evaluation" from the trigger basis (T4 without T1 or T3). The
    # tabletop showed that fails: an evaluation can also carry T3. Run kind is now declared.
    kind = intent.get("run_kind")
    if kind is None:
        out.append(Finding("error", "run_kind_undeclared", "/run_kind",
                           "declare whether this is a training run or an evaluation"))
    if kind == "evaluation":
        win = intent["start_window"]
        if win.get("end") is None:
            out.append(Finding("error", "standing_intent", "/start_window/end",
                               "a safeguards-off evaluation Intent must have an end date"))
        elif date.fromisoformat(win["end"]) - date.fromisoformat(win["start"]) > timedelta(days=MAX_EVAL_DAYS):
            out.append(Finding("error", "standing_intent", "/start_window",
                               f"an evaluation Intent may cover at most {MAX_EVAL_DAYS} days; file one per evaluation"))
    return out + intent_v03(intent)


# ------------------------------------------------------------------ Closeout

def closeout_adequacy(closeout: dict) -> list[Finding]:
    out: list[Finding] = []
    events = {e["event_id"]: e for e in closeout["security_events"]}
    for eid, e in events.items():
        if "detected_at" not in e:
            out.append(Finding("error", "detection_time_missing", f"/security_events/{eid}",
                               "each event needs detected_at; it starts the notice and notification clocks"))
        elif _ts(e["detected_at"]) < _ts(e["at"]):
            out.append(Finding("error", "detected_before_event", f"/security_events/{eid}", "detected_at precedes the event"))

    # Notification deadline. [T10]
    for n, note in enumerate(closeout["third_party_notifications"]):
        detections = [_ts(events[i]["detected_at"]) for i in note["affected_by"] if i in events and "detected_at" in events[i]]
        if note.get("notified") and note.get("notified_at") and detections:
            delay = _ts(note["notified_at"]) - min(detections)
            if delay > timedelta(hours=NOTIFY_HOURS) and not note.get("delay_reason"):
                out.append(Finding("error", "late_notification", f"/third_party_notifications/{n}",
                                   f"notified {delay.days} days after detection; a delay_reason is required "
                                   f"beyond {NOTIFY_HOURS} hours"))
    return out + closeout_v03(closeout)


# ------------------------------------------------------------------ cross-record

def reconcile_adequacy(intent: dict, closeout: dict) -> list[Finding]:
    out: list[Finding] = []
    monitors = effective_monitors(intent)
    # Attested absence is only as strong as the monitoring behind it. [T19]
    # v0.3: applies whatever the trigger basis, not only under T4. [R1 S2-E6]
    if closeout.get("attested_absence"):
        blind = [k for k in CORE_KINDS_T4 if not observable(k, monitors)]
        if blind:
            out.append(Finding("error", "absence_unsupported", "/attested_absence",
                               f"absence of events is attested, but no declared monitor could observe {blind}"))
    return out + reconcile_v03(intent, closeout)


def check_notices(intent: dict, closeout: dict, notices: list[dict]) -> list[Finding]:
    """Every detected event matching a declared criterion, and every third-party compromise,
    needs an ExceptionNotice filed within NOTICE_HOURS of detection. [T09]"""
    out: list[Finding] = []
    # v0.3: the duty follows a fixed list of reportable kinds, not the criteria the filer chose.
    # In round 1 both filers declared criteria no likely event would match, so nothing was owed. [R1 S2-E2, S3-E3]
    mine = [n for n in notices if n["run_id"] == closeout["run_id"]]
    for e in closeout["security_events"] + closeout.get("integrity_events", []):
        if "detected_at" not in e:
            continue
        if e["kind"] not in REPORTABLE:
            continue
        citing = [n for n in mine if e["event_id"] in n["event_ids"]]
        where = f"/security_events/{e['event_id']}"
        if not citing:
            out.append(Finding("error", "notice_missing", where,
                               f"{e['kind']!r} detected {e['detected_at']} has no ExceptionNotice"))
            continue
        first = min(_ts(n["filed_at"]) for n in citing)
        if first - _ts(e["detected_at"]) > timedelta(hours=NOTICE_HOURS):
            out.append(Finding("conduct", "notice_late", where,
                               f"first notice filed {first.isoformat()}, more than {NOTICE_HOURS} hours after detection"))
    listed = set(closeout.get("notice_ids", []))
    for n in mine:
        if listed and n["notice_id"] not in listed:
            out.append(Finding("error", "notice_not_listed", "/notice_ids",
                               f"notice {n['notice_id']!r} was filed but the closeout does not list it"))
    return out


def notice_rules(notice: dict) -> list[Finding]:
    if _ts(notice["filed_at"]) < _ts(notice["detected_at"]):
        return [Finding("error", "notice_before_detection", "/filed_at", "notice filed before detection")]
    return []


def tenancy_conflicts(intents: list[dict]) -> list[Finding]:
    """Two runs declaring the same surface with different tenancy cannot both be right. [T13]"""
    out: list[Finding] = []
    seen: dict[str, tuple[str, str]] = {}
    for i in intents:
        for s in i["egress_topology"]["writable_surfaces"]:
            sid = s["surface_id"]
            shared = s["tenancy"] != "run_only"
            if sid in seen and seen[sid][1] != str(shared):
                out.append(Finding("error", "tenancy_conflict", f"{i['run_id']}/egress_topology/writable_surfaces",
                                   f"surface {sid!r} is declared {s['tenancy']!r} here but shared differently by run "
                                   f"{seen[sid][0]!r}"))
            seen.setdefault(sid, (i["run_id"], str(shared)))
    return out


# ====================================================================== v0.3
# Rules added after round 1 of the independent tabletop (code/tabletop/independent).
# Each cites the round-1 evasion it targets as [R1 <scenario>-E<n>]. Round 2 tests them on
# scenarios the authors had not read when writing them.

def _months(duration: str) -> float:
    """ISO-8601 duration (PnD, PnM, PnY) or 'indefinite' -> months."""
    if duration == "indefinite":
        return float("inf")
    n, unit = int(duration[1:-1]), duration[-1]
    return {"D": n / 30.4, "M": n, "Y": 12 * n}[unit]


def _shared_agent_surfaces(topo: dict) -> list[dict]:
    return [s for s in topo["writable_surfaces"]
            if s.get("isolation") == "shared" or s["tenancy"] in ("shared_agents", "shared_runs", "external")]


def intent_v03(intent: dict) -> list[Finding]:
    out: list[Finding] = []

    def E(code: str, where: str, msg: str) -> None:
        out.append(Finding("error", code, where, msg))

    topo, sg = intent["egress_topology"], intent["safeguards_disabled"]
    criteria, triggers = intent["pause_criteria"], set(intent["trigger_basis"])
    monitors = effective_monitors(intent)

    # Safeguards checklist: every production safeguard, each with a state. "Relaxed" counts as disabled,
    # so the T4 floor cannot be escaped by calling a weakening a relaxation. [R1 S2-E1, S3-E9]
    items = sg.get("checklist")
    if items is None:
        E("safeguard_checklist_missing", "/safeguards_disabled/checklist", f"state every safeguard: {', '.join(SAFEGUARDS)}")
    else:
        named = [i["safeguard"] for i in items]
        missing = [x for x in SAFEGUARDS if x not in named]
        if missing or len(named) != len(set(named)):
            E("safeguard_checklist_incomplete", "/safeguards_disabled/checklist", f"each safeguard exactly once; missing {missing}")
        weakened = [i for i in items if i["state"] != "on"]
        if bool(weakened) != bool(sg["disabled"]):
            E("disabled_inconsistent", "/safeguards_disabled/disabled",
              "disabled must be true exactly when some checklist item is relaxed or off")
        for n, i in enumerate(items):
            if i["state"] != "on" and not i.get("change"):
                E("safeguard_change_missing", f"/safeguards_disabled/checklist/{n}", f"say what was changed in {i['safeguard']!r}")

    # Monitors must say how much they see and what feeds them. [R1 S2-E4, S3-E6]
    for n, m in enumerate(intent["monitoring_instruments"]):
        where = f"/monitoring_instruments/{n}"
        if m["coverage"] == "sampled" and ("sample_rate" not in m or "review_cadence" not in m):
            E("monitor_unspecified", where, "a sampled monitor needs sample_rate and review_cadence")
        if m["coverage"] == "on_alert" and not m.get("alert_source"):
            E("monitor_unspecified", where, "an on-alert monitor needs an alert_source")
        if not m.get("data_source"):
            E("monitor_unspecified", where, "state the data_source the monitor reads")

    # Every shared agent-writable surface is a channel, whatever the comms flag says. The duty attaches to
    # the surface, so denying communication no longer pays. [R1 S2-E3; judge finding on honesty cost]
    for n, srf in enumerate(topo["writable_surfaces"]):
        if "isolation" not in srf:
            E("isolation_undeclared", f"/egress_topology/writable_surfaces/{n}", "declare isolation: per_episode or shared")
        elif srf["isolation"] == "shared" and srf["tenancy"] == "run_only":
            E("tenancy_mislabelled", f"/egress_topology/writable_surfaces/{n}",
              "a surface agents share cannot be run_only (see the tenancy definition)")
    shared = _shared_agent_surfaces(topo)
    if shared:
        if not topo["inter_agent_comms_permitted"]:
            E("comms_flag_inconsistent", "/egress_topology/inter_agent_comms_permitted",
              f"surfaces {[x['surface_id'] for x in shared]} let agents read each other's writes, so this must be true")
        for kind, need_pause in (("environment_tampering", True), ("inter_agent_comms", False)):
            ok = [c for c in criteria if kind in c["matches"] and observable(kind, monitors)
                  and (c["required_action"] in PAUSING or not need_pause)]
            if not ok:
                E("shared_surface_floor", "/pause_criteria",
                  f"a run with a shared agent-writable surface needs an observable{' pausing' if need_pause else ''} "
                  f"criterion for {kind!r}")

    # Under safeguards-off every reportable kind must appear in some criterion (notify_only allowed beyond
    # the core kinds), so classification cannot route an event around every duty. [R1 S3-E3, S3-E4]
    if "T4" in triggers:
        covered = {k for c in criteria for k in c["matches"]}
        missing = [k for k in REPORTABLE if k not in covered]
        if missing:
            E("kind_uncriteried", "/pause_criteria", f"safeguards-off run has no criterion for {missing}")

    # Retention: per class, with coverage, and long enough. [R1 S2-E9, S3-E7]
    lr = intent["log_retention"]
    horizon = _months(lr["retain_until"].split("+", 1)[1])
    if horizon < RETENTION_FLOOR_MONTHS:
        E("retention_too_short", "/log_retention/retain_until",
          f"retain_until must be at least P{RETENTION_FLOOR_MONTHS}M after closeout")
    detail = {d["evidence_class"]: d for d in lr.get("detail", [])}
    for cls in lr["retained"]:
        d = detail.get(cls)
        if d is None:
            E("retention_detail_missing", "/log_retention/detail", f"give coverage and retention for {cls!r}")
            continue
        if d["coverage"] == "sampled" and "sample_rate" not in d:
            E("retention_detail_missing", "/log_retention/detail", f"{cls!r} is sampled; give sample_rate")
        if _months(d["retention"]) < horizon:
            E("retention_class_short", "/log_retention/detail",
              f"{cls!r} is kept {d['retention']}, shorter than the declared retain_until")
    if "minimum_preserved_pct" not in lr:
        E("preservation_floor_missing", "/log_retention/minimum_preserved_pct", "declare a minimum preserved share")

    # Facts that had nowhere to go in v0.2. [R1 S2-E10, S2-E12, S3-E8, S3-E14, S3-E15]
    for f in ("agent_capabilities", "readable_sources", "run_scale", "forecast_basis"):
        if f not in intent:
            E("field_missing", f"/{f}", f"{f} is required")
    if intent.get("run_kind") in ("training", "training_with_evaluation") and not intent.get("reward_design"):
        E("field_missing", "/reward_design", "a training run must describe its reward and grading design")
    if any(b != "low" for b in intent["predicted_capability_band"].values()) and not intent.get("eval_plan"):
        E("eval_plan_missing", "/eval_plan", "a forecast above low needs an eval_plan that tests it")

    # Process: time for intake review, separate restart approval, explicit end, real amendments.
    win = intent["start_window"]
    if "end" not in win:
        E("end_undeclared", "/start_window/end", "state an end date or null explicitly [R1 S2-E10]")
    elif intent.get("run_kind") in ("evaluation", "internal_deployment") and win["end"] is None:
        E("end_undeclared", "/start_window/end", "an evaluation or deployment needs an end date")
    if "amends" not in intent:
        lead = datetime.fromisoformat(win["start"] + "T00:00:00+00:00") - _ts(intent["filed_at"])
        if lead < timedelta(days=INTAKE_DAYS):
            E("no_intake_time", "/filed_at",
              f"file at least {INTAKE_DAYS} days before the start so intake review can happen [R1: every Intent]")
    elif not intent.get("changes"):
        E("amendment_without_changes", "/changes", "an amendment must list what changed [R1 S3-E2]")
    if intent["restart_protocol"]["approver_role"] in {c["authority_role"] for c in criteria}:
        E("self_approved_restart", "/restart_protocol/approver_role",
          "the restart approver must not be a role that decides pauses [R1 S2-E11, S3-E13]")
    return out


def closeout_v03(closeout: dict) -> list[Finding]:
    out: list[Finding] = []

    def E(code: str, where: str, msg: str) -> None:
        out.append(Finding("error", code, where, msg))

    events = closeout["security_events"] + closeout.get("integrity_events", [])
    ids = {e["event_id"] for e in events}

    # Completeness is attested, not implied by an empty list. [R1 S2-E6]
    if "attested_absence" not in closeout:
        E("absence_not_attested", "/attested_absence", "state attested_absence explicitly")
    elif not events and not closeout.get("absence_basis"):
        # An empty list must be explained either way: a basis for attesting absence, or the reason
        # absence cannot be attested (for example, monitoring too weak to support the claim). A first
        # v0.3 draft required attestation here, which left a weakly monitored run unable to lodge any
        # honest closeout once absence_unsupported applied.
        E("absence_basis_missing", "/absence_basis",
          "no events are listed: state the basis for attesting absence, or why it cannot be attested")
    elif not events and not closeout["attested_absence"]:
        out.append(Finding("warning", "absence_not_supportable", "/attested_absence",
                           "no events are listed and absence is not attested; the stated basis explains why"))
    if closeout.get("attested_absence") and not closeout.get("absence_basis"):
        E("absence_basis_missing", "/absence_basis", "say which monitors support the absence claim")
    # Classification is the filer's choice, so it must be argued. [R1 S3-E3]
    for e in events:
        if not e.get("classification_rationale"):
            E("classification_rationale_missing", f"/events/{e['event_id']}",
              f"say why {e['event_id']} is {e['kind']!r} and not a neighbouring kind")
    if "integrity_events" not in closeout:
        E("field_missing", "/integrity_events", "integrity_events is required (may be empty) [R1 S2-E5, S3-E10]")
    for e in closeout.get("integrity_events", []):
        if "detected_at" not in e:
            E("detection_time_missing", f"/integrity_events/{e['event_id']}", "each event needs detected_at")

    # Every internal incident is mapped to an event or explained. [R1 S2-E5, S3-E10]
    if "internal_incidents" not in closeout:
        E("field_missing", "/internal_incidents", "list every internal incident opened about the run (may be empty)")
    for n, inc in enumerate(closeout.get("internal_incidents", [])):
        refs = inc.get("event_ids", [])
        if not refs and not inc.get("not_an_event_reason"):
            E("incident_unmapped", f"/internal_incidents/{n}", "map the incident to events or state not_an_event_reason")
        for r in refs:
            if r not in ids:
                E("incident_unknown_event", f"/internal_incidents/{n}", f"event {r!r} is not listed")

    # Preservation per class; the headline figure is the weakest class. [R1 S2-E7, S3-E12]
    pres = closeout.get("preservation")
    if not pres:
        E("preservation_missing", "/preservation", "give preservation per evidence class")
    else:
        weakest = min(p["sample_rate"] * p["preserved_pct"] for p in pres)
        if closeout["logs_preserved_pct"] > weakest + 1e-9:
            E("preservation_overstated", "/logs_preserved_pct",
              f"{closeout['logs_preserved_pct']} exceeds the weakest class ({weakest:.2f}); see the field definition")

    # Mid-run changes, and no evidence destroyed while an incident is open. [R1 S2-E8]
    for f in ("config_changes", "surface_resets"):
        if f not in closeout:
            E("field_missing", f"/{f}", f"{f} is required (may be empty)")
    for n, r in enumerate(closeout.get("surface_resets", [])):
        at = _ts(r["at"])
        open_inc = [i for i in closeout.get("internal_incidents", [])
                    if _ts(i["opened_at"]) <= at and ("closed_at" not in i or at < _ts(i["closed_at"]))]
        if open_inc and not r["snapshot_retained"]:
            out.append(Finding("conduct", "evidence_destroyed", f"/surface_resets/{n}",
              f"surface {r['surface_id']!r} reset without a snapshot while incident {open_inc[0]['incident_id']!r} was open"))
    for n, c in enumerate(closeout.get("config_changes", [])):
        if not c["intent_amended"]:
            out.append(Finding("warning", "change_without_amendment", f"/config_changes/{n}",
                               "a configuration change without an Intent amendment; confirm it changes no declared fact"))
    return out


def reconcile_v03(intent: dict, closeout: dict) -> list[Finding]:
    out: list[Finding] = []
    if closeout.get("preservation"):
        covered = {p["evidence_class"] for p in closeout["preservation"]}
        missing = [c for c in intent["log_retention"]["retained"] if c not in covered]
        if missing:
            out.append(Finding("error", "preservation_incomplete", "/preservation", f"no preservation entry for {missing}"))
    if closeout["status"] == "rolling" and intent.get("run_kind") not in ("training", "training_with_evaluation"):
        out.append(Finding("error", "rolling_not_training", "/status", "only training runs may be rolling [R1 S3-E2]"))
    # (retention below the declared floor is a conduct finding in validate.reconcile, not a lodging error)
    return out
