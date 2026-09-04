from __future__ import annotations

import json
from io import BytesIO
import urllib.error

from hexapod_core.demo_tripod import DEFAULT_DEMO_TRIPOD
from rl_move.sim.play_core import (
    _MIDDLE_TUCK_QUAD,
    _NOSLIP_CLEAN,
    _NOSLIP_FLUID_MID,
    _NOSLIP_RIPPLE,
    _SCRIPTED_TRIPOD,
    _SE2_CPG,
    _SE2_TETRAPOD,
    _TRIPOD_HW,
)
from rl_move.sim.web_session import SimWebSession
from rl_move.sim.web_hub import (
    HubController, ROBOT_DEFAULT_TIMEOUT_S, ROBOT_SET_ZERO_TIMEOUT_S,
    RouteResponse, SimTarget, make_hub_handler,
)
from rl_move.sim.web_server import (
    DEFAULT_STANCE_POLICY,
    DEFAULT_TLS_CERT,
    DEFAULT_TLS_KEY,
    DEFAULT_WALK_POLICY,
    PAGE_PATHS,
    STATIC_FILES,
    WEBUI_DIR,
    _cert_has_sans,
    _resolve_policy,
    build_arg_parser,
    ensure_tls_certificate,
    make_handler,
)


def test_web_defaults_do_not_boot_a_learned_legacy_policy(tmp_path):
    args = build_arg_parser().parse_args([])

    assert DEFAULT_STANCE_POLICY is None
    assert args.stance is None
    assert args.http_port == 8898
    assert args.https_port == 8443
    assert args.tls_cert is None
    assert args.tls_key is None
    assert DEFAULT_TLS_CERT.name == ".hexapod_sts_cert.pem"
    assert DEFAULT_TLS_KEY.name == ".hexapod_sts_key.pem"
    assert str(DEFAULT_WALK_POLICY).startswith("scripted:")
    assert _resolve_policy(tmp_path, args.walk) == _TRIPOD_HW


def test_generated_tls_certificate_covers_localhost(tmp_path):
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"

    ensure_tls_certificate(cert, key, "127.0.0.1")

    assert cert.is_file()
    assert key.is_file()
    assert key.stat().st_mode & 0o777 == 0o600
    assert _cert_has_sans(cert, ["localhost"], ["127.0.0.1"])


