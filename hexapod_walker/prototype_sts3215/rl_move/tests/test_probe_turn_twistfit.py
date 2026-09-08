"""Unit tests for probe_turn_twistfit pure-math (no MuJoCo).

Covers: exact-twist recovery (fit + zero residual + equal per-foot
implied wz), detection of the TripodGait anchor-frozen stance law's
inconsistency, edge erosion, segment sweep accounting, and the
pre-registered support-bar evaluation."""
import math

import numpy as np
import pytest

from rl_move.sim.probe_turn_twistfit import (
    BAR, EDGE_ERODE_TICKS, analyze_stage, erode_segments, fit_twist_resid,
    implied_wz, segments, support_verdict, sweep_segments, twist_pred_vel)

LEG_ANGLES = [(i + 0.5) * math.pi / 3.0 for i in range(6)]
R0 = 0.22
DT = 0.01


def _exact_twist_paths(twist, T=120):
    """World-fixed feet under body twist -> body-frame paths (T,6,2)."""
    vx, vy, wz = twist
    p = np.array([[R0 * math.cos(a), R0 * math.sin(a)] for a in LEG_ANGLES])
    out = np.empty((T, 6, 2))
    out[0] = p
    for t in range(1, T):
        v = twist_pred_vel(out[t - 1], twist)
        # integrate with small substeps for near-exact rigid motion
        cur = out[t - 1].copy()
        for _ in range(10):
            cur = cur + twist_pred_vel(cur, twist) * (DT / 10)
        out[t] = cur
    return out


def test_fit_recovers_exact_twist():
    twist = (0.08, 0.0, 0.15)
    paths = _exact_twist_paths(twist)
    sel = np.ones((len(paths), 6), dtype=bool)
    res = analyze_stage(paths, sel, DT,
                        cmd_twists=np.tile(twist, (len(paths), 1)))
    assert res is not None
    assert res["wz_med"] == pytest.approx(0.15, rel=2e-3)
    assert res["vx_med"] == pytest.approx(0.08, rel=2e-3)
    assert res["resid_norm"] < 5e-3
    assert res["cmd_exact_resid_norm"] < 5e-3
    iw = res["per_foot_implied_wz_med"]
    assert all(v == pytest.approx(0.15, rel=5e-3) for v in iw)
    assert res["implied_wz_spread"] < 0.002


def test_anchor_frozen_chord_law_measured_small_but_nonzero():
    """TripodGait stance law: constant velocity frozen at the nominal
    anchor. The fitted wz stays ~= commanded (S1 no breach) and the
    exact-twist residual is small but nonzero (chord error)."""
    twist = (0.08, 0.0, 0.15)
    T = 40  # ~ one stance window
    p_nom = np.array([[R0 * math.cos(a), R0 * math.sin(a)]
                      for a in LEG_ANGLES])
    v_anchor = twist_pred_vel(p_nom, twist)   # frozen per-leg velocity
    paths = np.stack([p_nom + v_anchor * (t - T / 2) * DT
                      for t in range(T)])
    sel = np.ones((T, 6), dtype=bool)
    res = analyze_stage(paths, sel, DT,
                        cmd_twists=np.tile(twist, (T, 1)))
    assert res is not None
    # command encodes the full twist at the anchors
    assert res["wz_med"] == pytest.approx(0.15, rel=0.05)
    # chord inconsistency exists but is small (per-position mismatch)
    assert 0.0 < res["cmd_exact_resid_norm"] < BAR["cmd_resid_norm"]


def test_fit_requires_min_feet():
    p = np.zeros((2, 6, 2))
    p[:, :, 0] = np.arange(6)[None, :]
    sel = np.zeros((2, 6), dtype=bool)
    sel[:, :2] = True   # only 2 feet
    assert analyze_stage(p, sel, DT) is None
    tw = fit_twist_resid(p[0], np.zeros((6, 2)), sel[0])
    assert tw is None


def test_implied_wz_exact():
    twist = (0.03, -0.01, 0.2)
    p = np.array([[R0 * math.cos(a), R0 * math.sin(a)] for a in LEG_ANGLES])
    v = twist_pred_vel(p, twist)
    iw = implied_wz(p, v, twist[:2])
    assert np.allclose(iw, 0.2, atol=1e-12)


def test_erode_and_segments():
    col = np.array([1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0], dtype=bool)
    er = erode_segments(col, 2)
    assert er.sum() == (5 - 4) + (6 - 4)
    assert segments(col) == [(0, 4), (7, 12)]
    # erosion never adds ticks
    assert not (er & ~col).any()


def test_sweep_segments_ratio():
    T = 30
    des = np.zeros((T, 6, 2)); pads = np.zeros((T, 6, 2))
    plan = np.zeros((T, 6), dtype=bool)
    plan[5:25, 0] = True
    des[:, 0, 0] = np.linspace(0.0, 0.029, T)      # 2 cm commanded in seg
    pads[:, 0, 0] = np.linspace(0.0, 0.0145, T)    # half executed
    rows = sweep_segments(des, pads, plan)
    assert len(rows) == 1
    assert rows[0]["amp_ratio"] == pytest.approx(0.5, rel=1e-6)
    assert rows[0]["heading_err_deg"] == pytest.approx(0.0, abs=1e-9)


def _cell(wz, start, gain=1.0, resid=0.01, spread=0.001):
    return {"vx_cmd": 0.08, "wz_cmd": wz, "phase_offset": start,
            "stages": {"des": {"plan": {
                "wz_med": wz * gain, "cmd_exact_resid_norm": resid,
                "implied_wz_spread": spread, "vx_med": 0.08, "vy_med": 0.0,
                "n_fits": 100, "resid_norm": resid,
                "resid_rms_mps": resid * 0.1, "med_foot_speed_mps": 0.1,
                "per_foot_implied_wz_med": [wz * gain] * 6}}}}


def test_support_verdict_not_supported_when_command_consistent():
    cells = [_cell(0.15, 0.0), _cell(0.15, math.pi),
             _cell(-0.15, 0.0), _cell(-0.15, math.pi),
             _cell(0.0, 0.0), _cell(0.0, math.pi)]
    v = support_verdict(cells)
    assert v["supported"] is False
    assert len(v["checks"]) == 4          # straight cells excluded
    assert all(c["breach"] is False for c in v["checks"])


def test_support_verdict_supported_needs_all_four_arcs():
    bad = dict(gain=0.5)
    cells = [_cell(0.15, 0.0, **bad), _cell(0.15, math.pi, **bad),
             _cell(-0.15, 0.0, **bad), _cell(-0.15, math.pi, **bad)]
    assert support_verdict(cells)["supported"] is True
    cells[3] = _cell(-0.15, math.pi)      # one clean arc cell
    assert support_verdict(cells)["supported"] is False


def test_support_verdict_breach_kinds():
    v = support_verdict([_cell(0.15, 0.0, resid=0.5)])
    assert v["checks"][0]["S2"] is True and v["checks"][0]["breach"]
    v = support_verdict([_cell(0.15, 0.0, spread=0.15)])
    assert v["checks"][0]["S3"] is True
    v = support_verdict([_cell(0.15, 0.0, gain=1.2)])
    assert v["checks"][0]["S1"] is True
