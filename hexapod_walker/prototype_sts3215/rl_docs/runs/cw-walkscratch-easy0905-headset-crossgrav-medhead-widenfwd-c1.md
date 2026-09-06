# cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T02:11:55+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1

**wandb_id**: tj1ko3bp

**hypothesis**: Plain English: every widen2/irr heading+jitter composite tested so far was built in 0.5g FIRST, then abruptly transferred to 1g. Now that a plain-heading base(1g) champion exists (medhead-abrupt-c1-acq1, ACQ PASS, gait_valid 23/24 at 40M, leg-healthy), can the SAME widen2 full-8-way-heading-set composition be added FORWARD, directly at 1g, without ever touching 0.5g again? This tests whether the cross-gravity repair is a durable foundation for further curriculum extension natively in 1g, or whether composing new heading breadth only works pre-transfer.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10-duty every episode) single-leg sacrifice -- shows the 1g repair supports forward curriculum extension without another 0.5g detour. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint -- would mean 1g heading generalization still requires building the composite at 0.5g first. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: CANARY PASS - INFORMATIVE-POSITIVE. The now-ACQ-PASSed 1g cross-gravity medhead champion (headset-crossgrav-medhead-abrupt-c1-acq1, 23/24 native) supports composing the FULL widen2 8-way heading set NATIVELY at 1g, without a 0.5g detour first. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_widenfwd_c1_gate/report.json (24 eps, full 1g, 2M): aggregate gait_valid 23/24 -- walk/det 5/6 (only ep4 flagged sac=[0,3], duty 0.03/0.09 there vs 0.09-0.71 in the other 5 episodes for those same legs, i.e. transient not chronic), walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6. 0 falls/terminations in all 24 episodes. slip_per_m spans 3.6-203 with the extreme outliers (walk/sto/3, walk_startjitter/det/2, walk_startjitter/sto/3) confirmed via frame strip as the already-documented reversal-heading spin-in-place low-progress-denominator artifact (legs still cycling, net travel near-zero from a direction reversal), not a new defect. Video (walk_det_0, walk_startjitter_det_0) shows genuine six-leg cycling with clear body translation across multiple headings. Why: this is the sibling arm to medhead-irrfwd-c1 testing whether the cross-gravity repair is a durable foundation for FORWARD curriculum extension (composing new heading breadth on top of an already-1g-transferred champion) instead of only working when built at 0.5g first. Next: matched 40M ACQ continuation.

