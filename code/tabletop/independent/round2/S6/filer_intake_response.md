# Response to intake review: `tessellate-aria5-collab-eval-2026-09` (Tessellate AI)

The campaign configuration is fixed as described in the Intent and in this response, so we cannot add the monitoring or extend the retention that the two checker errors require. An amended Intent would still fail with `core_kind_uncovered` and `retention_too_short`, so we answer in text only and **do not file an amended Intent**. Where this response corrects or qualifies a value in the Intent, we say so explicitly. Those corrections are collected at the end.

---

**R1. Run status.**
- The scheduled start was 2026-09-21. This response does not include the first-episode timestamp, the number of episodes completed or the number of entries in the retrieval store.
- We cannot confirm a preservation hold. Event-log retention is 180 days from write, as filed.

**R2. Privilege-escalation and credential observability.**
- No `access_log_review` or `environment_integrity_check` is in place for this campaign, on the CI runners or on the retrieval-store backend. We cannot declare one.
- `privilege_escalation` and `credential_misuse` therefore remain unobservable by any declared instrument. This is the cause of the first checker error.

**R3. Retention.**
- The orchestration event log (inter-agent messages and tool calls) is retained for 180 days from write. That period is not measured from closeout, and we cannot raise it to closeout+P12M.
- No preservation floor beyond that retention is committed, so `minimum_preserved_pct` remains 0.
- Other classes:
  - `trajectories`: not retained as a separate class. The event log records every inter-agent message and tool call.
  - `config_snapshots`: not retained.
  - `access_logs`: not retained.
  - `egress_logs`: not retained. CI containers have no internet egress.
  - `chain_of_thought`: not retained.

**R4. Retrieval store.**
- (a) Yes. The store is per campaign, not per episode or per team. Notes written by any agent are retrievable by agents in later episodes of the campaign. It persists across episodes to avoid re-embedding cost; we do not claim the individual task requires cross-team read access (see R12(b)).
- (b) Store writes and retrievals are tool calls, and every tool call is recorded in the orchestration layer's structured event log. We give no field-level detail beyond that.
- (c) Before the campaign the store is seeded with documentation and issue history. It is not shared with any other run during the campaign. This response makes no statement about use after the campaign.
- (d) No closeout snapshot is committed. The store keeps only its current contents and has no write history.
- (e) No size, rate or format limits on notes are declared.

**R5. Output filters.**
- Classifier names are not provided.
- Confirmed: content filtering is applied only to each episode's final answer, before it is recorded as the episode result. Inter-agent messages and intermediate tool use are not content-filtered during an episode, and notes written to the store are intermediate tool use.
- No shadow scoring of intermediate outputs is declared for this campaign.
- The relaxation was approved by the Head of Safety Evaluations for this internal research campaign. Its purpose is to let researchers study emergent coordination without filter interference.

**R6. CI.**
- (a) The scratch CI system is shared across the campaign. Builds run in ephemeral containers, and the containers share a build cache across the campaign. We accept that the shared build cache is a surface agents' code can affect and that it is absent from `writable_surfaces`.
- (b) CI containers have no internet egress. We do not declare a package mirror or proxy.
- (c) No further detail is provided on credentials in the CI job environment.
- (d) No enforcement mechanism is specified in this response.
- (e) The task data is a frozen snapshot of open bug trackers. No external systems are in scope.

**R7. Grader and test integrity.**
- No detail is provided on whether patches can modify tests, test configuration or the harness.
- No `environment_integrity_check` or `write_audit` is in place.

**R8. Monitoring at scale.**
- The 0.01 `sample_rate` is the filer's estimate of the share of episodes researchers examine. It is not a parameter of a defined sampling protocol.
- The reviewers are research staff, and no maximum review latency is committed.
- There is no alerting. A researcher reviews a dashboard of episode outcomes daily.
- The campaign is expected to run about 50,000 episodes over two weeks. Agent-hours are not provided.
- No full-coverage automated monitor on inter-agent messages or store writes is in place, and we cannot add one.

**R9. Pause criteria and authority.**
- (a, b) Authority to stop the campaign rests with the lead researcher. Any engineer can kill an individual episode. No other role holds campaign-level pause authority, and we are not changing that.
- (c) PC2 names no recipient and no deadline. Incident handling for this campaign is informal.
- (d) The split between pausing and notify_only in PC1 and PC2 is the filer's codification for this filing. Beyond the stop and kill authorities above, the lab has no formal pause criteria.
- (e) No abnormal-pattern definition for `inter_agent_comms` exists.
- (f) The restart protocol in the Intent is the filer's statement. No further restart requirement exists.

**R10. Capability forecast.**
- The bands are the filer's assessment.
- This response provides no checkpoint identifier, no variant and no dangerous-capability eval results. The bands should not be read as resting on such results.

**R11. Compute band.**
- `<1e24` was entered for this campaign's compute and is an estimate. Aria-5's training-compute band is not provided.

**R12. Identity and least privilege.**
- (a) No detail is provided on patch author or committer identity.
- (b) We accept that `least_privilege_access` should be read as **relaxed**. Agents can read notes from other teams' earlier episodes because the store persists across the campaign, not because each task needs that access.

**R13. Run scale.**
- About 50,000 episodes over two weeks.
- Each episode has one team of five Aria-5 agents: a planner, two coders, a reviewer and a researcher.
- Episode duration and agent-hours are not provided.
- `concurrent_agents: 250` is an estimate, not a configured or measured value.
- No human users are declared.

**R14. Snapshot and data.**
- The task data is a frozen snapshot of open bug trackers, plus documentation and issue history in the retrieval store.
- No detail is provided on scanning for secrets, credentials, personal data or vulnerability reports.
- No results are shared outside Tessellate during the campaign.

**R15. Containment and investigator access.**
- No containment plan beyond R9(a, b) is in place, and freezing the store on a PC1 event is not committed.
- `model_access_committed` is not committed.
- The investigator scope-expansion commitment stands as filed.

---

**Corrections and qualifications to the filed Intent:**
- `least_privilege_access` should be read as relaxed.
- The CI shared build cache is an undeclared shared surface.
- These values are estimates: `sample_rate` 0.01, `concurrent_agents` 250 and `compute_band` (campaign compute).
- The pause criteria and restart protocol are the filer's codification of an informal arrangement.
