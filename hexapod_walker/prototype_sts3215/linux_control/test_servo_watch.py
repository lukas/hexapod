from __future__ import annotations


import servo_watch


class _Bus:
    def __init__(self) -> None:
        self.temperature_c = 32
        self.torque_calls: list[tuple[int, bool]] = []

    def read_all_feedback(self):
        return {
            joint: {"temp_c": self.temperature_c}
            for joint in range(18)
        }

    def torque(self, servo_id: int, enabled: bool) -> None:
        self.torque_calls.append((servo_id, enabled))


def test_servo_watch_requires_three_consecutive_hot_reads(monkeypatch):
    bus = _Bus()
    trips: list[str] = []
    watch = servo_watch.ServoWatch(
        lambda: bus, lambda: False, lambda joint: f"joint {joint}", trips.append
    )
    monkeypatch.setattr(watch, "_emit", lambda *_args, **_kwargs: None)

    bus.temperature_c = 83
    watch._tick()
    bus.temperature_c = 102
    watch._tick()
    assert bus.torque_calls == []
    assert watch.state()["tripped"] == []

    # A cool read resets the sequence; two later hot reads still do not trip.
    bus.temperature_c = 34
    watch._tick()
    bus.temperature_c = 70
    watch._tick()
    watch._tick()
    assert bus.torque_calls == []

    watch._tick()
    assert len(bus.torque_calls) == 18
    assert watch.state()["tripped"] == list(range(18))
    assert len(trips) == 18


class _StrainBus:
    """Scripted per-joint current/speed for the static-strain watchdog."""

    def __init__(self) -> None:
        self.current_a = 0.0
        self.speed_deg_s = 0.0

    def read_all_feedback(self):
        return {j: {"temp_c": 33, "current_a": self.current_a, "speed_deg_s": self.speed_deg_s}
                for j in range(18)}

    def torque(self, servo_id: int, enabled: bool) -> None:
        pass


def _strain_watch(bus, *, armed=True, busy=False):
    calls: list[tuple[str, dict]] = []
    w = servo_watch.ServoWatch(lambda: bus, lambda: busy, lambda j: f"joint {j}", None,
                               is_armed=lambda: armed, on_strain=lambda r, i: calls.append((r, i)))
    w._emit = lambda *a, **k: None
    return w, calls


def test_static_strain_releases_after_two_still_reads_and_latches():
    """2026-09-22: 18 servos at ~0.2 A each (3.6 A total), armed, idle, not moving = a fight."""
    bus = _StrainBus(); w, calls = _strain_watch(bus)
    bus.current_a = 0.2
    w._tick(); assert calls == [] and w.state()["strain"]["reads"] == 1
    w._tick(); assert len(calls) == 1
    assert "3.60 A total" in calls[0][0]
    w._tick(); assert len(calls) == 1, "latched: one release per strain episode"
    bus.current_a = 0.0
    w._tick(); assert w.state()["strain"]["released"] is False, "calm reading re-arms the watchdog"


def test_static_strain_ignores_motion_jobs_and_unarmed():
    bus = _StrainBus(); bus.current_a = 0.3
    # moving servos draw current legitimately
    bus.speed_deg_s = 40.0
    w, calls = _strain_watch(bus); w._tick(); w._tick(); assert calls == []
    # a running job owns the bus: not the watchdog's call
    bus.speed_deg_s = 0.0
    w, calls = _strain_watch(bus, busy=True); w._tick(); w._tick(); assert calls == []
    # torque already off: nothing to release
    w, calls = _strain_watch(bus, armed=False); w._tick(); w._tick(); assert calls == []


def test_static_strain_single_hot_servo_and_corrupt_reading():
    bus = _StrainBus(); w, calls = _strain_watch(bus)
    fb = {j: {"temp_c": 33, "current_a": 0.0, "speed_deg_s": 0.0} for j in range(18)}
    fb[7]["current_a"] = 0.9                       # one servo fighting
    fb[3]["current_a"] = 106.5                     # the 0x4000 bit-flip: excluded, not summed
    bus.read_all_feedback = lambda: fb
    w._tick(); w._tick()
    assert len(calls) == 1 and "joint 7 0.90 A" in calls[0][0]
    assert calls[0][1]["total_a"] == 0.9
