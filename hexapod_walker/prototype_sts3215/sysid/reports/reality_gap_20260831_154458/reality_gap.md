# Hexapod Sim Reality Report

- generated: 2026-08-31T15:44:59
- git: `df28a138`
- servo params `air`: sim_model.json (6968268e879e)
- servo params `loaded`: sim_model_loaded.json (144d43fa5dd3)
- servo params `rl_move/sim/sim_model_sysid.json`: sim_model_sysid.json (8b8d2f260256)

## Headline gap metrics

| trace | metric | hardware | sim air | sim loaded | sim rl_move/sim/sim_model_sysid.json |
|---|---|---|---|---|---|
| sysid_servo_spread_ground_5deg_v1_20260831_224252.csv | unloaded q_rmse_deg | — | 0.247 | 0.224 | 0.124 |
| sysid_servo_spread_ground_5deg_v1_20260831_224252.csv | unloaded qd_rmse_deg_s | — | 0.71 | 1.2 | 0.68 |
| sysid_servo_spread_ground_5deg_v1_20260831_224252.csv | cmd→motion latency (hw) | median 120.0 ms (p10 80.0 / p90 160.1 / max 217.9, n=36) | — | — | — |

## Timing (hardware)

- **sysid_servo_spread_ground_5deg_v1_20260831_224252.csv**: tick median 40.0 ms (nominal 40.0, p95 40.6, late 0.07%); send→recv RTT median 8.2 ms (p95 11.6)

## Servo-to-servo variation (t90)

- sysid_servo_spread_ground_5deg_v1_20260831_224252.csv [yaw]: median 480.0 ms over 6 joints, spread 6.6%
- sysid_servo_spread_ground_5deg_v1_20260831_224252.csv [hip]: median 530.0 ms over 6 joints, spread 7.5%
- sysid_servo_spread_ground_5deg_v1_20260831_224252.csv [knee]: median 500.0 ms over 6 joints, spread 4.6%

## Per-segment detail

### sysid_servo_spread_ground_5deg_v1_20260831_224252.csv

