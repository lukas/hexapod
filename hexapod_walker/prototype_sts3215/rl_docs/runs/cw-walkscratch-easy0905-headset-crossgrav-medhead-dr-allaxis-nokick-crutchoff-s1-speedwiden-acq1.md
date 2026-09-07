# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-speedwiden-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: acq_pass

**created**: 2026-09-07T11:10:49+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-speedwiden

**wandb_id**: 6582vtwg

**hypothesis**: Plain English: does the speed-band widening (0.03-0.12 m/s dynamic cap) that just CANARY PASSed (3/3 seeds, clean vs each seed's own baseline) hold at real 40M acquisition budget, or does it re-open the composite's known late-entrenchment fragility the way the widen8 heading axis did (canary PASS 3/3, then ACQ FAIL 3/3 via a heading-dependent front-leg-pair sacrifice)? Same single-axis test, warm-started from this seed's own speedwiden-CANARY-PASS checkpoint.

**gate**: PASS (widening holds) if 0 falls/24 (or near-0, matching each seed's own acq1 baseline of 0 terms) and gait_valid >=18/24 with no new chronic sacrifice beyond the parent acq1's own walk_startjitter/sto leg0/leg5 flag. FAIL if a new chronic sacrifice or falls appear, matching widen8's own ACQ-depth regression shape.

**verdict**: ACQ PASS: speed-band widening (0.03-0.12 m/s dynamic freeprog cap) HOLDS at full 40M acquisition depth on the crutch-off full-DR composite, seed s1 -- matches its sibling s0's clean result exactly (found orphaned/finished-but-unverdicted this cycle alongside the assigned s0 run; not another cycle's in-flight work -- W&B confirms finished at 40370176 steps, ledger's stale RUNNING status reconciled). gate: gait_valid 21/24 (6/6 walk/det, 6/6 walk/sto, 6/6 walk_startjitter/det, 3/6 walk_startjitter/sto), 0 falls/terminations across all 24 episodes -- identical total AND identical per-mode split to the parent crutchoff-s1-acq1 baseline (21/24, 0 terms), and the only sacrifice (walk_startjitter/sto ep2/3/4, legs [5],[0],[5]) matches the parent's own known chronic leg0/leg5 flag exactly. slip_per_m is LOWER than parent in every mode (e.g. walk/det med 3.47 vs parent 4.67, walk_startjitter/sto med 6.0 vs parent 8.35). Frame strip (walk_det_0) shows genuine six-leg forward translation. 2nd of 3 speedwiden-acq1 seeds clean; s2 podeval kicked off this cycle, unread. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxis_nokick_crutchoff_s1_speedwiden_acq1_gate/report.json vs ..._crutchoff_s1_acq1_gate/report.json, W&B 6582vtwg.

