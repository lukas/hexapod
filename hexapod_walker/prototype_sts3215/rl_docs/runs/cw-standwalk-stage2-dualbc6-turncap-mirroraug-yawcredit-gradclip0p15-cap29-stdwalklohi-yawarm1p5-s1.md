# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-yawarm1p5-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-03T22:19:17+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

**wandb_id**: j7v0uvo9

**hypothesis**: Seed-1 twin of cap29-stdwalklohi-yawarm1p5: same combined_yaw_arm_scale=1.5 lever, on the seed-1 cap29-stdwalklo-hi-s1 control, to check the mechanism's effect is seed-robust.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same PASS/FAIL bar as the seed0 twin, read against the seed1 control (cap29-stdwalklo-hi-s1) instead.

**verdict**: CANARY FAIL - MECHANISM (candidate (i)-v2 combined_yaw_arm_scale, dose 1.5, seed1). Ran probe_turn_authority.py --vx-cmds with the FULL 84-key non-train cfg-set replayed (this cycle's own family-wide gotcha: the 5-flag shorthand silently freezes some checkpoints) against this checkpoint AND a freshly-rerun seed1 control (cap29-stdwalklo-hi-s1, same full cfg) -- new/fresh control numbers matched the cached 17:19 file within noise (seed1 identical, seed0 delta <=0.01), so both are used interchangeably below. Pure-turn wz_med (seed-avg): this ckpt +0.197/-0.188 vs control +0.226/-0.247 -> regression 12.6% (+) / 24.0% (-), BOTH over the pre-registered 10% cap -- negative side breaks worse, same shape as every other cell in this grid (yawarm1p5 seed0, yawarm2p0 seed0, yawarm2p0-s1). Combined-tick (vx=0.08) wz_med: this ckpt +0.106/-0.158 vs the pre-registered comparator (cap29-stdwalklo-hi-s1 own combined read) +0.087/-0.142 -> BOTH signs beat the comparator cleanly (+22% / +11% magnitude) -- a clean bidirectional win, matching the seed0/dose1.5 twin (the only other cell in the grid to win both signs; both dose-2.0 cells were sign-asymmetric). No falls in any of the 8 wz=+-0.25 probe rows; straight-walk (wz=0,vx=0.08) shows no meaningful wz drift either side (0.014-0.018 vs control 0.018-0.020) so that clause doesn't drive the verdict. Training reward: quarters [25.6, 55.9, -190.7, 121.9], final ep_rew_mean 167.97 -- same family Q3 dip/recovery shape (rider c), not a training collapse. Per the pre-registered gate (PASS needs both signs to beat the comparator AND <=10% pure-turn regression), this FAILS on the regression clause alone despite a genuine, clean combined-tick win, exactly reproducing its seed0 twin's shape. THIS CLOSES THE CANDIDATE (i)-v2 DOSE x SEED GRID AT 4/4 FAIL (seed0/1.5 FAIL, seed1/1.5 FAIL [this run], seed0/2.0 FAIL, seed1/2.0 FAIL): every cell that wins the combined-tick axis (both dose-1.5 cells, bidirectionally) blows the pure-turn regression cap on the negative sign by 23-27%, and cells that stay under/near the cap on pure-turn (dose 2.0) lose the combined-tick win instead (sign-asymmetric or outright worse). Combined with the already-refuted omega-boost/omega-discount axis (both directions, STATUS 09-03), the WHOLE geometry/scaling-lever search for standwalk item 2 is now closed: no single-scalar open-loop lever clears the gate without trading pure-turn authority it wasn't supposed to touch (the lever is bit-exact on pure-turn by construction at the scripted-teacher level, so the RL-trained regression must come from the shared GRU-dual policy's representation, not the geometry itself). Next lever must touch WHAT the BC-anchor supervises (e.g. phase-scheduled anchor strength that weakens on combined ticks specifically), not another single-scalar dose on the existing mechanism. Evidence: logs/ckpt_eval/probe_turn_authority_yawarm1p5_s1_combined_09-03.json vs logs/ckpt_eval/probe_turn_authority_cap29_stdwalklo_hi_s1_combined_09-03{,_fullcfg}.json.

