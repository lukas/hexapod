"""CLI-level tests for --gru-rise-experts (standwalk rise flat/bridge
precision gap, 2026-09-24 ~21:3x): RiseKindGruActorCriticPolicy is a
warm-start-only architecture (Dual->RiseExperts transplant), so
_validate_gru_rise_experts must refuse every combination that isn't
"a Dual --init-from + obs.mode_onehot=1 + obs.rise_start_kind_gate=1",
mirroring test_gru_triple_cli.py's pattern exactly.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

from rl_move.sim.train_ppo_mjx import _validate_gru_rise_experts

_CKPT = Path("parent.zip")


def test_help_text_wires_flag():
    out = subprocess.run(
        [sys.executable, "-m", "rl_move.sim.train_ppo_mjx", "--help"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=60,
    )
    assert out.returncode == 0, out.stderr
    assert "--gru-rise-experts" in out.stdout


def test_default_off_is_a_noop():
    _validate_gru_rise_experts(
        False, False, False, False, None, False, False, 0.0, 0.0)
    _validate_gru_rise_experts(
        False, True, True, True, _CKPT, True, True, 1.0, 1.0)


def test_exclusive_with_dual_experts_and_triple():
    with pytest.raises(SystemExit, match="exclusive"):
        _validate_gru_rise_experts(
            True, True, False, False, _CKPT, False, False, 1.0, 1.0)
    with pytest.raises(SystemExit, match="exclusive"):
        _validate_gru_rise_experts(
            True, False, True, False, _CKPT, False, False, 1.0, 1.0)
    with pytest.raises(SystemExit, match="exclusive"):
        _validate_gru_rise_experts(
            True, False, False, True, _CKPT, False, False, 1.0, 1.0)


def test_requires_init_from():
    with pytest.raises(SystemExit, match="--init-from"):
        _validate_gru_rise_experts(
            True, False, False, False, None, False, False, 1.0, 1.0)


def test_refuses_actor_only_and_policy_backbone_transplants():
    with pytest.raises(SystemExit, match="dedicated"):
        _validate_gru_rise_experts(
            True, False, False, False, _CKPT, True, False, 1.0, 1.0)
    with pytest.raises(SystemExit, match="dedicated"):
        _validate_gru_rise_experts(
            True, False, False, False, _CKPT, False, True, 1.0, 1.0)


def test_requires_mode_onehot():
    with pytest.raises(SystemExit, match="obs.mode_onehot=1"):
        _validate_gru_rise_experts(
            True, False, False, False, _CKPT, False, False, 0.0, 1.0)


def test_requires_rise_start_kind_gate():
    with pytest.raises(SystemExit, match="obs.rise_start_kind_gate=1"):
        _validate_gru_rise_experts(
            True, False, False, False, _CKPT, False, False, 1.0, 0.0)


def test_fully_specified_call_is_allowed():
    _validate_gru_rise_experts(
        True, False, False, False, _CKPT, False, False, 1.0, 1.0)
