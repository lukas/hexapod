# cw-walkscratch-crutchoff-s1-widen8-loadslip-target6-alone

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T15:34:32+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s1-widen8-legdutyratio-loadslip

**wandb_id**: n2k2b5jx

**hypothesis**: Plain English: seed1 twin of the s0 loadslip-isolation arm this same window. Every walk_leg_loadslip_ratio_charge arm tried so far was ALSO trained with walk_leg_duty_ratio_charge=150 active and warm-started from a checkpoint that already had duty-ratio-charge baked in, so the reward-quarters collapse blamed on loadslip is confounded with the already-accepted (CANARY PASS) duty-ratio-charge-alone collapse shape. This arm inits from the TRUE pre-duty-charge s1 checkpoint (widen8-acq1) with duty-ratio-charge=0 and ONLY the corrected loadslip-ratio charge (150/target=6.0) live, replicating the s0 isolation arm on a second seed.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY, isolation scope, seed1 replicate. PASS-worth-CONTINUE if >=3/4 of the 4 held-out groups jointly improve slip AND progress vs the plain s1 widen8-acq1 undosed baseline with 0 new falls, AND reward-quarters do not show the same order-of-magnitude collapse as the s1 duty-ratio-charge-alone canary. FAIL if <3/4 groups improve or a new fall appears. Read together with the s0 twin: 2/2 FAIL closes load-slip-ratio-charge as a standalone lever; a split result needs a 3rd-seed tie-break before either claim.

**verdict**: CANARY FAIL - MECHANISM (isolation scope, seed1 replicate of s0's own isolation arm): same recipe on the s1 pre-duty-charge widen8-acq1 checkpoint. Vs the matched s1 undosed baseline (walk/det slip 7.80/fwd 0.20m gv4/6, walk/sto slip 7.27/fwd 0.87m gv6/6, walk_startjitter/det slip 8.51/fwd 0.49m gv6/6, walk_startjitter/sto slip 9.74/fwd 0.41m gv4/6): walk/det slip 7.71 (flat)/fwd 0.33m (better +65%) -- JOINTLY IMPROVES; walk/sto slip 7.25 (flat)/fwd 0.75m (worse -14%) -- mixed; walk_startjitter/det slip 7.92 (better -7%)/fwd 0.66m (better +35%) -- JOINTLY IMPROVES; walk_startjitter/sto slip 10.58 (worse +9%)/fwd 0.39m (flat) -- worse. **Cross-seed replication is exact**: BOTH s0 and s1 land at 2/4 groups jointly improving, and it is the SAME 2 groups both times (walk/det + walk_startjitter/det, the deterministic-policy modes) that improve while walk/sto + walk_startjitter/sto do not -- a reproducible det-vs-sto split, not noise. gait_valid flat vs baseline in every group both seeds (same chronic leg0/leg5 sacrifice, no worse no better), 0 new falls. Reward quarters [48.7, 122.3, -1382.1, -10490.3] again collapse MORE than duty-ratio-charge-alone's own -3589.9, confirming s0's finding that loadslip-ratio-charge's own unbounded-excess formula (not the duty-ratio confound) drives the collapse. Contact sheet confirms genuine forward walking. **2/2 seeds FAIL the >=3/4-groups bar identically -- CLOSES load-slip-ratio-charge as a standalone lever at this dose/target, with a newly-precise reason (uncapped excess) and a newly-precise partial-efficacy shape (helps det-mode consistently, not sto-mode) that should inform any future capped-excess or det/sto-aware redesign.**

