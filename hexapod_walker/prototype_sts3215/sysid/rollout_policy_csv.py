"""Roll an exported numpy policy in the MuJoCo twin and write a robot-style
rl_drive CSV, so `sysid.gait_metrics --footfall` scores sim and hardware with
the same code.

    uv run python -m sysid.rollout_policy_csv POLICY.json OUT.csv [--vx 0.10]
        [--seconds 10] [--dr 0] [--seed 0] [--servo-model air]
        [--write-speed 800 --write-acc 60] [--max-dq 1.5]

Columns match the robot's rl_drive CSV where the metrics need them (t_s, phase,
unix_s, vx_ref_mps, period_ms, body_roll_deg, body_pitch_deg, q{i}_deg,
cmd{i}_deg, act{i}) plus touch{i} (MuJoCo foot touch sensors, the contact ground
truth the robot lacks) and cx, cy, cz (chassis position, m). `cmd` is the
SafetyLayer's slew-clamped command, the same quantity the robot logs. The first
2.5 s (pin_command's hold + ramp) are labelled `hold`, the rest `walk`, so
`--phase walk` selects the constant-command part like on the robot.

--servo-model: "" (default) = rl_move/sim/sim_model.json (the 2026-09-21
reality-gap refit), "air" = sim_model_air_20260807.json (pre-refit parameters,
what the 09-13 policies were trained on), or a json path. --write-speed /
--write-acc override the bus profile (counts/s, Feetech acc units) and lift the
sim's velocity ceiling to match; --max-dq overrides the per-tick slew clamp.
These are sensitivity probes: a policy was trained with the values in its meta.
A _summary.json with the policy name sits next to the CSV (gait_metrics does not
need it; the ~/.hexapod lab-run layout does).
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np

from hexapod_core.joint_frame import mujoco_rel_rad_to_robot_abs_rad
from rl_move.np_policy import load_np_policy
from rl_move.sim.probe_ps200_transfer import Intervention, _force_walk, _policy_cfg
from rl_move.sim.probe_walk_income import pin_command
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.walk_task import SimHexapodJointWalkEnv

HOLD_RAMP_S = 2.5   # pin_command: 1 s hold + 1 s ramp, plus settle


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("policy", type=Path)
    ap.add_argument("out", type=Path, help="CSV path to write")
    ap.add_argument("--vx", type=float, default=0.10)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--dr", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--servo-model", default="")
    ap.add_argument("--write-speed", type=float, default=None)
    ap.add_argument("--write-acc", type=float, default=None)
    ap.add_argument("--max-dq", type=float, default=None)
    a = ap.parse_args(argv)

    policy = load_np_policy(str(a.policy))
    cfg = _policy_cfg(policy.meta, Intervention(name="rollout_policy_csv"))
    bus = cfg.setdefault("bus", {})
    if a.servo_model:
        bus["servo_params"] = a.servo_model
    if a.write_speed is not None:
        bus["write_speed"] = float(a.write_speed)
        bus["servo_vel_max_counts_s"] = "write_speed"
    if a.write_acc is not None:
        bus["write_acc"] = float(a.write_acc)
    if a.max_dq is not None:
        cfg.setdefault("safety", {})["max_delta_q_deg"] = float(a.max_dq)

    env = SimHexapodJointWalkEnv(params=SimServoParams.from_cfg(cfg),
                                 randomize=a.dr > 0, dr_scale=a.dr,
                                 episode_seconds=a.seconds, seed=a.seed, cfg=cfg)
    _force_walk(env)
    obs, _ = env.reset()
    assert obs.shape == policy.observation_space.shape, (obs.shape, policy.observation_space.shape)
    pin_command(env, a.vx, 0.0, 0.0)
    policy.reset()

    qadr = env._qadr
    touch = getattr(env, "_touch_adr", None)
    cols = (["t_s", "phase", "unix_s", "vx_ref_mps", "period_ms", "body_roll_deg", "body_pitch_deg"]
            + [f"q{j}_deg" for j in range(18)] + [f"cmd{j}_deg" for j in range(18)]
            + [f"act{j}" for j in range(18)] + [f"touch{i}" for i in range(6)] + ["cx", "cy", "cz"])
    rows = []
    tick = 0
    reason = ""
    t_start = time.time()
    while True:
        act, _ = policy.predict(obs, deterministic=True)
        obs, _r, term, trunc, info = env.step(act)
        tick += 1
        t = tick * env.dt
        q_abs = np.rad2deg(mujoco_rel_rad_to_robot_abs_rad(env.data.qpos[qadr]))
        cmd_abs = np.rad2deg(np.asarray(env.safety._last_safe, dtype=float))
        vx_ref = float(env._goal_traj.vx[min(tick, len(env._goal_traj.vx) - 1)])
        st = env._state
        tch = [float(env.data.sensordata[touch[i]]) if touch is not None and touch[i] >= 0 else float("nan")
               for i in range(6)]
        c = env.data.xpos[env._chassis_bid]
        rows.append([f"{t:.4f}", "walk" if t >= HOLD_RAMP_S else "hold", f"{t:.4f}", f"{vx_ref:.3f}",
                     f"{env.dt * 1000:.2f}", f"{np.rad2deg(st.imu_roll):.2f}", f"{np.rad2deg(st.imu_pitch):.2f}"]
                    + [f"{v:.3f}" for v in q_abs] + [f"{v:.3f}" for v in cmd_abs]
                    + [f"{v:.4f}" for v in np.asarray(act).ravel()] + [f"{v:.3f}" for v in tch]
                    + [f"{v:.4f}" for v in c])
        if term or trunc:
            reason = str(info.get("termination_reason") or ("trunc" if trunc else "term"))
            break

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    x0, x1 = float(rows[0][-3]), float(rows[-1][-3])
    y0, y1 = float(rows[0][-2]), float(rows[-1][-2])
    json.dump({"params": {"policy": {"name": policy.meta.get("name", "sim")}, "hz": 1 / env.dt},
               "ticks_logged": len(rows), "sim": True, "vx": a.vx, "dr": a.dr, "seed": a.seed,
               "servo_model": a.servo_model or "sim_model.json", "write_speed": a.write_speed,
               "write_acc": a.write_acc, "max_dq": a.max_dq, "termination": reason,
               "chassis_travel_m": [x1 - x0, y1 - y0]},
              open(a.out.with_name(a.out.stem + "_summary.json"), "w"), indent=1)
    print(f"{a.out.name}: {len(rows)} ticks at {1 / env.dt:.0f} Hz, end {reason}, "
          f"chassis dx {x1 - x0:+.3f} m dy {y1 - y0:+.3f} m ({time.time() - t_start:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
