"""CLI-level tests for --gru-triple / --log-std-anneal-core turn
(standwalk item-2 escalation, 09-04): TripleGruActorCriticPolicy is a
warm-start-only architecture (Dual->Triple transplant), so
_validate_gru_triple must refuse every combination that isn't "a Dual
--init-from + obs.mode_onehot=1 + obs.mode_onehot_turn_cmd=1", mirroring
test_gru_dual_log_std_split_cli.py's pattern (pull validation into a
pure function, plus one real --help subprocess run).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control", ROOT / "linux_control" / "urt2_setup"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.sim.train_ppo_mjx import (  # noqa: E402
    _parse_log_std_anneal_specs,
    _validate_gru_triple,
)

_CKPT = Path("parent.zip")


def test_help_text_wires_flag():
    out = subprocess.run(
        [sys.executable, "-m", "rl_move.sim.train_ppo_mjx", "--help"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=60,
    )
    assert out.returncode == 0, out.stderr
    assert "--gru-triple" in out.stdout


def test_default_off_is_a_noop():
    # Bit-exact legacy: gru_triple=False never raises regardless of
    # every other arg's state.
    _validate_gru_triple(False, False, False, None, False, False, 0.0, 0.0)
    _validate_gru_triple(False, True, True, _CKPT, True, True, 1.0, 1.0)


def test_exclusive_with_dual_and_experts():
    with pytest.raises(SystemExit, match="exclusive"):
        _validate_gru_triple(True, True, False, _CKPT, False, False,
                             1.0, 1.0)
    with pytest.raises(SystemExit, match="exclusive"):
        _validate_gru_triple(True, False, True, _CKPT, False, False,
                             1.0, 1.0)


def test_requires_init_from():
    with pytest.raises(SystemExit, match="--init-from"):
        _validate_gru_triple(True, False, False, None, False, False,
                             1.0, 1.0)


def test_refuses_actor_only_and_policy_backbone_transplants():
    with pytest.raises(SystemExit, match="dedicated"):
        _validate_gru_triple(True, False, False, _CKPT, True, False,
                             1.0, 1.0)
    with pytest.raises(SystemExit, match="dedicated"):
        _validate_gru_triple(True, False, False, _CKPT, False, True,
                             1.0, 1.0)


def test_requires_mode_onehot():
    with pytest.raises(SystemExit, match="obs.mode_onehot=1"):
        _validate_gru_triple(True, False, False, _CKPT, False, False,
                             0.0, 1.0)


def test_requires_mode_onehot_turn_cmd():
    with pytest.raises(SystemExit, match="obs.mode_onehot_turn_cmd=1"):
        _validate_gru_triple(True, False, False, _CKPT, False, False,
                             1.0, 0.0)


def test_fully_specified_call_is_allowed():
    _validate_gru_triple(True, False, False, _CKPT, False, False, 1.0, 1.0)


def test_log_std_anneal_core_accepts_turn():
    assert _parse_log_std_anneal_specs("-2.0", "turn", "1.0") == \
        [("turn", -2.0, 1.0)]


def test_log_std_anneal_core_multi_with_turn():
    assert _parse_log_std_anneal_specs(
        "-0.7,-2.0", "walk,turn", "0.5") == \
        [("walk", -0.7, 0.5), ("turn", -2.0, 0.5)]
