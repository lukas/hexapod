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

**verdict**: CORRECTED (provenance): a respec-clone gotcha (banked in CURRENT_TRUTHS by a concurrent cycle after my first pass) means this run carried NO --init-from at all -- it trained FULLY FROM SCRATCH with reward.walk_duty_gate=1.0 active from step 0, on top of the sdehalfgrav-remcost recipe (0.5g + term_cost_per_remaining_s=100/term_cost_max=450), NOT a warm-start off the parent's own LEGPARK-shuffle checkpoint as my first pass assumed. This is actually a CLEANER read than intended: does duty_gate + remcost's term_cost pricing, together, from scratch, produce real walking? Answer: NO. env/walk_duty_gate_factor declined 1.0->0.92 (penalizing correctly, not gamed). Det-mode gait_valid True/sac=[] (no leg ever sacrificed -- the mechanism prevents that from ever forming) but the robot is essentially FROZEN the whole 20s episode (v=0.001-0.037 m/s vs ref 0.06, net displacement 0.00-0.01m, ~9deg yaw drift only, current ~0.2-0.3A i.e. not straining/exploring). walk/sto (goal forces motion): gait_valid 0/6, ALL 6 TERM tilt_roll/pitch (falls), slip 3-14x band. Reward (-690/-787/-775/-897 at matched steps) matches the UN-gated sdehalfgrav-remcost-s0 parent's own from-scratch trajectory almost exactly (-648/-760/-827/-850) -- not a new collapse, remcost is already this negative from term_cost alone. This IS exactly what the remcost recipe's own launch hypothesis predicted as its failure mode ('retreat to the ~0-income park basin') if term_cost over-corrects toward fall-aversion -- confirmed directly, from scratch, no warm-start confound needed. CLOSES 'walk_duty_gate=1.0 + remcost term_cost, from scratch' as a repair recipe -- does not fund a 40M acquisition. Isolation follow-up (cw-walkscratch-easy0905-sdehalfgrav-dgfresh-s0, duty_gate=1.0 from scratch, NO remcost pricing) launched this cycle tests whether removing remcost's term_cost alone lets real walking emerge.

