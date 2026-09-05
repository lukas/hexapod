from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest
import numpy as np

from rl_move.env import TaskGoal
from rl_move.sim import web_session as sim_ws


def _bare_drive_session():
    session = sim_ws.SimWebSession.__new__(sim_ws.SimWebSession)
    session.lock = threading.RLock()
    session.drive_active = True
    session.last_drive_cmd_at = 100.0
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
    }
    return session


@pytest.mark.parametrize("vx,vy,wz", [(0.05, 0.0, 0.0),
                                       (0.03, 0.04, 0.1),
                                       (0.0, 0.0, -0.1)])
def test_sim_drive_neutral_clears_all_refs_on_first_call(monkeypatch, vx, vy, wz):
    session = _bare_drive_session()
    session.traj.vx, session.traj.vy, session.om_cmd = vx, vy, wz
    now = [100.0]
    monkeypatch.setattr(sim_ws.time, "monotonic", lambda: now[0])

    out = session.rl_drive_cmd(0.0, 0.0)
    assert out["active"] is True
    assert out["live"]["vx_ref"] == 0.0
    assert out["live"]["vy_ref"] == 0.0
    assert out["live"]["wz_ref"] == 0.0
    assert session.traj.vx == pytest.approx(0.0)
    assert session.traj.vy == pytest.approx(0.0)
    assert session.om_cmd == pytest.approx(0.0)


def test_sim_drive_reengages_on_next_command_after_neutral(monkeypatch):
    session = _bare_drive_session()
    now = [100.0]
    monkeypatch.setattr(sim_ws.time, "monotonic", lambda: now[0])

    session.rl_drive_cmd(0.0, 0.0)
    assert session.traj.vx == 0.0
    now[0] += 0.01
    session.rl_drive_cmd(0.03, 0.04, wz=0.1)

    assert session.traj.vx == pytest.approx(0.03)
    assert session.traj.vy == pytest.approx(0.04)
    assert session.om_cmd == pytest.approx(0.1)


@pytest.mark.parametrize("heartbeat_expired", [False, True])
def test_sim_next_tick_selects_hold_after_neutral_or_stale_heartbeat(
        monkeypatch, heartbeat_expired):
    session = _bare_drive_session()
    now = [100.0]
    monkeypatch.setattr(sim_ws.time, "monotonic", lambda: now[0])
    if heartbeat_expired:
        now[0] += sim_ws._DRIVE_HEARTBEAT_STALE_S + 0.01
    else:
        session.rl_drive_cmd(0.0, 0.0)
    session._apply_servo_regime = lambda: None
    session._demo_running = lambda: False
    session.timed_walk_until = None
    session.walk = object()
    session.push_ticks = 0
    session.chassis_bid = 0
    session.env = SimpleNamespace(data=SimpleNamespace(
        xfrc_applied=np.zeros((1, 6))))

    class SelectedPolicy(Exception):
        pass

    def select(role):
        raise SelectedPolicy(role)

    session._stance_action = select
    session._walk_predict = lambda: select("walk")
    # Stop after policy dispatch, before any physics or rendering work.
    with pytest.raises(SelectedPolicy, match="^hold$"):
        session._tick_locked()
    assert session.mode == session.traj.mode == "hold"
    assert session.traj.vx == session.traj.vy == session.om_cmd == 0.0
