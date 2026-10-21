<div align="center">

# Declare Before You Run

### An Open Filing Standard for Frontier Training and Evaluation Runs

[![🏅 4th Place · Apart Research AI Incident Response Sprint](https://img.shields.io/badge/%F0%9F%8F%85%204th%20Place-Apart%20Research%20AI%20Incident%20Response%20Sprint-gold?style=for-the-badge)](https://apartresearch.com/sprints/ai-incident-response-sprint-2026-09-11-to-2026-09-13#overview)

**🏅 Placed 4th globally out of 231 projects (971 sign-ups) at the [Apart Research AI Incident Response Sprint](https://apartresearch.com/sprints/ai-incident-response-sprint-2026-09-11-to-2026-09-13#entries), September 2026.**

**Mann Acharya** · **Archit Ojha** · **Gautam Sankara Raman** · **Karm Rajput**

*with [Apart Research](https://apartresearch.com)*

[Paper](website/assets/declare_before_you_run_frontier_training_evaluation_filing_standard.pdf) · [Site](https://mach-12.github.io/dbyr/) · [Timeline](https://mach-12.github.io/dbyr/#timeline)

</div>



## Interactive Demonstration

The [live site](https://mach-12.github.io/dbyr/) walks through the standard end to end: the DBYR lifecycle and record-schema diagrams, the [incident timeline](https://mach-12.github.io/dbyr/#timeline) as both a visual chart and a full event table, and the backtest results.

## Authors

- **Mann Acharya** — The Millennium Project. Originated the idea; led the project and policy analysis.
- **Archit Ojha** — Independent. Designed the record schema and verification stack.
- **Gautam Sankara Raman** — Independent. Conducted the incident timeline reconstruction; collected and analyzed public responses.
- **Karm Rajput** — Independent. Background research on the cybersecurity aspects of the project.

Research conducted at the [AI Incident Response Sprint](https://apartresearch.com/sprints/ai-incident-response-sprint-2026-09-11-to-2026-09-13), with Apart Research, September 2026, where it placed 4th of 231 submitted projects.

---

## The `dbyr` package

This repository is the executable form of the paper: the JSON Schemas for the four DBYR records, the checks an evaluator runs on them, the public / restricted / sealed disclosure views, a signed hash-chained ledger, and a backtest engine that scores the protocol against an incident.

### Install

```bash
pip install git+https://github.com/mach-12/dbyr      # the package and the dbyr command
pip install -e .                                     # or, from a clone
```

Python 3.11+. Dependencies: `jsonschema` and `cryptography`, installed automatically.

### Backtest your own case, step by step

You have an incident, real or synthetic, and want to know whether DBYR would have made its key decisions traceable and checkable. A **case** is one folder holding the incident's filings and the decision points they are scored on.

**Step 1. Create the case from the example, and run it unchanged.**

```bash
dbyr backtest init cases/my-case      # copies a complete example case and freezes the schema
dbyr backtest check cases/my-case     # ok (0 errors, 0 warnings)
dbyr backtest score cases/my-case     # prints the verdicts and the results tables
```

All three should succeed before you change anything. The folder now holds a working example (a synthetic safeguards-off evaluation at "Lab X", and a system deployed on it) and a [README](dbyr/backtest/template/README.md) describing every file. `init` records the current schema hash in `decision_points.json` as `schema_hash`: do not change it.

**Step 2. Replace the example filings with your incident's.**

Edit or replace `intent_A.json`, `notice_N1.json`, `closeout_A.json` and (only if a system was deployed) `runtime_S1.json`. The [record docs](docs/records/README.md) list every field and every check. Check each filing as you write it:

```bash
dbyr validate cases/my-case/intent_A.json
```

**Step 3. Run the protocol over the filings.**

```bash
dbyr run cases/my-case
```

An error with the code `schema` means a filing is malformed: fix it. Any other error is the protocol rejecting the filing. For a real incident, that rejection is a result to report, not something to fix.

**Step 4. Replace the example decision points with yours.**

Edit `decision_points.json`. Keep `case` and `schema_hash`; write everything else: where the filings are, and one entry per decision that shaped the incident, each with a test on a filing made before it and a test on the Closeout after it. The [case README](dbyr/backtest/template/README.md#4-replace-the-decision-points-with-your-own) lists the keys. Then check the case:

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

The same steps in Python:

```python
from dbyr import DBYR

dbyr = DBYR()
dbyr.init_case("cases/my-case")                     # step 1
report = dbyr.check("cases/my-case")                # step 3: the protocol's findings
print(report.ok, report.counts())                   # True {'error': 0, 'conduct': 0, 'warning': 1}
print(dbyr.check_case("cases/my-case"))             # step 4: [] when the case is ready
bt = dbyr.backtest("cases/my-case")                 # step 5
print(bt.verdicts())
bt.write("report/")
bt.write_results()
```

### The records

[`docs/records/`](docs/records/README.md) documents the four records a developer files: when each is due, every field with its disclosure tier and meaning, and every check with its severity and the reason for it.

| Record | Filed | Doc |
|---|---|---|
| TrainingRunIntent | before the run | [intent.md](docs/records/intent.md) |
| ExceptionNotice | within 72 hours of detecting a reportable event | [notice.md](docs/records/notice.md) |
| TrainingRunCloseout | at the end, and at least every 30 days | [closeout.md](docs/records/closeout.md) |
| SystemRuntimeRecord | before deployment at scale or external exposure | [runtime.md](docs/records/runtime.md) |

---

## Python API

Everything below is importable from the top-level package: `from dbyr import <name>`. The backtest names come from `dbyr.backtest`.

### `DBYR`: one object for the common tasks

Start here. Each method wraps one of the functions further down.

| Method | Returns | What it does |
|---|---|---|
| `DBYR().schema_hash()` | `str` | The hash of the frozen schemas. Publish it before a case is scored; recompute it when scoring. |
| `DBYR().load(*paths)` | `FilingSet` | Load a filing set from a folder, its `manifest.json`, or a list of record files. |
| `DBYR().check(*paths, views=True)` | `Report` | Run the whole protocol over a filing set. |
| `DBYR().validate(record)` | `list[Finding]` | Check one filing on its own. |
| `DBYR().project(record, tier)` | `dict` | The `"public"`, `"restricted"` or `"sealed"` view of one filing. |
| `DBYR().init_case(dest, name=None)` | `Path` | Write the example backtest case to a new folder, to start from. |
| `DBYR().check_case(case)` | `list[(severity, message)]` | Check a backtest case before scoring it. Scores nothing. |
| `DBYR().backtest(*cases, designs=None, strict=True)` | `BacktestReport` | Score one or more backtest cases and build the results tables. |

```python
from dbyr import DBYR

dbyr = DBYR()
dbyr.init_case("cases/my-case")
report = dbyr.check("cases/my-case")
for stage, at, finding in report.findings:
    print(stage, finding)

dbyr.check_case("cases/my-case")      # [] when the case is ready to score
bt = dbyr.backtest("cases/my-case")
print(bt.verdicts())
```

### Filing sets

A filing set is the unit the protocol runs on: Intents (and amendments), ExceptionNotices, Closeouts and SystemRuntimeRecords.

**`load_filing_set(*paths) -> FilingSet`**
Load from a `manifest.json` (`{"records": {"intent:A": "intent_A.json", ...}}`), a folder, or files. Without a manifest, every `*.json` with a `record_type` is a filing; other JSON is listed in `skipped`.

```python
from dbyr import load_filing_set
fs = load_filing_set("cases/my-case")
fs.records        # {"closeout_A.json": {...}, "intent_A.json": {...}, ...}  (no manifest: keyed by file name)
fs.files          # filing key -> path on disk
fs.description    # from the manifest, if any
fs.skipped        # JSON files that are not DBYR records
```

**`FilingSet`**: the loaded set (`records`, `files`, `description`, `skipped`).
**`FilingSetError`**: raised for a missing file, invalid JSON or a bad manifest.

### Running the protocol

**`run_protocol(filings, views=True, ledger=None, signing_key=None) -> Report`**
Runs every stage in the order an evaluator meets them: each record on its own, Intent versions, reconciliation of each Closeout against the Intent in force, notice timeliness, and lineage across runs sharing a surface. Optionally projects the disclosure views and signs lodged filings into a ledger.

```python
from dbyr import load_filing_set, run_protocol
report = run_protocol(load_filing_set("cases/my-case"))
report.ok              # False if any finding is an error
report.counts()        # {"error": 0, "conduct": 0, "warning": 1}
report.lodged          # filing keys that passed their own checks
report.views           # filing key -> public / restricted / sealed / openings
print(report.to_markdown())        # or report.to_json()
```

**`check_set(filings: dict) -> list[tuple[str, Finding]]`**
The checks alone, without views or a ledger: every finding labelled with the filing key or stage it belongs to.

**`Report`**: the result of `run_protocol` (`ok`, `counts()`, `findings`, `lodged`, `views`, `ledger_entries`, `to_json()`, `to_markdown()`).

### Checking individual records

| Function | Checks |
|---|---|
| `validate_record(record) -> list[Finding]` | One filing on its own: schema, cross-field rules and minimum content for its record type. |
| `reconcile(intent, closeout) -> list[Finding]` | A Closeout against the Intent it closes: matched criteria without a pause, restart approvals, undeclared surfaces, retention and preservation. |
| `check_notices(intent, closeout, notices) -> list[Finding]` | Every reportable event has an ExceptionNotice filed within 72 hours of detection. |
| `check_lineage(intents, closeouts) -> list[Finding]` | Runs reaching the same persistent shared surface cite each other and any exception already on record. |
| `linked_groups(intents) -> list[set[str]]` | The run ids that form one reconciliation unit because they share a surface. |

```python
import json
from dbyr import validate_record, reconcile

intent = json.load(open("cases/my-case/intent_A.json"))
closeout = json.load(open("cases/my-case/closeout_A.json"))
validate_record(intent)              # [] when the Intent lodges
for f in reconcile(intent, closeout):
    print(f)                          # [warning] code at /pointer: message
```

### Findings

Every check returns `Finding` objects with a `severity`, `code`, `where` (a JSON pointer) and `message`.

| Severity | Meaning |
|---|---|
| `error` | The filing is defective and is not lodged. |
| `conduct` | The filing lodges, but it records a breach of the filer's own commitments (a late notice, a matched criterion with no pause). It goes to adjudication; admitting a breach is never costlier than hiding it. |
| `warning` | For the reviewer's attention. |

**`errors(findings)`** and **`conduct(findings)`** filter a list to one severity.

### Disclosure views

Each field has a disclosure tier. A field above the viewer's tier is replaced by a salted commitment, so the viewer can see it exists and later check it without learning its value.

**`project(record, view, salts=None) -> (view, openings)`**
`view` is `"public"`, `"restricted"` or `"sealed"`. `openings` maps each committed field's JSON pointer to its salt; the filer keeps it.

**`all_views(record) -> dict`**: `{"public", "restricted", "sealed", "openings"}` in one call, with consistent salts.

**`check_opening(commitment, value, salt_hex) -> bool`**: check a revealed value against its commitment.

```python
import json
from dbyr import project, check_opening

intent = json.load(open("cases/my-case/intent_A.json"))
public, openings = project(intent, "public")
public["monitoring_instruments"]      # {"$commitment": "sha256:...", "$tier": "restricted"}

salt = openings["/monitoring_instruments"]
check_opening(public["monitoring_instruments"]["$commitment"], intent["monitoring_instruments"], salt)  # True
```

### The ledger

**`Ledger(path)`**: an append-only, hash-chained, Ed25519-signed record of lodged filings, one entry per line. Deleting, reordering or editing any entry breaks every later link.

| Method | What it does |
|---|---|
| `append(record, signing_key, filed_at=None) -> dict` | Validate, sign and append one filing; returns the entry. |
| `verify(trusted_keys=None) -> list[Finding]` | Recheck every hash link and signature. |
| `entries()` | Every entry, in order. |
| `head()` | The hash of the last entry. |

```python
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from dbyr import Ledger

key = Ed25519PrivateKey.generate()
book = Ledger(Path("record.jsonl"))
book.append(intent, key)
book.verify()                         # [] when every link and signature holds
```

### Schema and integrity

**`schema_hash() -> str`**: the SHA-256 of the canonical form of every schema file. Reformatting a schema does not change it; any change to its content does.
**`SCHEMA_VERSION`**: the schema version label.

---

## Backtests: `dbyr.backtest`

Scores the protocol against an incident: were the facts behind each decision written down before the run, and could they be checked afterwards? The whole engine, and an example case to start from, ship with the package.

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

---

## Command line

`dbyr <command>` (or `python -m dbyr <command>`):

| Command | What it does |
|---|---|
| `dbyr run PATH... [--out DIR] [--ledger FILE --key KEYFILE] [--json]` | Run the whole protocol over one filing set. `--out` writes `report.json`, `report.md` and every disclosure view. Exit code 1 if any finding is an error. |
| `dbyr validate FILE...` | Check each filing on its own. |
| `dbyr project --view TIER FILE` | Print the public, restricted or sealed view of a filing. |
| `dbyr keygen KEYFILE` | Write a new Ed25519 signing key, for `run --ledger`. |
| `dbyr verify LEDGER` | Recheck every hash link and signature in a ledger. |
| `dbyr freeze` | Print the schema hash. |
| `dbyr docs [DIR] [--check]` | Rewrite the field tables in the record docs (default `docs/records`) from the schemas. `--check` only reports stale docs, with exit code 1. |
| `dbyr backtest init DIR [--name NAME]` | Write the example backtest case to a new folder. |
| `dbyr backtest check CASE...` | Check cases before scoring: shape, the frozen schema hash, record keys, schema fields, placeholders. Scores nothing; exit code 1 on any error. |
| `dbyr backtest score CASE... [--out DIR] [--write-results] [--design NAME] [--json]` | Score cases and print the verdicts and tables. `--out` writes `report.md`, `report.html` and `metrics.json`; `--write-results` writes `results.json` and `results.md` next to each case. A CASE is a folder or a `decision_points.json`. |

---

## Layout

```
dbyr/                  the installable package
  api.py               DBYR, the facade
  filingset.py         loading filing sets
  protocol.py          run_protocol, check_set, Report
  rules/               the checks: intent, closeout, notice, runtime, reconcile, versions, lineage
  params.py            deadlines, floors and fixed lists the checks apply
  schema/              the JSON Schemas and their validators
  disclosure.py        public / restricted / sealed views with salted commitments
  ledger.py            the signed, hash-chained record
  integrity.py         canonical JSON, digests and the schema hash
  findings.py          Finding and its three severities
  docgen.py            the field tables in docs/records/, generated from the schemas
  backtest/            the backtest engine: case, lint, scoring, metrics, tables, render, report
    template/          the example case that `dbyr backtest init` writes
docs/records/          the four records: fields, deadlines and every check
benchmarks/            data only: the paper's backtest cases (benchmarks/<case>/)
tests/                 unit tests
website/               the project site
```

## Tests

```bash
python -m unittest discover -s tests
```