| segment | hardware | sim air | sim loaded | sim rl_move/sim/sim_model_sysid.json |
|---|---|---|---|---|
| L0_yaw_step+5_r0 | latency=120.1 t90=480.0 overshoot=0.0 tracking=98.4 | latency=80.2 t90=520.2 overshoot=0.0 tracking=91.4 | latency=159.9 t90=560.2 overshoot=0.0 tracking=91.4 | latency=159.9 t90=560.2 overshoot=0.0 tracking=96.5 |
| L0_yaw_step-5_r0 | latency=79.8 t90=479.8 overshoot=0.0 tracking=98.4 | latency=79.8 t90=520.0 overshoot=0.0 tracking=98.1 | latency=160.0 t90=560.0 overshoot=0.0 tracking=98.1 | latency=160.0 t90=560.0 overshoot=0.0 tracking=98.1 |
| L0_hip_step+5_r0 | latency=120.0 t90=520.0 overshoot=0.0 tracking=98.4 | latency=80.0 t90=480.0 overshoot=0.0 tracking=92.7 | latency=160.0 t90=559.8 overshoot=0.0 tracking=92.7 | latency=120.0 t90=520.0 overshoot=0.0 tracking=98.3 |
| L0_hip_step-5_r0 | latency=120.0 t90=679.7 overshoot=0.0 tracking=91.4 | latency=80.0 t90=480.0 overshoot=0.0 tracking=92.7 | latency=160.0 t90=560.0 overshoot=0.0 tracking=92.7 | latency=120.0 t90=520.0 overshoot=0.0 tracking=98.3 |
| L0_knee_step+5_r0 | latency=217.9 t90=520.2 overshoot=0.0 tracking=96.7 | latency=80.2 t90=520.2 overshoot=0.0 tracking=89.9 | latency=160.2 t90=520.2 overshoot=0.188 tracking=103.2 | latency=160.2 t90=560.2 overshoot=0.0 tracking=94.2 |
| L0_knee_step-5_r0 | latency=120.3 t90=520.0 overshoot=0.0 tracking=98.4 | latency=80.2 t90=480.2 overshoot=0.0 tracking=94.5 | latency=120.3 t90=520.0 overshoot=0.0 tracking=97.9 | latency=160.2 t90=560.0 overshoot=0.0 tracking=94.6 |
| L1_yaw_step+5_r0 | latency=160.1 t90=560.3 overshoot=0.0 tracking=96.7 | latency=80.3 t90=520.3 overshoot=0.0 tracking=91.4 | latency=160.1 t90=560.3 overshoot=0.0 tracking=91.4 | latency=160.1 t90=560.3 overshoot=0.0 tracking=96.9 |
| L1_yaw_step-5_r0 | latency=107.4 t90=547.6 overshoot=0.0 tracking=95.3 | latency=107.4 t90=507.6 overshoot=0.0 tracking=94.7 | latency=187.4 t90=587.6 overshoot=0.0 tracking=94.7 | latency=147.4 t90=547.6 overshoot=0.0 tracking=94.7 |
| L1_hip_step+5_r0 | latency=160.2 t90=520.3 overshoot=0.0 tracking=98.4 | latency=80.0 t90=480.2 overshoot=0.0 tracking=92.7 | latency=160.2 t90=560.0 overshoot=0.0 tracking=92.7 | latency=120.0 t90=520.3 overshoot=0.0 tracking=98.3 |
| L1_hip_step-5_r0 | latency=199.8 t90=640.0 overshoot=0.0 tracking=91.4 | latency=80.0 overshoot=0.0 tracking=89.2 | latency=159.8 overshoot=0.0 tracking=89.2 | latency=120.0 t90=520.0 overshoot=0.0 tracking=98.3 |
| L1_knee_step+5_r0 | latency=120.0 t90=480.0 overshoot=0.0 tracking=96.7 | latency=80.0 t90=520.0 overshoot=0.0 tracking=89.9 | latency=160.0 t90=560.0 overshoot=0.196 tracking=103.3 | latency=160.0 t90=560.0 overshoot=0.0 tracking=94.2 |
| L1_knee_step-5_r0 | latency=120.0 t90=479.8 overshoot=0.01 tracking=100.2 | latency=80.0 t90=479.8 overshoot=0.0 tracking=97.9 | latency=120.0 t90=520.0 overshoot=0.206 tracking=90.2 | latency=160.0 t90=560.0 overshoot=0.0 tracking=98.3 |
| L2_yaw_step+5_r0 | latency=160.1 t90=559.9 overshoot=0.0 tracking=94.9 | latency=79.9 t90=520.1 overshoot=0.0 tracking=91.4 | latency=160.1 t90=559.9 overshoot=0.0 tracking=91.4 | latency=160.1 t90=559.9 overshoot=0.0 tracking=96.5 |
| L2_yaw_step-5_r0 | latency=120.0 t90=519.8 overshoot=0.0 tracking=93.2 | latency=79.8 t90=519.8 overshoot=0.0 tracking=94.7 | latency=160.0 t90=559.8 overshoot=0.0 tracking=94.7 | latency=160.0 t90=559.8 overshoot=0.0 tracking=94.4 |
| L2_hip_step+5_r0 | latency=120.0 t90=479.8 overshoot=0.098 tracking=102.0 | latency=80.0 t90=479.8 overshoot=0.0 tracking=92.7 | latency=159.8 t90=560.0 overshoot=0.0 tracking=92.7 | latency=120.0 t90=520.0 overshoot=0.0 tracking=98.3 |
| L2_hip_step-5_r0 | latency=120.0 t90=560.0 overshoot=0.0 tracking=98.4 | latency=80.0 t90=479.8 overshoot=0.0 tracking=96.4 | latency=160.0 t90=560.0 overshoot=0.0 tracking=96.4 | latency=120.0 t90=519.8 overshoot=0.0 tracking=98.3 |
| L2_knee_step+5_r0 | latency=150.7 t90=550.7 overshoot=0.0 tracking=96.7 | latency=72.3 t90=510.7 overshoot=0.0 tracking=89.9 | latency=190.5 t90=550.7 overshoot=0.2 tracking=103.9 | latency=150.7 t90=550.7 overshoot=0.0 tracking=94.2 |
| L2_knee_step-5_r0 | latency=120.0 t90=519.8 overshoot=0.0 tracking=96.7 | latency=80.0 t90=479.8 overshoot=0.0 tracking=94.5 | latency=200.0 t90=519.8 overshoot=0.0 tracking=89.6 | latency=160.0 t90=560.0 overshoot=0.0 tracking=94.6 |
| L3_yaw_step+5_r0 | latency=119.9 t90=480.0 overshoot=0.186 tracking=98.4 | latency=80.0 t90=520.0 overshoot=0.0 tracking=91.4 | latency=159.8 t90=560.0 overshoot=0.0 tracking=91.4 | latency=159.8 t90=560.0 overshoot=0.0 tracking=96.6 |
| L3_yaw_step-5_r0 | latency=80.0 t90=479.8 overshoot=0.01 tracking=100.2 | latency=80.0 t90=520.1 overshoot=0.015 tracking=99.8 | latency=160.0 t90=560.0 overshoot=0.014 tracking=99.8 | latency=160.0 t90=560.0 overshoot=0.0 tracking=99.7 |
| L3_hip_step+5_r0 | latency=119.9 t90=519.9 overshoot=0.01 tracking=100.2 | latency=79.9 t90=480.0 overshoot=0.0 tracking=92.7 | latency=159.9 t90=559.9 overshoot=0.0 tracking=92.7 | latency=119.9 t90=519.9 overshoot=0.0 tracking=98.3 |
| L3_hip_step-5_r0 | latency=160.0 t90=560.2 overshoot=0.0 tracking=91.4 | latency=80.1 overshoot=0.0 tracking=89.2 | latency=160.0 overshoot=0.0 tracking=89.2 | latency=123.5 t90=520.2 overshoot=0.0 tracking=98.3 |
| L3_knee_step+5_r0 | latency=120.0 t90=480.0 overshoot=0.01 tracking=100.2 | latency=80.0 t90=519.8 overshoot=0.0 tracking=89.9 | latency=159.8 t90=519.8 overshoot=0.194 tracking=103.4 | latency=159.8 t90=559.8 overshoot=0.0 tracking=94.2 |
| L3_knee_step-5_r0 | latency=80.0 t90=480.0 overshoot=0.01 tracking=100.2 | latency=80.0 t90=480.0 overshoot=0.016 tracking=100.0 | latency=160.0 t90=600.0 overshoot=0.0 tracking=92.0 | latency=160.0 t90=560.0 overshoot=0.013 tracking=100.0 |
| L4_yaw_step+5_r0 | latency=120.0 t90=480.0 overshoot=0.0 tracking=98.4 | latency=80.0 t90=520.0 overshoot=0.0 tracking=91.4 | latency=160.0 t90=560.0 overshoot=0.0 tracking=91.4 | latency=160.0 t90=560.0 overshoot=0.0 tracking=96.5 |
| L4_yaw_step-5_r0 | latency=119.8 t90=479.8 overshoot=0.0 tracking=98.4 | latency=80.0 t90=520.0 overshoot=0.0 tracking=98.1 | latency=159.9 t90=560.0 overshoot=0.0 tracking=98.1 | latency=159.9 t90=560.0 overshoot=0.0 tracking=98.1 |
| L4_hip_step+5_r0 | latency=120.1 t90=480.0 overshoot=0.0 tracking=98.4 | latency=80.0 t90=480.0 overshoot=0.0 tracking=92.7 | latency=160.0 t90=560.0 overshoot=0.0 tracking=92.7 | latency=120.1 t90=520.0 overshoot=0.0 tracking=98.3 |
| L4_hip_step-5_r0 | latency=120.0 t90=480.0 overshoot=0.0 tracking=96.7 | latency=80.0 t90=480.0 overshoot=0.0 tracking=96.4 | latency=160.0 t90=559.8 overshoot=0.0 tracking=96.4 | latency=120.0 t90=534.0 overshoot=0.0 tracking=98.3 |
| L4_knee_step+5_r0 | latency=119.9 t90=479.9 overshoot=0.01 tracking=100.2 | latency=79.9 t90=519.9 overshoot=0.0 tracking=89.9 | latency=159.9 t90=519.9 overshoot=0.192 tracking=95.6 | latency=159.9 t90=559.9 overshoot=0.0 tracking=94.2 |
| L4_knee_step-5_r0 | latency=80.1 t90=479.8 overshoot=0.01 tracking=100.2 | latency=80.1 t90=479.8 overshoot=0.0 tracking=96.2 | latency=120.1 t90=520.1 overshoot=0.361 tracking=103.8 | latency=160.1 t90=560.1 overshoot=0.0 tracking=96.6 |
| L5_yaw_step+5_r0 | latency=80.0 t90=480.0 overshoot=0.0 tracking=98.4 | latency=80.0 t90=480.0 overshoot=0.0 tracking=91.4 | latency=160.1 t90=559.8 overshoot=0.0 tracking=91.4 | latency=160.1 t90=559.8 overshoot=0.0 tracking=96.5 |
| L5_yaw_step-5_r0 | latency=80.0 t90=480.0 overshoot=0.0 tracking=97.7 | latency=80.0 t90=519.8 overshoot=0.0 tracking=98.1 | latency=159.8 t90=559.8 overshoot=0.0 tracking=98.1 | latency=159.8 t90=559.8 overshoot=0.0 tracking=98.1 |
| L5_hip_step+5_r0 | latency=159.8 t90=519.8 overshoot=0.0 tracking=98.4 | latency=80.2 t90=480.0 overshoot=0.0 tracking=92.7 | latency=159.8 t90=560.0 overshoot=0.0 tracking=92.7 | latency=119.8 t90=519.8 overshoot=0.0 tracking=98.3 |
| L5_hip_step-5_r0 | latency=159.8 overshoot=0.0 tracking=87.9 | latency=79.9 overshoot=0.0 tracking=87.5 | latency=159.8 overshoot=0.0 tracking=87.5 | latency=120.0 t90=520.0 overshoot=0.0 tracking=98.3 |
| L5_knee_step+5_r0 | latency=120.5 t90=520.0 overshoot=0.01 tracking=100.2 | latency=79.8 t90=520.0 overshoot=0.0 tracking=89.9 | latency=159.8 t90=520.0 overshoot=0.199 tracking=103.1 | latency=159.8 t90=560.0 overshoot=0.0 tracking=94.2 |
| L5_knee_step-5_r0 | latency=120.3 t90=520.3 overshoot=0.0 tracking=96.7 | latency=80.1 t90=480.3 overshoot=0.0 tracking=96.2 | latency=160.3 t90=560.3 overshoot=0.0 tracking=89.4 | latency=160.3 t90=560.3 overshoot=0.0 tracking=96.6 |
