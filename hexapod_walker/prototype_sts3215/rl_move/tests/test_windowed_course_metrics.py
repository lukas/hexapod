"""Unit tests for eval_checkpoint.windowed_course_stats -- the PRIMARY
windowed command-following eval metric (operator eval directive
fb_20260829T141858_9421cd, 2026-08-29).

Synthetic-path tests: no physics, just the metric's own contract --
straight on-course, off-course, wrong-way, park-during-command,
stop-straddling windows, mid-window command reversal (grace), zigzag
sway vs its net course, and the speed-ratio/motion-floor pairing that
keeps parking from hiding in the angle statistic.
"""
from __future__ import annotations


import numpy as np
import pytest


pytest.importorskip("mujoco")

from rl_move.sim.eval_checkpoint import windowed_course_stats

DT = 0.01     # 100 Hz


def _path(vel_fn, cmd_fn, seconds: float):
    n = int(round(seconds / DT))
    xy = np.zeros((n, 2))
    cmd = np.zeros((n, 2))
    p = np.zeros(2)
    for i in range(n):
        t = i * DT
        p = p + np.asarray(vel_fn(t)) * DT
        xy[i] = p
        cmd[i] = cmd_fn(t)
    return xy, cmd


def test_straight_on_course():
    xy, cmd = _path(lambda t: (0.05, 0.0), lambda t: (0.05, 0.0), 10.0)
    st = windowed_course_stats(xy, cmd, DT, 1.0)
    assert st["n_cmd_windows"] > 50
    assert st["n_motion_valid"] == st["n_cmd_windows"]
    assert max(st["err_deg"]) < 1.0
    assert np.mean(st["speed_ratio"]) == pytest.approx(1.0, abs=0.01)
    assert sum(st["wrong"]) == 0


def test_45deg_off_course_and_wrong_way():
    xy, cmd = _path(lambda t: (0.05, 0.05), lambda t: (0.05, 0.0), 6.0)
    st = windowed_course_stats(xy, cmd, DT, 1.0)
    assert np.median(st["err_deg"]) == pytest.approx(45.0, abs=1.0)
    assert sum(st["wrong"]) == 0
    xy, cmd = _path(lambda t: (-0.05, 0.0), lambda t: (0.05, 0.0), 6.0)
    st = windowed_course_stats(xy, cmd, DT, 1.0)
    assert np.median(st["err_deg"]) == pytest.approx(180.0, abs=1.0)
    assert np.mean(st["wrong"]) == 1.0
    assert np.mean(st["speed_ratio"]) == pytest.approx(-1.0, abs=0.01)


def test_park_during_command_cannot_hide():
    """A parked robot under a move command: windows are COUNTED (they
    are commanded), score speed_ratio ~0, and fail the motion floor --
    so the angle stats are empty but the parking is fully visible in
    n_motion_valid/speed_ratio, never a silent pass."""
    xy, cmd = _path(lambda t: (0.0005, 0.0), lambda t: (0.05, 0.0), 6.0)
    st = windowed_course_stats(xy, cmd, DT, 1.0)
    assert st["n_cmd_windows"] > 30
    assert st["n_motion_valid"] == 0
    assert st["err_deg"] == []
    assert abs(np.mean(st["speed_ratio"])) < 0.02


def test_stop_straddling_windows_excluded():
    def cmd_fn(t):
        return (0.05, 0.0) if t < 3.0 or t > 3.5 else (0.0, 0.0)
    xy, cmd = _path(lambda t: (0.05, 0.0), cmd_fn, 7.0)
    st_all = windowed_course_stats(xy, cmd, DT, 1.0)
    st_nostop = windowed_course_stats(
        *_path(lambda t: (0.05, 0.0), lambda t: (0.05, 0.0), 7.0),
        DT, 1.0)
    # ~1.5 s of window positions straddle the stop and must vanish
    assert st_all["n_cmd_windows"] < st_nostop["n_cmd_windows"]
    assert st_all["n_cmd_windows"] > 0


def test_command_reversal_grace():
    """Windows straddling a 180 deg command flip cancel their own
    integrated command below the coherence floor and are skipped --
    the policy is never charged for a physically impossible
    instantaneous reversal (directive item 7 analog)."""
    def cmd_fn(t):
        return (0.05, 0.0) if t < 3.0 else (-0.05, 0.0)

    def vel_fn(t):
        return (0.05, 0.0) if t < 3.1 else (-0.05, 0.0)
    xy, cmd = _path(vel_fn, cmd_fn, 6.0)
    st = windowed_course_stats(xy, cmd, DT, 1.0)
    # every surviving window tracks its own (coherent) command well:
    # the flip transient itself was excused, not scored as wrong-way
    assert np.median(st["err_deg"]) < 15.0
    assert np.mean(st["wrong"]) < 0.1


