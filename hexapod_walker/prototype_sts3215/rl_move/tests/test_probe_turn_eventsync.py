"""Event-sync screen probe: pure analysis functions and the
pre-registered mechanical verdict (no MuJoCo needed)."""
import math

import numpy as np
import pytest

from rl_move.sim import probe_turn_eventsync as es


PERIOD = 75  # ticks (0.75 s @ 100 Hz)


def synth_masks(n_periods=10, shift_ticks=None, duty=0.5):
    """Planned stance + contact masks for 6 legs; contact = plan shifted
    per leg by shift_ticks (tripod phasing between leg groups)."""
    if shift_ticks is None:
        shift_ticks = [0] * 6
    T = n_periods * PERIOD
    t = np.arange(T)
    plan = np.zeros((T, 6), dtype=bool)
    contact = np.zeros((T, 6), dtype=bool)
    for f in range(6):
        ph = (t + (PERIOD // 2 if f % 2 else 0)) % PERIOD
        plan[:, f] = ph < duty * PERIOD
        ph_c = (t - shift_ticks[f] + (PERIOD // 2 if f % 2 else 0)) % PERIOD
        contact[:, f] = ph_c < duty * PERIOD
    return plan, contact


def test_event_offsets_recovers_common_and_differential_shift():
    shifts = [21, 21, 24, 21, 21, 21]  # leg 2 lags 30 ms extra
    plan, contact = synth_masks(shift_ticks=shifts)
    out = es.event_offsets(plan, contact, PERIOD)
    for f, s in enumerate(shifts):
        assert out["per_leg"][f]["touchdown_med_ms"] == pytest.approx(s * 10)
        assert out["per_leg"][f]["touchdown_iqr_ms"] == pytest.approx(0.0)
    assert out["touchdown_common_ms"] == pytest.approx(210.0)
    assert out["touchdown_differential_ms"][2] == pytest.approx(30.0)
    assert out["interleg_spread_ms"] == pytest.approx(30.0)


def test_event_offsets_wraps_circularly():
    # a lag of PERIOD-5 ticks must read as -5 ticks (early), not +70
    plan, contact = synth_masks(shift_ticks=[PERIOD - 5] * 6)
    out = es.event_offsets(plan, contact, PERIOD)
    assert out["touchdown_common_ms"] == pytest.approx(-50.0)


def test_support_state_stats_and_counterfactual():
    T = 100
    loaded = np.zeros((T, 6), dtype=bool)
    loaded[:40, [0, 2, 4]] = True            # pureA
    loaded[40:80, [1, 3, 5]] = True          # pureB
    loaded[80:, :4] = True                   # mixed (2 of A, 2 of B)
    wz = np.concatenate([np.full(40, .10), np.full(40, .10),
                         np.full(20, .01)])
    vx = np.full(T, .04)
    out = es.support_state_stats(loaded, wz, vx)
    assert out["states"]["pureA"]["frac"] == pytest.approx(0.4)
    assert out["states"]["pureB"]["frac"] == pytest.approx(0.4)
    assert out["states"]["mixed"]["frac"] == pytest.approx(0.2)
    assert out["wz_pure_avg"] == pytest.approx(0.10)
    assert out["wz_mean_overall"] == pytest.approx(0.082)
    # counterfactual: mixed ticks perform like pure -> exactly 0.10
    assert out["wz_counterfactual_mean"] == pytest.approx(0.10)
    gain = es.cell_gain(out, wz_cmd=0.15)
    assert gain == pytest.approx((0.10 - 0.082) / 0.082)
    # wrong commanded sign flips the gain negative
    assert es.cell_gain(out, wz_cmd=-0.15) == pytest.approx(-gain)


def _mk_result(wz_cmd, phase, gain_frac, spread_ms, diffs=None,
               straight_cf=0.001, fell=False, parity=True):
    """Build a minimal synthetic per-cell result for verdict tests."""
    m = 0.064 * math.copysign(1.0, wz_cmd) if wz_cmd else 0.0001
    cf = m + gain_frac * abs(m) * math.copysign(1.0, wz_cmd) if wz_cmd \
        else straight_cf
    return {
        "wz_cmd": wz_cmd, "phase_offset": phase, "fell": fell,
        "parity": {"ok": parity},
        "events": {"interleg_spread_ms": spread_ms,
                   "touchdown_differential_ms":
                       diffs if diffs is not None else [0.0] * 6},
        "support_states": {"wz_mean_overall": m,
                           "wz_counterfactual_mean": cf},
    }


def _grid(gain, spread, diffs_pos=None, diffs_neg=None, straight_cf=0.001,
          fell=False, parity=True):
    return [
        _mk_result(0.15, 0.0, gain, spread, diffs_pos, fell=fell,
                   parity=parity),
        _mk_result(0.15, math.pi, gain, spread, diffs_pos, parity=parity),
        _mk_result(-0.15, 0.0, gain, spread, diffs_neg, parity=parity),
        _mk_result(-0.15, math.pi, gain, spread, diffs_neg, parity=parity),
        _mk_result(0.0, 0.0, 0.0, spread, None, straight_cf=straight_cf,
                   parity=parity),
        _mk_result(0.0, math.pi, 0.0, spread, None, straight_cf=straight_cf,
                   parity=parity),
    ]


def test_historical_bar_preserved_but_is_not_causal_support():
    v = es.verdict(_grid(gain=0.15, spread=60.0))
    assert v["checks"]["s1_pass"] and v["checks"]["s2_pass"] \
        and v["checks"]["s3_pass"] and v["historical_bar_supported"]
    assert not v["supported"] and not v["observational_screen_passed"]


def test_verdict_rejects_small_or_wrong_sign_gain():
    assert not es.verdict(_grid(gain=0.05, spread=60.0))["historical_bar_supported"]
    v = es.verdict(_grid(gain=-0.15, spread=60.0))
    assert not v["checks"]["s1_pass"] and not v["historical_bar_supported"]


def test_verdict_rejects_common_shift_only_signal():
    # uniform offsets: tiny spread, no sign differential -> S2 fails
    # even with a large counterfactual gain (closed global-lag territory)
    v = es.verdict(_grid(gain=0.20, spread=20.0))
    assert not v["checks"]["s2_pass"] and not v["historical_bar_supported"]


def test_verdict_sign_differential_alone_can_pass_s2():
    dp = [0.0, 40.0, 0.0, 0.0, 0.0, 0.0]
    dn = [0.0, -40.0, 0.0, 0.0, 0.0, 0.0]  # 80 ms differential on leg 1
    v = es.verdict(_grid(gain=0.20, spread=20.0, diffs_pos=dp, diffs_neg=dn))
    assert v["checks"]["s2_pass"] and v["historical_bar_supported"]


def test_verdict_straight_drift_falls_or_parity_fail_s3():
    assert not es.verdict(_grid(0.15, 60.0, straight_cf=0.02))["historical_bar_supported"]
    assert not es.verdict(_grid(0.15, 60.0, fell=True))["historical_bar_supported"]
    assert not es.verdict(_grid(0.15, 60.0, parity=False))["historical_bar_supported"]


def test_parity_reference_covers_exactly_the_six_frozen_cells():
    cells = {(vx, wz) for vx, wz, _ in es.PARITY_REF}
    assert cells == {(0.08, 0.15), (0.08, -0.15), (0.08, 0.0)}
    phases = {p for _, _, p in es.PARITY_REF}
    assert phases == {0.0, math.pi}
    assert len(es.PARITY_REF) == 6
