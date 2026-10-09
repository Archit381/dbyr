"""Split scenarios into per-role views for one tabletop round.

    python stage_round.py ROUND SCENARIO_DIR S4 S5 S6

Writes, for each scenario:
  roundN/Sx/filer_inputs/setup.json     header + setup narrative + facts, *without* material flags
  roundN/Sx/filer_inputs/injects.json   header + injects (given to the filer only after its Intent is final)
  roundN/Sx/evaluator_logs.json         retained log entries only, no scenario header (fixes deviation 4)
The judge reads the full scenario file directly.

Prints counts only, so the coordinator can stage a sealed scenario without reading it.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HEADER = ("scenario_id", "title", "run_type", "lab", "start")


def stage(round_dir: Path, scenario: Path) -> dict:
    raw = scenario.read_bytes()
    s = json.loads(raw)
    out = round_dir / s["scenario_id"]
    (out / "filer_inputs").mkdir(parents=True, exist_ok=True)
    head = {k: s[k] for k in HEADER}
    setup = {**head, "setup": {"narrative": s["setup"]["narrative"],
                               "facts": [{"fact_id": f["fact_id"], "statement": f["statement"]}
                                         for f in s["setup"]["facts"]]}}
    (out / "filer_inputs" / "setup.json").write_text(json.dumps(setup, indent=2) + "\n", encoding="utf-8")
    (out / "filer_inputs" / "injects.json").write_text(json.dumps({**head, "injects": s["injects"]}, indent=2) + "\n",
                                                       encoding="utf-8")
    logs = {"retained_logs": [{k: e[k] for k in ("log_id", "kind", "covers", "shows", "gaps")}
                              for e in s["retained_logs"]]}
    (out / "evaluator_logs.json").write_text(json.dumps(logs, indent=2) + "\n", encoding="utf-8")
    return {"scenario": scenario.name, "sha256": hashlib.sha256(raw).hexdigest(), "facts": len(s["setup"]["facts"]),
            "material": sum(bool(f.get("material")) for f in s["setup"]["facts"]),
            "injects": len(s["injects"]), "logs": len(s["retained_logs"])}


def main(argv: list[str]) -> int:
    round_dir, scen_dir, ids = Path(argv[0]), Path(argv[1]), argv[2:]
    for sid in ids:
        print(json.dumps(stage(round_dir, scen_dir / f"{sid}.json")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
