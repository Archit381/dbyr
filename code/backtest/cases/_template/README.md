# Held-out case template

Copy this folder to `cases/<case-name>/` for each held-out incident (pre-registered:
Anthropic, 30 Jul 2026; UK AISI, 4 Aug 2026). The protocol is in paper Section 5.5.

1. **Freeze the schema first.** Run `python -m dbyr freeze` and publish the hash
   before anyone reconstructs filings for the case. At scoring time the hash in
   `results.json` must match the published one; if it does not, the result is void.
2. **Reconstruct filings** from public sources only: one `intent_*.json` per run,
   one `closeout_*.json` per run that ended or re-attested. Record the provenance
   of every value in `sources.json` as first-party, forced-choice or placeholder.
   Placeholders must never appear in a predicate.
3. **Extract decision points** from the developer's account *and* any third-party
   account, into `decision_points.json` (same format as `cases/hf-2026`). Set
   `"is_derivation_case": false`.
4. **Score independently.** The person who writes `decision_points.json` must not
   have drafted the schema. Run:

   ```
   python -m backtest.score backtest/cases/<case-name>
   ```

5. **Read the verdict.** The case fails the protocol if, on fewer than half of its
   decision points, a field satisfies both (a) recorded before and (b) checkable
   after. Report both filer variants.

The negative arm (safeguards-off runs with no incident) uses the same tooling:
reconstruct the Intent, then count how many pause criteria would have fired on
benign events to measure burden and false triggers.
