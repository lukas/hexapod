import json, sys, tempfile, threading, unittest
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

if __name__ == '__main__':
    unittest.main()
