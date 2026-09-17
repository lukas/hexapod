"""Canonical `currentcap29` flat-only rise/hold/lower probe.

Context (walkcurr track, 2026-09-17): a triage cycle root-causing
`cw-stance50hz-rlonly-currentcap29-s1-acq15m-lowlr`'s degradation
hand-reconstructed the `eval_checkpoint.py` invocation from the
training command and, on the FIRST attempt, omitted
`env.model_source=mesh_mjx` / `control.hz=50`. That silently evaluated
the checkpoint on the wrong physics (100 Hz `mesh` instead of 50 Hz
`mesh_mjx`) and produced a uniform 0/12 rise-flat read across every
snapshot in the run -- indistinguishable, at a glance, from a genuine
mid-training collapse. Only re-deriving the FULL cfg-set list (~50
flags: actuator/goal/reward/safety knobs baked into this recipe, not
just the two "obvious" ones) recovered numbers in the same ballpark as
the run's own archived probe. This module is the fix: the exact cfg
list, versioned in code instead of hand-retyped from a shell history
each time, so a future cycle can't repeat the mistake.

This is a MECHANICS-ONLY helper (arg-list construction + a thin CLI
that shells out to `eval_checkpoint.py`) -- it does not rank rollouts
and carries no reward/behavior opinion. Read the actual
`report.json`/video per RESEARCH_RULES; never trust a bare success
count.

Usage:
    uv run python -m rl_move.sim.probe_currentcap29_flatonly \
        rl_move/sim/policies/<ckpt>.zip --out-prefix <name> [--dr-scale 0.0]

Writes logs/ckpt_eval/<name>_flatonly_det/report.json (det-only pass)
and logs/ckpt_eval/<name>_flatonly_sto/report.json (det+sto pass,
--stochastic), matching the historical two-directory convention this
lineage's saga already reads from.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Verbatim from the `currentcap29` family's training/respec command
# (see `ops.sh entry cw-stance50hz-rlonly-currentcap29-s1-acq15m-lowlr`).
# Order matters for --cfg-set (later duplicate keys win); the two
# rise_flat_frac/rise_partial_frac pairs below are intentional --
# the FIRST pair is the recipe's own base split, the SECOND
# (FLATONLY_OVERRIDE_ARGS) forces the flat-only probe on top of it,
# exactly like every prior hand-run probe in this saga.
BASE_CFG_ARGS: list[str] = [
    "env.model_source=mesh_mjx",
    "control.hz=50",
    "safety.max_delta_q_deg=0.75",
    "actions.max_height_mm=88",
    "goal.rise_height_mm=[79,87]",
    "goal.rise_ramp_s=6.0",
    "goal.rise_hold_min_s=0.5",
    "reward.rise_score_income=1.0",
    "reward.rise_score_strip_pen=1.0",
    "reward.rise_posture_gate=1.0",
    "reward.rise_income_prog_gate=1.0",
    "reward.rise_finish_gate_signed=1.0",
    "reward.hold_still_gate=1.0",
    "reward.hold_flag_fade=1.0",
    "reward.k_current_hot=1.0",
    "reward.current_hot_a=2.0",
    "reward.term_cost_per_remaining_s=3.0",
    "reward.term_cost_max=60.0",
    "reward.hold_feet_load=1.0",
    "reward.hold_feet_load_min=1.0",
    "safety.hold_max_height_drop_mm=15",
    "safety.hold_height_grace_s=0.5",
    "safety.hold_min_load_terminate_s=1.0",
    "safety.hold_min_load_terminate_n=0.3",
    "safety.hold_min_load_terminate_grace_s=1.0",
    "safety.hold_grace_curriculum=1",
    "safety.hold_grace_start_drop_mm=40",
    "safety.hold_grace_start_grace_s=1.0",
    "goal.joint_action_bias_hip_deg=30.9",
    "goal.joint_action_bias_knee_deg=36.1",
    "goal.rise_partial_frac=0.5",
    "goal.rise_flat_frac=0.5",
    "reward.rise_score_income_curl_gate=0",
    "goal.rise_curl_gate=1",
    "reward.rise_curl_pretrain=0",
    "goal.rise_curl_gate_max_extra_s=30.0",
    "reward.k_current_pretuck=0.0",
    "reward.current_pretuck_hot_a=0.3",
    "reward.current_pretuck_curl_mm=40.0",
    "reward.k_rise_decouple=0.0",
    "reward.rise_decouple_curl_mm=40.0",
    "actions.rise_height_curl_gate=0",
    "actions.rise_height_curl_gate_frac=1.0",
    "actions.rise_height_curl_gate_floor=0.05",
    "safety.rise_curl_slew_gate=0",
    "safety.rise_curl_slew_gate_frac=1.0",
    "safety.rise_curl_slew_gate_floor=0.35",
    "goal.rise_start_ramp_steps=0",
    "goal.rise_start_flat_frac_start=0.0",
    "goal.rise_start_partial_frac_start=0.6",
    "ik.rise_leg_stagger_gate=0",
    "ik.rise_leg_stagger_threshold=0.5",
    "obs.current_sense=0",
    "obs.current_scale=0.0",
    "reward.k_current_rate=0",
    "reward.current_rate_a_per_s=0",
    "safety.max_current_a=2.9",
]

# Forces the flat-only probe on top of BASE_CFG_ARGS (must come after
# it in the final --cfg-set list so these win).
FLATONLY_OVERRIDE_ARGS: list[str] = [
    "goal.rise_flat_frac=1.0",
    "goal.rise_partial_frac=0",
]


def build_cfg_args() -> list[str]:
    """Full ordered --cfg-set VALUE list for the flat-only probe."""
    return list(BASE_CFG_ARGS) + list(FLATONLY_OVERRIDE_ARGS)


def build_argv(checkpoint: str, *, out: str, dr_scale: float = 0.0,
                stochastic: bool = False, seed: int = 0,
                modes: tuple[str, ...] = ("hold", "rise", "lower"),
                per_mode: int = 6) -> list[str]:
    argv = [
        checkpoint,
        "--task", "joint_goal",
        "--modes", *modes,
        "--per-mode", str(per_mode),
        "--dr-scale", str(dr_scale),
        "--seed", str(seed),
        "--no-video",
        "--out", out,
    ]
    for kv in build_cfg_args():
        argv += ["--cfg-set", kv]
    if stochastic:
        argv.append("--stochastic")
    return argv


def run_probe(checkpoint: str, out_prefix: str, *, dr_scale: float = 0.0,
              seed: int = 0) -> None:
    """Run the det-only pass then the det+sto pass, historical
    two-directory convention (`<out_prefix>_flatonly_{det,sto}`)."""
    for tag, stochastic in (("det", False), ("sto", True)):
        out_dir = f"logs/ckpt_eval/{out_prefix}_flatonly_{tag}"
        argv = build_argv(checkpoint, out=out_dir, dr_scale=dr_scale,
                           seed=seed, stochastic=stochastic)
        cmd = [sys.executable, "-m", "rl_move.sim.eval_checkpoint", *argv]
        print(f"[probe_currentcap29_flatonly] running {tag} pass -> {out_dir}",
              file=sys.stderr)
        subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("checkpoint")
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--dr-scale", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    run_probe(args.checkpoint, args.out_prefix, dr_scale=args.dr_scale,
              seed=args.seed)


if __name__ == "__main__":
    main()
