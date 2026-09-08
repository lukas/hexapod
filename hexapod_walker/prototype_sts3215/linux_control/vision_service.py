"""Standalone Mac vision service on its own port and its own process.

Until this existed, ``VisionRuntime`` was started inside
``rl_move.sim.web_server``, so the camera worker and the robot control bridge
shared one process: restarting vision -- or having it die -- took the robot
bridge on :8898 down with it.  Running vision here means it can be restarted,
diagnosed and fixed on its own.

The service is deliberately incapable of moving the robot.  ``--robot-url`` is
passed to the tracker's ``FeedbackClient``, which only ever issues
``GET /api/feedback``; there is no arm, deploy or motor path in this process.
Its job is camera frames and pose estimation, nothing else.

Run it with the tracker virtualenv, which is where PyObjC and AVFoundation
live::

    uv run python -m linux_control.vision_service --port 8766

``sim_viewer/hexapod_vision_8766.sh`` is the supported launcher.
"""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parent

from vision_agent_stats import (  # noqa: E402
    DEFAULT_LOG_LIMIT,
    VISION_ROLE,
    VisionAgentStats,
)

DEFAULT_PORT = 8766
DEFAULT_BIND = "127.0.0.1"
MAX_LOG_LIMIT = 500
DEFAULT_DATA_DIR = Path(os.environ.get(
    "HEXAPOD_DATA_DIR",
    Path.home() / "Library" / "Application Support" / "Hexapod Lab" / "data",
)).expanduser()


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


def build_parser() -> argparse.ArgumentParser:
    """Mirror the ``--vision-*`` flags of the hub so tuning transfers.

    The names are kept identical to ``rl_move.sim.web_server`` on purpose: a
    capture setting worked out on one is pasted straight into the other.
    """
    ap = argparse.ArgumentParser(
        prog="vision_service",
        description="Serve the hexapod camera and pose estimator on its own "
                    "port, with no ability to command the robot.",
    )
    ap.add_argument("--bind", default=DEFAULT_BIND)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument(
        "--robot-url", default=None,
        help="robot web service, read with GET /api/feedback only, for the "
             "joint overlay; omit to run the camera with no robot contact",
    )
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
    ap.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR,
        help="Robot Lab data directory holding codex-runs attempt metadata",
    )
    ap.add_argument(
        "--agent-role", default=VISION_ROLE,
        help="lane role to report on the agent page and API",
    )
    return ap


def validate(args: argparse.Namespace) -> None:
    """Reject settings the capture worker would only fail on much later."""
    if args.vision_camera < 0:
        raise SystemExit("--vision-camera must be non-negative")
    if (args.vision_processing_width != 0
            and args.vision_processing_width < 320):
        raise SystemExit("--vision-processing-width must be 0 or at least 320")
    if args.vision_target_fps <= 0.0:
        raise SystemExit("--vision-target-fps must be positive")
    if args.vision_opencv_threads <= 0:
        raise SystemExit("--vision-opencv-threads must be positive")
    if args.vision_capture_fps <= 0.0:
        raise SystemExit("--vision-capture-fps must be positive")
    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be a valid TCP port")


