"""HTTP/HTTPS bridge that serves the robot web UI against a MuJoCo session.

Run from ``hexapod_walker/prototype_sts3215``:

    uv run python -m rl_move.sim.web_server --http-port 8898 --https-port 8443

The route shapes intentionally match ``linux_control/web_drive.py`` so the
same browser UI can drive either the physical robot or the MuJoCo twin.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
WEBUI_DIR = ROOT / "linux_control" / "webui"
DEFAULT_LOG_DIR = ROOT / "logs" / "sim_web"
DEFAULT_STANCE_POLICY: Path | None = None
DEFAULT_WALK_POLICY = Path("scripted:tripod_highstep_demo_gait")
DEFAULT_TLS_CERT = Path("~/.hexapod_sts_cert.pem").expanduser()
DEFAULT_TLS_KEY = Path("~/.hexapod_sts_key.pem").expanduser()

PAGE_PATHS = {"/", "/index.html", "/motors", "/demos", "/dance", "/rock",
              "/quad", "/debug", "/rl", "/experiments", "/measure",
              "/calibrate"}
STATIC_FILES = {
    "/style.css": ("style.css", "text/css; charset=utf-8", "no-cache"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8",
                "no-cache"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml", "max-age=86400"),
}


def _add_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _https_cert_sans(bind: str) -> tuple[list[str], list[str]]:
    """Return the local names covered by the generated laptop certificate."""
    dns = ["localhost"]
    ips = ["127.0.0.1"]
    try:
        host = socket.gethostname().strip()
    except OSError:
        host = ""
    if host:
        _add_unique(dns, host)
        if "." not in host:
            _add_unique(dns, f"{host}.local")

    try:
        ip = ipaddress.ip_address(bind)
    except ValueError:
        if bind not in ("0.0.0.0", "::", ""):
            _add_unique(dns, bind)
    else:
        if not ip.is_unspecified:
            _add_unique(ips, str(ip))
    return dns, ips


def _cert_has_sans(cert_file: Path, dns: list[str], ips: list[str]) -> bool:
    if not cert_file.is_file():
        return False
    try:
        decoded = ssl._ssl._test_decode_cert(str(cert_file))
    except Exception:
        return False
    sans = decoded.get("subjectAltName", ())
    have_dns = {str(value) for kind, value in sans
                if str(kind).lower() == "dns"}
    have_ips = {str(value) for kind, value in sans
                if re.sub(r"\s+", "", str(kind).lower()) == "ipaddress"}
    return set(dns).issubset(have_dns) and set(ips).issubset(have_ips)


def ensure_tls_certificate(cert_file: Path, key_file: Path, bind: str,
                           *, configured: bool = False) -> None:
    """Ensure a TLS keypair exists, generating a local self-signed pair."""
    cert_file = cert_file.expanduser()
    key_file = key_file.expanduser()
    if configured:
        if cert_file.is_file() and key_file.is_file():
            print(f"TLS: using configured certificate {cert_file}", flush=True)
            return
        raise RuntimeError(
            "configured TLS certificate/key missing: "
            f"{cert_file} / {key_file}")

    dns, ips = _https_cert_sans(bind)
    if key_file.is_file() and _cert_has_sans(cert_file, dns, ips):
        return

    cert_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    san = ",".join([f"DNS:{value}" for value in dns]
                   + [f"IP:{value}" for value in ips])
    tmp_cert = cert_file.with_name(cert_file.name + ".tmp")
    tmp_key = key_file.with_name(key_file.name + ".tmp")
    for path in (tmp_cert, tmp_key):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    try:
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
             "-keyout", str(tmp_key), "-out", str(tmp_cert), "-days", "3650",
             "-subj", "/CN=localhost", "-addext", f"subjectAltName={san}"],
            check=True, capture_output=True,
        )
        tmp_key.chmod(0o600)
        tmp_cert.replace(cert_file)
        tmp_key.replace(key_file)
        print(f"TLS: generated self-signed certificate {cert_file} "
              f"with SANs {san}", flush=True)
    except Exception:
        for path in (tmp_cert, tmp_key):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise


def make_https_server(bind: str, port: int,
                      handler: type[BaseHTTPRequestHandler],
                      cert_file: Path, key_file: Path) -> ThreadingHTTPServer:
    """Create a threaded HTTPS server using the supplied certificate."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(cert_file), str(key_file))
    server = ThreadingHTTPServer((bind, port), handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.daemon_threads = True
    return server


def _camera_indexes(value: str) -> tuple[int, ...]:
    try:
        indexes = tuple(dict.fromkeys(
            int(item.strip()) for item in value.split(",") if item.strip()
        ))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "camera indexes must be comma-separated integers"
        ) from error
    if not indexes or any(index < 0 for index in indexes):
        raise argparse.ArgumentTypeError(
            "camera indexes need one or more non-negative values"
        )
    return indexes


