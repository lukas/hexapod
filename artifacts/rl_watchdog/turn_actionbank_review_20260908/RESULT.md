# Reviewed frozen action-response bank — completed

Result receipt 2026-09-08T06:55:07.258912+00:00. Controller full replay took 71.42 s; 4 continuous baselines and 296 branches (8 zero controls + 288 pulses). No PPO, plant regeneration, core edit, Git mutation or healthy-job stop.

**The original finite-pulse negative is supported.** Zero of 288 pulses reaches the unchanged 0.005 rad commanded-direction yaw gain. Maximum original observed gain is 0.0040968585769 rad; the additional true-endpoint maximum is 0.0041121956115 rad. This does not establish sustained control or close coordinated, longer, closed-loop or learned action classes. No conditional canary is justified by this bank.

All 296 branches match the completed owner bank exactly in original observed yaw, the original yaw/XY/pad-XY/contact trace hash, and final qpos. All 8 zero controls additionally match full MuJoCo integration state, registered episode/controller history, recurrent policy state and observation at prefix and endpoint; all 288 pulses match complete prefix state. All zero checks passed before pulse execution.

All 288 pulses pass the explicitly post-review corrected retention screen: complete 80-tick window, positive baseline progress, body-frame forward integral ≥0.9× baseline, loaded material-contact distance ≤1.25× baseline, each relative-tilt maximum ≤baseline +3°, no termination and all ticks in walk. The original proxy screen also passes 288/288. No numerical threshold was changed. Forward ratios span 0.9281–1.0305; material-slip distance ratios 0.9607–1.0847; mean material-slip speed ratios 0.9601–1.0769. Slip screening is total distance, so speed and loaded-foot time remain separately reported. Pulse loaded-foot times span 2.662–2.724 foot-seconds; baseline times 2.672–2.716. No action-bound clip hits occurred.

The original owner source was reconciled before interpretation: completed ed15d1c6... already used pitch_deg and checked final qpos, unlike the earlier draft snapshot. Those initial draft criticisms do not apply to its completed run. The review corrects relative-pitch extrema/fail-closed missing metrics, body-command progress and loaded material contact slip, and extends state parity. Private endpoint reads were verified not to alter live MuJoCo solver state.

The first reviewed attempt stopped in baseline capture before any branches because the history serializer lacked collections.deque support. The narrow fix serializes ordered deque values and maxlen; six focused tests pass. Its failure log is preserved. One subsequent complete bank succeeded with exit 0, retaining original-bank parity checks.

## Exact baseline windows

| wz | start | P | observed yaw rad | body forward m | material slip m | material speed m/s |
|---:|---:|---:|---:|---:|---:|---:|
| +0.15 | 0.000 | 600 | +0.027808 | 0.023290 | 0.041497 | 0.015484 |
| +0.15 | 0.000 | 638 | +0.033214 | 0.023963 | 0.040498 | 0.015145 |
| +0.15 | 3.142 | 600 | +0.028845 | 0.024847 | 0.043393 | 0.016240 |
| +0.15 | 3.142 | 638 | +0.029526 | 0.023384 | 0.042450 | 0.015840 |
| -0.15 | 0.000 | 600 | -0.031842 | 0.024663 | 0.045001 | 0.016605 |
| -0.15 | 0.000 | 638 | -0.026125 | 0.024104 | 0.045983 | 0.016930 |
| -0.15 | 3.142 | 600 | -0.026097 | 0.023161 | 0.046083 | 0.017093 |
| -0.15 | 3.142 | 638 | -0.032002 | 0.025099 | 0.045656 | 0.016897 |

Actual registered P1/P2 remain 600/638 with about 3.18348 rad phase separation. All inputs remain checkpoint 61f9c20f..., frozen XML 7efb8e8a..., full mesh 34 meshes/159 geoms/4.80573 kg, 100 Hz, 400/20/.375°/350 counts/s, exact 64-key cfg, seed 0 / DR 0, vx .08 and wz ±.15, original 1 s hold +1 s ramp, starts 0/π. Phase clock 1.333333 Hz corresponds to 0.7500001875 s; 75 followup ticks are the nearest 100 Hz representation.

## Preserved artifacts

- `full/bank.json`: reviewed raw result, SHA256 `c922b54761c3e2969540c8f6c57b16a502fff45db2e6fd5a5c4da5beea98766b` (local and controller copies verified).
- `owner_bank.json`: unchanged completed owner result for exact comparator provenance.
- `review_summary.json` and `branch_retention_comparison.json`: explicit original versus corrected screens and baseline measurements.
- `controller_preflight.json`: original copied-source check, exact frozen input hashes and five-helper AST equality across main/owner/execution worktrees.
- `controller_run.log`, `controller_initial_serializer_failure.log`, `review_manifest.json`: execution/repair receipts and file hashes.
- Final executed runner SHA256 `436b0eee695094f94d68346548e12efed147f087b1447ea2349b0f4feb67cd54`; sealed cfg SHA256 `aabf4cc25f78ebf3b28ff7b4a46fba85c109f4061becaf4212e8842b5c550e40`.