class FakeSession:
    def __init__(self):
        self.calls = []

    def ping(self):
        return {"ok": True, "service": "hexapod-sim", "kind": "sim"}

    def robot_state(self):
        return {"ok": True, "activity": "idle", "sim": True}

    def status(self):
        return {"ok": True, "sim": True, "motors": []}

    def operation_state(self):
        return {"ok": True, "running": False, "result": {"ok": True}}

    def list_demos(self):
        return [{"name": "quad_walk", "group": "quad"}]

    def demo_state(self):
        return {"name": "quad_walk", "status": "idle", "running": False}

    def rl_preflight(self, mode="stand"):
        return {"ok": True, "mode": mode, "sim": True}

    def rl_policy_info(self):
        return {"ok": True, "source": "stance.zip", "obs_dim": 68,
                "hidden": [256, 256], "act_dim": 18, "activation": "Tanh",
                "walk": {"source": "walk.zip", "obs_dim": 72,
                         "hidden": [256, 256], "act_dim": 18,
                         "activation": "Tanh"}}

    def rl_policies(self):
        return {"ok": True, "policies": []}

    def rl_roles(self):
        return {"ok": True, "roles": {}, "allowed_obs": {}}

    def rl_drive_state(self):
        return {"ok": True, "active": False}

    def rl_timing_probe(self, samples=200, read_samples=8):
        self.calls.append(("rl_timing_probe", samples, read_samples))
        return {"ok": True, "sim": True, "motion_free": True,
                "samples": samples, "read_samples": read_samples}

    def sim_state(self):
        return {"ok": True, "live": {"mode": "hold"}}

    def frame_jpeg(self):
        return b"\xff\xd8\xff\xd9"

    def logs(self):
        return {"ok": True, "files": []}

    def log_file(self, name, request_path=""):
        return b"t_s,mode\n", "text/csv; charset=utf-8"

    def cmd(self, line):
        self.calls.append(("cmd", line))
        return {"ok": True}

    def sim_reset(self, start="plant"):
        self.calls.append(("sim_reset", start))
        return {"ok": True, "status": start}

    def run_demo(self, name, **kw):
        self.calls.append(("run_demo", name, kw))
        return {"ok": True, "params": kw, "home": "stand",
                "demo": self.demo_state(), "robot": self.robot_state()}

    def set_demo_speed(self, speed):
        self.calls.append(("set_demo_speed", speed))
        return {"ok": True, "speed": speed, "demo": self.demo_state()}

    def stop_demo(self):
        self.calls.append(("stop_demo",))
        return {"ok": True, "demo": self.demo_state(),
                "robot": self.robot_state()}

    def go_zero(self, pose="sit", force=False):
        self.calls.append(("go_zero", pose, force))
        return {"ok": True, "pose": pose, "demo": self.demo_state(),
                "robot": self.robot_state()}

    def safe_zero(self):
        self.calls.append(("safe_zero",))
        return {"ok": True}

    def set_zero_here(self):
        self.calls.append(("set_zero_here",))
        return {"ok": True}

    def sim_fall(self):
        self.calls.append(("sim_fall",))
        return {"ok": True}

    def sim_recover(self):
        self.calls.append(("sim_recover",))
        return {"ok": True}

    def sim_push(self, x=4.0, y=0.0):
        self.calls.append(("sim_push", x, y))
        return {"ok": True}

    def sim_pose(self, degrees, source="api"):
        self.calls.append(("sim_pose", degrees, source))
        return {"ok": True, "status": f"synced {source} pose",
                "degrees": degrees, "live": {"mode": "hold"}}

    def rl_capture_plant(self):
        return {"ok": True}

    def rl_stop(self):
        return {"ok": True}

    def rl_policy_move(self, **kw):
        self.calls.append(("rl_policy_move", kw))
        return {"ok": True, **kw}

    def rl_role_set(self, role, file):
        self.calls.append(("rl_role_set", role, file))
        return {"ok": True}

    def rl_drive_start(self, vx=0.0, vy=0.0, wz=0.0, dh=0.0):
        self.calls.append(("rl_drive_start", vx, vy, wz, dh))
        return {"ok": True, "active": True}

    def rl_drive_cmd(self, vx, vy, wz=0.0, dh=0.0):
        self.calls.append(("rl_drive_cmd", vx, vy, wz, dh))
        return {"ok": True, "active": True}

    def rl_drive_stop(self):
        self.calls.append(("rl_drive_stop",))
        return {"ok": True, "active": False}

    def rl_policy_select(self, file):
        self.calls.append(("rl_policy_select", file))
        return {"ok": True, "name": file}


def _request(fake, path, method="GET", body=None):
    handler_cls = make_handler(fake, webui_dir=WEBUI_DIR)
    h = handler_cls.__new__(handler_cls)
    data = json.dumps(body).encode() if body is not None else b""
    h.path = path
    h.command = method
    h.headers = {"Content-Length": str(len(data))}
    h.rfile = BytesIO(data)
    h.wfile = BytesIO()
    h._headers = {}
    h.send_response = lambda code: setattr(h, "_code", code)
    h.send_header = lambda k, v: h._headers.__setitem__(k, v)
    h.end_headers = lambda: None
    if method == "POST":
        handler_cls.do_POST(h)
    else:
        handler_cls.do_GET(h)
    return h._code, h._headers, h.wfile.getvalue()


def _json(fake, path, method="GET", body=None):
    code, _headers, payload = _request(fake, path, method=method, body=body)
    if code >= 400:
        raise urllib.error.HTTPError(path, code, "error", {}, BytesIO(payload))
    return json.loads(payload.decode())


def test_serves_shared_webui_and_sim_ping():
    fake = FakeSession()
    code, headers, payload = _request(fake, "/rl")
    assert code == 200
    assert "text/html" in headers["Content-Type"]
    html = payload.decode()
    assert "Hexapod STS3215" in html
    assert 'id="rlbundletab"' in html
    assert "Complete policy" in html
    assert 'data-gait="6"' in html
    assert 'data-gait="8"' in html
    assert "CPG tetrapod" in html
    assert "Middle-up quad" in html
    assert 'id="rlstandrl" disabled' in html
    assert 'id="rllowerrl" disabled' in html
    assert "__HTTPS_PORT__" not in html
    assert _json(fake, "/api/ping")["service"] == "hexapod-sim"


