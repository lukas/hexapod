# walkcurr-rlonly-slew-smooth-s0-50hz — GO/NO-GO (2026-09-21 packaging cycle)

## Verdict: GO for simulation/export readiness as the walkcurr 50Hz walk-role hardware-transfer REFERENCE, superseding `bundle_rlonly_v2`'s own crutchoff-s0-warmadapt-acq1 candidate. NOT a physical-acceptance verdict.

One plain sentence: `walkcurr/STATUS.md`'s 2026-09-21 ~03:3x entry
promoted `cw-walk50hz-slew-smooth-s0` after confirming its one open
caution (duty-cycle/torque-margin at the raised slew cap) reads CLEAN,
and this cycle packages that promotion into the same transfer-manifest
format the parent bundle uses, plus re-verifies the two sub-bundle
options (rot60 full-heading wrap, composed rise+hold->walk handoff)
that were built against the now-superseded checkpoint.

## Why this cycle did this (gap it closes)

The promotion cycle itself named the gap plainly: "`bundle_rlonly_v2`'s
`transfer_manifest.json` and the `rot60_fullcircle/` sub-bundle still
point at the superseded `crutchoff-s0-warmadapt-acq1` checkpoint/export
— repackaging onto `slew-smooth-s0` ... is the next concrete,
agent-doable, CPU-only step — not done yet." With 13 free GPU slots,
an empty backlog, and every other track's own latest STATUS
independently closed pending Robot Lab or a new structural design
(surveyed via `ops.sh board`), this cycle did that packaging work.

## What shipped this cycle

1. **`rl_move/sim/cfg_recipe_walk50hz_slew_smooth_s0.py`** (+5 tests):
   versioned `--cfg-set` recipe for this checkpoint, verbatim from
   `ops.sh entry cw-walk50hz-slew-smooth-s0`, mirroring the sibling
   `cfg_recipe_walk50hz_rlonly_v2.py` module 1:1.
2. **`--walk-recipe` flag on `eval_lifecycle_handoff_rlonly.py`**
   (default `rlonly_v2` = bit-exact old behavior; new `slew_smooth_s0`
   choice) so the lifecycle-composition tool can build `env_walk` from
   either walk role's own real cfg contract.
3. **Exported the np policy**: `linux_control/policies/
   walkscratch_walk50hz_slew_smooth_s0.json`, parity 2.18e-07 (bar
   1e-5), validated via `rl_move.np_policy validate`.
4. **Re-ran the rot60 sustained-multiheading gate** (same panel
   `rot60_fullcircle`'s own `matched_trained_contract_speed_check`
   used) against this checkpoint: 16/16 gait_valid, 0/16 falls across
   all 4 DR-0 panels.
5. **Re-ran the composed lifecycle full-heading panel** (same
   8-heading x2-episode baseline/candidate structure
   `bundle_rlonly_lifecycle_v1`'s 2026-09-20 update used): baseline
   (rot60 off) 11/16 direct gait_valid (fails h+-90/h135/h-135, same
   pathology CLASS as the superseded checkpoint); candidate (rot60 on)
   16/16, 0 falls either arm. Re-rendered `drive.mp4`/
   `drive_h90_rot60.mp4` under `bundle_rlonly_lifecycle_v1/
   slewsmooth_s0/`.
6. **Wrote this manifest** collecting the checkpoint's own DR-0 gate
   numbers (already cached, matched-current-model-verified), the rot60
   panel, and the composed-lifecycle panel in one decision-ready place,
   same format as the parent bundle.

## TODAY bars (same rubric bundle_rlonly_v2 uses)

- Clean `rl_only` training lineage: PASS — plain warm-start of an
  already-clean lineage, no demonstration data, no scripted role.
- Reproducible non-interactive sim evidence: PASS — DR-0 gate (n=6/mode
  x4), rot60 sustained panel (n=4/mode x4), composed-lifecycle
  full-heading panel (n=2/heading x8 x2 arms) all committed.
- Video: PASS — `drive.mp4` (forward) + `drive_h90_rot60.mp4`
  (full-direction headline arm), both re-rendered fresh this cycle.
- Off-forward chronic leg-sacrifice limitation: PRESENT (same class as
  parent), OPTION available (rot60 wrap, validated through both the
  isolated walk role and the composed rise+hold->walk handoff).
- Duty-cycle/torque-margin at the raised slew cap: PASS (checked CLEAN
  the same cycle this checkpoint was promoted; matched-current-model
  control vs the champion).
- Physical acceptance: NOT CLAIMED — sim-only, no robot access.

Evidence: `transfer_manifest.json` (this directory);
`logs/ckpt_eval/cw_walk50hz_slew_smooth_s0_gate/report.json`;
`logs/ckpt_eval/cw_walk50hz_slew_smooth_s0_rot60_sectorstop60s_speed006/report.json`;
`logs/ckpt_eval/lifecycle_rot60_fullheading_panel_slewsmooth_20260921/`;
`rl_docs/tracks/walkcurr/bundle_rlonly_v2/rot60_fullcircle/GO_NOGO.md`
(2026-09-21 update); `rl_docs/tracks/walkcurr/bundle_rlonly_lifecycle_v1/GO_NOGO.md`
(2026-09-21 update).
