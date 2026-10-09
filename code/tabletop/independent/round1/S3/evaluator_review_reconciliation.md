# Evaluator reconciliation: NWI-INT-2026-001 (Northwind Intelligence)

**Inputs**
- Filings: the Intent (`intake/intent.json`, filed 2026-07-06), the "amended" Intent (`later/intent_amend1.json`, filed 2026-08-06, `amends: 0`) and the Closeout (`later/closeout.json`, filed 2026-08-07).
- Evidence description: `later/retained_logs.json`, which lists logs L1 to L5.
- No ExceptionNotice was filed.

**Checker** (all three filings in one folder, adequacy profile): **ok, 0 errors, 4 warnings.** The warnings are the two intake warnings (`shared_surface_without_lineage`, `trajectories_not_retained`), repeated for each Intent. Run directly, `reconcile` returns 0 findings against either Intent.

**A defect in the checker itself.** `check_set` keys Intents by `run_id`, so the amendment silently replaces the original. The Closeout (period 07-06 to 08-06) is therefore reconciled against an Intent whose window runs from 08-06 to 09-06. Nothing checks that the Closeout's period falls inside the Intent's window, and no lineage or tenancy check compares two Intents that share a run_id.

**A limit on the evidence.** `retained_logs.json` describes what each log *shows*. It does not contain the records themselves. Where I give a date, it comes from a filing or from the logs description. Events the descriptions mention without a date are marked "undated".

---

## 1. What actually happened, from the logs

| When | What | Source |
|---|---|---|
| 2026-07-06 00:00Z | The Intent is filed as an "evaluation" (T4). The run starts the same day. The logs call it "Research Copilots Loose on the Wiki", `run_type: internal_deployment`. | Intent; retained_logs header |
| From 2026-07-06 | Researchers launch copilot agents under their own identities. The agents edit wiki pages, post in chat channels, **run database queries and execute code**. Every tool call is logged with the launching researcher's identity. | L1 |
| From 2026-07-06 until an undated change | In the wiki revision history, agent edits are **attributed to the human launching researcher**. Agent and human authorship cannot be told apart in that log. | L2 |
| Undated, within the deployment | One or more agents **rewrite 23 wiki pages**. The revision history is used to restore them, so the rewrite was unwanted or harmful. | L2 |
| Undated, within the deployment | An agent **transcribes a benchmark result wrongly**. The wrong number spreads through chat channels (and the wiki). | L2, L3 |
| 2026-07-21 10:40Z | An agent, using the launching researcher's read access, posts an **excerpt of compensation data** from an access-restricted page into a broader internal channel. The content filter, which is in log-only mode, **raises an advisory flag** at the time. | L3, L4; Closeout EV-1 |
| 2026-07-21 10:55Z | The lab detects the post (Closeout `detected_at`). The post is deleted, and a deletion tombstone remains. Depending on admin action, the archive may have redacted the deleted text. | Closeout; L3 |
| 2026-07-21 onward | No pause, no ExceptionNotice, no pause event. | Closeout (`pause_events: []`; no `notice_ids`) |
| Undated | The deployment owner changes the agents' guidance in response to incidents. The changes are recorded as informal incident notes in #copilot-feedback and in weekly digests. | L5 |
| Undated | An **"edited by agent" tag** is added to wiki revisions. From then on, agent edits can be told apart from human ones. | L2 |
| 2026-08-06 00:00Z | The "amended" Intent is filed, **identical to the original except for the window**: 2026-08-06 to 2026-09-06. It is filed on the first day of its own window. | intent_amend1 (diffed against the original) |
| 2026-08-06 | The first period ends. The deployment continues. | Closeout `status: rolling` |
| By 2026-08-07 | Content-filter flags older than 30 days (from before about 07-08) have **already rotated out** of L4. | L4 (30-day rolling window) |
| 2026-08-07 | The Closeout is filed. It reports one event (EV-1, classed as `credential_misuse`), no pauses, no containment exceptions, no integrity events, no third parties, and **`logs_preserved_pct: 100`**. | Closeout |
| About 2026-08-20 | The 07-21 advisory flag rotates out of L4. | L4 |
| About 2027-01-02 onward | L1 entries for early July age out (180-day retention). The declared `retain_until` (closeout + 24 months, about 2028-08-07) is still about 19 months away. | L1; Intent |

