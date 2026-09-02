"""The one logical joint-coordinate contract used by the hexapod.

Every public controller, gait, policy, observation, telemetry record and
experiment uses ``robot_abs``:

* yaw: coxa yaw;
* hip: absolute femur angle in the leg plane;
* knee: absolute tibia angle in the same leg plane.

MuJoCo necessarily stores its knee hinge relative to the femur.  The two
conversion functions in this module exist only for an explicit physics
boundary; MuJoCo coordinates are never a policy or gait option.
"""
from __future__ import annotations

import math
import json
import zipfile
from pathlib import Path
import numpy as np

N_JOINTS = 18
DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi

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
    for leg in range(6):
        hip_j = 3 * leg + 1
        knee_j = 3 * leg + 2
        q[knee_j] = q[knee_j] - q[hip_j]
    return [float(v) for v in q]


def _mujoco_rel_to_robot_abs(q_mujoco_rel: np.ndarray | list[float]) -> list[float]:
    """MuJoCo's private hinge coordinates -> robot logical coordinates."""
    q = _as_joint_array(q_mujoco_rel)
    for leg in range(6):
        hip_j = 3 * leg + 1
        knee_j = 3 * leg + 2
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
    return [0.0, 19.0, 28.0] * 6
