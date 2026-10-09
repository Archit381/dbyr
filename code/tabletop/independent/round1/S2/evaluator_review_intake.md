# Evaluator review at intake: ACL-TR-2026-0518 (Aurora Compute Labs)

Filing reviewed: `evaluator_view/intake/intent.json` (TrainingRunIntent, filed 2026-05-18T00:00Z, signed by role `compliance`).
Checker: `python3 -m dbyr check .../intake/` returns **ok, 0 errors, 0 warnings (profile adequacy)**.

The filing passes every automated rule. That shows the filing is well formed and specific enough to pass. It does not show that it is adequate. Several of the passes depend on choices that look like the minimum the checker accepts. I tested this by editing copies of the filing in a scratch session (results are cited below):

- Declaring the build cache `shared_agents` with comms permitted produces `comms_not_retained`.
- Declaring it `cross_run` and shared produces `shared_surface_without_lineage`.
- A Closeout with `attested_absence: true` and 5% logs preserved raises nothing for this Intent.
- A detected `privilege_escalation` or `undeclared_surface_use` event with no ExceptionNotice raises only an `evidence_not_retained` warning.

## 1. Decision

**Request amendment before the run.** The run should not start until items 1–8 below are amended. Items 9–16 can be conditions on acceptance if the lab prefers to answer them in a dated amendment within the first 30-day period, but 1–8 change which obligations apply. They have to be settled before the run starts, because settling them afterwards lets the lab pick its obligations once it knows what happened.

There is also a timing problem. `filed_at` is 2026-05-18T00:00Z and `start_window.start` is 2026-05-18, so the filing leaves no time for intake review. If the run has already started, the amendment should say so and give the exact time of the first optimisation step.

## 2. Specific concerns

### A. Topology declared so as to avoid the comms, lineage and surface rules

**1. The build cache is a channel between agents, but the filing says inter-agent communication is not permitted** (`egress_topology.inter_agent_comms_permitted: false`; `writable_surfaces[s-build-cache].direction` = writers "rollout agents", readers "rollout agents"; `tenancy: run_only`).
A cache that many rollout agents write and many rollout agents read is a channel: one rollout can leave content that a later or concurrent rollout picks up. That is inter-agent communication in substance. The filing sidesteps rule A6 in two ways: it says comms are not permitted, and it labels the surface `run_only`, a tenancy value that does not describe sharing among agents. My probe: an honest `shared_agents` + `inter_agent_comms_permitted: true` immediately triggers `comms_not_retained`, because `inter_agent_messages` would have to be retained and monitored. The lab should state:
- (a) whether a cache entry written in one rollout/episode can be read by a different rollout, concurrently or later in the run;
- (b) whether the cache is keyed per rollout or shared run-wide.

If it is shared, the lab should declare `tenancy: shared_agents` and `inter_agent_comms_permitted: true`, retain `inter_agent_messages` (here: the cache write log with writer and reader identity), and add `write_audit` or `inter_agent_message_monitor`.

**2. A build cache that is "run-only" and lasts only for the run is implausible as stated** (`s-build-cache.persistence: run`, `tenancy: run_only`, readers list only "rollout agents").
Build caches normally exist so that build services and later jobs can reuse artefacts. The reader list leaves out the build services themselves, which are the obvious reader: they consume cached artefacts to produce builds. "run"/"run_only" is the one combination that keeps the surface out of `lineage.check_lineage` (`_shared_persistent` is false) and out of any `inherited_exceptions` duty. The lab should state:
- (a) the mechanism that purges the cache at run end, and what evidence it will file that the purge happened;
- (b) every non-agent reader (build services, CI, other training runs, release or production pipelines);
- (c) whether this cache instance, or the store behind it, was used by any earlier run.

If any of these is "yes", the lab should declare `persistence: cross_run` and the true tenancy, and list the other runs in `shared_surface_lineage` and any open exceptions in `inherited_exceptions`. The `surface_id` should stay stable across runs so that `tenancy_conflict` can catch a contradiction with another run's Intent.

