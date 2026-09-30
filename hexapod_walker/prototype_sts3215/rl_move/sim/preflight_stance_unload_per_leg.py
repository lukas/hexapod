"""preflight_stance_unload_per_leg.py -- zero-training scripted-teacher
check for standwalk Next item 1(b) (2026-09-30).

WHY: item 1(a) built `train.bc_anchor_teacher_stance_unload_frac_per_leg_
dose` (per-leg draw-conditioned generalization of the existing scalar
`stance_unload_frac` stance-tail-deceleration knob -- see
`sim_env.py::_stance_unload_frac_per_leg_from_draw`'s docstring for the
full derivation chain back to the 09-30 static-reachability scoping
pass). Per the design order there ("(b) a CPU-only zero-training
preflight ... to check whether the scripted teacher's OWN measured
foot-force/slip signature on the already-named hard episodes improves
before any RL spend"), this tool must answer that question WITHOUT
spending any GPU/training budget: does dosing the per-leg unload
fraction change the scripted TEACHER's own foot-force/slip signature
on the ceil225 own-cfg draw, for the SAME hard-leg episodes the
difficulty-reject verdict already named (ep1 sacrifices legs [4,5],
ep4 sacrifices leg [2], ep5 sacrifices leg [3] -- see `ops.sh index
story cw-adapt50hz-tfh16-noramp-ceil225-difficultyreject-fromceil20-s0`)?

HOW: reuses `goal.walk_residual_gate=1.0` + `goal.walk_residual_blend=
0.0` -- an EXISTING, already-tested knob (assistfade rung-3 residual-
blend mechanism, `sim_env.py` step()) that at blend=0 makes the
executed action EXACTLY the env's own `_walk_bc_gait` scripted
reference every tick, discarding whatever the "policy" argument
returns. That `_walk_bc_gait` is rebuilt every reset via
`_make_walk_bc_gait()`, which already reads
`train.bc_anchor_teacher_stance_unload_frac_per_leg_dose` and this
episode's OWN drawn `joint_zero_bias_deg`/`link_len_leg_pct` per leg
(item 1(a)'s own mechanism) -- so running this probe at dose=0.0 vs
dose>0.0 is a genuine, physics-real, zero-training A/B on the teacher
alone, through the exact same per-leg draw-conditioning code path a
future RL run would train under.

The rollout/scoring harness is `eval_checkpoint.run_episode` verbatim
(not reimplemented): same `sacrificed_legs`/`gait_valid`/
`slip_per_m_per_leg` fields the ceil225 gate itself reads, on a
`_ZeroModel` whose `.predict()` output is provably irrelevant (fully
overridden by the blend=0 reference) -- eliminates an entire class of
"reimplemented-the-gait-scoring-wrong" bugs.

Usage:
  uv run python -m rl_move.sim.preflight_stance_unload_per_leg \
      --dose 0.0 0.4 --seed 0 --per-mode 24 \
      --out logs/ckpt_eval/preflight_stance_unload_per_leg.json

Diagnostic only: no reward/cfg-default change, no MuJoCo artifact
beyond the JSON report. Run from the repo root (CPU-only, ~1-2 min for
per-mode 24 at two doses).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from rl_move.config import load_config

from .cfg_set import _parse_cfg_set
from .eval_checkpoint import ALL_MODES, run_episode
from .servo_model import SimServoParams
from .walk_task import SimHexapodJointWalkEnv

# The physics/goal/DR-relevant subset of the ceil225 training recipe
# (cw-adapt50hz-tfh16-noramp-ceil225-fromceil20-s0's own --cfg-set
# list -- see `ops.sh entry` for that run). Reward-only keys are
# omitted: the executed action is the scripted teacher reference
# regardless of reward (walk_residual_blend=0.0 below), so they cannot
# affect this probe's slip/force measurement -- only physics
# (env/dr/safety) and WHAT gets commanded (goal.walk_*) matter.
CEIL225_PHYSICS_CFG = [
    "env.model_source=mesh",
    "control.hz=50",
    "safety.max_delta_q_deg=0.75",
    "safety.max_roll_deg=25",
    "safety.max_pitch_deg=25",
    "goal.walk_speed_min_m_s=0.04",
    "goal.walk_speed_max_m_s=0.10",
    "goal.walk_heading_set=[]",
    "goal.walk_heading_max_rad=3.1415927",
    "goal.walk_cmd_resample_s=6.0",
    "goal.walk_stop_frac=0.15",
    "goal.walk_cmd_resample_jitter=0.2",
    "goal.walk_park_start_frac=0.25",
    "dr.placement_noise_deg=0.0",
    "dr.bad_start_prob=0.0",
    "dr.tipped_start_prob=0.0",
    "dr.latency_scale=1.0,1.0",
    "dr.foot_friction_scale=0.7,1.3",
    "dr.foot_stickslip_gain=0.0,0.8",
    "dr.joint_zero_bias_deg=2.25",
    "dr.link_len_leg_pct=0.035",
    "env.dr_stage_ramp_steps=0",
    # Pure-teacher execution: the "policy" action is discarded every
    # tick (see module docstring) -- this is what makes the probe
    # zero-training-relevant (teacher only, no RL actor in the loop).
    "goal.walk_residual_gate=1.0",
    "goal.walk_residual_blend=0.0",
]


class _ZeroModel:
    """Stand-in policy whose output is provably never used.

    `walk_residual_blend=0.0` replaces the executed action with the
    scripted teacher reference unconditionally (see module docstring)
    -- this returns an all-zero action purely to satisfy
    `run_episode`'s `model.predict(obs, deterministic=...)` contract.
    """

    def predict(self, obs, deterministic: bool = True):
        return np.zeros(18, dtype=np.float32), None

    def reset(self) -> None:
        pass


def _build_cfg(dose: float, extra_cfg_set: list[str] | None) -> dict:
    """Merge the ceil225 physics recipe + this probe's per-leg dose +
    any caller overrides onto a fresh default cfg. Pulled out of
    `_build_env` so the override-merge logic is unit-testable without
    building a MuJoCo env (RESEARCH_RULES "Tests": mechanics, not a
    MuJoCo-heavy round trip)."""
    cfg = load_config()
    specs = list(CEIL225_PHYSICS_CFG) + [
        f"train.bc_anchor_teacher_stance_unload_frac_per_leg_dose={dose}",
    ] + list(extra_cfg_set or [])
    for key, parsed in _parse_cfg_set(specs).items():
        node = cfg
        *path, leaf = key.split(".")
        for k in path:
            node = node.setdefault(k, {})
        node[leaf] = parsed
    return cfg


def _build_env(seed: int, episode_seconds: float, dose: float,
               extra_cfg_set: list[str]):
    cfg = _build_cfg(dose, extra_cfg_set)
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg), randomize=True, dr_scale=1.0,
        episode_seconds=episode_seconds, seed=seed, cfg=cfg,
        render_mode=None)
    gen = env._goal_gen
    for m in ALL_MODES:
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env


def _leg_difficulty_fracs(env) -> list[float] | None:
    """Per-leg difficulty in [0, 1], same formula as
    `sim_env.py::_stance_unload_frac_per_leg_from_draw` (link-length-
    span-over-ceiling and zero-bias-over-ceiling, averaged) -- computed
    directly from the just-completed episode's own `_ep_rand`/
    `randomizer.ranges` regardless of the configured dose, so the
    "hardest leg" can be identified even in the dose=0 baseline run
    (where the per-leg override itself is None/inactive). Returns
    None if there is no active DR draw (e.g. dr_scale=0)."""
    ep_rand = getattr(env, "_ep_rand", None)
    randomizer = getattr(env, "randomizer", None)
    if ep_rand is None or randomizer is None:
        return None
    ranges = randomizer.ranges
    link_pct = float(getattr(ranges, "link_len_leg_pct", 0.0))
    bias_deg = float(getattr(ranges, "joint_zero_bias_deg", 0.0))
    link_scale = np.asarray(ep_rand.link_scale, dtype=float)
    zero_bias_rad = np.asarray(ep_rand.joint_zero_bias_rad, dtype=float)
    out = []
    for i in range(6):
        leg_link_dev = float(np.max(np.abs(link_scale[i] - 1.0)))
        link_frac = (leg_link_dev / link_pct) if link_pct > 0 else 0.0
        leg_bias_deg = float(np.max(np.abs(
            zero_bias_rad[3 * i:3 * i + 3]))) * (180.0 / np.pi)
        bias_frac = (leg_bias_deg / bias_deg) if bias_deg > 0 else 0.0
        out.append(float(np.clip(0.5 * (link_frac + bias_frac), 0.0, 1.0)))
    return out


def run_dose(dose: float, *, seed: int, per_mode: int,
             episode_seconds: float, extra_cfg_set: list[str]) -> list[dict]:
    """Run `per_mode` sequential walk episodes at `dose` (this probe's
    own per-leg unload dose), same env/RNG-stream construction order as
    `eval_checkpoint.evaluate` -- episode index k is the k-th `reset()`
    call after fixed construction (seed, cfg), matching how the
    ceil225 gate's own "ep1/ep4/ep5" naming is reproducible. Each ep
    dict is annotated with `hardest_leg`/`hardest_leg_difficulty`/
    `hardest_leg_slip_per_m` (this episode's own DR draw, independent
    of dose -- see `_leg_difficulty_fracs`) so the dose=0 vs dose>0
    comparison can read the SAME named leg's slip on matched draws."""
    env = _build_env(seed, episode_seconds, dose, extra_cfg_set)
    model = _ZeroModel()
    eps = []
    try:
        for _ in range(per_mode):
            ep, _frames = run_episode(
                env, model, deterministic=True, video=False, annotate=None)
            fracs = _leg_difficulty_fracs(env)
            if fracs is not None:
                hardest = int(np.argmax(fracs))
                ep["hardest_leg"] = hardest
                ep["hardest_leg_difficulty"] = round(fracs[hardest], 3)
                spl = ep.get("slip_per_m_per_leg")
                ep["hardest_leg_slip_per_m"] = (
                    spl[hardest] if spl else None)
            eps.append(ep)
    finally:
        env.close()
    return eps


