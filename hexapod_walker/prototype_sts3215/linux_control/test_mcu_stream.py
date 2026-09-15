"""Off-robot tests for the MCU stream-bridge codec (2026-08-19 upgrade).

Run locally:  uv run pytest linux_control/test_mcu_stream.py -q
No hardware: a FakeSerial plays the firmware side of the 'S'/'s'
combined write+snapshot transaction, byte-exact against the framing in
firmware/feetech_bridge (sendSnapshot / feedHostByte).
"""
from __future__ import annotations

import struct
import threading
from unittest.mock import patch


from feetech_bus import (N_JOINTS, count_to_deg, deg_to_count,
                         joint_to_servo_id, speed_counts_to_deg_s)
import pytest

import mcu_feetech_bus
from mcu_feetech_bus import (SNAP_AGE_INVALID, SNAP_HEAD_LEN, SNAP_REC_LEN,
                             STREAM_HANDSHAKE_ATTEMPTS, SYNC_WRITE_ATTEMPTS,
                             McuBridgeError, McuFeetechBus, McuFirmwareError,
                             encode_sync_frame, parse_snapshot_payload)


# ---------------------------------------------------------------------------
# Unit conversion — the "wrong speed units" fix
# ---------------------------------------------------------------------------

def test_speed_counts_to_deg_s():
    # STS3215: counts/s, 4096/rev. 400 counts/s (the rl write_speed cap)
    # is ~35 deg/s — NOT the 0.732 rpm/unit SCS decode (which said 1757).
    assert abs(speed_counts_to_deg_s(400) - 35.15625) < 1e-9
    assert abs(speed_counts_to_deg_s(4096) - 360.0) < 1e-9
    assert speed_counts_to_deg_s(-100) == -speed_counts_to_deg_s(100)
    # The old bug was a ~50x inflation (49.97).
    assert abs((0.732 * 6.0) / (360.0 / 4096.0) - 50.0) < 0.05


# ---------------------------------------------------------------------------
# Frame encode (host -> MCU), matches firmware feedHostByte's reader
# ---------------------------------------------------------------------------

def _xor(data: bytes) -> int:
    x = 0
    for b in data:
        x ^= b
    return x


def test_encode_sync_frame_layout():
    items = [(2, 2048, 400, 20), (3, -12, 65535, 255)]
    frame = encode_sync_frame(ord("S"), items)
    assert frame[:2] == b"\xa5\x5a"
    assert frame[2] == ord("S")
    assert frame[3] == 2
    assert len(frame) == 4 + 2 * 6 + 1
    # Checksum covers cmd, n and the records (firmware binXor).
    assert frame[-1] == _xor(frame[2:-1])
    sid, pos, spd, acc = struct.unpack_from("<BhHB", frame, 4)
    assert (sid, pos, spd, acc) == (2, 2048, 400, 20)
    sid, pos, spd, acc = struct.unpack_from("<BhHB", frame, 10)
    assert (sid, pos, spd, acc) == (3, -12, 65535, 255)


def test_encode_snapshot_query():
    # n=0 'S' = read-only snapshot (positions+speed+IMU, no write).
    frame = encode_sync_frame(ord("S"), [])
    assert frame == bytes([0xA5, 0x5A, ord("S"), 0, ord("S") ^ 0])


# ---------------------------------------------------------------------------
# Snapshot decode (MCU -> host), byte-exact vs firmware sendSnapshot
# ---------------------------------------------------------------------------

def _fw_snapshot_payload(seq, pos_age, imu_age, imu_raw, servos) -> bytes:
    payload = struct.pack("<HHH", seq, pos_age, imu_age)
    payload += struct.pack("<7h", *imu_raw)
    for sid, ok, pos, spd in servos:
        payload += struct.pack("<BBhh", sid, ok, pos, spd)
    return payload


def _fw_snapshot_frame(payload: bytes, n: int) -> bytes:
    body = bytes([ord("s"), n]) + payload
    return bytes([0xA5, 0x5A]) + body + bytes([_xor(body)])


def test_parse_snapshot_payload():
    imu_raw = (100, -200, 16384, -5, 6, -7, 1234)
    servos = [(2 + j, 1, 2048 + j, -30 + j) for j in range(18)]
    payload = _fw_snapshot_payload(7, 3, 2, imu_raw, servos)
    assert len(payload) == SNAP_HEAD_LEN + 18 * SNAP_REC_LEN
    snap = parse_snapshot_payload(18, payload)
    assert snap["seq"] == 7
    assert snap["pos_age_ms"] == 3
    assert snap["imu_age_ms"] == 2
    assert snap["imu_raw"] == imu_raw
    assert len(snap["servos"]) == 18
    assert snap["servos"][0] == {"id": 2, "ok": True,
                                 "pos_counts": 2048, "spd_counts_s": -30}
    assert snap["servos"][17]["spd_counts_s"] == -13