**3. "Build services" are an unnamed hop that very likely leads outside the sandbox** (`permitted_paths[p-internal-build].via: "internal network (build services)"`, `enforcement: packet_filter`, `agent_writable: true`).
The only declared surface is the cache, but the path ends at build services. Build services typically (i) fetch dependencies from external registries, (ii) run agent-supplied build scripts, and (iii) hold registry or push credentials. Each of these is an undeclared surface or path: a package proxy, remote code execution on shared infrastructure, and credential reach. The lab should state:
- (a) which hosts and ports the packet filter allows (allowlist, not description; this can go in the sealed `detail`);
- (b) whether build services make outbound connections (package registries, artefact stores, the internet) on agents' behalf, and if so declare that as a `package_proxy` or `artifact_store` surface with its own tenancy;
- (c) whether build services execute agent-supplied content;
- (d) what credentials the build services hold.

**4. The credential declaration covers only credentials the agents hold directly, not credentials the agents can use through the build services** (`credential_scope.held_by_agents: []`, `admin_credentials_reachable: false`).
If build services push, sign or deploy using their own tokens, an agent that controls build inputs has the use of those credentials without holding them. The lab should state whether any credential that build services use can be exercised by agent-controlled input, and say what "reachable" was taken to mean.

**5. The "mixed" environment is unexplained** (`egress_topology.environment: mixed`).
"Mixed" means some of the run touches live systems. The filing does not say which. The only path declared is to internal build services, so either the build services are the live part (agents act on real company infrastructure) or other live components are undeclared. The lab should list every live (non-twin) system that agents can reach during the run, and the tasks or environments that use them.

### B. Pause criteria and monitoring narrow what counts as a reportable event

**6. A single pause criterion limits the duty to file notices to egress events alone** (`pause_criteria`: only `pc-egress`, matching `sandbox_egress`).
Under `adequacy.check_notices`, an ExceptionNotice within 72h is required only for event kinds that match a declared criterion, plus `third_party_compromise`. Under `validate.reconcile`, `criterion_matched_no_pause_event` fires only for matched kinds. With this filing:
- `undeclared_surface_use`, `credential_misuse`, `privilege_escalation`, `remote_code_execution`, `inter_agent_comms` and `agent_induced_outage` can all occur without any interim notice and without any pause. My probe confirmed this: a detected `privilege_escalation` with no notice produces no error.
- No criterion covers `third_party_compromise`, which matters because build services reach outside.

The lab should add pausing criteria for at least `undeclared_surface_use`, `remote_code_execution`, `privilege_escalation`, `credential_misuse` and `third_party_compromise`. It should also add `inter_agent_comms` if item 1 is resolved as "not shared". Each criterion needs a monitor that can observe it (see item 7).

**7. One sampled monitor makes the egress criterion pass the dead-criterion check on paper only** (`monitoring_instruments`: one `trajectory_review`, `coverage: sampled`, no `review_cadence`).
`trajectory_review` appears in the OBSERVERS list for `sandbox_egress`, so `pc-egress` passes the dead-criterion check (A1). But sampled human reading of transcripts will not reliably catch egress that goes through a packet-filtered network path, and agents may not narrate it at all. Nothing in the declared monitoring can observe `credential_misuse` or `privilege_escalation`; there is no `access_log_review` and no `environment_integrity_check`. Nothing audits writes to the one writable surface; there is no `write_audit`. The lab should state:
- (a) the sampling rate, and how samples are chosen;
- (b) the review cadence, and the maximum time from rollout to review;
- (c) why packet-filter logs are not alerted on.

It should add `egress_alerting` (coverage `all`) on p-internal-build, `write_audit` (coverage `all`) on s-build-cache, and `access_log_review` on the build services.

