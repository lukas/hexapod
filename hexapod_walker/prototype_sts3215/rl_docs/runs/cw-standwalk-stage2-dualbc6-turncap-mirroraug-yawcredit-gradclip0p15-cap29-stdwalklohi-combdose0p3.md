# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combdose0p3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-03T23:38:10+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

**wandb_id**: g47lpaq6

**hypothesis**: Plain English: the yaw-arm-scale geometry lever (candidate (i)-v2) just closed 4/4 FAIL -- every dose strong enough to win the combined-tick (walk+turn) wz axis also blew the pure-turn wz-regression cap, even though the geometry itself is bit-exact on pure-turn by construction, so the RL regression must come from the SHARED dual-core policy's representation being pulled by the combined-tick BC-anchor imitation target, not the geometry. The binary combined-tick BC-anchor skip (dose 0 vs 1, no middle) is already refuted. This canary tests the untried CONTINUOUS middle, built+unit-tested this cycle: train.bc_anchor_walk_combined_dose weights (does not skip) the walk BC-anchor's imitation pull on combined ticks only, leaving pure-turn/straight-walk ticks at full weight -- default 1.0 is bit-exact legacy (114/114 test_bc_anchor.py green, including new tests pinning the weighted-loss math and the bit-exact-off contract). (dose 0.3, seed0)

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. PASS if probe_turn_authority.py --vx-cmds (full 84-key non-train cfg-set replayed, see this run family's own probe-usage gotcha) combined-tick wz_med (vx=0.08, wz=+-0.25) on this checkpoint beats its own matched control's (cap29-stdwalklo-hi{,-s1}) combined read on BOTH signs, WITHOUT a pure-turn or straight-walk wz regression >10% vs that same control, and without new terminations on a walk-only flat DR-0 proxy read; FAIL if combined wz_med is flat/worse on either sign, or the pure-turn/straight-walk regression cap is blown, or course/direction_err_med/gait_valid regress vs control. Read the FULL training-reward curve, not just the final-step number (every cap29 sibling has shown a Q3 training-reward dip/recovery shape that is not itself a fail signal).

**verdict**: CANARY FAIL - MECHANISM (train.bc_anchor_walk_combined_dose=0.3, seed0). probe_turn_authority.py --vx-cmds, full 84-key non-train cfg-set replayed, seed-avg vs matched control cap29-stdwalklo-hi's own combined_09-03 read: combined-tick (vx=0.08) wz_med WINS both signs (+0.1313 vs ctrl +0.1101 = +19.3%; -0.1854 vs ctrl -0.1701 = +9.0%), zero falls (12/12 rows) -- but pure-turn (vx=0.0) wz_med REGRESSES on both signs past the 10% cap (+0.1964 vs ctrl +0.2230 = 12.0% regression; -0.2005 vs ctrl -0.2501 = 19.8% regression), and straight-walk wz drift (vx=0.08,wz=0) flips sign and grows in magnitude (+0.0295 vs ctrl -0.0408). Training reward healthy (quarters [23.4, 70.4, -81.3, 145.6], final ep_rew_mean 264.7, the family's known Q3-dip/Q4-recovery shape, not a collapse) so this is a genuine mechanism verdict, not a starved run. Why: weighting the walk BC-anchor's imitation pull DOWN on combined ticks only (dose<1.0) still lets the shared dual-core representation's pure-turn behavior drift once ANY combined-tick weight is loosened enough to win the wz axis -- same root cause already identified across the geometry-lever grid (yaw-arm-scale + both omega-boost directions): the regression traces to the SHARED representation, not to whichever knob is being turned. Next: read the sibling cells (combdose0p3-s1, combdose0p6{,-s1} -- another cycle's scope) the same way; if they also fail, the bc_anchor_walk_combined_dose axis is exhausted alongside the geometry-lever axis and the next lever must act on something neither family reaches (phase-scheduling the anchor weight WITHIN a stride, or splitting policy capacity so pure-turn gets a protected sub-path).

