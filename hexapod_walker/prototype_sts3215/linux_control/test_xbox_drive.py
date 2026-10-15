"""Input safety mechanics without evdev, network, bus, sleeps or physical IO."""
from types import SimpleNamespace

import pytest

import xbox_drive as x


BUTTONS = {x.BTN_TL, x.BTN_TR, x.BTN_B, x.BTN_X, x.BTN_Y, x.BTN_SELECT}


def pad(*, held=(), left_y=0):
    axes = {code: x.Axis(0, -100, 100) for code in (x.ABS_X, x.ABS_Y, x.ABS_RX, x.ABS_RY)}
    axes[x.ABS_Y] = x.Axis(left_y, -100, 100)
    return x.InputGate(axes, x.ABS_RX, set(held))


def frame(gate, *, keys=None, axes=None):
    if keys is not None:
        gate.buttons = set(keys)
    for code, value in (axes or {}).items():
        gate.event(x.EV_ABS, code, value)
    return gate.event(x.EV_SYN, x.SYN_REPORT, 0)


def test_bluetooth_right_stick_is_z_when_triggers_are_brake_gas():
    codes = {x.ABS_X, x.ABS_Y, x.ABS_Z, x.ABS_RZ, x.ABS_BRAKE, x.ABS_GAS}
    assert x.choose_turn_axis(codes, BUTTONS) == x.ABS_Z
    with pytest.raises(x.ControlError, match="Unsupported right-stick"):
        x.choose_turn_axis(codes - {x.ABS_GAS}, BUTTONS)


def test_usb_right_stick_is_rx_and_unknown_layout_fails_explicitly():
    assert x.choose_turn_axis({x.ABS_X, x.ABS_Y, x.ABS_RX, x.ABS_RY, x.ABS_Z, x.ABS_RZ}, BUTTONS) == x.ABS_RX
    with pytest.raises(x.ControlError, match="controller buttons"):
        x.choose_turn_axis({x.ABS_X, x.ABS_Y, x.ABS_RX, x.ABS_RY}, BUTTONS - {x.BTN_TL})


def test_axis_center_deadzone_and_unsigned_range():
    axis = x.Axis(32768, 0, 65535, 100)
    assert axis.normalized(32768) == 0
    assert axis.normalized(0) == -1
    assert axis.normalized(65535) == 1
    with pytest.raises(x.ControlError, match="Invalid stick range"):
        x.Axis(0, 0, 0).normalized(0)


def test_connect_held_lb_never_engages_until_release_and_neutral():
    gate = pad(held={x.BTN_TL}, left_y=-100)
    assert frame(gate) == []
    assert not gate.engaged
    frame(gate, axes={x.ABS_Y: 0})
    assert not gate.engaged
    frame(gate, keys=set())
    frame(gate, keys={x.BTN_TL})
    assert gate.engaged
    frame(gate, axes={x.ABS_Y: -100, x.ABS_X: 100, x.ABS_RX: 100})
    assert gate.velocity(30, 18, .35) == (30, -18, -.35)
    assert frame(gate, keys=set()) == ["stop"]
    assert not gate.engaged


def test_non_neutral_engage_cannot_become_active_while_lb_remains_held():
    gate = pad()
    frame(gate)
    frame(gate, keys={x.BTN_TL}, axes={x.ABS_RY: 100})
    frame(gate, axes={x.ABS_RY: 0})
    assert not gate.engaged
    frame(gate, keys=set())
    frame(gate, keys={x.BTN_TL})
    assert gate.engaged


@pytest.mark.parametrize("button,action", [(x.BTN_B, "stop_all"), (x.BTN_SELECT, "limp"), (x.BTN_MODE, "limp")])
def test_stop_buttons_disable_held_deadman_and_need_fresh_release(button, action):
    gate = pad()
    frame(gate)
    frame(gate, keys={x.BTN_TL})
    assert frame(gate, keys={x.BTN_TL, button}) == [action]
    frame(gate, keys={x.BTN_TL})
    assert not gate.engaged
    frame(gate, keys=set())
    frame(gate, keys={x.BTN_TL})
    assert gate.engaged


@pytest.mark.parametrize("button,pose", [(x.BTN_Y, "stand"), (x.BTN_X, "sit")])
def test_fresh_neutral_pose_chord_runs_only_while_rb_is_held(button, pose):
    gate = pad()
    frame(gate)
    assert frame(gate, keys={x.BTN_TR, button}) == []
    assert gate.pose == pose
    assert not gate.engaged
    frame(gate, keys={x.BTN_TR})  # Face button may be released.
    assert gate.pose == pose
    assert frame(gate, keys=set()) == ["stop"]
    assert gate.pose is None


