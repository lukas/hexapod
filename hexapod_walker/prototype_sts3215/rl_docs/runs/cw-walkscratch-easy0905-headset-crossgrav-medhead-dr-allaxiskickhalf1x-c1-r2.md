# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf1x-c1-r2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T09:29:15+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf1x-c1

**wandb_id**: mfwj180i

**hypothesis**: Plain English: does the champion survive ALL ~30 nominal realism axes at once when the one individually-fatal ingredient (full-dose kick, kick1x-c1 fell) is capped at its proven-safe half dose (dr.walk_kick_prob=0.15, kickhalf1x-c1 PASS 21/24 0 falls)? Retry of allaxiskickhalf1x-c1, which was REFUSED at launch by a stale pod code-marker (train-8 dirty vs local HEAD) -- code is now synced, config unchanged.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the 4-panel harness, no NEW chronic single-leg sacrifice, 0 falls -- clean single-axis tolerance composes to full (kick-safe) realism. FAIL/INFORMATIVE-NEGATIVE if gait_valid <12/24, a new chronic leg, or any fall -- axes interact even with every ingredient individually clean, and the DR-rung needs acquisition-scale training against the full stack.

**verdict**: CANARY FAIL - MECHANISM: capping the one previously-fatal ingredient (walk_kick_prob) to its proven-safe half dose does NOT rescue the full ~30-axis realism composite. 7/24 episodes terminate tilt_roll (0/6 det, 1/6 sto, 2/6 startjitter/det, 4/6 startjitter/sto) -- falls concentrate hardest in the startjitter modes (harder/perturbed start conditions), the same shape as the plain all-axis composite's (allaxis1x-c1) prior CANARY FAIL. Aggregate gait_valid 21/24 looks like a majority-pass in isolation, but this gate's own stated criterion is 0 falls / any fall = FAIL, and frame strips of the terminated episodes (walk_startjitter_sto_3, _sto_4, det_1) show the same progressive body-tilt-then-cutoff pattern already diagnosed on allaxis1x-c1. Kick dose was NOT the sole broken ingredient for the full composite -- axes still interact when ~30 are stacked together even with kick capped safe. Answers QUEUE AIM item (1)'s second half: the kick-safe composite also needs acquisition-scale training exposure (or a further bisection of which OTHER axis pair interacts) before it can be called safe, not just a kick-dose fix.

