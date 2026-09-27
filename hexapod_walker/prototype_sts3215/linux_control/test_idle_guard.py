"""Idle guard (idle_guard.py): standing + no request 20 min -> sit; current + no
motion + no request 60 min -> limp.  Pure state machine with an injected clock,
plus the watchdog wiring and the standing classifier on real 2026-09-27 poses."""
from __future__ import annotations

import pytest

from idle_guard import IdleGuard

STAND = {j: v for j, v in enumerate([0.0, 20.0, 100.0] * 6)}


def _g(**kw):
    return IdleGuard(sit_after_s=1200, limp_after_s=3600, limp_current_a=0.15, cooloff_s=300, **kw)


def _obs(g, now, *, req, armed=True, busy=False, rl=False, standing=True, pos=STAND, cur=0.3):
    return g.observe(now, armed=armed, busy=busy, rl_active=rl, standing=standing, positions=pos,
                     total_current_a=cur, last_request_mono=req)


def test_sit_fires_once_at_the_deadline_and_not_inside_the_cooloff():
    g = _g()
    assert _obs(g, 0.0, req=0.0) is None
    assert _obs(g, 1199.0, req=0.0) is None
    assert _obs(g, 1200.0, req=0.0) == "sit"
    assert g.state["last_action"] == "sit"
    for t in (1203.0, 1300.0, 1499.0):        # still "standing" while STEP-down plays / settles
        assert _obs(g, t, req=0.0) is None
    # cool-off over, robot STILL standing: lockout, no second sit
    assert _obs(g, 1500.0, req=0.0) is None and g.state["sit_lockout"] is True
    assert _obs(g, 5000.0, req=0.0, cur=0.05) is None


def test_request_or_heartbeat_resets_the_clock():
    g = _g()
    _obs(g, 0.0, req=0.0)
    assert _obs(g, 1150.0, req=1100.0) is None            # a request at 1100 (heartbeats count too)
    assert _obs(g, 2299.0, req=1100.0) is None
    assert _obs(g, 2300.0, req=1100.0) == "sit"


def test_external_control_suppresses_and_resets():
    g = _g()
    _obs(g, 0.0, req=0.0)
    assert _obs(g, 1200.0, req=0.0, rl=True) is None
    assert _obs(g, 1200.0, req=0.0, busy=True) is None
    assert _obs(g, 1200.0, req=0.0, armed=False) is None
    assert g.state["external_control"] is False and g.state["armed"] is False


def test_not_standing_never_sits_but_limp_still_runs_on_current():
    g = _g()
    _obs(g, 0.0, req=0.0, standing=False, cur=0.4)
    assert _obs(g, 1200.0, req=0.0, standing=False, cur=0.4) is None
    assert _obs(g, 3599.0, req=0.0, standing=False, cur=0.4) is None
    assert _obs(g, 3600.0, req=0.0, standing=False, cur=0.4) == "limp"
    assert _obs(g, 3700.0, req=0.0, standing=False, cur=0.4) is None   # once
    assert g.state["limped"] is True


def test_limp_needs_current_and_no_motion():
    g = _g()
    _obs(g, 0.0, req=0.0, standing=None, cur=0.05)
    assert _obs(g, 3600.0, req=0.0, standing=None, cur=0.05) is None    # belly-down, ~0 A: nothing to release
    moving = dict(STAND); moving[2] += 5.0
    g2 = _g(); _obs(g2, 0.0, req=0.0, standing=None, cur=0.5)
    assert _obs(g2, 3599.0, req=0.0, standing=None, cur=0.5, pos=moving) is None   # moved -> motion clock reset
    assert _obs(g2, 3600.0, req=0.0, standing=None, cur=0.5, pos=moving) is None
    assert _obs(g2, 7200.0, req=0.0, standing=None, cur=0.5, pos=moving) == "limp"


def test_sit_then_limp_when_the_sit_did_not_take_the_load_off():
    g = _g()
    _obs(g, 0.0, req=0.0, cur=0.5)
    assert _obs(g, 1200.0, req=0.0, cur=0.5) == "sit"
    assert _obs(g, 1500.0, req=0.0, cur=0.5) is None          # lockout
    assert _obs(g, 3600.0, req=0.0, cur=0.5) == "limp"        # feet pinned, still fighting: release


def test_disabled_by_zero():
    g = IdleGuard(sit_after_s=0, limp_after_s=0)
    _obs(g, 0.0, req=0.0); assert _obs(g, 1e6, req=0.0, cur=2.0) is None
    assert g.state["enabled"] is False


def test_no_request_ever_seen_uses_the_motion_clock_only_for_limp():
    g = _g()
    _obs(g, 0.0, req=None, cur=0.5)
    assert _obs(g, 5000.0, req=None, cur=0.5) is None     # never sits/limps without a request timestamp: unknown, not idle


def test_watchdog_wiring_calls_the_actions():
    import threading
    import servo_watch as sw
    from feetech_bus import N_JOINTS
    calls = []
    g = IdleGuard(sit_after_s=10, limp_after_s=20, limp_current_a=0.15, cooloff_s=5)
    w = sw.ServoWatch.__new__(sw.ServoWatch)
    w.__init__(lambda: None, lambda: False, lambda j: f"j{j}", is_armed=lambda: True,
               idle_guard=g, standing_fn=lambda present: True, rl_active_fn=lambda: False,
               last_request_fn=lambda: 995.0, on_idle_sit=lambda: calls.append("sit") or {"ok": True},
               on_idle_limp=lambda r, i: calls.append("limp"))
    w._emit = lambda *a, **k: None
    fb = {j: {"deg": [0.0, 20.0, 100.0][j % 3], "current_a": 0.05, "speed_deg_s": 0.0} for j in range(N_JOINTS)}
    import time as _t
    t = [1000.0]
    sw.time = type("T", (), {"monotonic": staticmethod(lambda: t[0]), "time": staticmethod(_t.time)})
    try:
        w._check_idle(fb); assert calls == []
        t[0] = 1010.0; w._check_idle(fb); assert calls == ["sit"] and w._idle_state["sit_result"] == {"ok": True}
        t[0] = 1030.0; w._check_idle(fb); assert calls == ["sit", "limp"]
        assert w._idle_state["limped"] is True
    finally:
        sw.time = _t


def test_standing_classifier_accepts_the_real_2026_09_27_stances():
    import api.demos as demos
    cls = [v for v in vars(demos).values() if isinstance(v, type) and hasattr(v, "_normal_standing_pose")][0]
    obj = cls.__new__(cls)
    assert obj._normal_standing_pose([0.0, 20.0, 124.0] * 6) is not None      # STEP final (robot_abs)
    assert obj._normal_standing_pose([0.0, 20.0, 101.0] * 6) is not None      # walk-ready
    assert obj._normal_standing_pose([5.6, 18.8, 107.9, -6.4, 18.2, 97.4, 3.9, 22.1, 93.0,
                                      4.0, 18.6, 105.8, -9.3, 18.1, 97.5, 3.2, 21.0, 95.2]) is not None
    assert obj._normal_standing_pose([0.0] * 18) is None                       # belly zero
