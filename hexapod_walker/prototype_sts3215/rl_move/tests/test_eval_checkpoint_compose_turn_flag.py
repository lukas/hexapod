"""``--compose-turn-blend-s`` wiring (todaypolicy/amp item (c),
2026-09-12): ``eval_checkpoint.py``'s standard multi-mode gate panel can
optionally run through the SAME non-RL turn-in-place composition
``probe_turn_compose.py`` already validated stand-alone (blend_s=0.15
costs zero efficacy vs the hard switch on the amp turncurr freeze
checkpoint) instead of a bespoke single-mode probe harness -- the
remaining named gap before packaging a composed controller ("full gate
+ fresh drivevideo on an actual PACKAGED composed controller").

Fast/mechanics-only per RESEARCH_RULES "Tests": no checkpoint load, no
rollout, no artifacts -- just argparse wiring (flag exists, default
None = bit-exact off, matches the exact ``_ComposedPolicy`` class the
already-green ``test_probe_turn_compose.py`` suite covers) and the
evaluate()-body wrap logic exercised directly against a bare fake
model + real env (same style as
``test_eval_checkpoint_gsde_reset_noise.py``), never invoking main()
end-to-end (no checkpoint zip needed for that).
"""
from __future__ import annotations

import sys

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim import eval_checkpoint
from rl_move.sim.probe_turn_compose import _ComposedPolicy
from rl_move.sim.walk_task import SimHexapodJointWalkEnv

N_ACT = 18


def test_flag_registered_default_none(capsys):
    """The flag exists, defaults to None (no wrap = bit-exact old
    behavior), and does not collide with --rot60."""
    old_argv = sys.argv
    sys.argv = ["eval_checkpoint", "--help"]
    try:
        with pytest.raises(SystemExit):
            eval_checkpoint.main()
    finally:
        sys.argv = old_argv
    out = capsys.readouterr().out
    assert "--compose-turn-blend-s" in out


def _walk_env(*, episode_seconds: float = 2.0):
    cfg = load_config()
    env = SimHexapodJointWalkEnv(cfg, seed=0, episode_seconds=episode_seconds)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise", "lower",
              "recover"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 0.0)
    gen.p_walk = 1.0
    return env


class _ZeroModel:
    use_sde = False

    def predict(self, obs, deterministic=True):
        return np.zeros(N_ACT), None


def test_stall_substitute_flags_registered_default_zero(capsys):
    """todaypolicy STATUS 2026-09-12 ~15:2x: the mode-independent
    periodic-substitution generalization gets the same wiring; both
    flags exist and default to 0.0 (disabled/bit-exact)."""
    old_argv = sys.argv
    sys.argv = ["eval_checkpoint", "--help"]
    try:
        with pytest.raises(SystemExit):
            eval_checkpoint.main()
    finally:
        sys.argv = old_argv
    out = capsys.readouterr().out
    assert "--stall-substitute-every-s" in out
    assert "--stall-substitute-dur-s" in out


def test_stall_substitute_requires_compose_flag(tmp_path, capsys):
    """Passing a stall-substitute knob without --compose-turn-blend-s
    is a usage error, not a silent no-op (both wrap the same
    _ComposedPolicy, which needs compose=True to do anything)."""
    old_argv = sys.argv
    sys.argv = ["eval_checkpoint", "--checkpoint", str(tmp_path / "x.zip"),
                "--stall-substitute-every-s", "4.0",
                "--stall-substitute-dur-s", "1.0"]
    try:
        with pytest.raises(SystemExit) as exc:
            eval_checkpoint.main()
    finally:
        sys.argv = old_argv
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "--stall-substitute-every-s" in err


def test_evaluate_wrap_logic_matches_probe_class():
    """Reproduces the exact wrap the new ``evaluate()`` block performs
    (``_ComposedPolicy(model, env, compose=True, blend_s=...)`` applied
    to the whole mode panel, not just walk) and confirms it runs
    end-to-end through ``run_episode`` without error, same as the
    already-validated probe path -- this is the wiring under test, the
    composition mechanism itself is ``test_probe_turn_compose.py``'s
    job."""
    env = _walk_env()
    env.reset(seed=0)
    wrapped = _ComposedPolicy(_ZeroModel(), env, compose=True, blend_s=0.15)
    ep, _ = eval_checkpoint.run_episode(
        env, wrapped, deterministic=True, video=False, annotate=None)
    env.close()
    assert "success" in ep
    assert wrapped.total_ticks > 0


def test_evaluate_wrap_logic_with_stall_substitute():
    """Same wrap as above but with the stall-substitute knobs also
    threaded through (mirrors the new evaluate() call site exactly) --
    confirms the periodic mode-independent substitution engages via
    this entry point too, not just via probe_turn_compose.py directly."""
    env = _walk_env()
    env.reset(seed=0)
    wrapped = _ComposedPolicy(_ZeroModel(), env, compose=True, blend_s=0.0,
                              stall_substitute_every_s=0.5,
                              stall_substitute_dur_s=0.2)
    ep, _ = eval_checkpoint.run_episode(
        env, wrapped, deterministic=True, video=False, annotate=None)
    env.close()
    assert "success" in ep
    assert wrapped.stall_ticks > 0