def _json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    n = int(handler.headers.get("Content-Length", 0) or 0)
    raw = handler.rfile.read(n) if n else b""
    if not raw:
        return {}
    try:
        obj = json.loads(raw.decode("utf-8", "ignore"))
    except ValueError:
        return {"_text": raw.decode("utf-8", "ignore")}
    return obj if isinstance(obj, dict) else {"_value": obj}


def _query_int(full_path: str, key: str, default: int) -> int:
    vals = urllib.parse.parse_qs(urllib.parse.urlsplit(full_path).query)
    try:
        return int(vals.get(key, [default])[0])
    except (TypeError, ValueError):
        return int(default)


def make_handler(session: Any, webui_dir: Path = WEBUI_DIR,
                 https_port: int = 8443) -> type[BaseHTTPRequestHandler]:
    """Create a request handler bound to ``session``.

    ``session`` is deliberately duck-typed so tests can provide a small fake
    while the real CLI uses ``SimWebSession``.
    """

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _send(self, code: int, body: bytes | str,
                  ctype: str = "text/plain; charset=utf-8",
                  cache: str | None = None) -> None:
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            if cache:
                self.send_header("Cache-Control", cache)
            elif "text/html" in ctype:
                self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(data)
            except OSError:
                pass

        def _json(self, code: int, obj: Any) -> None:
            self._send(code, json.dumps(obj), "application/json")

        def _static(self, path: str) -> bool:
            if path in PAGE_PATHS:
                index = webui_dir / "index.html"
                try:
                    page = index.read_text(encoding="utf-8")
                except OSError as e:
                    self._send(500, f"webui file missing: expected {index} ({e})")
                    return True
                page = page.replace("__HTTPS_PORT__", str(https_port))
                self._send(200, page, "text/html; charset=utf-8",
                           cache="no-cache")
                return True
            if path in STATIC_FILES:
                name, ctype, cache = STATIC_FILES[path]
                fpath = webui_dir / name
                try:
                    data = fpath.read_bytes()
                except OSError as e:
                    self._send(500, f"webui file missing: expected {fpath} ({e})")
                    return True
                self._send(200, data, ctype, cache=cache)
                return True
            return False

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if self._static(path):
                return
            try:
                if path == "/api/ping":
                    self._json(200, session.ping())
                elif path == "/api/robot":
                    self._json(200, session.robot_state())
                elif path == "/api/status":
                    self._json(200, session.status())
                elif path == "/api/demo/status":
                    self._json(200, session.robot_state())
                elif path == "/api/demos":
                    self._json(200, {"demos": session.list_demos()})
                elif path == "/api/pose":
                    self._json(200, session.pose())
                elif path == "/api/calibrate":
                    self._json(200, session.operation_state())
                elif path == "/api/calibration/report":
                    self._json(200, session.calibration_report())
                elif path == "/api/rl/preflight":
                    mode = "stand"
                    qs = self.path.split("?", 1)
                    if len(qs) == 2 and "mode=" in qs[1]:
                        mode = qs[1].split("mode=", 1)[1].split("&", 1)[0]
                    self._json(200, session.rl_preflight(mode=mode))
                elif path == "/api/rl/policy":
                    self._json(200, session.rl_policy_info())
                elif path == "/api/rl/policies":
                    self._json(200, session.rl_policies())
                elif path.startswith("/api/rl/policies/"):
                    name = Path(path[len("/api/rl/policies/"):]).name
                    text = session.get_rl_policy(name)
                    if text is None:
                        self._json(404, {"ok": False,
                                         "error": f"no policy {name!r}"})
                    else:
                        self._send(200, text, "application/json")
                elif path == "/api/rl/roles":
                    self._json(200, session.rl_roles())
                elif path == "/api/rl/drive":
                    self._json(200, session.rl_drive_state())
                elif path == "/api/rl/timing":
                    self._json(200, session.rl_timing_probe(
                        samples=_query_int(self.path, "samples", 200),
                        read_samples=_query_int(
                            self.path, "read_samples", 8)))
                elif path == "/api/standup/modes":
                    self._json(200, session.standup_modes())
                elif path == "/api/sim/state":
                    self._json(200, session.sim_state())
                elif path == "/api/sim/frame.jpg":
                    self._send(200, session.frame_jpeg(),
                               "image/jpeg", cache="no-cache")
                elif path == "/api/dances":
                    self._json(200, {"dances": session.list_dance_scripts()})
                elif path.startswith("/api/dances/"):
                    name = Path(path[len("/api/dances/"):]).name
                    script = session.get_dance_script(name)
                    if script is None:
                        self._json(404, {"ok": False,
                                         "error": f"no dance {name!r}"})
                    else:
                        self._json(200, script)
                elif path == "/api/logs":
                    self._json(200, session.logs())
                elif path.startswith("/api/logs/"):
                    name = Path(path[len("/api/logs/"):]).name
                    data, ctype = session.log_file(name, self.path)
                    self._send(200, data, ctype)
                else:
                    self._json(404, {"ok": False,
                                     "error": f"no sim route: {path}"})
            except FileNotFoundError as e:
                self._json(404, {"ok": False, "error": str(e)})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})

        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == "/cmd":
                n = int(self.headers.get("Content-Length", 0) or 0)
                raw = self.rfile.read(n) if n else b""
                line = raw.decode("utf-8", "ignore").strip()
                out = session.cmd(line)
                text = out.get("text")
                if text is None:
                    text = "ok" if out.get("ok") else (
                        out.get("error") or out.get("status") or "failed")
                self._send(200, str(text))
                return
            data = _json_body(self)
            try:
                if path == "/api/standup":
                    self._json(200, session.sim_standup(
                        mode=str(data.get("mode", "tuck")),
                        speed=float(data.get("speed", 1.0)),
                        direction=str(data.get("direction", "up"))))
                elif path == "/api/demo":
                    kw = dict(
                        speed=float(data.get("speed", 1.0)),
                        size=float(data.get("size", 1.0)),
                        softness=float(data.get("softness", 1.0)),
                    )
                    if data.get("rate") is not None:
                        kw["rate"] = float(data["rate"])
                    if data.get("torque") is not None:
                        kw["torque"] = int(float(data["torque"]))
                    if data.get("seconds") is not None:
                        kw["seconds"] = float(data["seconds"])
                    self._json(200, session.run_demo(
                        str(data.get("name", "")), **kw))
                elif path == "/api/calibrate":
                    self._json(200, session.run_calibrate(
                        mode=str(data.get("mode", "checkup")),
                        step_deg=float(data.get("step_deg", 10)),
                        nudge_deg=float(data.get("nudge_deg", 2)),
                        axis=str(data.get("axis", "all")),
                        clearance_mm=float(data.get("clearance_mm", 40)),
                        quad_body_frame=bool(data.get(
                            "quad_body_frame", False))))
                elif path == "/api/dances":
                    script = data
                    if isinstance(script, dict) and "script" in script:
                        script = script["script"]
                    self._json(200, session.save_dance_script(script))
                elif path == "/api/dances/delete":
                    self._json(200, session.delete_dance_script(
                        str((data or {}).get("name", ""))))
                elif path == "/api/demo/speed":
                    self._json(200, session.set_demo_speed(
                        data.get("speed", 1.0)))
                elif path == "/api/demo/stop":
                    self._json(200, session.stop_demo())
                elif path == "/api/standup/stop":
                    self._json(200, session.stop_demo())
                elif path == "/api/zero":
                    pose = str(data.get("pose", "sit"))
                    self._json(200, session.go_zero(
                        pose=pose, force=bool(data.get("force", False))))
                elif path == "/api/safe_zero":
                    self._json(200, session.safe_zero())
                elif path == "/api/set_zero":
                    self._json(200, session.set_zero_here())
                elif path == "/api/rl/capture_plant":
                    self._json(200, session.rl_capture_plant())
                elif path == "/api/rl/stop":
                    self._json(200, session.rl_stop())
                elif path in ("/api/rl/stand", "/api/rl/lower"):
                    self._json(200, session.rl_policy_move(
                        mode=path.rsplit("/", 1)[-1]))
                elif path == "/api/rl/walk":
                    self._json(200, session.rl_policy_move(
                        mode="walk",
                        vx=float(data.get("vx", 0.03)),
                        vy=float(data.get("vy", 0.0)),
                        duration_s=float(data.get("duration_s", 6.0))))
                elif path == "/api/rl/roles":
                    self._json(200, session.rl_role_set(
                        role=str(data.get("role", "")),
                        file=str(data.get("file", ""))))
                elif path == "/api/rl/drive/start":
                    self._json(200, session.rl_drive_start(
                        vx=float(data.get("vx", 0.0)),
                        vy=float(data.get("vy", 0.0)),
                        wz=float(data.get("wz", 0.0)),
                        dh=float(data.get("dh", 0.0))))
                elif path == "/api/rl/drive/cmd":
                    self._json(200, session.rl_drive_cmd(
                        vx=float(data.get("vx", 0.0)),
                        vy=float(data.get("vy", 0.0)),
                        wz=float(data.get("wz", 0.0)),
                        dh=float(data.get("dh", 0.0))))
                elif path == "/api/rl/drive/stop":
                    self._json(200, session.rl_drive_stop())
                elif path == "/api/rl/policies":
                    qs = self.path.split("?", 1)
                    name = ""
                    if len(qs) == 2 and "name=" in qs[1]:
                        name = qs[1].split("name=", 1)[1].split("&", 1)[0]
                    self._json(200, session.save_rl_policy(data, name=name))
                elif path == "/api/rl/policies/delete":
                    self._json(200, session.delete_rl_policy(
                        str((data or {}).get("file", ""))))
                elif path == "/api/rl/policy_select":
                    self._json(200, session.rl_policy_select(
                        file=str(data.get("file", ""))))
                elif path == "/api/sim/reset":
                    self._json(200, session.sim_reset(
                        start=str(data.get("start", "plant"))))
                elif path == "/api/sim/fall":
                    self._json(200, session.sim_fall())
                elif path == "/api/sim/recover":
                    self._json(200, session.sim_recover())
                elif path == "/api/sim/push":
                    self._json(200, session.sim_push(
                        x=float(data.get("x", 4.0)),
                        y=float(data.get("y", 0.0))))
                elif path == "/api/sim/pose":
                    self._json(200, session.sim_pose(
                        degrees=data.get("degrees"),
                        source=str(data.get("source", "api"))))
                else:
                    self._json(404, {"ok": False,
                                     "error": f"no sim route: {path}"})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})

    return Handler


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--http-port", type=int, default=8898)
    ap.add_argument("--https-port", type=int, default=8443,
                    help="HTTPS listener for browser Gamepad API "
                         "(default: 8443)")
    ap.add_argument("--tls-cert", type=Path,
                    help="custom TLS certificate (requires --tls-key)")
    ap.add_argument("--tls-key", type=Path,
                    help="custom TLS private key (requires --tls-cert)")
    ap.add_argument("--policy-dir", type=Path,
                    default=ROOT / "rl_move" / "sim" / "policies")
    ap.add_argument("--stance", type=Path,
                    default=DEFAULT_STANCE_POLICY)
    ap.add_argument("--walk", type=Path,
                    default=DEFAULT_WALK_POLICY)
    ap.add_argument("--recover", type=Path,
                    default=Path("ppo_goal_cw_recover_any21_pop3_B14.zip"))
    ap.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    ap.add_argument("--realtime", type=float, default=1.0)
    ap.add_argument("--viewer", action="store_true",
                    help="open a native MuJoCo viewer and use the web UI "
                         "as a remote control surface")
    ap.add_argument("--browser-frames", choices=("auto", "on", "off"),
                    default="auto",
                    help="serve JPEG frames to the browser: auto keeps "
                         "frames on for headless mode and off for --viewer")
    ap.add_argument("--robot-url", default="",
                    help="robot-side web_drive.py base URL, e.g. "
                         "http://hexapod.local:8080; can also be set "
                         "from the web UI")
    ap.add_argument("--robot-insecure-tls", action="store_true",
                    help="allow a self-signed HTTPS cert when proxying "
                         "to the robot")
    ap.add_argument("--target", choices=("sim", "robot", "both"),
                    default="sim",
                    help="initial hub target; robot/both need a robot URL")
    ap.add_argument("--phase-obs", action="store_true", default=True,
                    help="enable phase-clock walk observations (default)")
    ap.add_argument("--no-phase-obs", dest="phase_obs",
                    action="store_false",
                    help="disable phase-clock walk observations")
    ap.add_argument("--phase-hz", type=float, default=0.1666667)
    ap.add_argument("--all-models", action="store_true")
    ap.add_argument("--no-vision", action="store_true",
                    help="disable the local /vision camera worker and page")
    ap.add_argument("--vision-camera", type=int, default=0)
    ap.add_argument("--vision-camera-cycle", type=_camera_indexes,
                    default=(0, 1), metavar="INDEXES")
    ap.add_argument("--vision-processing-width", type=int, default=1280)
    ap.add_argument("--vision-target-fps", type=float, default=10.0)
    ap.add_argument("--vision-opencv-threads", type=int, default=4)
    ap.add_argument(
        "--vision-capture-backend",
        choices=("auto", "avfoundation", "opencv"),
        default="auto",
        help="camera transport; auto prefers native macOS NV12 capture",
    )
    ap.add_argument("--vision-capture-width", type=int, default=1920)
    ap.add_argument("--vision-capture-height", type=int, default=1440)
    ap.add_argument("--vision-capture-fps", type=float, default=30.0)
    return ap


