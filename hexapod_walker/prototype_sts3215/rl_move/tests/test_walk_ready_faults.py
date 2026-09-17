"""Recorded Walk Ready failure: stop the load before reporting a fault."""
import threading
from types import SimpleNamespace

import pytest

import api.demos as demos
import inplace_demos
from api.zero import ZeroApi
from hexapod_core.joint_frame import walk_start_pose_degrees


@pytest.fixture
def rig(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(demos, 'time', SimpleNamespace(
        monotonic=lambda: now[0], sleep=lambda dt: now.__setitem__(0, now[0] + dt)))
    target = walk_start_pose_degrees()
    state = SimpleNamespace(currents=[], reads=0, writes=[], limps=0, holds=0)

    def feedback():
        i = state.reads
        state.reads += 1
        amps = state.currents[min(i, len(state.currents)-1)] if state.currents else {}
        return {j: {'joint': j, 'deg': target[j], 'current_a': amps.get(j, .1)}
                for j in range(18)}

    bus = SimpleNamespace(trims=None, read_all_feedback=feedback)
    api = demos.DemosApi()
    api.names = {}
    api.drive = SimpleNamespace(bus=bus, armed=True, _lock=threading.RLock())
    api._present_pose18 = lambda: (target.copy(), [])
    api._pose_delta = lambda *args: 0.
    monkeypatch.setattr(inplace_demos, '_live_robot_ids', lambda bus: set(range(2,20)))
    for name in ('_set_torque_limit', '_enable_torque'):
        monkeypatch.setattr(inplace_demos, name, lambda *args, **kw: None)
    monkeypatch.setattr(inplace_demos, '_write_pose',
                        lambda bus,q,*args,**kw: state.writes.append(q))
    monkeypatch.setattr(inplace_demos, '_limp_all',
                        lambda *args: setattr(state, 'limps', state.limps+1))
    monkeypatch.setattr(inplace_demos, '_hold_here',
                        lambda *args: setattr(state, 'holds', state.holds+1))
    return api, state


@pytest.mark.parametrize('currents,trip', [
    ([{2:4.96},{},{}], False),
    ([{2:4.96},{2:4.96},{},{}], False),
    ([{2:4.96},{5:4.96},{8:4.96},{}], False),
    ([{2:4.96}]*3, True),
])
def test_current_trip_needs_three_fresh_samples_on_same_motor(rig,currents,trip):
    api,state=rig
    state.currents=currents
    result=api._step_to_rl_walk_ready_start_sync(abort_check=lambda:False)
    assert result['ok'] is not trip
    assert state.limps == int(trip)
    if trip:
        assert state.reads == 3
        assert not api.drive.armed
        assert result['limp']
        assert 'current trip' in result['error']


def test_final_verification_cannot_borrow_old_tracker_feedback(rig):
    api,state=rig
    calls=[0]
    def positions():
        calls[0]+=1
        if calls[0]==1:
            return walk_start_pose_degrees(),[]
        return [None]*18,list(range(18))
    api._present_pose18=positions
    result=api._step_to_rl_walk_ready_start_sync(abort_check=lambda:False)
    assert not result['ok'] and result['limp']
    assert calls[0]==4 and state.limps==1


def test_operator_abort_holds_instead_of_leaving_destination_active(rig):
    api,state=rig
    result=api._step_to_rl_walk_ready_start_sync(abort_check=lambda:True)
    assert result['aborted'] and not result['limp']
    assert state.holds==1 and state.limps==0


def test_acquisition_preserves_fault_result():
    api=ZeroApi()
    api.drive=SimpleNamespace()
    api._demo_abort=threading.Event()
    api._present_pose18=lambda:(walk_start_pose_degrees(),[])
    api._normal_standing_pose=lambda q:True
    fault={'ok':False,'limp':True,'error':'current trip','peak_a':4.96}
    api._step_to_rl_walk_ready_start_sync=lambda **kw:fault
    result=api._acquire_start('stand',gen=1)
    assert result['limp'] and result['peak_a']==4.96


def test_bulk_feedback_never_falls_back_to_cached_per_joint_reads():
    def stale(_joint):
        pytest.fail('an empty fresh sweep must not be filled from older reads')
    tracker=inplace_demos.CurrentPeakTracker()
    tracker.sample(SimpleNamespace(read_all_feedback=lambda:None, read_feedback=stale),
                   set(range(2,20)))
    assert tracker.last_fb==[]


def test_rl_stand_worker_defers_torque_to_acquisition(monkeypatch):
    from api.rl import RlApi
    api=RlApi()
    def unsafe(_enabled):
        pytest.fail('worker enabled old servo targets before start acquisition')
    api.drive=SimpleNamespace(dry_run=False,bus=object(),armed=False,
                              mode='idle',_lock=threading.RLock(),_torque_all=unsafe)
    api._lock=threading.RLock()
    api._demo_abort=threading.Event()
    api._demo_gen=0
    api._demo_thread=None
    api._bus_admission_error=lambda:None
    api._bus_hot_begin=api._bus_hot_end=lambda:None
    api._set_activity=lambda *args:None
    api._acquire_start=lambda *args,**kw:{'ok':False,'error':'preflight refused'}
    api.calibrate_state=api.robot_state=lambda:{}
    api._rl_walk_ready_stand()
    api._demo_thread.join(timeout=1)
    assert not api._demo_thread.is_alive()
    assert api._cal_result['error']=='preflight refused'
    assert not api.drive.armed
