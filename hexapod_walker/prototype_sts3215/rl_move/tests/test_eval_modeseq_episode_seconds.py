"""eval_modeseq.py's --episode-seconds resolver (RESEARCH_RULES
"Tests": fast, mechanics-only, no rollout-ranking).

Root cause this exists: the two-specialist/single-model driving loop
creates its env with a HARDCODED `episode_seconds=20.0`, silently
truncating any grammar + --drive-random --drive-seconds combination
whose real total duration exceeds 20s -- the segment that gets cut
is marked FAIL with `fall="episode_end"`, indistinguishable from a
genuine behavioral failure unless you already suspect the cap. Found
09-23 trying to run the track's actual required Stage-2 milestone (a
60s randomized-joystick walk segment) through this tool for the first
time: rise succeeded, but every walk segment was chopped at ~20s and
marked FAIL even though gait_valid was true throughout.

This test locks only the resolver function (no checkpoints/MuJoCo):
default None keeps the legacy 20.0s bit-exact; an explicit value
overrides it verbatim.
"""
from __future__ import annotations

from rl_move.sim.eval_modeseq import resolve_episode_seconds


def test_default_is_legacy_20s():
    assert resolve_episode_seconds(None) == 20.0


def test_explicit_override_applied():
    assert resolve_episode_seconds(90.0) == 90.0
    assert resolve_episode_seconds(5.0) == 5.0
