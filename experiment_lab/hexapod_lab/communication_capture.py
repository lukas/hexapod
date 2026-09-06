"""Attach the robot's passive host/MCU transcript to hardware Codex runs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Dict, Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import uuid


STATUS_NAME = "robot-communication.json"
TRANSCRIPT_NAME = "robot-communication.jsonl"
_BEGIN_RETRY_DELAYS_SECONDS = (0.05, 0.1)
_LOG_DOWNLOAD_TIMEOUT_SECONDS = 120.0


class CommunicationCaptureError(RuntimeError):
    pass


class _TerminalRangeError(CommunicationCaptureError):
    """A saved marker range cannot become retrievable on a later retry."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, payload: Dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RobotCommunicationCapture:
    """Bracket one hardware engineering attempt with flushed robot markers.

    The robot service owns the continuous recorder.  This class only adds two
    markers and copies the marker-bounded rows into the Codex attempt archive;
    it never polls the servo bus or changes robot state.
    """

    def __init__(
        self,
        telemetry_url: str,
        run_dir: Path,
        *,
        experiment_id: Optional[str],
        job_id: str,
        attempt: int,
        timeout_seconds: float = 10.0,
        download_timeout_seconds: float = _LOG_DOWNLOAD_TIMEOUT_SECONDS,
        max_bytes: int = 512 * 1024 * 1024,
        opener: Callable[..., Any] = urlopen,
    ):
        self.telemetry_url = telemetry_url
        self.run_dir = run_dir
        self.experiment_id = experiment_id
        self.job_id = job_id
        self.attempt = int(attempt)
        self.timeout_seconds = max(0.1, float(timeout_seconds))
        self.download_timeout_seconds = max(
            self.timeout_seconds,
            float(download_timeout_seconds),
        )
        self.max_bytes = max(1024, int(max_bytes))
        self.opener = opener
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.begin_status: Optional[Dict[str, Any]] = None
        self.end_status: Optional[Dict[str, Any]] = None
        self.begin_marker: Optional[str] = None
        self.end_marker: Optional[str] = None
        self.errors: list[str] = []
        self._finished = False

    @classmethod
    def resume(
        cls,
        run_dir: Path,
        *,
        opener: Callable[..., Any] = urlopen,
        expected_experiment_id: Optional[str] = None,
        expected_job_id: Optional[str] = None,
        expected_attempt: Optional[int] = None,
    ) -> "RobotCommunicationCapture":
        status_path = run_dir / STATUS_NAME
        try:
            saved = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommunicationCaptureError(
                "saved communication capture status is invalid"
            ) from exc
        if not isinstance(saved, dict) or saved.get("schema_version") != 1:
            raise CommunicationCaptureError(
                "saved communication capture schema is invalid"
            )
        capture = cls(
            str(saved.get("telemetry_url") or ""),
            run_dir,
            experiment_id=saved.get("experiment_id"),
            job_id=str(saved.get("job_id") or ""),
            attempt=int(saved.get("attempt") or 0),
            opener=opener,
        )
        if not capture.telemetry_url or not capture.job_id or capture.attempt < 1:
            raise CommunicationCaptureError(
                "saved communication capture identity is invalid"
            )
        expected = {
            "experiment_id": expected_experiment_id,
            "job_id": expected_job_id,
            "attempt": expected_attempt,
        }
        actual = {
            "experiment_id": capture.experiment_id,
            "job_id": capture.job_id,
            "attempt": capture.attempt,
        }
        for name, value in expected.items():
            if value is not None and actual[name] != value:
                raise CommunicationCaptureError(
                    f"saved communication capture {name} mismatched recovery state"
                )
        capture.started_at = saved.get("started_at")
        capture.finished_at = saved.get("finished_at")
        capture.begin_marker = saved.get("begin_marker")
        capture.end_marker = saved.get("end_marker")
        capture.begin_status = saved.get("begin_recorder")
        capture.end_status = saved.get("end_recorder")
        capture.errors = [
            str(error) for error in saved.get("errors", [])
            if isinstance(error, str)
        ]
        capture_state = saved.get("capture_state")
        if capture_state is not None and capture_state not in {
            "recording", "retryable", "terminal_complete",
            "terminal_incomplete",
        }:
            raise CommunicationCaptureError(
                "saved communication capture lifecycle is invalid"
            )
        if capture_state is not None:
            capture._finished = capture_state.startswith("terminal_")
        else:
            # Backward compatibility for status files written before the
            # explicit lifecycle field existed.  A successfully copied range
            # is terminal even when declared loss makes it incomplete.
            capture._finished = capture._saved_range_is_terminal() or bool(
                capture.finished_at and capture.begin_marker is None
            )
        return capture

    def begin(self) -> Dict[str, Any]:
        self.started_at = _utc_now()
        attempt = 0
        while True:
            attempt += 1
            try:
                self.begin_status = self._post_marker("robotlab_run_begin")
                self.begin_marker = self._marker_id(self.begin_status, "begin")
                break
            except HTTPError as exc:
                # HTTPError is a URLError subclass, but an HTTP response is
                # not the transient routing failure this retry is for.
                self.errors.append(f"begin: {type(exc).__name__}: {exc}")
                break
            except URLError as exc:
                if attempt > len(_BEGIN_RETRY_DELAYS_SECONDS):
                    self.errors.append(
                        f"begin: {type(exc).__name__}: {exc} "
                        f"(after {attempt} attempts)"
                    )
                    break
                # A transport failure can leave the preceding POST's fate
                # unknown.  The hardware attempt does not start until begin()
                # returns, markers are append-only, and only the retry whose
                # exact flushed acknowledgement is returned becomes the
                # transcript boundary.
                time.sleep(_BEGIN_RETRY_DELAYS_SECONDS[attempt - 1])
            except Exception as exc:
                self.errors.append(f"begin: {type(exc).__name__}: {exc}")
                break
        self._write_status()
        return self.status()

    def finish(self) -> Dict[str, Any]:
        if self._finished:
            # A prior caller may have completed the range copy but failed to
            # persist its final receipt. Retrying finish repairs that durable
            # status without emitting another end marker.
            self._write_status()
            return self.status()
        if self.finished_at is None:
            self.finished_at = _utc_now()
        self.errors = [
            error for error in self.errors if not error.startswith("finish:")
        ]
        if self.begin_marker is not None:
            try:
                # Once an end marker has been durably acknowledged, retries
                # must keep that exact boundary.  Re-emitting an end marker
                # widens the range and cannot repair already-declared loss.
                if self.end_marker is None or self.end_status is None:
                    self.end_status = self._post_marker("robotlab_run_end")
                    self.end_marker = self._marker_id(self.end_status, "end")
                self._copy_marker_range()
            except _TerminalRangeError as exc:
                self.errors.append(f"finish: {type(exc).__name__}: {exc}")
                self._finished = True
            except Exception as exc:
                self.errors.append(f"finish: {type(exc).__name__}: {exc}")
            else:
                self._finished = True
        elif not self.errors:
            self.errors.append("finish: begin marker was not recorded")
        if self.begin_marker is None:
            self._finished = True
        self._write_status()
        return self.status()

    def status(self) -> Dict[str, Any]:
        transcript = self.run_dir / TRANSCRIPT_NAME
        losses = self._loss_deltas()
        complete = bool(
            self.begin_marker
            and self.end_marker
            and transcript.is_file()
            and not self.errors
            and all(value == 0 for value in losses.values())
            and self.end_status
            and self.end_status.get("active") is True
            and self.end_status.get("communication_capture") is True
            and self.end_status.get("communication_scope") == "host_mcu_serial"
            and self.end_status.get("communication_rate_limited") is False
            and self.end_status.get("piggyback_snapshots") is False
            and self.end_status.get("writer_alive") is True
            and self.end_status.get("write_error") is None
        )
        capture_state = (
            "terminal_complete"
            if self._finished and complete
            else "terminal_incomplete"
            if self._finished
            else "retryable"
            if self.finished_at is not None
            else "recording"
        )
        return {
            "schema_version": 1,
            "complete": complete,
            "capture_state": capture_state,
            "scope": "host_mcu_serial",
            "experiment_id": self.experiment_id,
            "job_id": self.job_id,
            "attempt": self.attempt,
            "telemetry_url": self.telemetry_url,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "begin_marker": self.begin_marker,
            "end_marker": self.end_marker,
            "loss_deltas": losses,
            "errors": list(self.errors),
            "transcript": (
                {
                    "name": TRANSCRIPT_NAME,
                    "bytes": transcript.stat().st_size,
                    "sha256": _sha256(transcript),
                }
                if transcript.is_file() else None
            ),
            "begin_recorder": self._recorder_summary(self.begin_status),
            "end_recorder": self._recorder_summary(self.end_status),
        }

    def _post_marker(self, label: str) -> Dict[str, Any]:
        payload = json.dumps({
            "action": "mark",
            "label": label,
            "data": {
                "experiment_id": self.experiment_id,
                "job_id": self.job_id,
                "attempt": self.attempt,
            },
        }).encode("utf-8")
        request = Request(
            self.telemetry_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.opener(request, timeout=self.timeout_seconds) as response:
            posted = json.loads(response.read().decode("utf-8"))
        if not isinstance(posted, dict) or posted.get("ok") is not True:
            raise CommunicationCaptureError("robot telemetry marker was rejected")
        marker = posted.get("marker_id")
        if not isinstance(marker, str) or not marker:
            raise CommunicationCaptureError("robot telemetry marker id is missing")
        self._validate_recorder(posted)
        deadline = time.monotonic() + self.timeout_seconds
        acknowledged = posted
        while True:
            marker_ack = acknowledged.get("marker_ack")
            if (
                isinstance(marker_ack, dict)
                and marker_ack.get("marker_id") == marker
            ):
                break
            if time.monotonic() >= deadline:
                raise CommunicationCaptureError("robot telemetry marker was not flushed")
            time.sleep(0.05)
            acknowledged = self._get_status(marker)
        self._validate_recorder(acknowledged)
        self._validate_marker_ack(acknowledged["marker_ack"], marker)
        result = dict(posted)
        result.update({
            "marker_id": marker,
            "flushed_marker": marker,
            "observed_flushed_marker": acknowledged.get("flushed_marker"),
            "marker_post_paths": self._safe_paths(posted.get("paths")),
            "marker_flush_paths": self._safe_paths(acknowledged.get("paths")),
            "flush_ack_written": acknowledged.get("written"),
            "marker_ack": acknowledged["marker_ack"],
        })
        return result

    def _get_status(self, marker_id: Optional[str] = None) -> Dict[str, Any]:
        url = self.telemetry_url
        if marker_id:
            parsed = urlsplit(url)
            query = urlencode({"marker_id": marker_id})
            url = urlunsplit((
                parsed.scheme, parsed.netloc, parsed.path, query, "",
            ))
        request = Request(url, method="GET")
        with self.opener(request, timeout=self.timeout_seconds) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise CommunicationCaptureError("robot telemetry status was rejected")
        return result

    @staticmethod
    def _marker_id(status: Dict[str, Any], phase: str) -> str:
        marker = status.get("marker_id")
        if not isinstance(marker, str) or not marker:
            raise CommunicationCaptureError(f"{phase} marker id is missing")
        marker_ack = status.get("marker_ack")
        if (
            not isinstance(marker_ack, dict)
            or marker_ack.get("marker_id") != marker
        ):
            raise CommunicationCaptureError(f"{phase} marker was not flushed")
        return marker

    @classmethod
    def _validate_marker_ack(cls, ack: Dict[str, Any], marker_id: str) -> None:
        if ack.get("marker_id") != marker_id:
            raise CommunicationCaptureError("robot marker acknowledgement mismatched")
        path = ack.get("path")
        paths = cls._safe_paths(ack.get("paths"))
        if not isinstance(path, str) or not path or path not in paths:
            raise CommunicationCaptureError(
                "robot marker acknowledgement has no exact log part"
            )
        for name in ("seq", "written"):
            value = ack.get(name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 1
            ):
                raise CommunicationCaptureError(
                    f"robot marker acknowledgement has invalid {name}: {value!r}"
                )
        checkpoint = ack.get("capture_checkpoint")
        if not isinstance(checkpoint, dict):
            raise CommunicationCaptureError(
                "robot marker acknowledgement has no capture checkpoint"
            )
        for name in (
            "queue_dropped", "communication_dropped", "uncaptured_bytes",
            "capture_errors",
        ):
            value = checkpoint.get(name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CommunicationCaptureError(
                    f"robot marker checkpoint has invalid {name}: {value!r}"
                )

    @staticmethod
    def _validate_recorder(status: Dict[str, Any]) -> None:
        expected = {
            "active": True,
            "communication_capture": True,
            "communication_scope": "host_mcu_serial",
            "communication_rate_limited": False,
            "piggyback_snapshots": False,
            "writer_alive": True,
            "write_error": None,
        }
        for name, value in expected.items():
            if status.get(name) != value:
                raise CommunicationCaptureError(
                    f"robot recorder has invalid {name}: {status.get(name)!r}"
                )
        for name in (
            "queue_dropped", "communication_dropped", "uncaptured_bytes",
            "capture_errors", "offered", "written",
        ):
            value = status.get(name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CommunicationCaptureError(
                    f"robot recorder has invalid {name}: {value!r}"
                )

    def _copy_marker_range(self) -> None:
        assert self.begin_status is not None
        assert self.end_status is not None
        assert self.begin_marker is not None
        assert self.end_marker is not None
        begin_ack = self.begin_status.get("marker_ack")
        end_ack = self.end_status.get("marker_ack")
        if not isinstance(begin_ack, dict) or not isinstance(end_ack, dict):
            raise CommunicationCaptureError("recorder did not acknowledge markers")
        try:
            self._validate_marker_ack(begin_ack, self.begin_marker)
            self._validate_marker_ack(end_ack, self.end_marker)
        except CommunicationCaptureError as exc:
            raise _TerminalRangeError(str(exc)) from exc
        first = begin_ack["path"]
        last = end_ack["path"]
        end_paths = self._safe_paths(end_ack.get("paths"))
        try:
            first_index = end_paths.index(first)
        except ValueError as exc:
            raise _TerminalRangeError(
                "begin recorder part is absent from end status"
            ) from exc
        try:
            last_index = end_paths.index(last, first_index)
        except ValueError as exc:
            raise _TerminalRangeError(
                "end recorder part is absent from marker acknowledgement"
            ) from exc
        parts = end_paths[first_index:last_index + 1]
        destination = self.run_dir / TRANSCRIPT_NAME
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        started = False
        ended = False
        written = 0
        try:
            with temporary.open("xb") as output:
                for part_index, remote_path in enumerate(parts):
                    for line in self._log_lines(
                        remote_path,
                        from_marker=(
                            self.begin_marker if part_index == 0 else None
                        ),
                        through_marker=(
                            self.end_marker
                            if part_index == len(parts) - 1 else None
                        ),
                    ):
                        if not started:
                            if self._line_marker(line) != self.begin_marker:
                                continue
                            started = True
                        if written + len(line) > self.max_bytes:
                            raise _TerminalRangeError(
                                "marker-bounded communication transcript exceeds limit"
                            )
                        output.write(line)
                        written += len(line)
                        if self._line_marker(line) == self.end_marker:
                            ended = True
                            break
                    if ended:
                        break
                if not started:
                    raise _TerminalRangeError("begin marker not found in robot logs")
                if not ended:
                    raise _TerminalRangeError("end marker not found in robot logs")
                output.flush()
                os.fsync(output.fileno())
            temporary.chmod(0o600)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def _log_lines(
        self,
        remote_path: str,
        *,
        from_marker: Optional[str] = None,
        through_marker: Optional[str] = None,
    ) -> Iterable[bytes]:
        parsed = urlsplit(self.telemetry_url)
        basename = Path(remote_path).name
        if not basename or Path(basename).name != basename:
            raise _TerminalRangeError("unsafe robot log filename")
        query = urlencode({
            name: value
            for name, value in (
                ("from_marker", from_marker),
                ("through_marker", through_marker),
            )
            if value is not None
        })
        url = urlunsplit((
            parsed.scheme,
            parsed.netloc,
            f"/api/logs/{quote(basename, safe='')}",
            query,
            "",
        ))
        request = Request(url, method="GET")
        # Marker and status requests should fail fast, but a recorder part can
        # legitimately be tens or hundreds of megabytes.  Give that transfer
        # its own inactivity timeout so a healthy large capture is not lost
        # merely because the proxy needs more than the marker timeout to begin
        # or continue the response.
        try:
            with self.opener(
                request,
                timeout=self.download_timeout_seconds,
            ) as response:
                for line in response:
                    yield bytes(line)
        except HTTPError as exc:
            if (
                exc.code == 416
                and (from_marker is not None or through_marker is not None)
            ):
                raise _TerminalRangeError(
                    "robot log does not contain the acknowledged marker range"
                ) from exc
            raise

    @staticmethod
    def _line_marker(line: bytes) -> Optional[str]:
        try:
            record = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(record, dict) or record.get("record_type") != "marker":
            return None
        marker = record.get("marker_id")
        return marker if isinstance(marker, str) else None

    @staticmethod
    def _safe_paths(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str) and item]

    def _loss_deltas(self) -> Dict[str, Optional[int]]:
        names = (
            "queue_dropped",
            "communication_dropped",
            "uncaptured_bytes",
            "capture_errors",
        )
        out: Dict[str, Optional[int]] = {}
        for name in names:
            begin_ack = (self.begin_status or {}).get("marker_ack")
            end_ack = (self.end_status or {}).get("marker_ack")
            before_checkpoint = (
                begin_ack.get("capture_checkpoint")
                if isinstance(begin_ack, dict) else None
            )
            after_checkpoint = (
                end_ack.get("capture_checkpoint")
                if isinstance(end_ack, dict) else None
            )
            before = (
                before_checkpoint.get(name)
                if isinstance(before_checkpoint, dict) else None
            )
            after = (
                after_checkpoint.get(name)
                if isinstance(after_checkpoint, dict) else None
            )
            if (
                not isinstance(before, int)
                or isinstance(before, bool)
                or not isinstance(after, int)
                or isinstance(after, bool)
                or before < 0
                or after < before
            ):
                out[name] = None
            else:
                out[name] = after - before
        return out

    def _saved_range_is_terminal(self) -> bool:
        """Recognize a range atomically copied by an older Lab release."""
        if (
            not isinstance(self.begin_marker, str)
            or not self.begin_marker
            or not isinstance(self.end_marker, str)
            or not self.end_marker
            or not isinstance(self.begin_status, dict)
            or not isinstance(self.end_status, dict)
            or not (self.run_dir / TRANSCRIPT_NAME).is_file()
        ):
            return False
        try:
            begin_ack = self.begin_status.get("marker_ack")
            end_ack = self.end_status.get("marker_ack")
            if not isinstance(begin_ack, dict) or not isinstance(end_ack, dict):
                return False
            self._validate_marker_ack(begin_ack, self.begin_marker)
            self._validate_marker_ack(end_ack, self.end_marker)
        except CommunicationCaptureError:
            return False
        return True

    @staticmethod
    def _recorder_summary(status: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not status:
            return None
        keys = (
            "active", "communication_capture", "communication_scope",
            "communication_rate_limited",
            "piggyback_snapshots", "writer_alive", "write_error", "paths",
            "flushed_marker", "offered", "written", "queue_dropped",
            "communication_dropped", "uncaptured_bytes", "capture_errors",
            "marker_post_paths", "marker_flush_paths", "flush_ack_written",
            "marker_ack",
        )
        return {key: status.get(key) for key in keys}

    def _write_status(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        _atomic_json(self.run_dir / STATUS_NAME, self.status())
