# Backtest: hf-2026

**Derivation case.** (a) and (b) are traceability, not validation.

Schema hash: `sha256:dcd157d4878c905c5d4690ddcc36cf884950b8a98b823223e9b8d7e38e9cd997`
Reconstructed filings compliant: True

## Filer variant: diligent

| DP | (a) recorded before | (b) checkable after | (c) changes decision | why |
|---|---|---|---|---|
| DP1 | Yes | Partial | No | criterion cannot fire on an unseen event |
| DP2 | Yes | Yes | Unknown | awareness at the time not established |
| DP3 | Yes | Partial | No | criterion cannot fire on an unseen event |
| DP4 | Yes | Yes | Unknown | awareness at the time not established |
| DP5 | Yes | Yes | No | compliant: required action was taken and restart approved |
| DP6 | Yes | Yes | Unknown | obligation is to record, not to act |

v0.2 intake review of the reconstructed Intents: intent:A: comms_unmonitored, dead_criterion, shared_surface_floor; intent:B: comms_unmonitored, dead_criterion, shared_surface_floor

Attributable on 6 of 6; passes the held-out criterion (needs 3).

## Filer variant: as_believed

| DP | (a) recorded before | (b) checkable after | (c) changes decision | why |
|---|---|---|---|---|
| DP1 | No | Partial | No | criterion cannot fire on an unseen event |
| DP2 | Yes | Yes | Unknown | awareness at the time not established |
| DP3 | No | Partial | No | criterion cannot fire on an unseen event |
| DP4 | Yes | Yes | Unknown | awareness at the time not established |
| DP5 | Yes | Yes | No | compliant: required action was taken and restart approved |
| DP6 | Yes | Yes | Unknown | obligation is to record, not to act |

v0.2 intake review of the reconstructed Intents: intent:A: core_kind_uncovered, dead_criterion; intent:B: core_kind_uncovered, dead_criterion

Attributable on 4 of 6; passes the held-out criterion (needs 3).
