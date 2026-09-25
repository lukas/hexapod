"""eval_modeseq.py's --grammar resolver (RESEARCH_RULES "Tests": fast,
mechanics-only, no rollout-ranking).

Standwalk 2026-09-25 (riseexperts-acq1 composed-session Next item):
the parser only accepted rise/walk/lower tokens, so a full composed
rise+hold+lower+walk unified-session candidate couldn't even be
expressed as a --grammar string. This locks the now-factored-out
`parse_grammar()` (no checkpoints/MuJoCo needed): `hold` is a valid
non-first token (a stance segment exactly like `lower`, re-anchoring
from wherever the previous segment left the robot), legacy grammars
are unaffected, and the existing start/unknown-token validation still
raises `SystemExit`.
"""
from __future__ import annotations

import pytest

from rl_move.sim.eval_modeseq import parse_grammar


def test_legacy_grammar_unaffected():
    assert parse_grammar("rise,walk,lower,rise,walk") == [
        "rise", "walk", "lower", "rise", "walk"]


def test_hold_accepted_mid_sequence():
    assert parse_grammar("rise,hold,walk,lower") == [
        "rise", "hold", "walk", "lower"]


def test_hold_accepted_immediately_after_rise():
    assert parse_grammar("rise,hold") == ["rise", "hold"]


def test_hold_accepted_after_lower_start():
    assert parse_grammar("lower,hold") == ["lower", "hold"]


def test_whitespace_and_blank_tokens_ignored():
    assert parse_grammar(" rise , hold ,, walk ") == [
        "rise", "hold", "walk"]


def test_hold_rejected_as_first_token():
    with pytest.raises(SystemExit):
        parse_grammar("hold,walk,lower")


def test_walk_still_rejected_as_first_token():
    with pytest.raises(SystemExit):
        parse_grammar("walk,lower")


def test_unknown_token_rejected():
    with pytest.raises(SystemExit):
        parse_grammar("rise,jump,lower")


def test_empty_grammar_rejected():
    with pytest.raises(SystemExit):
        parse_grammar("  ,  ,")
