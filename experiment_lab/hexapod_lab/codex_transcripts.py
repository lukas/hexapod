"""Private, integrity-checked archives for Codex attempt transcripts.

Codex output is deliberately kept outside ``experiments/<id>``.  Experiment
evidence is immutable once its manifest is sealed; analysis performed later is
an audit record *about* that evidence, not additional experimental evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Dict, Optional, Tuple
import uuid

from .communication_capture import STATUS_NAME, TRANSCRIPT_NAME


TRANSCRIPT_MANIFEST = "transcript.manifest.json"
ROBOT_COMMUNICATION_MANIFEST = "robot-communication.manifest.json"
TRANSCRIPT_FILES = (
    "transcript.md",
    "events.jsonl",
    STATUS_NAME,
    TRANSCRIPT_NAME,
)
_ARCHIVED_FILES = (
    "prompt.md", "events.jsonl", "transcript.md", "stderr.log",
)
_ROBOT_COMMUNICATION_FILES = (STATUS_NAME, TRANSCRIPT_NAME)
_ATTEMPT_NAME = re.compile(r"attempt-([1-9][0-9]*)$")
_SHA256 = re.compile(r"[0-9a-f]{64}$")
_LOSS_COUNTERS = (
    "queue_dropped",
    "communication_dropped",
    "uncaptured_bytes",
    "capture_errors",
)
_HEALTHY_RECORDER_FIELDS = {
    "active": True,
    "communication_capture": True,
    "communication_scope": "host_mcu_serial",
    "communication_rate_limited": False,
    "piggyback_snapshots": False,
    "writer_alive": True,
    "write_error": None,
}
_CAPTURE_STATES = {
    "recording",
    "retryable",
    "terminal_complete",
    "terminal_incomplete",
}


class CodexTranscriptError(RuntimeError):
    pass


class CodexTranscriptNotFound(CodexTranscriptError):
    pass


class CodexTranscriptIntegrityError(CodexTranscriptError):
    pass


def _atomic_write(path: Path, payload: bytes, *, mode: int = 0o600) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_robot_communication_status(
    run_dir: Path,
    *,
    expected_job_id: str,
    expected_experiment_id: Optional[str],
    expected_attempt: int,
) -> Dict[str, Any]:
    status_path = run_dir / STATUS_NAME
    if status_path.is_symlink() or not status_path.is_file():
        raise CodexTranscriptIntegrityError(
            "Robot communication status is missing or unsafe"
        )
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CodexTranscriptIntegrityError(
            "Robot communication status is invalid"
        ) from exc
    if not isinstance(status, dict) or status.get("schema_version") != 1:
        raise CodexTranscriptIntegrityError(
            "Robot communication status schema is invalid"
        )
    if (
        status.get("job_id") != expected_job_id
        or status.get("experiment_id") != expected_experiment_id
        or status.get("attempt") != expected_attempt
        or isinstance(status.get("attempt"), bool)
    ):
        raise CodexTranscriptIntegrityError(
            "Robot communication status identity mismatch"
        )
    if not isinstance(status.get("complete"), bool):
        raise CodexTranscriptIntegrityError(
            "Robot communication status completeness is invalid"
        )
    capture_state = status.get("capture_state")
    if capture_state is not None and capture_state not in _CAPTURE_STATES:
        raise CodexTranscriptIntegrityError(
            "Robot communication capture lifecycle is invalid"
        )
    return status


def _status_marker(
    status: Dict[str, Any], name: str,
) -> str:
    marker = status.get(name)
    if not isinstance(marker, str) or not marker:
        raise CodexTranscriptIntegrityError(
            f"Robot communication status has no {name.replace('_', ' ')}"
        )
    return marker


def _status_recorder_checkpoint(
    status: Dict[str, Any],
    *,
    name: str,
    marker: str,
) -> Tuple[Dict[str, int], int]:
    recorder = status.get(name)
    if not isinstance(recorder, dict):
        raise CodexTranscriptIntegrityError(
            f"Robot communication status has no {name.replace('_', ' ')}"
        )
    for field, expected in _HEALTHY_RECORDER_FIELDS.items():
        if recorder.get(field) != expected:
            raise CodexTranscriptIntegrityError(
                f"Robot communication {name.replace('_', ' ')} is unhealthy"
            )
    if recorder.get("flushed_marker") != marker:
        raise CodexTranscriptIntegrityError(
            f"Robot communication {name.replace('_', ' ')} marker mismatch"
        )
    acknowledgement = recorder.get("marker_ack")
    if (
        not isinstance(acknowledgement, dict)
        or acknowledgement.get("marker_id") != marker
    ):
        raise CodexTranscriptIntegrityError(
            f"Robot communication {name.replace('_', ' ')} acknowledgement mismatch"
        )
    path = acknowledgement.get("path")
    paths = acknowledgement.get("paths")
    if (
        not isinstance(path, str)
        or not path
        or not isinstance(paths, list)
        or path not in paths
        or any(not isinstance(item, str) or not item for item in paths)
    ):
        raise CodexTranscriptIntegrityError(
            f"Robot communication {name.replace('_', ' ')} log path is invalid"
        )
    acknowledgement_values: Dict[str, int] = {}
    for field in ("seq", "written"):
        value = acknowledgement.get(field)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise CodexTranscriptIntegrityError(
                f"Robot communication {name.replace('_', ' ')} acknowledgement is invalid"
            )
        acknowledgement_values[field] = value
    checkpoint = acknowledgement.get("capture_checkpoint")
    if not isinstance(checkpoint, dict):
        raise CodexTranscriptIntegrityError(
            f"Robot communication {name.replace('_', ' ')} checkpoint is invalid"
        )
    normalized: Dict[str, int] = {}
    for field in _LOSS_COUNTERS:
        value = checkpoint.get(field)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
        ):
            raise CodexTranscriptIntegrityError(
                f"Robot communication {name.replace('_', ' ')} checkpoint is invalid"
            )
        normalized[field] = value
    return normalized, acknowledgement_values["seq"]


def _raw_communication_markers(
    path: Path,
    *,
    expected_experiment_id: Optional[str],
    expected_job_id: str,
    expected_attempt: int,
    expected_begin_seq: int,
    expected_end_seq: int,
) -> Tuple[str, str]:
    """Return marker IDs at the exact JSONL boundaries.

    Parsing every row ensures a hash-valid file is still a usable raw JSONL
    transcript.  The per-line bound avoids materializing a pathological row.
    """
    if path.is_symlink() or not path.is_file():
        raise CodexTranscriptIntegrityError(
            "Robot communication transcript is missing or unsafe"
        )
    first: Optional[Dict[str, Any]] = None
    last: Optional[Dict[str, Any]] = None
    max_line_bytes = 4 * 1024 * 1024
    try:
        with path.open("rb") as handle:
            while True:
                line = handle.readline(max_line_bytes + 1)
                if not line:
                    break
                if len(line) > max_line_bytes:
                    raise CodexTranscriptIntegrityError(
                        "Robot communication transcript row exceeds the validation limit"
                    )
                try:
                    record = json.loads(line)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise CodexTranscriptIntegrityError(
                        "Robot communication transcript is not valid JSONL"
                    ) from exc
                if not isinstance(record, dict):
                    raise CodexTranscriptIntegrityError(
                        "Robot communication transcript row is invalid"
                    )
                if first is None:
                    first = record
                last = record
    except OSError as exc:
        raise CodexTranscriptIntegrityError(
            "Robot communication transcript could not be read"
        ) from exc
    expected_data = {
        "experiment_id": expected_experiment_id,
        "job_id": expected_job_id,
        "attempt": expected_attempt,
    }
    expected = (
        (first, "robotlab_run_begin", "first", expected_begin_seq),
        (last, "robotlab_run_end", "last", expected_end_seq),
    )
    markers = []
    for record, label, boundary, sequence in expected:
        if (
            not isinstance(record, dict)
            or record.get("record_type") != "marker"
            or record.get("label") != label
            or not isinstance(record.get("marker_id"), str)
            or not record["marker_id"]
            or not isinstance(record.get("seq"), int)
            or isinstance(record.get("seq"), bool)
            or record.get("seq") != sequence
            or record.get("data") != expected_data
        ):
            raise CodexTranscriptIntegrityError(
                f"Robot communication transcript {boundary} row is not the expected marker"
            )
        markers.append(record["marker_id"])
    return markers[0], markers[1]


def _status_lifecycle(
    status: Dict[str, Any],
) -> Tuple[list[str], Dict[str, Optional[int]]]:
    if status.get("scope") != "host_mcu_serial":
        raise CodexTranscriptIntegrityError(
            "Robot communication capture scope is invalid"
        )
    if (
        not isinstance(status.get("telemetry_url"), str)
        or not status["telemetry_url"]
        or not isinstance(status.get("started_at"), str)
        or not status["started_at"]
        or not isinstance(status.get("finished_at"), str)
        or not status["finished_at"]
    ):
        raise CodexTranscriptIntegrityError(
            "Robot communication capture lifecycle is invalid"
        )
    errors = status.get("errors")
    if (
        not isinstance(errors, list)
        or any(not isinstance(error, str) for error in errors)
    ):
        raise CodexTranscriptIntegrityError(
            "Robot communication capture error receipt is invalid"
        )
    raw_losses = status.get("loss_deltas")
    if not isinstance(raw_losses, dict):
        raise CodexTranscriptIntegrityError(
            "Robot communication capture loss accounting is invalid"
        )
    losses: Dict[str, Optional[int]] = {}
    for field in _LOSS_COUNTERS:
        value = raw_losses.get(field)
        if value is not None and (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
        ):
            raise CodexTranscriptIntegrityError(
                "Robot communication capture loss accounting is invalid"
            )
        losses[field] = value
    return errors, losses


def _validate_marker_bounded_robot_communication(
    run_dir: Path,
    status: Dict[str, Any],
) -> Tuple[str, str, list[str], Dict[str, int]]:
    errors, reported_losses = _status_lifecycle(status)
    begin_marker = _status_marker(status, "begin_marker")
    end_marker = _status_marker(status, "end_marker")
    if begin_marker == end_marker:
        raise CodexTranscriptIntegrityError(
            "Robot communication capture markers are not distinct"
        )
    losses: Dict[str, int] = {}
    for field in _LOSS_COUNTERS:
        value = reported_losses[field]
        if value is None:
            raise CodexTranscriptIntegrityError(
                "Robot communication capture loss accounting is invalid"
            )
        losses[field] = value
    before, begin_seq = _status_recorder_checkpoint(
        status, name="begin_recorder", marker=begin_marker
    )
    after, end_seq = _status_recorder_checkpoint(
        status, name="end_recorder", marker=end_marker
    )
    if end_seq <= begin_seq:
        raise CodexTranscriptIntegrityError(
            "Robot communication marker sequence is invalid"
        )
    for field in _LOSS_COUNTERS:
        if after[field] - before[field] != losses[field]:
            raise CodexTranscriptIntegrityError(
                "Robot communication capture loss accounting mismatch"
            )

    transcript_path = run_dir / TRANSCRIPT_NAME
    transcript = status.get("transcript")
    if not isinstance(transcript, dict) or transcript.get("name") != TRANSCRIPT_NAME:
        raise CodexTranscriptIntegrityError(
            "Robot communication status transcript name is invalid"
        )
    size = transcript.get("bytes")
    digest = transcript.get("sha256")
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or size < 0
        or not isinstance(digest, str)
        or _SHA256.fullmatch(digest) is None
    ):
        raise CodexTranscriptIntegrityError(
            "Robot communication status transcript receipt is invalid"
        )
    if transcript_path.is_symlink() or not transcript_path.is_file():
        raise CodexTranscriptIntegrityError(
            "Robot communication transcript is missing or unsafe"
        )
    if transcript_path.stat().st_size != size or _sha256(transcript_path) != digest:
        raise CodexTranscriptIntegrityError(
            "Robot communication transcript differs from its status receipt"
        )
    first_marker, last_marker = _raw_communication_markers(
        transcript_path,
        expected_experiment_id=status["experiment_id"],
        expected_job_id=status["job_id"],
        expected_attempt=status["attempt"],
        expected_begin_seq=begin_seq,
        expected_end_seq=end_seq,
    )
    if first_marker != begin_marker or last_marker != end_marker:
        raise CodexTranscriptIntegrityError(
            "Robot communication transcript marker boundary mismatch"
        )
    return begin_marker, end_marker, errors, losses


def _validate_terminal_robot_communication(
    run_dir: Path,
    status: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str], bool]:
    """Validate a terminal complete capture or terminal diagnostic receipt."""
    capture_state = status.get("capture_state")
    if capture_state not in {"terminal_complete", "terminal_incomplete"}:
        raise CodexTranscriptIntegrityError(
            "Robot communication capture is not terminal"
        )
    errors, losses = _status_lifecycle(status)
    transcript = status.get("transcript")
    raw_path = run_dir / TRANSCRIPT_NAME

    if capture_state == "terminal_complete":
        if status.get("complete") is not True:
            raise CodexTranscriptIntegrityError(
                "Robot communication capture completeness contradicts its lifecycle"
            )
        begin, end, bounded_errors, bounded_losses = (
            _validate_marker_bounded_robot_communication(run_dir, status)
        )
        if bounded_errors:
            raise CodexTranscriptIntegrityError(
                "Robot communication capture reports errors"
            )
        if any(value != 0 for value in bounded_losses.values()):
            raise CodexTranscriptIntegrityError(
                "Robot communication capture is incomplete due to loss"
            )
        return begin, end, True

    if status.get("complete") is not False:
        raise CodexTranscriptIntegrityError(
            "Robot communication capture completeness contradicts its lifecycle"
        )
    if transcript is None:
        if raw_path.exists() or raw_path.is_symlink():
            raise CodexTranscriptIntegrityError(
                "Robot communication status omits an existing transcript"
            )
        if not errors and all(value == 0 for value in losses.values()):
            raise CodexTranscriptIntegrityError(
                "Robot communication diagnostic has no incomplete reason"
            )
        begin = status.get("begin_marker")
        end = status.get("end_marker")
        return (
            begin if isinstance(begin, str) and begin else None,
            end if isinstance(end, str) and end else None,
            False,
        )
    if not isinstance(transcript, dict):
        raise CodexTranscriptIntegrityError(
            "Robot communication status transcript receipt is invalid"
        )
    begin, end, bounded_errors, bounded_losses = (
        _validate_marker_bounded_robot_communication(run_dir, status)
    )
    # With a healthy exact range, no errors, and zero loss, the producer's own
    # complete predicate must be true. Reject a contradictory diagnostic seal.
    if not bounded_errors and all(
        value == 0 for value in bounded_losses.values()
    ):
        raise CodexTranscriptIntegrityError(
            "Robot communication capture completeness contradicts its evidence"
        )
    return begin, end, True


def finalize_robot_communication_manifest(
    run_dir: Path,
    *,
    expected_job_id: str,
    expected_experiment_id: Optional[str],
    expected_kind: str,
    expected_attempt: int,
) -> Optional[Dict[str, Any]]:
    """Seal a complete marker-bounded capture independently of the legacy seal.

    An absent, recording, or retryable status remains writable so recovery may
    finish the capture. Terminal incomplete status is still sealed as an
    authenticated diagnostic, with the raw range only when it validates.
    """
    if (
        not expected_job_id
        or Path(expected_job_id).name != expected_job_id
        or not isinstance(expected_attempt, int)
        or isinstance(expected_attempt, bool)
        or expected_attempt < 1
    ):
        raise CodexTranscriptIntegrityError(
            "Unsafe robot communication identity"
        )
    manifest_path = run_dir / ROBOT_COMMUNICATION_MANIFEST
    if manifest_path.exists() or manifest_path.is_symlink():
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise CodexTranscriptIntegrityError(
                "Robot communication manifest is unsafe"
            )
        return verify_robot_communication_manifest(
            run_dir,
            expected_job_id=expected_job_id,
            expected_experiment_id=expected_experiment_id,
            expected_kind=expected_kind,
            expected_attempt=expected_attempt,
        )
    status_path = run_dir / STATUS_NAME
    if status_path.is_symlink():
        raise CodexTranscriptIntegrityError(
            "Robot communication status is missing or unsafe"
        )
    if not status_path.exists():
        return None
    status = _load_robot_communication_status(
        run_dir,
        expected_job_id=expected_job_id,
        expected_experiment_id=expected_experiment_id,
        expected_attempt=expected_attempt,
    )
    if status.get("capture_state") not in {
        "terminal_complete", "terminal_incomplete",
    }:
        return None
    begin_marker, end_marker, has_transcript = _validate_terminal_robot_communication(
        run_dir, status
    )
    entries = []
    archived_names = [STATUS_NAME]
    if has_transcript:
        archived_names.append(TRANSCRIPT_NAME)
    for name in archived_names:
        path = run_dir / name
        if path.is_symlink() or not path.is_file():
            raise CodexTranscriptIntegrityError(
                f"Robot communication artifact is missing or unsafe: {name}"
            )
        entries.append({
            "name": name,
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    manifest = {
        "schema_version": 1,
        "job_id": expected_job_id,
        "experiment_id": expected_experiment_id,
        "kind": expected_kind,
        "attempt": expected_attempt,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "capture_state": status["capture_state"],
        "communication_complete": status["complete"],
        "integrity": {
            "status": "verified",
            "transcript": "verified_marker_bounded" if has_transcript else "absent",
        },
        "begin_marker": begin_marker,
        "end_marker": end_marker,
        "files": entries,
    }
    for name in archived_names:
        (run_dir / name).chmod(0o400)
    _atomic_write(
        manifest_path,
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    manifest_path.chmod(0o400)
    return verify_robot_communication_manifest(
        run_dir,
        expected_job_id=expected_job_id,
        expected_experiment_id=expected_experiment_id,
        expected_kind=expected_kind,
        expected_attempt=expected_attempt,
    )


def _redact_jsonl(
    source: Path,
    destination: Path,
    redact: Callable[[Any], Any],
    *,
    max_bytes: int,
    max_lines: int,
) -> None:
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    bytes_seen = 0
    lines_seen = 0
    truncated_reason = ""
    source_reached_kernel_limit = source.stat().st_size >= max_bytes
    output_bytes = 0
    output_budget = max(0, max_bytes - 512)
    # One pathological JSON event must not defeat the aggregate memory bound.
    max_line_bytes = max(4096, min(4 * 1024 * 1024, max_bytes // 4))
    try:
        with source.open("rb") as input_handle:
            with temporary.open("xb") as output_handle:
                while True:
                    line = input_handle.readline(max_line_bytes + 1)
                    if not line:
                        break
                    if len(line) > max_line_bytes:
                        truncated_reason = "event_line_byte_limit"
                        break
                    if lines_seen >= max_lines:
                        truncated_reason = "event_line_count_limit"
                        break
                    if bytes_seen + len(line) > max_bytes:
                        truncated_reason = "event_stream_byte_limit"
                        break
                    raw = line.rstrip(b"\r\n").decode("utf-8", errors="replace")
                    try:
                        event = redact(json.loads(raw))
                        rendered = json.dumps(
                            event,
                            ensure_ascii=False,
                            separators=(",", ":"),
                            sort_keys=True,
                        )
                    except json.JSONDecodeError:
                        # Retain malformed CLI output as a machine-readable
                        # event instead of silently dropping part of a run.
                        rendered = json.dumps(
                            {"type": "unparsed_output", "text": redact(raw)},
                            ensure_ascii=False,
                            separators=(",", ":"),
                            sort_keys=True,
                        )
                    rendered_bytes = (rendered + "\n").encode("utf-8")
                    if output_bytes + len(rendered_bytes) > output_budget:
                        truncated_reason = "redacted_event_stream_byte_limit"
                        break
                    output_handle.write(rendered_bytes)
                    output_bytes += len(rendered_bytes)
                    bytes_seen += len(line)
                    lines_seen += 1
                if not truncated_reason and source_reached_kernel_limit:
                    truncated_reason = "kernel_file_size_limit"
                if truncated_reason:
                    marker = {
                        "type": "capture.truncated",
                        "reason": truncated_reason,
                        "source_bytes_retained": bytes_seen,
                        "source_lines_retained": lines_seen,
                    }
                    output_handle.write(
                        (json.dumps(marker, sort_keys=True) + "\n").encode("utf-8")
                    )
                output_handle.flush()
                os.fsync(output_handle.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _redact_text_file(
    source: Path,
    destination: Path,
    redact_text: Callable[[str], str],
    *,
    max_bytes: int,
) -> None:
    with source.open("rb") as handle:
        payload = handle.read(max_bytes + 1)
    truncated = len(payload) >= max_bytes
    text = payload[:max_bytes].decode("utf-8", errors="replace")
    if truncated:
        text += (
            "\n[TRANSCRIPT CAPTURE TRUNCATED: source exceeded the configured "
            "byte limit]\n"
        )
    _atomic_write(destination, redact_text(text).encode("utf-8"))


def _event_text(event: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Extract the user-visible portions emitted by ``codex exec --json``."""
    event_type = str(event.get("type") or "event")
    item = event.get("item")
    if isinstance(item, dict):
        item_type = str(item.get("type") or "")
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            labels = {
                "agent_message": "Assistant",
                "reasoning": "Assistant reasoning summary",
                "error": "Error",
            }
            return labels.get(item_type, item_type.replace("_", " ").title()), text
    error = event.get("error")
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return "Error", error["message"]
    if event_type in {"error", "turn.failed"}:
        message = event.get("message")
        if isinstance(message, str) and message.strip():
            return "Error", message
    return None


