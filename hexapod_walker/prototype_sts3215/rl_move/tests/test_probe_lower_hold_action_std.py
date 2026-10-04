"""Mechanics-only smoke test for probe_lower_hold_action_std.py (the
walkcurr lowerrole hold-phase action-std diagnostic, 2026-10-04): env
construction must force a pure `lower`-only goal mix and the
descent/terminal-hold tick windows must line up with the recipe's own
hold_s/ramp_s constants. Per RESEARCH_RULES "Tests" rule 4 this does
NOT load the real (gitignored) SAC checkpoint -- that path is
exercised manually (see the tool's own module docstring for the CLI
invocation), not in the default fast suite.
"""
from __future__ import annotations

import numpy as np

from rl_move.sim.probe_lower_hold_action_std import (
    HOLD_S,
    RAMP_S,
    TERMINAL_WINDOW_S,
    _build_env,
    _set_mix_lower_only,
)


def test_set_mix_lower_only_zeroes_every_other_mode():
    from rl_move.sim.cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp import (  # noqa: E501
        CFG_ARGS,
    )

    env = _build_env(CFG_ARGS, episode_seconds=2.0, seed=0)
    gen = env._goal_gen
    _set_mix_lower_only(gen)
    assert gen.p_lower == 1.0
    assert gen.p_walk == 0.0
    assert all(getattr(gen, a) == 0.0 for a in vars(gen)
               if a.startswith("p_") and a != "p_lower")
    # Resetting with this mix must actually sample a `lower` goal.
    env.reset(seed=0)
    assert env._goal_gen is gen


def test_hold_and_ramp_window_ticks_match_recipe_constants():
    from rl_move.sim.cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp import (  # noqa: E501
        CFG_ARGS,
    )

    env = _build_env(CFG_ARGS, episode_seconds=15.0, seed=0)
    dt = env.dt
    hold_n = max(1, int(round(HOLD_S / dt)))
    ramp_n = max(1, int(round(RAMP_S / dt)))
    term_n = max(1, int(round(TERMINAL_WINDOW_S / dt)))
    # Sane, strictly-ordered windows inside a 15 s / dt-tick episode.
    n_steps = int(round(15.0 / dt))
    assert 0 < hold_n < hold_n + ramp_n < n_steps
    assert 0 < term_n < n_steps
    # Recipe leaves goal.lower_hold_s/lower_ramp_s unset -> code defaults
    # (1.0 s / 5.0 s) apply; this pins that assumption so a future
    # recipe edit that overrides either key fails loudly here instead
    # of silently mis-labelling the diagnostic's own windows.
    assert np.isclose(HOLD_S, 1.0)
    assert np.isclose(RAMP_S, 5.0)
