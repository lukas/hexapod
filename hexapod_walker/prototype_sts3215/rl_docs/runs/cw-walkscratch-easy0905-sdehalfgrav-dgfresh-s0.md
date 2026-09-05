# cw-walkscratch-easy0905-sdehalfgrav-dgfresh-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T15:53:26+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**wandb_id**: c3kd1elp

**hypothesis**: Plain English: same mechanism-isolation question as sde-dgfresh-s0 (does walk_duty_gate=1.0 let genuine six-leg walking emerge from a FRESH init, vs the warm-started dg1 cohort's freeze/spin collapse) but on the half-gravity cell, which is the OTHER physics cell the dg1 batch's remcost arms failed on. This is the cleaner half of that question too: remcost adds heavy term_cost pricing on top of gravity+gSDE, so testing plain sdehalfgrav (no remcost) isolates whether duty_gate alone is survivable at 0.5g before blaming remcost's fall-aversion for the freeze. Identical to cw-walkscratch-easy0905-sdehalfgrav-s0 except reward.walk_duty_gate=1.0 from step 0.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism-health canary (not a walking gate): env/walk_duty_gate_factor not saturated near 1.0 while duty is measurably low; walk_speed / net displacement clearly nonzero and not decaying to a frozen stance by the final quarter; reward not pinned flat at a near-zero constant. PASS reopens walk_duty_gate as viable on this cell; FAIL (freeze/park) means the mechanism needs an explicit anti-idle-charge complement (reward.k_walk_idle_charge, already implemented) before further spend, independent of remcost.

