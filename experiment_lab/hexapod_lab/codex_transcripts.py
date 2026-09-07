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


TRANSCRIPT_MANIFEST = "transcript.manifest.json"
TRANSCRIPT_FILES = ("transcript.md", "events.jsonl")
_ARCHIVED_FILES = ("prompt.md", "events.jsonl", "transcript.md", "stderr.log")
_ATTEMPT_NAME = re.compile(r"attempt-([1-9][0-9]*)$")
_SHA256 = re.compile(r"[0-9a-f]{64}$")


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
    if Path(job_id).name != job_id or not job_id or attempt < 1:
        raise CodexTranscriptIntegrityError("Unsafe Codex transcript identity")
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / TRANSCRIPT_MANIFEST
    if manifest_path.is_file():
        return verify_codex_transcript_manifest(
            run_dir,
            expected_job_id=job_id,
            expected_experiment_id=experiment_id,
            expected_kind=kind,
            expected_attempt=attempt,
        )

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
                    "transcript_url": f"{base}/transcript.md",
                    "transcript_access": "viewer",
                    "events_url": f"{base}/events.jsonl",
                    "events_access": "operator_or_automation",
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
        names = {entry["name"] for entry in manifest["files"]}
        if filename not in names:
            raise CodexTranscriptNotFound("Codex transcript file not found")
        path = run_dir / filename
        if path.is_symlink() or not path.is_file():
            raise CodexTranscriptIntegrityError("Codex transcript file is unsafe")
        return path
