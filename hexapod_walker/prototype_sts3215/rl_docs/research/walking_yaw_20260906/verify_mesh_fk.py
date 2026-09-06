"""Read-only model FK audit; no dynamics steps, training, or robot control.

Run from repository root with:
UV_CACHE_DIR=/tmp/hexapod-steering-review-uv uv run --no-project --offline \
  --python .venv/bin/python python hexapod_walker/prototype_sts3215/rl_docs/research/walking_yaw_20260906/verify_mesh_fk.py

Same-neutral target = actual mesh foot-site position at (yaw=0, hip=20,
absolute tibia=100), plus the unchanged TripodGait foot displacement.
The target is a sphere-centre/site, not a contact material point.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import mujoco
import numpy as np

REPO = Path(__file__).resolve().parents[5]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--proto', type=Path, default=REPO/'hexapod_walker/prototype_sts3215')
parser.add_argument('--xml', type=Path, action='append', help='Exact XML to audit; repeatable.')
args = parser.parse_args()
PROTO = args.proto
sys.path.insert(0, str(PROTO))
from hexapod_core.tripod_gait import TripodGait
from hexapod_core.se2_foot_gait import SE2FootGait
from hexapod_core.joint_frame import robot_abs_deg_to_mujoco_rel_rad


def audit(path):
    model = mujoco.MjModel.from_xml_path(str(path))
    data = mujoco.MjData(model)
    bid = lambda name: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
    sid = lambda name: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, name)
    jids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f'L{i}_{j}')
            for i in range(6) for j in ('yaw', 'pitch', 'knee')]
    qadr = model.jnt_qposadr[jids]
    sites = [sid(f'L{i}_foot_site') for i in range(6)]

    def fk(q):
        data.qpos[qadr] = robot_abs_deg_to_mujoco_rel_rad(q)
        mujoco.mj_forward(model, data)
        return data.site_xpos[sites].copy()

    neutral = fk([0., 20., 100.] * 6)
    roots = [data.xpos[bid(f'L{i}_yaw')].copy() for i in range(6)]
    rots = [data.xmat[bid(f'L{i}_yaw')].reshape(3, 3).copy() for i in range(6)]
    femur = model.body_pos[bid('L0_femur')].copy()
    tibia = model.body_pos[bid('L0_tibia')].copy()
    pad = model.body_pos[bid('L0_pad')].copy()
    site = model.site_pos[sites[0]].copy()
    coxa, hip_z, net_y = femur[0], femur[2], femur[1] + pad[1] + site[1]
    femur_len, tibia_len = tibia[0], pad[0] + site[0]

    def model_ik(target):
        result = []
        for i in range(6):
            x, y, z = rots[i].T @ (target[i] - roots[i])
            reach = math.sqrt(x*x + y*y - net_y*net_y)
            yaw = math.atan2(y, x) - math.atan2(net_y, reach)
            u, w = reach - coxa, hip_z - z
            length = math.hypot(u, w)
            cos_alpha = (length*length + femur_len*femur_len - tibia_len*tibia_len) / (2*length*femur_len)
            if not -1 <= cos_alpha <= 1:
                raise ValueError('IK infeasible')
            hip = math.atan2(w, u) - math.acos(cos_alpha)
            knee = math.atan2(w-femur_len*math.sin(hip), u-femur_len*math.cos(hip))
            result.extend(map(math.degrees, (yaw, hip, knee)))
        return result

    regimes = []
    legacy_se2 = SE2FootGait()
    legacy_se2.sync_plant_stance(20., 100.)
    for vx, wz in ((0., .25), (.08, .25), (0., -.25), (.08, -.25)):
        g = TripodGait(vx=vx, omega=wz)
        g.sync_plant_stance(20., 100.)
        raw_errors, mesh_ik_errors, per_leg_xy, speed_errors, legacy_se2_errors = [], [], [], [], []
        prior_error = None
        for step in range(151):
            phase = 2*math.pi*step/150
            g.reset_phase(phase=phase, t=10.)
            g._elapsed = 10.
            raw_q = g.desired_deg(10.)
            delta = np.array([g._foot_target_in_body(i, vx, 0., wz) for i in range(6)])
            target = neutral + delta
            err = fk(raw_q) - target
            raw_errors.append(np.linalg.norm(err, axis=1))
            per_leg_xy.append(np.linalg.norm(err[:, :2], axis=1))
            if prior_error is not None:
                speed_errors.append(np.linalg.norm((err-prior_error)/(.75/150), axis=1))
            prior_error = err
            mesh_ik_errors.append(np.linalg.norm(fk(model_ik(target))-target, axis=1))
            legacy_q = []
            for i in range(6):
                nx, ny = legacy_se2.neutral_body[i]
                solved = legacy_se2.leg_ik_body(i, nx+delta[i, 0], ny+delta[i, 1],
                    legacy_se2.foot_neutral_z+delta[i, 2])
                if solved is None:
                    raise ValueError('Legacy SE2 IK infeasible')
                legacy_q.extend(map(math.degrees, solved))
            legacy_se2_errors.append(np.linalg.norm(fk(legacy_q)-target, axis=1))
        regimes.append(dict(vx=vx, wz=wz,
            raw_same_neutral_error_max_mm=float(np.max(raw_errors)*1000),
            raw_xy_error_max_mm=float(np.max(per_leg_xy)*1000),
            raw_xy_per_leg_max_mm=(np.max(per_leg_xy, axis=0)*1000).tolist(),
            raw_error_velocity_max_mm_s=float(np.max(speed_errors)*1000),
            legacy_se2_ik_same_displacement_error_max_mm=float(np.max(legacy_se2_errors)*1000),
            exact_model_ik_error_max_mm=float(np.max(mesh_ik_errors)*1000)))
    return dict(path=str(path), xml_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        mujoco_version=mujoco.__version__, mass_kg=float(model.body_mass.sum()),
        foot_chain=dict(femur_body_pos=femur.tolist(), tibia_body_pos=tibia.tolist(),
            pad_body_pos=pad.tolist(), site_pos=site.tolist()),
        derived=dict(coxa_m=float(coxa), femur_m=float(femur_len),
            tibia_to_site_m=float(tibia_len), net_tangent_m=float(net_y), hip_rise_m=float(hip_z)),
        regimes=regimes)


paths = args.xml or [p for f in ('hexapod_mesh_mjx.xml', 'hexapod_mesh.xml')
                    if (p := PROTO/'mesh_mujoco'/f).exists()]
if not paths:
    parser.error("No model XML found; supply --xml.")
result = [audit(path) for path in paths]
print(json.dumps(result, indent=2))
