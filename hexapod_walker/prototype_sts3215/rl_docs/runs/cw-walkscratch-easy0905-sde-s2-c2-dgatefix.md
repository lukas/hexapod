# cw-walkscratch-easy0905-sde-s2-c2-dgatefix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-05T16:06:39+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sde-s2-c2

**wandb_id**: jw13d0rn

**hypothesis**: Plain English: sde-s2-c2 learned LEGPARK-SKATE (chronically parks a leg, rides income from the rest). walk_duty_gate already showed a real det-mode escape when applied from an early undifferentiated checkpoint (sde-s1-dg1, PASS) and its companion continuation off the SAME kind of early checkpoint spun/destabilized instead (sde-s2-dg1, FAIL) -- neither actually tested the entrenched-checkpoint case due to a respec provenance bug. This arm (n=2 alongside sde-s1-c2-dgatefix) fixes that: --init-from points at sde_s2_c2.zip itself, hand-built via backlog add. Does walk_duty_gate bring an ALREADY-parked leg back down on a second independent seed?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): watch env/walk_duty_gate_factor climb toward 1.0 (not saturate at ceiling despite harness-flagged sacrifice) alongside ep_rew_mean/env/walk_speed not collapsing to termination-dominated. PASS (funds 40M acquisition): harness walk/det gait_valid >=4/6 with duty_cycle>=0.10 on every leg. FAIL: factor saturates while a leg stays <0.10 duty, full-freeze (near-zero net displacement) substitutes for the sacrifice, or reward/speed collapses.

**verdict**: CANARY FAIL - MECHANISM: walk_duty_gate=1.0 on sde-s2-c2's own entrenched 40M LEGPARK-SKATE checkpoint does NOT clear the funding bar in 2M -- harness walk/det gait_valid 0/6 (also 0/6 startjitter/det), leg 1 duty stuck at 0.01 in every det episode (other legs 0.35-0.94), video (walk_det_0..5.png) shows that same leg rigidly extended/dragging the whole clip, slip/m 3.6-4.6 (vs the ~2.9 teacher band), speed only 0.088 m/s. This is a DIFFERENT failure signature than the previously-closed levers though: env/walk_duty_gate_factor genuinely DECLINES 1.0->0.64 across training (correctly penalizing the sacrifice, not saturating at ceiling the way the closed walk_gait_gate lever did) and there is no full-freeze substitution (real ~1.5m/20s net progress). ep_rew_mean quarters are RISING throughout (94->224->332->406), the 08-21 rising-reward/bad-eval pattern. Read as: mechanism is behaving as designed (real, ungamed pressure) but 2M is not enough budget to walk the entrenched exploiter out of the sacrifice basin -- evidence for 'needs longer budget on this exact recipe', not evidence the mechanism itself is unsound. Contrast with the sdehalfgrav+remcost siblings in this same batch, whose reward gets WORSE not better under the identical mechanism -- do not generalize this one seed's promising trend to the whole entrenched-checkpoint question without a 2nd bare-sde confirmation or a longer continuation.

