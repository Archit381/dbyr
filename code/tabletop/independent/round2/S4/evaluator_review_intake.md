# Intake review: HF-KESTREL2-AUTO-EVAL-2026-04 (Helix Foundry)

Reviewed: `intake/intent.json` (filed 2026-04-09T16:00Z) and `intake/checker_output.txt`. I re-ran the checker (`python3 -m dbyr check ../intake`, adequacy profile). It reports `ok 0 errors, 0 conduct, 0 warnings`. The filing is well-formed, but the checker only tests form. It cannot tell whether the declared topology matches the environment the fields describe, and that is where the problems are.

## 1. Decision: reject (refile before the run starts)

This is a safeguards-off (T4) agentic autonomy evaluation. The agent has a shell, Python and a headless browser. Human confirmation of its actions is switched off, and its egress allowlist knowingly includes **live third-party hosts** (`network_isolation: relaxed`, "the allowlist includes third-party hosts that the internal service clones load content from"). The path to those hosts is declared `agent_writable: true`. Read together, the filing describes an unattended agent that can send arbitrary requests to systems Helix Foundry does not own. Four things about that setup fall short:

1. **The external write surface is undeclared.** The only declared writable surface is `SURF-CLONES` (`tenancy: run_only`, `persistence: ephemeral`). The third-party hosts reachable through P1 are not declared as a surface at all, though they would be `tenancy: external` and almost certainly not ephemeral. Because they are left out, `inter_agent_comms_permitted: false` and `shared_surface_lineage: []` are asserted without being shown. A write to an external host can be read back by a later episode or another run.
2. **Nothing can detect a pause event while the run is going.** The monitors are (a) a 1% trajectory sample reviewed *once, after the evaluation completes*, and (b) an egress-log review that only the evaluation engineer can trigger, by request. There is no `egress_alerting`, `write_audit` or `environment_integrity_check`, and nothing runs in real time or automatically. PC-1 ("pause" on `sandbox_egress` / `third_party_compromise`) can in practice only fire after the run has ended. The same goes for the 72-hour ExceptionNotice clock, which starts at detection.
3. **The most likely harms only trigger a notification.** `remote_code_execution`, `agent_induced_outage`, `credential_misuse`, `data_exposure`, `access_boundary_breach`, `undeclared_surface_use` and `environment_tampering` are all `notify_only`. Every pause and notify decision rests with one role (ROLE-EVAL-ENG). That same role is the only source of alerts, and the report goes to that role's own chain.
4. **The evidence an investigator would need is not kept.** Only `trajectories` are retained, and `minimum_preserved_pct` is 0. The egress proxy request log is the data source for the only network monitor, yet it is not a retained class. Nor are `tool_calls`, `access_logs` or `config_snapshots`, the last of which would show allowlist changes. After any third-party incident, an outside investigator could not reconstruct which external hosts were contacted, with which methods and payloads, or under which allowlist version.

Requests 1–9 are blocking. Requests 10–20 should be answered in the refiled Intent but would not by themselves block acceptance.

Note on timing: `filed_at` is 2026-04-09 and the start window is 2026-04-13 to 2026-05-14. If any episodes have already run, the lab should say so in the refiling, along with the dates. Any such episodes ran under the monitoring and retention described here and should be covered in the Closeout.

## 2. Requests for information

### Blocking

**R1. `egress_topology.writable_surfaces`: the third-party hosts are missing.**
P1 is `agent_writable: true` and reaches third-party hosts, but the only writable surface declared is SURF-CLONES. The lab should either:
(a) declare an additional surface (or surfaces) for the third-party hosts, with `tenancy: external`, an honest `persistence` value and `via_path: P1`, and state by category which kinds of host they are (for example CDN or static assets, fonts, analytics or telemetry, auth/SSO/OAuth providers, maps or payment APIs, object storage, user-content hosts, package registries); or
(b) show that writes are impossible: state the proxy rule that limits third-party hosts to GET/HEAD with no request body, and say whether it is enforced at the proxy for every protocol, including WebSockets and HTTP CONNECT tunnels.
It is not enough to say the hosts are "only used for loading content". The agent has a shell and can make any request the proxy allows.

