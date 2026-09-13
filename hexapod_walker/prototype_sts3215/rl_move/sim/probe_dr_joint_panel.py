"""Frozen-policy JOINT model-error sensitivity panel (speed sim-to-real).

Operator order 2026-09-13 (speed track redirect, `rl_docs/tracks/speed/
DESIGN.md` "Sim-to-real robustness direction"): the PS200 hardware run
peaked at 16.78 deg roll where the matched mesh replay peaked at 3.32 deg,
and every ONE-FACTOR frozen-policy probe (zero offset, deadband, support
loss, friction loss, recurrent/load-triggered/load-share torque) either
failed to reproduce the scale or was not learnable/selective.  This panel
tests what those probes could not: JOINTLY sampled, CORRELATED and
PER-LEG-ASYMMETRIC combinations of physically bounded model error, applied
as one fixed ensemble per rollout to the frozen PS200 fast parent and the
two lower-roll control policies.

Physical signature anchor (all hardware evidence reachable from this pod):

* command protocol `sysid/protocols/walk_rl_ps200_fwd100_oab_v1.json`
  (0.10 m/s forward 12 s, out-and-back, run 43a6a88a90f9);
* peak |roll| 16.78 deg with REPEATED same-direction excursions, no trip
  (25 deg guard never fired);
* matched nominal-sim replay peak roll 3.32 deg (closed-loop probe
  baseline 1.0-2.2 deg);
* the two deployed control gaits rolled visibly less on the same floor.

NAMED UNCERTAINTIES (recorded, not blockers, per the 09-13 order): the
hardware run's per-joint positions/currents/contact timings and its exact
achieved-speed number are not exported to this pod; forward-speed loss is
therefore reported but weighted low in ranking, and current pattern is not
scored.  Refine when Robot Lab exports more channels.

Ensembles are sampled deterministically from ``--panel-seed`` in three
modes (independent / correlated / asymmetric), each dimension inside the
physically bounded ``PanelBounds`` (units + provenance in the dataclass).
A fixed, pre-registered fraction of ensembles (index mod 3 == 2) plus the
rollout seeds {2,3,4} are HELD OUT: written to ``heldout_manifest.json``,
never rolled out or ranked here, reserved for the later robustness gate so
the trained DR arms cannot pass by memorizing the diagnostic set.

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_dr_joint_panel

Outputs ``panel_spec.json``, ``heldout_manifest.json``, ``results.json``,
``rows.csv`` and ``report.md`` beneath
``logs/ckpt_eval/dr_joint_panel_<UTC>`` unless ``--out`` is supplied.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import numpy as np

from rl_move.np_policy import load_np_policy
from rl_move.sim.domain_rand import (DEG2RAD, G0, N_LEGS, DomainRandomizer,
                                     EpisodeRandomization)
from rl_move.sim.probe_ps200_transfer import (
    HARDWARE_PS200_PEAK_ROLL_DEG, POLICIES, SIM_TRACE_PS200_PEAK_ROLL_DEG,
    Intervention, PolicySpec, _force_walk, _policy_cfg, _policy_path,
    _separated_peak_count)
from rl_move.sim.probe_walk_income import pin_command
from rl_move.sim.servo_model import N_JOINTS, SimServoParams, _act_id
from rl_move.sim.walk_task import SimHexapodJointWalkEnv

ROOT = Path(__file__).resolve().parents[2]

MODES = ("independent", "correlated", "asymmetric")
HELDOUT_STRIDE = 3            # ensemble index % 3 == 2 -> held out
SEARCH_SEEDS = (0, 1)         # panel/ranking rollout seeds
HELDOUT_SEEDS = (2, 3, 4)     # reserved for the later robustness gate
LEFT_LEGS = (0, 1, 2)         # tipped_roll sign convention: 3-5 = right
RIGHT_LEGS = (3, 4, 5)
FRONT_LEGS = (0, 5)           # load-share convention (probe addendum 3)
REAR_LEGS = (2, 3)


@dataclass(frozen=True)
class PanelBounds:
    """Physically bounded uncertainty, per DESIGN.md's six families.

    Provenance: "train DR" = the calibrated training ``RandRanges``
    defaults; "eng" = conservative engineering bound beyond training DR,
    justified inline.  Everything is a multiplicative scale unless the
    name carries a unit.  Bounds deliberately exceed training DR where a
    plausible physical story exists, and nowhere allow absurd physics.
    """
    # -- inertial (train DR mass 0.85-1.20, com 12 mm; eng: unmodeled
    #    cable loom / battery shift, as-built audit spread) --
    mass_scale: tuple[float, float] = (0.85, 1.25)
    com_xy_m: float = 0.025
    com_z_m: float = 0.015
    leg_mass_pct: float = 0.20          # train DR 0.10
    # -- geometry (train DR global 0.02 / per-leg 0.012; eng: print +
    #    assembly stack-up measured on Hexapod-2 family) --
    link_global_pct: float = 0.02
    link_leg_pct: float = 0.02
    # -- contact (train DR friction 0.6-1.4, stiffness 0.7-2.0; eng:
    #    smooth/dusty floor lower tail, worn pad + hard floor upper) --
    friction_scale: tuple[float, float] = (0.45, 1.40)
    foot_friction_scale: tuple[float, float] = (0.50, 1.10)  # per foot
    contact_stiff_scale: tuple[float, float] = (0.50, 3.00)
    ground_tilt_deg: tuple[float, float] = (0.0, 3.0)        # train DR 2.0
    # -- actuator (train DR kp 0.20 / kv 0.25 / torque 0.80-1.05 /
    #    vel 0.85-1.10; eng: unit spread + battery sag under gait load,
    #    STS3215 datasheet stall/voltage derating) --
    kp_pct: float = 0.35
    kv_pct: float = 0.40
    torque_scale: tuple[float, float] = (0.55, 1.05)
    leg_torque_scale: tuple[float, float] = (0.60, 1.05)     # per leg
    vel_scale: tuple[float, float] = (0.70, 1.10)
    # -- timing / sensing (train DR latency 0.7-1.8, drop 0.05; eng:
    #    bus congestion seen in 100 Hz transport era) --
    latency_scale: tuple[float, float] = (0.70, 2.50)
    cmd_drop_prob: tuple[float, float] = (0.0, 0.08)
    imu_bias_deg: float = 2.0                                # calib residual
    # -- joint mechanics (deadband train DR 0.5-1.8x calibrated
    #    motor_model.json; probe addendum screened static-uniform to 3x
    #    alone -- interactions untested; zero-offset probe screened
    #    frame-coupled +-5 deg alone) --
    deadband_scale: tuple[float, float] = (0.50, 3.00)
    zero_bias_deg: float = 5.0


@dataclass
class Ensemble:
    mode: str
    index: int
    split: str                     # "search" | "heldout"
    params: dict                   # JSON-serializable sampled values
    latents: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"{self.mode}_{self.index:03d}"


def neutral_params() -> dict:
    return {
        "mass_scale": 1.0,
        "com_offset_m": [0.0, 0.0, 0.0],
        "leg_mass_scale": np.ones((N_LEGS, 3)).tolist(),
        "link_scale": np.ones((N_LEGS, 3)).tolist(),
        "friction_scale": 1.0,
        "foot_friction_scale": [1.0] * N_LEGS,
        "contact_stiff_scale": 1.0,
        "ground_tilt_deg": 0.0,
        "ground_tilt_az_deg": 0.0,
        "kp_scale": [1.0] * N_JOINTS,
        "kv_scale": [1.0] * N_JOINTS,
        "torque_scale": 1.0,
        "leg_torque_scale": [1.0] * N_LEGS,
        "vel_scale": 1.0,
        "latency_scale": 1.0,
        "cmd_drop_prob": 0.0,
        "deadband_scale": 1.0,
        "joint_zero_bias_deg": [0.0] * N_JOINTS,
        "imu_bias_deg": [0.0, 0.0],
    }


def _leg_joints(leg: int) -> tuple[int, int, int]:
    return (3 * leg, 3 * leg + 1, 3 * leg + 2)


def _sample_independent(rng: np.random.Generator, b: PanelBounds) -> dict:
    """Every knob drawn independently -- joint interactions by volume."""
    u = rng.uniform
    p = neutral_params()
    p["mass_scale"] = float(u(*b.mass_scale))
    p["com_offset_m"] = [float(u(-b.com_xy_m, b.com_xy_m)),
                         float(u(-b.com_xy_m, b.com_xy_m)),
                         float(u(-b.com_z_m, b.com_z_m))]
    p["leg_mass_scale"] = u(1.0 - b.leg_mass_pct, 1.0 + b.leg_mass_pct,
                            (N_LEGS, 3)).tolist()
    g = u(1.0 - b.link_global_pct, 1.0 + b.link_global_pct)
    p["link_scale"] = (g * u(1.0 - b.link_leg_pct, 1.0 + b.link_leg_pct,
                             (N_LEGS, 3))).tolist()
    p["friction_scale"] = float(u(*b.friction_scale))
    p["foot_friction_scale"] = u(*b.foot_friction_scale, N_LEGS).tolist()
    p["contact_stiff_scale"] = float(u(*b.contact_stiff_scale))
    p["ground_tilt_deg"] = float(u(*b.ground_tilt_deg))
    p["ground_tilt_az_deg"] = float(u(0.0, 360.0))
    p["kp_scale"] = u(1.0 - b.kp_pct, 1.0 + b.kp_pct, N_JOINTS).tolist()
    p["kv_scale"] = u(1.0 - b.kv_pct, 1.0 + b.kv_pct, N_JOINTS).tolist()
    p["torque_scale"] = float(u(*b.torque_scale))
    p["leg_torque_scale"] = u(*b.leg_torque_scale, N_LEGS).tolist()
    p["vel_scale"] = float(u(*b.vel_scale))
    p["latency_scale"] = float(u(*b.latency_scale))
    p["cmd_drop_prob"] = float(u(*b.cmd_drop_prob))
    p["deadband_scale"] = float(u(*b.deadband_scale))
    p["joint_zero_bias_deg"] = u(-b.zero_bias_deg, b.zero_bias_deg,
                                 N_JOINTS).tolist()
    p["imu_bias_deg"] = u(-b.imu_bias_deg, b.imu_bias_deg, 2).tolist()
    return p


def _sample_correlated(rng: np.random.Generator,
                       b: PanelBounds) -> tuple[dict, dict]:
    """Latent physical stories couple many knobs at once.

    battery_sag: one supply sags under gait load -> torque AND speed drop
        together, latency rises (servo retries), all 18 joints coherently.
    worn_leg:    one leg's gearbox/linkage is worn -> that leg's kp/torque
        down, deadband-equivalent zero slop up, foot friction down.
    build_mass:  as-built mass error comes WITH a CoM shift and heavier
        leg hardware, not independently.
    floor:       a slick floor is usually also softer/duller and tilted.
    """
    u = rng.uniform
    p = neutral_params()
    lat = {
        "battery_sag": float(u(0.0, 1.0)),
        "worn_leg": int(rng.integers(0, N_LEGS)),
        "worn_leg_g": float(u(0.0, 1.0)),
        "build_mass_g": float(u(-1.0, 1.0)),
        "floor_g": float(u(0.0, 1.0)),
    }
    g = lat["battery_sag"]
    p["torque_scale"] = float(b.torque_scale[1]
                              - g * (b.torque_scale[1] - b.torque_scale[0]))
    p["vel_scale"] = float(b.vel_scale[1]
                           - g * (b.vel_scale[1] - b.vel_scale[0]))
    p["latency_scale"] = float(1.0 + g * (b.latency_scale[1] - 1.0)
                               * u(0.3, 1.0))
    p["kp_scale"] = (np.ones(N_JOINTS)
                     * (1.0 - g * b.kp_pct * u(0.0, 1.0))).tolist()

    w, wg = lat["worn_leg"], lat["worn_leg_g"]
    kp = np.asarray(p["kp_scale"])
    for j in _leg_joints(w):
        kp[j] *= 1.0 - wg * b.kp_pct
    p["kp_scale"] = kp.tolist()
    lts = np.ones(N_LEGS)
    lts[w] = 1.0 - wg * (1.0 - b.leg_torque_scale[0])
    p["leg_torque_scale"] = lts.tolist()
    zb = np.zeros(N_JOINTS)
    for j in _leg_joints(w):
        zb[j] = float(u(-1.0, 1.0)) * wg * b.zero_bias_deg
    p["joint_zero_bias_deg"] = zb.tolist()
    ffs = np.ones(N_LEGS)
    ffs[w] = 1.0 - wg * (1.0 - b.foot_friction_scale[0])
    p["foot_friction_scale"] = ffs.tolist()
    p["deadband_scale"] = float(1.0 + wg * (b.deadband_scale[1] - 1.0)
                                * u(0.0, 1.0))

    m = lat["build_mass_g"]
    mid = 0.5 * (b.mass_scale[0] + b.mass_scale[1])
    half = 0.5 * (b.mass_scale[1] - b.mass_scale[0])
    p["mass_scale"] = float(mid + m * half)
    p["com_offset_m"] = [float(m * b.com_xy_m * u(-1.0, 1.0)),
                         float(m * b.com_xy_m * u(-1.0, 1.0)),
                         float(m * b.com_z_m * u(-1.0, 1.0))]
    p["leg_mass_scale"] = (np.ones((N_LEGS, 3))
                           * (1.0 + m * b.leg_mass_pct
                              * u(0.0, 1.0))).tolist()

    f = lat["floor_g"]
    p["friction_scale"] = float(1.0 - f * (1.0 - b.friction_scale[0]))
    p["contact_stiff_scale"] = float(
        1.0 - f * (1.0 - b.contact_stiff_scale[0]))
    p["ground_tilt_deg"] = float(f * b.ground_tilt_deg[1] * u(0.0, 1.0))
    p["ground_tilt_az_deg"] = float(u(0.0, 360.0))
    return p, lat


def _sample_asymmetric(rng: np.random.Generator,
                       b: PanelBounds) -> tuple[dict, dict]:
    """Systematic per-side / per-leg-group manufacturing+wear asymmetry."""
    u = rng.uniform
    p = neutral_params()
    group_name, legs = [("left", LEFT_LEGS), ("right", RIGHT_LEGS),
                        ("front", FRONT_LEGS), ("rear", REAR_LEGS),
                        ("single", (int(rng.integers(0, N_LEGS)),))][
                            int(rng.integers(0, 5))]
    g = float(u(0.4, 1.0))          # asymmetry strength
    lat = {"group": group_name, "legs": list(legs), "strength": g}
    kp = np.ones(N_JOINTS)
    kv = np.ones(N_JOINTS)
    zb = np.zeros(N_JOINTS)
    lts = np.ones(N_LEGS)
    ffs = np.ones(N_LEGS)
    lms = np.ones((N_LEGS, 3))
    lnk = np.ones((N_LEGS, 3))
    for leg in legs:
        for j in _leg_joints(leg):
            kp[j] = 1.0 - g * b.kp_pct * u(0.5, 1.0)
            kv[j] = 1.0 + g * b.kv_pct * u(-1.0, 1.0)
            zb[j] = g * b.zero_bias_deg * u(-1.0, 1.0)
        lts[leg] = 1.0 - g * (1.0 - b.leg_torque_scale[0]) * u(0.5, 1.0)
        ffs[leg] = 1.0 - g * (1.0 - b.foot_friction_scale[0]) * u(0.5, 1.0)
        lms[leg] = 1.0 + g * b.leg_mass_pct * u(-1.0, 1.0, 3)
        lnk[leg] = 1.0 + g * b.link_leg_pct * u(-1.0, 1.0, 3)
    p.update(kp_scale=kp.tolist(), kv_scale=kv.tolist(),
             joint_zero_bias_deg=zb.tolist(),
             leg_torque_scale=lts.tolist(),
             foot_friction_scale=ffs.tolist(),
             leg_mass_scale=lms.tolist(), link_scale=lnk.tolist())
    # Mild global context so the asymmetry acts on a non-nominal robot.
    p["mass_scale"] = float(u(0.95, 1.15))
    p["friction_scale"] = float(u(0.7, 1.2))
    p["torque_scale"] = float(u(0.8, 1.05))
    p["latency_scale"] = float(u(0.9, 1.6))
    p["deadband_scale"] = float(u(0.8, 2.0))
    return p, lat


def sample_ensembles(panel_seed: int, n_per_mode: int,
                     bounds: PanelBounds | None = None) -> list[Ensemble]:
    """Deterministic ensemble list; split is a pure function of index."""
    b = bounds or PanelBounds()
    out: list[Ensemble] = []
    for mi, mode in enumerate(MODES):
        rng = np.random.default_rng([panel_seed, mi])
        for i in range(n_per_mode):
            if mode == "independent":
                p, lat = _sample_independent(rng, b), {}
            elif mode == "correlated":
                p, lat = _sample_correlated(rng, b)
            else:
                p, lat = _sample_asymmetric(rng, b)
            split = ("heldout" if i % HELDOUT_STRIDE == HELDOUT_STRIDE - 1
                     else "search")
            out.append(Ensemble(mode=mode, index=i, split=split,
                                params=p, latents=lat))
    return out


def ensemble_episode(base: EpisodeRandomization,
                     params: dict) -> EpisodeRandomization:
    """Overwrite a neutral (dr_scale=0) episode sample with the ensemble."""
    tilt = float(params["ground_tilt_deg"]) * DEG2RAD
    az = float(params["ground_tilt_az_deg"]) * DEG2RAD
    grade = np.array([math.tan(tilt) * math.cos(az),
                      math.tan(tilt) * math.sin(az), -1.0])
    gravity = G0 * grade / np.linalg.norm(grade)
    return dataclasses.replace(
        base,
        mass_scale=float(params["mass_scale"]),
        com_offset_m=np.asarray(params["com_offset_m"], dtype=float),
        leg_mass_scale=np.asarray(params["leg_mass_scale"], dtype=float),
        link_scale=np.asarray(params["link_scale"], dtype=float),
        friction_scale=float(params["friction_scale"]),
        contact_stiff_scale=float(params["contact_stiff_scale"]),
        gravity_vec=gravity,
        kp_scale=np.asarray(params["kp_scale"], dtype=float),
        kv_scale=np.asarray(params["kv_scale"], dtype=float),
        torque_scale=float(params["torque_scale"]),
        latency_scale=float(params["latency_scale"]),
        deadband_scale=float(params["deadband_scale"]),
        vel_scale=float(params["vel_scale"]),
        cmd_drop_prob=float(params["cmd_drop_prob"]),
        joint_zero_bias_rad=np.asarray(params["joint_zero_bias_deg"],
                                       dtype=float) * DEG2RAD,
        zero_drift_cmd_frame=True,
        imu_bias_rad=np.asarray(params["imu_bias_deg"],
                                dtype=float) * DEG2RAD,
    )


class FixedEnsembleRandomizer(DomainRandomizer):
    """Returns the SAME ensemble episode every reset (frozen diagnostic)."""

    def __init__(self, params: dict):
        super().__init__(None, scale=0.0)
        self._ens_params = params

    def sample(self, rng: np.random.Generator) -> EpisodeRandomization:
        return ensemble_episode(super().sample(rng), self._ens_params)


class PanelEnv(SimHexapodJointWalkEnv):
    """Walk env + post-reset per-foot friction / per-leg torque asymmetry.

    ``EpisodeRandomization`` has no per-foot friction or per-leg torque
    saturation field, so these two panel dimensions are applied as direct
    MjModel edits AFTER reset (the same field-edit recipe as
    ``apply_fault_to_model`` and the friction_loss intervention).  Ground
    friction combines by element-wise max, so a foot dosed below the floor
    coefficient also caps the floor -- effective values are recorded.
    """

    def __init__(self, *args, panel_params: dict, **kwargs):
        self._panel_params = panel_params
        super().__init__(*args, **kwargs)
        self.effective_foot_friction: list[float] = []

    def reset(self, *args, **kwargs):
        out = super().reset(*args, **kwargs)
        p = self._panel_params
        mj = self._mujoco
        model = self.model
        ffs = np.asarray(p["foot_friction_scale"], dtype=float)
        if np.any(ffs != 1.0):
            foot_gids = []
            for leg in range(N_LEGS):
                gid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM,
                                    f"L{leg}_foot")
                if gid < 0:
                    raise ValueError(f"model has no L{leg}_foot geom")
                foot_gids.append(gid)
            ground_gids = [g for g in (
                mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, n)
                for n in ("floor", "terrain")) if g >= 0]
            if not ground_gids:
                raise ValueError("model has no floor or terrain geom")
            dosed = model.geom_friction[foot_gids, 0] * ffs
            model.geom_friction[foot_gids, 0] = dosed
            cap = float(np.min(dosed))
            for g in ground_gids:
                model.geom_friction[g, 0] = min(
                    float(model.geom_friction[g, 0]), cap)
            ground = max(float(model.geom_friction[g, 0])
                         for g in ground_gids)
            self.effective_foot_friction = [
                round(max(float(v), ground), 4) for v in dosed]
        lts = np.asarray(p["leg_torque_scale"], dtype=float)
        if np.any(lts != 1.0):
            from rl_move.sim.servo_model import joint_names
            names = joint_names()
            for leg in range(N_LEGS):
                s = float(lts[leg])
                if s == 1.0:
                    continue
                for j in _leg_joints(leg):
                    pa = _act_id(model, names[j])
                    va = _act_id(model, names[j] + "_d")
                    model.actuator_forcerange[pa] *= s
                    model.actuator_forcerange[va] *= s
        return out


def rollout(spec: PolicySpec, ens: Ensemble | None, *, seed: int,
            episode_s: float, cmd_m_s: float) -> dict:
    """One frozen-policy episode under one fixed ensemble (None=nominal)."""
    policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, Intervention(name="panel"))
    params = ens.params if ens is not None else neutral_params()
    env = PanelEnv(
        params=SimServoParams.from_cfg(cfg),
        randomizer=FixedEnsembleRandomizer(params),
        episode_seconds=episode_s, seed=seed, cfg=cfg,
        panel_params=params)
    _force_walk(env)
    obs, _info = env.reset()
    if obs.shape != policy.observation_space.shape:
        raise RuntimeError(f"{spec.name}: obs {obs.shape} != policy "
                           f"{policy.observation_space.shape}")
    pin_command(env, cmd_m_s, 0.0, 0.0)
    policy.reset()

    hz = float(policy.meta["control_hz"])
    rolls: list[float] = []
    contact_ticks = np.zeros(6, dtype=int)
    contact_seen = np.zeros(6, dtype=int)
    min_contact_feet = 6
    x0 = float(env.data.xpos[env._chassis_bid, 0])
    x_walk = None
    x_final = x0
    term_reason = ""
    ticks = 0
    try:
        while True:
            t_s = env._step_i * env.dt
            action, _ = policy.predict(obs, deterministic=True)
            obs, _r, terminated, truncated, info = env.step(action)
            ticks += 1
            rolls.append(float(info.get("roll_rel_deg", 0.0)))
            if t_s >= 2.0 and x_walk is None:
                x_walk = float(env.data.xpos[env._chassis_bid, 0])
            x_final = float(env.data.xpos[env._chassis_bid, 0])
            contacts = [bool(info[f"walk_foot{leg}_contact"])
                        for leg in range(6)
                        if f"walk_foot{leg}_contact" in info]
            for leg, on in enumerate(contacts):
                contact_seen[leg] += 1
                contact_ticks[leg] += int(on)
            if contacts:
                min_contact_feet = min(min_contact_feet, sum(contacts))
            if terminated or truncated:
                term_reason = str(info.get("termination_reason") or "")
                break
    finally:
        eff_fric = list(env.effective_foot_friction)
        env.close()

    abs_rolls = [abs(v) for v in rolls]
    duty = [float(contact_ticks[i] / max(contact_seen[i], 1))
            for i in range(6)]
    elapsed_walk = max(ticks / hz - 2.0, 1e-9)
    x_walk = x_final if x_walk is None else x_walk
    return {
        "policy": spec.name,
        "ensemble": ens.name if ens is not None else "nominal",
        "mode": ens.mode if ens is not None else "nominal",
        "split": ens.split if ens is not None else "baseline",
        "seed": seed,
        "ticks": ticks,
        "terminated": bool(term_reason),
        "termination_reason": term_reason,
        "peak_abs_roll_deg": round(max(abs_rolls, default=0.0), 3),
        "rms_roll_deg": round(float(np.sqrt(np.mean(np.square(rolls))))
                              if rolls else 0.0, 3),
        "positive_peaks_over_5deg": _separated_peak_count(
            rolls, threshold=5.0, dt=1.0 / hz),
        "negative_peaks_over_5deg": _separated_peak_count(
            [-v for v in rolls], threshold=5.0, dt=1.0 / hz),
        "forward_speed_after_2s_m_s": round(
            (x_final - x_walk) / elapsed_walk, 4),
        "min_contact_feet": min_contact_feet,
        "contact_duty_spread": round(max(duty) - min(duty), 3) if contact_seen.any() else 0.0,
        "contact_duty": [round(d, 3) for d in duty],
        "effective_foot_friction": eff_fric,
    }


def _med(rows: list[dict], key: str) -> float:
    vals = [r[key] for r in rows]
    return float(median(vals)) if vals else 0.0


def summarize(rows: list[dict], policy: str, ensemble: str) -> dict:
    grp = [r for r in rows
           if r["policy"] == policy and r["ensemble"] == ensemble]
    if not grp:
        return {}
    return {
        "policy": policy,
        "ensemble": ensemble,
        "n": len(grp),
        "med_peak_abs_roll_deg": round(_med(grp, "peak_abs_roll_deg"), 3),
        "med_rms_roll_deg": round(_med(grp, "rms_roll_deg"), 3),
        "med_recurrent_peaks": round(median(
            max(r["positive_peaks_over_5deg"],
                r["negative_peaks_over_5deg"]) for r in grp), 1),
        "med_speed_m_s": round(_med(grp, "forward_speed_after_2s_m_s"), 4),
        "med_duty_spread": round(_med(grp, "contact_duty_spread"), 3),
        "fall_frac": round(sum(r["terminated"] for r in grp) / len(grp), 3),
    }


def provisional_score(ps: dict, nominal_speed: float) -> float:
    """Stage-1 ranking on the fast parent only (no controls yet).

    Signature: peak roll near 16.78 deg, repeated >=5 deg same-direction
    excursions, NO fall (hardware never tripped the 25 deg guard), and no
    speed GAIN (hardware surely did not speed up; exact loss unknown --
    named uncertainty, weighted low).
    """
    if not ps:
        return 0.0
    roll = ps["med_peak_abs_roll_deg"]
    roll_score = max(0.0, 1.0 - abs(roll - HARDWARE_PS200_PEAK_ROLL_DEG)
                     / HARDWARE_PS200_PEAK_ROLL_DEG)
    recur_score = min(ps["med_recurrent_peaks"] / 3.0, 1.0)
    nofall_score = 1.0 - ps["fall_frac"]
    speed_pen = (0.15 if nominal_speed > 0
                 and ps["med_speed_m_s"] > 1.10 * nominal_speed else 0.0)
    return round(0.55 * roll_score + 0.25 * recur_score
                 + 0.20 * nofall_score - speed_pen, 4)


def signature_score(ps: dict, ctrls: list[dict],
                    nominal_speed: float) -> dict:
    """Stage-2 score: stage-1 signature + control selectivity.

    The two control gaits rolled visibly less on the same floor, so a
    candidate REAL-model-error ensemble should reproduce that ordering:
    big parent roll, materially smaller control roll.
    """
    base = provisional_score(ps, nominal_speed)
    ctrl_max = max((c["med_peak_abs_roll_deg"] for c in ctrls if c),
                   default=0.0)
    ratio = (ps["med_peak_abs_roll_deg"] / ctrl_max
             if ctrl_max > 1e-6 else float("inf"))
    select_score = max(0.0, min((ratio - 1.0) / 0.5, 1.0))
    return {
        "stage1_score": base,
        "control_max_roll_deg": round(ctrl_max, 3),
        "parent_over_control_ratio": (round(ratio, 3)
                                      if math.isfinite(ratio) else None),
        "selectivity_score": round(select_score, 4),
        "final_score": round(0.75 * base + 0.25 * select_score, 4),
    }


def _write_outputs(out_dir: Path, *, args, bounds: PanelBounds,
                   ensembles: list[Ensemble], rows: list[dict],
                   ranking: list[dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = {
        "panel_seed": args.panel_seed,
        "n_per_mode": args.n_per_mode,
        "modes": MODES,
        "bounds": dataclasses.asdict(bounds),
        "search_seeds": SEARCH_SEEDS,
        "heldout_seeds": HELDOUT_SEEDS,
        "heldout_rule": f"index % {HELDOUT_STRIDE} == {HELDOUT_STRIDE - 1}",
        "episode_s": args.episode_s,
        "cmd_m_s": args.cmd,
        "hardware_anchor": {
            "peak_roll_deg": HARDWARE_PS200_PEAK_ROLL_DEG,
            "matched_sim_peak_roll_deg": SIM_TRACE_PS200_PEAK_ROLL_DEG,
            "protocol": "sysid/protocols/walk_rl_ps200_fwd100_oab_v1.json",
            "named_uncertainties": [
                "hardware per-joint position/current/contact traces not "
                "exported to this pod",
                "hardware achieved-speed number not exported; speed loss "
                "reported, weighted low",
                "control policies' hardware roll magnitudes not "
                "quantified; ordering (visibly lower) used only",
            ],
        },
        "ensembles": [dataclasses.asdict(e) for e in ensembles],
    }
    (out_dir / "panel_spec.json").write_text(json.dumps(spec, indent=1))
    heldout = {
        "purpose": "Robustness-gate evaluation set. NEVER use for "
                   "structured-DR fitting, ranking or model selection; "
                   "the trained DR arms' held-out gate runs these "
                   "ensembles x heldout seeds only.",
        "heldout_seeds": HELDOUT_SEEDS,
        "episode_s": args.episode_s,
        "cmd_m_s": args.cmd,
        "ensembles": [dataclasses.asdict(e) for e in ensembles
                      if e.split == "heldout"],
    }
    (out_dir / "heldout_manifest.json").write_text(
        json.dumps(heldout, indent=1))
    (out_dir / "results.json").write_text(json.dumps(
        {"rows": rows, "ranking": ranking}, indent=1))
    if rows:
        keys = [k for k in rows[0] if k not in ("contact_duty",
                                                "effective_foot_friction")]
        with (out_dir / "rows.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    lines = ["# DR joint sensitivity panel", "",
             f"panel_seed={args.panel_seed} n_per_mode={args.n_per_mode} "
             f"episode_s={args.episode_s} cmd={args.cmd}",
             "", "| rank | ensemble | mode | ps200 roll | recur | falls |"
             " speed | ctrl max roll | ratio | final |",
             "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for i, r in enumerate(ranking):
        s = r.get("score", {})
        p = r.get("ps200", {})
        lines.append(
            f"| {i + 1} | {r['ensemble']} | {r['mode']} "
            f"| {p.get('med_peak_abs_roll_deg', '')} "
            f"| {p.get('med_recurrent_peaks', '')} "
            f"| {p.get('fall_frac', '')} | {p.get('med_speed_m_s', '')} "
            f"| {s.get('control_max_roll_deg', '')} "
            f"| {s.get('parent_over_control_ratio', '')} "
            f"| {s.get('final_score', s.get('stage1_score', ''))} |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--panel-seed", type=int, default=20260913)
    ap.add_argument("--n-per-mode", type=int, default=16)
    ap.add_argument("--episode-s", type=float, default=14.0)
    ap.add_argument("--cmd", type=float, default=0.10)
    ap.add_argument("--top-k", type=int, default=12,
                    help="stage-2 (controls) candidates")
    ap.add_argument("--quick", action="store_true",
                    help="tiny smoke: 2 ensembles/mode, 1 seed, 6 s")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if args.quick:
        args.n_per_mode = 2
        args.episode_s = 6.0
        args.top_k = 2
    seeds = SEARCH_SEEDS[:1] if args.quick else SEARCH_SEEDS

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = args.out or (ROOT / "logs" / "ckpt_eval"
                           / f"dr_joint_panel_{stamp}")
    bounds = PanelBounds()
    ensembles = sample_ensembles(args.panel_seed, args.n_per_mode, bounds)
    search = [e for e in ensembles if e.split == "search"]
    rows: list[dict] = []

    # Baselines: all three policies, nominal model.
    for pname, spec in POLICIES.items():
        for seed in seeds:
            rows.append(rollout(spec, None, seed=seed,
                                episode_s=args.episode_s, cmd_m_s=args.cmd))
            print(f"[baseline] {pname} seed={seed} "
                  f"roll={rows[-1]['peak_abs_roll_deg']} "
                  f"v={rows[-1]['forward_speed_after_2s_m_s']}", flush=True)
    nominal_speed = summarize(rows, "ps200", "nominal").get(
        "med_speed_m_s", 0.0)

    # Stage 1: fast parent across every SEARCH ensemble.
    for e in search:
        for seed in seeds:
            rows.append(rollout(POLICIES["ps200"], e, seed=seed,
                                episode_s=args.episode_s, cmd_m_s=args.cmd))
        s = summarize(rows, "ps200", e.name)
        print(f"[stage1] {e.name} roll={s['med_peak_abs_roll_deg']} "
              f"peaks={s['med_recurrent_peaks']} falls={s['fall_frac']} "
              f"v={s['med_speed_m_s']}", flush=True)

    ranked = sorted(
        ({"ensemble": e.name, "mode": e.mode,
          "ps200": summarize(rows, "ps200", e.name)} for e in search),
        key=lambda r: provisional_score(r["ps200"], nominal_speed),
        reverse=True)
    for r in ranked:
        r["score"] = {"stage1_score":
                      provisional_score(r["ps200"], nominal_speed)}

    # Stage 2: controls on the top-k signature candidates.
    by_name = {e.name: e for e in ensembles}
    for r in ranked[:args.top_k]:
        e = by_name[r["ensemble"]]
        for pname in ("walkteach", "allheading"):
            for seed in seeds:
                rows.append(rollout(POLICIES[pname], e, seed=seed,
                                    episode_s=args.episode_s,
                                    cmd_m_s=args.cmd))
        ctrls = [summarize(rows, p, e.name)
                 for p in ("walkteach", "allheading")]
        r["controls"] = ctrls
        r["score"] = signature_score(r["ps200"], ctrls, nominal_speed)
        print(f"[stage2] {e.name} final={r['score']['final_score']} "
              f"ratio={r['score']['parent_over_control_ratio']}",
              flush=True)

    # Control-tested (stage-2) ensembles rank above stage-1-only ones:
    # a signature candidate REQUIRES selectivity evidence.
    ranked.sort(key=lambda r: ("final_score" in r["score"],
                               r["score"].get(
                                   "final_score",
                                   r["score"].get("stage1_score", 0.0))),
                reverse=True)
    _write_outputs(out_dir, args=args, bounds=bounds, ensembles=ensembles,
                   rows=rows, ranking=ranked)
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
