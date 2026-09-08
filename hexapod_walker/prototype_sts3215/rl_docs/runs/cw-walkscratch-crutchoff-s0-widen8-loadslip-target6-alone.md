# cw-walkscratch-crutchoff-s0-widen8-loadslip-target6-alone

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T15:31:34+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6

**wandb_id**: gwoifvs7

**hypothesis**: Plain English: every walk_leg_loadslip_ratio_charge arm tried so far (target=1.5 closed, target=6.0 w150/w45/w15) was ALSO trained with walk_leg_duty_ratio_charge=150 active at the same time, warm-started from a checkpoint that already had duty-ratio-charge training baked in -- so the huge reward-quarters collapse blamed on the loadslip charge is confounded: the SAME duty-ratio-charge alone (own canary, no loadslip) already produces an identical-shaped collapse (ep_rew_mean -31/-3590 across quarters, verdicted CANARY PASS as 'fully explained by ep_len growth, not behavioral collapse'). This arm removes that confound: init from the TRUE pre-duty-charge checkpoint (widen8-acq1, matched undosed baseline gait_valid 20/24) with walk_leg_duty_ratio_charge=0 and ONLY walk_leg_loadslip_ratio_charge=150/target=6.0 (the corrected calibration) live. Does the load-slip-ratio charge, tested alone without the duty-ratio charge's own reward-scale and init confound, show a real efficacy signal (>=3/4 held-out groups improving slip+progress vs the plain widen8-acq1 baseline) that the confounded reads could not distinguish from noise?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY, isolation scope. PASS-worth-CONTINUE if >=3/4 of the 4 held-out groups (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto) jointly improve slip AND progress vs the plain widen8-acq1 undosed baseline (gait_valid 20/24) with 0 new falls, AND reward-quarters do not show the same order-of-magnitude collapse as the duty-ratio-charge-alone canary (if it does, re-confirms ep_len-growth as the driver, not a new problem). FAIL if <3/4 groups improve or a new fall appears -- closes load-slip-ratio-charge as a standalone lever too (not just in combination), leaving only a genuinely new per-leg mechanism design.

