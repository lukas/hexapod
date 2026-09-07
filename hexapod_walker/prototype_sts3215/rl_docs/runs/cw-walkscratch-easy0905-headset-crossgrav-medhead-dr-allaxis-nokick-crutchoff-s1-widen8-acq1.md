# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-07T08:26:11+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8

**wandb_id**: fy8zil9f

**hypothesis**: Plain English: the crutch-off full-realism composite's 8-way heading widening was clean at 2M-canary depth on both crutch-off seeds; the open question is whether it holds at real 40M acquisition budget, since this exact composite's push-recovery fragility only ever showed up at ACQ depth (not canary depth) on one of the three crutch-isolation seeds. Same single-axis widen (8-way goal.walk_heading_set), init from this seed's own 2M widen8-CANARY-PASS checkpoint, full 40M budget. Prediction-if-true (composable at scale): 0 or near-0 falls across 24 held-out episodes, gait_valid stays majority (>=18/24), matching the canary. Prediction-if-false: tilt-roll falls reappear on the new rear headings specifically once training entrenches further (the same late-entrenchment pattern s0's crutch-ON canary showed), or a chronic single-leg sacrifice emerges on the widened panel.

**gate**: ACQUISITION (40M): held-out gate on own cfg (8-way heading set, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid majority (>=18/24), flat-or-better vs this seed's own 2M widen8 canary (21/24). FAIL if any new fall (esp. tilt_roll on rear headings) or a NEW chronic single-leg sacrifice not present in the canary. Reward rising with a soft/inconclusive dir-metric on new headings alone = continue, not FAIL, per the 08-21 ruling.

**verdict**: ACQ FAIL (misaligned, per this gate's own pre-registered criterion). 0 falls/terminations across all 24 held-out episodes (matching canary) but gait_valid DROPPED from the 2M widen8 canary's 21/24 to 20/24, and per-episode diff vs that same seed's own canary (same held-out episode indices/headings) shows a NEW chronic single-leg sacrifice at walk/det ep5 (clean gv=True at canary, now gv=False sac=[0,5], duty~0 on leg5) that was not present before -- exactly the gate's named FAIL condition ('a NEW chronic single-leg sacrifice not present in the canary') and exactly this hypothesis's own predicted failure mode. Reward rose monotonically all 4 quarters (264->533->684->773, ep_rew_mean 966.9) -- per the 08-21 ruling this is reward-rising-while-eval-regresses-on-a-specific-axis, i.e. MISALIGNED not merely under-trained: more budget entrenched a heading-specific shortcut (drag/park one leg on a hard new rear/diagonal heading from the widened 8-way set) rather than resolving it, matching the same late-entrenchment push-recovery-fragility shape already seen once elsewhere in this composite. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxis_nokick_crutchoff_s1_widen8{,_acq1}_gate/report.json (per-episode diff), contact sheet walk_det_5.