def test_sim_highstep_tripod_row_uses_shared_default_and_tune():
    row = _SCRIPTED_TRIPOD[_TRIPOD_HW]
    assert row["period"] == DEFAULT_DEMO_TRIPOD.period_s
    assert row["lift_mm"] == DEFAULT_DEMO_TRIPOD.lift_mm
    assert row["stride_scale"] == DEFAULT_DEMO_TRIPOD.stride_scale
    assert row["cruise"] == DEFAULT_DEMO_TRIPOD.max_vx_mps

    session = SimWebSession.__new__(SimWebSession)
    session.demo_tripod = DEFAULT_DEMO_TRIPOD
    session.walk_list = [_TRIPOD_HW]
    session.wi = 0
    session.gait = object()
    session.msg = ""
    session.traj = type("T", (), {"vx": 0.0, "vy": 0.0})()
    session.om_cmd = 0.0

    out = session._apply_demo_tripod_tune(  # noqa: SLF001
        {"stride": 0.75, "vx": 35})

    assert out["ok"] is True
    assert session.demo_tripod.stride_scale == 0.75
    assert session.demo_tripod.max_vx_mps == 0.035
    assert session.gait is None

    session.traj.vx = 0.01
    out = session._apply_demo_tripod_tune({"stride": 0.80})  # noqa: SLF001
    assert out["ok"] is False
    assert "before GTUNE" in out["error"]


def test_sim_drive_gait_ids_map_to_scripted_candidates():
    session = SimWebSession.__new__(SimWebSession)
    session.walk_list = [
        _TRIPOD_HW, _NOSLIP_RIPPLE, _SE2_TETRAPOD, _SE2_CPG, _NOSLIP_CLEAN,
        _MIDDLE_TUCK_QUAD, _NOSLIP_FLUID_MID,
    ]
    session.wi = 0
    session.gait = object()
    session.walk = object()
    session.n_walk = 999
    session.walk_kind = "plain"
    session.msg = ""
    session.demo_tripod = DEFAULT_DEMO_TRIPOD
    session._cpg_loaded = None

    out = session._set_scripted_gait_id(2)  # noqa: SLF001
    assert out["ok"] is True
    assert session.walk_list[session.wi] == _NOSLIP_RIPPLE
    assert session.walk is None

    out = session._set_scripted_gait_id(4)  # noqa: SLF001
    assert out["ok"] is True
    assert session.walk_list[session.wi] == _SE2_TETRAPOD

    out = session._set_scripted_gait_id(6)  # noqa: SLF001
    assert out["ok"] is False
    assert "CPGLOAD" in out["status"]

    session._cpg_loaded = {
        "name": "robust120-winner-yawtrim",
        "gait": "tetrapod",
        "gait_kw": {"period": 2.0, "swing_frac": 0.3, "lift": 0.03},
    }
    out = session._set_scripted_gait_id(6)  # noqa: SLF001
    assert out["ok"] is True
    assert session.walk_list[session.wi] == _SE2_CPG

    out = session._set_scripted_gait_id(7)  # noqa: SLF001
    assert out["ok"] is True
    assert session.walk_list[session.wi] == _NOSLIP_CLEAN

    out = session._set_scripted_gait_id(8)  # noqa: SLF001
    assert out["ok"] is True
    assert session.walk_list[session.wi] == _MIDDLE_TUCK_QUAD

    out = session._set_scripted_gait_id(14)  # noqa: SLF001
    assert out["ok"] is True
    assert session.walk_list[session.wi] == _NOSLIP_FLUID_MID


def test_dispatches_rl_drive_and_sim_routes():
    fake = FakeSession()
    timing = _json(fake, "/api/rl/timing?samples=7&read_samples=3")
    assert timing["motion_free"] is True
    assert timing["samples"] == 7
    assert timing["read_samples"] == 3
    assert _json(fake, "/api/rl/drive/start", method="POST",
                 body={"vx": 0.04, "vy": 0.01, "wz": -0.1,
                       "dh": 0.5})["active"]
    assert _json(fake, "/api/rl/drive/cmd", method="POST",
                 body={"vx": 0.05, "vy": -0.02})["active"]
    assert _json(fake, "/api/rl/drive/cmd", method="POST",
                 body={"vx": 0.0, "vy": 0.0, "wz": 0.2, "dh": -1})["active"]
    assert _json(fake, "/api/sim/reset", method="POST",
                 body={"start": "belly"})["status"] == "belly"
    assert _json(fake, "/api/sim/pose", method="POST",
                 body={"degrees": list(range(18)),
                       "source": "test"})["status"] == "synced test pose"
    assert ("rl_drive_cmd", 0.05, -0.02, 0.0, 0.0) in fake.calls
    assert ("rl_drive_cmd", 0.0, 0.0, 0.2, -1.0) in fake.calls
    assert ("rl_drive_start", 0.04, 0.01, -0.1, 0.5) in fake.calls
    assert ("rl_timing_probe", 7, 3) in fake.calls
    assert ("sim_reset", "belly") in fake.calls
    assert ("sim_pose", list(range(18)), "test") in fake.calls


