from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from rl_move.env import TaskGoal
from rl_move.sim import web_session as sim_ws


def _bare_drive_session():
    session = sim_ws.SimWebSession.__new__(sim_ws.SimWebSession)
    session.lock = threading.RLock()
    session.drive_active = True
    session.last_drive_cmd_at = 100.0
    session.drive_zero_since = None
    session.drive_last_vx = 0.0
    session.drive_last_vy = 0.0
    session.drive_last_wz = 0.0
    session.traj = SimpleNamespace(
        vx=0.05,
        vy=0.0,
        goal=TaskGoal(),
        _pub=TaskGoal(),
    )
    session.om_cmd = 0.0
    session.mode = "walk"
    session.msg = "drive session active"
    session.auto = None
    session.downed = False
    session.sitting = False
    session.pose_hold_q = None
    session._record_command = lambda *args, **kwargs: None
    session._engage_walk = lambda: True
    session._drive_band = lambda: (0.05, 0.06)
    session._live = lambda: {
        "status": session.msg,
        "vx_ref": round(float(session.traj.vx), 4),
        "vy_ref": round(float(session.traj.vy), 4),
        "wz_ref": round(float(session.om_cmd), 4),
        "walk_zero_dwell_s": round(
            session._drive_zero_dwell_remaining(), 2),
    }
    return session


def test_sim_drive_neutral_dwell_keeps_last_walk_ref(monkeypatch):
    session = _bare_drive_session()
    now = [100.0]
    monkeypatch.setattr(sim_ws.time, "monotonic", lambda: now[0])

    out = session.rl_drive_cmd(0.0, 0.0)
    assert out["active"] is True
    assert session.traj.vx == pytest.approx(0.05)
    assert session.traj.vy == pytest.approx(0.0)
    assert session.drive_zero_since == pytest.approx(100.0)
    assert out["live"]["walk_zero_dwell_s"] == pytest.approx(1.5)

    now[0] += sim_ws._DRIVE_HOLD_SWITCH_S - 0.01
    session.rl_drive_cmd(0.0, 0.0)
    assert session.traj.vx == pytest.approx(0.05)
    assert session.traj.vy == pytest.approx(0.0)

    now[0] += 0.02
    session.rl_drive_cmd(0.0, 0.0)
    assert session.traj.vx == pytest.approx(0.0)
    assert session.traj.vy == pytest.approx(0.0)
    assert session.om_cmd == pytest.approx(0.0)
    assert session.drive_zero_since == pytest.approx(100.0)


def test_sim_drive_moving_command_clears_neutral_dwell(monkeypatch):
    session = _bare_drive_session()
    session.drive_zero_since = 99.0
    session.traj.vx = 0.0
    session.traj.vy = 0.0
    now = [100.0]
    monkeypatch.setattr(sim_ws.time, "monotonic", lambda: now[0])

    session.rl_drive_cmd(0.03, 0.04, wz=0.1)

    assert session.drive_zero_since is None
    assert session.traj.vx == pytest.approx(0.03)
    assert session.traj.vy == pytest.approx(0.04)
    assert session.om_cmd == pytest.approx(0.1)
    assert session.drive_last_vx == pytest.approx(0.03)
    assert session.drive_last_vy == pytest.approx(0.04)
    assert session.drive_last_wz == pytest.approx(0.1)
