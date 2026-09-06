# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T02:13:19+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1

**wandb_id**: xlhp3w8c

**hypothesis**: Plain English: every irr-timing composite tested so far was built in 0.5g FIRST, then abruptly transferred to 1g. Now that a plain-heading base(1g) champion exists (medhead-abrupt-c1-acq1, ACQ PASS, gait_valid 23/24 at 40M, leg-healthy), can the SAME command-timing-irregularity jitter be added FORWARD, directly at 1g, without ever touching 0.5g again? Tests whether the cross-gravity repair is a durable foundation for further curriculum extension natively in 1g (mirrors the sibling widenfwd-c1 arm on the heading axis).

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10-duty every episode) single-leg sacrifice -- shows the 1g repair supports forward curriculum extension without another 0.5g detour. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint -- would mean 1g timing-irregularity generalization still requires building the composite at 0.5g first. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: CANARY PASS - INFORMATIVE-POSITIVE. Mirrors the sibling widenfwd-c1 arm: the now-ACQ-PASSed 1g cross-gravity medhead champion supports composing command-timing-irregularity (irr) jitter NATIVELY at 1g, without a 0.5g detour first. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_irrfwd_c1_gate/report.json (24 eps, full 1g, 2M): aggregate gait_valid 22/24 -- walk/det 4/6 (episodes 1 and 5 flag sac=[2,5], duty 0.04-0.07 there vs 0.17-0.61 for those same legs in the other 4 episodes -- transient softening, not chronic, matches the mild jitter-sensitivity shape already seen on medhead/widen2c1/irracq1/widenirrc1/s3acq), walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6. 0 falls/terminations in all 24 episodes. slip_per_m unusually TIGHT and clean (3.06-5.63, no reversal-heading outliers unlike the widenfwd sibling's 3.6-203 spread) -- forward_dist_m 1.79-2.69m/20s throughout. Video (walk_det_0, walk_det_1 the flagged episode) confirms genuine multi-leg cycling with real chassis translation even in the 4/6 episode. Why: sibling arm to medhead-widenfwd-c1 testing whether the cross-gravity repair is a durable foundation for FORWARD curriculum extension on the irr-timing axis instead of only working when built at 0.5g first -- both siblings now PASS, so the 1g repair generalizes across BOTH extension axes (heading breadth and command-timing jitter). Next: matched 40M ACQ continuation.

