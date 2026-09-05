# cw-walkscratch-easy0905-base-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T08:28:36+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**wandb_id**: 3ysuqplh

**hypothesis**: Plain English: teacher-free PPO never learned to walk on the realistic sim, so this operator-ordered pilot makes the simulation deliberately EASY and removes the stand-still reward windfall to test whether walking emerges at all. Easy levers vs the retired litrep wave: zero servo latency/deadband/sensor noise, 3x torque, 360 deg/s velocity ceiling (was ~35), 30 deg tilt envelope, inert current trip, struct comp off, command on from tick 0 (new goal.walk_cmd_hold_s/walk_cmd_ramp_s=0 kill the ~+200 opening K_WALK windfall), freeprog income k=2/cap 0.06 with 0.1 s EMA, stance-centered action box on the TRUE robot_abs plant (knee bias 35 -> knee_abs 100; the old 15 was ~20 deg off), gamma .995/lam .97/n_steps 128, 256,256,128 ELU from scratch. mesh_mjx 4.81 kg twin @100 Hz. No teacher/BC/phase/clock/motion prior anywhere. Arm: base seed 1 (seed replication of base-s0; no other change).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism-health canary (NOT a walking gate): finite losses; weights changing; real joint/foot excursion beyond the settled stance on eval video/telemetry; motor contract logged at 360 deg/s (no hidden cruise limiter); per-tick reward agrees with the WALKSCRATCH_EASY bank (park ~0, movement income positive, NO opening-stop windfall). Healthy -> pre-registered +18M continuation from OWN checkpoint only. No-walk-at-2M is NOT a failure; stop only for nonfinite training / no-op actions / implementation failure / proven exploit. Recipe+proof: rl_docs/tracks/walkcurr/EASY_PILOT_20260905.md (tests 13/13), snapshot 8c418c1b.

**verdict**: CANARY PASS (mechanism-health scope only, no skill claim). Seed replicate of base-s0, same healthy fingerprint: finite losses (value_loss 1430->845, EV 0->0.03), std anneal on schedule, real motion (walk_speed ~0.11 m/s), motor contract 360 deg/s, reward bank-consistent (reward_walk +0.18->+0.25/tick, no windfall, zero terminations). ep_rew decline (-136->-543) is the same ep_len artifact (102->490); per-tick improving, v_along_cmd +0.0017->+0.010 m/s (best of the two base seeds). Next: pre-registered own-checkpoint 40M acquisition continuation (operator 09-05 order).

