# Hexapod Sim Reality Report

- generated: 2026-08-31T15:36:38
- git: `df28a138`
- servo params `loaded`: sim_model_loaded.json (144d43fa5dd3)

## Headline gap metrics

| trace | metric | hardware | sim loaded |
|---|---|---|---|
| sysid_micro_l0_yaw_ground_v1_20260831_223619.csv | unloaded q_rmse_deg | — | 0.414 |
| sysid_micro_l0_yaw_ground_v1_20260831_223619.csv | unloaded qd_rmse_deg_s | — | 3.24 |
| sysid_micro_l0_yaw_ground_v1_20260831_223619.csv | cmd→motion latency (hw) | median 100.0 ms (p10 84.0 / p90 115.9 / max 119.9, n=2) | — |

## Timing (hardware)

- **sysid_micro_l0_yaw_ground_v1_20260831_223619.csv**: tick median 40.0 ms (nominal 40.0, p95 41.23, late 0.0%); send→recv RTT median 8.1 ms (p95 11.9)

## Per-segment detail

### sysid_micro_l0_yaw_ground_v1_20260831_223619.csv

| segment | hardware | sim loaded |
|---|---|---|
| L0_yaw_step+2_ground_r0 | latency=119.9 t90=240.0 overshoot=0.021 tracking=96.7 | latency=160.0 overshoot=0.0 tracking=78.7 |
| L0_yaw_step-2_ground_r0 | latency=80.0 t90=239.8 overshoot=0.022 tracking=101.1 | latency=160.0 t90=320.0 overshoot=0.0 tracking=95.5 |
