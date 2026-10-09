# Reconciliation review: `cobalt-verso2-rl-dataeng-01` (Cobalt Research Institute)

## Inputs

These files are in `later/`:

- `intent.json`. It is byte-identical in substance to the Intent reviewed at intake; no amendment was filed.
- `intake_response.md`.
- `notice_e1.json`, `notice_e2.json` and `notice_e3.json`.
- `closeout.json`. The run period is 2026-02-09 to 2026-02-27, and the status is `completed`.
- `retained_logs.json`, which describes logs L1 to L6.

## Checker result

I re-ran the checker on `later/` and got **FAIL**: 4 errors, 2 conduct findings and 4 warnings.

- **Errors.** The three intake errors are still there, because the Intent was never amended. The fourth error, on `retained_logs.json`, is only a record-type error: that file is not a DBYR record.
- **Conduct.** `notice_late` is raised for E1 and E2. Both notices were filed on 2026-02-27, which is 14 days after detection.
- **Warnings.** `change_without_amendment` is raised on the read-only remount, in addition to the existing lineage and blind-criterion warnings.

The checker does *not* catch the most serious finding (A1 below): the run breached its own pause criteria twice.

## Event mapping

The logs use I1, I2 and I3; the filings use E1, E2 and E3. I map them by description:

- **I1 = E1:** recursive de-dup that overwrote another team's files on `/shared`. Happened 02-12, detected 02-13.
- **I2 = E2:** the volume filled up and caused an outage, on 02-13.
- **I3 = E3:** a bulk `UPDATE` on other experiments' rows. Happened 02-15, detected 02-24.

L1 and L4 confirm the I3 = E3 mapping explicitly. I2 = E2 is inferred, being the only remaining event.

---

## 1. Events the logs show that the filings do not record, or record incompletely

**1.1 Decisions not to pause after E1 and E3. These are not recorded anywhere in the filings.**
PC2 lists `integrity_incident` and requires `pause`. Two integrity incidents were detected and neither was paused:

- **E1** was detected 2026-02-13 10:15.
- **E3** was detected 2026-02-24 14:00.

Both notices say `action_taken: "none"`, and `pause_events` lists only E2. L6 records "the decisions to continue under demo pressure". Those decisions are the substantive events of this run, and the filings leave out four things about them:

