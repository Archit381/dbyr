# DBYR v0.3 reference implementation

Code for *Declare Before You Run: A Run-Indexed Disclosure Protocol for Frontier
Training and Evaluation*. It is a reference for the filing format and the checks
described in the paper, not a production register.

```
pip install -r requirements.txt      # jsonschema, cryptography
./reproduce.sh                       # tests, schema hash, tabletop, worked example, field routes
```

## What is here

| Path | What it does | Paper |
|---|---|---|
| `dbyr/schema/*.schema.json` | JSON Schema 2020-12 for the four records (Intent, Closeout, ExceptionNotice, Runtime). `x-tier` marks each field public, restricted or sealed; `x-route` gives its derivation route. | §4.3, App. B |
| `dbyr/adequacy.py` | Minimum-content checks run at intake (v0.2, extended in v0.3 after tabletop round 1; see `tabletop/independent/V03_CHANGES.md`): dead criteria, core coverage under safeguards-off, path writability, run kind, evaluation windows, interim-notice and notification deadlines, cross-run tenancy conflicts. Each cites the tabletop evasion that motivated it. | §4.3, §5.2 |
| `dbyr/validate.py` | Schema conformance plus rules a schema cannot express: T4 when safeguards are off, declared roles, every affected party accounted for, no silent scope narrowing. `reconcile()` checks a Closeout against its Intent. | §4.3 |
| `dbyr/lineage.py` | Cross-run checks: runs reaching the same persistent shared surface must cite each other and any exception already on record. Groups linked runs into one reconciliation unit. | §3.2, §4.3 |
| `dbyr/redact.py` | Projects a filing into public / restricted / sealed views. Hidden fields become salted SHA-256 commitments that can be opened later. | §4.4 |
| `dbyr/ledger.py` | Append-only JSON Lines record. Each entry is Ed25519-signed and hash-chained to the previous one; edits, deletions and reordering are detected. | §4.4, Fig. 3 |
| `dbyr/freeze.py` | Frozen-schema hash, published before held-out scoring. | §5.5 |
| `tabletop/` | The tabletop exercise: three synthetic scenarios with honest filings (false-positive control) and 20 evasion attempts, scored against the v0.1 rules and the current checks. | §5.2 |
| `dbyr/routes.py` | Counts Intent fields by derivation route (adoption argument). | §4.3 |
| `backtest/score.py` | Scores decision points on (a) recorded before, (b) checkable after, (c) changes decision, for two filer variants. Emits the paper's table. | §5.2 |
| `backtest/cases/hf-2026/` | Reconstructed filings and six decision points for the 2026 incident. `sources.json` gives the provenance of every value. | §2, §5 |
| `backtest/cases/_template/` | Instructions for the pre-registered held-out cases. | §5.5 |
| `tabletop/independent/` | The independent tabletop: pre-registered protocol, sealed scenarios, round-by-round filings, evaluator reviews, judge sheets and deviations. | §5.2 |
| `tests/` | 55 unit tests. | |

## Command line

```
python -m dbyr validate [--profile baseline|adequacy] FILE...
python -m dbyr reconcile INTENT CLOSEOUT
python -m dbyr lineage FILE...
python -m dbyr project --view public|restricted|sealed FILE
python -m dbyr keygen KEYFILE
python -m dbyr append LEDGER KEYFILE FILE...
python -m dbyr verify LEDGER
python -m dbyr freeze
python -m tabletop.run --tex-dir ../generated
python -m backtest.score backtest/cases/hf-2026 --tex-dir ../generated
python -m dbyr.routes --tex-dir ../generated
```

## Three severities

`error`: the filing is defective and cannot be lodged. `conduct`: the filing
lodges but truthfully records a breach of the filer's own commitments (a matched
criterion with no pause, logs lost below the declared floor, evidence destroyed,
a late notice); it goes to adjudication. Refusing such a filing would pay the
filer to hide the breach. `warning`: for the reviewer's attention.

## Two rule profiles

`baseline` is the v0.1 rule set: well formed and internally consistent. `adequacy`
(the default) adds the minimum-content checks (v0.3). The tabletop scores evasions
against both. The reconstructed 2026 filings pass `baseline` and are rejected by
`adequacy`, because the declared communication criterion has no monitor that
could ever trigger it.

## Reading the tabletop honestly

There are two exercises, and they test different things.

**Scripted suite (`tabletop/run.py`).** The authors wrote 20 evasions, played
the filer and wrote the checks. The v0.1 column is a fair test, because those
rules were fixed before any evasion was written. The current-rules column is
in-sample: the checks and most evasions came from the same reviewer critiques.
Its informative outputs are the six residual evasions no validator can catch and
the absence of false positives on honest filings.

**Independent tabletop (`tabletop/independent/`).** Separate model instances,
started fresh, write the scenarios, play a red-team filer told to disclose as
little as possible while staying truthful, review filings as the evaluator, and
judge. The protocol and metrics were committed before any scenario existed;
three scenarios were sealed and hashed before round 1. Round 1 ran on v0.2;
v0.3 changes each cite a round-1 evasion (`V03_CHANGES.md`); round 2 runs v0.3
on the sealed scenarios. Independence is of context, not of model, and the
evaluator's requests are not answered by a simulated lab. Every departure from
the protocol is in `DEVIATIONS.md`.

## Reading the worked example honestly

The schema was written after reading the reports of this incident. On this case,
columns (a) and (b) are **traceability**: they confirm the fields capture what
they were written to capture, and they cannot fail by construction. Only column
(c) could have come out against the protocol, and it did: no decision point
yields a "Yes". The same scorer is meant to be run on held-out cases with a
frozen schema and an independent scorer (`backtest/cases/_template/`).

Two filer variants are scored. **Diligent** declares every write permission that
is a configuration fact before the run. **As-believed** declares the package
proxy only as a read path, which models the completeness failure the paper
expects. The gap between them is the cost of incomplete declaration.

The reconstructed filings are **not filings by OpenAI**. Every value is marked in
`sources.json` as first-party, forced-choice (the record shows no decision was
made, but a filing would have required one) or placeholder (not public; never
scored).

## Limits of this code

* It checks filings against each other. A V1 reconciliation additionally checks
  them against retained logs, which requires on-premises access and is out of
  scope here.
* Signatures prove which key signed; binding keys to roles is an operator task.
* `x-tier` projection leaks structure (field names, array lengths) by design: the
  public view shows that a field exists. Hide counts by padding if that matters.
* No network service, access control or key management. Do not deploy as is.
