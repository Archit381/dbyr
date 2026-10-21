"""A backtest case: the filings for one incident, and the decision points they are scored on.

A case is a decision_points.json file, given directly or as the folder that holds it. Next to it:

  sources.json           optional. Provenance of every value: first-party, forced-choice, placeholder.
  annotations.json       optional. Information added after scoring for secondary analysis (decision
                         kinds, public disclosure dates, the investigation window, escape-reason and
                         provenance overrides). Never read by the pre-registered scoring.

The filings themselves can be found in one of two ways:

  "filings": PATH        a filing set anywhere on disk, exactly what `dbyr run` accepts: a folder or
                         a manifest.json, relative to decision_points.json. Record keys are the
                         filing set's keys (from its manifest, else the file names).
  "records": {KEY: FILE} the filings listed one by one, relative to decision_points.json.

decision_points.json is pre-registered: never edited after scoring. Nothing in a case is
incident-specific code: any case in this shape can be scored.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

from ..filingset import FilingSetError, load_filing_set
from .fingerprint import Fingerprint

TEMPLATE = Path(__file__).resolve().parent / "template"   # a complete synthetic case, shipped with the package
SPEC = "decision_points.json"
SOURCES = "sources.json"
ANNOTATIONS = "annotations.json"

AWARENESS = ("yes", "no", "unclear")
RULES = ("pause_criterion", "record_obligation")
DECISION_KINDS = ("setup", "respond", "tell", "investigate")
VARIANT_OPS = ("description", "remove_surfaces", "remove_paths", "path_writable")


class CaseError(ValueError):
    """The case folder is missing a file or does not have the expected shape."""


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CaseError(f"{path}: no such file") from None
    except json.JSONDecodeError as exc:
        raise CaseError(f"{path}: not valid JSON ({exc})") from None


def _check_spec(spec: dict, where: Path) -> None:
    problems = []
    for key in ("case", "closes", "variants", "decision_points"):
        if key not in spec:
            problems.append(f"missing {key!r}")
    if ("records" in spec) == ("filings" in spec):
        problems.append("give exactly one of 'filings' (a filing set) or 'records' (key -> file)")
    if problems:
        raise CaseError(f"{where}: " + "; ".join(problems))
    if not spec["variants"]:
        problems.append("no filer variants")
    for name, v in spec["variants"].items():
        unknown = set(v) - set(VARIANT_OPS)
        if unknown:
            problems.append(f"variant {name!r} has unknown operations {sorted(unknown)}")
    seen = set()
    for i, dp in enumerate(spec["decision_points"]):
        label = dp.get("id", f"#{i}")
        for key in ("id", "decision", "developer_aware", "recorded_before", "checkable_after", "decision_rule"):
            if key not in dp:
                problems.append(f"decision point {label}: missing {key!r}")
        if dp.get("id") in seen:
            problems.append(f"decision point {label}: duplicate id")
        seen.add(dp.get("id"))
        if dp.get("developer_aware") not in AWARENESS:
            problems.append(f"decision point {label}: developer_aware must be one of {AWARENESS}")
        rule = dp.get("decision_rule", {})
        if rule.get("rule") not in RULES:
            problems.append(f"decision point {label}: decision_rule.rule must be one of {RULES}")
        if rule.get("rule") == "pause_criterion" and "event_kind" not in rule:
            problems.append(f"decision point {label}: a pause_criterion rule needs an event_kind")
    if not spec["decision_points"]:
        problems.append("no decision points")
    if problems:
        raise CaseError(f"{where}: " + "; ".join(problems))


def _check_keys(spec: dict, records: dict, where: Path) -> None:
    """Every record key the case uses must exist in the filings."""
    problems = []
    known = set(records)
    for ck, ik in spec["closes"].items():
        for key in (ck, ik):
            if key not in known:
                problems.append(f"closes names {key!r}, which is not among the filings {sorted(known)}")
    for name, v in spec["variants"].items():
        for op in ("remove_surfaces", "remove_paths", "path_writable"):
            for key in v.get(op, {}):
                if key not in known:
                    problems.append(f"variant {name!r} edits {key!r}, which is not among the filings")
    for dp in spec["decision_points"]:
        rule = dp["decision_rule"]
        if rule.get("closeout") and rule["closeout"] not in spec["closes"]:
            problems.append(f"decision point {dp['id']}: decision_rule.closeout {rule['closeout']!r} is not in 'closes'")
    if problems:
        raise CaseError(f"{where}: " + "; ".join(problems))


def _check_annotations(ann: dict, ids: set[str], where: Path) -> None:
    problems = []
    for dp, kind in ann.get("decision_kinds", {}).items():
        if dp not in ids:
            problems.append(f"decision_kinds names unknown decision point {dp!r}")
        if kind not in DECISION_KINDS:
            problems.append(f"decision_kinds[{dp!r}] must be one of {DECISION_KINDS}")
    for key in ("escape_reasons", "provenance"):
        for dp in ann.get(key, {}):
            if dp not in ids:
                problems.append(f"{key} names unknown decision point {dp!r}")
    for i, item in enumerate(ann.get("first_outside_account", [])):
        if not {"date", "what"} <= set(item):
            problems.append(f"first_outside_account[{i}] needs 'date' and 'what'")
    inv = ann.get("investigation")
    if inv is not None:
        for key in ("incident_window", "review_window"):
            w = inv.get(key)
            if not (isinstance(w, list) and len(w) == 2):
                problems.append(f"investigation.{key} must be [start, end]")
    if problems:
        raise CaseError(f"{where}: " + "; ".join(problems))


def apply_variant(records: dict, variant: dict) -> dict:
    """A copy of the records as a given filer would have filed them. Logic unchanged from the
    pre-registered scorer."""
    out = copy.deepcopy(records)
    for key, surfaces in variant.get("remove_surfaces", {}).items():
        topo = out[key]["egress_topology"]
        topo["writable_surfaces"] = [s for s in topo["writable_surfaces"] if s["surface_id"] not in surfaces]
        topo["shared_surface_lineage"] = [l for l in topo["shared_surface_lineage"] if l["surface_id"] not in surfaces]
        # A filer who does not know a surface is shared also does not know agents can communicate
        # through it (the flag is a fact about the environment, as the filer believes it).
        if not any(s.get("isolation") == "shared" or s["tenancy"] != "run_only" for s in topo["writable_surfaces"]):
            topo["inter_agent_comms_permitted"] = False
    # A filer who believes a path does not exist does not declare it at all.
    for key, paths in variant.get("remove_paths", {}).items():
        topo = out[key]["egress_topology"]
        topo["permitted_paths"] = [p for p in topo["permitted_paths"] if p["path_id"] not in paths]
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


def _locate(path: Path) -> tuple[Path, Path]:
    """(case folder, decision_points.json) for a folder or a decision-points file."""
    if path.is_file():
        return path.parent, path
    if path.is_dir():
        if not (path / SPEC).exists():
            raise CaseError(f"{path}: no {SPEC} in this folder")
        return path, path / SPEC
    raise CaseError(f"{path}: no such file or folder")


@dataclass
class Case:
    path: Path                      # the case folder (holds decision_points.json)
    spec: dict
    records: dict[str, dict]
    files: dict[str, Path] = field(default_factory=dict)   # filing key -> file it was read from
    sources: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)
    fingerprint: Fingerprint | None = None

    @classmethod
    def load(cls, path: str | Path) -> "Case":
        """Load a case from its folder or its decision_points.json. Every input is fingerprinted
        before the filings are read."""
        folder, spec_file = _locate(Path(path))
        spec = _read(spec_file)
        if not isinstance(spec, dict):
            raise CaseError(f"{spec_file}: must be a JSON object")
        _check_spec(spec, spec_file)

        if "filings" in spec:
            target = (folder / spec["filings"]).resolve()
            fingerprint = Fingerprint.take(folder, target if target.is_dir() else target.parent)
            try:
                fs = load_filing_set(target)
            except FilingSetError as exc:
                raise CaseError(f"{spec_file}: 'filings' could not be loaded: {exc}") from None
            records, files = fs.records, fs.files
        else:
            fingerprint = Fingerprint.take(folder)
            files = {key: folder / name for key, name in spec["records"].items()}
            records = {key: _read(f) for key, f in files.items()}
        for key, rec in records.items():
            if not isinstance(rec, dict) or "record_type" not in rec:
                raise CaseError(f"{files[key]}: not a DBYR record (no record_type)")
        _check_keys(spec, records, spec_file)

        sources = _read(folder / SOURCES) if (folder / SOURCES).exists() else {}
        annotations = _read(folder / ANNOTATIONS) if (folder / ANNOTATIONS).exists() else {}
        _check_annotations(annotations, {dp["id"] for dp in spec["decision_points"]}, folder / ANNOTATIONS)
        return cls(folder, spec, records, files, sources, annotations, fingerprint)

    @property
    def name(self) -> str:
        return self.spec["case"]

    @property
    def title(self) -> str:
        return self.spec.get("title", self.name)

    @property
    def label(self) -> str:
        """Short column heading for tables: annotations.label, else the case name."""
        return self.annotations.get("label", self.name)

    @property
    def is_derivation_case(self) -> bool:
        return bool(self.spec.get("is_derivation_case", False))

    @property
    def closes(self) -> dict[str, str]:
        return self.spec["closes"]

    @property
    def decision_points(self) -> list[dict]:
        return self.spec["decision_points"]

    @property
    def variants(self) -> dict[str, dict]:
        return self.spec["variants"]

    @property
    def primary_variant(self) -> str:
        """The variant tables report: annotations.primary_variant, else as_believed, else the first."""
        chosen = self.annotations.get("primary_variant")
        if chosen:
            if chosen not in self.variants:
                raise CaseError(f"{self.path / ANNOTATIONS}: primary_variant {chosen!r} is not a variant")
            return chosen
        return "as_believed" if "as_believed" in self.variants else next(iter(self.variants))

    def variant_records(self, name: str) -> dict[str, dict]:
        return apply_variant(self.records, self.variants[name])

    def record_file(self, key: str) -> str:
        """The file name a filing was read from (sources.json is keyed by file name)."""
        return self.files[key].name

    def verify_unchanged(self) -> list[str]:
        """Differences between the inputs now and when the case was loaded; empty if none."""
        return self.fingerprint.diff(self.fingerprint.again()) if self.fingerprint else []


def init_case(dest: str | Path, name: str | None = None) -> Path:
    """Write the example case (a synthetic safeguards-off cyber evaluation that passes every check)
    to a new folder, ready to copy from. The case is named after the folder unless `name` is given."""
    import shutil

    dest = Path(dest)
    if dest.exists() and any(dest.iterdir()):
        raise CaseError(f"{dest}: folder exists and is not empty")
    shutil.copytree(TEMPLATE, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "results.*"))
    spec = json.loads((dest / SPEC).read_text(encoding="utf-8"))
    spec["case"] = name or dest.name
    (dest / SPEC).write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest
