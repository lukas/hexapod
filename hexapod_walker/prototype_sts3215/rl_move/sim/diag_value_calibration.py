"""diag_value_calibration.py — does the critic already "expect" the
leg-sacrifice outcome at the chronic off-axis headings?

WHY (walkcurr off-axis-heading front-leg (0/5) sacrifice, 2026-09-09):
six independent repair mechanisms across the whole exposure/batch-
composition axis (heading-exposure reweight, heading-gain dose-
scaling, wide-log_std exploration hold, advantage-filtered self-
distillation, 100%-isolation curriculum) AND the one named PPO-loss-
level lever (per-heading advantage normalization) have ALL failed to
move the deterministic mean off the chronic sacrifice at headings
+-90/+-135/180 (see rl_docs/tracks/walkcurr/STATUS.md, CURRENT_TRUTHS
2026-09-09 ~20:3x/~21:3x). The isolation-curriculum result is the
sharpest clue: training on ONLY the broken headings for the WHOLE 2M
steps (zero competing forward data) still leaves the deterministic
mean byte-identical to the frozen parent, even though the training
reward itself visibly moves (falls) — i.e. real gradient signal flows
through *something*, but never the policy mean for these legs. A
PPO policy-gradient update only moves the mean in a direction where
sampled actions have non-trivial (nonzero, correctly-signed) ADVANTAGE
= return_to_go - V(s). If the critic already predicts a return at
these particular states that matches what the sacrifice behavior
achieves (i.e. V(s) tracks the entrenched habit's own return, not the
achievable-but-rare better outcome), gradient-based policy improvement
stalls even with unlimited on-distribution data -- a value-
miscalibration / vanishing-advantage local optimum, not an exploration,
pricing, or batch-composition problem. This is a NEW, previously-
untested class of explanation (none of the six closed mechanisms
touched the critic's own calibration) and is cheap to check directly:
replay a real rollout and diff V(s) against the REALIZED discounted
return at the same tick, at a broken heading vs a healthy one, on the
frozen champion.

THIS IS A DIAGNOSTIC ONLY: zero training spend, no shared-code edits,
CPU harness pod. It does not launch anything or change any default.
The result decides whether "recalibrate/reset the critic on the rare
states before the next policy update" is worth designing as the 7th
mechanism, or whether the value function is already well-calibrated
(pointing back at something else entirely, e.g. multi-step temporal
commitment rather than a single-tick advantage problem).

UPDATE 2026-09-09 (this entry): the original per-heading pinned mode
below (Reads 1/2 in rl_docs/tracks/walkcurr/STATUS.md) was found
INCONCLUSIVE — holding one heading fixed for a full 20s episode
(``pinned_heading_cfg``'s ``walk_cmd_resample_s=0.0``) is itself OOD
relative to training, which resamples the commanded heading every 6s
even within this exact recipe's own 20s training episodes
(``goal.walk_cmd_resample_s=6.0`` in every widen8/crutchoff launch
command). The V-G residual exploded and flipped sign between a 5s and
a 20s full pin, tracking the pin duration, not a clean calibration
signal. ``--natural-resample`` (added this entry) fixes exactly that:
it runs the SAME matched cfg-set with NO heading override at all (the
recipe's own ``goal.walk_heading_set``/``walk_cmd_resample_s=6.0``
apply unchanged, so the heading naturally resamples mid-episode just
like training), and buckets EVERY tick post-hoc by the CURRENT
commanded heading read directly off the observation (``heading_cos``,
the same on/off-axis classifier ``heading_adv_norm``/
``heading_selfdistill`` already use, same default ``cos_max=0.5``)
instead of by which heading was requested at reset. This is the
"resample-matched" fix named as option (a) in the previous entry's
STATUS.md writeup (option (b), instrumenting the actual training
rollout buffer's own GAE, is a larger change and was not attempted
here).

Method: build the exact matched env/cfg-set stack a pinned-heading-
panel run uses (reuses train_ppo_sim._parse_cfg_set + eval_checkpoint's
own ENV_CLASSES/pinned_heading_cfg -- no reimplementation), load the
checkpoint via gru_policy.load_checkpoint_auto, and manually step
deterministic episodes while recording, PER TICK: the critic's V(s)
prediction (policy.predict_values, called on the observation the
action was actually sampled from) and the realized reward. After each
episode, compute the true discounted return-to-go G_t = sum_{k>=0}
gamma^k * r_{t+k} (using the run's own gamma, default 0.99) and the
residual V(s_t) - G_t. Reports, per heading: n ticks, mean/median
residual, mean |residual|, and a same-scale reference stat from the
episode's own reward magnitude (residual as a fraction of the return
range) so the number isn't dangled unitless. Two or more headings can
be compared in one invocation (typically one broken + h000 as the
healthy control on the SAME checkpoint, so any residual-scale
difference cannot be attributed to a different network).

    uv run python -m rl_move.sim.diag_value_calibration \
        --checkpoint rl_move/sim/policies/ppo_goal_cw_walkscratch_crutchoff_s0_widen8_legdutyratio_swinggap_dose10_plusduty_acq1_cont10m.zip \
        --cfg-set env.model_source=mesh_mjx --cfg-set control.hz=100 ... (same matched stack as ops.sh evalcmd) \
        --headings 0,180,90,-90,135,-135 --episodes 3 --seed 0 \
        --out logs/diag_value_calibration/widen8_s0_cont10m.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from .eval_checkpoint import ENV_CLASSES, heading_label, pinned_heading_cfg
from .heading_selfdistill import heading_cos, heading_frame_width, heading_vref_index
from .servo_model import SimServoParams


def _build_env(task: str, cfg_set: list[str] | None, angle: float | None,
               speed: float | None, seed: int, dr_scale: float,
               episode_seconds: float | None = None, natural: bool = False):
    """``natural=True`` skips the ``pinned_heading_cfg`` override
    entirely (``angle``/``speed`` are ignored): the run's own
    ``--cfg-set goal.walk_heading_set=...``/``walk_cmd_resample_s=...``
    apply unchanged, so the commanded heading resamples mid-episode
    exactly like training instead of being pinned for the whole
    episode."""
    from .train_ppo_sim import _parse_cfg_set
    from rl_move.config import load_config
    cfg = load_config()
    if cfg_set:
        for key, parsed in _parse_cfg_set(cfg_set).items():
            sect, name = key.split(".", 1)
            cfg.setdefault(sect, {})[name] = parsed
    if not natural:
        for name, val in pinned_heading_cfg(angle, speed).items():
            cfg.setdefault("goal", {})[name] = val
    has_dr_ov = bool(cfg.get("dr"))
    env_cls = ENV_CLASSES[task]
    kw = {}
    if episode_seconds is not None:
        kw["episode_seconds"] = episode_seconds
    # Same semantics as eval_checkpoint.py's make_env: randomize fires
    # when --dr-scale > 0 OR a dr.* override is present in --cfg-set
    # (so an overridden field can be probed even at dr_scale=0).
    return env_cls(params=SimServoParams.from_cfg(cfg),
                   randomize=(dr_scale > 0 or has_dr_ov),
                   dr_scale=dr_scale, seed=seed,
                   render_mode=None, cfg=cfg, **kw)


def _episode_trace(env, model, *, deterministic: bool) -> tuple[list, list]:
    """Return (values, rewards) — one entry per control tick."""
    import torch

    obs, _ = env.reset()
    if hasattr(model, "reset"):
        model.reset()
    values, rewards = [], []
    done = False
    while not done:
        obs_t, _ = model.policy.obs_to_tensor(obs)
        with torch.no_grad():
            v = model.policy.predict_values(obs_t)
        values.append(float(v.item()))
        a, _ = model.predict(obs, deterministic=deterministic)
        obs, r, term, trunc, _info = env.step(a)
        rewards.append(float(r))
        done = term or trunc
    return values, rewards


def _resolve_vref_index(model) -> int:
    """Index of ``[vx_ref, vy_ref]`` inside one plain-walk-task obs
    frame for THIS model's live action space, with a loud error
    (never a silently-wrong index) if the obs layout is not the plain
    walk-task frame this diagnostic (like ``heading_selfdistill``/
    ``heading_adv_norm``) assumes."""
    n_act = int(model.action_space.shape[0])
    idx = heading_vref_index(n_act)
    frame_w = heading_frame_width(n_act)
    obs_dim = int(model.observation_space.shape[0])
    if obs_dim != frame_w:
        raise SystemExit(
            "--natural-resample obs-width mismatch: expected "
            f"{frame_w} (n_act={n_act}) got {obs_dim} -- this "
            "checkpoint's obs layout is not the plain walk-task frame "
            "this diagnostic's index math assumes (phase/yaw-cmd/mode/"
            "recover/fault tail or stacked history frames unbuilt)")
    return idx


def _episode_trace_with_cos(env, model, *, deterministic: bool,
                            vref_idx: int) -> tuple[list, list, list]:
    """Like ``_episode_trace`` but also returns, per tick, the cosine
    of the CURRENTLY commanded heading vs. forward (read straight off
    the observation the action was sampled from) — the on/off-axis
    classification the natural-resample mode buckets residuals by."""
    import torch

    obs, _ = env.reset()
    if hasattr(model, "reset"):
        model.reset()
    values, rewards, cos_list = [], [], []
    done = False
    while not done:
        obs_t, _ = model.policy.obs_to_tensor(obs)
        with torch.no_grad():
            v = model.policy.predict_values(obs_t)
        values.append(float(v.item()))
        vref = np.asarray(obs[vref_idx:vref_idx + 2], dtype=np.float64)
        cos_list.append(float(heading_cos(vref[None, :])[0]))
        a, _ = model.predict(obs, deterministic=deterministic)
        obs, r, term, trunc, _info = env.step(a)
        rewards.append(float(r))
        done = term or trunc
    return values, rewards, cos_list


def _returns_to_go(rewards: list[float], gamma: float) -> list[float]:
    out = [0.0] * len(rewards)
    running = 0.0
    for i in range(len(rewards) - 1, -1, -1):
        running = rewards[i] + gamma * running
        out[i] = running
    return out


def _group_stats(residuals: list[float], values: list[float],
                  returns: list[float]) -> dict:
    if not residuals:
        return {"n_ticks": 0}
    res_np = np.asarray(residuals, dtype=np.float64)
    g_np = np.asarray(returns, dtype=np.float64)
    g_range = float(g_np.max() - g_np.min()) if len(g_np) else 0.0
    return {
        "n_ticks": len(residuals),
        "mean_residual": round(float(res_np.mean()), 4),
        "median_residual": round(float(np.median(res_np)), 4),
        "mean_abs_residual": round(float(np.abs(res_np).mean()), 4),
        "residual_frac_of_return_range": (
            round(float(np.abs(res_np).mean()) / g_range, 4)
            if g_range > 1e-9 else None),
        "mean_V": round(float(np.mean(values)), 4),
        "mean_G": round(float(np.mean(g_np)), 4),
    }


def _run_natural_resample(model, args) -> dict:
    vref_idx = _resolve_vref_index(model)
    on_res, off_res = [], []
    on_v, off_v, on_g, off_g = [], [], [], []
    ep_returns = []
    off_axis_ticks_frac = []
    for ep_i in range(args.episodes):
        env = _build_env(args.task, args.cfg_set, None, None,
                          args.seed + ep_i, args.dr_scale,
                          args.episode_seconds, natural=True)
        values, rewards, cos_list = _episode_trace_with_cos(
            env, model, deterministic=not args.stochastic,
            vref_idx=vref_idx)
        env.close()
        g = _returns_to_go(rewards, args.gamma)
        ep_returns.append(round(sum(rewards), 2))
        n_off = 0
        for v, gt, c in zip(values, g, cos_list):
            resid = v - gt
            if c <= args.cos_max:
                off_res.append(resid); off_v.append(v); off_g.append(gt)
                n_off += 1
            else:
                on_res.append(resid); on_v.append(v); on_g.append(gt)
        off_axis_ticks_frac.append(round(n_off / max(1, len(cos_list)), 3))
    report = {
        "checkpoint": str(args.checkpoint), "gamma": args.gamma,
        "episodes": args.episodes, "deterministic": not args.stochastic,
        "mode": "natural_resample", "cos_max": args.cos_max,
        "episode_seconds": args.episode_seconds,
        "off_axis_ticks_frac_per_episode": off_axis_ticks_frac,
        "groups": {
            "on_axis": _group_stats(on_res, on_v, on_g),
            "off_axis": _group_stats(off_res, off_v, off_g),
        },
        "episode_returns": ep_returns,
    }
    for grp in ("on_axis", "off_axis"):
        s = report["groups"][grp]
        if s["n_ticks"]:
            print(f"[diag_value_calibration] natural_resample {grp}: "
                  f"n={s['n_ticks']} mean_residual={s['mean_residual']:+.3f} "
                  f"mean_abs={s['mean_abs_residual']:.3f} "
                  f"mean_V={s['mean_V']:.2f} mean_G={s['mean_G']:.2f}")
        else:
            print(f"[diag_value_calibration] natural_resample {grp}: "
                  "n=0 ticks (never visited this episode set)")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("--task", default="joint_walk")
    ap.add_argument("--cfg-set", action="append", default=None)
    ap.add_argument("--headings", type=str, default=None,
                    help="comma-separated heading angles in DEGREES, "
                         "e.g. 0,180,90,-90,135,-135 (required unless "
                         "--natural-resample)")
    ap.add_argument("--natural-resample", action="store_true",
                    help="do NOT pin the heading: run the matched "
                         "cfg-set's own goal.walk_heading_set/"
                         "walk_cmd_resample_s unchanged (heading "
                         "resamples mid-episode exactly like training) "
                         "and bucket every tick's V-G residual by the "
                         "CURRENT commanded heading read off the obs "
                         "(on-axis vs off-axis, --cos-max threshold) "
                         "instead of by which heading was requested at "
                         "reset. Fixes the full-episode-pin OOD "
                         "artifact found in the per-heading mode "
                         "(rl_docs/tracks/walkcurr/STATUS.md 09-09).")
    ap.add_argument("--cos-max", type=float, default=0.5,
                    help="on/off-axis threshold for --natural-resample, "
                         "matching heading_selfdistill/heading_adv_norm's "
                         "own default")
    ap.add_argument("--speed", type=float, default=0.06)
    ap.add_argument("--dr-scale", type=float, default=0.0,
                    help="matches eval_checkpoint.py's --dr-scale "
                         "(0.0 = clean/DR-0 read, the pinned-heading-"
                         "panel default for this family)")
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--episode-seconds", type=float, default=None,
                    help="default: the env class's own default (short); "
                         "pass 20.0 to match this campaign's standard "
                         "pinned-heading-panel/gate episode length")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--gamma", type=float, default=0.99)
    ap.add_argument("--stochastic", action="store_true",
                    help="sample actions instead of deterministic mean "
                         "(off by default: this diagnostic targets the "
                         "deterministic-mean stall specifically)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if not args.natural_resample and not args.headings:
        ap.error("--headings is required unless --natural-resample")

    from .gru_policy import load_checkpoint_auto
    model = load_checkpoint_auto(args.checkpoint, device="cpu")

    if args.natural_resample:
        report = _run_natural_resample(model, args)
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(report, indent=2))
            print(f"[diag_value_calibration] wrote {args.out}")
        return

    headings = [math.radians(float(x)) for x in args.headings.split(",")]
    report: dict = {"checkpoint": str(args.checkpoint), "gamma": args.gamma,
                     "episodes_per_heading": args.episodes,
                     "deterministic": not args.stochastic, "headings": {}}

    for h in headings:
        label = heading_label(h)
        residuals: list[float] = []
        v_all: list[float] = []
        g_all: list[float] = []
        ep_returns = []
        for ep_i in range(args.episodes):
            env = _build_env(args.task, args.cfg_set, h, args.speed,
                              args.seed + ep_i, args.dr_scale,
                              args.episode_seconds)
            values, rewards = _episode_trace(
                env, model, deterministic=not args.stochastic)
            env.close()
            g = _returns_to_go(rewards, args.gamma)
            for v, gt in zip(values, g):
                residuals.append(v - gt)
            v_all.extend(values)
            g_all.extend(g)
            ep_returns.append(sum(rewards))
        residuals_np = np.asarray(residuals, dtype=np.float64)
        g_np = np.asarray(g_all, dtype=np.float64)
        g_range = float(g_np.max() - g_np.min()) if len(g_np) else 0.0
        report["headings"][label] = {
            "angle_deg": round(math.degrees(h), 1),
            "n_ticks": len(residuals),
            "mean_residual": round(float(residuals_np.mean()), 4),
            "median_residual": round(float(np.median(residuals_np)), 4),
            "mean_abs_residual": round(float(np.abs(residuals_np).mean()), 4),
            "residual_frac_of_return_range": (
                round(float(np.abs(residuals_np).mean()) / g_range, 4)
                if g_range > 1e-9 else None),
            "mean_V": round(float(np.mean(v_all)), 4),
            "mean_G": round(float(np.mean(g_np)), 4),
            "episode_returns": [round(x, 2) for x in ep_returns],
        }
        print(f"[diag_value_calibration] {label}: mean_residual="
              f"{report['headings'][label]['mean_residual']:+.3f}  "
              f"mean_abs={report['headings'][label]['mean_abs_residual']:.3f}  "
              f"mean_V={report['headings'][label]['mean_V']:.2f}  "
              f"mean_G={report['headings'][label]['mean_G']:.2f}")

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2))
        print(f"[diag_value_calibration] wrote {args.out}")


if __name__ == "__main__":
    main()
