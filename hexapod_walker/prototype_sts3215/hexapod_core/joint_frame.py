"""The one logical joint-coordinate contract used by the hexapod.

Logical controller/gait poses, policy actions and observations use
``robot_abs``:

* yaw: coxa yaw;
* hip: absolute femur angle in the leg plane;
* knee: absolute tibia angle in the same leg plane.

MuJoCo stores its knee hinge relative to the femur. The conversions in this
module serve that simulation boundary. Physical knee servos also measure a
relative hinge angle: motor_setup.feetech_bus separately converts logical
poses and coherent raw feedback, including trims and physical limits. Raw
servo diagnostics are explicitly servo_relative, never logical policy poses.
See JOINT_COORDINATES.md for the historical hardware enforcement gap.

Ordering contract (one vocabulary, one indexing API, no hand-rolled math):
  * ``N_LEGS`` = 6 legs, counter-clockwise from the front-left; ``AXES`` =
    ``("yaw", "hip", "knee")`` per leg, proximal to distal.
  * joint ``j = 3 * leg + axis`` is leg-major; use ``joint_index`` /
    ``leg_of`` / ``axis_of`` / ``leg_slice`` instead of writing it out.
  * ``JOINT_NAMES[j]`` is ``L{leg}_{axis}`` — the robot, telemetry and the
    tracker share it; the MuJoCo models spell hip ``pitch``, exposed only
    through ``SIM_JOINT_NAMES`` (same order, same indices).
  * Servo bus ID = ``j + 2`` (IDs 2..19; ID 1 is the factory default, never
    assigned); use ``servo_id`` / ``joint_of_servo``.
"""
from __future__ import annotations

import math
import json
import zipfile
from pathlib import Path
import numpy as np

N_LEGS = 6
AXES = ("yaw", "hip", "knee")
N_JOINTS = N_LEGS * len(AXES)
JOINT_NAMES = tuple(f"L{leg}_{axis}" for leg in range(N_LEGS) for axis in AXES)

# The MuJoCo models (mujoco_prototype.py, mesh_mujoco/build_mesh_model.py)
# name the hip hinge ``pitch``.  Same joint, same index; only the spelling
# differs, so the mapping is positional.
SIM_AXES = ("yaw", "pitch", "knee")
SIM_JOINT_NAMES = tuple(
    f"L{leg}_{axis}" for leg in range(N_LEGS) for axis in SIM_AXES)

FACTORY_SERVO_ID = 1          # every STS3215 ships as ID 1; never assigned
SERVO_ID_OFFSET = 2           # joint 0 -> ID 2, ..., joint 17 -> ID 19
SERVO_IDS = range(SERVO_ID_OFFSET, SERVO_ID_OFFSET + N_JOINTS)

DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi


def joint_index(leg: int, axis: int | str) -> int:
    """Leg-major joint index of ``(leg, axis)``; ``axis`` is a name or 0..2."""
    if isinstance(axis, str):
        axis = AXES.index(axis)
    if not 0 <= int(leg) < N_LEGS or not 0 <= int(axis) < len(AXES):
        raise ValueError(f"no joint for leg={leg!r} axis={axis!r}")
    return int(leg) * len(AXES) + int(axis)


def leg_of(j: int) -> int:
    _check_joint(j)
    return int(j) // len(AXES)


def axis_of(j: int) -> str:
    _check_joint(j)
    return AXES[int(j) % len(AXES)]


def leg_slice(leg: int) -> slice:
    """``q[leg_slice(leg)]`` is that leg's ``(yaw, hip, knee)`` triple."""
    start = joint_index(leg, 0)
    return slice(start, start + len(AXES))


def leg_joints(leg: int) -> tuple[int, int, int]:
    """The three joint indices of ``leg`` in axis order."""
    start = joint_index(leg, 0)
    return (start, start + 1, start + 2)


def servo_id(j: int) -> int:
    """Logical joint 0..17 -> servo bus ID 2..19."""
    _check_joint(j)
    return int(j) + SERVO_ID_OFFSET


def joint_of_servo(sid: int) -> int:
    """Servo bus ID 2..19 -> logical joint; ``ValueError`` for any other ID."""
    if int(sid) not in SERVO_IDS:
        raise ValueError(f"servo ID {sid!r} is not a robot joint (IDs "
                         f"{SERVO_IDS.start}..{SERVO_IDS.stop - 1})")
    return int(sid) - SERVO_ID_OFFSET


def sim_joint_name(j: int) -> str:
    """MuJoCo joint name for logical joint ``j`` (``L{leg}_{yaw|pitch|knee}``)."""
    _check_joint(j)
    return SIM_JOINT_NAMES[int(j)]


