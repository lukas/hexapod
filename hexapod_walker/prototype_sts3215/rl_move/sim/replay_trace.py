"""Open-loop hardware-trace replay: sim-to-real divergence finder.

Feeds a logged on-robot episode CSV's recorded command stream
(``cmd*_deg`` — the post-safety targets the servos actually received)
through ServoProfile + free-base MuJoCo, starting from the trace's own
measured initial pose, with NO policy in the loop. Then overlays
hardware vs sim roll(t) / roll-rate(t) / q(t) and reports the first
tick where the trajectories materially diverge, plus per-foot contact
/ slip diagnostics around that tick.

Why (RL_REVIEW_BUNDLE 08-11, "we now have the data to model the
transient"): the real robot develops lateral roll during load
transitions (belly-curl rise: 5/5 deterministic tilt_roll trips at
tick ~227; walk takeoff: 13-27 deg first-second transients) that the
sim does not produce. This experiment discriminates the candidate
causes:

- joint positions diverge first        -> actuator/load model
- joints agree, contacts/slip diverge  -> contact/pinning
- both plausible, roll accel differs   -> inertia/CoM/mass distribution

Run (from prototype_sts3215/, repo .venv):
    uv run python -m rl_move.sim.replay_trace \
        --csv rl_move/hardware_traces/stand_fail_20260811/*.csv \
        --servo-params both --plot
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


from rl_move.attitude import ComplementaryAttitude
from .servo_model import (
    ServoProfile, SimServoParams, apply_params_to_model, build_model,
    joint_qpos_addrs, joint_qvel_addrs, lowest_collidable_z,
    position_actuator_ids, resolve_model_source,
)
from .leg_mount_flex import (
    addresses as leg_mount_flex_addresses,
    from_cfg as leg_mount_flex_from_cfg,
)
from .joint_series_flex import (
    ACTIVE_JOINT_NAMES as SERIES_ACTIVE_JOINT_NAMES,
    addresses as joint_series_flex_addresses,
    from_cfg as joint_series_flex_from_cfg,
)
from hexapod_core.joint_frame import (
    mujoco_rel_rad_to_robot_abs_rad, robot_abs_rad_to_mujoco_rel_rad,
)

DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi

# Deployed RL runner write profile (rl_policy.py bus defaults).
RL_SPEED_DEG_S = 400.0 * 360.0 / 4096.0          # 35.2
RL_ACC_UNITS = 20.0

LOADED_MODEL_PATH = Path(__file__).resolve().parent / "sim_model_loaded.json"

# Divergence thresholds: "material" = sustained, not one noisy tick.
ROLL_DIV_DEG = 2.0        # |sim_roll_rel - hw_roll_rel|
Q_DIV_DEG = 3.0           # per-joint |sim_q - hw_q| (moving joints)
SUSTAIN_TICKS = 5         # must hold this many consecutive ticks
MOVING_PTP_DEG = 4.0      # a joint "moves" if its hw range exceeds this
CONTACT_N = 0.5           # touch-sensor force threshold


# ---------------------------------------------------------------------------
# Trace loading
# ---------------------------------------------------------------------------

def _phase_window(rows: list[dict], phase: str) -> list[dict]:
    """First-to-last active-phase window, including brief interruptions.

    The hardware logger changes ``walk`` to ``hold`` during short joystick
    or safety interruptions.  Those rows contain real servo targets and real
    elapsed time.  Dropping them concatenates unrelated commands; selecting
    only the longest walk bout discards much of runs such as PS200.  Exclude
    only the leading setup and final post-run hold/tail.
    """
    active = [i for i, row in enumerate(rows) if row.get("phase") == phase]
    return rows[active[0]:active[-1] + 1] if active else []


def _trace_time(rows: list[dict]) -> tuple[np.ndarray, str]:
    """Prefer the logger's monotonic clock and return time from segment 0."""
    for key in ("mono_s", "t_s"):
        try:
            values = np.asarray([float(row[key]) for row in rows], dtype=float)
        except (KeyError, TypeError, ValueError):
            continue
        if (np.all(np.isfinite(values)) and len(values) > 1
                and np.all(np.diff(values) > 0.0)):
            return values - values[0], key
    raise SystemExit("trace has no strictly increasing mono_s or t_s clock")


