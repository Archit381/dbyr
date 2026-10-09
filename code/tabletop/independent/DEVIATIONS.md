# Deviations from the pre-registered protocol

1. **S1 filer did not complete (round 1).** The S1 scenario is a cyber-capability
   evaluation. The filer instance was stopped by a safety classifier while reading
   the schemas, before writing any filing. We did not reword the task and retry,
   since that would be an attempt to route around a safety control. S1 is
   therefore unscored in round 1, and round 1 has two scenarios (S2, S3), not
   three. A human red team (the authors' team) could play S1; that is listed as
   future work rather than done here.

2. **Material-fact flags hidden from the filer.** The protocol says the filer sees
   "one scenario's setup". We passed the setup facts without the scenario
   writer's `material` flags, so the filer could not target exactly the facts the
   judge scores. This is a narrowing of what the filer sees, not a widening.

3. **Scenario gaps filled by the filer.** Some scenarios do not state values the
   schema requires (for example compute band, trigger basis). The S2 filer chose
   values and flagged them in its private log. The judge is told to treat such
   values as neither true nor false of the scenario.

4. **Evaluator log view leaked scenario content (round 1).** The staged
   `retained_logs.json` kept the scenario header (including `run_type`) and the
   scenario writer's log summaries, some of which name an event the lab never
   detected (S2 I3). Reconciliation credit in round 1, especially for S2 I3 and
   S3's run type, is partly inflated by this. Round 2 strips the header and passes
   only the log entries.

5. **Judge summary saved by the coordinator.** The round-1 judge's harness refused
   to let it write `summary.md`; it returned the full text, which is saved
   as `round1/judge/summary.md`, verbatim except that the ranked rule-change
   list was condensed from bullets to prose without changing its content. The per-scenario sheets were written
   by the judge directly.

6. **Intake requests answered (round 2, added before round 2 ran).** In round 1,
   `caught_intake` meant only that the evaluator asked; the lab never answered.
   In round 2 the filer receives the evaluator's intake requests and responds in
   character (truthfully, minimally), by text and/or an amended Intent. The
   judge scores the pre-registered categories unchanged and adds **M3b**: of the
   facts scored `caught_intake`, the share the lab's response disclosed fully.
   This is an addition, not a change to M1-M6.

7. **Round-2 prompts saved.** Round-1 prompts were not kept. Round-2 prompts are
   committed in `round2/prompts/` before any agent ran, and were sent verbatim.
   Roles work in folders outside the repository holding only their own inputs
   and a copy of the frozen v0.3 checker (hash in `FREEZE.txt`).

8. **Truthful Intents that cannot pass (round 2, S5 and S6).** Both filers
   stopped rather than file a false statement: the runs as described lack the
   monitoring and retention v0.3 requires, so no true Intent passes. The
   protocol assumes a lodged filing passes the checker. We continued with each
   failing Intent treated as *submitted, not accepted*: it goes to intake with
   its checker errors visible, and phases A2 and B proceed, so intake,
   reconciliation and event capture can still be scored. The judge is told the
   Intent was not lodgeable under v0.3. Decided before the evaluators saw any
   filing.

9. **Round-2 judge restarted.** The first round-2 judge instance was cut off by a
   session interruption after making counterfactual probes (a scratch folder per
   probe, across S4-S6) and before writing any score sheet or summary. Its partial folder was set aside unread by the coordinator
   (`judge_attempt1_interrupted`, outside the repository) and a fresh judge was
   started with the same verbatim prompt. Before the restart the coordinator
   checked that the sealed scenarios still match `SEALED.sha256`, that the
   repository copies of all filings, private logs and evaluator reviews are
   byte-identical to the role workspaces, and that each role's checker reports
   the frozen v0.3 hash.