@pytest.mark.parametrize("keys,axes", [
    ({x.BTN_TL, x.BTN_TR, x.BTN_Y}, {}),
    ({x.BTN_TR, x.BTN_Y, x.BTN_X}, {}),
    ({x.BTN_TR, x.BTN_Y}, {x.ABS_Y: 100}),
])
def test_conflicting_or_non_neutral_pose_chord_cannot_start(keys, axes):
    gate = pad()
    frame(gate)
    frame(gate, keys=keys, axes=axes)
    assert gate.pose is None
    assert not gate.engaged


@pytest.mark.parametrize("keys,axes", [
    ({x.BTN_TL, x.BTN_TR}, {}),
    ({x.BTN_TR, x.BTN_X}, {}),
    ({x.BTN_TR}, {x.ABS_RX: 100}),
])
def test_pose_cancellation_latches_off_until_fresh_release(keys, axes):
    gate = pad()
    frame(gate)
    frame(gate, keys={x.BTN_TR, x.BTN_Y})
    assert frame(gate, keys=keys, axes=axes) == ["stop"]
    frame(gate, keys={x.BTN_TR, x.BTN_Y}, axes={x.ABS_RX: 0})
    assert gate.pose is None
    frame(gate, keys=set())
    frame(gate, keys={x.BTN_TR, x.BTN_Y})
    assert gate.pose == "stand"


def test_snapshot_of_held_pose_chord_never_starts_a_pose():
    gate = pad(held={x.BTN_TR, x.BTN_Y})
    frame(gate)
    assert frame(gate) == []
    assert gate.pose is None


def test_syn_dropped_stops_then_ignores_events_until_resnapshot():
    gate = pad()
    frame(gate)
    frame(gate, keys={x.BTN_TL})
    assert gate.event(x.EV_SYN, x.SYN_DROPPED, 0) == ["stop"]
    assert not gate.engaged
    assert gate.event(x.EV_KEY, x.BTN_Y, 1) == []
    with pytest.raises(x.ControlError, match="lost input events"):
        frame(gate)


class RecordingClient(x.WebClient):
    def __init__(self):
        super().__init__("http://never.invalid")
        self.sent = []
        self.reject_drive = False

    def request(self, path, body=None):
        self.sent.append((path, body))
        if self.reject_drive and isinstance(body, str) and body.startswith("JLEASE "):
            raise x.ControlError("expired lease")
        if path == "/api/gamepad/pose":
            return {"token": "a" * 32, "state": "prepared" if body["action"] == "prepare" else "running", "timeout_s": .75}
        return {"scripted_gamepad_lease": {"version": 1, "timeout_s": .75},
                "scripted_gamepad_pose": {"version": 1, "timeout_s": .75}}


def test_no_startup_command_and_no_rearm_or_calibration():
    client = RecordingClient()
    client.check_server()
    client.stop()
    assert client.sent == [("/api/ping", None)]
    client.begin()
    client.drive((0, 0, 0))
    token = client.token
    client.drive((30, 0, 0))
    assert client.sent[1:] == [
        ("/cmd", f"JLEASE BEGIN {token}"),
        ("/cmd", f"JLEASE {token} 0.000 0.000 0.0000"),
        ("/cmd", f"JLEASE {token} 30.000 0.000 0.0000")]
    client.stop()
    assert client.sent[-1] == ("/cmd", f"JLEASE STOP {token}")
    assert client.token is None


def test_uncertain_begin_remembers_token_for_stop_and_does_not_retry():
    client = RecordingClient()
    client.reject_drive = True
    with pytest.raises(x.ControlError, match="expired"):
        client.begin()
    token = client.token
    assert token
    client.reject_drive = False
    client.stop()
    assert client.sent[-1] == ("/cmd", f"JLEASE STOP {token}")


