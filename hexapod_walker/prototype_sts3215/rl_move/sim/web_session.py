"""MuJoCo session object controlled by the hexapod web UI API."""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_move.env import TaskGoal, build_obs
from rl_move.safety import SafetyLayer
from hexapod_core.demo_tripod import (
    DEFAULT_DEMO_TRIPOD, DemoTripodPreset, format_demo_tripod,
    parse_demo_tripod_tune_tokens, tune_demo_tripod,
)
from linux_control.cpg_controller_loader import (  # noqa: E402
    list_cpg_controllers as _list_cpg_controllers,
    load_cpg_controller as _load_cpg_controller,
)

from .joint_task import action_to_q_rad, q_rad_to_action
from hexapod_core.joint_frame import (
    FRAME_ROBOT_ABS,
    JOINT_CONTRACT,
    mujoco_rel_rad_to_robot_abs_deg,
    robot_abs_rad_to_mujoco_rel_rad,
)
from hexapod_core.scripted_walk_contract import (
    SCRIPTED_WALK_ACC_UNITS,
    SCRIPTED_WALK_SPEED_COUNTS_S,
)
from .play_core import (
    _CRUISE,
    _DESC,
    _HIST_K,
    _DEFAULT_STANCE_PROFILE,
    _MIDDLE_TUCK_QUAD,
    _N_MODE,
    _NOSLIP,
    _NOSLIP_CLEAN,
    _NOSLIP_FLUID,
    _NOSLIP_FLUID_FAST,
    _NOSLIP_FLUID_HYBRID,
    _NOSLIP_FLUID_PULSE,
    _NOSLIP_FLUID_PUSH,
    _NOSLIP_RIPPLE,
    _NOSLIP_WAVE,
    _ROLE_OBS,
    _SE2_CPG,
    _SE2_TETRAPOD,
    _SE2_WAVE,
    _SCRIPTED_ROWS,
    _SCRIPTED_SE2,
    _SCRIPTED_TRIPOD,
    make_noslip_gait,
    _SPEED_MAX,
    _TRIPOD_HW,
    _load_profiles,
    _obs_width,
    _sim_only_obs,
    _PlayEnv,
    scan_policies,
)

QUAD_VARIANTS = {
    "_safe": ("rear_safe", "walk_safe", "trot_safe", "safe"),
    "": ("rear", "walk", "trot", "cool"),
    "_pitch": ("rear_pitch", "walk_pitch", "trot_pitch", "pitched"),
    "_aft": ("rear_aft", "walk_aft", "trot_aft", "aft-shift"),
    "_high": ("rear_high", "walk_high", "trot_high", "high-body"),
    "_step": ("rear_step", "walk_step", "trot_step", "high-step"),
    "_aggressive": (
        "rear_aggressive", "walk_aggressive", "trot_aggressive",
        "aggressive"),
}


def _quad_name(action: str, suffix: str) -> str:
    return f"quad_{action}{suffix}"


QUAD_REAR_DEMOS = tuple(
    _quad_name("rear", suffix) for suffix in QUAD_VARIANTS)
QUAD_DOWN_DEMOS = tuple(
    _quad_name("down", suffix) for suffix in QUAD_VARIANTS)
QUAD_REARED_END_DEMOS = tuple(
    _quad_name(action, suffix)
    for suffix in QUAD_VARIANTS
    for action in ("rear", "hold", "walk", "walk_back",
                   "trot", "trot_back"))
QUAD_REQUIRES_REAR = tuple(
    _quad_name(action, suffix)
    for suffix in QUAD_VARIANTS
    for action in ("hold", "walk", "walk_back", "trot",
                   "trot_back", "down"))
QUAD_STREAM_DEMOS = (*QUAD_REARED_END_DEMOS, *QUAD_DOWN_DEMOS)
QUAD_DEMO_GAITS = {}
for _quad_suffix, (_rear_gait, _walk_gait, _trot_gait, _label) in (
        QUAD_VARIANTS.items()):
    QUAD_DEMO_GAITS[_quad_name("rear", _quad_suffix)] = _rear_gait
    QUAD_DEMO_GAITS[_quad_name("hold", _quad_suffix)] = _rear_gait
    QUAD_DEMO_GAITS[_quad_name("down", _quad_suffix)] = _rear_gait
    QUAD_DEMO_GAITS[_quad_name("walk", _quad_suffix)] = _walk_gait
    QUAD_DEMO_GAITS[_quad_name("walk_back", _quad_suffix)] = _walk_gait
    QUAD_DEMO_GAITS[_quad_name("trot", _quad_suffix)] = _trot_gait
    QUAD_DEMO_GAITS[_quad_name("trot_back", _quad_suffix)] = _trot_gait


def _quad_action(name: str) -> str:
    for suffix in sorted(QUAD_VARIANTS, key=len, reverse=True):
        if suffix and name.endswith(suffix):
            return name[:-len(suffix)].removeprefix("quad_")
    return name.removeprefix("quad_")


def _ms_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"samples": 0}
    arr = np.asarray(values, dtype=float) * 1000.0
    return {
        "samples": int(arr.size),
        "mean_ms": round(float(np.mean(arr)), 3),
        "p50_ms": round(float(np.percentile(arr, 50)), 3),
        "p95_ms": round(float(np.percentile(arr, 95)), 3),
        "max_ms": round(float(np.max(arr)), 3),
    }


_DRIVE_HEARTBEAT_STALE_S = 0.6
_DRIVE_HOLD_SWITCH_S = 1.5
_DRIVE_MOVE_EPS_MPS = 1e-4
_DRIVE_YAW_EPS_RAD_S = 1e-4


@dataclass
class SimWebConfig:
    policy_dir: Path
    stance: Path | None
    walk: Path
    recover: Path
    log_dir: Path
    realtime: float = 1.0
    viewer: bool = False
    web_frames: bool = True
    phase_obs: bool = False
    phase_hz: float = 0.1666667
    all_models: bool = False


