# cw-walkscratch-crutchoff-s1-widen8-legdutyratio-loadslip

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-08T13:10:33+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: c53162rm

**hypothesis**: Seed1 twin of the s0 load-slip-charge canary launched this same window: does the peer-excluded-MEDIAN load-slip ratio charge (target 1.5, charge 150), on top of the existing 0.30-dose duty-ratio charge, fix the gait_valid-recovers-via-worse-slip trade that dose escalation and the swing-count-floor both failed to fix on this seed. Same seed1/init-from/heading-set/DR/motor cfg as the matched 0.30-dose s1 guardfix1 sibling, only the new load-slip charge added.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. (a) post-grace env/walk_leg_loadslip_ratio_excess and env/reward_walk_leg_loadslip_ratio must appear, finite, in real GPU telemetry. (b) zero new falls/terminations vs the matched 0.30-dose s1 guardfix1 sibling at the same seed/budget. (c) same joint gait_valid-AND-slip/progress comparison the swing-floor arms used: >=3/4 groups must jointly improve vs that sibling for a CONTINUE signal; report whether the gait_valid-recovers/slip-worsens trade persists. Read together with s0/s2 siblings: majority (>=2/3 seeds hitting >=3/4) funds a cont10m depth read; minority does not.

**verdict**: CANARY PASS - mechanism healthy, no efficacy. Telemetry PASS: env/walk_leg_loadslip_ratio_excess and env/reward_walk_leg_loadslip_ratio engage finite post-grace (step ~1.57M). Falls PASS: 0 new terminations vs the matched 0.30-dose guardfix1 s1 sibling in all 4 groups. Efficacy FAIL: the pre-registered >=3/4-groups-jointly-improve bar is not met -- walk/det flat (slip 9.08->9.04, prog 0.92->0.93), walk/sto worse (slip 6.96->8.14 +17%, prog 1.19->1.01 -15%), sj/det worse (slip 8.86->9.44, prog 1.06->1.01), sj/sto worse (slip 13.15->13.68, prog 0.68->0.63); 0/4 groups clear both axes. wandb_history shows the load-slip excess/ratio SATURATED near ceiling for the whole post-grace window (excess 0.86->0.90->1.0, ratio climbing 11.8->12.3, never narrowing) while ep_rew_mean collapses to -9858/-34057 in the last two quarters with unchanged eval behavior -- a saturated-penalty-with-no-repair-gradient shape, the same fingerprint that already closed the swing-count-floor lever on this lineage. This seed alone means at most 1/3 of {s0,s1,s2} can hit the >=3/4 bar (s2 also short, see its own verdict) -- majority (>=2/3) cannot be reached regardless of s0's own read, so cont10m is not funded by this batch; s0 stays owned by a concurrent cycle and gets its own verdict. Video (contact sheet) confirms genuine forward walking, no gate/video conflict on this run; no safety concern. Evidence: logs/ckpt_eval/cw_walkscratch_crutchoff_s1_widen8_legdutyratio_loadslip_gate/report.json vs .../legdutyratiofresh_guardfix1_gate & .../legdutyratio_swingfloor_gate; logs/experiments/cw-walkscratch-crutchoff-s1-widen8-legdutyratio-loadslip/wandb_history.csv; W&B c53162rm.