def test_zigzag_sway_vs_net_course():
    """A +/-30 deg zigzag around a followed course: 1 s-window course
    error stays FAR below the instantaneous 30 deg (the windowed
    metric sees the net course, per the directive's whole point), and
    with_sway reports the real perpendicular oscillation."""
    def vel_fn(t):
        a = np.radians(30.0) * (1 if int(t / 0.5) % 2 == 0 else -1)
        return (0.05 * np.cos(a), 0.05 * np.sin(a))
    xy, cmd = _path(vel_fn, lambda t: (0.05, 0.0), 8.0)
    st = windowed_course_stats(xy, cmd, DT, 1.0, with_sway=True)
    assert np.median(st["err_deg"]) < 12.0
    assert max(st["sway_rms_m"]) > 0.002
    # straight control: near-zero sway
    st0 = windowed_course_stats(
        *_path(lambda t: (0.05, 0.0), lambda t: (0.05, 0.0), 8.0),
        DT, 1.0, with_sway=True)
    assert max(st0["sway_rms_m"]) < 1e-6


def _cmd_fn_90turn(t):
    return (0.05, 0.0) if t < 3.0 else (0.0, 0.05)


def _vel_fn_90turn_with_lag(t):
    # Models unavoidable physical reorientation lag (a real gait needs
    # time to reorient stance after a heading command changes): the
    # velocity keeps the OLD direction for 0.4s past the command
    # change, then snaps to the new one and tracks perfectly forever
    # after -- i.e. perfect steady-state tracking, transient-only lag.
    return (0.05, 0.0) if t < 3.4 else (0.0, 0.05)


def test_scripted_90deg_turn_slips_past_coherence_floor_by_default():
    """A moderate (90 deg, non-reversing) scripted command change does
    NOT trip the reversal-grace floor (its vector-sum ratio stays
    ~0.71, above the 0.5 min_cmd_coherence default) -- so by default a
    window straddling it IS scored, charging a brief, unavoidable
    physical reorientation lag as course error even though tracking is
    perfect before and after. This is the 09-22 hybrid_demo
    transition-tick artifact (measured live: envwide-headset16's
    course_err_1s_p90_deg dominated by windows straddling scripted
    heading changes, not steady-state tracking)."""
    xy, cmd = _path(_vel_fn_90turn_with_lag, _cmd_fn_90turn, 6.0)
    st = windowed_course_stats(xy, cmd, DT, 1.0)
    assert st["n_cmd_windows"] > 0
    assert np.percentile(st["err_deg"], 90) > 25.0   # the artifact: NOT excluded


def test_max_turn_deg_excludes_the_scripted_turn_window():
    """Opt-in max_turn_deg fixes the P90 statistic (the actual gate
    quantity) for the artifact above: excluding windows whose command
    direction changes >45 deg mid-window removes the reference-
    blending windows that preceded the transition entirely (their OWN
    command integral mixes both phases), collapsing p90 from ~34deg to
    0deg. A handful of windows starting exactly AT/just-after the
    transition still show real residual reorientation-catch-up error
    (not excluded by this filter, and correctly so -- that error is
    genuine, just a small minority no longer able to dominate the p90
    tail). Bit-identical to the default (None) call otherwise."""
    xy, cmd = _path(_vel_fn_90turn_with_lag, _cmd_fn_90turn, 6.0)
    baseline = windowed_course_stats(xy, cmd, DT, 1.0)
    st = windowed_course_stats(xy, cmd, DT, 1.0, max_turn_deg=45.0)
    assert st["n_cmd_windows"] < baseline["n_cmd_windows"]
    assert np.percentile(baseline["err_deg"], 90) > 25.0
    assert np.percentile(st["err_deg"], 90) < 5.0
    # default (None) is unaffected -- exact same call with no kwarg
    st_default = windowed_course_stats(xy, cmd, DT, 1.0)
    assert st_default["n_cmd_windows"] == baseline["n_cmd_windows"]
    assert st_default["err_deg"] == baseline["err_deg"]
