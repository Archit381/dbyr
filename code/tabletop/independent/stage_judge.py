"""Rebuild the round-2 judge workspace from the repository, and fill the judge prompt.

    python code/tabletop/independent/stage_judge.py WORK_DIR

Run from the repository root (the folder holding .git). Creates, for S4-S6:

  WORK/<S>/filer/      setup.json, injects.json, filings/, private_log.md,
                       intake_requests.md, intake_response.md, kit/ (code at tag v0.3)
  WORK/<S>/evaluator/  review_intake.md, review_reconciliation.md, intake/, later/
  WORK/judge/          empty output folder
  WORK/judge_prompt.md the verbatim round-2 judge prompt with paths filled in

This is the same layout the role agents worked in (deviation 7). The kit is
exported from the frozen v0.3 tag, not from the working tree, and its schema
hash is checked against FREEZE.txt before anything is written.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROUND = Path("code/tabletop/independent/round2")
IND = Path("code/tabletop/independent")
SCENARIOS = ("S4", "S5", "S6")
V03_HASH = "sha256:dcd157d4878c905c5d4690ddcc36cf884950b8a98b823223e9b8d7e38e9cd997"


def export_kit(dest: Path) -> None:
    """Write code/ at tag v0.3 into dest (dest/dbyr, dest/tabletop, ...)."""
    tar = subprocess.run(["git", "archive", "--format=tar", "v0.3", "code"], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        for m in t.getmembers():
            if not m.name.startswith("code/") or m.name == "code/":
                continue
            m.name = m.name[len("code/"):]
            t.extract(m, dest, filter="data")


def main(argv: list[str]) -> int:
    if not Path(".git").exists():
        sys.exit("run from the repository root")
    work = Path(argv[0]).resolve()
    if work.exists() and any(work.iterdir()):
        sys.exit(f"{work} is not empty; choose a new folder")
    for s in SCENARIOS:
        src, f, e = ROUND / s, work / s / "filer", work / s / "evaluator"
        f.mkdir(parents=True)
        e.mkdir(parents=True)
        shutil.copy(src / "filer_inputs/setup.json", f / "setup.json")
        shutil.copy(src / "filer_inputs/injects.json", f / "injects.json")
        shutil.copytree(src / "filings", f / "filings")
        shutil.copy(src / "filer_private_log.md", f / "private_log.md")
        shutil.copy(src / "evaluator_review_intake.md", f / "intake_requests.md")  # what the filer was sent
        shutil.copy(src / "filer_intake_response.md", f / "intake_response.md")
        export_kit(f / "kit")
        shutil.copy(src / "evaluator_review_intake.md", e / "review_intake.md")
        shutil.copy(src / "evaluator_review_reconciliation.md", e / "review_reconciliation.md")
        shutil.copytree(src / "evaluator_view/intake", e / "intake")
        shutil.copytree(src / "evaluator_view/later", e / "later")
        got = subprocess.run([sys.executable, "-m", "dbyr", "freeze"], cwd=f / "kit", check=True,
                             capture_output=True, text=True).stdout.strip()
        if got != V03_HASH:
            sys.exit(f"{s}: kit hash {got} does not match frozen v0.3 {V03_HASH}")
    (work / "judge").mkdir()

    root = Path.cwd().resolve()
    prompt = (ROUND / "prompts/judge.md").read_text(encoding="utf-8").split("\n", 2)[2]
    fill = {"{PROTOCOL}": str(root / IND / "PROTOCOL.md"), "{DEVIATIONS}": str(root / IND / "DEVIATIONS.md"),
            "{SCENARIOS}": "S4, S5 and S6", "{SCEN_DIR}": str(root / IND / "scenarios/sealed"),
            "{WORK}": str(work), "{OUT}": str(work / "judge")}
    for k, v in fill.items():
        prompt = prompt.replace(k, v)
    (work / "judge_prompt.md").write_text(prompt, encoding="utf-8")
    print(f"staged {', '.join(SCENARIOS)} in {work}; kit hash verified; prompt at {work / 'judge_prompt.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
