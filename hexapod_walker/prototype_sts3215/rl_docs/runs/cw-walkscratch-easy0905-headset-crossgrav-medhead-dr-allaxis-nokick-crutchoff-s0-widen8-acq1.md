# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-07T08:38:42+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8

**wandb_id**: qahuzut4

**hypothesis**: Plain English: the crutch-off full-realism composite's 8-way heading widening was clean at 2M-canary depth on all 3 crutch-off seeds (s0 21/24->3/3 now, s1 21/24, s2 22/24); the open question is whether it holds at real 40M acquisition budget, since this exact composite's push-recovery fragility only ever showed up at ACQ depth (not canary depth) on one of the three crutch-isolation seeds -- this s0 twin completes the ACQ trio alongside the already-launched s1/s2-widen8-acq1 arms. Same single-axis widen (8-way goal.walk_heading_set), init from this seed's own 2M widen8-CANARY-PASS checkpoint, full 40M budget. Prediction-if-true (composable at scale): 0 or near-0 falls across 24 held-out episodes, gait_valid stays majority (>=18/24), matching the canary. Prediction-if-false: tilt-roll falls reappear on the new rear headings specifically once training entrenches further (the same late-entrenchment pattern this exact seed's crutch-ON canary showed), or a chronic single-leg sacrifice emerges on the widened panel.

**gate**: ACQUISITION (40M): held-out gate on own cfg (8-way heading set, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid majority (>=18/24), flat-or-better vs this seed's own 2M widen8 canary (22/24). FAIL if any new fall (esp. tilt_roll on rear headings) or a NEW chronic single-leg sacrifice not present in the canary. Reward rising with a soft/inconclusive dir-metric on new headings alone = continue, not FAIL, per the 08-21 ruling.

**verdict**: ACQ FAIL (misaligned, per this gate's own pre-registered criterion) -- closes item(1)'s widen8 ACQ trio 3/3 FAIL, identical fingerprint on every seed. 0 falls/terminations across all 24 held-out episodes (matching canary) but gait_valid DROPPED from the 2M widen8 canary's clean 22/24 (walk/det was 6/6 clean) to 20/24: per-episode diff vs this seed's own canary (same held-out episode indices/headings) shows TWO new chronic single-leg sacrifices at walk/det ep0 (sac=[5]) and ep5 (sac=[0,5]) that were both clean in the canary -- exactly the gate's named FAIL condition and exactly the s1/s2 twins' own fingerprint (same episode indices, same legs). Reward rose monotonically all 4 quarters (266.9->530.3->636.2->796.1) -- per the 08-21 ruling this is reward-rising-while-eval-regresses, i.e. MISALIGNED not merely under-trained. NEW STRUCTURAL READING (checked mesh leg-mount coords, mesh_mujoco/hexapod_mesh.xml): the sacrificed legs [0,5] are the FRONT pair (both x=+0.087, the two legs closest together on the nose), NOT the previously-diagnosed L1/L4 middle pair (CURRENT_TRUTHS 'Walkcurr Reward Mechanisms' section, 11 failed reward-price mechanisms). This generalizes that diagnosis: the widen8 set's 3 new headings are all rear/diagonal-rear (135,-135,180 deg out of the 8-way set); for a rear-ish commanded heading the FRONT leg pair is the redundant/least-loaded pair by the same forward-gait logic that makes the middle pair redundant for forward commands -- a heading-direction-dependent redundant-leg-pair pattern, not a fixed structural pair. Do not relaunch widen8 at ACQ depth on this recipe without either (a) the still-unbuilt role-aware/support-margin reward mechanism (11 prior reward-price designs already exhausted for the L1/L4 case; any new design must also cover this direction-dependent front-pair case) or (b) a narrower heading widen that excludes the specific rear headings pending a bisection. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxis_nokick_crutchoff_s0_widen8{,_acq1}_gate/report.json, mesh_mujoco/hexapod_mesh.xml leg coords, s1/s2 twins' identical fingerprint.

