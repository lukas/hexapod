# cw-walkscratch-easy0905-widen8-jointspace-freshinit-halfdr2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T14:58:35+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: 5w1uwrd1

**hypothesis**: Plain English: the 3-arm single-axis DR knockout (bad_start/fault/push each removed alone) all failed to ignite fresh-init walking on the widen8 full-DR composite, confirming DR breadth itself (not one named axis) is the ignition blocker. This tests the OTHER licensed branch: does UNIFORMLY HALVING every DR axis's magnitude/probability (not removing any axis, just shrinking all of them together -- sensor noise, mass/friction/gain jitter, bad_start/fault/push probabilities and severities all x0.5, ranges compressed toward their center) let a fresh-init policy ignite walking where the full-strength composite could not?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: PASS if majority gait_valid (>=13/24 pooled or >=3/4 modes) AND net forward speed >=0.03 m/s median AND 0 new falls vs the offctrl baseline -- licenses a 40M follow-up + a matched dose ladder back up toward full strength. FAIL (still flat/thrashing, slip 8-142/m, near-zero net speed matching the closed fingerprint) rules out this dose as sufficient and licenses the quarter-strength sibling (this cycle's other arm) as the next rung down.

