# Hexapod Sim Reality Report

- generated: 2026-08-31T15:39:20
- git: `df28a138`
- servo params `air`: sim_model.json (6968268e879e)
- servo params `loaded`: sim_model_loaded.json (144d43fa5dd3)
- servo params `rl_move/sim/sim_model_sysid.json`: sim_model_sysid.json (8b8d2f260256)

## Headline gap metrics

| trace | metric | hardware | sim air | sim loaded | sim rl_move/sim/sim_model_sysid.json |
|---|---|---|---|---|---|
| sysid_micro_l0_axes_ground_5deg_v1_20260831_223852.csv | unloaded q_rmse_deg | — | 0.264 | 0.269 | 0.16 |
| sysid_micro_l0_axes_ground_5deg_v1_20260831_223852.csv | unloaded qd_rmse_deg_s | — | 1.6 | 1.97 | 1.44 |
| sysid_micro_l0_axes_ground_5deg_v1_20260831_223852.csv | cmd→motion latency (hw) | median 120.1 ms (p10 99.4 / p90 145.1 / max 160.2, n=6) | — | — | — |

## Timing (hardware)

- **sysid_micro_l0_axes_ground_5deg_v1_20260831_223852.csv**: tick median 40.0 ms (nominal 40.0, p95 40.62, late 0.0%); send→recv RTT median 8.2 ms (p95 11.8)

## Per-segment detail

### sysid_micro_l0_axes_ground_5deg_v1_20260831_223852.csv

| segment | hardware | sim air | sim loaded | sim rl_move/sim/sim_model_sysid.json |
|---|---|---|---|---|
| L0_yaw_step+5_ground_r0 | latency=130.1 t90=480.0 overshoot=0.0 tracking=98.4 | latency=79.8 t90=519.8 overshoot=0.0 tracking=91.4 | latency=160.0 t90=559.7 overshoot=0.0 tracking=91.4 | latency=160.0 t90=559.7 overshoot=0.0 tracking=96.5 |
| L0_yaw_step-5_ground_r0 | latency=79.4 t90=479.6 overshoot=0.0 tracking=98.4 | latency=79.4 t90=519.6 overshoot=0.0 tracking=98.1 | latency=159.6 t90=559.6 overshoot=0.0 tracking=98.1 | latency=159.6 t90=559.6 overshoot=0.0 tracking=98.1 |
| L0_hip_step+5_ground_r0 | latency=119.4 t90=524.7 overshoot=0.0 tracking=98.4 | latency=79.2 t90=479.2 overshoot=0.0 tracking=92.7 | latency=159.4 t90=559.1 overshoot=0.0 tracking=92.7 | latency=119.4 t90=524.7 overshoot=0.0 tracking=98.3 |
| L0_hip_step-5_ground_r0 | latency=160.2 t90=560.2 overshoot=0.0 tracking=93.2 | latency=80.2 t90=480.2 overshoot=0.0 tracking=91.2 | latency=160.2 t90=560.2 overshoot=0.0 tracking=91.2 | latency=120.0 t90=520.2 overshoot=0.0 tracking=98.3 |
| L0_knee_step+5_ground_r0 | latency=120.0 t90=520.0 overshoot=0.0 tracking=93.2 | latency=80.0 t90=520.0 overshoot=0.0 tracking=89.9 | latency=160.0 t90=560.0 overshoot=0.183 tracking=97.3 | latency=160.0 t90=560.0 overshoot=0.0 tracking=94.2 |
| L0_knee_step-5_ground_r0 | latency=120.2 t90=520.2 overshoot=0.0 tracking=93.2 | latency=87.7 t90=480.2 overshoot=0.0 tracking=96.2 | latency=200.3 t90=560.2 overshoot=0.0 tracking=98.5 | latency=160.4 t90=560.2 overshoot=0.0 tracking=96.6 |
