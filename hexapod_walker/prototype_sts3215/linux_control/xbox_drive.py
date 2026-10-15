#!/usr/bin/env python3
"""Bluetooth Xbox controller → the existing web_drive HTTP server (Linux).

No bus ownership, automatic arm, calibration, or startup motion.
Hold LB with neutral sticks, then use left stick to walk and right stick to
turn. Release LB or press B to stop. Back / Xbox is emergency limp.
Use the web UI to stand before driving and to lower afterwards.

    uv run python linux_control/xbox_drive.py --list
    uv run python linux_control/xbox_drive.py --api http://127.0.0.1:8080

--dry-run prints requests without opening any network connection.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import fcntl
import glob
import json
import math
import os
import select
import signal
import struct
import time
import urllib.error
import urllib.request
import uuid

EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
SYN_REPORT, SYN_DROPPED = 0, 3
ABS_X, ABS_Y, ABS_Z, ABS_RX, ABS_RY, ABS_RZ = 0, 1, 2, 3, 4, 5
ABS_GAS, ABS_BRAKE = 9, 10
BTN_B, BTN_X, BTN_Y = 0x131, 0x133, 0x134
BTN_TL, BTN_TR, BTN_SELECT, BTN_MODE = 0x136, 0x137, 0x13A, 0x13C
EVENT = struct.Struct("llHHi")
HEARTBEAT_S = 0.1
HTTP_TIMEOUT_S = 0.35
MAX_EVENT_AGE_S = 0.25
RESET_BUTTONS = {BTN_TL, BTN_TR, BTN_B, BTN_X, BTN_Y, BTN_SELECT, BTN_MODE}


class ControlError(RuntimeError):
    """A refused/uncertain command; release controls before trying again."""


def _read_ioctl(fd: int, nr: int, size: int) -> bytes:
    buf = bytearray(size)
    request = (2 << 30) | (size << 16) | (ord("E") << 8) | nr
    fcntl.ioctl(fd, request, buf)
    return bytes(buf)


def _bits(data: bytes) -> set[int]:
    return {i for i in range(len(data) * 8) if data[i // 8] & (1 << (i % 8))}


@dataclass(frozen=True)
class Axis:
    value: int
    minimum: int
    maximum: int
    flat: int = 0

    def normalized(self, value: int) -> float:
        span = (self.maximum - self.minimum) / 2
        if span <= 0:
            raise ControlError("Invalid stick range; fix the gamepad driver.")
        result = (value - (self.maximum + self.minimum) / 2) / span
        return 0.0 if abs(result) <= max(0.12, self.flat / span) else max(-1.0, min(1.0, result))


def choose_turn_axis(axes: set[int], buttons: set[int]) -> int:
    """Distinguish HID Xbox Bluetooth Z/RZ sticks from USB Z/RZ triggers."""
    required = {BTN_TL, BTN_TR, BTN_B, BTN_X, BTN_Y}
    if not required <= buttons or not {BTN_SELECT, BTN_MODE} & buttons:
        raise ControlError("Unsupported controller buttons; use an Xbox-compatible evdev gamepad.")
    if not {ABS_X, ABS_Y} <= axes:
        raise ControlError("Controller has no left stick; select its gamepad event device.")
    if {ABS_RX, ABS_RY} <= axes:
        return ABS_RX
    if {ABS_Z, ABS_RZ, ABS_BRAKE, ABS_GAS} <= axes:
        return ABS_Z
    raise ControlError(
        "Unsupported right-stick layout; need RX/RY or Z/RZ with BRAKE/GAS "
        "triggers. Update the Xbox HID driver or select the gamepad event device.")


class Device:
    def __init__(self, path: str):
        self.path = path
        self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            # Kernel event times must share the clock used to reject queued input.
            clock_request = (1 << 30) | (4 << 16) | (ord("E") << 8) | 0xA0
            try:
                fcntl.ioctl(self.fd, clock_request, struct.pack("i", time.CLOCK_MONOTONIC))
            except OSError as exc:
                raise ControlError("Cannot select evdev monotonic timestamps; update the Linux input driver.") from exc
            self.name = _read_ioctl(self.fd, 0x06, 256).split(b"\0", 1)[0].decode("utf-8", "replace")
            abs_codes = _bits(_read_ioctl(self.fd, 0x20 + EV_ABS, 8))
            key_codes = _bits(_read_ioctl(self.fd, 0x20 + EV_KEY, 96))
            self.turn_axis = choose_turn_axis(abs_codes, key_codes)
            self.axes = {}
            right_y = ABS_RY if self.turn_axis == ABS_RX else ABS_RZ
            for code in (ABS_X, ABS_Y, self.turn_axis, right_y):
                value, lo, hi, _fuzz, flat, _resolution = struct.unpack(
                    "iiiiii", _read_ioctl(self.fd, 0x40 + code, 24))
                axis = Axis(value, lo, hi, flat)
                axis.normalized(value)  # Reject invalid ranges before any command.
                self.axes[code] = axis
            self.buttons = _bits(_read_ioctl(self.fd, 0x18, 96))
        except Exception:
            os.close(self.fd)
            raise

    def close(self):
        os.close(self.fd)


def list_devices() -> list[tuple[str, str, bool]]:
    devices = []
    for path in sorted(glob.glob("/dev/input/event*")):
        try:
            device = Device(path)
        except (OSError, ControlError) as exc:
            devices.append((path, str(exc), False))
        else:
            devices.append((path, device.name, True))
            device.close()
    return devices


class InputGate:
    """Pure input state: fresh neutral + released buttons gates every engage."""
    def __init__(self, axes: dict[int, Axis], turn_axis: int, buttons: set[int]):
        self.axes = axes
        self.turn_axis = turn_axis
        self.values = {code: axis.normalized(axis.value) for code, axis in axes.items()}
        self.buttons = set(buttons)
        self.previous = set(buttons)
        self.ready = False
        self.engaged = False
        self.dropped = False

    def neutral(self) -> bool:
        return not any(self.values.values())

    def block(self):
        self.ready = self.engaged = False

    def event(self, typ: int, code: int, value: int, now: float) -> list[str]:
        if typ == EV_SYN and code == SYN_DROPPED:
            self.block()
            self.dropped = True
            return ["stop"]
        if self.dropped:
            if typ == EV_SYN and code == SYN_REPORT:
                raise ControlError("Gamepad lost input events; reconnecting with fresh neutral state.")
            return []
        if typ == EV_ABS and code in self.axes:
            self.values[code] = self.axes[code].normalized(value)
        elif typ == EV_KEY:
            if value:
                self.buttons.add(code)
            else:
                self.buttons.discard(code)
        elif typ == EV_SYN and code == SYN_REPORT:
            return self.frame(now)
        return []

    def frame(self, now: float) -> list[str]:
        pressed = self.buttons - self.previous
        self.previous = set(self.buttons)
        if pressed & {BTN_SELECT, BTN_MODE}:
            self.block()
            return ["limp"]
        if BTN_B in pressed:
            self.block()
            return ["stop_all"]
        if self.engaged and BTN_TL not in self.buttons:
            self.block()
            return ["stop"]
        if not self.ready and self.neutral() and not self.buttons & RESET_BUTTONS:
            self.ready = True
        if BTN_TL in pressed:
            if self.ready and self.neutral() and not self.buttons & (RESET_BUTTONS - {BTN_TL}):
                self.engaged = True
            else:
                self.block()
        return []

    def velocity(self, max_vx: float, max_vy: float, max_omega: float) -> tuple[float, float, float]:
        return (-self.values[ABS_Y] * max_vx,
                -self.values[ABS_X] * max_vy,
                -self.values[self.turn_axis] * max_omega)


class WebClient:
    def __init__(self, base: str, *, dry_run: bool = False):
        self.base = base.rstrip("/")
        self.dry_run = dry_run
        self.token = None
        self.lease_timeout_s = 0.75

    def request(self, path: str, body: str | dict | None = None):
        method = "GET" if body is None else "POST"
        if self.dry_run:
            print(f"[dry-run] {method} {path} {body if body is not None else ''}", flush=True)
            return {}
        data = None if body is None else (body.encode() if isinstance(body, str) else json.dumps(body).encode())
        headers = {"Content-Type": "application/json" if isinstance(body, dict) else "text/plain",
                   "X-Hexapod-Source": "bluetooth-xbox"}
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as response:
                text = response.read().decode()
        except urllib.error.HTTPError as exc:
            raise ControlError(f"{path}: HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc
        except (OSError, urllib.error.URLError) as exc:
            raise ControlError(f"{path}: {exc}; check web_drive at {self.base}.") from exc
        if path == "/cmd":
            if text.startswith(("refused", "need ", "bad ", "unknown")):
                raise ControlError(text)
            return text
        try:
            result = json.loads(text)
        except ValueError as exc:
            raise ControlError(f"{path}: invalid JSON; check web_drive version.") from exc
        if not isinstance(result, dict) or result.get("ok") is False:
            raise ControlError(f"{path}: {result}")
        return result

    def check_server(self):
        result = self.request("/api/ping")
        if self.dry_run:
            return
        lease = result.get("scripted_gamepad_lease") or {}
        if lease.get("version") != 1 or lease.get("timeout_s") != 0.75:
            raise ControlError("web_drive lacks the 0.75s gamepad lease watchdog; deploy matching web_drive and drive_controller first.")
        self.lease_timeout_s = float(lease["timeout_s"])

    def begin(self):
        # Remember the token before sending: even a timed-out BEGIN must be stopped.
        self.token = uuid.uuid4().hex
        self.request("/cmd", f"JLEASE BEGIN {self.token}")

    def drive(self, velocity: tuple[float, float, float]):
        if self.token is None:
            raise ControlError("Drive needs a fresh neutral LB engage.")
        vx, vy, omega = velocity
        self.request("/cmd", f"JLEASE {self.token} {vx:.3f} {vy:.3f} {omega:.4f}")

    def stop(self, *, explicit: bool = False):
        errors = []
        token, self.token = self.token, None
        # Do not acquire, arm or alter another session on a quiet disconnect.
        commands = []
        if token:
            commands.append(("/cmd", f"JLEASE STOP {token}"))
        if explicit:
            commands.append(("/api/demo/stop", {}))
        if explicit and not token:
            commands.append(("/cmd", "J 0 0 0"))
        for path, body in commands:
            try:
                self.request(path, body)
            except ControlError as exc:
                errors.append(str(exc))
        if errors:
            raise ControlError("; ".join(errors) + "; any active lease expires on the server.")

    def action(self, action: str):
        if action == "limp":
            self.token = None
            self.request("/cmd", "X")
        elif action in ("stop", "stop_all"):
            self.stop(explicit=action == "stop_all")
        else:
            raise ValueError(action)


def drain_input(device: Device, gate: InputGate, client: WebClient):
    # Drain to EAGAIN before deciding on a heartbeat: LB release may be in
    # the next read, beyond this read's 64-event buffer.
    while True:
        try:
            data = os.read(device.fd, EVENT.size * 64)
        except BlockingIOError:
            return
        if not data or len(data) % EVENT.size:
            raise ControlError("Gamepad disconnected or sent an incomplete event.")
        for seconds, micros, typ, code, value in EVENT.iter_unpack(data):
            now = time.monotonic()
            age = now - (seconds + micros / 1_000_000)
            if age > MAX_EVENT_AGE_S or age < -0.05:
                gate.block()
                client.stop()
                raise ControlError("Stale gamepad input; reconnecting, release LB and center sticks.")
            for action in gate.event(typ, code, value, now):
                client.action(action)


def run_device(device: Device, client: WebClient, args):
    gate = InputGate(device.axes, device.turn_axis, device.buttons)
    next_send = 0.0
    last_tick = time.monotonic()
    gate.frame(last_tick)
    while True:
        readable, _, _ = select.select([device.fd], [], [], 0.025)
        now = time.monotonic()
        if now - last_tick >= client.lease_timeout_s:
            gate.block()
            client.stop()
            raise ControlError("Input loop stalled; release LB and center sticks before reconnecting.")
        last_tick = now
        if readable:
            drain_input(device, gate, client)
        now = time.monotonic()
        if now - last_tick >= client.lease_timeout_s:
            gate.block()
            client.stop()
            raise ControlError("Input handling stalled; release LB and center sticks before reconnecting.")
        if gate.engaged and now >= next_send:
            if client.token is None:
                client.begin()
                # BEGIN can take a network round trip. Drain any release that
                # arrived during it before sending the first velocity command.
                continue
            client.drive(gate.velocity(args.max_vx, args.max_vy, args.max_omega))
            next_send = time.monotonic() + HEARTBEAT_S


def _terminate(_signum, _frame):
    raise KeyboardInterrupt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--device", help="Explicit /dev/input/event* (otherwise discover a compatible gamepad)")
    parser.add_argument("--api", default="http://127.0.0.1:8080")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-vx", type=float, default=30.0, help="Forward speed cap, mm/s")
    parser.add_argument("--max-vy", type=float, default=18.0, help="Sideways speed cap, mm/s")
    parser.add_argument("--max-omega", type=float, default=0.35, help="Turn speed cap, rad/s")
    args = parser.parse_args(argv)
    for name in ("max_vx", "max_vy", "max_omega"):
        if not math.isfinite(getattr(args, name)) or getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be finite and positive")
    if args.list:
        for path, name, compatible in list_devices():
            print(f"{path}: {name}" + (" [compatible]" if compatible else ""))
        return
    client = WebClient(args.api, dry_run=args.dry_run)
    signal.signal(signal.SIGTERM, _terminate)
    print("[xbox] LB + neutral to engage; sticks walk/turn; release LB or B stops. "
          "Back/Xbox = LIMP. Use web UI Stand/Lower.", flush=True)
    previous_error = None
    try:
        while True:
            device = None
            try:
                paths = [args.device] if args.device else [p for p, _, ok in list_devices() if ok]
                if len(paths) != 1:
                    raise ControlError("No compatible gamepad; pair it, then check --list." if not paths
                                       else "Multiple compatible gamepads; select one with --device.")
                client.check_server()
                device = Device(paths[0])
                print(f"[xbox] connected {device.path}: {device.name}; release controls and center sticks.", flush=True)
                previous_error = None
                run_device(device, client, args)
            except (ControlError, OSError) as exc:
                message = str(exc)
                if message != previous_error:
                    print(f"[xbox] {message}", flush=True)
                    previous_error = message
            finally:
                if device is not None:
                    device.close()
                try:
                    client.stop()
                except ControlError as exc:
                    print(f"[xbox] stop unconfirmed: {exc}", flush=True)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("[xbox] stopped", flush=True)


if __name__ == "__main__":
    main()
