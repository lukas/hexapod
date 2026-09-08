# cw-walkscratch-crutchoff-s2-widen8-legdutyratio-loadslip

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-08T13:13:37+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: 2ypexwbn

**hypothesis**: Seed2 twin of the s0/s1 load-slip-charge canaries launched this same window (the pre-registered n=3 batch, learning from today's own lesson that n=2 swing-floor reads needed a 3rd tie-break twice): does the peer-excluded-MEDIAN load-slip ratio charge (target 1.5, charge 150), on top of the existing 0.30-dose duty-ratio charge, fix the gait_valid-recovers-via-worse-slip trade. Same seed2/init-from/heading-set/DR/motor cfg as the matched 0.30-dose s2 guardfix1 sibling, only the new load-slip charge added.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. (a) post-grace env/walk_leg_loadslip_ratio_excess and env/reward_walk_leg_loadslip_ratio must appear, finite, in real GPU telemetry. (b) zero new falls/terminations vs the matched 0.30-dose s2 guardfix1 sibling at the same seed/budget. (c) same joint gait_valid-AND-slip/progress comparison the swing-floor arms used: >=3/4 groups must jointly improve vs that sibling for a CONTINUE signal; report whether the gait_valid-recovers/slip-worsens trade persists. Read together with s0/s1 siblings: majority (>=2/3 seeds hitting >=3/4) funds a cont10m depth read; minority does not -- this seed decides ties.

**verdict**: CANARY PASS - mechanism healthy, efficacy short of the CONTINUE bar. Telemetry PASS: env/walk_leg_loadslip_ratio_excess/env/reward_walk_leg_loadslip_ratio engage finite post-grace (step ~1.57M). Falls PASS: 0 new terminations vs the matched 0.30-dose guardfix1 s2 sibling in all 4 groups. Efficacy MARGINAL/MIXED: 2/4 groups clear both axes (walk/det slip 9.84->9.01 prog 0.82->0.91; sj/det slip 9.46->9.06 prog 1.02->1.07) but the other 2/4 are flat-to-worse (walk/sto slip 7.35->7.38 flat, prog 1.08->1.00 -7%; sj/sto slip 12.14->12.63 +4%, prog 0.68->0.68 flat) -- short of the pre-registered >=3/4-groups bar for a CONTINUE signal, though less clearly null than s1 (0/4). Same saturated-charge/reward-collapse fingerprint as s1: env/walk_leg_loadslip_ratio_excess pinned 0.86-0.90 for the whole post-grace window (not narrowing) while ep_rew_mean collapses to -9839/-24190 in the last two quarters with only marginal eval movement. Cross-seed math: with s1 at 0/4 and this run at 2/4, at most 1/3 of {s0,s1,s2} can clear the pre-registered >=3/4 bar regardless of s0's own read -- majority (>=2/3) is unreachable, so this batch does not fund a cont10m depth read; s0 stays owned by a concurrent cycle and gets its own verdict. Video (contact sheet) shows genuine progressive forward walking, no gate/video conflict; no safety concern. Evidence: logs/ckpt_eval/cw_walkscratch_crutchoff_s2_widen8_legdutyratio_loadslip_gate/report.json vs .../legdutyratiofresh_guardfix1_gate; logs/experiments/cw-walkscratch-crutchoff-s2-widen8-legdutyratio-loadslip/wandb_history.csv; W&B 2ypexwbn.

