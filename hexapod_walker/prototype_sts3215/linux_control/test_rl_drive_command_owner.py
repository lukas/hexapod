"""Drive ownership regressions with a parked worker and no physical IO."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api.rl import RlApi


class ParkedThread:
    def __init__(self, **kwargs):
        self.alive = False

    def start(self):
        self.alive = True  # Never execute the physical worker.

    def is_alive(self):
        return self.alive


class FakeApi(RlApi):
    def __init__(self):
        self._lock = threading.RLock()
        self.drive = SimpleNamespace(dry_run=False, bus=object(), armed=True,
                                     _lock=threading.RLock())
        self._demo_thread = None
        self._demo_name = ""
        self._drive_cmd = None
        self._demo_gen = 0
        self._demo_abort = threading.Event()

    def _bus_admission_error(self):
        return None

    def _role_weights(self, role):
        return Path(f"/tmp/fake_{role}.json")

    def _set_activity(self, *args):
        pass


@pytest.fixture
def api(monkeypatch):
    import rl_policy
    monkeypatch.setattr(rl_policy, "preflight", lambda *args: (True, "", {}))
    monkeypatch.setattr("api.rl.threading.Thread", ParkedThread)
    return FakeApi()


def test_owned_start_records_owner_and_matching_command_updates(api):
    result = api.rl_drive_start(command_owner="trial-one", vx=.08)
    assert result["ok"] and result["command_owner"] == "trial-one"
    assert api.rl_drive_state()["command_owner"] == "trial-one"
    assert api._demo_params["command_owner"] == "trial-one"
    assert api.rl_drive_cmd(command_owner="trial-one", vx=.06)["ok"]
    assert api._drive_cmd._vx == .06


@pytest.mark.parametrize("owner", [None, "other-tab", "", 123])
def test_foreign_heartbeat_cannot_zero_command_or_refresh_watchdog(api, owner):
    api.rl_drive_start(command_owner="trial-one", vx=.08)
    before = api._drive_cmd._t_cmd
    result = api.rl_drive_cmd(command_owner=owner, vx=0)
    assert not result["ok"] and result["command_owner_mismatch"]
    assert result["active"]
    assert api._drive_cmd._vx == .08
    assert api._drive_cmd._t_cmd == before


def test_foreign_start_cannot_adopt_or_replace_active_session(api):
    api.rl_drive_start(command_owner="trial-one", vx=.08)
    command = api._drive_cmd
    assert not api.rl_drive_start()["ok"]
    assert not api.rl_drive_start(command_owner="trial-two")["ok"]
    assert api.rl_drive_start(command_owner="trial-one")["already"]
    assert api._drive_cmd is command and command._vx == .08


def test_legacy_unowned_commands_continue_working(api):
    assert api.rl_drive_start(vx=.08)["ok"]
    assert api.rl_drive_cmd(vx=.02)["ok"]
    assert api.rl_drive_cmd(vx=.03, command_owner="optional-new-client")["ok"]
    assert api._drive_cmd._vx == .03


def test_stop_always_available_without_owner(api):
    api.rl_drive_start(command_owner="trial-one", vx=.08)
    assert api.rl_drive_stop()["ok"]
    assert api._drive_cmd._stop


def test_new_session_does_not_inherit_old_owner(api):
    api.rl_drive_start(command_owner="trial-one")
    api._demo_thread.alive = False
    assert api.rl_drive_start()["ok"]
    assert api.rl_drive_state()["command_owner"] is None
    assert api.rl_drive_cmd(vx=.08)["ok"]


@pytest.mark.parametrize("owner", ["", " ", "x" * 129, 1, {}])
def test_invalid_owner_is_refused_before_start(api, owner):
    assert not api.rl_drive_start(command_owner=owner)["ok"]
    assert api._demo_thread is None


@pytest.mark.parametrize("remote_owner", [None, "cli-trial", "this-browser"])
def test_browser_poll_only_heartbeats_its_own_session(remote_owner):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the production UI-function regression")
    source = (Path(__file__).resolve().parent / "webui" / "app.js").read_text()
    # Execute the actual functions, with browser/network surfaces replaced.
    ranges = [
        ("function drvCanUseInput()", "function drvLockRlControls("),
        ("async function drvSend()", "async function drvEnded()"),
        ("async function refreshRlRuntimeState()", "setInterval(()=>{ if(activeView === 'rl')"),
    ]
    functions = "\n".join(source[source.index(a):source.index(b, source.index(a))]
                          for a, b in ranges)
    preamble = r"""
const assert = require('node:assert/strict');
let drvActive=false, drvHb=null, drvStartPromise=null, drvOwnsSession=false;
let drvCommandOwner='this-browser', drvInputAllowed=false, rlTimer=null;
let drvGamepadNeedsNeutral=false;
const elements={}, requests=[];
let heartbeatStarts=0;
function $(id){ return elements[id] ||= {}; }
function drvLockRlControls(active){ drvInputAllowed=active; }
function drvClearHeartbeat(){ drvHb=null; }
function drvResetLocalInput(){}
function drvSetPanelState(allowed){ drvInputAllowed=allowed; }
function drvPaint(){}
function drvVec(){ return [0,0,0,0]; }
function setInterval(){ ++heartbeatStarts; return 1; }
function clearInterval(){}
async function fetch(path, options){
  requests.push({path, options});
  return {json:async()=>path.startsWith('/api/calibrate')
    ? {running:false}
    : {ok:true, active:true, command_owner:remoteOwner}};
}
"""
    checks = r"""
(async()=>{
  await refreshRlRuntimeState();
  const ours=remoteOwner==='this-browser';
  assert.equal(drvActive,true);
  assert.equal(drvOwnsSession,ours);
  assert.equal(!!drvCanUseInput(),ours);
  assert.equal(heartbeatStarts,ours?1:0);
  if(!ours){
    assert.equal($('rldriveend').disabled,false);
    assert.equal($('rldrivepanel').disabled,false);
  }
  await drvSend();
  const commands=requests.filter(r=>r.path==='/api/rl/drive/cmd');
  assert.equal(commands.length,ours?1:0);
  if(ours) assert.equal(JSON.parse(commands[0].options.body).command_owner,'this-browser');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    subprocess.run([node, "-"], input="const remoteOwner=" + json.dumps(remote_owner)
                   + ";\n" + preamble + functions + checks,
                   check=True, capture_output=True, text=True)
