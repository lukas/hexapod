"""Render a clean walk-only joystick-drive video for one policy checkpoint.

This is the operator-facing video helper. It is intentionally narrower than
``eval_checkpoint`` and ``manual_drive_session``:

- walk-only policies start from a settled plant walk episode, not a
  rise/hold/lower sequence;
- the full STL mesh model is required by default on local CPU rollouts;
- scripted joystick commands are installed before the first policy action, and
  the observation history is rebuilt so the first visible action sees the
  command shown in the HUD;
- recurrent checkpoints are loaded through the shared state-threading wrapper.

Example:

    uv run --with imageio --with imageio-ffmpeg --with pillow \
      python -m rl_move.sim.drive_video rl_move/sim/policies/policy.zip \
      --cfg-set obs.history_frames=64 --cfg-set goal.walk_phase_obs=1
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np

_PROTO = Path(__file__).resolve().parents[2]


def _script(name: str, *, seconds: float, dt: float, speed: float,
            blend_s: float) -> tuple[np.ndarray, np.ndarray, list[str]]:
    n = max(2, int(round(seconds / dt)) + 1)
    vx = np.zeros(n, dtype=float)
    vy = np.zeros(n, dtype=float)
    labels = ["stop"] * n

    if name == "square":
        phases = [
            (0.0, speed, 0.0, "forward"),
            (4.0, 0.0, speed, "left"),
            (8.0, -speed, 0.0, "reverse"),
            (12.0, 0.0, -speed, "right"),
            (16.0, speed, 0.0, "forward"),
        ]
    elif name == "human":
        d = speed / math.sqrt(2.0)
        phases = [
            (0.0, speed, 0.0, "forward"),
            (5.0, 0.0, -speed, "crab-right"),
            (9.0, d, d, "diag-left"),
            (13.0, -speed, 0.0, "reverse"),
            (17.0, 0.0, 0.0, "stop"),
            (19.5, speed, 0.0, "restart"),
            (24.0, 0.0, 0.0, "final-stop"),
        ]
    elif name == "sweep":
        phases = [(0.0, None, None, "sweep")]
    else:
        raise ValueError(f"unknown script {name!r}")

    def tick(t_s: float) -> int:
        return min(n - 1, max(0, int(round(t_s / dt))))

    if name == "sweep":
        theta = np.linspace(math.radians(45.0), math.radians(-135.0), n)
        vx[:] = speed * np.cos(theta)
        vy[:] = speed * np.sin(theta)
        labels = ["sweep"] * n
        return vx, vy, labels

    cur = (float(phases[0][1]), float(phases[0][2]))
    for idx, (t0, tvx, tvy, label) in enumerate(phases):
        k0 = tick(t0)
        k1 = tick(phases[idx + 1][0]) if idx + 1 < len(phases) else n
        if k1 <= k0:
            continue
        tvx_f, tvy_f = float(tvx), float(tvy)
        if idx == 0:
            vx[k0:k1] = tvx_f
            vy[k0:k1] = tvy_f
        else:
            nb = min(max(1, int(round(blend_s / dt))), k1 - k0)
            vx[k0:k0 + nb] = np.linspace(cur[0], tvx_f, nb)
            vy[k0:k0 + nb] = np.linspace(cur[1], tvy_f, nb)
            vx[k0 + nb:k1] = tvx_f
            vy[k0 + nb:k1] = tvy_f
        for k in range(k0, k1):
            labels[k] = label
        cur = (tvx_f, tvy_f)
    return vx, vy, labels


def _force_walk_only(env) -> None:
    gen = env._goal_gen
    for mode in ("walk", "hold", "lean", "track", "unload", "raise",
                 "rise", "lower", "recover", "quadwalk", "getup"):
        if hasattr(gen, f"p_{mode}"):
            setattr(gen, f"p_{mode}", 1.0 if mode == "walk" else 0.0)


def _install_script(env, vx: np.ndarray, vy: np.ndarray) -> None:
    traj = env._goal_traj
    if traj is None or not hasattr(traj, "vx") or not hasattr(traj, "vy"):
        raise RuntimeError("env did not sample a walk trajectory")
    n = min(len(traj.vx), len(vx))
    traj.vx[:n] = vx[:n]
    traj.vy[:n] = vy[:n]
    if n < len(traj.vx):
        traj.vx[n:] = vx[n - 1]
        traj.vy[n:] = vy[n - 1]
    if getattr(traj, "wz", None) is not None:
        traj.wz[:] = 0.0


def _fresh_obs_after_command(env):
    from rl_move.env import build_obs

    env._state = env._read_state()
    return env._final_obs(
        build_obs(env.cfg, env._state, env._q_nom, env._prev_action,
                  goal=env._current_goal(), tilt_ref=env._tilt_ref0),
        reset=True)


def _contact(env) -> list[bool]:
    out = []
    for adr in env._touch_adr:
        out.append(bool(adr >= 0 and env.data.sensordata[adr] > 0.5))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("--script", choices=("square", "human", "sweep"),
                    default="square")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--speed", type=float, default=0.08)
    ap.add_argument("--blend-s", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dr-scale", type=float, default=0.0)
    ap.add_argument("--policy-mode", choices=("stochastic", "deterministic"),
                    default="stochastic")
    ap.add_argument("--render-every", type=int, default=4)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--cfg-set", action="append", default=[])
    ap.add_argument("--model-source", choices=("mesh", "mesh_mjx",
                    "primitive"), default="mesh")
    ap.add_argument("--allow-mesh-fallback", action="store_true",
                    help="allow env.model_source=mesh to fall back to the "
                         "checked-in mesh_mjx twin when full STL assets are "
                         "missing")
    args = ap.parse_args()

    from rl_move.config import load_config
    from .eval_checkpoint import (_course_window_ep_keys, _save_video,
                                  model_identity)
    from .servo_model import SimServoParams, motor_contract
    from .train_ppo_sim import _annotate_frame, _parse_cfg_set
    from .walk_task import SimHexapodJointWalkEnv

    cfg = load_config()
    for key, parsed in _parse_cfg_set(args.cfg_set).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    cfg.setdefault("env", {})["model_source"] = args.model_source
    # This is a video/readability helper, not a training/eval gate: start from
    # the operator-recognizable six-foot plant instead of drawing park starts.
    cfg.setdefault("goal", {})["walk_park_start_frac"] = 0.0

    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg),
        randomize=args.dr_scale > 0,
        dr_scale=args.dr_scale,
        episode_seconds=args.seconds,
        seed=args.seed,
        render_mode="rgb_array",
        cfg=cfg)
    identity = model_identity(env)
    if (args.model_source == "mesh" and identity["model_variant"] != "full_mesh"
            and not args.allow_mesh_fallback):
        raise SystemExit(
            "full mesh assets are missing; run "
            "`uv run --with numpy --with scipy --with shapely --with trimesh "
            "python mesh_mujoco/build_mesh_model.py --no-render` from the "
            "prototype dir, or pass --allow-mesh-fallback explicitly")

    _force_walk_only(env)
    vx, vy, labels = _script(args.script, seconds=args.seconds, dt=env.dt,
                             speed=args.speed, blend_s=args.blend_s)

    from .gru_policy import load_checkpoint_auto, wrap_recurrent_predictor
    model = load_checkpoint_auto(args.checkpoint, device="cpu")
    assert model.observation_space.shape == env.observation_space.shape, (
        f"obs mismatch: policy {model.observation_space.shape} vs env "
        f"{env.observation_space.shape} -- pass the run's cfg stack")
    model = wrap_recurrent_predictor(model)

    obs, reset_info = env.reset()
    del obs
    _install_script(env, vx, vy)
    obs = _fresh_obs_after_command(env)
    if hasattr(model, "reset"):
        model.reset()

    out = args.out_dir or (
        _PROTO / "logs" / "manual_drive" /
        f"{args.checkpoint.stem}_drive_{time.strftime('%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)

    deterministic = args.policy_mode == "deterministic"
    frames = []
    rows = []
    course_xy = []
    course_cmd = []
    contacts = []
    currents = []
    pads = [env.model.body(f"L{i}_pad").id for i in range(6)]
    pad_xy = []
    cmd_dist = 0.0
    along_dist = 0.0
    term_reason = ""
    ret = 0.0

    for i in range(env.episode_steps):
        action, _ = model.predict(obs, deterministic=deterministic)
        obs, reward, term, trunc, info = env.step(action)
        ret += float(reward)

        k = min(env._step_i, len(vx) - 1)
        v = env._body_vel_xy()
        cmd = np.array([vx[k], vy[k]], dtype=float)
        speed_ref = float(np.hypot(*cmd))
        if speed_ref > 1e-3:
            cmd_dist += speed_ref * env.dt
            along_dist += float(v @ cmd / speed_ref) * env.dt
        bxy = env.data.xpos[env._chassis_bid, :2].copy()
        course_xy.append((float(bxy[0]), float(bxy[1])))
        course_cmd.append((float(cmd[0]), float(cmd[1])))
        contacts.append(_contact(env))
        pad_xy.append([env.data.xpos[b, :2].copy() for b in pads])
        cur = getattr(env._state, "servo_current", None)
        if cur is not None:
            currents.append(np.asarray(cur, dtype=float).copy())

        row = {
            "t": round(env._step_i * env.dt, 3),
            "label": labels[k],
            "cmd_vx": round(float(cmd[0]), 4),
            "cmd_vy": round(float(cmd[1]), 4),
            "act_vx": round(float(v[0]), 4),
            "act_vy": round(float(v[1]), 4),
            "roll_deg": round(float(info.get("roll_rel_deg", 0.0)), 3),
            "pitch_deg": round(float(info.get("pitch_rel_deg", 0.0)), 3),
            "height_mm": info.get("height_mm"),
            "max_current_a": info.get("max_current_a"),
        }
        rows.append(row)

        if i % max(1, args.render_every) == 0:
            actual_speed = float(np.hypot(v[0], v[1]))
            lines = [
                f"{args.script} {args.policy_mode} full-mesh "
                f"t={row['t']:5.2f}s {row['label']}",
                f"cmd vx/vy {cmd[0]:+.3f}/{cmd[1]:+.3f} m/s "
                f"speed {speed_ref:.3f}",
                f"act vx/vy {v[0]:+.3f}/{v[1]:+.3f} m/s "
                f"speed {actual_speed:.3f}",
                f"tilt r/p {row['roll_deg']:+.1f}/{row['pitch_deg']:+.1f}deg",
            ]
            if term:
                lines.append(f"TERMINATED: {info.get('termination_reason')}")
            frames.append(_annotate_frame(env.render(), lines))

        if term or trunc:
            term_reason = str(info.get("termination_reason", "")) if term else ""
            break

    contact = np.asarray(contacts, dtype=bool)
    pad_xy_arr = np.asarray(pad_xy, dtype=float)
    duty = contact.mean(axis=0) if len(contact) else np.zeros(6)
    swings = []
    slips = []
    for leg in range(6):
        c = contact[:, leg] if len(contact) else np.zeros(0, dtype=bool)
        d = np.diff(c.astype(int)) if len(c) else np.zeros(0, dtype=int)
        swings.append(int(np.sum(d == -1)))
        if len(pad_xy_arr) > 1:
            moved = np.linalg.norm(np.diff(pad_xy_arr[:, leg, :], axis=0),
                                   axis=1)
            slips.append(float(moved[c[:-1]].sum()) if len(c) > 1 else 0.0)
        else:
            slips.append(0.0)

    cur = np.asarray(currents, dtype=float) if currents else np.zeros((1, 18))
    summary = {
        "checkpoint": str(args.checkpoint),
        "script": args.script,
        "policy_mode": args.policy_mode,
        "seed": args.seed,
        "dr_scale": args.dr_scale,
        **identity,
        "motor_contract": motor_contract(cfg, backend="servo_profile_np"),
        "reset_info": reset_info,
        "terminated": bool(term_reason),
        "termination_reason": term_reason,
        "sim_seconds": rows[-1]["t"] if rows else 0.0,
        "return": round(ret, 2),
        "cmd_dist_m": round(cmd_dist, 3),
        "along_dist_m": round(along_dist, 3),
        "progress_ratio": round(along_dist / cmd_dist, 3)
        if cmd_dist > 1e-6 else None,
        "slip_m_total": round(float(sum(slips)), 3),
        "slip_per_m": round(float(sum(slips)) / max(along_dist, 0.05), 3)
        if cmd_dist > 1e-6 else None,
        "duty_cycle": [round(float(x), 3) for x in duty],
        "swing_count": swings,
        "sacrificed_legs": [
            leg for leg in range(6)
            if duty[leg] < 0.10 or (duty[leg] > 0.95 and swings[leg] == 0)
        ],
        "cur_max_a": round(float(cur.max()), 3),
        "cur_p95_a": round(float(np.percentile(cur, 95)), 3),
    }
    summary["gait_valid"] = not summary["sacrificed_legs"]
    summary.update(_course_window_ep_keys(course_xy, course_cmd, env.dt))

    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    (out / "ticks.json").write_text(json.dumps(rows, indent=1))
    _save_video(frames, out / "drive")
    if (out / "drive.png").exists():
        (out / "contact_sheet.png").write_bytes((out / "drive.png").read_bytes())

    print(json.dumps(summary, indent=2))
    print(f"[drive_video] artifacts -> {out}")
    return 0 if not term_reason else 1


if __name__ == "__main__":
    raise SystemExit(main())
