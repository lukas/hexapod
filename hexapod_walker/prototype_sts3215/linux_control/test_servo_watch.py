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