def load_trace(csv_path: Path, *, phase: str = "auto") -> dict:
    """Load one contiguous motion bout from an on-robot episode CSV.

    Old traces label active control as ``run``; the current robot logger uses
    ``walk``.  ``phase='auto'`` chooses whichever has the most active rows,
    while preserving brief hold rows between its first and last active tick.
    Timing comes from ``mono_s`` where available so a
    50/100 Hz recording is replayed at its actual rate rather than at the
    historical 25 Hz assumption.
    """
    with csv_path.open(newline="") as stream:
        all_rows = list(csv.DictReader(stream))
    if phase not in {"auto", "run", "walk"}:
        raise ValueError("phase must be 'auto', 'run', or 'walk'")
    candidates = ("run", "walk") if phase == "auto" else (phase,)
    selected_phase, rows = max(
        ((candidate, _phase_window(all_rows, candidate))
         for candidate in candidates),
        key=lambda item: sum(row.get("phase") == item[0]
                             for row in item[1]),
    )
    active_count = sum(row.get("phase") == selected_phase for row in rows)
    if active_count < 25:
        counts = {candidate: sum(r.get("phase") == candidate
                                 for r in all_rows)
                  for candidate in candidates}
        raise SystemExit(
            f"{csv_path.name}: only {active_count} {selected_phase} "
            f"ticks (phase totals: {counts})")
    trace_t, time_source = _trace_time(rows)
    tr = {
        "name": csv_path.name,
        "phase": selected_phase,
        "active_phase_mask": np.array(
            [row.get("phase") == selected_phase for row in rows]),
        "interrupted_ticks": len(rows) - active_count,
        "time_source": time_source,
        "t": trace_t,
        "roll": np.array([float(r["roll_deg"]) for r in rows]),
        "pitch": np.array([float(r["pitch_deg"]) for r in rows]),
        "gyro_x": np.array([float(r["gyro_x_dps"]) for r in rows]),
        "gyro_y": np.array([float(r["gyro_y_dps"]) for r in rows]),
        "q": np.array([[float(r[f"q{j}_deg"]) for j in range(18)]
                       for r in rows]),
        "cmd": np.array([[float(r[f"cmd{j}_deg"]) for j in range(18)]
                         for r in rows]),
    }
    # Keep the robot's own servo evidence beside the pose trace.  Older CSVs
    # lack some fields; NaN means unavailable, never zero current/latency.
    def optional_vector(prefix: str, suffix: str = "") -> np.ndarray:
        def number(row: dict, key: str) -> float:
            try:
                return float(row[key])
            except (KeyError, TypeError, ValueError):
                return float("nan")
        return np.array([[number(r, f"{prefix}{j}{suffix}")
                          for j in range(18)] for r in rows])

    def optional_scalar(name: str) -> np.ndarray:
        out = []
        for row in rows:
            try:
                out.append(float(row[name]))
            except (KeyError, TypeError, ValueError):
                out.append(float("nan"))
        return np.asarray(out)

    tr["current_a"] = optional_vector("cur", "_a")
    tr["max_current_a"] = optional_scalar("max_cur_a")
    tr["logger_lag_ms"] = optional_scalar("lag_ms")
    tr["period_ms"] = optional_scalar("period_ms")
    tr["accel_g"] = np.column_stack([
        optional_scalar("ax_g"), optional_scalar("ay_g"),
        optional_scalar("az_g")])
    summary = {}
    sp = csv_path.with_name(csv_path.stem + "_summary.json")
    if sp.exists():
        summary = json.loads(sp.read_text())
    tr["summary"] = summary
    ref = (summary.get("params", {}).get("tilt_ref_deg")
           or [tr["roll"][0], tr["pitch"][0]])
    tr["ref_roll"], tr["ref_pitch"] = float(ref[0]), float(ref[1])
    return tr


# ---------------------------------------------------------------------------
# Free-base replay
# ---------------------------------------------------------------------------

def _replay_substeps(t_s: np.ndarray, physics_dt_s: float,
                     max_tick_s: float = 0.12) -> np.ndarray:
    """Physics steps between recorded samples, without clock drift.

    For ``N`` timestamped rows there are ``N - 1`` real intervals.  In
    particular, do not invent a median-length interval after the last row:
    doing so advances the simulated pose beyond the last hardware sample.
    """
    t_s = np.asarray(t_s, dtype=float)
    if t_s.ndim != 1 or t_s.size == 0:
        raise ValueError("trace time must be a non-empty 1-D array")
    if not (np.isfinite(physics_dt_s) and physics_dt_s > 0.0):
        raise ValueError("physics_dt_s must be finite and > 0")
    diffs = np.diff(t_s)
    if not np.all(np.isfinite(t_s)) or np.any(diffs <= 0.0):
        raise ValueError("trace time must be finite and strictly increasing")
    intervals = np.clip(diffs, physics_dt_s, max_tick_s)
    result = np.empty(diffs.size, dtype=int)
    elapsed_target_s = 0.0
    elapsed_steps = 0
    for i, interval in enumerate(intervals):
        elapsed_target_s += float(interval)
        target_steps = int(round(elapsed_target_s / physics_dt_s))
        result[i] = max(1, target_steps - elapsed_steps)
        elapsed_steps += int(result[i])
    return result


