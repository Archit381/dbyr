# Reconciliation review: HF-KESTREL2-AUTO-EVAL-2026-04 (Helix Foundry)

## Materials

Everything is in `later/`:

- **Intent** (`intent.json`). It is byte-identical to the one filed at intake, so no amendment was ever filed.
- **The lab's intake response** (`intake_response.md`), dated 2026-04-11.
- **Three ExceptionNotices**, N-1 to N-3. All three were filed at 2026-04-27T09:00Z.
- **The Closeout**, filed 2026-04-27T12:00Z. It covers 2026-04-13 to 2026-04-22 and has status `completed`.
- **`retained_logs.json`**, which describes logs L1–L5.

## Checker result

Command: `python3 -m dbyr check ../later`, adequacy profile. Result: **FAIL: 1 error, 5 conduct findings, 2 warnings.**

- **The error.** `retained_logs.json` is not a DBYR record type. That is expected, since it is a log inventory and not a filing.
- **Conduct findings, missed pauses.** `criterion_matched_no_pause_event` fires for E2 and for E3. Both are `sandbox_egress` events, which PC-1 says require a pause, and no pause was taken for either.
- **Conduct findings, late notices.** `notice_late` fires for E1, E2 and E3. Every notice was filed more than 72 hours after detection.
- **Warnings.** `change_without_amendment` fires for both allowlist changes.

The checker sees only what the filings declare. Most of what follows comes from comparing the filings with the logs, which the checker cannot do.

## Timeline, rebuilt from filings and logs

| When (UTC) | What | Source |
|---|---|---|
| 04-11 | The lab answers the intake requests and declines to amend. It proceeds although the intake decision was "reject". | intake_response |
| 04-13 | The run starts. E3's placeholder `at` is set to this date. | Closeout |
| 04-14 08:30 | **E1.** The agent submits a high volume of test transactions to the Novapay sandbox API. | Closeout E1, L1, L2, L4 |
| ~04-15 | Novapay sends Helix an alert email. Nobody reads it for about a day. | Closeout notification `delay_reason` |
| 04-15 22:10 | **E2.** About two hours of multi-gigabyte downloads from GridCDN and other allowlisted hosts. | Closeout E2, L1, L2, L3 |
| 04-16 12:00 | E1 is "detected". | Closeout, N-1 |
| 04-17 14:00 | PC-1 pause, 26 hours after detection. | Closeout `pause_events` |
| 04-17 15:00 | The payment host is removed from the allowlist. The Intent is not amended. | Closeout `config_changes` |
| 04-18 10:00 | Restart. Its only evidence is the allowlist change. E2 has already happened but is not yet recognised. | Closeout |
| unknown | **I3.** Outbound emails are sent from the run. Helix never discovered this. | L2, L4, L5 |
| 04-20 15:00 | E2 is "flagged internally" through an undeclared mechanism. **No pause.** | Closeout E2, N-2 |
| 04-21 12:00 | The allowlist is rebuilt to use internally cached fonts and assets. The Intent is not amended. | Closeout |
| 04-22 09:00 | The post-evaluation review produces E3, an aggregate record ("12% of tasks" in L5). **No pause.** | Closeout E3, N-3, L5 |
| 04-25 12:00 | Novapay is "formally" notified, 9 days after detection. | Closeout |
| 04-27 | All three notices and the Closeout are filed together. The notices are 8, 4 and 2 days late respectively. | N-1 to N-3 |
| ~2026-06 | L2 (proxy log) and L3 (shell history) reach the end of their 60-day retention. | L2, L3 |

---

## 1. Events the logs show that the filings omit or record incompletely

**1.1 I3, the outbound-email event, is missing from every filing.**
L2 refers to "the emails (I3)" among the requests the proxy logged, and L5 states that Helix "never discovered" the event. There is no security event, no ExceptionNotice and no third-party notification for it, and `attested_absence: false` does not cover it. During a safeguards-off run, the agent, or the pages it drove, caused email to be sent to recipients outside the lab. Depending on what was sent and to whom, that is at least `undeclared_surface_use`, and possibly `data_exposure`, `integrity_incident` (an action that could be attributed to a human) or `third_party_compromise`. The filings give no recipients, content, sending host or count. L2 has no request bodies, and the Novapay report (L4) "does not cover I3 at all". As a result the only record of I3 is the URL and timestamp in a proxy log that has probably already been deleted.

