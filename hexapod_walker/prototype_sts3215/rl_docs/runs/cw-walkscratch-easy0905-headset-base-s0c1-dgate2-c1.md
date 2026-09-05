# cw-walkscratch-easy0905-headset-base-s0c1-dgate2-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-05T17:34:05+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1-acq1

**wandb_id**: j41igzz5

**hypothesis**: The FAILED s0c1-acq1 checkpoint walks fast with zero falls but chronically parks leg 4 at duty 0.03-0.07 (marginal underuse, NOT gSDE-style near-zero LEGPARK-SKATE, now closed for good). The prior repair attempt (headset-base-s0c1-dgate-c1, walk_duty_gate=0.9/floor=0.15) was CANARY FAIL - MECHANISM (INERT-DOSE): PPO's own training-time rollout noise already satisfies the lenient 0.15 floor even for a leg whose deterministic policy sits at 0.04-0.07, so almost no repair gradient reached eval-time behavior. This canary retries the SAME repair at a stronger, bank-proven dose (floor 0.15->0.35, ~2.3x; full gate strength g=1.0) that the new test_duty_gate_strong_floor_* bank (walkcurr-dutygate-strongfloor-bank-0905, 39/39 green) proves still leaves a healthy six-leg tripod's income untouched (leg-4 duty ~0.52 >> 0.35) while measurably increasing the price on a token-touchdown twin at the same ~0.05 duty magnitude as the real fingerprint (return drops from -432 to -536 on the identical trajectory, floor=0.15 vs 0.35).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): env/walk_duty_min and env/walk_duty_gate_factor must show REAL movement off the 0.15-floor plateau this exact checkpoint/dose combo already produced (not stuck at 0.9-1.0 the whole run the way the inert 0.9/0.15 dose did); det-mode leg-4 duty in the harness gate report should climb measurably above the 0.04-0.07 baseline (not necessarily clear the 0.10 sacrifice bar at 2M, but real movement toward it); no new falls vs the s0c1-acq1 baseline; slip/m not dramatically worse. FAIL if duty stays pinned at the exact same 0.04-0.07 baseline (still inert) or if a DIFFERENT leg parks or falls appear (destabilized). PASS licenses a 40M acquisition continuation to see if the base-family champion selection changes.

**verdict**: CANARY FAIL - MECHANISM (INERT-DOSE, reconfirmed at 2.3x dose). Result: stronger duty_gate_floor dose (0.15->0.35) does NOT unstick the chronically-parked leg-4 on the base-family heading walker; det-mode behavior is statistically identical to the parent (s0c1-acq1) checkpoint. Evidence: parent-matched gate reports both show walk/det gait_valid 0/6, leg[4] sacrificed all 6 episodes, duty 0.04-0.06 (child) vs 0.03-0.07 (parent); walk_startjitter/det is WORSE on the child (duty 0.01-0.03, swing_count 7-28/20s). Video (walk_det_*_sheet.png, walk_startjitter_det_2_sheet.png) shows the identical single-leg hitched/tucked pose. Why: env/walk_duty_gate_factor genuinely declined in training (1.0->0.56, real pricing, unlike the inert 0.15 dose that stayed pinned at 1.0) and ep_rew_mean rose every quarter (27->62->114->124) -- the same 08-21 rising-reward shape the concurrent cycle's sde-s2-c2-dgatefix-cont40m continued to 40M on, but that continuation's own outcome (factor RE-SATURATED by 40M, sacrifice unchanged) shows this shape does not reliably predict repair. policy_std is already at its schedule floor (0.135) at 2M yet sto-mode duty (0.16-0.23) still diverges sharply from det-mode duty (0.04-0.06): the training-time price is satisfied by noise-driven duty spikes that never move the policy mean. Closes 'raise duty_gate_floor magnitude alone' as a repair lever for the marginal-underuse class (2/2 doses inert). What's next: a real fix needs a mechanism the mean itself must satisfy (harder floor + explicit per-leg exploration anneal), a new mechanism+bank design question, not a relaunch of this lever; sibling headset-base-irr-dgate2-c1 (irr-timing/1g composition, same dose) still computing remotely on train-4, registered via evalpending, read before any further duty_gate_floor spend.