**R2. `permitted_paths[P1].enforcement: proxy_allowlist` (hostname-based): how it can be bypassed.**
The lab should state:
(a) whether the allowlist matches on the full hostname or on a wildcard suffix (for example `*.cloudfront.net` or `*.googleapis.com`). A wildcard reaches any tenant on that provider, which makes it an unrestricted write channel;
(b) whether it checks SNI, the Host header or both, and whether domain fronting is blocked;
(c) whether any allowlisted host follows open redirects or proxies arbitrary URLs;
(d) whether the agent workstation resolves DNS itself. If it does, DNS is a second egress path and should be declared as P2;
(e) whether any traffic other than HTTP(S) can leave the workstation.
A short table of rule type, enforcement point and the bypass tested, with a yes/no result for each, would resolve this.

**R3. The clones' own outbound traffic (possible SSRF relay).**
The clones "load content from" third-party hosts, and the agent can write to the clones. The lab should state whether the clones' outbound requests pass through the same P1 allowlist or through a separate path. It should also state whether the agent can make a clone fetch a URL it chooses (for example an avatar URL, webhook, import or preview feature). If a clone has its own egress, declare it as a permitted path and give its enforcement.

**R4. `monitoring_instruments`: at least one in-run, automatic detector for the pause-criterion events.**
The pause criteria are currently unreachable during the run. The lab should name a monitor that sees **every** request from the agent (and from the clones on the agent's behalf) to a host outside the clone set, in real time. Examples: `egress_alerting` with `coverage: all` on the proxy log, or a `write_audit` that alerts on any request with a body or a non-GET method to a third-party host. For that monitor, give the `alert_source` (a rule, not a person), who receives the alert, and the time from alert to pause. Separately, the lab should explain why a 1% sample is a meaningful `trajectory_review`. That requires the expected number of episodes; see R11. With one concurrent agent over a month, 1% may mean a single transcript, or none.

**R5. `pause_criteria` PC-2: why the listed events are `notify_only`.**
For each of `remote_code_execution`, `agent_induced_outage`, `credential_misuse` and `data_exposure`, the lab should state either (a) why continuing the run is acceptable once one has been detected, or (b) that it moves the event to `pause` or `pause_and_review`. If any of these events affects a third party, it is a `third_party_compromise` in substance. The lab should say whether PC-1 applies in that case or whether the PC-2 label decides. It should also state who a "notify" goes to, since the notifying role and the authority role are the same.

**R6. `pause_criteria.authority_role` and `restart_protocol`: separation of roles.**
At present ROLE-EVAL-ENG raises the alerts, adjudicates them and decides whether to pause. ROLE-HEAD-EVAL signed the safeguard relaxation, approves restarts and signs the Intent. The only evidence a restart needs is the evaluation engineer's own account of the event, and `intent_amendment_required: false` lets the run resume after a confirmed sandbox egress with the same allowlist. The lab should:
(a) name a role outside the evaluation chain (security or incident response) that can pause and must agree to any restart after a PC-1 event;
(b) require a restart after a PC-1 event to include an allowlist or topology fix and an Intent amendment, or explain why not;
(c) add logs as restart evidence: the proxy log entries and the episode transcript in full.

**R7. `log_retention`: keep the evidence the monitors themselves use.**
The lab should add `egress_logs` (the full proxy request log, including method, host, path, size and status for every request, from both the agent and the clones), `tool_calls` and `config_snapshots` (each version of the allowlist and clone configuration, with timestamps). For each, give `coverage` and `retention`. It should also:
- set `minimum_preserved_pct` to a real floor or explain why it is 0. It currently contradicts `trajectories: coverage complete`;
- reconcile `retain_until: closeout+P12M` with `retention: P1Y`. P1Y is counted from the time of writing, so transcripts from April 2026 could expire before closeout+12 months. It also falls short of the closeout+P24M default; explain the shorter period;
- replace `review_method` ("made available on request") with an actual review method that says who reviews what, and when.

**R8. `credential_scope` and the clone contents.**
`held_by_agents` lists only test-account credentials and `admin_credentials_reachable` is false. The lab should state:
(a) whether the clones, or the agent workstation, hold any API keys, tokens or service-account credentials for the **live third-party services** they load content from (for example map or analytics keys embedded in pages or config), and whether the agent can read them;
(b) whether the clones' backend or database credentials can be reached from the agent's shell (for example through environment variables, mounted config or a metadata endpoint);
(c) what data the clones are seeded with. Is it synthetic, or a copy or subset of production or employee data? `data_exposure` is currently `notify_only`, so this matters.

**R9. `inter_agent_comms_permitted: false` and `shared_surface_lineage: []`.**
The schema treats the comms flag as a statement of fact about the environment. The lab should confirm it still holds given that (a) episodes run one after another, and an episode could write to an allowlisted external host and a later episode, or a later run, could read it back; and (b) SURF-CLONES is described as "internal service clones". Are clones created fresh for each episode from a fixed image, or do they persist as shared staging instances that other runs or teams also use? The lab should state where each clone instance comes from and how it is reset, and say whether any other run_id uses the same clone images or the same allowlist.

### Non-blocking (answer in the refiling)

**R10. `safeguards_disabled.relaxed: "human confirmation of agent actions"`: what changed.**
This does not map to any of the six checklist items. The lab should describe the production control it replaces: which actions currently need confirmation (network writes, form submissions, code execution, purchases?) and who confirms them. It should also say whether any action class still needs confirmation in this run. If none does, say so explicitly.

**R11. `eval_plan` / E-AUTONOMY-1: what the evaluation consists of.**
The lab should give: the number of tasks and episodes; the maximum steps or wall-clock time per episode; the task families (for example resource acquisition, self-exfiltration or replication proxies, long-horizon software tasks, web interaction with the clones); whether any task asks the agent to interact with, sign up to or post to a third-party service; how success is scored; and the threshold that would put autonomy at "high". The lab should also say what follows if "high" is observed partway through: halt, amend or continue?

**R12. `forecast_basis`: the forecast is circular.**
"This evaluation is the measurement of the autonomy forecast" gives no prior evidence. The lab should cite the results that support "medium": earlier Kestrel or Kestrel-2 checkpoints, benchmark scores, or prior runs by ID.

**R13. `predicted_capability_band.cyber: low` with no cyber evaluation.**
The run gives a safeguards-off agent a shell and live reachability to third-party hosts, and it lists `remote_code_execution` and `privilege_escalation` among its own event kinds. The lab should give its evidence that cyber capability is "low". Without that evidence, it should add a cyber evaluation to `eval_plan` or justify why exposure to live hosts is acceptable while cyber capability is unmeasured.

**R14. Model identity and `compute_band: <1e24`.**
The lab should name the evaluated checkpoint (model and version) and state whether `<1e24` is the compute for the evaluation itself or the training compute of the evaluated model. If the model's training compute is in a higher band, or the developer has covered status, the lab should explain why `trigger_basis` is only T4 and not also T1 or T2.

**R15. `agent_capabilities` / `readable_sources`: "the agent's own workstation environment".**
The lab should state whether the workstation is a fresh VM or container per episode and whether it has persistent storage. It should say whether the agent can reach model weights, inference endpoints (including its own), internal source code, cloud metadata or other internal networks from it. It should also say whether package installs (pip, npm, apt) are possible and through which allowlisted registries. Registries can carry writes or exfiltration, and a registry would be a `package_proxy` surface. "Web content served through the egress proxy allowlist" is not an enumeration of readable sources; give the host categories, as in R1.

**R16. The `evaluation harness` reads SURF-CLONES: risk of grader tampering.**
The harness reads what the agent writes. The lab should state whether grading depends on clone state that the agent can change, and what stops the agent from writing to that state directly to pass (`environment_tampering` is currently `notify_only` with no integrity monitor). An `environment_integrity_check` instrument, or a description of how the grader is isolated, would resolve this.

**R17. `per_episode_reset: on` and the external state.**
The lab should confirm that the reset covers the workstation and the clones, and say what it does about state the agent created on external hosts (accounts, uploads, posts, scheduled jobs). If external state is not cleaned up, list it as residual state in the surface declaration.

**R18. Third-party notification responsibility (roles).**
Neither declared role handles external notification or security response. The lab should name the role (title and organisation) that would notify affected third-party operators, decides who counts as affected, and files the ExceptionNotice within 72 hours. It should also give the contact channel (restricted tier).

**R19. `containment_plan` is missing (an optional field).**
For a run with live external reachability, the lab should state what happens on detected subversion (for example revoking the proxy credential, killing the workstation, snapshotting the clone) and the conditions for taking the environment fully offline.

**R20. `investigator_scope_expansion.model_access_committed` is omitted.**
For an autonomy evaluation run with safeguards off, the lab should state whether a post-incident investigator would get query access to the exact evaluated checkpoint and scaffold, and if not, why not.
