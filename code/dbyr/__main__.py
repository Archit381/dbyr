"""Command line: python -m dbyr <command> ...

  check [--profile P] PATH...      every check over a set of filings (files or directories)
  validate [--profile P] FILE...   schema + cross-field rules (+ v0.2 adequacy by default)
  reconcile INTENT CLOSEOUT        check a Closeout against its Intent
  lineage FILE...                  cross-run lineage over a set of filings
  project --view TIER FILE         print the public | restricted | sealed view
  keygen KEYFILE                   write a new Ed25519 signing key (PEM)
  append LEDGER KEYFILE FILE...    validate, sign and append filings
  verify LEDGER                    recheck every hash link and signature
  freeze                           print the frozen-schema hash
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, NoEncryption, PrivateFormat, load_pem_private_key)

from . import check_lineage, linked_groups, project, reconcile, schema_hash, validate_record
from .check import check_set, load_set
from .ledger import Ledger


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _counts(findings) -> str:
    n = lambda s: sum(f.severity == s for f in findings)
    return f"{n('error')} errors, {n('conduct')} conduct, {n('warning')} warnings"


def _report(label: str, findings) -> int:
    errs = [f for f in findings if f.severity == "error"]
    status = "FAIL" if errs else "ok"
    print(f"{status:4}  {label}  ({_counts(findings)})")
    for f in findings:
        print(f"      {f}")
    return 1 if errs else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dbyr", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    ck = sub.add_parser("check"); ck.add_argument("--profile", choices=["baseline", "adequacy"], default="adequacy"); ck.add_argument("paths", nargs="+")
    v = sub.add_parser("validate"); v.add_argument("files", nargs="+")
    v.add_argument("--profile", choices=["baseline", "adequacy"], default="adequacy")
    r = sub.add_parser("reconcile"); r.add_argument("intent"); r.add_argument("closeout")
    sub.add_parser("lineage").add_argument("files", nargs="+")
    pr = sub.add_parser("project"); pr.add_argument("--view", required=True, choices=["public", "restricted", "sealed"]); pr.add_argument("file")
    sub.add_parser("keygen").add_argument("keyfile")
    a = sub.add_parser("append"); a.add_argument("ledger"); a.add_argument("keyfile"); a.add_argument("files", nargs="+")
    sub.add_parser("verify").add_argument("ledger")
    sub.add_parser("freeze")
    args = p.parse_args(argv)

    if args.cmd == "check":
        found = check_set(load_set(args.paths), profile=args.profile)
        errs = [f for _, f in found if f.severity == "error"]
        print(f"{'FAIL' if errs else 'ok':4}  {_counts([f for _, f in found])} (profile {args.profile})")
        for where, f in found:
            print(f"      {where}: {f}")
        return 1 if errs else 0
    if args.cmd == "validate":
        return max(_report(f, validate_record(_load(f), profile=args.profile)) for f in args.files)
    if args.cmd == "reconcile":
        return _report(f"{args.closeout} against {args.intent}", reconcile(_load(args.intent), _load(args.closeout)))
    if args.cmd == "lineage":
        records = [_load(f) for f in args.files]
        intents = [r for r in records if r["record_type"] == "TrainingRunIntent"]
        closeouts = [r for r in records if r["record_type"] == "TrainingRunCloseout"]
        print("reconciliation groups:", [sorted(g) for g in linked_groups(intents)])
        return _report("lineage", check_lineage(intents, closeouts))
    if args.cmd == "project":
        view, _ = project(_load(args.file), args.view)
        print(json.dumps(view, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "keygen":
        key = Ed25519PrivateKey.generate()
        Path(args.keyfile).write_bytes(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
        Path(args.keyfile).chmod(0o600)
        print(f"wrote {args.keyfile}")
        return 0
    if args.cmd == "append":
        key = load_pem_private_key(Path(args.keyfile).read_bytes(), password=None)
        ledger = Ledger(Path(args.ledger))
        for f in args.files:
            entry = ledger.append(_load(f), key)
            print(f"seq {entry['seq']}  {entry['record_type']:22} {entry['entry_hash']}")
        return 0
    if args.cmd == "verify":
        return _report(args.ledger, Ledger(Path(args.ledger)).verify())
    if args.cmd == "freeze":
        print(schema_hash())
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
