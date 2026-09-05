# cw-walkscratch-easy0905-headset-base-irr-swinggate-fix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-05T21:42:58+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-irr-acq1

**wandb_id**: 4rnm653m

**hypothesis**: Batch member 3/3 of the entrenched-checkpoint swing_gate retrofit question (siblings: swinggate-fix on s0c1_acq1, medhead-swinggate-fix on medhead_acq1): does reward.walk_swing_gate cure the base(1g)-family leg favoritism on a third entrenched 40M champion (headset-base-irr-acq1, ACQ FAIL under the irregular-timing axis)? Completes the n=3 entrenched-checkpoint batch before concluding swing_gate does/doesn't repair already-entrenched exploiters on this family.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M): repair-signal if the chronically-sacrificed leg's duty majority-clears the harness gait_valid duty>0.10 bar with 0 new falls. FAIL - MECHANISM if the same leg stays chronically parked in a majority of episodes regardless of walk_swing_gate_factor showing real decline. Read as part of the n=3 entrenched-checkpoint batch (s0c1, medhead, irr).

**verdict**: CANARY FAIL - MECHANISM (engaged, no repair; entrenched-checkpoint retrofit on irr_acq1): the retrofit's per-mode gait_valid tally (walk/det 3/6, walk/sto 6/6, walk_startjitter/det 3/6, walk_startjitter/sto 5/6 = 17/24) is statistically indistinguishable from the undosed irr_acq1 twin's own baseline (3/6, 6/6, 3/6, 6/6 = 18/24) -- same alternating leg1/4 sacrifice pattern in the same two det-adjacent modes, one fewer clean episode overall (noise, not a trend: startjitter/sto slipped from 6/6 to 5/6, everything else matches exactly). 2M of walk_swing_gate=1.0 produced no majority-clearing repair signal. 0 new falls (terms 0 all modes, matching twin). 4th and last of the swing_gate batch this cycle: all 4 arms (fresh + 3 entrenched retrofits) now read FAIL -- 2 cleanly INERT (fresh, s0c1-fix: harness numbers essentially unchanged vs their own undosed twins), 2 noise-level marginal with no majority-clearing repair (medhead-fix, irr-fix). **This closes reward.walk_swing_gate end-to-end as a per-leg-utilization repair lever for the base(1g) family, the 7th independently-designed mechanism to fail after walk_gait_gate+k_step_event (6/6 FAIL) and walk_duty_gate (9/9 FAIL across every provenance x dose).** The next lever for this family must be structural (curriculum-widen from a leg-healthy champion the way halfgrav's widen2 is doing, a different exploration/init scheme, or accepting the base(1g) family's per-leg pathology as closed and reallocating spend to the healthy halfgrav lineage) rather than another reward-shaping variant -- do not fund a further reward-price mechanism for base-family leg favoritism without a genuinely new causal theory. Evidence: ops.sh report logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_irr_swinggate_fix_gate/report.json vs logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_irr_acq1_gate/report.json, W&B run page, plus the 3 sibling verdicts this cycle (swinggate-fresh, swinggate-fix, medhead-swinggate-fix).