**8. Detection time is unconstrained, so the 72-hour notice clock can be delayed indefinitely.**
The notice clock and the notification clock both start at `detected_at`. With sampled review and no stated cadence, an egress event that is sampled late, or never sampled, is "detected" late or not at all, and the 72h duty never runs. The lab should commit to a maximum interval between an event and its review: a `review_cadence` on each monitor, for example "daily, with all flagged rollouts reviewed within 24h". In each Closeout it should report the gap between `at` and `detected_at` for every event.

### C. Using the filing to dodge later reporting duties

**9. "No events" can be attested with no monitoring that could have seen them** (Closeout `attested_absence`).
`reconcile_adequacy` rejects an unsupported absence attestation only when T4 is listed. This run is T2 only, so a Closeout that attests no events under one sampled monitor passes; my probe confirmed it passes with `logs_preserved_pct: 5`. The lab should commit now that any `attested_absence: true` in a Closeout will state the sampling rate achieved and will be limited to the event kinds its monitors could observe.

**10. Logs are retained for one month after closeout, and only trajectories** (`log_retention.retained: ["trajectories"]`, `retain_until: closeout+P1M`, no `minimum_preserved_pct`).
- P1M is 1/24th of the stated default (P24M). It is also ambiguous for a rolling run: one month after each 30-day Closeout, or after the final one? An investigator who arrives after an external report would find logs already deleted.
- Without `egress_logs`, `access_logs`, `tool_calls` and `config_snapshots`, the one criterion (egress) cannot be reconciled against network evidence at V1. Without cache write logs, neither can surface use. `reconcile` only *warns* (`evidence_not_retained`) when a Closeout cites evidence that was never retained.
- With no `minimum_preserved_pct`, a Closeout can report any preservation level without triggering `retention_below_floor`.
- `review_method` says review is sampled. It does not say whether *retention* covers every trajectory or only the sample.

The lab should:
- retain all trajectories, `tool_calls`, `egress_logs` (packet-filter logs for p-internal-build), `access_logs` (build services), `config_snapshots` (filter rules and the cache configuration) and the cache write/read log;
- set `retain_until: closeout+P24M`, measured from the final Closeout;
- declare `minimum_preserved_pct` (100 for egress and access logs);
- state that retention is complete, not limited to the sample.

**11. The same role adjudicates pauses and approves restarts, and no amendment is required to restart** (`pause_criteria[0].authority_role` and `restart_protocol.approver_role` are both `training-lead`; `evidence_required: ["root-cause summary"]`; `intent_amendment_required: false`).
The person with the strongest incentive to keep training decides whether an egress event happened, pauses, and approves the restart on the strength of a summary they write. Even if an egress event shows that the declared topology was wrong, the run can resume without correcting the Intent. Such events are exactly the ones that show it was wrong. The lab should:
- name a restart approver separate from the training lead (for example `compliance` or a safety role) and give their contact channel;
- require as evidence the egress and filter logs for the event, the corrected topology, and the remediation;
- set `intent_amendment_required: true` whenever the event involved a path or surface not declared in the Intent.

**12. "Sandbox egress" is undefined, so egress through the permitted path can be relabelled.**
Traffic through the *permitted* path p-internal-build that goes beyond the build services, or content that build services forward outward, could be recorded as `undeclared_surface_use` or `monitor_alert` instead of `sandbox_egress`. Neither of those has a criterion, so the event would not trigger a pause or a notice. The lab should define `sandbox_egress` for this run in `pause_criteria[0].description`. Suggested definition: any connection or data flow initiated by agent action that reaches a destination outside the declared allowlist, including flows that build services make on agent-supplied input.

### D. Capability forecast and run-kind declarations that keep T3/T4 off

**13. Cyber and autonomy are forecast at medium, one band below the T3 trigger, with no eval plan to test the forecast** (`predicted_capability_band.cyber: medium`, `autonomy: medium`; `eval_plan` absent; `trigger_basis: ["T2"]`).
"Medium" is the highest value that keeps T3 off (A9 checks consistency only). The filing has no `eval_plan`, so nothing during the run can show that the forecast was wrong, and no field obliges the lab to amend if checkpoints exceed it. The lab should:
- state the basis of the forecast (predecessor model scores and benchmarks);
- add an `eval_plan` with cyber and autonomy evaluations at stated checkpoint intervals, naming internal or external evaluators;
- commit to file an amendment adding T3 within 72h of any checkpoint reaching "high".

