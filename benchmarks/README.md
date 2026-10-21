# DBYR benchmarks

Each benchmark is a consumer of the protocol in
[`dbyr/`](../dbyr/): it builds or reconstructs filing sets, runs the checks on them, and scores the
result. Nothing in `dbyr/` imports from here.

```bash
pip install -e ..                   # from the repository root: pip install -e .
cd benchmarks
python -m backtest.score backtest/cases/hf-2026         # derivation case (worked example)
python -m backtest.score backtest/cases/anthropic-2026  # held-out case
python -m backtest.score backtest/cases/aisi-2026       # held-out case
```

Add `--tex-dir DIR` to write the paper's macros. Each benchmark rewrites its committed `results.json` and `results.md`; a clean rerun changes
nothing.

Every case folder is also a filing set: `dbyr run backtest/cases/<case>` runs the whole protocol over
its records and skips the case's own `decision_points.json`, `sources.json` and `results.json`.

