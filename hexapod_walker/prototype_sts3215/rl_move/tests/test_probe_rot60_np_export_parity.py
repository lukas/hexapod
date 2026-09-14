"""sweep_and_compare (probe_rot60_np_export_parity.py) -- mechanics-only
unit tests. No mujoco, no checkpoint, no torch: fake stub models
exercise the sector-sweep comparison harness in isolation (<< 1s).
See probe_rot60_np_export_parity.py's module docstring for the real-
checkpoint evidence this unit-tests the mechanics of
(logs/ckpt_eval/rlonly_v2_rot60_np_export_parity/report.json).
"""
from __future__ import annotations

import numpy as np

from rl_move.sim.probe_rot60_np_export_parity import sweep_and_compare

OBS_DIM = 72


class _FakeSpace:
    def __init__(self, n):
        self.shape = (n,)


class _StubModel:
    """Deterministic function of obs -> 18 actions, model.predict
    contract only (mirrors NumpyMLPModel/PPO closely enough for
    Rot60Policy's __getattr__ passthrough + .predict call)."""

    def __init__(self, scale: float = 1.0):
        self.scale = scale
        self.observation_space = _FakeSpace(OBS_DIM)
        self.action_space = _FakeSpace(18)

    def predict(self, obs, deterministic: bool = True, **_kw):
        obs = np.asarray(obs)
        # Cheap deterministic 18-wide function of the obs vector.
        a = np.tanh(self.scale * obs[:18])
        return a, None


def test_identical_models_report_pass_and_zero_diff():
    a, b = _StubModel(), _StubModel()
    report = sweep_and_compare(a, b, obs_dim=OBS_DIM, samples=40)
    assert report["PASS"] is True
    assert report["worst_abs_action_diff"] == 0.0
    assert report["k_sequence_matches"] is True
    # A 40-sample heading sweep over -pi..pi should visit more than
    # one 60deg sector.
    assert len(report["distinct_k_values_visited"]) > 1


def test_diverging_models_report_fail_with_nonzero_diff():
    a, b = _StubModel(scale=1.0), _StubModel(scale=1.5)
    report = sweep_and_compare(a, b, obs_dim=OBS_DIM, samples=40)
    assert report["PASS"] is False
    assert report["worst_abs_action_diff"] > 0.0
    # Both wrapped in their OWN Rot60Policy fed the IDENTICAL obs
    # sequence -- k is a pure function of (vx, vy, last_k), so the
    # sector trajectory itself must still agree even though the
    # underlying actors disagree numerically.
    assert report["k_sequence_matches"] is True


def test_tolerance_is_respected():
    a, b = _StubModel(), _StubModel()
    report_tight = sweep_and_compare(a, b, obs_dim=OBS_DIM, samples=10,
                                     tol=1e-9)
    assert report_tight["PASS"] is True  # exactly zero diff, any tol