# ---------------------------------------------------------------------------
# Full step_all transaction against a fake firmware
# ---------------------------------------------------------------------------

class FakeSerial:
    def __init__(self, reply: bytes):
        self._rx = bytearray(reply)
        self.tx = bytearray()

    def read(self, n: int = 1) -> bytes:
        out = bytes(self._rx[:n])
        del self._rx[:n]
        return out

    def write(self, data) -> None:
        self.tx += bytes(data)

    def flush(self) -> None:
        pass

    def reset_input_buffer(self) -> None:
        pass


def _mk_bus(reply: bytes) -> McuFeetechBus:
    bus = McuFeetechBus.__new__(McuFeetechBus)
    bus._ser = FakeSerial(reply)
    bus._lock = threading.Lock()
    bus.trims = [0.0] * N_JOINTS
    bus._pos_cache = {}
    bus._pos_cache_mono = 0.0
    bus._fb_cache = {}
    bus._fb_cache_mono = 0.0
    bus._live_cache = None
    bus._live_cache_t = 0.0
    bus._imu_calib = None
    bus._imu_mount = "normal"
    bus.streaming = True
    bus.sync_write_retries = 0
    bus.imu_wake_attempts = 0
    bus._imu_wake_mono = 0.0
    return bus


def _timed_bus(reply: bytes, clock: list[float]) -> McuFeetechBus:
    class TimedSerial(FakeSerial):
        def reset_input_buffer(self):
            clock[0] += 0.003

        def write(self, data):
            clock[0] += 0.007
            super().write(data)

        def flush(self):
            clock[0] += 0.053

        def read(self, n=1):
            clock[0] += 0.011
            return super().read(n)

    class TimedLock:
        def __enter__(self):
            clock[0] += 0.021

        def __exit__(self, *_args):
            pass

    bus = _mk_bus(reply)
    bus._ser = TimedSerial(reply)
    bus._lock = TimedLock()
    return bus


def test_snapshot_trace_separates_lock_write_flush_and_reply():
    clock = [10.0]
    payload = _fw_snapshot_payload(7, 3, 2, (0, 0, 16384, 0, 0, 0, 0),
                                   [(2 + j, 1, 2048, 0) for j in range(18)])
    bus = _timed_bus(_fw_snapshot_frame(payload, 18), clock)
    with patch("mcu_feetech_bus.time.monotonic", lambda: clock[0]):
        snap = bus.read_snapshot()

    assert snap is not None and snap["seq"] == 7
    assert bytes(bus._ser.tx) == encode_sync_frame(ord("S"), [])
    trace, = bus.debug_events()
    assert trace["ok"] is True
    assert trace["lock_wait_ms"] == 21.0
    assert trace["reset_input_ms"] == 3.0
    assert trace["serial_write_ms"] == 7.0
    assert trace["serial_flush_ms"] == 53.0
    assert trace["write_flush_ms"] == 63.0
    assert trace["first_byte_wait_ms"] == 11.0


def test_sync_write_trace_preserves_ack_and_retry():
    clock = [10.0]
    bus = _timed_bus(b"ERR\nOK\n", clock)
    items = [(2, 2048, 400, 20)]
    bus._pending = list(items)
    with patch("mcu_feetech_bus.time.monotonic", lambda: clock[0]):
        bus._flush_sync()

    assert bytes(bus._ser.tx) == encode_sync_frame(ord("W"), items) * 2
    first, second = bus.debug_events()
    assert first["ok"] is False and first["reason"] == "ack_rejected"
    assert first["attempt"] == 1 and first["reply"] == "ERR"
    assert second["ok"] is True and "reason" not in second
    assert second["attempt"] == 2 and second["reply"] == "OK"
    for trace in (first, second):
        assert trace["cmd"] == "W" and trace["want"] == "OK"
        assert trace["lock_wait_ms"] == 21.0
        assert trace["reset_input_ms"] == 3.0
        assert trace["serial_write_ms"] == 7.0
        assert trace["serial_flush_ms"] == 53.0
        assert trace["write_flush_ms"] == 63.0
    assert first["ack_wait_ms"] == 44.0
    assert second["ack_wait_ms"] == 33.0
    # The bounded re-send is counted so it can never be a quiet habit.
    assert bus.sync_write_retries == 1


