"""System-ID baseline: does the SCRIPTED (open-loop, no policy) lower
descent itself draw rail-level trip current, or is the ~2.6-2.9 A
sustained reading only seen in `cw-stance50hz-rlonly-lowerrole-scratch-
sac-*` policy rollouts a policy-specific excess?

Scoped item: `walkcurr/STATUS.md` Next(1)'s 2026-10-01 stall-
corroboration follow-up named this as the CHEAPER of its two unscoped
next questions and recommended doing it first: "a current-cap system-
ID check: what sustained torque does the scripted/stance baseline
itself draw during an equivalent load phase, to tell whether 2.6-2.9A
is normal-for-this-motion or policy-specific excess" (see
`rl_docs/tracks/walkcurr/lowerrole_overcurrent_stallclass_2026-10-01/
SUMMARY.md`'s Recommendation section). Zero GPU spend, CPU MuJoCo only.

WHY `probe_lower_achievability.py` itself does not already answer
this: that script's own `cur_max_a`/`cur_p95_a` read
`env._state.servo_current` -- under the DEFAULT `bus.current_model=
"power"` model (sim_env.py, 2026-09-19) that signal is the validated
MECHANICAL-POWER current (iq/18 + k*|torque*qvel|), which reads ~0 A
at a quasi-static hold (high torque, ~0 velocity -> ~0 mechanical
power) BY DESIGN (same reasoning robot_state.py's own
`over_current_signal` docstring gives for why the SafetyLayer trip
does NOT key on `servo_current`). An open-loop, perfectly-tracked IK
descent is exactly this kind of near-zero-velocity, high-support-load
motion, so `servo_current` alone cannot see what the policy's
over_current TRIP actually responds to.

This module reuses `probe_lower_achievability.py`'s env/schedule/IK
machinery UNCHANGED (same `LAUNCH_OVERRIDES`, same bus 400/20 pin, same
HOLD_S/RAMP_S pacing) and swaps only the captured signal for
`robot_state.over_current_reading` (== `over_current_signal`, the
exact legacy torque-proxy SafetyLayer trips on and `trip_summary`
analyzes, per `audit_over_current.py`'s anatomy: `min(|torque|*1.2,
3.0)` lowpassed, rails at 2.64 A when |torque| saturates the actuator's
+-2.2 N*m forcerange). Comparing per-joint peak torque-proxy current
under PERFECT, DISTURBANCE-FREE tracking against the policy's own
2.6-2.9 A over_current trips tells us whether supporting the
mesh-model's 3.5 kg body through this depth range is BY ITSELF
(independent of any policy quality) already a near-rail load on
specific joints -- in which case the lower role's over_current rate is
substantially a system-ID / torque-budget fact (the honest fix being
`safety.max_current_a` recalibration or an actuator-contract change,
not more reward shaping) -- or whether the scripted baseline stays
comfortably under rail everywhere, in which case the policy's own
rail-level current is excess the policy is adding (a genuine
control-quality question, reward-shaping back in scope).

Usage (CPU, no GPU, no checkpoint)::

    uv run python -m rl_move.sim.probe_lower_scripted_current_baseline
    uv run python -m rl_move.sim.probe_lower_scripted_current_baseline \\
        --depths-mm 25,55,75,88 --seeds 0,1,2
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from hexapod_core.joint_frame import JOINT_NAMES
from rl_move.body_ik import BodyOffset, FixedFootBodyIK
from rl_move.robot_state import N_JOINTS, over_current_reading
from rl_move.sim.joint_task import q_rad_to_action
from rl_move.sim.probe_lower_achievability import (
    DEFAULT_DEPTHS_MM,
    EPISODE_SECONDS,
    LAUNCH_OVERRIDES,
    _height_schedule,
    _make_env,
)
from rl_move.robot_state import DEG2RAD

ROOT = Path(__file__).resolve().parents[2]
TRIP_A = float(LAUNCH_OVERRIDES[("safety", "max_current_a")])


def replay_open_loop_trip_trace(depth_mm: float, seed: int,
                                episode_seconds: float = EPISODE_SECONDS
                                ) -> dict:
    """Same open-loop feet-anchored IK descent as
    `probe_lower_achievability.replay_open_loop`, but captures the full
    (T, 18) trip-relevant `over_current_reading` trace instead of the
    mechanical-power `servo_current` scalar max, and reports PER-JOINT
    peak/rail-dwell stats (no aggregation across joints -- the
    question is WHICH joints approach rail, to compare directly
    against the policy's own L1/L5-hip-concentrated signature)."""
    env = _make_env(seed, episode_seconds)
    env._goal_gen.lower_m = (depth_mm * 0.001, depth_mm * 0.001)
    obs, _ = env.reset()
    n = env.episode_steps + 1
    height = _height_schedule(depth_mm * 0.001, n, env.dt)
    ik = FixedFootBodyIK(cfg=env.cfg)
    ik.reset(env._q_nom, plant_q_rad=env._plant_deg * DEG2RAD)

    trace = []
    term = trunc = False
    reason = None
    step = 0
    while not (term or trunc):
        h = float(height[min(step, n - 1)])
        res = ik.solve(BodyOffset(roll=0.0, pitch=0.0, height=h,
                                  x=0.0, y=0.0, curl=0.0))
        act = q_rad_to_action(res.q_rad)
        obs, r, term, trunc, info = env.step(np.asarray(act).ravel())
        sig = over_current_reading(env._state)
        trace.append(np.asarray(sig, dtype=float) if sig is not None
                     else np.zeros(N_JOINTS))
        step += 1
        if term:
            reason = info.get("termination_reason")
    env.close()

    arr = np.abs(np.stack(trace))  # (T, 18)
    per_joint_max = arr.max(axis=0)
    per_joint_dwell_frac = (arr >= TRIP_A).mean(axis=0)
    final_joint = int(np.argmax(per_joint_max))
    return {
        "depth_mm": depth_mm, "seed": seed, "steps": step,
        "term": bool(term), "reason": reason,
        "per_joint_max_a": per_joint_max.round(3).tolist(),
        "per_joint_rail_dwell_frac": per_joint_dwell_frac.round(4).tolist(),
        "worst_joint": JOINT_NAMES[final_joint],
        "worst_joint_max_a": round(float(per_joint_max[final_joint]), 3),
        "any_joint_at_rail": bool(np.any(per_joint_max >= TRIP_A)),
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
            row = replay_open_loop_trip_trace(depth_mm, seed,
                                              args.episode_seconds)
            rows.append(row)
            print(json.dumps({k: v for k, v in row.items()
                              if k != "per_joint_rail_dwell_frac"}))

    # Aggregate: per-joint max across ALL depths/seeds swept, so a
    # single joint's worst-case rail proximity shows regardless of
    # which depth triggers it.
    all_max = np.stack([r["per_joint_max_a"] for r in rows])
    agg_max = all_max.max(axis=0)
    agg = {JOINT_NAMES[j]: round(float(agg_max[j]), 3)
           for j in range(N_JOINTS)}
    agg_sorted = dict(sorted(agg.items(), key=lambda kv: -kv[1]))

    out = args.out or (ROOT / "logs/probe_lower_scripted_current_baseline.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"trip_threshold_a": TRIP_A, "rows": rows,
         "aggregate_per_joint_max_a_sorted": agg_sorted}, indent=1))
    print(f"wrote {out}")
    print("aggregate per-joint max (A), worst first:")
    for name, val in list(agg_sorted.items())[:6]:
        print(f"  {name}: {val}")


if __name__ == "__main__":
    main()