def summarize(eps: list[dict]) -> dict:
    n = len(eps)
    valid = sum(1 for e in eps if e.get("gait_valid"))
    sac_hist: dict[int, int] = {}
    per_leg_slip = np.full((n, 6), np.nan)
    for i, e in enumerate(eps):
        for leg in e.get("sacrificed_legs") or []:
            sac_hist[leg] = sac_hist.get(leg, 0) + 1
        spl = e.get("slip_per_m_per_leg")
        if spl:
            per_leg_slip[i] = spl
    return {
        "n": n,
        "gait_valid": valid,
        "gait_valid_rate": round(valid / n, 3) if n else None,
        "sacrificed_leg_histogram": {str(k): v
                                     for k, v in sorted(sac_hist.items())},
        "n_episodes_with_any_sacrifice": sum(
            1 for e in eps if e.get("sacrificed_legs")),
        "slip_per_m_per_leg_median": [
            round(float(x), 3) for x in
            np.nanmedian(per_leg_slip, axis=0)] if n else None,
        "hardest_leg_slip_per_m_median": (round(float(np.nanmedian([
            e["hardest_leg_slip_per_m"] for e in eps
            if e.get("hardest_leg_slip_per_m") is not None])), 3)
            if any(e.get("hardest_leg_slip_per_m") is not None
                   for e in eps) else None),
        "per_episode": [
            {"idx": i, "sacrificed_legs": e.get("sacrificed_legs"),
             "gait_valid": e.get("gait_valid"),
             "slip_per_m": e.get("slip_per_m"),
             "slip_per_m_per_leg": e.get("slip_per_m_per_leg"),
             "prog_ratio": e.get("progress_ratio"),
             "hardest_leg": e.get("hardest_leg"),
             "hardest_leg_difficulty": e.get("hardest_leg_difficulty"),
             "hardest_leg_slip_per_m": e.get("hardest_leg_slip_per_m")}
            for i, e in enumerate(eps)],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dose", type=float, nargs="+", default=[0.0, 0.4],
                    help="per-leg unload doses to compare (first is the "
                         "baseline, default 0.0=legacy identity)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--per-mode", type=int, default=24)
    ap.add_argument("--episode-seconds", type=float, default=20.0)
    ap.add_argument("--cfg-set", action="append", default=None,
                    help="extra overrides applied on top of the ceil225 "
                         "physics recipe")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    report = {"seed": args.seed, "per_mode": args.per_mode,
              "episode_seconds": args.episode_seconds,
              "doses": {}}
    for dose in args.dose:
        eps = run_dose(dose, seed=args.seed, per_mode=args.per_mode,
                       episode_seconds=args.episode_seconds,
                       extra_cfg_set=args.cfg_set)
        summary = summarize(eps)
        report["doses"][str(dose)] = summary
        print(f"[dose={dose}] gait_valid {summary['gait_valid']}/"
              f"{summary['n']}={summary['gait_valid_rate']} | "
              f"sacrificed-leg episodes "
              f"{summary['n_episodes_with_any_sacrifice']}/{summary['n']} "
              f"hist={summary['sacrificed_leg_histogram']} | "
              f"slip/m per-leg median={summary['slip_per_m_per_leg_median']} | "
              f"hardest-leg slip/m median="
              f"{summary['hardest_leg_slip_per_m_median']}")

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(report, f, indent=2)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
