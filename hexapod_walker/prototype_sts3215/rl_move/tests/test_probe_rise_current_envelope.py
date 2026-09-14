"""Mechanics-only smoke test for probe_rise_current_envelope.py (the
walkcurr rise actuator-current-envelope diagnostic, 2026-09-14):
env construction + a few open-loop replay ticks must not crash and
must report a physically sane, bounded current reading. Not a
rollout-ranking bank -- no pass/fail on gait quality, just "the tool
runs and returns numbers in-range."
"""
from pathlib import Path

import numpy as np

from rl_move.sim.probe_rise_current_envelope import (
    LAUNCH_OVERRIDES,
    _make_rise_env,
)
from rl_move.sim.joint_task import q_rad_to_action

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "rl_move/sim/refs/rise_ref_mesh_scripted.npz"


def test_make_rise_env_forces_flat_start_rise_only():
    env = _make_rise_env(seed=0, episode_seconds=15.0)
    env.reset()
    assert env._goal_gen.p_rise == 1.0
    assert env._goal_gen.force_rise_start == "flat"
    assert all(getattr(env._goal_gen, a) == 0.0
               for a in vars(env._goal_gen)
               if a.startswith("p_") and a != "p_rise")


def test_open_loop_replay_few_ticks_reports_bounded_current():
    assert REF.exists(), "mesh-native rise ref must ship in the repo"
    env = _make_rise_env(seed=0, episode_seconds=15.0)
    env.reset()
    ref = np.load(REF)
    q_ref, ref_dt = ref["q_rad"], float(ref["dt"])
    for step in range(5):
        j = int(round(step * env.dt / ref_dt))
        act = q_rad_to_action(q_ref[min(max(j, 0), len(q_ref) - 1)])
        _, _, term, trunc, _ = env.step(np.asarray(act).ravel())
        cur = env._state.servo_current
        assert cur is not None
        assert np.all(np.abs(cur) <= 3.0 + 1e-6)  # servo_current hard cap
        assert np.all(np.isfinite(cur))
        if term or trunc:
            break


def test_launch_overrides_match_walkcurr_stance50hz_stack():
    # These three keys are the physics-load-bearing subset of the
    # cw-stance50hz-rlonly-* launch cfg (env.model_source, control.hz,
    # safety.max_delta_q_deg) -- pin them so a future edit can't
    # silently drift the probe off the lineage it's meant to diagnose.
    assert LAUNCH_OVERRIDES[("env", "model_source")] == "mesh_mjx"
    assert LAUNCH_OVERRIDES[("control", "hz")] == 50.0
    assert LAUNCH_OVERRIDES[("safety", "max_delta_q_deg")] == 0.75
