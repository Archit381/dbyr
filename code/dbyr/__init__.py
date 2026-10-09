"""Declare Before You Run (DBYR) v0.1 reference implementation.

This is a reference for the filing format and checks described in the paper,
not a production register. It validates filings, checks cross-run lineage,
projects disclosure tiers, keeps a signed hash-chained record and computes the
frozen-schema hash used for pre-registered validation.
"""

from .freeze import schema_hash
from .lineage import check_lineage, linked_groups
from .redact import all_views, check_opening, project
from .schemas import SCHEMA_VERSION
from .adequacy import check_notices
from .validate import PROFILES, Finding, errors, reconcile, validate_record

__all__ = [
    "SCHEMA_VERSION",
    "Finding",
    "all_views",
    "PROFILES",
    "check_lineage",
    "check_notices",
    "check_opening",
    "errors",
    "linked_groups",
    "project",
    "reconcile",
    "schema_hash",
    "validate_record",
]
