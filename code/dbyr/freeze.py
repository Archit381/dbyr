"""Frozen-schema hash for pre-registration.

The held-out validation (paper Section 5.5) requires the schema to be fixed
before scoring. This module hashes every schema file in canonical form, so
reformatting a file does not change the hash but any change to its content does.
Publish the hash before scoring; recompute it at scoring time; they must match.
"""

from __future__ import annotations

import json

from .canonical import digest
from .schemas import SCHEMA_VERSION, schema_files


def schema_bundle() -> dict:
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in schema_files()}


def schema_hash() -> str:
    return digest({"schema_version": SCHEMA_VERSION, "files": schema_bundle()})
