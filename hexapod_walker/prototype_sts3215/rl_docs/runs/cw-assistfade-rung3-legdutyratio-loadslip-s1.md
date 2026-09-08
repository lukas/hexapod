# cw-assistfade-rung3-legdutyratio-loadslip-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-08T13:17:49+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-assistfade-rung3-legdutyratio-s1

**wandb_id**: xy50u8mx

**hypothesis**: Same as the s0 sibling (cw-assistfade-rung3-legdutyratio-loadslip-s0): does directly pricing per-leg relative load-slip on top of the already-on duty-ratio charge fix rung3's chronic leg-sacrifice-plus-drift FAIL, where the swing-count-floor add-on already failed on BOTH seeds (CANARY FAIL - MECHANISM)? Second seed of the same lever, matched to the legdutyratio-s1/swingfloor-s1 lineage (leg[0,5] sacrifice pattern) so a 2-seed read is available before drawing any track-level conclusion, same discipline the swing-floor arms used.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same criteria as the s0 sibling's gate text (mechanism-health canary only; (a) telemetry engages finite post-grace; (b) zero new falls vs the matched legdutyratio-s1 sibling; (c) per-leg duty/slip narrows vs BOTH legdutyratio-s1 and the already-FAIL swingfloor-s1 sibling without new regression). Read s0+s1 together before any track-level verdict -- do not pool a single seed.

**verdict**: CANARY FAIL - MECHANISM. Same shape as the matched s0 sibling: outright regression on the gate's primary walk/det+sto panel, not a narrowing. walk/det: slip med 17.02->18.56m (worse), prog med 0.05->-0.02 (worse, net-zero/negative displacement); gait_valid ticks 0/6->6/6 but every episode's own fwd distance is ~0.02m -- a near-stationary pose, not six-leg walking (contact sheet walk_det_0.png shows the robot settle into a crouch in frame 1 and hold that pose the rest of the 20s episode). walk/sto: slip med 15.56->14.73 (mild improve) but prog med 0.05->-0.01 (worse) AND 2 NEW over_current terminations appear (0->2) -- a regression the mild slip number doesn't offset. walk_startjitter/det stays 0/6 gait_valid, 6/6 terms both sides (no change); walk_startjitter/sto flat at 2/6. Gate criterion (a) telemetry PASSES: the NEW per-leg mechanism's own env/walk_leg_loadslip_ratio_excess is finite post-grace and stays in a modest, non-saturating 0.085-0.22 band the whole window (NOT climbing/escalating) -- correcting an earlier draft of this verdict that mistakenly cited the OLD, unrelated env/walk_loadslip_ratio (a pre-existing episode-cumulative slip/progress metric already in this recipe's reward stack, climbing 0.065->5.69 independent of this charge) as if it were this mechanism's own telemetry; per the matched s0 verdict's own correct framing, that shared pre-existing metric's trend is NOT diagnostic of the new charge and training-reward collapse (peak +130..+210 -> final -2293.6) is driven mostly by the collapsing walk/progress reward itself (consistent with the eval panel's near-zero/negative displacement) plus the pre-existing duty-ratio charge escalating (-0.1->-11.5) and the old loadslip_excess charge (small, to -0.29), not by an escalating NEW charge. Criterion (b) new-falls is VIOLATED (walk/sto +2 terminations); criterion (c) narrowing is not observed on the primary panel -- the same 'outright worse' clause that failed s0. This is the 2nd-of-2 assistfade rung3 seeds to FAIL this mechanism (matches s0's outright-worse verdict); load-slip-ratio-charge now closes 2/2 FAIL-MECHANISM on assistfade rung3, same as swing-count-floor's earlier 2/2 FAIL-MECHANISM close on this lineage -- neither of the two named per-leg add-ons repairs rung3's chronic-leg/drift problem; a new mechanism design (not another dose/seed of either) is needed before further rung3 spend. Evidence: ops.sh review cw-assistfade-rung3-legdutyratio-loadslip-s1; logs/ckpt_eval/cw_assistfade_rung3_legdutyratio_loadslip_s1_gate/report.json vs cw_assistfade_rung3_legdutyratio_s1_gate/report.json; logs/experiments/cw-assistfade-rung3-legdutyratio-loadslip-s1/wandb_history.csv (env/walk_leg_loadslip_ratio_excess column, NOT env/walk_loadslip_ratio); W&B xy50u8mx.

