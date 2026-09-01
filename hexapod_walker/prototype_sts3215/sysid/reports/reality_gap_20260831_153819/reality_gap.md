# Hexapod Sim Reality Report

- generated: 2026-08-31T15:38:19
- git: `df28a138`
- servo params `air`: sim_model.json (6968268e879e)
- servo params `loaded`: sim_model_loaded.json (144d43fa5dd3)
- servo params `rl_move/sim/sim_model_sysid.json`: sim_model_sysid.json (8b8d2f260256)

## Headline gap metrics

| trace | metric | hardware | sim air | sim loaded | sim rl_move/sim/sim_model_sysid.json |
|---|---|---|---|---|---|
| sysid_micro_l0_axes_ground_v1_20260831_223754.csv | unloaded q_rmse_deg | — | 0.247 | 0.236 | 0.121 |
| sysid_micro_l0_axes_ground_v1_20260831_223754.csv | unloaded qd_rmse_deg_s | — | 1.4 | 1.61 | 1.2 |
| sysid_micro_l0_axes_ground_v1_20260831_223754.csv | cmd→motion latency (hw) | median 120.0 ms (p10 105.2 / p90 139.9 / max 159.8, n=6) | — | — | — |

## Timing (hardware)

- **sysid_micro_l0_axes_ground_v1_20260831_223754.csv**: tick median 40.0 ms (nominal 40.0, p95 40.72, late 0.24%); send→recv RTT median 8.1 ms (p95 11.8)

## Per-segment detail

### sysid_micro_l0_axes_ground_v1_20260831_223754.csv

| segment | hardware | sim air | sim loaded | sim rl_move/sim/sim_model_sysid.json |
|---|---|---|---|---|
| L0_yaw_step+2_ground_r0 | latency=90.3 t90=279.8 overshoot=0.0 tracking=96.7 | latency=90.3 overshoot=0.0 tracking=78.7 | latency=159.8 overshoot=0.0 tracking=78.7 | latency=159.8 t90=320.0 overshoot=0.0 tracking=92.5 |
| L0_yaw_step-2_ground_r0 | latency=120.0 t90=240.0 overshoot=0.0 tracking=92.3 | latency=79.8 t90=240.0 overshoot=0.0 tracking=95.5 | latency=160.0 t90=320.0 overshoot=0.0 tracking=95.5 | latency=160.0 t90=320.0 overshoot=0.0 tracking=95.7 |
| L0_hip_step+2_ground_r0 | latency=120.0 t90=400.0 overshoot=0.022 tracking=101.1 | latency=80.0 overshoot=0.0 tracking=81.7 | latency=160.0 overshoot=0.0 tracking=81.7 | latency=120.0 t90=319.9 overshoot=0.0 tracking=95.7 |
| L0_hip_step-2_ground_r0 | latency=159.8 overshoot=0.0 tracking=83.5 | latency=79.8 overshoot=0.0 tracking=78.6 | latency=159.8 overshoot=0.0 tracking=78.6 | latency=120.0 t90=320.0 overshoot=0.0 tracking=96.0 |
| L0_knee_step+2_ground_r0 | latency=120.0 t90=335.2 overshoot=0.0 tracking=92.2 | latency=80.0 overshoot=0.0 tracking=74.9 | latency=160.0 t90=600.0 overshoot=0.0 tracking=89.5 | latency=160.0 overshoot=0.0 tracking=85.8 |
| L0_knee_step-2_ground_r0 | latency=120.0 t90=279.8 overshoot=0.0 tracking=92.3 | latency=81.6 t90=240.0 overshoot=0.0 tracking=90.7 | latency=160.0 t90=320.0 overshoot=0.0 tracking=76.1 | latency=160.0 t90=320.0 overshoot=0.0 tracking=91.1 |
