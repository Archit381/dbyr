"""Checks on one TrainingRunIntent.

Three groups, run in this order:
  consistency   roles, the T4 trigger, lineage references; warnings on monitoring and retention
  coverage      criteria a declared monitor can observe, enforced and declared paths, core coverage
                under safeguards-off, the inter-agent channel, the evaluation window
  completeness  the safeguards checklist, monitor specifications, shared surfaces, reportable kinds,
                retention, required fields, intake time and amendments

They check what a filing commits to, not whether it is true. A false filing that is
specific enough passes; catching it needs reconciliation against retained logs.
Rules cite the evasion that motivated them: [T..] the scripted tabletop, [R1 ..] round 1
of the independent tabletop.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from ..findings import Finding
from ..params import CORE_KINDS_T4, INTAKE_DAYS, MAX_EVAL_DAYS, PAUSING, REPORTABLE, RETENTION_FLOOR_MONTHS, SAFEGUARDS
from .common import effective_monitors, months, observable, shared_agent_surfaces, ts


def check_intent(intent: dict) -> list[Finding]:
    return consistency(intent) + coverage(intent) + completeness(intent)


def consistency(intent: dict) -> list[Finding]:
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


def coverage(intent: dict) -> list[Finding]:
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
    # Run kind is declared, not inferred from the trigger basis: an evaluation can also carry T3.
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
    return out


def completeness(intent: dict) -> list[Finding]:
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
    # the surface, so denying communication does not pay. [R1 S2-E3; judge finding on honesty cost]
    for n, srf in enumerate(topo["writable_surfaces"]):
        if "isolation" not in srf:
            E("isolation_undeclared", f"/egress_topology/writable_surfaces/{n}", "declare isolation: per_episode or shared")
        elif srf["isolation"] == "shared" and srf["tenancy"] == "run_only":
            E("tenancy_mislabelled", f"/egress_topology/writable_surfaces/{n}",
              "a surface agents share cannot be run_only (see the tenancy definition)")
    shared = shared_agent_surfaces(topo)
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
    horizon = months(lr["retain_until"].split("+", 1)[1])
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
        if months(d["retention"]) < horizon:
            E("retention_class_short", "/log_retention/detail",
              f"{cls!r} is kept {d['retention']}, shorter than the declared retain_until")
    if "minimum_preserved_pct" not in lr:
        E("preservation_floor_missing", "/log_retention/minimum_preserved_pct", "declare a minimum preserved share")

    # Facts a filer must state. [R1 S2-E10, S2-E12, S3-E8, S3-E14, S3-E15]
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
        lead = datetime.fromisoformat(win["start"] + "T00:00:00+00:00") - ts(intent["filed_at"])
        if lead < timedelta(days=INTAKE_DAYS):
            E("no_intake_time", "/filed_at",
              f"file at least {INTAKE_DAYS} days before the start so intake review can happen [R1: every Intent]")
    elif not intent.get("changes"):
        E("amendment_without_changes", "/changes", "an amendment must list what changed [R1 S3-E2]")
    if intent["restart_protocol"]["approver_role"] in {c["authority_role"] for c in criteria}:
        E("self_approved_restart", "/restart_protocol/approver_role",
          "the restart approver must not be a role that decides pauses [R1 S2-E11, S3-E13]")
    return out
