"""Actuator-current-envelope diagnostic for the `walkcurr` LOWER gap.

Sibling of `probe_rise_current_envelope.py` (same conventions, same
LAUNCH_OVERRIDES, same output schema), built for the lower-stage
question that track's own STATUS flagged 2026-09-17 ("the honest next
question is whether the `lower` height-ramp target is kinematically/
dynamically reachable at all under the corrected 3.5 kg mesh + its
actuator current envelope ... a cheap first cut (no training): a
static IK/torque-budget check of whether the commanded end-of-ramp
height is solvable and holdable without exceeding the actuator current
model"). Four independent lower-mode arms (score-prog, ratchet-partial,
dense-posture, stage-gate x2 directions -- 4/4 FAIL-MECHANISM) all park
the same lineage's own `lower` descent at the identical ~28-31mm/
0-2-of-12-ok floor no matter which reward/gate lever moved; this
answers whether that floor is a torque-budget ceiling or a behavior
problem.

This is a DIAGNOSTIC PROBE ONLY: it replays a purely GEOMETRIC,
OPEN-LOOP descent (no policy in the loop, nothing trained here, no
motion prior fed to any actor) through the exact `joint_goal` raw
18-joint action space this lineage trains in, to measure PHYSICS —
per `RL_GOALS.md` rl_only rules this never touches any training
lineage. The open-loop q_rad target at each tick comes from
`FixedFootBodyIK` (a fixed-foot analytic IK -- feet stay anchored at
the settled plant footprint while the commanded body height ramps
down), used here purely as a reference-trajectory ORACLE, exactly as
`probe_rise_current_envelope.py` replays a scripted `q_rad` npz — never
as a training signal for any actor.

Usage (CPU, no GPU, no checkpoint)::

    uv run python -m rl_move.sim.probe_lower_achievability
    uv run python -m rl_move.sim.probe_lower_achievability --depths-mm 15,25,35,45,55,65,75,88
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from rl_move.body_ik import BodyOffset, FixedFootBodyIK
from rl_move.config import load_config
from rl_move.robot_state import DEG2RAD
from rl_move.sim.joint_task import SimHexapodJointGoalEnv, q_rad_to_action
from rl_move.sim.servo_model import SimServoParams

ROOT = Path(__file__).resolve().parents[2]

# Verbatim from the `cw-stance50hz-rlonly-currentcap29-*-lowerstagegate-*`
# lineage's own ledger extra_args -- the exact stack the persistent
# ~28-31mm/0-2-of-12-ok floor was measured on. Only physics-load-bearing
# keys kept (goal.joint_action_bias_* only shifts what a POLICY's raw
# output means; we command an absolute q_rad target directly via
# q_rad_to_action, so applying it here would silently offset our
# intended pose instead of reflecting real physics -- same reasoning
# as probe_rise_current_envelope.py).
LAUNCH_OVERRIDES = {
    ("env", "model_source"): "mesh_mjx",
    ("control", "hz"): 50.0,
    ("safety", "max_delta_q_deg"): 0.75,
    ("safety", "max_current_a"): 2.9,
    ("actions", "max_height_mm"): 88.0,
}

EPISODE_SECONDS = 15.0
# The lineage's own hold/ramp pacing (GoalGenerator.lower_hold_s /
# lower_ramp_s, both hardcoded -- see goal_task.py).
HOLD_S = 1.0
RAMP_S = 5.0
DEFAULT_DEPTHS_MM = (15.0, 25.0, 35.0, 45.0, 55.0, 65.0, 75.0, 85.0, 88.0)


def _make_env(seed: int, episode_seconds: float) -> SimHexapodJointGoalEnv:
    cfg = load_config()
    for (sec, leaf), val in LAUNCH_OVERRIDES.items():
        cfg.setdefault(sec, {})[leaf] = val
    env = SimHexapodJointGoalEnv(
        params=SimServoParams.from_cfg(cfg), randomize=False,
        dr_scale=0.0, episode_seconds=episode_seconds, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for a in [a for a in vars(gen) if a.startswith("p_")]:
        setattr(gen, a, 0.0)
    gen.p_lower = 1.0
    return env


def _height_schedule(depth_m: float, n_steps: int, dt: float) -> np.ndarray:
    """Reproduce GoalGenerator's own `mode == "lower"` plain-descent
    schedule (goal_task.py) for a PINNED depth: 0 for HOLD_S, then a
    linear ramp to -depth_m over RAMP_S, held there to the episode end.
    """
    height = np.zeros(n_steps)
    hold_n = max(1, int(round(HOLD_S / dt)))
    ramp_n = max(1, int(round(RAMP_S / dt)))
    target = -depth_m
    height[:] = target
    height[:hold_n] = 0.0
    end = min(hold_n + ramp_n, n_steps)
    if end > hold_n:
        height[hold_n:end] = np.linspace(0.0, target, end - hold_n)
    return height


def replay_open_loop(depth_mm: float, seed: int,
                      episode_seconds: float = EPISODE_SECONDS) -> dict:
    """Open-loop, feet-anchored IK descent to `depth_mm` below the
    settled plant, through the raw joint_goal action space."""
    env = _make_env(seed, episode_seconds)
    env._goal_gen.lower_m = (depth_mm * 0.001, depth_mm * 0.001)
    obs, _ = env.reset()
    n = env.episode_steps + 1
    height = _height_schedule(depth_mm * 0.001, n, env.dt)
    ik = FixedFootBodyIK(cfg=env.cfg)
    ik.reset(env._q_nom, plant_q_rad=env._plant_deg * DEG2RAD)

    cur_max, cur_samples, step = 0.0, [], 0
    term = trunc = False
    reason = None
    ik_fail = False
    while not (term or trunc):
        h = float(height[min(step, n - 1)])
        res = ik.solve(BodyOffset(roll=0.0, pitch=0.0, height=h,
                                  x=0.0, y=0.0, curl=0.0))
        if not res.ok:
            ik_fail = True
        act = q_rad_to_action(res.q_rad)
        obs, r, term, trunc, info = env.step(np.asarray(act).ravel())
        cur = env._state.servo_current
        if cur is not None:
            cur_now = float(np.max(np.abs(cur)))
            cur_max = max(cur_max, cur_now)
            cur_samples.append(cur_now)
        step += 1
        if term:
            reason = info.get("termination_reason")
    h_rel = float(env.data.xpos[env._chassis_bid, 2]) - env._z0
    h_err_end_mm = round(1000 * (h_rel - height[min(step, n - 1)]), 1)
    p95 = float(np.percentile(cur_samples, 95)) if cur_samples else 0.0
    env.close()
    return {
        "depth_mm": depth_mm, "seed": seed, "steps": step,
        "term": bool(term), "reason": reason, "ik_fail": ik_fail,
        "cur_max_a": round(cur_max, 3), "cur_p95_a": round(p95, 3),
        "h_err_end_mm": h_err_end_mm,
        "over_trip": cur_max >= float(
            LAUNCH_OVERRIDES[("safety", "max_current_a")]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depths-mm", default=",".join(
        str(d) for d in DEFAULT_DEPTHS_MM))
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--episode-seconds", type=float, default=EPISODE_SECONDS)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    depths = [float(d) for d in args.depths_mm.split(",")]
    seeds = [int(s) for s in args.seeds.split(",")]

    rows = []
    for depth_mm in depths:
        for seed in seeds:
            row = replay_open_loop(depth_mm, seed, args.episode_seconds)
            rows.append(row)
            print(json.dumps(row))

    out = args.out or (ROOT / "logs/probe_lower_achievability.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