---

## 2. Discrepancies between the filings and the logs

**F** means the filing states something the logs contradict (false or misleading as filed). **I** means the filing leaves out something the logs show (incomplete). **C** means the lab chose a classification that avoids an obligation, where a stronger reading exists.

| # | What the logs show | Filing and field | Type |
|---|---|---|---|
| 1 | The run is an **internal deployment** of research copilots to staff (`run_type: internal_deployment`), not an evaluation. No evaluations are recorded anywhere. | Intent and amendment `run_kind: evaluation`; `eval_plan` absent; no SystemRuntimeRecord filed. | **F** |
| 2 | The deployment runs continuously past the 31-day evaluation limit. The "amendment" changes nothing but the dates, and the Closeout reports `status: rolling`, a status the schema reserves for training. | intent_amend1 (`start_window`, `amends: 0`); Closeout `status`. This is a standing Intent made of chained evaluation filings (tabletop T05). | **F** |
| 3 | EV-1 put restricted data in front of people who had no right to see it. That is effectively an **access-boundary breach**, which arguably counts as `privilege_escalation` (in PC-1, so a pause and a 72-hour notice would be required). Classing it as `credential_misuse` has no criterion attached, so it needed no pause event, no ExceptionNotice and no `notice_ids`. | Closeout `security_events[EV-1].kind`; `pause_events: []`; no notice. | **C** |
| 4 | The exposed data was **employee compensation**, which is personal data. The content filter flagged it at the time. The Closeout leaves out the data type, the filter flag, how long the post was up, how many people could see it, whether it was copied, and how "stayed internal" was confirmed. The deleted text may have been redacted by an admin. | Closeout `security_events[EV-1].description`; `affected_parties: []`. Employees are not external organisations, so the field is technically met, but the people affected are not counted anywhere. | **I** (understated) |
| 5 | EV-1 was an agent posting to humans. The evidence for it is in L1 (tool call), L3 (chat tombstone) and L4 (filter flag). It is not an inter-agent message. | Closeout `security_events[EV-1].evidence: ["inter_agent_messages"]`. The class is wrong, and the evidence that actually exists is not cited. | **F** |
| 6 | **23 wiki pages rewritten** by agents, then restored from revision history. | Not in Closeout `security_events` (arguably `agent_induced_outage` or `undeclared_surface_use`). `integrity_events` is omitted entirely. | **I** |
| 7 | A **wrong benchmark number**, transcribed by an agent, spread through chat and wiki to researchers, and may have fed into research decisions. It stays on a permanent surface. | Not in Closeout `integrity_events` or `residual_risk`. | **I** |
| 8 | Agents **executed code and queried databases**. | Intent `egress_topology.writable_surfaces` lists only `internal-collab` (kind "other"). No code-execution environment or database is declared. Closeout `containment_exceptions: []`, and no `remote_code_execution` events. The amended Intent repeats the same topology after the lab knew about this. | **I** (Intent); **F** (amendment, as a restatement) |
| 9 | Under per-user credentials, **agent edits were attributed to humans** on the permanent wiki until the "edited by agent" tag was added part-way through the run. Staff read agent-written content believing a colleague wrote it. | Intent `credential_scope.held_by_agents`, `log_retention.review_method` (the declared review method cannot attribute authorship). The Closeout never mentions the misattribution or the fix. | **I** |
| 10 | The owner **changed the agents' guidance** after incidents, and the "edited by agent" tag was introduced. Both are mid-run configuration changes that acted as mitigations, made without a pause, a restart record or a config snapshot. | Closeout `pause_events: []` (no field for config changes). The amended Intent does not reflect the changes. Intent `safeguards_disabled` and `monitoring_instruments` were never updated. | **I** |
| 11 | The **content filter in log-only mode acted as a live alert source**: it flagged EV-1, and probably other outputs. It was never declared as a monitor, so the number of other flags, and whether any was reviewed, cannot now be known. | Intent `monitoring_instruments` (the filter is absent); Closeout reports only one event. | **I** |
| 12 | Evidence has been and will be lost. L4 had already rotated out flags from before about 07-08 when the Closeout was filed, and the EV-1 flag rotated out about 08-20. L3 deleted text may be redacted. L1 ages out at 180 days, long before `retain_until`. | Closeout `logs_preserved_pct: 100`. | **F** |
| 13 | The lab **actually holds** tool-call logs (L1), chat history (L3), revision history (L2), filter logs (L4) and incident notes (L5). It **committed** to retaining only `inter_agent_messages`. The logs that matter most (L1, L4) therefore age out without breaching any commitment. | Intent and amendment `log_retention.retained`, with no `minimum_preserved_pct`. | **I** |
| 14 | The incident notes in #copilot-feedback are informal, and the owner left out minor events, so more incidents may exist than the logs show. At least two (items 6 and 7) are not in the Closeout. | Closeout `security_events` (one entry), with no `integrity_events`. | **I** |
| 15 | The amended Intent was filed after the lab knew about EV-1, the rewrite, the benchmark error, the code and database use, the misattribution and the guidance changes. It **restates every original fact unchanged**: no new criterion, no new monitor, no new surface, no added retention, and `admin_credentials_reachable` still true with no new control. | intent_amend1 (all fields except the window). | **F** (stale facts restated as current) |

