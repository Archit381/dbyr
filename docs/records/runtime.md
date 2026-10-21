# SystemRuntimeRecord

The SystemRuntimeRecord is filed before a system built on a covered run's model is deployed
internally at scale or exposed externally. A deployment is the hand-off from a run that was watched
to a system people use, so this record does two things:

- **It ties the system to its runs.** It names the runs the system is built on, and the protocol
  checks that each was cleared for integration, with no known problem left open, when the system
  went live.
- **It makes the deployment's own advance commitments,** in the same shape as an Intent's: how the
  system is watched, what pauses or withdraws it, who decides, how it is restored, and what evidence
  is kept.

Incidents after deployment are reported in [ExceptionNotices](notice.md) and
[Closeouts](closeout.md) that name the `system_id` instead of a `run_id`. They are checked against
this record exactly as a run's are checked against its Intent.

Its fields fall into six groups:

| # | Group | What it answers |
|---|---|---|
| 1 | [Identity](#1-identity) | Who is filing, for which system, and who holds each role? |
| 2 | [Origin and deployment](#2-origin-and-deployment) | Which runs is the system built on, where is it deployed, and when? |
| 3 | [What the system can do](#3-what-the-system-can-do) | What tools and compute does it have, and can its instances read each other's output? |
| 4 | [Exposure and oversight](#4-exposure-and-oversight) | Who uses it, how is it overseen, and how often is it re-evaluated? |
| 5 | [Monitoring and pause criteria](#5-monitoring-and-pause-criteria) | How is it watched, what pauses it, who decides, and how is it restored? |
| 6 | [Evidence retention](#6-evidence-retention) | What evidence from the deployment is kept? |

**When:** before `deployment_window.start`. While the system stays deployed, a Closeout naming its
`system_id` is due at least every 30 days.

**Example:** [`dbyr/backtest/template/runtime_S1.json`](../../dbyr/backtest/template/runtime_S1.json),
an external deployment of the template's evaluation run that passes every check.

## Fields

Generated from [`system_runtime_record.schema.json`](../../dbyr/schema/system_runtime_record.schema.json).
Required "yes" means the schema requires it. Types are Python type hints; see
[Field types](README.md#field-types).

<!-- fields:start -->
### 1. Identity

Who is filing, for which system, and who holds each role.

| Field | Required | Tier | Meaning | Type |
|---|---|---|---|---|
| `schema_version` | yes | public | The schema version the filing is written against. | `Literal["0.1.0"]` |
| `record_type` | yes | public | The record type. It fixes which schema and which checks apply. | `Literal["SystemRuntimeRecord"]` |
| `system_id` | yes | public | Identifier of the deployed system. | `str` |
| `filed_at` | yes | public | When the record was filed: before deployment_window.start. A later filing is a conduct finding. | `datetime` |
| `signer` | yes | public | Who signs the filing. | `dict` |
| `signer.role_id` | yes | public | The signing role, declared in the roles of the Intent, or of the SystemRuntimeRecord for a deployed system. | `str` |
| `signer.organisation` | yes | public | The organisation the signer acts for. | `str` |
| `roles` | yes | public | Every role this record and the system's later filings name. Titles are public; contacts restricted; identities sealed. | `list[dict]` |
| `roles[].role_id` | yes | public | Identifier other fields use to name the role. | `str` |
| `roles[].title` | yes | public | The role's title. | `str` |
| `roles[].organisation` | yes | public | The organisation the role belongs to. | `str` |
| `roles[].contact_channel` | no | restricted | How to reach the role holder. | `str` |
| `roles[].id_hash` | no | sealed | Hash of the role holder's identity, recoverable only under legal hold. | `str` |

### 2. Origin and deployment

Which runs the system is built on, where it is deployed, and when.

| Field | Required | Tier | Meaning | Type |
|---|---|---|---|---|
| `base_run_ids` | yes | public | The runs whose models the system is built on. Each must have an Intent on record, and its latest Closeout before deployment must clear it for system integration. | `list[str]` |
| `deployment_context` | yes | public | Where the system runs: internal research, internal production, or external use. | `Literal["internal_research", "internal_production", "external"]` |
| `deployment_window` | yes | public | When the system is deployed. A null end means it stays deployed; Closeouts for the system are then due every 30 days. | `dict` |
| `deployment_window.start` | yes | public | First day of the window. | `date` |
| `deployment_window.end` | no | public | null means open-ended: a rolling training run, or a system that stays deployed. Closeouts are then due every 30 days. | `date \| None` |

### 3. What the system can do

The tools it gives the model, how much compute it can use, and whether its instances share output.

| Field | Required | Tier | Meaning | Type |
|---|---|---|---|---|
| `tools_and_scaffolding` | no | restricted | The tools and scaffolding the system gives the model. A tool no base run's agent_capabilities included is a warning: the run's monitoring never saw it in use. | `list[str]` |
| `inference_scaling` | no | restricted | How much inference compute the system can use, and how it scales. | `str` |
| `inter_agent_comms_permitted` | yes | public | Whether instances of the system can read each other's output. | `bool` |

### 4. Exposure and oversight

Who uses it, how people oversee it, and how often it is re-evaluated.

| Field | Required | Tier | Meaning | Type |
|---|---|---|---|---|
| `user_exposure` | no | restricted | Who uses the system, and how many. Required for an external deployment. | `str` |
| `oversight_mode` | no | restricted | How people oversee the system in operation. Required for an external deployment. | `str` |
| `recurring_eval_cadence` | no | restricted | How often the system is re-evaluated. Required for an external deployment. | `str` |

### 5. Monitoring and pause criteria

How the deployed system is watched, what pauses it, who decides, and how it is restored.

| Field | Required | Tier | Meaning | Type |
|---|---|---|---|---|
| `monitoring_instruments` | yes | restricted | How the deployed system is watched. An empty array is a declared absence of monitoring. | `list[dict]` |
| `monitoring_instruments[].kind` | yes | restricted | aggregate_report: counts or volume summaries; observes no individual event. | `Literal["cot_monitor", "reward_seeking_monitor", "trajectory_review", "environment_integrity_check", "access_log_review", "network_alerting", "inter_agent_message_monitor", "write_audit", "aggregate_report"]` |
| `monitoring_instruments[].coverage` | yes | restricted | How much the monitor sees: everything, a sample, or only what an alert raises. | `Literal["all", "sampled", "on_alert"]` |
| `monitoring_instruments[].review_cadence` | no | restricted | How often the monitor's output is reviewed, required when coverage is sampled. | `str` |
| `monitoring_instruments[].sample_rate` | no | restricted | Share of episodes or records reviewed, required when coverage is sampled. Range 0–1. | `float` |
| `monitoring_instruments[].alert_source` | no | restricted | What raises the alert, required when coverage is on_alert. | `str` |
| `monitoring_instruments[].data_source` | no | restricted | The log or stream the monitor reads. | `str` |
| `pause_criteria` | yes | restricted | Events that pause or withdraw the deployed system, who decides, and what must be done. | `list[dict]` |
| `pause_criteria[].criterion_id` | yes | restricted | Identifier that pause events and notices cite. | `str` |
| `pause_criteria[].description` | no | restricted | The criterion in words. | `str` |
| `pause_criteria[].matches` | yes | restricted | Event kinds (see Closeout security_events[].kind) that trigger this criterion. | `list[EventKind]` |
| `pause_criteria[].adjudication` | yes | restricted | Whether a person or an automated check decides that the criterion has fired. | `Literal["human", "machine"]` |
| `pause_criteria[].authority_role` | yes | restricted | The role that decides a pause. It may not also approve restarts. | `str` |
| `pause_criteria[].required_action` | yes | restricted | What the filer commits to do when the criterion fires. pause, pause_and_review and halt_and_amend_intent count as pausing; notify_only does not. | `Literal["pause", "pause_and_review", "halt_and_amend_intent", "notify_only"]` |
| `restart_protocol` | yes | restricted | How a paused system is restored to service. | `dict` |
| `restart_protocol.approver_role` | yes | restricted | The role that approves a restart. It must differ from every pause authority_role. | `str` |
| `restart_protocol.evidence_required` | yes | restricted | What must be shown before a restart is approved. | `list[str]` |
| `restart_protocol.intent_amendment_required` | yes | restricted | Whether a restart requires amending the Intent first. | `bool` |

### 6. Evidence retention

What evidence from the deployment is kept, so later reports can be checked.

| Field | Required | Tier | Meaning | Type |
|---|---|---|---|---|
| `log_retention` | yes | public | What evidence from the deployment is kept, for how long, and how it is reviewed. | `dict` |
| `log_retention.retained` | yes | public | Evidence classes kept for the run. | `list[EvidenceClass]` |
| `log_retention.retain_until` | yes | public | Default closeout+P24M (ISO 8601 duration after closeout). Matches `^closeout\+P[0-9]+[YM]$`. | `str` |
| `log_retention.review_method` | yes | public | How retained evidence is reviewed. | `str` |
| `log_retention.minimum_preserved_pct` | no | public | The least share of generated evidence the filer commits to keep. A Closeout reporting less is a conduct finding. Range 0–100. | `float` |
| `log_retention.detail` | no | public | One entry per retained evidence class. | `list[dict]` |
| `log_retention.detail[].evidence_class` | yes | public | The class this entry describes. | `EvidenceClass` |
| `log_retention.detail[].coverage` | yes | public | Whether every record of the class is kept, or a sample. | `Literal["complete", "sampled"]` |
| `log_retention.detail[].sample_rate` | no | public | Share of records kept, required when coverage is sampled. Range 0–1. | `float` |
| `log_retention.detail[].retention` | yes | public | How long this class is actually kept after it is written. Matches `^(P[0-9]+[DMY]\|indefinite)$`. | `str` |
<!-- fields:end -->

## Checks on this filing

These run when the record is filed. An error stops it being lodged.

### The same commitments as an Intent

Monitors, pause criteria, the restart protocol and retention are checked exactly as in an Intent;
see [intent.md](intent.md#checks-on-this-filing) for why each exists.

| Code | Severity | Fires when | Why |
|---|---|---|---|
| `unknown_role` | error | A criterion's `authority_role`, `restart_protocol.approver_role` or `signer.role_id` is not declared in `roles`. | Every decision must trace to a declared role. |
| `no_monitoring_declared` | warning | `monitoring_instruments` is empty. | A Closeout attesting no events then carries little weight. |
| `monitor_unspecified` | error | A sampled monitor lacks `sample_rate` or `review_cadence`, an on-alert monitor lacks `alert_source`, or any monitor lacks `data_source`. | [R1 S2-E4, S3-E6] |
| `dead_criterion` | error | No declared monitor can observe any of a pause criterion's event kinds. | A criterion nothing can see cannot fire. [T02] |
| `partly_blind_criterion` | warning | No declared monitor can observe some of a criterion's event kinds. | |
| `comms_not_retained` | error | Instances can read each other's output but `inter_agent_messages` is not retained. | [T06] |
| `comms_unmonitored` | error | Instances can read each other's output but neither an `inter_agent_message_monitor` nor `trajectory_review` watches it. | [T06] |
| `self_approved_restart` | error | `restart_protocol.approver_role` is also a role that decides pauses. | [R1 S2-E11, S3-E13] |
| `retention_too_short` | error | `retain_until` is less than 12 months after closeout. | [R1 S2-E9, S3-E7] |
| `retention_detail_missing` | error | A retained evidence class has no `detail` entry, or a sampled class has no `sample_rate`. | [R1 S2-E9, S3-E7] |
| `retention_class_short` | error | A class is kept for less time than `retain_until`. | [R1 S2-E9, S3-E7] |
| `preservation_floor_missing` | error | `log_retention.minimum_preserved_pct` is missing. | Later Closeouts are checked against it. |

### Deployment

| Code | Severity | Fires when | Why |
|---|---|---|---|
| `exposure_undeclared` | error | An `external` deployment does not state `user_exposure`, `oversight_mode` or `recurring_eval_cadence`. | Who uses the system and who watches it must be on record before anyone outside is exposed. |
| `runtime_record_late` | conduct | The record is filed after `deployment_window.start`. | It is due before anyone is exposed; a late filing is recorded, not refused. |

## Checks across filings

### Deployment hand-off

Run over the set: each system is checked against what was on record about its base runs on the
first day of its deployment window.

| Code | Severity | Fires when | Why |
|---|---|---|---|
| `base_run_unknown` | error | A `base_run_id` has no Intent on record. | A deployment must trace to runs that were declared and watched. |
| `deployed_uncleared` | conduct | A base run had no Closeout on record when the system was deployed, or its latest Closeout does not set `cleared_for_system_integration` to true. | Shipping a model whose run was never cleared is a breach of the run's own record. |
| `deployed_over_open_incident` | conduct | A containment exception on a base run was still open, or a notice on it was not yet resolved in a Closeout, when the system was deployed. | A known, unresolved problem was carried into deployment. |
| `untested_tools` | warning | `tools_and_scaffolding` gives the model a tool that no base run's `agent_capabilities` included. | The run's monitoring never saw that tool in use. |

### After deployment

A Closeout or Notice that names the `system_id` is checked against this record with the same
reconciliation, notice and cadence checks as a run's (see [closeout.md](closeout.md#checks-across-filings)
and [notice.md](notice.md#checks-across-filings)). A Closeout for a system with no
SystemRuntimeRecord in the set is an error (`runtime_record_missing`).
