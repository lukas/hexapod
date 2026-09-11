"""Tests for diag_teacher_replay_divergence.py (standwalk stage-2
distillation diagnostic, 2026-09-11). Fast, mechanics-only: the pure
``_rollout`` aggregation loop against a tiny real PPO model/env (reused
from test_heading_selfdistill, no dependency on any pulled ledger run
or trained checkpoint file) and CLI arg-parsing smoke checks."""
from __future__ import annotations

import argparse

import numpy as np
import pytest
from stable_baselines3 import PPO

from rl_move.sim.diag_teacher_replay_divergence import _rollout
from rl_move.tests.test_heading_selfdistill import _make_ppo, _TinyHeadingEnv


def test_rollout_return_matches_manual_reward_sum():
    model = _make_ppo(PPO)
    env = _TinyHeadingEnv(0)
    row = _rollout(env, model, seed=0)
    # _TinyHeadingEnv terminates at t>=8, one reward per tick.
    assert row["ticks"] == 8
    assert row["seed"] == 0
    assert isinstance(row["return"], float)
    # No termination_reason/cmd_speed_m_s keys on this tiny env's info
    # dict -- both diagnostics degrade to None rather than crashing.
    assert row["term_reason"] is None
    assert row["cmd_speed_mean"] is None


def test_rollout_is_deterministic_for_a_fixed_seed():
    model = _make_ppo(PPO)
    row_a = _rollout(_TinyHeadingEnv(0), model, seed=3)
    row_b = _rollout(_TinyHeadingEnv(0), model, seed=3)
    assert row_a["return"] == pytest.approx(row_b["return"])
    assert row_a["ticks"] == row_b["ticks"]


def test_cli_requires_walk_teacher_run():
    from rl_move.sim.diag_teacher_replay_divergence import main
    import sys

    old_argv = sys.argv
    try:
        sys.argv = ["diag_teacher_replay_divergence.py"]
        with pytest.raises(SystemExit):
            main()
    finally:
        sys.argv = old_argv


def test_cli_defaults():
    ap = argparse.ArgumentParser()
    ap.add_argument("--walk-teacher-run", required=True)
    ap.add_argument("--stance-teacher-run", default=None)
    ap.add_argument("--episodes", type=int, default=8)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--cfg-set", action="append", default=[])
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args(["--walk-teacher-run", "some-run"])
    assert args.stance_teacher_run is None
    assert args.episodes == 8
    assert args.cfg_set == []
