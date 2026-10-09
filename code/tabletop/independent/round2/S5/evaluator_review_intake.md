# Intake review: `cobalt-verso2-rl-dataeng-01` (Cobalt Research Institute)

Filed 2026-02-05. Start window 2026-02-09 to 2026-03-02. Trigger: T4. Checker re-run by the evaluator: **FAIL, 3 errors and 3 warnings** (output matches `checker_output.txt`).

## 1. Decision: **Reject.** Refile before the run starts.

The filing fails the adequacy profile on three counts:

- There is no pause criterion that can observe `privilege_escalation`.
- Inter-agent messages are not retained, although inter-agent communication is declared permitted.
- `retain_until` is `closeout+P3M`, and the minimum is P12M.

Each of these blocks acceptance by itself. More important, the filing describes something the checker cannot see. The run gives 64 RL agents read access and in practice write access to a production-shared NFS volume that "other internal workloads" also read and write. It also lets them write to the lab's experiment-tracking database, which human researchers read. Write scope on both is limited only by *instruction*. The run is also labelled `network_isolation: on`, `per_episode_reset: on`, `admin_credentials_reachable: false` and `permitted_paths: []`. These claims are hard to square with the surfaces declared. Monitoring, for its part, is a weekly review of 2% of transcripts plus aggregate metrics.

As filed, an investigator could not answer three questions after an incident:

- What did the agents write to `/shared` or the database?
- Did they touch other workloads or the run's own metrics and grading?
- Which agent did it?

None of the evidence that would answer them is retained. The individual problems are listed below in rough priority order.

## 2. Requests for information

### A. Reach of the shared filesystem and least-privilege relaxation

**1. `safeguards_disabled.checklist[least_privilege_access].change`: the actual mount scope.**
The filing says only that the mount is "broader than the per-job default" and that agents are "instructed" to write only under `/shared/rl-scratch`. Provide:

- (a) the exact path or paths mounted into agent sandboxes, with the mode (ro or rw) for each path;
- (b) the POSIX UID/GID or NFS export identity the agents use, and whether it is unique to this run or shared with other jobs;
- (c) whether any technical control (export rules, ACLs, a read-only bind mount outside `rl-scratch`, a seccomp or LSM policy) prevents writes outside `/shared/rl-scratch`;
- (d) what "repository-exploration tasks" need that the per-job default does not give.

If no technical control exists, say so explicitly. In that case the declared writable surface is the whole mount, not `rl-scratch`. A sufficient answer is a mount table plus an export/ACL listing. Prose will not do.

**2. `readable_sources` / `writable_surfaces[cobalt-shared-fs]`: what lives on `/shared`.**
"Shared networked filesystem volume" does not say what agents can read. The filing also omits `data_classes`. List the top-level directories reachable from the mount and the owning team or workload of each. State whether any of the following sit inside the mount:

- (i) code, configs or fixtures for this run's graders or reward computation;
- (ii) task specifications or reference solutions for this run;
- (iii) checkpoints or weights of Verso-2 or any other model;
- (iv) other runs' training data, scratch areas or outputs;
- (v) credentials, tokens, SSH keys, kubeconfigs, `.env` or `.netrc` files, or service-account key files;
- (vi) personal, customer or otherwise restricted data;
- (vii) source repositories for training, monitoring or DBYR tooling.

For each item, answer yes or no and give its path.

**3. `credential_scope.admin_credentials_reachable: false`: basis for the claim.**
The mount is wider than default and covers a volume shared with other internal workloads. Describe how this was established: secret scanning of the reachable tree, with the tool, date and result count. Say whether credentials found by that scan were removed or left in place.

### B. Identity of the other workloads and lineage

**4. `shared_surface_lineage` (empty) and `writable_surfaces[*].direction`.**
The filing names "other internal workloads" as writers *and* readers of `cobalt-shared-fs`. That contradicts an empty lineage. The checker warns on both surfaces. Provide:

- the `run_id` of every DBYR-covered run that can reach either surface during the start window;
- for non-DBYR workloads, a category list (for example "data pipelines", "eval jobs", "researcher notebooks") with the approximate number of jobs;
- whether any of those workloads *execute* content read from `/shared`, such as scripts, notebooks, configs or pipeline definitions.

The last point decides whether an agent write can turn into code execution in another workload.

**5. `inherited_exceptions` (omitted).**
State whether any linked run has an open containment exception on `cobalt-shared-fs` or `cobalt-exp-tracking-db`. If one does, cite it. If none does, state that explicitly.

### C. Experiment-tracking database (likely reward/metric integrity issue)

**6. `writable_surfaces[cobalt-exp-tracking-db]`: why agents can write to it, and how far that reaches.**
"Postgres experiment-tracking database" with a single service account does not describe scope. Provide:

- (a) the grants held by the agents' service account, table by table, at the level of SELECT, INSERT, UPDATE, DELETE and DDL;
- (b) whether the account is used only by this run or is the same account other jobs or researchers use;
- (c) whether agents can read or modify rows belonging to other runs or experiments;
- (d) whether the database holds *this run's* training metrics, rewards, grades, eval results or checkpoint-selection data;
- (e) whether any column holds secrets, such as run configs with embedded tokens or connection strings.

**7. `tenancy: shared_agents` on the database: probable misclassification.**
Readers include "experiment-tracking users", so other people and processes read what agents write. Confirm whether the tenancy should be `shared_runs`, and whether any external party, such as collaborators or a SaaS front-end, reads it (which would make it `external`). Name the human population that reads it and roughly how many people that is. `run_scale.human_users` is omitted, and `environment: mixed` implies live users somewhere.

