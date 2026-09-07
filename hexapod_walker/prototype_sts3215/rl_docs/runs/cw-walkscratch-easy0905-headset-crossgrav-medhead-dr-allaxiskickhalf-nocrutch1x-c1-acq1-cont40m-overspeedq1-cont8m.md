# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1-cont8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T16:25:21+00:00

**pod**: hexapod-mjx-train-0

**steps**: 8000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1

**wandb_id**: 403dz6fy

**hypothesis**: Plain English: the 2M overspeed-charge canary shows the mechanism is genuinely ACTIVE (not inert) -- per-tick reward_walk_freeprog_pen sits at -1.3..-1.4, LARGER in magnitude than reward_walk income itself (0.83-0.98), and terminations/tilt_roll crashed 93->25->11->10 across the 2M window (the policy is stabilizing under it, not entrenching a new exploit) -- but prog_ratio only softened slightly (1.6-2.1 parent -> 1.4-1.76 here, not reaching the <=1.35 mechanism-works bar) and slip/m stayed flat-to-worse in every mode (4.93-6.24 vs parent's 4.98-5.42), so the overspeed-financed-slip question is UNRESOLVED, not falsified, at this dose/budget: a penalty that already dominates income should eventually move an entrenched fast-skate habit, but 2M steps of continued PPO from a checkpoint already deeply committed to 1.7-2x overspeed may simply be too little horizon to escape that local optimum. This is an 8M same-recipe continuation (sole change: budget only, k_over=1.0 unchanged) to give the dominant charge enough steps to actually move v_along_cmd_m_s (flat at 0.083-0.084 across the whole 2M canary) before judging the slip hypothesis.

**gate**: CONTINUE if prog_ratio med moves meaningfully toward <=1.35 in >=2/4 modes AND v_along_cmd_m_s trends below 0.075 by the run's end (from the canary's flat 0.083-0.084) -- then read slip: <=3.9 confirms overspeed-financed slip, >=4.5 falsifies it (genuine gait-style floor, close the axis). FAIL-MECHANISM if terminations/tilt_roll or any other termination class rises back up, gv drops <18/24, or reward per-tick components (env/reward_walk) collapse to near-zero/negative (would mean the charge is now suppressing walking itself, not just excess speed). INCONCLUSIVE-KEEP-GOING (relaunch once more with 2x budget) if v_along_cmd_m_s is still flat/unmoved but termination counts keep dropping and reward_walk keeps rising (still adapting, just slower than one 8M step).