def test_dry_run_never_touches_network_including_stop_and_emergency(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("dry run touched the network")
    monkeypatch.setattr(x.urllib.request, "urlopen", forbidden)
    client = x.WebClient("http://never.invalid", dry_run=True)
    client.check_server()
    client.begin()
    client.drive((10, 0, 0))
    client.action("stop_all")
    client.prepare_pose("stand")
    assert client.renew_pose() == "running"
    client.action("stop_all")
    client.action("limp")


def test_pose_stop_cancels_own_reservation_without_global_demo_stop():
    client = RecordingClient()
    client.prepare_pose("sit")
    token = client.pose_token
    assert client.sent == [("/api/gamepad/pose", {"action": "prepare", "pose": "sit"})]
    client.renew_pose()
    client.stop(explicit=True)
    assert client.sent[-2:] == [
        ("/api/gamepad/pose", {"action": "renew", "token": token}),
        ("/api/gamepad/pose", {"action": "stop", "token": token})]
    assert client.pose_token is None


def test_old_server_cannot_drive_without_pose_watchdog(monkeypatch):
    client = x.WebClient("http://never.invalid")
    monkeypatch.setattr(client, "request", lambda *args: {"scripted_gamepad_lease": {"version": 1, "timeout_s": .75}})
    with pytest.raises(x.ControlError, match="leased gamepad stand/sit"):
        client.check_server()


def test_missing_watchdog_refuses_before_any_motion(monkeypatch):
    client = x.WebClient("http://never.invalid")
    monkeypatch.setattr(client, "request", lambda *args: {"ok": True})
    with pytest.raises(x.ControlError, match="deploy matching"):
        client.check_server()


def test_explicit_stop_and_emergency_use_canonical_web_handlers():
    client = RecordingClient()
    client.action("stop_all")
    assert client.sent == [("/api/demo/stop", {}), ("/cmd", "J 0 0 0")]
    client.action("limp")
    assert client.sent[-1] == ("/cmd", "X")


def packed(*events, seconds=1):
    return b"".join(x.EVENT.pack(seconds, 0, typ, code, value) for typ, code, value in events)


@pytest.fixture
def input_loop(monkeypatch):
    def run(*polls, ticks=None, raises=OSError, match="end test"):
        """Each poll contains read chunks, drained to EAGAIN before the next poll."""
        polls = iter(polls)
        pending = iter(())

        def select(*args):
            nonlocal pending
            try:
                chunks = next(polls)
            except StopIteration:
                raise OSError("end test") from None
            pending = iter(chunks)
            return ([123] if chunks else [], [], [])

        def read(*args):
            try:
                return next(pending)
            except StopIteration:
                raise BlockingIOError from None

        clock = iter(ticks) if ticks is not None else None
        monkeypatch.setattr(x.time, "monotonic", lambda: next(clock) if clock is not None else 1)
        monkeypatch.setattr(x.select, "select", select)
        monkeypatch.setattr(x.os, "read", read)
        client = RecordingClient()
        device = SimpleNamespace(fd=123, axes=pad().axes, turn_axis=x.ABS_RX, buttons=set())
        with pytest.raises(raises, match=match):
            x.run_device(device, client, SimpleNamespace(max_vx=30, max_vy=18, max_omega=.35))
        return client
    return run


def test_input_loop_stall_cannot_send_another_heartbeat(input_loop):
    client = input_loop([], ticks=[0, 1], raises=x.ControlError, match="stalled")
    assert client.sent == []


def test_release_beyond_first_64_queued_events_prevents_any_drive(input_loop):
    events = [(x.EV_KEY, x.BTN_TL, 1), (x.EV_SYN, x.SYN_REPORT, 0)]
    events += [(x.EV_ABS, x.ABS_Y, -100), (x.EV_SYN, x.SYN_REPORT, 0)] * 31
    assert len(events) == 64
    release = packed((x.EV_KEY, x.BTN_TL, 0), (x.EV_SYN, x.SYN_REPORT, 0))
    client = input_loop([packed(*events), release])
    assert client.sent == []


def test_release_during_begin_is_drained_before_first_velocity(input_loop):
    press = packed((x.EV_KEY, x.BTN_TL, 1), (x.EV_SYN, x.SYN_REPORT, 0))
    release = packed((x.EV_KEY, x.BTN_TL, 0), (x.EV_SYN, x.SYN_REPORT, 0))
    client = input_loop([press], [release])
    assert len(client.sent) == 2
    assert client.sent[0][1].startswith("JLEASE BEGIN ")
    assert client.sent[1][1].startswith("JLEASE STOP ")


def test_release_during_pose_preparation_prevents_worker_start(input_loop):
    press = packed((x.EV_KEY, x.BTN_TR, 1), (x.EV_KEY, x.BTN_Y, 1), (x.EV_SYN, x.SYN_REPORT, 0))
    release = packed((x.EV_KEY, x.BTN_TR, 0), (x.EV_SYN, x.SYN_REPORT, 0))
    client = input_loop([press], [release])
    assert [body["action"] for _, body in client.sent] == ["prepare", "stop"]


def test_old_kernel_timestamp_stops_and_demands_resnapshot(monkeypatch):
    client = RecordingClient()
    gate = pad()
    frame(gate)
    frame(gate, keys={x.BTN_TL})
    monkeypatch.setattr(x.time, "monotonic", lambda: 2)
    monkeypatch.setattr(x.os, "read", lambda *args: packed((x.EV_ABS, x.ABS_Y, -100), seconds=1))
    with pytest.raises(x.ControlError, match="Stale gamepad"):
        x.drain_input(SimpleNamespace(fd=123), gate, client)
    assert not gate.engaged
    assert client.sent == []