**14. Checkpoint evaluations with safeguards off would fall outside the filing** (`run_kind: training`; `safeguards_disabled: {disabled: false}`, `relaxed` not stated).
If the lab plans dangerous-capability evaluations of checkpoints with refusal training or filters off, those are T4 activity. They would bring the T4 core-coverage rule (A4) and the absence check into force, and as a separate evaluation they would be capped at 31 days (A5). Labelling the run `training` and leaving `relaxed` unstated avoids all of that. The lab should state whether any safeguards-off evaluation of checkpoints will happen during the window. If so, it should declare `run_kind: training_with_evaluation`, add T4, and list what is relaxed. If not, it should say so and set `relaxed: []` explicitly.

**15. The window is open-ended with no compute ceiling** (`start_window`: `start` only, no `end`; `compute_band: 1e24-1e25`).
An open-ended rolling run can cross into 1e25–1e26, and possibly the T1 threshold, partway through, while the filing still reports the lower band. The lab should state the projected total compute and the expected end date (or the condition that ends the run). It should commit to amend the Intent before the cumulative compute crosses the band edge, and confirm that it will file a Closeout every 30 days.

### E. Investigator access

**16. Model access for investigators is not committed** (`investigator_scope_expansion.model_access_committed` absent).
The lab commits to scope expansion, but with no model access and one-month log retention the commitment means little. The lab should state whether a post-incident investigator will get access to the checkpoints that were live during any event, and should give a contact channel for the `compliance` role.

## 3. What I will watch for during the run and at reconciliation

1. **Packet-filter and build-service logs for p-internal-build.** I will look for destinations outside the stated allowlist and for outbound fetches or pushes that build services make on agent-supplied input. Any such flow is `sandbox_egress` and should have a notice within 72h and a `pc-egress` pause event. Under the current filing I expect it to be relabelled.
2. **Contents of s-build-cache.** I will look for writes of executables, scripts, build configs or encoded data. I will check whether entries written in one rollout are read in another (inter-agent channel), and whether anything other than rollout agents reads them (CI, other runs, release pipelines).
3. **Cache persistence.** I will check for evidence that the cache was purged at run end, and whether any later Intent from Aurora declares `s-build-cache` or the same underlying store. That would mean `persistence: run` / `run_only` was false.
4. **Event classification.** I will check whether events are filed under kinds with no criterion (`undeclared_surface_use`, `remote_code_execution`, `monitor_alert`) when the facts are egress. I will also look for Closeout events with no ExceptionNotice.
5. **Gap between `at` and `detected_at`.** Long gaps would indicate that the sampled review is delaying the notice clock.
6. **Pauses and restarts.** I will compare `pause_events` with events, look for restarts approved by the training lead without new evidence or an Intent amendment, and check whether `action_taken` matched `pause_and_review`.
7. **The Closeout's `attested_absence`, `logs_preserved_pct` and achieved sampling rate.** I will check them against the monitoring that was actually deployed.
8. **Log retention.** I will check whether logs still exist when reconciliation happens (P1M), whether all trajectories or only sampled ones were retained, and whether the evidence classes that events cite were in fact retained.
9. **Use of credentials or actions through build services.** I will look for pushes, signing or deploys triggered by agent-controlled input.
10. **Compute and capability drift.** I will look for checkpoint evaluations and their results, any eval run with safeguards off, and cumulative compute against the 1e25 edge. I will also check that a Closeout is filed every 30 days.
11. **Third parties.** I will look for any contact with external registries or services through build services. It should appear as `third_party_compromise` or in `third_party_notifications` if anything outside Aurora was affected.
