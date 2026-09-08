# cw-walkscratch-easy0905-widen8-jointspace-freshinit-halfdr2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T14:58:35+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: 5w1uwrd1

**hypothesis**: Plain English: the 3-arm single-axis DR knockout (bad_start/fault/push each removed alone) all failed to ignite fresh-init walking on the widen8 full-DR composite, confirming DR breadth itself (not one named axis) is the ignition blocker. This tests the OTHER licensed branch: does UNIFORMLY HALVING every DR axis's magnitude/probability (not removing any axis, just shrinking all of them together -- sensor noise, mass/friction/gain jitter, bad_start/fault/push probabilities and severities all x0.5, ranges compressed toward their center) let a fresh-init policy ignite walking where the full-strength composite could not?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: PASS if majority gait_valid (>=13/24 pooled or >=3/4 modes) AND net forward speed >=0.03 m/s median AND 0 new falls vs the offctrl baseline -- licenses a 40M follow-up + a matched dose ladder back up toward full strength. FAIL (still flat/thrashing, slip 8-142/m, near-zero net speed matching the closed fingerprint) rules out this dose as sufficient and licenses the quarter-strength sibling (this cycle's other arm) as the next rung down.

**verdict**: CANARY FAIL - MECHANISM: halving every DR axis's magnitude/probability together does NOT ignite fresh-init walking -- reproduces the closed 4/4 thrash-in-place fingerprint at a lower dose, not a PASS. Pooled naive numbers look borderline (gait_valid 13/24, pooled speed_mean_m_s median 0.039 m/s, just clears the 0.03 floor) but that clearance is an artifact of walk/sto skating: sto-mode slip_per_m is 88-244/m (worse than the full-strength composite's own 69-74/m fingerprint) while along_dist_m (net progress toward the commanded heading) stays ~0 in every mode (pooled median 0.004m over a ~20s episode; walk/det median 0.001m) and wrong_direction_frac sits at ~42-49% (coin-flip, no directional control) in all four groups. Contact-sheet frame strips for walk/det/0 and walk/sto/4 show the body stationary across all 6 sampled frames in each clip -- legs cycling/skating without net translation, not gaited locomotion. This matches the concurrently-landed nodiscrete2m sibling's own closed-fingerprint numbers (det slip 58-80/m, fwd med 0.01-0.02m, gait_valid 6/6 despite zero net movement) almost exactly, so the half-dose point on this ladder is FAIL, same class as the 3-arm axis-knockout trio. Licenses the quarter-strength sibling (quarterdr2m, already launched) as the next rung down per the pre-registered gate text; do not fund a 40M follow-up on this half-dose config. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_widen8_jointspace_freshinit_halfdr2m_gate/report.json; W&B 5w1uwrd1.

