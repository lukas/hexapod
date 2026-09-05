"""Opt-in CPU replay of the deployed policy/bus/snapshot contract.

The policy and SafetyLayer retain their trained clock. Servo writes coalesce
to the latest safe target; sensor snapshots are held between acquisitions.
Velocity and attitude use the hardware filters, once per acquired frame.
The current estimator remains the simulator's UNCALIBRATED torque proxy.

``transport.enabled=1`` selects this mode. Defaults: write_hz=50,
snapshot_hz=10, velocity_alpha=.3, attitude_alpha=.98. Optional
``write_intervals_ms`` / ``snapshot_intervals_ms`` are repeating measured
inter-arrival traces; ``*_jitter_ms`` adds seeded uniform +/- jitter.
Events are sampled on the policy grid (at most one policy tick late), never
interpolated or replayed in catch-up bursts. This models sample/hold and
coalescing, not asynchronous sub-tick wire latency or packet corruption.
"""
from __future__ import annotations

from dataclasses import replace
import math

import numpy as np

from rl_move.attitude import ComplementaryAttitude, G0
from rl_move.robot_state import JointVelocityFilter, RobotState


class Cadence:
    """Deadline cadence with an independent RNG and no catch-up bursts."""

    def __init__(self, hz: float, *, intervals_ms=(), jitter_ms=0.0,
                 seed=0):
        self.hz = float(hz)
        if not math.isfinite(self.hz) or self.hz <= 0:
            raise ValueError("transport cadence hz must be positive and finite")
        self.intervals = tuple(float(v) / 1000 for v in intervals_ms)
        self.jitter = float(jitter_ms) / 1000
        durations = self.intervals or (1 / self.hz,)
        if (any(not math.isfinite(v) or v <= 0 for v in durations)
                or not math.isfinite(self.jitter)
                or self.jitter < 0 or self.jitter >= min(durations)):
            raise ValueError("transport intervals must exceed nonnegative jitter")
        self.seed = int(seed)
        self.reset()

    def reset(self):
        self.rng = np.random.default_rng(self.seed)
        self.next_t = None
        self.index = 0
        self.events = 0
        self.skipped = 0
        self.max_late_s = 0.0

    def _interval(self):
        base = (self.intervals[self.index % len(self.intervals)]
                if self.intervals else 1 / self.hz)
        self.index += 1
        return base + (self.rng.uniform(-self.jitter, self.jitter)
                       if self.jitter else 0.0)

    def due(self, now: float) -> bool:
        now = float(now)
        if not math.isfinite(now):
            raise ValueError("transport timestamp must be finite")
        if self.next_t is None:
            self.next_t = now
        if now + 1e-9 < self.next_t:
            return False
        self.max_late_s = max(self.max_late_s, now - self.next_t)
        self.events += 1
        self.next_t += self._interval()
        while self.next_t <= now + 1e-9:
            self.next_t += self._interval()
            self.skipped += 1
        return True


