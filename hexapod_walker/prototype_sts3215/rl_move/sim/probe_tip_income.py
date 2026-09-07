"""probe_tip_income.py — tip / combined-turn income + authority sweep
(todaypolicy robotwalk-turns lineage, 2026-09-07 yawref-cont8m
FAIL-QUALIFICATION follow-up).

WHAT THIS MEASURES, one sentence: at the exact cells the cont8m
qualification failed on (tip-in-place wz=+/-0.3 stuck at achieved
~0.21-0.22 rad/s across 3 generations; arc-right vx=0.08 wz=-0.15
regressed 0.0905->0.1162), does the EXACT trained reward stack
actually pay MORE for turning at the commanded rate than for the
policy's current under-rotation / refusal / wrong-sign / crabbing —
i.e. is the tip deficit a PRICING defect (reward optimum below the
command) or an AUTHORITY/optimization deficit (reward monotone in
achieved wz but the gait mechanism saturates)?

Method (matched-trajectory, same convention as probe_combined_frame):
scripted TripodGait drives on the REAL env + the cont8m ledger reward
stack (probe_combined_frame.CFG + the cont8m deltas: k_yaw_prog=2.0,
walk_course_ref_yaw=1.0, walk_sway_arc_aware=1.0), forcing the cell's
command on every tick and sweeping the SCRIPTED turn-rate factor
f in {-1, 0, 0.5, 1.0, 1.33} x wz_ref (wrong-sign / refusal / half /
faithful / overdrive), plus a 'crab' drive on the combined cell
(world-course holder that never yaws). Per drive: walk-tick reward
total, every reward_* channel, ACHIEVED body wz (mean/med of
env._body_wz() over walk ticks) and net body yaw. Reading:
  - reward NOT monotone toward f=1.0 achieved-wz => pricing defect,
    the mechanism lever is a reprice (encode in semantics bank);
  - reward monotone but achieved wz saturates well below wz_ref even
    scripted at f=1.33 => authority ceiling of the gait mechanism,
    the lever is authority/optimization, not another income knob.

Run: uv run python -m rl_move.sim.probe_tip_income [--seconds 6]
     [--extra k=v ...]
"""
from __future__ import annotations

import argparse
import math

import numpy as np

from rl_move.sim.probe_combined_frame import CFG as BASE_CFG

# cont8m ledger deltas vs the 20260906 stack the base probe pinned
CONT8M_DELTAS = {
    "reward.k_yaw_prog": 2.0,
    "reward.walk_course_ref_yaw": 1.0,
    "reward.walk_sway_arc_aware": 1.0,
}

CELLS = {
    # name: (vx_ref, vy_ref, wz_ref)
    "tip-left":  (0.0, 0.0, +0.3),
    "tip-right": (0.0, 0.0, -0.3),
    "arc-right": (0.08, 0.0, -0.15),
    # straight-forward control cell for the ci_yaw_gate bank tests
    # (wz_ref=0: the gate must be bit-exact inert here)
    "fwd": (0.08, 0.0, 0.0),
}


