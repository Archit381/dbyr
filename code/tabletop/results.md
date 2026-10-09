# Tabletop exercise

Evasions: 20. Caught by v0.1 rules: 2. Caught under current adequacy rules (v0.3): 14. Residual: T11, T12, T14, T15, T16, T17.
False positives on honest filings: none.

| ID | Scen. | Evasion | Source | v0.1 | v0.3 | v0.3 codes | If missed, what exposes it |
|---|---|---|---|---|---|---|---|
| T01 | S1 | Vague topology: ``standard sandboxing'', writability omitted, no surfaces | External review | missed | caught | comms_channel_undeclared, writability_undeclared |  |
| T02 | S2 | Criterion no declared monitor can trigger | External review | missed | caught | core_kind_uncovered, dead_criterion |  |
| T03 | S2 | Every criterion only notifies | External review | missed | caught | core_kind_uncovered |  |
| T04 | S2 | One catch-all criterion on monitor alerts | Authors | missed | caught | core_kind_uncovered, kind_uncriteried |  |
| T05 | S2 | Standing quarterly Intent for evaluations | Earlier critique | missed | caught | standing_intent |  |
| T06 | S2 | Declare communication permitted so coordination is never an exception | Authors | missed | caught | comms_channel_undeclared, comms_not_retained, comms_unmonitored, kind_uncriteried |  |
| T07 | S2 | No monitoring under safeguards-off | Authors | missed | caught | core_kind_uncovered, dead_criterion, no_monitoring_t4 |  |
| T08 | S2 | Egress path with no enforcement | Authors | missed | caught | unenforced_path_t4 |  |
| T09 | S2 | Exception first reported at the 30-day closeout | External review | missed | caught | notice_missing |  |
| T10 | S2 | Third party notified 20 days late, no reason | External review | missed | caught | late_notification |  |
| T11 | S2 | Third party not told; reason ``not required'' | Authors | missed | missed |  | Adjudicator reviews stated reasons; requester right (future work) |
| T12 | S2 | Scope narrowed with boilerplate grounds | Authors | missed | missed |  | Refusal is on record; adequacy of grounds needs an adjudicator |
| T13 | S1 | One run declares a shared cache run-only | Earlier critique | missed | caught | comms_channel_undeclared, tenancy_conflict, tenancy_mislabelled |  |
| T14 | S1 | Both runs declare a shared cache run-only | Earlier critique | missed | missed |  | V1: access logs show cross-run writes |
| T15 | S2 | Safeguards-off not declared (T4 omitted) | External review | missed | missed |  | V1: configuration snapshots; whistleblower |
| T16 | S1 | Runs split below the compute threshold | External review | missed | missed |  | V2: compute telemetry (research stage) |
| T17 | S1 | Capability forecast lowered to avoid T3 | Earlier critique | missed | missed |  | Closeout capability results against forecast; external evaluation |
| T18 | S2 | Restart approved by an undeclared approver | Authors | caught | caught | restart_wrong_approver |  |
| T19 | S2 | Absence of events attested with blind monitoring | Authors | missed | caught | absence_unsupported, core_kind_uncovered, dead_criterion |  |
| T20 | S2 | Investigation scope narrowed with no refusal logged | Authors | caught | caught | silent_scope_narrowing |  |

## Honest filing controls

- S1: baseline errors none, adequacy errors none; warnings ['shared_surface_without_lineage']; Intent has 170 filled values
- S2: baseline errors none, adequacy errors none; warnings ['undeclared_surface']; Intent has 173 filled values
- S3: baseline errors none, adequacy errors none; warnings none; Intent has 169 filled values