class SimWebSession:
    """Route-compatible controller for one local MuJoCo hexapod."""

    STAND_HANDOFF_STABLE_S = 0.60
    STAND_HANDOFF_SETTLE_S = 0.25
    STAND_HANDOFF_MAX_TILT_DEG = 7.0
    STAND_HANDOFF_MAX_CURRENT_A = 2.2

    def __init__(self, cfg: SimWebConfig):
        self.cfg = cfg
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.msg = "starting MuJoCo"
        self.armed = False
        self.mode = "hold"
        self.auto: list | None = None
        self.downed = False
        self.sitting = False
        self.drive_active = False
        self.last_drive_cmd_at = 0.0
        self.drive_zero_since: float | None = None
        self.drive_last_vx = 0.0
        self.drive_last_vy = 0.0
        self.drive_last_wz = 0.0
        self.timed_walk_until: float | None = None
        self.job_kind: str | None = None
        self.job_result: dict[str, Any] = {"ok": True, "ended": "idle"}
        self.sim_t = 0.0
        self.gait = None
        self.gait_t = 0.0
        self.om_cmd = 0.0
        self.demo_tripod: DemoTripodPreset = DEFAULT_DEMO_TRIPOD
        self._cpg_loaded: dict[str, Any] | None = None
        self.hist: list[np.ndarray] | None = None
        self.gru = {"state": None, "start": np.ones((1,), dtype=bool)}
        self.push_ticks = 0
        self.push_force = np.zeros(3, dtype=float)
        self.demo_name: str | None = None
        self.demo_status = "idle"
        self.demo_params: dict[str, Any] = {}
        self.demo_speed_live = 1.0
        self.demo_pose_fn = None
        self.demo_t = 0.0
        self.demo_duration = 0.0
        self.demo_started_sim_t = 0.0
        self.demo_telemetry: dict[str, Any] | None = None
        # Dance scripts (dances-as-data, hexapod_core/dance_script.py):
        # notes = [(t, msg)] surfaced live; cap = tightest per-act speed cap.
        self.demo_notes: list[tuple[float, str]] = []
        self.demo_note: str = ""
        self.demo_speed_cap: float | None = None
        self.demo_is_script = False
        self.demo_end_home = ""
        self.demo_direct_profile = False
        self.demo_write_speed_deg_s: float | None = None
        self.demo_write_acc_units: float | None = None
        self.demo_last_target_deg: list[float] | None = None
        self.quad_reared = False
        self.pose_hold_q: np.ndarray | None = None
        self.command_log: list[tuple[float, str, str | None]] = []
        self.last_command = ""
        self.log_dir = cfg.log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._log_fp = None
        self._log_writer = None
        self._log_name = ""
        self._last_log_row_t = -1.0
        self.roles: dict[str, str] = {}
        self.role_models: dict[str, tuple[Any, Path, int] | str] = {}
        self._frame_ready = threading.Event()
        self._frame_jpeg: bytes | None = None
        self._frame_error = ""
        self._frame_interval_s = 1.0 / 8.0
        self._last_frame_at = 0.0
        self.thread: threading.Thread | None = None
        self.cv2 = None

        self._load_runtime()
        if not cfg.viewer:
            self.thread = threading.Thread(target=self._run,
                                           name="sim-web-tick",
                                           daemon=True)
            self.thread.start()

    def _load_runtime(self) -> None:
        import mujoco
        from stable_baselines3 import PPO

        from .servo_model import SimServoParams
        from ..config import load_config

        root = Path(__file__).resolve().parents[2]
        self._proto_root = root
        from hexapod_core.middle_tuck_quad_gait import MiddleTuckQuadGait
        from hexapod_core.noslip_gait import NoSlipGait
        from hexapod_core.se2_foot_gait import SE2FootGait
        from hexapod_core.tripod_gait import TripodGait

        self.mujoco = mujoco
        self.PPO = PPO
        if self.cfg.web_frames:
            import cv2
            self.cv2 = cv2
        self.load_checkpoint_auto = self._load_checkpoint_auto
        self.MiddleTuckQuadGait = MiddleTuckQuadGait
        self.NoSlipGait = NoSlipGait
        self.SE2FootGait = SE2FootGait
        self.TripodGait = TripodGait

        cfg = load_config()
        cfg.setdefault("obs", {})["mode_onehot"] = 1.0
        cfg["obs"]["mode_onehot_cmd"] = 1.0
        self.walk_widths: tuple[int, ...] = (72, 78, 1152)
        if self.cfg.phase_obs:
            cfg.setdefault("goal", {})["walk_phase_obs"] = 1.0
            cfg["goal"]["walk_phase_hz"] = self.cfg.phase_hz
            _ROLE_OBS[74] = "walk"
            self.walk_widths = (72, 74, 78, 1152)
        render_mode = "rgb_array" if self.cfg.web_frames else None
        self.env = _PlayEnv(params=SimServoParams.from_cfg(cfg),
                            randomize=False, episode_seconds=3600.0,
                            render_mode=render_mode, cfg=cfg)
        self.traj = self.env.traj
        self.chassis_bid = self.env.model.body("chassis").id
        self.profiles = _load_profiles()

        cats = scan_policies(self.cfg.policy_dir,
                             all_models=self.cfg.all_models)
        self.rejected_policy_errors: dict[str, str] = {}
        self.stance_list = self._current_contract_policies(cats["stance"])
        self.walk_list = self._current_contract_policies(cats["walk"])
        self.walk_list.extend([
            _NOSLIP, _NOSLIP_CLEAN, _NOSLIP_RIPPLE, _NOSLIP_WAVE,
            _NOSLIP_FLUID, _NOSLIP_FLUID_FAST, _NOSLIP_FLUID_HYBRID,
            _NOSLIP_FLUID_PUSH, _NOSLIP_FLUID_PULSE,
            _SE2_TETRAPOD, _SE2_WAVE, _SE2_CPG,
            _MIDDLE_TUCK_QUAD,
        ])
        self.walk_list.extend(_SCRIPTED_TRIPOD)

        self.stance = None
        self.n_stance = 68
        self.si = -1
        if self.cfg.stance is not None:
            try:
                self.si = self._ensure_listed(
                    self.stance_list, self.cfg.stance, (68,))
                self.stance = self._load_model(
                    self.stance_list[self.si], device="cpu")
                self.n_stance = int(self.stance.observation_space.shape[0])
            except (FileNotFoundError, OSError, ValueError) as exc:
                self.rejected_policy_errors[str(self.cfg.stance)] = str(exc)

        try:
            if self.cfg.walk in _SCRIPTED_ROWS:
                self.wi = self.walk_list.index(self.cfg.walk)
            else:
                self.wi = self._ensure_listed(
                    self.walk_list, self.cfg.walk, self.walk_widths)
        except (FileNotFoundError, OSError, ValueError) as exc:
            self.rejected_policy_errors[str(self.cfg.walk)] = str(exc)
            self.wi = self.walk_list.index(_TRIPOD_HW)
        self.policy_index = self._build_policy_index()
        self._register_uploaded_policies()

        self.n_env = int(self.env.observation_space.shape[0])
        selected_walk = self.walk_list[self.wi]
        if selected_walk in _SCRIPTED_ROWS:
            self.walk = None
            self.n_walk = 72
            self.walk_kind = "plain"
        else:
            self.walk = self._load_model(selected_walk, device="cpu")
            self.n_walk = int(self.walk.observation_space.shape[0])
            self.walk_kind = self._walk_kind_of(self.n_walk)
            if self.walk_kind == "plain" and self.n_walk > self.n_env:
                raise ValueError(f"{selected_walk} needs --phase-obs")
        self.recover = None
        if self.cfg.recover.exists():
            try:
                self.recover = self._load_model(
                    self.cfg.recover, device="cpu")
            except (OSError, ValueError) as exc:
                self.rejected_policy_errors[str(self.cfg.recover)] = str(exc)

        self._regime_base: dict[str, Any] = {}
        self.servo_fit_counts = float(
            getattr(SimServoParams.load(), "speed_counts_s", 350.0))
        if self.walk is not None:
            self._apply_vel_contract(self.walk_list[self.wi].stem)

        self.traj.start_at = "plant"
        self.obs, _ = self.env.reset()
        self.q_plant = self._q_now()
        self.z_plant = self._chassis_z()
        self.q_sit = self.q_plant.copy()
        hidden = len(self.rejected_policy_errors)
        stance_note = ("" if self.stance is not None
                       else "; no v2 stance selected")
        hidden_note = (f"; {hidden} pre-v2/missing policies rejected"
                       if hidden else "")
        self.msg = f"ready: {self._active_walk_name()}{stance_note}{hidden_note}"

    def _load_checkpoint_auto(self, path: Path, device: str = "cpu"):
        """Load plain PPO checkpoints without requiring sb3-contrib.

        Only 78-obs recurrent GRU checkpoints need ``gru_policy`` and its
        sb3-contrib dependency; the default web-sim stance/walk pair is
        plain PPO and should start in a lean local venv.
        """
        from hexapod_core.joint_frame import require_checkpoint_joint_contract
        require_checkpoint_joint_contract(path)
        if _obs_width(path) == 78:
            from .gru_policy import load_checkpoint_auto
            model = load_checkpoint_auto(path, device=device)
        else:
            model = self.PPO.load(path, device=device)
        return model

    # -- uploaded numpy policies (policies as data, rl_move/np_policy) ---
    # The robot's export_policy_np.py JSON is an uploadable artifact:
    # POST /api/rl/policies lands in ~/.hexapod_policies, the picker
    # lists it next to the checkpoint zips, and select/role/run all
    # work — the same file drives the sim and any robot.

    @staticmethod
    def _policy_obs_width(p: Path) -> int | None:
        if p.suffix == ".json":
            from ..np_policy import np_policy_obs_width
            return np_policy_obs_width(p)
        return _obs_width(p)

    def _policy_contract_error(self, p: Path) -> str:
        try:
            if p.suffix == ".json":
                from ..np_policy import validate_np_policy
                obj = json.loads(p.read_text())
                errors, _ = validate_np_policy(obj)
                if errors:
                    return "; ".join(errors[:3])
            else:
                from hexapod_core.joint_frame import (
                    require_checkpoint_joint_contract,
                )
                require_checkpoint_joint_contract(p)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return str(exc)
        return ""

    def _current_contract_policies(self, paths: list[Path]) -> list[Path]:
        current: list[Path] = []
        for path in paths:
            error = self._policy_contract_error(path)
            if error:
                self.rejected_policy_errors[str(path)] = error
            else:
                current.append(path)
        return current

    def _load_model(self, p: Path, device: str = "cpu"):
        if p.suffix == ".json":
            from ..np_policy import load_np_policy
            m = load_np_policy(p)
            prof = m.meta.get("profile")
            if isinstance(prof, dict):
                # Trained goal ramps travel with the file — same
                # contract as the robot runner.
                self.profiles[p.stem] = prof
            return m
        return self._load_checkpoint_auto(p, device=device)

    def _register_uploaded_policies(self) -> None:
        from ..np_policy import UPLOAD_DIR
        try:
            paths = sorted(UPLOAD_DIR.glob("*.json"))
        except OSError:
            paths = []
        for p in paths:
            error = self._policy_contract_error(p)
            if error:
                self.rejected_policy_errors[str(p)] = error
                continue
            w = self._policy_obs_width(p)
            p = p.resolve()
            if w == 68 and p not in self.stance_list:
                self.stance_list.append(p)
            elif w in (72, 74) and p not in self.walk_list:
                self.walk_list.append(p)
        self.policy_index = self._build_policy_index()

    def save_rl_policy(self, obj, *, name: str = "") -> dict[str, Any]:
        from ..np_policy import (UPLOAD_DIR, safe_policy_name,
                                 validate_np_policy)
        errs, info = validate_np_policy(obj)
        if errs:
            return {"ok": False, "error": "; ".join(errs[:5])}
        stem = safe_policy_name(name or info.get("name") or "")
        if stem is None:
            return {"ok": False,
                    "error": "need a name ([A-Za-z0-9._-]{1,64}) — "
                             "?name=... or meta.name"}
        try:
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            p = UPLOAD_DIR / f"{stem}.json"
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(obj))
            tmp.replace(p)
        except OSError as e:
            return {"ok": False, "error": f"save failed: {e}"}
        with self.lock:
            self._record_command(f"/api/rl/policies upload {stem}")
            self._register_uploaded_policies()
        return {"ok": True, "file": p.name, "obs_dim": info["obs_dim"],
                "slot": "stance" if info["obs_dim"] == 68 else "walk",
                "hidden": info.get("hidden"), "bytes": p.stat().st_size}

    def get_rl_policy(self, file: str) -> str | None:
        name = Path(str(file)).name
        if not name.endswith(".json"):
            name += ".json"
        from ..np_policy import UPLOAD_DIR
        p = UPLOAD_DIR / name
        try:
            return p.read_text() if p.is_file() else None
        except OSError:
            return None

    def delete_rl_policy(self, file: str) -> dict[str, Any]:
        from ..np_policy import UPLOAD_DIR
        name = Path(str(file)).name
        if not name.endswith(".json"):
            name += ".json"
        p = (UPLOAD_DIR / name).resolve()
        if not p.is_file():
            return {"ok": False, "error": f"no uploaded policy {name!r}"}
        with self.lock:
            active = {self.walk_list[self.wi]}
            if self.si >= 0:
                active.add(self.stance_list[self.si])
            in_role = any(isinstance(e, tuple) and e[1] == p
                          for e in self.role_models.values())
            if p in active or in_role:
                return {"ok": False,
                        "error": f"{name} is selected/role-assigned — "
                                 f"switch away first"}
            try:
                p.unlink()
            except OSError as e:
                return {"ok": False, "error": str(e)}
            keep_s = self.stance_list[self.si] if self.si >= 0 else None
            keep_w = self.walk_list[self.wi]
            if p in self.stance_list:
                self.stance_list.remove(p)
            if p in self.walk_list:
                self.walk_list.remove(p)
            self.si = (self.stance_list.index(keep_s)
                       if keep_s is not None else -1)
            self.wi = self.walk_list.index(keep_w)
            self.policy_index = self._build_policy_index()
        return {"ok": True, "deleted": name}

    def _ensure_listed(self, lst: list[Path], p: Path,
                       want: tuple[int, ...]) -> int:
        if not p.exists():
            raise FileNotFoundError(
                f"{p} not found; pass --policy-dir or pull checkpoints first")
        w = self._policy_obs_width(p)
        if w not in want:
            raise ValueError(f"{p}: obs width {w}, need one of {want}")
        error = self._policy_contract_error(p)
        if error:
            raise ValueError(error)
        p = p.resolve()
        if p not in lst:
            lst.insert(0, p)
        return lst.index(p)

    def _build_policy_index(self) -> dict[str, Path]:
        out: dict[str, Path] = {}
        for p in self.stance_list + self.walk_list:
            out[p.name] = p
            out[p.stem] = p
        for p in _SCRIPTED_ROWS:
            out[f"scripted:{p.name}"] = p
            out[p.name] = p
        return out

    @staticmethod
    def _ckpt_regime(stem: str) -> dict[str, float] | None:
        regimes = (
            (("fasttrack1", "steer6", "fastnoslip"),
             dict(speed=1500.0, acc=80.0, clamp_deg=5.0,
                  cruise=0.08, vmax=0.10)),
            (("middose", "midnoslip"),
             dict(speed=750.0, acc=40.0, clamp_deg=3.0,
                  cruise=0.08, vmax=0.10)),
        )
        for tokens, regime in regimes:
            if any(t in stem for t in tokens):
                return regime
        return None

    @staticmethod
    def _walk_kind_of(width: int) -> str:
        return {1152: "hist", 78: "gru"}.get(width, "plain")

    def _apply_vel_contract(self, stem: str) -> None:
        if self._ckpt_regime(stem) is not None:
            mode = 3.0
        else:
            mode = 1.0 if _sim_only_obs("walk", stem) else 2.0
        self.env.cfg.setdefault("goal", {})["walk_obs_body_vel"] = mode

    def _reset_memories(self, hard: bool) -> None:
        self.hist = None
        if hard:
            self.gru["state"] = None
            self.gru["start"] = np.ones((1,), dtype=bool)

    def _walk_predict(self) -> np.ndarray:
        if self.walk_kind == "hist":
            frame = self.obs[:72].copy()
            if self.hist is None:
                self.hist = [frame.copy() for _ in range(_HIST_K)]
            else:
                self.hist.pop()
                self.hist.insert(0, frame)
            a, _ = self.walk.predict(np.concatenate(self.hist),
                                     deterministic=True)
            return a
        if self.walk_kind == "gru":
            o = np.concatenate([self.obs[:72], self.obs[-_N_MODE:]])
            a, self.gru["state"] = self.walk.policy.predict(
                o, state=self.gru["state"],
                episode_start=self.gru["start"], deterministic=True)
            self.gru["start"] = np.zeros((1,), dtype=bool)
            return a
        a, _ = self.walk.predict(self.obs[:self.n_walk], deterministic=True)
        return a

    def _chassis_z(self) -> float:
        return float(self.env.data.xpos[self.chassis_bid, 2])

    def _q_now(self) -> np.ndarray:
        return self.env.data.qpos[7:25].copy()

    def _q_now_robot_abs(self) -> np.ndarray:
        from hexapod_core.joint_frame import mujoco_rel_rad_to_robot_abs_rad
        return mujoco_rel_rad_to_robot_abs_rad(self._q_now())

    def _roll_pitch_deg(self) -> tuple[float, float]:
        qw, qx, qy, qz = self.env.data.qpos[3:7]
        roll = math.atan2(2 * (qw * qx + qy * qz),
                          1 - 2 * (qx * qx + qy * qy))
        pitch = math.asin(max(-1.0, min(1.0, 2 * (qw * qy - qz * qx))))
        return round(math.degrees(roll), 1), round(math.degrees(pitch), 1)

    def _body_vel(self) -> tuple[float, float]:
        try:
            v = self.env._body_vel_xy()
            return float(v[0]), float(v[1])
        except Exception:
            return 0.0, 0.0

    def _clear_drive_dwell(self) -> None:
        self.drive_zero_since = None
        self.drive_last_vx = 0.0
        self.drive_last_vy = 0.0
        self.drive_last_wz = 0.0

    def _drive_cmd_moving(self, vx: float, vy: float, wz: float) -> bool:
        return (float(np.hypot(vx, vy)) > _DRIVE_MOVE_EPS_MPS
                or abs(wz) > _DRIVE_YAW_EPS_RAD_S)

    def _drive_remember_refs(self) -> None:
        if self._drive_cmd_moving(self.traj.vx, self.traj.vy, self.om_cmd):
            self.drive_last_vx = float(self.traj.vx)
            self.drive_last_vy = float(self.traj.vy)
            self.drive_last_wz = float(self.om_cmd)

    def _drive_zero_dwell_remaining(self,
                                    now: float | None = None) -> float:
        if self.drive_zero_since is None or not self.drive_active:
            return 0.0
        if now is None:
            now = time.monotonic()
        return max(0.0, _DRIVE_HOLD_SWITCH_S
                   - (float(now) - self.drive_zero_since))

    def _drive_neutral_dwell_locked(self, now: float) -> bool:
        was_walking = (
            self.mode == "walk"
            or self._drive_cmd_moving(self.traj.vx, self.traj.vy, self.om_cmd)
        )
        if not was_walking:
            self.drive_zero_since = None
            return False
        if self.drive_zero_since is None:
            self.drive_zero_since = now
        if self._drive_zero_dwell_remaining(now) <= 0.0:
            return False
        if not self._drive_cmd_moving(
                self.traj.vx, self.traj.vy, self.om_cmd):
            vx = self.drive_last_vx
            vy = self.drive_last_vy
            wz = self.drive_last_wz
            if not self._drive_cmd_moving(vx, vy, wz):
                vx, _vmax = self._drive_band()
                vy = 0.0
                wz = 0.0
            self.traj.vx = float(vx)
            self.traj.vy = float(vy)
            self._set_drive_wz(float(wz))
        self.msg = "drive coasting before hold"
        return True

    def _published_height_ref(self) -> float:
        pub = getattr(self.traj, "_pub", self.traj.goal)
        return float(getattr(pub, "height_ref", self.traj.goal.height_ref))

    def _do_reset(self, start: str, h_goal: float, note: str) -> None:
        self._stop_demo_locked(status="idle", clear_name=True)
        self.quad_reared = False
        self.pose_hold_q = None
        self.auto = None
        self.downed = False
        self.sitting = False
        self.drive_active = False
        self._clear_drive_dwell()
        self.timed_walk_until = None
        self.gait = None
        self.gait_t = 0.0
        self.om_cmd = 0.0
        self.traj.start_at = start
        self.traj.goal = TaskGoal()
        self.traj.goal.height_ref = h_goal
        self.traj.vx = self.traj.vy = 0.0
        self.traj.mode = "hold"
        self.traj.reset_published()
        self._reset_memories(hard=True)
        self.obs, _ = self.env.reset()
        if start == "plant":
            self.q_plant = self._q_now()
            self.z_plant = self._chassis_z()
        self.msg = note
        self._finish_job(note)

    def _demo_running(self) -> bool:
        return self.demo_pose_fn is not None

    def _set_demo_safety(self, wide: bool) -> None:
        """Widen the tilt trip while an open-loop demo plays.

        The RL episode terminates at 10 deg body tilt — correct for
        policies, but scripted choreography legitimately exceeds it
        (quad rear is -20 deg pitch by design; the robot guards these
        acts at 45 deg). 60 deg still catches a genuine tip-over.
        """
        s = self.env.safety
        if "tilt" not in self._regime_base:
            self._regime_base["tilt"] = (s.max_roll, s.max_pitch)
        if wide:
            s.max_roll = s.max_pitch = math.radians(60.0)
        else:
            s.max_roll, s.max_pitch = self._regime_base["tilt"]

    def _stop_demo_locked(self, status: str = "aborted",
                          clear_name: bool = False) -> None:
        if self._regime_base.get("tilt"):
            self._set_demo_safety(False)
        self.demo_pose_fn = None
        self.demo_t = 0.0
        self.demo_duration = 0.0
        self.demo_status = status
        self.demo_params = {}
        self.demo_notes = []
        self.demo_note = ""
        self.demo_speed_cap = None
        self.demo_is_script = False
        self.demo_end_home = ""
        self.demo_direct_profile = False
        self.demo_write_speed_deg_s = None
        self.demo_write_acc_units = None
        self.demo_last_target_deg = None
        if clear_name:
            self.demo_name = None
            self.demo_telemetry = None
        self._close_log()

    def _demo_speed_eff_locked(self) -> float:
        speed = float(self.demo_speed_live)
        if self.demo_name in QUAD_DEMO_GAITS:
            try:
                from hexapod_core import quad_walk as QW
                gait = QUAD_DEMO_GAITS[self.demo_name]
                cap = QW.GAITS.get(gait, {}).get("speed_cap")
                if cap is not None:
                    speed = min(speed, float(cap))
            except Exception:
                pass
        if self.demo_speed_cap is not None:
            speed = min(speed, float(self.demo_speed_cap))
        hi = 10.0 if (self.demo_name or "").startswith("standup_") else 3.0
        return max(0.25, min(hi, speed))

    def _record_command(self, text: str, key: str | None = None) -> None:
        clean = " ".join(str(text).split())
        if len(clean) > 80:
            clean = clean[:77] + "..."
        self.last_command = clean
        row = (float(self.sim_t), clean, key)
        if key and self.command_log and self.command_log[-1][2] == key:
            self.command_log[-1] = row
        else:
            self.command_log.append(row)
            del self.command_log[:-6]

    def _scripted_tripod_kw(self, p: Path) -> dict[str, Any] | None:
        if p == _TRIPOD_HW:
            return self.demo_tripod.play_row("hardware high-step demo")
        return _SCRIPTED_TRIPOD.get(p)

    def _scripted_se2_kw(self, p: Path) -> dict[str, Any] | None:
        if p == _SE2_TETRAPOD:
            return {"gait": "tetrapod"}
        if p == _SE2_WAVE:
            return {"gait": "wave"}
        if p == _SE2_CPG and self._cpg_loaded is not None:
            return {
                "gait": self._cpg_loaded["gait"],
                **self._cpg_loaded["gait_kw"],
            }
        return None

    def _new_gait(self):
        # Gaits use robot-absolute joints. q_plant is private MuJoCo state,
        # so its femur-relative hinge crosses the boundary explicitly here.
        plant_deg = mujoco_rel_rad_to_robot_abs_deg(self.q_plant)
        kw = self._scripted_tripod_kw(self.walk_list[self.wi])
        if kw is not None:
            g = self.TripodGait(period=kw["period"],
                                lift=kw["lift_mm"] * 0.001,
                                ramp=kw.get("ramp", 0.4),
                                stride_scale=kw.get("stride_scale", 1.0))
            g.sync_plant_stance(plant_deg[1], plant_deg[2])
            g.set_lift_mm(kw["lift_mm"])
            g.reset_phase(t=0.0)
            return g
        se2_kw = self._scripted_se2_kw(self.walk_list[self.wi])
        if se2_kw is not None:
            se2_kw = dict(se2_kw)
            gait_name = str(se2_kw.pop("gait", "tetrapod"))
            g = self.SE2FootGait(gait=gait_name, **se2_kw)
            g.sync_plant_stance(plant_deg[1], plant_deg[2])
            return g
        if self.walk_list[self.wi] == _MIDDLE_TUCK_QUAD:
            g = self.MiddleTuckQuadGait.crawl()
            g.sync_plant_stance(plant_deg[1], plant_deg[2])
            return g
        g = make_noslip_gait(self.walk_list[self.wi], self.NoSlipGait)
        g.sync_plant_stance(plant_deg[1], plant_deg[2])
        return g

    def _blend_ticks(self) -> int:
        gap = max(self.z_plant - self._chassis_z(), 0.0)
        return int(round(min(max(gap / 0.020, 0.5), 4.0) / self.env.dt))

    def _stance_profile(self, kind: str) -> dict[str, float]:
        path = self._role_path(kind) or self._active_stance_path()
        if path is None:
            raise RuntimeError(
                f"{kind} needs a {JOINT_CONTRACT} stance policy")
        prof = self.profiles.get(path.stem, {})
        return {**_DEFAULT_STANCE_PROFILE[kind], **prof.get(kind, {})}

    def _apply_ramp(self, kind: str) -> dict[str, float]:
        prof = self._stance_profile(kind)
        self.traj.HEIGHT_RATE = abs(prof["target_m"]) / max(prof["ramp_s"], 0.1)
        self.traj.BELLY_HOLD_S = float(prof["hold_s"]) if kind == "stand" else 0.0
        return prof

    def _restore_phys(self, keep_q: np.ndarray, keep_v: np.ndarray) -> None:
        self.env.data.qpos[:] = keep_q
        self.env.data.qvel[:] = keep_v
        self.mujoco.mj_forward(self.env.model, self.env.data)
        self.env._profile.reset(self._q_now())
        self.env.safety.set_nominal(self._q_now_robot_abs())

    def _re_anchor_plant(self) -> None:
        keep_q = self.env.data.qpos.copy()
        keep_v = self.env.data.qvel.copy()
        self.traj.start_at = "plant"
        self.traj.goal = TaskGoal()
        self.traj.vx = self.traj.vy = 0.0
        self._clear_drive_dwell()
        self.traj.reset_published()
        self._reset_memories(hard=False)
        self.obs, _ = self.env.reset()
        self._restore_phys(keep_q, keep_v)

    def _re_anchor_belly(self) -> None:
        keep_q = self.env.data.qpos.copy()
        keep_v = self.env.data.qvel.copy()
        self.traj.start_at = "zero"
        self.traj.goal = TaskGoal()
        self.traj.vx = self.traj.vy = 0.0
        self._clear_drive_dwell()
        self.traj.reset_published()
        self._reset_memories(hard=False)
        self.obs, _ = self.env.reset()
        self._restore_phys(keep_q, keep_v)

    def _role_path(self, role: str) -> Path | None:
        entry = self.role_models.get(role)
        if isinstance(entry, tuple):
            return entry[1]
        return None

    def _role_model(self, role: str):
        entry = self.role_models.get(role)
        if isinstance(entry, tuple):
            return entry[0], entry[2]
        if role == "hold" and entry == "walk":
            return self.walk, self.n_walk
        return self.stance, self.n_stance

    def _stance_action(self, role: str) -> np.ndarray:
        model, n = self._role_model(role)
        if model is None:
            return q_rad_to_action(self._q_now_robot_abs())
        a, _ = model.predict(self.obs[:n], deterministic=True)
        return a

    def _do_stand(self) -> None:
        self.pose_hold_q = None
        if self._role_model("stand")[0] is None:
            self.msg = (
                f"stand unavailable: select a {JOINT_CONTRACT} stance policy")
            return
        if self.auto is not None:
            if self.auto[0] == "lower":
                self.auto = None
            elif self.auto[0] == "recover":
                self.msg = "recovering - wait for the stand"
                return
            else:
                self.msg = "rise already running"
                return
        self.sitting = False
        prof = self._apply_ramp("stand")
        if (not self.downed and self.traj.start_at == "plant"
                and self._chassis_z() > 0.09):
            self.traj.goal.height_ref = 0.0
            self.msg = "rising back up (in place)"
            return
        keep_q = self.env.data.qpos.copy()
        keep_v = self.env.data.qvel.copy()
        self.downed = False
        self.gait = None
        self.om_cmd = 0.0
        self.traj.start_at = "zero"
        self.traj.goal = TaskGoal()
        self.traj.goal.height_ref = float(prof["target_m"])
        self.traj.vx = self.traj.vy = 0.0
        self._clear_drive_dwell()
        self.traj.mode = "rise"
        self.traj.reset_published()
        self._reset_memories(hard=False)
        self.obs, _ = self.env.reset()
        self._restore_phys(keep_q, keep_v)
        ramp_done_s = float(prof["hold_s"]) + float(prof["ramp_s"])
        release_after_s = ramp_done_s + self.STAND_HANDOFF_SETTLE_S
        fallback_s = ramp_done_s + 1.5
        stable_ticks = max(1, int(round(
            self.STAND_HANDOFF_STABLE_S / self.env.dt)))
        self.auto = ["rise", 0, fallback_s, 0, release_after_s, stable_ticks]
        self.msg = "RISE (in place)"

    def _do_sit(self) -> None:
        self.pose_hold_q = None
        if self.downed:
            self.msg = "robot is down - reset or recover first"
            return
        if self.sitting:
            self.msg = "already lowered"
            return
        if self.auto is not None and self.auto[0] in ("blend", "fold", "fell"):
            self.msg = "scripted transition in progress"
            return
        self.auto = None
        self.traj.vx = self.traj.vy = 0.0
        self.om_cmd = 0.0
        self._clear_drive_dwell()
        if self.traj.start_at in ("zero", "belly"):
            self.auto = ["fold", 0, int(6.0 / self.env.dt), self._chassis_z()]
            self.msg = "LOWER: settling to the ground"
            return
        if self._role_model("lower")[0] is None:
            self.msg = (
                f"lower unavailable: select a {JOINT_CONTRACT} stance policy")
            return
        prof = self._apply_ramp("lower")
        self.traj.goal.height_ref = float(prof["target_m"])
        total = float(prof["hold_s"]) + float(prof["ramp_s"]) + 1.5
        self.auto = ["lower", 0, total]
        self.msg = "LOWER: crouch, then settle"

    def _upright(self) -> bool:
        roll, pitch = self._roll_pitch_deg()
        return (self._chassis_z() > 0.10 and abs(roll) < 17.0
                and abs(pitch) < 17.0)

    def _stand_handoff_ready(self) -> tuple[bool, dict[str, float | None]]:
        roll, pitch = self._roll_pitch_deg()
        z_m = self._chassis_z()
        min_z = max(0.095, float(getattr(self, "z_plant", 0.11)) - 0.03)
        state = getattr(self.env, "_state", None)
        cur_arr = getattr(state, "servo_current", None)
        cur = (float(np.max(np.abs(cur_arr)))
               if cur_arr is not None and len(cur_arr) else None)
        tilt = max(abs(float(roll)), abs(float(pitch)))
        ok = (z_m >= min_z
              and tilt <= self.STAND_HANDOFF_MAX_TILT_DEG
              and (cur is None or cur <= self.STAND_HANDOFF_MAX_CURRENT_A))
        return ok, {
            "z_m": z_m,
            "min_z_m": min_z,
            "tilt_deg": tilt,
            "max_current_a": cur,
        }

    def _direct_profile_step_locked(self, q_rad: np.ndarray) -> None:
        """Issue one canonical robot-absolute target at the MuJoCo boundary."""
        self.env._profile.command_robot_abs(
            q_rad,
            speed_deg_s=self.demo_write_speed_deg_s,
            acc_units=self.demo_write_acc_units)
        self.env._cmd = np.asarray(q_rad, dtype=float).copy()
        self.env._advance()
        self.env._state = self.env._read_state()
        self.env._step_i += 1
        goal = self.env._current_goal()
        self.obs = self.env._final_obs(
            build_obs(self.env.cfg, self.env._state, self.env._q_nom,
                      self.env._prev_action, goal=goal,
                      tilt_ref=self.env._tilt_ref0),
            reset=False)

    def _demo_end_live_locked(self) -> dict[str, Any]:
        roll, pitch = self._roll_pitch_deg()
        out: dict[str, Any] = {
            "height_mm": round(self._chassis_z() * 1000.0, 1),
            "roll_deg": roll,
            "pitch_deg": pitch,
        }
        if self.demo_last_target_deg is not None:
            actual = mujoco_rel_rad_to_robot_abs_deg(self._q_now())
            out["max_lag_deg"] = round(max(
                abs(a - b) for a, b in zip(actual, self.demo_last_target_deg)
            ), 2)
        return out

    def _finish_demo_locked(self) -> None:
        name = self.demo_name or "demo"
        end_home = self.demo_end_home
        self.demo_pose_fn = None
        self._set_demo_safety(False)
        live = self._demo_end_live_locked()
        max_lag = live.get("max_lag_deg")
        ok = True
        if self.demo_is_script or end_home == "sit":
            ok = (
                self._chassis_z() < 0.09
                and (max_lag is None or float(max_lag) <= 12.0))
            self.sitting = bool(ok)
            self.downed = not ok
            self.quad_reared = False
            self.q_sit = self._q_now()
            self.pose_hold_q = self.q_sit.copy()
            self.msg = (f"{name} done - sitting" if ok
                        else f"{name} did not reach sit cleanly")
        elif end_home == "stand":
            ok = self._upright()
            if ok:
                self.sitting = False
                self.downed = False
                self.quad_reared = False
                self.q_plant = self._q_now()
                self.z_plant = self._chassis_z()
                self.pose_hold_q = self.q_plant.copy()
                self.traj.start_at = "plant"
                self.msg = f"{name} done - standing"
            else:
                self.sitting = False
                self.downed = True
                self.pose_hold_q = self._q_now().copy()
                self.traj.start_at = "zero"
                self.msg = (
                    f"{name} command ended low/tilted - did not stand")
        else:
            self.sitting = False
            self.downed = False
            self.quad_reared = name in QUAD_REARED_END_DEMOS
            self.pose_hold_q = self._q_now().copy()
            self.msg = f"{name} done - holding"
        self.demo_status = "done" if ok else "failed"
        self.demo_end_home = ""
        self.demo_direct_profile = False
        self.demo_write_speed_deg_s = None
        self.demo_write_acc_units = None
        self.demo_telemetry = {
            "ok": ok,
            "ended": end_home or "hold",
            **live,
            "sim_t_s": round(self.sim_t - self.demo_started_sim_t, 2),
            "demo_time_s": round(self.demo_t, 2),
            "log_name": self._log_name or None,
            "log": str(self.log_dir / self._log_name)
            if self._log_name else None,
        }
        self.demo_last_target_deg = None
        self._close_log()

    def _do_fall(self) -> None:
        roll = 0.4
        pitch = 0.3
        cr, sr = math.cos(roll / 2), math.sin(roll / 2)
        cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
        self.traj.vx = self.traj.vy = 0.0
        self._clear_drive_dwell()
        self.env.data.qpos[2] = 0.20
        self.env.data.qpos[3:7] = [cr * cp, sr * cp, cr * sp, sr * sp]
        lo, hi = self.env.model.jnt_range[1:, 0], self.env.model.jnt_range[1:, 1]
        self.env.data.qpos[7:25] = np.random.uniform(lo, hi)
        self.env.data.qvel[:] = 0.0
        self.mujoco.mj_forward(self.env.model, self.env.data)
        self._reset_memories(hard=True)
        self.sitting = False
        self.downed = False
        self.auto = ["fell", 0, int(4.0 / self.env.dt), self._chassis_z()]
        self.msg = "FALLING into sprawled pose"

    def _do_recover(self) -> None:
        self.pose_hold_q = None
        if self.recover is None:
            self.msg = f"no recovery checkpoint ({self.cfg.recover.name})"
            return
        if self.auto is not None and self.auto[0] == "fell":
            self.msg = "still tumbling - recover after it lands"
            return
        self.traj.vx = self.traj.vy = 0.0
        self.om_cmd = 0.0
        self._re_anchor_belly()
        self.downed = False
        self.sitting = False
        self.upright_ticks = 0
        self.env.cfg.setdefault("goal", {})["walk_obs_body_vel"] = 1.0
        self.auto = ["recover", 0, int(20.0 / self.env.dt)]
        self.msg = "RECOVER: policy getting up"

    def _engage_walk(self) -> bool:
        if self.auto is not None:
            self.msg = "auto transition in progress"
            return False
        if self.downed:
            self.msg = "robot is down - reset or recover first"
            return False
        if self.sitting:
            self.msg = "lowered - stand first"
            return False
        if self._chassis_z() < 0.09:
            self.msg = "too low to walk - stand first"
            return False
        self.traj.goal.roll_ref = self.traj.goal.pitch_ref = 0.0
        self.traj.goal.height_ref = 0.0
        self.traj._pub.roll_ref = self.traj._pub.pitch_ref = 0.0
        self.traj._pub.height_ref = 0.0
        self.pose_hold_q = None
        if self.walk is not None:
            self._apply_vel_contract(self.walk_list[self.wi].stem)
        return True

    def _drive_band(self) -> tuple[float, float]:
        kw = self._scripted_tripod_kw(self.walk_list[self.wi])
        if kw is not None:
            return kw["cruise"], kw["cruise"]
        if self.walk_list[self.wi] in _SCRIPTED_SE2:
            return 0.03, 0.04
        if self.walk_list[self.wi] == _MIDDLE_TUCK_QUAD:
            return 0.015, 0.030
        if self.walk_list[self.wi] in {
                _NOSLIP, _NOSLIP_CLEAN, _NOSLIP_RIPPLE, _NOSLIP_WAVE,
                _NOSLIP_FLUID, _NOSLIP_FLUID_FAST, _NOSLIP_FLUID_HYBRID,
                _NOSLIP_FLUID_PUSH, _NOSLIP_FLUID_PULSE}:
            return 0.02, 0.04
        reg = None if self.walk is None else self._ckpt_regime(self.walk_list[self.wi].stem)
        if reg is not None:
            return reg["cruise"], reg["vmax"]
        return _CRUISE, _SPEED_MAX

    def _apply_servo_regime(self) -> None:
        prof = self.env._profile
        if prof is None:
            return
        if not self._regime_base:
            self._regime_base["vel"] = prof._vel_default.copy()
            self._regime_base["speed"] = self.env.write_speed_deg_s
            self._regime_base["acc"] = self.env.write_acc_units
            self._regime_base["dq"] = self.env.safety.max_dq
        scripted_live = self.walk_list[self.wi] in _SCRIPTED_ROWS
        reg = None if scripted_live or self.walk is None else self._ckpt_regime(
            self.walk_list[self.wi].stem)
        if scripted_live:
            s = (SCRIPTED_WALK_SPEED_COUNTS_S
                 / max(self.servo_fit_counts, 1.0))
            prof._vel_default[:] = self._regime_base["vel"] * s
            self.env.write_speed_deg_s = (
                SCRIPTED_WALK_SPEED_COUNTS_S * 360.0 / 4096.0)
            self.env.write_acc_units = SCRIPTED_WALK_ACC_UNITS
            self.env.safety.max_dq = self._regime_base["dq"]
        elif reg is not None:
            s = reg["speed"] / max(self.servo_fit_counts, 1.0)
            prof._vel_default[:] = self._regime_base["vel"] * s
            self.env.write_speed_deg_s = reg["speed"] * 360.0 / 4096.0
            self.env.write_acc_units = reg["acc"]
            self.env.safety.max_dq = math.radians(reg["clamp_deg"])
        else:
            prof._vel_default[:] = self._regime_base["vel"]
            self.env.write_speed_deg_s = self._regime_base["speed"]
            self.env.write_acc_units = self._regime_base["acc"]
            self.env.safety.max_dq = self._regime_base["dq"]

    def _tick_locked(self) -> None:
        self._apply_servo_regime()
        now = time.monotonic()
        if self.drive_active and now - self.last_drive_cmd_at > _DRIVE_HEARTBEAT_STALE_S:
            if not self._drive_neutral_dwell_locked(now):
                self.traj.vx = self.traj.vy = 0.0
                self._set_drive_wz(0.0)
        if self.timed_walk_until is not None and self.sim_t >= self.timed_walk_until:
            self.traj.vx = self.traj.vy = 0.0
            self._clear_drive_dwell()
            self.timed_walk_until = None
            self._finish_job("timed walk complete")

        demo_running = self._demo_running()
        cmd_speed = float(np.hypot(self.traj.vx, self.traj.vy))
        scripted = self.walk is None
        walking = ((cmd_speed > 1e-3 or (scripted and abs(self.om_cmd) > 1e-3))
                   and self.auto is None and not self.downed and not self.sitting
                   and not demo_running)
        if not walking:
            self.gait = None
            self.hist = None
        self.mode = ("demo" if demo_running
                     else "rise" if self.auto is not None and self.auto[0] in
                     ("rise", "blend", "recover")
                     else "lower" if self.auto is not None and self.auto[0] in
                     ("lower", "fold", "fell")
                     else "walk" if walking else "hold")
        self.traj.mode = "hold" if self.mode == "demo" else self.mode
        if self.mode == "walk":
            self._drive_remember_refs()
        elif not self._drive_cmd_moving(self.traj.vx, self.traj.vy,
                                        self.om_cmd):
            self.drive_zero_since = None

        action = None
        if self.push_ticks > 0:
            self.env.data.xfrc_applied[self.chassis_bid, :3] = self.push_force
            self.push_ticks -= 1
        else:
            self.env.data.xfrc_applied[self.chassis_bid, :3] = 0.0

        if self.downed:
            action = q_rad_to_action(self._q_now_robot_abs())
        elif self.auto is not None and self.auto[0] == "rise":
            action = self._stance_action("stand")
            self.auto[1] += 1
            t_s = self.auto[1] * self.env.dt
            ready, details = self._stand_handoff_ready()
            if len(self.auto) >= 6 and t_s >= self.auto[4] and ready:
                self.auto[3] += 1
            elif len(self.auto) >= 6:
                self.auto[3] = 0
            stable_done = len(self.auto) >= 6 and self.auto[3] >= self.auto[5]
            if stable_done or t_s >= self.auto[2]:
                if self._chassis_z() > 0.06:
                    self.q_blend_from = self._q_now()
                    self.auto = ["blend", 0, self._blend_ticks()]
                    if stable_done:
                        self.msg = (
                            "stand stable - aligning to walk stance "
                            f"(z={details['z_m']:.3f}m)")
                    else:
                        self.msg = "aligning to walk stance"
                else:
                    self.auto = None
                    self._finish_job("rise failed", ok=False)
        elif self.auto is not None and self.auto[0] == "blend":
            self.auto[1] += 1
            s = min(self.auto[1] / max(self.auto[2], 1), 1.0)
            q_model = ((1.0 - s) * self.q_blend_from + s * self.q_plant)
            action = q_rad_to_action(
                self.env._mujoco_to_logical_q(q_model))
            if self.auto[1] >= self.auto[2]:
                self._re_anchor_plant()
                self.auto = None
                self._finish_job("up at walk stance")
        elif self.auto is not None and self.auto[0] == "lower":
            action = self._stance_action("lower")
            self.auto[1] += 1
            if self.auto[1] * self.env.dt >= self.auto[2]:
                self.auto = ["fold", 0, int(6.0 / self.env.dt),
                             self._chassis_z()]
                self.msg = "settling to ground"
        elif self.auto is not None and self.auto[0] == "fold":
            self.env._advance(limp=True)
            self.auto[1] += 1
            z = self._chassis_z()
            settled = self.auto[1] * self.env.dt > 1.0 and abs(z - self.auto[3]) < 2e-5
            self.auto[3] = z
            if settled or self.auto[1] >= self.auto[2]:
                self._re_anchor_belly()
                self.auto = None
                self.sitting = True
                self.q_sit = self._q_now()
                self._finish_job("lowered, parked on ground")
        elif self.auto is not None and self.auto[0] == "fell":
            self.env._advance(limp=True)
            self.auto[1] += 1
            z = self._chassis_z()
            settled = self.auto[1] * self.env.dt > 1.0 and abs(z - self.auto[3]) < 2e-5
            self.auto[3] = z
            if settled or self.auto[1] >= self.auto[2]:
                self._re_anchor_belly()
                self.auto = None
                self.downed = True
                self.msg = "FALLEN - recover or reset"
        elif self.auto is not None and self.auto[0] == "recover":
            action, _ = self.recover.predict(self.obs[:72], deterministic=True)
            self.auto[1] += 1
            self.upright_ticks = self.upright_ticks + 1 if self._upright() else 0
            if self.upright_ticks >= int(1.0 / self.env.dt):
                self._re_anchor_plant()
                self.auto = None
                self._finish_job("recovered - standing")
            elif self.auto[1] >= self.auto[2]:
                self.auto = None
                self._finish_job("recovery timed out", ok=False)
        elif demo_running:
            pose_deg = self.demo_pose_fn(self.demo_t)
            self.demo_last_target_deg = [float(v) for v in pose_deg]
            pose_rad = np.radians(pose_deg)
            if self.demo_direct_profile:
                self._direct_profile_step_locked(pose_rad)
            else:
                action = q_rad_to_action(pose_rad)
            self.demo_t += self.env.dt * self._demo_speed_eff_locked()
            while self.demo_notes and self.demo_notes[0][0] <= self.demo_t:
                self.demo_note = self.demo_notes.pop(0)[1]
            self.demo_status = (
                f"{self.demo_note} · x{self.demo_speed_live:.2f}"
                if self.demo_note
                else f"running @ {self.demo_speed_live:.2f}x")
            if self.demo_t >= self.demo_duration:
                self._finish_demo_locked()
        elif self.sitting:
            action = q_rad_to_action(
                self.env._mujoco_to_logical_q(self.q_sit))
        elif self.pose_hold_q is not None:
            action = q_rad_to_action(
                self.env._mujoco_to_logical_q(self.pose_hold_q))
        elif walking and scripted:
            if self.gait is None:
                self.gait = self._new_gait()
                self.gait_t = 0.0
            self.gait.set_velocity(vx=self.traj.vx, vy=self.traj.vy,
                                   omega=self.om_cmd)
            # Gait output is robot-absolute; actions here drive MuJoCo.
            q_robot = np.radians(self.gait.desired_deg(self.gait_t))
            action = q_rad_to_action(q_robot)
            self.gait_t += self.env.dt
        elif walking:
            action = self._walk_predict()
        else:
            action = self._stance_action("hold")

        if action is not None:
            self.obs, _r, term, trunc, info = self.env.step(action)
            if term or trunc:
                if self._demo_running():
                    self._stop_demo_locked(
                        status=(info.get("termination_reason")
                                or "episode end") + "; DOWN")
                self.downed = True
                self.auto = None
                self.drive_active = False
                self.timed_walk_until = None
                self.traj.vx = self.traj.vy = 0.0
                self._clear_drive_dwell()
                reason = info.get("termination_reason") or "episode end"
                self._finish_job(f"{reason}; DOWN", ok=False)
        self.sim_t += self.env.dt
        self._write_log_row()

    def _run(self) -> None:
        while not self.stop_event.is_set():
            t0 = time.monotonic()
            with self.lock:
                self._tick_locked()
                now = time.monotonic()
                if (self.cfg.web_frames
                        and now - self._last_frame_at >= self._frame_interval_s):
                    self._last_frame_at = now
                    self._render_frame_locked()
            if self.cfg.realtime > 0:
                delay = self.env.dt / self.cfg.realtime - (time.monotonic() - t0)
                if delay > 0:
                    self.stop_event.wait(delay)

    def run_native_viewer(self, web_url: str = "") -> None:
        """Run physics and a native MuJoCo viewer on this process thread.

        Closing the window only detaches the viewer: the sim keeps
        stepping headless and the web server stays up (operator 08-22 —
        the old close-to-stop coupling kept killing the web UI by
        accident). Ctrl-C in the terminal stops the whole server.
        """
        import mujoco
        import mujoco.viewer

        print("MuJoCo viewer: closing the window detaches the viewer; "
              "the sim + web server keep running (Ctrl-C stops them)",
              flush=True)
        with mujoco.viewer.launch_passive(self.env.model,
                                          self.env.data) as viewer:
            while viewer.is_running() and not self.stop_event.is_set():
                t0 = time.monotonic()
                with self.lock:
                    self._tick_locked()
                    self._update_viewer_hud_locked(viewer, mujoco, web_url)
                    now = time.monotonic()
                    if (self.cfg.web_frames
                            and now - self._last_frame_at >= self._frame_interval_s):
                        self._last_frame_at = now
                        self._render_frame_locked()
                    viewer.sync()
                if self.cfg.realtime > 0:
                    delay = (self.env.dt / self.cfg.realtime
                             - (time.monotonic() - t0))
                    if delay > 0:
                        self.stop_event.wait(delay)
        if self.stop_event.is_set():
            return
        print("MuJoCo viewer closed — sim continues headless; web UI "
              f"still at {web_url or 'the same URL'}", flush=True)
        self._run()

    def _update_viewer_hud_locked(self, viewer: Any, mujoco_mod: Any,
                                  web_url: str) -> None:
        set_texts = getattr(viewer, "set_texts", None)
        if set_texts is None:
            return
        live = self._live()
        width = 54

        def cell(text: str) -> str:
            text = str(text)
            if len(text) > width:
                text = text[:width - 3] + "..."
            return text.ljust(width)

        commands = [
            f"{t:7.1f}s  {cmd}" for t, cmd, _key in self.command_log[-4:]
        ]
        while len(commands) < 4:
            commands.append("")

        labels = [
            "Hexapod sim",
            "status",
            "mode",
            "cmd ref",
            "body vel",
            "tilt",
            "url",
            "last cmd",
            "commands",
            "",
            "",
            "",
        ]
        values = [
            "MuJoCo web control",
            live["status"],
            f"{live['mode']}  h {live['height_mm']:>6.1f} mm",
            f"{live['vx_ref']:+.3f},{live['vy_ref']:+.3f} m/s",
            f"{live['vx_body']:+.3f},{live['vy_body']:+.3f} m/s",
            f"{live['roll_deg']:+.1f},{live['pitch_deg']:+.1f} deg",
            web_url or "",
            self.last_command,
            *commands,
        ]
        title = "\n".join(label.ljust(12) for label in labels)
        detail = "\n".join(cell(value) for value in values)
        set_texts([(mujoco_mod.mjtFontScale.mjFONTSCALE_100,
                    mujoco_mod.mjtGridPos.mjGRID_TOPLEFT,
                    title, detail)])

    def _render_frame_locked(self) -> None:
        try:
            if self.cv2 is None:
                raise RuntimeError("browser frames disabled")
            frame = self.env.render()
            if frame is None:
                raise RuntimeError("browser frames disabled")
            img = self.cv2.cvtColor(frame, self.cv2.COLOR_RGB2BGR)
            ok, data = self.cv2.imencode(
                ".jpg", img, [int(self.cv2.IMWRITE_JPEG_QUALITY), 86])
            if not ok:
                raise RuntimeError("could not encode sim frame")
            self._frame_jpeg = data.tobytes()
            self._frame_error = ""
        except Exception as e:
            self._frame_error = str(e)
        finally:
            self._frame_ready.set()

    def _finish_job(self, ended: str, ok: bool = True) -> None:
        self.msg = ended
        if self.job_kind:
            self.job_result = {
                "ok": ok,
                "ended": ended,
                "mode": self.job_kind,
                "sim_t_s": round(self.sim_t, 2),
                "log": self._log_name or None,
            }
            self.job_kind = None
            self._close_log()
        elif ended:
            self.job_result = {"ok": ok, "ended": ended,
                               "sim_t_s": round(self.sim_t, 2)}

    def _open_log(self, kind: str) -> None:
        self._close_log()
        stamp = time.strftime("%Y%m%d_%H%M%S")
        self._log_name = f"sim_{kind}_{stamp}.csv"
        self._log_fp = (self.log_dir / self._log_name).open("w", newline="")
        self._log_writer = csv.DictWriter(self._log_fp, fieldnames=[
            "t_s", "mode", "height_mm", "height_ref_mm", "roll_deg",
            "pitch_deg", "vx_ref_mps", "vy_ref_mps", "wz_ref_rad_s",
            "vx_body_mps", "vy_body_mps", "stance", "walk", "msg",
        ])
        self._log_writer.writeheader()
        self._last_log_row_t = -1.0

    def _write_log_row(self) -> None:
        if self._log_writer is None or self.sim_t - self._last_log_row_t < 0.04:
            return
        roll, pitch = self._roll_pitch_deg()
        vx, vy = self._body_vel()
        self._log_writer.writerow({
            "t_s": round(self.sim_t, 3),
            "mode": self.mode,
            "height_mm": round(self._chassis_z() * 1000.0, 1),
            "height_ref_mm": round(self._published_height_ref()
                                   * 1000.0, 1),
            "roll_deg": roll,
            "pitch_deg": pitch,
            "vx_ref_mps": round(float(self.traj.vx), 4),
            "vy_ref_mps": round(float(self.traj.vy), 4),
            "wz_ref_rad_s": round(float(getattr(self, "om_cmd", 0.0)), 4),
            "vx_body_mps": round(vx, 4),
            "vy_body_mps": round(vy, 4),
            "stance": self._active_stance_name(),
            "walk": self._active_walk_name(),
            "msg": self.msg,
        })
        self._last_log_row_t = self.sim_t

    def _close_log(self) -> None:
        if self._log_fp is not None:
            self._log_fp.close()
        self._log_fp = None
        self._log_writer = None

    def _active_stance_name(self) -> str:
        path = self._active_stance_path()
        return path.name if path is not None else "unassigned"

    def _active_stance_path(self) -> Path | None:
        if self.si < 0 or self.si >= len(self.stance_list):
            return None
        return self.stance_list[self.si]

    def _active_walk_name(self) -> str:
        p = self.walk_list[self.wi]
        return f"scripted:{p.name}" if p in _SCRIPTED_ROWS else p.name

    def _live(self) -> dict[str, Any]:
        roll, pitch = self._roll_pitch_deg()
        vx, vy = self._body_vel()
        chassis_xyz = [
            round(float(value), 6)
            for value in self.env.data.xpos[self.chassis_bid]
        ]
        joint_deg = [
            round(float(value), 4)
            for value in mujoco_rel_rad_to_robot_abs_deg(self._q_now())
        ]
        feet_xyz: list[list[float] | None] = []
        for leg in range(6):
            try:
                site_id = self.env.model.site(f"L{leg}_foot_site").id
                feet_xyz.append([
                    round(float(value), 6)
                    for value in self.env.data.site_xpos[site_id]
                ])
            except (KeyError, ValueError):
                feet_xyz.append(None)
        return {
            "joint_frame": FRAME_ROBOT_ABS,
            "joint_contract": JOINT_CONTRACT,
            "model": self._active_walk_name(),
            "stance": self._active_stance_name(),
            "mode": self.mode,
            "status": self.msg,
            "vx_ref": round(float(self.traj.vx), 4),
            "vy_ref": round(float(self.traj.vy), 4),
            "wz_ref": round(float(getattr(self, "om_cmd", 0.0)), 4),
            "vx_body": round(vx, 4),
            "vy_body": round(vy, 4),
            "roll_deg": roll,
            "pitch_deg": pitch,
            "height_mm": round(self._chassis_z() * 1000.0, 1),
            "height_ref_mm": round(self._published_height_ref()
                                   * 1000.0, 1),
            "height_live": True,
            "walk_zero_dwell_s": round(self._drive_zero_dwell_remaining(), 2),
            "t_s": round(self.sim_t, 1),
            "chassis_xyz_m": chassis_xyz,
            "joint_deg": joint_deg,
            "foot_xyz_m": feet_xyz,
        }

    # Public API methods used by web_server.py -------------------------

    def demo_state(self) -> dict[str, Any]:
        with self.lock:
            return {
                "name": self.demo_name,
                "status": self.demo_status,
                "running": self._demo_running(),
                "speed_live": self.demo_speed_live,
                "params": dict(self.demo_params),
                "progress": {"msg": self.demo_status, "live": self._live()}
                if self._demo_running() else None,
                "telemetry": dict(self.demo_telemetry)
                if self.demo_telemetry else None,
                "bus_hot": False,
            }

    def list_demos(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        actions = (
            ("rear", "REAR UP", "tip back on 4 legs and hold"),
            ("hold", "HOLD", "settle to reared hold"),
            ("walk", "WALK FORWARD", "animal walk while reared"),
            ("walk_back", "WALK BACKWARD", "reverse animal walk while reared"),
            ("trot", "TROT FORWARD", "diagonal pairs while reared"),
            ("trot_back", "TROT BACKWARD", "reverse diagonal pairs while reared"),
            ("down", "COME DOWN", "untuck fronts and return to stand"),
        )
        for suffix, (_rear_gait, _walk_gait, _trot_gait, label) in (
                QUAD_VARIANTS.items()):
            tag = "" if not suffix else f" {label.upper()}"
            for action, title, desc in actions:
                out.append({
                    "name": _quad_name(action, suffix),
                    "title": f"[8 quad] {title}{tag} - {desc}",
                    "air": False,
                    "group": "quad",
                    "live_speed": True,
                    "has_size": False,
                })
        for meta in self.list_dance_scripts():
            out.append({
                "name": meta["name"],
                "title": meta.get("title") or meta["name"],
                "air": True,            # scripts start AND end at sit zero
                "group": "uploaded",
                "live_speed": True,
                "has_size": False,
                "uploaded": True,
                "stands": bool(meta.get("stands")),
                "seconds": meta.get("seconds"),
            })
        return out

    def standup_modes(self) -> dict[str, Any]:
        path = self._proto_root / "linux_control" / "standup_modes.json"
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError) as e:
            return {"ok": False, "error": f"standup_modes.json: {e}"}
        return {
            "ok": True,
            "frame": data.get("frame", ""),
            "modes": [
                {"name": name,
                 "description": m.get("description", ""),
                 "keyframes": len(m.get("keyframes", [])),
                 "total_s": m.get("total_s")}
                for name, m in (data.get("modes") or {}).items()],
        }

    def pose(self) -> dict[str, Any]:
        with self.lock:
            deg = [round(float(v), 2)
                   for v in mujoco_rel_rad_to_robot_abs_deg(self._q_now())]
            return {"ok": True, "sim": True, "degrees": deg, "live": 18,
                    "armed": self.armed, "mode": self.mode,
                    "ts": time.time()}

    def _standup_frames(self, mode: str,
                        direction: str) -> list[tuple[list[float], float]]:
        data = json.loads(
            (self._proto_root / "linux_control" / "standup_modes.json")
            .read_text())
        mode = (mode or "tuck").strip()
        if mode == "plant":
            kfs = data["modes"]["tuck"]["keyframes"]
            plant = mujoco_rel_rad_to_robot_abs_deg(self.q_plant)
            keyframes = list(kfs[:-1]) + [{"q_deg": plant, "s": 0.5}]
        else:
            keyframes = data["modes"][mode]["keyframes"]
        frames = [([float(v) for v in kf["q_deg"]], float(kf["s"]))
                  for kf in keyframes]
        if (direction or "up").strip().lower() in {"down", "lower", "sit"}:
            qs = [q for q, _ in frames]
            ss = [s for _, s in frames]
            frames = [(qs[-1], 0.8)] + [
                (qs[i], ss[i + 1]) for i in range(len(qs) - 2, -1, -1)]
        return frames

    @staticmethod
    def _pose_fn_from_frames(
            start_deg: list[float],
            frames: list[tuple[list[float], float]]):
        import bisect
        segs: list[tuple[float, float, Any]] = []
        bounds: list[float] = []
        t = 0.0
        cur = [float(v) for v in start_deg]
        for target, seconds in frames:
            a = list(cur)
            b = [float(v) for v in target]
            dur = max(0.05, float(seconds))

            def fn(u: float, a=a, b=b) -> list[float]:
                w = 0.5 - 0.5 * math.cos(math.pi * u)
                return [x + (y - x) * w for x, y in zip(a, b)]

            segs.append((t, t + dur, fn))
            t += dur
            bounds.append(t)
            cur = b

        def pose_at(tt: float) -> list[float]:
            if not segs:
                return list(start_deg)
            i = min(bisect.bisect_right(bounds, max(0.0, tt)),
                    len(segs) - 1)
            t0, t1, fn = segs[i]
            u = (max(0.0, tt) - t0) / max(1e-9, t1 - t0)
            return fn(min(1.0, max(0.0, u)))

        return pose_at, t

    def sim_standup(self, *, mode: str = "tuck", speed: float = 1.0,
                    direction: str = "up") -> dict[str, Any]:
        with self.lock:
            try:
                frames = self._standup_frames(mode, direction)
            except (OSError, ValueError, KeyError) as e:
                return {"ok": False,
                        "error": f"unknown stand-up mode: {e}"}
            speed = self._clamp_float(speed, 1.0, 0.25, 10.0)
            direction = (direction or "up").strip().lower()
            down = direction in {"down", "lower", "sit"}
            home = "sit" if down else "stand"
            name = f"standup_{mode}" + ("_down" if down else "")
            switched_from = self.demo_name if self._demo_running() else None
            self._record_command(
                f"/api/standup mode={mode} direction={direction} "
                f"speed={speed:.2f}")
            self._do_reset("plant" if down else "zero", 0.0,
                           f"{name}: command playback")
            start_deg = mujoco_rel_rad_to_robot_abs_deg(self._q_now())
            pose_fn, dur = self._pose_fn_from_frames(start_deg, frames)
            self._set_demo_safety(True)
            self.demo_pose_fn = pose_fn
            self.demo_t = 0.0
            self.demo_duration = dur
            self.demo_notes = []
            self.demo_note = ""
            self.demo_speed_cap = 10.0
            self.demo_is_script = False
            self.demo_end_home = home
            self.demo_direct_profile = True
            # compare_standup.py validated these stand-up paths with a
            # 90 deg/s bus profile; the ServoProfile still applies its
            # fitted per-axis velocity ceiling, latency, deadband, and
            # torque/friction limits.
            self.demo_write_speed_deg_s = 90.0
            self.demo_write_acc_units = self.env.write_acc_units
            self.demo_last_target_deg = None
            self.demo_started_sim_t = self.sim_t
            self.demo_name = name
            self.demo_status = f"running @ {speed:.2f}x"
            self.demo_speed_live = speed
            self.demo_telemetry = None
            self.demo_params = {"mode": mode, "speed": speed,
                                "direction": direction,
                                "home": home,
                                "seconds": round(dur / speed, 2)}
            if switched_from:
                self.demo_params["switched_from"] = switched_from
            self.drive_active = False
            self.timed_walk_until = None
            self.auto = None
            self.gait = None
            self.om_cmd = 0.0
            self._clear_drive_dwell()
            self.armed = True
            self.sitting = False
            self.pose_hold_q = None
            self.msg = f"{name} running"
            self._open_log(name)
            return {"ok": True, "params": dict(self.demo_params),
                    "home": home, "switched": bool(switched_from),
                    "switched_from": switched_from,
                    "demo": self.demo_state(),
                    "robot": self.robot_state()}

    # -- dance scripts (dances as data — same API shape as the robot) --------
    # Sources: the repo's baked library (dances/) is always available;
    # uploads via POST /api/dances land in ~/.hexapod_dances (upload wins
    # on a name clash, mirroring "robot-local state beats the repo").

    @property
    def _dance_upload_dir(self) -> Path:
        return Path.home() / ".hexapod_dances"

    def _dance_sources(self) -> list[Path]:
        return [self._dance_upload_dir, self._proto_root / "dances"]

    def _dance_file(self, name: str) -> Path | None:
        from hexapod_core import dance_script as DS
        if not isinstance(name, str) or not DS.NAME_RE.match(name):
            return None
        for d in self._dance_sources():
            p = d / f"{name}.json"
            if p.is_file():
                return p
        return None

    def list_dance_scripts(self) -> list[dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for d in reversed(self._dance_sources()):   # uploads override repo
            try:
                paths = sorted(d.glob("*.json"))
            except OSError:
                continue
            for p in paths:
                try:
                    s = json.loads(p.read_text())
                    out[s["name"]] = {
                        "name": s["name"],
                        "title": s.get("title") or s["name"],
                        "stands": bool(s.get("stands")),
                        "seconds": s.get("seconds"),
                        "acts": len(s.get("acts") or []),
                        "bytes": p.stat().st_size,
                        "baked_from": s.get("baked_from"),
                    }
                except (OSError, ValueError, KeyError):
                    continue
        return sorted(out.values(), key=lambda m: m["name"])

    def get_dance_script(self, name: str) -> dict[str, Any] | None:
        p = self._dance_file(name)
        if p is None:
            return None
        try:
            return json.loads(p.read_text())
        except (OSError, ValueError):
            return None

    def save_dance_script(self, script: Any) -> dict[str, Any]:
        from hexapod_core import dance_script as DS
        errs, stats = DS.validate_script(script)
        if errs:
            return {"ok": False, "error": "; ".join(errs[:5])}
        name = script["name"]
        if name in QUAD_STREAM_DEMOS:
            return {"ok": False, "error": f"{name!r} is a built-in demo name"}
        try:
            self._dance_upload_dir.mkdir(parents=True, exist_ok=True)
            p = self._dance_upload_dir / f"{name}.json"
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(script))
            tmp.replace(p)
        except OSError as e:
            return {"ok": False, "error": f"save failed: {e}"}
        return {"ok": True, "name": name, "stats": stats,
                "bytes": p.stat().st_size}

    def delete_dance_script(self, name: str) -> dict[str, Any]:
        p = self._dance_file(name)
        if p is None or p.parent != self._dance_upload_dir:
            return {"ok": False,
                    "error": f"no uploaded dance {name!r} (repo-baked "
                             f"scripts can't be deleted here)"}
        try:
            p.unlink()
        except OSError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "deleted": name}

    def _run_dance_script(self, name: str, script: dict[str, Any],
                          speed: float) -> dict[str, Any]:
        """Compile a dance script to a sim timeline and start it."""
        from hexapod_core import dance_script as DS
        try:
            kfs = DS.load_standup_keyframes(
                self._proto_root / "linux_control" / "standup_modes.json")
        except (OSError, ValueError):
            kfs = {}
        try:
            pose_fn, dur, notes, cap = DS.compile_script_timeline(
                script, standup_keyframes=kfs)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        switched_from = self.demo_name if self._demo_running() else None
        self._record_command(f"/api/demo name={name} speed={speed:.2f}")
        # Scripts start at sit zero (belly down, legs straight out).
        self._do_reset("zero", 0.0, f"sit zero -> {name}")
        self._set_demo_safety(True)
        self.demo_pose_fn = pose_fn
        self.demo_t = 0.0
        self.demo_duration = dur
        self.demo_notes = list(notes)
        self.demo_note = ""
        self.demo_speed_cap = cap
        self.demo_is_script = True
        self.demo_direct_profile = True
        self.demo_write_speed_deg_s = self.env.write_speed_deg_s
        self.demo_write_acc_units = self.env.write_acc_units
        self.demo_started_sim_t = self.sim_t
        self.demo_name = name
        self.demo_status = f"running @ {speed:.2f}x"
        self.demo_speed_live = speed
        self.demo_telemetry = None
        params: dict[str, Any] = {"speed": speed, "home": "sit",
                                  "seconds": round(dur, 1)}
        if switched_from:
            params["switched_from"] = switched_from
        self.demo_params = params
        self.drive_active = False
        self.timed_walk_until = None
        self.auto = None
        self.gait = None
        self.om_cmd = 0.0
        self._clear_drive_dwell()
        self.armed = True
        self.msg = f"{name} running"
        self._open_log(f"demo_{name}")
        return {
            "ok": True,
            "params": dict(params),
            "home": "sit",
            "switched": bool(switched_from),
            "switched_from": switched_from,
            "demo": self.demo_state(),
            "robot": self.robot_state(),
        }

    @staticmethod
    def _clamp_float(value: Any, default: float,
                     lo: float, hi: float) -> float:
        try:
            x = float(value)
        except (TypeError, ValueError):
            x = default
        return max(lo, min(hi, x))

    def set_demo_speed(self, speed: Any) -> dict[str, Any]:
        v = self._clamp_float(speed, 1.0, 0.25, 3.0)
        with self.lock:
            self._record_command(f"/api/demo/speed speed={v:.2f}",
                                 key="demo-speed")
            self.demo_speed_live = v
            if self.demo_params:
                self.demo_params = {**self.demo_params, "speed_live": v}
            if self._demo_running():
                self.demo_status = f"running @ {v:.2f}x"
            return {"ok": True, "speed": v,
                    "running": self._demo_running(),
                    "demo": self.demo_state()}

    def run_demo(self, name: str, *, speed: float = 1.0,
                 size: float = 1.0, rate: float | None = None,
                 torque: int | None = None, softness: float = 1.0,
                 seconds: float | None = None) -> dict[str, Any]:
        name = (name or "").strip()
        if name not in QUAD_STREAM_DEMOS:
            script = self.get_dance_script(name)
            if script is None:
                return {"ok": False,
                        "error": f"demo {name!r} is not simulated yet",
                        "demos": [d["name"] for d in self.list_demos()]}
            with self.lock:
                return self._run_dance_script(
                    name, script,
                    self._clamp_float(speed, 1.0, 0.25, 3.0))
        with self.lock:
            try:
                from hexapod_core import quad_walk as QW
            except Exception as e:
                return {"ok": False, "error": f"quad_walk missing: {e}"}

            speed = self._clamp_float(speed, 1.0, 0.25, 3.0)
            action = _quad_action(name)
            if name in QUAD_DOWN_DEMOS:
                dur = float(QW.EXIT_TOTAL_S)
            else:
                default_dur = 300.0 if name in QUAD_REQUIRES_REAR else 40.0
                dur = self._clamp_float(seconds, default_dur, 2.0, 300.0)
                if name in QUAD_REAR_DEMOS:
                    dur = max(dur, float(QW.ENTRY_TOTAL_S) + 0.5)
            switched_from = self.demo_name if self._demo_running() else None
            quad_current = self._demo_running() and self.demo_name in QUAD_STREAM_DEMOS
            if name in QUAD_REQUIRES_REAR and not (self.quad_reared or quad_current):
                return {
                    "ok": False,
                    "error": "quad: rear up first, then walk/trot/down",
                    "demo": self.demo_state(),
                    "robot": self.robot_state(),
                }
            self._record_command(
                f"/api/demo name={name} speed={speed:.2f} seconds={dur:.1f}")

            if name in QUAD_REAR_DEMOS:
                self._do_reset("plant", 0.0, f"stand zero -> {name}")
            else:
                if quad_current:
                    self._stop_demo_locked(status="aborted")
                self.pose_hold_q = None
                self.drive_active = False
                self.timed_walk_until = None
                self.traj.vx = self.traj.vy = 0.0
                self.auto = None
                self.gait = None
                self.om_cmd = 0.0
                self._clear_drive_dwell()
            self._set_demo_safety(True)
            base_deg = mujoco_rel_rad_to_robot_abs_deg(self.q_plant)
            gait = QUAD_DEMO_GAITS[name]
            phase = (
                "rear" if action == "rear"
                else "hold" if action == "hold"
                else "down" if action == "down"
                else "walk")
            direction = -1.0 if action in ("walk_back", "trot_back") else 1.0
            self.demo_pose_fn = QW.make_quad_walk_pose_fn(
                base_deg, dur, gait=gait, direction=direction, phase=phase)
            self.demo_t = 0.0
            self.demo_duration = dur
            self.demo_started_sim_t = self.sim_t
            self.demo_end_home = "stand" if name in QUAD_DOWN_DEMOS else ""
            self.demo_direct_profile = True
            self.demo_write_speed_deg_s = self.env.write_speed_deg_s
            self.demo_write_acc_units = 254.0
            self.demo_name = name
            self.demo_status = f"running @ {speed:.2f}x"
            self.demo_speed_live = speed
            self.demo_telemetry = None
            params: dict[str, Any] = {
                "speed": speed,
                "home": "stand" if name in QUAD_REAR_DEMOS else "quad",
                "seconds": dur,
            }
            if switched_from:
                params["switched_from"] = switched_from
            self.demo_params = params
            self.drive_active = False
            self.timed_walk_until = None
            self.auto = None
            self.gait = None
            self.om_cmd = 0.0
            self._clear_drive_dwell()
            self.armed = True
            self.msg = f"{name} running"
            self._open_log(f"demo_{name}")
            return {
                "ok": True,
                "params": dict(params),
                "home": params["home"],
                "switched": bool(switched_from),
                "switched_from": switched_from,
                "demo": self.demo_state(),
                "robot": self.robot_state(),
            }

    def stop_demo(self) -> dict[str, Any]:
        with self.lock:
            self._record_command("/api/demo/stop")
            was_running = self._demo_running()
            prev = self.demo_name or ""
            self._stop_demo_locked(status="aborted" if was_running else "idle")
            if was_running and prev in QUAD_STREAM_DEMOS:
                self.quad_reared = False
                self.pose_hold_q = self._q_now().copy()
            self.drive_active = False
            self.timed_walk_until = None
            self.traj.vx = self.traj.vy = 0.0
            self._clear_drive_dwell()
            self.mode = "hold"
            self.traj.mode = "hold"
            self.msg = "demo stopped - holding"
            return {"ok": True, "demo": self.demo_state(),
                    "robot": self.robot_state()}

    def go_zero(self, pose: str = "sit", *, force: bool = False) -> dict[str, Any]:
        pose = (pose or "sit").strip().lower()
        pose = "stand" if pose in {"stand", "standing", "plant"} else "sit"
        with self.lock:
            self._record_command(f"/api/zero pose={pose}")
            if pose == "stand":
                self._do_reset("plant", 0.0, "at stand zero")
                self.armed = True
            else:
                self._do_reset("zero", 0.0, "at sit zero")
                self.sitting = True
                self.q_sit = self._q_now()
                self.armed = True
            self.demo_name = f"{pose}_zero"
            self.demo_status = "done"
            self.demo_params = {"home": pose, "force": bool(force)}
            return {"ok": True, "pose": pose, "demo": self.demo_state(),
                    "robot": self.robot_state()}

    def safe_zero(self, *, dry_run: bool = False) -> dict[str, Any]:
        return self.go_zero("sit")

    def set_zero_here(self) -> dict[str, Any]:
        with self.lock:
            self._record_command("/api/set_zero")
            return {"ok": True, "sim": True, "ok_n": 18, "count": 18,
                    "message": "sim logical zero unchanged"}

    def ping(self) -> dict[str, Any]:
        return {"ok": True, "service": "hexapod-sim",
                "kind": "sim", "mode": self.mode,
                "viewer": self.cfg.viewer,
                "frames": self.cfg.web_frames}

    def status(self) -> dict[str, Any]:
        with self.lock:
            return {"ok": True, "sim": True, "motors": [],
                    "live": self._live()}

    def robot_state(self) -> dict[str, Any]:
        with self.lock:
            act = "armed" if self.armed else "limp"
            if self.drive_active:
                act = "driving"
            elif self._demo_running():
                act = "demo"
            elif self.auto is not None or self.job_kind:
                act = "rl"
            return {"ok": True, "activity": act, "detail": self.msg,
                    "mode": self.mode, "armed": self.armed,
                    "sim": True, "live": self._live(),
                    "demo": self.demo_state()}

    def operation_state(self) -> dict[str, Any]:
        with self.lock:
            running = bool(self.job_kind)
            return {"ok": True, "running": running,
                    "name": "rl_policy_sim" if running else "",
                    "progress": {"msg": self.msg, "live": self._live()},
                    "result": self.job_result}

    def calibration_report(self) -> dict[str, Any]:
        with self.lock:
            try:
                from hexapod_core import tripod_gait as TG
            except Exception:
                TG = None
            plant_deg = [round(float(v), 3) for v in
                         mujoco_rel_rad_to_robot_abs_deg(self.q_plant)]

            def foot_from(hip_deg: float, knee_deg: float) -> dict[str, float]:
                if TG is None:
                    return {"radial_mm": 0.0, "z_mm": 0.0}
                hip = math.radians(float(hip_deg))
                knee = math.radians(float(knee_deg))
                reach = (TG.COXA_MM + TG.FEMUR_MM * math.cos(hip)
                         + TG.TIBIA_MM * math.cos(knee))
                z = (-TG.FEMUR_MM * math.sin(hip)
                     - TG.TIBIA_MM * math.sin(knee))
                return {"radial_mm": round(reach, 2), "z_mm": round(z, 2)}

            per_leg = []
            for leg in range(6):
                yaw, hip, knee = plant_deg[leg * 3:leg * 3 + 3]
                per_leg.append({
                    "leg": leg,
                    "yaw_deg": yaw,
                    "hip_deg": hip,
                    "knee_deg": knee,
                    **foot_from(hip, knee),
                })
            z_vals = [float(r["z_mm"]) for r in per_leg]
            radial_vals = [float(r["radial_mm"]) for r in per_leg]
            params = getattr(self.env, "params", None)
            servo_params = None
            if params is not None:
                try:
                    servo_params = {
                        "source": getattr(params, "source", ""),
                        "timestamp": getattr(params, "timestamp", ""),
                        "speed_counts_s": getattr(params, "speed_counts_s", None),
                        "axes": {
                            ax: asdict(p)
                            for ax, p in getattr(params, "axes", {}).items()
                        },
                        "spread": getattr(params, "spread", {}),
                    }
                except Exception:
                    servo_params = {"source": str(getattr(params, "source", ""))}
            report = {
                "ok": True,
                "mode": "calibration_report",
                "sim": True,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "phases": [{
                    "name": "sim_snapshot",
                    "ok": True,
                    "summary": "MuJoCo state and active servo contract",
                }],
                "geometry": {
                    "ok": True,
                    "nominal_mm": ({
                        "coxa": TG.COXA_MM,
                        "femur": TG.FEMUR_MM,
                        "tibia": TG.TIBIA_MM,
                        "chassis_flat_to_flat": TG.CHASSIS_FLAT_TO_FLAT_MM,
                    } if TG is not None else {}),
                    "plant_joint_deg": plant_deg,
                    "per_leg": per_leg,
                    "summary": {
                        "mean_foot_z_mm": round(sum(z_vals) / len(z_vals), 2),
                        "foot_z_spread_mm": round(max(z_vals) - min(z_vals), 2),
                        "mean_radial_mm": round(
                            sum(radial_vals) / len(radial_vals), 2),
                        "radial_spread_mm": round(
                            max(radial_vals) - min(radial_vals), 2),
                    },
                    "mujoco_hint": {
                        "plant_joint_deg": plant_deg,
                        "neutral_foot_z_m": round(
                            (sum(z_vals) / len(z_vals)) * 0.001, 5),
                    },
                },
                "imu": {
                    "ok": True,
                    "sim": True,
                    "body_calibrated": True,
                    "body_frame": {
                        "pitch_axis": "pitch",
                        "pitch_axis_roll": 0.0,
                        "pitch_axis_pitch": 1.0,
                        "pitch_sign": 1.0,
                        "source": "mujoco_body_frame",
                    },
                },
                "actuators": {
                    "ok": True,
                    "sim": True,
                    "learned_model": servo_params,
                    "snapshot": None,
                },
                "live": self._live(),
            }
            stamp = time.strftime("%Y%m%d_%H%M%S")
            path = self.log_dir / f"calibration_report_{stamp}.json"
            latest = self.log_dir / "calibration_report_latest.json"
            path.write_text(json.dumps(report, indent=2) + "\n")
            latest.write_text(json.dumps(report, indent=2) + "\n")
            report["path"] = str(path)
            report["log_name"] = path.name
            report["latest"] = str(latest)
            return report

    def run_calibrate(self, *, mode: str = "checkup",
                      clearance_mm: float = 40.0, **_kw) -> dict[str, Any]:
        mode = (mode or "checkup").strip().lower()
        with self.lock:
            if mode not in {"checkup", "calibration", "auto", "all",
                            "geometry", "imu"}:
                self.job_result = {
                    "ok": False,
                    "mode": mode,
                    "error": f"sim calibration mode {mode!r} is report-only",
                }
            else:
                report = self.calibration_report()
                phases = list(report.get("phases") or [])
                if mode in {"checkup", "calibration", "auto", "all"}:
                    phases = [
                        {"name": "imu_rest", "ok": True,
                         "summary": "sim IMU is body-frame exact"},
                        {"name": "geometry_plant", "ok": True,
                         "summary": "sim plant pose captured"},
                        {"name": "actuator_contract", "ok": True,
                         "summary": "active servo params captured"},
                    ]
                self.job_result = {
                    "ok": True,
                    "mode": "checkup" if mode in {"calibration", "auto",
                                                 "all"} else mode,
                    "phases": phases,
                    "report": report,
                    "geometry": report.get("geometry"),
                    "imu": report.get("imu"),
                    "actuators": report.get("actuators"),
                    "path": report.get("path"),
                    "log_name": report.get("log_name"),
                    "latest": report.get("latest"),
                    "clearance_mm": float(clearance_mm),
                    "msg": "sim calibration report saved",
                }
            self.msg = self.job_result.get("msg") or self.job_result.get(
                "error") or "sim calibration"
            self.job_kind = None
            return {"ok": bool(self.job_result.get("ok")),
                    "calibrate": self.operation_state(),
                    "result": dict(self.job_result)}

    def sim_state(self) -> dict[str, Any]:
        with self.lock:
            return {"ok": True, "active": self.drive_active,
                    "joint_frame": FRAME_ROBOT_ABS,
                    "joint_contract": JOINT_CONTRACT,
                    "auto": self.auto[0] if self.auto else None,
                    "downed": self.downed, "sitting": self.sitting,
                    "viewer": self.cfg.viewer,
                    "frames": self.cfg.web_frames,
                    "live": self._live()}

    def rl_preflight(self, mode: str = "stand") -> dict[str, Any]:
        with self.lock:
            roll, pitch = self._roll_pitch_deg()
            if self.auto is not None:
                return {"ok": False, "error": "auto transition running",
                        "roll_deg": roll, "pitch_deg": pitch}
            if mode == "walk" and (self.downed or self.sitting
                                   or self._chassis_z() < 0.09):
                return {"ok": False, "error": "stand before walking",
                        "roll_deg": roll, "pitch_deg": pitch}
            return {"ok": True, "sim": True, "mode": mode,
                    "roll_deg": roll, "pitch_deg": pitch,
                    "max_pose_delta_deg": 0.0, "pose_tol_deg": 180.0}

    def rl_policy_info(self) -> dict[str, Any]:
        with self.lock:
            stance_path = self._active_stance_path()
            stance_info = (
                self._model_info(self.stance, stance_path)
                if self.stance is not None and stance_path is not None
                else self._unavailable_stance_info()
            )
            return {"ok": True, **stance_info,
                    "walk": self._model_info(self.walk, self.walk_list[self.wi])
                    if self.walk is not None else self._scripted_info()}

    def rl_timing_probe(self, *, samples: int = 200,
                        read_samples: int = 8) -> dict[str, Any]:
        """Non-mutating timing probe for the active MuJoCo walk policy path."""
        samples = max(1, min(2000, int(samples)))
        read_samples = max(0, min(50, int(read_samples)))
        with self.lock:
            if self.walk is None:
                return {"ok": False, "sim": True, "motion_free": True,
                        "error": ("active sim walk driver is scripted; "
                                  "select a learned walk policy")}
            model = self.walk
            policy_path = self.walk_list[self.wi]
            n_walk = int(self.n_walk)
            walk_kind = self.walk_kind
            obs = self.obs.copy()
            state = self.env._state
            q_nom = self.env._q_nom.copy()
            prev_action = self.env._prev_action.copy()
            goal = self.env._current_goal()
            tilt_ref = tuple(self.env._tilt_ref0)
            cfg = self.env.cfg
            max_dq = self.env.safety.max_dq
            max_roll = self.env.safety.max_roll
            max_pitch = self.env.safety.max_pitch
            dt = float(self.env.dt)

            read_times: list[float] = []
            for _ in range(read_samples):
                t0 = time.perf_counter()
                _ = self._live()
                _ = self._q_now()
                _ = self._roll_pitch_deg()
                read_times.append(time.perf_counter() - t0)

            scratch_safety = SafetyLayer(cfg)
            scratch_safety.max_dq = max_dq
            scratch_safety.max_roll = max_roll
            scratch_safety.max_pitch = max_pitch
            scratch_safety.set_nominal(q_nom)
            scratch_safety.set_tilt_reference(*tilt_ref)

            obs_times: list[float] = []
            policy_times: list[float] = []
            safety_times: list[float] = []
            total_times: list[float] = []
            bad_action = ""
            safety_trip = ""
            action_abs_max = 0.0

            def predict_once():
                if walk_kind == "hist":
                    frame = obs[:72].copy()
                    return model.predict(
                        np.concatenate([frame for _ in range(_HIST_K)]),
                        deterministic=True)
                if walk_kind == "gru":
                    o = np.concatenate([obs[:72], obs[-_N_MODE:]])
                    return model.policy.predict(
                        o, state=None, episode_start=np.ones((1,), dtype=bool),
                        deterministic=True)
                return model.predict(obs[:n_walk], deterministic=True)

            for _ in range(samples):
                tick_t0 = time.perf_counter()

                stage_t = time.perf_counter()
                _ = build_obs(cfg, state, q_nom, prev_action, goal=goal,
                              tilt_ref=tilt_ref)
                obs_times.append(time.perf_counter() - stage_t)

                stage_t = time.perf_counter()
                raw_act, _ = predict_once()
                policy_times.append(time.perf_counter() - stage_t)

                stage_t = time.perf_counter()
                action, bad = scratch_safety.validate_action(
                    raw_act, n_act=18)
                if action is None:
                    bad_action = bad
                    break
                q_prop = action_to_q_rad(action)
                q_safe, status = scratch_safety.filter(
                    q_prop, state, action=action)
                safety_times.append(time.perf_counter() - stage_t)
                if status.terminate:
                    safety_trip = status.reason
                    break

                prev_action = action.copy()
                action_abs_max = max(action_abs_max,
                                     float(np.max(np.abs(action))))
                _ = q_safe
                total_times.append(time.perf_counter() - tick_t0)

            return {
                "ok": not bad_action and not safety_trip,
                "sim": True,
                "motion_free": True,
                "mutates_sim_state": False,
                "physics_step_not_measured": True,
                "policy": policy_path.stem,
                "policy_file": policy_path.name,
                "obs_dim": n_walk,
                "policy_hz": round(1.0 / dt, 3) if dt > 0 else None,
                "budget_ms": round(dt * 1000.0, 3),
                "snapshot_read": _ms_stats(read_times),
                "snapshot_read_errors": 0,
                "hot_path": {
                    "total": _ms_stats(total_times),
                    "obs": _ms_stats(obs_times),
                    "policy": _ms_stats(policy_times),
                    "safety": _ms_stats(safety_times),
                },
                "max_delta_q_deg": round(math.degrees(max_dq), 4),
                "action_abs_max": round(action_abs_max, 4),
                "bad_action": bad_action or None,
                "safety_trip": safety_trip or None,
            }

    def _model_info(self, model: Any, path: Path) -> dict[str, Any]:
        if hasattr(model, "meta"):      # uploaded numpy policy
            return {"source": str(path),
                    "obs_dim": int(model.observation_space.shape[0]),
                    "act_dim": int(model.action_space.shape[0]),
                    "hidden": list(model.hidden),
                    "activation": model.meta.get("activation", "tanh"),
                    "uploaded": True,
                    "joint_frame": FRAME_ROBOT_ABS,
                    "joint_contract": JOINT_CONTRACT}
        return {"source": str(path), "obs_dim": int(model.observation_space.shape[0]),
                "act_dim": int(model.action_space.shape[0]),
                "hidden": self._hidden_layers(model),
                "joint_frame": FRAME_ROBOT_ABS,
                "joint_contract": JOINT_CONTRACT,
                "activation": getattr(getattr(model.policy, "activation_fn", None),
                                      "__name__", model.policy.__class__.__name__)}

    @staticmethod
    def _unavailable_stance_info() -> dict[str, Any]:
        return {"source": None, "obs_dim": 68, "act_dim": 18,
                "hidden": [], "activation": "unavailable",
                "joint_frame": FRAME_ROBOT_ABS,
                "joint_contract": JOINT_CONTRACT,
                "error": f"select a {JOINT_CONTRACT} stance policy"}

    @staticmethod
    def _hidden_layers(model: Any) -> list[int]:
        try:
            import torch.nn as nn
            return [m.out_features for m in model.policy.mlp_extractor.policy_net
                    if isinstance(m, nn.Linear)]
        except Exception:
            return []

    def _scripted_info(self) -> dict[str, Any]:
        return {"source": self._active_walk_name(), "obs_dim": 72,
                "act_dim": 18, "hidden": [], "activation": "scripted",
                "joint_frame": FRAME_ROBOT_ABS,
                "joint_contract": JOINT_CONTRACT}

    def rl_policies(self) -> dict[str, Any]:
        with self.lock:
            rows = []
            for p in self.stance_list:
                rows.append(self._policy_row(p, "stance", 68,
                                             p == self._active_stance_path()))
            for p in self.walk_list:
                if p in _SCRIPTED_ROWS:
                    rows.append(self._policy_row(p, "walk", 72,
                                                 p == self.walk_list[self.wi],
                                                 scripted=True))
                else:
                    rows.append(self._policy_row(
                        p, "walk", self._policy_obs_width(p) or 0,
                        p == self.walk_list[self.wi]))
            return {"ok": True, "dir": str(self.cfg.policy_dir),
                    "joint_frame": FRAME_ROBOT_ABS,
                    "joint_contract": JOINT_CONTRACT,
                    "rejected_count": len(self.rejected_policy_errors),
                    "policies": rows}

    def _policy_row(self, p: Path, slot: str, obs_dim: int, active: bool,
                    scripted: bool = False) -> dict[str, Any]:
        file = f"scripted:{p.name}" if scripted else p.name
        row = {"file": file, "name": p.stem, "slot": slot,
               "obs_dim": obs_dim, "active": active,
               "notes": _DESC.get(p.stem, "scripted gait" if scripted else "")}
        if p.suffix == ".json":
            row["uploaded"] = True
            try:
                meta = json.loads(p.read_text())["meta"]
                row["name"] = meta.get("name") or p.stem
                row["notes"] = meta.get("notes") or "uploaded policy"
            except (OSError, ValueError, KeyError):
                row["notes"] = "uploaded policy"
        return row

    def rl_roles(self) -> dict[str, Any]:
        with self.lock:
            roles = {}
            for role in ("walk", "hold", "stand", "lower"):
                roles[role] = {"file": self.roles.get(role, ""),
                               "resolved": self._role_resolved(role)}
            return {"ok": True,
                    "allowed_obs": {"walk": list(self.walk_widths),
                                    "hold": [68, *self.walk_widths],
                                    "stand": [68], "lower": [68]},
                    "roles": roles}

    def _role_resolved(self, role: str) -> str:
        if role == "walk":
            return self._active_walk_name()
        entry = self.role_models.get(role)
        if isinstance(entry, tuple):
            return entry[1].name
        if entry == "walk":
            return "walk policy @ zero command"
        return self._active_stance_name()

    def rl_role_set(self, role: str, file: str) -> dict[str, Any]:
        role = role.strip().lower()
        if role not in {"walk", "hold", "stand", "lower"}:
            return {"ok": False, "error": f"bad role {role!r}"}
        with self.lock:
            self._record_command(
                f"/api/rl/roles {role}={file or 'default'}")
            if not file:
                self.roles.pop(role, None)
                self.role_models.pop(role, None)
                return self.rl_roles()
            if role == "hold" and file == "walk":
                self.roles[role] = "walk"
                self.role_models[role] = "walk"
                return self.rl_roles()
            p = self.policy_index.get(file)
            if p is None or p in _SCRIPTED_ROWS:
                return {"ok": False, "error": f"unknown policy {file!r}"}
            w = self._policy_obs_width(p)
            if role in {"stand", "lower"} and w != 68:
                return {"ok": False, "error": f"{role} needs obs 68"}
            if role == "hold" and w not in (68, *self.walk_widths):
                return {"ok": False, "error": "hold needs stance/walk obs"}
            model = self._load_model(p)
            self.roles[role] = p.name
            self.role_models[role] = (model, p, int(w or 0))
            return self.rl_roles()

    def rl_policy_select(self, file: str) -> dict[str, Any]:
        with self.lock:
            self._record_command(f"/api/rl/policy_select file={file}")
            p = self.policy_index.get(file)
            if p is None:
                return {"ok": False, "error": f"unknown policy {file!r}"}
            if p in _SCRIPTED_ROWS:
                self._set_walk_path(p)
                return {"ok": True, "name": p.stem, "slot": "walk"}
            w = self._policy_obs_width(p)
            if w == 68:
                self._set_stance_path(p)
                return {"ok": True, "name": p.stem, "slot": "stance"}
            if w in self.walk_widths or (p.suffix == ".json"
                                         and w in (72, 74)):
                self._set_walk_path(p)
                return {"ok": True, "name": p.stem, "slot": "walk"}
            return {"ok": False, "error": f"unsupported obs width {w}"}

    def _set_stance_path(self, p: Path) -> None:
        model = self._load_model(p)
        self.si = self.stance_list.index(p.resolve())
        self.stance = model
        self.n_stance = int(model.observation_space.shape[0])
        self.msg = f"stance model -> {p.stem}"

    def _set_walk_path(self, p: Path) -> None:
        self.wi = self.walk_list.index(p)
        self.gait = None
        if p in _SCRIPTED_ROWS:
            self.walk = None
            self.n_walk = 72
            self.walk_kind = "plain"
            self.msg = f"walk driver -> scripted {p.name}"
            return
        self.walk = self._load_model(p)
        self.n_walk = int(self.walk.observation_space.shape[0])
        self.walk_kind = self._walk_kind_of(self.n_walk)
        if self.walk_kind == "plain" and self.n_walk > self.n_env:
            raise ValueError(f"{p.stem} needs --phase-obs")
        self._reset_memories(hard=True)
        self._apply_vel_contract(p.stem)
        self.msg = f"walk model -> {p.stem}"

    def rl_capture_plant(self) -> dict[str, Any]:
        with self.lock:
            self._record_command("/api/rl/capture_plant")
            self.q_plant = self._q_now()
            self.z_plant = self._chassis_z()
            return {"ok": True, "sim": True,
                    "hip_deg": round(math.degrees(self.q_plant[1]), 1),
                    "knee_deg": round(math.degrees(self.q_plant[2]), 1)}

    def rl_policy_move(self, mode: str, vx: float = 0.03, vy: float = 0.0,
                       duration_s: float = 6.0) -> dict[str, Any]:
        with self.lock:
            if mode == "walk":
                self._record_command(
                    f"/api/rl/walk vx={vx:+.3f} vy={vy:+.3f} "
                    f"duration={duration_s:.1f}")
            else:
                self._record_command(f"/api/rl/{mode}")
            self.drive_active = False
            self._clear_drive_dwell()
            self.timed_walk_until = None
            self._open_log(mode)
            self.job_kind = mode
            if mode == "stand":
                self._do_stand()
                if self.auto is None:
                    self._finish_job(self.msg, ok=False)
                    return {"ok": False, "error": self.msg,
                            "active": False, "live": self._live()}
            elif mode == "lower":
                self._do_sit()
                if self.auto is None:
                    self._finish_job(self.msg, ok=False)
                    return {"ok": False, "error": self.msg,
                            "active": False, "live": self._live()}
            elif mode == "walk":
                if not self._engage_walk():
                    self._finish_job(self.msg, ok=False)
                    return {"ok": False, "error": self.msg}
                _, vmax = self._drive_band()
                mag = float(np.hypot(vx, vy))
                scale = min(vmax / mag, 1.0) if mag > 1e-9 else 0.0
                self.traj.vx = float(vx * scale)
                self.traj.vy = float(vy * scale)
                self.timed_walk_until = self.sim_t + max(0.1, duration_s)
                self.msg = "timed walk running"
            else:
                self._finish_job(f"bad mode {mode}", ok=False)
                return {"ok": False, "error": f"bad mode {mode}"}
            return {"ok": True, "status": self.msg,
                    "active": self.drive_active, "live": self._live()}

    def rl_stop(self) -> dict[str, Any]:
        with self.lock:
            self._record_command("/api/rl/stop")
            self.drive_active = False
            self.timed_walk_until = None
            self.traj.vx = self.traj.vy = 0.0
            self.om_cmd = 0.0
            self._clear_drive_dwell()
            self.auto = None
            self._finish_job("stopped - holding")
            return {"ok": True, "status": self.msg, "live": self._live()}

    def rl_drive_start(self, vx: float = 0.0, vy: float = 0.0,
                       wz: float = 0.0, dh: float = 0.0) -> dict[str, Any]:
        with self.lock:
            self._record_command("/api/rl/drive/start")
            if self.auto is None and (self.sitting or self._chassis_z() < 0.09):
                self._do_stand()
                if self.auto is None:
                    return {"ok": False, "active": False,
                            "error": self.msg, "status": self.msg,
                            "live": self._live()}
            self.drive_active = True
            self.last_drive_cmd_at = time.monotonic()
            self.traj.vx = self.traj.vy = 0.0
            self.om_cmd = 0.0
            self._clear_drive_dwell()
            seed_vx = float(vx)
            seed_vy = float(vy)
            seed_wz = max(-0.5, min(0.5, float(wz)))
            seed_dh = max(-1.0, min(1.0, float(dh)))
            if seed_vx or seed_vy or seed_wz or seed_dh:
                self.rl_drive_cmd(seed_vx, seed_vy, seed_wz, seed_dh)
            self._open_log("drive")
            self.msg = "drive session active"
            return {"ok": True, "active": True, "status": self.msg,
                    "live": self._live()}

    # Live height-nudge envelope (D-pad up/down heartbeats) — mirrors
    # the hardware runner's DRIVE_HEIGHT_* constants in
    # linux_control/rl_policy.py so the twin behaves like the robot.
    _DRIVE_HEIGHT_RATE_MPS = 0.010
    _DRIVE_HEIGHT_MIN_M = -0.045
    _DRIVE_HEIGHT_MAX_M = 0.030
    _DRIVE_HEIGHT_EPS_M = 0.003

    def _set_drive_wz(self, wz: float) -> None:
        self.om_cmd = wz
        twz = getattr(self.traj, "wz", None)
        if twz is not None:
            try:
                twz[:] = wz
            except (TypeError, ValueError):
                self.traj.wz = wz

    def rl_drive_cmd(self, vx: float, vy: float, wz: float = 0.0,
                     dh: float = 0.0) -> dict[str, Any]:
        with self.lock:
            wz = max(-0.5, min(0.5, float(wz)))
            dh = max(-1.0, min(1.0, float(dh)))
            self._record_command(
                f"/api/rl/drive/cmd vx={vx:+.3f} vy={vy:+.3f} wz={wz:+.3f}"
                + (f" dh={dh:+.1f}" if dh else ""),
                key="drive-cmd")
            if not self.drive_active:
                return {"ok": True, "active": False, "status": "not active",
                        "result": self.job_result}
            now = time.monotonic()
            hb_dt = min(max(now - self.last_drive_cmd_at, 0.0), 0.5)
            self.last_drive_cmd_at = now
            goal = self.traj.goal
            moving = self._drive_cmd_moving(vx, vy, wz)
            if moving and abs(goal.height_ref) > self._DRIVE_HEIGHT_EPS_M:
                self.drive_zero_since = None
                # Walk champions trained at height_ref 0: ramp a nudged
                # body back to the walk anchor height first; the gait
                # engages on a later heartbeat once the ref is ~0.
                step = self._DRIVE_HEIGHT_RATE_MPS * hb_dt
                goal.height_ref = (
                    0.0 if abs(goal.height_ref) <= step
                    else goal.height_ref
                    - math.copysign(step, goal.height_ref))
                self.traj._pub.height_ref = goal.height_ref
                self.traj.vx = self.traj.vy = 0.0
                self._set_drive_wz(0.0)
                self.msg = "returning to walk height"
            elif moving:
                if self._engage_walk():
                    self.drive_zero_since = None
                    _, vmax = self._drive_band()
                    mag = float(np.hypot(vx, vy))
                    scale = min(vmax / mag, 1.0) if mag > 1e-9 else 0.0
                    self.traj.vx = float(vx * scale)
                    self.traj.vy = float(vy * scale)
                    self._set_drive_wz(wz)
                    self._drive_remember_refs()
                    if self.msg == "returning to walk height":
                        self.msg = "drive session active"
            elif self._drive_neutral_dwell_locked(now):
                pass
            else:
                self.traj.vx = self.traj.vy = 0.0
                self._set_drive_wz(0.0)
                if dh and self.auto is None and not self.downed \
                        and not self.sitting:
                    # Stance policy tracks the ref (pose-hold would
                    # freeze it), like the viewer's LB/RB nudges.
                    self.pose_hold_q = None
                    goal.height_ref = max(
                        self._DRIVE_HEIGHT_MIN_M,
                        min(self._DRIVE_HEIGHT_MAX_M,
                            goal.height_ref
                            + dh * self._DRIVE_HEIGHT_RATE_MPS * hb_dt))
                    self.traj._pub.height_ref = goal.height_ref
                if self.mode != "walk":
                    self.drive_zero_since = None
            return {"ok": True, "active": self.drive_active,
                    "status": self.msg, "live": self._live()}

    def rl_drive_stop(self) -> dict[str, Any]:
        with self.lock:
            self._record_command("/api/rl/drive/stop")
            self.drive_active = False
            self.traj.vx = self.traj.vy = 0.0
            self.om_cmd = 0.0
            self._clear_drive_dwell()
            self._close_log()
            self.job_result = {"ok": True, "ended": "drive stopped",
                               "sim_t_s": round(self.sim_t, 2),
                               "log": self._log_name or None}
            self.msg = "drive stopped - holding"
            return {"ok": True, "active": False, "result": self.job_result,
                    "live": self._live()}

    def rl_drive_state(self) -> dict[str, Any]:
        with self.lock:
            return {"ok": True, "active": self.drive_active,
                    "status": self.msg, "result": self.job_result,
                    "live": self._live()}

    _SCRIPTED_GAIT_BY_ID = {
        0: _TRIPOD_HW,
        1: _NOSLIP,
        2: _NOSLIP_RIPPLE,
        3: _NOSLIP_WAVE,
        4: _SE2_TETRAPOD,
        5: _SE2_WAVE,
        6: _SE2_CPG,
        7: _NOSLIP_CLEAN,
        8: _MIDDLE_TUCK_QUAD,
        9: _NOSLIP_FLUID,
        10: _NOSLIP_FLUID_FAST,
        11: _NOSLIP_FLUID_HYBRID,
        12: _NOSLIP_FLUID_PUSH,
        13: _NOSLIP_FLUID_PULSE,
    }

    def _set_scripted_gait_id(self, gait_id: int) -> dict[str, Any]:
        p = self._SCRIPTED_GAIT_BY_ID.get(int(gait_id))
        if p is None:
            return {"ok": False, "status": f"bad GAIT {gait_id}"}
        if p == _SE2_CPG and self._cpg_loaded is None:
            return {"ok": False,
                    "status": "refused GAIT 6 - CPGLOAD a controller first"}
        self._set_walk_path(p)
        if p == _TRIPOD_HW:
            desc = format_demo_tripod(self.demo_tripod)
        elif p == _SE2_CPG:
            desc = f"SE2 CPG ({self._cpg_loaded['name']})"
        else:
            desc = p.name
        self.msg = "walk driver -> scripted " + desc
        return {"ok": True, "status": self.msg}

    def _cpg_dirs(self) -> tuple[Path, Path]:
        root = getattr(self, "_proto_root", ROOT)
        return (
            root / "linux_control" / "policies",
            root / "rl_move" / "sim" / "policies",
        )

    def _load_cpg_controller(self, name: str) -> dict[str, Any]:
        try:
            loaded = _load_cpg_controller(name, dirs=self._cpg_dirs())
        except (ValueError, OSError) as e:
            return {"ok": False, "error": f"bad CPGLOAD: {e}"}
        self._cpg_loaded = loaded
        gk = loaded["gait_kw"]
        self.msg = (
            f"loaded CPG '{loaded['name']}' ({loaded['gait']}, "
            f"period={gk['period']:.2f} swing_frac={gk['swing_frac']:.3f} "
            f"lift={gk['lift'] * 1000:.1f}mm) - send GAIT 6 to use it"
        )
        if self.walk_list[self.wi] == _SE2_CPG:
            self.gait = None
        return {"ok": True, "status": self.msg, "text": self.msg}

    def _apply_demo_tripod_tune(self, updates: dict[str, float]) -> dict[str, Any]:
        if abs(self.traj.vx) + abs(self.traj.vy) + abs(self.om_cmd) > 1e-4:
            self.msg = "tripod tune refused while walking"
            return {"ok": False, "status": self.msg,
                    "error": "send J 0 0 0 before GTUNE"}
        try:
            self.demo_tripod = tune_demo_tripod(self.demo_tripod, updates)
        except ValueError as e:
            return {"ok": False, "error": f"bad GTUNE: {e}"}
        if self.walk_list[self.wi] == _TRIPOD_HW:
            self.gait = None
        self.msg = "GTUNE " + format_demo_tripod(self.demo_tripod)
        return {"ok": True, "status": self.msg}

    def cmd(self, line: str) -> dict[str, Any]:
        parts = line.strip().split()
        head = parts[0].upper() if parts else ""
        with self.lock:
            self._record_command(f"/cmd {line.strip()}",
                                 key="cmd-j" if head == "J" else None)
            if head == "ARM":
                self.armed = True
                self.msg = "sim armed"
            elif head in {"P", "STAND"}:
                self._do_reset("plant", 0.0, "reset plant")
            elif head in {"X", "DISARM", "RELAX"}:
                self.armed = False
                self.quad_reared = False
                self.rl_stop()
                self._clear_drive_dwell()
                self.msg = "sim stopped"
            elif head == "SETTLE":
                self.armed = False
                self._do_sit()
            elif head == "HOLD":
                self.traj.vx = self.traj.vy = 0.0
                self._set_drive_wz(0.0)
                self._clear_drive_dwell()
                self.msg = "holding"
            elif head == "GAIT" and len(parts) >= 2:
                try:
                    out = self._set_scripted_gait_id(int(parts[1]))
                except ValueError:
                    out = {"ok": False, "error": "bad GAIT"}
                self.msg = out.get("status") or out.get("error") or self.msg
                return out
            elif head == "CPGLIST":
                rows = _list_cpg_controllers(dirs=self._cpg_dirs())
                return {"ok": True, "text": json.dumps(rows)}
            elif head == "CPGLOAD" and len(parts) >= 2:
                return self._load_cpg_controller(parts[1])
            elif head == "GTUNE":
                if len(parts) == 1:
                    self.msg = "GTUNE " + format_demo_tripod(
                        self.demo_tripod)
                    return {"ok": True, "status": self.msg}
                try:
                    updates = parse_demo_tripod_tune_tokens(parts[1:])
                except ValueError as e:
                    return {"ok": False, "error": f"bad GTUNE: {e}"}
                return self._apply_demo_tripod_tune(updates)
            elif head == "K" and len(parts) >= 2:
                try:
                    return self._apply_demo_tripod_tune(
                        {"lift": float(parts[1])})
                except ValueError:
                    return {"ok": False, "error": "bad K"}
            elif head == "J" and len(parts) >= 4:
                if len(parts) >= 5:
                    try:
                        gait_id = int(parts[4])
                    except ValueError:
                        gait_id = None
                    p = self._SCRIPTED_GAIT_BY_ID.get(gait_id)
                    if p is not None and self.walk_list[self.wi] != p:
                        out = self._set_scripted_gait_id(gait_id)
                        if not out.get("ok"):
                            return out
                if self._engage_walk():
                    vx = float(parts[1]) / 1000.0
                    vy = float(parts[2]) / 1000.0
                    om = float(parts[3])
                    if self.walk_list[self.wi] == _TRIPOD_HW:
                        vx = max(-self.demo_tripod.max_vx_mps,
                                 min(self.demo_tripod.max_vx_mps, vx))
                        vy = max(-self.demo_tripod.max_vy_mps,
                                 min(self.demo_tripod.max_vy_mps, vy))
                        om = max(-self.demo_tripod.max_omega_rad_s,
                                 min(self.demo_tripod.max_omega_rad_s, om))
                    self.traj.vx = vx
                    self.traj.vy = vy
                    self.om_cmd = om
                    self._drive_remember_refs()
                    self.msg = "J command routed to sim"
            return {"ok": True, "status": self.msg}

    def sim_reset(self, start: str = "plant") -> dict[str, Any]:
        with self.lock:
            if start not in {"plant", "zero", "belly"}:
                start = "plant"
            self._record_command(f"/api/sim/reset start={start}")
            h = 0.0
            self._do_reset("zero" if start in {"zero", "belly"} else "plant",
                           h, f"reset {start}")
            return {"ok": True, "status": self.msg, "live": self._live()}

    def sim_pose(self, degrees: Any, source: str = "robot") -> dict[str, Any]:
        try:
            if not isinstance(degrees, (list, tuple)) or len(degrees) != 18:
                raise ValueError("expected 18 joint degrees")
            q_deg = np.array([float(v) for v in degrees], dtype=float)
            if not np.all(np.isfinite(q_deg)):
                raise ValueError("joint degrees must be finite numbers")
        except Exception as e:
            return {"ok": False, "error": str(e)}

        q_robot = np.radians(q_deg)
        q_model = robot_abs_rad_to_mujoco_rel_rad(q_robot)
        with self.lock:
            self._record_command(f"/api/sim/pose source={source}")
            self._stop_demo_locked(status="idle", clear_name=True)
            self.auto = None
            self.downed = False
            self.sitting = False
            self.drive_active = False
            self.timed_walk_until = None
            self.gait = None
            self.gait_t = 0.0
            self.om_cmd = 0.0
            self.traj.start_at = "plant"
            self.traj.goal = TaskGoal()
            self.traj.vx = self.traj.vy = 0.0
            self._clear_drive_dwell()
            self.traj.mode = "hold"
            self.traj.reset_published()
            self._reset_memories(hard=True)
            if hasattr(self.env, "_place_at_plant"):
                self.env._place_at_plant(q_model)
            else:
                qpos = self.env.data.qpos.copy()
                qpos[7:25] = q_model
                qvel = np.zeros_like(self.env.data.qvel)
                self._restore_phys(qpos, qvel)
            self.pose_hold_q = q_model.copy()
            self.q_plant = q_model.copy()
            self.z_plant = self._chassis_z()
            self.env._profile.reset(self._q_now())
            self.env.safety.set_nominal(q_robot)
            self._finish_job(f"synced {source} pose")
            return {
                "ok": True,
                "status": self.msg,
                "source": source,
                "live_joints": 18,
                "degrees": [round(float(v), 2) for v in q_deg],
                "live": self._live(),
            }

    def sim_fall(self) -> dict[str, Any]:
        with self.lock:
            self._record_command("/api/sim/fall")
            self._do_fall()
            return {"ok": True, "status": self.msg, "live": self._live()}

    def sim_recover(self) -> dict[str, Any]:
        with self.lock:
            self._record_command("/api/sim/recover")
            self.job_kind = "recover"
            self._open_log("recover")
            self._do_recover()
            return {"ok": self.auto is not None and self.auto[0] == "recover",
                    "status": self.msg, "live": self._live()}

    def sim_push(self, x: float = 4.0, y: float = 0.0) -> dict[str, Any]:
        with self.lock:
            self._record_command(f"/api/sim/push x={x:+.1f} y={y:+.1f}")
            self.push_force[:] = [x, y, 0.0]
            self.push_ticks = int(0.20 / self.env.dt)
            self.msg = f"push {x:+.1f},{y:+.1f} N"
            return {"ok": True, "status": self.msg, "live": self._live()}

    def frame_jpeg(self) -> bytes:
        if not self.cfg.web_frames:
            raise RuntimeError("browser frames disabled; use native MuJoCo viewer")
        if not self._frame_ready.wait(2.0):
            raise RuntimeError("sim frame not ready")
        with self.lock:
            if self._frame_jpeg is not None:
                return self._frame_jpeg
            err = self._frame_error or "sim frame unavailable"
        raise RuntimeError(err)

    def logs(self) -> dict[str, Any]:
        files = []
        self.log_dir.mkdir(parents=True, exist_ok=True)
        for f in sorted(self.log_dir.iterdir()):
            if f.is_file():
                st = f.stat()
                files.append({"name": f.name, "bytes": st.st_size,
                              "mtime_unix": round(st.st_mtime, 1)})
        files.sort(key=lambda x: -x["mtime_unix"])
        return {"ok": True, "dir": str(self.log_dir), "files": files}

    def log_file(self, name: str, request_path: str = "") -> tuple[bytes, str]:
        f = self.log_dir / Path(name).name
        if not f.is_file():
            raise FileNotFoundError(f"no such log: {name!r}")
        tail = 0
        if "tail=" in request_path:
            try:
                tail = int(request_path.split("tail=", 1)[1].split("&", 1)[0])
            except ValueError:
                tail = 0
        data = f.read_bytes()
        if tail > 0:
            lines = data.splitlines()[-tail:]
            data = b"\n".join(lines) + (b"\n" if lines else b"")
        return data, "text/csv; charset=utf-8"

    def close(self) -> None:
        self.stop_event.set()
        if getattr(self, "thread", None):
            self.thread.join(timeout=2.0)
        self._close_log()
