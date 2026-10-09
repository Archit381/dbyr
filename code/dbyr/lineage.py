"""Cross-run checks over a set of filings.

Per-run filings fragment oversight in the same way per-agent monitors do
(Makins et al., 2026). These checks link runs that reach the same persistent,
shared surface, so reconciliation is done over the linked group rather than run
by run. Surface identity is by surface_id, which a developer must keep stable
across runs for the same physical surface.
"""

from __future__ import annotations

from datetime import datetime

from .validate import Finding


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _shared_persistent(surface: dict) -> bool:
    return surface["persistence"] in ("cross_run", "permanent") and surface["tenancy"] != "run_only"


def _surfaces(intent: dict) -> dict[str, dict]:
    return {s["surface_id"]: s for s in intent["egress_topology"]["writable_surfaces"]}


def check_lineage(intents: list[dict], closeouts: list[dict], profile: str = "adequacy") -> list[Finding]:
    out: list[Finding] = []
    ordered = sorted(intents, key=lambda i: _ts(i["filed_at"]))

    for idx, later in enumerate(ordered):
        later_surfaces = _surfaces(later)
        cited = {(l["surface_id"], l["run_id"]) for l in later["egress_topology"]["shared_surface_lineage"]}
        inherited = {(x["run_id"], x["exception_id"]) for x in later["egress_topology"].get("inherited_exceptions", [])}

        for earlier in ordered[:idx]:
            for sid, s in _surfaces(earlier).items():
                if sid in later_surfaces and _shared_persistent(s) and _shared_persistent(later_surfaces[sid]):
                    if (sid, earlier["run_id"]) not in cited:
                        out.append(Finding(
                            "error", "lineage_not_cited", f"{later['run_id']}/egress_topology/shared_surface_lineage",
                            f"run {earlier['run_id']!r} reaches persistent shared surface {sid!r} but is not cited"))

        # Exceptions on a surface this run reaches that were on record, and still open, when it filed.
        # Only closeouts already filed count: a run cannot cite what nobody had recorded yet.
        for c in closeouts:
            if c["run_id"] == later["run_id"] or _ts(c["filed_at"]) > _ts(later["filed_at"]):
                continue
            for x in c["containment_exceptions"]:
                still_open = x["status"] == "open" or _ts(x.get("closed_at", x["opened_at"])) > _ts(later["filed_at"])
                if (x["surface_id"] in later_surfaces
                        and _ts(x["opened_at"]) <= _ts(later["filed_at"])
                        and still_open
                        and (c["run_id"], x["exception_id"]) not in inherited):
                    out.append(Finding(
                        "error", "inherited_exception_not_cited", f"{later['run_id']}/egress_topology/inherited_exceptions",
                        f"exception {x['exception_id']!r} on {x['surface_id']!r} (run {c['run_id']!r}) "
                        "was open when this run filed and is not cited"))
    if profile == "adequacy":
        from .adequacy import tenancy_conflicts
        out += tenancy_conflicts(intents)
    return out


def linked_groups(intents: list[dict]) -> list[set[str]]:
    """Runs connected through persistent shared surfaces. Each group is one reconciliation unit."""
    parent: dict[str, str] = {i["run_id"]: i["run_id"] for i in intents}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_surface: dict[str, list[str]] = {}
    for i in intents:
        for sid, s in _surfaces(i).items():
            if _shared_persistent(s):
                by_surface.setdefault(sid, []).append(i["run_id"])
    for runs in by_surface.values():
        for r in runs[1:]:
            parent[find(r)] = find(runs[0])

    groups: dict[str, set[str]] = {}
    for run in parent:
        groups.setdefault(find(run), set()).add(run)
    return sorted(groups.values(), key=lambda g: sorted(g))
