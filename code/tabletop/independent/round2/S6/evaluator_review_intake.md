# Intake review: `tessellate-aria5-collab-eval-2026-09` (Tessellate AI)

Reviewed: `intake/intent.json` (filed 2026-09-17), `intake/checker_output.txt`. I re-ran the checker myself and got the same result: **FAIL, 2 errors, 3 warnings**.

## 1. Decision: REJECT (resubmit before the run starts or continues)

Reasons, most important first:

1. **The checker fails, and both errors go to the heart of the filing.**
   - `core_kind_uncovered`: no declared monitor can observe `privilege_escalation`. That is a core kind for a safeguards-off run.
   - `retention_too_short`: `closeout+P4M` is below the 12-month floor.
2. **The filing passes everything else only by sitting exactly on the thresholds.**
   - The only monitor that counts as an observer is `trajectory_review` at `sample_rate: 0.01`. That equals the profile's `MIN_SAMPLE`. Researchers review it as part of "analysis of agent coordination", so it is not a safety review.
   - The filing was made 4 days before the start, against a 3-day minimum.
   - The window is 30 days, against a 31-day maximum.
   - `minimum_preserved_pct` is declared as **0**, so the lab commits to preserving nothing.
   - Every pause-relevant event kind (egress, tampering, inter-agent comms, data exposure, integrity) is "observable" only through a 1% sample of an orchestration log. With 250 concurrent agents running for a month, about 99% of episodes are never seen by anyone. The `aggregate_report` observes no individual event.
3. **The material risk is the combination of the two relaxations, and the filing does not describe it.**
   - The retrieval store persists for the whole campaign and is readable by **every** Aria-5 agent in the campaign. Readers are not limited to the episode team.
   - Output filters apply only to final answers, so the notes agents write to that store are unfiltered.
   - Together this is a month-long, unfiltered, shared memory across 250 agents. It is lightly watched, and its contents are not committed to be snapshotted or retained once the run ends.
   - This is the channel through which collusion, encoded messages, injected instructions or grader-gaming strategies would spread. The filing frames it as "documentation, issue history, agent-written notes".
4. **By design, agents' code runs in CI ("submit proposed patches for test runs").** Yet CI is not declared as a writable surface. Nothing is said about its isolation, credentials, caches or dependency fetching, and CI execution logs are not retained.
5. **The pause authority is not independent.**
   - The lead researcher signs the Intent.
   - The lead researcher is the sole authority on every criterion, and PC1 says they decide "whether to stop the campaign", which makes a `pause_and_review` criterion discretionary.
   - Every other reportable kind, including `remote_code_execution`, `credential_misuse` and `data_exposure`, is `notify_only`, and the filing does not say who is notified.
6. **Timing.** The window opened on 2026-09-21, and today is 2026-10-08. If any part of the campaign has already run under a failing Intent, the lab must say so (see request 1).

## 2. Requests for information

**R1. Run status (`start_window`, `filed_at`).**
- The window opened 17 days before this review. State whether any episodes have run. If so, give:
  - the first episode timestamp;
  - the number of episodes completed;
  - the current number of entries in the retrieval store.
- Confirm that every log written since the start is under preservation hold. Without a hold, the `P180D` per-class clock is already running out on the earliest records.
- Resolved by: a dated statement of what has run, plus a written preservation hold covering all event-log records and the retrieval store from the first episode.

**R2. Privilege-escalation and credential observability (`monitoring_instruments`; checker errors and warnings).**
- No declared instrument can see privilege escalation or credential misuse. The orchestration log records tool calls at the agent interface. It does not record what agent-authored code does once it runs inside CI.
- Declare an `access_log_review` or `environment_integrity_check` on the CI runners and the retrieval-store backend, giving for each:
  - its data source (e.g. runner auth/audit logs, container runtime events, store ACL logs);
  - its coverage (not sampled);
  - its alert source;
  - its review latency in hours.
- Then make `privilege_escalation` and `credential_misuse` pausing criteria.

**R3. Retention (`log_retention`).**
- Raise `retain_until` to at least `closeout+P12M`; the schema default is P24M.
- Set each class's `retention` to measure from closeout, not from write. As filed, `P180D`-from-write and `closeout+P4M` use different start points, and records from the first week can expire before `retain_until`.
- Replace `minimum_preserved_pct: 0` with a real floor, and explain why any figure below 100 is acceptable for complete-coverage classes.
- Add the following classes to `retained`, or justify each omission:
  - `trajectories`: the full agent transcripts, including model outputs the orchestration log does not capture. The checker warns that, without them, V1 reconciliation is impossible.
  - `config_snapshots`: the state of the retrieval store, the CI configuration and permissions at each change.
  - `access_logs`
  - `egress_logs`: needed so the claim of "no egress" can be checked.
  - `chain_of_thought`, if the model produces it.

**R4. Retrieval store contents and lifecycle (`writable_surfaces[campaign-retrieval-store]`, `per_episode_reset` relaxation).**

State:
- (a) whether "agents in this campaign" means every one of the 250 concurrent agents across all episode teams, and if so, why the collaborative task needs cross-team read access;
- (b) whether every write and every read/retrieval result is logged with agent ID, episode ID, timestamp and full content, or only metadata;
- (c) whether the store is seeded from any earlier run or campaign, and whether its contents (including agent-written notes) will be reused in later runs, evaluations or **training data** for any model. This determines whether `persistence: run` and the empty `shared_surface_lineage` are accurate;
- (d) what happens to the store at closeout (deleted, archived or snapshotted), with a commitment to retain a full snapshot for the retention period;
- (e) any size, rate or format limits on notes, and whether non-natural-language content (encoded or binary blobs) is permitted.