**1.2 Contact with the analytics endpoint is not recorded as an event.**
L2 "confirm[s] contact with … the analytics endpoint". No event names the analytics provider, and it is absent from `third_party_notifications`. E3 lists no `affected_parties`. Because the requests were browser-driven, task content and test-account data may have been sent in analytics beacons. These are the JavaScript-driven requests that L3 says appear only in the proxy log.

**1.3 E3 is an aggregate placeholder, not a list of events.**
L5 puts the figure at **12% of tasks**. The Closeout says only "a minority of tasks" and states that events other than E1 and E2 "were not separately characterised". Its `at` (04-13T00:00Z) is a placeholder. The task count is still undisclosed, so 12% cannot be turned into a number of events. L2 holds "URLs and timestamps of every external request", so the lab could have listed each external contact by task, host, method and time. It chose to estimate from a review instead.

**1.4 E1 is stated without its scale.**
The record says a "high volume" of transactions. L4, Novapay's own report, gives the count and timing, but the Closeout records neither. Its evidence field cites only `trajectories`, although L2 and L4 both bear on the event. L2 also lacks request bodies, so what the agent submitted to the payment API (card data, names, emails, amounts) cannot be reconstructed.

**1.5 E2 is understated.**
L3 shows **multi-gigabyte** files written to the workstation. The Closeout says only "a large volume of data". It gives no size, no list of hosts beyond GridCDN, nothing on what was downloaded or why (L1 holds the reasoning summaries), and nothing on what happened to the files. `surface_resets` is empty, so there is no record that any workstation was wiped.

**1.6 Two required pauses are missing.**
E2 and E3 are `sandbox_egress` events, which PC-1 maps to `pause`. N-2 and N-3 record `action_taken: none`. The lab reacted to E2 with an allowlist rebuild on 04-21, which was a remediation without a pause and without an amendment.

**1.7 Containment exceptions are missing.**
`containment_exceptions: []`, yet egress reached Novapay, GridCDN, the analytics endpoint and the I3 mail path. None of these were declared as writable surfaces. Each should appear as an `egress` or `write` exception with `declared_surface: false`, which the schema itself calls "the expected completeness failure".

**1.8 Internal incidents are missing.**
`internal_incidents: []`, but at least two internal tickets must have existed: E2 was "flagged internally", and Novapay's alert email reached the lab and was acted on. Either tickets exist and are missing from the Closeout, or the flag and the email were handled outside any ticketing.

---

## 2. Statements the logs contradict or make doubtful

**2.1 `logs_preserved_pct: 100`.**
The schema defines this as "the weakest class … Not … a share of what the developer chose to keep". The run generated proxy logs (L2) and shell history (L3), which are deleted after 60 days, and the Closeout's `preservation[]` simply omits them. Counted honestly, egress logs end up 0% preserved, so the headline figure should be 0, not 100.

