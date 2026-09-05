"""Tests for the opt-in measured-feasibility command governor
(rl_move/sim/command_envelope.py) + the pure scoring math of its
paired evaluator (todaypolicy hardware-delivery item, operator MCP
note fb_20260905T071610_749846, 09-05). CPU-pure — no MuJoCo."""
import math

import numpy as np
import pytest

from rl_move.sim.command_envelope import (CommandEnvelope, EnvelopeConfig)
from rl_move.sim.eval_command_envelope import (SCENARIOS, command_at,
                                               pair_deltas, score_traces)

DT = 0.01  # 100 Hz


def _run(env, script, sat_fn=None):
    outs = []
    for k, req in enumerate(script):
        sat = sat_fn(k, outs) if sat_fn else 0.0
        outs.append(env.step(DT, req, sat))
    return outs


def test_disabled_is_identity_passthrough():
    env = CommandEnvelope(EnvelopeConfig(enabled=False))
    for req in [(0.08, 0.0, 0.25), (-0.08, 0.02, -1.0), (0.0, 0.0, 0.0)]:
        # even under absurd saturation feedback, disabled = identity
        out = env.step(DT, req, 1.0)
        assert out.applied == req
        assert out.requested == req
        assert out.authority == 1.0
        assert out.governing is False
    # no internal creep either
    assert env.step(DT, (0.08, 0.0, 0.25), 1.0).applied == (0.08, 0.0, 0.25)


def test_rate_limited_continuity_and_convergence():
    cfg = EnvelopeConfig(enabled=True)
    env = CommandEnvelope(cfg)
    req = (0.08, 0.0, 0.25)
    outs = _run(env, [req] * 300)  # 3 s, zero saturation
    prev = (0.0, 0.0, 0.0)
    rates = (cfg.vx_rate, cfg.vy_rate, cfg.wz_rate)
    for o in outs:
        for i in range(3):
            assert abs(o.applied[i] - prev[i]) <= rates[i] * DT + 1e-12
        prev = o.applied
    # converges to the full request when the loop is feasible
    assert outs[-1].applied == pytest.approx(req, abs=1e-9)
    assert outs[-1].authority == pytest.approx(1.0, abs=1e-6)


def test_reversal_and_stop_are_continuous():
    cfg = EnvelopeConfig(enabled=True)
    env = CommandEnvelope(cfg)
    script = ([(0.08, 0.0, 0.0)] * 200 + [(0.0, 0.0, 0.0)] * 100
              + [(-0.08, 0.0, 0.0)] * 200)
    outs = _run(env, script)
    applied_vx = [o.applied[0] for o in outs]
    d = np.abs(np.diff([0.0] + applied_vx))
    assert float(d.max()) <= cfg.vx_rate * DT + 1e-12
    # actually reaches the reversed command
    assert applied_vx[-1] == pytest.approx(-0.08, abs=1e-9)
    # passes through (near) zero on the way — no sign jump
    signs = np.sign(np.asarray(applied_vx)[np.abs(applied_vx) > 1e-9])
    flips = np.where(np.diff(signs) != 0)[0]
    assert len(flips) == 1


def test_saturation_throttles_combined_and_recovers():
    cfg = EnvelopeConfig(enabled=True, mode="shared")
    env = CommandEnvelope(cfg)
    req = (0.08, 0.0, 0.25)
    # feasible warmup
    _run(env, [req] * 100)
    # sustained saturation well over target
    outs_hot = _run(env, [req] * 400, sat_fn=lambda k, o: 0.9)
    g = outs_hot[-1].authority
    assert g < 1.0
    assert g >= cfg.authority_floor - 1e-12
    # shared mode shrinks BOTH axes by the same factor
    a = outs_hot[-1].applied
    assert a[0] == pytest.approx(0.08 * g, rel=1e-3)
    assert a[2] == pytest.approx(0.25 * g, rel=1e-3)
    # curvature (turn radius vx/wz) preserved by shared throttling
    assert a[0] / a[2] == pytest.approx(0.08 / 0.25, rel=1e-6)
    # feedback clears -> authority recovers toward 1
    outs_cool = _run(env, [req] * 2000, sat_fn=lambda k, o: 0.0)
    assert outs_cool[-1].authority > 0.95
    assert outs_cool[-1].applied[0] == pytest.approx(0.08, abs=2e-3)


def test_floor_bounds_throttle():
    cfg = EnvelopeConfig(enabled=True, authority_floor=0.35)
    env = CommandEnvelope(cfg)
    outs = _run(env, [(0.08, 0.0, 0.25)] * 3000, sat_fn=lambda k, o: 1.0)
    assert outs[-1].authority == pytest.approx(0.35, abs=1e-9)
    assert outs[-1].applied[0] == pytest.approx(0.08 * 0.35, rel=1e-3)