class DeployedTransport:
    def __init__(self, cfg: dict, policy_hz: float):
        allowed = {"enabled", "write_hz", "snapshot_hz", "seed",
                   "write_intervals_ms", "snapshot_intervals_ms",
                   "write_jitter_ms", "snapshot_jitter_ms", "velocity_alpha",
                   "attitude_alpha", "velocity_max_jump_rad"}
        if set(cfg) - allowed:
            raise ValueError(f"Unknown transport keys: {sorted(set(cfg) - allowed)}")
        self.cfg = dict(cfg)
        self.policy_hz = float(policy_hz)
        if not math.isfinite(self.policy_hz) or self.policy_hz <= 0:
            raise ValueError("transport policy_hz must be positive and finite")
        seed = int(cfg.get("seed", 0))
        self.write = self._cadence("write", 50.0, seed)
        self.snapshot = self._cadence("snapshot", 10.0, seed + 1)
        for cadence in (self.write, self.snapshot):
            if cadence.hz > self.policy_hz:
                raise ValueError("CPU transport cadence cannot exceed policy_hz")
            if cadence.intervals and min(cadence.intervals) < 1 / self.policy_hz:
                raise ValueError("transport trace interval is below one policy tick")
        velocity_alpha = float(cfg.get("velocity_alpha", .3))
        attitude_alpha = float(cfg.get("attitude_alpha", .98))
        if not (0 <= velocity_alpha <= 1 and 0 <= attitude_alpha <= 1):
            raise ValueError("transport filter alpha must be within [0, 1]")
        max_jump = float(cfg.get("velocity_max_jump_rad", .5))
        if not math.isfinite(max_jump) or max_jump <= 0:
            raise ValueError("transport velocity_max_jump_rad must be positive")
        self.velocity = JointVelocityFilter(
            alpha=velocity_alpha, max_jump_rad=max_jump)
        self.attitude = ComplementaryAttitude(alpha=attitude_alpha)
        self.reset()

    @classmethod
    def from_cfg(cls, cfg: dict, policy_hz: float):
        section = cfg.get("transport") or {}
        if not bool(section.get("enabled", False)):
            return None
        return cls(section, policy_hz)

    def _cadence(self, name, default, seed):
        return Cadence(self.cfg.get(name + "_hz", default),
                       intervals_ms=self.cfg.get(name + "_intervals_ms", ()),
                       jitter_ms=self.cfg.get(name + "_jitter_ms", 0), seed=seed)

    def reset(self):
        self.write.reset()
        self.snapshot.reset()
        self.velocity.reset()
        self.attitude = ComplementaryAttitude(alpha=self.attitude.alpha)
        self.state: RobotState | None = None
        self.reads = 0
        self.max_snapshot_age_s = 0.0

    def acquire(self, raw: RobotState, *, accel_tilt=None) -> RobotState:
        """Consume a raw IMU/encoder frame only when acquisition is due.

        ``raw.joint_velocity`` is deliberately never used. ``accel_tilt``
        carries the sim's existing DR tilt corruption into the hardware
        filter without re-filtering an already filtered attitude.
        """
        now = float(raw.timestamp)
        self.reads += 1
        fresh = self.snapshot.due(now)
        if fresh:
            dt = 0.0 if self.state is None else now - self.state.timestamp
            accel = np.asarray(raw.imu_accel, dtype=float).copy()
            if accel_tilt is not None:
                roll, pitch = accel_tilt
                norm = float(np.linalg.norm(accel))
                accel = norm * np.array([
                    -math.sin(pitch), math.sin(roll) * math.cos(pitch),
                    math.cos(roll) * math.cos(pitch)])
            att = self.attitude.update(tuple(accel / G0),
                                       tuple(raw.imu_gyro), dt)
            self.state = replace(
                raw, joint_position=raw.joint_position.copy(),
                joint_velocity=self.velocity.update(raw.joint_position, now),
                imu_roll=att.roll, imu_pitch=att.pitch, imu_yaw=att.yaw,
                imu_accel=accel, imu_gyro=raw.imu_gyro.copy(), dt=dt,
                commanded_position=raw.commanded_position.copy(),
                servo_current=(None if raw.servo_current is None
                               else raw.servo_current.copy()))
        assert self.state is not None
        age = max(0.0, now - self.state.timestamp)
        self.max_snapshot_age_s = max(self.max_snapshot_age_s, age)
        # Fresh-frame flags are per consumption, never left true on a held
        # frame (hardware debounces health using distinct acquisitions).
        return replace(self.state, timing={
            **self.state.timing, "source": "sim_deployed_transport",
            "snapshot_fresh": fresh, "snapshot_sequence": self.snapshot.events,
            "snapshot_age_s": age, "full_feedback": fresh,
            "full_feedback_complete": fresh,
            "feedback_sample_seq": self.snapshot.events,
            "feedback_sample_fresh": fresh, "feedback_complete": True,
            "feedback_valid_ids": list(range(18)),
        })

    @staticmethod
    def safety_state(state):
        """Match the async hardware runner's once-per-frame health mask."""
        if state.timing.get("snapshot_fresh"):
            return state
        return replace(state, servo_current=None, servo_load=None,
                       servo_temperature=None)

    def summary(self):
        return {
            "enabled": True, "backend": "cpu", "policy_hz": self.policy_hz,
            "write_hz": self.write.hz, "snapshot_hz": self.snapshot.hz,
            "velocity_alpha": self.velocity.alpha,
            "attitude_alpha": self.attitude.alpha,
            "writes": self.write.events, "snapshots": self.snapshot.events,
            "sensor_reads": self.reads,
            "max_snapshot_age_s": self.max_snapshot_age_s,
            "max_write_grid_delay_s": self.write.max_late_s,
            "max_snapshot_grid_delay_s": self.snapshot.max_late_s,
            "skipped_write_deadlines": self.write.skipped,
            "skipped_snapshot_deadlines": self.snapshot.skipped,
            "config": self.cfg,
        }