def joint_of_name(name: str) -> int:
    """Index of a joint name in either vocabulary (``L2_hip`` == ``L2_pitch``)."""
    if name in JOINT_NAMES:
        return JOINT_NAMES.index(name)
    if name in SIM_JOINT_NAMES:
        return SIM_JOINT_NAMES.index(name)
    raise ValueError(f"unknown joint name {name!r}")


def _check_joint(j: int) -> None:
    if not 0 <= int(j) < N_JOINTS:
        raise ValueError(f"joint index {j!r} outside 0..{N_JOINTS - 1}")

FRAME_ROBOT_ABS = "robot_abs"
JOINT_CONTRACT = "robot_abs_tibia_v2"


def _as_joint_array(q: np.ndarray | list[float] | tuple[float, ...]) -> np.ndarray:
    return np.asarray(q, dtype=float).reshape(N_JOINTS).copy()


def _robot_abs_to_mujoco_rel(q_robot_abs: np.ndarray | list[float]) -> list[float]:
    """Robot logical coordinates -> MuJoCo's private hinge coordinates.

    Unit-agnostic: degrees in gives degrees out; radians in gives
    radians out.
    """
    q = _as_joint_array(q_robot_abs)
    for leg in range(N_LEGS):
        hip_j = joint_index(leg, "hip")
        knee_j = joint_index(leg, "knee")
        q[knee_j] = q[knee_j] - q[hip_j]
    return [float(v) for v in q]


def _mujoco_rel_to_robot_abs(q_mujoco_rel: np.ndarray | list[float]) -> list[float]:
    """MuJoCo's private hinge coordinates -> robot logical coordinates."""
    q = _as_joint_array(q_mujoco_rel)
    for leg in range(N_LEGS):
        hip_j = joint_index(leg, "hip")
        knee_j = joint_index(leg, "knee")
        q[knee_j] = q[knee_j] + q[hip_j]
    return [float(v) for v in q]


def robot_abs_rad_to_mujoco_rel_rad(q_robot_abs_rad: np.ndarray | list[float]) -> np.ndarray:
    return np.asarray(_robot_abs_to_mujoco_rel(q_robot_abs_rad), dtype=float)


def mujoco_rel_rad_to_robot_abs_rad(q_mujoco_rel_rad: np.ndarray | list[float]) -> np.ndarray:
    return np.asarray(_mujoco_rel_to_robot_abs(q_mujoco_rel_rad), dtype=float)


def robot_abs_deg_to_mujoco_rel_rad(q_robot_abs_deg: np.ndarray | list[float]) -> np.ndarray:
    return robot_abs_rad_to_mujoco_rel_rad(
        np.asarray(q_robot_abs_deg, dtype=float) * DEG2RAD)


def mujoco_rel_rad_to_robot_abs_deg(q_mujoco_rel_rad: np.ndarray | list[float]) -> list[float]:
    return [float(v) for v in mujoco_rel_rad_to_robot_abs_rad(q_mujoco_rel_rad) * RAD2DEG]


def require_robot_abs_joint_frame(meta: dict | None, *,
                                  source: str = "policy") -> str:
    """Validate an artifact's coordinate contract; never reinterpret it.

    Metadata is mandatory so an old MuJoCo-relative checkpoint cannot be
    mistaken for a deployable robot policy.
    """
    raw = None if meta is None else meta.get("joint_frame")
    contract = None if meta is None else meta.get("joint_contract")
    if raw != FRAME_ROBOT_ABS or contract != JOINT_CONTRACT:
        raise ValueError(
            f"{source}: expected joint_frame={FRAME_ROBOT_ABS!r} and "
            f"joint_contract={JOINT_CONTRACT!r}, got {raw!r}/{contract!r}; "
            "pre-v2 artifacts must be regenerated, not converted at deployment")
    return FRAME_ROBOT_ABS


def require_checkpoint_joint_contract(path: str | Path) -> str:
    """Reject an SB3 checkpoint created before the v2 coordinate contract."""
    try:
        with zipfile.ZipFile(path) as archive:
            data = json.loads(archive.read("data"))
    except Exception as exc:
        raise ValueError(f"{path}: cannot read checkpoint contract") from exc
    frame = data.get("joint_frame")
    contract = data.get("joint_contract")
    if frame != FRAME_ROBOT_ABS or contract != JOINT_CONTRACT:
        raise ValueError(
            f"{path}: checkpoint frame/contract is {frame!r}/{contract!r}, "
            f"expected {FRAME_ROBOT_ABS!r}/{JOINT_CONTRACT!r}; pre-v2 "
            "weights cannot be warm-started")
    return contract


def robot_stand_degrees() -> list[float]:
    """Robot stand/plant pose in logical robot degrees."""
    try:
        from motor_setup.feetech_bus import standing_pose_degrees
        q = [float(v) for v in standing_pose_degrees()]
        if len(q) == N_JOINTS:
            return q
    except Exception:
        pass
    return [0.0, 19.0, 28.0] * N_LEGS
