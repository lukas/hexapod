# sysid/simgap: sim-to-real gap tools (hexapod2 vs MuJoCo)

Written 2026-09-13 for `docs/SIM_REAL_GAP_CATALOG_2026-09-13.md`. Everything runs
from `hexapod_walker/prototype_sts3215` with `uv run`, on the 25 Robot Lab v2
traces pinned in `rl_move/sim/hexapod2_replay_matrix.json` (fetch once with
`uv run python -m rl_move.sim.replay_hexapod2_matrix --split all --fetch-only`).

| script | what it does | output |
|---|---|---|
| `hw_metrics.py` | hardware-only metrics per trace: hold-phase joint droop per leg, walk tracking error, roll/gyro spectrum bands relative to the stride frequency, loop period and feedback age, per-joint current | `/tmp/simgap/hw_metrics.json` |
| `replay_variants.py` | open-loop replay of all traces through `rl_move.sim.replay_trace._ReplaySim` under a physics variant; per-run npz time series (hardware and sim roll, gyro, joints, foot force and position, actuator torque) and a `result.json` with gate counts, Spearman rank correlation of hardware vs sim peak roll, per-family medians and foot stance statistics. `--hold-probe` replays each recorded hold pose statically and reports joint torque, foot forces and sim vs hardware droop | `/tmp/simgap/variants/<variant>/` |
| `summarize_variants.py` | one table over every variant directory (`--md` for markdown) | stdout |
| `closed_loop_variants.py` | frozen deployed actors (PS200, walkteach, allheading) policy-in-the-loop under variants: peak/rms roll, speed, yaw drift, feet in contact, stationary and swinging feet, falls, plus the DR draw per rollout | `logs/ckpt_eval/simgap_closed_loop_<UTC>/` or `--out` |
| `contact_compare.py` | side-camera foot timelines (vision pod job) vs the replay's foot motion, identity-free statistics with the same speed thresholds | `/tmp/simgap/contact_compare_<variant>.json` |
| `variants/*.json` | `joint_series_flex` tables: backlash (near-zero spring inside +-b deg, joint-limit stop beyond) on all joints / hip+knee / yaw; uniform soft hip/knee 40/30 N m/rad; soft hips on one tripod only | |

Variant grammar (comma separated tokens):

- replay: `baseline` (rigid, loaded servo fit), `air`, `mu<f>` foot-floor slide
  friction, `torque<f>` scale of the 2.2 N m clamp, `kp<f>` scale of the fitted
  position gain, `friction<f>` joint frictionloss in N m, `com<x>/<y>/<z>` mm,
  `series:<json>`, `mount:<json>`.
- closed loop: `baseline`, `air`/`loaded`, `mu<f>`, `torque<f>`, `kp<f>`,
  `dr<f>` (dr_scale), `hz<f>` control rate, `nostruct`, `series:<json>`.

Vision side: `hexapod-vision-lab:/data/jobs/simgap/s1_foot_timeline.py` tracks
red boot tips at 30 fps in the cam2 clips and writes per-frame stance/swing
tables to `/data/results/simgap/`; copy them to `/tmp/simgap/vision/` before
running `contact_compare.py`.

Findings and the variant tables are in the catalog doc; do not re-run the
whole grid to check a single number, each replay variant takes about two
minutes and each closed-loop variant about ten.