class SnapshotSink:
    def __init__(self):
        self.offered = []

    def wants_snapshot(self):
        return True

    def __call__(self, kind, payload):
        self.offered.append((kind, payload))


def _scan_reply(ids: list[int]) -> bytes:
    return ("OK " + ",".join(str(sid) for sid in ids) + "\n").encode("ascii")


def test_scan_empty_reply_does_not_poison_live_cache():
    bus = _mk_bus(_scan_reply([2, 3, 4]) + b"OK \n" + _scan_reply([2, 3, 4]))

    assert bus.scan(range(2, 20)) == [2, 3, 4]
    bus._live_cache_t = -10.0

    assert bus.scan(range(2, 20)) == []
    assert bus._live_cache == [2, 3, 4]

    assert bus.scan(range(2, 20)) == [2, 3, 4]


def test_scan_reports_transport_errors_separately_from_empty_bus():
    for reply in (None, 'ERR busy', 'OK garbage'):
        bus = _mk_bus(b'')
        bus._transact = lambda *args, **kwargs: reply
        assert bus.scan() == []
        assert bus.last_scan_error
        bus._transact = lambda *args, **kwargs: 'OK '
        assert bus.scan() == []
        assert bus.last_scan_error is None


def test_step_all_round_trip():
    imu_raw = (0, 0, 16384, 131, -131, 0, 0)   # flat, 1 g, ±1 dps
    servos = [(2 + j, 1, 2048 + 10 * j, 40) for j in range(18)]
    reply = _fw_snapshot_frame(
        _fw_snapshot_payload(42, 4, 1, imu_raw, servos), 18)
    bus = _mk_bus(reply)

    degrees = [float(j) for j in range(N_JOINTS)]
    snap = bus.step_all(degrees, speed=400, acc=20)
    assert snap is not None

    # The API tibia is absolute; the physical knee hinge is tibia minus hip.
    want_raw = [d - degrees[j - 1] if j % 3 == 2 else d
                for j, d in enumerate(degrees)]
    want_items = [(joint_to_servo_id(j), deg_to_count(j, want_raw[j], 0.0),
                   400, 20) for j in range(N_JOINTS)]
    assert bytes(bus._ser.tx) == encode_sync_frame(ord("S"), want_items)

    # RX side: engineering units.
    assert snap["seq"] == 42 and snap["pos_age_ms"] == 4
    for j in range(N_JOINTS):
        expected = count_to_deg(j, 2048 + 10 * j)
        if j % 3 == 2:
            expected += count_to_deg(j - 1, 2048 + 10 * (j - 1))
        assert abs(snap["pos_deg"][j]
                   - expected) < 1e-9
        assert abs(snap["speed_deg_s"][j]
                   - speed_counts_to_deg_s(80 if j % 3 == 2 else 40)) < 1e-9
        assert snap['raw_pos_deg'][j] == count_to_deg(j, 2048 + 10 * j)
    imu = snap["imu"]
    assert imu is not None
    assert abs(imu["az_g"] - 1.0) < 1e-6
    assert abs(imu["gx_dps"] - 1.0) < 1e-6
    assert abs(imu["gy_dps"] + 1.0) < 1e-6
    # Position cache refreshed for read_position_deg fast hits.
    assert abs(bus._pos_cache[0] - count_to_deg(0, 2048)) < 1e-9


def test_step_all_offers_passive_command_and_snapshot():
    imu_raw = (0, 0, 16384, 0, 0, 0, 0)
    servos = [(2 + j, 1, 2048 + j, 20) for j in range(18)]
    reply = _fw_snapshot_frame(
        _fw_snapshot_payload(9, 3, 2, imu_raw, servos), 18)
    bus = _mk_bus(reply)
    offered = []
    bus.set_telemetry_sink(lambda kind, payload: offered.append((kind, payload)))

    command = [float(j) for j in range(N_JOINTS)]
    assert bus.step_all(command, speed=400, acc=20) is not None

    kind, payload = next(row for row in offered if row[0] == "step")
    assert kind == "step"
    assert payload["command_deg"] == command
    assert len(payload["position_deg"]) == N_JOINTS
    assert len(payload["speed_deg_s"]) == N_JOINTS
    assert payload["snapshot_seq"] == 9
    assert payload["imu"]["az_g"] == 1.0
    assert b"".join(p["data"] for k, p in offered if k == "serial_rx") == reply
    assert b"".join(p["data"] for k, p in offered if k == "serial_tx") == bytes(bus._ser.tx)