def test_dispatches_robot_compatible_demo_routes():
    fake = FakeSession()
    demos = _json(fake, "/api/demos")
    assert demos["demos"][0]["name"] == "quad_walk"

    started = _json(fake, "/api/demo", method="POST",
                    body={"name": "quad_walk", "speed": 1.25,
                          "seconds": 40})
    assert started["ok"] is True
    assert started["home"] == "stand"
    assert ("run_demo", "quad_walk",
            {"speed": 1.25, "size": 1.0, "softness": 1.0,
             "seconds": 40.0}) in fake.calls

    assert _json(fake, "/api/demo/speed", method="POST",
                 body={"speed": 0.75})["speed"] == 0.75
    assert _json(fake, "/api/demo/stop", method="POST")["ok"] is True
    assert _json(fake, "/api/zero", method="POST",
                 body={"pose": "stand"})["pose"] == "stand"


def test_unknown_route_returns_json_404():
    fake = FakeSession()
    try:
        _json(fake, "/nope")
    except urllib.error.HTTPError as e:
        assert e.code == 404
        body = json.loads(e.read().decode())
        assert body["ok"] is False


def test_cmd_text_payload_survives_sim_handler():
    fake = FakeSession()

    def payload_cmd(line):
        fake.calls.append(("cmd", line))
        return {"ok": True, "text": '[{"file":"cpg_controller_x.json"}]'}

    fake.cmd = payload_cmd
    code, _headers, payload = _request(
        fake, "/cmd", method="POST", body="CPGLIST")

    assert code == 200
    assert payload.decode() == '[{"file":"cpg_controller_x.json"}]'
    assert ("cmd", '"CPGLIST"') in fake.calls


class FakeTarget:
    def __init__(self, name):
        self.name = name
        self.calls = []
        self.timeouts = []

    def available(self):
        return True

    def ping_meta(self):
        return {"available": True, "ok": True, "name": self.name}

    def request(self, method, full_path, body=b"", headers=None,
                timeout=None):
        self.calls.append((method, full_path, body))
        self.timeouts.append(timeout)
        path = full_path.split("?", 1)[0]
        if path == "/cmd":
            return RouteResponse.text("ok")
        try:
            data = json.loads(body.decode()) if body else {}
        except ValueError:
            data = body.decode("utf-8", "replace")
        return RouteResponse.json({
            "ok": True,
            "target": self.name,
            "method": method,
            "path": path,
            "body": data,
        })

    def close(self):
        pass


class ConfigurableFakeTarget(FakeTarget):
    def __init__(self, name):
        super().__init__(name)
        self.base_url = ""

    def available(self):
        return bool(self.base_url)

    def configure(self, base_url, insecure_tls=None):
        self.base_url = (
            base_url if "://" in base_url else "http://" + base_url
        ).rstrip("/")

    def config_meta(self):
        if not self.available():
            return {"available": False}
        return {"available": True, "url": self.base_url}

    def ping_meta(self):
        return {**self.config_meta(), "ok": self.available(),
                "name": self.name}


class DemoFakeTarget(FakeTarget):
    def __init__(self, name, demos):
        super().__init__(name)
        self.demos = demos

    def config_meta(self):
        return {"available": True, "url": f"http://{self.name}.local"}

    def request(self, method, full_path, body=b"", headers=None,
                timeout=None):
        path = full_path.split("?", 1)[0]
        if method == "GET" and path == "/api/demos":
            self.calls.append((method, full_path, body))
            return RouteResponse.json({"ok": True, "demos": self.demos})
        return super().request(method, full_path, body, headers)


class FailingDemoTarget(FakeTarget):
    def config_meta(self):
        return {"available": True, "url": f"http://{self.name}.local"}

    def request(self, method, full_path, body=b"", headers=None,
                timeout=None):
        path = full_path.split("?", 1)[0]
        if method == "GET" and path == "/api/demos":
            self.calls.append((method, full_path, body))
            return RouteResponse.json(
                {"ok": False, "error": "offline"}, 502)
        return super().request(method, full_path, body, headers)


