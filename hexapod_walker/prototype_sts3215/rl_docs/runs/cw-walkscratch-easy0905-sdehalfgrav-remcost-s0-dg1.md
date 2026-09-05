# cw-walkscratch-easy0905-sdehalfgrav-remcost-s0-dg1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_FAIL

**created**: 2026-09-05T15:07:50+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-remcost-s0

**wandb_id**: 698t5lme

**hypothesis**: Plain English: sdehalfgrav-remcost-s0 also learned LEGPARK-SKATE (1/4 legs chronically parked) and the recency-based walk_gait_gate repair FAILED here too (4/4 closed, gate factor saturated at ceiling). This is the new duty-FRACTION gate (reward.walk_duty_gate=1.0, bank-verified 5/5 green this cycle) ported onto the remcost recipe's different term-cost pricing -- tests whether the mechanism generalizes off bare-sde. Single lever, cheap 2M canary before any 40M spend.

**gate**: MECHANISM-HEALTH CANARY: env/walk_duty_gate_factor should climb toward 1.0 (not saturate at ceiling the way walk_gait_gate_factor did), reward/speed not collapsing, 0 blowups. PASS funds a 40M acquisition continuation with the real gate (gait_valid majority, duty>=0.10 all legs); FAIL closes the lever on remcost too.

**verdict**: MECHANISM-HEALTH CANARY FAIL. env/walk_duty_gate_factor declined 1.0->0.92 over the 2M steps (correctly penalizing, not saturated/gamed). Det-mode reads gait_valid True / sac=[] in all 6 episodes -- no chronically-parked leg, so the specific LEGPARK exploit the parent showed (sac=[1,4], fwd 3.34m via a quadruped shuffle) IS broken. But the walk_det HUD/frame strip shows the robot did NOT replace it with walking: it is essentially FROZEN in a static crouch for the whole 20s episode (v=0.001-0.037 m/s vs ref 0.06 at multiple checked frames, net displacement 0.00-0.01m, only ~9deg body yaw drift, current mean ~0.2-0.3A i.e. not straining) -- a full-stasis dodge, not a marginal shuffle. This clears gait_valid/sac trivially because a leg that never lifts keeps duty near 1.0, comfortably above the 0.15 floor -- cheaper than walking, which necessarily drops a swinging leg's duty below ceiling. walk/sto (where the goal forces motion) is far worse: gait_valid 0/6, ALL 6 episodes end TERM tilt_roll/tilt_pitch (falls) with slip 3-14x the ~2.9 teacher band. Reward trajectory (-690/-787/-775/-897 at matched absolute env steps) tracks almost exactly the UN-gated parent's OWN trajectory over the identical step range (-648/-760/-827/-850) -- NOT a reward collapse relative to baseline, this recipe's reward is already this negative from term_cost pricing regardless of duty_gate. Context: this recipe (remcost = term_cost_per_remaining_s/term_cost_max) was built specifically to stop a sprint-then-fall exploit by charging early death, and its own launch hypothesis explicitly named 'policy retreats to the ~0-income park basin' as the predicted FAILURE mode if the pricing over-corrects toward fall-aversion -- that is exactly what this canary shows once duty_gate closes off the shuffle income route: the heavily fall-averse policy retreated to total stasis rather than search for a new gait in 2M. CLOSES the instant-full-dose walk_duty_gate warm-start repair on the remcost recipe -- does NOT fund a 40M acquisition off this checkpoint. Next: cw-walkscratch-easy0905-sdehalfgrav-dgfresh-s0 (from-scratch, duty_gate=1.0 from step 0, no remcost term_cost, launched this cycle) isolates whether duty_gate alone (without remcost's fall-aversion pricing or a warm-start shock) is survivable at 0.5g.

