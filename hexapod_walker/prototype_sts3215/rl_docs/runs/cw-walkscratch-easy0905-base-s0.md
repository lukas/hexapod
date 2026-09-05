# cw-walkscratch-easy0905-base-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T08:26:05+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**wandb_id**: 706y3op2

**hypothesis**: Plain English: teacher-free PPO never learned to walk on the realistic sim, so this operator-ordered pilot makes the simulation deliberately EASY and removes the stand-still reward windfall to test whether walking emerges at all. Easy levers vs the retired litrep wave: zero servo latency/deadband/sensor noise, 3x torque, 360 deg/s velocity ceiling (was ~35), 30 deg tilt envelope, inert current trip, struct comp off, command on from tick 0 (new goal.walk_cmd_hold_s/walk_cmd_ramp_s=0 kill the ~+200 opening K_WALK windfall), freeprog income k=2/cap 0.06 with 0.1 s EMA, stance-centered action box on the TRUE robot_abs plant (knee bias 35 -> knee_abs 100; the old 15 was ~20 deg off), gamma .995/lam .97/n_steps 128, 256,256,128 ELU from scratch. mesh_mjx 4.81 kg twin @100 Hz. No teacher/BC/phase/clock/motion prior anywhere. Arm: base seed 0.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism-health canary (NOT a walking gate): finite losses; weights changing; real joint/foot excursion beyond the settled stance on eval video/telemetry; motor contract logged at 360 deg/s (no hidden cruise limiter); per-tick reward agrees with the WALKSCRATCH_EASY bank (park ~0, movement income positive, NO opening-stop windfall). Healthy -> pre-registered +18M continuation from OWN checkpoint only. No-walk-at-2M is NOT a failure; stop only for nonfinite training / no-op actions / implementation failure / proven exploit. Recipe+proof: rl_docs/tracks/walkcurr/EASY_PILOT_20260905.md (tests 13/13), snapshot 8c418c1b.

**verdict**: CANARY PASS (mechanism-health scope only, no skill claim). Finite losses (value_loss 1435->854, EV rising 0->0.04), weights/metrics evolving, std anneal on schedule (0.37->0.22), real motion (walk_speed ~0.11 m/s, mean current 1.36 A), motor contract logged resolved_vel_max=360 deg/s slew=3.6 deg/tick (no hidden limiter), GPU physics VERIFIED warp/4096. Reward agrees with WALKSCRATCH_EASY bank: reward_walk positive (+0.17->+0.24/tick), no opening windfall, zero terminations. Declining ep_rew (-124->-532) is a LENGTH ARTIFACT: ep_len 100->486 with per-tick freeprog cross-drift charge (-1.96->-1.69/tick, improving); per-tick total improving (-1.24->-1.09), v_along_cmd rising through zero to +0.008 m/s. Next: pre-registered own-checkpoint acquisition continuation (40M per operator 09-05 full-fleet order).

