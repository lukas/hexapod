"""Forward the hub's ``/vision`` routes to the standalone vision service.

The camera used to run inside ``rl_move.sim.web_server``.  Now that it has its
own process, the hub keeps the same URLs working by proxying them, so existing
bookmarks, the Robot Lab camera gallery and the CoreWeave tunnel do not have to
learn a second port.

Two properties matter more than throughput here:

* ``/api/vision/frame.mjpg`` never ends.  It is relayed chunk by chunk and
  stops as soon as either side goes away, instead of being buffered.
* When the vision service is down the proxy answers ``503``.  It must never
  fall back to starting a camera in this process -- that would silently
  recreate the coupling the split exists to remove.
"""

from __future__ import annotations

from http import HTTPStatus
import json
import socket
from typing import Any, Mapping
import urllib.error
import urllib.request
from urllib.parse import urlsplit

#: Paths the standalone service owns.  Everything else falls through to the
#: hub's own handler.
PROXIED_PREFIXES = ("/api/vision/", "/vision/")
PROXIED_EXACT = ("/vision", "/api/vision")

STREAM_CHUNK_BYTES = 32768
CONNECT_TIMEOUT_S = 5.0
STREAM_IDLE_TIMEOUT_S = 30.0

# Headers that describe one hop and must not be copied to the other.
_HOP_BY_HOP = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
})


def is_proxied(path: str) -> bool:
    return path in PROXIED_EXACT or path.startswith(PROXIED_PREFIXES)


def _is_stream(path: str, content_type: str) -> bool:
    """Treat anything multipart as endless, not just the known frame route."""
    return (path == "/api/vision/frame.mjpg"
            or content_type.startswith("multipart/"))


def wrap_handler_with_vision_proxy(base_handler: type,
                                   upstream: str) -> type:
    """Add ``/vision`` and ``/api/vision/*`` routes proxied to ``upstream``."""
    origin = upstream.rstrip("/")

    class Handler(base_handler):  # type: ignore[valid-type,misc]
        def _proxy_unavailable(self, detail: str) -> None:
            body = json.dumps({
                "ok": False,
                "error": "vision service unavailable",
                "upstream": origin,
                "detail": detail,
            }, separators=(",", ":")).encode("utf-8")
            self.send_response(HTTPStatus.SERVICE_UNAVAILABLE)
            self.send_header("Content-Type",
                             "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass

        def _proxy_relay_headers(self, response: Any) -> None:
            for name, value in response.headers.items():
                if name.lower() in _HOP_BY_HOP:
                    continue
                self.send_header(name, value)

        def _proxy_stream(self, response: Any) -> None:
            """Relay an open-ended body until either end stops."""
            while True:
                try:
                    chunk = response.read(STREAM_CHUNK_BYTES)
                except (OSError, socket.timeout):
                    return
                if not chunk:
                    return
                try:
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except OSError:
                    # The browser closed the stream; drop it without noise.
                    return

        def _proxy(self, method: str, body: bytes | None = None) -> None:
            split = urlsplit(self.path)
            target = origin + split.path
            if split.query:
                target += "?" + split.query
            headers: dict[str, str] = {}
            for name in ("Accept", "Content-Type", "Range"):
                value = self.headers.get(name)
                if value:
                    headers[name] = value
            request = urllib.request.Request(
                target, data=body, headers=headers, method=method)
            try:
                response = urllib.request.urlopen(
                    request, timeout=CONNECT_TIMEOUT_S)
            except urllib.error.HTTPError as error:
                # An upstream 4xx is a real answer: pass it through intact so
                # the page sees the tracker's own error body.
                response = error
            except (urllib.error.URLError, OSError) as error:
                self._proxy_unavailable(str(getattr(error, "reason", error)))
                return
            with response:
                content_type = response.headers.get("Content-Type", "")
                streaming = _is_stream(split.path, content_type)
                self.send_response(response.status)
                self._proxy_relay_headers(response)
                if streaming:
                    # Length is unknown and the socket must not be reused.
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.close_connection = True
                    _set_idle_timeout(response, STREAM_IDLE_TIMEOUT_S)
                    self._proxy_stream(response)
                    return
                payload = response.read()
                if "Content-Length" not in response.headers:
                    self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                try:
                    self.wfile.write(payload)
                except OSError:
                    pass

        def do_GET(self) -> None:  # noqa: N802 - http.server API
            if is_proxied(urlsplit(self.path).path):
                self._proxy("GET")
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802 - http.server API
            if not is_proxied(urlsplit(self.path).path):
                super().do_POST()
                return
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length > 8_000_000:
                self._proxy_unavailable("request body is too large")
                return
            self._proxy("POST", self.rfile.read(length) if length else b"")

    return Handler


def _set_idle_timeout(response: Any, seconds: float) -> None:
    """Bound how long a stalled frame stream may hold this worker thread.

    ``urlopen``'s connect timeout does not cover an idle body, so a vision
    service that accepts the connection and then stops producing frames would
    otherwise pin a handler thread forever.  Best effort: the attribute path is
    private, and losing the timeout is better than failing the stream.
    """
    try:
        response.fp.raw._sock.settimeout(seconds)
    except (AttributeError, OSError):
        pass


def upstream_health(upstream: str, *,
                    timeout: float = CONNECT_TIMEOUT_S) -> Mapping[str, Any]:
    """One-shot probe used by launchers and status commands."""
    target = upstream.rstrip("/") + "/api/vision/health"
    try:
        with urllib.request.urlopen(target, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as error:
        return {"ok": False, "upstream": upstream, "error": str(error)}
    if not isinstance(payload, dict):
        return {"ok": False, "upstream": upstream,
                "error": "health response is not an object"}
    return payload
