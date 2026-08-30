"""MuJoCo flip lab: sim-only impulse sweeps and open-loop roll search.

This is intentionally not a hardware runner. It loads the same MuJoCo
plant used by the training stack, applies the fitted servo model, keeps the
SafetyLayer command-slew contract, and asks two questions:

1. How much external roll torque does the current physics need to invert?
2. Can a small, explainable joint program roll the robot over by itself?

Usage:

    uv run python -m rl_move.sim.flip_lab impulse --source mesh_mjx
    uv run python -m rl_move.sim.flip_lab search --source mesh_mjx \
        --iterations 4 --population 16 --out logs/flip_lab/search.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control", ROOT / "linux_control" / "urt2_setup"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import mujoco  # noqa: E402

from rl_move.config import cfg_get, load_config  # noqa: E402
from rl_move.robot_state import DEG2RAD, N_JOINTS  # noqa: E402
from rl_move.sim.servo_model import (  # noqa: E402
    ServoProfile,
    SimServoParams,
    apply_params_to_model,
    build_model,
    joint_names,
    joint_qpos_addrs,
    joint_qvel_addrs,
    lowest_collidable_z,
    position_actuator_ids,
)
from rl_move.sim.sim_env import (  # noqa: E402
    _default_plant_deg,
    leg_chassis_collision_from_cfg,
    set_foot_ground_friction,
    soften_contacts,
)

CURRENT_PER_NM = 1.2
CURRENT_CAP_A = 3.0
DEFAULT_TORQUES_NM = (0.0, 1.5, 2.5, 3.5, 4.5, 6.0)
SIDE_LEGS = {
    "left": (0, 1, 2),
    "right": (3, 4, 5),
}


@dataclass(frozen=True)
class RealismLimits:
    """Hard gates for whether a sim flip is worth believing."""

    min_roll_tilt_deg: float = 60.0
    min_roll_gain_deg: float = 10.0
    min_initial_tilt_deg: float | None = None
    max_initial_tilt_deg: float | None = None
    max_peak_current_a: float = 3.0
    sustained_current_a: float = 2.5
    max_over_current_s: float = 2.0
    max_contact_force_n: float = 450.0
    max_body_lin_vel_m_s: float = 1.25
    max_body_ang_vel_rad_s: float = 12.0
    allow_assist_torque: bool = False


@dataclass(frozen=True)
class FlipCandidate:
    """Low-dimensional side-roll program.

    Angles are in degrees in the robot/model joint frame used by MuJoCo.
    The candidate is symmetric across the chosen side: the roll-side legs
    tuck, the opposite legs brace and kick.
    """

    side: str = "left"
    tuck_yaw_deg: float = 0.0
    tuck_hip_deg: float = -62.0
    tuck_knee_deg: float = 138.0
    kick_yaw_deg: float = 0.0
    kick_hip_deg: float = 30.0
    kick_knee_deg: float = -12.0
    windup_s: float = 1.4
    kick_s: float = 1.0
    coast_s: float = 1.0
    hold_s: float = 0.7
    assist_torque_nm: float = 0.0

    @property
    def total_s(self) -> float:
        return self.windup_s + self.kick_s + self.coast_s + self.hold_s


@dataclass(frozen=True)
class RockCandidate:
    """Repeated leg-only roll program.

    Each half-cycle tucks one side and extends the opposite side as a lever.
    The first half-cycle preloads away from the requested side, then the
    program alternates and finishes holding the requested roll direction.
    """

    side: str = "left"
    tuck_yaw_deg: float = 0.0
    tuck_hip_deg: float = -70.0
    tuck_knee_deg: float = 145.0
    lever_yaw_deg: float = 0.0
    lever_hip_deg: float = 28.0
    lever_knee_deg: float = 62.0
    raise_hip_deg: float = 28.0
    raise_knee_deg: float = 62.0
    raise_s: float = 1.2
    half_s: float = 1.0
    cycles: int = 5
    hold_s: float = 1.0

    @property
    def total_s(self) -> float:
        return self.raise_s + 2.0 * self.half_s * self.cycles + self.hold_s


@dataclass
class RolloutMetrics:
    score: float
    rolled: bool
    flipped: bool
    final_inverted: bool
    realistic: bool
    realistic_rolled: bool
    realistic_flipped: bool
    unstable: bool
    warning_count: int
    realism_violations: list[str]
    initial_tilt_deg: float
    max_tilt_deg: float
    roll_gain_deg: float
    final_tilt_deg: float
    initial_side_z: float
    min_side_z: float
    max_side_z: float
    final_side_z: float
    side_swapped: bool
    realistic_side_swapped: bool
    min_up_z: float
    final_up_z: float
    inverted_time_s: float
    over_current_time_s: float
    max_current_a: float
    max_torque_nm: float
    max_contact_force_n: float
    max_body_lin_vel_m_s: float
    max_body_ang_vel_rad_s: float
    min_root_z_m: float
    final_root_z_m: float | None
    seconds: float


_BOUNDS = (
    ("tuck_yaw_deg", -25.0, 25.0),
    ("tuck_hip_deg", -80.0, -25.0),
    ("tuck_knee_deg", 95.0, 150.0),
    ("kick_yaw_deg", -25.0, 25.0),
    ("kick_hip_deg", 5.0, 30.0),
    ("kick_knee_deg", -20.0, 75.0),
    ("windup_s", 0.7, 3.2),
    ("kick_s", 0.4, 2.6),
    ("coast_s", 0.3, 2.4),
    ("hold_s", 0.3, 1.4),
)

_ROCK_BOUNDS = (
    ("tuck_yaw_deg", -35.0, 35.0),
    ("tuck_hip_deg", -80.0, -20.0),
    ("tuck_knee_deg", 100.0, 150.0),
    ("lever_yaw_deg", -35.0, 35.0),
    ("lever_hip_deg", 10.0, 30.0),
    ("lever_knee_deg", -20.0, 95.0),
    ("raise_hip_deg", 18.0, 30.0),
    ("raise_knee_deg", 52.0, 78.0),
    ("raise_s", 0.0, 2.5),
    ("half_s", 0.25, 2.3),
    ("cycles", 0.0, 8.0),
    ("hold_s", 0.3, 3.5),
)


def candidate_from_unit(x: Iterable[float], *, side: str = "left",
                        assist_torque_nm: float = 0.0) -> FlipCandidate:
    vals = list(float(v) for v in x)
    if len(vals) != len(_BOUNDS):
        raise ValueError(f"expected {len(_BOUNDS)} values, got {len(vals)}")
    kwargs: dict[str, float | str] = {"side": side,
                                      "assist_torque_nm": assist_torque_nm}
    for raw, (name, lo, hi) in zip(vals, _BOUNDS):
        u = min(1.0, max(0.0, raw))
        kwargs[name] = lo + u * (hi - lo)
    return FlipCandidate(**kwargs)


def rock_candidate_from_unit(x: Iterable[float], *,
                             side: str = "left") -> RockCandidate:
    vals = list(float(v) for v in x)
    if len(vals) != len(_ROCK_BOUNDS):
        raise ValueError(f"expected {len(_ROCK_BOUNDS)} values, got {len(vals)}")
    kwargs: dict[str, float | str | int] = {"side": side}
    for raw, (name, lo, hi) in zip(vals, _ROCK_BOUNDS):
        u = min(1.0, max(0.0, raw))
        val = lo + u * (hi - lo)
        kwargs[name] = int(round(val)) if name == "cycles" else val
    return RockCandidate(**kwargs)


def side_leg_sets(side: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if side not in SIDE_LEGS:
        raise ValueError(f"side must be one of {tuple(SIDE_LEGS)}, got {side!r}")
    tuck = SIDE_LEGS[side]
    kick = tuple(i for i in range(6) if i not in tuck)
    return tuck, kick


def opposite_side(side: str) -> str:
    if side not in SIDE_LEGS:
        raise ValueError(f"side must be one of {tuple(SIDE_LEGS)}, got {side!r}")
    return "right" if side == "left" else "left"


def _quat_roll(theta: float) -> tuple[float, float, float, float]:
    return (math.cos(theta / 2.0), math.sin(theta / 2.0), 0.0, 0.0)


def _parse_float_list(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


class FlipLab:
    """Direct MuJoCo lab using the campaign's model and servo contract."""

    def __init__(self, *, source: str = "mesh_mjx",
                 servo_params: str = "loaded",
                 foot_friction: float | None = None,
                 control_hz: float | None = None,
                 max_delta_q_deg: float | None = None,
                 write_speed: float | None = None,
                 write_acc: float | None = None,
                 servo_vel_max_counts_s: str | float | None = None,
                 start_roll_deg: float = 0.0,
                 start_pose: str = "plant",
                 settle_s: float = 0.5,
                 realism_limits: RealismLimits | None = None,
                 seed: int = 0):
        self.cfg = load_config()
        self.cfg.setdefault("env", {})["model_source"] = source
        if foot_friction is not None:
            self.cfg.setdefault("env", {})["foot_friction_slide"] = (
                float(foot_friction))
        if control_hz is not None:
            self.cfg.setdefault("control", {})["hz"] = float(control_hz)
        if max_delta_q_deg is not None:
            self.cfg.setdefault("safety", {})["max_delta_q_deg"] = (
                float(max_delta_q_deg))
        if write_speed is not None:
            self.cfg.setdefault("bus", {})["write_speed"] = float(write_speed)
        if write_acc is not None:
            self.cfg.setdefault("bus", {})["write_acc"] = float(write_acc)
        if servo_vel_max_counts_s is not None:
            self.cfg.setdefault("bus", {})["servo_vel_max_counts_s"] = (
                servo_vel_max_counts_s)
        if servo_params:
            self.cfg.setdefault("bus", {})["servo_params"] = servo_params

        self.rng = np.random.default_rng(seed)
        self.params = SimServoParams.from_cfg(self.cfg)
        self.model = build_model(
            flat_terrain=True,
            mesh_visuals=False,
            source=source,
            leg_chassis_collision=leg_chassis_collision_from_cfg(self.cfg))
        apply_params_to_model(self.model, self.params)
        soften_contacts(self.model)
        mu = float(cfg_get(self.cfg, "env", "foot_friction_slide",
                           default=0.0))
        if mu > 0.0:
            set_foot_ground_friction(self.model, mu)
        self.data = mujoco.MjData(self.model)
        self.start_roll_deg = float(start_roll_deg)
        self.start_pose = str(start_pose)
        self.settle_s = float(settle_s)
        self.realism_limits = realism_limits or RealismLimits(
            sustained_current_a=float(cfg_get(
                self.cfg, "safety", "max_current_a", default=2.5)),
            max_over_current_s=float(cfg_get(
                self.cfg, "safety", "over_current_trip_s", default=2.0)))

        self.qadr = joint_qpos_addrs(self.model)
        self.vadr = joint_qvel_addrs(self.model)
        self.pos_act = position_actuator_ids(self.model)
        self.chassis_bid = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_BODY, "chassis")
        if self.chassis_bid < 0:
            raise RuntimeError("model has no chassis body")
        self.foot_gids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM,
                              f"L{i}_foot")
            for i in range(6)
        ]
        self.joint_ranges = self._joint_ranges()
        self.plant_q = self._clip_q(_default_plant_deg() * DEG2RAD)
        self.control_dt = 1.0 / float(cfg_get(self.cfg, "control", "hz",
                                              default=100.0))
        self.write_speed_deg_s = (
            float(cfg_get(self.cfg, "bus", "write_speed", default=400.0))
            * 360.0 / 4096.0)
        self.write_acc_units = float(cfg_get(self.cfg, "bus", "write_acc",
                                             default=20.0))
        self.max_delta_q_rad = (
            float(cfg_get(self.cfg, "safety", "max_delta_q_deg",
                          default=0.375)) * DEG2RAD)

    def _joint_ranges(self) -> np.ndarray:
        ranges = []
        for name in joint_names():
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT,
                                    name)
            if jid < 0:
                raise RuntimeError(f"joint {name!r} missing")
            ranges.append(self.model.jnt_range[jid])
        return np.asarray(ranges, dtype=float)

    def _clip_q(self, q: np.ndarray) -> np.ndarray:
        q = np.asarray(q, dtype=float).reshape(N_JOINTS).copy()
        return np.clip(q, self.joint_ranges[:, 0], self.joint_ranges[:, 1])

    def _place(self, q_rad: np.ndarray, *, roll_deg: float = 0.0) -> None:
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:3] = (0.0, 0.0, 0.22)
        self.data.qpos[3:7] = _quat_roll(roll_deg * DEG2RAD)
        self.data.qpos[self.qadr] = q_rad
        self.data.qvel[:] = 0.0
        self.data.ctrl[:] = 0.0
        self.data.ctrl[self.pos_act] = q_rad
        mujoco.mj_forward(self.model, self.data)
        low = lowest_collidable_z(self.model, self.data)
        self.data.qpos[2] += 0.002 - low
        mujoco.mj_forward(self.model, self.data)
        for _ in range(80):
            worst = min((self.data.contact[i].dist
                         for i in range(self.data.ncon)), default=0.0)
            if worst > -1e-4:
                break
            self.data.qpos[2] += -worst + 0.001
            mujoco.mj_forward(self.model, self.data)

    def _contact_force_peak(self) -> float:
        buf = np.zeros(6, dtype=float)
        peak = 0.0
        for ci in range(self.data.ncon):
            mujoco.mj_contactForce(self.model, self.data, ci, buf)
            peak = max(peak, float(np.linalg.norm(buf[:3])))
        return peak

    def _tilt(self) -> tuple[float, float]:
        R = np.asarray(self.data.xmat[self.chassis_bid], dtype=float).reshape(3, 3)
        up_z = float(R[2, 2])
        tilt = math.degrees(math.acos(min(1.0, max(-1.0, up_z))))
        return up_z, tilt

    def _side_z(self) -> float:
        R = np.asarray(self.data.xmat[self.chassis_bid], dtype=float).reshape(3, 3)
        return float(R[2, 1])

    def _state_finite(self) -> bool:
        return bool(
            np.all(np.isfinite(self.data.qpos))
            and np.all(np.isfinite(self.data.qvel))
            and np.all(np.isfinite(self.data.xmat[self.chassis_bid]))
        )

    def _warning_count(self) -> int:
        return int(sum(w.number for w in self.data.warning))

    def _realism_violations(self, cand: FlipCandidate, *,
                            unstable: bool,
                            warning_count: int,
                            initial_tilt: float | None,
                            max_current: float,
                            over_current_time: float,
                            max_contact: float,
                            max_lin_v: float,
                            max_ang_v: float) -> list[str]:
        lim = self.realism_limits
        violations = []
        if unstable or warning_count:
            violations.append("mujoco_unstable")
        if (lim.min_initial_tilt_deg is not None
                and initial_tilt is not None
                and initial_tilt < lim.min_initial_tilt_deg):
            violations.append("bad_initial_tilt")
        if (lim.max_initial_tilt_deg is not None
                and initial_tilt is not None
                and initial_tilt > lim.max_initial_tilt_deg):
            violations.append("bad_initial_tilt")
        if cand.assist_torque_nm and not lim.allow_assist_torque:
            violations.append("external_body_torque")
        if max_current > lim.max_peak_current_a:
            violations.append("peak_current")
        if over_current_time > lim.max_over_current_s:
            violations.append("sustained_over_current")
        if max_contact > lim.max_contact_force_n:
            violations.append("excess_contact_force")
        if max_lin_v > lim.max_body_lin_vel_m_s:
            violations.append("excess_body_linear_velocity")
        if max_ang_v > lim.max_body_ang_vel_rad_s:
            violations.append("excess_body_angular_velocity")
        return violations

    def _settle_hold(self, seconds: float) -> None:
        q = self.data.qpos[self.qadr].copy()
        self.data.ctrl[:] = 0.0
        self.data.ctrl[self.pos_act] = q
        for _ in range(max(0, int(round(seconds / self.model.opt.timestep)))):
            self.data.xfrc_applied[:] = 0.0
            mujoco.mj_step(self.model, self.data)

    def phase_targets(self, cand: FlipCandidate) -> list[np.ndarray]:
        tuck_legs, kick_legs = side_leg_sets(cand.side)
        plant = self.plant_q.copy()

        windup = plant.copy()
        for leg in tuck_legs:
            windup[3 * leg: 3 * leg + 3] = (
                cand.tuck_yaw_deg * DEG2RAD,
                cand.tuck_hip_deg * DEG2RAD,
                cand.tuck_knee_deg * DEG2RAD,
            )

        kick = windup.copy()
        for leg in kick_legs:
            kick[3 * leg: 3 * leg + 3] = (
                cand.kick_yaw_deg * DEG2RAD,
                cand.kick_hip_deg * DEG2RAD,
                cand.kick_knee_deg * DEG2RAD,
            )

        coast = kick.copy()
        for leg in kick_legs:
            coast[3 * leg + 1] = min(coast[3 * leg + 1],
                                     5.0 * DEG2RAD)
            coast[3 * leg + 2] = max(coast[3 * leg + 2],
                                     70.0 * DEG2RAD)
        return [self._clip_q(windup), self._clip_q(kick), self._clip_q(coast)]

    def rock_pose(self, side: str, cand: RockCandidate) -> np.ndarray:
        tuck_legs, lever_legs = side_leg_sets(side)
        q = self.plant_q.copy()
        for leg in tuck_legs:
            q[3 * leg: 3 * leg + 3] = (
                cand.tuck_yaw_deg * DEG2RAD,
                cand.tuck_hip_deg * DEG2RAD,
                cand.tuck_knee_deg * DEG2RAD,
            )
        for leg in lever_legs:
            q[3 * leg: 3 * leg + 3] = (
                cand.lever_yaw_deg * DEG2RAD,
                cand.lever_hip_deg * DEG2RAD,
                cand.lever_knee_deg * DEG2RAD,
            )
        return self._clip_q(q)

    def rock_raise_pose(self, cand: RockCandidate) -> np.ndarray:
        q = self.plant_q.copy()
        for leg in range(6):
            q[3 * leg + 1] = cand.raise_hip_deg * DEG2RAD
            q[3 * leg + 2] = cand.raise_knee_deg * DEG2RAD
        return self._clip_q(q)

    def rock_start_pose(self, cand: RockCandidate) -> np.ndarray:
        if self.start_pose == "plant":
            return self.plant_q
        if self.start_pose == "rock":
            return self.rock_pose(cand.side, cand)
        if self.start_pose == "rock-opposite":
            return self.rock_pose(opposite_side(cand.side), cand)
        if self.start_pose == "raise":
            return self.rock_raise_pose(cand)
        raise ValueError(
            "start_pose must be one of plant, rock, rock-opposite, raise; "
            f"got {self.start_pose!r}")

    def _target_for_time(self, targets: list[np.ndarray],
                         cand: FlipCandidate, t: float) -> np.ndarray:
        if t < cand.windup_s:
            return targets[0]
        if t < cand.windup_s + cand.kick_s:
            return targets[1]
        return targets[2]

    def _rock_target_for_time(self, cand: RockCandidate, t: float,
                              *, goal: str = "roll") -> np.ndarray:
        if t < cand.raise_s:
            return self.rock_raise_pose(cand)
        tr = t - cand.raise_s
        active_s = 2.0 * cand.half_s * cand.cycles
        if tr >= active_s:
            if goal == "side-to-side":
                return self.rock_pose(opposite_side(cand.side), cand)
            return self.rock_pose(cand.side, cand)
        half_i = int(max(0.0, tr) // max(cand.half_s, 1e-6))
        phase_side = opposite_side(cand.side) if half_i % 2 == 0 else cand.side
        return self.rock_pose(phase_side, cand)

    def _apply_assist_torque(self, cand: FlipCandidate, t: float,
                             side_sign: float) -> None:
        if (not cand.assist_torque_nm
                or t < cand.windup_s
                or t >= cand.windup_s + cand.kick_s):
            return
        phase = (t - cand.windup_s) / max(cand.kick_s, 1e-6)
        torque = cand.assist_torque_nm * math.sin(math.pi * phase) * side_sign
        R = np.asarray(self.data.xmat[self.chassis_bid],
                       dtype=float).reshape(3, 3)
        self.data.xfrc_applied[self.chassis_bid, 3:6] = R[:, 0] * torque

    def evaluate_candidate(self, cand: FlipCandidate, *,
                           settle_s: float = 0.5,
                           total_s: float | None = None,
                           record_stride: int = 25) -> RolloutMetrics:
        del record_stride  # reserved for future trace dumps
        self._place(self.plant_q, roll_deg=self.start_roll_deg)
        if settle_s > 0.0:
            self._settle_hold(settle_s)
        initial_up_z, initial_tilt = self._tilt()
        initial_side_z = self._side_z()

        targets = self.phase_targets(cand)
        profile = ServoProfile(self.params, self.data.qpos[self.qadr].copy())
        cmd = self.data.qpos[self.qadr].copy()
        next_control_t = self.data.time
        t0 = self.data.time
        h = self.model.opt.timestep
        total = float(total_s if total_s is not None else cand.total_s)
        side_sign = 1.0 if cand.side == "left" else -1.0
        warning0 = self._warning_count()

        min_up_z = initial_up_z
        final_up_z = initial_up_z
        final_tilt = initial_tilt
        min_side_z = initial_side_z
        max_side_z = initial_side_z
        final_side_z = initial_side_z
        inverted_ticks = 0
        max_current = 0.0
        max_torque = 0.0
        max_contact = 0.0
        max_lin_v = 0.0
        max_ang_v = 0.0
        min_root_z = float(self.data.qpos[2])
        over_current_ticks = 0
        unstable = False

        steps = max(1, int(round(total / h)))
        for _ in range(steps):
            t = self.data.time - t0
            if self.data.time + 1e-12 >= next_control_t:
                desired = self._target_for_time(targets, cand, t)
                delta = np.clip(desired - cmd, -self.max_delta_q_rad,
                                self.max_delta_q_rad)
                cmd = self._clip_q(cmd + delta)
                profile.command(cmd, speed_deg_s=self.write_speed_deg_s,
                                acc_units=self.write_acc_units)
                next_control_t += self.control_dt

            target = profile.tick(h)
            q = self.data.qpos[self.qadr]
            err = target - q
            db = profile.deadband_rad
            eff = q + np.sign(err) * np.maximum(np.abs(err) - db, 0.0)
            self.data.ctrl[:] = 0.0
            self.data.ctrl[self.pos_act] = eff

            self.data.xfrc_applied[:] = 0.0
            self._apply_assist_torque(cand, t, side_sign)

            mujoco.mj_step(self.model, self.data)
            warning_count = self._warning_count() - warning0
            if warning_count or not self._state_finite():
                unstable = True
                break
            torque_abs = np.abs(self.data.qfrc_actuator[self.vadr])
            current = np.minimum(torque_abs * CURRENT_PER_NM, CURRENT_CAP_A)
            max_current = max(max_current, float(np.max(current)))
            if float(np.max(current)) > self.realism_limits.sustained_current_a:
                over_current_ticks += 1
            max_torque = max(max_torque, float(np.max(torque_abs)))
            max_contact = max(max_contact, self._contact_force_peak())
            max_lin_v = max(max_lin_v, float(np.linalg.norm(self.data.qvel[:3])))
            max_ang_v = max(max_ang_v, float(np.linalg.norm(self.data.qvel[3:6])))
            min_root_z = min(min_root_z, float(self.data.qpos[2]))
            up_z, tilt = self._tilt()
            side_z = self._side_z()
            min_up_z = min(min_up_z, up_z)
            final_up_z, final_tilt = up_z, tilt
            min_side_z = min(min_side_z, side_z)
            max_side_z = max(max_side_z, side_z)
            final_side_z = side_z
            if up_z < -0.75:
                inverted_ticks += 1

        inverted_time = inverted_ticks * h
        max_tilt = math.degrees(math.acos(min(1.0, max(-1.0, min_up_z))))
        roll_gain = max(0.0, max_tilt - initial_tilt)
        rolled = (max_tilt >= self.realism_limits.min_roll_tilt_deg
                  and roll_gain >= self.realism_limits.min_roll_gain_deg)
        over_current_time = over_current_ticks * h
        flipped = min_up_z < -0.75
        final_inverted = final_up_z < -0.5
        side_swapped = (
            abs(initial_side_z) >= 0.65
            and abs(final_side_z) >= 0.65
            and initial_side_z * final_side_z < -0.35
            and 60.0 <= final_tilt <= 120.0
        )
        warning_count = max(0, self._warning_count() - warning0)
        violations = self._realism_violations(
            cand,
            unstable=unstable,
            warning_count=warning_count,
            initial_tilt=initial_tilt,
            max_current=max_current,
            over_current_time=over_current_time,
            max_contact=max_contact,
            max_lin_v=max_lin_v,
            max_ang_v=max_ang_v)
        realistic = not violations
        score = self._score(
            min_up_z=min_up_z,
            final_up_z=final_up_z,
            max_current=max_current,
            max_contact=max_contact,
            max_lin_v=max_lin_v,
            max_ang_v=max_ang_v,
            realism_violations=violations)
        return RolloutMetrics(
            score=float(score),
            rolled=bool(rolled and not unstable),
            flipped=bool(flipped and not unstable),
            final_inverted=bool(final_inverted and not unstable),
            realistic=bool(realistic),
            realistic_rolled=bool(rolled and not unstable and realistic),
            realistic_flipped=bool(flipped and final_inverted
                                   and not unstable and realistic),
            unstable=bool(unstable),
            warning_count=warning_count,
            realism_violations=violations,
            initial_tilt_deg=round(float(initial_tilt), 3),
            max_tilt_deg=round(float(max_tilt), 3),
            roll_gain_deg=round(float(roll_gain), 3),
            final_tilt_deg=round(float(final_tilt), 3),
            initial_side_z=round(float(initial_side_z), 6),
            min_side_z=round(float(min_side_z), 6),
            max_side_z=round(float(max_side_z), 6),
            final_side_z=round(float(final_side_z), 6),
            side_swapped=bool(side_swapped and not unstable),
            realistic_side_swapped=bool(side_swapped and not unstable
                                        and realistic),
            min_up_z=round(float(min_up_z), 6),
            final_up_z=round(float(final_up_z), 6),
            inverted_time_s=round(float(inverted_time), 4),
            over_current_time_s=round(float(over_current_time), 4),
            max_current_a=round(float(max_current), 4),
            max_torque_nm=round(float(max_torque), 4),
            max_contact_force_n=round(float(max_contact), 3),
            max_body_lin_vel_m_s=round(float(max_lin_v), 4),
            max_body_ang_vel_rad_s=round(float(max_ang_v), 4),
            min_root_z_m=round(float(min_root_z), 5),
            final_root_z_m=round(float(self.data.qpos[2]), 5)
            if math.isfinite(float(self.data.qpos[2])) else None,
            seconds=round(float(total), 4),
        )

    def evaluate_rock_candidate(self, cand: RockCandidate, *,
                                settle_s: float = 0.5,
                                total_s: float | None = None,
                                record_stride: int = 25,
                                goal: str = "roll") -> RolloutMetrics:
        del record_stride
        if goal not in ("roll", "invert", "side-to-side"):
            raise ValueError(
                "goal must be 'roll', 'invert', or 'side-to-side', "
                f"got {goal!r}")
        self._place(self.rock_start_pose(cand), roll_deg=self.start_roll_deg)
        if settle_s > 0.0:
            self._settle_hold(settle_s)
        initial_up_z, initial_tilt = self._tilt()
        initial_side_z = self._side_z()

        profile = ServoProfile(self.params, self.data.qpos[self.qadr].copy())
        cmd = self.data.qpos[self.qadr].copy()
        next_control_t = self.data.time
        t0 = self.data.time
        h = self.model.opt.timestep
        total = float(total_s if total_s is not None else cand.total_s)
        warning0 = self._warning_count()

        min_up_z = initial_up_z
        final_up_z = initial_up_z
        final_tilt = initial_tilt
        min_side_z = initial_side_z
        max_side_z = initial_side_z
        final_side_z = initial_side_z
        inverted_ticks = 0
        over_current_ticks = 0
        max_current = 0.0
        max_torque = 0.0
        max_contact = 0.0
        max_lin_v = 0.0
        max_ang_v = 0.0
        min_root_z = float(self.data.qpos[2])
        unstable = False

        steps = max(1, int(round(total / h)))
        for _ in range(steps):
            t = self.data.time - t0
            if self.data.time + 1e-12 >= next_control_t:
                desired = self._rock_target_for_time(cand, t, goal=goal)
                delta = np.clip(desired - cmd, -self.max_delta_q_rad,
                                self.max_delta_q_rad)
                cmd = self._clip_q(cmd + delta)
                profile.command(cmd, speed_deg_s=self.write_speed_deg_s,
                                acc_units=self.write_acc_units)
                next_control_t += self.control_dt

            target = profile.tick(h)
            q = self.data.qpos[self.qadr]
            err = target - q
            eff = q + np.sign(err) * np.maximum(
                np.abs(err) - profile.deadband_rad, 0.0)
            self.data.ctrl[:] = 0.0
            self.data.ctrl[self.pos_act] = eff
            self.data.xfrc_applied[:] = 0.0

            mujoco.mj_step(self.model, self.data)
            warning_count = self._warning_count() - warning0
            if warning_count or not self._state_finite():
                unstable = True
                break
            torque_abs = np.abs(self.data.qfrc_actuator[self.vadr])
            current = np.minimum(torque_abs * CURRENT_PER_NM, CURRENT_CAP_A)
            max_current = max(max_current, float(np.max(current)))
            if float(np.max(current)) > self.realism_limits.sustained_current_a:
                over_current_ticks += 1
            max_torque = max(max_torque, float(np.max(torque_abs)))
            max_contact = max(max_contact, self._contact_force_peak())
            max_lin_v = max(max_lin_v, float(np.linalg.norm(self.data.qvel[:3])))
            max_ang_v = max(max_ang_v, float(np.linalg.norm(self.data.qvel[3:6])))
            min_root_z = min(min_root_z, float(self.data.qpos[2]))
            up_z, tilt = self._tilt()
            side_z = self._side_z()
            min_up_z = min(min_up_z, up_z)
            final_up_z, final_tilt = up_z, tilt
            min_side_z = min(min_side_z, side_z)
            max_side_z = max(max_side_z, side_z)
            final_side_z = side_z
            if up_z < -0.75:
                inverted_ticks += 1

        inverted_time = inverted_ticks * h
        max_tilt = math.degrees(math.acos(min(1.0, max(-1.0, min_up_z))))
        roll_gain = max(0.0, max_tilt - initial_tilt)
        rolled = (max_tilt >= self.realism_limits.min_roll_tilt_deg
                  and roll_gain >= self.realism_limits.min_roll_gain_deg)
        over_current_time = over_current_ticks * h
        flipped = min_up_z < -0.75
        final_inverted = final_up_z < -0.5
        side_swapped = (
            abs(initial_side_z) >= 0.65
            and abs(final_side_z) >= 0.65
            and initial_side_z * final_side_z < -0.35
            and 60.0 <= final_tilt <= 120.0
        )
        warning_count = max(0, self._warning_count() - warning0)
        violations = self._realism_violations(
            FlipCandidate(side=cand.side),
            unstable=unstable,
            warning_count=warning_count,
            initial_tilt=initial_tilt,
            max_current=max_current,
            over_current_time=over_current_time,
            max_contact=max_contact,
            max_lin_v=max_lin_v,
            max_ang_v=max_ang_v)
        realistic = not violations
        score = self._score_roll(
            goal=goal,
            min_up_z=min_up_z,
            final_up_z=final_up_z,
            initial_side_z=initial_side_z,
            final_side_z=final_side_z,
            max_tilt_deg=max_tilt,
            roll_gain_deg=roll_gain,
            final_tilt_deg=final_tilt,
            max_current=max_current,
            max_contact=max_contact,
            max_lin_v=max_lin_v,
            max_ang_v=max_ang_v,
            realism_violations=violations)
        return RolloutMetrics(
            score=float(score),
            rolled=bool(rolled and not unstable),
            flipped=bool(flipped and not unstable),
            final_inverted=bool(final_inverted and not unstable),
            realistic=bool(realistic),
            realistic_rolled=bool(rolled and not unstable and realistic),
            realistic_flipped=bool(flipped and final_inverted
                                   and not unstable and realistic),
            unstable=bool(unstable),
            warning_count=warning_count,
            realism_violations=violations,
            initial_tilt_deg=round(float(initial_tilt), 3),
            max_tilt_deg=round(float(max_tilt), 3),
            roll_gain_deg=round(float(roll_gain), 3),
            final_tilt_deg=round(float(final_tilt), 3),
            initial_side_z=round(float(initial_side_z), 6),
            min_side_z=round(float(min_side_z), 6),
            max_side_z=round(float(max_side_z), 6),
            final_side_z=round(float(final_side_z), 6),
            side_swapped=bool(side_swapped and not unstable),
            realistic_side_swapped=bool(side_swapped and not unstable
                                        and realistic),
            min_up_z=round(float(min_up_z), 6),
            final_up_z=round(float(final_up_z), 6),
            inverted_time_s=round(float(inverted_time), 4),
            over_current_time_s=round(float(over_current_time), 4),
            max_current_a=round(float(max_current), 4),
            max_torque_nm=round(float(max_torque), 4),
            max_contact_force_n=round(float(max_contact), 3),
            max_body_lin_vel_m_s=round(float(max_lin_v), 4),
            max_body_ang_vel_rad_s=round(float(max_ang_v), 4),
            min_root_z_m=round(float(min_root_z), 5),
            final_root_z_m=round(float(self.data.qpos[2]), 5)
            if math.isfinite(float(self.data.qpos[2])) else None,
            seconds=round(float(total), 4),
        )

    @staticmethod
    def _realism_cost(violations: list[str] | None) -> float:
        weights = {
            "mujoco_unstable": 10000.0,
            "bad_initial_tilt": 3000.0,
        }
        return sum(weights.get(v, 400.0) for v in (violations or []))

    @staticmethod
    def _score(*, min_up_z: float, final_up_z: float,
               max_current: float, max_contact: float,
               max_lin_v: float, max_ang_v: float,
               realism_violations: list[str] | None = None) -> float:
        # Lower is better. The main objective is inversion; the remaining
        # terms keep the search from preferring violent contact artifacts.
        invert_cost = 120.0 * (min_up_z + 1.0)
        final_cost = 40.0 * (final_up_z + 1.0)
        current_cost = 15.0 * max(0.0, max_current - 2.5) ** 2
        contact_cost = 0.02 * max(0.0, max_contact - 120.0)
        velocity_cost = 2.0 * max(0.0, max_lin_v - 1.5)
        spin_cost = 0.4 * max(0.0, max_ang_v - 15.0)
        realism_cost = FlipLab._realism_cost(realism_violations)
        return (invert_cost + final_cost + current_cost + contact_cost
                + velocity_cost + spin_cost + realism_cost)

    def _score_roll(self, *, goal: str, min_up_z: float, final_up_z: float,
                    initial_side_z: float, final_side_z: float,
                    max_tilt_deg: float, roll_gain_deg: float,
                    final_tilt_deg: float,
                    max_current: float, max_contact: float,
                    max_lin_v: float, max_ang_v: float,
                    realism_violations: list[str] | None = None) -> float:
        # Lower is better. For the rolling search, first get past a real
        # roll threshold, then prefer candidates that finish tilted instead
        # of just throwing one instant of angular velocity into the body.
        roll_goal = self.realism_limits.min_roll_tilt_deg
        gain_goal = self.realism_limits.min_roll_gain_deg
        tilt_deficit = max(0.0, roll_goal - max_tilt_deg)
        gain_deficit = max(0.0, gain_goal - roll_gain_deg)
        final_deficit = max(0.0, 0.75 * roll_goal - final_tilt_deg)
        current_limit = self.realism_limits.sustained_current_a
        contact_limit = self.realism_limits.max_contact_force_n
        lin_limit = self.realism_limits.max_body_lin_vel_m_s
        ang_limit = self.realism_limits.max_body_ang_vel_rad_s
        current_cost = 15.0 * max(0.0, max_current - current_limit) ** 2
        contact_cost = 0.02 * max_contact
        contact_cost += 1.5 * max(0.0, max_contact - contact_limit)
        contact_cost += 0.002 * max(0.0, max_contact - contact_limit) ** 2
        velocity_cost = 20.0 * max(0.0, max_lin_v - lin_limit)
        spin_cost = 6.0 * max(0.0, max_ang_v - ang_limit)
        realism_cost = FlipLab._realism_cost(realism_violations)
        dynamics_cost = (current_cost + contact_cost + velocity_cost
                         + spin_cost + realism_cost)
        if goal == "invert":
            flip_deficit = max(0.0, min_up_z + 0.75)
            final_invert_deficit = max(0.0, final_up_z + 0.5)
            deep_final_bonus = max(0.0, -0.5 - final_up_z)
            return (220.0 * flip_deficit
                    + 180.0 * final_invert_deficit
                    + 4.0 * gain_deficit
                    + 0.5 * max(0.0, 160.0 - max_tilt_deg)
                    - 25.0 * deep_final_bonus
                    + dynamics_cost)
        if goal == "side-to-side":
            start_side_deficit = max(0.0, 0.70 - abs(initial_side_z))
            opposite_progress = -initial_side_z * final_side_z
            opposite_deficit = max(0.0, 0.70 - opposite_progress)
            final_side_deficit = max(0.0, 0.80 - abs(final_side_z))
            final_side_tilt_cost = abs(final_tilt_deg - 90.0)
            cross_over_deficit = max(0.0, min_up_z + 0.55)
            return (350.0 * start_side_deficit
                    + 420.0 * opposite_deficit
                    + 180.0 * final_side_deficit
                    + 1.6 * final_side_tilt_cost
                    + 120.0 * cross_over_deficit
                    + 2.5 * gain_deficit
                    + dynamics_cost)
        return (6.0 * tilt_deficit + 8.0 * gain_deficit
                + 2.0 * final_deficit + dynamics_cost)

    def impulse_sweep(self, torques_nm: Iterable[float], *,
                      side: str = "left",
                      pulse_s: float = 1.0,
                      total_s: float = 3.0,
                      settle_s: float = 0.5) -> list[dict]:
        side_sign = 1.0 if side == "left" else -1.0
        rows = []
        for mag in torques_nm:
            self._place(self.plant_q, roll_deg=self.start_roll_deg)
            if settle_s > 0.0:
                self._settle_hold(settle_s)
            initial_up, initial_tilt = self._tilt()
            t0 = self.data.time
            h = self.model.opt.timestep
            warning0 = self._warning_count()
            max_tilt = initial_tilt
            min_up = initial_up
            max_current = 0.0
            max_contact = 0.0
            max_lin_v = 0.0
            max_ang_v = 0.0
            unstable = False
            for _ in range(max(1, int(round(total_s / h)))):
                t = self.data.time - t0
                self.data.xfrc_applied[:] = 0.0
                if t < pulse_s and mag:
                    torque = float(mag) * math.sin(math.pi * t / pulse_s)
                    R = np.asarray(self.data.xmat[self.chassis_bid],
                                   dtype=float).reshape(3, 3)
                    self.data.xfrc_applied[self.chassis_bid, 3:6] = (
                        R[:, 0] * torque * side_sign)
                self.data.ctrl[:] = 0.0
                self.data.ctrl[self.pos_act] = self.plant_q
                mujoco.mj_step(self.model, self.data)
                warning_count = self._warning_count() - warning0
                if warning_count or not self._state_finite():
                    unstable = True
                    break
                up, tilt = self._tilt()
                min_up = min(min_up, up)
                max_tilt = max(max_tilt, tilt)
                torque_abs = np.abs(self.data.qfrc_actuator[self.vadr])
                current = np.minimum(torque_abs * CURRENT_PER_NM,
                                     CURRENT_CAP_A)
                max_current = max(max_current, float(np.max(current)))
                max_contact = max(max_contact, self._contact_force_peak())
                max_lin_v = max(max_lin_v,
                                float(np.linalg.norm(self.data.qvel[:3])))
                max_ang_v = max(max_ang_v,
                                float(np.linalg.norm(self.data.qvel[3:6])))
            final_up = None if unstable else float(self._tilt()[0])
            roll_gain = max(0.0, max_tilt - initial_tilt)
            within_limits = (
                not unstable
                and max_current <= self.realism_limits.max_peak_current_a
                and max_contact <= self.realism_limits.max_contact_force_n
                and max_lin_v <= self.realism_limits.max_body_lin_vel_m_s
                and max_ang_v <= self.realism_limits.max_body_ang_vel_rad_s
            )
            rows.append({
                "torque_nm": float(mag),
                "side": side,
                "pulse_s": float(pulse_s),
                "initial_tilt_deg": round(float(initial_tilt), 3),
                "max_tilt_deg": round(float(max_tilt), 3),
                "roll_gain_deg": round(float(roll_gain), 3),
                "min_up_z": round(float(min_up), 6),
                "final_up_z": round(final_up, 6) if final_up is not None
                else None,
                "flipped": bool(min_up < -0.75 and not unstable),
                "final_inverted": bool(final_up is not None
                                       and final_up < -0.5
                                       and not unstable),
                "unstable": bool(unstable),
                "warning_count": max(0, self._warning_count() - warning0),
                "max_current_a": round(float(max_current), 4),
                "max_contact_force_n": round(float(max_contact), 3),
                "max_body_lin_vel_m_s": round(float(max_lin_v), 4),
                "max_body_ang_vel_rad_s": round(float(max_ang_v), 4),
                "within_limits": bool(within_limits),
            })
        return rows

    def render_candidate_video(self, cand: FlipCandidate, path: Path,
                               *, fps: int = 30, width: int = 960,
                               height: int = 720,
                               total_s: float | None = None) -> None:
        try:
            import imageio.v2 as imageio
        except Exception as exc:  # pragma: no cover - optional path
            raise RuntimeError("video export needs imageio") from exc

        self._place(self.plant_q, roll_deg=self.start_roll_deg)
        if self.settle_s > 0.0:
            self._settle_hold(self.settle_s)
        renderer = mujoco.Renderer(self.model, width=width, height=height)
        cam = mujoco.MjvCamera()
        mujoco.mjv_defaultFreeCamera(self.model, cam)
        cam.distance = 0.9
        cam.azimuth = 135
        cam.elevation = -25
        cam.lookat[:] = (0.0, 0.0, 0.08)

        targets = self.phase_targets(cand)
        profile = ServoProfile(self.params, self.data.qpos[self.qadr].copy())
        cmd = self.data.qpos[self.qadr].copy()
        next_control_t = self.data.time
        t0 = self.data.time
        h = self.model.opt.timestep
        total = float(total_s if total_s is not None else cand.total_s)
        frame_dt = 1.0 / fps
        next_frame_t = 0.0
        side_sign = 1.0 if cand.side == "left" else -1.0
        frames = []
        for _ in range(max(1, int(round(total / h)))):
            t = self.data.time - t0
            if self.data.time + 1e-12 >= next_control_t:
                desired = self._target_for_time(targets, cand, t)
                cmd = self._clip_q(
                    cmd + np.clip(desired - cmd, -self.max_delta_q_rad,
                                  self.max_delta_q_rad))
                profile.command(cmd, speed_deg_s=self.write_speed_deg_s,
                                acc_units=self.write_acc_units)
                next_control_t += self.control_dt
            target = profile.tick(h)
            q = self.data.qpos[self.qadr]
            err = target - q
            eff = q + np.sign(err) * np.maximum(
                np.abs(err) - profile.deadband_rad, 0.0)
            self.data.ctrl[:] = 0.0
            self.data.ctrl[self.pos_act] = eff
            self.data.xfrc_applied[:] = 0.0
            self._apply_assist_torque(cand, t, side_sign)
            mujoco.mj_step(self.model, self.data)
            if t + 1e-12 >= next_frame_t:
                renderer.update_scene(self.data, camera=cam)
                frames.append(renderer.render())
                next_frame_t += frame_dt
        renderer.close()
        path.parent.mkdir(parents=True, exist_ok=True)
        imageio.mimsave(path, frames, fps=fps)

    def render_rock_candidate_video(self, cand: RockCandidate, path: Path,
                                    *, fps: int = 30, width: int = 960,
                                    height: int = 720,
                                    total_s: float | None = None,
                                    goal: str = "roll") -> None:
        try:
            import imageio.v2 as imageio
        except Exception as exc:  # pragma: no cover - optional path
            raise RuntimeError("video export needs imageio") from exc

        self._place(self.rock_start_pose(cand), roll_deg=self.start_roll_deg)
        if self.settle_s > 0.0:
            self._settle_hold(self.settle_s)
        renderer = mujoco.Renderer(self.model, width=width, height=height)
        cam = mujoco.MjvCamera()
        mujoco.mjv_defaultFreeCamera(self.model, cam)
        cam.distance = 0.9
        cam.azimuth = 135
        cam.elevation = -25
        cam.lookat[:] = (0.0, 0.0, 0.08)

        profile = ServoProfile(self.params, self.data.qpos[self.qadr].copy())
        cmd = self.data.qpos[self.qadr].copy()
        next_control_t = self.data.time
        t0 = self.data.time
        h = self.model.opt.timestep
        total = float(total_s if total_s is not None else cand.total_s)
        frame_dt = 1.0 / fps
        next_frame_t = 0.0
        frames = []
        for _ in range(max(1, int(round(total / h)))):
            t = self.data.time - t0
            if self.data.time + 1e-12 >= next_control_t:
                desired = self._rock_target_for_time(cand, t, goal=goal)
                cmd = self._clip_q(
                    cmd + np.clip(desired - cmd, -self.max_delta_q_rad,
                                  self.max_delta_q_rad))
                profile.command(cmd, speed_deg_s=self.write_speed_deg_s,
                                acc_units=self.write_acc_units)
                next_control_t += self.control_dt
            target = profile.tick(h)
            q = self.data.qpos[self.qadr]
            err = target - q
            eff = q + np.sign(err) * np.maximum(
                np.abs(err) - profile.deadband_rad, 0.0)
            self.data.ctrl[:] = 0.0
            self.data.ctrl[self.pos_act] = eff
            self.data.xfrc_applied[:] = 0.0
            mujoco.mj_step(self.model, self.data)
            if t + 1e-12 >= next_frame_t:
                renderer.update_scene(self.data, camera=cam)
                frames.append(renderer.render())
                next_frame_t += frame_dt
        renderer.close()
        path.parent.mkdir(parents=True, exist_ok=True)
        imageio.mimsave(path, frames, fps=fps)


def cem_search(lab: FlipLab, *, side: str, iterations: int,
               population: int, elite_frac: float, seed: int,
               assist_torque_nm: float, total_s: float | None = None,
               settle_s: float = 0.5) -> dict:
    rng = np.random.default_rng(seed)
    dim = len(_BOUNDS)
    mean = np.full(dim, 0.5)
    std = np.full(dim, 0.32)
    elite_n = max(1, int(round(population * elite_frac)))
    history = []
    best_row = None

    for it in range(iterations):
        xs = np.clip(rng.normal(mean, std, size=(population, dim)), 0.0, 1.0)
        if it == 0:
            xs[0] = 0.5
        rows = []
        for x in xs:
            cand = candidate_from_unit(
                x, side=side, assist_torque_nm=assist_torque_nm)
            metrics = lab.evaluate_candidate(
                cand, total_s=total_s, settle_s=settle_s)
            row = {
                "candidate": asdict(cand),
                "metrics": asdict(metrics),
                "unit": [round(float(v), 6) for v in x],
            }
            rows.append(row)
            if best_row is None or metrics.score < best_row["metrics"]["score"]:
                best_row = row
        rows.sort(key=lambda r: r["metrics"]["score"])
        elites = np.asarray([r["unit"] for r in rows[:elite_n]], dtype=float)
        mean = 0.7 * mean + 0.3 * elites.mean(axis=0)
        std = np.maximum(0.05, 0.7 * std + 0.3 * elites.std(axis=0))
        history.append({
            "iteration": it,
            "best_score": rows[0]["metrics"]["score"],
            "best_max_tilt_deg": rows[0]["metrics"]["max_tilt_deg"],
            "best_roll_gain_deg": rows[0]["metrics"]["roll_gain_deg"],
            "best_final_tilt_deg": rows[0]["metrics"]["final_tilt_deg"],
            "best_flipped": rows[0]["metrics"]["flipped"],
            "best_realistic": rows[0]["metrics"]["realistic"],
            "best_realistic_flipped": rows[0]["metrics"]["realistic_flipped"],
            "best_candidate": rows[0]["candidate"],
        })
        print("[flip_lab] iter=%d best_score=%.3f max_tilt=%.1f "
              "final_tilt=%.1f flipped=%s realistic_flip=%s" % (
                  it, rows[0]["metrics"]["score"],
                  rows[0]["metrics"]["max_tilt_deg"],
                  rows[0]["metrics"]["final_tilt_deg"],
                  rows[0]["metrics"]["flipped"],
                  rows[0]["metrics"]["realistic_flipped"]))
    return {
        "settings": {
            "side": side,
            "iterations": iterations,
            "population": population,
            "elite_frac": elite_frac,
            "seed": seed,
            "assist_torque_nm": assist_torque_nm,
            "total_s": total_s,
            "start_roll_deg": lab.start_roll_deg,
            "settle_s": settle_s,
            "bounds": _BOUNDS,
            "realism_limits": asdict(lab.realism_limits),
        },
        "best": best_row,
        "history": history,
    }


def cem_rock_search(lab: FlipLab, *, side: str, iterations: int,
                    population: int, elite_frac: float, seed: int,
                    total_s: float | None = None,
                    settle_s: float = 0.5,
                    goal: str = "roll") -> dict:
    rng = np.random.default_rng(seed)
    dim = len(_ROCK_BOUNDS)
    mean = np.full(dim, 0.5)
    std = np.full(dim, 0.34)
    elite_n = max(1, int(round(population * elite_frac)))
    history = []
    best_row = None

    for it in range(iterations):
        xs = np.clip(rng.normal(mean, std, size=(population, dim)), 0.0, 1.0)
        if it == 0:
            xs[0] = 0.5
            xs[1 % population] = np.array([
                0.5, 0.1, 0.95,
                0.5, 0.95, 0.4,
                0.85, 0.4, 0.5,
                0.35, 0.55, 0.5])
            if population > 2:
                xs[2] = np.array([
                    0.123231, 0.195713, 0.0,
                    0.132607, 0.0, 0.243909,
                    0.85, 0.4, 0.5,
                    0.936601, 0.391366, 0.818573])
        rows = []
        for x in xs:
            cand = rock_candidate_from_unit(x, side=side)
            metrics = lab.evaluate_rock_candidate(
                cand, total_s=total_s, settle_s=settle_s, goal=goal)
            row = {
                "candidate": asdict(cand),
                "metrics": asdict(metrics),
                "unit": [round(float(v), 6) for v in x],
            }
            rows.append(row)
            if best_row is None or metrics.score < best_row["metrics"]["score"]:
                best_row = row
        rows.sort(key=lambda r: r["metrics"]["score"])
        elites = np.asarray([r["unit"] for r in rows[:elite_n]], dtype=float)
        mean = 0.7 * mean + 0.3 * elites.mean(axis=0)
        std = np.maximum(0.05, 0.7 * std + 0.3 * elites.std(axis=0))
        history.append({
            "iteration": it,
            "best_score": rows[0]["metrics"]["score"],
            "best_max_tilt_deg": rows[0]["metrics"]["max_tilt_deg"],
            "best_roll_gain_deg": rows[0]["metrics"]["roll_gain_deg"],
            "best_final_tilt_deg": rows[0]["metrics"]["final_tilt_deg"],
            "best_final_side_z": rows[0]["metrics"]["final_side_z"],
            "best_rolled": rows[0]["metrics"]["rolled"],
            "best_side_swapped": rows[0]["metrics"]["side_swapped"],
            "best_realistic": rows[0]["metrics"]["realistic"],
            "best_realistic_rolled": rows[0]["metrics"]["realistic_rolled"],
            "best_realistic_side_swapped": (
                rows[0]["metrics"]["realistic_side_swapped"]),
            "best_candidate": rows[0]["candidate"],
        })
        print("[flip_lab] rock goal=%s iter=%d best_score=%.3f max_tilt=%.1f "
              "gain=%.1f final_tilt=%.1f final_side_z=%.2f "
              "side_swapped=%s realistic_side=%s" % (
                  goal, it, rows[0]["metrics"]["score"],
                  rows[0]["metrics"]["max_tilt_deg"],
                  rows[0]["metrics"]["roll_gain_deg"],
                  rows[0]["metrics"]["final_tilt_deg"],
                  rows[0]["metrics"]["final_side_z"],
                  rows[0]["metrics"]["side_swapped"],
                  rows[0]["metrics"]["realistic_side_swapped"]))
    return {
        "settings": {
            "side": side,
            "iterations": iterations,
            "population": population,
            "elite_frac": elite_frac,
            "seed": seed,
            "total_s": total_s,
            "start_roll_deg": lab.start_roll_deg,
            "settle_s": settle_s,
            "goal": goal,
            "bounds": _ROCK_BOUNDS,
            "realism_limits": asdict(lab.realism_limits),
        },
        "best": best_row,
        "history": history,
    }


def _write_json(path: str | None, blob: dict | list) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(blob, indent=2, allow_nan=False) + "\n")
    print(f"[flip_lab] wrote {p}")


