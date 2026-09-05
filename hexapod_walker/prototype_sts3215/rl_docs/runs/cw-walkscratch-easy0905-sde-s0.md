# cw-walkscratch-easy0905-sde-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T08:29:52+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**wandb_id**: fqwncrsp

**hypothesis**: Plain English: teacher-free PPO never learned to walk on the realistic sim, so this operator-ordered pilot makes the simulation deliberately EASY and removes the stand-still reward windfall to test whether walking emerges at all. Easy levers vs the retired litrep wave: zero servo latency/deadband/sensor noise, 3x torque, 360 deg/s velocity ceiling (was ~35), 30 deg tilt envelope, inert current trip, struct comp off, command on from tick 0 (new goal.walk_cmd_hold_s/walk_cmd_ramp_s=0 kill the ~+200 opening K_WALK windfall), freeprog income k=2/cap 0.06 with 0.1 s EMA, stance-centered action box on the TRUE robot_abs plant (knee bias 35 -> knee_abs 100; the old 15 was ~20 deg off), gamma .995/lam .97/n_steps 128, 256,256,128 ELU from scratch. mesh_mjx 4.81 kg twin @100 Hz. No teacher/BC/phase/clock/motion prior anywhere. Arm: gSDE — ONLY change vs base-s0 is --use-sde with resample every 20 ticks (0.2 s); hypothesis: temporally-correlated exploration converts the freeprog gradient into sustained strides where per-tick Gaussian noise dithers in place.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism-health canary (NOT a walking gate): finite losses; weights changing; real joint/foot excursion beyond the settled stance on eval video/telemetry; motor contract logged at 360 deg/s (no hidden cruise limiter); per-tick reward agrees with the WALKSCRATCH_EASY bank (park ~0, movement income positive, NO opening-stop windfall). Healthy -> pre-registered +18M continuation from OWN checkpoint only. No-walk-at-2M is NOT a failure; stop only for nonfinite training / no-op actions / implementation failure / proven exploit. Recipe+proof: rl_docs/tracks/walkcurr/EASY_PILOT_20260905.md (tests 13/13), snapshot 8c418c1b.

**verdict**: CANARY PASS (mechanism-health scope only, no skill claim). gSDE arm learning with a distinct exploration signature, all gates green: finite losses (value_loss 2370->1788), motor contract 360 deg/s, reward bank-consistent. REALIZED ACTION AMPLITUDE >> base at the same annealed log_std (per fb_20260905T080341_ef45b6 item 3, recorded): entropy_loss -40 vs base -7.5, action_delta charge 10x base (-0.113 vs -0.010/tick), walk_speed 0.28 vs 0.11 m/s, some dynamic falls (reward_termination -0.05/tick vs 0). Still healthy: ep_len rising 117->282, v_along_cmd +0.017 m/s at 2M = best of cohort, freeprog charge stable. Continuation MUST NOT pass --use-sde/--activation-fn (plain --init-from rejects both; PPO.load preserves gSDE+ELU from checkpoint). Next: own-checkpoint 40M acquisition continuation.

