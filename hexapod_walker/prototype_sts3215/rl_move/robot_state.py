"""Synchronized RobotState acquisition for Phase-1 balance."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from .attitude import ComplementaryAttitude, G0
from .config import cfg_get

N_JOINTS = 18
DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi


@dataclass
class RobotState:
    timestamp: float
    joint_position: np.ndarray       # (18,) rad
    joint_velocity: np.ndarray       # (18,) rad/s
    imu_roll: float
    imu_pitch: float
    imu_yaw: float
    imu_gyro: np.ndarray             # (3,) rad/s
    imu_accel: np.ndarray            # (3,) m/s²
    commanded_position: np.ndarray   # (18,) rad
    servo_load: np.ndarray | None = None
    servo_current: np.ndarray | None = None
    servo_temperature: np.ndarray | None = None
    bus_ok: bool = True
    imu_ok: bool = True
    dt: float = 0.0
    timing: dict = field(default_factory=dict)


@dataclass
class AcquisitionTiming:
    t_pos: float = 0.0
    t_imu: float = 0.0
    t_fb: float = 0.0
    t_total: float = 0.0
    did_full_feedback: bool = False


class JointVelocityFilter:
    def __init__(self, *, alpha: float = 0.3, max_jump_rad: float = 0.5,
                 n: int = N_JOINTS):
        self.alpha = float(alpha)
        self.max_jump = float(max_jump_rad)
        self.n = int(n)
        self._q_prev: np.ndarray | None = None
        self._qd = np.zeros(self.n, dtype=float)
        self._t_prev: float | None = None

    def reset(self) -> None:
        self._q_prev = None
        self._qd[:] = 0.0
        self._t_prev = None

    def update(self, q: np.ndarray, t: float) -> np.ndarray:
        q = np.asarray(q, dtype=float).reshape(self.n)
        if self._q_prev is None or self._t_prev is None:
            self._q_prev = q.copy()
            self._t_prev = float(t)
            self._qd[:] = 0.0
            return self._qd.copy()
        dt = float(t) - self._t_prev
        if dt < 1e-4 or dt > 0.25:
            # Missed / bad sample — hold velocity, refresh pose stamp carefully.
            self._q_prev = q.copy()
            self._t_prev = float(t)
            return self._qd.copy()
        dq = q - self._q_prev
        # Reject absurd jumps (bus glitch); hold qd.
        if np.any(np.abs(dq) > self.max_jump):
            self._q_prev = q.copy()
            self._t_prev = float(t)
            return self._qd.copy()
        raw = dq / dt
        a = self.alpha
        self._qd = a * raw + (1.0 - a) * self._qd
        self._q_prev = q.copy()
        self._t_prev = float(t)
        return self._qd.copy()


class RobotStateEstimator:
    """One coherent snapshot per ``update()`` call."""

    def __init__(self, bus: Any, cfg: dict | None = None):
        self.bus = bus
        cfg = cfg or {}
        self._alpha = float(cfg_get(cfg, "velocity_filter", "alpha", default=0.3))
        self._max_jump = float(
            cfg_get(cfg, "velocity_filter", "max_jump_rad", default=0.5))
        fb_hz = float(cfg_get(cfg, "sensing", "full_feedback_hz", default=10))
        self._fb_period = (1.0 / fb_hz) if fb_hz > 0 else 1e9
        self._qd_filter = JointVelocityFilter(
            alpha=self._alpha, max_jump_rad=self._max_jump)
        self._att = ComplementaryAttitude(alpha=0.98)
        self._cmd = np.zeros(N_JOINTS, dtype=float)
        self._last_fb_t = -1e9
        self._load = np.zeros(N_JOINTS, dtype=float)
        self._current = np.zeros(N_JOINTS, dtype=float)
        self._temp = np.zeros(N_JOINTS, dtype=float)
        self._have_fb = False
        self._fb_sample_seq = 0
        self._last_fb_valid_ids: list[int] = []
        self._last_fb_complete = False
        self._imu_stale_s = float(
            cfg_get(cfg, "safety", "imu_stale_ms", default=100)) / 1000.0
        self.last_timing = AcquisitionTiming()
        self._t_prev_state: float | None = None

    def _acquire_feedback(self) -> tuple[float, list[int], bool]:
        """Read one health frame, retaining every valid per-joint value."""
        t_c = time.monotonic()
        try:
            fb = self.bus.read_all_feedback()
        except Exception:
            fb = {}
        elapsed = time.monotonic() - t_c
        validated: dict[int, tuple[float, float, float]] = {}
        if isinstance(fb, dict):
            for j, rec in fb.items():
                try:
                    jj = int(j)
                    load = float(rec["load_pct"])
                    current = float(rec["current_a"])
                    temp = float(rec["temp_c"])
                except (KeyError, TypeError, ValueError):
                    continue
                values = (load, current, temp)
                if (0 <= jj < N_JOINTS
                        and all(math.isfinite(value) for value in values)):
                    validated[jj] = values

        valid_ids = sorted(validated)
        complete = valid_ids == list(range(N_JOINTS))
        # Rate-limit the next attempt even when this one is incomplete. A
        # missing ID must be observed on separate physical acquisitions, not
        # retried four times inside one direct runner tick.
        # Anchor the cadence after the transaction completes.  A slow or
        # timed-out aggregate read must not make the very next state update
        # immediately issue another aggregate transaction.
        self._last_fb_t = time.monotonic()
        self._fb_sample_seq += 1
        self._last_fb_valid_ids = valid_ids
        self._last_fb_complete = complete
        if validated:
            self._have_fb = True
            for jj, (load, current, temp) in validated.items():
                self._load[jj] = load
                self._current[jj] = current
                self._temp[jj] = temp
        return elapsed, valid_ids, complete

    def _feedback_timing(self, *, attempted: bool,
                         valid_ids: list[int] | None = None,
                         complete: bool | None = None) -> dict:
        current_ids = list(valid_ids or []) if attempted else []
        current_complete = bool(complete) if attempted else False
        return {
            # Historical keys describe this state-building call.
            "full_feedback": current_complete,
            "full_feedback_attempted": attempted,
            "full_feedback_complete": current_complete,
            "full_feedback_count": len(current_ids),
            "full_feedback_ids": current_ids,
            # Persistent acquisition identity lets a slower direct runner
            # consume a partial frame even if a later position-only substep
            # produced the RobotState it receives.
            "feedback_sample_seq": (self._fb_sample_seq
                                    if self._fb_sample_seq else None),
            "feedback_sample_fresh": attempted,
            "feedback_complete": self._last_fb_complete,
            "feedback_valid_count": len(self._last_fb_valid_ids),
            "feedback_valid_ids": list(self._last_fb_valid_ids),
            "feedback_missing_ids": [
                j for j in range(N_JOINTS)
                if j not in self._last_fb_valid_ids],
        }

    def update_feedback(self, state: RobotState) -> RobotState:
        """Attach one health acquisition without re-running q/IMU filters."""
        t_fb, valid_ids, complete = self._acquire_feedback()
        timing = dict(state.timing or {})
        timing["t_fb"] = t_fb
        timing.update(self._feedback_timing(
            attempted=True, valid_ids=valid_ids, complete=complete))
        return replace(
            state,
            servo_load=self._load.copy() if self._have_fb else None,
            servo_current=self._current.copy() if self._have_fb else None,
            servo_temperature=self._temp.copy() if self._have_fb else None,
            timing=timing,
        )

    def set_commanded(self, q_rad: np.ndarray | list[float]) -> None:
        self._cmd = np.asarray(q_rad, dtype=float).reshape(N_JOINTS).copy()

    def reset_episode_filters(self) -> None:
        """Clear qd history + attitude transients; keep physical level."""
        self._qd_filter.reset()
        self._att.reset_transients()
        self._t_prev_state = None

    def _state_from_sample(
            self, pos_deg: dict | None, imu: dict | None, *,
            t0: float, timing: AcquisitionTiming,
            want_full_feedback: bool | None, source: str,
            snapshot_meta: dict | None = None) -> RobotState:
        bus_ok = isinstance(pos_deg, dict) and len(pos_deg) >= N_JOINTS
        q = np.zeros(N_JOINTS, dtype=float)
        if bus_ok:
            for j in range(N_JOINTS):
                if j not in pos_deg:
                    bus_ok = False
                    break
                q[j] = float(pos_deg[j]) * DEG2RAD
        elif isinstance(pos_deg, dict):
            for j, deg in pos_deg.items():
                if 0 <= int(j) < N_JOINTS:
                    q[int(j)] = float(deg) * DEG2RAD

        t_now = time.monotonic()
        qd = self._qd_filter.update(q, t_now)
        imu_ok = isinstance(imu, dict) and "ax_g" in imu
        if imu_ok:
            accel_g = (imu["ax_g"], imu["ay_g"], imu["az_g"])
            gyro_rps = (imu["gx_dps"] * DEG2RAD,
                        imu["gy_dps"] * DEG2RAD,
                        imu["gz_dps"] * DEG2RAD)
            accel_mps2 = np.array(
                [accel_g[0] * G0, accel_g[1] * G0, accel_g[2] * G0],
                dtype=float)
            gyro = np.array(gyro_rps, dtype=float)
            dt_att = 0.0 if self._t_prev_state is None \
                else max(0.0, t_now - self._t_prev_state)
            att = self._att.update(accel_g, gyro_rps, dt_att)
            roll, pitch, yaw = att.roll, att.pitch, att.yaw
        else:
            accel_mps2 = np.zeros(3, dtype=float)
            gyro = np.zeros(3, dtype=float)
            roll = pitch = yaw = 0.0

        # --- opportunistic full feedback ---
        did_fb = False
        fb_attempted = False
        fb_valid_ids: list[int] = []
        if want_full_feedback is None:
            want_full_feedback = (t_now - self._last_fb_t) >= self._fb_period
        if want_full_feedback:
            fb_attempted = True
            timing.t_fb, fb_valid_ids, did_fb = self._acquire_feedback()
        timing.did_full_feedback = did_fb

        dt = 0.0 if self._t_prev_state is None else (t_now - self._t_prev_state)
        self._t_prev_state = t_now
        timing.t_total = time.monotonic() - t0
        self.last_timing = timing
        timing_dict = {
            "t_pos": timing.t_pos,
            "t_imu": timing.t_imu,
            "t_fb": timing.t_fb,
            "t_total": timing.t_total,
            "source": source,
        }
        timing_dict.update(self._feedback_timing(
            attempted=fb_attempted, valid_ids=fb_valid_ids,
            complete=did_fb))
        if snapshot_meta:
            timing_dict.update(snapshot_meta)

        return RobotState(
            timestamp=t_now,
            joint_position=q,
            joint_velocity=qd,
            imu_roll=float(roll),
            imu_pitch=float(pitch),
            imu_yaw=float(yaw),
            imu_gyro=gyro,
            imu_accel=accel_mps2,
            commanded_position=self._cmd.copy(),
            servo_load=self._load.copy() if self._have_fb else None,
            servo_current=self._current.copy() if self._have_fb else None,
            servo_temperature=self._temp.copy() if self._have_fb else None,
            bus_ok=bus_ok,
            imu_ok=imu_ok,
            dt=float(dt),
            timing=timing_dict,
        )

    def update_from_snapshot(
            self, snap: dict, *,
            want_full_feedback: bool | None = None,
            source: str = "step_all") -> RobotState | None:
        """Build state from an already-acquired MCU snapshot.

        ``McuFeetechBus.step_all()`` writes 18 goals and returns the same
        snapshot shape as ``read_snapshot()``. Consuming it here avoids a
        second host<->MCU transaction inside high-rate RL stream ticks while
        preserving velocity filtering, attitude estimation, and sparse full
        feedback sampling.
        """
        if not isinstance(snap, dict):
            return None
        pos_deg = snap.get("pos_deg")
        if not isinstance(pos_deg, dict):
            return None
        timing = AcquisitionTiming()
        meta = {
            "snapshot_seq": snap.get("seq"),
            "pos_age_ms": snap.get("pos_age_ms"),
            "imu_age_ms": snap.get("imu_age_ms"),
        }
        return self._state_from_sample(
            pos_deg, snap.get("imu"), t0=time.monotonic(), timing=timing,
            want_full_feedback=want_full_feedback, source=source,
            snapshot_meta=meta)

    def update(self, *, want_full_feedback: bool | None = None) -> RobotState:
        t0 = time.monotonic()
        timing = AcquisitionTiming()

        # --- positions + IMU ---
        # Fast path (stream firmware): ONE host<->MCU round trip returns
        # cached positions + IMU ('S' n=0 snapshot; caches are refreshed
        # by the MCU's free-running acquisition loop at ~150-250 Hz).
        # Legacy path: separate read_all_positions + read_imu
        # transactions, each blocking on the servo bus.
        pos_deg: dict | None = None
        imu = None
        snap = None
        source = "legacy_read"
        snap_meta = None
        read_snap = getattr(self.bus, "read_snapshot", None)
        if read_snap is not None:
            t_a = time.monotonic()
            try:
                snap = read_snap()
            except Exception:
                snap = None
            if snap is not None:
                timing.t_pos = time.monotonic() - t_a
                pos_deg = snap["pos_deg"]
                imu = snap["imu"]
                source = "read_snapshot"
                snap_meta = {
                    "snapshot_seq": snap.get("seq"),
                    "pos_age_ms": snap.get("pos_age_ms"),
                    "imu_age_ms": snap.get("imu_age_ms"),
                }
        if snap is None:
            t_a = time.monotonic()
            pos_deg = self.bus.read_all_positions()
            timing.t_pos = time.monotonic() - t_a
            t_b = time.monotonic()
            try:
                imu = self.bus.read_imu(apply_calib=True)
            except Exception:
                imu = None
            timing.t_imu = time.monotonic() - t_b

        return self._state_from_sample(
            pos_deg, imu, t0=t0, timing=timing,
            want_full_feedback=want_full_feedback, source=source,
            snapshot_meta=snap_meta)
