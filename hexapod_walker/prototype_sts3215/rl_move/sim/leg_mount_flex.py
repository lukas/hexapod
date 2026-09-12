"""Opt-in passive compliance at the six leg mounts.

The existing :mod:`struct_compliance` approximation reduces actuator gains,
but it does not add a physical state which can store and release elastic
energy.  This module provides the smallest dynamic alternative: one passive
pitch hinge at each yaw-output body.  The hinge is hidden from the 18-joint
robot contract; it rotates the complete downstream leg about the mount's
local Y axis while the named yaw/pitch/knee joints and actuators stay intact.

Nothing here selects the feature globally.  Call :func:`from_cfg`, then pass
the returned spec to :func:`apply_to_mjspec` before compiling a MuJoCo model.
Missing ``leg_mount_flex`` configuration is deliberately a no-op.  Once
enabled, every physical value is required so an experiment cannot silently
inherit invented stiffness or damping values.

Configuration (a scalar broadcasts to all six legs):

.. code-block:: yaml

   leg_mount_flex:
     enabled: 1
     stiffness_nm_rad: [20, 20, 20, 20, 20, 20]
     damping_nms_rad: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
     frictionloss_nm: [0, 0, 0, 0, 0, 0]
     springref_deg: [0, 0, 0, 0, 0, 0]
     range_deg: [[-15, 15], [-15, 15], [-15, 15],
                 [-15, 15], [-15, 15], [-15, 15]]

``springref_deg`` is the unloaded spring reference, not a geometry offset.
The XML pose and its keyframes retain flex coordinate zero.  A non-zero
spring reference therefore represents preload and must lie inside the joint
range.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from rl_move.config import cfg_get


N_LEGS = 6
JOINT_NAMES = tuple(f"L{i}_mount_flex" for i in range(N_LEGS))


def _required(cfg: dict, key: str) -> Any:
    value = cfg_get(cfg, "leg_mount_flex", key, default=None)
    if value is None:
        raise ValueError(
            "leg_mount_flex.enabled=1 requires explicit "
            f"leg_mount_flex.{key}")
    return value


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray))


def _per_leg_scalar(value: Any, *, key: str) -> tuple[float, ...]:
    if _is_sequence(value):
        if len(value) != N_LEGS:
            raise ValueError(
                f"leg_mount_flex.{key} must be a scalar or {N_LEGS} values")
        raw = value
    else:
        raw = [value] * N_LEGS
    try:
        out = tuple(float(v) for v in raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"leg_mount_flex.{key} values must be numeric") from exc
    if not all(math.isfinite(v) for v in out):
        raise ValueError(f"leg_mount_flex.{key} values must be finite")
    return out


def _per_leg_range(value: Any) -> tuple[tuple[float, float], ...]:
    key = "range_deg"
    # A positive scalar is a symmetric half-range shared by every leg.
    if not _is_sequence(value):
        half = _per_leg_scalar(value, key=key)[0]
        ranges = ((-half, half),) * N_LEGS
    elif len(value) == 2 and not any(_is_sequence(v) for v in value):
        # One explicit [lower, upper] pair shared by every leg.
        try:
            pair = tuple(float(v) for v in value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "leg_mount_flex.range_deg values must be numeric") from exc
        ranges = (pair,) * N_LEGS
    elif len(value) == N_LEGS and not any(_is_sequence(v) for v in value):
        # Six positive half-ranges, one per leg.
        halves = _per_leg_scalar(value, key=key)
        ranges = tuple((-v, v) for v in halves)
    elif len(value) == N_LEGS and all(
            _is_sequence(v) and len(v) == 2 for v in value):
        try:
            ranges = tuple((float(v[0]), float(v[1])) for v in value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "leg_mount_flex.range_deg values must be numeric") from exc
    else:
        raise ValueError(
            "leg_mount_flex.range_deg must be a half-range scalar, one "
            "[lower, upper] pair, six half-ranges, or six pairs")
    if not all(math.isfinite(lo) and math.isfinite(hi)
               for lo, hi in ranges):
        raise ValueError("leg_mount_flex.range_deg values must be finite")
    # qpos=0 is the geometry/keyframe reference and must be strictly inside
    # the safety stop rather than born on an active limit constraint.
    if not all(lo < 0.0 < hi for lo, hi in ranges):
        raise ValueError(
            "every leg_mount_flex.range_deg interval must contain 0 "
            "strictly (the nominal geometry coordinate)")
    return ranges


@dataclass(frozen=True)
class LegMountFlexSpec:
    """Validated six-leg passive-hinge parameters in user-facing units."""

    stiffness_nm_rad: tuple[float, ...]
    damping_nms_rad: tuple[float, ...]
    frictionloss_nm: tuple[float, ...]
    springref_deg: tuple[float, ...]
    range_deg: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        scalar_fields = (
            ("stiffness_nm_rad", self.stiffness_nm_rad),
            ("damping_nms_rad", self.damping_nms_rad),
            ("frictionloss_nm", self.frictionloss_nm),
            ("springref_deg", self.springref_deg),
        )
        for name, values in scalar_fields:
            if len(values) != N_LEGS or not all(
                    math.isfinite(float(v)) for v in values):
                raise ValueError(f"{name} must contain {N_LEGS} finite values")
        if (len(self.range_deg) != N_LEGS
                or not all(_is_sequence(pair) and len(pair) == 2
                           for pair in self.range_deg)):
            raise ValueError(f"range_deg must contain {N_LEGS} pairs")
        if not all(float(v) > 0.0 for v in self.stiffness_nm_rad):
            raise ValueError("stiffness_nm_rad must be > 0 for every leg")
        if not all(float(v) >= 0.0 for v in self.damping_nms_rad):
            raise ValueError("damping_nms_rad must be >= 0 for every leg")
        if not all(float(v) >= 0.0 for v in self.frictionloss_nm):
            raise ValueError("frictionloss_nm must be >= 0 for every leg")
        for leg, ((lo, hi), ref) in enumerate(
                zip(self.range_deg, self.springref_deg)):
            lo, hi, ref = float(lo), float(hi), float(ref)
            if not (math.isfinite(lo) and math.isfinite(hi)
                    and lo < 0.0 < hi):
                raise ValueError(
                    f"range_deg[{leg}] must contain 0 strictly")
            if not lo <= ref <= hi:
                raise ValueError(
                    f"springref_deg[{leg}]={ref} is outside range "
                    f"[{lo}, {hi}]")

    def summary(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "joint_names": list(JOINT_NAMES),
            "stiffness_nm_rad": list(self.stiffness_nm_rad),
            "damping_nms_rad": list(self.damping_nms_rad),
            "frictionloss_nm": list(self.frictionloss_nm),
            "springref_deg": list(self.springref_deg),
            "range_deg": [list(v) for v in self.range_deg],
        }


def from_cfg(cfg: dict | None) -> LegMountFlexSpec | None:
    """Return a validated flex spec, or ``None`` when explicitly/default off."""
    cfg = cfg or {}
    raw_enabled = cfg_get(cfg, "leg_mount_flex", "enabled", default=0.0)
    try:
        enabled = float(raw_enabled)
    except (TypeError, ValueError) as exc:
        raise ValueError("leg_mount_flex.enabled must be 0 or 1") from exc
    if enabled == 0.0:
        return None
    if enabled != 1.0:
        raise ValueError("leg_mount_flex.enabled must be exactly 0 or 1")

    stiffness = _per_leg_scalar(
        _required(cfg, "stiffness_nm_rad"), key="stiffness_nm_rad")
    damping = _per_leg_scalar(
        _required(cfg, "damping_nms_rad"), key="damping_nms_rad")
    friction = _per_leg_scalar(
        _required(cfg, "frictionloss_nm"), key="frictionloss_nm")
    springref = _per_leg_scalar(
        _required(cfg, "springref_deg"), key="springref_deg")
    ranges = _per_leg_range(_required(cfg, "range_deg"))
    return LegMountFlexSpec(
        stiffness_nm_rad=stiffness,
        damping_nms_rad=damping,
        frictionloss_nm=friction,
        springref_deg=springref,
        range_deg=ranges,
    )


def _joint_width(joint_type: int, *, velocity: bool = False) -> int:
    """qpos/qvel width for one compiled MuJoCo joint type."""
    import mujoco

    jt = int(joint_type)
    if jt == int(mujoco.mjtJoint.mjJNT_FREE):
        return 6 if velocity else 7
    if jt == int(mujoco.mjtJoint.mjJNT_BALL):
        return 3 if velocity else 4
    return 1


def _compiled_joint_map(model, *, velocity: bool = False) -> dict[str, tuple[int, int]]:
    import mujoco

    addrs = model.jnt_dofadr if velocity else model.jnt_qposadr
    out: dict[str, tuple[int, int]] = {}
    for jid in range(model.njnt):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, jid)
        if not name:
            raise ValueError(
                "leg mount flex requires every pre-existing joint to be named")
        out[name] = (int(addrs[jid]), _joint_width(
            model.jnt_type[jid], velocity=velocity))
    return out


def _remap_key_vector(old: np.ndarray, *, old_model, new_model,
                      velocity: bool) -> np.ndarray:
    expected = old_model.nv if velocity else old_model.nq
    if old.size != expected:
        kind = "qvel" if velocity else "qpos"
        raise ValueError(
            f"keyframe {kind} has {old.size} values; expected {expected}")
    if velocity:
        new = np.zeros(new_model.nv, dtype=float)
    else:
        # Preserve the valid identity quaternion and any non-zero joint refs.
        new = np.asarray(new_model.qpos0, dtype=float).copy()
    old_map = _compiled_joint_map(old_model, velocity=velocity)
    new_map = _compiled_joint_map(new_model, velocity=velocity)
    for name, (old_addr, width) in old_map.items():
        if name not in new_map:
            raise ValueError(f"pre-existing joint {name!r} vanished during flex rewrite")
        new_addr, new_width = new_map[name]
        if new_width != width:
            raise ValueError(f"joint {name!r} changed width during flex rewrite")
        new[new_addr:new_addr + width] = old[old_addr:old_addr + width]
    # New flex coordinates intentionally remain zero.  springref is passive
    # preload, not a keyframe geometry offset (see module docstring).
    return new


def apply_to_mjspec(mj_spec, flex: LegMountFlexSpec | None):
    """Add six passive mount hinges to a ``mujoco.MjSpec`` in place.

    Existing keyframe qpos/qvel vectors are remapped by *joint name*, not by
    assuming the free-root-plus-18 layout.  This matters because adding a
    joint to ``L{i}_yaw`` interleaves it between yaw and pitch in compiled
    qpos; MuJoCo otherwise pads six zeroes at the end and silently assigns
    every keyframe angle after L0 yaw to the wrong joint.

    Returns the same ``MjSpec`` for convenient composition with the existing
    foot-radius compilation path.
    """
    if flex is None:
        return mj_spec

    import mujoco

    old_model = mj_spec.compile()
    old_keys: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for key in mj_spec.keys:
        qpos = np.asarray(list(key.qpos), dtype=float)
        qvel = np.asarray(list(key.qvel), dtype=float)
        old_keys[key.name] = (qpos, qvel)

    for leg, name in enumerate(JOINT_NAMES):
        if mujoco.mj_name2id(
                old_model, mujoco.mjtObj.mjOBJ_JOINT, name) >= 0:
            raise ValueError(f"leg mount flex joint {name!r} already exists")
        yaw_name = f"L{leg}_yaw"
        if mujoco.mj_name2id(
                old_model, mujoco.mjtObj.mjOBJ_JOINT, yaw_name) < 0:
            raise ValueError(f"required active joint {yaw_name!r} is missing")
        body = mj_spec.body(yaw_name)
        if body is None:
            raise ValueError(f"required body {yaw_name!r} is missing")
        lo_deg, hi_deg = flex.range_deg[leg]
        body.add_joint(
            name=name,
            type=mujoco.mjtJoint.mjJNT_HINGE,
            pos=[0.0, 0.0, 0.0],
            axis=[0.0, 1.0, 0.0],
            ref=0.0,
            stiffness=flex.stiffness_nm_rad[leg],
            springref=math.radians(flex.springref_deg[leg]),
            limited=True,
            range=[math.radians(lo_deg), math.radians(hi_deg)],
            armature=0.0,
            damping=flex.damping_nms_rad[leg],
            frictionloss=flex.frictionloss_nm[leg],
        )

    # Compile once to obtain the topology's authoritative new addresses.
    # At this point MuJoCo has only padded old key vectors; never return this
    # intermediate model to a caller.
    new_model = mj_spec.compile()
    for key in mj_spec.keys:
        old_qpos, old_qvel = old_keys[key.name]
        if old_qpos.size:
            key.qpos = _remap_key_vector(
                old_qpos, old_model=old_model, new_model=new_model,
                velocity=False).tolist()
        if old_qvel.size:
            key.qvel = _remap_key_vector(
                old_qvel, old_model=old_model, new_model=new_model,
                velocity=True).tolist()
    return mj_spec


@dataclass(frozen=True)
class LegMountFlexAddresses:
    joint_ids: tuple[int, ...]
    qpos_addrs: tuple[int, ...]
    dof_addrs: tuple[int, ...]


def addresses(model, *, required: bool = True) -> LegMountFlexAddresses | None:
    """Resolve the six hidden flex coordinates by name.

    With ``required=False``, a fully rigid model returns ``None``.  A partial
    installation always raises because it would make per-leg diagnostics
    misleading.
    """
    import mujoco

    jids = tuple(int(mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_JOINT, name)) for name in JOINT_NAMES)
    present = tuple(j >= 0 for j in jids)
    if not any(present):
        if required:
            raise ValueError("model has no leg mount flex joints")
        return None
    if not all(present):
        missing = [name for name, ok in zip(JOINT_NAMES, present) if not ok]
        raise ValueError(f"model has an incomplete leg mount flex set: {missing}")
    return LegMountFlexAddresses(
        joint_ids=jids,
        qpos_addrs=tuple(int(model.jnt_qposadr[j]) for j in jids),
        dof_addrs=tuple(int(model.jnt_dofadr[j]) for j in jids),
    )


def diagnostics(model, data) -> dict[str, Any]:
    """Serializable hidden-flex state for replay/calibration artifacts."""
    addrs = addresses(model, required=False)
    if addrs is None:
        return {"enabled": False}
    qaddr = np.asarray(addrs.qpos_addrs, dtype=int)
    daddr = np.asarray(addrs.dof_addrs, dtype=int)
    jids = np.asarray(addrs.joint_ids, dtype=int)
    q = np.asarray(data.qpos[qaddr], dtype=float)
    qd = np.asarray(data.qvel[daddr], dtype=float)
    springref = np.asarray(model.qpos_spring[qaddr], dtype=float)
    spring_tau = -np.asarray(model.jnt_stiffness[jids], dtype=float) * (
        q - springref)
    passive_source = getattr(data, "qfrc_passive", None)
    passive = (None if passive_source is None else
               np.asarray(passive_source[daddr], dtype=float).tolist())
    return {
        "enabled": True,
        "joint_names": list(JOINT_NAMES),
        "angle_deg": np.degrees(q).tolist(),
        "velocity_deg_s": np.degrees(qd).tolist(),
        "spring_torque_nm": spring_tau.tolist(),
        # MJX's host-side FakeData intentionally carries only fields used by
        # the policy/reward loop, not qfrc_passive.  Spring torque remains
        # exactly reconstructable there; report total passive force only
        # when the backend exposes it.
        "passive_force_nm": passive,
        "max_abs_angle_deg": float(np.max(np.abs(np.degrees(q)))),
    }


__all__ = [
    "JOINT_NAMES",
    "LegMountFlexAddresses",
    "LegMountFlexSpec",
    "addresses",
    "apply_to_mjspec",
    "diagnostics",
    "from_cfg",
]
