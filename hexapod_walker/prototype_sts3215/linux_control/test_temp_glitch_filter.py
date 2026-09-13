"""The bus holds back an isolated servo-temperature jump until a second read agrees."""
from __future__ import annotations

import mcu_feetech_bus
from mcu_feetech_bus import McuFeetechBus


def _bus():
    return McuFeetechBus.__new__(McuFeetechBus)


def _fb(sid: int, temp: int) -> dict:
    return {"id": sid, "joint": sid - 2, "temp_c": temp}


def _run(bus, temps, dt=0.0):
    out = []
    for t in temps:
        fb = _fb(5, t)
        bus._filter_temp(fb)
        out.append(fb["temp_c"])
        if dt:
            mcu_feetech_bus.time.monotonic.advance(dt)
    return out


class _Clock:
    def __init__(self, t=100.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def test_first_reading_is_taken_as_is():
    assert _run(_bus(), [30]) == [30]


def test_isolated_jump_is_replaced_and_raw_kept():
    bus = _bus()
    assert _run(bus, [30, 30, 61, 30, 30]) == [30, 30, 30, 30, 30]
    fb = _fb(5, 57)
    bus._filter_temp(fb)
    assert fb["temp_c"] == 30 and fb["temp_raw_c"] == 57


def test_a_jump_read_twice_in_a_row_is_still_held(monkeypatch):
    # The MCU refreshes at ~10 Hz and the host polls at 10 Hz: one bad pass is often read twice.
    monkeypatch.setattr(mcu_feetech_bus.time, "monotonic", _Clock())
    assert _run(_bus(), [30, 108, 108, 108, 30, 30], dt=0.1) == [30, 30, 30, 30, 30, 30]


def test_a_jump_that_lasts_a_second_is_accepted(monkeypatch):
    monkeypatch.setattr(mcu_feetech_bus.time, "monotonic", _Clock())
    out = _run(_bus(), [30] + [45] * 12 + [46], dt=0.1)
    assert out[:2] == [30, 30] and out[-2:] == [45, 46] and 45 in out
    assert 11 <= out.index(45) <= 12                    # held for about a second of agreeing reads


def test_slow_heating_passes_untouched(monkeypatch):
    monkeypatch.setattr(mcu_feetech_bus.time, "monotonic", _Clock())
    temps = list(range(30, 60, 2))
    assert _run(_bus(), temps, dt=0.5) == temps


def test_stale_state_is_dropped(monkeypatch):
    bus = _bus()
    clock = _Clock()
    monkeypatch.setattr(mcu_feetech_bus.time, "monotonic", clock)
    _run(bus, [30])
    clock.advance(10.0)
    assert _run(bus, [52]) == [52]


def test_servos_are_filtered_independently():
    bus = _bus()
    for sid, t in ((2, 30), (3, 45)):
        bus._filter_temp(_fb(sid, t))
    a, b = _fb(2, 45), _fb(3, 45)
    bus._filter_temp(a)
    bus._filter_temp(b)
    assert a["temp_c"] == 30 and b["temp_c"] == 45


def test_read_all_feedback_applies_the_filter():
    import struct
    import threading

    bus = _bus()
    bus._lock = threading.Lock()
    bus._fb_cache, bus._fb_cache_mono = {}, 0.0
    bus._pos_cache, bus._pos_cache_mono = {}, 0.0
    bus.trims = [0.0] * mcu_feetech_bus.N_JOINTS

    def rec(temp):
        return bytes([5, 1]) + struct.pack("<hhH", 2048, 0, 0) + bytes([112, temp, 0]) + struct.pack("<h", 10)

    replies = [rec(30), rec(61), rec(30)]
    bus._bin_req = lambda cmd, ids, timeout=1.5: (1, replies.pop(0))
    seen = [bus.read_all_feedback()[3]["temp_c"] for _ in range(3)]
    assert seen == [30, 30, 30]