def _resolve_policy(pdir: Path, p: Path | None) -> Path | None:
    if p is None:
        return None
    raw = str(p)
    if raw.startswith("scripted:"):
        return Path(raw.removeprefix("scripted:"))
    return p if p.is_absolute() else pdir / p


def _browser_frames(args: argparse.Namespace) -> bool:
    if args.browser_frames == "on":
        return True
    if args.browser_frames == "off":
        return False
    return not args.viewer


def _reexec_under_mjpython_for_viewer() -> None:
    """macOS native MuJoCo viewer must run under mjpython."""
    if sys.platform != "darwin" or os.environ.get("MJPYTHON_BIN"):
        return
    mjpython = Path(sys.executable).with_name("mjpython")
    if not mjpython.is_file():
        sys.exit("native MuJoCo viewer on macOS needs mjpython; run:\n"
                 "  uv run mjpython -m rl_move.sim.web_server --viewer")
    os.execv(str(mjpython), [str(mjpython), "-m",
                             "rl_move.sim.web_server", *sys.argv[1:]])


def main(session_factory: Callable[..., Any] | None = None) -> None:
    args = build_arg_parser().parse_args()
    if args.https_port <= 0:
        raise SystemExit("--https-port must be positive")
    if bool(args.tls_cert) != bool(args.tls_key):
        raise SystemExit("--tls-cert and --tls-key must be provided together")
    if args.vision_camera < 0:
        raise SystemExit("--vision-camera must be non-negative")
    if (args.vision_processing_width != 0
            and args.vision_processing_width < 320):
        raise SystemExit("--vision-processing-width must be 0 or at least 320")
    if args.vision_target_fps <= 0.0:
        raise SystemExit("--vision-target-fps must be positive")
    if args.vision_opencv_threads <= 0:
        raise SystemExit("--vision-opencv-threads must be positive")
    if min(args.vision_capture_width, args.vision_capture_height) <= 0:
        raise SystemExit("--vision-capture-width/height must be positive")
    if args.vision_capture_fps <= 0.0:
        raise SystemExit("--vision-capture-fps must be positive")
    if args.viewer and session_factory is None:
        _reexec_under_mjpython_for_viewer()
    use_hub = session_factory is None
    if session_factory is None:
        from .web_session import SimWebConfig, SimWebSession
        cfg = SimWebConfig(
            policy_dir=args.policy_dir,
            stance=_resolve_policy(args.policy_dir, args.stance),
            walk=_resolve_policy(args.policy_dir, args.walk),
            recover=_resolve_policy(args.policy_dir, args.recover),
            log_dir=args.log_dir,
            realtime=args.realtime,
            viewer=args.viewer,
            web_frames=_browser_frames(args),
            phase_obs=args.phase_obs,
            phase_hz=args.phase_hz,
            all_models=args.all_models,
        )
        session_factory = SimWebSession
        sim_session = session_factory(cfg)
        from .web_hub import (HubController, RobotProxyTarget, SimTarget,
                              make_hub_handler)
        session = HubController(
            sim=SimTarget(sim_session),
            robot=RobotProxyTarget(
                args.robot_url,
                insecure_tls=args.robot_insecure_tls),
            target=args.target if args.robot_url else "sim")
        handler_factory = lambda: make_hub_handler(
            session, WEBUI_DIR, args.https_port, PAGE_PATHS, STATIC_FILES)
    else:
        session = session_factory(args)
        handler_factory = lambda: make_handler(
            session, https_port=args.https_port)
    http_srv = None
    https_srv = None
    https_thread = None
    vision_runtime = None
    try:
        handler = handler_factory()
        if not args.no_vision:
            linux_control = ROOT / "linux_control"
            if str(linux_control) not in sys.path:
                sys.path.insert(0, str(linux_control))
            from vision_server import (  # noqa: PLC0415
                DEFAULT_REPORT_DIR,
                DEFAULT_UI_DIR,
                VisionRuntime,
                materialize_default_config,
                wrap_handler_with_vision,
            )
            vision_runtime = VisionRuntime(
                materialize_default_config(),
                camera_index=args.vision_camera,
                camera_cycle=args.vision_camera_cycle,
                processing_width=args.vision_processing_width,
                target_fps=args.vision_target_fps,
                opencv_threads=args.vision_opencv_threads,
                capture_backend=args.vision_capture_backend,
                capture_width=args.vision_capture_width,
                capture_height=args.vision_capture_height,
                capture_fps=args.vision_capture_fps,
                robot_url=args.robot_url or None,
                report_dir=DEFAULT_REPORT_DIR,
            )
            vision_runtime.start()
            handler = wrap_handler_with_vision(
                handler, vision_runtime, DEFAULT_UI_DIR
            )
        cert_file = (args.tls_cert or DEFAULT_TLS_CERT).expanduser()
        key_file = (args.tls_key or DEFAULT_TLS_KEY).expanduser()
        ensure_tls_certificate(cert_file, key_file, args.bind,
                               configured=bool(args.tls_cert))
        https_srv = make_https_server(
            args.bind, args.https_port, handler, cert_file, key_file)
        https_thread = threading.Thread(
            target=https_srv.serve_forever,
            name="sim-web-https",
            daemon=True,
        )
        https_thread.start()

        http_srv = ThreadingHTTPServer((args.bind, args.http_port), handler)
        http_srv.daemon_threads = True
        http_url = f"http://{args.bind}:{args.http_port}/rl"
        https_url = f"https://{args.bind}:{args.https_port}/rl"
        print(f"sim web UI: {http_url}", flush=True)
        print(f"sim web UI (gamepad): {https_url}", flush=True)
        if vision_runtime is not None:
            print(
                f"vision UI: https://{args.bind}:{args.https_port}/vision "
                "(read-only)",
                flush=True,
            )
        if use_hub:
            robot = args.robot_url or "(connect from web UI)"
            print(f"hub target: {session.target} | robot: {robot}",
                  flush=True)
        run_viewer = getattr(session, "run_native_viewer", None)
        if args.viewer and run_viewer:
            server_thread = threading.Thread(target=http_srv.serve_forever,
                                             name="sim-web-http",
                                             daemon=True)
            server_thread.start()
            try:
                run_viewer(https_url)
            finally:
                http_srv.shutdown()
                server_thread.join(timeout=2.0)
        else:
            http_srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if http_srv is not None:
            http_srv.server_close()
        if https_srv is not None:
            https_srv.shutdown()
            https_srv.server_close()
        if https_thread is not None:
            https_thread.join(timeout=2.0)
        if vision_runtime is not None:
            vision_runtime.stop()
        close = getattr(session, "close", None)
        if close:
            close()


if __name__ == "__main__":
    main()