class _ReplaySim:
    """Free-base sim placed at a recorded pose; mirrors the training
    env's model prep (soften_contacts) and fit_loaded_actuator's
    placement recipe so the replay sees the same plant."""

    def __init__(self, params: SimServoParams, *, mu: float = 0.0,
                 com_shift_mm: tuple[float, float, float] = (0., 0., 0.),
                 leg_chassis: bool = False, leg_mount_flex=None,
                 joint_series_flex=None,
                 model_source: str | None = None,
                 imu_pos_mm: tuple[float, float, float] = (0., 0., 0.)):
        import mujoco
        from .sim_env import set_foot_ground_friction, soften_contacts
        self._mujoco = mujoco
        # leg_chassis: env.leg_chassis_collision axis (SIM.md gap 4) —
        # validate the belly knife-edge mechanism against the recorded
        # tapes. Compile-time XML rewrite, hence the build_model kwarg.
        self._model_source = (resolve_model_source(None)
                              if model_source is None else model_source)
        self.model = build_model(fixed_base=False, flat_terrain=True,
                                 leg_chassis_collision=leg_chassis,
                                 source=self._model_source,
                                 leg_mount_flex=leg_mount_flex,
                                 joint_series_flex=joint_series_flex)
        soften_contacts(self.model)
        if mu > 0.0:
            set_foot_ground_friction(self.model, mu)
        apply_params_to_model(self.model, params)
        self.params = params
        self.data = mujoco.MjData(self.model)
        self._qadr = joint_qpos_addrs(self.model)
        self._vadr = joint_qvel_addrs(self.model)
        self._pos_act = position_actuator_ids(self.model)
        self._flex_addrs = leg_mount_flex_addresses(
            self.model, required=False)
        self._series_flex_addrs = joint_series_flex_addresses(
            self.model, expected=joint_series_flex, required=False)
        if ((joint_series_flex is None)
                != (self._series_flex_addrs is None)):
            raise ValueError(
                "replay model joint-series-flex topology does not match cfg")
        self._series_flex_slots = (
            () if self._series_flex_addrs is None else tuple(
                SERIES_ACTIVE_JOINT_NAMES.index(name)
                for name in self._series_flex_addrs.joint_names))
        self._chassis_bid = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_BODY, "chassis")
        if any(abs(c) > 1e-9 for c in com_shift_mm):
            self.model.body_ipos[self._chassis_bid] += (
                np.asarray(com_shift_mm) * 1e-3)
        gid = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_SENSOR, "chassis_gyro")
        self._gyro_adr = self.model.sensor_adr[gid] if gid >= 0 else -1
        self._imu_pos_m = np.asarray(imu_pos_mm, dtype=float) * 1e-3
        if self._imu_pos_m.shape != (3,) or not np.all(
                np.isfinite(self._imu_pos_m)):
            raise ValueError("imu_pos_mm must contain three finite values")
        self._imu_prev_v: np.ndarray | None = None
        self._imu_f_accum = np.zeros(3)
        self._imu_f_n = 0
        self._gyro_accum = np.zeros(3)
        self._gyro_n = 0
        self._attitude = ComplementaryAttitude(alpha=0.98)
        self._pad_bids = [mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_BODY, f"L{i}_pad")
            for i in range(6)]
        self._touch_adr = []
        for i in range(6):
            sid = mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_SENSOR, f"L{i}_foot_t")
            self._touch_adr.append(
                self.model.sensor_adr[sid] if sid >= 0 else -1)

    def place(self, q_rad: np.ndarray) -> None:
        """Place a recorded robot-absolute pose in the private model."""
        import mujoco_prototype as MP
        from rl_move.body_ik import fk_all_feet
        mujoco = self._mujoco
        feet = fk_all_feet(q_rad)
        foot_drop = float(np.min(feet[:, 2]))
        base_z = MP.YAW_OUTPUT_HEIGHT - foot_drop + MP.FOOT_R + 0.002
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:3] = (0.0, 0.0, base_z)
        self.data.qpos[3:7] = (1.0, 0.0, 0.0, 0.0)
        q_model = robot_abs_rad_to_mujoco_rel_rad(q_rad)
        self.data.qpos[self._qadr] = q_model
        self.data.qvel[:] = 0.0
        self.data.ctrl[:] = 0.0
        self.data.ctrl[self._pos_act] = q_model
        mujoco.mj_forward(self.model, self.data)
        if self._model_source != "primitive":
            # Match SimHexapodBalanceEnv._place_at_plant.  The legacy FK
            # estimate lands the corrected mesh family about 60 mm high;
            # letting it free-fall during replay invents a tick-zero impact.
            low = lowest_collidable_z(self.model, self.data)
            self.data.qpos[2] += 0.002 - low
            mujoco.mj_forward(self.model, self.data)
        for _ in range(40):
            worst = 0.0
            for ci in range(self.data.ncon):
                worst = min(worst, float(self.data.contact[ci].dist))
            if worst > -1e-4:
                break
            self.data.qpos[2] += -worst + 0.001
            mujoco.mj_forward(self.model, self.data)

    def roll_pitch(self) -> tuple[float, float]:
        """Chassis attitude in the IMU convention (roll=atan2(ay,az))."""
        R = np.asarray(self.data.xmat[self._chassis_bid],
                       dtype=float).reshape(3, 3)
        f = R.T @ np.array([0.0, 0.0, 9.80665])
        return (math.atan2(f[1], f[2]),
                math.atan2(-f[0], math.hypot(f[1], f[2])))

    def gyro_dps(self) -> np.ndarray:
        if self._gyro_adr >= 0:
            return (np.asarray(
                self.data.sensordata[self._gyro_adr:self._gyro_adr + 3])
                * RAD2DEG)
        return np.asarray(self.data.qvel[3:6]) * RAD2DEG

    def _point_velocity(self) -> np.ndarray:
        """World velocity at the configured chassis-mounted IMU point."""
        velocity = np.zeros(6)
        self._mujoco.mj_objectVelocity(
            self.model, self.data, self._mujoco.mjtObj.mjOBJ_BODY,
            self._chassis_bid, velocity, 0)
        rotation = np.asarray(
            self.data.xmat[self._chassis_bid], dtype=float).reshape(3, 3)
        return velocity[3:] + np.cross(
            velocity[:3], rotation @ self._imu_pos_m)

    def _reset_imu_estimator(self) -> tuple[float, float]:
        """Seed the same complementary estimator used by the robot runner."""
        rotation = np.asarray(
            self.data.xmat[self._chassis_bid], dtype=float).reshape(3, 3)
        specific_force = rotation.T @ -np.asarray(
            self.model.opt.gravity, dtype=float)
        gyro = self.gyro_dps() / RAD2DEG
        self._attitude = ComplementaryAttitude(alpha=0.98)
        estimate = self._attitude.update(
            tuple(specific_force / 9.80665), tuple(gyro), 0.0)
        self._imu_prev_v = self._point_velocity()
        self._imu_f_accum[:] = 0.0
        self._imu_f_n = 0
        self._gyro_accum[:] = 0.0
        self._gyro_n = 0
        return estimate.roll, estimate.pitch

    def _step(self) -> None:
        """Advance physics and accumulate IMU-rate evidence for one step."""
        self._mujoco.mj_step(self.model, self.data)
        velocity = self._point_velocity()
        if self._imu_prev_v is not None:
            acceleration = (
                velocity - self._imu_prev_v) / self.model.opt.timestep
            self._imu_f_accum += acceleration - self.model.opt.gravity
            self._imu_f_n += 1
        self._imu_prev_v = velocity
        if self._gyro_adr >= 0:
            self._gyro_accum += np.asarray(
                self.data.sensordata[self._gyro_adr:self._gyro_adr + 3],
                dtype=float)
        else:
            self._gyro_accum += np.asarray(self.data.qvel[3:6], dtype=float)
        self._gyro_n += 1

    def _sample_imu_estimator(self, elapsed_s: float) -> tuple[float, float]:
        """Consume one hardware-rate sample from accumulated specific force."""
        rotation = np.asarray(
            self.data.xmat[self._chassis_bid], dtype=float).reshape(3, 3)
        if self._imu_f_n:
            force_world = self._imu_f_accum / self._imu_f_n
        else:
            force_world = -np.asarray(self.model.opt.gravity, dtype=float)
        force_body = rotation.T @ force_world
        gyro = (self._gyro_accum / self._gyro_n if self._gyro_n
                else self.gyro_dps() / RAD2DEG)
        estimate = self._attitude.update(
            tuple(force_body / 9.80665), tuple(gyro), float(elapsed_s))
        self._imu_f_accum[:] = 0.0
        self._imu_f_n = 0
        self._gyro_accum[:] = 0.0
        self._gyro_n = 0
        return estimate.roll, estimate.pitch

    def foot_state(self) -> tuple[np.ndarray, np.ndarray]:
        """(contact force per foot, pad world xyz per foot)."""
        f = np.array([
            float(self.data.sensordata[a]) if a >= 0 else 0.0
            for a in self._touch_adr])
        xyz = np.array([self.data.xpos[b] if b >= 0 else np.zeros(3)
                        for b in self._pad_bids])
        return f, xyz

    def replay(self, tr: dict, *, settle_s: float = 0.4,
               speed_deg_s: float = RL_SPEED_DEG_S,
               acc_units: float = RL_ACC_UNITS,
               fold_roll_deg: float = 0.0) -> dict:
        """Feed the recorded cmd stream; sample sim state per tick.

        ``fold_roll_deg``: persistent one-side fold bias added to the
        physical command, the exact ``sim_env._rise_rock_offset``
        mapping (target body roll / TIP_ROLL_PER_FOLD -> hip/knee
        fold on the side the roll leans toward). Used to CALIBRATE
        the rise-rock DR dose against the recorded failure.
        """
        mujoco = self._mujoco
        fold_dq = np.zeros(18)
        if abs(fold_roll_deg) > 1e-9:
            from .sim_env import SimHexapodBalanceEnv
            fold = (abs(fold_roll_deg)
                    / SimHexapodBalanceEnv.TIP_ROLL_PER_FOLD * DEG2RAD)
            legs = (3, 4, 5) if fold_roll_deg > 0 else (0, 1, 2)
            for leg in legs:
                fold_dq[3 * leg + 1] -= fold
                fold_dq[3 * leg + 2] += 0.5 * fold
        q0 = tr["q"][0] * DEG2RAD
        self.place(q0)
        dt = self.model.opt.timestep
        q0_model = robot_abs_rad_to_mujoco_rel_rad(q0)
        for _ in range(int(settle_s / dt)):
            # q0 is robot-absolute, while MuJoCo's knee coordinate is
            # relative to the femur.  Keep the initial settle on the same
            # explicit joint-frame boundary as placement and tick commands.
            self.data.ctrl[self._pos_act] = q0_model
            mujoco.mj_step(self.model, self.data)
        roll0, pitch0 = self.roll_pitch()
        imu_roll0, imu_pitch0 = self._reset_imu_estimator()

        profile = ServoProfile(self.params,
                               self.data.qpos[self._qadr].copy())
        cmd = tr["cmd"] * DEG2RAD + fold_dq
        t_hw = tr["t"]
        out = {k: [] for k in ("roll", "pitch", "imu_roll", "imu_pitch",
                               "gyro_x", "gyro_y", "q",
                               "base_xyz",
                               "flex_deg",
                               "series_flex_deg",
                               "tau_nm", "current_proxy_a",
                               "foot_f", "foot_xyz")}
        substeps = _replay_substeps(t_hw, dt)

        def record_sample(elapsed_s: float) -> None:
            r, p = self.roll_pitch()
            ir, ip = self._sample_imu_estimator(elapsed_s)
            g = self.gyro_dps()
            f, xyz = self.foot_state()
            out["roll"].append(r * RAD2DEG)
            out["pitch"].append(p * RAD2DEG)
            out["imu_roll"].append(ir * RAD2DEG)
            out["imu_pitch"].append(ip * RAD2DEG)
            out["gyro_x"].append(float(g[0]))
            out["gyro_y"].append(float(g[1]))
            out["q"].append(mujoco_rel_rad_to_robot_abs_rad(
                self.data.qpos[self._qadr]) * RAD2DEG)
            out["base_xyz"].append(self.data.qpos[:3].copy())
            out["flex_deg"].append(
                np.zeros(6) if self._flex_addrs is None else
                np.degrees(self.data.qpos[
                    np.asarray(self._flex_addrs.qpos_addrs, dtype=int)]))
            series_deg = np.zeros(18)
            if self._series_flex_addrs is not None:
                angles = np.degrees(self.data.qpos[np.asarray(
                    self._series_flex_addrs.flex_qpos_addrs, dtype=int)])
                series_deg[np.asarray(
                    self._series_flex_slots, dtype=int)] = angles
            out["series_flex_deg"].append(series_deg)
            tau = np.asarray(self.data.qfrc_actuator[self._vadr], dtype=float)
            out["tau_nm"].append(tau.copy())
            # Deliberately labelled a proxy: the 1.2 A/Nm conversion is not
            # yet calibrated.  Hardware cur*_a remains the identification
            # target rather than being silently equated to this estimate.
            out["current_proxy_a"].append(
                np.minimum(np.abs(tau) * 1.2, 3.0))
            out["foot_f"].append(f)
            out["foot_xyz"].append(xyz)

        # CSV row k records feedback after that tick's servo transaction.
        # Treat its measured pose as the state at t[k], hold cmd[k] across
        # [t[k], t[k+1]], and compare the resulting state to row k+1.  The
        # old order advanced cmd[k] first and compared that future state to
        # row k, creating a one-tick phase lead and an extra tail interval.
        record_sample(0.0)
        for k, per in enumerate(substeps):
            profile.command(robot_abs_rad_to_mujoco_rel_rad(cmd[k]),
                            speed_deg_s=speed_deg_s,
                            acc_units=acc_units)
            # Honor the recorded inter-tick duration (loop overruns).
            # A 100 Hz trace legitimately has 10 ms ticks.  The old 20 ms
            # lower clamp replayed those policies at half speed.
            for _ in range(int(per)):
                self.data.ctrl[self._pos_act] = profile.tick(dt)
                self._step()
            record_sample(float(per) * dt)
        res = {k: np.asarray(v) for k, v in out.items()}
        res["ref_roll"] = roll0 * RAD2DEG
        res["ref_pitch"] = pitch0 * RAD2DEG
        res["ref_imu_roll"] = imu_roll0 * RAD2DEG
        res["ref_imu_pitch"] = imu_pitch0 * RAD2DEG
        return res