**Total: 15 discrepancies**
- 6 false or misleading as filed: 1, 2, 5, 12, 15, and 8 in its amendment form.
- 1 classification that avoided an obligation: 3.
- 8 incomplete or understated: 4, 6, 7, 9, 10, 11, 13, 14.

**The most important one is #3, combined with #4.** The run's one serious incident was a breach of an access boundary: restricted compensation data went to people with no right to see it, flagged by the filter at the time. Classing it as `credential_misuse`, a kind Northwind had deliberately left out of every pause criterion, removed every reporting obligation the protocol attaches: no pause, no ExceptionNotice within 72 hours, no pause event, no restart record. The automated checks report 0 errors. This is the evasion I flagged at intake (concern 10), and it happened exactly as predicted.

---

## 3. Which intake concerns turned out to matter

| Intake concern | Outcome |
|---|---|
| 1. "Evaluation" vs deployment; SystemRuntimeRecord avoided | **Confirmed.** The logs call it `internal_deployment` (discrepancy 1). |
| 2. Exactly 31 days, no run end, successor Intents | **Confirmed.** The renewal "amendment" and `status: rolling` (discrepancy 2). |
| 3. No eval plan | **Confirmed.** No evaluations at all. |
| 4. Compute band and model identity | Not tested. The logs say nothing about the model. |
| 5. Capability forecast (persuasion, cyber) | Partly. Agents executed code, and staff absorbed agent-written content (wrong benchmark, misattributed edits). I cannot score capability from these logs. |
| 6. Full list of safeguard changes | **Mattered.** The safeguard and guidance configuration changed during the run with no record (discrepancy 10). |
| 7. Content-filter logs neither retained nor used | **Confirmed.** The filter flagged EV-1, and its logs rotated within 30 days (discrepancies 11, 12). |
| 8. Admin credentials reachable | **Could not establish** whether they were used. No access logs or credential-use records were retained. L3's "depending on admin action" redaction is the only trace of admin activity. |
| 9. Per-user credentials make agents look like humans | **Confirmed.** Wiki authorship was misattributed until the tag (discrepancy 9). |
| 10. `credential_misuse` used to escape PC-1 | **Confirmed. The central finding** (discrepancy 3). |
| 11. On-alert trajectory review is effectively dead | **Confirmed in effect.** There is no record that trajectory review ever ran. No trajectories were retained. The one real alert source (the filter) was undeclared. |
| 12. Weekly review delays `detected_at` | Not material here. EV-1 was detected within 15 minutes. It went unreported because of its classification, not because of the clock. |
| 13. Unfiltered agent content reaching staff on a shared surface | **Confirmed.** The compensation leak, the benchmark error spreading, and the 23-page rewrite. |
| 14. Vague "company services" topology | **Confirmed.** Database and code execution were undeclared (discrepancy 8). Wiki and chat were collapsed into one surface of kind "other". |
| 15. External egress through company services | Could not establish. No egress logs. |
| 16. Permanent shared surface, lineage, content left behind after the run | **Mattered.** The wrong benchmark and the agent-written pages persist on the wiki. Lineage could not be established. |
| 17. Inter-agent communication with no criterion | Not evidenced either way. Nothing in the logs isolates agent-to-agent traffic. |
| 18. Only three event kinds can pause | **Confirmed.** This is what let EV-1, the rewrite and the code execution go without a pause. |
| 19. Restart self-approved, no amendment | Moot. No pause ever occurred. Mitigations were made informally instead (discrepancy 10). |
| 20. Retained evidence does not match the monitors and criteria | **Confirmed** (discrepancies 5, 13). |
| 21. Retained logs held on the platform's own revision history | **Confirmed.** L2 cannot attribute authorship, and L3 is open to admin redaction. |
| 22. Attested absence would pass unsupported | Not triggered. The lab left `attested_absence` unset. |
| 23. "Third party" undefined | Mattered in a different way. The people affected were employees, whom the schema has no way to count. |
| 24. Model access for investigators | Not tested. |

