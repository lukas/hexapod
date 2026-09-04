"""Tests for the 09-04 transition-stress suite (operator directive
fb_20260904T074505_6a3ac9): SEQ_NEXT_STRESS grammar (default OFF,
bit-exact), aggregate_stress gate semantics (over_current reported but
never vetoing alone; mechanical terms veto), smoothness telemetry, and
the over_current audit's exact lowpass deconvolution.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "linux_control"))
sys.path.insert(0, str(ROOT / "linux_control" / "urt2_setup"))

from rl_move.config import load_config  # noqa: E402
from rl_move.sim.walk_task import SimHexapodJointWalkEnv  # noqa: E402
from rl_move.sim.eval_cmd_stress import aggregate_stress  # noqa: E402
from rl_move.sim.eval_checkpoint import _smoothness_fields  # noqa: E402
from rl_move.sim.audit_over_current import (  # noqa: E402
    AMPS_PER_NM, CUR_CAP_A, LP_TAU_S, RAIL_A, deconvolve_torque)


def _make_env(seed=0, *, stress=None, seg_s=(2.5, 4.0),
              episode_seconds=30.0):
    cfg = load_config()
    g = cfg.setdefault("goal", {})
    g["mode_seq"] = 1.0
    g["mode_seq_segment_s_min"] = seg_s[0]
    g["mode_seq_segment_s_max"] = seg_s[1]
    g["mode_seq_max_segments"] = 10
    if stress is not None:
        g["mode_seq_stress"] = stress
    cfg.setdefault("obs", {})["mode_onehot"] = 1.0
    return SimHexapodJointWalkEnv(cfg, seed=seed,
                                  episode_seconds=episode_seconds)


def _plans(env, n=6):
    out = []
    for _ in range(n):
        env.reset()
        out.append([str(p["mode"]) for p in env._seq_plan])
    return out


def test_stress_off_bitexact_plans():
    a = _make_env(seed=11, stress=None)
    b = _make_env(seed=11, stress=0.0)
    assert _plans(a) == _plans(b)


def test_stress_grammar_transitions():
    legal = SimHexapodJointWalkEnv.SEQ_NEXT_STRESS
    seen = set()
    for seed in range(10):
        env = _make_env(seed=seed, stress=1.0)
        for plan in _plans(env, n=4):
            for m0, m1 in zip(plan, plan[1:]):
                assert m1 in legal[m0], (m0, m1)
                seen.add((m0, m1))
    # The two stress-only transitions the legacy grammar never samples
    # must actually occur (that is the point of the suite).
    assert ("rise", "lower") in seen
    assert ("walk", "hold") in seen


def test_stress_legal_superset_of_legacy():
    legacy = SimHexapodJointWalkEnv.SEQ_NEXT
    stress = SimHexapodJointWalkEnv.SEQ_NEXT_STRESS
    for m, nxt in legacy.items():
        assert set(nxt) <= set(stress[m])


def _ep(term_reason=None, **kw):
    ep = {"terminated": term_reason is not None,
          "term_reason": term_reason or "",
          "seq_n_segments_planned": 4, "seq_n_segments_reached": 4,
          "seq_completed": term_reason is None}
    ep.update(kw)
    return ep


def test_aggregate_stress_over_current_reported_not_vetoing():
    reports = {"dr0": {"episodes": {"rise/det": [
        _ep(None, cmd_rate_p95_deg_s=20.0, cmd_jerk_p95_deg_s2=900.0,
            slew_sat_frac=0.10, cur_rail_frac=0.0),
        _ep("over_current", cur_rail_frac=0.4),
    ]}}}
    v = aggregate_stress(reports)
    assert v["over_current_terms"] == 1
    assert v["mech_term_reasons"] == {}
    assert v["gate"]["zero_mech_terms"] is True
    assert v["gate"]["pass"] is True
    assert v["smoothness"]["cmd_rate_p95_deg_s_med"] == 20.0
    assert v["smoothness"]["cur_rail_frac_med"] == 0.2


def test_aggregate_stress_mechanical_term_vetoes():
    reports = {"dr0": {"episodes": {"rise/det": [
        _ep("tilt_roll"), _ep(None)]}}}
    v = aggregate_stress(reports)
    assert v["mech_term_reasons"] == {"tilt_roll": 1}
    assert v["gate"]["zero_mech_terms"] is False
    assert v["gate"]["pass"] is False


def test_deconvolve_torque_roundtrip():
    rng = np.random.default_rng(0)
    dt = 0.01
    tau_true = np.abs(rng.uniform(0, 2.2, size=(400, 3)))
    raw = np.minimum(tau_true * AMPS_PER_NM, CUR_CAP_A)
    a = dt / (dt + LP_TAU_S)
    filt = np.empty_like(raw)
    filt[0] = raw[0]
    for i in range(1, len(raw)):
        filt[i] = (1 - a) * filt[i - 1] + a * raw[i]
    tau_rec = deconvolve_torque(filt, dt)
    np.testing.assert_allclose(tau_rec, tau_true, atol=1e-9)


def test_rail_identity_constant():
    # 2.64 A is EXACTLY the forcerange rail image — the audit's anchor.
    assert abs(RAIL_A - 2.64) < 1e-12


def test_smoothness_fields_units_and_saturation():
    dt = 0.01
    env = SimpleNamespace(dt=dt, cfg={"safety": {"max_delta_q_deg": 0.375}})
    # ramp at exactly the slew cap on joint 0, others still.
    # commanded_position is in RADIANS (sim_env._cmd contract).
    n = 100
    cmd = [np.zeros(18) for _ in range(n)]
    for i in range(n):
        cmd[i] = cmd[i].copy()
        cmd[i][0] = np.radians(0.375 * i)
    f = _smoothness_fields(cmd, env)
    assert f["slew_sat_frac"] == 1.0
    assert abs(f["cmd_rate_max_deg_s"] - 37.5) < 1e-6
    assert f["cmd_jerk_p95_deg_s2"] == 0.0
    assert _smoothness_fields(cmd[:2], env) == {}