AGENT_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vision agent · Hexapod</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;
background:#0c1110;color:#e8f1ec}
*{box-sizing:border-box}body{margin:0;padding:24px;max-width:1100px}
h1{font-size:24px;margin:0 0 4px}
.sub{color:#8fa79b;font-size:13px;margin-bottom:20px}
.sub a{color:#b7f34a}
.tiles{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:24px}
.tile{flex:1 1 150px;padding:14px 16px;border:1px solid #2a3932;
border-radius:14px;background:#141c19}
.tile .k{color:#8fa79b;font-size:11px;letter-spacing:.09em;
text-transform:uppercase}
.tile .v{font-size:22px;font-variant-numeric:tabular-nums;margin-top:6px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid #22302a}
th{color:#8fa79b;font-weight:600;font-size:11px;letter-spacing:.07em;
text-transform:uppercase}
td.n{text-align:right;font-variant-numeric:tabular-nums}
.bad{color:#ff8f8f}.ok{color:#b7f34a}
.empty{color:#8fa79b;padding:18px 0}
</style></head><body>
<h1>Vision agent</h1>
<div class="sub">Camera quality and pose estimation only &mdash; this lane
cannot arm or move the robot. &nbsp;<a href="/vision">Live vision UI</a>
&nbsp;<a href="/api/agent/usage">usage JSON</a>
&nbsp;<a href="/api/agent/log">log JSON</a></div>
<div class="tiles" id="tiles"></div>
<table><thead><tr>
<th>Started</th><th>Model</th><th class="n">Turns</th>
<th class="n">In</th><th class="n">Out</th><th class="n">Cache r/w</th>
<th class="n">Cost</th><th>Result</th></tr></thead>
<tbody id="rows"></tbody></table>
<div class="empty" id="empty" hidden>No vision-agent attempts recorded yet.</div>
<script>
const n = v => (typeof v === 'number') ? v.toLocaleString() : '—';
const usd = v => (typeof v === 'number') ? '$' + v.toFixed(4) : '—';
function tile(k, v){
  return '<div class="tile"><div class="k">' + k +
         '</div><div class="v">' + v + '</div></div>';
}
async function refresh(){
  const res = await fetch('/api/agent/log?limit=50');
  if(!res.ok) return;
  const data = await res.json();
  const t = data.totals || {}, d = data.last_24h || {};
  document.getElementById('tiles').innerHTML =
    tile('Attempts', n(t.attempts)) +
    tile('Failed', n(t.failed)) +
    tile('Input tokens', n(t.input_tokens)) +
    tile('Output tokens', n(t.output_tokens)) +
    tile('Cache read', n(t.cache_read_tokens)) +
    tile('Total cost', usd(t.cost_usd)) +
    tile('Cost 24h', usd(d.cost_usd));
  const rows = (data.attempts || []).map(a =>
    '<tr><td>' + (a.started_at || '—').replace('T', ' ').slice(0, 19) +
    '</td><td>' + (a.model || '') +
    '</td><td class="n">' + n(a.turns) +
    '</td><td class="n">' + n(a.input_tokens) +
    '</td><td class="n">' + n(a.output_tokens) +
    '</td><td class="n">' + n(a.cache_read_tokens) + ' / ' +
    n(a.cache_write_tokens) +
    '</td><td class="n">' + usd(a.cost_usd) +
    '</td><td class="' + (a.ok ? 'ok' : 'bad') + '">' +
    (a.ok ? 'ok' : 'failed') + '</td></tr>').join('');
  document.getElementById('rows').innerHTML = rows;
  document.getElementById('empty').hidden = rows.length > 0;
}
refresh();
setInterval(refresh, 15000);
</script></body></html>
"""


def make_base_handler(stats: VisionAgentStats,
                      role: str) -> type[BaseHTTPRequestHandler]:
    """Routes this service owns outside the tracker's ``/api/vision`` tree.

    The tracker handler answers every ``/api/vision/*`` path itself and 404s
    the ones it does not know, so the agent endpoints deliberately live under
    ``/api/agent/*`` where they cannot be swallowed.
    """

    class Handler(BaseHTTPRequestHandler):
        server_version = "hexapod-vision"
        protocol_version = "HTTP/1.1"

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass

        def _json(self, code: int, payload: Any) -> None:
            self._send(
                code,
                json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                "application/json; charset=utf-8",
            )

        def _limit(self) -> int:
            raw = parse_qs(urlsplit(self.path).query).get("limit", [""])[0]
            try:
                value = int(raw)
            except ValueError:
                return DEFAULT_LOG_LIMIT
            return max(1, min(MAX_LOG_LIMIT, value))

        def do_GET(self) -> None:  # noqa: N802 - http.server API
            path = urlsplit(self.path).path
            if path == "/healthz":
                self._json(HTTPStatus.OK, {
                    "ok": True,
                    "service": "hexapod-vision",
                    "role": role,
                    "motion_capable": False,
                })
            elif path == "/api/agent/log":
                self._json(HTTPStatus.OK,
                           stats.snapshot(limit=self._limit()))
            elif path == "/api/agent/usage":
                snapshot = stats.snapshot(limit=1)
                self._json(HTTPStatus.OK, {
                    "role": snapshot["role"],
                    "totals": snapshot["totals"],
                    "last_24h": snapshot["last_24h"],
                    "by_model": snapshot["by_model"],
                    "attempts_recorded": snapshot["scanned"],
                    "generated_at": snapshot["generated_at"],
                })
            elif path in {"/agent", "/agent/"}:
                self._send(HTTPStatus.OK, AGENT_PAGE.encode("utf-8"),
                           "text/html; charset=utf-8")
            elif path in {"", "/"}:
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/vision")
                self.send_header("Content-Length", "0")
                self.end_headers()
            else:
                self._json(HTTPStatus.NOT_FOUND,
                           {"ok": False, "error": "not found"})

        def do_POST(self) -> None:  # noqa: N802 - http.server API
            # Everything this service can be asked to change lives under the
            # tracker's own /api/vision routes, which are handled before this.
            self._json(HTTPStatus.NOT_FOUND,
                       {"ok": False, "error": "not found"})

        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("%s - %s\n" % (
                self.address_string(), fmt % args))

    return Handler


def build_runtime(args: argparse.Namespace) -> tuple[Any, type, Path]:
    """Construct the tracker runtime exactly as the hub used to.

    Imported lazily so ``--help`` and the argument tests do not need PyObjC.
    """
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from vision_server import (  # noqa: PLC0415
        DEFAULT_REPORT_DIR,
        DEFAULT_UI_DIR,
        VisionRuntime,
        materialize_default_config,
        wrap_handler_with_vision,
    )
    runtime = VisionRuntime(
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
    return runtime, wrap_handler_with_vision, DEFAULT_UI_DIR


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate(args)
    stats = VisionAgentStats(args.data_dir)
    runtime, wrap_handler_with_vision, ui_dir = build_runtime(args)
    handler = wrap_handler_with_vision(
        make_base_handler(stats, args.agent_role), runtime, ui_dir)
    runtime.start()
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    server.daemon_threads = True
    print(f"vision UI:    http://{args.bind}:{args.port}/vision", flush=True)
    print(f"agent log:    http://{args.bind}:{args.port}/agent", flush=True)
    print(f"robot target: {args.robot_url or '(none)'} "
          "(read-only GET /api/feedback)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        runtime.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
