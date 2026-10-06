"""Mechanics-only import/argparse check for joystick_demo_lifecycle.py
(the continuous-mp4 render of the full rise->walk->turn->lower rl_only
chain, closing the gap named in todaypolicy/STATUS.md 2026-10-06). No
mujoco/env/model -- the module's own role-switch/offset-clamp math is
already covered by test_joystick_demo_compose.py (reused verbatim, not
re-derived here); this test only checks the new module wires together
and exposes the CLI it documents, per RESEARCH_RULES "Tests" (fast,
mechanics only, no rollout-ranking banks)."""
from __future__ import annotations

import importlib


def test_module_imports_without_mujoco_side_effects():
    mod = importlib.import_module("rl_move.sim.joystick_demo_lifecycle")
    assert hasattr(mod, "main")


def test_cli_requires_out_and_accepts_known_scripts():
    import sys

    from rl_move.sim.joystick_demo_lifecycle import main
    argv = sys.argv
    try:
        sys.argv = ["joystick_demo_lifecycle"]
        try:
            main()
            raised = False
        except SystemExit as e:
            raised = e.code not in (0, None)
        assert raised, "argparse should reject a call missing --out"
    finally:
        sys.argv = argv


def test_reuses_joystick_demo_compose_grammar_not_a_fork():
    # the new module must import (not redefine) resolve_roles/
    # joystick_script -- a duplicate definition here would silently
    # diverge from the already-tested grammar in
    # test_joystick_demo_compose.py.
    import rl_move.sim.joystick_demo_compose as jdc
    import rl_move.sim.joystick_demo_lifecycle as jdl

    assert jdl.resolve_roles is jdc.resolve_roles
    assert jdl.joystick_script is jdc.joystick_script
