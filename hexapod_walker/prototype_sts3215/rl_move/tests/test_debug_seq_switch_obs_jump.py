"""debug_seq_switch_obs_jump._install_switch_probe (2026-09-02
DIG-IN instrument): locks the two structural claims the standwalk
duration-mismatch dig-in (STATUS.md 2026-09-02) rests on before
trusting any pod read built on top of it:

1. a SAME-family switch (walk="plant" -> lower="plant") installs an
   IDENTICAL q_nom/z0 (the frames are literally the same dict entry),
   so the probe must measure an EXACT zero jump regardless of the
   robot's actual pose at the switch tick;
2. a family-CHANGING switch (rise="belly" -> walk="plant") installs a
   DIFFERENT canonical frame, so the probe must report family_changed
   and a nonzero jump whenever the actual pose differs from both
   canonical frames (the belly probe is the zero pose; a robot that
   has risen is nowhere near it).

Also locks that the probe is read-only: wrapping `_seq_maybe_switch`
must not change the env's own obs/reward stream (same guarantee any
diagnostic instrument needs before its readings are trusted)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "linux_control"))
sys.path.insert(0, str(ROOT / "linux_control" / "urt2_setup"))

from rl_move.config import load_config  # noqa: E402
from rl_move.sim.debug_seq_switch_obs_jump import (  # noqa: E402
    _install_switch_probe,
)
from rl_move.sim.walk_task import SimHexapodJointWalkEnv  # noqa: E402


def _make_env(seed: int, episode_seconds: float, plan: str,
              seg_s=(6.0, 8.0)) -> SimHexapodJointWalkEnv:
    cfg = load_config()
    g = cfg.setdefault("goal", {})
    g["mode_seq"] = 1.0
    g["mode_seq_segment_s_min"], g["mode_seq_segment_s_max"] = seg_s
    g["mode_seq_forced_plan"] = plan
    cfg.setdefault("obs", {})["mode_onehot"] = 1.0
    return SimHexapodJointWalkEnv(cfg, seed=seed,
                                  episode_seconds=episode_seconds)


def _run_to_end(env, events):
    rng = np.random.default_rng(0)
    done = False
    obs = None
    n = env.action_space.shape[0]
    while not done:
        a = rng.uniform(-0.05, 0.05, n)
        obs, _, term, trunc, _ = env.step(a)
        done = term or trunc
    return obs


def test_same_family_switch_zero_jump():
    env = _make_env(0, 12.0, "walk:6,lower:6")
    env.reset()
    events = _install_switch_probe(env)
    _run_to_end(env, events)
    fam_switches = [e for e in events if e["old_mode"] == "walk"
                   and e["new_mode"] == "lower"]
    assert len(fam_switches) == 1
    e = fam_switches[0]
    assert e["family_changed"] is False
    assert e["old_family"] == e["new_family"] == "plant"
    # exact zero: same dict entry installed, no floating-point noise
    assert e["q_jump_l2_deg"] == 0.0
    assert e["h_jump_mm"] == 0.0


def test_family_changing_switch_nonzero_jump():
    env = _make_env(0, 12.0, "rise:6,walk:6")
    env.reset()
    events = _install_switch_probe(env)
    _run_to_end(env, events)
    fam_switches = [e for e in events if e["old_mode"] == "rise"
                   and e["new_mode"] == "walk"]
    assert len(fam_switches) == 1
    e = fam_switches[0]
    assert e["family_changed"] is True
    assert e["old_family"] == "belly" and e["new_family"] == "plant"
    # belly q_nom is the all-zero joint pose (see _seq_capture_frames);
    # a robot 6s into a rise attempt is not sitting at exactly that
    # pose, so the reinstalled plant frame must move q_rel measurably.
    assert e["q_jump_l2_deg"] > 5.0


def test_probe_is_read_only():
    """Wrapping _seq_maybe_switch must not perturb the env's own
    step() outputs — same seed/actions, with vs without the probe
    installed, must produce bit-identical obs/reward streams."""
    plan = "rise:5,walk:5,lower:5"
    env_a = _make_env(1, 20.0, plan)
    env_b = _make_env(1, 20.0, plan)
    oa0, _ = env_a.reset()
    ob0, _ = env_b.reset()
    np.testing.assert_array_equal(oa0, ob0)
    _install_switch_probe(env_b)   # only b is instrumented
    rng = np.random.default_rng(0)
    n = env_a.action_space.shape[0]
    done = False
    while not done:
        act = rng.uniform(-0.1, 0.1, n)
        ra = env_a.step(act)
        rb = env_b.step(act)
        np.testing.assert_array_equal(ra[0], rb[0])
        assert ra[1] == pytest.approx(rb[1])
        done = ra[2] or ra[3]
