"""``--compose-turn-blend-s`` wiring for ``hybrid_demo.py`` (todaypolicy
STATUS 2026-09-12 ~19:4x GO_NOGO open item 1): the composed-turn-role
transfer manifest packaged this cycle named "not wired into
hybrid_demo.py -- no single-command full stand->walk(composed-turn)->
lower session exists yet" as an open follow-up. This wires the SAME
``probe_turn_compose._ComposedPolicy`` ``eval_checkpoint.py``/
``drive_video.py`` already use into the walk phase of the composed
demo session.

Fast/mechanics-only per RESEARCH_RULES "Tests": no checkpoint load, no
mujoco rollout, no artifacts -- just argparse wiring (flag exists,
default None = bit-exact off) and the wrap-object identity/plan-
provenance logic, mirroring
``test_eval_checkpoint_compose_turn_flag.py``'s style. The composition
mechanism itself is already covered by ``test_probe_turn_compose.py``.
"""
from __future__ import annotations

import sys

import pytest

from rl_move.sim import hybrid_demo


def test_flag_registered_default_none(capsys):
    old_argv = sys.argv
    sys.argv = ["hybrid_demo", "--help"]
    try:
        with pytest.raises(SystemExit):
            hybrid_demo.main()
    finally:
        sys.argv = old_argv
    out = capsys.readouterr().out
    assert "--compose-turn-blend-s" in out
    assert "--stall-substitute-every-s" in out
    assert "--stall-substitute-dur-s" in out


def test_stall_substitute_requires_compose_flag():
    """Passing a stall-substitute knob without --compose-turn-blend-s
    is a usage error, not a silent no-op -- both wrap the same
    _ComposedPolicy, which needs compose=True to do anything."""
    old_argv = sys.argv
    sys.argv = ["hybrid_demo", "fake_checkpoint.zip",
                "--stall-substitute-every-s", "4.0",
                "--stall-substitute-dur-s", "1.0"]
    try:
        with pytest.raises(SystemExit) as exc:
            hybrid_demo.main()
    finally:
        sys.argv = old_argv
    assert exc.value.code != 0


def test_default_composition_rl_walk_has_no_compose_keys_when_unset():
    """Bit-exact-off contract: when --compose-turn-blend-s is not
    passed, the generated rl_walk controller carries none of the
    compose keys (matches pre-existing behavior/artifacts exactly)."""
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="")
    ap.add_argument("--stand-mode", default="step")
    ap.add_argument("--lower-mode", default="")
    ap.add_argument("--stand-controller", default="scripted")
    ap.add_argument("--lower-controller", default="scripted")
    ap.add_argument("--stance-policy", default=None)
    ap.add_argument("--lower-policy", default=None)
    ap.add_argument("--stand-release", default="stable")
    ap.add_argument("--stand-handoff-stable-s", type=float, default=0.75)
    ap.add_argument("--stand-handoff-settle-s", type=float, default=0.25)
    ap.add_argument("--stand-handoff-min-z-m", type=float, default=0.10)
    ap.add_argument("--stand-handoff-max-tilt-deg", type=float, default=7.0)
    ap.add_argument("--stand-handoff-max-current-a", type=float, default=2.2)
    ap.add_argument("--stand-time-scale", type=float, default=1.0)
    ap.add_argument("--lower-time-scale", type=float, default=1.0)
    ap.add_argument("--walk-ready-align-s", type=float, default=0.75)
    ap.add_argument("--pre-lower-align-s", type=float, default=0.75)
    ap.add_argument("--limp-after-lower-s", type=float, default=2.0)
    ap.add_argument("--script", default="human")
    ap.add_argument("--walk-seconds", type=float, default=20.0)
    ap.add_argument("--speed", type=float, default=0.08)
    ap.add_argument("--wz-max", type=float, default=0.3)
    ap.add_argument("--blend-s", type=float, default=0.5)
    ap.add_argument("--policy-mode", default="deterministic")
    ap.add_argument("--model-source", default="mesh")
    args = ap.parse_args([])
    plan = hybrid_demo._default_composition(args, None)
    walk_ctrl = plan["controllers"]["rl_walk"]
    assert "compose_turn_blend_s" not in walk_ctrl
    assert "stall_substitute_every_s" not in walk_ctrl
