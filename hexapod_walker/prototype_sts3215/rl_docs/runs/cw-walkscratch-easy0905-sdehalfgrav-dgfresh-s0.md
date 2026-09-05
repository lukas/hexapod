# cw-walkscratch-easy0905-sdehalfgrav-dgfresh-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-05T15:53:26+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**wandb_id**: c3kd1elp

**hypothesis**: Plain English: same mechanism-isolation question as sde-dgfresh-s0 (does walk_duty_gate=1.0 let genuine six-leg walking emerge from a FRESH init, vs the warm-started dg1 cohort's freeze/spin collapse) but on the half-gravity cell, which is the OTHER physics cell the dg1 batch's remcost arms failed on. This is the cleaner half of that question too: remcost adds heavy term_cost pricing on top of gravity+gSDE, so testing plain sdehalfgrav (no remcost) isolates whether duty_gate alone is survivable at 0.5g before blaming remcost's fall-aversion for the freeze. Identical to cw-walkscratch-easy0905-sdehalfgrav-s0 except reward.walk_duty_gate=1.0 from step 0.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism-health canary (not a walking gate): env/walk_duty_gate_factor not saturated near 1.0 while duty is measurably low; walk_speed / net displacement clearly nonzero and not decaying to a frozen stance by the final quarter; reward not pinned flat at a near-zero constant. PASS reopens walk_duty_gate as viable on this cell; FAIL (freeze/park) means the mechanism needs an explicit anti-idle-charge complement (reward.k_walk_idle_charge, already implemented) before further spend, independent of remcost.

**verdict**: CANARY FAIL - MECHANISM: FULL FREEZE at 0.5g, mirrors the 1g bare-sde dgfresh pair exactly -- disambiguates that the freeze is intrinsic to walk_duty_gate=1.0 from scratch, not caused by remcost pricing, warm-starting, or full gravity specifically. Evidence: det walk fwd med 0.07m/20s, identical to 2 decimals across all 6 episodes (video walk_det_0..5.png: static splayed-leg pose, no swinging leg at any sampled tick), slip_per_m 90.1 (near-zero-displacement artifact), env/walk_duty_gate_factor 0.92-1.0 for the entire 2M run, ep_rew_mean quarters -248/-335/-383/-363 (worsening then flat-negative, not rising -- not the 08-21 ambiguous case). sto/startjitter modes: 0/6 and 0/6 gait_valid, every episode falls or drifts with 2-4 legs sacrificed -- fragile, not a hidden success. Why: same as sde-dgfresh-s0b -- a trailing-duty floor alone is trivially satisfied by 6-leg stasis with zero net motion. Next: no further bare walk_duty_gate arm on this or the sde cell without pairing reward.k_walk_idle_charge (anti-park travel floor, implemented, 0 in every arm to date); CURRENT_TRUTHS.md updated with the 3/3 disambiguation.

