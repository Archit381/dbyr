# v0.3 rule changes, each tied to round 1

The protocol allows rule changes between rounds if every change cites the
round-1 evasion it targets. Numbers in brackets refer to the round-1 judge's
ranked list (`round1/judge/summary.md`).

| # | Change | Targets |
|---|---|---|
| 1 | Reportable event kinds extended (`environment_tampering`, `access_boundary_breach`, `data_exposure`, `integrity_incident`); `integrity_events` and `internal_incidents` required; every internal incident mapped to events or given a reason; `attested_absence` required and explained; each event carries a `classification_rationale` | S2-E5, S2-E6, S3-E3, S3-E10 [1] |
| 2 | Interim-notice duty follows a fixed list of reportable kinds, not the filer's criteria; under safeguards-off every reportable kind needs a criterion; any run with a shared agent-writable surface needs an observable pausing criterion for tampering and a criterion for inter-agent communication | S2-E2, S3-E3, S3-E4 [2] |
| 3 | Safeguards checklist of six production safeguards, each stated; "relaxed" counts as disabled, so the safeguards-off floor applies | S2-E1, S3-E9 [3] |
| 4 | Terms defined in the schema (tenancy, "permitted", preservation denominator, event completeness, evidence classes); retention and preservation per evidence class; retention floor of 12 months; preservation floor required | S2-E7, S2-E9, S3-E7, S3-E12 [4] |
| 5 | Monitors state data source, sample rate and cadence, and alert source; sub-1% samples, on-alert monitors without an alert source and aggregate reports observe nothing | S2-E4, S3-E5, S3-E6 [5] |
| 6 | Each writable surface declares `isolation`; a shared surface cannot be `run_only`; `inter_agent_comms_permitted` is a fact about the environment and must be true when any surface is shared | S2-E3 [6] |
| 7 | Closeout lists `config_changes` and `surface_resets`; a reset without a snapshot during an open incident is recorded | S2-E8 [7] |
| 8 | `internal_deployment` run kind; evaluation windows summed across amendments; amendments list their changes; only training may be rolling | S3-E1, S3-E2 [8] |
| 9 | The set checker keeps every Intent version and reconciles each Closeout against the version in force | S3-E2 [9] |
| 10 | Required: `agent_capabilities`, `readable_sources`, `run_scale`, `forecast_basis`; `reward_design` for training; `eval_plan` when any forecast is above low | S2-E10, S2-E12, S3-E8, S3-E14, S3-E15 [10] |
| 11 | Intent filed at least 3 days before the start; restart approver holds no pause authority; explicit end date; closeout cadence and coverage checked | S2-E11, S3-E13, every round-1 Intent [11] |
| 12 | **Conduct severity.** Findings that record a breach the filer admits (criterion matched with no pause, restart by the wrong role, logs below the declared floor, evidence destroyed, a late notice, an overdue closeout, operation outside the window) no longer stop a filing being lodged. They are flagged for adjudication. Without this, v0.3 would have paid filers to hide the breach | Judge headline finding 4 ("v0.2 creates incentives against honesty") |
| 13 | A run with no events and monitoring too weak to attest absence can close out by stating why absence is not attested. A first v0.3 draft required attestation here, which, combined with change 1, left such a run unable to lodge any honest closeout | Found while upgrading the honest control filings |

## Not changed, and why

* **Truth of a statement** (S3-E5, a volume digest called an access-log review):
  no validator can check this; it is left to V1 reconciliation.
* **Low capability forecasts** (S2-E12, S3-E15): a basis and an eval plan are
  now required, but whether the forecast is honest is checked only against later
  results.
* **`also_matches[]`** on events (judge item 2): self-declared, so a filer
  dodging a criterion would leave it empty. Change 2 removes the payoff instead.
* **Affected internal people** (S3 I2, employee data exposed): the new
  `data_exposure` kind records the event; there is still no field for internal
  people affected. Listed as open.

## Scripted suite after v0.3

Two scripted attacks (T14, T15) and one (T19) were written before the v0.3
fields existed and were initially "caught" only because they deleted those
fields. They were rewritten as rule-aware lies (every declaration consistent
with the false one). After that, the scripted results are unchanged from v0.2:
2 caught by v0.1 rules, 14 by the current rules, 6 residual.