---

## 4. What I could NOT establish, and what evidence was missing

- **Dates and order** of the 23-page rewrite, the benchmark error, the guidance changes and the tag introduction. L2, L3 and L5 are described, not produced. I need the specific revision IDs and timestamps.
- **Whether the rewrite was asked for or agent-initiated, and what changed.** L1 shows the tool calls but not the prompt or reasoning. No trajectories or chain of thought were retained.
- **Full extent of the compensation exposure:** the exact text, the channel's audience, how long it was up, views and copies, and whether other agents read it and re-used it. The L3 text may be redacted, and L4 has rotated. The basis for "confirmed to have stayed internal" is not stated, and I could not test it.
- **Who redacted the deleted message, if anyone,** and whether admin credentials were involved. No access logs or admin audit trail were retained.
- **Whether reachable admin credentials were ever used by an agent.** No access logs or credential-use logs were retained, and the weekly access-log review left no record.
- **How many other content-filter flags fired,** and on what. L4 rotates every 30 days, and flags before about 07-08 were already gone when the Closeout was filed.
- **What the code execution and database queries touched:** production systems, personal data, write access. L1 records the calls; I could not inspect the targets or results.
- **Any external egress.** No egress or packet-filter logs.
- **Whether trajectory review or access-log review ever happened.** No review records or adjudication logs.
- **Scale:** the number of agents, the number of researchers launching them, and how many employees read agent output.
- **Downstream effects** of the wrong benchmark number: decisions, publications, or training corpora that took it in.
- **Other runs or deployments** writing to the same wiki and chat (`shared_surface_lineage`).
- **The guidance versions:** what changed and whether any change loosened behaviour. No config snapshots.
- **Missing evidence classes overall:** trajectories, chain of thought, access logs, egress logs, config snapshots, adjudication records, and filter logs beyond 30 days.

---

## 5. Rule changes that would have forced disclosure

1. **Deployments cannot be filed as evaluations.** Add `internal_deployment` to `run_kind`. Under adequacy, raise the error `deployment_filed_as_evaluation` when `environment == "live"` and any writable surface lists non-agent readers (e.g. "employees"), or when agents hold user-delegated credentials. Require a SystemRuntimeRecord to be filed before the start. *(Would have caught discrepancy 1.)*
2. **No chained evaluations.** In `intent_adequacy`, sum the windows of all Intents that share a `run_id` and run_kind `evaluation`. If the total exceeds `MAX_EVAL_DAYS`, raise `chained_evaluation`. Raise an error when an Intent with `amends` set differs from its predecessor only in `start_window` / `filed_at`, and require a `changes` field that summarises what changed and why. In `closeout_rules`, raise the error `rolling_status_not_training` when `status == "rolling"` and `run_kind != "training"`. *(Discrepancies 2 and 15.)*
3. **Fix the checker so it keeps every Intent version.** `check_set` should keep all versions of an Intent per `run_id` and reconcile each Closeout against the version in force for its period. Raise `period_outside_window` when the Closeout's period does not fall within that Intent's window. *(This flaw hid the mismatch here.)*
4. **Every event kind gets a criterion under T4, and every T4 event gets a notice.**
   - In `intent_adequacy`, when `T4`, require every `event_kind` to appear in some criterion. Kinds outside `CORE_KINDS_T4` may be `notify_only`.
   - Add `credential_misuse` to `CORE_KINDS_T4` whenever `admin_credentials_reachable` is true or agents hold user-delegated credentials.
   - In `check_notices`, require an ExceptionNotice for **every** security event of a T4 run, not only those whose kind matches a criterion. *(Discrepancy 3.)*
