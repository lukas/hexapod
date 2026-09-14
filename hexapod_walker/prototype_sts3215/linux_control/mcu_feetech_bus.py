#!/usr/bin/env python3
"""FeetechBus-compatible driver over the Uno Q MCU UART bridge.

Talks to ``firmware/feetech_bridge`` on ``/dev/ttyHS1`` (STM32 LPUART1).
The MCU owns D0/D1 → FE-URT UART (1 Mbps). Stops ``arduino-router`` while
open so this process can own the port.

Used by ``web_drive`` / ``DriveController`` and by ``urt2_motor_setup``.

    from mcu_feetech_bus import open_feetech_bus
    bus, port = open_feetech_bus()          # MCU preferred, else USB
    bus, port = open_feetech_bus("mcu")     # force MCU bridge

STREAM mode (2026-08-19, the 50-100 Hz feedback upgrade) is the ONLY
supported contract: on open the driver sends ``STREAM 1`` and requires
``OK STREAM 1`` back. The firmware then free-runs the servo bus itself
(pos+speed sync-read + IMU every pass, full current/load/volt/temp state
at ~10 Hz) and serves ``read_snapshot`` / ``read_all_feedback`` /
``read_imu`` from RAM caches with no servo-bus wait — one short
host<->MCU UART round trip each. ``step_all()`` SyncWrites 18 goals AND
returns the freshest state snapshot in a SINGLE round trip (the whole
bus cost of a control tick).

There is no legacy synchronous path any more. A sketch that answers the
handshake with anything but ``OK STREAM 1`` makes ``McuFeetechBus``
raise ``McuFirmwareError`` naming the fix (``firmware/
flash_feetech_bridge.sh arduino@<robot>.local``). Until 2026-09-14 the
driver silently fell back to per-call servo-bus reads (9-13 ms per
18-servo read), which made 100 Hz impossible while looking like a slow
policy — see rl_docs/HARDWARE_100HZ_TIMING_2026-09-10.md, Cause 1.
"""
from __future__ import annotations

import glob
import json
import os
import struct
import subprocess
import threading
import time
from pathlib import Path
from async_bus_guard import require_bus_available

from feetech_bus import (  # noqa: E402
    ADDR_PRESENT_CURRENT,
    ADDR_PRESENT_LOAD,
    ADDR_PRESENT_SPEED,
    ADDR_PRESENT_TEMP,
    ADDR_PRESENT_VOLTAGE,
    ADDR_TORQUE_ENABLE,
    BAUD_DEFAULT,
    FeetechBus,
    N_JOINTS,
    count_to_deg,
    deg_to_count,
    joint_to_servo_id,
    load_trims,
    normalize_acc,
    normalize_speed,
)

MCU_PORT_DEFAULT = "/dev/ttyHS1"
# Firmware HOST_BAUD. The STREAM sketch only speaks 921600; the old 115200
# fallback existed for pre-STREAM sketches and is gone with them.
MCU_BAUD = 921_600
FLASH_HINT = ("flash the current bridge with "
              "firmware/flash_feetech_bridge.sh arduino@<robot>.local, "
              "then sudo systemctl restart hexapod-web")
MCU_SERIAL_READ_TIMEOUT = float(os.environ.get(
    "HEXAPOD_MCU_SERIAL_READ_TIMEOUT", "0.005"))
HELLO_TOKEN = "HELLO feetech_bridge"
COMM_SUCCESS = 0
COMM_FAIL = 1


class McuBridgeError(RuntimeError):
    """The MCU bridge answered HELLO but did not complete the handshake."""


class McuFirmwareError(McuBridgeError):
    """The flashed sketch does not implement STREAM mode (pre-2026-08-19).

    Raised instead of degrading to the legacy synchronous bus path. The
    message names the fix; ``web_drive`` surfaces it to the operator.
    """

# 's' snapshot reply: fixed header (seq u16, pos_age u16, imu_age u16,
# imu 7×i16) then 6 bytes per servo (id, ok, pos i16, spd i16).
SNAP_HEAD_LEN = 20
SNAP_REC_LEN = 6
SNAP_AGE_INVALID = 0xFFFF
# bb2071e98: bounded retry for the empty-reply boot race on STREAM 1.
STREAM_HANDSHAKE_ATTEMPTS = 3
# Bounded re-send of one W frame (the MCU host-UART ring can drop a frame
# during an acquisition pass). Each use is printed and counted.
SYNC_WRITE_ATTEMPTS = 2
# An all-zero IMU frame with a valid age is an MPU asleep after a power
# glitch; the host wakes it with ``IMU`` at most this often (see read_imu).
IMU_WAKE_MIN_INTERVAL_S = 2.0


def encode_sync_frame(cmd: int, items: list[tuple[int, int, int, int]]
                      ) -> bytes:
    """Binary ``A5 5A <cmd> n {id,pos,spd,acc}×n xor`` frame ('W' / 'S')."""
    n = min(len(items), 18)
    payload = bytearray([0xA5, 0x5A, cmd & 0xFF, n])
    x = (cmd & 0xFF) ^ n
    for sid, pos, speed, acc in items[:n]:
        chunk = struct.pack("<BhHB", sid & 0xFF, int(pos),
                            int(speed) & 0xFFFF, int(acc) & 0xFF)
        payload.extend(chunk)
        for b in chunk:
            x ^= b
    payload.append(x)
    return bytes(payload)


def parse_snapshot_payload(rn: int, payload: bytes) -> dict:
    """Decode the 's' reply payload (header + ``rn`` servo records).

    Returns raw integer fields; unit conversion happens in
    ``McuFeetechBus.step_all`` (needs trims / IMU calib).
    """
    seq, pos_age, imu_age = struct.unpack_from("<HHH", payload, 0)
    imu_raw = struct.unpack_from("<7h", payload, 6)
    servos = []
    for k in range(rn):
        sid, ok, pos, spd = struct.unpack_from(
            "<BBhh", payload, SNAP_HEAD_LEN + k * SNAP_REC_LEN)
        servos.append({"id": sid, "ok": bool(ok),
                       "pos_counts": pos, "spd_counts_s": spd})
    return {
        "seq": seq,
        "pos_age_ms": pos_age,
        "imu_age_ms": imu_age,
        "imu_raw": imu_raw,
        "servos": servos,
    }


