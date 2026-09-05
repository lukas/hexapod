# cw-walkscratch-easy0905-sdehalfgrav-remcost-s0-dgatefix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-05T16:07:55+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-remcost-s0

**wandb_id**: mmbhvbzs

**hypothesis**: Plain English: remcost-s0's own 40M sdehalfgrav-remcost checkpoint learned LEGPARK-SKATE under the remcost term-cost recipe (ACQ CONTINUE verdict, legs chronically parked). The mechanism-health batch's own remcost dg1 arms were actually FRESH-FROM-SCRATCH (respec provenance bug, no --init-from at all) and went to full-freeze -- informative but not a test of curing THIS entrenched checkpoint. This arm hand-builds the vector so --init-from points at the checkpoint's own real output, the actual entrenched-checkpoint question for the remcost recipe.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): watch env/walk_duty_gate_factor climb toward 1.0 (not saturate at ceiling despite harness-flagged sacrifice) alongside ep_rew_mean/env/walk_speed not collapsing to termination-dominated. PASS (funds 40M acquisition): harness walk/det gait_valid >=4/6 with duty_cycle>=0.10 on every leg. FAIL: factor saturates while a leg stays <0.10 duty, full-freeze (near-zero net displacement) substitutes for the sacrifice, or reward/speed collapses.

**verdict**: CANARY FAIL - MECHANISM: walk_duty_gate=1.0 on sdehalfgrav-remcost-s0's own entrenched 40M LEGPARK-SKATE checkpoint does NOT clear the funding bar in 2M -- harness walk/det gait_valid 0/6 (also 0/6 startjitter/det), legs 1 AND 4 stuck at 0.01 duty in every det episode (others 0.27-0.33), video (walk_det_0..5.png) shows the same two legs rigidly extended/dragging every clip, slip/m 1.53 (within the ~2.9 teacher band, notably better than bare-sde), speed 0.264 m/s (healthy, real ~4.6m/20s forward progress -- NOT a full-freeze). Unlike the closed walk_gait_gate lever, env/walk_duty_gate_factor genuinely DECLINES 1.0->0.72 across training (real, ungamed penalizing pressure). BUT ep_rew_mean quarters WORSEN monotonically across the whole run (-344->-415->-472->-495) even as the factor declines and speed holds steady -- this is the opposite of the 08-21 rising-reward-bad-eval continue case: the entrenched two-leg-parked skate is being priced increasingly harshly without any behavioral escape appearing within budget, i.e. the exploiter is simply accumulating more penalty for the same frozen behavior. Read as: for this recipe (remcost's term_cost pricing + an already 40M-entrenched two-leg-park), duty_gate applies real pressure but the local optimum is too committed to unlearn in 2M -- closes this specific combination as a same-budget cure; a longer continuation (not a new mechanism) is the only untried lever left on this exact checkpoint.