def test_step_all_marks_dead_servo():
    imu_raw = (0, 0, 16384, 0, 0, 0, 0)
    servos = [(2 + j, 1 if j != 5 else 0, 2000, 0) for j in range(18)]
    reply = _fw_snapshot_frame(
        _fw_snapshot_payload(1, 2, 3, imu_raw, servos), 18)
    bus = _mk_bus(reply)
    sink = SnapshotSink()
    bus.set_telemetry_sink(sink)
    snap = bus.step_all([0.0] * N_JOINTS)
    assert snap is not None
    assert 5 not in snap["pos_deg"]          # dead servo omitted
    assert len(snap["pos_deg"]) == 17
    payload = next(p for k, p in sink.offered if k == "step")
    assert payload["missing_servo_ids"] == [7]
    assert payload["servo_reports"][5] == {
        "id": 7, "ok": False, "pos_counts": 2000, "spd_counts_s": 0,
    }


def test_step_all_bad_checksum_returns_none():
    imu_raw = (0, 0, 16384, 0, 0, 0, 0)
    servos = [(2 + j, 1, 2048, 0) for j in range(18)]
    frame = bytearray(_fw_snapshot_frame(
        _fw_snapshot_payload(1, 2, 3, imu_raw, servos), 18))
    frame[-1] ^= 0xFF                        # corrupt checksum
    bus = _mk_bus(bytes(frame))
    sink = SnapshotSink()
    bus.set_telemetry_sink(sink)
    assert bus.step_all([0.0] * N_JOINTS) is None
    assert b"".join(p["data"] for k, p in sink.offered if k == "serial_rx") == bytes(frame)
    result = next(p for k, p in sink.offered if k == "serial_result")
    assert not result["ok"] and result["reason"] == "checksum_mismatch"


def test_snapshot_imu_invalid_age():
    servos = [(2 + j, 1, 2048, 0) for j in range(18)]
    reply = _fw_snapshot_frame(
        _fw_snapshot_payload(1, 2, SNAP_AGE_INVALID,
                             (0, 0, 0, 0, 0, 0, 0), servos), 18)
    bus = _mk_bus(reply)
    snap = bus.read_snapshot()
    assert snap is not None
    assert snap["imu"] is None               # dead/asleep MPU -> no IMU
    # TX was the read-only n=0 query.
    assert bytes(bus._ser.tx) == encode_sync_frame(ord("S"), [])


def test_read_imu_prefers_stream_snapshot():
    imu_raw = (0, 0, 16384, 131, -131, 0, 0)
    servos = [(2 + j, 1, 2048, 0) for j in range(18)]
    reply = _fw_snapshot_frame(
        _fw_snapshot_payload(5, 2, 1, imu_raw, servos), 18)
    bus = _mk_bus(reply)

    imu = bus.read_imu()
    assert imu is not None
    assert abs(imu["az_g"] - 1.0) < 1e-6
    assert abs(imu["gx_dps"] - 1.0) < 1e-6
    assert abs(imu["gy_dps"] + 1.0) < 1e-6
    assert bytes(bus._ser.tx) == encode_sync_frame(ord("S"), [])


def test_flush_sync_raises_after_bounded_binary_retry():
    # Two identical W frames, then a loud failure. The ASCII ``SW`` re-encode
    # and the per-servo ``WP`` glide that used to follow are gone: they
    # re-sent the same goals through slower paths and hid a dropping link.
    item = (2, 2048, 2239, 200)
    bus = _mk_bus(b"ERR\n" * 6 + b"OK\n")
    bus._pending = [item]
    with pytest.raises(RuntimeError, match="SyncWrite failed after 2"):
        bus._flush_sync()
    tx = bytes(bus._ser.tx)
    assert tx == encode_sync_frame(ord("W"), [item]) * SYNC_WRITE_ATTEMPTS
    assert b"SW " not in tx and b"WP " not in tx
    assert bus.sync_write_retries == 0


def test_recording_preserves_sync_write_bytes_and_does_not_request_snapshot():
    bus = _mk_bus(b"OK\r\n")
    sink = SnapshotSink()
    bus.set_telemetry_sink(sink)
    item = (2, 2048, 400, 20)
    bus._pending = [item]

    bus._flush_sync()

    tx = bytes(bus._ser.tx)
    assert tx == encode_sync_frame(ord("W"), [item])
    assert not any(k == "step" for k, _ in sink.offered)
    assert b"".join(p["data"] for k, p in sink.offered if k == "serial_rx") == b"OK\r\n"
    assert b"".join(p["data"] for k, p in sink.offered if k == "serial_tx") == tx


