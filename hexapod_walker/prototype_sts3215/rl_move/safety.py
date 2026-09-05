"""Independent safety filter for Phase-1 balance."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from .body_ik import BodyOffset, N_ACT, N_JOINTS
from .config import cfg_get
from .robot_state import RobotState, DEG2RAD, RAD2DEG

try:
    from motor_setup.feetech_bus import AXIS_LIMITS_DEG
except Exception:  # pragma: no cover
    AXIS_LIMITS_DEG = {
        0: (-35.0, 35.0),
        1: (-80.0, 40.0),
        2: (-20.0, 150.0),
    }


@dataclass
class SafetyStatus:
    ok: bool = True
    terminate: bool = False
    reason: str = ""
    # Which joint (and how hard) for the per-servo trips. Kept OUT of
    # ``reason`` on purpose: run logs / eval tooling match the bare
    # tokens ("over_load", "over_current"), and the 08-11 bench sessions
    # showed the trip is useless for diagnosis without the joint name.
    detail: str = ""
    clipped_action: np.ndarray | None = None
    held: bool = False


_AXIS_NAMES = ("yaw", "hip", "knee")
_JOINT_LIMIT_LO_RAD = np.array(
    [AXIS_LIMITS_DEG[j % 3][0] * DEG2RAD for j in range(N_JOINTS)],
    dtype=float,
)
_JOINT_LIMIT_HI_RAD = np.array(
    [AXIS_LIMITS_DEG[j % 3][1] * DEG2RAD for j in range(N_JOINTS)],
    dtype=float,
)


def _joint_name(j: int) -> str:
    return f"L{j // 3} {_AXIS_NAMES[j % 3]}"


class SafetyLayer:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.max_roll = math.radians(
            float(cfg_get(cfg, "safety", "max_roll_deg", default=15)))
        self.max_pitch = math.radians(
            float(cfg_get(cfg, "safety", "max_pitch_deg", default=15)))
        self.max_dq = math.radians(
            float(cfg_get(cfg, "safety", "max_delta_q_deg", default=2.0)))
        # Entry slew ramp (08-13, takeoff-transient instrumentation —
        # operator ruling "staged gait-entry transition"): the 08-11
        # bench tapes show the walk policy saturates the full
        # max_delta_q slew on ALL 18 joints from tick 0 at ZERO
        # command (a whole-body posture snap; 14/26 tapes cross 5 deg
        # roll before the velocity ramp even starts). When
        # entry_slew_ramp_s > 0, the per-tick rate limit starts at
        # entry_slew_start_deg and ramps linearly to max_delta_q_deg
        # over that many seconds after set_nominal() (episode start /
        # policy engage on hardware), throttling the drop-in snap.
        # Default 0.0 = OFF = bit-exact legacy behavior.
        self.entry_ramp_s = float(
            cfg_get(cfg, "safety", "entry_slew_ramp_s", default=0.0))
        self.entry_start_dq = math.radians(
            float(cfg_get(cfg, "safety", "entry_slew_start_deg",
                          default=0.25)))
        self._entry_ticks = 0
        self.imu_stale_s = float(
            cfg_get(cfg, "safety", "imu_stale_ms", default=100)) / 1000.0
        self.max_temp = float(cfg_get(cfg, "safety", "max_temp_c", default=65))
        self.max_current = float(
            cfg_get(cfg, "safety", "max_current_a", default=2.5))
        # Over-current terminates only when SUSTAINED. STS3215s tolerate
        # short excursions past 2.5 A harmlessly (the cooked knee took
        # minutes at ~7 A); the per-tick effort penalty already punishes
        # every over-current step, and a badly-placed start (frozen feet
        # fighting isometrically) needs a few ticks for the policy to
        # unload before we give up on the episode.
        trip_s = float(cfg_get(cfg, "safety", "over_current_trip_s",
                               default=0.8))
        hz = float(cfg_get(cfg, "control", "hz", default=25))
        self._hz = hz
        self._over_current_trip_ticks = max(1, int(round(trip_s * hz)))
        self._over_current_ticks = 0
        # Over-temp needs consecutive FRESH feedback reads (not control
        # ticks): a corrupted byte on the shared half-duplex bus
        # occasionally reads 70-90 C on a servo that is actually ~33 C
        # (four phantom trips 08-09, plus one more 08-09 night after the
        # first tick-based debounce — temps are cached for ~2.5 control
        # ticks between 10 Hz feedback reads, so ONE bad read satisfied
        # "3 consecutive ticks"). 3 fresh reads = 300 ms of sustained
        # over-temp, which real heat easily provides and a glitch cannot.
        self._over_temp_trip_ticks = 3
        self._over_temp_ticks = 0
        self.max_load = float(cfg_get(cfg, "safety", "max_load_pct", default=90))
        self._incomplete_feedback_trip_ticks = 3
        self._incomplete_feedback_ticks = 0
        self._last_feedback_sample_seq: int | None = None
        self._last_safe = np.zeros(N_JOINTS, dtype=float)
        self._tilt_ref = (0.0, 0.0)
        self._estop = False
        self._t_imu_ok: float | None = None

    def set_nominal(self, q_rad: np.ndarray) -> None:
        self._last_safe = np.asarray(q_rad, dtype=float).reshape(N_JOINTS).copy()
        self._over_current_ticks = 0
        self._over_temp_ticks = 0
        self._incomplete_feedback_ticks = 0
        self._last_feedback_sample_seq = None
        self._entry_ticks = 0
        # Re-read the entry-slew params on every engage/reset so the
        # in-run cfg scheduler (sched.key=safety.entry_slew_start_deg /
        # entry_slew_ramp_s) and staged curricula actually take effect
        # per episode (RISE_WALK_NEXT_48H P2 entry-slew curriculum,
        # 08-13). __init__ caches were per-process constants; with an
        # unchanged cfg this re-read is bit-exact.
        self.entry_ramp_s = float(
            cfg_get(self.cfg, "safety", "entry_slew_ramp_s",
                    default=0.0))
        self.entry_start_dq = math.radians(
            float(cfg_get(self.cfg, "safety", "entry_slew_start_deg",
                          default=0.25)))

    def set_tilt_reference(self, roll: float, pitch: float) -> None:
        """Anchor the tilt trip to the episode's starting attitude.

        The measured tilt can carry a large constant bias (IMU mounted at
        an angle, imperfect calibration, sloped floor). Tipping over is a
        CHANGE in tilt, and a biased IMU still measures change correctly —
        so trip on |tilt - reference|, not on the absolute reading, or the
        bias silently eats the whole safety budget.
        """
        self._tilt_ref = (float(roll), float(pitch))

    def estop(self) -> None:
        self._estop = True

    def clear_estop(self) -> None:
        self._estop = False

    @property
    def estopped(self) -> bool:
        return self._estop

    def validate_action(self, action: Any,
                        n_act: int = N_ACT) -> tuple[np.ndarray | None, str]:
        try:
            a = np.asarray(action, dtype=float).reshape(n_act)
        except Exception:
            return None, "bad_action_shape"
        if not np.all(np.isfinite(a)):
            return None, "action_nan_inf"
        return np.clip(a, -1.0, 1.0), ""

    def check_servo_health(self, state: RobotState) -> SafetyStatus | None:
        """Evaluate health, consuming each physical feedback frame once.

        Partial frames keep their valid joint values safety-relevant while
        their missing IDs are debounced independently.  ``feedback_sample_seq``
        persists across position-only state updates, so a direct runner cannot
        skip a partial frame merely because its final inner substep did not
        itself perform the feedback transaction.
        """
        timing = dict(state.timing or {})
        raw_seq = timing.get("feedback_sample_seq")
        fresh_sample = False
        if raw_seq is not None:
            try:
                seq = int(raw_seq)
            except (TypeError, ValueError):
                seq = None
            if seq is not None and seq != self._last_feedback_sample_seq:
                fresh_sample = True
                self._last_feedback_sample_seq = seq
        elif (timing.get("feedback_sample_fresh")
              or timing.get("full_feedback_attempted")
              or timing.get("full_feedback")):
            # Backward-compatible states without acquisition identity are
            # assumed to represent one new caller-supplied sample.
            fresh_sample = True

        has_validity = ("feedback_valid_ids" in timing
                        or "full_feedback_ids" in timing)
        raw_ids = timing.get(
            "feedback_valid_ids", timing.get("full_feedback_ids", ()))
        valid_ids: list[int] = []
        try:
            valid_ids = sorted({
                int(j) for j in raw_ids if 0 <= int(j) < N_JOINTS})
        except (TypeError, ValueError):
            valid_ids = []
        if not has_validity:
            valid_ids = list(range(N_JOINTS))
        declared_complete = bool(timing.get(
            "feedback_complete", timing.get("full_feedback_complete",
                                                timing.get("full_feedback"))))
        complete = bool(
            declared_complete
            and (not has_validity
                 or valid_ids == list(range(N_JOINTS))))

        def selected(name: str) -> tuple[np.ndarray | None, list[int]]:
            value = getattr(state, name, None)
            if value is None or not valid_ids:
                return None, []
            try:
                arr = np.asarray(value, dtype=float).reshape(N_JOINTS)
            except (TypeError, ValueError):
                return None, []
            ids = [j for j in valid_ids if math.isfinite(float(arr[j]))]
            return arr, ids

        temp, temp_ids = selected("servo_temperature")
        if fresh_sample and temp is not None and temp_ids:
            j = max(temp_ids, key=lambda idx: float(temp[idx]))
            if float(temp[j]) > self.max_temp:
                self._over_temp_ticks += 1
            elif complete:
                self._over_temp_ticks = 0
            if self._over_temp_ticks >= self._over_temp_trip_ticks:
                return SafetyStatus(
                    ok=False, terminate=True, reason="over_temp",
                    detail=f"{_joint_name(j)} {float(temp[j]):.1f}C",
                    held=True)

        current, current_ids = selected("servo_current")
        if current is not None and current_ids:
            cur = np.abs(current)
            j = max(current_ids, key=lambda idx: float(cur[idx]))
            if float(cur[j]) > self.max_current:
                self._over_current_ticks += 1
                if self._over_current_ticks >= self._over_current_trip_ticks:
                    return SafetyStatus(
                        ok=False, terminate=True, reason="over_current",
                        detail=f"{_joint_name(j)} {float(cur[j]):.2f}A",
                        held=True)
            elif complete:
                self._over_current_ticks = 0

        load, load_ids = selected("servo_load")
        if load is not None and load_ids:
            j = max(load_ids, key=lambda idx: float(load[idx]))
            if float(load[j]) > self.max_load:
                return SafetyStatus(
                    ok=False, terminate=True, reason="over_load",
                    detail=f"{_joint_name(j)} {float(load[j]):.0f}%",
                    held=True)

        if fresh_sample:
            if complete:
                self._incomplete_feedback_ticks = 0
            else:
                self._incomplete_feedback_ticks += 1
                if (self._incomplete_feedback_ticks
                        >= self._incomplete_feedback_trip_ticks):
                    missing = [j for j in range(N_JOINTS)
                               if j not in valid_ids]
                    return SafetyStatus(
                        ok=False, terminate=True,
                        reason="incomplete_feedback",
                        detail=(f"{len(valid_ids)}/{N_JOINTS} valid; "
                                f"missing {missing}"),
                        held=True)
        return None

    def filter(self, proposed_q: np.ndarray, state: RobotState,
               *, ik_ok: bool = True, ik_reason: str = "",
               action: np.ndarray | None = None) -> tuple[np.ndarray, SafetyStatus]:
        status = SafetyStatus(ok=True, clipped_action=action)

        if self._estop:
            status.ok = False
            status.terminate = True
            status.reason = "estop"
            status.held = True
            return self._last_safe.copy(), status

        if not ik_ok:
            # Unreachable target ≠ emergency: HOLD the last safe pose and
            # keep the episode alive. With the curl channel many action
            # combinations are legitimately unreachable (e.g. body up
            # while legs are uncurled); terminating would kill nearly
            # every exploratory rollout of the rise task. The gated task
            # reward already makes a held (non-tracking) pose unrewarding.
            status.ok = False
            status.reason = ik_reason or "ik_fail"
            status.held = True
            return self._last_safe.copy(), status

        if not state.bus_ok:
            status.ok = False
            status.terminate = True
            status.reason = "bus_fail"
            status.held = True
            return self._last_safe.copy(), status

        if state.imu_ok:
            self._t_imu_ok = state.timestamp
        else:
            if self._t_imu_ok is None or (
                    state.timestamp - self._t_imu_ok) > self.imu_stale_s:
                status.ok = False
                status.terminate = True
                status.reason = "imu_stale"
                status.held = True
                return self._last_safe.copy(), status

        if abs(state.imu_roll - self._tilt_ref[0]) > self.max_roll:
            status.ok = False
            status.terminate = True
            status.reason = "tilt_roll"
            status.held = True
            return self._last_safe.copy(), status
        if abs(state.imu_pitch - self._tilt_ref[1]) > self.max_pitch:
            status.ok = False
            status.terminate = True
            status.reason = "tilt_pitch"
            status.held = True
            return self._last_safe.copy(), status

        health_status = self.check_servo_health(state)
        if health_status is not None:
            health_status.clipped_action = action
            return self._last_safe.copy(), health_status

        q = np.asarray(proposed_q, dtype=float).reshape(N_JOINTS).copy()
        if not np.all(np.isfinite(q)):
            status.ok = False
            status.terminate = True
            status.reason = "q_nan_inf"
            status.held = True
            return self._last_safe.copy(), status

        # Per-step rate limit vs last safe command. With the entry
        # slew ramp active (entry_slew_ramp_s > 0) the limit starts at
        # entry_start_dq right after set_nominal() and ramps linearly
        # to max_dq; off (0.0, the default) this is exactly max_dq.
        max_dq = self.max_dq
        if self.entry_ramp_s > 0.0:
            t = self._entry_ticks / self._hz
            if t < self.entry_ramp_s:
                f = t / self.entry_ramp_s
                max_dq = min(self.max_dq, self.entry_start_dq
                             + f * (self.max_dq - self.entry_start_dq))
        self._entry_ticks += 1
        dq = q - self._last_safe
        dq = np.clip(dq, -max_dq, max_dq)
        q = self._last_safe + dq

        # Joint limits (deg in AXIS_LIMITS).
        q = np.clip(q, _JOINT_LIMIT_LO_RAD, _JOINT_LIMIT_HI_RAD)

        self._last_safe = q.copy()
        return q, status


def action_to_body_offset(action: np.ndarray, cfg: dict) -> BodyOffset:
    from .body_ik import body_offset_from_action
    return body_offset_from_action(
        action,
        max_roll=math.radians(float(cfg_get(cfg, "actions", "max_roll_deg", default=3))),
        max_pitch=math.radians(float(cfg_get(cfg, "actions", "max_pitch_deg", default=3))),
        max_h=float(cfg_get(cfg, "actions", "max_height_mm", default=5)) * 0.001,
        max_x=float(cfg_get(cfg, "actions", "max_x_mm", default=5)) * 0.001,
        max_y=float(cfg_get(cfg, "actions", "max_y_mm", default=5)) * 0.001,
    )