class PoseFakeTarget(FakeTarget):
    def __init__(self, name, degrees):
        super().__init__(name)
        self.degrees = degrees

    def request(self, method, full_path, body=b"", headers=None,
                timeout=None):
        path = full_path.split("?", 1)[0]
        if method == "GET" and path == "/api/pose":
            self.calls.append((method, full_path, body))
            return RouteResponse.json({
                "ok": True,
                "degrees": self.degrees,
                "live": len([x for x in self.degrees if x is not None]),
                "ts": 123.0,
                "armed": True,
                "mode": "idle",
            })
        return super().request(method, full_path, body, headers)


def _hub_request(hub, path, method="GET", body=None):
    handler_cls = make_hub_handler(
        hub, WEBUI_DIR, 8443, PAGE_PATHS, STATIC_FILES)
    h = handler_cls.__new__(handler_cls)
    data = json.dumps(body).encode() if body is not None else b""
    h.path = path
    h.command = method
    h.headers = {"Content-Length": str(len(data))}
    h.rfile = BytesIO(data)
    h.wfile = BytesIO()
    h._headers = {}
    h.send_response = lambda code: setattr(h, "_code", code)
    h.send_header = lambda k, v: h._headers.__setitem__(k, v)
    h.end_headers = lambda: None
    if method == "POST":
        handler_cls.do_POST(h)
    else:
        handler_cls.do_GET(h)
    return h._code, h._headers, h.wfile.getvalue()


def _hub_json(hub, path, method="GET", body=None):
    code, _headers, payload = _hub_request(
        hub, path, method=method, body=body)
    if code >= 400:
        raise urllib.error.HTTPError(path, code, "error", {}, BytesIO(payload))
    return json.loads(payload.decode())


def test_hub_ping_and_target_switch():
    sim = FakeTarget("sim")
    robot = FakeTarget("robot")
    hub = HubController(sim=sim, robot=robot, target="both")
    ping = _hub_json(hub, "/api/ping")
    assert ping["service"] == "hexapod-hub"
    assert ping["target"] == "both"
    assert ping["active"] == {"robot": True, "sim": True}

    switched = _hub_json(hub, "/api/hub", method="POST",
                         body={"target": "sim"})
    assert switched["target"] == "sim"
    assert switched["active"] == {"robot": False, "sim": True}


def test_hub_can_configure_robot_target_at_runtime():
    sim = FakeTarget("sim")
    robot = ConfigurableFakeTarget("robot")
    hub = HubController(sim=sim, robot=robot, target="sim")
    ping = _hub_json(hub, "/api/ping")
    assert ping["target"] == "sim"
    assert ping["targets"]["robot"] == {"available": False}

    connected = _hub_json(hub, "/api/hub", method="POST",
                          body={"robot_url": "hexapod.local:8080",
                                "target": "robot"})
    assert connected["ok"] is True
    assert connected["target"] == "robot"
    assert connected["active"] == {"robot": True, "sim": False}
    assert connected["targets"]["robot"]["url"] == "http://hexapod.local:8080"

    r = _hub_json(hub, "/api/status")
    assert r["target"] == "robot"
    assert robot.calls[-1][1] == "/api/status"


def test_hub_demos_include_robot_catalog_while_target_is_sim():
    sim = DemoFakeTarget("sim", [
        {"name": "quad_walk", "title": "sim quad", "group": "quad"},
    ])
    robot = DemoFakeTarget("robot", [
        {"name": "dance_wild", "title": "wild", "group": "plant"},
        {"name": "quad_walk", "title": "robot quad", "group": "quad"},
    ])
    hub = HubController(sim=sim, robot=robot, target="sim")
    catalog = _hub_json(hub, "/api/demos")
    by_name = {d["name"]: d for d in catalog["demos"]}

    assert catalog["ok"] is True
    assert catalog["target"] == "sim"
    assert by_name["dance_wild"]["target"] == "robot"
    assert by_name["quad_walk"]["target"] == "robot"
    assert by_name["quad_walk"]["available_on"] == ["robot", "sim"]


def test_hub_demos_keep_local_robot_catalog_when_live_robot_fails():
    sim = DemoFakeTarget("sim", [
        {"name": "quad_walk", "title": "sim quad", "group": "quad"},
    ])
    robot = FailingDemoTarget("robot")
    hub = HubController(sim=sim, robot=robot, target="sim")
    catalog = _hub_json(hub, "/api/demos")
    names = {d["name"] for d in catalog["demos"]}

    assert catalog["ok"] is True
    assert "dance_walk" in names
    assert catalog["sources"]["robot"]["local"] is True
    assert catalog["sources"]["robot"]["live_error"] == "offline"


