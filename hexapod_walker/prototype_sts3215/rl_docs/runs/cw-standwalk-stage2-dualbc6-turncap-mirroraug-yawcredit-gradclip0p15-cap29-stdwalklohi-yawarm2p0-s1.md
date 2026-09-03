# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-yawarm2p0-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-03T22:23:21+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

**wandb_id**: hfect0is

**hypothesis**: Seed-1 twin of cap29-stdwalklohi-yawarm2p0: same combined_yaw_arm_scale=2.0 lever, on the seed-1 cap29-stdwalklo-hi-s1 control, to check the mechanism's effect is seed-robust.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same PASS/FAIL bar as the seed0 twin, read against the seed1 control (cap29-stdwalklo-hi-s1) instead.

**verdict**: CANARY FAIL - MECHANISM (candidate (i)-v2 combined_yaw_arm_scale, dose 2.0, seed1). Ran probe_turn_authority.py --vx-cmds with the FULL 84-key non-train cfg-set replayed against this checkpoint AND a freshly-run seed1 control (cap29-stdwalklo-hi-s1, same full cfg, per this ledger's own gate text 'read against the seed1 control instead') -- new artifacts logs/ckpt_eval/probe_turn_authority_yawarm2p0_s1_combined_09-03.json vs logs/ckpt_eval/probe_turn_authority_cap29_stdwalklo_hi_s1_combined_09-03_fullcfg.json (the cached 17:19 s1-control file was pre-gotcha shorthand-cfg, not reused). Pure-turn wz_med (seed-avg): this ckpt +0.207/-0.180 vs seed1 control +0.226/-0.247 -> regression 8.3% (+, within the 10% cap) / 27.4% (-, BLOWS the cap) -- same shape as every prior cell in this family (negative side always the one that breaks). Combined-tick (vx=0.08) wz_med: this ckpt +0.109/-0.136 vs the seed1 control's own combined read +0.087/-0.142 -> positive side beats cleanly (+26%) but negative side is WEAKER than its own control (-4.5%), i.e. sign-asymmetric -- same failure shape as combskip/omegaboost/yawboost-lodose and this candidate's own seed0/dose2.0 cell (which also flipped from dose1.5's clean bidirectional win to asymmetric-then-regressed by dose2.0). No falls on any wz=+-0.25 row (12/12); the seed1 control had one unrelated fall at wz=0/vx=0 (straight-walk cell, not scored by either gate clause). Reward: quarters [23.5, 59.3, -200.6, 116.8], final ep_rew_mean 164.6 -- same family Q3 dip/recovery shape, weakest final value of the four dose x seed cells so far but not a collapse (still positive, still climbing in Q4). FAILS both gate clauses (regression cap AND comparator-both-signs), closing 3/4 of the candidate (i)-v2 dose x seed grid at FAIL (seed0/1.5, seed0/2.0, seed1/2.0); only seed1/1.5 (a concurrent cycle's run) remains to confirm 4/4. Working theory unchanged from the seed0/dose2.0 read: yaw-arm-scale's clean bidirectional win sits in a narrow window near dose 1.5 that a real RL fine-tune cannot hold at dose 2.0, on either seed -- this whole lever likely closes at 4/4 without escalating past dose 2.0.

