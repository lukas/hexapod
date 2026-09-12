"""Opt-in post-encoder torsional compliance for the 18 servo joints.

This module inserts a *serial* passive hinge after each selected named servo
joint.  The original joint and every actuator/sensor which names it remain on
an encoder-side carrier body; the original output body, its geometry, and its
entire child subtree move through a second, co-axial passive coordinate.  Thus
the named 18-joint robot contract remains encoder-side while link pose is
``encoder angle + flex angle``.

The feature is deliberately not wired into the default simulator.  Consumers
must call :func:`from_cfg` and pass the result to :func:`apply_to_mjspec`.
Missing configuration and ``enabled: 0`` are exact no-ops.  When enabled, the
configuration contains one explicit entry for every physical joint; selectors
can then isolate a leg or axis without changing the parameter table used by a
fit::

    joint_series_flex:
      enabled: 1
      legs: [0, 1, 2, 3, 4, 5]
      axes: [yaw, pitch, knee]
      joints:
        L0_yaw: {stiffness_nm_rad: 30, damping_nms_rad: 0.2,
                 frictionloss_nm: 0, springref_deg: 0,
                 range_deg: [-6, 6]}
        # ...all remaining 17 named joints are required...

``springref_deg`` is an unloaded spring reference, not a geometry offset.
Keyframes retain zero hidden deflection, so a non-zero spring reference
represents preload.  MuJoCo does not allow a moving body to have exactly zero
inertia, so each carrier receives one millionth of the original output body's
spatial inertia and the same amount is subtracted from the output.  This keeps
the nominal assembled mass/inertia unchanged while making the numerical
carrier dynamically negligible.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import math
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np

from rl_move.config import cfg_get


N_LEGS = 6
AXES = ("yaw", "pitch", "knee")
ACTIVE_JOINT_NAMES = tuple(
    f"L{leg}_{axis}" for leg in range(N_LEGS) for axis in AXES)
FLEX_JOINT_NAMES = tuple(
    f"{name}_series_flex" for name in ACTIVE_JOINT_NAMES)
ENCODER_BODY_NAMES = tuple(
    f"{name}_encoder_carrier" for name in ACTIVE_JOINT_NAMES)

_PARAMETER_KEYS = frozenset({
    "stiffness_nm_rad",
    "damping_nms_rad",
    "frictionloss_nm",
    "springref_deg",
    "range_deg",
})
_POSE_ATTRIBUTES = (
    "pos", "quat", "axisangle", "xyaxes", "zaxis", "euler")
_CARRIER_INERTIA_FRACTION = 1e-6


def _finite_float(value: Any, *, path: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be numeric") from exc
    if not math.isfinite(out):
        raise ValueError(f"{path} must be finite")
    return out


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray))


@dataclass(frozen=True)
class JointFlexParams:
    """One output-side torsional spring in user-facing units."""

    stiffness_nm_rad: float
    damping_nms_rad: float
    frictionloss_nm: float
    springref_deg: float
    range_deg: tuple[float, float]

    def __post_init__(self) -> None:
        values = (
            self.stiffness_nm_rad,
            self.damping_nms_rad,
            self.frictionloss_nm,
            self.springref_deg,
            *self.range_deg,
        )
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("series-flex parameters must be finite")
        if self.stiffness_nm_rad <= 0.0:
            raise ValueError("stiffness_nm_rad must be > 0")
        if self.damping_nms_rad < 0.0:
            raise ValueError("damping_nms_rad must be >= 0")
        if self.frictionloss_nm < 0.0:
            raise ValueError("frictionloss_nm must be >= 0")
        lo, hi = self.range_deg
        if not lo < 0.0 < hi:
            raise ValueError(
                "range_deg must contain geometry-zero strictly")
        if not lo <= self.springref_deg <= hi:
            raise ValueError(
                "springref_deg must lie inside range_deg")

    def as_dict(self) -> dict[str, Any]:
        return {
            "stiffness_nm_rad": self.stiffness_nm_rad,
            "damping_nms_rad": self.damping_nms_rad,
            "frictionloss_nm": self.frictionloss_nm,
            "springref_deg": self.springref_deg,
            "range_deg": list(self.range_deg),
        }


def _parse_params(name: str, raw: Any) -> JointFlexParams:
    path = f"joint_series_flex.joints.{name}"
    if not isinstance(raw, Mapping):
        raise ValueError(f"{path} must be a mapping")
    missing = sorted(_PARAMETER_KEYS - set(raw))
    extra = sorted(set(raw) - _PARAMETER_KEYS)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {missing}")
        if extra:
            details.append(f"unknown {extra}")
        raise ValueError(f"{path} must have exactly five fields ({'; '.join(details)})")

    raw_range = raw["range_deg"]
    if not _is_sequence(raw_range) or len(raw_range) != 2:
        raise ValueError(f"{path}.range_deg must be [lower, upper]")
    range_deg = (
        _finite_float(raw_range[0], path=f"{path}.range_deg[0]"),
        _finite_float(raw_range[1], path=f"{path}.range_deg[1]"),
    )
    try:
        return JointFlexParams(
            stiffness_nm_rad=_finite_float(
                raw["stiffness_nm_rad"], path=f"{path}.stiffness_nm_rad"),
            damping_nms_rad=_finite_float(
                raw["damping_nms_rad"], path=f"{path}.damping_nms_rad"),
            frictionloss_nm=_finite_float(
                raw["frictionloss_nm"], path=f"{path}.frictionloss_nm"),
            springref_deg=_finite_float(
                raw["springref_deg"], path=f"{path}.springref_deg"),
            range_deg=range_deg,
        )
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc


def _parse_legs(raw: Any) -> tuple[int, ...]:
    path = "joint_series_flex.legs"
    if not _is_sequence(raw) or not raw:
        raise ValueError(f"{path} must be a non-empty list")
    try:
        legs = tuple(int(value) for value in raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} entries must be integer leg indices") from exc
    if any(isinstance(value, float) and not value.is_integer()
           for value in raw):
        raise ValueError(f"{path} entries must be integer leg indices")
    if len(set(legs)) != len(legs) or any(
            leg < 0 or leg >= N_LEGS for leg in legs):
        raise ValueError(f"{path} must contain unique indices in [0, 5]")
    return tuple(leg for leg in range(N_LEGS) if leg in legs)


def _parse_axes(raw: Any) -> tuple[str, ...]:
    path = "joint_series_flex.axes"
    if not _is_sequence(raw) or not raw:
        raise ValueError(f"{path} must be a non-empty list")
    axes = tuple(str(value) for value in raw)
    if len(set(axes)) != len(axes) or any(axis not in AXES for axis in axes):
        raise ValueError(
            f"{path} must contain unique values selected from {AXES}")
    return tuple(axis for axis in AXES if axis in axes)


@dataclass(frozen=True)
class JointSeriesFlexSpec:
    """Validated 18-entry table plus a deterministic fit selector."""

    legs: tuple[int, ...]
    axes: tuple[str, ...]
    entries: tuple[tuple[str, JointFlexParams], ...]

    def __post_init__(self) -> None:
        names = tuple(name for name, _ in self.entries)
        if names != ACTIVE_JOINT_NAMES:
            raise ValueError(
                "entries must contain all 18 physical joints in canonical order")
        if not self.legs or any(leg not in range(N_LEGS) for leg in self.legs):
            raise ValueError("legs must select at least one valid leg")
        if not self.axes or any(axis not in AXES for axis in self.axes):
            raise ValueError("axes must select at least one valid axis")

    @property
    def selected_joint_names(self) -> tuple[str, ...]:
        return tuple(
            name for name in ACTIVE_JOINT_NAMES
            if int(name[1]) in self.legs and name.split("_", 1)[1] in self.axes)

    def params(self, joint_name: str) -> JointFlexParams:
        for name, params in self.entries:
            if name == joint_name:
                return params
        raise KeyError(joint_name)

    def summary(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "legs": list(self.legs),
            "axes": list(self.axes),
            "selected_joint_names": list(self.selected_joint_names),
            "joints": {
                name: params.as_dict() for name, params in self.entries
            },
        }


def from_cfg(cfg: dict | None) -> JointSeriesFlexSpec | None:
    """Parse an explicit 18-entry table, or return ``None`` when off."""
    cfg = cfg or {}
    raw_enabled = cfg_get(cfg, "joint_series_flex", "enabled", default=0)
    try:
        enabled = float(raw_enabled)
    except (TypeError, ValueError) as exc:
        raise ValueError("joint_series_flex.enabled must be 0 or 1") from exc
    if enabled == 0.0:
        return None
    if enabled != 1.0:
        raise ValueError("joint_series_flex.enabled must be exactly 0 or 1")

    section = cfg_get(cfg, "joint_series_flex", default=None)
    if not isinstance(section, Mapping):
        raise ValueError("joint_series_flex must be a mapping")
    for required in ("legs", "axes", "joints"):
        if required not in section:
            raise ValueError(
                f"joint_series_flex.enabled=1 requires joint_series_flex.{required}")
    legs = _parse_legs(section["legs"])
    axes = _parse_axes(section["axes"])
    joints = section["joints"]
    if not isinstance(joints, Mapping):
        raise ValueError("joint_series_flex.joints must be a mapping")
    missing = sorted(set(ACTIVE_JOINT_NAMES) - set(joints))
    extra = sorted(set(joints) - set(ACTIVE_JOINT_NAMES))
    if missing or extra or len(joints) != len(ACTIVE_JOINT_NAMES):
        details = []
        if missing:
            details.append(f"missing {missing}")
        if extra:
            details.append(f"unknown {extra}")
        raise ValueError(
            "joint_series_flex.joints must contain exactly the 18 named "
            f"servo joints ({'; '.join(details)})")
    entries = tuple(
        (name, _parse_params(name, joints[name]))
        for name in ACTIVE_JOINT_NAMES)
    return JointSeriesFlexSpec(legs=legs, axes=axes, entries=entries)


def _find_joint_body(root: ET.Element, joint_name: str) -> tuple[
        ET.Element, ET.Element, ET.Element]:
    matches: list[tuple[ET.Element, ET.Element, ET.Element]] = []
    for parent in root.iter():
        for body in parent.findall("body"):
            for joint in body.findall("joint"):
                if joint.get("name") == joint_name:
                    matches.append((parent, body, joint))
    if len(matches) != 1:
        raise ValueError(
            f"expected one body-local joint {joint_name!r}; found {len(matches)}")
    return matches[0]


def _hidden_name(active_name: str) -> str:
    return f"{active_name}_series_flex"


def _carrier_name(active_name: str) -> str:
    return f"{active_name}_encoder_carrier"


def _compiled_inertial(model, body_name: str) -> ET.Element:
    """Explicit inertial for MJCF bodies whose mass was geom-inferred."""
    import mujoco

    bid = int(mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_BODY, body_name))
    if bid < 0:
        raise ValueError(f"compiled body {body_name!r} is missing")

    def values(array) -> str:
        return " ".join(format(float(value), ".17g") for value in array)

    return ET.Element("inertial", {
        "pos": values(model.body_ipos[bid]),
        "quat": values(model.body_iquat[bid]),
        "mass": format(float(model.body_mass[bid]), ".17g"),
        "diaginertia": values(model.body_inertia[bid]),
    })


def _insert_series_body(root: ET.Element, active_name: str,
                        params: JointFlexParams, old_model) -> None:
    parent, output_body, active_joint = _find_joint_body(root, active_name)
    if active_joint.get("type", "hinge") != "hinge":
        raise ValueError(f"active joint {active_name!r} must be a hinge")
    axis = active_joint.get("axis", "0 0 1")
    pos = active_joint.get("pos", "0 0 0")

    parent_index = list(parent).index(output_body)
    parent.remove(output_body)
    output_body.remove(active_joint)

    carrier = ET.Element("body", {"name": _carrier_name(active_name)})
    # Moving the old body's frame onto the carrier keeps global kinematics
    # exact.  The original named body becomes an identity child and retains
    # its inertia, geoms, sites, and descendants on the output side.
    for attribute in _POSE_ATTRIBUTES:
        if attribute in output_body.attrib:
            carrier.set(attribute, output_body.attrib.pop(attribute))

    # An empty moving carrier is rejected by MuJoCo even when its descendants
    # have mass.  Split a negligible fraction of the output spatial inertia
    # onto the carrier.  At zero flex the two frames coincide, so their sum is
    # the original nominal rigid-body inertia (up to parse rounding).
    output_inertial = output_body.find("inertial")
    if output_inertial is None:
        body_name = output_body.get("name")
        if not body_name:
            raise ValueError(
                f"body containing {active_name!r} is unnamed")
        output_inertial = _compiled_inertial(old_model, body_name)
        output_body.insert(0, output_inertial)
    if "mass" not in output_inertial.attrib:
        raise ValueError(f"body containing {active_name!r} has no mass")
    carrier_inertial = deepcopy(output_inertial)
    for attribute in ("mass", "diaginertia", "fullinertia"):
        if attribute not in output_inertial.attrib:
            continue
        values = [float(value) for value in
                  output_inertial.attrib[attribute].split()]
        carrier_inertial.set(attribute, " ".join(
            format(value * _CARRIER_INERTIA_FRACTION, ".17g")
            for value in values))
        output_inertial.set(attribute, " ".join(
            format(value * (1.0 - _CARRIER_INERTIA_FRACTION), ".17g")
            for value in values))
    carrier.append(carrier_inertial)
    carrier.append(active_joint)

    lo_deg, hi_deg = params.range_deg
    passive = ET.Element("joint", {
        "name": _hidden_name(active_name),
        "type": "hinge",
        "pos": pos,
        "axis": axis,
        "ref": "0",
        "stiffness": format(params.stiffness_nm_rad, ".17g"),
        "springref": format(math.radians(params.springref_deg), ".17g"),
        "limited": "true",
        "range": (
            f"{format(math.radians(lo_deg), '.17g')} "
            f"{format(math.radians(hi_deg), '.17g')}"),
        "armature": "0",
        "damping": format(params.damping_nms_rad, ".17g"),
        "frictionloss": format(params.frictionloss_nm, ".17g"),
    })
    output_body.insert(list(output_body).index(output_inertial) + 1, passive)
    carrier.append(output_body)
    parent.insert(parent_index, carrier)


def apply_to_mjspec(mj_spec, flex: JointSeriesFlexSpec | None):
    """Return an MjSpec with true serial hinges after selected servo joints.

    A new spec is returned because MjSpec cannot reparent an existing body in
    place.  The source is serialized to canonical MJCF, rewritten structurally,
    and parsed with the original binary assets.  Existing keyframe qpos/qvel
    values are then remapped by joint name using the shared mount-flex helper;
    hidden flex coordinates stay at geometry-zero.
    """
    if flex is None:
        return mj_spec

    import mujoco
    from .leg_mount_flex import _remap_key_vector

    old_model = mj_spec.compile()
    all_hidden = set(FLEX_JOINT_NAMES) | set(ENCODER_BODY_NAMES)
    existing = []
    for name in all_hidden:
        joint_id = mujoco.mj_name2id(
            old_model, mujoco.mjtObj.mjOBJ_JOINT, name)
        body_id = mujoco.mj_name2id(
            old_model, mujoco.mjtObj.mjOBJ_BODY, name)
        if joint_id >= 0 or body_id >= 0:
            existing.append(name)
    if existing:
        raise ValueError(
            f"joint series flex is already or partially installed: {sorted(existing)}")

    old_keys = {
        key.name: (
            np.asarray(list(key.qpos), dtype=float),
            np.asarray(list(key.qvel), dtype=float),
        )
        for key in mj_spec.keys
    }
    root = ET.fromstring(mj_spec.to_xml())
    worldbody = root.find("worldbody")
    if worldbody is None:
        raise ValueError("MjSpec has no worldbody")
    for name in flex.selected_joint_names:
        _insert_series_body(worldbody, name, flex.params(name), old_model)

    rewritten = ET.tostring(root, encoding="unicode")
    new_spec = mujoco.MjSpec.from_string(
        rewritten, assets=dict(mj_spec.assets))
    new_model = new_spec.compile()
    for key in new_spec.keys:
        old_qpos, old_qvel = old_keys[key.name]
        if old_qpos.size:
            key.qpos = _remap_key_vector(
                old_qpos, old_model=old_model, new_model=new_model,
                velocity=False).tolist()
        if old_qvel.size:
            key.qvel = _remap_key_vector(
                old_qvel, old_model=old_model, new_model=new_model,
                velocity=True).tolist()
    return new_spec


@dataclass(frozen=True)
class JointSeriesFlexAddresses:
    joint_names: tuple[str, ...]
    active_joint_ids: tuple[int, ...]
    flex_joint_ids: tuple[int, ...]
    active_qpos_addrs: tuple[int, ...]
    flex_qpos_addrs: tuple[int, ...]
    active_dof_addrs: tuple[int, ...]
    flex_dof_addrs: tuple[int, ...]


def addresses(model, *, expected: JointSeriesFlexSpec | None = None,
              required: bool = True) -> JointSeriesFlexAddresses | None:
    """Resolve installed hidden coordinates in canonical physical order."""
    import mujoco

    present_names = []
    flex_ids = []
    for active_name in ACTIVE_JOINT_NAMES:
        hidden = _hidden_name(active_name)
        jid = int(mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_JOINT, hidden))
        if jid >= 0:
            present_names.append(active_name)
            flex_ids.append(jid)
    if not present_names:
        if required:
            raise ValueError("model has no joint series-flex coordinates")
        return None
    if expected is not None and tuple(present_names) != expected.selected_joint_names:
        missing = sorted(set(expected.selected_joint_names) - set(present_names))
        extra = sorted(set(present_names) - set(expected.selected_joint_names))
        raise ValueError(
            "model series-flex selection does not match spec: "
            f"missing={missing}, extra={extra}")

    active_ids = tuple(int(mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_JOINT, name)) for name in present_names)
    if any(jid < 0 for jid in active_ids):
        raise ValueError("a series-flex output has no matching active joint")
    flex_ids_tuple = tuple(flex_ids)
    return JointSeriesFlexAddresses(
        joint_names=tuple(present_names),
        active_joint_ids=active_ids,
        flex_joint_ids=flex_ids_tuple,
        active_qpos_addrs=tuple(
            int(model.jnt_qposadr[jid]) for jid in active_ids),
        flex_qpos_addrs=tuple(
            int(model.jnt_qposadr[jid]) for jid in flex_ids_tuple),
        active_dof_addrs=tuple(
            int(model.jnt_dofadr[jid]) for jid in active_ids),
        flex_dof_addrs=tuple(
            int(model.jnt_dofadr[jid]) for jid in flex_ids_tuple),
    )


def diagnostics(model, data) -> dict[str, Any]:
    """Return serial encoder/output state and passive torque diagnostics."""
    addrs = addresses(model, required=False)
    if addrs is None:
        return {"enabled": False}
    aq = np.asarray(data.qpos[list(addrs.active_qpos_addrs)], dtype=float)
    fq = np.asarray(data.qpos[list(addrs.flex_qpos_addrs)], dtype=float)
    fqd = np.asarray(data.qvel[list(addrs.flex_dof_addrs)], dtype=float)
    flex_jids = np.asarray(addrs.flex_joint_ids, dtype=int)
    flex_qaddrs = np.asarray(addrs.flex_qpos_addrs, dtype=int)
    springref = np.asarray(model.qpos_spring[flex_qaddrs], dtype=float)
    spring_tau = -np.asarray(
        model.jnt_stiffness[flex_jids], dtype=float) * (fq - springref)
    passive_source = getattr(data, "qfrc_passive", None)
    passive = (None if passive_source is None else np.asarray(
        passive_source[list(addrs.flex_dof_addrs)], dtype=float).tolist())
    return {
        "enabled": True,
        "joint_names": list(addrs.joint_names),
        "encoder_angle_deg": np.degrees(aq).tolist(),
        "flex_angle_deg": np.degrees(fq).tolist(),
        "output_angle_deg": np.degrees(aq + fq).tolist(),
        "flex_velocity_deg_s": np.degrees(fqd).tolist(),
        "spring_torque_nm": spring_tau.tolist(),
        "passive_force_nm": passive,
        "max_abs_flex_deg": float(np.max(np.abs(np.degrees(fq)))),
    }


__all__ = [
    "ACTIVE_JOINT_NAMES",
    "AXES",
    "ENCODER_BODY_NAMES",
    "FLEX_JOINT_NAMES",
    "JointFlexParams",
    "JointSeriesFlexAddresses",
    "JointSeriesFlexSpec",
    "addresses",
    "apply_to_mjspec",
    "diagnostics",
    "from_cfg",
]