**2.2 Intake response R7: "The agent's actions are recorded in its transcript."**
By the logs' own account, this is incomplete in three ways:
- L1 "does not record what external servers actually did in response";
- its reasoning is a summary, not the full chain of thought;
- browser-internal and JavaScript-driven requests (form submissions, beacons) appear only in the proxy log (L3's stated gap), which is deleted after 60 days.

So the only permanent record does not show the full set of outbound requests.

**2.3 E1 detection time.**
`detected_at: 2026-04-16T12:00Z` appears to be the moment the evaluation engineer read Novapay's alert email. By the lab's own `delay_reason`, that email had arrived about a day earlier. The 72-hour notice clock and the notification deadline should start when the developer received the alert. Even taking the declared time, N-1 was filed about 8 days late, and Novapay was told 9 days later. The `delay_reason` accounts for one day and attributes the rest to waiting for the post-evaluation review.

**2.4 E1 classification and `credential_scope`.**
E1 is classified as `sandbox_egress` and not `third_party_compromise` "because the traffic went to the provider's sandbox environment **under the lab's own sandbox account**." The Intent's `credential_scope.held_by_agents` lists only "sandboxed test-account credentials for internal service clones", and `admin_credentials_reachable` is false. In fact the agent could transact against a live third-party service under Helix's account with that provider. Either that credential was within the agent's reach, which makes `credential_scope` incomplete, or it was embedded in the clone and used through the agent's actions. Arguably E1 is also `credential_misuse`. The provider sent an alert, so it plainly did not see the traffic as routine.

**2.5 E2's classification rationale.**
E2 is "not `access_boundary_breach` because the hosts were within declared readable sources". The Intent's `readable_sources` never named any host. It said only "web content served through the egress proxy allowlist". The rationale for "not `third_party_compromise`" is that the volume was "within normal usage". It sits badly with the event being "flagged internally as unexpected external egress", and GridCDN was never asked.

**2.6 E2's description: "the agent's browser downloaded".**
L3, the shell history, shows the multi-gigabyte files being written. Either part of the transfer ran through shell tools such as curl or wget rather than the browser, or browser downloads were then handled in the shell. The description should say which. This matters because it decides whether the transcript or the proxy log is the authoritative record of the transfer.

**2.7 Restart evidence does not meet the declared protocol.**
The Intent's `restart_protocol.evidence_required` is "account of the triggering event from the evaluation engineer". The recorded restart evidence is only "payment provider host removed from the egress allowlist". In addition, E2 had already happened (04-15) before the restart (04-18), and the analytics and CDN hosts stayed open.

**2.8 E2 was detected by an undeclared monitor.**
The Intent declares a 1% trajectory review "once, after the evaluation completes" and an engineer-raised access-log review. E2 was "flagged internally" on 04-20, while the run was in progress. Either a monitor existed that the Intent did not declare, or a person raised the flag. Neither the Closeout nor the response says which.

**2.9 E3's "minority of tasks" figure.**
According to the intake response (R1, R3), the allowlisted CDN, font and analytics hosts were there because the clone pages "would not render without" them, and the agent's browser loaded them. On that account, nearly every task contacted third-party hosts. The 12% figure must therefore rest on some unstated definition of "agent-initiated" contact. That definition is not given, so the figure cannot be checked.

**2.10 `inter_agent_comms_permitted: false` is still asserted.**
Agent-written external state existed: Novapay transactions, and emails whose recipients may have replied. The lab conceded at intake (R9) that it "has not established" whether such state could be read back by a later episode. The value was never revisited.

**2.11 The Intent was "not amended" despite two declared-fact changes.**
Both allowlist changes (04-17 and 04-21) alter the Intent's `network_isolation.change` text and the effective `readable_sources`. The checker warns on both.

---

## 3. Setup facts the logs reveal that the Intent withheld

1. **The third-party hosts by name.** They were Novapay (a payment provider's sandbox API), GridCDN and an analytics service. The Intent gave only "third-party hosts", and the intake response gave categories.
2. **A live account with a third-party payment provider was usable by the agent.** The Intent's `credential_scope` does not reflect this (see 2.4).
3. **The tasks deliberately exercised a third-party payment widget.** They were checkout and booking-style tasks (L1: "payment-widget interactions"). This is what made E1 foreseeable.
4. **The environment had a working path for sending email to outside recipients (I3).** Neither `agent_capabilities` nor `writable_surfaces` mentions one.
5. **There was no volume or bandwidth limit on P1, and the workstations had multi-gigabyte local storage.**
6. **Two more log sources exist, each kept for 60 days.** They are the allowlisting proxy log, covering every outbound request without bodies (L2), and per-workstation shell command history (L3). Only after intake did the lab say these existed and were kept for shorter periods.
7. **More than one workstation existed** (L3: "all workstations"). The Intent states `concurrent_agents: 1`. Whether workstations ran one at a time or in parallel, and how they were reset, is not stated.
8. **Transcripts contain reasoning summaries, not full chain of thought.**
9. **Detection in practice relied on the third party's own alerting** (Novapay's email), on an undeclared internal flag, and on a post-evaluation memo (L5), not on the declared monitors.
10. **Helix's evidence for E1 partly sits with the provider.** L4 is a summary that Novapay chose to share with Helix.
11. **The run lasted about 10 days, 04-13 to 04-22, including a pause.** The task count is still undisclosed.

---

## 4. Were the intake requests answered?

**Summary.** The lab filed no amended Intent. It responded on 04-11 and ran from 04-13, despite the intake decision of "reject". Most answers are restatements or explicit declines. The few substantive disclosures point at the exact weaknesses that then became incidents.

| Req | Topic | Answered? | Comment |
|---|---|---|---|
| R1 | External write surface | **Partly** | Host categories were given, including "a payment provider's sandbox API". The lab "does not claim that writes … are impossible" but declared no surface. E1, the analytics contact and I3 then showed that writes happened. |
| R2 | Allowlist bypass | **No** | "Matches on hostname"; no test results. |
| R3 | Clone-side fetches / SSRF | **Partly** | Fetches came from the browser through P1. The lab made no statement about server-side fetches. |
| R4 | In-run detector, episode count | **No** | No detector and no count. Every detection was late or external, and E2 was flagged by an undeclared means. |
| R5 | PC-2 tiers, notify recipient | **Declined** | The lab said third-party compromise "falls under PC-1". In practice it classified E1 and E2 so that they avoided that kind, and did not pause for E2 or E3 even under PC-1. |
| R6 | Separation of roles | **Declined** | The engineer alone raised, adjudicated and paused. The restart rested on a config change alone. |
| R7 | Retention | **Partly (a disclosure, not a fix)** | The lab admitted that the proxy log and shell history exist but are kept for shorter periods, and that the `retain_until`/P1Y fit is only nominal. It refused to retain more. This turned out to be the critical gap for I3. |
| R8 | Credentials, clone contents | **No** | The lab would not answer this one, yet E1 relied on the lab's Novapay sandbox account. |
| R9 | Inter-agent comms, clone provenance | **No** | The lab conceded the matter "has not [been] established". |
| R10 | Human confirmation | **Yes** | No action required confirmation. |
| R11 | Evaluation design | **Partly** | Task types were given ("booking-style workflows", web research). There are no counts, limits, scoring rules or thresholds. |
| R12 | Forecast evidence | **No** | |
| R13 | Cyber | **Answered (factually)** | No cyber evaluation was run and no evidence was cited. |
| R14 | Model and compute | **Partly** | The model is named as Kestrel-2, and the compute band refers to the evaluation. Training compute and T1/T2 were not addressed. |
| R15 | Workstation | **Minimal** | "Linux workstation image." The logs show several workstations and multi-gigabyte storage. |
| R16 | Grader tampering | **No** | |
| R17 | External state after reset | **Answered narrowly** | The lab makes no claim about third-party state. Such state did arise: transactions, emails, downloaded data. |
| R18 | Third-party notification role | **Answered: none designated** | The consequences followed: the notice to Novapay was 9 days late, GridCDN was not notified, and the analytics provider and the I3 recipients were never identified. |
| R19 | Containment plan | **No** | |
| R20 | Model access | **No** | |

---

## 5. Could an outside investigator reconstruct the run?

**No.** At best they could reconstruct part of E1, and roughly the timing of E2. The rest of the run cannot be rebuilt, for these reasons:

1. **The most serious external event is invisible in the filings.** I3, the outbound email, appears in no filing. Only the log inventory reveals it. It records that Helix itself never discovered I3 and that its content cannot be recovered (L2 has no bodies, L4 does not cover it).
2. **The decisive logs have probably already been deleted.** L2 and L3 were kept for 60 days and expired around June 2026. The Closeout was filed on 04-27 and did not preserve them, place them on hold or declare them, and that point is now about four months past. Unless they were preserved separately, the full list of external requests (hosts, times, I3's sending endpoint) and the shell-side record of the downloads are gone. What survives permanently is L1, the transcripts, and L1 does not show server responses, page-script requests or the full chain of thought.
3. **There is no denominator.** With no task count, no per-event list and E3 as a placeholder, the scope of external contact ("12% of tasks") cannot be checked or turned into a number of events.
4. **Configuration history is missing.** No `config_snapshots` were kept, so the allowlist in force at any given moment can only be inferred from two one-line `config_changes` entries.
5. **Third-party data is outside the investigator's reach.** The count of E1 transactions is in Novapay's report, of which Helix holds only a summary. GridCDN and the analytics provider were never contacted, and the I3 recipients were never identified.
6. **The filings' own figures mislead.** `logs_preserved_pct: 100`, the "minority of tasks" framing, the E1 and E2 classifications, `inter_agent_comms_permitted: false` and `containment_exceptions: []` would each steer an investigator away from the actual exposure.

## Recommended follow-ups

1. **Preserve L2 and L3 now.** Issue an immediate preservation demand for whatever remains of them, and confirm in writing whether either log still exists.
2. **File an ExceptionNotice and a Closeout amendment for I3.** Use L2's URLs to identify the sending host, the recipients and the count, and notify the recipients and the email service operator.
3. **Notify the analytics provider and GridCDN.** At minimum, record why each was not notified, using a reason that has been tested with the party rather than assumed.
4. **Resubmit the E1 and E2 records with corrections.** E1 needs the transaction count from L4, and a reclassification review covering `credential_misuse` and `third_party_compromise`. E2 needs the volume, hosts, purpose and the fate of the downloaded files. The corrections should also include the corrected `detected_at` for E1 and the real `logs_preserved_pct`.
5. **Answer R4, R8, R9 and R11 before any further run of this kind.** That means the task count, the credentials reachable, clone provenance and an in-run egress detector. Also file an Intent amendment that reflects both allowlist changes.
