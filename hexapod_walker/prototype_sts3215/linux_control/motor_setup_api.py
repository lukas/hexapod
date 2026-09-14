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
            limit = read(48)
            result = dict(ok=False, joint=joint, id=sid, before_deg=before_deg,
                          target_deg=target_deg, reached_deg=None, after_deg=None,
                          peak_current_a=0.0, max_load_pct=0.0, torque_off=False,
                          voltage_v=None, temp_c=None, min_voltage_v=None,
                          max_voltage_v=None, max_temp_c=None,
                          voltage_fault_reads=0, temperature_fault_reads=0)
            force_reads = voltage_reads = temperature_reads = 0

            def observe():
                nonlocal force_reads, voltage_reads, temperature_reads
                # These are fresh servo-register transactions, not cached
                # /api/feedback snapshots. Each fault votes separately and
                # resets on its next healthy reading, including preflight.
                load = (read(60) & 0x3ff) / 10.0
                current = (read(69) & 0x7fff) * 0.0065
                result['peak_current_a'] = max(result['peak_current_a'], current)
                result['max_load_pct'] = max(result['max_load_pct'], load)
                force_reads = force_reads + 1 if load >= 18 or current >= 0.25 else 0
                if force_reads >= 3:
                    raise ValueError('Motor met resistance; nudge stopped.')
                voltage, temperature = read(62, 1) / 10.0, read(63, 1)
                voltage_reads = voltage_reads + 1 if not 9.0 <= voltage <= 14.0 else 0
                temperature_reads = temperature_reads + 1 if temperature >= 60 else 0
                result.update(voltage_v=voltage, temp_c=temperature,
                              voltage_fault_reads=voltage_reads,
                              temperature_fault_reads=temperature_reads)
                for key, value, reduce in (
                        ('min_voltage_v', voltage, min),
                        ('max_voltage_v', voltage, max),
                        ('max_temp_c', temperature, max)):
                    result[key] = value if result[key] is None else reduce(result[key], value)
                if voltage_reads >= 3:
                    raise ValueError(f'Motor voltage unsafe: {voltage:.1f} V outside 9.0..14.0 V '
                                     'on 3 consecutive fresh reads; nudge stopped.')
                if temperature_reads >= 3:
                    raise ValueError(f'Motor temperature unsafe: {temperature:g} C >= 60 C '
                                     'on 3 consecutive fresh reads; nudge stopped.')
                position = read(56)
                if not 0 <= position <= 4095:
                    raise ValueError('Invalid encoder reading; nudge stopped.')
                result['reached_deg'] = count_to_deg(joint, position)
                return position

            self.wiggling = True
            try:
                observe()
                while force_reads or voltage_reads or temperature_reads:
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
                    if (abs(position - target) <= 3
                            and not (force_reads or voltage_reads or temperature_reads)):
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

    def recovery_nudge(self, data):
        """Bounded raw recovery for L0/L4 and L1/L3/L5 support hip/knee joints.

        At most two joints move by <=5 degrees while selected joints hold
        their freshly read positions. The 200/1000 torque cap, 90 speed,
        4 acceleration and 3-second active bound are fixed; a hold-only
        probe lasts one second. An optional two-phase plan keeps supports
        enabled between phases, each bounded to 3 seconds (6 seconds total).
        Phase targets are cumulative raw deltas from the initial pose;
        settling admits <=2-degree error, not exact target achievement.
        Explicit l4_30pct effort permits only a single outward L4 knee move
        with all five specified supports; that knee alone is capped at 300.
        l4_50pct permits up to 10 degrees with that knee alone capped at 500;
        both explicit profiles retain the 3-second bound and 1 A hard stop.
        This never re-zeros or returns home.
        """
        from feetech_bus import COUNTS_PER_DEG, JOINT_SIGN, count_to_deg, joint_limits

        if not isinstance(data, dict) or set(data) - {'deltas_deg', 'hold_joints', 'phases', 'effort_profile'}:
            raise ValueError('Recovery accepts deltas_deg or phases, hold_joints, and optional effort_profile.')
        effort_profile = data.get('effort_profile')
        if 'effort_profile' in data and effort_profile not in ('l4_30pct', 'l4_50pct'):
            raise ValueError('Unknown recovery effort profile.')
        profile_cap, profile_current, profile_load, delta_bound = (
            (500, .75, 53., 10) if effort_profile == 'l4_50pct' else (300, .5, 33., 5))
        phased = 'phases' in data
        if phased and ('deltas_deg' in data or not isinstance(data['phases'], list)
                       or len(data['phases']) != 2
                       or any(not isinstance(p, dict) or set(p) != {'deltas_deg'}
                              for p in data['phases'])):
            raise ValueError('Provide exactly two phases with deltas_deg, without top-level deltas_deg.')
        phase_deltas = ([p['deltas_deg'] for p in data['phases']] if phased
                        else [data.get('deltas_deg', {})])
        holds = data.get('hold_joints', [])
        allowed = {1, 2, 4, 5, 10, 11, 13, 14, 16, 17}
        if (not isinstance(holds, list) or any(type(j) is not int or j not in allowed for j in holds)
                or len(set(holds)) != len(holds)):
            raise ValueError('hold_joints must contain distinct joints from 1,2,4,5,10,11,13,14,16,17.')
        phase_offsets, phase_pairs = [], []
        for deltas in phase_deltas:
            if (not isinstance(deltas, dict) or len(deltas) > 2 or (phased and not deltas)
                    or any(key not in {'1', '2', '4', '5', '10', '11', '13', '14', '16', '17'} for key in deltas)):
                raise ValueError('Choose at most two moving joints from 1,2,4,5,10,11,13,14,16,17 per phase.')
            offsets = {}
            for key, delta in deltas.items():
                if (type(delta) not in (int, float) or not math.isfinite(delta)
                        or not 0 < abs(delta) <= delta_bound):
                    raise ValueError(f'Each raw delta must be finite, nonzero and within -{delta_bound}..{delta_bound} degrees.')
                joint = int(key)
                offset = math.trunc(delta * COUNTS_PER_DEG * JOINT_SIGN[joint])
                if not offset:
                    raise ValueError('Recovery delta is smaller than one encoder count.')
                offsets[joint] = offset
            phase_offsets.append(offsets)
            phase_pairs.append(next(((hip, hip + 1) for hip in (1, 4, 10, 13, 16)
                if hip in offsets and hip + 1 in offsets
                and deltas[str(hip)] * deltas[str(hip + 1)] < 0
                and math.isclose(deltas[str(hip)] + deltas[str(hip + 1)], 0., abs_tol=.1)), None))
        moving = set().union(*phase_offsets)
        if moving & set(holds):
            raise ValueError('A joint cannot both move and hold.')
        if effort_profile and (phased or moving != {14} or phase_deltas[0]['14'] >= 0
                               or set(holds) != {10, 11, 13, 16, 17}):
            raise ValueError(f'{effort_profile} requires one outward joint14 move and holds10,11,13,16,17, without phases.')
        participants = sorted(moving | set(holds))
        if not 1 <= len(participants) <= 6:
            raise ValueError('Choose one to six recovery participants.')
        phase_index = 0
        offsets, pair_joints = phase_offsets[0], phase_pairs[0]
        duration = 3.0 if offsets else 1.0
        self.abort.clear()
        with self.lock, self.drive._lock:
            bus = self._ready()
            registered = self._registry()['servos']
            if any(str(j + 2) not in registered for j in participants):
                raise ValueError('Assign every recovery participant before moving.')
            deadline = None
            active_start = None
            active_healthy_scan = False
            partial_bad_health = False

            class ActiveDeadline(TimeoutError):
                pass

            def check():
                if self.abort.is_set():
                    raise ValueError('Recovery stopped.')
                if deadline is not None and time.monotonic() >= deadline:
                    raise ActiveDeadline('Recovery active time limit reached.')

            def read(sid, addr, size=2, *, guarded=True):
                fn = bus.pkt.read1ByteTxRx if size == 1 else bus.pkt.read2ByteTxRx
                for _ in range(3):
                    if guarded:
                        check()
                    value, comm, err = fn(sid, addr)
                    if comm == 0 and err == 0:
                        return value
                raise ValueError(f'Servo {sid} feedback unavailable at register {addr}.')

            def write_limit(sid, value, *, guarded=True):
                if guarded:
                    check()
                _, comm, err = bus.pkt.write2ByteTxRx(sid, 48, value)
                if comm != 0 or err != 0 or read(sid, 48, guarded=guarded) != value:
                    raise ValueError(f'Servo {sid} torque limit unverified.')

            if any(read(sid, 40, 1) != 0 for sid in range(2, 20)):
                raise ValueError('All 18 motors must have torque off before recovery.')
            result = dict(ok=False, joint_frame='servo_relative', joints={}, torque_off=False,
                          active_seconds=0., pair_error_deg=0., max_pair_error_deg=0., pair_fault_reads=0,
                          effort_profile=effort_profile or 'default')
            if phased:
                result.update(phase_index=1, phases=[dict(index=i + 1, deltas_deg=dict(d),
                              settled=False) for i, d in enumerate(phase_deltas)])
            homes, targets, limits, pair_homes = {}, {}, {}, {}
            planned_targets = [{} for _ in phase_offsets]
            phase_start = None

            def set_start(j, count):
                before = count_to_deg(j, count)
                lo, hi = joint_limits(j)
                if not (0 <= count <= 4095 and lo <= before <= hi):
                    raise ValueError(f'Joint {j} recovery start or target outside raw limits.')
                target = count
                for i, changes in enumerate(phase_offsets):
                    target += changes.get(j, 0)
                    if not (0 <= target <= 4095 and lo <= count_to_deg(j, target) <= hi):
                        raise ValueError(f'Joint {j} recovery start or target outside raw limits.')
                    planned_targets[i][j] = target
                homes[j], pair_homes[j], targets[j] = count, count, planned_targets[0][j]
                goal = count_to_deg(j, targets[j])
                result['joints'][str(j)].update(before_deg=before, target_deg=goal,
                                                before_counts=count, target_counts=targets[j])

            for j in participants:
                result['joints'][str(j)] = dict(
                    joint=j, id=j + 2, role='move' if j in offsets else 'hold',
                    reached_deg=None, after_deg=None, torque_off=False,
                    current_a=None, peak_current_a=0., load_pct=None, max_load_pct=0.,
                    voltage_v=None, temp_c=None, min_voltage_v=None, max_voltage_v=None,
                    max_temp_c=None, support_drift_deg=0., max_support_drift_deg=0.,
                    force_fault_reads=0, voltage_fault_reads=0,
                    temperature_fault_reads=0, support_drift_fault_reads=0, samples=0,
                    current_soft_limit_a=profile_current if effort_profile and j == 14 else .25,
                    load_soft_limit_pct=profile_load if effort_profile and j == 14 else 23.,
                    torque_enabled=None, torque_read_values=[], servo_status=None, seen_statuses=[], moving=None,
                    accepted_goal_counts=None, observed_goal_counts=None,
                    observed_torque_limit=None, last_sample_monotonic_s=None, active_sample_s=None)
                set_start(j, read(j + 2, 56))
                limits[j] = read(j + 2, 48)
                result['joints'][str(j)].update(saved_torque_limit=limits[j],
                                                applied_torque_limit=None)
                result['joints'][str(j)]['protection_config'] = {
                    name: read(j + 2, addr, size) for name, addr, size in (
                        ('unload_mask', 19, 1), ('current_protection_raw', 28, 2),
                        ('mode', 33, 1), ('protection_torque_raw', 34, 1),
                        ('protection_time_raw', 35, 1), ('overload_torque_raw', 36, 1))}

            def pending():
                return result['pair_fault_reads'] or any(
                    row[key] for row in result['joints'].values() for key in (
                        'force_fault_reads', 'voltage_fault_reads',
                        'temperature_fault_reads', 'support_drift_fault_reads'))

            def observe():
                nonlocal active_healthy_scan, partial_bad_health
                partial_bad_health = False
                positions = {}
                for j in participants:
                    sid, row = j + 2, result['joints'][str(j)]
                    if active_start is not None:
                        row['servo_status'] = read(sid, 65, 1)
                        if row['servo_status'] not in row['seen_statuses']:
                            row['seen_statuses'].append(row['servo_status'])
                        if (phased or effort_profile) and row['servo_status'] != 0:
                            raise ValueError(f'Joint {j} servo status fault {row["servo_status"]} during recovery phase.')
                        row['moving'] = read(sid, 66, 1)
                        row['torque_enabled'] = read(sid, 40, 1)
                        row['torque_read_values'].append(row['torque_enabled'])
                        # One corrupt status byte must not masquerade as a
                        # lost support. Confirm with fresh register reads;
                        # never re-enable or rewrite a goal in this path.
                        for _ in range(2):
                            if row['torque_enabled'] == 1:
                                break
                            partial_bad_health = True
                            row['torque_enabled'] = read(sid, 40, 1)
                            row['torque_read_values'].append(row['torque_enabled'])
                        row['last_sample_monotonic_s'] = time.monotonic()
                        row['active_sample_s'] = row['last_sample_monotonic_s'] - active_start
                        if row['torque_enabled'] != 1:
                            raise ValueError(f'Joint {j} torque unexpectedly off '
                                             f'(value={row["torque_enabled"]}, status={row["servo_status"]}).')
                        row['observed_goal_counts'] = read(sid, 42)
                        if row['observed_goal_counts'] != targets[j]:
                            raise ValueError(f'Joint {j} goal changed: {row["observed_goal_counts"]}, expected {targets[j]}.')
                        row['observed_torque_limit'] = read(sid, 48)
                        if row['observed_torque_limit'] != row['applied_torque_limit']:
                            raise ValueError(f'Joint {j} torque limit changed: {row["observed_torque_limit"]}, '
                                             f'expected {row["applied_torque_limit"]}.')
                    current = (read(sid, 69) & 0x7fff) * .0065
                    row.update(current_a=current, peak_current_a=max(row['peak_current_a'], current))
                    partial_bad_health |= current >= row['current_soft_limit_a']
                    if current >= 1.0:
                        raise ValueError(f'Joint {j} hard current {current:.3f} A >= 1 A.')
                    load = (read(sid, 60) & 0x3ff) / 10.
                    row.update(load_pct=load, max_load_pct=max(row['max_load_pct'], load))
                    partial_bad_health |= load >= row['load_soft_limit_pct']
                    voltage = read(sid, 62, 1) / 10.
                    row['voltage_v'] = voltage
                    row['min_voltage_v'] = voltage if row['min_voltage_v'] is None else min(row['min_voltage_v'], voltage)
                    row['max_voltage_v'] = voltage if row['max_voltage_v'] is None else max(row['max_voltage_v'], voltage)
                    partial_bad_health |= not 9. <= voltage <= 14.
                    temperature = read(sid, 63, 1)
                    row['temp_c'] = temperature
                    row['max_temp_c'] = temperature if row['max_temp_c'] is None else max(row['max_temp_c'], temperature)
                    partial_bad_health |= temperature >= 60
                    count = read(sid, 56)
                    if not 0 <= count <= 4095:
                        raise ValueError(f'Joint {j} invalid raw encoder reading.')
                    positions[j] = count
                    angle = count_to_deg(j, count)
                    # A prior phase's mover becomes a support without losing
                    # its command. Anchor to that goal, not a sagged reading.
                    anchor = row['target_deg'] if phased else row['before_deg']
                    drift = abs(angle - anchor) if j not in offsets else 0.
                    partial_bad_health |= drift > 3.
                    row.update(reached_deg=angle, reached_counts=count, support_drift_deg=drift,
                               max_support_drift_deg=max(row['max_support_drift_deg'], drift),
                               samples=row['samples'] + 1)
                    faults = {'force': current >= row['current_soft_limit_a']
                                      or load >= row['load_soft_limit_pct'],
                              'voltage': not 9. <= voltage <= 14.,
                              'temperature': temperature >= 60,
                              'support_drift': drift > 3.}
                    for name, bad in faults.items():
                        key = name + '_fault_reads'
                        row[key] = row[key] + 1 if bad else 0
                        if row[key] >= 3:
                            raise ValueError(f'Joint {j} {name} fault on 3 consecutive fresh reads '
                                             f'({current:.3f} A, {load:.1f}% load, {voltage:.1f} V, '
                                             f'{temperature:g} C, support drift {drift:.2f} deg).')
                    if pair_joints and j == pair_joints[1]:
                        # Both moving-joint reads are fresh now: check their
                        # coupling before spending time on support telemetry.
                        error = sum(result['joints'][str(k)]['reached_deg']
                                    - count_to_deg(k, pair_homes[k]) for k in pair_joints)
                        result['pair_error_deg'] = error
                        result['max_pair_error_deg'] = max(result['max_pair_error_deg'], abs(error))
                        result['pair_fault_reads'] = result['pair_fault_reads'] + 1 if abs(error) > 1.5 else 0
                        if abs(error) > 2.5 or result['pair_fault_reads'] >= 3:
                            raise ValueError(f'L{pair_joints[0] // 3} hip/knee actual pair mismatch {error:.2f} deg.')
                if active_start is not None:
                    active_healthy_scan = not pending()
                return positions

            def write_targets():
                group = bus.pkt.groupSyncWrite
                group.clearParam()
                try:
                    for j in sorted(offsets):
                        check()
                        bus.pkt.SyncWritePosEx(j + 2, targets[j], 90, 4)
                    check()
                    if group.txPacket() not in (None, 0):
                        raise ValueError('Recovery coordinated target write failed.')
                finally:
                    group.clearParam()
                for j in sorted(offsets):
                    accepted = read(j + 2, 42)
                    result['joints'][str(j)]['accepted_goal_counts'] = accepted
                    if accepted != targets[j]:
                        raise ValueError(f'Joint {j} recovery target not accepted: {accepted}, expected {targets[j]}.')

            self.wiggling = True
            try:
                preflight_end = time.monotonic() + 3.
                observe()
                while pending():
                    if self.abort.wait(.05):
                        raise ValueError('Recovery stopped.')
                    if time.monotonic() >= preflight_end:
                        raise TimeoutError('Recovery health preflight did not clear.')
                    observe()
                # Refresh raw starts after health admission, validate every
                # endpoint, then preload/verify all goals before any enable.
                for j in participants:
                    set_start(j, read(j + 2, 56))
                for j in participants:
                    sid = j + 2
                    applied = min(limits[j], profile_cap if effort_profile and j == 14 else 200)
                    write_limit(sid, applied)
                    result['joints'][str(j)]['applied_torque_limit'] = applied
                    check()
                    if bus.pkt.WritePosEx(sid, homes[j], 90, 4) != 0:
                        raise ValueError(f'Joint {j} present-position preload failed.')
                    if read(sid, 42) != homes[j]:
                        raise ValueError(f'Joint {j} present-position preload unverified.')
                    result['joints'][str(j)]['accepted_goal_counts'] = homes[j]
                active_start = time.monotonic()
                deadline = active_start + duration
                total_deadline = active_start + 6. if phased else deadline
                phase_start = active_start
                if phased:
                    result['phases'][0].update(started_active_s=0., start_counts=dict(homes),
                                               target_counts=dict(targets))
                for j in participants:
                    check()
                    bus.torque(j + 2, True)
                    if read(j + 2, 40, 1) != 1:
                        raise ValueError(f'Joint {j} torque enable unverified.')
                if offsets:
                    write_targets()
                settled_scans = []
                while True:
                    positions = observe()
                    if phased:
                        check()
                        phase = result['phases'][phase_index]
                        phase.update(reached_counts=dict(positions),
                                     elapsed_s=time.monotonic() - phase_start)
                        if (not pending() and not partial_bad_health
                                and all(row['servo_status'] == 0 for row in result['joints'].values())
                                and all(abs(positions[j] - targets[j]) <= 2 * COUNTS_PER_DEG
                                        for j in offsets)):
                            settled_scans.append(dict(counts=positions,
                                                      active_s=time.monotonic() - active_start))
                            settled_scans = settled_scans[-3:]
                        else:
                            settled_scans.clear()
                        if len(settled_scans) == 3 and all(
                                max(scan['counts'][j] for scan in settled_scans)
                                - min(scan['counts'][j] for scan in settled_scans) <= 3
                                for j in participants):
                            phase['settled'] = True
                            phase['settle_scans'] = list(settled_scans)
                            if phase_index == 1:
                                result['ok'] = True
                                break
                            # All next endpoints were preflighted while off.
                            # Fresh feedback validates the immutable plan;
                            # drift must not enlarge a step beyond five degrees.
                            for j in phase_offsets[1]:
                                if abs(planned_targets[1][j] - positions[j]) > 5 * COUNTS_PER_DEG:
                                    raise ValueError(f'Joint {j} next phase exceeds five degrees from its actual position.')
                            check()
                            transition_time = time.monotonic()
                            if transition_time >= deadline:
                                raise ActiveDeadline('Recovery active time limit reached before phase transition.')
                            phase_index = 1
                            result['phase_index'] = 2
                            offsets, pair_joints = phase_offsets[1], phase_pairs[1]
                            targets.update(planned_targets[1])
                            pair_homes.update(positions)
                            for j, row in ((int(key), value) for key, value in result['joints'].items()):
                                row.update(role='move' if j in offsets else 'hold',
                                           target_counts=targets[j], target_deg=count_to_deg(j, targets[j]))
                            phase_start = transition_time
                            deadline = min(total_deadline, phase_start + 3.)
                            result['phases'][1].update(started_active_s=phase_start - active_start,
                                                      start_counts=dict(positions), target_counts=dict(targets))
                            settled_scans.clear()
                            write_targets()
                            continue
                    elif offsets and not pending() and all(abs(positions[j] - targets[j]) <= 3 for j in offsets):
                        check()
                        result['ok'] = True
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        if not offsets and not pending():
                            result['ok'] = True
                            break
                        raise TimeoutError('Recovery active time limit reached.')
                    if self.abort.wait(min(.05, remaining)):
                        raise ValueError('Recovery stopped.')
                    if not offsets and time.monotonic() >= deadline:
                        if pending():
                            raise ValueError('Recovery hold ended with pending health votes.')
                        result['ok'] = True
                        break
            except ActiveDeadline as exc:
                # A one-second hold can end between register reads. A
                # completed healthy ACTIVE sweep is required, and any bad
                # partial observation prevents a success claim. Cleanup
                # starts now; the deadline is never extended for a scan.
                if not offsets and active_healthy_scan and not partial_bad_health and not pending():
                    result['ok'] = True
                else:
                    result['error'] = str(exc)
            except Exception as exc:
                result['error'] = str(exc)
            finally:
                if phased and phase_start is not None:
                    result['phases'][phase_index]['elapsed_s'] = time.monotonic() - phase_start
                    if result.get('error'):
                        result['phases'][phase_index]['error'] = result['error']
                errors = []
                # Off commands for ALL participants precede any verification
                # or limit restoration. One failed servo cannot skip others.
                for j in participants:
                    try:
                        bus.torque(j + 2, False)
                    except Exception as exc:
                        errors.append(f'Joint {j} torque-off command: {exc}')
                if active_start is not None:
                    result['active_seconds'] = time.monotonic() - active_start
                for j in participants:
                    try:
                        if read(j + 2, 40, 1, guarded=False) != 0:
                            raise ValueError('torque remains enabled')
                        result['joints'][str(j)]['torque_off'] = True
                    except Exception as exc:
                        errors.append(f'Joint {j} torque off unverified: {exc}')
                result['torque_off'] = all(row['torque_off'] for row in result['joints'].values())
                for j in participants:
                    if result['torque_off']:
                        try:
                            write_limit(j + 2, limits[j], guarded=False)
                        except Exception as exc:
                            errors.append(f'Joint {j} limit restore: {exc}')
                    try:
                        after = read(j + 2, 56, guarded=False)
                        if not 0 <= after <= 4095:
                            raise ValueError('invalid raw encoder reading')
                        result['joints'][str(j)].update(after_counts=after, after_deg=count_to_deg(j, after))
                    except Exception as exc:
                        errors.append(f'Joint {j} post-recovery feedback: {exc}')
                if errors:
                    result['ok'] = False
                    result['error'] = '; '.join(filter(None, [result.get('error'), *errors]))
                self.wiggling = False
            return result