def test_partial_reply_bytes_survive_payload_timeout():
    partial = b"\xa5\x5as\x01\x12\x34"
    bus = _mk_bus(partial)
    sink = SnapshotSink()
    bus.set_telemetry_sink(sink)
    assert bus._bin_txn(encode_sync_frame(ord("S"), []), ord("s"),
                        SNAP_REC_LEN, SNAP_HEAD_LEN, timeout=0.003) is None
    assert b"".join(p["data"] for k, p in sink.offered if k == "serial_rx") == partial
    assert next(p for k, p in sink.offered if k == "serial_result")["reason"] == "payload_timeout"


def test_discarded_input_and_ascii_reply_are_retained():
    class BufferedSerial(FakeSerial):
        @property
        def in_waiting(self):
            return len(self._rx)

        def write(self, data):
            super().write(data)
            self._rx.extend(b"OK 18\r\n")

        def reset_input_buffer(self):
            self._rx.clear()

    bus = _mk_bus(b"")
    bus._ser = BufferedSerial(b"leftover\x00\xff")
    sink = SnapshotSink()
    bus.set_telemetry_sink(sink)
    assert bus._transact("SCAN") == "OK 18"
    reset = next(p for k, p in sink.offered if k == "serial_input_reset")
    assert reset["data"] == b"leftover\x00\xff" and reset["uncaptured_bytes"] == 0
    assert b"".join(p["data"] for k, p in sink.offered if k == "serial_tx") == b"SCAN\n"
    assert b"".join(p["data"] for k, p in sink.offered if k == "serial_rx") == b"OK 18\r\n"


def test_read_imu_without_snapshot_imu_returns_none_and_does_not_probe_ascii():
    # IMU age 0xFFFF = the MCU has no valid sample (sensor absent / I2C
    # failing; the firmware owns that retry). Until 2026-09-14 this fell
    # through to ASCII ``IMUR`` + an ``IMU`` wake (1 s timeout + sleep) and
    # blocked the bus for ~2 s per call during an IMU dropout.
    servos = [(2 + j, 1, 2048, 0) for j in range(18)]
    reply = _fw_snapshot_frame(
        _fw_snapshot_payload(3, 2, SNAP_AGE_INVALID,
                             (0, 0, 0, 0, 0, 0, 0), servos), 18)
    bus = _mk_bus(reply + b"OK 1 2 3 4 5 6 7\n")
    assert bus.read_imu() is None
    assert bytes(bus._ser.tx) == encode_sync_frame(ord("S"), [])
    assert bus.imu_wake_attempts == 0


def test_read_imu_wakes_a_sleeping_mpu_once_per_interval(monkeypatch):
    # Valid fresh age + all-zero frame = MPU asleep after a power glitch. The
    # firmware caches zeros as a good sample (it only re-inits on a failed
    # read), so the host sends ONE bounded ``IMU`` wake, prints and counts
    # it, and does not repeat inside IMU_WAKE_MIN_INTERVAL_S.
    clock = [50.0]
    monkeypatch.setattr(mcu_feetech_bus.time, "monotonic", lambda: clock[0])
    servos = [(2 + j, 1, 2048, 0) for j in range(18)]
    asleep = _fw_snapshot_frame(
        _fw_snapshot_payload(4, 2, 3, (0, 0, 0, 0, 0, 0, 0), servos), 18)
    bus = _mk_bus(asleep + b"OK 0x68\n" + asleep + asleep + b"ERR wake\n")

    assert bus.read_imu() is None
    assert bus.read_imu() is None          # inside the interval: no resend
    tx = bytes(bus._ser.tx)
    assert tx == (encode_sync_frame(ord("S"), []) + b"IMU\n"
                  + encode_sync_frame(ord("S"), []))
    assert bus.imu_wake_attempts == 1
    assert b"IMUR" not in tx

    clock[0] += mcu_feetech_bus.IMU_WAKE_MIN_INTERVAL_S
    assert bus.read_imu() is None
    assert bytes(bus._ser.tx).count(b"IMU\n") == 2
    assert bus.imu_wake_attempts == 2


# ---------------------------------------------------------------------------
# open(): the STREAM handshake is mandatory and its failure is loud
# ---------------------------------------------------------------------------

