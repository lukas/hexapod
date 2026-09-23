"""Settled-stance measurement from a ``--rollout-trace-out`` .npz.

WHAT IT DOES
    Replays a recorded per-tick ``qpos`` trace (written by
    ``eval_checkpoint.py --rollout-trace-out``) through the SAME mesh model
    via ``mj_forward`` (no dynamics, pure forward-kinematics placement) and
    reports, per tick: each leg's chassis-local foot-site radius (planar xy
    distance from the chassis origin, rotated into the chassis frame by its
    own ``xmat`` — so chassis roll/pitch/yaw don't contaminate the number)
    and the knee angle in ``robot_abs`` degrees (``hexapod_core.joint_frame``
    convention: absolute tibia angle in the leg plane, not MuJoCo's
    hip-relative hinge coordinate).

    Built 2026-09-23 for the extplant82 stance-gate checks (see
    ``rl_docs/runs/cw-walk50hz-gru-extplant82-s0.md``): that run's own
    written gate needs foot radius + knee robot_abs, a field the standard
    eval report does NOT carry, so this replaces the ad hoc one-off script
    used for the warm-start arm with something reusable for every future
    extplant (or any other stance-target) arm.

USAGE
    uv run python -m rl_move.scripts.measure_settled_stance TRACE.npz
        [--model-source mesh] [--settle-frac 0.8]

    ``--settle-frac`` (default 0.8) marks the tail fraction of the episode
    used for the "settled" summary (mean/min/max over ticks >= that frac of
    the episode length) — the reset transient and any brief park->walk peak
    are excluded from the headline numbers, matching how the extplant82-s0
    NOGO writeup described "steady-state" vs the early transition spike.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


def measure(qpos: np.ndarray, *, model_source: str = "mesh") -> dict:
    """Return per-tick foot radius (6, T) mm and knee robot_abs (6, T) deg.

    ``qpos`` is ``(T, nq)`` with the free-joint pos+quat in ``qpos[:, 0:7]``
    and the 18 commanded joints in MuJoCo's own private ordering elsewhere
    in the vector (addressed via ``joint_qpos_addrs``, never a bare slice).
    """
    import mujoco
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from rl_move.sim import servo_model
    from hexapod_core import joint_frame as jf

    model = servo_model.build_model(source=model_source, fixed_base=False)
    data = mujoco.MjData(model)
    qpos_addrs = servo_model.joint_qpos_addrs(model)  # SIM_JOINT_NAMES order
    chassis_bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "chassis")
    foot_sids = [
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"L{i}_foot_site")
        for i in range(jf.N_LEGS)
    ]
    if any(s < 0 for s in foot_sids) or chassis_bid < 0:
        raise RuntimeError("model missing L{i}_foot_site or chassis body — "
                           "model_source/model family mismatch?")

    T = qpos.shape[0]
    radius_mm = np.zeros((jf.N_LEGS, T))
    knee_abs_deg = np.zeros((jf.N_LEGS, T))
    for t in range(T):
        data.qpos[:7] = qpos[t, :7]
        data.qpos[qpos_addrs] = qpos[t, 7:7 + len(qpos_addrs)]
        mujoco.mj_forward(model, data)
        R = np.asarray(data.xmat[chassis_bid], dtype=float).reshape(3, 3)
        origin = np.asarray(data.xpos[chassis_bid], dtype=float)
        for i in range(jf.N_LEGS):
            foot = np.asarray(data.site_xpos[foot_sids[i]], dtype=float)
            local = R.T @ (foot - origin)
            radius_mm[i, t] = float(np.hypot(local[0], local[1])) * 1000.0
        # MuJoCo-private -> robot_abs (adds hip back onto the knee hinge).
        q_rel = qpos[t, 7:7 + len(qpos_addrs)]
        q_abs_deg = jf.mujoco_rel_rad_to_robot_abs_deg(q_rel)
        for i in range(jf.N_LEGS):
            knee_abs_deg[i, t] = q_abs_deg[jf.joint_index(i, "knee")]
    return {"radius_mm": radius_mm, "knee_abs_deg": knee_abs_deg}


def summarize(res: dict, *, settle_frac: float = 0.8) -> dict:
    T = res["radius_mm"].shape[1]
    t0 = int(round(settle_frac * T))
    tail = slice(t0, T)
    r_tail = res["radius_mm"][:, tail]
    k_tail = res["knee_abs_deg"][:, tail]
    return {
        "n_ticks": T,
        "settled_from_tick": t0,
        "radius_mm_mean": float(r_tail.mean()),
        "radius_mm_per_leg_mean": [float(x) for x in r_tail.mean(axis=1)],
        "radius_mm_range": [float(r_tail.min()), float(r_tail.max())],
        "knee_abs_deg_mean": float(k_tail.mean()),
        "knee_abs_deg_per_leg_mean": [float(x) for x in k_tail.mean(axis=1)],
        "knee_abs_deg_range": [float(k_tail.min()), float(k_tail.max())],
        "final_tick_radius_mm_per_leg": [float(x) for x in res["radius_mm"][:, -1]],
        "final_tick_knee_abs_deg_per_leg": [float(x) for x in res["knee_abs_deg"][:, -1]],
        "reset_tick_radius_mm_per_leg": [float(x) for x in res["radius_mm"][:, 0]],
        "peak_radius_mm": float(res["radius_mm"].max()),
        "peak_radius_tick": int(res["radius_mm"].max(axis=0).argmax()),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("trace", type=Path)
    ap.add_argument("--model-source", default="mesh")
    ap.add_argument("--settle-frac", type=float, default=0.8)
    args = ap.parse_args(argv)

    d = np.load(args.trace, allow_pickle=True)
    qpos = np.asarray(d["qpos"], dtype=float)
    res = measure(qpos, model_source=args.model_source)
    summ = summarize(res, settle_frac=args.settle_frac)
    import json
    print(json.dumps(summ, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