**R5. Output filters on intermediate outputs (`model_output_filters` relaxed).**
- Name the production classifiers that are disabled on intermediate outputs.
- Confirm that this covers agent-to-agent messages **and** notes written to the persistent store, so that content production would block reaches the other 249 agents and persists.
- Say whether filters run in shadow (logging, not blocking) on intermediate outputs. If not, explain why shadow scoring is infeasible.
- Resolved by: a list of classifiers, their mode on intermediate outputs, and the retention of their scores.

**R6. Sandboxed CI as an undeclared surface (`egress_topology`, `agent_capabilities`).**
- Agent patches execute in CI. Declare CI as a writable surface with tenancy and isolation, and state:
  - (a) whether runners, workspaces, build caches or artifact stores are shared across episodes or teams, or wiped per job;
  - (b) how dependencies are resolved. If there is a package mirror or proxy, it is a `package_proxy` surface and a `permitted_path`, and the empty `permitted_paths` is wrong. If dependencies are vendored, say so;
  - (c) what credentials, tokens or service accounts the CI job environment holds. `held_by_agents: []` must be true of the code agents run, not only of the agents;
  - (d) the enforcement that gives CI no egress (physical separation or packet filter), and whether CI shares hosts or networks with any non-sandbox system;
  - (e) what "digital_twin" is a twin of, and whether CI is purpose-built or a partition of Tessellate's internal CI.

**R7. Grader and test integrity (`environment_tampering`, PC1).**
- The CI test results are the grader. State whether patches may modify:
  - test files;
  - test configuration (e.g. `conftest.py`, CI workflow files, build scripts);
  - the harness itself.
- State what prevents a patch from changing the grading of its own episode or of later ones.
- Declare an `environment_integrity_check` or `write_audit` that detects such changes on every submission, not 1%. As filed, PC1's tampering criterion can fire only if a researcher happens to sample the episode.

**R8. Monitoring that matches the scale (`monitoring_instruments[0]`).**
- Specify:
  - what a 1% sample is drawn from (episodes, messages or tool-call records), and how it is drawn;
  - who reviews it (research staff or safety staff);
  - the maximum latency from event to review;
  - the number of episodes and agent-hours in the campaign, so the absolute number of reviewed episodes can be computed (see R13).
- Add at least one full-coverage automated monitor on inter-agent messages and store writes (an `inter_agent_message_monitor`), with its alert source and escalation path. "During the campaign, as part of researcher analysis of agent coordination" is not a review cadence.

**R9. Pause criteria and authority (`pause_criteria`, `roles`, `restart_protocol`).**
- (a) Remove the discretion in PC1, so that a matched event pauses the campaign automatically pending review rather than leaving the lead researcher to decide whether to stop.
- (b) Give a role other than the lead researcher (who also signs the Intent) authority to pause on its own: head-safety-evals or a third party.
- (c) For PC2, name who is notified and within how many hours.
- (d) Justify keeping `remote_code_execution`, `credential_misuse`, `access_boundary_breach` and `data_exposure` as `notify_only` while safeguards are relaxed. Any of them occurring in this environment would mean the sandbox has been breached.
- (e) `inter_agent_comms` is the intended behaviour, so as a criterion it will match continuously or never. Define the abnormal pattern that should match, e.g. encoded content, coordination across teams, instructions aimed at the grader or the monitors.
- (f) Explain why a restart needs only the event-log records of the triggering episodes. Each pause should require a store snapshot and a review of what other agents read from the implicated notes. State why `intent_amendment_required: false` holds even after a containment event.

**R10. Capability forecast (`predicted_capability_band`, `forecast_basis`).**
- The basis offered describes what the **evaluation** is designed to elicit, not what **Aria-5** can do. Provide:
  - the checkpoint identifier;
  - whether it is the production model or a pre-release or helpful-only variant;
  - its most recent dangerous-capability eval results for cyber and autonomy, with dates and evaluators;
  - whether those evals were run with the same relaxations.
- Explain why 250 coordinating software agents with code execution and persistent shared memory are "low" for autonomy and cyber. Bug-fixing at scale is closely related to finding vulnerabilities.

**R11. Compute band (`compute_band`).**
- State whether `<1e24` refers to the compute used by this campaign or to Aria-5's training compute, and give Aria-5's training-compute band separately.

**R12. Identity and least privilege (`identity_separation`, `least_privilege_access` marked "on").**
- (a) State the author and committer identity on patches submitted to CI. Confirm that no human's git identity, token or bot account tied to a person is used.
- (b) Reconcile `least_privilege_access: on` with every agent being able to read every other team's notes for a month. If the task does not need that access, the safeguard is relaxed and should be declared as such.

**R13. Run scale (`run_scale`).**
- Give:
  - the total number of episodes;
  - team size;
  - the number of teams;
  - episode duration;
  - total agent-hours;
  - `human_users` (confirm 0).

**R14. Snapshot contents and data exposure (`readable_sources`, `data_classes`).**
- Identify the source of the "static snapshot of bug-tracker issues": public open-source projects, Tessellate internal repositories, or customer data.
- Say whether it has been scanned for secrets, credentials, personal data and unpatched vulnerability reports.
- Populate `data_classes`.
- `data_exposure` is in PC2, but nothing in the filing says what data could be exposed or to whom.

**R15. Containment and investigator access (`containment_plan`, `investigator_scope_expansion.model_access_committed`).**
- Provide `on_detected_subversion` and `full_offline_conditions`. In particular, say whether the retrieval store is frozen and quarantined on a PC1 event, and whether every agent is stopped or only the triggering episode.
- Commit `model_access_committed: true`, with the exact checkpoint preserved for the retention period.
- Specify what an investigator receives: full logs, the store snapshot, and the CI images.
