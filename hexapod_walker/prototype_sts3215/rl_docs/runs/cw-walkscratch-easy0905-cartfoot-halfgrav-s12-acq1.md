# cw-walkscratch-easy0905-cartfoot-halfgrav-s12-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-08T11:53:10+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s12

**wandb_id**: hijwfdoc

**hypothesis**: Plain English: 4th-seed replicate of the halfgrav cart_foot ON 40M acquisition, breaking the tie in the closed n=3 cohort where cart_foot's gait_valid advantage over joint-space held for 2/3 seeds (s7 22/24 vs 10/24, s10 17/24 vs 7/24) but vanished for s11 (11/24 vs 10/24, near-parity). Own-checkpoint continuation of the CANARY-PASSed s12 2M arm (telemetry matched s7/s10/s11 band exactly).

**gate**: ACQUISITION gate: >=0.03 m/s median net forward in >=1 of walk/det,sto, 0 falls in det (same bar every s7/s10/s11 ON arm cleared). Read together with offctrl-s12-acq1 (matched joint-space OFF sibling, launched same cycle): gait_valid gap vs slip-only difference determines whether this seed extends the seed7/10 majority pattern (2/3, real cart_foot advantage) or the seed11 minority pattern (1/3, near-parity) for this recipe family.

**verdict**: Fresh-init cart_foot (ON) halfgrav seed12 clears its own acquisition floor cleanly: 0 falls/terminations in 24/24 gate episodes across all 4 groups, fwd med 4.10/3.69/4.14/3.34m over 20s (~0.17-0.20 m/s), well above the 0.03 m/s floor. gait_valid is 0/6 walk/det (every det episode sacrifices leg [4] identically -- fixed start conditions), 5/6 walk/sto (1 ep adds leg1), 1/6 startjitter/det, 3/6 startjitter/sto = 9/24 total. slip/m med 1.61/1.75/1.62/1.66 across the 4 groups. Reward quarters rise monotonically (-696.8/182.1/926.4/1178.7), completed naturally at 40,370,176 steps -- 08-21 satisfied either way since evals already clear the acquisition gate. Video reviewed (walk_det_0.png strip): real forward translation every frame, six legs visible cycling with a clear split between the swinging majority and one dragging leg, not a frozen pose. NEW CROSS-SEED FINDING: this is the 4th seed pair for this recipe and, unlike s7/s10 (clear cart_foot gait_valid advantage) or s11 (near-parity, ON slightly ahead), seed12 goes the OTHER way -- see the matched offctrl-s12-acq1 verdict (this cycle) for the joint OFF/ON comparison; do not treat this as resolving or contradicting the prior spread, just adding a 4th, differently-signed data point. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_halfgrav_s12_acq1_gate/report.json; W&B hijwfdoc.

