"""``drive_video.py --rot60`` CLI wiring (2026-09-14, walkcurr design-note
follow-up): the interactive ``ops.sh drivevideo`` demo path gets the
same rot60 exact-symmetry wrap ``eval_checkpoint.py --rot60`` already
validated offline (Canary A), so a --script human/sweep/turn capture
at an off-axis heading shows real full-direction walking instead of
the closed off-axis LEGPARK-SKATE fingerprint.

Fast/mechanics-only (RESEARCH_RULES "Tests"): argparse registration
only, no checkpoint load, no rollout, no artifacts -- same minimal
style as ``test_eval_checkpoint_compose_turn_flag.py``'s own
``test_flag_registered_default_none``.
"""
from __future__ import annotations

import sys

import pytest


def test_flag_registered_default_off(capsys):
    from rl_move.sim import drive_video

    old_argv = sys.argv
    sys.argv = ["drive_video", "--help"]
    try:
        with pytest.raises(SystemExit):
            drive_video.main()
    finally:
        sys.argv = old_argv
    out = capsys.readouterr().out
    assert "--rot60" in out
    assert "--compose-turn-blend-s" in out  # unaffected sibling flag


def test_rot60_does_not_require_a_value(tmp_path):
    """``store_true`` -- bare ``--rot60`` parses without an argument,
    same contract as ``eval_checkpoint.py``'s flag."""
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--rot60", action="store_true")
    ns = ap.parse_args(["--rot60"])
    assert ns.rot60 is True
    ns2 = ap.parse_args([])
    assert ns2.rot60 is False