def _rollout(cell: str, drive: str, factor: float, seconds: float,
             extra: dict | None = None, seed: int = 0) -> dict:
    from rl_move.config import load_config
    from rl_move.robot_state import DEG2RAD
    from rl_move.sim.joint_task import q_rad_to_action
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    from rl_move.sim.probe_walk_income import WALK_PLANT
    from hexapod_core.tripod_gait import TripodGait

    vx_ref, vy_ref, wz_ref = CELLS[cell]
    cfg = load_config()
    stack = dict(BASE_CFG)
    stack.update(CONT8M_DELTAS)
    if extra:
        stack.update(extra)
    for key, val in stack.items():
        sec, leaf = key.split(".", 1)
        cfg.setdefault(sec, {})[leaf] = val
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=False,
        dr_scale=0.0, episode_seconds=seconds, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    env.reset()
    tr = env._goal_traj
    tr.vx[:] = vx_ref
    tr.vy[:] = vy_ref
    tr.wz[:] = wz_ref
    gait = TripodGait(vx=0.0, lift=0.025)
    gait.sync_plant_stance(*WALK_PLANT)
    gait.reset_phase()
    tot = 0.0
    t_gait = 0.0
    walk_ticks = 0
    other_ticks = 0
    sums: dict = {}
    wz_meas: list[float] = []
    yaw0 = None
    yaw_last = 0.0
    while True:
        R = env.data.xmat[env._chassis_bid].reshape(3, 3)
        yaw = math.atan2(R[1, 0], R[0, 0])
        if yaw0 is None:
            yaw0 = yaw
        yaw_last = yaw
        if drive == "crab":
            # hold the world chord while never yawing the stroke frame
            gv = (vx_ref * math.cos(-yaw) - vy_ref * math.sin(-yaw),
                  vx_ref * math.sin(-yaw) + vy_ref * math.cos(-yaw))
            om = 0.0
        else:
            gv = (vx_ref, vy_ref)
            om = factor * wz_ref
        t_gait += env.dt
        gait.set_velocity(vx=gv[0], vy=gv[1], omega=om)
        act = q_rad_to_action(
            np.asarray(gait.desired_deg(t_gait)) * DEG2RAD)
        _o, r, term, trunc, info = env.step(act)
        if info.get("goal_mode", "walk") == "walk":
            walk_ticks += 1
            tot += float(r)
            wz_meas.append(float(env._body_wz()))
            for k, v in info.items():
                if isinstance(v, (int, float)) and k.startswith("reward_"):
                    sums[k] = sums.get(k, 0.0) + float(v)
        else:
            other_ticks += 1
        if term or trunc:
            break
    env.close()
    wz_arr = np.asarray(wz_meas) if wz_meas else np.zeros(1)
    return dict(
        total=tot, sums=sums, walk_ticks=walk_ticks,
        other_ticks=other_ticks,
        wz_mean=float(np.mean(wz_arr)), wz_med=float(np.median(wz_arr)),
        net_yaw_deg=math.degrees(yaw_last - (yaw0 or 0.0)),
        terminated=bool(term), dt=env.dt)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seconds", type=float, default=6.0)
    ap.add_argument("--extra", action="append", default=[],
                    help="extra cfg overrides key=val")
    args = ap.parse_args()
    extra = {}
    for kv in args.extra:
        k, v = kv.split("=", 1)
        extra[k] = float(v)
    plans = {
        "tip-left":  [("f-1.0", -1.0), ("f0", 0.0), ("f0.5", 0.5),
                      ("f1.0", 1.0), ("f1.33", 1.33)],
        "tip-right": [("f-1.0", -1.0), ("f0", 0.0), ("f0.5", 0.5),
                      ("f1.0", 1.0), ("f1.33", 1.33)],
        "arc-right": [("f0", 0.0), ("f0.5", 0.5), ("f1.0", 1.0),
                      ("f1.33", 1.33), ("crab", None)],
    }
    print(f"stack = probe_combined_frame.CFG + cont8m deltas "
          f"{CONT8M_DELTAS} + {extra or 'none'}; "
          f"{args.seconds}s per drive, walk-tick-scored")
    for cell, drives in plans.items():
        vx_ref, vy_ref, wz_ref = CELLS[cell]
        print(f"\n#### cell {cell}: vx_ref={vx_ref} wz_ref={wz_ref}")
        for name, factor in drives:
            drive = "crab" if factor is None else "scripted"
            r = _rollout(cell, drive, factor or 0.0, args.seconds, extra)
            print(f"== {name:6s} total={r['total']:+9.1f} "
                  f"wz_mean={r['wz_mean']:+.3f} wz_med={r['wz_med']:+.3f} "
                  f"(ref {wz_ref:+.2f}) net_yaw={r['net_yaw_deg']:+7.1f}deg "
                  f"walk_ticks={r['walk_ticks']} "
                  f"other={r['other_ticks']} term={r['terminated']}")
            for k in sorted(r["sums"]):
                print(f"   {k:38s} {r['sums'][k]:+10.1f}")


if __name__ == "__main__":
    main()
