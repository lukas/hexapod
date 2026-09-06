"""Tests for `--defer-final-artifacts` (fb_20260906T032210_129bed item 1
implementation handoff, 09-06): additive-only instrumentation that
persists `<checkpoint>.training_complete.json` the instant
`model.learn()` returns, before the background eval/video drain that
otherwise holds the GPU-owning trainer idle for minutes doing CPU-only
work. Default OFF, no behavior change when unset; this is NOT itself a
capacity fix (the trainer still calls `bg.shutdown()` and waits) — see
the docstring on `_write_training_complete_marker` and
OPERATOR_QUESTIONS.md for the remaining steps.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from rl_move.sim.train_ppo_mjx import (  # noqa: E402
    _json_safe_config,
    _write_training_complete_marker,
)


def test_help_text_wires_flag():
    out = subprocess.run(
        [sys.executable, "-m", "rl_move.sim.train_ppo_mjx", "--help"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=60,
    )
    assert out.returncode == 0, out.stderr
    assert "--defer-final-artifacts" in out.stdout


def test_marker_written_atomically_with_expected_fields(tmp_path):
    ckpt = tmp_path / "ppo_goal_cw_test.zip"
    ckpt.write_bytes(b"fake checkpoint bytes")

    marker_path = _write_training_complete_marker(
        ckpt, steps=1_234_567, run_name="cw-test-run", task="joint_walk",
        run_id="abcd1234", resolved_config={"seed": 1, "steps": 1234567})

    assert marker_path == ckpt.parent / "ppo_goal_cw_test.training_complete.json"
    assert marker_path.exists()
    # no leftover tmp file (rename, not copy)
    assert not (marker_path.parent / (marker_path.name + ".tmp")).exists()

    payload = json.loads(marker_path.read_text())
    assert payload["run_name"] == "cw-test-run"
    assert payload["task"] == "joint_walk"
    assert payload["steps"] == 1_234_567
    assert payload["checkpoint_path"] == str(ckpt)
    assert payload["wandb_run_id"] == "abcd1234"
    assert payload["resolved_config"] == {"seed": 1, "steps": 1234567}
    # md5 of the exact bytes just written
    import hashlib
    assert payload["checkpoint_md5"] == hashlib.md5(
        ckpt.read_bytes()).hexdigest()


def test_marker_handles_missing_checkpoint_gracefully(tmp_path):
    ckpt = tmp_path / "not_yet_saved.zip"
    marker_path = _write_training_complete_marker(
        ckpt, steps=100, run_name="r", task="t", run_id=None,
        resolved_config={})
    payload = json.loads(marker_path.read_text())
    assert payload["checkpoint_md5"] is None
    assert payload["wandb_run_id"] is None


def test_json_safe_config_stringifies_non_primitives():
    ns = argparse.Namespace(
        seed=1, steps=2_000_000, run_name="r", flag=True, missing=None,
        cfg_set=["a=1", "b=2"], weird_path=Path("/tmp/x"))
    out = _json_safe_config(ns)
    assert out["seed"] == 1
    assert out["steps"] == 2_000_000
    assert out["flag"] is True
    assert out["missing"] is None
    assert out["cfg_set"] == ["a=1", "b=2"]
    assert out["weird_path"] == str(Path("/tmp/x"))
    # must round-trip through json.dumps with no surprises
    json.dumps(out)
