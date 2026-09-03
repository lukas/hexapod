# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-yawboost3p0-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-03T20:25:53+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

**wandb_id**: bva17b13

**hypothesis**: Plain English: two independent mechanisms (bc_anchor_teacher_omega_boost, bc_anchor_walk_combined_skip) already tried to fix combined-tick (walk+turn) yaw authority by pushing BOTH command signs together and both left the SAME sign asymmetry (negative-wz combined beats the comparator, positive does not) -- neither mechanism can close a sign-asymmetric gap by construction. This arm is the untried candidate (ii) from STATUS item 2: the family already trains reward.k_walk_yaw=1.0 on EVERY walk tick (not zero, correcting an earlier probe_turn_authority.py docstring); a new multiplicative reward.walk_yaw_combined_boost (walk_task.py, default 1.0=bit-exact identity, tested in test_task_semantics.py test_walk_yaw_combined_boost_* and the exploit-pinning test_combined_yaw_boost_prices_symmetric_authority_over_asymmetric_exploit -- built+PASS this cycle, snapshot exp/standwalk-combined-yaw-boost-lever-09-03) scales ONLY the existing yaw-kernel income on genuine combined ticks (linear speed AND yaw rate both commanded), leaving the already-good pure-turn/straight-walk supervision untouched. Also applies STATUS item-2 rider (a): safety.max_current_a lowered from the sibling canaries' 2.9 (silently disables over_current -- above the measured 2.64A model ceiling) to 2.5. This cell: boost=3.0, seed=1.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M-step canary vs the matched control (cap29-stdwalklo-hi{,-s1}, identical recipe minus this flag): PASS if probe_turn_authority.py --vx-cmds combined-tick wz_med (vx=0.08,wz=+-0.25) on this checkpoint beats the checkpoint-scope combined comparator (cap29-stdwalklo-hi{,-s1} own combined read: +0.110/-0.171) on BOTH signs, closing (not just narrowing) the sign asymmetry (positive-side gain >= negative-side gain in relative terms), without a pure-turn or straight-walk wz regression >10% vs control, and without new terminations on a walk-only flat DR-0 proxy read; FAIL if combined wz_med is flat/worse on either sign, the asymmetry does not close, or course/direction_err_med/gait_valid regress vs control. NOTE (rider c, STATUS item 2): the whole cap29 family (incl. both combskip seeds) showed a Q3 training-reward collapse -- read the FULL reward curve, not just the final-step number, before trusting this 2M endpoint.

**verdict**: CANARY FAIL - MECHANISM (seed1, walk_yaw_combined_boost dose 3.0). Ran probe_turn_authority.py --vx-cmds vs the seed-matched control cap29-stdwalklo-hi-s1. Pure-turn wz_med regresses 18.2% (+, 0.2279->0.1864) and 28.1% (-, -0.2459->-0.1768) vs control -- both past the 10% cap. Combined-tick: positive wz_med 0.1006 does NOT clear the +0.110 comparator (barely, but fails); negative -0.1873 does beat -0.171. Same pattern as the seed0 twin and the dose-6.0 pair: whichever sign nominally improves is bought by blowing the pure-turn regression cap by 2-3x. No falls in probe. REFUTED at dose 3.0, seed 1. Evidence: logs/ckpt_eval/probe_turn_authority_yawboost3p0_s1_combined_09-03.json vs logs/ckpt_eval/probe_turn_authority_cap29_stdwalklo_hi_s1_combined_09-03.json. This closes the dose-3.0 pair (2/2 seeds FAIL) and, combined with the dose-6.0 pair (also 2/2 FAIL, see cap29-stdwalklohi-yawboost6p0{,-s1} verdicts), REFUTES candidate (ii) (reward.walk_yaw_combined_boost) at ALL 4 doses/seeds tested -- STATUS Next item 2's fallback triggers: candidate (i) (tripod_gait.py combined vx+omega foot-target geometry) is now the only remaining lever, and per that item's own prescription needs its own before/after validation harness before any GPU spend.