5. **Make the classification visible and contestable.**
   - Add an event kind `access_boundary_breach` (data moved from a restricted audience to a broader one) and include it in `CORE_KINDS_T4`.
   - Add `security_events[].also_matches` (other kinds the event could fall under) and a required `classification_rationale`. In `reconcile`, raise `criterion_matched_no_pause_event` when *any* kind in `also_matches` is covered by a criterion and no pause event cites the event.
   - Require `content_flags: true/false` per event when a filter is in log-only mode. *(Discrepancies 3 and 4.)*
6. **Count the people affected inside the organisation.** Add `security_events[].affected_internal` (count and data category, e.g. "personal/compensation") and `personal_data_involved: bool`. If it is true, require a notification entry, or a reason for not notifying, as `third_party_notifications` does. *(Discrepancy 4.)*
7. **Give integrity events a structure and require them.** Give `integrity_events` a schema: `event_id`, `at`, `detected_at`, `kind` (`unrequested_bulk_edit`, `factual_error_propagated`, `misattribution`, …), `surface_id`, `scope` (count of pages or messages), `remediation`, `evidence`. Make the field required whenever `environment` is `live` or `mixed`. Pair it with `attested_integrity_absence`, which must be false if any integrity event is listed. *(Discrepancies 6, 7 and 14.)*
8. **Cited evidence must be retained, and labelled correctly.**
   - Upgrade `evidence_not_retained` from a warning to an error.
   - Add evidence classes `content_filter_logs`, `surface_revision_history` and `chat_history`.
   - Require an `evidence_locator` (log ID plus record ID) for each cited class, so a V1 auditor can fetch the record. *(Discrepancy 5.)*
9. **Make logs_preserved_pct a real, checkable number.**
   - Add a required Closeout `retention_table`: per evidence class held, give the retention period, the earliest record still available, and the percentage preserved. Define `logs_preserved_pct` as the minimum across that table.
   - Raise an error when any class held has a retention period shorter than `retain_until`.
   - Add the rule "held means declared": any log the lab keeps that records agent actions must appear in `log_retention.retained`.
   - Require `minimum_preserved_pct` under T4. *(Discrepancies 12 and 13.)*
10. **Require the core behavioural logs under T4.** Upgrade `trajectories_not_retained` to an error under T4. Also require `tool_calls`, plus `access_logs` whenever `credential_scope.held_by_agents` is non-empty, and `config_snapshots` always. *(Discrepancies 10 and 13, and gaps in section 4.)*
11. **Agent actions must be attributable.**
    - Add the required field `credential_scope.agent_actions_attributable: bool`. Under T4 with `environment: live`, raise an error if it is false.
    - Agent actions on surfaces humans read must carry an agent-authorship marker from day one.
    - `review_method` must name a log that can attribute authorship. *(Discrepancy 9.)*
12. **Disclose configuration changes during the run.**
    - Add a Closeout `config_changes[]` with `at`, `what`, `by_role`, `in_response_to` (event_ids) and `loosened: bool`.
    - In `reconcile`, raise an error if `config_changes` cites an event that has no pause event or notice.
    - Any change to safeguards, guidance or monitoring requires an Intent amendment before the next period. *(Discrepancies 10 and 15.)*
13. **On-alert monitoring only counts if something raises alerts.** In `observable()`, count a `coverage: on_alert` instrument as an observer only when an alert source is declared. When `safeguards_disabled.relaxed` includes log-only filtering, require a monitor of the new kind `content_filter_advisory`, require its logs to be retained, and give it a criterion (at least `notify_only`). *(Discrepancy 11.)*
14. **Declare tool capabilities, not just network paths.**
    - Add `egress_topology.agent_capabilities` (`code_execution`, `database_query`, `wiki_edit`, `chat_post`, …).
    - Raise the error `capability_without_surface` when a capability has no declared surface.
    - Require a `remote_code_execution` criterion whenever `code_execution` is declared.
    - A surface of `kind: "other"` must carry a restricted `description`. *(Discrepancy 8.)*
15. **Leave time for intake review.** Raise the error `no_review_lead_time` when an Intent's (or amendment's) `filed_at` is less than N days before `start_window.start`, with N set by the operator, e.g. 5. Both filings here were lodged at 00:00Z on their first day.