def _sudo(cmd: list[str]) -> bool:
    try:
        r = subprocess.run(
            ["sudo", "-n"] + cmd,
            capture_output=True, text=True, timeout=8,
        )
        if r.returncode == 0:
            return True
    except (OSError, subprocess.TimeoutExpired):
        pass
    pw = os.environ.get("HEXAPOD_SUDO_PASSWORD", "arduino")
    try:
        r = subprocess.run(
            ["sudo", "-S"] + cmd,
            input=pw + "\n",
            capture_output=True, text=True, timeout=8,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def stop_arduino_router() -> bool:
    return _sudo(["systemctl", "stop", "arduino-router"])


def start_arduino_router() -> bool:
    return _sudo(["systemctl", "start", "arduino-router"])


def mcu_reset() -> bool:
    """Hard-boot the MCU: ready poke + SWD reset via remoteocd (~5 s).

    After an SoC (re)boot the STM32 does NOT auto-run its sketch — stock
    boot relies on arduino-router bringing it up ~80 s in. The reset-only
    remoteocd recipe (mcu_reset.cfg) starts the flashed sketch immediately;
    verified 2026-08-07 (the gpiochip1 line-37 poke alone is NOT enough).
    """
    _sudo(["gpioset", "-c", "/dev/gpiochip1", "-t0", "37=0"])
    ocd = sorted(glob.glob(
        "/home/arduino/.arduino15/packages/arduino/tools/remoteocd/"
        "*/remoteocd"))
    cfg = Path(__file__).resolve().parent / "mcu_reset.cfg"
    if not ocd or not cfg.is_file():
        return False
    try:
        r = subprocess.run(
            [ocd[-1], "upload", "-f", str(cfg), "/dev/null"],
            capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def claim_mcu_port(port: str = MCU_PORT_DEFAULT) -> str:
    if not Path(port).exists():
        raise SystemExit(f"MCU bridge port {port!r} not found")
    stop_arduino_router()
    # Give the router a moment to actually release the UART — opening the
    # port too early was part of the boot-time first-HELLO failure.
    time.sleep(0.5)
    return port


def find_mcu_port() -> str | None:
    env = os.environ.get("HEXAPOD_BUS_PORT")
    if env in ("mcu", "MCU", "bridge", "ttyHS1"):
        return MCU_PORT_DEFAULT if Path(MCU_PORT_DEFAULT).exists() else None
    if env and Path(env).exists() and "ttyHS" in env:
        return env
    if Path(MCU_PORT_DEFAULT).exists():
        return MCU_PORT_DEFAULT
    hits = sorted(glob.glob("/dev/ttyHS*"))
    return hits[0] if hits else None


def find_usb_bus_port(explicit: str | None = None) -> str | None:
    if explicit and explicit not in ("mcu", "MCU", "bridge", "ttyHS1"):
        if str(explicit).startswith("/dev/ttyHS"):
            return None
        return explicit
    env = os.environ.get("HEXAPOD_BUS_PORT")
    if env and env not in ("mcu", "MCU", "bridge", "ttyHS1") \
            and not str(env).startswith("/dev/ttyHS"):
        return env
    candidates = []
    for pat in ("/dev/ttyUSB*", "/dev/ttyCH343USB*", "/dev/ttyACM*",
                "/dev/cu.usbserial*", "/dev/cu.usbmodem*"):
        candidates.extend(sorted(glob.glob(pat)))
    ranked = sorted(
        candidates,
        key=lambda p: (0 if ("CH343" in p or "USB" in p.upper()
                             or "usbserial" in p) else 1, p),
    )
    return ranked[0] if ranked else None


def open_feetech_bus(port: str | None = None, *, baud: int = BAUD_DEFAULT):
    """Open MCU bridge (preferred on Uno Q) or USB URT ``FeetechBus``.

    Returns ``(bus, port_name)``.
    """
    explicit = port or os.environ.get("HEXAPOD_BUS_PORT")
    force_mcu = explicit in ("mcu", "MCU", "bridge", "ttyHS1") or (
        explicit is not None and str(explicit).startswith("/dev/ttyHS"))
    force_usb = bool(explicit) and not force_mcu

    if not force_usb:
        mcu = explicit if (force_mcu and explicit
                           and str(explicit).startswith("/dev/")) \
            else find_mcu_port()
        if mcu:
            # An MCU port exists: this is the robot. Open it (the
            # constructor owns the boot-time HELLO retries) and never
            # drift onto a USB adapter if it fails -- that silently swapped
            # transports and hid a dead/old bridge behind a slower one.
            print(f"[bus] MCU Feetech bridge on {mcu}")
            return McuFeetechBus(mcu), mcu

    usb = find_usb_bus_port(None if force_mcu else explicit)
    if usb:
        print(f"[bus] USB Feetech on {usb} @ {baud}")
        return FeetechBus(usb, baud), usb

    raise SystemExit(
        "No Feetech bus found.  Wire FE-URT UART→D0/D1 and flash "
        "firmware/feetech_bridge, or plug a USB URT-2 "
        "(or set HEXAPOD_BUS_PORT=mcu|/dev/ttyUSB0).")


class _FakePort:
    """Stand-in for scservo PortHandler (baud-swap recovery is MCU-side)."""

    def __init__(self, bus: "McuFeetechBus"):
        self._bus = bus

    def setBaudRate(self, baud: int) -> bool:
        # Host↔MCU link baud; servo-bus baud changes aren't wired yet.
        return baud in (MCU_BAUD, 115_200, BAUD_DEFAULT, 1_000_000)

    def closePort(self) -> None:
        pass

    def isOpen(self) -> bool:
        return True


class _GroupSyncWrite:
    def __init__(self, bus: "McuFeetechBus"):
        self._bus = bus

    def txPacket(self):
        self._bus._flush_sync()

    def clearParam(self):
        self._bus._pending.clear()


class _PktProxy:
    def __init__(self, bus: "McuFeetechBus"):
        self._bus = bus
        self.groupSyncWrite = _GroupSyncWrite(bus)

    def SyncWritePosEx(self, sid, pos, speed, acc) -> None:
        self._bus._pending.append(
            (int(sid), int(pos), int(speed), int(acc)))

    def WritePosEx(self, sid, pos, speed, acc=0):
        line = self._bus._transact(
            f"WP {int(sid)} {int(pos)} {int(speed)} {int(acc)}", timeout=0.6)
        ok = bool(line and line.startswith("OK"))
        self._bus._emit_goal_items(
            [(int(sid), int(pos), int(speed), int(acc))],
            kind="joint_write", ok=ok)
        return 0 if ok else COMM_FAIL

    def write1ByteTxRx(self, sid, addr, val):
        line = self._bus._transact(
            f"W1 {int(sid)} {int(addr)} {int(val)}", timeout=0.5)
        ok = bool(line and line.startswith("OK"))
        return 0, (COMM_SUCCESS if ok else COMM_FAIL), 0

    def write2ByteTxRx(self, sid, addr, val):
        line = self._bus._transact(
            f"W2 {int(sid)} {int(addr)} {int(val)}", timeout=0.5)
        ok = bool(line and line.startswith("OK"))
        return 0, (COMM_SUCCESS if ok else COMM_FAIL), 0

    def read1ByteTxRx(self, sid, addr):
        line = self._bus._transact(
            f"R1 {int(sid)} {int(addr)}", timeout=0.5)
        if not line or not line.startswith("OK"):
            return 0, COMM_FAIL, 0
        parts = line.split()
        try:
            return int(parts[1]), COMM_SUCCESS, 0
        except (IndexError, ValueError):
            return 0, COMM_FAIL, 0

    def read2ByteTxRx(self, sid, addr):
        line = self._bus._transact(
            f"R2 {int(sid)} {int(addr)}", timeout=0.5)
        if not line or not line.startswith("OK"):
            return 0, COMM_FAIL, 0
        parts = line.split()
        try:
            return int(parts[1]), COMM_SUCCESS, 0
        except (IndexError, ValueError):
            return 0, COMM_FAIL, 0

    def ReadPos(self, sid):
        pos = self._bus._read_pos_counts(int(sid))
        if pos is None:
            return 0, COMM_FAIL, 0
        return pos, COMM_SUCCESS, 0

    def ping(self, sid):
        ok = self._bus.ping(int(sid))
        return 0, (COMM_SUCCESS if ok else COMM_FAIL), 0

    def unLockEprom(self, sid):
        self._bus._transact(f"UL {int(sid)}", timeout=0.5)
        return COMM_SUCCESS

    def LockEprom(self, sid):
        self._bus._transact(f"LK {int(sid)}", timeout=0.5)
        return COMM_SUCCESS


class McuFeetechBus:
    """Drop-in stand-in for ``FeetechBus`` over the MCU bridge."""

    def __init__(self, port: str = MCU_PORT_DEFAULT, baud: int = MCU_BAUD,
                 *, claim: bool = True):
        del baud
        if claim:
            claim_mcu_port(port)
        try:
            import serial
        except ImportError as e:
            raise SystemExit(
                "pyserial required for MCU bridge") from e
        self.port_name = port
        self.port = _FakePort(self)
        self.scs = type("scs", (), {"COMM_SUCCESS": COMM_SUCCESS})()
        self.pkt = _PktProxy(self)
        self.trims = load_trims()
        self._pending: list[tuple[int, int, int, int]] = []
        self._lock = threading.Lock()
        self._live_cache: list[int] | None = None
        self._live_cache_t = 0.0
        self._fb_cache: dict[int, dict] = {}
        self._fb_cache_mono = 0.0
        self._pos_cache: dict[int, float] = {}
        self._pos_cache_mono = 0.0
        self._bin_trace_events: list[dict] = []
        self._bin_trace_seq = 0
        self._bin_trace_slow_ms = float(
            os.environ.get("HEXAPOD_BUS_TRACE_SLOW_MS", "30"))
        self._bin_trace_keep = int(
            os.environ.get("HEXAPOD_BUS_TRACE_KEEP", "64"))
        # Optional passive observer.  None in the normal case, so there is
        # no logger function call at all on the bus hot path until an
        # operator starts a telemetry session.
        self._telemetry_sink = None
        self._imu_calib: dict | None = None
        self.reload_imu_calib()
        self._imu_mount: str = "normal"
        self.reload_imu_mount()
        self._ser = None
        self.baud = MCU_BAUD
        last_hello = None
        connected = False
        # Retry rounds: right after boot the bridge can be unresponsive for
        # several seconds (MCU still booting / TFT bitbang splash stalling
        # setup()). Short 2 s probes keep a just-woken MCU from missing its
        # window by seconds; every boot used to fail its first HELLO, exit,
        # and eat a systemd restart cycle (~16 s) — retrying in-process is
        # much cheaper.
        rounds = 6
        for attempt in range(rounds):
            try:
                if self._ser is not None:
                    self._ser.close()
            except Exception:
                pass
            self._ser = serial.Serial(
                port, MCU_BAUD, timeout=MCU_SERIAL_READ_TIMEOUT,
                write_timeout=1.0)
            time.sleep(0.12)
            self._serial_reset_input()
            # TFT bitbang init can briefly stall the MCU after reset.
            hello = self._transact("HELLO", timeout=2.0)
            last_hello = hello
            if hello is not None and "HELLO" in hello:
                connected = True
                break
            print(f"[bus] no HELLO from {port} (attempt {attempt + 1}/"
                  f"{rounds}, got {last_hello!r}) — retrying")
            if attempt == 2:
                # Several silent attempts: the MCU is probably not running
                # at all (it does not auto-boot after an SoC reset). Hard-
                # boot it over SWD and let the sketch paint its splash.
                print("[bus] MCU silent — SWD reset via remoteocd")
                if mcu_reset():
                    print("[bus] MCU reset ok")
                time.sleep(3.0)
            time.sleep(0.5)
        if not connected:
            try:
                self._ser.close()
            except Exception:
                pass
            raise SystemExit(
                f"No feetech_bridge on {port} (got {last_hello!r}). "
                "Flash firmware/feetech_bridge and wire URT UART to D0/D1.")

        # STREAM mode is mandatory: ask the firmware to free-run acquisition
        # so reads are cache-served (module docstring) and refuse to run on
        # anything that does not confirm it.
        #
        # A freshly-booted bridge can answer HELLO before it is ready to stream
        # and then return nothing to the first STREAM inside the timeout. That
        # empty reply used to read as "old firmware", so the driver fell to the
        # slow legacy path for the whole session and every RL drive was refused
        # ("snapshot transport unavailable") until the service was restarted by
        # hand (bb2071e98). Retry on an EMPTY reply only, bounded; an explicit
        # reply that is not ``OK STREAM 1`` is the wrong sketch and is an error.
        line = None
        for attempt in range(1, STREAM_HANDSHAKE_ATTEMPTS + 1):
            line = self._transact("STREAM 1", timeout=1.5)
            if line:
                if attempt > 1:
                    print(f"[bus] STREAM answered on attempt {attempt}")
                break
            print(f"[bus] no STREAM reply (attempt {attempt}/"
                  f"{STREAM_HANDSHAKE_ATTEMPTS}) — retrying")
            time.sleep(0.5)
        if not line:
            self._ser.close()
            raise McuBridgeError(
                f"feetech_bridge on {port} answered HELLO but gave no reply "
                f"to STREAM 1 in {STREAM_HANDSHAKE_ATTEMPTS} attempts. This is "
                "a boot-time race, not old firmware: restart hexapod-web "
                "(the service restarts itself); if it repeats, "
                + FLASH_HINT + ".")
        if line.strip() != "OK STREAM 1":
            self._ser.close()
            raise McuFirmwareError(
                f"feetech_bridge on {port} answered {line!r} to STREAM 1; "
                "the flashed sketch predates STREAM mode (2026-08-19) and "
                "the slow legacy bus path is no longer supported -- "
                + FLASH_HINT + ".")
        # Transport-capability flag read by tooling (bus_bench,
        # motor_setup/inplace_demos dense waypoints). Always True here; a USB
        # ``FeetechBus`` has no such attribute.
        self.streaming = True
        self.sync_write_retries = 0
        self.imu_wake_attempts = 0
        self._imu_wake_mono = 0.0
        print("[bus] MCU stream mode ON")

    def set_telemetry_sink(self, sink) -> None:
        """Attach/detach a nonblocking passive recorder callback.

        The sink receives only data already acquired by the caller; this
        method never starts a polling thread or adds a bus transaction.
        Assignment is atomic under CPython, so it can be toggled by an HTTP
        handler while another test owns the bus.
        """
        if sink is not None and not callable(sink):
            raise TypeError("telemetry sink must be callable or None")
        self._telemetry_sink = sink

    def _emit_telemetry(self, kind: str, payload: dict) -> None:
        sink = getattr(self, "_telemetry_sink", None)
        if sink is None:
            return
        try:
            sink(kind, payload)
        except Exception:
            # Observability must never be able to fail a bus operation.
            pass

    def _serial_read(self, size: int = 1) -> bytes:
        """Observe bytes before parsing, including partial/rejected replies."""
        try:
            data = self._ser.read(size)
        except Exception as exc:
            self._emit_telemetry("serial_read_error", {
                "requested_bytes": size, "error": repr(exc),
            })
            raise
        if data and getattr(self, "_telemetry_sink", None) is not None:
            self._emit_telemetry("serial_rx", {"data": bytes(data)})
        return data

    def _serial_write(self, data: bytes):
        try:
            written = self._ser.write(data)
        except Exception as exc:
            self._emit_telemetry("serial_write_error", {
                "data": bytes(data), "error": repr(exc),
            })
            raise
        if getattr(self, "_telemetry_sink", None) is not None:
            self._emit_telemetry("serial_tx", {
                "data": bytes(data), "written_bytes": written,
            })
        return written

    def _serial_reset_input(self) -> None:
        # Retain bytes the existing transaction would discard. Reading only
        # the bytes already buffered does not send a request or wait for a
        # new reply. The cap bounds a pathological unsolicited-data burst.
        if getattr(self, "_telemetry_sink", None) is not None:
            try:
                pending = int(getattr(self._ser, "in_waiting", 0))
                data = self._ser.read(min(pending, 65536)) if pending else b""
                self._emit_telemetry("serial_input_reset", {
                    "data": bytes(data), "buffered_bytes": pending,
                    "uncaptured_bytes": max(0, pending - len(data)),
                })
            except Exception as exc:
                self._emit_telemetry("serial_capture_error", {
                    "stage": "input_reset", "error": repr(exc),
                })
        self._ser.reset_input_buffer()

    def _command_from_items(
            self, items: list[tuple[int, int, int, int]]) -> tuple[
                list[float | None], list[int | None], list[int | None]]:
        command: list[float | None] = [None] * N_JOINTS
        speeds: list[int | None] = [None] * N_JOINTS
        accelerations: list[int | None] = [None] * N_JOINTS
        for sid, count, speed, acc in items:
            joint = int(sid) - 2
            if not 0 <= joint < N_JOINTS:
                continue
            # count_to_deg ignores trim; undo the trim that deg_to_count
            # added so the logged target stays in logical robot degrees.
            command[joint] = (
                count_to_deg(joint, int(count)) - float(self.trims[joint]))
            speeds[joint] = int(speed)
            accelerations[joint] = int(acc)
        return command, speeds, accelerations

    def _emit_goal_items(self, items: list[tuple[int, int, int, int]], *,
                         kind: str, ok: bool | None = None) -> None:
        if getattr(self, "_telemetry_sink", None) is None:
            return
        command, speeds, accelerations = self._command_from_items(items)
        payload = {
            "command_deg": command,
            "speed_counts_s": speeds,
            "acc_units": accelerations,
        }
        if ok is not None:
            payload["ok"] = bool(ok)
        self._emit_telemetry(kind, payload)

    @staticmethod
    def _snapshot_payload(snapshot: dict | None) -> dict:
        if not isinstance(snapshot, dict):
            return {"snapshot_ok": False}
        positions = snapshot.get("pos_deg") or {}
        speeds = snapshot.get("speed_deg_s") or {}
        return {
            "snapshot_ok": True,
            "snapshot_seq": snapshot.get("seq"),
            "position_age_ms": snapshot.get("pos_age_ms"),
            "imu_age_ms": snapshot.get("imu_age_ms"),
            "position_deg": [positions.get(j) for j in range(N_JOINTS)],
            "speed_deg_s": [speeds.get(j) for j in range(N_JOINTS)],
            "servo_reports": snapshot.get("servo_reports", []),
            "missing_servo_ids": [j + 2 for j in range(N_JOINTS)
                                  if j not in positions],
            "imu": dict(snapshot["imu"])
            if isinstance(snapshot.get("imu"), dict) else None,
        }

    def reload_imu_calib(self) -> dict | None:
        """Load ``logs/imu_calib.json`` (or clear if missing)."""
        try:
            from imu_calibrate import load_imu_calib
            self._imu_calib = load_imu_calib()
        except Exception as exc:
            # load_imu_calib returns None for a missing/invalid file; an
            # exception here is a code/import fault and must not read as
            # "robot has no calibration".
            self._imu_calib = None
            print(f"[bus] WARNING IMU calibration unavailable: {exc!r} "
                  "(samples will be uncalibrated)")
        return self._imu_calib

    def reload_imu_mount(self) -> str:
        """Load the IMU mount orientation from ``logs/imu_mount.json``.

        ``{"mount": "flip_y"}`` — how the GY-521 sits relative to the
        chassis frame (X fwd, Z up; see rl_move/attitude.py). Applied to
        RAW axes in read_imu, BEFORE bias calibration, so a rest calib
        captured after a remount stays consistent. Options:
        normal | flip_x (y,z negated) | flip_y (x,z) | flip_z (x,y).
        History: 2026-08-09 the module was briefly remounted chip-down
        (flip_y), then remounted right-side-up during the same-day
        reassembly → back to "normal". This chip reads |g| ≈ 1.27 at
        rest (scale quirk); the rest calib absorbs it as z bias.
        """
        mount = "normal"
        path = Path(__file__).resolve().parent / "logs" / "imu_mount.json"
        if path.is_file():
            try:
                d = json.loads(path.read_text())
                m = str(d.get("mount", "normal")).lower()
                if m in ("normal", "flip_x", "flip_y", "flip_z"):
                    mount = m
                else:
                    print(f"[bus] WARNING {path.name}: unknown mount {m!r}; "
                          "using 'normal'")
            except Exception as exc:
                print(f"[bus] WARNING {path.name} unreadable ({exc!r}); "
                      "using mount 'normal'")
        self._imu_mount = mount
        return mount

    def _readline_bytes(self, timeout: float) -> bytes | None:
        deadline = time.monotonic() + timeout
        buf = bytearray()
        while time.monotonic() < deadline:
            chunk = self._serial_read(1)
            if not chunk:
                continue
            if chunk == b"\n":
                return bytes(buf).strip()
            if chunk != b"\r":
                buf.extend(chunk)
                if len(buf) > 2048:
                    buf.clear()
        return None

    def _readline(self, timeout: float) -> str | None:
        line = self._readline_bytes(timeout)
        if line is None:
            return None
        return line.decode("ascii", errors="replace").strip()

    def _transact(self, cmd: str, *, timeout: float = 0.8) -> str | None:
        require_bus_available(self)
        t0 = time.monotonic()
        with self._lock:
            require_bus_available(self)
            self._serial_reset_input()
            self._serial_write((cmd.strip() + "\n").encode("ascii"))
            self._ser.flush()
            reply = None
            for _ in range(8):
                line = self._readline(timeout)
                if line is None:
                    break
                if line.startswith("HELLO") and not cmd.startswith("HELLO"):
                    continue
                reply = line
                break
        try:
            from event_log import emit_mcu
            emit_mcu(cmd.strip(), reply, ms=(time.monotonic() - t0) * 1000.0)
        except Exception:
            pass
        return reply

    def _transact_try(self, cmd: str, *, timeout: float = 0.8) -> str | None:
        """Best-effort transaction: return immediately if the MCU link is busy."""
        require_bus_available(self)
        if not self._lock.acquire(blocking=False):
            return None
        t0 = time.monotonic()
        try:
            require_bus_available(self)
            self._serial_reset_input()
            self._serial_write((cmd.strip() + "\n").encode("ascii"))
            self._ser.flush()
            reply = None
            for _ in range(8):
                line = self._readline(timeout)
                if line is None:
                    break
                if line.startswith("HELLO") and not cmd.startswith("HELLO"):
                    continue
                reply = line
                break
        finally:
            self._lock.release()
        try:
            from event_log import emit_mcu
            emit_mcu(cmd.strip(), reply, ms=(time.monotonic() - t0) * 1000.0)
        except Exception:
            pass
        return reply

    def debug_counters(self, *, reset: bool = False,
                       timeout: float = 0.8) -> dict | None:
        """Read MCU bridge DBG counters, optionally resetting them first."""
        line = self._transact("DBG RESET" if reset else "DBG",
                              timeout=timeout)
        if not line or not line.startswith("OK"):
            return None
        out: dict[str, int | str] = {}
        for part in line.split()[1:]:
            if "=" not in part:
                continue
            key, val = part.split("=", 1)
            try:
                out[key] = int(val, 0)
            except ValueError:
                out[key] = val
        cmd = out.get("last_bin_cmd")
        if isinstance(cmd, int) and 32 <= cmd <= 126:
            out["last_bin_cmd_chr"] = chr(cmd)
        return out

    def ping(self, sid: int) -> bool:
        line = self._transact(f"PING {int(sid)}", timeout=0.4)
        return bool(line and line.startswith("OK"))

    def scan(self, id_range=range(1, 31)) -> list[int]:
        self.last_scan_error = None
        now = time.monotonic()
        if self._live_cache is not None and now - self._live_cache_t < 2.0:
            return [s for s in self._live_cache if s in id_range]
        line = self._transact("SCAN", timeout=2.5)
        if line is None:
            self.last_scan_error = 'Motor controller did not answer SCAN within 2.5 seconds. Motor presence is unknown; check the controller connection and retry.'
        elif not (line.strip() == 'OK' or line.startswith('OK ')):
            self.last_scan_error = f'Motor controller rejected SCAN: {line}. Motor presence is unknown.'
        found: list[int] = []
        if line and line.startswith("OK"):
            rest = line[2:].strip()
            if rest:
                for part in rest.split(","):
                    part = part.strip()
                    if part.isdigit():
                        found.append(int(part))
                    else:
                        self.last_scan_error = f'Unreadable motor scan reply: {line}. Motor presence is unknown; retry.'
        # Do not cache an empty scan. A single transient empty reply after a
        # dense motion stream must not poison the immediate retry path.
        if found:
            self._live_cache = found
            self._live_cache_t = now
        return [s for s in found if s in id_range]

    def torque(self, sid: int, on: bool) -> None:
        cmd = f"T {int(sid)} {1 if on else 0}"
        line = self._transact(cmd, timeout=0.4)
        if line is None:
            raise TimeoutError(f"{cmd}: no MCU acknowledgement")
        if not line.startswith("OK"):
            raise RuntimeError(f"{cmd}: MCU rejected torque command: {line}")

    def enable_all_torque(self, on: bool = True) -> None:
        cmd = f"TA {1 if on else 0}"
        line = self._transact(cmd, timeout=1.0)
        if line is None:
            raise TimeoutError(f"{cmd}: no MCU acknowledgement")
        if not line.startswith("OK"):
            raise RuntimeError(f"{cmd}: MCU rejected torque command: {line}")

    def set_id(self, old_id: int, new_id: int) -> None:
        self.pkt.unLockEprom(old_id)
        self.pkt.write1ByteTxRx(old_id, 5, new_id)
        self.pkt.LockEprom(new_id)
        self._live_cache = None

    def _read_exact(self, n: int, timeout: float) -> bytes | None:
        deadline = time.monotonic() + timeout
        buf = bytearray()
        while len(buf) < n and time.monotonic() < deadline:
            chunk = self._serial_read(n - len(buf))
            if chunk:
                buf.extend(chunk)
            else:
                time.sleep(0.0005)
        return bytes(buf) if len(buf) == n else None

    def _record_bin_trace(self, trace: dict, *, ok: bool,
                          reason: str | None = None) -> None:
        """Keep a small ring of slow/failing binary transaction timings."""
        elapsed_ms = float(trace.get("elapsed_ms") or 0.0)
        slow_ms = float(getattr(self, "_bin_trace_slow_ms", 30.0))
        if ok and elapsed_ms < slow_ms:
            return
        self._bin_trace_seq = int(getattr(self, "_bin_trace_seq", 0)) + 1
        event = {
            "seq": self._bin_trace_seq,
            "ok": bool(ok),
            **({"reason": reason} if reason else {}),
            **trace,
        }
        events = getattr(self, "_bin_trace_events", None)
        if events is None:
            self._bin_trace_events = []
            events = self._bin_trace_events
        events.append(event)
        keep = max(1, int(getattr(self, "_bin_trace_keep", 64)))
        if len(events) > keep:
            del events[:-keep]
        try:
            from event_log import emit
            emit(
                "bus_timing",
                (
                    f"{trace.get('cmd')}->{trace.get('want')} "
                    f"{'ok' if ok else reason or 'fail'} "
                    f"{elapsed_ms:.1f}ms"
                ),
                src="mcu",
                level=("warn" if ok else "error"),
                data=event,
            )
        except Exception:
            pass

    def drain_debug_events(self) -> list[dict]:
        events = list(getattr(self, "_bin_trace_events", []))
        self._bin_trace_events = []
        return events

    def debug_events(self) -> list[dict]:
        return list(getattr(self, "_bin_trace_events", []))

    def _bin_txn(self, frame: bytes, want: int, rec_size: int,
                 head_len: int = 0, *, timeout: float = 1.2
                 ) -> tuple[int, bytes] | None:
        """Send a binary frame; return (n, payload) of the A5 5A reply.

        ``payload`` is ``head_len`` fixed bytes + n × ``rec_size`` records
        (checksum verified, framing stripped).
        """
        require_bus_available(self)
        cmd = chr(frame[2]) if len(frame) > 2 and 32 <= frame[2] <= 126 else frame[2]
        trace: dict = {
            "cmd": cmd,
            "want": chr(want) if 32 <= want <= 126 else want,
            "n": int(frame[3]) if len(frame) > 3 else None,
            "timeout_ms": round(float(timeout) * 1000.0, 3),
        }
        t_start = time.monotonic()
        t_lock_req = t_start

        def finish(result, *, ok: bool, reason: str | None = None):
            trace["elapsed_ms"] = round((time.monotonic() - t_start) * 1000.0, 3)
            self._record_bin_trace(trace, ok=ok, reason=reason)
            self._emit_telemetry("serial_result", {
                "protocol": "binary", "ok": ok, "reason": reason, **trace,
            })
            return result

        with self._lock:
            require_bus_available(self)
            t_locked = time.monotonic()
            trace["lock_wait_ms"] = round((t_locked - t_lock_req) * 1000.0, 3)
            t0 = time.monotonic()
            self._serial_reset_input()
            trace["reset_input_ms"] = round((time.monotonic() - t0) * 1000.0, 3)
            t_write = time.monotonic()
            self._serial_write(frame)
            trace["serial_write_ms"] = round(
                (time.monotonic() - t_write) * 1000.0, 3)
            t_flush = time.monotonic()
            self._ser.flush()
            trace["serial_flush_ms"] = round(
                (time.monotonic() - t_flush) * 1000.0, 3)
            trace["write_flush_ms"] = round((time.monotonic() - t0) * 1000.0, 3)
            # Skip any ASCII chatter (HELLO) until A5 arrives.
            deadline = time.monotonic() + timeout
            t0 = time.monotonic()
            ascii_drains = 0
            pre_a5 = bytearray()
            pre_a5_lines: list[str] = []
            while time.monotonic() < deadline:
                b = self._serial_read(1)
                if not b:
                    continue
                if b[0] == 0xA5:
                    break
                if len(pre_a5) < 96:
                    pre_a5.extend(b[:96 - len(pre_a5)])
                # drain a possible ASCII line
                if b[0] in (ord("H"), ord("O"), ord("E")):
                    ascii_drains += 1
                    rest = self._readline_bytes(0.05)
                    if rest is not None:
                        raw_line = bytes([b[0]]) + rest
                        pre_a5_lines.append(
                            raw_line[:128].decode(
                                "ascii", errors="backslashreplace"))
                        if len(pre_a5) < 96:
                            pre_a5.extend(raw_line[1:96 - len(pre_a5) + 1])
                        if raw_line.startswith(b"ERR"):
                            trace["first_byte_wait_ms"] = round(
                                (time.monotonic() - t0) * 1000.0, 3)
                            trace["ascii_drains"] = ascii_drains
                            trace["pre_a5_hex"] = bytes(pre_a5).hex()
                            trace["pre_a5_ascii"] = bytes(pre_a5).decode(
                                "ascii", errors="backslashreplace")
                            trace["pre_a5_lines"] = pre_a5_lines[:4]
                            return finish(
                                None, ok=False, reason="ascii_err")
            else:
                trace["first_byte_wait_ms"] = round(
                    (time.monotonic() - t0) * 1000.0, 3)
                trace["ascii_drains"] = ascii_drains
                if pre_a5:
                    trace["pre_a5_hex"] = bytes(pre_a5).hex()
                    trace["pre_a5_ascii"] = bytes(pre_a5).decode(
                        "ascii", errors="backslashreplace")
                if pre_a5_lines:
                    trace["pre_a5_lines"] = pre_a5_lines[:4]
                return finish(None, ok=False, reason="no_a5")
            trace["first_byte_wait_ms"] = round(
                (time.monotonic() - t0) * 1000.0, 3)
            trace["ascii_drains"] = ascii_drains
            if pre_a5:
                trace["pre_a5_hex"] = bytes(pre_a5).hex()
                trace["pre_a5_ascii"] = bytes(pre_a5).decode(
                    "ascii", errors="backslashreplace")
            if pre_a5_lines:
                trace["pre_a5_lines"] = pre_a5_lines[:4]
            t0 = time.monotonic()
            hdr = self._read_exact(3, timeout)  # 5A cmd n
            trace["hdr_ms"] = round((time.monotonic() - t0) * 1000.0, 3)
            if not hdr or hdr[0] != 0x5A or hdr[1] != want:
                trace["hdr"] = list(hdr or b"")
                return finish(None, ok=False, reason="bad_header")
            rn = hdr[2]
            trace["reply_n"] = int(rn)
            if rn > 18:
                return finish(None, ok=False, reason="reply_n_gt_18")
            want_len = head_len + rn * rec_size
            t0 = time.monotonic()
            payload = self._read_exact(head_len + rn * rec_size, timeout)
            trace["payload_ms"] = round((time.monotonic() - t0) * 1000.0, 3)
            trace["payload_len"] = 0 if payload is None else len(payload)
            trace["payload_want_len"] = int(want_len)
            if payload is None:
                return finish(None, ok=False, reason="payload_timeout")
            t0 = time.monotonic()
            chk = self._read_exact(1, timeout)
            trace["checksum_ms"] = round((time.monotonic() - t0) * 1000.0, 3)
            if chk is None:
                return finish(None, ok=False, reason="checksum_timeout")
            x = hdr[1] ^ rn
            for b in payload:
                x ^= b
            if chk[0] != x:
                trace["checksum_got"] = int(chk[0])
                trace["checksum_want"] = int(x)
                return finish(None, ok=False, reason="checksum_mismatch")
            return finish((rn, payload), ok=True)

    def _bin_req(self, cmd: int, ids: list[int] | None, *,
                 timeout: float = 1.2) -> tuple[int, bytes] | None:
        """Send A5 5A 'F' n [ids…] xor; return (n, payload_bytes) of 'f'.

        Only the full-feedback block remains on this path; positions come
        from the snapshot ('S'/'s').
        """
        assert cmd == ord("F"), cmd
        if ids is None:
            id_bytes = b""
        else:
            id_bytes = bytes(int(i) & 0xFF for i in ids)[:18]
        n = len(id_bytes)
        body = bytes([cmd & 0xFF, n]) + id_bytes
        x = 0
        for b in body:
            x ^= b
        frame = bytes([0xA5, 0x5A]) + body + bytes([x])
        return self._bin_txn(frame, ord("f"), 13, timeout=timeout)

    def _fb_dict_from_rec(self, rec: bytes) -> dict | None:
        if len(rec) < 13 or rec[1] == 0:
            return None
        sid = rec[0]
        pos, spd, load = struct.unpack_from("<hhH", rec, 2)
        volt, temp, moving = rec[8], rec[9], rec[10]
        cur, = struct.unpack_from("<h", rec, 11)
        joint = int(sid) - 2
        if joint < 0 or joint >= N_JOINTS:
            return None
        # Speed: library already sign-decoded; unit is counts/s (steps/s),
        # so deg/s = counts × 360/4096. (Until 2026-08-07 this used the
        # SCS-series 0.732 rpm/unit convention — a clean 50× inflation:
        # the battery's "1537 °/s" readings were exactly the commanded
        # 350 counts/s profile speed.)
        speed_deg_s = float(spd) * 360.0 / 4096.0
        return {
            "joint": joint,
            "id": int(sid),
            "deg": count_to_deg(joint, int(pos)),
            "load_pct": (int(load) & 0x3FF) / 10.0,
            "volt": volt / 10.0,
            "temp_c": int(temp),
            "current_a": cur * 0.0065,
            "speed_deg_s": speed_deg_s,
            "moving": int(moving),
            "pos_counts": int(pos),
        }

    # The temperature byte of the FeedBack record is wrong on roughly 1.5 % of
    # reads (a 30 C servo reports 40-61 C for exactly one read, then 30 again,
    # while position/current/voltage in the same checksummed record are fine).
    # A servo cannot move 8 C in a second, so a jump is held back until reads
    # have agreed with it for TEMP_JUMP_CONFIRM_S. A count of reads is not
    # enough: the MCU refreshes temperatures at ~10 Hz and the host polls at
    # 10 Hz too, so one bad MCU pass is often read twice (2026-09-12 evening:
    # "joint 4 hot 108 C, 3 consecutive polls" limped a 31 C robot).
    TEMP_JUMP_C = 8
    TEMP_JUMP_CONFIRM_S = 1.0
    TEMP_HOLD_MAX_S = 5.0

    def _filter_temp(self, fb: dict) -> None:
        """Replace an isolated temperature jump with the last accepted value.

        Keeps ``temp_raw_c`` when a reading was overridden so the raw byte is
        still visible to anyone who wants it.  Mutates ``fb`` in place.
        """
        state = getattr(self, "_temp_filter", None)
        if state is None:
            state = self._temp_filter = {}
        sid = fb["id"]
        raw = fb["temp_c"]
        now = time.monotonic()
        prev = state.get(sid)
        if prev is None or now - prev["t"] > self.TEMP_HOLD_MAX_S:
            state[sid] = {"temp": raw, "t": now, "pending": None, "since": None}
            return
        if abs(raw - prev["temp"]) < self.TEMP_JUMP_C:
            prev.update(temp=raw, t=now, pending=None, since=None)
            return
        pending = prev["pending"]
        if pending is not None and abs(raw - pending) < self.TEMP_JUMP_C:
            if now - prev["since"] >= self.TEMP_JUMP_CONFIRM_S:
                # Reads have agreed on the new level for long enough: the jump is real.
                prev.update(temp=raw, t=now, pending=None, since=None)
                return
        else:
            prev["pending"], prev["since"] = raw, now
        fb["temp_raw_c"] = raw
        fb["temp_c"] = prev["temp"]

    def read_all_feedback(self, ids: list[int] | None = None
                          ) -> dict[int, dict]:
        """One MCU round-trip: FeedBack block for every id.

        Returns ``{joint: feedback_dict}``. ``ids=None`` → MCU default 2..19.
        """
        got = self._bin_req(ord("F"), ids, timeout=1.5)
        out: dict[int, dict] = {}
        if not got:
            return out
        rn, payload = got
        for k in range(rn):
            rec = payload[k * 13:(k + 1) * 13]
            fb = self._fb_dict_from_rec(rec)
            if fb is None:
                continue
            self._filter_temp(fb)
            out[fb["joint"]] = fb
            self._fb_cache[fb["id"]] = fb
            self._pos_cache[fb["joint"]] = float(fb["deg"])
        self._fb_cache_mono = time.monotonic()
        self._pos_cache_mono = self._fb_cache_mono
        if getattr(self, "_telemetry_sink", None) is not None:
            self._emit_telemetry("feedback", {
                "position_deg": [
                    out[j].get("deg") if j in out else None
                    for j in range(N_JOINTS)],
                "speed_deg_s": [
                    out[j].get("speed_deg_s") if j in out else None
                    for j in range(N_JOINTS)],
                "current_a": [
                    out[j].get("current_a") if j in out else None
                    for j in range(N_JOINTS)],
                "load_pct": [
                    out[j].get("load_pct") if j in out else None
                    for j in range(N_JOINTS)],
                "voltage_v": [
                    out[j].get("volt") if j in out else None
                    for j in range(N_JOINTS)],
                "temperature_c": [
                    out[j].get("temp_c") if j in out else None
                    for j in range(N_JOINTS)],
                "moving": [
                    out[j].get("moving") if j in out else None
                    for j in range(N_JOINTS)],
            })
        return out

    def _read_pos_counts(self, sid: int) -> int | None:
        """Direct single-servo present position in raw counts (``RP``)."""
        line = self._transact(f"RP {int(sid)}", timeout=0.5)
        if not line or not line.startswith("OK"):
            return None
        parts = line.split()
        if len(parts) < 2:
            return None
        try:
            return int(parts[1])
        except ValueError:
            return None

    def read_position_deg(self, joint: int) -> float | None:
        """Present angle of one joint.

        Served from the position cache filled by the last snapshot /
        feedback read when that is < 50 ms old (so 18 consecutive calls
        cost one bus transaction), else one ``read_snapshot`` refresh.
        A joint the snapshot flags not-ok gets one direct ``RP`` read so
        the caller can name exactly which servo is silent.
        """
        if (time.monotonic() - self._pos_cache_mono < 0.05
                and joint in self._pos_cache):
            return self._pos_cache[joint]
        snap = self.read_snapshot()
        if snap is not None and joint in snap["pos_deg"]:
            return snap["pos_deg"][joint]
        pos = self._read_pos_counts(joint_to_servo_id(joint))
        if pos is None:
            return None
        return count_to_deg(joint, pos)

    def read_feedback(self, joint: int) -> dict | None:
        """Match ``FeetechBus.read_feedback`` (bulk path when possible)."""
        sid = joint_to_servo_id(joint)
        if (time.monotonic() - self._fb_cache_mono < 0.05
                and sid in self._fb_cache):
            return dict(self._fb_cache[sid])
        bulk = self.read_all_feedback(self._live_cache)
        if joint in bulk:
            return bulk[joint]
        # Fallback: single-id bulk.
        bulk = self.read_all_feedback([sid])
        return bulk.get(joint)

    def write_joint(self, joint: int, deg: float,
                    speed: int = 1500, acc: int = 30,
                    *, allow_max_speed: bool = False) -> None:
        speed = normalize_speed(speed, allow_max=allow_max_speed)
        acc = normalize_acc(acc)
        count = deg_to_count(joint, deg, self.trims[joint])
        self.pkt.WritePosEx(joint_to_servo_id(joint), count, speed, acc)

    def write_all(self, degrees, speed: int = 1500, acc: int = 30, *,
                  allow_max_speed: bool = False) -> None:
        require_bus_available(self)
        speed = normalize_speed(speed, allow_max=allow_max_speed)
        acc = normalize_acc(acc)
        for joint, deg in enumerate(degrees):
            count = deg_to_count(joint, deg, self.trims[joint])
            self.pkt.SyncWritePosEx(
                joint_to_servo_id(joint), count, speed, acc)
        self.pkt.groupSyncWrite.txPacket()
        self.pkt.groupSyncWrite.clearParam()

    def step_all(self, degrees, speed: int = 1500, acc: int = 30, *,
                 allow_max_speed: bool = False, apply_calib: bool = True
                 ) -> dict | None:
        """SyncWrite all 18 goals AND get a state snapshot: ONE round trip.

        The whole bus cost of a control tick ('S' n=18). Returns ``None``
        only on a framing/checksum error or reply timeout -- the command
        may or may not have been applied; callers treat the tick as a
        missing sample (the RL runner re-holds the same target), they do
        not re-send through another path.

        Returns ``{"seq", "pos_age_ms", "imu_age_ms",
        "pos_deg": {joint: deg}, "speed_deg_s": {joint: deg/s},
        "imu": read_imu-style dict | None, "servo_reports": [...]}``.
        Ages are how stale the MCU's caches were at reply time
        (typically <= one background pass, a few ms).
        """
        speed = normalize_speed(speed, allow_max=allow_max_speed)
        acc = normalize_acc(acc)
        degrees = [float(value) for value in degrees]
        items = []
        for joint, deg in enumerate(degrees):
            items.append((joint_to_servo_id(joint),
                          deg_to_count(joint, deg, self.trims[joint]),
                          speed, acc))
        snapshot = self._snapshot_txn(items, apply_calib=apply_calib)
        if getattr(self, "_telemetry_sink", None) is not None:
            payload = self._snapshot_payload(snapshot)
            payload.update({
                "command_deg": degrees,
                "speed_counts_s": int(speed),
                "acc_units": int(acc),
            })
            self._emit_telemetry("step", payload)
        return snapshot

    def read_snapshot(self, *, apply_calib: bool = True) -> dict | None:
        """Positions + speed + IMU in ONE round trip ('S' n=0, no write).

        Same return shape as ``step_all``; ``None`` only on a framing/
        checksum error or reply timeout.
        """
        snapshot = self._snapshot_txn([], apply_calib=apply_calib)
        if getattr(self, "_telemetry_sink", None) is not None:
            self._emit_telemetry(
                "snapshot", self._snapshot_payload(snapshot))
        return snapshot

    def _snapshot_txn(self, items: list[tuple[int, int, int, int]], *,
                      apply_calib: bool) -> dict | None:
        frame = encode_sync_frame(ord("S"), items)
        got = self._bin_txn(frame, ord("s"), SNAP_REC_LEN,
                            head_len=SNAP_HEAD_LEN, timeout=0.5)
        if not got:
            return None
        rn, payload = got
        snap = parse_snapshot_payload(rn, payload)
        pos_deg: dict[int, float] = {}
        speed_deg_s: dict[int, float] = {}
        for rec in snap["servos"]:
            joint = int(rec["id"]) - 2
            if not rec["ok"] or not 0 <= joint < N_JOINTS:
                continue
            deg = count_to_deg(joint, rec["pos_counts"])
            pos_deg[joint] = deg
            # STS speed unit is counts/s → deg/s = counts × 360/4096.
            speed_deg_s[joint] = rec["spd_counts_s"] * 360.0 / 4096.0
            self._pos_cache[joint] = deg
        self._pos_cache_mono = time.monotonic()
        imu = None
        if (snap["imu_age_ms"] != SNAP_AGE_INVALID
                and any(snap["imu_raw"])):
            ax, ay, az, gx, gy, gz, temp_raw = snap["imu_raw"]
            imu = self._imu_sample(ax, ay, az, gx, gy, gz, temp_raw,
                                   apply_calib=apply_calib)
        return {
            "seq": snap["seq"],
            "pos_age_ms": snap["pos_age_ms"],
            "imu_age_ms": snap["imu_age_ms"],
            "pos_deg": pos_deg,
            "speed_deg_s": speed_deg_s,
            "imu": imu,
            # Keep rejected per-servo records instead of losing their IDs
            # when the position dictionary filters an MCU ok=false entry.
            "servo_reports": snap["servos"],
        }

    def _flush_sync(self) -> None:
        items = list(self._pending)
        self._pending.clear()
        require_bus_available(self)
        if not items:
            return
        # Recording observes this exact W transaction; it must never change
        # command selection or ask the MCU to acquire additional feedback.
        self._emit_goal_items(items, kind="sync_write")
        binary_replies: list[str | None] = []
        frame = encode_sync_frame(ord("W"), items)
        for attempt in range(SYNC_WRITE_ATTEMPTS):
            trace = {"cmd": "W", "want": "OK", "n": len(items),
                     "attempt": attempt + 1, "timeout_ms": 800.0}
            t_start = time.monotonic()
            line = None
            reason = None
            try:
                with self._lock:
                    require_bus_available(self)
                    trace["lock_wait_ms"] = round(
                        (time.monotonic() - t_start) * 1000.0, 3)
                    t0 = time.monotonic()
                    self._serial_reset_input()
                    trace["reset_input_ms"] = round(
                        (time.monotonic() - t0) * 1000.0, 3)
                    t_write = time.monotonic()
                    self._serial_write(frame)
                    trace["serial_write_ms"] = round(
                        (time.monotonic() - t_write) * 1000.0, 3)
                    t_flush = time.monotonic()
                    self._ser.flush()
                    trace["serial_flush_ms"] = round(
                        (time.monotonic() - t_flush) * 1000.0, 3)
                    trace["write_flush_ms"] = round(
                        (time.monotonic() - t0) * 1000.0, 3)
                    t_ack = time.monotonic()
                    line = self._readline(0.8)
                    trace["ack_wait_ms"] = round(
                        (time.monotonic() - t_ack) * 1000.0, 3)
                    trace["reply"] = line[:128] if line is not None else None
                    if not line or not line.startswith("OK"):
                        reason = "ack_missing" if line is None else "ack_rejected"
            except Exception as exc:
                reason = "transaction_exception"
                trace["exception"] = repr(exc)
                raise
            finally:
                trace["elapsed_ms"] = round(
                    (time.monotonic() - t_start) * 1000.0, 3)
                self._record_bin_trace(
                    trace, ok=bool(line and line.startswith("OK")),
                    reason=reason)
            binary_replies.append(line)
            if line and line.startswith("OK"):
                if attempt:
                    # Not silent: the firmware notes the host UART ring can
                    # drop a whole W frame during an acquisition pass, so one
                    # bounded re-send of the same absolute pose is kept -- but
                    # every use is counted and printed so a link that needs
                    # it often is visible in the journal.
                    self.sync_write_retries = (
                        getattr(self, "sync_write_retries", 0) + 1)
                    print(f"[bus] WARNING SyncWrite needed retry "
                          f"{attempt + 1}/{SYNC_WRITE_ATTEMPTS} "
                          f"(first reply {binary_replies[0]!r}; "
                          f"total retries {self.sync_write_retries})")
                return
            if attempt + 1 < SYNC_WRITE_ATTEMPTS:
                time.sleep(0.01)
        # No ASCII ``SW`` re-encode and no per-servo ``WP`` glide any more:
        # those re-sent the same goals through slower paths and hid a
        # dropping link. Callers see the failure; torque stays as it was.
        raise RuntimeError(
            f"SyncWrite failed after {SYNC_WRITE_ATTEMPTS} attempts: "
            f"replies={binary_replies!r}")

    def power_summary(self, *, timeout: float = 2.5) -> dict:
        """One-shot bus power: live count, sum current, avg volt, max load.

        Uses MCU ``PWR`` → ``OK <n> <I_mA> <V10> <load10>``.
        """
        line = self._transact("PWR", timeout=timeout)
        if not line or not line.startswith("OK"):
            raise RuntimeError(f"PWR failed: {line!r}")
        parts = line.split()
        if len(parts) < 5:
            raise RuntimeError(f"PWR bad reply: {line!r}")
        n = int(parts[1])
        i_ma = int(parts[2])
        v10 = int(parts[3])
        load10 = int(parts[4])
        summary = {
            "live": n,
            "current_a": i_ma / 1000.0,
            "volt": v10 / 10.0,
            "max_load_pct": load10 / 10.0,
        }
        self._emit_telemetry("power", dict(summary))
        return summary

    def read_imu(self, *, timeout: float = 0.6,
                 apply_calib: bool = True) -> dict | None:
        """MPU-6050 sample from the streamed snapshot (one round trip).

        Returns engineering units, or ``None`` when the MCU has no valid
        IMU sample (``imu_age_ms`` = 0xFFFF or an all-zero frame: an
        asleep/unplugged MPU; the firmware owns the wake/retry, see
        ``STREAM_IMU_RUNTIME_FAIL_GRACE_MS``). Scale assumes the sketch's
        +-2 g / +-250 dps config. When ``logs/imu_calib.json`` exists and
        ``apply_calib``, subtracts rest gyro/accel biases.

        Until 2026-09-14 a snapshot without IMU fell through to the ASCII
        ``IMUR`` read plus an ``IMU`` wake (1 s timeout + sleep) on EVERY
        call: during a dropout each poller blocked the bus for up to ~2 s.
        What that path also did, and what is kept here bounded and loud,
        is wake a sleeping MPU: after a power glitch the MPU-6050 boots
        asleep, I2C reads succeed and return zeros, and the firmware caches
        the zeros as a valid fresh sample (it only re-inits on a FAILED
        read). ``_snapshot_txn`` reports such a frame as ``imu=None`` with
        a valid age; on that exact signature one ``IMU`` (WHO_AM_I +
        PWR_MGMT_1 wake) is sent at most every ``IMU_WAKE_MIN_INTERVAL_S``,
        printed and counted (``imu_wake_attempts``). This call still returns
        None; the next snapshot carries the real sample once it is awake.
        ``timeout`` is kept for signature compatibility.
        """
        del timeout
        snap = self.read_snapshot(apply_calib=apply_calib)
        if not isinstance(snap, dict):
            return None
        if isinstance(snap.get("imu"), dict):
            return snap["imu"]
        if snap.get("imu_age_ms") != SNAP_AGE_INVALID:
            now = time.monotonic()
            last = getattr(self, "_imu_wake_mono", 0.0)
            if now - last >= IMU_WAKE_MIN_INTERVAL_S:
                self._imu_wake_mono = now
                self.imu_wake_attempts = (
                    getattr(self, "imu_wake_attempts", 0) + 1)
                print("[bus] WARNING IMU frame all-zero with fresh age "
                      f"({snap.get('imu_age_ms')} ms): MPU asleep; sending "
                      f"wake (count {self.imu_wake_attempts})")
                reply = self._transact("IMU", timeout=1.0)
                if not reply or not reply.startswith("OK"):
                    print(f"[bus] WARNING IMU wake not acknowledged: "
                          f"{reply!r}")
        return None

    def _imu_sample(self, ax: int, ay: int, az: int, gx: int, gy: int,
                    gz: int, temp_raw: int, *, apply_calib: bool = True
                    ) -> dict:
        """Raw int16 MPU sample → engineering units (mount + calib)."""
        # Mount orientation (chip frame -> chassis frame), before calib —
        # see reload_imu_mount. Accel and gyro rotate together.
        m = self._imu_mount
        if m == "flip_x":
            ay, az, gy, gz = -ay, -az, -gy, -gz
        elif m == "flip_y":
            ax, az, gx, gz = -ax, -az, -gx, -gz
        elif m == "flip_z":
            ax, ay, gx, gy = -ax, -ay, -gx, -gy
        sample = {
            "ax_g": ax / 16384.0,
            "ay_g": ay / 16384.0,
            "az_g": az / 16384.0,
            "gx_dps": gx / 131.0,
            "gy_dps": gy / 131.0,
            "gz_dps": gz / 131.0,
            "temp_c": temp_raw / 340.0 + 36.53,
            "ax_raw": ax,
            "ay_raw": ay,
            "az_raw": az,
            "gx_raw": gx,
            "gy_raw": gy,
            "gz_raw": gz,
            "temp_raw": temp_raw,
            "mount": m,
            "calibrated": False,
        }
        if apply_calib and self._imu_calib:
            try:
                from imu_calibrate import apply_imu_calib
                return apply_imu_calib(sample, self._imu_calib)
            except Exception as exc:
                # A calibration that cannot be applied is a code/data bug;
                # count it and say so instead of quietly returning an
                # uncalibrated sample that still claims to be the IMU.
                self.imu_calib_apply_errors = (
                    getattr(self, "imu_calib_apply_errors", 0) + 1)
                if self.imu_calib_apply_errors in (1, 10, 100, 1000):
                    print(f"[bus] WARNING IMU calibration not applied "
                          f"({exc!r}); count "
                          f"{self.imu_calib_apply_errors}")
                return sample
        return sample

    def display_init(self, *, timeout: float = 6.0) -> bool:
        """Hard-reinit the ST7789 (MCU ``DI`` → RST + chrome).

        Always full reinit on the MCU — needed after the ribbon is reseated
        while the sketch keeps ``ready==true`` and would otherwise paint into
        a blank panel. Budget ≥~1.6 s for bitbang clear.
        """
        line = self._transact("DI", timeout=timeout)
        return bool(line and line.startswith("OK"))

    def display_recover(self, *, attempts: int = 3,
                        timeout: float = 6.0) -> bool:
        """Startup / fault path: force DI until OK (or attempts exhausted)."""
        for i in range(max(1, int(attempts))):
            try:
                if self.display_init(timeout=timeout):
                    return True
            except Exception:
                pass
            time.sleep(0.15 * (i + 1))
        return False

    def display_self_test(self, *, timeout: float = 6.0) -> bool:
        """Run the MCU TFT color self-test (``DT``: white/red/green/blue)."""
        line = self._transact("DT", timeout=timeout)
        return bool(line and line.startswith("OK"))

    def display_push(self, lines: list[str], *, timeout: float = 8.0
                     ) -> dict | None:
        """Push status lines; MCU also lights motors from live current.

        ``DX a|b|c`` → ``OK <n> <I_mA> <V10> <load10>`` (same as ``PWR``).
        """
        clean = []
        for s in lines[:12]:
            t = "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in str(s))
            clean.append(t[:20])
        payload = "|".join(clean) if clean else "idle"
        line = self._transact("DX " + payload, timeout=timeout)
        if not line or not line.startswith("OK"):
            return None
        parts = line.split()
        if len(parts) < 5:
            return {"live": 0, "current_a": 0.0, "volt": 0.0,
                    "max_load_pct": 0.0}
        return {
            "live": int(parts[1]),
            "current_a": int(parts[2]) / 1000.0,
            "volt": int(parts[3]) / 10.0,
            "max_load_pct": int(parts[4]) / 10.0,
        }

    def display_job(self, lines: list[str], *, pct: int = -1,
                    timeout: float = 8.0) -> bool:
        """Job-mode TFT (MCU ``DJ``): full-screen text + progress bar.

        Rows are positional — title, 4 body lines, footer — 26 chars each.
        ``pct`` −1 hides the bar. This does not read servos, but it still
        transacts over the shared MCU serial link; callers must skip it while
        motion or calibration timing owns the bus. The next ``display_push``
        returns the panel to the normal schematic.
        """
        clean = []
        for s in list(lines)[:6]:
            t = "".join(ch if 32 <= ord(ch) <= 126 and ch != "|" else " "
                        for ch in str(s))
            clean.append(t[:26])
        while len(clean) < 6:
            clean.append("")
        payload = f"{int(pct)}|" + "|".join(clean)
        line = self._transact("DJ " + payload, timeout=timeout)
        return bool(line and line.startswith("OK"))

    def display_job_try(self, lines: list[str], *, pct: int = -1,
                        timeout: float = 1.5) -> bool:
        """Best-effort ``display_job`` that never waits to acquire the lock."""
        clean = []
        for s in list(lines)[:6]:
            t = "".join(ch if 32 <= ord(ch) <= 126 and ch != "|" else " "
                        for ch in str(s))
            clean.append(t[:26])
        while len(clean) < 6:
            clean.append("")
        payload = f"{int(pct)}|" + "|".join(clean)
        line = self._transact_try("DJ " + payload, timeout=timeout)
        return bool(line and line.startswith("OK"))

    def close(self) -> None:
        try:
            self._transact("STREAM 0", timeout=0.5)
        except Exception:
            pass
        try:
            self._ser.close()
        except Exception:
            pass
