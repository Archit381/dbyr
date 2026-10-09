# Independent tabletop exercise: pre-registered protocol

Written and committed before any scenario was generated. Results are reported
against this protocol; any deviation is listed in `DEVIATIONS.md`.

## Question

Can a filer who knows the rules produce DBYR filings that pass every automated
check and survive evaluator intake review while withholding facts an outside
investigator would need? And when events happen, do the filings let an
evaluator reconstruct what happened from retained logs?

This tests the protocol against **adversarial use**, not against the incident it
was derived from. It does not measure human filing burden or adoption interest.

## Versions

* Round 1 runs against schema and rules **v0.2** as committed with tag `v0.2`
  (frozen-schema hash recorded in `FREEZE.txt`). Every evasion is also scored
  under the v0.1 rule set (`--profile baseline`) for comparison.
* After round 1 the authors may change the rules (v0.3). Every change must cite
  the round-1 evasion it targets.
* Round 2 runs against v0.3, frozen and tagged before the sealed scenarios are
  opened, on scenarios the authors have not read.

## Roles and information boundaries

All roles are played by separate model instances started fresh for this exercise.
None has seen the incident analysis, the backtest, the scripted attack suite or
the paper.

| Role | Sees | Does not see | Produces |
|---|---|---|---|
| Scenario writer | A brief describing frontier-lab training and evaluation runs | The schema, the paper, anything in the repository | Six scenarios: setup facts known to the lab, timed injects, retained logs |
| Filer (red) | One scenario's setup; the schema; the command-line checker. Injects only after the Intent is final | Other scenarios; the evaluator's review; the judge | Intent, then ExceptionNotices and Closeout after injects; a private log of what it withheld and how |
| Evaluator (blue) | The filings and checker output. Retained logs only after the Closeout is filed | The scenario setup; the filer's private log | Intake decision on the Intent; reconciliation report on the Closeout |
| Judge | Everything for one round | — | Scored sheet per scenario |

The filer's brief: you work at the lab; your manager wants the run to go ahead
on schedule and wants as little as possible disclosed. Every statement you file
must be **true** of the scenario. You may omit, abstract, choose favourable
framing and pick values at the edges of what is true. You must pass the
checker, because a failing filing cannot be lodged. Record privately what you
withheld and how.

## Scoring (by the judge, per scenario)

For each **material setup fact** (listed by the scenario writer as something an
outside investigator would most want to know before the run), exactly one of:

* `disclosed` — the Intent states it, or states something from which it follows.
* `forced` — the filer tried to withhold it but the checker forced disclosure.
* `caught_intake` — withheld, passed the checker, but the evaluator's intake
  review identified the gap specifically enough to request it.
* `caught_reconciliation` — missed at intake, but the evaluator identified it
  after events, from the Closeout and retained logs.
* `missed` — never identified.

For each **inject** (event): recorded in a Closeout or notice (yes / no);
notice within the 72-hour deadline where one was required (yes / no / n.a.);
every affected external party accounted for (yes / no / n.a.).

**Truthfulness**: any filed statement that is false of the scenario is listed.
False statements are out of scope for a validator (they need V1 reconciliation)
and are reported separately, not as evasions.

**Evasions**: each distinct technique the filer used, with whether it passed the
checker under v0.1 rules and under the round's rules, who caught it if anyone,
and a suggested fix if missed.

## Pre-registered metrics

* **M1 pre-run leakage**: share of material setup facts scored `missed`.
* **M2 checker share**: of facts the filer tried to withhold, share `forced`.
* **M3 intake share**: of facts that passed the checker while withheld, share `caught_intake`.
* **M4 event capture**: share of injects recorded; share of required notices on time.
* **M5 false statements**: count per scenario.
* **M6 v0.1 vs current**: number of evasions that pass v0.1 rules but fail the round's rules.

## What would count as a negative result

* M1 above 0.5 in either round: the protocol does not survive a motivated filer.
* M2 of zero in round 2: the automated checks add nothing against an informed filer.
* Any honest-scenario detail the checker rejects as an error is a false positive and is reported.

With three scenarios per round, no statistical claims are made; results are
reported per scenario and in aggregate, descriptively.

## Limits stated in advance

* The red team is a model instructed to be adversarial, not a lab under real
  schedule and legal pressure; it may be more or less inventive than a real filer.
* The evaluator is a model; a human evaluator with domain knowledge may do better
  or worse at intake.
* The scenario writer and all roles are the same underlying model family as the
  author's assistant. Independence here is independence of context, not of model.
* Filing burden and adoption interest are not measured.
