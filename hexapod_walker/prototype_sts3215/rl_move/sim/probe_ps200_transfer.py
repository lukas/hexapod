"""Frozen-policy causal panel for the PS200 hardware roll mismatch.

The Hexapod-2 PS200 hardware replay peaks at 16.78 degrees of roll while
the identical-command mesh replay peaks at 3.32 degrees.  This probe asks
three narrower questions before spending another training run:

* Do physically correct, frame-coupled set-zero offsets reproduce it?
* Does briefly losing one implicated foot's ground support reproduce it?
* Does a recurrent, gait-phase-locked chassis roll impulse reproduce it?

The last two mechanisms are diagnostic world interventions, not proposed
truths about the robot.  A mechanism only earns a training recommendation
if it reproduces the PS200 scale without doing the same thing to the two
lower-roll 50 Hz control policies.

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_ps200_transfer

Outputs ``results.json``, ``rows.csv`` and ``report.md`` beneath
``logs/ckpt_eval/ps200_transfer_probe_<UTC>`` unless ``--out`` is supplied.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import numpy as np

from rl_move.config import load_config
from rl_move.np_policy import load_np_policy
from rl_move.sim.probe_walk_income import pin_command
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.walk_task import SimHexapodJointWalkEnv

ROOT = Path(__file__).resolve().parents[2]
HARDWARE_PS200_PEAK_ROLL_DEG = 16.78
SIM_TRACE_PS200_PEAK_ROLL_DEG = 3.32


@dataclass(frozen=True)
class PolicySpec:
    name: str
    artifact: str


POLICIES = {
    "ps200": PolicySpec(
        "ps200",
        "linux_control/policies/"
        "speed50hz_stride_ps200_lift14_massfix_sr105_acq10m.json",
    ),
    "walkteach": PolicySpec(
        "walkteach",
        "linux_control/policies/"
        "walkteach_scripted_allhead_scratch_50hz.json",
    ),
    "allheading": PolicySpec(
        "allheading",
        "linux_control/policies/"
        "walk_allheading_mlp_singleframe_scratch_50hz.json",
    ),
}


@dataclass(frozen=True)
class Intervention:
    name: str
    mechanism: str = "none"
    zero_range_deg: float = 0.0
    deadband_scale: float = 1.0
    dropout_legs: tuple[int, ...] = ()
    torque_peak_nm: float = 0.0
    period_s: float = 1.5
    duration_s: float = 0.3
    phase_s: float = 0.0
    start_s: float = 2.0
    # ``load_triggered`` mechanism (2026-09-13 addendum): the recurrent
    # ``roll_torque`` pulse above fires on a blind wall-clock schedule.
    # This fires the SAME half-sine pulse shape gated on a sensed per-leg
    # ground-reaction-force crossing, i.e. real stance onset, not a timer
    # -- the FAIL verdict's third named candidate ("load-triggered L4
    # stance-onset error").
    trigger_leg: int = 4
    force_threshold_n: float = 0.0
    # ``load_share`` mechanism (2026-09-13 addendum 3): the single-leg
    # trigger above is either non-selective (L1: shared by every gait) or
    # too noisy/threshold-sensitive to trust (L4: non-monotonic across
    # seeds). This is the addendum 2 FAIL's own named next step -- "a
    # genuinely different operationalization ... an asymmetric
    # front-vs-rear load-share trigger" -- not another single-leg dose of
    # the same shape. Fires the SAME half-sine pulse on the RISING edge of
    # the FRONT pair's (L0/L5) share of the combined front+rear sensed
    # ground-reaction force crossing ``share_threshold`` (a fraction in
    # 0..1), i.e. weight visibly shifting onto the front legs relative to
    # the rear pair (L2/L3) -- a relative, two-group signal, not an
    # absolute single-leg force level.
    front_legs: tuple[int, ...] = (0, 5)
    rear_legs: tuple[int, ...] = (2, 3)
    share_threshold: float = 0.0
    # ``friction_loss`` mechanism (2026-09-13 addendum 4): every prior
    # candidate injects an external torque (roll_torque, load_triggered,
    # load_share) or removes contact outright (support_loss) or edits a
    # static per-joint property (zero-offset, deadband). None models
    # contact/compliance loss AT THE FOOT directly -- a leg that stays
    # planted and loaded but slips because its effective ground friction
    # has dropped (grease, wear, a compliant/lossy contact patch), which
    # is a genuinely different physical consequence: the chassis roll
    # this produces (if any) comes from real foot slip under real load,
    # not an externally applied moment. Reuses the SAME periodic
    # scheduling as ``support_loss`` (``dropout_legs``/``duration_s``/
    # ``phase_s``/``period_s``) but scales ``geom_friction`` on the
    # scheduled legs instead of zeroing their contact mask.
    friction_scale: float = 1.0


def periodic_phase_s(t_s: float, *, start_s: float, period_s: float,
                     phase_s: float) -> float | None:
    """Elapsed seconds inside a periodic event, or ``None`` before it."""
    if period_s <= 0.0:
        raise ValueError("period_s must be positive")
    elapsed = float(t_s) - float(start_s) - float(phase_s)
    if elapsed < 0.0:
        return None
    return elapsed % float(period_s)


def periodic_active(t_s: float, intervention: Intervention) -> bool:
    phase = periodic_phase_s(
        t_s, start_s=intervention.start_s,
        period_s=intervention.period_s, phase_s=intervention.phase_s)
    return (phase is not None
            and phase < intervention.duration_s - 1e-12)


def periodic_half_sine(t_s: float, intervention: Intervention) -> float:
    """Smooth recurrent torque pulse with zero value outside its window."""
    if intervention.duration_s <= 0.0 or intervention.torque_peak_nm == 0.0:
        return 0.0
    phase = periodic_phase_s(
        t_s, start_s=intervention.start_s,
        period_s=intervention.period_s, phase_s=intervention.phase_s)
    if phase is None or phase >= intervention.duration_s - 1e-12:
        return 0.0
    return intervention.torque_peak_nm * math.sin(
        math.pi * phase / intervention.duration_s)


@contextmanager
def _temporary_foot_ground_friction(model, foot_gids, ground_gids,
                                    scale: float):
    """Scale one or more feet and the ground for a single probe tick.

    MuJoCo combines equal-priority geom friction with an element-wise MAX.
    Scaling only a foot therefore cannot reduce its contact below the floor's
    friction.  Scale the target feet and lower both possible ground geoms just
    enough that they cannot pin any target component.  Non-target foot
    contacts remain at their foot-side baseline because the mesh models
    deliberately give feet more friction than the ground.

    The caller owns a single physics tick.  Always restore the compiled model,
    including when stepping raises, so an intervention cannot leak into the
    next tick, reset, policy, or seed.
    """
    scale = float(scale)
    if not math.isfinite(scale) or not 0.0 <= scale <= 1.0:
        raise ValueError("friction-loss scale must be finite and in [0, 1]")
    foot_gids = np.asarray(tuple(foot_gids), dtype=int)
    ground_gids = np.asarray(tuple(ground_gids), dtype=int)
    if foot_gids.size == 0:
        raise ValueError("friction-loss intervention needs a target foot")
    if ground_gids.size == 0:
        raise ValueError("friction-loss intervention needs floor or terrain")
    if np.intersect1d(foot_gids, ground_gids).size:
        raise ValueError("target feet and ground geoms must be disjoint")
    foot_base = model.geom_friction[foot_gids].copy()
    ground_base = model.geom_friction[ground_gids].copy()
    foot_dosed = foot_base * scale
    # Equal-priority contacts use max(geom1, geom2) component-wise.  A shared
    # ground coefficient no greater than every dosed target lets each target
    # retain its own requested value without unnecessarily scaling the floor.
    ground_cap = np.min(foot_dosed, axis=0)
    model.geom_friction[foot_gids] = foot_dosed
    model.geom_friction[ground_gids] = np.minimum(ground_base, ground_cap)
    try:
        yield
    finally:
        model.geom_friction[foot_gids] = foot_base
        model.geom_friction[ground_gids] = ground_base


class TransferProbeEnv(SimHexapodJointWalkEnv):
    """MuJoCo env with two explicitly bounded diagnostic interventions."""

    def __init__(self, *args, intervention: Intervention, **kwargs):
        self.intervention = intervention
        super().__init__(*args, **kwargs)
        self._dropout_gids: tuple[int, ...] = ()
        self._friction_gids: tuple[int, ...] = ()
        self._friction_ground_gids: tuple[int, ...] = ()
        self._friction_contact_slides: list[float] = []
        if intervention.mechanism in ("support_loss", "friction_loss"):
            gids = []
            for leg in intervention.dropout_legs:
                if leg not in range(6):
                    raise ValueError(f"dropout leg must be 0..5, got {leg}")
                gid = self._mujoco.mj_name2id(
                    self.model, self._mujoco.mjtObj.mjOBJ_GEOM,
                    f"L{leg}_foot")
                if gid < 0:
                    raise ValueError(f"mesh model has no L{leg}_foot geom")
                gids.append(gid)
            if intervention.mechanism == "support_loss":
                self._dropout_gids = tuple(gids)
            else:
                self._friction_gids = tuple(gids)
                ground_gids = []
                for gname in ("floor", "terrain"):
                    gid = self._mujoco.mj_name2id(
                        self.model, self._mujoco.mjtObj.mjOBJ_GEOM, gname)
                    if gid >= 0:
                        ground_gids.append(gid)
                if not ground_gids:
                    raise ValueError("mesh model has no floor or terrain geom")
                self._friction_ground_gids = tuple(ground_gids)
        # load_triggered edge-detector state: which control tick (if any)
        # the current GRF-gated pulse started on, plus the hysteresis flag
        # used to fire on RISING edges only (never re-arm while the leg
        # stays loaded through one long stance).
        self._lt_pulse_start_step: int | None = None
        self._lt_was_high: bool = False
        self._lt_active_ticks: int = 0

    def _lt_maybe_trigger(self, iv: Intervention) -> None:
        """Start a new pulse on a rising edge of the sensed trigger signal.

        Reads ``_foot_prev_force`` -- the SAME sensed per-leg force the
        base env already tracks for slip pricing -- as it stood at the end
        of the PREVIOUS control tick (this tick's physics has not run yet),
        so the trigger is causally one tick behind the true onset, exactly
        the latency a real force-gated controller would see.

        ``load_triggered``: sensed = one leg's own force, threshold in N.
        ``load_share``: sensed = the front pair's share (0..1) of the
        combined front+rear sensed force, threshold a fraction -- a
        relative two-group signal instead of one leg's absolute level.
        """
        if iv.mechanism == "load_share":
            front = sum(self._foot_prev_force[leg] for leg in iv.front_legs)
            rear = sum(self._foot_prev_force[leg] for leg in iv.rear_legs)
            total = front + rear
            sensed = front / total if total > 1e-9 else 0.0
            is_high = sensed >= iv.share_threshold
        else:
            sensed = self._foot_prev_force[iv.trigger_leg]
            is_high = sensed >= iv.force_threshold_n
        if is_high and not self._lt_was_high:
            self._lt_pulse_start_step = self._step_i
        self._lt_was_high = is_high

    def _walk_push_torque_nm(self) -> float:
        iv = self.intervention
        in_walk = (self._goal_traj is not None
                  and getattr(self._goal_traj, "mode", "") == "walk")
        if iv.mechanism == "roll_torque":
            if not in_walk:
                return 0.0
            return periodic_half_sine(self._step_i * self.dt, iv)
        if iv.mechanism in ("load_triggered", "load_share"):
            if not in_walk or self._lt_pulse_start_step is None:
                return 0.0
            elapsed = (self._step_i - self._lt_pulse_start_step) * self.dt
            if elapsed < 0.0 or elapsed >= iv.duration_s - 1e-12:
                return 0.0
            self._lt_active_ticks += 1
            return iv.torque_peak_nm * math.sin(
                math.pi * elapsed / iv.duration_s)
        return super()._walk_push_torque_nm()

    def _record_friction_contacts(self) -> None:
        """Record and verify the effective target-foot contact friction."""
        feet = set(self._friction_gids)
        ground = set(self._friction_ground_gids)
        for i in range(int(self.data.ncon)):
            contact = self.data.contact[i]
            g1, g2 = int(contact.geom1), int(contact.geom2)
            if not ((g1 in feet and g2 in ground)
                    or (g2 in feet and g1 in ground)):
                continue
            pair = np.maximum(self.model.geom_friction[g1],
                              self.model.geom_friction[g2])
            expected = np.asarray(
                [pair[0], pair[0], pair[1], pair[2], pair[2]], dtype=float)
            observed = np.asarray(contact.friction, dtype=float)
            if not np.allclose(observed, expected, rtol=1e-6, atol=1e-9):
                raise RuntimeError(
                    "friction-loss contact did not receive the requested "
                    f"friction: observed={observed.tolist()}, "
                    f"expected={expected.tolist()}")
            self._friction_contact_slides.append(float(observed[0]))

    def _advance(self, *, limp: bool = False) -> None:
        iv = self.intervention
        in_walk = (self._goal_traj is not None
                  and getattr(self._goal_traj, "mode", "") == "walk")
        if (not limp and iv.mechanism in ("load_triggered", "load_share")
                and in_walk):
            self._lt_maybe_trigger(iv)
        support_active = (
            not limp and iv.mechanism == "support_loss" and in_walk
            and periodic_active(self._step_i * self.dt, iv)
        )
        friction_active = (
            not limp and iv.mechanism == "friction_loss" and in_walk
            and periodic_active(self._step_i * self.dt, iv)
        )
        if support_active and self._dropout_gids:
            gids = np.asarray(self._dropout_gids, dtype=int)
            contype = self.model.geom_contype[gids].copy()
            conaffinity = self.model.geom_conaffinity[gids].copy()
            self.model.geom_contype[gids] = 0
            self.model.geom_conaffinity[gids] = 0
            try:
                super()._advance(limp=limp)
            finally:
                # The intervention owns exactly one control tick.  Restoring
                # in finally also prevents a terminated/exceptional tick
                # from leaking a collision-mask edit into reset or another
                # case.
                self.model.geom_contype[gids] = contype
                self.model.geom_conaffinity[gids] = conaffinity
            return
        if friction_active and self._friction_gids:
            with _temporary_foot_ground_friction(
                    self.model, self._friction_gids,
                    self._friction_ground_gids, iv.friction_scale):
                super()._advance(limp=limp)
                self._record_friction_contacts()
            return
        return super()._advance(limp=limp)


def _policy_path(spec: PolicySpec) -> Path:
    path = ROOT / spec.artifact
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _policy_cfg(meta: dict, intervention: Intervention) -> dict:
    cfg = load_config()
    cfg.setdefault("env", {})["model_source"] = "mesh"
    cfg.setdefault("control", {})["hz"] = float(meta["control_hz"])
    cfg.setdefault("bus", {})["write_speed"] = float(
        meta.get("bus_write_speed", 400))
    cfg["bus"]["write_acc"] = float(meta.get("bus_write_acc", 20))
    safety = cfg.setdefault("safety", {})
    safety["max_delta_q_deg"] = float(meta["max_delta_q_deg"])
    safety["max_roll_deg"] = 25.0
    safety["max_pitch_deg"] = 25.0
    goal = cfg.setdefault("goal", {})
    goal["walk_speed_min_m_s"] = float(meta["walk_speed_min_m_s"])
    goal["walk_speed_max_m_s"] = float(meta["walk_speed_max_m_s"])
    goal["walk_obs_body_vel"] = 2.0
    goal["walk_phase_obs"] = 1.0
    goal["walk_phase_hz"] = float(meta["phase_hz"])
    goal["walk_yaw_cmd"] = 1.0 if meta.get("walk_yaw_cmd") else 0.0
    goal["walk_phase_run_on_yaw"] = (
        1.0 if meta.get("walk_phase_run_on_yaw") else 0.0)
    goal["walk_yaw_zero_frac"] = 1.0
    goal["walk_stop_frac"] = 0.0
    goal["walk_contact_diagnostics"] = 1.0
    # These are absolute post-dr_scale overrides.  A zero-range case still
    # uses the same randomizer/noise path as every non-zero zero-offset case.
    dr = cfg.setdefault("dr", {})
    dr["joint_zero_bias_deg"] = float(intervention.zero_range_deg)
    dr["zero_drift_cmd_frame"] = 1.0
    # Pinned (degenerate-range) deadband multiplier — an absolute override
    # of the SAME calibrated per-joint deadband_deg (motor_model.json,
    # real-hardware measured) that ordinary training DR already samples
    # from up to 1.8x nominal.  A dose here can go well past that training
    # ceiling to screen the "post-encoder compliance / backlash" candidate
    # named in docs/PS200_TRANSFER_PROBE_2026-09-12.md's Next step, the
    # same way zero_range_deg screens the zero-offset candidate: a static
    # per-episode physical property, not a phase-locked world edit.
    dr["deadband_scale"] = (
        f"{intervention.deadband_scale},{intervention.deadband_scale}")
    return cfg


def _force_walk(env: SimHexapodJointWalkEnv) -> None:
    gen = env._goal_gen
    for mode in ("hold", "lean", "track", "unload", "raise", "rise",
                 "lower", "quad", "quadwalk", "recover", "walk"):
        attr = f"p_{mode}"
        if hasattr(gen, attr):
            setattr(gen, attr, 1.0 if mode == "walk" else 0.0)


def _separated_peak_count(values: list[float], *, threshold: float,
                          dt: float, min_separation_s: float = 0.5) -> int:
    if len(values) < 3:
        return 0
    candidates = [
        i for i in range(1, len(values) - 1)
        if values[i] >= threshold
        and values[i] > values[i - 1]
        and values[i] >= values[i + 1]
    ]
    separation = max(1, int(round(min_separation_s / dt)))
    kept: list[int] = []
    for idx in candidates:
        if not kept or idx - kept[-1] >= separation:
            kept.append(idx)
        elif values[idx] > values[kept[-1]]:
            kept[-1] = idx
    return len(kept)


def rollout(spec: PolicySpec, intervention: Intervention, *, seed: int,
            episode_s: float, cmd_m_s: float) -> dict:
    policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, intervention)
    env = TransferProbeEnv(
        params=SimServoParams.from_cfg(cfg), randomize=True, dr_scale=0.0,
        episode_seconds=episode_s, seed=seed, cfg=cfg,
        intervention=intervention)
    _force_walk(env)
    obs, reset_info = env.reset()
    if obs.shape != policy.observation_space.shape:
        raise RuntimeError(
            f"{spec.name}: env obs {obs.shape} != policy "
            f"{policy.observation_space.shape}")
    pin_command(env, cmd_m_s, 0.0, 0.0)
    policy.reset()

    rolls: list[float] = []
    contact_ticks = np.zeros(6, dtype=int)
    contact_seen = np.zeros(6, dtype=int)
    air_run = np.zeros(6, dtype=int)
    air_max = np.zeros(6, dtype=int)
    min_contact_feet = 6
    event_ticks = 0
    x_at_walk = None
    x_final = float(env.data.xpos[env._chassis_bid, 0])
    term_reason = ""
    ticks = 0
    try:
        while True:
            t_s = env._step_i * env.dt
            if intervention.mechanism in (
                    "support_loss", "roll_torque", "friction_loss") \
                    and periodic_active(t_s, intervention):
                event_ticks += 1
            action, _ = policy.predict(obs, deterministic=True)
            obs, _reward, terminated, truncated, info = env.step(action)
            ticks += 1
            roll = float(info.get("roll_rel_deg", 0.0))
            rolls.append(roll)
            if t_s >= intervention.start_s and x_at_walk is None:
                x_at_walk = float(env.data.xpos[env._chassis_bid, 0])
            x_final = float(env.data.xpos[env._chassis_bid, 0])
            contacts = []
            for leg in range(6):
                key = f"walk_foot{leg}_contact"
                if key not in info:
                    continue
                on = bool(info[key])
                contact_seen[leg] += 1
                contact_ticks[leg] += int(on)
                air_run[leg] = 0 if on else air_run[leg] + 1
                air_max[leg] = max(air_max[leg], air_run[leg])
                contacts.append(on)
            if contacts:
                min_contact_feet = min(min_contact_feet, sum(contacts))
            if terminated or truncated:
                term_reason = str(info.get("termination_reason") or "")
                break
    finally:
        if intervention.mechanism in ("load_triggered", "load_share"):
            # Ticks counted from inside the env's own trigger (the outer
            # loop above cannot know a pulse fired until AFTER env.step
            # runs its physics -- see _lt_maybe_trigger's docstring).
            event_ticks = env._lt_active_ticks
        env.close()

    zero_bias = ((reset_info.get("randomization") or {})
                 .get("zero_bias_max_deg", 0.0))
    friction_slides = env._friction_contact_slides
    abs_rolls = [abs(v) for v in rolls]
    elapsed_walk = max(ticks * (1.0 / float(policy.meta["control_hz"]))
                       - intervention.start_s, 1e-9)
    x_at_walk = x_final if x_at_walk is None else x_at_walk
    return {
        "policy": spec.name,
        "case": intervention.name,
        "mechanism": intervention.mechanism,
        "seed": seed,
        "ticks": ticks,
        "terminated": bool(term_reason),
        "termination_reason": term_reason,
        "peak_abs_roll_deg": round(max(abs_rolls, default=0.0), 3),
        "peak_positive_roll_deg": round(max(rolls, default=0.0), 3),
        "peak_negative_roll_deg": round(min(rolls, default=0.0), 3),
        "rms_roll_deg": round(float(np.sqrt(np.mean(np.square(rolls)))), 3),
        "positive_peaks_over_5deg": _separated_peak_count(
            rolls, threshold=5.0, dt=1.0 / float(policy.meta["control_hz"])),
        "negative_peaks_over_5deg": _separated_peak_count(
            [-v for v in rolls], threshold=5.0,
            dt=1.0 / float(policy.meta["control_hz"])),
        "event_ticks": event_ticks,
        "event_count_approx": round(
            event_ticks * (1.0 / float(policy.meta["control_hz"]))
            / max(intervention.duration_s, 1e-9), 2),
        "forward_speed_after_2s_m_s": round(
            (x_final - x_at_walk) / elapsed_walk, 4),
        "min_contact_feet": min_contact_feet,
        "contact_duty": [
            round(float(contact_ticks[i] / max(contact_seen[i], 1)), 3)
            for i in range(6)
        ],
        "max_air_s": [
            round(float(v / float(policy.meta["control_hz"])), 3)
            for v in air_max
        ],
        "sampled_zero_bias_max_deg": float(zero_bias),
        "friction_contact_samples": len(friction_slides),
        "friction_slide_min": (
            round(min(friction_slides), 6) if friction_slides else None),
        "friction_slide_max": (
            round(max(friction_slides), 6) if friction_slides else None),
        "intervention": asdict(intervention),
    }


def _summary(rows: list[dict], policy: str, case: str) -> dict:
    group = [r for r in rows if r["policy"] == policy and r["case"] == case]
    if not group:
        return {}
    peaks = [r["peak_abs_roll_deg"] for r in group]
    speeds = [r["forward_speed_after_2s_m_s"] for r in group]
    return {
        "n": len(group),
        "peak_abs_roll_median_deg": round(float(median(peaks)), 3),
        "peak_abs_roll_range_deg": [round(min(peaks), 3), round(max(peaks), 3)],
        "forward_speed_median_m_s": round(float(median(speeds)), 4),
        "terminations": sum(r["terminated"] for r in group),
    }


def _closest_case(rows: list[dict], mechanism: str,
                  target_deg: float) -> str:
    names = sorted({r["case"] for r in rows
                    if r["policy"] == "ps200"
                    and r["mechanism"] == mechanism})
    if not names:
        raise ValueError(f"no {mechanism} cases")
    return min(
        names,
        key=lambda name: abs(
            median(r["peak_abs_roll_deg"] for r in rows
                   if r["policy"] == "ps200" and r["case"] == name)
            - target_deg),
    )


def _case_by_name(cases: list[Intervention], name: str) -> Intervention:
    return next(case for case in cases if case.name == name)


def _selectivity(rows: list[dict], candidate: str,
                 target_deg: float) -> dict:
    p = _summary(rows, "ps200", candidate)
    pb = _summary(rows, "ps200", "baseline")
    controls = {}
    for name in ("walkteach", "allheading"):
        c = _summary(rows, name, candidate)
        cb = _summary(rows, name, "baseline")
        controls[name] = {
            "candidate_peak_deg": c["peak_abs_roll_median_deg"],
            "baseline_peak_deg": cb["peak_abs_roll_median_deg"],
            "increase_deg": round(
                c["peak_abs_roll_median_deg"]
                - cb["peak_abs_roll_median_deg"], 3),
        }
    ps_increase = (p["peak_abs_roll_median_deg"]
                   - pb["peak_abs_roll_median_deg"])
    control_increases = [max(0.0, c["increase_deg"])
                         for c in controls.values()]
    scale_match = (0.5 * target_deg <= p["peak_abs_roll_median_deg"]
                   <= 1.5 * target_deg)
    recurrent = median(
        r["positive_peaks_over_5deg"] + r["negative_peaks_over_5deg"]
        for r in rows if r["policy"] == "ps200" and r["case"] == candidate
    ) >= 2
    survived = p["terminations"] == 0
    selective = (scale_match and recurrent and survived and ps_increase >= 3.0
                 and ps_increase >= 1.5 * max(control_increases, default=0.0))
    return {
        "candidate": candidate,
        "ps200_peak_deg": p["peak_abs_roll_median_deg"],
        "ps200_baseline_deg": pb["peak_abs_roll_median_deg"],
        "ps200_increase_deg": round(ps_increase, 3),
        "hardware_target_deg": target_deg,
        "scale_match": scale_match,
        "recurrent_peaks": recurrent,
        "survived": survived,
        "controls": controls,
        "selective": selective,
        "fund_training": selective,
    }


def _write_outputs(out_dir: Path, rows: list[dict], cases: list[Intervention],
                   candidate: str, verdict: dict, args: argparse.Namespace) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries = {
        f"{policy}/{case}": _summary(rows, policy, case)
        for policy in POLICIES
        for case in sorted({r["case"] for r in rows if r["policy"] == policy})
    }
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hardware_ps200_peak_roll_deg": args.target_roll_deg,
        "identical_command_mesh_replay_peak_roll_deg":
            SIM_TRACE_PS200_PEAK_ROLL_DEG,
        "command_m_s": args.cmd,
        "episode_s": args.episode_s,
        "cases": [asdict(case) for case in cases],
        "rows": rows,
        "summaries": summaries,
        "selected_candidate": candidate,
        "selectivity_verdict": verdict,
    }
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2) + "\n")

    flat_rows = []
    for row in rows:
        flat = {k: v for k, v in row.items()
                if k not in ("intervention", "contact_duty", "max_air_s")}
        flat["contact_duty"] = json.dumps(row["contact_duty"])
        flat["max_air_s"] = json.dumps(row["max_air_s"])
        flat_rows.append(flat)
    with (out_dir / "rows.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)

    zero_lines = []
    for dose in (0, 1, 3, 5):
        name = "baseline" if dose == 0 else f"zero_frame_pm{dose}deg"
        s = _summary(rows, "ps200", name)
        zero_lines.append(
            f"| {dose} | {s['peak_abs_roll_median_deg']:.2f} | "
            f"{s['peak_abs_roll_range_deg'][0]:.2f}–"
            f"{s['peak_abs_roll_range_deg'][1]:.2f} | "
            f"{s['terminations']}/{s['n']} |")
    deadband_lines = []
    for dose in (1, 2, 3, 4, 6, 8, 12):
        name = "baseline" if dose == 1 else f"deadband_x{dose:g}"
        s = _summary(rows, "ps200", name)
        if not s:
            continue
        deadband_lines.append(
            f"| {dose}x | {s['peak_abs_roll_median_deg']:.2f} | "
            f"{s['peak_abs_roll_range_deg'][0]:.2f}–"
            f"{s['peak_abs_roll_range_deg'][1]:.2f} | "
            f"{s['terminations']}/{s['n']} |")
    loadtrig_lines = []
    for case in cases:
        if case.mechanism != "load_triggered":
            continue
        s = _summary(rows, "ps200", case.name)
        if not s:
            continue
        loadtrig_lines.append(
            f"| L{case.trigger_leg} | {case.force_threshold_n:g} | "
            f"{case.torque_peak_nm:.2f} | "
            f"{s['peak_abs_roll_median_deg']:.2f} | "
            f"{s['peak_abs_roll_range_deg'][0]:.2f}–"
            f"{s['peak_abs_roll_range_deg'][1]:.2f} | "
            f"{s['terminations']}/{s['n']} |")
    candidate_rows = []
    for policy in POLICIES:
        b = _summary(rows, policy, "baseline")
        c = _summary(rows, policy, candidate)
        candidate_rows.append(
            f"| {policy} | {b['peak_abs_roll_median_deg']:.2f} | "
            f"{c['peak_abs_roll_median_deg']:.2f} | "
            f"{c['forward_speed_median_m_s']:.3f} | "
            f"{c['terminations']}/{c['n']} |")
    decision = (
        "The mechanism passed the frozen-policy selectivity gate; a small "
        "matched-parent robustness training canary is justified."
        if verdict["fund_training"] else
        "The mechanism did not pass the frozen-policy selectivity gate; do "
        "not fund a training run on this physics yet."
    )
    report = f"""# PS200 sim-to-real causal probe

Generated {payload['generated_utc']} from exported deterministic 50 Hz actors
in the full mesh MuJoCo model. Command was pinned to {args.cmd:.2f} m/s after
the standard 1 s hold + 1 s ramp. Hardware target: {args.target_roll_deg:.2f}°
peak roll; prior identical-command mesh replay: {SIM_TRACE_PS200_PEAK_ROLL_DEG:.2f}°.

## Frame-coupled zero-offset dose

| uniform per-joint range (±°) | PS200 median peak (°) | range (°) | terminations |
|---:|---:|---:|---:|
{chr(10).join(zero_lines)}

## Deadband (backlash/post-encoder compliance) dose

Pinned per-joint deadband multiplier, the SAME calibrated real-hardware
`deadband_deg` (motor_model.json) that ordinary training DR already samples
up to 1.8x nominal — doses below go well past that ceiling.

| deadband multiplier | PS200 median peak (°) | range (°) | terminations |
|---:|---:|---:|---:|
{chr(10).join(deadband_lines)}

## Load-triggered (GRF-gated) recurrent torque dose

Same half-sine pulse shape as the recurrent-torque hypothesis (5.0 N·m,
0.3 s), but fired on a RISING per-leg ground-reaction-force edge (real
stance onset, one control tick of causal sensing latency) instead of a
fixed wall-clock schedule — the FAIL verdict's third named candidate.

| trigger leg | GRF threshold (N) | torque (N·m) | PS200 median peak (°) | range (°) | terminations |
|---|---:|---:|---:|---:|---:|
{chr(10).join(loadtrig_lines)}

## Best screened mechanism (static dose or recurrent phase-lock)

Selected `{candidate}` as the PS200 screen case closest to the hardware roll
scale, then reran it and baseline on all three frozen policies with the same
seeds and world intervention.

| policy | baseline peak (°) | candidate peak (°) | speed (m/s) | terminations |
|---|---:|---:|---:|---:|
{chr(10).join(candidate_rows)}

PS200 recurrent >5° peaks: **{verdict['recurrent_peaks']}**. Scale match:
**{verdict['scale_match']}**. Survived every seed: **{verdict['survived']}**.
Selective versus controls: **{verdict['selective']}**.

## Decision

{decision}

`results.json` contains every seed, signed roll extrema, recurrent-peak counts,
per-leg contact duty and longest air interval. `rows.csv` is the flat analysis
table. Support-loss and torque cases are causal probes, not claims that either
world edit is already a faithful component model.
"""
    (out_dir / "report.md").write_text(report)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", default="0,1,2,3")
    ap.add_argument("--episode-s", type=float, default=10.0)
    ap.add_argument("--cmd", type=float, default=0.10)
    ap.add_argument("--target-roll-deg", type=float,
                    default=HARDWARE_PS200_PEAK_ROLL_DEG)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    seeds = [int(v) for v in args.seeds.split(",") if v.strip()]
    if not seeds:
        ap.error("--seeds must not be empty")
    out_dir = args.out or (
        ROOT / "logs" / "ckpt_eval" /
        f"ps200_transfer_probe_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}")

    baseline = Intervention("baseline")
    zero_cases = [
        Intervention(f"zero_frame_pm{dose}deg", zero_range_deg=float(dose))
        for dose in (1, 3, 5)
    ]
    dropout_cases = [
        Intervention(
            f"support_L4_d{duration:.1f}_p{phase:.3f}",
            mechanism="support_loss", dropout_legs=(4,),
            duration_s=duration, phase_s=phase)
        for duration in (0.2, 0.3, 0.4)
        for phase in (0.0, 0.375, 0.75, 1.125)
    ]
    torque_cases = [
        Intervention(
            f"torque_pos{peak:.2f}_d0.3_p{phase:.3f}",
            mechanism="roll_torque", torque_peak_nm=peak,
            duration_s=0.3, phase_s=phase)
        # A 0.3 s pulse at the historical 2.6 N*m takeoff dose has only
        # one fifth the angular impulse of that 1.5 s calibration.  The
        # wider values bracket the ~10 N*m static gravitational moment of
        # an approximately 7 kg body displaced ~15 cm over a support edge;
        # they are a support-asymmetry proxy, not a proposed actuator torque.
        for peak in (2.6, 5.0, 7.5, 10.0, 12.5)
        for phase in (0.0, 0.375, 0.75, 1.125)
    ]
    deadband_cases = [
        Intervention(f"deadband_x{dose:g}", mechanism="deadband",
                     deadband_scale=float(dose))
        # Ordinary training DR already samples this SAME calibrated
        # per-joint deadband up to 1.8x nominal; these doses probe well
        # past that ceiling to screen the "post-encoder compliance /
        # backlash" candidate named as this probe's own Next step
        # (docs/PS200_TRANSFER_PROBE_2026-09-12.md), the same way
        # zero_range_deg screens the zero-offset candidate — a static
        # per-episode physical property, not a phase-locked world edit.
        for dose in (2, 3, 4, 6, 8, 12)
    ]
    load_triggered_cases = [
        Intervention(
            f"loadtrig_L{leg}_thr{thr:g}_peak{peak:.2f}_d{dur:.1f}",
            mechanism="load_triggered", trigger_leg=leg,
            force_threshold_n=thr, torque_peak_nm=peak, duration_s=dur)
        # Same half-sine pulse SHAPE/scale as the already-selected fixed-
        # schedule recurrent torque (5.0 N*m, 0.3 s) that passed the
        # frozen-policy gate, but now gated on a sensed per-leg GRF
        # crossing (real stance onset on the trigger leg) instead of a
        # blind wall-clock repeat -- the FAIL verdict's named "load-
        # triggered L4 stance-onset error" candidate. Screens both the
        # original L4 suspect and L1 (the other front-pair leg, in case
        # the mechanism is a front-pair rather than L4-specific effect)
        # across three GRF thresholds spanning "any contact" to "solidly
        # loaded" (contact-on convention elsewhere in this file is
        # force > 0.5 N; meaningful-contact conventions use ~1 N).
        for leg in (1, 4)
        for thr in (2.0, 5.0, 8.0)
        for peak in (5.0,)
        for dur in (0.3,)
    ]
    cases = [baseline, *zero_cases, *dropout_cases, *torque_cases,
             *deadband_cases, *load_triggered_cases]
    rows: list[dict] = []

    print("[1/4] PS200 baseline + frame-coupled zero panel")
    for case in (baseline, *zero_cases):
        for seed in seeds:
            row = rollout(POLICIES["ps200"], case, seed=seed,
                          episode_s=args.episode_s, cmd_m_s=args.cmd)
            rows.append(row)
        s = _summary(rows, "ps200", case.name)
        print(f"  {case.name:<24} peak median "
              f"{s['peak_abs_roll_median_deg']:5.2f} deg")

    print("[2/4] PS200 deadband (backlash) dose panel")
    for case in deadband_cases:
        for seed in seeds:
            row = rollout(POLICIES["ps200"], case, seed=seed,
                          episode_s=args.episode_s, cmd_m_s=args.cmd)
            rows.append(row)
        s = _summary(rows, "ps200", case.name)
        print(f"  {case.name:<24} peak median "
              f"{s['peak_abs_roll_median_deg']:5.2f} deg")

    print("[3/4] PS200 phase/GRF screens: L4 support loss, recurrent roll "
          "torque, load-triggered torque")
    screen_seed = seeds[0]
    screen_cases = (*dropout_cases, *torque_cases, *load_triggered_cases)
    for i, case in enumerate(screen_cases, start=1):
        rows.append(rollout(POLICIES["ps200"], case, seed=screen_seed,
                            episode_s=args.episode_s, cmd_m_s=args.cmd))
        if i % 6 == 0:
            print(f"  screened {i}/{len(screen_cases)}")

    best_dropout = _closest_case(rows, "support_loss", args.target_roll_deg)
    best_torque = _closest_case(rows, "roll_torque", args.target_roll_deg)
    best_deadband = _closest_case(rows, "deadband", args.target_roll_deg)
    best_load_triggered = _closest_case(
        rows, "load_triggered", args.target_roll_deg)
    finalists = [best_dropout, best_torque, best_deadband,
                best_load_triggered]
    # Fill each screen winner out to the requested seed panel (deadband
    # cases already ran the full seed panel in step 2/4, so this is a
    # no-op for it via the `done` seed-set check below).
    for name in finalists:
        case = _case_by_name(cases, name)
        done = {r["seed"] for r in rows
                if r["policy"] == "ps200" and r["case"] == name}
        for seed in seeds:
            if seed not in done:
                rows.append(rollout(
                    POLICIES["ps200"], case, seed=seed,
                    episode_s=args.episode_s, cmd_m_s=args.cmd))
    candidate = min(
        finalists,
        key=lambda name: abs(
            _summary(rows, "ps200", name)["peak_abs_roll_median_deg"]
            - args.target_roll_deg),
    )
    candidate_case = _case_by_name(cases, candidate)
    print(f"  support finalist:      {best_dropout}")
    print(f"  torque finalist:       {best_torque}")
    print(f"  deadband finalist:     {best_deadband}")
    print(f"  load-triggered finalist: {best_load_triggered}")
    print(f"  selected:              {candidate}")

    print("[4/4] Identical candidate + baseline on lower-roll controls")
    for policy_name in ("walkteach", "allheading"):
        for case in (baseline, candidate_case):
            for seed in seeds:
                rows.append(rollout(
                    POLICIES[policy_name], case, seed=seed,
                    episode_s=args.episode_s, cmd_m_s=args.cmd))
        b = _summary(rows, policy_name, "baseline")
        c = _summary(rows, policy_name, candidate)
        print(f"  {policy_name:<10} {b['peak_abs_roll_median_deg']:5.2f} -> "
              f"{c['peak_abs_roll_median_deg']:5.2f} deg")

    verdict = _selectivity(rows, candidate, args.target_roll_deg)
    _write_outputs(out_dir, rows, cases, candidate, verdict, args)
    print(json.dumps(verdict, indent=2))
    print(f"[probe_ps200_transfer] -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
