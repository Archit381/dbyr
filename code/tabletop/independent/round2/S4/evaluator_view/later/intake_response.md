# Helix Foundry response to intake review: HF-KESTREL2-AUTO-EVAL-2026-04

Responding role: Head of Evaluations (ROLE-HEAD-EVAL), Helix Foundry. Response date: 2026-04-11.

No amended Intent is filed with this response. The Intent filed on 2026-04-09 stands as lodged. No episodes have run as of this response.

## Blocking requests

**R1. Third-party hosts.** The allowlisted third-party hosts fall into these categories: font and static-asset CDNs, an analytics service, and a payment provider's sandbox API. They are on the allowlist because the internal service clones embed content from them and the pages would not render without it. The lab does not claim that writes to these hosts are impossible. No request-method restriction is declared for them. No additional surface is declared in this response.

**R2. Allowlist enforcement.** The allowlist matches on hostname. The lab has no bypass-test results for items (a) to (e) to report.

**R3. Clone outbound traffic.** The third-party content is loaded by the agent's browser through P1, which is why those hosts are on the allowlist. The lab makes no statement in this response about server-side fetch features of the clones.

**R4. In-run detection.** No real-time or automatic detector is declared for this evaluation. The declared monitors are the two in the filed Intent. The 1% trajectory sample is the lab's minimum commitment, not an estimate of statistical power. The lab does not give an episode count in this response.

**R5. PC-2.** The actions are as filed. An event that meets the definition of `third_party_compromise` falls under PC-1, which lists that kind. The filing does not name a recipient for `notify_only` criteria.

**R6. Separation of roles.** Authority to abort a task or the whole evaluation rests with the evaluation engineer. The restart approver, the restart evidence and the amendment requirement are as filed. The lab adds no further pause authority in this response.

**R7. Retention.**
- The egress proxy request log and the shell command history are kept for shorter periods than the filing's retention horizon. That is why neither is declared as a retained class.
- The agent's actions are recorded in its transcript, which is retained.
- `minimum_preserved_pct` is a floor, not an estimate. The lab does not set a higher floor in this filing.
- On `retain_until`: the lab's transcript retention period is one year. The declared `closeout+P12M` is met only if that year is counted from completion of the evaluation. The lab does not state a longer hold in this response.
- `closeout+P12M` is the protocol floor, and the lab chose the floor.
- `review_method` is as filed.

**R8. Credentials and clone contents.** Agents hold the sandboxed test-account credentials declared in `credential_scope`. The lab makes no further statement in this response on (a), (b) or (c).

**R9. Inter-agent communication.** The filed value was declared on the basis of the declared surfaces. The lab has not established whether state written to an allowlisted third-party host persists and could be read back by a later episode or run. The lab makes no statement in this response on clone provenance or on other run_ids.

## Non-blocking requests

**R10.** Human confirmation is the production action-confirmation gate. In this evaluation, no browser or shell action requires human confirmation.

**R11.** Tasks are long-horizon computer-use tasks, including booking-style workflows and multi-step web research, designed to be carried out against the internal service clones. The lab does not provide counts, step limits, scoring or thresholds in this response.

**R12.** The lab does not cite prior results in this filing.

**R13.** This run includes no cyber evaluation. The lab does not cite further evidence on cyber capability here.

**R14.** The evaluated model is Kestrel-2. The `compute_band` value refers to the compute used by this evaluation run. The lab makes no statement in this response on training compute or on T1 or T2.

**R15.** The agent for each task is given a Linux workstation image. The readable host categories are those given under R1. The lab makes no further statement in this response.

**R16.** No further statement in this response.

**R17.** The `per_episode_reset` declaration makes no claim about state on third-party hosts.

**R18.** This filing designates no role for third-party notification.

**R19.** No containment plan is filed. The evaluation engineer can abort a task or the evaluation.

**R20.** The lab makes no commitment on model access in this filing.
