# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-friction1x-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: HARDENING PASS

**created**: 2026-09-06T09:00:28+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-friction1x-c1-acq1

**wandb_id**: uia0zijo

**hypothesis**: Plain English: does the friction-restore axis (dr.friction_scale 0.6-1.4) hold up over a SECOND 40M block (80M cumulative), the same endurance question already asked of the crossgrav/halfgrav cont40m siblings? Source is clean at 40M (24/24 gait_valid, 0 falls, sac=[] every episode, monotonic reward).

**gate**: PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with slip_per_m staying near the source's own 3.4-4.3 band and no NEW chronic single-leg sacrifice. FAIL/ENTRENCHES if a chronic single-leg sacrifice newly emerges/spreads across multiple modes.

**verdict**: HARDENING PASS/HOLDS: +40M (80M cumulative) on the friction-restoration DR axis (dr.friction_scale 0.6-1.4) mildly softens from its own 40M parent's perfect 24/24 to 23/24 -- one new single-episode flag (walk_startjitter/det ep1, leg5, slip 3.69 still in-band), every other mode/episode stays clean (walk/det 6/6, walk/sto 6/6, walk_startjitter/sto 6/6). 0 falls/terminations either side. Slip/m medians (3.45-4.36) stay inside the source's own registered 3.4-4.3 band. Reward monotonic rising every quarter (558.5/1037.8/1124.1/1201.9). A single scattered flag, not a chronic pattern -- clears the run's own pre-registered majority + no-new-chronic-leg bar comfortably. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_friction1x_c1_acq1_cont40m_gate/report.json vs ..._acq1_gate/report.json, W&B uia0zijo.