def _render_transcript(
    run_dir: Path,
    events_path: Path,
    *,
    job_id: str,
    experiment_id: Optional[str],
    kind: str,
    attempt: int,
    max_bytes: int,
) -> str:
    engineering = kind == "engineering"
    chunks = ["\n".join([
        "# Codex run transcript",
        "",
        f"- Job: `{job_id}`",
        f"- Experiment: `{experiment_id or 'none'}`",
        f"- Role: `{kind}`",
        f"- Attempt: `{attempt}`",
        "",
        (
            "This viewer-safe engineering transcript contains the model's "
            "user-visible messages. Input context, reasoning, and tool events "
            "remain in the operator-only redacted JSONL record."
            if engineering
            else "This transcript is generated from the redacted Codex JSON "
            "event stream. The JSONL file is the complete machine-readable record."
        ),
        "",
    ])]
    used = len(chunks[0].encode("utf-8"))

    def append_block(label: str, text: str, *, allowance: Optional[int] = None) -> bool:
        nonlocal used
        prefix = f"## {label}\n\n" if label.startswith("Input") else f"### {label}\n\n"
        suffix = "\n\n"
        room = max(0, max_bytes - used - len((prefix + suffix).encode("utf-8")))
        if allowance is not None:
            room = min(room, max(0, allowance))
        encoded = text.rstrip().encode("utf-8")
        complete = len(encoded) <= room
        if not complete:
            marker = b"\n\n[Transcript view truncated; use the operator JSON event stream.]"
            content_room = max(0, room - len(marker))
            encoded = encoded[:content_room] + marker
        block = prefix + encoded.decode("utf-8", errors="replace") + suffix
        chunks.append(block)
        used += len(block.encode("utf-8"))
        return complete

    prompt_path = run_dir / "prompt.md"
    if prompt_path.is_file() and not engineering:
        with prompt_path.open("rb") as handle:
            prompt = handle.read(max(1, max_bytes // 2) + 1)
        append_block(
            "Input prompt",
            prompt[: max(1, max_bytes // 2)].decode("utf-8", errors="replace"),
            allowance=max(1, max_bytes // 2),
        )
    heading = "## Model transcript\n\n"
    if used + len(heading.encode("utf-8")) < max_bytes:
        chunks.append(heading)
        used += len(heading.encode("utf-8"))
    visible = 0
    with events_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            if engineering:
                item = event.get("item")
                if not (
                    isinstance(item, dict)
                    and item.get("type") == "agent_message"
                ):
                    continue
            extracted = _event_text(event)
            if extracted is None:
                continue
            label, text = extracted
            complete = append_block(label, text)
            visible += 1
            if not complete:
                break
    if visible == 0:
        notice = (
            "No user-visible model message was emitted during this attempt. "
            "See `events.jsonl` for lifecycle and error events.\n"
        )
        room = max(0, max_bytes - used)
        encoded = notice.encode("utf-8")[:room]
        chunks.append(encoded.decode("utf-8", errors="replace"))
    rendered = "".join(chunks).rstrip() + "\n"
    encoded = rendered.encode("utf-8")
    if len(encoded) > max_bytes:
        rendered = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return rendered


def finalize_codex_transcript(
    run_dir: Path,
    *,
    job_id: str,
    experiment_id: Optional[str],
    kind: str,
    attempt: int,
    redact: Callable[[Any], Any],
    redact_text: Callable[[str], str],
    max_capture_bytes: int = 64 * 1024 * 1024,
    max_event_lines: int = 100_000,
    max_human_bytes: int = 2 * 1024 * 1024,
) -> Dict[str, Any]:
    """Sanitize and seal one completed attempt's transcript artifacts.

    New runs stream into hidden ``*.raw`` files.  Legacy runs streamed into the
    public filenames directly; those are atomically rewritten before a
    manifest makes them available through Robot Lab.
    """
    if (
        Path(job_id).name != job_id
        or not job_id
        or not isinstance(attempt, int)
        or isinstance(attempt, bool)
        or attempt < 1
    ):
        raise CodexTranscriptIntegrityError("Unsafe Codex transcript identity")
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / TRANSCRIPT_MANIFEST
    if manifest_path.exists() or manifest_path.is_symlink():
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise CodexTranscriptIntegrityError("Codex transcript manifest is unsafe")
        manifest = verify_codex_transcript_manifest(
            run_dir,
            expected_job_id=job_id,
            expected_experiment_id=experiment_id,
            expected_kind=kind,
            expected_attempt=attempt,
        )
        # The robot capture may finish after this legacy manifest was sealed.
        # Its independent receipt can therefore be attached on any retry.
        try:
            finalize_robot_communication_manifest(
                run_dir,
                expected_job_id=job_id,
                expected_experiment_id=experiment_id,
                expected_kind=kind,
                expected_attempt=attempt,
            )
        except Exception as exc:
            # Optional communication evidence must not make a valid Codex
            # transcript unavailable. Direct callers and archive resolution
            # still receive precise integrity failures from the verifier.
            print(
                "Could not attach robot communication archive: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
        return manifest

    raw_events = run_dir / ".events.raw.jsonl"
    events_path = run_dir / "events.jsonl"
    event_source = raw_events if raw_events.is_file() else events_path
    if not event_source.is_file():
        # A launch failure still has a real attempt and prompt. Preserve an
        # explicit empty stream rather than pretending the attempt never ran.
        _atomic_write(raw_events, b"")
        event_source = raw_events
    max_capture_bytes = max(64 * 1024, int(max_capture_bytes))
    max_event_lines = max(1, int(max_event_lines))
    max_human_bytes = max(16 * 1024, int(max_human_bytes))
    _redact_jsonl(
        event_source,
        events_path,
        redact,
        max_bytes=max_capture_bytes,
        max_lines=max_event_lines,
    )

    raw_stderr = run_dir / ".stderr.raw.log"
    stderr_path = run_dir / "stderr.log"
    stderr_source = raw_stderr if raw_stderr.is_file() else stderr_path
    if stderr_source.is_file():
        _redact_text_file(
            stderr_source,
            stderr_path,
            redact_text,
            max_bytes=min(max_capture_bytes, 4 * 1024 * 1024),
        )
    else:
        _atomic_write(stderr_path, b"")

    prompt_path = run_dir / "prompt.md"
    if prompt_path.is_file():
        _redact_text_file(
            prompt_path,
            prompt_path,
            redact_text,
            max_bytes=max_capture_bytes,
        )
    else:
        _atomic_write(prompt_path, b"")

    transcript = _render_transcript(
        run_dir,
        events_path,
        job_id=job_id,
        experiment_id=experiment_id,
        kind=kind,
        attempt=attempt,
        max_bytes=max_human_bytes,
    )
    transcript_path = run_dir / "transcript.md"
    _atomic_write(transcript_path, redact_text(transcript).encode("utf-8"))

    entries = []
    for name in _ARCHIVED_FILES:
        path = run_dir / name
        if not path.is_file() or path.is_symlink():
            raise CodexTranscriptIntegrityError(
                f"Codex transcript artifact is missing or unsafe: {name}"
            )
        entries.append({
            "name": name,
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    manifest = {
        "schema_version": 1,
        "job_id": job_id,
        "experiment_id": experiment_id,
        "kind": kind,
        "attempt": attempt,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": entries,
    }
    _atomic_write(
        manifest_path,
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    for path in [*(run_dir / entry["name"] for entry in entries), manifest_path]:
        path.chmod(0o400)
    raw_events.unlink(missing_ok=True)
    raw_stderr.unlink(missing_ok=True)
    try:
        finalize_robot_communication_manifest(
            run_dir,
            expected_job_id=job_id,
            expected_experiment_id=experiment_id,
            expected_kind=kind,
            expected_attempt=attempt,
        )
    except Exception as exc:
        # See the retry path above: communication capture is independently
        # sealed and must not block publication of the legacy four-file seal.
        print(
            "Could not attach robot communication archive: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
    return manifest


def verify_codex_transcript_manifest(
    run_dir: Path,
    *,
    expected_job_id: str,
    expected_experiment_id: Optional[str],
    expected_kind: str,
    expected_attempt: int,
    expected_manifest_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    manifest_path = run_dir / TRANSCRIPT_MANIFEST
    if manifest_path.is_symlink():
        raise CodexTranscriptIntegrityError("Codex transcript manifest is unsafe")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CodexTranscriptNotFound("Codex transcript is not finalized") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise CodexTranscriptIntegrityError("Codex transcript manifest is invalid") from exc
    if (
        expected_manifest_sha256 is not None
        and _sha256(manifest_path) != expected_manifest_sha256
    ):
        raise CodexTranscriptIntegrityError("Codex transcript manifest changed")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise CodexTranscriptIntegrityError("Codex transcript manifest schema is invalid")
    if (
        manifest.get("job_id") != expected_job_id
        or manifest.get("experiment_id") != expected_experiment_id
        or manifest.get("kind") != expected_kind
        or manifest.get("attempt") != expected_attempt
        or isinstance(manifest.get("attempt"), bool)
    ):
        raise CodexTranscriptIntegrityError("Codex transcript manifest identity mismatch")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise CodexTranscriptIntegrityError("Codex transcript manifest has no file list")
    seen = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise CodexTranscriptIntegrityError("Codex transcript manifest entry is invalid")
        name = entry.get("name")
        expected_size = entry.get("bytes")
        expected_digest = entry.get("sha256")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name not in _ARCHIVED_FILES
            or name in seen
            or not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or expected_size < 0
            or not isinstance(expected_digest, str)
            or _SHA256.fullmatch(expected_digest) is None
        ):
            raise CodexTranscriptIntegrityError("Codex transcript manifest entry is unsafe")
        seen.add(name)
        path = run_dir / name
        if path.is_symlink() or not path.is_file():
            raise CodexTranscriptIntegrityError(f"Codex transcript file is missing: {name}")
        if path.stat().st_size != expected_size or _sha256(path) != expected_digest:
            raise CodexTranscriptIntegrityError(f"Codex transcript file changed: {name}")
    if seen != set(_ARCHIVED_FILES):
        raise CodexTranscriptIntegrityError("Codex transcript manifest is incomplete")
    return manifest


def verify_robot_communication_manifest(
    run_dir: Path,
    *,
    expected_job_id: str,
    expected_experiment_id: Optional[str],
    expected_kind: str,
    expected_attempt: int,
    expected_manifest_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify the independent communication receipt and its semantic claims."""
    manifest_path = run_dir / ROBOT_COMMUNICATION_MANIFEST
    if manifest_path.is_symlink():
        raise CodexTranscriptIntegrityError(
            "Robot communication manifest is unsafe"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CodexTranscriptNotFound(
            "Robot communication archive is not finalized"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise CodexTranscriptIntegrityError(
            "Robot communication manifest is invalid"
        ) from exc
    if (
        expected_manifest_sha256 is not None
        and _sha256(manifest_path) != expected_manifest_sha256
    ):
        raise CodexTranscriptIntegrityError(
            "Robot communication manifest changed"
        )
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise CodexTranscriptIntegrityError(
            "Robot communication manifest schema is invalid"
        )
    if (
        manifest.get("job_id") != expected_job_id
        or manifest.get("experiment_id") != expected_experiment_id
        or manifest.get("kind") != expected_kind
        or manifest.get("attempt") != expected_attempt
        or isinstance(manifest.get("attempt"), bool)
    ):
        raise CodexTranscriptIntegrityError(
            "Robot communication manifest identity mismatch"
        )
    files = manifest.get("files")
    if not isinstance(files, list):
        raise CodexTranscriptIntegrityError(
            "Robot communication manifest has no file list"
        )
    seen = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise CodexTranscriptIntegrityError(
                "Robot communication manifest entry is invalid"
            )
        name = entry.get("name")
        expected_size = entry.get("bytes")
        expected_digest = entry.get("sha256")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name not in _ROBOT_COMMUNICATION_FILES
            or name in seen
            or not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or expected_size < 0
            or not isinstance(expected_digest, str)
            or _SHA256.fullmatch(expected_digest) is None
        ):
            raise CodexTranscriptIntegrityError(
                "Robot communication manifest entry is unsafe"
            )
        seen.add(name)
        path = run_dir / name
        if path.is_symlink() or not path.is_file():
            raise CodexTranscriptIntegrityError(
                f"Robot communication file is missing: {name}"
            )
        if path.stat().st_size != expected_size or _sha256(path) != expected_digest:
            raise CodexTranscriptIntegrityError(
                f"Robot communication file changed: {name}"
            )
    if STATUS_NAME not in seen:
        raise CodexTranscriptIntegrityError(
            "Robot communication manifest is incomplete"
        )
    status = _load_robot_communication_status(
        run_dir,
        expected_job_id=expected_job_id,
        expected_experiment_id=expected_experiment_id,
        expected_attempt=expected_attempt,
    )
    begin_marker, end_marker, has_transcript = _validate_terminal_robot_communication(
        run_dir, status
    )
    expected_files = {STATUS_NAME}
    if has_transcript:
        expected_files.add(TRANSCRIPT_NAME)
    if seen != expected_files:
        raise CodexTranscriptIntegrityError(
            "Robot communication manifest file set contradicts its status"
        )
    expected_integrity = {
        "status": "verified",
        "transcript": "verified_marker_bounded" if has_transcript else "absent",
    }
    if (
        manifest.get("capture_state") != status["capture_state"]
        or manifest.get("communication_complete") is not status["complete"]
        or manifest.get("integrity") != expected_integrity
        or manifest.get("begin_marker") != begin_marker
        or manifest.get("end_marker") != end_marker
    ):
        raise CodexTranscriptIntegrityError(
            "Robot communication manifest marker mismatch"
        )
    return manifest


class CodexTranscriptArchive:
    """Resolve authenticated transcript links without trusting URL path parts."""

    def __init__(self, data_dir: Path, store: Any):
        self.root = data_dir / "codex-runs"
        self.store = store

    def attempts_for_job(
        self, experiment_id: str, job: Dict[str, Any]
    ) -> list[Dict[str, Any]]:
        if job.get("experiment_id") != experiment_id:
            return []
        job_id = str(job.get("id") or "")
        if not job_id or Path(job_id).name != job_id:
            return []
        job_dir = self.root / job_id
        if not job_dir.is_dir() or job_dir.is_symlink():
            return []
        attempts = []
        for attempt_dir in sorted(job_dir.iterdir(), key=lambda path: path.name):
            match = _ATTEMPT_NAME.fullmatch(attempt_dir.name)
            if not match or not attempt_dir.is_dir() or attempt_dir.is_symlink():
                continue
            attempt = int(match.group(1))
            descriptor: Dict[str, Any] = {"attempt": attempt, "available": False}
            receipt = self.store.codex_transcript_attempt(job_id, attempt)
            if receipt is None:
                descriptor["state"] = (
                    "finalizing"
                    if (attempt_dir / TRANSCRIPT_MANIFEST).is_file()
                    else "recording"
                )
                attempts.append(descriptor)
                continue
            try:
                manifest = verify_codex_transcript_manifest(
                    attempt_dir,
                    expected_job_id=job_id,
                    expected_experiment_id=experiment_id,
                    expected_kind=str(job.get("kind") or ""),
                    expected_attempt=attempt,
                    expected_manifest_sha256=receipt["manifest_sha256"],
                )
            except CodexTranscriptNotFound:
                descriptor["state"] = "recording"
            except CodexTranscriptIntegrityError:
                descriptor["state"] = "integrity_error"
            else:
                base = (
                    f"/api/experiments/{experiment_id}/codex-runs/{job_id}/"
                    f"attempts/{attempt}"
                )
                descriptor.update({
                    "available": True,
                    "state": "finalized",
                    "generated_at": manifest.get("generated_at"),
                    "manifest_sha256": receipt["manifest_sha256"],
                    "files": list(manifest["files"]),
                    "transcript_url": f"{base}/transcript.md",
                    "transcript_access": "viewer",
                    "events_url": f"{base}/events.jsonl",
                    "events_access": "operator_or_automation",
                })
                communication_path = attempt_dir / ROBOT_COMMUNICATION_MANIFEST
                communication_receipt = self.store.codex_communication_attempt(
                    job_id, attempt
                )
                if communication_receipt is not None:
                    try:
                        communication = verify_robot_communication_manifest(
                            attempt_dir,
                            expected_job_id=job_id,
                            expected_experiment_id=experiment_id,
                            expected_kind=str(job.get("kind") or ""),
                            expected_attempt=attempt,
                            expected_manifest_sha256=communication_receipt[
                                "manifest_sha256"
                            ],
                        )
                    except (CodexTranscriptNotFound, CodexTranscriptIntegrityError):
                        descriptor.update({
                            "communication_available": False,
                            "communication_state": "integrity_error",
                        })
                    else:
                        descriptor.update({
                            "communication_available": True,
                            "communication_state": "finalized",
                            "communication_generated_at": communication.get(
                                "generated_at"
                            ),
                            "communication_manifest_sha256": (
                                communication_receipt["manifest_sha256"]
                            ),
                            "communication_files": list(communication["files"]),
                            "communication_complete": communication[
                                "communication_complete"
                            ],
                            "communication_capture_state": communication[
                                "capture_state"
                            ],
                            "communication_integrity": dict(
                                communication["integrity"]
                            ),
                        })
                elif communication_path.is_file() or communication_path.is_symlink():
                    try:
                        verify_robot_communication_manifest(
                            attempt_dir,
                            expected_job_id=job_id,
                            expected_experiment_id=experiment_id,
                            expected_kind=str(job.get("kind") or ""),
                            expected_attempt=attempt,
                        )
                    except (CodexTranscriptNotFound, CodexTranscriptIntegrityError):
                        communication_state = "integrity_error"
                    else:
                        communication_state = "finalizing"
                    descriptor.update({
                        "communication_available": False,
                        "communication_state": communication_state,
                    })
                else:
                    status_path = attempt_dir / STATUS_NAME
                    raw_path = attempt_dir / TRANSCRIPT_NAME
                    if status_path.exists() or status_path.is_symlink():
                        try:
                            status = _load_robot_communication_status(
                                attempt_dir,
                                expected_job_id=job_id,
                                expected_experiment_id=experiment_id,
                                expected_attempt=attempt,
                            )
                            communication_state = str(
                                status.get("capture_state") or "recording"
                            )
                            if communication_state.startswith("terminal_"):
                                _validate_terminal_robot_communication(
                                    attempt_dir, status
                                )
                                communication_state = "finalizing"
                        except CodexTranscriptIntegrityError:
                            communication_state = "integrity_error"
                        descriptor.update({
                            "communication_available": False,
                            "communication_state": communication_state,
                        })
                    elif raw_path.exists() or raw_path.is_symlink():
                        descriptor.update({
                            "communication_available": False,
                            "communication_state": "recording",
                        })
                if descriptor.get("communication_available"):
                    descriptor.update({
                        "communication_status_url": f"{base}/{STATUS_NAME}",
                        "communication_status_access": "operator_or_automation",
                    })
                    communication_names = {
                        entry["name"]
                        for entry in descriptor["communication_files"]
                    }
                    if TRANSCRIPT_NAME in communication_names:
                        descriptor.update({
                            "communication_url": f"{base}/{TRANSCRIPT_NAME}",
                            "communication_access": "operator_or_automation",
                        })
            attempts.append(descriptor)
        attempts.sort(key=lambda item: item["attempt"])
        return attempts

    def resolve(
        self,
        experiment_id: str,
        job_id: str,
        attempt: int,
        filename: str,
    ) -> Path:
        if filename not in TRANSCRIPT_FILES or Path(filename).name != filename:
            raise CodexTranscriptNotFound("Codex transcript file not found")
        job = self.store.get_codex_transcript_source_job(job_id)
        if not job or job.get("experiment_id") != experiment_id:
            raise CodexTranscriptNotFound("Codex transcript run not found")
        if Path(job_id).name != job_id or attempt < 1:
            raise CodexTranscriptNotFound("Codex transcript run not found")
        run_dir = self.root / job_id / f"attempt-{attempt}"
        if run_dir.is_symlink() or not run_dir.is_dir():
            raise CodexTranscriptNotFound("Codex transcript attempt not found")
        receipt = self.store.codex_transcript_attempt(job_id, attempt)
        if receipt is None:
            raise CodexTranscriptNotFound("Codex transcript is not finalized")
        manifest = verify_codex_transcript_manifest(
            run_dir,
            expected_job_id=job_id,
            expected_experiment_id=experiment_id,
            expected_kind=str(job.get("kind") or ""),
            expected_attempt=attempt,
            expected_manifest_sha256=receipt["manifest_sha256"],
        )
        if filename in _ROBOT_COMMUNICATION_FILES:
            communication_receipt = self.store.codex_communication_attempt(
                job_id, attempt
            )
            if communication_receipt is None:
                raise CodexTranscriptNotFound(
                    "Robot communication archive is not finalized"
                )
            communication = verify_robot_communication_manifest(
                run_dir,
                expected_job_id=job_id,
                expected_experiment_id=experiment_id,
                expected_kind=str(job.get("kind") or ""),
                expected_attempt=attempt,
                expected_manifest_sha256=communication_receipt["manifest_sha256"],
            )
            names = {entry["name"] for entry in communication["files"]}
        else:
            names = {entry["name"] for entry in manifest["files"]}
        if filename not in names:
            raise CodexTranscriptNotFound("Codex transcript file not found")
        path = run_dir / filename
        if path.is_symlink() or not path.is_file():
            raise CodexTranscriptIntegrityError("Codex transcript file is unsafe")
        return path