# ---------------------------------------------------------------------------
# Divergence analysis
# ---------------------------------------------------------------------------

def _first_sustained(mask: np.ndarray, sustain: int = SUSTAIN_TICKS) -> int:
    """First index where ``mask`` stays True for ``sustain`` ticks; -1."""
    run = 0
    for i, m in enumerate(mask):
        run = run + 1 if m else 0
        if run >= sustain:
            return i - sustain + 1
    return -1


def analyze(tr: dict, sim: dict) -> dict:
    hw_roll_rel = tr["roll"] - tr["ref_roll"]
    # The robot CSV contains ComplementaryAttitude output, not an external
    # measurement of chassis orientation.  Compare it to the equivalent
    # simulated sensor estimate; keep rigid-body truth as a separate metric.
    sim_roll_rel = sim["imu_roll"] - sim["ref_imu_roll"]
    sim_true_roll_rel = sim["roll"] - sim["ref_roll"]
    d_roll = np.abs(sim_roll_rel - hw_roll_rel)
    hw_pitch_rel = tr["pitch"] - tr["ref_pitch"]
    sim_pitch_rel = sim["imu_pitch"] - sim["ref_imu_pitch"]
    sim_true_pitch_rel = sim["pitch"] - sim["ref_pitch"]
    roll_tick = _first_sustained(d_roll > ROLL_DIV_DEG)

    moving = np.ptp(tr["q"], axis=0) > MOVING_PTP_DEG
    dq = np.abs(sim["q"] - tr["q"])            # (n, 18) deg
    q_tick, q_joint = -1, -1
    for j in np.flatnonzero(moving):
        t_j = _first_sustained(dq[:, j] > Q_DIV_DEG)
        if t_j >= 0 and (q_tick < 0 or t_j < q_tick):
            q_tick, q_joint = t_j, int(j)
    q_rmse = float(np.sqrt(np.mean(dq[:, moving] ** 2))) if moving.any() \
        else float("nan")

    # Contact events: per-foot liftoff / touchdown ticks + loaded slip.
    f = sim["foot_f"]
    on = f > CONTACT_N
    xy = sim["foot_xyz"][:, :, :2]
    slip = np.zeros_like(f)
    slip[1:] = np.linalg.norm(np.diff(xy, axis=0), axis=2) \
        * (on[1:] & on[:-1])
    events = []
    for foot in range(6):
        ch = np.flatnonzero(np.diff(on[:, foot].astype(int)) != 0)
        for k in ch:
            events.append((int(k) + 1, foot,
                           "touchdown" if on[k + 1, foot] else "liftoff"))
    events.sort()

    # Peak rel-roll comparison — did the sim reproduce the excursion?
    hw_peak = float(np.max(np.abs(hw_roll_rel)))
    sim_peak = float(np.max(np.abs(sim_roll_rel)))
    sim_true_peak = float(np.max(np.abs(sim_true_roll_rel)))
    duration_s = float(tr["t"][-1] - tr["t"][0])
    displacement_m = float(np.linalg.norm(
        sim["base_xyz"][-1, :2] - sim["base_xyz"][0, :2]))
    max_flex_deg = float(np.max(np.abs(sim["flex_deg"])))
    series_flex = np.asarray(
        sim.get("series_flex_deg", np.zeros((len(tr["t"]), 18))),
        dtype=float)
    max_series_flex_deg = float(np.max(np.abs(series_flex)))
    roll_rmse = float(np.sqrt(np.mean(
        (sim_roll_rel - hw_roll_rel) ** 2)))
    pitch_rmse = float(np.sqrt(np.mean(
        (sim_pitch_rel - hw_pitch_rel) ** 2)))

    return {
        "roll_div_tick": int(roll_tick),
        "q_div_tick": int(q_tick), "q_div_joint": q_joint,
        "q_rmse_moving_deg": round(q_rmse, 2),
        "hw_peak_roll_rel_deg": round(hw_peak, 2),
        "sim_peak_roll_rel_deg": round(sim_peak, 2),
        "sim_true_peak_roll_rel_deg": round(sim_true_peak, 2),
        "hw_peak_current_a": round(float(np.nanmax(tr["current_a"])), 3)
        if np.any(np.isfinite(tr["current_a"])) else None,
        "sim_peak_current_proxy_a": round(
            float(np.max(sim["current_proxy_a"])), 3),
        "sim_displacement_mm": round(displacement_m * 1000.0, 1),
        "sim_speed_mm_s": round(displacement_m * 1000.0 / duration_s, 1)
        if duration_s > 0.0 else None,
        "sim_max_mount_flex_deg": round(max_flex_deg, 2),
        "sim_max_series_flex_deg": round(max_series_flex_deg, 2),
        "roll_waveform_rmse_deg": round(roll_rmse, 2),
        "pitch_waveform_rmse_deg": round(pitch_rmse, 2),
        "trace_duration_s": round(duration_s, 3),
        "trace_median_hz": round(
            1.0 / float(np.median(np.diff(tr["t"]))), 2),
        "hw_roll_rel": hw_roll_rel, "sim_roll_rel": sim_roll_rel,
        "sim_true_roll_rel": sim_true_roll_rel,
        "sim_true_pitch_rel": sim_true_pitch_rel,
        "d_roll": d_roll, "dq": dq, "moving": moving,
        "slip_mm": slip * 1000.0, "contact_on": on,
        "contact_events": events,
    }


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

