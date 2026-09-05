# cw-walkscratch-easy0905-halfgrav-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T08:27:20+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**wandb_id**: 0vll8nk4

**hypothesis**: Plain English: teacher-free PPO never learned to walk on the realistic sim, so this operator-ordered pilot makes the simulation deliberately EASY and removes the stand-still reward windfall to test whether walking emerges at all. Easy levers vs the retired litrep wave: zero servo latency/deadband/sensor noise, 3x torque, 360 deg/s velocity ceiling (was ~35), 30 deg tilt envelope, inert current trip, struct comp off, command on from tick 0 (new goal.walk_cmd_hold_s/walk_cmd_ramp_s=0 kill the ~+200 opening K_WALK windfall), freeprog income k=2/cap 0.06 with 0.1 s EMA, stance-centered action box on the TRUE robot_abs plant (knee bias 35 -> knee_abs 100; the old 15 was ~20 deg off), gamma .995/lam .97/n_steps 128, 256,256,128 ELU from scratch. mesh_mjx 4.81 kg twin @100 Hz. No teacher/BC/phase/clock/motion prior anywhere. Arm: half gravity — ONLY change vs base-s0 is ease.gravity_scale=0.5 (supported per-world MJX easing path; Yu-2018 removable-assist analog); hypothesis: at half weight support/swing is easier and stepping emerges earlier. Evaluated at its OWN gravity; full-gravity is a later diagnostic, never automatic promotion.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism-health canary (NOT a walking gate): finite losses; weights changing; real joint/foot excursion beyond the settled stance on eval video/telemetry; motor contract logged at 360 deg/s (no hidden cruise limiter); per-tick reward agrees with the WALKSCRATCH_EASY bank (park ~0, movement income positive, NO opening-stop windfall). Healthy -> pre-registered +18M continuation from OWN checkpoint only. No-walk-at-2M is NOT a failure; stop only for nonfinite training / no-op actions / implementation failure / proven exploit. Recipe+proof: rl_docs/tracks/walkcurr/EASY_PILOT_20260905.md (tests 13/13), snapshot 8c418c1b.

**verdict**: CANARY PASS (mechanism-health scope only, no skill claim; evaluated at its OWN 0.5g). Same healthy fingerprint as base: finite losses, std anneal on schedule, real motion (walk_speed ~0.11 m/s at lower current 1.16 A, consistent with half weight), motor contract 360 deg/s, reward bank-consistent (reward_walk +0.16->+0.23/tick, no windfall, zero terminations), ep_rew decline = ep_len artifact (100->486), v_along_cmd rising to +0.008 m/s. Gravity easing verified live: height sits lower-variance, currents ~15% below base. Next: own-checkpoint 40M acquisition continuation at 0.5g; full-gravity remains a later diagnostic, never automatic promotion.

