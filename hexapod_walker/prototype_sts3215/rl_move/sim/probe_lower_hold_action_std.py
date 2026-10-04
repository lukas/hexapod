"""Zero-GPU diagnostic (walkcurr lowerrole residual ~24-28% composed
over_current gap, genuinely-new-mechanism scoping, 2026-10-04):
does the trained SAC lower-role policy's OWN action distribution
collapse (near-zero Gaussian std) during the terminal HOLD sub-phase
of the `lower` episode, relative to the preceding DESCENT ramp?

## Why this probe, not a fourth reward lever or a GPU canary
`lowerrole_terminal_support_forensics_2026-10-02/SUMMARY.md` found a
universal, near-IDENTICAL (passing vs failing episodes alike) 2-leg
(L2+L5) terminal support habit, and every pricing lever that asked for
a DIFFERENT support pattern (`k_load_even`, `k_stance_count`,
`k_load_rotate`) destabilized the only stable configuration the policy
has ever discovered -- the SAME tilt-failure signature every time,
"monotone bad," not fixable by another dose (walkcurr/STATUS.md,
2026-10-03). Before spending GPU on an "exploration-schedule" idea
(targeted entropy/noise boost during the hold segment specifically, so
the policy keeps sampling alternative support patterns instead of
freezing on the first one it finds), check CHEAPLY whether the premise
that idea rests on -- SAC's own policy head collapsing to a
near-deterministic output once it finds a stable hold config, with no
further exploration of alternatives during the ~9s hold -- is actually
true on the real champion checkpoint. If the action std during hold is
NOT depressed relative to descent, the "entropy starves hold-phase
exploration" story is false and that whole mechanism class should not
be built; if it IS depressed, that is positive evidence for scoping an
hold-phase-targeted exploration fix next (still unbuilt either way --
this file only reads an existing checkpoint, it does not implement
the fix).

Read-only / CPU-only, same class of tool as
`probe_lower_achievability.py` / `probe_turn_authority.py`: loads an
already-adopted checkpoint (default the standing lower-role champion,
`drramp-acq1 s0`), rolls out N `lower`-mode episodes from a clean plant
reset (randomize=False, matching the registered composed direct-arm
gate's own env construction, `eval_lifecycle_handoff_rlonly.py::
_build_env`), and at every tick queries the SAC actor's own
`get_action_dist_params` for the pre-squash Gaussian std (the policy's
OWN uncertainty, not the realized action noise / not the executed
action) -- deterministic rollout (matching the gate's "direct" det
arm) so the trajectory itself is reproducible while still reading the
stochastic head's parameters off every visited state. Reports mean
action std (across the 18 action dims) for the DESCENT window
(hold_s..hold_s+ramp_s) vs the TERMINAL-HOLD window (last 2s of the
episode), split by whether the episode ultimately passed
(|height_err_end_mm|<=15 and not terminated) or failed.

Nothing trains here and no training lineage is touched; this changes
no cfg default and adds no key.

Usage::

    uv run python -m rl_move.sim.probe_lower_hold_action_std
    uv run python -m rl_move.sim.probe_lower_hold_action_std \\
        --checkpoint rl_move/sim/policies/ppo_goal_cw_stance50hz_rlonly_lowerrole_scratch_sac_s0_drramp_acq1.zip \\
        --episodes 18 --seed 0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CKPT = (ROOT / "rl_move" / "sim" / "policies" /
                "ppo_goal_cw_stance50hz_rlonly_lowerrole_scratch_sac_s0_"
                "drramp_acq1.zip")

HOLD_S = 1.0   # goal_task.py GoalGenerator.lower_hold_s (unset by this
               # recipe's own CFG_ARGS, so the code default applies)
RAMP_S = 5.0   # ditto, lower_ramp_s code default
TERMINAL_WINDOW_S = 2.0


def _build_env(cfg_args: list[str], *, episode_seconds: float, seed: int):
    from rl_move.config import load_config
    from .cfg_set import parse_cfg_set
    from .servo_model import SimServoParams
    from .walk_task import SimHexapodJointWalkEnv

    cfg = load_config()
    for key, parsed in parse_cfg_set(cfg_args).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg), cfg=cfg, randomize=False,
        episode_seconds=episode_seconds, seed=seed, render_mode=None)
    return env


def _set_mix_lower_only(gen) -> None:
    for attr in [a for a in vars(gen) if a.startswith("p_")]:
        setattr(gen, attr, 0.0)
    gen.p_walk = 0.0
    gen.p_lower = 1.0


def run(checkpoint: str, episodes: int, seed: int,
        episode_seconds: float) -> dict:
    from .cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp import (
        CFG_ARGS as LOWER_CFG_ARGS,
    )
    from .gru_policy import load_checkpoint_auto

    env = _build_env(LOWER_CFG_ARGS, episode_seconds=episode_seconds,
                      seed=seed)
    model = load_checkpoint_auto(checkpoint, device="cpu")
    n_model = int(model.observation_space.shape[0])

    import torch as th
    actor = model.policy.actor

    dt = env.dt
    hold_n = max(1, int(round(HOLD_S / dt)))
    ramp_n = max(1, int(round(RAMP_S / dt)))
    descent_lo, descent_hi = hold_n, hold_n + ramp_n
    term_n = max(1, int(round(TERMINAL_WINDOW_S / dt)))
    n_steps = max(1, int(round(episode_seconds / dt)))

    per_ep = []
    for ep in range(episodes):
        gen = env._goal_gen
        _set_mix_lower_only(gen)
        obs, _ = env.reset(seed=seed + ep)
        std_trace = []
        term = trunc = False
        info: dict = {}
        for _t in range(n_steps):
            obs_in = obs[:n_model]
            obs_t, _ = model.policy.obs_to_tensor(
                np.asarray(obs_in, dtype=np.float32)[None, :])
            with th.no_grad():
                mean_actions, log_std, _kw = actor.get_action_dist_params(
                    obs_t)
                std = th.exp(log_std).mean().item()
            std_trace.append(std)
            a, _ = model.predict(obs_in, deterministic=True)
            obs, _rw, term, trunc, info = env.step(a)
            if term or trunc:
                break
        h_err_mm = round(1000.0 * (
            float(env.data.xpos[env._chassis_bid, 2])
            - (env._z0 + env._h_target)), 1)
        passed = (not term) and abs(h_err_mm) <= 15.0
        std_arr = np.asarray(std_trace)
        n_got = std_arr.shape[0]
        descent = std_arr[min(descent_lo, n_got):min(descent_hi, n_got)]
        terminal = std_arr[max(0, n_got - term_n):n_got]
        per_ep.append({
            "ep": ep, "passed": bool(passed),
            "height_err_end_mm": h_err_mm,
            "term_reason": (str(info.get("termination_reason"))
                            if term else None),
            "n_ticks": int(n_got),
            "descent_std_mean": (float(descent.mean())
                                 if descent.size else None),
            "terminal_hold_std_mean": (float(terminal.mean())
                                       if terminal.size else None),
        })

    def _avg(key, cond):
        vals = [r[key] for r in per_ep if cond(r) and r[key] is not None]
        return (float(np.mean(vals)) if vals else None, len(vals))

    summary = {
        "checkpoint": str(checkpoint),
        "episodes": episodes,
        "n_pass": sum(1 for r in per_ep if r["passed"]),
        "descent_std_pass": _avg("descent_std_mean", lambda r: r["passed"]),
        "descent_std_fail": _avg("descent_std_mean",
                                 lambda r: not r["passed"]),
        "terminal_hold_std_pass": _avg("terminal_hold_std_mean",
                                      lambda r: r["passed"]),
        "terminal_hold_std_fail": _avg("terminal_hold_std_mean",
                                      lambda r: not r["passed"]),
        "per_episode": per_ep,
    }
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", default=str(DEFAULT_CKPT))
    ap.add_argument("--episodes", type=int, default=18)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    summary = run(args.checkpoint, args.episodes, args.seed,
                  args.episode_seconds)
    print(json.dumps({k: v for k, v in summary.items()
                      if k != "per_episode"}, indent=2))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, indent=2))
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
