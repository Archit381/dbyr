# Backtest case

A case scores the DBYR protocol against one incident or set of runs: for each decision that shaped
the outcome, was its fact written down before the run, and could it be checked afterwards? This
folder is a complete, working case: a synthetic safeguards-off cyber evaluation at a fictional
"Lab X" that passes every check. Run it once unchanged, then replace its contents step by step.

```
<case>/
  decision_points.json   what the case is scored on, and where its filings are
  intent_A.json          TrainingRunIntent, filed before the run
  notice_N1.json         ExceptionNotice, filed within 72 hours of an event
  closeout_A.json        TrainingRunCloseout, filed at the end (and at least every 30 days)
  sources.json           optional: where every value came from
  annotations.json       optional: information added after scoring, for the results tables
```

## Steps

1. **Create the case and run it as is.**

   ```bash
   dbyr backtest init cases/<case-name>      # writes this example
   dbyr backtest check cases/<case-name>     # checks the case; scores nothing
   dbyr backtest score cases/<case-name>     # scores it and prints the tables
   ```

   All three should succeed. You now know the tooling works before you change anything.

2. **Freeze the schema.** Run `dbyr freeze` and record the hash before anyone writes filings for the
   case. Every result carries the hash it was scored with; if the two differ, the result is void.

3. **Write the filings.** One `intent_*.json` per run (an amendment is another Intent with the same
   `run_id` and an `amends` field), one `notice_*.json` per ExceptionNotice, and one
   `closeout_*.json` per run that ended or re-attested. A record is any JSON object with a
   `record_type`; records are paired by `run_id`. Every field, its disclosure tier and when it is
   required is in `dbyr/schema/`. When reconstructing a real incident, use public sources only, keep
   snapshots of them in `sources/`, and record the provenance of every value in `sources.json` as
   first-party, forced-choice or placeholder.

   The filings can live in this folder or anywhere else (see step 5).

4. **Check the filings** with the protocol itself:

   ```bash
   dbyr run cases/<case-name>
   ```

   Errors with the code `schema` mean a filing is not well formed: fix them. Any other error is the
   protocol rejecting the filing at intake. A reconstruction of a real incident can be rejected, and
   if it is, that rejection is a result to report, not something to fix. `dbyr run` lists
   `decision_points.json`, `sources.json` and `annotations.json` as skipped.

5. **Write `decision_points.json`.**
   - Say where the filings are, in one of two ways:
     - `"records": {"intent:A": "intent_A.json", ...}` lists each filing, relative to this file.
     - `"filings": "../../filings/lab-x/"` points at any filing set: a folder or its
       `manifest.json`, exactly what `dbyr run` takes. Record keys are then the filing set's keys:
       its manifest's keys, or the file names if it has no manifest.
   - `closes` maps each Closeout key to its Intent key.
   - `variants` lists the filer variants to score: `diligent` (declares what was actually true) and
     `as_believed` (declares what the filer plausibly believed). Their operations, which edit a copy
     of the Intent, are `remove_surfaces`, `remove_paths` and `path_writable`.
   - Each decision point names the decision taken, the field that should have captured it, whether
     the developer was aware at the time (`yes`, `no` or `unclear`, with a source), and three tests:
     - `recorded_before`: a predicate on a filing made before the event. Use `pointer` with `equals`
       or `exists`, `any` with `where`, or `all`.
     - `checkable_after`: a predicate on the Closeout, plus the `evidence` classes a later check
       would need retained.
     - `decision_rule`: `pause_criterion` with an `event_kind` (and, with several runs, the
       `closeout` it is scored against), or `record_obligation`.

     Never use a placeholder value in a predicate; `dbyr backtest check` warns if one does. To keep
     the scoring independent, the person who writes the decision points should not be the person
     who wrote the filings.

6. **Score and read the verdict.**

   ```bash
   dbyr backtest score cases/<case-name> --out report/ --write-results
   ```

   For each variant and decision point, the scorer reports (a) recorded before, (b) checkable after
   and (c) changes the decision. A case fails the protocol if, on fewer than half of its decision
   points, a field satisfies both (a) and (b). Report both variants. Every input file, including the
   filings wherever they are, is hashed before and after scoring; if anything changed, the run stops.

   `--out` writes `report.md`, `report.html` and `metrics.json`; `--write-results` writes
   `results.json` and `results.md` next to `decision_points.json`.

7. **Optional: annotate for the results tables.** After scoring, `annotations.json` can add what
   the tables need but the scoring never reads. Write it only after the decision points are
   frozen, and record when it was added.

   | Key | What it holds |
   |---|---|
   | `label` | the case's column heading in the tables |
   | `primary_variant` | the filer variant the tables report (default `as_believed`) |
   | `decision_kinds` | per decision point: `setup`, `respond`, `tell` or `investigate` |
   | `first_outside_account` | dated accounts outside the organisation, each with `date`, `what` and `source` |
   | `investigation` | `incident_window` and `review_window`, each `[start, end]` |
   | `today` | per question (`commitments`, `who_knew`, `outside`, `affected`, `investigation`, `checkable`), what the organisation's own accounts show |
   | `escape_reasons`, `provenance` | per-decision overrides of the automatic classification; give the reason in `_notes` |

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