def _load_candidate_blob(path: str) -> dict:
    blob = json.loads(Path(path).read_text())
    if "best" in blob and isinstance(blob["best"], dict):
        blob = blob["best"]
    if "candidate" in blob and isinstance(blob["candidate"], dict):
        out = dict(blob["candidate"])
        if "half_s" in out and "raise_s" not in out:
            out.setdefault("raise_hip_deg", 28.0)
            out.setdefault("raise_knee_deg", 62.0)
            out["raise_s"] = 0.0
        return out
    if isinstance(blob, dict):
        out = dict(blob)
        if "half_s" in out and "raise_s" not in out:
            out.setdefault("raise_hip_deg", 28.0)
            out.setdefault("raise_knee_deg", 62.0)
            out["raise_s"] = 0.0
        return out
    raise ValueError(f"{path}: expected candidate dict or search result")


def _make_lab(args) -> FlipLab:
    limits = RealismLimits(
        min_roll_tilt_deg=args.min_real_roll_tilt_deg,
        min_roll_gain_deg=args.min_real_roll_gain_deg,
        min_initial_tilt_deg=args.min_real_initial_tilt_deg,
        max_initial_tilt_deg=args.max_real_initial_tilt_deg,
        max_peak_current_a=args.max_real_peak_current_a,
        sustained_current_a=args.real_sustained_current_a,
        max_over_current_s=args.max_real_over_current_s,
        max_contact_force_n=args.max_real_contact_n,
        max_body_lin_vel_m_s=args.max_real_lin_vel,
        max_body_ang_vel_rad_s=args.max_real_ang_vel,
        allow_assist_torque=args.allow_assist_realism,
    )
    return FlipLab(
        source=args.source,
        servo_params=args.servo_params,
        foot_friction=args.foot_friction,
        control_hz=args.control_hz,
        max_delta_q_deg=args.max_delta_q_deg,
        write_speed=args.write_speed,
        write_acc=args.write_acc,
        servo_vel_max_counts_s=args.servo_vel_max_counts_s,
        start_roll_deg=args.start_roll_deg,
        start_pose=args.start_pose,
        settle_s=args.settle_s,
        realism_limits=limits,
        seed=args.seed,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--source", default="mesh_mjx",
                       choices=("mesh", "mesh_mjx", "primitive"))
        p.add_argument("--servo-params", default="loaded",
                       help="'loaded', '', or explicit servo json")
        p.add_argument("--foot-friction", type=float, default=None)
        p.add_argument("--control-hz", type=float, default=None)
        p.add_argument("--max-delta-q-deg", type=float, default=None)
        p.add_argument("--write-speed", type=float, default=None)
        p.add_argument("--write-acc", type=float, default=None)
        p.add_argument("--servo-vel-max-counts-s", default=None)
        p.add_argument("--start-roll-deg", type=float, default=0.0)
        p.add_argument("--start-pose", default="plant",
                       choices=("plant", "rock", "rock-opposite", "raise"))
        p.add_argument("--settle-s", type=float, default=0.5)
        p.add_argument("--min-real-roll-tilt-deg", type=float, default=60.0)
        p.add_argument("--min-real-roll-gain-deg", type=float, default=10.0)
        p.add_argument("--min-real-initial-tilt-deg", type=float, default=None)
        p.add_argument("--max-real-initial-tilt-deg", type=float, default=None)
        p.add_argument("--max-real-peak-current-a", type=float, default=3.0)
        p.add_argument("--real-sustained-current-a", type=float, default=2.5)
        p.add_argument("--max-real-over-current-s", type=float, default=2.0)
        p.add_argument("--max-real-contact-n", type=float, default=450.0)
        p.add_argument("--max-real-lin-vel", type=float, default=1.25)
        p.add_argument("--max-real-ang-vel", type=float, default=12.0)
        p.add_argument("--allow-assist-realism", action="store_true")
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--out", default=None)

    imp = sub.add_parser("impulse")
    add_common(imp)
    imp.add_argument("--side", default="left", choices=tuple(SIDE_LEGS))
    imp.add_argument("--torque-nm", default=",".join(
        str(x) for x in DEFAULT_TORQUES_NM))
    imp.add_argument("--pulse-s", type=float, default=1.0)
    imp.add_argument("--total-s", type=float, default=3.0)

    sea = sub.add_parser("search")
    add_common(sea)
    sea.add_argument("--side", default="left", choices=tuple(SIDE_LEGS))
    sea.add_argument("--iterations", type=int, default=4)
    sea.add_argument("--population", type=int, default=16)
    sea.add_argument("--elite-frac", type=float, default=0.25)
    sea.add_argument("--assist-torque-nm", type=float, default=0.0)
    sea.add_argument("--total-s", type=float, default=None)
    sea.add_argument("--video", default=None)

    rock = sub.add_parser("rock-search")
    add_common(rock)
    rock.add_argument("--side", default="left", choices=tuple(SIDE_LEGS))
    rock.add_argument("--iterations", type=int, default=6)
    rock.add_argument("--population", type=int, default=24)
    rock.add_argument("--elite-frac", type=float, default=0.25)
    rock.add_argument("--goal", default="roll",
                      choices=("roll", "invert", "side-to-side"))
    rock.add_argument("--total-s", type=float, default=None)
    rock.add_argument("--video", default=None)

    rock_eval = sub.add_parser("rock-eval")
    add_common(rock_eval)
    rock_eval.add_argument("--candidate", required=True)
    rock_eval.add_argument("--goal", default="roll",
                           choices=("roll", "invert", "side-to-side"))
    rock_eval.add_argument("--total-s", type=float, default=None)
    rock_eval.add_argument("--video", default=None)

    args = ap.parse_args()
    t_start = time.time()
    lab = _make_lab(args)
    if args.cmd == "impulse":
        rows = lab.impulse_sweep(
            _parse_float_list(args.torque_nm),
            side=args.side,
            pulse_s=args.pulse_s,
            total_s=args.total_s,
            settle_s=args.settle_s)
        for row in rows:
            print(json.dumps(row, sort_keys=True, allow_nan=False))
        _write_json(args.out, {"rows": rows})
    elif args.cmd == "search":
        result = cem_search(
            lab,
            side=args.side,
            iterations=max(1, args.iterations),
            population=max(2, args.population),
            elite_frac=min(0.9, max(0.05, args.elite_frac)),
            seed=args.seed,
            assist_torque_nm=args.assist_torque_nm,
            total_s=args.total_s,
            settle_s=args.settle_s)
        result["elapsed_s"] = round(time.time() - t_start, 3)
        print(json.dumps(result["best"], indent=2, allow_nan=False))
        _write_json(args.out, result)
        if args.video and result["best"]:
            cand = FlipCandidate(**result["best"]["candidate"])
            lab.render_candidate_video(cand, Path(args.video),
                                       total_s=args.total_s)
            print(f"[flip_lab] wrote {args.video}")
    elif args.cmd == "rock-search":
        result = cem_rock_search(
            lab,
            side=args.side,
            iterations=max(1, args.iterations),
            population=max(2, args.population),
            elite_frac=min(0.9, max(0.05, args.elite_frac)),
            seed=args.seed,
            total_s=args.total_s,
            settle_s=args.settle_s,
            goal=args.goal)
        result["elapsed_s"] = round(time.time() - t_start, 3)
        print(json.dumps(result["best"], indent=2, allow_nan=False))
        _write_json(args.out, result)
        if args.video and result["best"]:
            cand = RockCandidate(**result["best"]["candidate"])
            lab.render_rock_candidate_video(cand, Path(args.video),
                                            total_s=args.total_s,
                                            goal=args.goal)
            print(f"[flip_lab] wrote {args.video}")
    elif args.cmd == "rock-eval":
        cand = RockCandidate(**_load_candidate_blob(args.candidate))
        metrics = lab.evaluate_rock_candidate(
            cand, total_s=args.total_s, settle_s=args.settle_s,
            goal=args.goal)
        result = {
            "settings": {
                "source": args.source,
                "start_roll_deg": args.start_roll_deg,
                "settle_s": args.settle_s,
                "goal": args.goal,
                "total_s": args.total_s,
                "realism_limits": asdict(lab.realism_limits),
            },
            "candidate": asdict(cand),
            "metrics": asdict(metrics),
            "elapsed_s": round(time.time() - t_start, 3),
        }
        print(json.dumps(result, indent=2, allow_nan=False))
        _write_json(args.out, result)
        if args.video:
            lab.render_rock_candidate_video(cand, Path(args.video),
                                            total_s=args.total_s,
                                            goal=args.goal)
            print(f"[flip_lab] wrote {args.video}")
    else:  # pragma: no cover
        raise AssertionError(args.cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
