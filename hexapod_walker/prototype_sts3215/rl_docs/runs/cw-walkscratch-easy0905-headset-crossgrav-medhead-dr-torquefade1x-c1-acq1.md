# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T07:56:09+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade1x-c1

**wandb_id**: 11p0scan

**hypothesis**: Does the campaign's hardest torque-fade dose point (dr.torque_scale 1.0, i.e. the REAL unassisted servo torque spec with zero battery/actuator-assist crutch, PERFECT 24/24 gait_valid at its 2M canary) hold up at a real acquisition-scale (40M) training budget, the same canary-vs-ACQ durability question already answered YES for friction1x and mass1x?

**gate**: ACQ PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice vs the 2M canary and 0 falls. ACQ FAIL - MECHANISM if it collapses (gait_valid <12/24, a new chronic leg, or falls appear).

**verdict**: ACQ PASS -- the campaign's hardest torque-crutch-removal dose (dr.torque_scale=1.0, the REAL unassisted servo torque spec, zero battery/actuator-assist crutch) holds at full 40M acquisition scale, not just its 2M canary. PERFECT 24/24 gait_valid across all 4 panels (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), sac=[] every single episode, 0 terminations/falls. slip/m runs higher than the crutched 1.5x/2x siblings (4.6-6.75 vs their 3.x-5.x band) and forward_dist is correspondingly shorter (0.76-1.9m/20s vs their ~1.5-2.6m) -- the policy is visibly working harder without the torque assist, but stability and gait validity are untouched. Frame strip (walk_det_0_sheet.png) confirms clean six-leg tripod-phase cycling, upright body, no drag/tip. This closes QUEUE AIM frontier item (3): torque-crutch removal is now clean at BOTH canary and ACQ scale at the hardest (1x, no-crutch) dose -- joining the already-PASSed 1.5x/2x cont40m holds. The precondition for item (4) (contextual DONE-gate rungs once composite+no-crutch holds) now has its no-crutch half satisfied; the composite half is still pending allaxiskickhalf1x-c1-r2's gate (genuinely computing this cycle, left for the next reader).

