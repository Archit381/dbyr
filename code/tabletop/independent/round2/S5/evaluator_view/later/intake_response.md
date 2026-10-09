# Cobalt Research Institute: response to intake review of `cobalt-verso2-rl-dataeng-01`

## Status

No amended Intent is filed. The run configuration is fixed. Cobalt cannot truthfully clear the three blocking errors:

- **privilege_escalation:** no declared instrument observes it.
- **inter_agent_messages:** not collected.
- **Retention:** sampled transcripts are kept for 120 days.

Any amendment would therefore still fail the checker. We answer here in text only.

Cobalt also corrects two values in the filed Intent, under items 3 and 11.

Where an item says "Not provided in this response", Cobalt is not answering that point here. It is not a statement that the thing is absent.

## A. Shared filesystem

**1. Mount scope.**
- (a) The whole `/shared` volume is mounted read-write into agent sandboxes.
- (b) Not provided in this response.
- (c) There is no technical control that prevents writes outside `/shared/rl-scratch`. The prompt instruction is the only control. The declared writable surface `cobalt-shared-fs` is therefore the whole volume.
- (d) The broader mount lets agents explore realistic repositories.
- Mount table and export/ACL listing: not provided in this response.

**2. Contents of `/shared`.**
- Besides `rl-scratch`, the volume holds working data belonging to two other internal teams.
- An itemised directory listing and yes/no answers to items (i) to (vii): not provided in this response.

**3. `admin_credentials_reachable: false`.**
- This value was not established by a secret scan, and no scan is cited.
- Cobalt withdraws reliance on it. Cobalt cannot attest that no admin credentials are reachable from the mount.

## B. Other workloads and lineage

**4. Other workloads.**
- Cobalt identifies no other DBYR-filed run that reaches either surface during the start window.
- The non-DBYR users of `/shared` are the two internal teams named in item 2.
- Job counts: not provided in this response.
- Whether those workloads execute content read from `/shared` has not been established.

**5. Inherited exceptions.** Cobalt is aware of no open containment exception on `cobalt-shared-fs` or `cobalt-exp-tracking-db`.

## C. Experiment-tracking database

**6. Agent access to the database.**
- Agents read from the database and write results to it.
- All agents in the run use a single service account.
- Items (a) and (c) to (e), and whether other jobs use the same account: not provided in this response.

**7. Tenancy.**
- The database is a shared experiment-tracking database. Cobalt accepts `shared_runs` as the better classification.
- No external reader is identified.
- Size of the human readership: not provided in this response.

## D. Reward and grading

**8. Grader inputs.**
- Grader inputs and integrity protections for each task family: not provided in this response.
- Nothing other than the sampled transcript review is declared that would detect `environment_tampering`. Aggregate training metrics are also collected, but they observe no individual event.

## E. Network and environment

**9. Network paths.**
- Network egress from agent sandboxes is blocked.
- Agents do reach the NFS server and the Postgres host over the internal network. `permitted_paths: []` described egress only, not these internal paths.
- Enforcement mechanism, packet-filter rule set, and reachability of other hosts on the segment: not provided in this response.

**10. Environment.** `/shared` and the experiment-tracking database are the live shared instances, not copies. "Mixed" referred to sandboxed agent execution against live shared storage.

**11. Episode reset.**
- `rl-scratch` wipe schedule: not provided in this response.
- Writes to `/shared` and to the database persist, and later episodes can read them.
- Cobalt accepts that `per_episode_reset` should be declared `relaxed`.

## F. Monitoring and pause criteria

**12. Detection path.**
- For every event kind in PC1 and PC2, the only individual-event instrument is the 2% transcript sample, reviewed weekly. Detection latency is up to one review cycle, and only if the event falls in the sample.
- Two exceptions are visible without a monitor: `agent_induced_outage` through operations, and `third_party_compromise` through external report.
- `credential_misuse` and `privilege_escalation` are not observable by any declared instrument during the run.
- No NFS access log is collected, and Postgres keeps no general query log.

**13. PC3.**
- A PC3 event is an agent acting on content that another agent wrote, as seen in a reviewed transcript.
- No dedicated monitor exists. Detection relies on the transcript sample.
- Agents can read data written by other workloads on `/shared`, and cross-workload signalling is not covered by PC3.

**14. Duration.**
- The run is expected to fall within the declared window of 2026-02-09 to 2026-03-02, which allows two to three weekly reviews.
- Episode count: not provided in this response.

## G. Retention

**15. Retention.**
- These changes cannot be made for this run. Per-write records with author, access logs and tool-call logs beyond the sampled transcripts are not collected.
- The retention period is 120 days from writing, so early transcripts may expire about three months after closeout.
- `minimum_preserved_pct: 2` equals the transcript sample rate.
- Full trajectories are not kept for episodes that touch paths outside `rl-scratch` or that write to the database. No mechanism exists to select those episodes.

## H. Governance

**16. Authority.**
- (a) The on-call engineer can pause the run. Written status: not provided in this response.
- (b) No restart approver outside the run team is designated.
- (c) No such amendment requirement is committed.
- (d) The evidence list is as filed. Access logs for the event window cannot be supplied because they are not collected.

**17. Containment.**
- No containment plan is filed.
- Incident response is coordinated through an on-call rotation shared with the broader training organisation.
- Quarantine of `/shared` content: not provided in this response.
- Agent database writes are made under one service account, so the database cannot attribute rows to individual agents.

## I. Forecast and triggers

**18. Forecast, compute and evals.**
- `compute_band` covers this fine-tune only.
- Cumulative Verso-2 compute and the base checkpoint's eval results: not provided in this response.
- No eval plan is filed for this run.
- `model_access_committed` is not committed in this filing.
