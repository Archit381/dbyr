# Backtesting DBYR against an incident

This is for researchers testing whether DBYR would have helped in a past incident. A lab using DBYR
does not need any of it: labs file and check records as the [root README](../../README.md) describes.

The backtest asks: **had DBYR existed during this incident, would the questions that mattered afterwards have been answerable from the records?** The records are the answers, written in advance by the lab; the decision points are the questions, written afterwards with hindsight. The score is how many questions the records answer.

- **Decision points are never filed.** They are the list of questions an investigator asks after an incident: which decisions shaped it, and what record should have captured each. They exist only to measure the protocol.
- **The lab never writes them.** For a past incident, researchers write them from the public account of the incident, and someone other than the person who reconstructed the filings. They are frozen before scoring.
- dbyr then answers each question from the records, the same way every time: was the fact recorded before (a), checkable after (b), and would a declared rule have changed the decision (c)?

| | Filing (labs) | Backtesting (this page) |
|---|---|---|
| What you write | the records: Intent, Notice, Closeout, runtime record | the records the lab would have filed, **plus** a list of questions about the incident (decision points) |
| When | before, during and after every covered run | after an incident |
| Main command | `dbyr run` | `dbyr backtest score` |
| Decision points? | **no**: they are not part of the protocol and are never filed | yes |

The paper's cases are in [`benchmarks/`](../../benchmarks/), one folder per incident.

## Backtest an incident, step by step

A **case** is one folder holding the incident's filings and its decision points.

**Step 1. Create the case from the example, and run it unchanged.**

```bash
dbyr backtest init cases/my-case      # copies a complete example case and freezes the schema
dbyr backtest check cases/my-case     # ok (0 errors, 0 warnings)
dbyr backtest score cases/my-case     # prints the verdicts and the results tables
```

All three should succeed before you change anything. The folder now holds a working example (a synthetic safeguards-off evaluation at "Lab X", and a system deployed on it) and a [README](template/README.md) describing every file. `init` records the current schema hash in `decision_points.json` as `schema_hash`: do not change it.

**Step 2. Replace the example filings with the ones the lab would have filed.**

Edit or replace `intent_A.json`, `notice_N1.json`, `closeout_A.json` and (only if a system was deployed) `runtime_S1.json`. For a real incident, use public sources only and record where every value came from in `sources.json`. Check each filing as you write it with `dbyr validate`. The [record docs](../../docs/records/README.md) list every field and every check.

**Step 3. Run the protocol over the filings.**

```bash
dbyr run cases/my-case
```

An error with the code `schema` means a filing is malformed: fix it. Any other error is the protocol rejecting the filing. For a real incident, that rejection is itself a result, not something to fix.

**Step 4. Write the decision points.**

Replace the example decision points in `decision_points.json` with the questions about your incident; keep `case` and `schema_hash`. dbyr does not generate them. **[Writing `decision_points.json`](../../docs/cases/decision_points.md)** describes every key, the test syntax and a complete example. Then check the case:

```bash
dbyr backtest check cases/my-case     # shape, schema hash, record keys, fields, placeholders
```

**Step 5. Score it.**

```bash
dbyr backtest score cases/my-case --out report/ --write-results
```

The case **passes if at least half its decision points were recorded before and checkable after**. Every input is hashed before and after scoring; if anything changed, or the schema is no longer the one frozen in step 1, scoring stops.

**Step 6 (optional). Add context for the tables.**

Edit `annotations.json` (decision kinds, when outsiders learned, the investigation window) and score again. The scoring never reads it; it only fills table cells that would otherwise say "not annotated".

**What you end up with**

| File | Written by | What it is |
|---|---|---|
| `cases/my-case/results.json`, `results.md` | step 5, `--write-results` | the case's pre-registered result, to commit |
| `report/report.md`, `report.html` | step 5, `--out` | the full report: verdicts, the four results tables, every decision point |
| `report/metrics.json` | step 5, `--out` | the same results as data |

In Python:

```python
from dbyr import DBYR

dbyr = DBYR()
dbyr.init_case("cases/my-case")                     # step 1
print(dbyr.check_case("cases/my-case"))             # step 4: [] when the case is ready
bt = dbyr.backtest("cases/my-case")                 # step 5
print(bt.verdicts())
bt.write("report/")
bt.write_results()
```

## Command line

| Command | What it does |
|---|---|
| `dbyr backtest init DIR [--name NAME]` | Write the example backtest case to a new folder. |
| `dbyr backtest check CASE...` | Check cases before scoring: shape, the frozen schema hash, record keys, schema fields, placeholders. Scores nothing; exit code 1 on any error. |
| `dbyr backtest score CASE... [--out DIR] [--write-results] [--design NAME] [--json]` | Score cases and print the verdicts and tables. `--out` writes `report.md`, `report.html` and `metrics.json`; `--write-results` writes `results.json` and `results.md` next to each case. A CASE is a folder or a `decision_points.json`. |
| `dbyr freeze` | Print the schema hash a case is frozen against. |

## Python API: `dbyr.backtest`

Scores the protocol against an incident: were the facts behind each decision written down before the run, and could they be checked afterwards? The whole engine, and an example case to start from, ship with the package.

