# Case template

A case is a folder holding the DBYR filings for one incident or set of runs, plus the decision points
it is scored on. This folder is a complete, working case: a synthetic safeguards-off cyber evaluation
at a fictional "Lab X" that passes every check. Copy it, run it once unchanged, then replace its
contents step by step.

Commands run from `benchmarks/`, after `pip install -e .` at the repository root.

```
_template/
  intent_A.json          TrainingRunIntent, filed before the run
  notice_N1.json         ExceptionNotice, filed within 72 hours of an event
  closeout_A.json        TrainingRunCloseout, filed at the end (and at least every 30 days)
  sources.json           where every value came from
  decision_points.json   which filings make up the case, and what it is scored on
```

## Steps

1. **Copy the template and run it as is.**

   ```bash
   cp -r backtest/cases/_template backtest/cases/<case-name>
   dbyr run backtest/cases/<case-name>
   python -m backtest.score backtest/cases/<case-name>
   ```

   Both should succeed, and the scorer writes `results.json` and `results.md` into the folder. You now
   know the tooling works before you change anything.

2. **Freeze the schema.** Run `dbyr freeze` and record the hash, before anyone writes filings for the
   case. Every `results.json` carries the hash it was scored with; if the two differ, the result is
   void.

3. **Write the filings.** Replace the three example records with your own: one `intent_*.json` per
   run (an amendment is another Intent with the same `run_id` and an `amends` field), one
   `notice_*.json` per ExceptionNotice, and one `closeout_*.json` per run that ended or re-attested.
   File names are a convention only: a record is any JSON object with a `record_type`, and records
   are paired by `run_id`. Every field, its disclosure tier and when it is required is in
   [`dbyr/schema/`](../../../../dbyr/schema/). When reconstructing a real incident, use public sources
   only, keep snapshots of them in `sources/`, and record the provenance of every value in
   `sources.json` as first-party, forced-choice or placeholder.

4. **Check the filings.**

   ```bash
   dbyr run backtest/cases/<case-name>
   ```

   Errors with the code `schema` mean a filing is not well formed: fix them, because the scorer
   refuses such filings. Any other error is the protocol rejecting the filing at intake. A
   reconstruction of a real incident can be rejected, and if it is, that rejection is itself a
   result to report, not something to fix. The scorer lists it under `protocol_errors`. `dbyr run` skips
   `decision_points.json`, `sources.json` and `results.json`, and lists them as skipped.

5. **Write `decision_points.json`.**
   - `records` maps a key to each filing file, and `closes` maps each Closeout key to its Intent key.
   - `variants` lists the filer variants to score: `diligent` (declares what was actually true) and
     `as_believed` (declares what the filer plausibly believed). Their operations, which edit a copy of
     the Intent, are `remove_surfaces`, `remove_paths` and `path_writable`.
   - Each decision point names the decision taken, the field that should have captured it, whether
     the developer was aware at the time (`yes`, `no` or `unclear`, with a source), and three tests:
     - `recorded_before`: a predicate on a filing made before the event. Use `pointer` with `equals`
       or `exists`, `any` with `where`, or `all`.
     - `checkable_after`: a predicate on the Closeout, plus the `evidence` classes a later check would
       need retained.
     - `decision_rule`: `pause_criterion` with an `event_kind`, or `record_obligation`.

     Never use a placeholder value in a predicate. To keep the scoring independent, the person who
     writes the decision points should not be the person who wrote the filings.

6. **Score and read the verdict.**

   ```bash
   python -m backtest.score backtest/cases/<case-name>
   ```

   For each variant and decision point, the scorer reports (a) recorded before, (b) checkable after
   and (c) changes the decision. A case fails the protocol if, on fewer than half of its decision
   points, a field satisfies both (a) and (b). Report both variants.

## Reading `dbyr run`

- **error**: the filing is defective. A filing with an error in its own checks is not lodged, and any
  error fails the set (exit code 1).
- **conduct**: the filing lodges, but it records a breach of the filer's own commitments, such as a
  late notice or a matched pause criterion with no pause. It goes to adjudication.
- **warning**: for the reviewer's attention.

`--out DIR` also writes `report.json`, `report.md`, and `views/<filing>/` with the public, restricted
and sealed views plus `openings.json`, the salts that open each commitment. To sign the lodged
filings into a hash-chained record, run `dbyr keygen lab.key`, then
`dbyr run <folder> --ledger record.jsonl --key lab.key`, then `dbyr verify record.jsonl`.

## Negative arm

Safeguards-off runs with no incident use the same tooling: write the Intent, then count how many pause
criteria would have fired on benign events, to measure burden and false triggers.
