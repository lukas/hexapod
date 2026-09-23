"""Regression test for the 2026-09-23 audit_over_current.py field bug.

BUG: the 2026-09-19 current-model split (sim_env.py::_read_state) made
``over_current_signal`` -- not ``servo_current`` -- the SafetyLayer's
actual over_current TRIP channel under the now-default
``bus.current_model="power"``. ``servo_current`` under that model is a
near-zero mechanical-power estimate that reads ~0 A even during a real
stall (by design -- see the module docstring). ``audit_over_current.
classify_trace`` read ``servo_current`` unconditionally, so it audited
the wrong (irrelevant) column for every power-model trace: a genuine
sustained-rail trip that fired ``term_reason="over_current"`` in the
episode summary would misclassify as ``NO_RAIL`` because the recorded
servo_current never approached the rail.

These tests pin the fix: ``classify_trace`` must prefer
``over_current_signal`` when the trace has real (non-NaN) values for
it, and fall back to ``servo_current`` only for legacy
torque_proxy-style traces (no separate trip signal recorded).
"""
from __future__ import annotations

import json

import numpy as np

from rl_move.sim.audit_over_current import classify_trace, RAIL_A


def _ep(term_reason="over_current"):
    return {"mode": "rise", "start_kind": "bridge",
            "term_reason": term_reason}


def _write(tmp_path, name, *, servo_current, over_current_signal,
          t_s=None, qvel=None, height_mm=None, ep=None):
    t = len(servo_current)
    payload = {
        "ep_json": json.dumps(ep or _ep()),
        "servo_current": np.asarray(servo_current, dtype=np.float64),
        "t_s": (np.asarray(t_s, dtype=np.float64) if t_s is not None
               else np.arange(t, dtype=np.float64) * 0.02),
    }
    if over_current_signal is not None:
        payload["over_current_signal"] = np.asarray(
            over_current_signal, dtype=np.float64)
    if qvel is not None:
        payload["qvel"] = np.asarray(qvel, dtype=np.float64)
    if height_mm is not None:
        payload["height_mm"] = np.asarray(height_mm, dtype=np.float64)
    p = tmp_path / name
    np.savez(p, **payload)
    return p


def test_power_model_trace_audits_the_trip_signal_not_servo_current(tmp_path):
    """servo_current near-zero (power model) but over_current_signal
    sustained at the rail on one joint -- must NOT read NO_RAIL just
    because servo_current is low, and must record which field it used."""
    T = 60
    n_j = 18
    servo_current = np.full((T, n_j), 0.1)  # power-model: ~0 A, never rails
    over_current_signal = np.zeros((T, n_j))
    over_current_signal[10:50, 3] = RAIL_A  # sustained rail on joint 3
    qvel = np.zeros((T, 6 + n_j))  # hot joint static -> stall
    height_mm = np.linspace(30.0, 30.5, T)  # no real height progress
    p = _write(tmp_path, "power.npz", servo_current=servo_current,
              over_current_signal=over_current_signal, qvel=qvel,
              height_mm=height_mm)
    out = classify_trace(str(p), trip_a=2.9, trip_s=0.5, stall_qvel=0.05)
    assert out["current_field"] == "over_current_signal"
    assert out["cur_max_a"] == RAIL_A
    assert out["classification"] != "NO_RAIL"


def test_legacy_torque_proxy_trace_falls_back_to_servo_current(tmp_path):
    """No over_current_signal key at all (old trace / legacy
    bus.current_model="torque_proxy" run where servo_current IS the
    trip signal) -- must still classify off servo_current, unchanged."""
    T = 40
    n_j = 18
    servo_current = np.zeros((T, n_j))
    servo_current[5:35, 2] = RAIL_A
    p = _write(tmp_path, "legacy.npz", servo_current=servo_current,
              over_current_signal=None)
    out = classify_trace(str(p), trip_a=2.9, trip_s=0.5, stall_qvel=0.05)
    assert out["current_field"] == "servo_current"
    assert out["cur_max_a"] == RAIL_A


def test_all_nan_over_current_signal_falls_back_to_servo_current(tmp_path):
    """A trace saved under the new schema but from a legacy
    torque_proxy run (over_current_signal=None every tick -> NaN-filled
    column, per _save_rollout_trace's None-column contract) must still
    fall back to servo_current, not silently audit an all-NaN column."""
    T = 30
    n_j = 18
    servo_current = np.zeros((T, n_j))
    servo_current[3:20, 1] = RAIL_A
    over_current_signal = np.full((T, n_j), np.nan)
    p = _write(tmp_path, "nan.npz", servo_current=servo_current,
              over_current_signal=over_current_signal)
    out = classify_trace(str(p), trip_a=2.9, trip_s=0.5, stall_qvel=0.05)
    assert out["current_field"] == "servo_current"
    assert out["cur_max_a"] == RAIL_A
