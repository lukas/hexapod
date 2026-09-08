# Scratch s0 matched 10M charge comparison

Both arms retain the corrected source's behavior; this panel does **not demonstrate a clean continued-charge benefit**. This is an evidence artifact, not a ledger verdict, launch, or walking/joystick qualification.

Read at 2026-09-08 03:25:48 UTC using native authenticated `eval_report` and `get_run`. Both gate paths were exact literal matches, without a fallback selection notice. Full provenance, configurations, criteria and measured values are in [comparison.json](comparison.json).

## Original criteria

The launch gate, unchanged in historical commit `eb095e34d`, required each arm to retain **at least 21/24 gait-valid episodes, no new falls and no new chronic leg sacrifice** relative to the corrected 2M source. Charge benefit additionally required better held-out leg use/gait **without command-progress or slip regression**. Equal outcomes do not establish continued-charge advantage. The gate explicitly grants **no automatic further budget, new seed or final walking/joystick qualification**. The verbatim gate is preserved in the JSON.

## Exact gate measurements

Each group has six episodes; progress and slip are group medians. The fixed panel has 24 episodes total.

| Group | Gait on / off | Terms on / off | Progress on / off | Slip per m on / off |
|---|---:|---:|---:|---:|
| walk/det | 6 / 5 | 0 / 0 | 0.9215 / 0.9230 | 9.6965 / 8.4485 |
| walk/sto | 6 / 6 | 0 / 0 | 0.9625 / 1.0210 | 7.8900 / 6.8205 |
| startjitter/det | 6 / 6 | 0 / 0 | 0.9890 / 1.0165 | 9.6525 / 9.0940 |
| startjitter/sto | 4 / 4 | 0 / 0 | 0.6480 / 0.6755 | 12.6555 / 12.7170 |

Totals: **on 22/24, off 21/24, source 21/24; zero gate terminations for all three**. No new sacrificed episode/leg appears in either arm. The source, on, and off all retain startjitter/sto episode 2's leg-5 sacrifice and episode 3's leg-0 sacrifice (indices start at zero).

The only gait flip is **walk/det episode 0, leg 5**:

| Metric | Corrected 2M source | Charge on | Charge off |
|---|---:|---:|---:|
| Rounded leg-5 duty | 0.09 | 0.11 | 0.07 |
| Gait valid | false | true | false |
| Progress ratio | 0.286 | 0.269 | 0.284 |
| Slip per m | 21.359 | 22.466 | 19.606 |

The evaluator's sacrificed-leg threshold is duty below 0.10, or duty above 0.95 with zero swings; printed duty is rounded. The additional gait-valid result is a narrow threshold crossing accompanied by worse command progress and slip in that episode. Across groups, on has lower median progress in four of four and higher median slip in three of four. These are descriptive fixed-panel differences, not a significance claim.

## Matching and limits

- The 82 launch configuration keys differ only in `reward.walk_leg_duty_ratio_charge=150` versus `0`. Other flag differences are run output name and notes. Training RNG is the existing seed 2; both launch code hashes are `78e18bb1408fc061bc817917bcd2a3f43001da86`.
- Both start from source MD5 `2156daae67933cd1bc1a66accf422edb`, already trained through the corrected 2M active-charge stage. This is continued charge versus withdrawal after shared exposure, **not a fresh or never-exposed initialization**.
- Endpoint checkpoints each contain 10,485,760 steps and 4,469,269 bytes. Root verified off MD5 `ce8e200539e0e67d22b0fe3b22757f69` and on MD5 `5c6b4932a0ff5ecd7559fab0d91394e7`.
- All 24 corresponding reported randomization and reset-start-jitter records match exactly; every episode starts in `plant`. The same fields match the source. Gate seed 0, model `mesh_mjx_twin` (4.80573 kg), 100 Hz motor contract, std 0.135 and jitter-panel settings also match.
- Recovery used standard `ops.sh podeval` on retained evaluator code. It rendered legacy 100 Hz video; root changed no evaluation physics, flags or RNG. Reports do not carry a full effective configuration dump or evaluator code hash, so byte-identical evaluation runtimes are not established. No new video inspection is claimed here.

## Continuation interpretation

Both meet the original **numeric retention** criteria. The stronger preregistered charge-benefit conjunction is not met: the one gait gain comes with measured command/slip costs.

There is **no automatic continuation** under the original gate. A separately preregistered bounded paired duration study could test whether this small leg-use gain broadens without those costs, using equal budgets, the existing initialization/RNG and explicit progress/slip tolerances and stop criteria. That would be a new question, not exploitation of a proven reward improvement. Retain both endpoints and do not compare raw returns across their different reward scales.
