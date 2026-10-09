"""Canonical JSON encoding and hashing.

Every hash in DBYR (ledger entries, commitments, the frozen-schema hash) is taken
over the same canonical form, so two parties holding the same record compute the
same digest.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    """Sorted keys, no insignificant whitespace, UTF-8, no NaN/Infinity."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(value: Any) -> str:
    """Prefixed SHA-256 digest of a JSON value's canonical form."""
    return "sha256:" + sha256_hex(canonical_bytes(value))
