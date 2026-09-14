"""Incremental servo commissioning and small identification movements."""
import json
import math
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

AXES = ('yaw', 'hip', 'knee')


class MotorSetup:
    def __init__(self, drive, bench, registry):
        self.drive, self.bench = drive, bench
        self.registry = Path(registry)
        self.lock = threading.Lock()
        self.abort = threading.Event()
        self.wiggling = False

    def _registry(self):
        if not self.registry.exists():
            return {'scheme': 'ids_2_to_19', 'servos': {}}
        data = json.loads(self.registry.read_text())
        if not isinstance(data.get('servos'), dict):
            raise ValueError('Motor registry is invalid; restore it before setup.')
        return data

    def status(self):
        reg = self._registry()
        slots = []
        for j in range(18):
            sid = j + 2
            entry = reg['servos'].get(str(sid), {})
            slots.append(dict(id=sid, joint=j, leg=j // 3, axis=AXES[j % 3],
                              name=f'L{j // 3} {AXES[j % 3]}',
                              saved=bool(entry), verified=bool(entry.get('web_verified_at'))))
        assigned = sum(slot["saved"] for slot in slots)
        return dict(ok=True, slots=slots, assigned=assigned, required=18, ready=assigned == 18)

    def require_setup_for(self, path, body):
        """Keep stop/setup operations available before motor commissioning."""
        if path == '/cmd' and body.strip().upper() in ('X', 'DISARM', 'RELAX', 'HOLD') or path.endswith('/stop'):
            self.abort.set()
            return
        if self.wiggling:
            raise ValueError('Motor identification is running; wait for it to finish.')
        if path.startswith('/api/setup') or path.startswith('/api/tft/') or path.endswith('/stop'):
            return
        if path == '/cmd' and body.strip().upper() in ('X', 'HOLD', 'J 0 0 0'):
            return
        if not self.status()['ready']:
            raise ValueError('Motor setup required: assign all 18 motors in Motor setup before using robot controls.')

    def _ready(self):
        d = self.drive
        if d.dry_run or d.bus is None:
            raise ValueError('No motor bus connected.')
        if d.armed or (self.bench._demo_thread and self.bench._demo_thread.is_alive()):
            raise ValueError('Stop any running activity and disarm before motor setup.')
        return d.bus

    def _scan(self, bus):
        # Bypass the MCU's two-second cached inventory after a cable swap.
        if hasattr(bus, '_live_cache'):
            bus._live_cache = None
        ids = sorted(bus.scan(range(1, 31)))
        if getattr(bus, 'last_scan_error', None):
            raise ValueError(bus.last_scan_error)
        return ids

    def scan(self):
        with self.lock, self.drive._lock:
            bus = self._ready()
            ids = self._scan(bus)
            new_ids = [sid for sid in ids if str(sid) not in self._registry()['servos']]
            assigned_ids = sorted(int(sid) for sid in self._registry()['servos'])
            return dict(ok=True, ids=ids, new_ids=new_ids, single=len(new_ids) == 1,
                        missing_ids=[sid for sid in assigned_ids if sid not in ids])

    def assign(self, data):
        sid, joint = data.get('source_id'), data.get('joint')
        if type(sid) is not int or not 1 <= sid <= 30:
            raise ValueError('Source ID must be between 1 and 30.')
        if type(joint) is not int or not 0 <= joint < 18:
            raise ValueError('Choose one of the 18 joints.')
        target = joint + 2
        with self.lock, self.drive._lock:
            bus = self._ready()
            reg = self._registry()
            if str(target) in reg['servos'] and data.get('replace') is not True:
                raise ValueError('This joint has a saved assignment. Confirm replacement first.')
            before = self._scan(bus)
            new_ids = [i for i in before if str(i) not in reg['servos']]
            if new_ids != [sid]:
                raise ValueError('Scan again with one new motor added; assigned motors can stay connected.')
            if target != sid and target in before:
                raise ValueError('The motor already assigned to this joint is still connected. Choose an empty joint.')
            bus.torque(sid, False)
            value, comm, err = bus.pkt.read1ByteTxRx(sid, 40)
            if comm != 0 or err != 0 or value != 0:
                raise ValueError('Could not verify torque is off; no ID was changed.')
            if not all(bus.ping(sid) for _ in range(3)):
                raise ValueError('Motor connection is unstable; no ID was changed.')
            if sid != target:
                bus.set_id(sid, target)
                time.sleep(0.15)
            value, comm, err = bus.pkt.read1ByteTxRx(target, 5)
            if comm != 0 or err != 0 or value != target or not bus.ping(target):
                raise ValueError('ID verification failed. Rescan before retrying; the ID may have changed.')
            if self._scan(bus) != sorted((set(before) - {sid}) | {target}):
                raise ValueError('Unexpected bus inventory after assignment. Rescan before retrying.')
            now = datetime.now(timezone.utc).isoformat()
            name = f'L{joint // 3} {AXES[joint % 3]}'
            reg['servos'][str(target)] = dict(id=target, joint=joint, leg=joint // 3,
                axis=AXES[joint % 3], name=name, from_id=sid, named_at=now, web_verified_at=now)
            reg['updated'] = now
            self.registry.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.registry.with_suffix('.json.tmp')
            tmp.write_text(json.dumps(reg, indent=2) + '\n')
            os.replace(tmp, self.registry)
            return dict(ok=True, id=target, name=name,
                        message=f'Verified {name} at ID {target}. Label it, leave it connected, then add and scan the next motor.')

    def wiggle(self, data):
        joint = data.get('joint')
        if type(joint) is not int or not 0 <= joint < 18:
            raise ValueError('Choose one of the 18 joints.')
        sid = joint + 2
        self.abort.clear()
        with self.lock, self.drive._lock:
            bus = self._ready()
            if str(sid) not in self._registry()['servos']:
                raise ValueError('Assign this motor before identifying it.')
            def read(addr, size=2):
                fn = bus.pkt.read1ByteTxRx if size == 1 else bus.pkt.read2ByteTxRx
                for _ in range(3):
                    value, comm, err = fn(sid, addr)
                    if comm == 0 and err == 0:
                        return value
                raise ValueError('Motor feedback unavailable; identification stopped.')
            def write(addr, value):
                _, comm, err = bus.pkt.write2ByteTxRx(sid, addr, value)
                if comm != 0 or err != 0:
                    raise ValueError('Motor setting could not be verified.')
            home = read(56)
            if not 0 <= home <= 4095 or read(40, 1) != 0:
                raise ValueError('Motor must be disarmed with a valid encoder reading.')
            if not 90 <= read(62, 1) <= 140 or read(63, 1) >= 60:
                raise ValueError('Check motor voltage and temperature before identifying it.')
            limit = read(48)
            self.wiggling = True
            try:
                write(48, min(limit, 150))
                # Set the current position before enabling torque: never jump to an old goal.
                if bus.pkt.WritePosEx(sid, home, 90, 4) != 0:
                    raise ValueError('Motor did not accept the position command.')
                if self.abort.is_set():
                    raise ValueError('Identification stopped.')
                bus.torque(sid, True)
                for target in (min(4095, home + 34), max(0, home - 34), home):
                    if self.abort.is_set():
                        raise ValueError('Identification stopped.')
                    if bus.pkt.WritePosEx(sid, target, 90, 4) != 0:
                        raise ValueError('Motor did not accept the position command.')
                    deadline = time.monotonic() + 1.5
                    while True:
                        if self.abort.wait(0.05):
                            raise ValueError('Identification stopped.')
                        load = read(60) & 0x3ff
                        current = read(69) & 0x7fff
                        if load >= 180 or current * 0.0065 >= 0.25:
                            raise ValueError('Motor met resistance; identification stopped.')
                        if abs(read(56) - target) < 12:
                            break
                        if time.monotonic() >= deadline:
                            raise ValueError('Motor did not reach the small identification target.')
                return dict(ok=True, message=f'L{joint // 3} {AXES[joint % 3]} identified; torque off.')
            finally:
                try:
                    bus.torque(sid, False)
                    if read(40, 1) != 0:
                        raise ValueError('Could not verify torque off after identification.')
                    write(48, limit)
                finally:
                    self.wiggling = False

    def nudge(self, data):
        """One relative, low-torque servo move, then torque off; never re-zero.

        Requires camera-confirmed support/clearance. The electrical guards do
        not establish a collision-free path or correct encoder calibration.
        """
        from feetech_bus import COUNTS_PER_DEG, JOINT_SIGN, count_to_deg, joint_limits

        if set(data) - {'joint', 'delta_deg'}:
            raise ValueError('Nudge accepts only joint and delta_deg; its guards are fixed.')
        joint, delta = data.get('joint'), data.get('delta_deg')
        if type(joint) is not int or not 0 <= joint < 18:
            raise ValueError('Choose one of the 18 joints.')
        if (type(delta) not in (int, float) or not math.isfinite(delta)
                or not 0 < abs(delta) <= 10):
            raise ValueError('delta_deg must be finite, nonzero, and within -10..10.')
        # Round toward zero so quantization never enlarges the requested move.
        delta_counts = math.trunc(delta * COUNTS_PER_DEG * JOINT_SIGN[joint])
        if not delta_counts:
            raise ValueError('delta_deg is smaller than one encoder count.')
        sid = joint + 2
        self.abort.clear()
        with self.lock, self.drive._lock:
            bus = self._ready()
            if str(sid) not in self._registry()['servos']:
                raise ValueError('Assign this motor before nudging it.')

            def read(addr, size=2, motor=sid):
                fn = bus.pkt.read1ByteTxRx if size == 1 else bus.pkt.read2ByteTxRx
                for _ in range(3):
                    value, comm, err = fn(motor, addr)
                    if comm == 0 and err == 0:
                        return value
                raise ValueError('Motor feedback unavailable; nudge stopped.')

            def write_limit(value):
                _, comm, err = bus.pkt.write2ByteTxRx(sid, 48, value)
                if comm != 0 or err != 0:
                    raise ValueError('Motor torque limit write failed.')

            # Software disarmed state alone does not prove the other 17 are off.
            if any(read(40, 1, motor) != 0 for motor in range(2, 20)):
                raise ValueError('All 18 motors must have torque off before nudging.')
            home = read(56)
            target = home + delta_counts
            before_deg, target_deg = count_to_deg(joint, home), count_to_deg(joint, target)
            lo, hi = joint_limits(joint)
            if not (0 <= home <= 4095 and 0 <= target <= 4095
                    and lo <= before_deg <= hi and lo <= target_deg <= hi):
                raise ValueError('Nudge start or target is outside encoder/joint limits.')
            if not 90 <= read(62, 1) <= 140 or read(63, 1) >= 60:
                raise ValueError('Check motor voltage and temperature before nudging.')
            limit = read(48)
            result = dict(ok=False, joint=joint, id=sid, before_deg=before_deg,
                          target_deg=target_deg, reached_deg=None, after_deg=None,
                          peak_current_a=0.0, max_load_pct=0.0, torque_off=False)
            force_reads = 0

            def observe():
                nonlocal force_reads
                # These are fresh servo-register transactions, not cached
                # /api/feedback snapshots. Isolated bad force samples reset.
                load = (read(60) & 0x3ff) / 10.0
                current = (read(69) & 0x7fff) * 0.0065
                result['peak_current_a'] = max(result['peak_current_a'], current)
                result['max_load_pct'] = max(result['max_load_pct'], load)
                force_reads = force_reads + 1 if load >= 18 or current >= 0.25 else 0
                if force_reads >= 3:
                    raise ValueError('Motor met resistance; nudge stopped.')
                if not 90 <= read(62, 1) <= 140 or read(63, 1) >= 60:
                    raise ValueError('Motor voltage or temperature unsafe; nudge stopped.')
                position = read(56)
                if not 0 <= position <= 4095:
                    raise ValueError('Invalid encoder reading; nudge stopped.')
                result['reached_deg'] = count_to_deg(joint, position)
                return position

            self.wiggling = True
            try:
                observe()
                while force_reads:
                    if self.abort.wait(0.05):
                        raise ValueError('Nudge stopped.')
                    observe()
                write_limit(min(limit, 150))
                # Clear an old servo goal before enabling this one motor.
                if bus.pkt.WritePosEx(sid, home, 90, 4) != 0:
                    raise ValueError('Motor did not accept the current-position preload.')
                if self.abort.is_set():
                    raise ValueError('Nudge stopped.')
                bus.torque(sid, True)
                if self.abort.is_set():
                    raise ValueError('Nudge stopped.')
                if bus.pkt.WritePosEx(sid, target, 90, 4) != 0:
                    raise ValueError('Motor did not accept the nudge target.')
                deadline = time.monotonic() + 3.0
                while True:
                    if self.abort.wait(0.05):
                        raise ValueError('Nudge stopped.')
                    position = observe()
                    if abs(position - target) <= 3 and force_reads == 0:
                        result['ok'] = True
                        break
                    if time.monotonic() >= deadline:
                        raise ValueError('Motor did not reach the small nudge target.')
            except Exception as exc:
                result['error'] = str(exc)
            finally:
                try:
                    bus.torque(sid, False)
                    if read(40, 1) != 0:
                        raise ValueError('Could not verify torque off after nudge.')
                    result['torque_off'] = True
                    write_limit(limit)
                    after = read(56)
                    if not 0 <= after <= 4095:
                        raise ValueError('Invalid post-nudge encoder reading.')
                    result['after_deg'] = count_to_deg(joint, after)
                except Exception as exc:
                    result['ok'] = False
                    result['error'] = '; '.join(filter(None, (result.get('error'), str(exc))))
                finally:
                    self.wiggling = False
            return result
