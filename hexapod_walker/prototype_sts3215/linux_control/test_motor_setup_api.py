import json, sys, tempfile, threading, unittest
from io import BytesIO
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
from motor_setup_api import MotorSetup

class Bus:
    def __init__(self, ids=(1,)):
        self.ids=list(ids); self.pkt=self; self.writes=[]; self.failed=False; self.t=0
    def scan(self, ids): return self.ids[:]
    def ping(self, sid): return sid in self.ids
    def torque(self, sid, on): self.writes.append(('torque',sid,on))
    def set_id(self, old, new):
        self.writes.append(('id',old,new))
        if not self.failed: self.ids=[new if i==old else i for i in self.ids]
    def read1ByteTxRx(self, sid, addr):
        return (self.t if addr==40 else sid, 0 if sid in self.ids else -1, 0)

class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.bus=Bus(); self.drive=SimpleNamespace(bus=self.bus, dry_run=False, armed=False, _lock=threading.Lock())
        self.api=MotorSetup(self.drive,SimpleNamespace(_demo_thread=None),Path(self.tmp.name)/'registry.json')
        self.data=dict(source_id=1,joint=0)
    def test_assign_verified_and_persisted(self):
        self.assertEqual(self.api.assign(self.data)['id'],2)
        self.assertTrue(self.api.status()['slots'][0]['verified'])
        self.assertEqual(self.bus.writes,[('torque',1,False),('id',1,2)])
    def test_multiple_or_swapped_motors_no_writes(self):
        for ids in ([1,2],[3],[]):
            self.bus.ids=ids
            with self.assertRaises(ValueError): self.api.assign(self.data)
        self.assertEqual(self.bus.writes,[])
    def test_armed_no_writes(self):
        self.drive.armed=True
        with self.assertRaises(ValueError): self.api.assign(self.data)
        self.assertEqual(self.bus.writes,[])
    def test_bad_joint_no_writes(self):
        for changes in ({'joint':18},{'joint':True},{'source_id':254}):
            with self.assertRaises(ValueError): self.api.assign(self.data|changes)
        self.assertEqual(self.bus.writes,[])
    def test_failed_write_does_not_record_success(self):
        self.bus.failed=True
        with self.assertRaises(ValueError): self.api.assign(self.data)
        self.assertFalse(self.api.registry.exists())
    def test_torque_verification_prevents_id_write(self):
        self.bus.t=1
        with self.assertRaises(ValueError): self.api.assign(self.data)
        self.assertFalse(any(w[0]=='id' for w in self.bus.writes))
    def test_replacement_requires_explicit_confirmation(self):
        self.api.assign(self.data); self.bus.ids=[1]; self.bus.writes=[]
        with self.assertRaises(ValueError): self.api.assign(self.data)
        self.assertEqual(self.bus.writes,[])
        self.api.assign(self.data|{'replace':True})
    def test_two_robots_do_not_share_assignments(self):
        other = MotorSetup(self.drive, self.api.bench, Path(self.tmp.name)/'other-robot.json')
        self.api.assign(self.data)
        self.assertTrue(self.api.status()['slots'][0]['saved'])
        self.assertFalse(any(slot['saved'] for slot in other.status()['slots']))

    def test_controls_require_setup_but_stop_and_setup_work(self):
        for path, body in [('/cmd','ARM'),('/api/zero','{}'),('/api/set_zero','{}')]:
            with self.assertRaises(ValueError): self.api.require_setup_for(path, body)
        for path, body in [('/cmd','X'),('/api/setup/scan','{}'),('/api/demo/stop','{}')]:
            self.api.require_setup_for(path, body)
        reg={'servos': {str(j+2): {'id':j+2, 'joint':j} for j in range(18)}}
        self.api.registry.write_text(json.dumps(reg))
        self.api.require_setup_for('/cmd','ARM')

    def test_incremental_chain_and_collision(self):
        self.api.assign(self.data)
        self.bus.ids.append(1)
        self.assertEqual(self.api.scan()['new_ids'], [1])
        with self.assertRaises(ValueError): self.api.assign(self.data | {'replace': True})
        self.api.assign(dict(source_id=1, joint=1))
        self.assertEqual(sorted(self.bus.ids), [2, 3])
        self.assertEqual(self.api.status()['assigned'], 2)
        self.assertEqual(self.api.scan()['new_ids'], [])

    def test_scan_distinguishes_missing_assigned_and_new_ids(self):
        self.api.assign(self.data)
        self.bus.ids = [1]
        result = self.api.scan()
        self.assertEqual(result['new_ids'], [1])
        self.assertEqual(result['missing_ids'], [2])
        self.bus.ids = []
        self.assertEqual(self.api.scan()['ids'], [])

    def test_scan_transport_failure_is_not_an_empty_inventory(self):
        self.bus.ids = []
        self.bus.last_scan_error = 'Controller timeout'
        with self.assertRaisesRegex(ValueError, 'Controller timeout'):
            self.api.scan()

    def wiggle_bus(self):
        self.api.assign(self.data)
        self.bus.ids.append(3)
        self.bus.writes=[]
        self.bus.pos=2000
        self.bus.limit=500
        self.bus.read1ByteTxRx=lambda sid,addr: ({40:0,62:114,63:30}[addr],0,0)
        self.bus.read2ByteTxRx=lambda sid,addr: ({56:self.bus.pos,48:self.bus.limit,60:0,69:0}[addr],0,0)
        def write(sid,addr,value):
            self.bus.writes.append(('limit',sid,value)); self.bus.limit=value
            return 0,0,0
        def position(sid,pos,speed,acc):
            self.bus.writes.append(('position',sid,pos)); self.bus.pos=pos
            return 0
        self.bus.write2ByteTxRx=write
        self.bus.WritePosEx=position

    def test_wiggle_only_selected_motor_and_restores(self):
        self.wiggle_bus()
        self.api.wiggle({'joint':0})
        self.assertTrue(all(w[1]==2 for w in self.bus.writes))
        self.assertEqual([w[2] for w in self.bus.writes if w[0]=='position'],[2000,2034,1966,2000])
        self.assertEqual(self.bus.writes[-2:], [('torque',2,False),('limit',2,500)])

    def test_wiggle_failure_and_stop_cleanup(self):
        for stop in (False, True):
            self.wiggle_bus()
            def position(*args):
                if stop: self.api.require_setup_for('/cmd','X')
                return 0 if stop else -1
            self.bus.WritePosEx=position
            with self.assertRaises(ValueError): self.api.wiggle({'joint':0})
            self.assertFalse(self.api.wiggling)
            self.assertEqual(self.bus.writes[-2:], [('torque',2,False),('limit',2,500)])
            self.api.registry.unlink()
            self.bus=Bus(); self.drive.bus=self.bus

    def test_busy_worker(self):
        self.api.bench._demo_thread=SimpleNamespace(is_alive=lambda:True)
        with self.assertRaises(ValueError): self.api.assign(self.data)
        self.assertEqual(self.bus.writes,[])

    def nudge_bus(self):
        self.wiggle_bus()
        self.bus.ids = list(range(2, 20))
        self.bus.on = set()
        self.bus.current = self.bus.load = 0
        def torque(sid, on):
            self.bus.writes.append(('torque', sid, on))
            self.bus.on.add(sid) if on else self.bus.on.discard(sid)
        self.bus.torque = torque
        self.bus.read1ByteTxRx = lambda sid, addr: (
            {40: int(sid in self.bus.on), 62:114, 63:30}[addr], 0, 0)
        self.bus.read2ByteTxRx = lambda sid, addr: (
            {56:self.bus.pos, 48:self.bus.limit, 60:self.bus.load,
             69:self.bus.current}[addr], 0, 0)

    def test_nudge_preloads_only_selected_servo_without_returning_home(self):
        self.nudge_bus()
        result = self.api.nudge({'joint': 0, 'delta_deg': 3.0})
        self.assertTrue(result['ok'])
        self.assertEqual(self.bus.writes, [
            ('limit', 2, 150), ('position', 2, 2000), ('torque', 2, True),
            ('position', 2, 2034), ('torque', 2, False), ('limit', 2, 500)])
        self.assertEqual(result['reached_deg'], result['after_deg'])
        self.assertEqual(result['target_deg'], result['after_deg'])
        self.assertGreater(result['after_deg'], result['before_deg'])
        self.assertTrue(result['torque_off'])
        self.assertFalse(self.bus.on)

    def test_nudge_preserves_lower_torque_and_negative_delta(self):
        self.nudge_bus()
        self.bus.limit = 90
        result = self.api.nudge({'joint': 0, 'delta_deg': -3})
        self.assertTrue(result['ok'])
        self.assertEqual(self.bus.writes[0], ('limit', 2, 90))
        self.assertEqual(self.bus.pos, 1966)

    def test_nudge_rejects_invalid_input_and_out_of_limit_target_without_writes(self):
        self.nudge_bus()
        for data in ({'joint':True, 'delta_deg':3}, {'joint':18, 'delta_deg':3},
                     *({'joint':0, 'delta_deg':v} for v in
                       [None, True, '3', 0, .001, 10.1, float('nan'), float('inf')]),
                     {'joint':0, 'delta_deg':3, 'force':True}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.api.nudge(data)
        self.bus.pos = 2440  # yaw near +35 degrees
        with self.assertRaisesRegex(ValueError, 'limits'):
            self.api.nudge({'joint':0, 'delta_deg':3})
        self.assertEqual(self.bus.writes, [])

    def test_nudge_requires_other_servos_off(self):
        self.nudge_bus()
        self.bus.on.add(19)
        with self.assertRaisesRegex(ValueError, 'All 18'):
            self.api.nudge({'joint':0, 'delta_deg':3})
        self.assertEqual(self.bus.writes, [])

    def test_nudge_resistance_records_fault_and_disables_before_restoring_limit(self):
        for current, load in [(39, 0), (0, 180)]:
            self.nudge_bus()
            original = self.bus.WritePosEx
            def position(sid, pos, speed, acc):
                response = original(sid, pos, speed, acc)
                if pos != 2000:
                    self.bus.current, self.bus.load = current, load
                return response
            self.bus.WritePosEx = position
            result = self.api.nudge({'joint':0, 'delta_deg':3})
            self.assertFalse(result['ok'])
            self.assertIn('resistance', result['error'])
            self.assertEqual(result['peak_current_a'], current * .0065)
            self.assertEqual(result['max_load_pct'], load / 10)
            self.assertEqual(self.bus.writes[-2:], [('torque',2,False),('limit',2,500)])
            self.assertFalse(self.bus.on)
            self.api.registry.unlink()
            self.bus = Bus(); self.drive.bus = self.bus

    def test_nudge_abort_prevents_target_and_disables_servo(self):
        self.nudge_bus()
        original = self.bus.torque
        def torque(sid, on):
            original(sid, on)
            if on:
                self.api.require_setup_for('/cmd', 'X')
        self.bus.torque = torque
        result = self.api.nudge({'joint':0, 'delta_deg':3})
        self.assertFalse(result['ok'])
        self.assertIn('stopped', result['error'])
        self.assertEqual([w[2] for w in self.bus.writes if w[0]=='position'], [2000])
        self.assertFalse(self.bus.on)

    def test_nudge_isolated_force_sample_clears_instead_of_ending_move(self):
        self.nudge_bus()
        original = self.bus.read2ByteTxRx
        force_samples = iter([39, 0])
        seen = []
        def read(sid, addr):
            if self.bus.on and addr == 69:
                value = next(force_samples)
                seen.append(value)
                return value, 0, 0
            return original(sid, addr)
        self.bus.read2ByteTxRx = read
        result = self.api.nudge({'joint':0, 'delta_deg':3})
        self.assertTrue(result['ok'])
        self.assertEqual(seen, [39, 0])
        self.assertGreater(result['peak_current_a'], .25)
        self.assertTrue(result['torque_off'])

    def test_nudge_force_vote_resets_and_requires_three_consecutive_reads(self):
        self.nudge_bus()
        original = self.bus.read2ByteTxRx
        force_samples = iter([39, 0, 39, 39, 39])
        seen = []
        def read(sid, addr):
            if self.bus.on and addr == 69:
                value = next(force_samples)
                seen.append(value)
                return value, 0, 0
            if self.bus.on and addr == 56:
                return 2000, 0, 0  # not yet at target when sample clears
            return original(sid, addr)
        self.bus.read2ByteTxRx = read
        result = self.api.nudge({'joint':0, 'delta_deg':3})
        self.assertFalse(result['ok'])
        self.assertIn('resistance', result['error'])
        self.assertEqual(seen, [39, 0, 39, 39, 39])
        self.assertTrue(result['torque_off'])

    def nudge_health_samples(self, samples, *, during_motion=True):
        self.nudge_bus()
        original = self.bus.read1ByteTxRx
        samples = iter(samples)
        seen = []
        pair = None
        def read(sid, addr):
            nonlocal pair
            if addr in (62, 63) and (self.bus.on or not during_motion):
                if addr == 62:
                    pair = next(samples)
                    seen.append(pair)
                return pair[addr - 62], 0, 0
            return original(sid, addr)
        self.bus.read1ByteTxRx = read
        return seen

    def test_nudge_isolated_health_votes_clear_before_target_completion(self):
        # The fake reaches its target immediately. Pending health votes
        # must still force a fresh read; alternating fault types cannot add.
        samples = [(88, 30), (114, 60), (141, 30), (114, 30)]
        seen = self.nudge_health_samples(samples)
        result = self.api.nudge({'joint':0, 'delta_deg':3})
        self.assertTrue(result['ok'])
        self.assertEqual(seen, samples)
        self.assertEqual(result['voltage_fault_reads'], 0)
        self.assertEqual(result['temperature_fault_reads'], 0)
        self.assertEqual((result['voltage_v'], result['temp_c']), (11.4, 30))
        self.assertEqual((result['min_voltage_v'], result['max_voltage_v'], result['max_temp_c']),
                         (8.8, 14.1, 60))
        self.assertTrue(result['torque_off'])

    def test_nudge_three_fresh_health_faults_trip_with_actual_values(self):
        for bad, field, value in (((88, 30), 'voltage', '8.8 V'),
                                  ((141, 30), 'voltage', '14.1 V'),
                                  ((114, 60), 'temperature', '60 C')):
            with self.subTest(bad=bad):
                samples = [bad, (114, 30), bad, bad, bad]
                seen = self.nudge_health_samples(samples)
                original = self.bus.read2ByteTxRx
                self.bus.read2ByteTxRx = lambda sid, addr: (
                    (2000, 0, 0) if self.bus.on and addr == 56 else original(sid, addr))
                result = self.api.nudge({'joint':0, 'delta_deg':3})
                self.assertFalse(result['ok'])
                self.assertEqual(seen, samples)
                self.assertEqual(result[field + '_fault_reads'], 3)
                other = 'temperature' if field == 'voltage' else 'voltage'
                self.assertEqual(result[other + '_fault_reads'], 0)
                self.assertIn(value, result['error'])
                self.assertIn('3 consecutive fresh reads', result['error'])
                self.assertEqual((result['voltage_v'], result['temp_c']), (bad[0] / 10, bad[1]))
                self.assertEqual(self.bus.writes[-2:], [('torque',2,False),('limit',2,500)])
                self.assertTrue(result['torque_off'])
            self.api.registry.unlink()
            self.bus = Bus(); self.drive.bus = self.bus

    def test_nudge_transient_preflight_health_recovers_before_enabling(self):
        samples = [(88, 60), (114, 30), (114, 30)]
        seen = self.nudge_health_samples(samples, during_motion=False)
        original = self.bus.torque
        def torque(sid, on):
            if on:
                self.assertEqual(seen, samples[:2])
            original(sid, on)
        self.bus.torque = torque
        result = self.api.nudge({'joint':0, 'delta_deg':3})
        self.assertTrue(result['ok'])
        self.assertEqual(seen, samples)

    def test_nudge_confirmed_preflight_health_fault_never_enables(self):
        samples = [(114, 61)] * 3
        seen = self.nudge_health_samples(samples, during_motion=False)
        result = self.api.nudge({'joint':0, 'delta_deg':3})
        self.assertFalse(result['ok'])
        self.assertEqual(seen, samples)
        self.assertEqual(result['temperature_fault_reads'], 3)
        self.assertEqual(result['temp_c'], 61)
        self.assertIn('61 C', result['error'])
        self.assertFalse(any(w[0] == 'position' or w == ('torque',2,True)
                             for w in self.bus.writes))
        self.assertTrue(result['torque_off'])

    def test_nudge_failed_torque_off_never_restores_high_limit(self):
        self.nudge_bus()
        original = self.bus.torque
        self.bus.torque = lambda sid, on: original(sid, on) if on else None
        result = self.api.nudge({'joint':0, 'delta_deg':3})
        self.assertFalse(result['ok'])
        self.assertFalse(result['torque_off'])
        self.assertIn('verify torque off', result['error'])
        self.assertEqual(self.bus.limit, 150)

    def test_nudge_feedback_failure_stops_and_keeps_cleanup(self):
        self.nudge_bus()
        original = self.bus.read2ByteTxRx
        self.bus.read2ByteTxRx = lambda sid, addr: (
            (0, -1, 0) if self.bus.on and addr == 60 else original(sid, addr))
        result = self.api.nudge({'joint':0, 'delta_deg':3})
        self.assertFalse(result['ok'])
        self.assertIn('feedback unavailable', result['error'])
        self.assertTrue(result['torque_off'])
        self.assertEqual(self.bus.limit, 500)

    def test_nudge_http_route_and_quarantine(self):
        import web_drive
        calls = []
        setup = SimpleNamespace(require_setup_for=lambda *args: None,
                                nudge=lambda data: calls.append(data) or {'ok': True})
        def request(quarantined=False):
            handler = web_drive.Handler.__new__(web_drive.Handler)
            data = json.dumps({'joint':4, 'delta_deg':3}).encode()
            handler.path = '/api/setup/nudge'; handler.command = 'POST'
            handler.headers = {'Content-Length': str(len(data))}
            handler.rfile = BytesIO(data); handler._peer = lambda: 'test'
            responses = []
            handler._json = lambda code, obj, **kw: responses.append((code, obj))
            with patch.object(web_drive, 'SETUP', setup), patch.object(
                    web_drive, 'BENCH', SimpleNamespace(bus_access_state=lambda **kw:
                        {'bus_quarantined': True} if quarantined else None)):
                handler.do_POST()
            return responses
        self.assertEqual(request(), [(200, {'ok':True})])
        self.assertEqual(calls, [{'joint':4, 'delta_deg':3}])
        self.assertEqual(request(True)[0][0], 503)
        self.assertEqual(len(calls), 1)

if __name__ == '__main__':
    unittest.main()
