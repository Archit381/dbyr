"""Write generated/schema_fields.tex from the DBYR schemas and adequacy constants.

    python3 paper_tools/schema_tables.py        (run from the repository root)

Produces, for main.tex:
  * protocol constants (\\dbyrNoticeHours, \\dbyrIntakeDays, ...) read from code/dbyr/adequacy.py
  * field lists for the schema figure (\\figIntentList etc.), with tier letters
  * longtable rows for Appendix B (\\appIntentRows etc.)

"Required" means required by the JSON Schema or, unconditionally, by the adequacy
profile. Conditionally required fields are marked in the appendix, not the figure.
Reads the code; never changes it. Lives outside code/dbyr so the frozen v0.3
checker is untouched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

from dbyr import adequacy  # noqa: E402

SCHEMA = ROOT / "code/dbyr/schema"
OUT = ROOT / "generated/schema_fields.tex"

RECORDS = [
    ("Intent", "training_run_intent.schema.json"),
    ("Closeout", "training_run_closeout.schema.json"),
    ("Notice", "exception_notice.schema.json"),
    ("Runtime", "system_runtime_record.schema.json"),
]
META = {"schema_version", "record_type", "filed_at", "amends", "changes"}

# Required by adequacy.py regardless of other values (see intent_v03 / closeout_v03).
ADEQ_ALWAYS = {
    "Intent": {"run_kind", "agent_capabilities", "readable_sources", "run_scale", "forecast_basis"},
    "Closeout": {"attested_absence", "integrity_events", "internal_incidents", "preservation",
                 "config_changes", "surface_resets"},
}
# Required by adequacy.py only in some cases.
ADEQ_WHEN = {
    ("Intent", "reward_design"): "training runs",
    ("Intent", "eval_plan"): "any forecast above low",
    ("Closeout", "absence_basis"): "no events listed, or absence attested",
    ("Closeout", "notice_ids"): "notices were filed",
}

# Notes for fields whose schema has no description.
NOTES = {
    "run_id": "Stable identifier; amendments keep it.",
    "developer": "Legal entity filing.",
    "trigger_basis": "T1 compute, T2 covered developer, T3 forecast crossing, T4 safeguards off.",
    "start_window": "Start and explicit end (null only for rolling training).",
    "data_classes": "Classes of training or evaluation data.",
    "predicted_capability_band": "Per domain: cyber, CBRN, autonomy, persuasion.",
    "egress_topology": "Paths with enforcement and writability; credential scope; inter-agent communication as a fact "
                       "about the environment; writable surfaces by direction, persistence, tenancy and isolation; "
                       "lineage to other runs; inherited exceptions.",
    "safeguards_disabled": "Checklist of six production safeguards, each on, relaxed or off; relaxed counts as "
                           "disabled; signing role.",
    "restart_protocol": "Approver (who holds no pause authority), evidence required, whether an amendment is needed.",
    "containment_plan": "What is revoked on detected subversion; full-offline conditions.",
    "eval_plan": "Planned evaluations, internal or external.",
    "log_retention": "Per-class retention and coverage; floor of 12 months; declared minimum preserved share; "
                     "review method.",
    "amendments_allowed": "Whether the Intent may be amended.",
    "signer": "Role and organisation; Ed25519 signature in the ledger.",
    "run_scale": "Agents, episodes and concurrency.",
    "period_start": "Start of the period this Closeout covers.",
    "period_end": "End of the period; at most 30 days after the start.",
    "status": "Completed, aborted, paused or rolling.",
    "pause_events": "Criterion, who triggered it, action taken, restart approval and evidence.",
    "containment_exceptions": "Deviations from the declared topology, flagged if the surface was undeclared.",
    "evals_planned_vs_run": "Evaluations planned against those run.",
    "logs_retention_confirmed": "Retention as declared is in place.",
    "scope_requested_vs_granted": "Per investigator; every narrowing needs a logged refusal with grounds.",
    "residual_risk": "Free-text residual risk.",
    "cleared_for_system_integration": "Whether the output may be integrated.",
    "config_changes": "Mid-run configuration changes, with time and reason.",
    "surface_resets": "Resets of shared surfaces; a reset without a snapshot during an open incident is a conduct "
                      "finding.",
    "notice_id": "Identifier cited by the Closeout.",
    "detected_at": "When the developer detected the exception; the 72-hour clock starts here.",
    "kinds": "Reportable event kinds.",
    "criterion_ids": "Declared criteria the event matches.",
    "summary": "What happened.",
    "affected_parties": "External parties affected.",
    "action_taken": "Pause, review, halt or none.",
    "system_id": "Deployed system identifier.",
    "base_run_ids": "Runs whose outputs the system uses.",
    "deployment_context": "Internal research, internal production or external.",
    "tools_and_scaffolding": "Tools and scaffolding available to the system.",
    "inference_scaling": "Inference-time scaling budget.",
    "inter_agent_comms_permitted": "Whether instances can read each other's output.",
    "user_exposure": "Who interacts with the system.",
    "oversight_mode": "Human oversight in operation.",
    "recurring_eval_cadence": "How often the system is re-evaluated.",
}


def esc(s: str) -> str:
    return s.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")


def tt(name: str) -> str:
    return r"\texttt{" + esc(name).replace(r"\_", r"\_\allowbreak{}") + "}"


def tier_letter(prop: dict) -> str:
    return {"restricted": "R", "sealed": "S"}.get(prop.get("x-tier", "public"), "P")


def note(name: str, prop: dict) -> str:
    d = (prop.get("description") or "").strip()
    if d:
        d = d.split(". ")[0].rstrip(".") + "."
    return esc(d or NOTES.get(name, ""))


def main() -> int:
    lines = ["% Generated by paper_tools/schema_tables.py from code/dbyr. Do not edit by hand."]
    consts = {
        "dbyrNoticeHours": adequacy.NOTICE_HOURS, "dbyrNotifyHours": adequacy.NOTIFY_HOURS,
        "dbyrMaxEvalDays": adequacy.MAX_EVAL_DAYS, "dbyrIntakeDays": adequacy.INTAKE_DAYS,
        "dbyrRetentionFloorMonths": adequacy.RETENTION_FLOOR_MONTHS,
        "dbyrCloseoutDays": adequacy.CLOSEOUT_EVERY_DAYS,
        "dbyrMinSamplePct": f"{adequacy.MIN_SAMPLE * 100:g}",
        "dbyrSafeguardsN": len(adequacy.SAFEGUARDS),
        "dbyrSafeguardsList": ", ".join(s.replace("_", " ") for s in adequacy.SAFEGUARDS),
        "dbyrReportableN": len(adequacy.REPORTABLE),
    }
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in consts.items()]

    for key, fname in RECORDS:
        s = json.loads((SCHEMA / fname).read_text(encoding="utf-8"))
        req = set(s.get("required", [])) | ADEQ_ALWAYS.get(key, set())
        props = s["properties"]
        fig = [(n, p) for n, p in props.items() if n in req and n not in META]
        lines.append(f"\\newcommand{{\\fig{key}N}}{{{len(fig)}}}")
        lines.append(f"\\newcommand{{\\fig{key}List}}{{" +
                     ", ".join(f"{tier_letter(p)}/{esc(n)}" for n, p in fig) + "}")
        rows = []
        for n, p in props.items():
            if n in ("schema_version", "record_type"):
                continue
            if n in s.get("required", []):
                need = "schema"
            elif n in ADEQ_ALWAYS.get(key, set()):
                need = "adequacy"
            elif (key, n) in ADEQ_WHEN:
                need = "if " + ADEQ_WHEN[(key, n)]
            else:
                need = "optional"
            route = "/".join(p.get("x-route", [])) or "--"
            tier = p.get("x-tier", "nested" if n == "roles" else "public")
            rows.append(f"{tt(n)} & {route} & {tier} & {esc(need)} & {note(n, p)} \\\\ \\addlinespace")
        lines.append(f"\\newcommand{{\\app{key}Rows}}{{%\n" + "\n".join(rows) + "\n}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
