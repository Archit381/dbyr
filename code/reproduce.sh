#!/usr/bin/env sh
# Reproduce every number in the paper that comes from code.
set -eu
cd "$(dirname "$0")"

echo "== unit tests"
python3 -m unittest discover -s tests

echo "== frozen-schema hash"
python3 -m dbyr freeze

echo "== tabletop exercise (writes ../generated/tabletop_macros.tex)"
python3 -m tabletop.run --tex-dir ../generated

echo "== worked example on the derivation case (writes ../generated/backtest_macros.tex)"
python3 -m backtest.score backtest/cases/hf-2026 --tex-dir ../generated

echo "== field routes (writes ../generated/routes_macros.tex)"
python3 -m dbyr.routes --tex-dir ../generated

echo "== schema tables for the paper (writes ../generated/schema_fields.tex)"
python3 ../paper_tools/schema_tables.py
