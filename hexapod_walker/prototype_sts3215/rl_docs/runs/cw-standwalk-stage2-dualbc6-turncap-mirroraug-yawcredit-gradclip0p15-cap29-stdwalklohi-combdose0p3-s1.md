# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combdose0p3-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL-MECHANISM

**created**: 2026-09-03T23:43:39+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

**wandb_id**: 74lk03zl

**hypothesis**: Plain English: the yaw-arm-scale geometry lever (candidate (i)-v2) just closed 4/4 FAIL -- every dose strong enough to win the combined-tick (walk+turn) wz axis also blew the pure-turn wz-regression cap, even though the geometry itself is bit-exact on pure-turn by construction, so the RL regression must come from the SHARED dual-core policy's representation being pulled by the combined-tick BC-anchor imitation target, not the geometry. The binary combined-tick BC-anchor skip (dose 0 vs 1, no middle) is already refuted. This canary tests the untried CONTINUOUS middle, built+unit-tested this cycle: train.bc_anchor_walk_combined_dose weights (does not skip) the walk BC-anchor's imitation pull on combined ticks only, leaving pure-turn/straight-walk ticks at full weight -- default 1.0 is bit-exact legacy (114/114 test_bc_anchor.py green, including new tests pinning the weighted-loss math and the bit-exact-off contract). (dose 0.3, seed1)

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. PASS if probe_turn_authority.py --vx-cmds (full 84-key non-train cfg-set replayed, see this run family's own probe-usage gotcha) combined-tick wz_med (vx=0.08, wz=+-0.25) on this checkpoint beats its own matched control's (cap29-stdwalklo-hi{,-s1}) combined read on BOTH signs, WITHOUT a pure-turn or straight-walk wz regression >10% vs that same control, and without new terminations on a walk-only flat DR-0 proxy read; FAIL if combined wz_med is flat/worse on either sign, or the pure-turn/straight-walk regression cap is blown, or course/direction_err_med/gait_valid regress vs control. Read the FULL training-reward curve, not just the final-step number (every cap29 sibling has shown a Q3 training-reward dip/recovery shape that is not itself a fail signal). (seed1: read against the seed1 control cap29-stdwalklo-hi-s1 instead.)

**verdict**: CANARY FAIL - MECHANISM (train.bc_anchor_walk_combined_dose=0.3, seed1) -- closes the dose-0.3 arm 2/2 FAIL, matching its seed0 twin near-exactly. probe_turn_authority.py --vx-cmds, full 84-key non-train cfg-set replayed, seed-avg vs matched control cap29-stdwalklo-hi-s1 own combined_09-03 read: combined-tick (vx=0.08) wz_med WINS both signs (+0.1206 vs ctrl +0.0868 = +39.0%; -0.1533 vs ctrl -0.1369 = +12.0%), zero falls (12/12 rows) -- but pure-turn (vx=0.0) wz_med REGRESSES past the 10% cap on BOTH signs (+0.2023 vs ctrl +0.2279 = 11.2% regression; -0.1954 vs ctrl -0.2459 = 20.5% regression), and straight-walk wz drift (vx=0.08,wz=0) flips sign and grows (ctrl -0.0189 -> cand +0.0337), same pathology as seed0 (which read 12.0%/19.8% pure-turn regression and a matching sign-flip). Training reward healthy and matches the family Q3-dip/Q4-recovery shape (quarters [23.3,58.1,-91.2,136.2], final ep_rew_mean 179.6), so this is a genuine mechanism verdict, not a starved run. Why: same root cause as every prior cell in this search (geometry-lever grid + dose-0.3 seed0) -- weighting the combined-tick BC-anchor pull down still lets the SHARED dual-core representations pure-turn behavior drift once any combined-tick weight is loosened enough to win the wz axis; the seed0/seed1 numbers track each other within ~1-2pp on every axis, ruling out seed noise as the explanation. Next: dose-0.3 arm now closed 2/2 FAIL; only combdose0p6{,-s1} remain open in this grid (owned by a concurrent cycle) -- if those also fail the whole bc_anchor_walk_combined_dose axis is exhausted alongside the geometry-lever axis and the next lever must act on something neither family reaches (phase-scheduling the anchor weight WITHIN a stride, or splitting policy capacity so pure-turn gets a protected sub-path).

