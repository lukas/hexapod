# cw-walkscratch-crutchoff-s0-widen8-loadslip-target6-alone

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T15:31:34+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6

**wandb_id**: gwoifvs7

**hypothesis**: Plain English: every walk_leg_loadslip_ratio_charge arm tried so far (target=1.5 closed, target=6.0 w150/w45/w15) was ALSO trained with walk_leg_duty_ratio_charge=150 active at the same time, warm-started from a checkpoint that already had duty-ratio-charge training baked in -- so the huge reward-quarters collapse blamed on the loadslip charge is confounded: the SAME duty-ratio-charge alone (own canary, no loadslip) already produces an identical-shaped collapse (ep_rew_mean -31/-3590 across quarters, verdicted CANARY PASS as 'fully explained by ep_len growth, not behavioral collapse'). This arm removes that confound: init from the TRUE pre-duty-charge checkpoint (widen8-acq1, matched undosed baseline gait_valid 20/24) with walk_leg_duty_ratio_charge=0 and ONLY walk_leg_loadslip_ratio_charge=150/target=6.0 (the corrected calibration) live. Does the load-slip-ratio charge, tested alone without the duty-ratio charge's own reward-scale and init confound, show a real efficacy signal (>=3/4 held-out groups improving slip+progress vs the plain widen8-acq1 baseline) that the confounded reads could not distinguish from noise?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY, isolation scope. PASS-worth-CONTINUE if >=3/4 of the 4 held-out groups (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto) jointly improve slip AND progress vs the plain widen8-acq1 undosed baseline (gait_valid 20/24) with 0 new falls, AND reward-quarters do not show the same order-of-magnitude collapse as the duty-ratio-charge-alone canary (if it does, re-confirms ep_len-growth as the driver, not a new problem). FAIL if <3/4 groups improve or a new fall appears -- closes load-slip-ratio-charge as a standalone lever too (not just in combination), leaving only a genuinely new per-leg mechanism design.

**verdict**: CANARY FAIL - MECHANISM (isolation scope, mechanism healthy, efficacy short of bar, but real+reproducible partial signal -- see s1 twin): init from the TRUE pre-duty-charge widen8-acq1 checkpoint, walk_leg_duty_ratio_charge=0, ONLY walk_leg_loadslip_ratio_charge=150/target=6.0 live. Vs the matched undosed widen8-acq1 baseline (walk/det slip 7.57/fwd 0.41m gv4/6, walk/sto slip 6.67/fwd 1.09m gv6/6, walk_startjitter/det slip 7.94/fwd 0.58m gv6/6, walk_startjitter/sto slip 9.33/fwd 0.37m gv4/6): walk/det slip 7.06 (better)/fwd 0.33m (worse) -- mixed; walk/sto slip 6.28 (better)/fwd 0.99m (worse) -- mixed; walk_startjitter/det slip 7.57 (better)/fwd 0.78m (better, +34%) -- JOINTLY IMPROVES; walk_startjitter/sto slip 8.92 (better)/fwd 0.46m (better, +24%) -- JOINTLY IMPROVES. 2/4 groups jointly improve (short of the >=3/4 bar) but ALL 4 groups improve on slip, gait_valid is flat (not worse) in every group, 0 new falls. Reward quarters [53.1, 109.8, -628.2, -9865.8] collapse MORE than the duty-ratio-charge-alone canary's own [31.1, 63.4, -903.4, -3589.9] despite this arm having NO duty-ratio-charge at all -- this REFUTES my own launch hypothesis that the duty-ratio-charge confound was inflating the collapse magnitude; instead it shows walk_leg_loadslip_ratio_charge's own unbounded-excess formula (no cap on how far a leg's slip ratio can exceed target, unlike duty-ratio's shortfall which is naturally bounded at target=0.30) is the real driver of the reward-scale collapse, independent of any confound. Contact sheet confirms genuine forward walking on video (not a stationary artifact). Net: closes load-slip-ratio-charge as a standalone lever at this dose/target too (same as the confounded reads), but for a NEWLY IDENTIFIED reason (uncapped excess, not the duty-ratio confound) -- concrete next design lever is a CAPPED excess term (clip worst_excess to a max before multiplying by weight), not further weight/target dosing or confound removal. See s1 twin (same cycle) for cross-seed replication of the exact same 2/4-groups pattern.