def plot_overlay(tr: dict, runs: dict[str, tuple[dict, dict]],
                 out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ticks = np.arange(len(tr["t"]))
    moving = np.ptp(tr["q"], axis=0) > MOVING_PTP_DEG
    top_j = np.argsort(np.ptp(tr["q"], axis=0))[::-1][:6]
    n_rows = 3 + 1
    fig, axs = plt.subplots(n_rows, 1, figsize=(13, 3.0 * n_rows),
                            sharex=True)

    ax = axs[0]
    ax.plot(ticks, tr["roll"] - tr["ref_roll"], "k-", lw=2,
            label="hardware roll_rel")
    for tag, (sim, an) in runs.items():
        ax.plot(ticks, an["sim_roll_rel"], lw=1.4,
                label=f"sim IMU {tag} (div@{an['roll_div_tick']})")
        ax.plot(ticks, an["sim_true_roll_rel"], lw=0.9, ls=":",
                label=f"sim chassis {tag}")
        if an["roll_div_tick"] >= 0:
            ax.axvline(an["roll_div_tick"], ls=":", alpha=0.5)
    ax.axhline(10, color="r", ls="--", alpha=0.4, label="tilt trip 10°")
    ax.axhline(-10, color="r", ls="--", alpha=0.4)
    ax.set_ylabel("roll rel (deg)")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_title(tr["name"])

    ax = axs[1]
    ax.plot(ticks, tr["gyro_x"], "k-", lw=2, label="hardware gyro_x")
    for tag, (sim, an) in runs.items():
        ax.plot(ticks, sim["gyro_x"], lw=1.2, label=f"sim {tag}")
    ax.set_ylabel("roll rate (deg/s)")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)

    ax = axs[2]
    cmap = plt.cm.tab10
    for i, j in enumerate(top_j):
        c = cmap(i % 10)
        ax.plot(ticks, tr["q"][:, j], color=c, lw=2, alpha=0.8,
                label=f"q{j} hw")
        for tag, (sim, an) in runs.items():
            ls = "--" if tag == "air" else ":"
            ax.plot(ticks, sim["q"][:, j], color=c, lw=1.2, ls=ls)
    ax.set_ylabel("q (deg) — hw solid / sim dashed(air) dotted(loaded)")
    ax.legend(loc="upper left", fontsize=7, ncol=6)
    ax.grid(alpha=0.3)

    ax = axs[3]
    tag0 = next(iter(runs))
    sim, an = runs[tag0]
    for foot in range(6):
        base = foot * 1.2
        ax.fill_between(ticks, base, base + an["contact_on"][:, foot],
                        step="mid", alpha=0.35)
        ax.plot(ticks, base + np.minimum(an["slip_mm"][:, foot], 1.0),
                lw=0.8)
        ax.text(-6, base + 0.4, f"L{foot}", fontsize=8)
    ax.set_ylabel(f"sim contact+slip ({tag0})")
    ax.set_xlabel(f"tick ({tr['time_source']}; median "
                  f"{1000.0 * np.median(np.diff(tr['t'])):.1f} ms)")
    ax.grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)
    print(f"  wrote {out}")


# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, nargs="+", required=True)
    ap.add_argument("--phase", choices=("auto", "run", "walk"),
                    default="auto",
                    help="active CSV phase (default: first-to-last window "
                         "of the more common run/walk phase)")
    ap.add_argument("--model-source",
                    choices=("mesh", "mesh_mjx", "primitive"), default=None,
                    help="explicit model family (default: normal resolver)")
    ap.add_argument("--servo-params", default="both",
                    choices=("air", "loaded", "both"))
    ap.add_argument("--mu", type=float, default=0.0,
                    help="foot-ground slide friction override "
                         "(0 = XML default; large ~50 = pinned feet)")
    ap.add_argument("--com-shift-mm", type=str, default="0,0,0",
                    help="chassis CoM shift in mm, 'x,y,z' "
                         "(+y = left side; -y shifts CoM right)")
    ap.add_argument("--leg-chassis-collision", action="store_true",
                    help="enable the env.leg_chassis_collision contact "
                         "axis (belly knife-edge, SIM.md gap 4) in the "
                         "replay model")
    ap.add_argument("--leg-mount-flex-json", type=Path, default=None,
                    help="JSON object with explicit leg_mount_flex physical "
                         "parameters; absent = rigid model")
    ap.add_argument("--joint-series-flex-json", type=Path, default=None,
                    help="JSON object with an explicit 18-entry "
                         "joint_series_flex table; absent = rigid model")
    ap.add_argument("--imu-pos-mm", default="0,0,0",
                    help="chassis-frame IMU x,y,z in mm")
    ap.add_argument("--plot", action="store_true")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="plot/JSON output dir (default: alongside csv)")
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args(argv)

    try:
        imu_pos_mm = tuple(float(x) for x in args.imu_pos_mm.split(","))
    except ValueError:
        ap.error("--imu-pos-mm must be x,y,z in millimetres")
    if len(imu_pos_mm) != 3 or not np.all(np.isfinite(imu_pos_mm)):
        ap.error("--imu-pos-mm must be three finite values")

    mount_flex = None
    if args.leg_mount_flex_json is not None:
        blob = json.loads(args.leg_mount_flex_json.read_text())
        section = blob.get("leg_mount_flex", blob)
        mount_flex = leg_mount_flex_from_cfg({
            "leg_mount_flex": {**section, "enabled": 1}})
    series_flex = None
    if args.joint_series_flex_json is not None:
        blob = json.loads(args.joint_series_flex_json.read_text())
        section = blob.get("joint_series_flex", blob)
        series_flex = joint_series_flex_from_cfg({
            "joint_series_flex": {**section, "enabled": 1}})
    if mount_flex is not None and series_flex is not None:
        ap.error("--leg-mount-flex-json and --joint-series-flex-json "
                 "are mutually exclusive")

    param_sets = {}
    if args.servo_params in ("air", "both"):
        param_sets["air"] = SimServoParams.load()
    if args.servo_params in ("loaded", "both"):
        param_sets["loaded"] = SimServoParams.load(LOADED_MODEL_PATH)

    all_out = {}
    for csv_path in args.csv:
        tr = load_trace(csv_path, phase=args.phase)
        n = len(tr["t"])
        hz = 1.0 / float(np.median(np.diff(tr["t"])))
        print(f"\n[{tr['name']}] {n} {tr['phase']} ticks at {hz:.1f} Hz "
              f"({tr['time_source']}), "
              f"hw peak roll_rel "
              f"{np.max(np.abs(tr['roll'] - tr['ref_roll'])):.1f} deg")
        runs = {}
        rec = {}
        com_shift = tuple(float(x) for x in args.com_shift_mm.split(","))
        for tag, params in param_sets.items():
            sim = _ReplaySim(params, mu=args.mu, com_shift_mm=com_shift,
                             leg_chassis=args.leg_chassis_collision,
                             leg_mount_flex=mount_flex,
                             joint_series_flex=series_flex,
                             model_source=args.model_source,
                             imu_pos_mm=imu_pos_mm)
            res = sim.replay(tr)
            an = analyze(tr, res)
            runs[tag] = (res, an)
            rec[tag] = {k: an[k] for k in (
                "roll_div_tick", "q_div_tick", "q_div_joint",
                "q_rmse_moving_deg", "hw_peak_roll_rel_deg",
                "sim_peak_roll_rel_deg", "sim_true_peak_roll_rel_deg",
                "hw_peak_current_a",
                "sim_peak_current_proxy_a", "sim_displacement_mm",
                "sim_speed_mm_s", "sim_max_mount_flex_deg",
                "sim_max_series_flex_deg",
                "roll_waveform_rmse_deg", "pitch_waveform_rmse_deg",
                "trace_duration_s", "trace_median_hz")}
            first_events = ", ".join(
                f"t{t}:L{f}:{e}" for t, f, e in an["contact_events"][:8])
            print(f"  [{tag:>6}] roll div tick "
                  f"{an['roll_div_tick']:>4}  q div tick "
                  f"{an['q_div_tick']:>4} (j{an['q_div_joint']})  "
                  f"q RMSE {an['q_rmse_moving_deg']:.2f} deg  "
                  f"sim peak roll {an['sim_peak_roll_rel_deg']:.1f} vs hw "
                  f"{an['hw_peak_roll_rel_deg']:.1f}")
            if first_events:
                print(f"           contact events: {first_events}")
        all_out[tr["name"]] = rec
        if args.plot:
            out_dir = args.out_dir or csv_path.parent
            out_dir.mkdir(parents=True, exist_ok=True)
            plot_overlay(tr, runs,
                         out_dir / (csv_path.stem + ".replay.png"))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(all_out, indent=2))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
