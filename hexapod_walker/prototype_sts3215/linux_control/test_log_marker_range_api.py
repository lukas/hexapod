"""Off-robot tests for exact marker-bounded robot log downloads."""
from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import sys
from urllib.parse import urlencode

_HERE = Path(__file__).resolve().parent
for _path in (_HERE, _HERE.parent / "motor_setup"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import event_log  # noqa: E402
import web_drive as web_drive_module  # noqa: E402


def _marker(marker_id: str) -> dict:
    return {
        "schema_version": 2,
        "record_type": "marker",
        "marker_id": marker_id,
    }


def _encode(rows: list[dict]) -> bytes:
    return b"".join((json.dumps(row) + "\n").encode() for row in rows)


def _request(path: str) -> tuple[int, dict[str, str], bytes]:
    handler_cls = web_drive_module.Handler
    handler = handler_cls.__new__(handler_cls)
    handler.path = path
    handler.command = "GET"
    handler.headers = {"Content-Length": "0"}
    handler.rfile = BytesIO()
    handler.wfile = BytesIO()
    handler._headers = {}
    handler.send_response = lambda code: setattr(handler, "_code", code)
    handler.send_header = (
        lambda key, value: handler._headers.__setitem__(key, value)
    )
    handler.end_headers = lambda: None
    handler_cls.do_GET(handler)
    return handler._code, handler._headers, handler.wfile.getvalue()


def _quiet_event_log(monkeypatch, log_dir: Path) -> None:
    monkeypatch.setattr(event_log, "log_dir", lambda: log_dir)
    monkeypatch.setattr(event_log, "emit_http", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        event_log, "emit_api_error", lambda *_args, **_kwargs: None
    )


def test_log_api_returns_inclusive_exact_marker_range(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir()
    _quiet_event_log(monkeypatch, logs)
    rows = [
        {"record_type": "serial_tx", "data_hex": "old"},
        _marker("begin/exact+marker"),
        {"record_type": "serial_rx", "data_hex": "inside"},
        _marker("end exact marker"),
        {"record_type": "serial_tx", "data_hex": "later"},
    ]
    (logs / "telemetry.jsonl").write_bytes(_encode(rows))
    query = urlencode({
        "from_marker": "begin/exact+marker",
        "through_marker": "end exact marker",
    })

    code, headers, body = _request(f"/api/logs/telemetry.jsonl?{query}")

    assert code == 200
    assert headers["Content-Type"] == "application/x-ndjson"
    assert int(headers["Content-Length"]) == len(body)
    assert body == _encode(rows[1:4])


def test_log_api_supports_each_bound_for_rotated_parts(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir()
    _quiet_event_log(monkeypatch, logs)
    first = [
        {"record_type": "serial_tx", "data_hex": "old"},
        _marker("begin-rotated"),
        {"record_type": "serial_rx", "data_hex": "first"},
    ]
    last = [
        {"record_type": "serial_rx", "data_hex": "last"},
        _marker("end-rotated"),
        {"record_type": "serial_tx", "data_hex": "later"},
    ]
    (logs / "part-1.jsonl").write_bytes(_encode(first))
    (logs / "part-2.jsonl").write_bytes(_encode(last))

    first_code, _, first_body = _request(
        "/api/logs/part-1.jsonl?from_marker=begin-rotated"
    )
    last_code, _, last_body = _request(
        "/api/logs/part-2.jsonl?through_marker=end-rotated"
    )

    assert first_code == 200
    assert first_body == _encode(first[1:])
    assert last_code == 200
    assert last_body == _encode(last[:2])


def test_log_api_rejects_missing_marker_and_ambiguous_tail(
    tmp_path, monkeypatch,
):
    logs = tmp_path / "logs"
    logs.mkdir()
    _quiet_event_log(monkeypatch, logs)
    (logs / "telemetry.jsonl").write_bytes(_encode([_marker("present")]))

    missing_code, _, missing_body = _request(
        "/api/logs/telemetry.jsonl?from_marker=absent"
    )
    mixed_code, _, mixed_body = _request(
        "/api/logs/telemetry.jsonl?tail=1&through_marker=present"
    )

    assert missing_code == 416
    assert "from_marker not found" in json.loads(missing_body)["error"]
    assert mixed_code == 400
    assert "tail cannot be combined" in json.loads(mixed_body)["error"]


def test_log_api_keeps_tail_and_path_traversal_behavior(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir()
    _quiet_event_log(monkeypatch, logs)
    rows = [{"line": 1}, {"line": 2}, {"line": 3}]
    (logs / "ordinary.jsonl").write_bytes(_encode(rows))
    (tmp_path / "secret.jsonl").write_text("outside log directory\n")
    (logs / "linked.jsonl").symlink_to(tmp_path / "secret.jsonl")

    tail_code, _, tail_body = _request(
        "/api/logs/ordinary.jsonl?tail=2"
    )
    traversal_code, _, traversal_body = _request(
        "/api/logs/../secret.jsonl?from_marker=anything"
    )
    encoded_code, _, encoded_body = _request(
        "/api/logs/..%2Fsecret.jsonl?from_marker=anything"
    )
    symlink_code, _, symlink_body = _request(
        "/api/logs/linked.jsonl?from_marker=anything"
    )

    assert tail_code == 200
    assert tail_body == _encode(rows[-2:])
    assert traversal_code == 404
    assert b"outside log directory" not in traversal_body
    assert encoded_code == 404
    assert b"outside log directory" not in encoded_body
    assert symlink_code == 404
    assert b"outside log directory" not in symlink_body
