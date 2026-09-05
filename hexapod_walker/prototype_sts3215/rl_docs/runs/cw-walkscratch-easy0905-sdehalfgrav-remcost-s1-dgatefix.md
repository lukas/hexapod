# cw-walkscratch-easy0905-sdehalfgrav-remcost-s1-dgatefix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-05T16:09:12+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-remcost-s1

**wandb_id**: m9sj7qzp

**hypothesis**: Plain English: remcost-s1's own 40M sdehalfgrav-remcost checkpoint learned LEGPARK-SKATE under the remcost term-cost recipe (ACQ CONTINUE verdict, legs chronically parked). The mechanism-health batch's own remcost dg1 arms were actually FRESH-FROM-SCRATCH (respec provenance bug, no --init-from at all) and went to full-freeze -- informative but not a test of curing THIS entrenched checkpoint. This arm hand-builds the vector so --init-from points at the checkpoint's own real output, the actual entrenched-checkpoint question for the remcost recipe.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): watch env/walk_duty_gate_factor climb toward 1.0 (not saturate at ceiling despite harness-flagged sacrifice) alongside ep_rew_mean/env/walk_speed not collapsing to termination-dominated. PASS (funds 40M acquisition): harness walk/det gait_valid >=4/6 with duty_cycle>=0.10 on every leg. FAIL: factor saturates while a leg stays <0.10 duty, full-freeze (near-zero net displacement) substitutes for the sacrifice, or reward/speed collapses.

**verdict**: CANARY FAIL - MECHANISM: walk_duty_gate=1.0 on sdehalfgrav-remcost-s1's own entrenched 40M LEGPARK-SKATE checkpoint does NOT clear the funding bar in 2M -- harness walk/det gait_valid 0/6 (also 0/6 startjitter/det), legs 1 AND 4 stuck at 0.00 duty in every det episode (others 0.31-0.52), video (walk_det_0..5.png) shows the same two legs rigidly extended/dragging every clip, slip/m 2.25 (within the ~2.9 teacher band), speed 0.171 m/s (real ~2.6m/20s forward progress -- NOT a full-freeze). Matches sibling s0-dgatefix (this same batch) almost exactly: env/walk_duty_gate_factor genuinely DECLINES 1.0->0.66 (real ungamed pressure) while ep_rew_mean quarters WORSEN monotonically (-322->-416->-465->-582), the opposite of the 08-21 continue case -- 2/2 seed confirmation that for the remcost recipe, an already-entrenched two-leg-park exploiter absorbs the new penalty without escaping within 2M. Closes the entrenched-checkpoint duty_gate cure on remcost at n=2 same-budget; leaves a longer continuation (not a new price/termination lever) as the only untried option on these two exact checkpoints.

