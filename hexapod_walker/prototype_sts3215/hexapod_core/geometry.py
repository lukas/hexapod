"""Frozen mechanical dimensions of the STS3215 prototype (millimetres).

These are the numbers the MuJoCo primitive model (``mujoco_prototype.py``)
needs from the CAD. The CAD generators themselves live in the separate
``lukas/hexapod-cad`` repo (``hexapod_prototype.py`` there is the source of
truth); this module is the values they produced at the split on
2026-09-15, so the sim carries no trimesh/build123d dependency.

If a dimension changes in the CAD, change it here in the same PR that
regenerates ``mesh_mujoco/assets`` + ``mesh_mujoco/hexapod_mesh.xml``.
"""
from __future__ import annotations

import os

_PROTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Chassis: regular hexagon of two printed plates.
CHASSIS_FLAT_TO_FLAT = 200.0   # distance between opposite hex edges
CHASSIS_PLATE_T = 4.0          # thickness of each printed plate
CHASSIS_GAP = 20.0             # vertical gap between top and bottom plates

# Leg link lengths (axis to axis).
COXA_LENGTH = 12.5             # yaw axis -> hip-pitch axis
FEMUR_LENGTH = 90.0            # hip-pitch axis -> knee axis
TIBIA_LENGTH = 150.0           # knee axis -> foot tip

# Servo envelope (STS3215).
SERVO_BODY_H = 34.3            # back mount face -> front (output) face
SERVO_OUTPUT_H = 2.0           # output hub / horn-cap stack above the front face
SERVO_OUTPUT_X = 12.5          # output shaft offset from body centre, toward +X
HORN_STACK_H = 5.0             # plastic horn height
WELL_RIM_Z = 34.3              # yaw-servo well rim (= SERVO_BODY_H)

# Coxa bracket.
COXA_ARM_T = 6.0               # arm slab thickness in +Z
COXA_HIP_DROP = 38.4           # hip-pitch axis drop below the yaw output
COXA_HIP_ANCHOR_Y = -25.65     # hip-pitch axis offset along the coxa Y

# Foot boot.
FOOT_BOOT_OD = 9.0
FOOT_BOOT_SOCKET_DEPTH = 20.0
FOOT_BOOT_TIP_L = 8.0

# Battery block under the belly (two packs).
BATTERY_W = 75.0
BATTERY_D = 34.0
BATTERY_H = 26.5
BATTERY_PACK_GAP = 4.0
BATTERY_UNDER_YAW_DEG = 30.0
BATTERY_UNDER_CENTRE = (0.0, 0.0)

# Electronics tray centre (chassis XY).
ELEC_TRAY_CENTRE_X = 0.0
ELEC_TRAY_CENTRE_Y = -2.5

# Standing pose keyframe.
STANCE_FEMUR_DEG = -25.0
STANCE_TIBIA_DEG = 75.0

# Optional visual meshes for the primitive model. The CAD build writes
# printables to <prototype>/stl_prototype and reference meshes to
# <prototype>/stl_reference; neither is tracked here, so a plain checkout
# renders the model from primitives (mujoco_prototype checks isfile()).
STL_DIR = os.path.join(_PROTO, "stl_prototype")
REF_STL_DIR = os.path.join(_PROTO, "stl_reference")
NOPRINT_SUFFIX = "_DO_NOT_PRINT"
NOT_PRINTED_MESHES = frozenset({
    "tibia_link", "assembly_preview",
    "servo_body", "servo_horn", "disc_horn", "yaw_bearing", "mpu6050",
    "uno_q", "buck_converter",
    "antispark_switch_body", "antispark_switch_toggle",
    "lipo_battery_body", "lipo_xt60",
    "motor_controller", "breakout", "screen",
    "hex_post_standoff", "hex_post_thumb_nut", "hex_post_magnet",
    "chassis_standoff",
    "wago", "wago3", "wago5",
})


def stl_path(base: str) -> str:
    """Absolute path of the CAD-built STL for a logical mesh name."""
    base = base[:-4] if base.endswith(".stl") else base
    if base in NOT_PRINTED_MESHES:
        return os.path.join(REF_STL_DIR, f"{base}{NOPRINT_SUFFIX}.stl")
    return os.path.join(STL_DIR, f"{base}.stl")
