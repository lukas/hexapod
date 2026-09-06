# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T06:21:16+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: 25i0uyfk

**hypothesis**: This is the campaign's culmination arm: every individual DR axis (mass/geometry/friction/compliance/gains/latency/deadband/velcap/cmddrop/startpose/zerobias/encoder-noise/tilt-noise/gyro-noise-and-bias/imu-bias/imu-mount-position/action-noise/ground-tilt/fault/ext-push/kick/push) has now scored at least one clean single-axis PASS in isolation on this same champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24, 0 falls) -- but the campaign has ALSO found that pairwise compositions can regress sharply even when both ingredients are individually clean (irr+widen: two clean sources, composite FAILs at ACQ scale). Does the champion survive ALL nominal realism axes turned on AT ONCE, not just one at a time? dr.torque_scale is deliberately left at the campaign's fixed idealized crutch (3,3), unchanged from every sibling single-axis arm, since torque-crutch removal is its own separate active dose-response study (torquefade1x/15x) -- this arm isolates the ONE new variable of full-axis composition.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the champion's clean single-axis tolerance actually composes to full realism, not just to isolated axes. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls) -- shows realism axes interact/compound even when each is individually harmless, and the DR-rung must budget real acquisition-scale training against the FULL stack, not just per-axis canaries.

**verdict**: CANARY FAIL - MECHANISM -- the campaign culmination composite (ALL ~20 individually-clean DR axes at nominal 1x dose simultaneously, torque_scale left at the fixed 3x crutch) produces REAL FALLS that no single axis produced alone. Evidence: 5/24 episodes terminate tilt_roll (walk/det ep3, walk/sto ep3, walk_startjitter/det ep4, walk_startjitter/sto ep0+ep3), spread across all 4 panels -- not confined to one mode. roll_peak_deg runs 16-33 across the whole set (vs the clean single-axis siblings tighter roll band), and the terminated episodes own frame strips (walk_det_3.png) show the body visibly tipping/rolling through the back half of the episode before the safety cutoff fires. gait_valid nominally stays majority (23/24) and slip/m (3.8-7.7) is only moderately worse than single-axis siblings, but the gate own pre-registered FAIL criterion is falls appearing at all, which they do -- video and metrics agree, no tooling disagreement. Why: this directly confirms the gate own hypothesis text -- realism axes that are each individually harmless in isolation compound/interact when stacked, and the champion single-axis tolerance does NOT automatically compose to full-realism tolerance. Same class of pairwise-composition regression already seen once (irr+widen composing to an ACQ-scale regression from two individually-clean sources), now confirmed at full ~20-axis composite scale. What next: do NOT fund an ACQ continuation of this exact all-axis-at-once composite -- the bisection already in flight (allaxiskickhalf1x-c1, halving the kick-realism dose specifically, since single-axis kick1x-c1 was independently the sweep only other fall) is the right next read to isolate whether kick dose alone explains the compounding or whether it is a genuine multi-axis interaction; read that before any further composite-realism launch. (Re-recorded after an agent git-checkout mishap wiped the earlier ledger write; W&B notes/RL_LOG/rl_docs md already carried the original text unaffected.)

