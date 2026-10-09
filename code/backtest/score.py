"""Score DBYR v0.1 against a case's decision points.

    python -m backtest.score backtest/cases/hf-2026 [--tex-dir ../generated]

For each decision point and each filer variant it reports three things:

  (a) recorded before   Did a field in a filing made before the event capture
                        the material fact? Checked mechanically against the
                        reconstructed filing.
  (b) checkable after   Does the Closeout record the event, and was the evidence
                        a V1 reconciliation needs declared retained? "Partial"
                        when the Closeout itself reports retention below the
                        Intent's floor for behavioural evidence.
  (c) changes decision  Would the filing have required a different action than
                        the one taken? Derived from the developer's awareness at
                        the time and from the declared criteria, never assumed.

(a) and (b) measure attributability; only (c) bears on prevention. On a
derivation case (the schema was written from it), (a) and (b) are traceability
and cannot fail by construction; the same code is meant to be run on a held-out
case with a frozen schema and an independent scorer.

The held-out failure criterion from the paper is applied: a case fails if, on
fewer than half of its decision points, a field satisfies both (a) and (b).
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dbyr import check_lineage, check_notices, errors, reconcile, schema_hash, validate_record  # noqa: E402

BEHAVIOURAL = {"trajectories", "inter_agent_messages", "chain_of_thought", "tool_calls"}


# ------------------------------------------------------------------ predicates

def _get(doc: dict, pointer: str):
    node = doc
    for part in [p for p in pointer.split("/") if p]:
        if isinstance(node, list):
            node = node[int(part)]
        elif isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _matches(item: dict, where: dict) -> bool:
    for key, want in where.items():
        have = item.get(key)
        if isinstance(want, dict):
            if "contains" in want and not (isinstance(have, list) and want["contains"] in have):
                return False
            if want.get("nonempty") and not have:
                return False
        elif isinstance(want, list):
            if have not in want:
                return False
        elif have != want:
            return False
    return True


def holds(pred: dict, records: dict) -> bool:
    if "all" in pred:
        return all(holds(p, records) for p in pred["all"])
    doc = records[pred["record"]]
    if "any" in pred:
        items = _get(doc, pred["any"]) or []
        return any(_matches(i, pred.get("where", {})) for i in items)
    value = _get(doc, pred["pointer"])
    if "equals" in pred:
        return value == pred["equals"]
    if pred.get("exists"):
        return value is not None
    raise ValueError(f"unrecognised predicate {pred}")


# ------------------------------------------------------------------ variants

def apply_variant(records: dict, variant: dict) -> dict:
    out = copy.deepcopy(records)
    for key, surfaces in variant.get("remove_surfaces", {}).items():
        topo = out[key]["egress_topology"]
        topo["writable_surfaces"] = [s for s in topo["writable_surfaces"] if s["surface_id"] not in surfaces]
        topo["shared_surface_lineage"] = [l for l in topo["shared_surface_lineage"] if l["surface_id"] not in surfaces]
        # A filer who does not know a surface is shared also does not know agents can communicate
        # through it (v0.3 defines the flag as a fact about the environment, as the filer believes it).
        if not any(s.get("isolation") == "shared" or s["tenancy"] != "run_only" for s in topo["writable_surfaces"]):
            topo["inter_agent_comms_permitted"] = False
    for key, paths in variant.get("path_writable", {}).items():
        for p in out[key]["egress_topology"]["permitted_paths"]:
            if p["path_id"] in paths:
                p["agent_writable"] = paths[p["path_id"]]
    for key, rec in out.items():
        if rec["record_type"] != "TrainingRunCloseout":
            continue
        intent = next((r for k, r in out.items() if r["record_type"] == "TrainingRunIntent" and r["run_id"] == rec["run_id"]), None)
        if intent:
            declared = {s["surface_id"] for s in intent["egress_topology"]["writable_surfaces"]}
            for x in rec["containment_exceptions"]:
                x["declared_surface"] = x["surface_id"] in declared
    return out


# ------------------------------------------------------------------ scoring

def score_checkable(dp: dict, records: dict, closes: dict) -> str:
    pred = dp["checkable_after"]
    if not holds(pred, records):
        return "No"
    record_key = pred["record"] if "record" in pred else pred["all"][0]["record"]
    closeout = records[record_key]
    intent = records[closes[record_key]]
    retained = set(intent["log_retention"]["retained"])
    evidence = set(pred.get("evidence", []))
    if not evidence <= retained:
        return "No"
    floor = intent["log_retention"].get("minimum_preserved_pct")
    if floor is not None and closeout["logs_preserved_pct"] < floor and evidence & BEHAVIOURAL:
        return "Partial"
    return "Yes"


def score_decision(dp: dict, records: dict, closes: dict) -> tuple[str, str]:
    rule = dp["decision_rule"]
    if rule["rule"] == "record_obligation":
        return "Unknown", "obligation is to record, not to act"
    closeout_key = next(iter(closes))
    intent = records[closes[closeout_key]]
    closeout = records[closeout_key]
    criteria = [c for c in intent["pause_criteria"] if rule["event_kind"] in c["matches"]]
    if not criteria:
        return "No", "no declared criterion matches"
    aware = dp["developer_aware"]
    if aware == "no":
        return "No", "criterion cannot fire on an unseen event"
    if aware == "unclear":
        return "Unknown", "awareness at the time not established"
    kinds = {e["event_id"]: e["kind"] for e in closeout["security_events"]}
    ids = {c["criterion_id"]: c for c in criteria}
    for p in closeout["pause_events"]:
        cited_kind = any(kinds.get(e) == rule["event_kind"] for e in p.get("triggering_event_ids", []))
        if (p["criterion_id"] in ids or cited_kind) and p["action_taken"] == ids.get(p["criterion_id"], criteria[0])["required_action"]:
            return "No", "compliant: required action was taken and restart approved"
    return "Yes", "declared criterion required an action that was not taken"


def score_case(case_dir: Path) -> dict:
    spec = json.loads((case_dir / "decision_points.json").read_text(encoding="utf-8"))
    base = {k: json.loads((case_dir / f).read_text(encoding="utf-8")) for k, f in spec["records"].items()}
    closes = spec["closes"]

    # The reconstructed filings must pass the v0.1 rule set (baseline profile), or the backtest
    # scores a broken filing. The v0.2 intake review is reported separately below: on this case
    # it is expected to reject the reconstruction, and that rejection is itself a result.
    integrity = {}
    for k, rec in base.items():
        integrity[k] = [str(f) for f in errors(validate_record(rec, profile="baseline"))]
    notices = [r for r in base.values() if r["record_type"] == "ExceptionNotice"]
    for ck, ik in closes.items():
        integrity[f"{ck} vs {ik}"] = [str(f) for f in errors(reconcile(base[ik], base[ck], profile="baseline"))]
        integrity[f"{ck} notices"] = [str(f) for f in errors(check_notices(base[ik], base[ck], notices))]
    intents = [r for r in base.values() if r["record_type"] == "TrainingRunIntent"]
    closeouts = [r for r in base.values() if r["record_type"] == "TrainingRunCloseout"]
    integrity["lineage"] = [str(f) for f in errors(check_lineage(intents, closeouts, profile="baseline"))]

    variants = {}
    for name, variant in spec["variants"].items():
        recs = apply_variant(base, variant)
        rows = []
        for dp in spec["decision_points"]:
            c, reason = score_decision(dp, recs, closes)
            rows.append({
                "id": dp["id"],
                "recorded_before": "Yes" if holds(dp["recorded_before"], recs) else "No",
                "checkable_after": score_checkable(dp, recs, closes),
                "changes_decision": c,
                "reason": reason,
            })
        n = len(rows)
        both = sum(r["recorded_before"] == "Yes" and r["checkable_after"] != "No" for r in rows)
        variants[name] = {
            "rows": rows,
            "recorded_before": sum(r["recorded_before"] == "Yes" for r in rows),
            "checkable_after": sum(r["checkable_after"] != "No" for r in rows),
            "checkable_partial": sum(r["checkable_after"] == "Partial" for r in rows),
            "changes_decision_yes": sum(r["changes_decision"] == "Yes" for r in rows),
            "changes_decision_unknown": sum(r["changes_decision"] == "Unknown" for r in rows),
            "attributable": both,
            "n": n,
            "passes_heldout_criterion": both >= math.ceil(n / 2),
            "intake_errors": {k: sorted({f.code for f in errors(validate_record(r, profile="adequacy"))})
                              for k, r in recs.items() if r["record_type"] == "TrainingRunIntent"},
        }
    return {
        "case": spec["case"],
        "is_derivation_case": spec["is_derivation_case"],
        "schema_hash": schema_hash(),
        "filings_compliant": all(not v for v in integrity.values()),
        "integrity": integrity,
        "decision_points": spec["decision_points"],
        "variants": variants,
    }


# ------------------------------------------------------------------ output

def _tex(s: str) -> str:
    return (s.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%")
             .replace("_", r"\_").replace("#", r"\#"))


def _breakable(name: str) -> str:
    """Field names are long monospace tokens; allow breaks after underscores and dots."""
    return _tex(name).replace(r"\_", r"\_\allowbreak{}").replace(".", r".\allowbreak{}")


def latex_rows(result: dict) -> str:
    dil = {r["id"]: r for r in result["variants"]["diligent"]["rows"]}
    bel = {r["id"]: r for r in result["variants"]["as_believed"]["rows"]}
    lines = []
    for dp in result["decision_points"]:
        d, b = dil[dp["id"]], bel[dp["id"]]
        fields = ", ".join(r"\fld{" + _breakable(f.strip()) + "}" for f in dp["field"].split(","))
        lines.append(
            f"{_tex(dp['date'])} & {_tex(dp['decision'])} & {fields} & "
            f"{d['recorded_before']} / {b['recorded_before']} & {d['checkable_after']} & "
            f"{d['changes_decision']} \\\\ \\addlinespace")
    v, w = result["variants"]["diligent"], result["variants"]["as_believed"]
    lines.append(r"\midrule")
    lines.append(
        rf"\multicolumn{{3}}{{l}}{{\textbf{{Total of {v['n']}}}}} & "
        rf"{v['recorded_before']} / {w['recorded_before']} & {v['checkable_after']} "
        rf"({v['checkable_partial']} partial) & {v['changes_decision_yes']} yes, {v['changes_decision_unknown']} unknown \\")
    return "\n".join(lines) + "\n"


def latex_macros(result: dict) -> str:
    v, w = result["variants"]["diligent"], result["variants"]["as_believed"]
    h = result["schema_hash"].split(":", 1)[1]
    m = {
        "btN": v["n"],
        "btRecordedDiligent": v["recorded_before"],
        "btRecordedBelieved": w["recorded_before"],
        "btCheckable": v["checkable_after"],
        "btPartial": v["checkable_partial"],
        "btChangesYes": v["changes_decision_yes"],
        "btChangesUnknown": v["changes_decision_unknown"],
        "btAttributableDiligent": v["attributable"],
        "btAttributableBelieved": w["attributable"],
        "btIntakeDiligent": ", ".join(r"\texttt{" + c.replace("_", r"\_") + "}" for c in v["intake_errors"]["intent:A"]),
        "btIntakeBelieved": ", ".join(r"\texttt{" + c.replace("_", r"\_") + "}" for c in w["intake_errors"]["intent:A"]),
        "dbyrSchemaHashShort": h[:16],
        "dbyrSchemaHash": h,
    }
    head = "% Generated by code/backtest/score.py. Do not edit by hand.\n"
    # Table rows are a macro, not a file to \\input: \\input inside tabularx breaks the rules after it.
    rows = "\\newcommand{\\btRows}{%\n" + latex_rows(result) + "}\n"
    return head + "".join(f"\\newcommand{{\\{k}}}{{{val}}}\n" for k, val in m.items()) + rows


def markdown(result: dict) -> str:
    out = [f"# Backtest: {result['case']}", ""]
    if result["is_derivation_case"]:
        out += ["**Derivation case.** (a) and (b) are traceability, not validation.", ""]
    out += [f"Schema hash: `{result['schema_hash']}`",
            f"Reconstructed filings compliant: {result['filings_compliant']}", ""]
    for name, v in result["variants"].items():
        out += [f"## Filer variant: {name}", "",
                "| DP | (a) recorded before | (b) checkable after | (c) changes decision | why |",
                "|---|---|---|---|---|"]
        out += [f"| {r['id']} | {r['recorded_before']} | {r['checkable_after']} | {r['changes_decision']} | {r['reason']} |"
                for r in v["rows"]]
        out += ["", "v0.2 intake review of the reconstructed Intents: " +
                "; ".join(f"{k}: {', '.join(c) or 'accepted'}" for k, c in v["intake_errors"].items())]
        verdict = "passes" if v["passes_heldout_criterion"] else "FAILS"
        out += ["", f"Attributable on {v['attributable']} of {v['n']}; {verdict} the held-out criterion "
                    f"(needs {math.ceil(v['n'] / 2)}).", ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case_dir", type=Path)
    ap.add_argument("--tex-dir", type=Path, help="write backtest_macros.tex (numbers and table rows) here")
    args = ap.parse_args(argv)

    result = score_case(args.case_dir)
    (args.case_dir / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    report = markdown(result)
    (args.case_dir / "results.md").write_text(report, encoding="utf-8")
    print(report)
    if not result["filings_compliant"]:
        print("Reconstructed filings are not compliant:", json.dumps(result["integrity"], indent=2))
        return 1
    if args.tex_dir:
        args.tex_dir.mkdir(parents=True, exist_ok=True)
        (args.tex_dir / "backtest_macros.tex").write_text(latex_macros(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