### The `DBYR` methods for backtests

| Method | Returns | What it does |
|---|---|---|
| `DBYR().init_case(dest, name=None)` | `Path` | Write the example backtest case to a new folder, to start from. |
| `DBYR().check_case(case)` | `list[(severity, message)]` | Check a backtest case before scoring it. Scores nothing. |
| `DBYR().backtest(*cases, designs=None, strict=True)` | `BacktestReport` | Score one or more backtest cases and build the results tables. |

### What a case is

A case is a `decision_points.json` file, given directly or as the folder that holds it. It lists the decision points to score, the filer variants, and where its filings are, in one of two ways:

```jsonc
"records": {"intent:A": "intent_A.json", "closeout:A": "closeout_A.json"}   // filings listed one by one
"filings": "../../filings/lab-x/"                                           // or any filing set
```

`"filings"` points at a filing set kept anywhere on disk: a folder or its `manifest.json`, exactly what `dbyr run` takes, relative to `decision_points.json`. The same filings can then be checked with `dbyr run` and scored with `dbyr backtest score`, without copying them. Next to `decision_points.json`, a case may hold `sources.json` (the provenance of every value) and `annotations.json` (information added after scoring, for the tables; the scoring never reads it). `dbyr backtest init DIR` writes a complete example whose README explains every field.

**Freezing the schema.** A case records `"schema_hash"`: the hash `dbyr freeze` prints, taken before any filing for the case is written. `dbyr backtest init` fills it in. A case scored against a different schema is void: `dbyr backtest check` reports a stale hash as an error, and a case with no hash as a warning.

### Running a backtest

**`Backtest(*cases, designs=None, strict=True).run() -> BacktestReport`**
Loads each case, hashes every input file (including filings kept outside the case folder), scores every decision point under every filer variant, computes the metrics, builds the results tables, and re-hashes the inputs. If any input changed during scoring, it raises `InputsChanged`; if a case's `schema_hash` is not the current schema's, it raises `SchemaChanged` before scoring. With `strict=False`, both are recorded in the report instead, and a stale case's verdict reads "void".

```python
from dbyr.backtest import Backtest

report = Backtest("cases/my-case").run()
report.verdicts()                     # pre-registered pass/fail per case and filer variant
report.table("question_matrix")       # a Table: columns, rows, notes
report.integrity                      # per case: input hashes, and whether they changed
report.write("report/")               # report.md, report.html, metrics.json
report.write_results()                # results.json and results.md next to each case
```

**`BacktestReport`**

| Member | What it holds |
|---|---|
| `verdicts()` | Attributable count, the number needed to pass, and pass/fail, per case and variant. |
| `table(design)` | One of the four table designs (below). |
| `results` | The pre-registered scoring output per case (the `results.json` shape). |
| `metrics` | Every metric per case, including the per-decision classification. |
| `integrity` | Input hashes before and after scoring, per case. |
| `markdown()`, `to_json()`, `write(out)` | The full report as Markdown, JSON, or files. |
| `write_results()` | The pre-registered per-case outputs, `results.json` and `results.md`, next to each case. |

**Table designs** (`DESIGNS`), each a single table answering the questions asked after an incident:

| Design | Shape |
|---|---|
| `scorecard` | One row per case, one column per question. |
| `question_matrix` | One row per question (who knew, what was traceable, why the rest escaped, who was told, how far investigators could look...), one column per case. |
| `today_vs_dbyr` | What today's record supports, what the DBYR record supports, and the evidence. |
| `lifecycle` | One row per stage of an incident: setting up, noticing, responding, telling, investigating. |

**Lower-level pieces**

| Name | What it does |
|---|---|
| `init_case(dest, name=None) -> Path` | Write the example case to a new folder. `TEMPLATE` is its location inside the package. |
| `check_case(case) -> list[(severity, message)]` | Check a case without scoring it: its shape, that every record key exists, that each predicate reads a real schema field, and that none reads a placeholder value. |
| `Case.load(path) -> Case` | Load and validate one case from its folder or its `decision_points.json`; its inputs are fingerprinted first. Raises `CaseError` for a missing file or a malformed case. |
| `score(case) -> dict` | The pre-registered scoring alone: (a) recorded before, (b) checkable after, (c) changes decision, attributable, and the verdict. |
| `compute_metrics(case, scored) -> dict` | The metrics for the tables. Registered metrics come from the scoring; metrics added after scoring are marked new in every output. |
| `build_table(design, metrics) -> Table` | Build one table design from a list of case metrics. |
| `Fingerprint.take(folder, *more)` / `.diff(other)` | Hash every file under one or more folders; list what changed between two fingerprints. |
| `apply_variant(records, variant)` | The filings as a given filer variant would have written them. |

A case may add an optional `annotations.json` (decision kinds, outside-account dates, the investigation window) for the tables; the scoring never reads it. Without it, the cells that need it say "not annotated".

## Layout

```
dbyr/backtest/         the backtest engine: case, lint, scoring, metrics, tables, render, report
  template/            the example case that `dbyr backtest init` writes
docs/cases/            how to write a backtest case's decision_points.json
benchmarks/            data only: the paper's backtest cases (benchmarks/<case>/)
```
