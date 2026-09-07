# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-speedwiden-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: acq_pass

**created**: 2026-09-07T11:07:22+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-speedwiden

**wandb_id**: wz9biedf

**hypothesis**: Plain English: does the speed-band widening (0.03-0.12 m/s dynamic cap) that just CANARY PASSed (3/3 seeds, clean vs each seed's own baseline) hold at real 40M acquisition budget, or does it re-open the composite's known late-entrenchment fragility the way the widen8 heading axis did (canary PASS 3/3, then ACQ FAIL 3/3 via a heading-dependent front-leg-pair sacrifice)? Same single-axis test, warm-started from this seed's own speedwiden-CANARY-PASS checkpoint.

**gate**: PASS (widening holds) if 0 falls/24 (or near-0, matching each seed's own acq1 baseline of 0 terms) and gait_valid >=18/24 with no new chronic sacrifice beyond the parent acq1's own walk_startjitter/sto leg0/leg5 flag. FAIL if a new chronic sacrifice or falls appear, matching widen8's own ACQ-depth regression shape.

**verdict**: ACQ PASS: speed-band widening (0.03-0.12 m/s dynamic freeprog cap) HOLDS at full 40M acquisition depth on the crutch-off full-DR composite, seed s0. gate: gait_valid 21/24 (6/6 walk/det, 6/6 walk/sto, 6/6 walk_startjitter/det, 3/6 walk_startjitter/sto), 0 falls/terminations across all 24 episodes -- identical total and identical per-mode split to the parent crutchoff-s0-acq1 baseline (21/24, 0 terms), and the only sacrifice (walk_startjitter/sto ep2/3/4, legs [5],[0],[5]) matches the parent's own known chronic leg0/leg5 flag exactly, not a new failure mode. slip_per_m is actually LOWER than parent in every one of the 4 modes (e.g. walk/det med 3.4 vs parent 4.75; walk_startjitter/sto med 6.0 vs parent 8.4) -- still above the 2.9 teacher band but a real improvement, not a regression. Frame strips (walk_det_0, walk_startjitter_sto_3) show genuine six-leg forward translation with the flagged leg's known chronic-park matching the parent fingerprint, no new pathology. This differs from the sibling widen8 heading axis, which canary-PASSed 3/3 then ACQ-FAILed 3/3 via a NEW heading-dependent front-leg sacrifice -- speed-widening does not share that late-entrenchment fragility. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxis_nokick_crutchoff_s0_speedwiden_acq1_gate/report.json vs ..._crutchoff_s0_acq1_gate/report.json, W&B wz9biedf.