class _ScriptedSerial(FakeSerial):
    """Answers each written line with the next scripted reply."""

    def __init__(self, replies: list[bytes], clock: list[float]):
        super().__init__(b"")
        self.replies = list(replies)
        self.clock = clock
        self.lines: list[bytes] = []
        self.closed = False

    def write(self, data):
        super().write(data)
        self.lines.append(bytes(data))
        if self.replies:
            self._rx.extend(self.replies.pop(0))

    def read(self, n: int = 1) -> bytes:
        out = super().read(n)
        if not out:
            # Idle link: let the driver's deadline expire without waiting.
            self.clock[0] += 0.05
        return out

    def close(self):
        self.closed = True


def _open_with_replies(monkeypatch, replies: list[bytes]) -> tuple:
    clock = [100.0]
    ser = _ScriptedSerial(replies, clock)
    import serial
    monkeypatch.setattr(serial, "Serial", lambda *a, **k: ser)
    monkeypatch.setattr(mcu_feetech_bus.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(mcu_feetech_bus.time, "sleep",
                        lambda dt: clock.__setitem__(0, clock[0] + dt))
    return ser, clock


def test_open_accepts_stream_firmware(monkeypatch):
    ser, _clock = _open_with_replies(
        monkeypatch, [b"HELLO feetech_bridge v3\n", b"OK STREAM 1\n"])
    bus = McuFeetechBus("/dev/fake", claim=False)
    assert bus.streaming is True
    assert ser.lines == [b"HELLO\n", b"STREAM 1\n"]
    assert not hasattr(bus, "has_stream")


@pytest.mark.parametrize("reply", [b"ERR\n", b"OK STREAM 0\n", b"OK\n"])
def test_open_refuses_pre_stream_firmware_and_names_the_flash_script(
        monkeypatch, reply):
    # An explicit reply that is not ``OK STREAM 1`` is the wrong sketch:
    # no silent legacy path, no retry, one clear error naming the fix.
    ser, _clock = _open_with_replies(
        monkeypatch, [b"HELLO feetech_bridge\n", reply])
    with pytest.raises(McuFirmwareError) as info:
        McuFeetechBus("/dev/fake", claim=False)
    msg = str(info.value)
    assert "firmware/flash_feetech_bridge.sh arduino@<robot>.local" in msg
    assert reply.strip().decode() in msg
    assert ser.lines.count(b"STREAM 1\n") == 1
    assert ser.closed


def test_open_retries_empty_stream_reply_then_fails_as_boot_race(monkeypatch):
    # bb2071e98: a just-booted bridge can answer HELLO and then say nothing
    # to STREAM 1. Retry a bounded number of times; if it never answers this
    # is a bridge/boot fault (McuBridgeError), NOT a firmware mismatch.
    ser, _clock = _open_with_replies(
        monkeypatch, [b"HELLO feetech_bridge\n"])
    with pytest.raises(McuBridgeError) as info:
        McuFeetechBus("/dev/fake", claim=False)
    assert not isinstance(info.value, McuFirmwareError)
    assert "no reply to STREAM 1" in str(info.value)
    assert ser.lines.count(b"STREAM 1\n") == STREAM_HANDSHAKE_ATTEMPTS
    assert ser.closed


def test_open_recovers_when_a_later_stream_attempt_answers(monkeypatch):
    ser, _clock = _open_with_replies(
        monkeypatch, [b"HELLO feetech_bridge\n", b"", b"OK STREAM 1\n"])
    bus = McuFeetechBus("/dev/fake", claim=False)
    assert bus.streaming is True
    assert ser.lines.count(b"STREAM 1\n") == 2


def test_no_stream_opt_out_is_gone():
    assert "HEXAPOD_NO_STREAM" not in mcu_feetech_bus.__doc__
    assert not hasattr(McuFeetechBus, "_flush_sync_ascii_fallback")
    assert not hasattr(McuFeetechBus, "_flush_sync_slow_wp_fallback")


def test_pose_read_compatibility_uses_snapshot_transport_only():
    bus = _mk_bus(b'')
    calls = []
    bus.read_snapshot = lambda: calls.append(1) or {
        "pos_deg": {1: 20., 2: 80.}, "raw_pos_deg": {1: 20., 2: 60.}}
    assert bus.read_all_positions() == {1: 20., 2: 80.}
    assert bus.read_all_raw_positions([4]) == {2: 60.}
    assert len(calls) == 2