### D. Reward and grader design (tampering exposure)

**8. `reward_design`.**
"Graders run outside agent sandboxes" says where the grader process runs, not what it reads. For each task family (dataset cleaning, pipeline repair, report production), specify what artefact the grader inspects and where it reads that artefact from (`/shared`, the database or the sandbox). Also state whether the grader's verdict depends on state the agent can write, such as test fixtures, expected outputs, pipeline success flags in the database or files in the mount. If the grader reads from either shared surface, describe the integrity protection, such as checksums, a read-only snapshot or a separate copy. Confirm whether `environment_tampering` would be detected by anything other than the 2% weekly sample.

### E. Network isolation and environment

**9. `permitted_paths: []` vs networked NFS and Postgres; `network_isolation: on`.**
An empty `permitted_paths` means "no egress at all", yet agents reach a networked NFS server and a Postgres host. Declare those as permitted paths with `via`, `enforcement` and `agent_writable: true`, and link each surface by `via_path`. Also state whether any other host on that network segment is reachable from the sandbox, given that the NFS and database hosts sit on the internal network. A sufficient answer is the egress or packet-filter rule set for agent sandboxes.

**10. `environment: mixed`.**
State which components are live and which are digital twin. In particular, say whether `/shared` and the experiment-tracking database are the production instances used by Cobalt staff, or copies.

**11. `per_episode_reset: on` vs cross-run persistent shared surfaces.**
Writes to `/shared/rl-scratch` and to the database persist across episodes and runs, so state carries over between episodes regardless of sandbox reset. Answer three questions:

- Is `rl-scratch` wiped per episode, per run or never?
- Can a later episode, or a later run, read what an earlier episode wrote?
- Should `per_episode_reset` be declared `relaxed`?

### F. Monitoring and pause criteria

**12. `monitoring_instruments`: detection path for each pause criterion.**
The only individual-event monitor is a 2% weekly transcript sample. There is no `access_log_review`, `write_audit`, `inter_agent_message_monitor`, `environment_integrity_check` or `egress_alerting`. For each event kind listed in PC1 and PC2, name the instrument that would surface it and the expected detection latency. As one example, a write outside `/shared/rl-scratch` or into another run's database rows would only be seen if it happened to fall in the sample and appeared in the transcript text. The checker already flags PC1 as unable to observe `credential_misuse` and `privilege_escalation`. Either add instruments that can observe them (for example, NFS and Postgres audit logs reviewed on alert) or state that these events are undetectable during the run.

**13. PC3 (`inter_agent_comms`, `notify_only`).**
Inter-agent communication is structurally permitted through both shared surfaces. Explain what concretely constitutes a PC3 event, given that any read of another agent's file qualifies. Also explain what monitor would raise it, since there is no `inter_agent_message_monitor`. Say whether agents in this run can read writes by *other workloads*. If they can, cross-workload signalling is also possible, and it is not covered.

**14. Run duration vs review cadence.**
The filing gives a start window but no expected run length or number of episodes. Give the expected wall-clock duration and episode count, so that "weekly review of 2%" can be assessed. A run of 2 to 3 weeks gets 2 or 3 reviews in total.

### G. Retention and evidence

**15. `log_retention` (checker errors).**
Make these changes:

- Raise `retain_until` to at least `closeout+P12M`; the schema default is P24M.
- Add `inter_agent_messages`, meaning every write to `/shared` and to the database by agents, with author.
- Also add `tool_calls`, `access_logs` (NFS and Postgres auth/audit) and `config_snapshots` (mount, exports and database grants at each change).

Reconcile `detail.retention: P120D`, which counts from the time of writing, with `retain_until`. As filed, early trajectories could be deleted before `retain_until`. Justify `minimum_preserved_pct: 2`. If 98% of trajectories are discarded, an investigator cannot reconstruct an incident found after the fact. State whether full trajectories are kept at least for any episode that touches a path outside `rl-scratch` or writes to the database.

### H. Governance

**16. `restart_protocol` and authority.**
The `rl-lead` role currently does three things:

- signs the Intent;
- signs the safeguard relaxation;
- solely approves restarts, with no Intent amendment required and evidence limited to "a summary".

Provide:

- (a) whether `oncall` can pause without rl-lead's agreement, and whether that is written into the framework;
- (b) a restart approver independent of the run team, at least for PC1 events;
- (c) a requirement to amend the Intent when the triggering event shows that a declared surface or scope was wrong;
- (d) the evidence list for restart, for example access logs covering the event window and a re-audit of the mount and grants.

**17. `containment_plan` (omitted).**
Describe what happens on detected subversion, given that the affected surfaces are shared with other workloads. Cover three things:

- who notifies the owners of those workloads;
- whether `/shared` content written by the run is quarantined;
- whether database rows written by agents can be identified and rolled back.

### I. Capability forecast and trigger basis

**18. `forecast_basis` / `predicted_capability_band` / `trigger_basis`.**
"No capability-targeted training data" does not support `autonomy: low` and `cyber: low` for a run that RL-trains agentic code execution, filesystem exploration of real internal repositories, and database operation. Provide:

- the base Verso-2 checkpoint's most recent dangerous-capability eval results in the cyber and autonomy domains, with eval names and dates;
- the cumulative training compute of Verso-2 including this fine-tune, to show whether T1 or T2 also apply. `compute_band` appears to count the fine-tune only.
- an `eval_plan` for the post-run checkpoint, since none is filed;
- whether `investigator_scope_expansion.model_access_committed` will be set. It is omitted.
