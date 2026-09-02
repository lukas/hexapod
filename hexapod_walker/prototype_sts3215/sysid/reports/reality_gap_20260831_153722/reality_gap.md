# Hexapod Sim Reality Report

- generated: 2026-08-31T15:37:22
- git: `df28a138`
- servo params `air`: sim_model.json (6968268e879e)
- servo params `loaded`: sim_model_loaded.json (144d43fa5dd3)
- servo params `rl_move/sim/sim_model_sysid.json`: sim_model_sysid.json (8b8d2f260256)

## Headline gap metrics

| trace | metric | hardware | sim air | sim loaded | sim rl_move/sim/sim_model_sysid.json |
|---|---|---|---|---|---|
| sysid_micro_l0_yaw_ground_v1_20260831_223619.csv | unloaded q_rmse_deg | — | 0.343 | 0.414 | 0.225 |
| sysid_micro_l0_yaw_ground_v1_20260831_223619.csv | unloaded qd_rmse_deg_s | — | 2.02 | 3.24 | 2.98 |
| sysid_micro_l0_yaw_ground_v1_20260831_223619.csv | cmd→motion latency (hw) | median 100.0 ms (p10 84.0 / p90 115.9 / max 119.9, n=2) | — | — | — |

## Timing (hardware)

- **sysid_micro_l0_yaw_ground_v1_20260831_223619.csv**: tick median 40.0 ms (nominal 40.0, p95 41.23, late 0.0%); send→recv RTT median 8.1 ms (p95 11.9)

## Per-segment detail

### sysid_micro_l0_yaw_ground_v1_20260831_223619.csv

| segment | hardware | sim air | sim loaded | sim rl_move/sim/sim_model_sysid.json |
|---|---|---|---|---|
| L0_yaw_step+2_ground_r0 | latency=119.9 t90=240.0 overshoot=0.021 tracking=96.7 | latency=92.4 overshoot=0.0 tracking=78.7 | latency=160.0 overshoot=0.0 tracking=78.7 | latency=160.0 t90=320.0 overshoot=0.0 tracking=92.5 |
| L0_yaw_step-2_ground_r0 | latency=80.0 t90=239.8 overshoot=0.022 tracking=101.1 | latency=80.0 t90=239.8 overshoot=0.0 tracking=95.5 | latency=160.0 t90=320.0 overshoot=0.0 tracking=95.5 | latency=160.0 t90=320.0 overshoot=0.0 tracking=95.5 |