def test_combined_only_leaves_pure_commands_at_full_authority():
    cfg = EnvelopeConfig(enabled=True, combined_only=True)
    env = CommandEnvelope(cfg)
    # pure forward under heavy (irrelevant) saturation: not governed
    outs = _run(env, [(0.08, 0.0, 0.0)] * 300, sat_fn=lambda k, o: 0.9)
    assert outs[-1].governing is False
    assert outs[-1].authority == 1.0
    assert outs[-1].applied[0] == pytest.approx(0.08, abs=1e-9)
    # pure turn likewise
    outs = _run(env, [(0.0, 0.0, 0.25)] * 300, sat_fn=lambda k, o: 0.9)
    assert outs[-1].governing is False
    assert outs[-1].applied[2] == pytest.approx(0.25, abs=1e-9)


def test_yaw_priority_sheds_translation_only():
    cfg = EnvelopeConfig(enabled=True, mode="yaw_priority")
    env = CommandEnvelope(cfg)
    req = (0.08, 0.0, 0.25)
    _run(env, [req] * 100)  # converge
    outs = _run(env, [req] * 600, sat_fn=lambda k, o: 0.9)
    g = outs[-1].authority
    assert g < 1.0
    assert outs[-1].applied[0] == pytest.approx(0.08 * g, rel=1e-3)
    # yaw demand passes intact
    assert outs[-1].applied[2] == pytest.approx(0.25, abs=1e-9)


def test_requested_always_preserved_verbatim():
    env = CommandEnvelope(EnvelopeConfig(enabled=True))
    req = (0.08, -0.03, 0.25)
    out = env.step(DT, req, 0.9)
    assert out.requested == req  # provenance: original demand echoed


def test_command_at_segments():
    _dur, segs = SCENARIOS["stop_restart"]
    assert command_at(segs, 0.5) == (0.0, 0.0, 0.0)
    assert command_at(segs, 1.0) == (0.08, 0.0, 0.0)
    assert command_at(segs, 5.5) == (0.0, 0.0, 0.0)
    assert command_at(segs, 8.0) == (0.08, 0.0, 0.0)


def _mk_traces(T, dt, req, applied, vx_ach, wz_ach):
    t = np.arange(T) * dt
    return {
        "t": t,
        "req": np.tile(req, (T, 1)).astype(float),
        "applied": np.tile(applied, (T, 1)).astype(float),
        "authority": np.ones(T),
        "body_v": np.tile([vx_ach, 0.0], (T, 1)).astype(float),
        "wz": np.full(T, wz_ach, dtype=float),
        "yaw": np.cumsum(np.full(T, wz_ach) * dt),
        "sat_frac": np.full(T, 0.4),
        "sat_frac_yaw": np.full(T, 0.5),
        "peak_ratio": np.full(T, 2.5),
        "n_contact": np.full(T, 4.0),
        "walk": np.ones(T),
    }


def test_score_traces_scores_against_requested_not_applied():
    # Governor "cheats" by applying half the request; achieved matches
    # the APPLIED command perfectly. Scoring must still show the miss
    # vs the ORIGINAL request — throttling cannot fake success.
    T, dt = 1000, 0.01
    segs = [(0.0, 0.08, 0.0, 0.25)]
    tr = _mk_traces(T, dt, req=[0.08, 0.0, 0.25], applied=[0.04, 0.0, 0.125],
                    vx_ach=0.04, wz_ach=0.125)
    m = score_traces(tr, dt=dt, segments=segs, slip_m=0.0, cmd_prog_m=1.0,
                     fell=False, t_score_start=0.0)
    assert m["vx_err_med_steady"] == pytest.approx(0.04, abs=1e-9)
    assert m["wz_err_med_steady"] == pytest.approx(0.125, abs=1e-9)
    assert m["progress_ratio"] == pytest.approx(0.5, rel=1e-6)
    assert m["yaw_ratio"] == pytest.approx(0.5, rel=1e-2)
    # requested-vs-applied authority is reported explicitly
    assert m["vx_authority_med"] == pytest.approx(0.5, rel=1e-9)
    assert m["wz_authority_med"] == pytest.approx(0.5, rel=1e-9)


def test_score_traces_parking_scores_zero_progress():
    T, dt = 500, 0.01
    segs = [(0.0, 0.08, 0.0, 0.0)]
    tr = _mk_traces(T, dt, req=[0.08, 0.0, 0.0], applied=[0.0, 0.0, 0.0],
                    vx_ach=0.0, wz_ach=0.0)
    m = score_traces(tr, dt=dt, segments=segs, slip_m=0.0, cmd_prog_m=0.4,
                     fell=False, t_score_start=0.0)
    assert m["progress_ratio"] == pytest.approx(0.0, abs=1e-9)
    assert m["vx_err_med_steady"] == pytest.approx(0.08, abs=1e-9)
    assert m["vx_authority_med"] == pytest.approx(0.0, abs=1e-9)


def test_pair_deltas_matches_scenario_seed():
    rows = [
        {"scenario": "fwd", "seed": 0, "arm": "baseline",
         "progress_ratio": 0.8, "fell": False},
        {"scenario": "fwd", "seed": 0, "arm": "env_shared",
         "progress_ratio": 0.7, "fell": False},
    ]
    d = pair_deltas(rows)
    assert len(d) == 1
    assert d[0]["arm"] == "env_shared"
    assert d[0]["progress_ratio"]["delta"] == pytest.approx(-0.1)
