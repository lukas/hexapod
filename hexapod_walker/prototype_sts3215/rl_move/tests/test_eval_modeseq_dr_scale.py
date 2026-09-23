"""eval_modeseq.py's --dr-scale passthrough (RESEARCH_RULES "Tests":
fast, mechanics-only, no rollout-ranking).

Root cause this exists: this harness's `make_env()` hardcoded
`randomize=False`, so the Stage-2 single-arc milestone's own gate text
("DR-0 AND own-DR") could only ever be half-checked -- there was no
way to run the composed rise/walk/lower session at the walk
champion's trained DR ceiling through this tool. Found 09-23
immediately after fixing the --episode-seconds truncation bug and
running the milestone for the first time at DR-0 only.

This test locks only the resolver function (no checkpoints/MuJoCo):
default 0.0 keeps `randomize=False` bit-exact; any positive value
turns randomization on, matching every other eval harness's own
`randomize=dr_scale>0` convention.
"""
from __future__ import annotations

from rl_move.sim.eval_modeseq import resolve_randomize


def test_default_zero_keeps_randomize_off():
    assert resolve_randomize(0.0) is False


def test_positive_dr_scale_turns_randomize_on():
    assert resolve_randomize(1.0) is True
    assert resolve_randomize(0.7) is True
    assert resolve_randomize(0.05) is True


def test_negative_dr_scale_stays_off():
    # argparse never rejects a negative float; keep the same "> 0"
    # semantics every other harness in the repo uses rather than
    # silently accepting a nonsensical negative scale as "on".
    assert resolve_randomize(-1.0) is False
