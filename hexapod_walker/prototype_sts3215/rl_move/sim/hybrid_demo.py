"""Composable MuJoCo demo: stand controller, RL joystick walk, lower controller.

This is the headless/video counterpart to the interactive player. It treats a
demo as a small controller/state composition, so stand, walk, and lower pieces
can be swapped independently while keeping the handoff points visible.

Default composition:

    belly_zero
      -> standup_modes.json:step forward, or learned stance policy
      -> align to sim_walk_start
      -> bookkeeping re-anchor into the walk policy's plant frame
      -> SB3 walk checkpoint under a scripted joystick path
      -> align to sim_walk_start
      -> standup_modes.json:step reverse, or learned stance policy
      -> limp settle

Example:

    uv run --with imageio --with imageio-ffmpeg --with pillow \
      python -m rl_move.sim.hybrid_demo \
      rl_move/sim/policies/ppo_goal_cw_walk_allheading_tf_stressmix_ft1.zip \
      --cfg-set obs.history_frames=64 \
      --cfg-set env.model_source=mesh \
      --cfg-set control.hz=100 \
      --cfg-set goal.walk_obs_body_vel=2 \
      --cfg-set goal.walk_phase_obs=1 \
      --cfg-set goal.walk_phase_hz=1.333333
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np

_PROTO = Path(__file__).resolve().parents[2]
_STANDUP_FILE = _PROTO / "linux_control" / "standup_modes.json"
_SIM_WALK_START_DEG = [0.0, 20.0, 80.0] * 6
_STAND_HANDOFF_STABLE_S = 0.75
_STAND_HANDOFF_SETTLE_S = 0.25
_STAND_HANDOFF_MIN_Z_M = 0.10
_STAND_HANDOFF_MAX_TILT_DEG = 7.0
_STAND_HANDOFF_MAX_CURRENT_A = 2.2


def _smooth(s: float) -> float:
    s = max(0.0, min(1.0, float(s)))
    return 3.0 * s * s - 2.0 * s * s * s


def _q_now(env) -> np.ndarray:
    return env._state.joint_position.copy()


def _chassis_z(env) -> float:
    return float(env.data.xpos[env._chassis_bid, 2])


def _project_path(path: str | Path) -> Path:
    p = Path(path).expanduser()
    return p if p.is_absolute() else _PROTO / p


def _load_standup_modes(path: Path = _STANDUP_FILE) -> dict[str, Any]:
    data = json.loads(path.read_text())
    modes = data.get("modes")
    if not isinstance(modes, dict) or not modes:
        raise ValueError(f"{path}: missing non-empty modes object")
    return data


def _stance_checkpoint(args: argparse.Namespace, role: str) -> str:
    if role == "lower" and args.lower_policy is not None:
        return str(args.lower_policy)
    if args.stance_policy is None:
        raise ValueError(
            f"learned {role} requires --stance-policy with the v2 contract")
    return str(args.stance_policy)


def _default_composition(args: argparse.Namespace,
                         checkpoint: Path | None) -> dict[str, Any]:
    ckpt = str(checkpoint) if checkpoint is not None else ""
    lower_mode = args.lower_mode or args.stand_mode
    stand_controller = (
        "learned_stand" if args.stand_controller == "learned"
        else "scripted_stand")
    lower_controller = (
        "learned_lower" if args.lower_controller == "learned"
        else "scripted_lower")
    controllers = {
        "align_walk_ready": {
            "type": "pose_blend",
            "target": "sim_walk_start",
            "seconds": args.walk_ready_align_s,
        },
        "bookkeeping_walk_frame": {
            "type": "bookkeeping_reanchor",
            "start_at": "plant",
            "mode": "hold",
        },
        "rl_walk": {
            "type": "sb3_walk_policy",
            "checkpoint": ckpt,
            "policy_mode": args.policy_mode,
            "script": args.script,
            "seconds": args.walk_seconds,
            "speed_m_s": args.speed,
            "wz_max_rad_s": args.wz_max,
            "blend_s": args.blend_s,
        },
        "align_before_lower": {
            "type": "pose_blend",
            "target": "sim_walk_start",
            "seconds": args.pre_lower_align_s,
        },
        "limp_settle": {
            "type": "limp_settle",
            "seconds": args.limp_after_lower_s,
        },
    }
    if args.stand_controller == "learned":
        controllers["learned_stand"] = {
            "type": "learned_stance_policy",
            "checkpoint": _stance_checkpoint(args, "stand"),
            "role": "stand",
            "start_at": "zero",
            "release": args.stand_release,
            "handoff_stable_s": args.stand_handoff_stable_s,
            "handoff_settle_s": args.stand_handoff_settle_s,
            "handoff_min_z_m": args.stand_handoff_min_z_m,
            "handoff_max_tilt_deg": args.stand_handoff_max_tilt_deg,
            "handoff_max_current_a": args.stand_handoff_max_current_a,
        }
    else:
        controllers["scripted_stand"] = {
            "type": "standup_mode",
            "mode": args.stand_mode,
            "direction": "forward",
            "time_scale": args.stand_time_scale,
        }
    if args.lower_controller == "learned":
        controllers["learned_lower"] = {
            "type": "learned_stance_policy",
            "checkpoint": _stance_checkpoint(args, "lower"),
            "role": "lower",
            "start_at": "plant",
        }
    else:
        controllers["scripted_lower"] = {
            "type": "standup_mode",
            "mode": lower_mode,
            "direction": "reverse",
            "time_scale": args.lower_time_scale,
        }
    return {
        "schema": "hexapod.hybrid_demo.v1",
        "name": args.name or f"{Path(ckpt).stem or 'walk_policy'}_hybrid",
        "model_source": args.model_source,
        "states": {
            "belly_zero": {
                "bookkeeping_start_at": "zero",
                "pose_family": "logical_zero_belly_down",
            },
            "step_stand": {
                "pose_family": f"standup_modes.{args.stand_mode}.final",
            },
            "walk_ready": {
                "pose_family": "sim_walk_start",
                "q_deg": _SIM_WALK_START_DEG,
            },
            "walk_done": {
                "pose_family": "post_policy_runtime_state",
            },
            "grounded": {
                "pose_family": "scripted_lower_limp_settled",
            },
        },
        "controllers": controllers,
        "sequence": [
            {"phase": "stand", "controller": stand_controller,
             "from_state": "belly_zero", "to_state": "step_stand"},
            {"phase": "walk_ready_align", "controller": "align_walk_ready",
             "from_state": "step_stand", "to_state": "walk_ready"},
            {"phase": "walk_reanchor", "controller": "bookkeeping_walk_frame",
             "from_state": "walk_ready", "to_state": "walk_ready"},
            {"phase": "walk", "controller": "rl_walk",
             "from_state": "walk_ready", "to_state": "walk_done"},
            {"phase": "pre_lower_align", "controller": "align_before_lower",
             "from_state": "walk_done", "to_state": "walk_ready"},
            {"phase": "lower", "controller": lower_controller,
             "from_state": "walk_ready", "to_state": "grounded"},
            {"phase": "limp", "controller": "limp_settle",
             "from_state": "grounded", "to_state": "grounded"},
        ],
    }


def _load_composition(args: argparse.Namespace) -> dict[str, Any]:
    if args.composition is None:
        return _default_composition(args, args.checkpoint)
    plan = json.loads(args.composition.read_text())
    if args.checkpoint is not None:
        plan.setdefault("controllers", {}).setdefault("rl_walk", {})
        plan["controllers"]["rl_walk"]["checkpoint"] = str(args.checkpoint)
    return plan


def _standup_keyframes(modes: dict[str, Any], mode: str, *,
                       reverse: bool, time_scale: float
                       ) -> list[dict[str, Any]]:
    if mode not in modes["modes"]:
        known = ", ".join(sorted(modes["modes"]))
        raise ValueError(f"unknown standup mode {mode!r}; known: {known}")
    frames = list(modes["modes"][mode].get("keyframes", []))
    if not frames:
        raise ValueError(f"standup mode {mode!r} has no keyframes")
    if reverse:
        frames = list(reversed(frames))
    out = []
    for i, frame in enumerate(frames):
        q_deg = frame.get("q_deg")
        if not isinstance(q_deg, list) or len(q_deg) != 18:
            raise ValueError(f"standup mode {mode!r} keyframe {i}: bad q_deg")
        out.append({
            "label": f"{mode}:{'rev' if reverse else 'fwd'}:{i}",
            "q_rad": np.radians(np.asarray(q_deg, dtype=float)),
            "seconds": max(0.0, float(frame.get("s", 0.0))
                           * max(float(time_scale), 1e-6)),
        })
    return out


def _target_pose_rad(target: str, env) -> np.ndarray:
    if target == "sim_walk_start":
        return np.radians(np.asarray(_SIM_WALK_START_DEG, dtype=float))
    if target == "env_plant":
        return env._plant_deg.astype(float) * math.pi / 180.0
    raise ValueError(f"unknown pose_blend target {target!r}")


def _restore_phys(env, keep_q: np.ndarray, keep_v: np.ndarray) -> None:
    env.data.qpos[:] = keep_q
    env.data.qvel[:] = keep_v
    env._mujoco.mj_forward(env.model, env.data)
    q = _q_now(env)
    env._profile.reset(q)
    env.safety.set_nominal(q)


def _reanchor(env, *, start_at: str, mode: str) -> None:
    from rl_move.env import TaskGoal

    keep_q = env.data.qpos.copy()
    keep_v = env.data.qvel.copy()
    traj = env.traj
    traj.start_at = start_at
    traj.goal = TaskGoal()
    traj.vx = traj.vy = 0.0
    twz = getattr(traj, "wz", None)
    if twz is not None:
        try:
            twz[:] = 0.0
        except (TypeError, ValueError):
            traj.wz = 0.0
    traj.mode = mode
    traj.reset_published()
    env.reset()
    _restore_phys(env, keep_q, keep_v)


def _set_traj_cmd(traj, vx: float, vy: float, wz: float) -> None:
    traj.vx = float(vx)
    traj.vy = float(vy)
    twz = getattr(traj, "wz", None)
    if twz is not None:
        try:
            twz[:] = float(wz)
        except (TypeError, ValueError):
            traj.wz = float(wz)
    elif abs(float(wz)) > 1e-9:
        traj.wz = float(wz)


def _fresh_obs(env):
    from .drive_video import _fresh_obs_after_command

    return _fresh_obs_after_command(env)


class _Recorder:
    def __init__(self, env, *, render_stride: int, plan: dict[str, Any]):
        from .eval_checkpoint import _course_window_ep_keys
        from .train_ppo_sim import _annotate_frame
        from .drive_video import _contact

        self.env = env
        self.render_stride = max(1, int(render_stride))
        self.plan = plan
        self._course_window_ep_keys = _course_window_ep_keys
        self._annotate_frame = _annotate_frame
        self._contact = _contact
        self.frames: list[np.ndarray] = []
        self.rows: list[dict[str, Any]] = []
        self.contacts: list[list[bool]] = []
        self.currents: list[np.ndarray] = []
        self.pad_xy: list[list[np.ndarray]] = []
        self.walk_xy: list[tuple[float, float]] = []
        self.walk_cmd: list[tuple[float, float]] = []
        self.walk_yaw_err_abs: list[float] = []
        self.walk_hold_wz_abs: list[float] = []
        self.walk_wz_cmd_abs: list[float] = []
        self.walk_along_m = 0.0
        self.walk_cmd_m = 0.0
        self.termination_reason = ""
        self.truncated = False
        self.phase_marks: list[dict[str, Any]] = []
        self.phase_errors: list[str] = []
        self._pads = [env.model.body(f"L{i}_pad").id for i in range(6)]

    def mark(self, phase: str, event: str, **extra: Any) -> None:
        self.phase_marks.append({
            "t": round(len(self.rows) * self.env.dt, 3),
            "phase": phase,
            "event": event,
            **extra,
        })

    def record(self, phase: str, label: str, info: dict[str, Any] | None,
               *, reward: float | None = None,
               walk_label: str | None = None) -> None:
        env = self.env
        info = info or {}
        env._state = env._read_state()
        try:
            goal = env._current_goal()
            cmd = np.array([float(getattr(goal, "vx_ref", 0.0)),
                            float(getattr(goal, "vy_ref", 0.0))])
            cmd_wz = float(getattr(goal, "wz_ref", 0.0) or 0.0)
        except Exception:
            cmd = np.zeros(2)
            cmd_wz = 0.0
        vel = env._body_vel_xy()
        act_wz = env._body_wz()
        speed_ref = float(np.hypot(cmd[0], cmd[1]))
        if phase == "walk":
            if speed_ref > 1e-6:
                self.walk_cmd_m += speed_ref * env.dt
                self.walk_along_m += float(vel @ cmd / speed_ref) * env.dt
            if abs(cmd_wz) > 1e-4:
                self.walk_wz_cmd_abs.append(abs(cmd_wz))
                self.walk_yaw_err_abs.append(abs(act_wz - cmd_wz))
            else:
                self.walk_hold_wz_abs.append(abs(act_wz))
            bxy = env.data.xpos[env._chassis_bid, :2].copy()
            self.walk_xy.append((float(bxy[0]), float(bxy[1])))
            self.walk_cmd.append((float(cmd[0]), float(cmd[1])))
        cur = getattr(env._state, "servo_current", None)
        if cur is not None:
            self.currents.append(np.asarray(cur, dtype=float).copy())
        self.contacts.append(self._contact(env))
        self.pad_xy.append([env.data.xpos[b, :2].copy() for b in self._pads])
        row = {
            "t": round(len(self.rows) * env.dt, 3),
            "phase": phase,
            "label": walk_label or label,
            "cmd_vx": round(float(cmd[0]), 4),
            "cmd_vy": round(float(cmd[1]), 4),
            "cmd_wz": round(float(cmd_wz), 4),
            "act_vx": round(float(vel[0]), 4),
            "act_vy": round(float(vel[1]), 4),
            "act_wz": round(float(act_wz), 4),
            "z_m": round(_chassis_z(env), 4),
            "roll_deg": round(float(info.get("roll_rel_deg", 0.0)), 3),
            "pitch_deg": round(float(info.get("pitch_rel_deg", 0.0)), 3),
            "max_current_a": info.get("max_current_a"),
        }
        if reward is not None:
            row["reward"] = round(float(reward), 4)
        self.rows.append(row)
        if (len(self.rows) - 1) % self.render_stride == 0:
            actual_speed = float(np.hypot(vel[0], vel[1]))
            lines = [
                f"{self.plan.get('name', 'hybrid')} t={row['t']:5.2f}s "
                f"{phase}:{row['label']}",
                f"cmd vx/vy {cmd[0]:+.3f}/{cmd[1]:+.3f} m/s "
                f"speed {speed_ref:.3f} wz {cmd_wz:+.3f}",
                f"act vx/vy {vel[0]:+.3f}/{vel[1]:+.3f} m/s "
                f"speed {actual_speed:.3f} wz {act_wz:+.3f}",
                f"z {row['z_m']:.3f}m tilt r/p "
                f"{row['roll_deg']:+.1f}/{row['pitch_deg']:+.1f}deg",
            ]
            if self.termination_reason:
                lines.append(f"TERMINATED: {self.termination_reason}")
            self.frames.append(self._annotate_frame(env.render(), lines))

    def summary(self, *, identity: dict[str, Any],
                reset_info: dict[str, Any],
                motor_contract: dict[str, Any]) -> dict[str, Any]:
        contacts = np.asarray(self.contacts, dtype=bool)
        pad_xy = np.asarray(self.pad_xy, dtype=float)
        duty = contacts.mean(axis=0) if len(contacts) else np.zeros(6)
        swings: list[int] = []
        slips: list[float] = []
        for leg in range(6):
            c = contacts[:, leg] if len(contacts) else np.zeros(0, dtype=bool)
            d = np.diff(c.astype(int)) if len(c) else np.zeros(0, dtype=int)
            swings.append(int(np.sum(d == -1)))
            if len(pad_xy) > 1 and len(c) > 1:
                moved = np.linalg.norm(np.diff(pad_xy[:, leg, :], axis=0),
                                       axis=1)
                slips.append(float(moved[c[:-1]].sum()))
            else:
                slips.append(0.0)
        cur = (np.asarray(self.currents, dtype=float)
               if self.currents else np.zeros((1, 18)))
        rows = self.rows
        roll_peak = max((abs(float(r["roll_deg"])) for r in rows), default=0.0)
        pitch_peak = max((abs(float(r["pitch_deg"])) for r in rows), default=0.0)
        out: dict[str, Any] = {
            "composition": self.plan,
            **identity,
            "motor_contract": motor_contract,
            "reset_info": reset_info,
            "terminated": bool(self.termination_reason),
            "termination_reason": self.termination_reason,
            "truncated": bool(self.truncated),
            "sim_seconds": round(rows[-1]["t"], 3) if rows else 0.0,
            "phase_marks": self.phase_marks,
            "phase_errors": self.phase_errors,
            "roll_peak_abs_deg": round(float(roll_peak), 3),
            "pitch_peak_abs_deg": round(float(pitch_peak), 3),
            "z_min_m": round(min((float(r["z_m"]) for r in rows), default=0.0),
                             4),
            "z_max_m": round(max((float(r["z_m"]) for r in rows), default=0.0),
                             4),
            "walk_cmd_dist_m": round(float(self.walk_cmd_m), 3),
            "walk_along_dist_m": round(float(self.walk_along_m), 3),
            "walk_progress_ratio": (
                round(float(self.walk_along_m / self.walk_cmd_m), 3)
                if self.walk_cmd_m > 1e-6 else None),
            "slip_m_total_all_phases": round(float(sum(slips)), 3),
            "slip_per_walk_m_all_phases": (
                round(float(sum(slips)) / max(self.walk_along_m, 0.05), 3)
                if self.walk_cmd_m > 1e-6 else None),
            "duty_cycle_all_phases": [round(float(x), 3) for x in duty],
            "swing_count_all_phases": swings,
            "sacrificed_legs_all_phases": [
                leg for leg in range(6)
                if duty[leg] < 0.10 or (duty[leg] > 0.95 and swings[leg] == 0)
            ],
            "cur_max_a": round(float(cur.max()), 3),
            "cur_p95_a": round(float(np.percentile(cur, 95)), 3),
            "walk_wz_cmd_abs_max_rad_s": (
                round(float(max(self.walk_wz_cmd_abs)), 3)
                if self.walk_wz_cmd_abs else 0.0),
            "walk_turn_wz_err_med_rad_s": (
                round(float(np.median(self.walk_yaw_err_abs)), 4)
                if self.walk_yaw_err_abs else None),
            "walk_hold_wz_med_rad_s": (
                round(float(np.median(self.walk_hold_wz_abs)), 4)
                if self.walk_hold_wz_abs else None),
        }
        if self.walk_xy:
            out.update(self._course_window_ep_keys(
                self.walk_xy, self.walk_cmd, self.env.dt))
        out["walk_gait_valid"] = not out["sacrificed_legs_all_phases"]
        return out


def _run_pose_blend(env, rec: _Recorder, phase: str, target: np.ndarray,
                    seconds: float, *, label: str) -> tuple[bool, np.ndarray]:
    from .joint_task import q_rad_to_action

    q0 = _q_now(env)
    n = max(1, int(round(max(float(seconds), 0.0) / env.dt)))
    obs = None
    for i in range(n):
        s = _smooth((i + 1) / n)
        action = q_rad_to_action((1.0 - s) * q0 + s * target)
        obs, reward, term, trunc, info = env.step(action)
        rec.record(phase, label, info, reward=reward)
        if term or trunc:
            rec.termination_reason = str(info.get("termination_reason", ""))
            rec.truncated = bool(trunc)
            return False, obs
    return True, obs


def _run_standup_mode(env, rec: _Recorder, modes: dict[str, Any],
                      phase: str, ctrl: dict[str, Any]
                      ) -> tuple[bool, np.ndarray]:
    reverse = str(ctrl.get("direction", "forward")) == "reverse"
    sim_mode = "lower" if reverse else "rise"
    env.traj.mode = sim_mode
    frames = _standup_keyframes(
        modes, str(ctrl.get("mode", "step")), reverse=reverse,
        time_scale=float(ctrl.get("time_scale", 1.0)))
    obs = None
    for frame in frames:
        ok, obs = _run_pose_blend(env, rec, phase, frame["q_rad"],
                                  frame["seconds"], label=frame["label"])
        if not ok:
            return False, obs
    return True, obs


def _load_any_policy(path: Path):
    if path.suffix == ".json":
        from rl_move.np_policy import load_np_policy

        return load_np_policy(path)
    from hexapod_core.joint_frame import require_checkpoint_joint_contract
    from .gru_policy import load_checkpoint_auto, wrap_recurrent_predictor

    require_checkpoint_joint_contract(path)
    return wrap_recurrent_predictor(load_checkpoint_auto(path, device="cpu"))


def _stance_profile(path: Path, role: str,
                    override: dict[str, Any] | None = None
                    ) -> dict[str, float]:
    from .play_core import _DEFAULT_STANCE_PROFILE, _load_profiles

    role_key = "lower" if role == "lower" else "stand"
    prof: dict[str, Any] = dict(_DEFAULT_STANCE_PROFILE[role_key])
    profile: dict[str, Any] | None = None
    if path.suffix == ".json":
        try:
            meta = json.loads(path.read_text()).get("meta", {})
            if isinstance(meta.get("profile"), dict):
                profile = meta["profile"]
        except Exception:
            profile = None
    if profile is None:
        profile = _load_profiles().get(path.stem)
    if isinstance(profile, dict) and isinstance(profile.get(role_key), dict):
        prof.update(profile[role_key])
    if isinstance(override, dict):
        prof.update(override)
    hold_s = float(prof.get("hold_s", 0.0))
    ramp_s = float(prof.get("ramp_s", 0.0))
    target_m = float(prof["target_m"])
    total_s = float(prof.get("total_s", hold_s + ramp_s + 1.5))
    return {
        "hold_s": hold_s,
        "ramp_s": ramp_s,
        "target_m": target_m,
        "total_s": max(total_s, hold_s + ramp_s),
    }


def _run_learned_stance(env, rec: _Recorder, phase: str,
                        ctrl: dict[str, Any], model, n_obs: int,
                        policy_path: Path) -> tuple[bool, np.ndarray]:
    from rl_move.env import TaskGoal

    role = str(ctrl.get("role", "stand"))
    role_key = "lower" if role == "lower" else "stand"
    sim_mode = "lower" if role_key == "lower" else "rise"
    start_at = str(ctrl.get(
        "start_at", "plant" if role_key == "lower" else "zero"))
    prof = _stance_profile(
        policy_path, role_key,
        ctrl.get("profile") if isinstance(ctrl.get("profile"), dict)
        else None)

    _reanchor(env, start_at=start_at, mode=sim_mode)
    env.traj.HEIGHT_RATE = (
        abs(prof["target_m"]) / max(float(prof["ramp_s"]), 0.1))
    env.traj.BELLY_HOLD_S = (
        float(prof["hold_s"]) if role_key == "stand" else 0.0)
    env.traj.goal = TaskGoal()
    env.traj.goal.height_ref = float(prof["target_m"])
    env.traj.vx = env.traj.vy = 0.0
    env.traj.mode = sim_mode
    env.traj.reset_published()
    obs = _fresh_obs(env)
    if hasattr(model, "reset"):
        model.reset()

    rec.mark(phase, "profile", role=role_key, start_at=start_at,
             checkpoint=str(policy_path), obs_dim=int(n_obs), profile=prof)
    release = str(ctrl.get(
        "release", "stable" if role_key == "stand" else "profile"))
    if release not in {"stable", "profile"}:
        raise ValueError(f"{phase}: unknown learned stance release {release!r}")
    early_release = role_key == "stand" and release == "stable"
    profile_total_s = float(prof["total_s"])
    release_after_s = (
        float(prof["hold_s"]) + float(prof["ramp_s"])
        + float(ctrl.get("handoff_settle_s", _STAND_HANDOFF_SETTLE_S)))
    stable_needed = max(1, int(round(float(ctrl.get(
        "handoff_stable_s", _STAND_HANDOFF_STABLE_S)) / env.dt)))
    min_z = float(ctrl.get("handoff_min_z_m", _STAND_HANDOFF_MIN_Z_M))
    max_tilt = float(ctrl.get(
        "handoff_max_tilt_deg", _STAND_HANDOFF_MAX_TILT_DEG))
    max_current = float(ctrl.get(
        "handoff_max_current_a", _STAND_HANDOFF_MAX_CURRENT_A))
    run_total_s = profile_total_s
    if early_release:
        # Keep the full profile as a fallback if stability never appears.
        run_total_s = max(profile_total_s,
                          release_after_s + stable_needed * env.dt)
    n = max(1, int(round(run_total_s / env.dt)))
    label = f"{role_key}:{policy_path.stem}"
    stable_ticks = 0
    for i in range(n):
        action, _ = model.predict(obs[:n_obs], deterministic=True)
        obs, reward, term, trunc, info = env.step(action)
        rec.record(phase, label, info, reward=reward)
        if term or trunc:
            rec.termination_reason = str(info.get("termination_reason", ""))
            rec.truncated = bool(trunc)
            return False, obs
        if early_release:
            t_s = (i + 1) * env.dt
            cur = info.get("max_current_a")
            if cur is None:
                state_cur = getattr(getattr(env, "_state", None),
                                    "servo_current", None)
                if state_cur is not None:
                    cur = float(np.max(np.abs(state_cur)))
            tilt_abs = max(abs(float(info.get("roll_rel_deg", 0.0))),
                           abs(float(info.get("pitch_rel_deg", 0.0))))
            z_m = _chassis_z(env)
            current_ok = cur is None or float(cur) <= max_current
            if (t_s >= release_after_s and z_m >= min_z
                    and tilt_abs <= max_tilt and current_ok):
                stable_ticks += 1
            else:
                stable_ticks = 0
            if stable_ticks >= stable_needed:
                rec.mark(phase, "early_handoff",
                         t_s=round(t_s, 3),
                         profile_total_s=round(profile_total_s, 3),
                         release_after_s=round(release_after_s, 3),
                         stable_s=round(stable_ticks * env.dt, 3),
                         z_m=round(z_m, 4),
                         tilt_abs_deg=round(tilt_abs, 3),
                         max_current_a=(round(float(cur), 3)
                                        if cur is not None else None))
                break
    if role_key == "stand":
        env.traj.mode = "hold"
    return True, obs


def _run_limp(env, rec: _Recorder, phase: str,
              seconds: float) -> tuple[bool, np.ndarray]:
    n = max(0, int(round(max(float(seconds), 0.0) / env.dt)))
    for _ in range(n):
        env._advance(limp=True)
        rec.record(phase, "limp", {})
    return True, _fresh_obs(env)


def _run_walk(env, rec: _Recorder, ctrl: dict[str, Any],
              model) -> tuple[bool, np.ndarray]:
    from .drive_video import _script

    seconds = float(ctrl.get("seconds", 20.0))
    speed = float(ctrl.get("speed_m_s", ctrl.get("speed", 0.08)))
    wz_max = float(ctrl.get("wz_max_rad_s", ctrl.get("wz_max", 0.3)))
    script = str(ctrl.get("script", "human"))
    blend_s = float(ctrl.get("blend_s", 0.5))
    deterministic = str(ctrl.get("policy_mode", "deterministic")) == (
        "deterministic")
    vx, vy, wz, labels = _script(script, seconds=seconds, dt=env.dt,
                                 speed=speed, blend_s=blend_s,
                                 wz_max=wz_max)
    env.traj.mode = "walk"
    env.traj.reset_published()
    _set_traj_cmd(env.traj, float(vx[0]), float(vy[0]), float(wz[0]))
    obs = _fresh_obs(env)
    if hasattr(model, "reset"):
        model.reset()
    n = max(1, int(round(seconds / env.dt)))
    for i in range(n):
        k = min(i, len(vx) - 1)
        _set_traj_cmd(env.traj, float(vx[k]), float(vy[k]), float(wz[k]))
        action, _ = model.predict(obs, deterministic=deterministic)
        obs, reward, term, trunc, info = env.step(action)
        rec.record("walk", "policy", info, reward=reward,
                   walk_label=labels[k])
        if term or trunc:
            rec.termination_reason = str(info.get("termination_reason", ""))
            rec.truncated = bool(trunc)
            return False, obs
    _set_traj_cmd(env.traj, 0.0, 0.0, 0.0)
    env.traj.mode = "hold"
    return True, obs


def _write_transfer_manifest(path: Path, plan: dict[str, Any],
                             summary: dict[str, Any]) -> None:
    controllers = plan.get("controllers", {})
    walk = controllers.get("rl_walk", {})
    ckpt = str(walk.get("checkpoint", ""))
    phase_to_controller = {
        str(item.get("phase")): controllers.get(str(item.get("controller")), {})
        for item in plan.get("sequence", [])
    }
    stand = phase_to_controller.get("stand", {})
    lower = phase_to_controller.get("lower", {})

    def stance_component(ctrl: dict[str, Any], *,
                         state: str, role: str) -> dict[str, Any]:
        if ctrl.get("type") == "learned_stance_policy":
            return {
                "state": state,
                "controller": ctrl.get("checkpoint") or ctrl.get("policy"),
                "role": ctrl.get("role", role),
                "profile": ctrl.get("profile", "from policy metadata"),
                "release": ctrl.get(
                    "release",
                    "stable" if ctrl.get("role", role) == "stand"
                    else "profile"),
                "hardware_route": "Use the matching exported JSON in "
                                  "linux_control/policies/ after read-only "
                                  "preflight; do not treat this sim pass as "
                                  "hardware validation.",
            }
        return {
            "state": state,
            "controller": "linux_control/standup_modes.json",
            "mode": ctrl.get("mode", "step"),
            "direction": ctrl.get("direction", "forward"),
            "hardware_route": "RL tab Stand Up uses STEP stand then "
                              "sim walk-ready verification.",
        }

    architecture_note = (
        "SB3 transformer/recurrent checkpoints need a deployable runtime or "
        "distillation/export path. The existing export_policy_np.py path is "
        "for plain MlpPolicy JSON exports.")
    if "tf" not in ckpt and "transformer" not in ckpt:
        architecture_note = (
            "If this checkpoint is an SB3 MlpPolicy, export it with "
            "rl_move.sim.export_policy_np and keep the cfg/control_hz meta "
            "aligned with this demo.")
    manifest = {
        "schema": "hexapod.transfer_candidate.v1",
        "source_demo_summary": str(path / "summary.json"),
        "no_physical_robot_motion_performed": True,
        "candidate_is_composition_not_single_policy": True,
        "components": [
            stance_component(stand, state="belly_zero -> walk_ready",
                             role="stand"),
            {
                "state": "walk_ready -> walk_done",
                "controller": ckpt,
                "policy_mode": walk.get("policy_mode", "deterministic"),
                "joystick_contract": {
                    "body_frame_vx_vy_m_s": True,
                    "demo_script": walk.get("script", ""),
                    "demo_speed_m_s": walk.get("speed_m_s"),
                    "demo_wz_max_rad_s": walk.get("wz_max_rad_s"),
                },
            },
            stance_component(lower, state="walk_ready -> grounded",
                             role="lower"),
        ],
        "transfer_blockers_or_work": [
            architecture_note,
            "Run only the read-only hardware preflight first: 18 servos, IMU, "
            "pose near sim_walk_start or STEP stand, tilt within limit.",
            "Joystick commands must stay inside the trained command envelope "
            "until a hardware ladder says otherwise.",
            "Stop immediately on tip, brownout, high current, missing servo, "
            "or hot motor.",
        ],
        "demo_metrics": {
            "terminated": summary.get("terminated"),
            "termination_reason": summary.get("termination_reason"),
            "walk_progress_ratio": summary.get("walk_progress_ratio"),
            "course_err_1s_med_deg": summary.get("course_err_1s_med_deg"),
            "course_err_1s_p90_deg": summary.get("course_err_1s_p90_deg"),
            "cur_max_a": summary.get("cur_max_a"),
        },
    }
    (path / "transfer_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("checkpoint", nargs="?", type=Path,
                    help="SB3 walk checkpoint. Optional when --composition "
                         "contains controllers.rl_walk.checkpoint")
    ap.add_argument("--composition", type=Path,
                    help="JSON composition to run. Positional checkpoint "
                         "overrides controllers.rl_walk.checkpoint")
    ap.add_argument("--write-composition-template", type=Path,
                    help="write the default composition JSON and exit")
    ap.add_argument("--name", default="")
    ap.add_argument("--stand-mode", default="step")
    ap.add_argument("--lower-mode", default="")
    ap.add_argument("--stand-controller",
                    choices=("scripted", "learned"), default="scripted",
                    help="controller used for belly_zero -> stand")
    ap.add_argument("--lower-controller",
                    choices=("scripted", "learned"), default="scripted",
                    help="controller used for walk_ready -> grounded")
    ap.add_argument("--stance-policy", type=Path,
                    default=None,
                    help="learned stand/lower checkpoint or exported JSON")
    ap.add_argument("--lower-policy", type=Path, default=None,
                    help="optional learned lower checkpoint/JSON; defaults "
                         "to --stance-policy")
    ap.add_argument("--stand-release", choices=("stable", "profile"),
                    default="stable",
                    help="learned stand release mode: stable hands off after "
                         "the ramp plus a short stability window; profile "
                         "runs the policy metadata total_s")
    ap.add_argument("--stand-handoff-stable-s", type=float,
                    default=_STAND_HANDOFF_STABLE_S)
    ap.add_argument("--stand-handoff-settle-s", type=float,
                    default=_STAND_HANDOFF_SETTLE_S)
    ap.add_argument("--stand-handoff-min-z-m", type=float,
                    default=_STAND_HANDOFF_MIN_Z_M)
    ap.add_argument("--stand-handoff-max-tilt-deg", type=float,
                    default=_STAND_HANDOFF_MAX_TILT_DEG)
    ap.add_argument("--stand-handoff-max-current-a", type=float,
                    default=_STAND_HANDOFF_MAX_CURRENT_A)
    ap.add_argument("--stand-time-scale", type=float, default=1.0)
    ap.add_argument("--lower-time-scale", type=float, default=1.0)
    ap.add_argument("--walk-ready-align-s", type=float, default=0.75)
    ap.add_argument("--pre-lower-align-s", type=float, default=0.75)
    ap.add_argument("--limp-after-lower-s", type=float, default=2.0)
    ap.add_argument("--script", choices=("square", "human", "sweep",
                                         "human_turn", "turn"),
                    default="human")
    ap.add_argument("--walk-seconds", type=float, default=20.0)
    ap.add_argument("--speed", type=float, default=0.08)
    ap.add_argument("--wz-max", type=float, default=0.3,
                    help="max scripted yaw rate for turn-capable scripts")
    ap.add_argument("--blend-s", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dr-scale", type=float, default=0.0)
    ap.add_argument("--policy-mode", choices=("deterministic", "stochastic"),
                    default="deterministic")
    ap.add_argument("--render-every", type=int, default=0,
                    help="control ticks between rendered frames. 0 chooses "
                         "about 25 fps from the configured control.hz")
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--cfg-set", action="append", default=[])
    ap.add_argument("--model-source", choices=("mesh", "mesh_mjx",
                    "primitive"), default="mesh")
    ap.add_argument("--allow-mesh-fallback", action="store_true",
                    help="allow env.model_source=mesh to fall back to the "
                         "checked-in mesh_mjx twin when full STL assets are "
                         "missing")
    args = ap.parse_args()

    plan = _load_composition(args)
    if args.write_composition_template is not None:
        args.write_composition_template.write_text(
            json.dumps(plan, indent=2) + "\n")
        print(args.write_composition_template)
        return 0

    controllers = plan.get("controllers", {})
    sequence = plan.get("sequence", [])
    walk_ctrl = controllers.get("rl_walk", {})
    checkpoint_raw = str(walk_ctrl.get("checkpoint") or "").strip()
    if not checkpoint_raw:
        raise SystemExit("no walk checkpoint supplied")
    checkpoint = Path(checkpoint_raw)

    from rl_move.config import load_config
    from rl_move.env import TaskGoal
    from .eval_checkpoint import _save_video, model_identity
    from .play_core import _PlayEnv
    from .servo_model import SimServoParams, motor_contract
    from .train_ppo_sim import _parse_cfg_set

    cfg = load_config()
    for key, parsed in _parse_cfg_set(args.cfg_set).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    cfg.setdefault("env", {})["model_source"] = str(
        plan.get("model_source") or args.model_source)
    cfg.setdefault("goal", {})["walk_park_start_frac"] = 0.0

    total_s = 120.0
    try:
        stand_modes = _load_standup_modes()
        mode = str(controllers.get("scripted_stand", {}).get("mode", "step"))
        lower = str(controllers.get("scripted_lower", {}).get("mode", mode))
        total_s += sum(float(k["s"]) for k in
                       stand_modes["modes"][mode]["keyframes"])
        total_s += sum(float(k["s"]) for k in
                       stand_modes["modes"][lower]["keyframes"])
    except Exception:
        stand_modes = _load_standup_modes()
    total_s += float(walk_ctrl.get("seconds", args.walk_seconds))

    env = _PlayEnv(
        params=SimServoParams.from_cfg(cfg),
        randomize=args.dr_scale > 0,
        dr_scale=args.dr_scale,
        episode_seconds=total_s,
        seed=args.seed,
        render_mode="rgb_array",
        cfg=cfg,
    )
    env.traj._dt = env.dt
    identity = model_identity(env)
    if (cfg["env"].get("model_source") == "mesh"
            and identity["model_variant"] != "full_mesh"
            and not args.allow_mesh_fallback):
        raise SystemExit(
            "full mesh assets are missing; run "
            "`uv run --with numpy --with scipy --with shapely --with trimesh "
            "python mesh_mujoco/build_mesh_model.py --no-render` from the "
            "prototype dir, or pass --allow-mesh-fallback explicitly")

    # The composition contract accepts either an SB3 checkpoint or the exact
    # portable JSON consumed by the board.  Keep the closed-loop demo on that
    # shared loader so a hardware candidate is tested after serialization,
    # rather than silently falling back to its pre-export torch checkpoint.
    model = _load_any_policy(checkpoint)
    if model.observation_space.shape != env.observation_space.shape:
        raise SystemExit(
            f"obs mismatch: policy {model.observation_space.shape} vs env "
            f"{env.observation_space.shape}; pass the run's cfg stack via "
            "--cfg-set or use ops.sh hybriddemo <run>")
    traj = env.traj
    traj.start_at = "plant"
    traj.goal = TaskGoal()
    _set_traj_cmd(traj, 0.0, 0.0, 0.0)
    traj.mode = "hold"
    traj.reset_published()
    _plant_obs, plant_reset_info = env.reset()
    plant_z = _chassis_z(env)

    traj.start_at = "zero"
    traj.goal = TaskGoal()
    _set_traj_cmd(traj, 0.0, 0.0, 0.0)
    traj.mode = "rise"
    traj.reset_published()
    _obs, reset_info = env.reset()
    reset_info = {"zero_reset": reset_info, "plant_reset": plant_reset_info,
                  "plant_z_m": plant_z}

    hz = 1.0 / max(env.dt, 1e-9)
    render_stride = (args.render_every if args.render_every > 0
                     else max(1, int(round(hz / 25.0))))
    out = args.out_dir or (
        _PROTO / "logs" / "manual_drive" /
        f"{checkpoint.stem}_hybrid_{time.strftime('%Y%m%d_%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)
    rec = _Recorder(env, render_stride=render_stride, plan=plan)
    stance_models: dict[str, tuple[Any, int, Path]] = {}

    ok = True
    for item in sequence:
        phase = str(item.get("phase", item.get("controller", "")))
        ctrl_name = str(item.get("controller", ""))
        ctrl = controllers.get(ctrl_name)
        if not isinstance(ctrl, dict):
            rec.phase_errors.append(f"{phase}: unknown controller {ctrl_name}")
            ok = False
            break
        rec.mark(phase, "start", from_state=item.get("from_state"),
                 to_state=item.get("to_state"), controller=ctrl_name)
        kind = str(ctrl.get("type", ""))
        if kind == "standup_mode":
            ok, _obs = _run_standup_mode(env, rec, stand_modes, phase, ctrl)
        elif kind == "pose_blend":
            env.traj.mode = "hold"
            target = _target_pose_rad(str(ctrl.get("target", "")), env)
            ok, _obs = _run_pose_blend(
                env, rec, phase, target, float(ctrl.get("seconds", 0.75)),
                label=str(ctrl.get("target", "pose")))
        elif kind == "bookkeeping_reanchor":
            _reanchor(env, start_at=str(ctrl.get("start_at", "plant")),
                      mode=str(ctrl.get("mode", "hold")))
            _obs = _fresh_obs(env)
            rec.record(phase, "reanchor", {})
            ok = True
        elif kind == "sb3_walk_policy":
            ok, _obs = _run_walk(env, rec, ctrl, model)
        elif kind == "learned_stance_policy":
            raw = ctrl.get("checkpoint") or ctrl.get("policy")
            if not raw:
                rec.phase_errors.append(
                    f"{phase}: learned stance controller has no checkpoint")
                ok = False
            else:
                p = _project_path(str(raw))
                if not p.exists():
                    rec.phase_errors.append(
                        f"{phase}: stance checkpoint missing: {p}")
                    ok = False
                else:
                    key = str(p.resolve())
                    if key not in stance_models:
                        stance_model = _load_any_policy(p)
                        n_obs = int(np.prod(
                            stance_model.observation_space.shape))
                        n_env = int(np.prod(env.observation_space.shape))
                        if n_obs > n_env:
                            raise SystemExit(
                                f"stance obs mismatch: policy {(n_obs,)} vs "
                                f"env {env.observation_space.shape}")
                        stance_models[key] = (stance_model, n_obs, p)
                    stance_model, n_obs, p = stance_models[key]
                    ok, _obs = _run_learned_stance(
                        env, rec, phase, ctrl, stance_model, n_obs, p)
        elif kind == "limp_settle":
            ok, _obs = _run_limp(env, rec, phase,
                                 float(ctrl.get("seconds", 2.0)))
        else:
            rec.phase_errors.append(f"{phase}: unsupported controller {kind}")
            ok = False
        rec.mark(phase, "end", ok=ok, rows=len(rec.rows))
        if not ok:
            break

    summary = rec.summary(
        identity=identity, reset_info=reset_info,
        motor_contract=motor_contract(cfg, backend="servo_profile_np"))
    (out / "composition.json").write_text(json.dumps(plan, indent=2) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / "ticks.json").write_text(json.dumps(rec.rows, indent=1) + "\n")
    _write_transfer_manifest(out, plan, summary)
    _save_video(rec.frames, out / "drive")
    if (out / "drive.png").exists():
        (out / "contact_sheet.png").write_bytes((out / "drive.png").read_bytes())

    print(json.dumps(summary, indent=2))
    print(f"[hybrid_demo] artifacts -> {out}")
    env.close()
    return 0 if ok and not summary.get("terminated") else 1


if __name__ == "__main__":
    raise SystemExit(main())
