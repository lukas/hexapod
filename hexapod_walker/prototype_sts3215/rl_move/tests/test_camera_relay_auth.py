"""Exercise the deployed Caddy routing against local mock auth/app servers.

No camera, cluster endpoint, login record, or real credential is accessed.
"""
import base64
from contextlib import ExitStack
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
from types import SimpleNamespace

import pytest


CONFIG = Path(__file__).resolve().parents[4] / "experiment_lab/deploy/camera-relay.Caddyfile"
# `caddy hash-password --algorithm bcrypt --bcrypt-cost 4 --plaintext test-only-secret`
TEST_HASH = "$2a$04$ldiLDm17j9ZfXcGLSCvJ5.pvzpfyhMic4YZNCo4isXE9DoUrxcZZ6"
SSO_COOKIE = "hexapod_sso=test-only-session"


def basic(user, password="test-only-secret"):
    encoded = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(port, path, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
    try:
        connection.request("GET", path, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read().decode()
    finally:
        connection.close()


@pytest.fixture(scope="module")
def relay(tmp_path_factory):
    caddy = shutil.which("caddy")
    if caddy is None:
        pytest.skip("Caddy is required to exercise the actual relay configuration")
    directory = tmp_path_factory.mktemp("camera-relay-auth")
    events = {"auth": [], "camera": [], "lab": []}

    def handler_for(service):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                events[service].append((self.path, dict(self.headers)))
                code, body, user = 200, service, None
                if service == "auth":
                    assert self.path == "/auth"
                    if self.headers.get("Cookie") == SSO_COOKIE:
                        user = "test-user"
                    else:
                        code, body = 401, "auth-denied"
                elif service == "lab":
                    valid_key = (
                        self.headers.get("Authorization") == "Bearer test-api-key"
                        or self.headers.get("X-API-Key") == "test-api-key")
                    if self.path not in ("/healthz", "/robots.txt") and not valid_key:
                        code, body = 401, "lab-denied"
                self.send_response(code)
                self.send_header("Content-Length", str(len(body)))
                if user:
                    self.send_header("X-Hexapod-User", user)
                self.end_headers()
                self.wfile.write(body.encode())

        return Handler

    with ExitStack() as cleanup:
        upstreams = {}
        for service in events:
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(service))
            worker = threading.Thread(
                target=lambda s=server: s.serve_forever(poll_interval=0.01), daemon=True)
            worker.start()
            cleanup.callback(server.server_close)
            cleanup.callback(worker.join, 1)
            cleanup.callback(server.shutdown)
            upstreams[service] = f"127.0.0.1:{server.server_port}"

        camera_port, lab_port = free_port(), free_port()
        source = CONFIG.read_text()
        replacements = {
            "camera.cwd1f0-new-cluster.coreweave.app {": f"http://127.0.0.1:{camera_port} {{",
            "robot-lab.cwd1f0-new-cluster.coreweave.app {": f"http://127.0.0.1:{lab_port} {{",
            "https://hexapod.cwd1f0-new-cluster.coreweave.app": f"http://{upstreams['auth']}",
            "127.0.0.1:8766": upstreams["camera"],
            "127.0.0.1:8767": upstreams["lab"],
            "{env.LAB_LOGIN_HASH}": TEST_HASH,
        }
        for original, replacement in replacements.items():
            assert original in source, f"Relay config changed: missing {original}"
            source = source.replace(original, replacement)
        # Disable the admin listener and certificate automation in this local harness.
        config = directory / "Caddyfile"
        config.write_text("{\n admin off\n auto_https off\n}\n" + source)
        adapted = subprocess.run(
            [caddy, "adapt", "--config", str(config), "--adapter", "caddyfile"],
            capture_output=True, text=True, timeout=2)
        assert adapted.returncode == 0, adapted.stderr
        document = json.loads(adapted.stdout)

        def assert_local_upstreams(node):
            if isinstance(node, dict):
                if "upstreams" in node:
                    assert all(upstream["dial"] in upstreams.values()
                               for upstream in node["upstreams"])
                for value in node.values():
                    assert_local_upstreams(value)
            elif isinstance(node, list):
                for value in node:
                    assert_local_upstreams(value)

        assert_local_upstreams(document)
        runtime_config = directory / "config.json"
        runtime_config.write_text(json.dumps(document))
        with (directory / "caddy.log").open("w+") as log:
            process = subprocess.Popen(
                [caddy, "run", "--config", str(runtime_config)],
                cwd=directory, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 2
                while True:
                    try:
                        with socket.create_connection(("127.0.0.1", camera_port), timeout=0.05):
                            break
                    except OSError:
                        if process.poll() is not None or time.monotonic() >= deadline:
                            log.seek(0)
                            pytest.fail(f"Local Caddy did not start: {log.read()}")
                        time.sleep(0.01)
                yield SimpleNamespace(camera=camera_port, lab=lab_port, events=events)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer invalid"},
    {"X-API-Key": "invalid"},
    {"X-Hexapod-User": "forged", "Authorization": "Bearer invalid"},
    {"Cookie": "hexapod_sso=invalid"},
    basic("lukas", "wrong-password"),
])
def test_camera_requires_valid_basic_or_sso(relay, headers):
    before = len(relay.events["camera"])
    status, _ = request(relay.camera, "/api/vision/status", headers)
    assert status == 401
    assert len(relay.events["camera"]) == before


@pytest.mark.parametrize("user", ["lukas", "camera"])
def test_valid_basic_camera_clients_skip_sso(relay, user):
    auth_calls = len(relay.events["auth"])
    assert request(relay.camera, "/api/vision/status", basic(user)) == (200, "camera")
    assert len(relay.events["auth"]) == auth_calls


def test_valid_sso_reaches_camera_with_verified_identity(relay):
    auth_calls = len(relay.events["auth"])
    assert request(relay.camera, "/api/vision/status", {
        "Cookie": SSO_COOKIE, "X-Hexapod-User": "forged"
    }) == (200, "camera")
    assert len(relay.events["auth"]) == auth_calls + 1
    assert relay.events["camera"][-1][1]["X-Hexapod-User"] == "test-user"


@pytest.mark.parametrize("path,headers,expected", [
    ("/private", {"Authorization": "Bearer test-api-key"}, (200, "lab")),
    ("/private", {"X-API-Key": "test-api-key"}, (200, "lab")),
    ("/private", {"Authorization": "Bearer invalid"}, (401, "lab-denied")),
    ("/private", {"X-API-Key": "invalid"}, (401, "lab-denied")),
    ("/mcp", {"Authorization": "Bearer test-api-key"}, (200, "lab")),
    ("/mcp", {}, (401, "lab-denied")),
    ("/healthz", {}, (200, "lab")),
    ("/robots.txt", {}, (200, "lab")),
])
def test_robot_lab_exemptions_retain_application_auth(relay, path, headers, expected):
    auth_calls, app_calls = len(relay.events["auth"]), len(relay.events["lab"])
    assert request(relay.lab, path, headers) == expected
    assert len(relay.events["auth"]) == auth_calls
    assert len(relay.events["lab"]) == app_calls + 1
