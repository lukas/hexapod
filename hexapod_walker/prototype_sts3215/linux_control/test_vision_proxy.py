"""The hub keeps serving /vision from another process, or says so plainly.

The two behaviours worth protecting are that an endless MJPEG body is relayed
rather than buffered, and that a vision service which is down produces a 503
instead of the hub quietly opening a camera of its own.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
from typing import Any
import urllib.error
import urllib.request

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import vision_proxy  # noqa: E402

FRAME_COUNT = 5


class _Upstream(BaseHTTPRequestHandler):
    """A stand-in vision service: one static route, one endless stream."""

    protocol_version = "HTTP/1.1"
    posted: list[tuple[str, bytes]] = []

    def log_message(self, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        if self.path.startswith("/api/vision/frame.mjpg"):
            self.send_response(200)
            self.send_header(
                "Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Connection", "close")
            self.end_headers()
            for index in range(FRAME_COUNT):
                self.wfile.write(b"--frame\r\n\r\npart%d\r\n" % index)
                self.wfile.flush()
                time.sleep(0.01)
            return
        if self.path.startswith("/vision"):
            body = b"<html>vision ui</html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/vision/state":
            body = json.dumps({"ok": True, "camera": "idle"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        body = json.dumps({"ok": False, "error": "not found"}).encode()
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", "0") or 0)
        _Upstream.posted.append((self.path, self.rfile.read(length)))
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _Hub(BaseHTTPRequestHandler):
    """Whatever the hub itself serves; the proxy must leave it alone."""

    protocol_version = "HTTP/1.1"

    def log_message(self, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        body = b'{"hub":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        self.do_GET()


def _serve(handler: type) -> tuple[str, ThreadingHTTPServer, threading.Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{server.server_port}", server, thread


@pytest.fixture()
def upstream():
    _Upstream.posted = []
    url, server, thread = _serve(_Upstream)
    try:
        yield url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture()
def hub(upstream: str):
    handler = vision_proxy.wrap_handler_with_vision_proxy(_Hub, upstream)
    url, server, thread = _serve(handler)
    try:
        yield url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture()
def hub_without_upstream():
    # Port 1 is reserved and never listening, so this is a closed upstream
    # without the flakiness of binding and releasing a real port.
    handler = vision_proxy.wrap_handler_with_vision_proxy(
        _Hub, "http://127.0.0.1:1")
    url, server, thread = _serve(handler)
    try:
        yield url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _get(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


@pytest.mark.parametrize("path,expected", [
    ("/vision", True),
    ("/vision/", True),
    ("/vision/assets/app.js", True),
    ("/api/vision", True),
    ("/api/vision/state", True),
    ("/visionary", False),
    ("/api/sim/state", False),
    ("/rl", False),
])
def test_only_vision_paths_are_proxied(path: str, expected: bool) -> None:
    assert vision_proxy.is_proxied(path) is expected


def test_vision_ui_is_served_through_the_hub(hub: str) -> None:
    status, body = _get(f"{hub}/vision")
    assert status == 200
    assert b"vision ui" in body


def test_non_vision_paths_still_reach_the_hub(hub: str) -> None:
    status, body = _get(f"{hub}/api/sim/state")
    assert status == 200
    assert json.loads(body) == {"hub": True}


def test_upstream_404_is_passed_through_not_masked(hub: str) -> None:
    status, body = _get(f"{hub}/api/vision/unknown")
    assert status == 404
    assert json.loads(body)["error"] == "not found"


def test_posts_are_forwarded_with_their_body(hub: str) -> None:
    request = urllib.request.Request(
        f"{hub}/api/vision/camera/start",
        data=b'{"index":1}',
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 200
    assert _Upstream.posted == [("/api/vision/camera/start", b'{"index":1}')]


def test_mjpeg_is_relayed_frame_by_frame(hub: str) -> None:
    """A buffered read would return nothing until the stream ended."""
    with urllib.request.urlopen(f"{hub}/api/vision/frame.mjpg",
                                timeout=10) as response:
        assert response.headers["Content-Type"].startswith("multipart/")
        first = response.read(len(b"--frame\r\n\r\npart0\r\n"))
        assert b"part0" in first
        rest = response.read()
    assert b"part%d" % (FRAME_COUNT - 1) in rest


def test_down_upstream_returns_503_and_names_it(
        hub_without_upstream: str) -> None:
    status, body = _get(f"{hub_without_upstream}/api/vision/state")
    assert status == 503
    payload = json.loads(body)
    assert payload["ok"] is False
    assert payload["upstream"] == "http://127.0.0.1:1"


def test_down_upstream_never_falls_back_to_local_capture() -> None:
    """The whole point of the split: no camera in the robot-bridge process."""
    source = (HERE / "vision_proxy.py").read_text(encoding="utf-8")
    assert "VisionRuntime" not in source
    assert "vision_server" not in source


def test_hub_still_answers_while_vision_is_down(
        hub_without_upstream: str) -> None:
    status, body = _get(f"{hub_without_upstream}/api/sim/state")
    assert status == 200
    assert json.loads(body) == {"hub": True}
