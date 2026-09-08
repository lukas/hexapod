"""Zero-training diagnostic: calibrate `reward.walk_leg_loadslip_
ratio_target` against a REAL checkpoint's own deterministic walk
behavior, the same way `reward.walk_leg_duty_ratio_target` (0.30) was
set from "the calibrated passing population's own p10 worst-leg
ratio" (see `walk_task.py` near `walk_legduty_ratio_charge`) instead
of an assume-and-go guess.

Why this exists (2026-09-08, walkcurr/assistfade triage): the n=3
`walk_leg_loadslip_ratio_charge` canary batch (target=1.5, charge=150)
closed 0/3 -- not a clean regression, but a "saturated excess, no
repair gradient" shape: `env/walk_leg_loadslip_ratio_excess` sat near
0.86-1.04 for the ENTIRE post-grace window on 2 of 3 seeds (STATUS.md
09-08 ~13:3x/13:4x), meaning the worst leg's own peer-ratio almost
never dropped below ~2.4-2.5x its peers even in a healthy-looking
walk -- i.e. target=1.5 may simply be below what ANY gait (good or
bad) on this lineage actually achieves, turning the charge into a
constant background tax instead of a corrective gradient. This script
answers that directly instead of guessing again: replay an already-
PASSED checkpoint's own deterministic walk rollouts with
`goal.walk_contact_diagnostics=1` (existing, default-off, ZERO effect
on reward/action -- see `walk_task.py`'s `contact_diag` block) so the
per-foot tangential contact velocity is visible every tick without
turning any charge on, then compute the SAME peer-excluded-MEDIAN
ratio formula the charge itself uses
(`walk_legslip_ratio_tick`/`walk_legslip_ratio_charge`, imported
verbatim -- no reimplementation) over the observed rollout. Report
p10/p50/p90 of the worst-leg ratio: if a known-GOOD gait's own p50
sits well above the assumed target, the target (not the mechanism) is
what needs to move before spending another dose canary.

Reward-affecting cfg (reward.*, dr.*) is deliberately NOT replayed
from the source run: this loads a FROZEN checkpoint and only its
observation-shaping cfg (goal.*/control.*/env.*/action-box/heading-
set) affects a frozen policy's deterministic actions -- reward.* does
not change what `model.predict(obs)` returns, and dr.* is skipped on
purpose to match the gate suite's own DR-0 clean read (`ops.sh review`
reports "dr=0.0" for every gate eval this finding is about). Read-only
analysis tool: never trains, never writes to the ledger/checkpoints.

Usage:
  uv run python -m rl_move.sim.calibrate_loadslip_target \
      rl_move/sim/policies/<ckpt>.zip \
      --cfg-set goal.walk_heading_set=[...] --cfg-set goal.walk_pure=1 \
      [--episodes 12] [--episode-seconds 20] [--tau-s 1.0]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT,):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.config import load_config  # noqa: E402
from rl_move.sim.servo_model import SimServoParams  # noqa: E402
from rl_move.sim.walk_task import (  # noqa: E402
    SimHexapodJointWalkEnv,
    walk_legslip_ratio_charge,
    walk_legslip_ratio_tick,
)


def _build_env(cfg_overrides: dict, *, episode_seconds: float, seed: int):
    from rl_move.sim.train_ppo_sim import _parse_cfg_set

    cfg = load_config()
    for key, parsed in _parse_cfg_set(cfg_overrides).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    # Always DR-0 clean (matches the gate suite's own "dr=0.0" read this
    # calibration is meant to be comparable with) and diagnostics-on.
    cfg.setdefault("goal", {})["walk_contact_diagnostics"] = 1.0
    return SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg),
        randomize=False,
        dr_scale=0.0,
        episode_seconds=episode_seconds,
        seed=seed,
        render_mode=None,
        cfg=cfg,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("--episodes", type=int, default=12)
    ap.add_argument("--episode-seconds", type=float, default=20.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tau-s", type=float, default=1.0,
                    help="EMA time constant -- match reward.walk_leg_"
                         "loadslip_ratio_tau_s (default 1.0)")
    ap.add_argument("--cfg-set", action="append", default=[],
                    help="observation-shaping cfg overrides from the "
                         "source run's own launch argv (goal.*/"
                         "control.*/env.*), e.g. "
                         "goal.walk_heading_set=[0.0,...]. reward.*/"
                         "dr.* entries are harmless to pass but have "
                         "no effect on a frozen checkpoint's actions "
                         "and are skipped from the DR-0 read either way.")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    # Reward/DR overrides don't change a frozen policy's actions and
    # would only add noise/confusion to this read -- drop them.
    cfg_overrides = [c for c in args.cfg_set
                     if not (c.startswith("reward.") or c.startswith("dr."))]
    env = _build_env(cfg_overrides, episode_seconds=args.episode_seconds,
                     seed=args.seed)
    if hasattr(env, "set_goal_mix"):
        # Pure-walk read (matches the training run's own --goal-mix
        # walk=1.0 convention) -- without this, goal-mix tasks sample
        # their full mode mix (hold/rise/track/...) and most episodes
        # never touch "walk" at all.
        env.set_goal_mix({"walk": 1.0})

    from rl_move.sim.gru_policy import load_checkpoint_auto
    model = load_checkpoint_auto(args.checkpoint, device="cpu")

    worst_ratios: list[float] = []
    per_leg_ratios: list[list[float]] = [[] for _ in range(6)]
    n_ticks = 0
    n_episodes_walked = 0
    for ep in range(args.episodes):
        obs, _info0 = env.reset()
        if hasattr(model, "reset"):
            model.reset()
        ema = [0.0] * 6
        ticks_this_ep = 0
        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, _r, term, trunc, info = env.step(action)
            done = bool(term or trunc)
            if info.get("goal_mode") != "walk":
                continue
            tv = [float(info.get(f"walk_foot{f}_tangent_vel_m_s", 0.0))
                  for f in range(6)]
            ema = walk_legslip_ratio_tick(ema, tv=tv, dt=env.dt,
                                          tau_s=args.tau_s)
            # target=0.0 -> worst_excess == max(ratio); ratios is the
            # full per-leg peer-excluded-median array we actually want.
            _worst_excess, ratios = walk_legslip_ratio_charge(ema, 0.0)
            worst_ratios.append(max(ratios))
            for f in range(6):
                per_leg_ratios[f].append(ratios[f])
            n_ticks += 1
            ticks_this_ep += 1
        if ticks_this_ep > 0:
            n_episodes_walked += 1

    def pct(a: list[float], p: float) -> float:
        return float(np.percentile(a, p)) if a else float("nan")

    report = {
        "checkpoint": str(args.checkpoint),
        "episodes_requested": args.episodes,
        "episodes_with_walk_ticks": n_episodes_walked,
        "n_ticks_walk": n_ticks,
        "tau_s": args.tau_s,
        "worst_leg_ratio_percentiles": {
            str(p): pct(worst_ratios, p) for p in (10, 25, 50, 75, 90, 95)},
        "per_leg_ratio_median": [pct(per_leg_ratios[f], 50)
                                 for f in range(6)],
        "current_assumed_target": 1.5,
    }
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)


if __name__ == "__main__":
    main()
