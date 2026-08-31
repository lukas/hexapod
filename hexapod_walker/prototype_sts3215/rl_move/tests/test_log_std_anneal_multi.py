"""Unit tests for _parse_log_std_anneal_specs (08-31, standwalk
dualbc5-turncap mechanism search): comma-list support on
--log-std-final/--log-std-anneal-core/--log-std-anneal-frac so ONE
launch can anneal the walk core's log_std UP (a guaranteed-to-move
exploration lever, the "worth noting" follow-up from the entboost
CANARY FAIL verdict, 08-31 ~07:0x STATUS update) while independently
still cooling the stance core DOWN toward -4.0 — every prior canary in
this lineage could only target ONE core per launch. Pure-function
tests only (mirrors test_gru_dual_log_std_split_cli.py's pattern);
mujoco/GPU-free.
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
)


def test_none_is_off():
    assert _parse_log_std_anneal_specs(None, "all", "1.0") == []


def test_single_value_is_bit_exact_one_triple():
    """The pre-08-31 single-value CLI form (every already-launched
    recipe) must still produce exactly the one triple it always did."""
    assert _parse_log_std_anneal_specs("-4.0", "stance", "0.5") == [
        ("stance", -4.0, 0.5)]


def test_single_value_default_frac():
    assert _parse_log_std_anneal_specs("-3", "all", "1.0") == [
        ("all", -3.0, 1.0)]


def test_multi_pair_walk_and_stance():
    out = _parse_log_std_anneal_specs(
        "-0.7,-4.0", "walk,stance", "0.1,0.5")
    assert out == [("walk", -0.7, 0.1), ("stance", -4.0, 0.5)]


def test_frac_broadcasts_across_multi_pairs():
    out = _parse_log_std_anneal_specs("-0.7,-4.0", "walk,stance", "0.25")
    assert out == [("walk", -0.7, 0.25), ("stance", -4.0, 0.25)]


def test_core_cannot_broadcast_across_multi_finals():
    """A single core with >1 final is ambiguous (which final does the
    lone core get?) — broadcasting it produces two identical cores,
    caught by the duplicate-core refusal rather than silently picking
    one final for the shared core."""
    with pytest.raises(SystemExit, match="[Dd]uplicate"):
        _parse_log_std_anneal_specs("-0.7,-4.0", "walk", "0.1,0.5")


def test_all_combined_with_another_core_refused():
    with pytest.raises(SystemExit, match="'all' cannot be combined"):
        _parse_log_std_anneal_specs("-0.7,-4.0", "all,stance", "0.1,0.5")


def test_duplicate_core_refused():
    with pytest.raises(SystemExit, match="[Dd]uplicate"):
        _parse_log_std_anneal_specs("-0.7,-4.0", "walk,walk", "0.1,0.5")


def test_unknown_core_refused():
    with pytest.raises(SystemExit, match="unknown core"):
        _parse_log_std_anneal_specs("-4.0", "torso", "1.0")


def test_length_mismatch_refused():
    with pytest.raises(SystemExit, match="mismatch"):
        _parse_log_std_anneal_specs("-0.7,-4.0,-1.0", "walk,stance", "1.0")


def test_help_text_still_wires_all_three_flags():
    out = subprocess.run(
        [sys.executable, "-m", "rl_move.sim.train_ppo_mjx", "--help"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=60,
    )
    assert out.returncode == 0, out.stderr
    for flag in ("--log-std-final", "--log-std-anneal-core",
                 "--log-std-anneal-frac"):
        assert flag in out.stdout


from rl_move.sim.train_ppo_mjx import _fixup_log_std_final_argv  # noqa: E402


def test_fixup_merges_comma_list_negative_value():
    """The exact crash from the stdwalk-mild launch (08-31): a bare
    two-token '--log-std-final -0.8,-4.0' argv (what launch_run.py's
    --arg harness always emits) must become one '=' token so
    argparse's negative-number heuristic never sees it as a stray
    option string."""
    out = _fixup_log_std_final_argv(
        ["--log-std-final", "-0.8,-4.0", "--foo", "bar"])
    assert out == ["--log-std-final=-0.8,-4.0", "--foo", "bar"]


def test_fixup_leaves_bare_negative_number_untouched():
    """A single negative value already parses fine (argparse's own
    negative-number regex matches it) — merging it is harmless but
    unnecessary; confirm the transform still applies it consistently
    (single code path, no special-casing 'already fine' values)."""
    out = _fixup_log_std_final_argv(["--log-std-final", "-4.0"])
    assert out == ["--log-std-final=-4.0"]


def test_fixup_leaves_missing_value_untouched():
    """A dangling --log-std-final with nothing after it (or another
    flag right after, e.g. a bare store_true flag) is not this
    function's problem — argparse's own error path handles it."""
    assert _fixup_log_std_final_argv(["--log-std-final"]) == [
        "--log-std-final"]
    assert _fixup_log_std_final_argv(["--log-std-final", "--gru-dual"]) == [
        "--log-std-final", "--gru-dual"]


def test_fixup_leaves_unrelated_flags_untouched():
    out = _fixup_log_std_final_argv(["--ent-coef", "-0.5", "--steps", "10"])
    assert out == ["--ent-coef", "-0.5", "--steps", "10"]


def test_fixup_is_idempotent_on_already_merged_form():
    out = _fixup_log_std_final_argv(["--log-std-final=-0.8,-4.0"])
    assert out == ["--log-std-final=-0.8,-4.0"]
