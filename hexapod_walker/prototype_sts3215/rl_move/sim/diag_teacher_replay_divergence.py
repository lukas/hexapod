"""diag_teacher_replay_divergence.py -- why does distill_gru.py's
teacher-replay collection see BIMODAL returns on a checkpoint whose
own DR-0 gate is clean 24/24?

WHY (standwalk STATUS 2026-09-11 ~20:3x/~21:5x): the first real
``--walk-teacher-run``/``--stance-teacher-run`` collection probe (8
episodes, 1 epoch, ``--dr-scale 0.0``) returned per-episode walk
returns ~[-468, -520, +521, +415] (4 episodes) that do NOT match this
exact checkpoint's own clean DR-0 gate (24/24 gait_valid, zero
falls). Two named, UNTESTED candidate explanations were left for
"the next reader":

  (a) ``distill_gru._make_env`` always builds the collection env with
      ``randomize=True`` (a live ``DomainRandomizer``, even at
      ``dr_scale=0``), while ``eval_checkpoint.py``'s own harness uses
      ``randomize=(dr_scale>0 or has_dr_override)`` -- i.e.
      ``randomize=False`` (``env.randomizer is None``) at
      ``dr_scale=0``. ``RandRanges.scaled(0)`` zeros every randomized
      quantity's WIDTH and every event PROBABILITY (bad_start/
      tipped_start/fault/push all ``* 0``), so the two SHOULD be
      physically near-identical -- but sampling a (zero-width)
      randomizer still draws from ``self.rng`` once per reset, a draw
      the no-randomizer path never makes, so the two are NOT the same
      seeded rollout even when reset with the same integer seed.
  (b) the pulled walk-teacher cfg replays the TRAINING-time command
      distribution (e.g. ``goal.walk_cmd_mode=stress_mix``) verbatim
      at collection time, which may draw harder commands (backward /
      fast turn-in-place / stop-then-reverse) than whatever narrower
      panel the checkpoint's own DR-0 gate happens to exercise -- a
      command-distribution mismatch, not an RNG/DR bug at all.

This script builds the exact walk-mode collection env BOTH ways
(matching ``distill_gru._make_env``'s ``randomize=True`` and
``eval_checkpoint.py``'s ``randomize=False``, same pulled cfg either
way) against the SAME walk teacher, rolls out N matched-seed
deterministic episodes on each, and reports per-episode return,
termination reason, and the commanded speed drawn (via
``goal.walk_cmd_metrics=1``, additive telemetry-only cfg, no other
effect) so explanation (a) and (b) can be told apart before spending
a real collection budget.

THIS IS A DIAGNOSTIC ONLY: zero training spend, no shared-code edits,
CPU harness. It does not launch anything or change any default.

    uv run python -m rl_move.sim.diag_teacher_replay_divergence \
        --walk-teacher-run cw-walk50hz-amp-mesh-m2plain-scratch-styleoff-acq15m \
        --episodes 12 --seed 0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _rollout(env, teacher, seed: int) -> dict:
    import torch

    obs, _ = env.reset(seed=seed)
    done = False
    ep_ret = 0.0
    n_ticks = 0
    speeds = []
    term_reason = None
    while not done:
        act, _ = teacher.predict(obs, deterministic=True)
        obs, r, term, trunc, info = env.step(np.clip(act, -1.0, 1.0))
        ep_ret += float(r)
        n_ticks += 1
        if "cmd_speed_m_s" in info:
            speeds.append(float(info["cmd_speed_m_s"]))
        if term:
            term_reason = info.get("termination_reason")
        done = term or trunc
    return {"seed": seed, "return": ep_ret, "ticks": n_ticks,
            "term_reason": term_reason,
            "cmd_speed_mean": (float(np.mean(speeds)) if speeds else None)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--walk-teacher-run", required=True)
    ap.add_argument("--stance-teacher-run", default=None,
                    help="optional -- match a real distill_gru.py "
                         "--stance-teacher-run pairing exactly, since "
                         "merge_teacher_cfgs unions BOTH sides' keys "
                         "into the walk-env cfg too (09-11 ~21:5x fix)")
    ap.add_argument("--episodes", type=int, default=8)
    ap.add_argument("--seed0", type=int, default=0,
                    help="first seed; episodes use seed0..seed0+episodes-1")
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--cfg-set", action="append", default=[],
                    help="K=V, resolves a stance/walk pulled-cfg "
                         "conflict on purpose (same convention as "
                         "distill_gru.py's own --cfg-set)")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    # Cap thread pools before torch/numpy heavy imports (same fix as
    # distill_gru.py / eval_checkpoint.py -- MuJoCo-stepping +
    # tiny-MLP-forward bound, never matmul-bound).
    import os
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ.setdefault(v, "2")

    from stable_baselines3 import PPO

    from .distill_gru import _build_cfg, merge_teacher_cfgs, pull_teacher_run
    from .servo_model import SimServoParams
    from .walk_task import SimHexapodJointWalkEnv

    pulled = pull_teacher_run(args.walk_teacher_run)
    print(f"[diag] walk-teacher-run {args.walk_teacher_run}: "
         f"ckpt={pulled['checkpoint'].name} dr_scale={pulled['dr_scale']} "
         f"cfg={pulled['cfg']}")
    stance_pulled = None
    if args.stance_teacher_run:
        stance_pulled = pull_teacher_run(args.stance_teacher_run)
        print(f"[diag] stance-teacher-run {args.stance_teacher_run}: "
             f"ckpt={stance_pulled['checkpoint'].name} "
             f"cfg={stance_pulled['cfg']}")
    from .train_ppo_sim import _parse_cfg_set
    explicit = {"goal.walk_cmd_metrics": 1.0}
    explicit.update(_parse_cfg_set(args.cfg_set))
    _, walk_extra = merge_teacher_cfgs(
        stance_pulled["cfg"] if stance_pulled else None,
        pulled["cfg"], explicit, {})
    cfg = _build_cfg(walk_extra)

    teacher = PPO.load(pulled["checkpoint"], device="cpu")
    params = SimServoParams.load()

    variants = {
        "randomize_true_dr0": dict(randomize=True, dr_scale=0.0),
        "randomize_false": dict(randomize=False, dr_scale=0.0),
    }
    results = {}
    for name, kw in variants.items():
        env = SimHexapodJointWalkEnv(
            params=params, episode_seconds=args.episode_seconds, cfg=cfg,
            seed=args.seed0, **kw)
        env.set_goal_mix({"walk": 1.0})
        rows = [_rollout(env, teacher, args.seed0 + i)
               for i in range(args.episodes)]
        rets = [r["return"] for r in rows]
        print(f"\n[diag] {name}: n={len(rows)} "
             f"return med={np.median(rets):.1f} "
             f"min={min(rets):.1f} max={max(rets):.1f}")
        for r in rows:
            print(f"    seed={r['seed']:3d} return={r['return']:8.1f} "
                 f"ticks={r['ticks']:4d} term={r['term_reason']} "
                 f"cmd_speed_mean={r['cmd_speed_mean']}")
        results[name] = rows

    # Direct byte-comparison of the two variants' FIRST reset
    # observation at the same seed -- if these already differ, the
    # two envs never faced the same episode content at all (points at
    # (a); if they match but returns still diverge downstream, points
    # at command-content drift mid-episode or at (b)).
    env_t = SimHexapodJointWalkEnv(params=params, cfg=cfg,
                                   episode_seconds=args.episode_seconds,
                                   seed=args.seed0, **variants["randomize_true_dr0"])
    env_f = SimHexapodJointWalkEnv(params=params, cfg=cfg,
                                   episode_seconds=args.episode_seconds,
                                   seed=args.seed0, **variants["randomize_false"])
    env_t.set_goal_mix({"walk": 1.0})
    env_f.set_goal_mix({"walk": 1.0})
    obs_t, _ = env_t.reset(seed=args.seed0)
    obs_f, _ = env_f.reset(seed=args.seed0)
    obs_match = bool(np.allclose(obs_t, obs_f, atol=1e-6))
    print(f"\n[diag] same-seed reset obs match "
         f"(randomize=True,dr_scale=0 vs randomize=False): {obs_match}"
         f"{'' if obs_match else f' max_abs_diff={np.max(np.abs(obs_t - obs_f)):.4g}'}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(
            {"walk_teacher_run": args.walk_teacher_run,
             "obs_match_same_seed": obs_match, "results": results}, indent=2))
        print(f"[diag] wrote {out_path}")


if __name__ == "__main__":
    main()
