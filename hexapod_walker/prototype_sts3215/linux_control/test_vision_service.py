"""The standalone vision service's own routes, without a camera.

``build_runtime`` is the only part that needs PyObjC, and it is imported
lazily, so everything here runs on a machine with no camera attached.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import threading
from http.server import ThreadingHTTPServer
from typing import Any
import urllib.error
import urllib.request

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import vision_service  # noqa: E402
from vision_agent_stats import VisionAgentStats  # noqa: E402


@pytest.fixture()
def service(tmp_path: Path):
    """Serve only the routes this module owns, with no tracker wrapper."""
    handler = vision_service.make_base_handler(
        VisionAgentStats(tmp_path), vision_service.VISION_ROLE)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _get(url: str) -> tuple[int, Any]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        body = error.read()
        status = error.code
    try:
        return status, json.loads(body.decode("utf-8"))
    except ValueError:
        return status, body.decode("utf-8", "replace")


def test_healthz_declares_the_service_cannot_move_the_robot(
        service: str) -> None:
    status, payload = _get(f"{service}/healthz")
    assert status == 200
    assert payload["ok"] is True
    assert payload["service"] == "hexapod-vision"
    assert payload["motion_capable"] is False


def test_agent_endpoints_are_outside_the_tracker_namespace() -> None:
    """They must not start with /api/vision/, which the tracker 404s itself."""
    source = (HERE / "vision_service.py").read_text(encoding="utf-8")
    assert '"/api/agent/log"' in source
    assert '"/api/agent/usage"' in source
    assert "/api/vision/agent" not in source


def test_usage_is_empty_but_well_formed_before_any_run(service: str) -> None:
    status, payload = _get(f"{service}/api/agent/usage")
    assert status == 200
    assert payload["role"] == "vision"
    assert payload["totals"]["attempts"] == 0
    assert payload["totals"]["cost_usd"] == 0
    assert payload["by_model"] == {}


def test_log_reports_recorded_attempts(service: str, tmp_path: Path) -> None:
    run_dir = tmp_path / "codex-runs" / "job-a" / "attempt-1"
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(json.dumps({
        "job_id": "job-a", "attempt": 1, "kind": "vision",
        "provider": "claude", "model": "claude-opus-5", "returncode": 0,
        "started_at": "2026-09-07T10:00:00+00:00",
        "usage": {"cost_usd": 0.5, "input_tokens": 10, "output_tokens": 2},
    }), encoding="utf-8")
    status, payload = _get(f"{service}/api/agent/log")
    assert status == 200
    assert [item["job_id"] for item in payload["attempts"]] == ["job-a"]
    assert payload["totals"]["input_tokens"] == 10


def test_log_limit_is_clamped(service: str) -> None:
    for query in ("?limit=0", "?limit=-5", "?limit=99999", "?limit=nonsense"):
        status, _ = _get(f"{service}/api/agent/log{query}")
        assert status == 200, query


def test_agent_page_is_served_and_links_the_api(service: str) -> None:
    status, body = _get(f"{service}/agent")
    assert status == 200
    assert "/api/agent/usage" in body
    assert "cannot arm or move the robot" in body


def test_unknown_paths_are_json_404(service: str) -> None:
    status, payload = _get(f"{service}/nope")
    assert status == 404
    assert payload["ok"] is False


def test_root_redirects_to_the_vision_ui(service: str) -> None:
    request = urllib.request.Request(f"{service}/")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args: Any, **kwargs: Any) -> None:
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=5) as response:
            assert response.status == 302
            assert response.headers["Location"] == "/vision"
    except urllib.error.HTTPError as error:
        assert error.code == 302
        assert error.headers["Location"] == "/vision"


def test_parser_defaults_match_the_hub(tmp_path: Path) -> None:
    args = vision_service.build_parser().parse_args([])
    assert args.port == 8766
    assert args.bind == "127.0.0.1"
    assert args.vision_capture_width == 1920
    assert args.vision_capture_height == 1440
    assert args.vision_capture_fps == 30.0
    assert args.vision_target_fps == 10.0
    assert args.vision_processing_width == 1280
    assert args.vision_camera_cycle == (0, 1)


@pytest.mark.parametrize("argv", [
    ["--vision-camera", "-1"],
    ["--vision-processing-width", "100"],
    ["--vision-target-fps", "0"],
    ["--vision-opencv-threads", "0"],
    ["--vision-capture-fps", "0"],
    ["--port", "0"],
])
def test_invalid_settings_are_rejected_up_front(argv: list[str]) -> None:
    args = vision_service.build_parser().parse_args(argv)
    with pytest.raises(SystemExit):
        vision_service.validate(args)