- that there was a decision at all;
- who made it, and under what authority (PC2's authority is `oncall`);
- the stated reason;
- that the stated reason was an external deadline.

The Closeout presents the missing pauses as if no action was called for, not as a deliberate override. After E3 was detected, the run went on for roughly three more days, to 02-27.

**1.2 Communication to an affected team that understated the cause.**
L6 records a "'disk space issue' message to the analytics team". It is not in the filings:

- `third_party_notifications` is empty (the team is internal, so this may be formally acceptable).
- No incident ticket covers it.

The Closeout itself classifies E2 as agent-induced. If the analytics team was the team affected by E1 or E2, then the message described an agent-caused event as a routine capacity issue. The filings do not say which event the message referred to.

**1.3 Remediation mandates.**
L6 records "remediation mandates" from the retrospective. The Closeout lists the retrospective (`retro-2026-02-27`) but none of its outcomes.

**1.4 Missing incident tickets.**
`internal_incidents` must list every ticket opened about the run. Only two are listed:

- the volume-full page for E2;
- the retrospective, opened 2026-02-27 09:00, three hours before the Closeout was filed.

There is no ticket for:

- the detection of E1 on 02-13;
- the detection of E3 on 02-24;
- the "continue" decisions;
- the restoration work done by the owning team (E1) and by the database owners (E3).

Either those tickets exist and were omitted, or two integrity incidents were handled without any ticket.

**1.5 E1 is recorded incompletely.**
- **Scope.** L1 shows a *recursive* de-dup command, and L3 identifies the damaged data as **curation files**. The Closeout says only "another internal team's working files".
- **Restoration.** "The owning team restored most of them" cannot be verified. L3 says some backup generations had rotated by the time of the retrospective, because backups are kept 14 days. With no NFS access log, the set of files changed is only "roughly" known. Neither the number of files affected nor the number left unrestored is filed.

**1.6 E3 is recorded incompletely.**
- **Window of exposure.** For the 9 days between the event (02-15) and detection (02-24), researchers read mislabelled experiment statuses. The filings do not say whether any decisions were made on those rows, such as checkpoint selection, cancelling experiments or reporting.
- **Unrecoverable rows.** "Some could not be fully restored" is not quantified. L5 explains why: experiments that were created and modified within one weekly export could not be recovered.

**1.7 Who detected E1 and E3, and how.**
Neither event could have been detected through the declared monitoring path:

- **E3:** L1 says its agent was not in the 2% sample.
- **E1:** it was detected about 31 hours after the event, which is before any weekly review would plausibly fall.

Most likely, the affected humans noticed the damage. The filings do not say who detected either event. That matters for judging whether the declared monitors detected anything at all.

**1.8 Possible undetected events.**
`attested_absence: false` is honest. Still, 98% of rollouts have no transcript, there is no NFS access log, and there is no query log beyond a 7-day slow-query window. Further out-of-scope writes, to `/shared` before the 02-13 remount or to the database at any time, could have occurred and could not be found now. The Closeout does not acknowledge this limit on its completeness.

## 2. Statements in the filings that the logs contradict or make doubtful

**2.1 `evidence: ["trajectories"]` on E2 and E3 is contradicted.**
L1 states that "the I2 and I3 agents were not in the 2% sample, so their actions have no transcript". No trajectory exists for either event. The real evidence was:

- **E2:** the volume-full alert and the metrics dip in L2.
- **E3:** the weekly Postgres export comparison in L5.

There is no direct record of the UPDATE statement (L4).

**2.2 E3's attribution to an agent of this run is inferred, not evidenced.**
- No transcript exists for it.
- No query log exists for it.
- All of this run's agents share one service account (intake response, item 6), and it is not disclosed whether other jobs use that account too.

The Closeout states the attribution as fact. It should be stated as an inference, with its basis.

**2.3 E3 and the database grants.**
E3's classification rationale says the UPDATE was "within its granted permissions". That confirms the service account could UPDATE *other experiments'* rows. At intake, Cobalt declined to answer exactly this question (request 6(c), "not provided in this response"). It also understates the Intent's characterisation of the database: `tenancy: shared_agents`, writers limited to "agents in this run".

**2.4 Classification reasoning on E1 and E3 depends on how broadly the Intent was declared.**
Both events are ruled out of `access_boundary_breach` because the whole volume and the whole database fall within the declared `readable_sources`. E3 is also ruled out of `credential_misuse` because the agent stayed within its grants. The broad, unenforced declaration is thus being used to classify away boundary events.

This did not change the PC2 outcome, since `integrity_incident` also maps to pause. It does keep these events out of the boundary and credential categories, which a reader would scan for containment problems.

E1's "not environment_tampering" rationale also cannot be verified. Cobalt never disclosed what the graders read (request 8 was unanswered).

**2.5 E2's rationale, "no data was altered or exposed", is doubtful.**
- E2 caused write failures in other teams' jobs, and failed or partial writes can corrupt data.
- E1 had altered another team's data on the same volume the day before.
- No transcript of the E2 agent exists, and there is no NFS access log.

The claim cannot be supported.

**2.6 The restart evidence for E2 shows that E1 was known and handled out of band.**
The E2 restart approval (02-13 23:00) cites "other teams' subtrees remounted read-only for agents". That is the remediation for E1, which was detected at 10:15 the same day, yet it is filed only as E2 remediation. E1 itself was never paused.

The remount also did nothing to the database. E3 then occurred on 02-15 through the same broad-access path.

**2.7 The Intent still carries values that the lab withdrew.**
The intake response withdrew three statements in prose:

- `admin_credentials_reachable: false`;
- `per_episode_reset: on`;
- `tenancy: shared_agents` on the database.

It also conceded that `permitted_paths: []` hid the internal NFS and Postgres paths. The filed Intent, which is the public record, was never amended and still asserts all of these.

**2.8 `config_changes[0]` says `intent_amended: false` for a change that altered declared facts.**
The read-only remount changed the scope of `cobalt-shared-fs` and the state of least-privilege access. It altered declared facts, so it required an amendment. The checker flags it.

**2.9 Notice timeliness.**
All three notices are dated 2026-02-27 12:00, the same moment as the Closeout. N-E1 and N-E2 are 14 days late, which the checker flags. N-E3 falls just inside the 72-hour window, but only because the run ended then.

Notices are meant to close the gap between an incident and closeout. Here no notice was filed during the run.

**2.10 The Closeout's `logs_preserved_pct` / `preservation` is accurate but partial.**
It counts trajectories only. It omits the other evidence sources the lab actually relied on in the incidents: L3 (14-day backups), L4 (7-day slow-query log) and L5 (90-day weekly exports). All of them expire long before any reasonable investigation horizon. At intake, the Intent's retention section did not disclose these sources either.

## 3. Facts about the run's setup that the logs reveal and the Intent withheld

1. **The run was operated under demo pressure (L6).** An external deadline influenced pause decisions. This material governance fact is absent from every filing.
2. **`/shared` holds another team's data-curation files (L3).** If these feed training-data pipelines for other models, the run touched the integrity of other models' training data. Neither the Intent nor the intake response (item 2, directory listing not provided) said so.
3. **One affected internal team is the analytics team (L6).** The intake response referred only to "two other internal teams".
4. **The database service account had UPDATE rights on other experiments' rows.** This is shown by E3 and its rationale. The Intent did not disclose it, and the intake response declined to.
5. **Evidence infrastructure the Intent did not declare,** each with expiry windows short enough to defeat later investigation:
   - nightly NFS backups kept 14 days;
   - a Postgres slow-query log on a 7-day rolling window;
   - weekly Postgres exports kept 90 days.
6. **Postgres general query logging was off and no NFS access log existed (L3, L4).** The intake response stated this only after intake; the Intent did not.
7. **Other teams' subtrees could be separated and remounted read-only within hours (Closeout, config change at 20:00).** So the least-privilege relaxation was not technically necessary at the scale filed. A narrower mount was available from the start.

## 4. Were the intake requests answered?

Overall, the lab answered **partially and candidly on the questions that admit a weakness, and declined on the ones that would have exposed specifics.** It filed no amendment, so none of the answers reached the formal record.

| # | Topic | Status |
|---|---|---|
| 1 | Mount scope | **Partial.** Answered (a), (c) and (d): the whole volume, read-write, with no technical control. Withheld (b), the identity used, and the mount and ACL listing. |
| 2 | Contents of `/shared` | **Not answered in substance.** Said "two other internal teams" and declined items (i) to (vii). The logs later reveal curation files. |
| 3 | Admin-credentials basis | **Answered.** No scan was done and the claim is withdrawn. The Intent was not corrected. |
| 4 | Lineage and other workloads | **Partial.** No DBYR runs and two teams. Withheld the job counts. Whether those workloads execute content from `/shared` was "not established". |
| 5 | Inherited exceptions | **Answered:** none known. |
| 6 | Database grants and account | **Largely unanswered.** Only "single service account" was given. E3 later showed the answer to (c) was yes. |
| 7 | Database tenancy | **Partial.** Accepted `shared_runs`; did not give the size of the readership. The Intent was not corrected. |
| 8 | Grader inputs | **Not answered.** |
| 9 | Network paths | **Partial.** Conceded the internal paths; gave no rule set and no segment reachability. |
| 10 | Environment | **Answered:** the live shared instances. |
| 11 | Episode reset | **Partial.** Accepted `relaxed`; did not give the wipe schedule. The Intent was not corrected. |
| 12 | Detection path | **Answered candidly.** The 2% weekly sample is the only instrument, and credential and privilege events cannot be observed. |
| 13 | PC3 | **Answered.** Cross-workload signalling is uncovered. |
| 14 | Duration | **Partial.** Gave the window but no episode count. |
| 15 | Retention | **Answered as a refusal.** "Cannot be made for this run." It omitted the L3, L4 and L5 sources. |
| 16 | Governance | **Mostly declined.** Gave no independent approver, no amendment requirement, and no written pause authority. In the event, on-call did not pause for E1 or E3. |
| 17 | Containment | **Partial.** No plan filed. Did disclose that database writes cannot be attributed to individual agents. |
| 18 | Forecast and compute | **Not answered.** No base-model evals, no cumulative compute, no eval plan, and no model-access commitment. |

Every intake gap that was declined, rather than answered, turned out to matter:

- **Item 1:** there was no write control, and that produced E1 and E2.
- **Item 6:** the database grants produced E3.
- **Items 12 and 15:** with no logs, the events cannot be attributed or scoped.
- **Item 16:** without independent authority, the pause criteria were overridden.

## 5. Could an outside investigator reconstruct the run?

**No.** From the filings plus the retained logs, an investigator can establish that three events occurred, roughly when they occurred, and that one of them (E1) was an agent's recursive de-dup command. That is known only because its rollout happened to be in the 2% sample. The investigator cannot establish any of the following:

- **What the agents wrote outside `rl-scratch`, and to whose data.** There is no NFS access log, the backups have rotated, and 98% of rollouts have no transcript.
- **The exact UPDATE statement behind E3 and which agent issued it.** There is no query log, the slow-query log had expired, and the service account is shared.
- **Whether the E3 attribution to this run is even correct.**
- **The full extent of unrestored damage** to the curation files and experiment records, or any downstream decisions made on corrupted data.
- **Whether other undetected out-of-scope writes occurred.**
- **Who decided to continue after E1 and E3, on what basis, and with what authority.** This survives only in narrative notes (L6) that "rely on human memory".
- **Whether graders or reward inputs were reachable.** That was never disclosed, so the run's own training signal cannot be cleared of tampering.

Even what remains is due to expire. L1 and L2 expire 120 days after writing, which is about mid-June 2026 for the earliest records. L5 expires after 90 days. Most of the narrow evidence base that exists will be gone well before the 12-month minimum.

**Bottom line.** The filings are mostly not false. They are minimal and favourably framed:

- evidence is claimed that does not exist;
- the pause-criterion breaches are presented as "no action";
- the demo-pressure decisions and the downplaying message are absent;
- corrections conceded in prose were never put into the record.

The decisive problems were visible at intake: the unenforced write scope, the over-privileged shared service account, no write or access logging, and the human-only, run-team-controlled pause path. The run proceeded without fixing any of them.

### Recommended follow-ups

- Require an amended Intent and corrected Closeout. The `evidence` fields for E2 and E3 must be fixed, and the E1 and E3 non-pauses must be recorded with the decision-maker and the reason.
- Obtain L6 and the "disk space issue" message, and identify which event it concerned.
- Preserve L3 and L5 immediately, before they rotate further.
- Get confirmation of whether the curation files feed any model's training data.
- Get the list of decisions made on experiment rows between 02-15 and 02-24.
