# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combskip-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-03T16:33:07+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

**wandb_id**: 203b2exr

**hypothesis**: Seed-1 twin of cap29-stdwalklohi-combskip: same combined-tick BC-anchor-skip lever (train.bc_anchor_walk_combined_skip=1.0) on the seed-1 cap29-stdwalklo-hi-s1 control, to check the mechanism's effect is seed-robust and not a seed0 fluke.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same PASS/FAIL bar as the seed0 twin, read against the seed1 control (cap29-stdwalklo-hi-s1) instead.

**verdict**: CANARY FAIL - MECHANISM (seed1 twin of the combskip seed0 canary — same verdict). Ran probe_turn_authority.py --vx-cmds on this checkpoint plus the matched control cap29-stdwalklo-hi-s1, identical probe cfg. Pure-turn wz_med: this ckpt +0.205/-0.187 vs control +0.228/-0.246 -> regression 10.2% (+) / 23.9% (-), both at/over the pre-registered 10% cap. Combined-tick (vx=0.08) wz_med: this ckpt +0.110/-0.185 vs the pre-registered comparator (yawdensity_canary_s1) +0.145/-0.107 -> negative side beats it hugely (+73% magnitude) but positive side stays WORSE than the comparator, same sign-asymmetric pattern as seed0. Per the pre-registered gate (PASS needs both signs to beat the comparator AND <=10% pure-turn regression vs control), this fails on the regression clause, reproducing seed0's result 2/2 seeds. Side note: the control cap29-stdwalklo-hi-s1 itself fell/terminated on the zero-command (wz=0,vx=0) probe cell while this combskip checkpoint did not -- not a new termination introduced by the treatment, so it doesn't change the verdict. Next: branch (a) (tripod_gait.py combined vx+omega foot-target geometry fix) is now the sole remaining candidate per standwalk STATUS Next item 2; the combined-tick BC-anchor-skip mechanism is refuted 2/2 seeds, do not retry it alone. Evidence: logs/ckpt_eval/probe_turn_authority_combskip_s1_combined_09-03.json, probe_turn_authority_cap29_stdwalklo_hi_s1_combined_09-03.json.

