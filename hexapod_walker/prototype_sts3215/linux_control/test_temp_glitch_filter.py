"""The bus holds back an isolated servo-temperature jump until a second read agrees."""
from __future__ import annotations

import mcu_feetech_bus
from mcu_feetech_bus import McuFeetechBus


def _bus():
    return McuFeetechBus.__new__(McuFeetechBus)


def _fb(sid: int, temp: int) -> dict:
    return {"id": sid, "joint": sid - 2, "temp_c": temp}


def _run(bus, temps):
    out = []
    for t in temps:
        fb = _fb(5, t)
        bus._filter_temp(fb)
        out.append(fb["temp_c"])
    return out


def test_first_reading_is_taken_as_is():
    assert _run(_bus(), [30]) == [30]


def test_isolated_jump_is_replaced_and_raw_kept():
    bus = _bus()
    assert _run(bus, [30, 30, 61, 30, 30]) == [30, 30, 30, 30, 30]
    fb = _fb(5, 57)
    bus._filter_temp(fb)
    assert fb["temp_c"] == 30 and fb["temp_raw_c"] == 57


def test_sustained_jump_is_accepted_on_second_read():
    assert _run(_bus(), [30, 45, 45, 46]) == [30, 30, 45, 46]


def test_slow_heating_passes_untouched():
    temps = list(range(30, 60, 2))
    assert _run(_bus(), temps) == temps


def test_stale_state_is_dropped(monkeypatch):
    bus = _bus()
    clock = {"t": 100.0}
    monkeypatch.setattr(mcu_feetech_bus.time, "monotonic", lambda: clock["t"])
    _run(bus, [30])
    clock["t"] += 10.0
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