def test_hub_demos_show_local_robot_catalog_before_robot_is_configured():
    sim = DemoFakeTarget("sim", [
        {"name": "quad_walk", "title": "sim quad", "group": "quad"},
    ])
    hub = HubController(sim=sim, robot=None, target="sim")
    catalog = _hub_json(hub, "/api/demos")
    names = {d["name"] for d in catalog["demos"]}

    assert catalog["ok"] is True
    assert "dance_walk" in names
    assert catalog["sources"]["robot"]["local"] is True
    assert catalog["sources"]["robot"]["configured"] is False


def test_hub_syncs_sim_from_robot_pose():
    fake = FakeSession()
    degrees = [float(i) for i in range(18)]
    hub = HubController(
        sim=SimTarget(fake),
        robot=PoseFakeTarget("robot", degrees),
        target="both",
    )
    synced = _hub_json(hub, "/api/sim/sync_robot_pose", method="POST")

    assert synced["ok"] is True
    assert synced["status"] == "synced robot pose"
    assert synced["robot_pose"]["live"] == 18
    assert ("sim_pose", degrees, "robot") in fake.calls


def test_hub_routes_sim_timing_probe_with_query_params():
    fake = FakeSession()
    hub = HubController(sim=SimTarget(fake), robot=None, target="sim")
    timing = _hub_json(hub, "/api/rl/timing?samples=11&read_samples=4")

    assert timing["ok"] is True
    assert timing["sim"] is True
    assert timing["samples"] == 11
    assert timing["read_samples"] == 4
    assert ("rl_timing_probe", 11, 4) in fake.calls


def test_hub_broadcasts_drive_commands_only_in_both_mode():
    sim = FakeTarget("sim")
    robot = FakeTarget("robot")
    hub = HubController(sim=sim, robot=robot, target="both")
    d = _hub_json(hub, "/api/rl/drive/cmd", method="POST",
                  body={"vx": 0.04, "vy": 0.0})
    assert d["ok"] is True
    assert d["hub"]["robot"]["body"]["vx"] == 0.04
    assert d["hub"]["sim"]["body"]["vx"] == 0.04
    assert ("POST", "/api/rl/drive/cmd", b'{"vx": 0.04, "vy": 0.0}') in robot.calls
    assert ("POST", "/api/rl/drive/cmd", b'{"vx": 0.04, "vy": 0.0}') in sim.calls

    _hub_json(hub, "/api/hub", method="POST", body={"target": "robot"})
    _hub_json(hub, "/api/wiggle", method="POST",
              body={"joint": 1, "amp": 4})
    assert robot.calls[-1][1] == "/api/wiggle"
    assert sim.calls[-1][1] == "/api/rl/drive/cmd"


def test_hub_broadcasts_demo_commands_in_both_mode():
    sim = FakeTarget("sim")
    robot = FakeTarget("robot")
    hub = HubController(sim=sim, robot=robot, target="both")
    d = _hub_json(hub, "/api/demo", method="POST",
                  body={"name": "quad_walk", "speed": 1.0})
    assert d["ok"] is True
    assert d["hub"]["robot"]["body"]["name"] == "quad_walk"
    assert d["hub"]["sim"]["body"]["name"] == "quad_walk"
    assert ("POST", "/api/demo", b'{"name": "quad_walk", "speed": 1.0}') in robot.calls
    assert ("POST", "/api/demo", b'{"name": "quad_walk", "speed": 1.0}') in sim.calls


def test_hub_uses_long_robot_timeout_for_set_zero():
    sim = FakeTarget("sim")
    robot = FakeTarget("robot")
    hub = HubController(sim=sim, robot=robot, target="both")

    d = _hub_json(hub, "/api/set_zero", method="POST")
    assert d["ok"] is True
    assert robot.calls[-1][1] == "/api/set_zero"
    assert robot.timeouts[-1] == ROBOT_SET_ZERO_TIMEOUT_S
    assert sim.calls == []

    _hub_json(hub, "/api/wiggle", method="POST",
              body={"joint": 1, "amp": 4})
    assert robot.calls[-1][1] == "/api/wiggle"
    assert robot.timeouts[-1] == ROBOT_DEFAULT_TIMEOUT_S
