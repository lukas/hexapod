"""Incremental servo commissioning and small identification movements."""
import json
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
            reassign = data.get('reassign') is True
            if reassign and (data.get('isolated') is not True or before != [sid]):
                raise ValueError('Connect only the motor being reassigned and confirm it is isolated. Motors sharing an ID cannot be distinguished by a scan.')
            if not reassign and new_ids != [sid]:
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
            expected = sorted((set(before) - {sid}) | {target})
            observed = None
            for attempt in range(3):
                observed = self._scan(bus)
                if observed == expected:
                    break
                if attempt < 2:
                    time.sleep(0.1)
            else:
                raise ValueError(f'Motor verified at ID {target}, but assignment was not saved because the bus inventory changed. Expected IDs {expected}; received {observed}. Scan again and use Finish assignment on ID {target}.')
            now = datetime.now(timezone.utc).isoformat()
            name = f'L{joint // 3} {AXES[joint % 3]}'
            if reassign and data.get('clear_source') is True and sid != target:
                reg['servos'].pop(str(sid), None)
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
