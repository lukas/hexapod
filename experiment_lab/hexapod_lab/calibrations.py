"""Immutable calibration evidence archive for Robot Lab.

This archive deliberately does not apply a calibration.  It records the exact
canonical report, an optional exact pose-configuration snapshot, and the
immutable tag-layout revision identity effective when the evidence was observed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import sqlite3
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from .db import Store


MAX_CALIBRATION_BYTES = 2 * 1024 * 1024
MAX_SCHEMA_VERSION = 2_147_483_647
MAX_CLOCK_SKEW = timedelta(minutes=5)
_ADVISORY_TRACKER_KIND = "advisory_visual_encoder_calibration"
_REPORT_ALIASES = ("report", "calibration")
_POSE_CONFIG_ALIASES = ("pose_config", "config", "configuration")
_SENSITIVE_METADATA_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "client_secret",
    "cookie",
    "credentials",
    "id_token",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "set_cookie",
    "token",
}
_ENVELOPE_FIELDS = {
    "report",
    "calibration",
    "pose_config",
    "config",
    "configuration",
    "observed_at",
    "recorded_at",
    "robot_id",
}
_LAYOUT_SNAPSHOT_FIELDS = (
    "id",
    "revision_number",
    "robot_id",
    "layout_sha256",
    "pose_config_sha256",
    "floor_map_sha256",
    "part_map_sha256",
    "observed_at",
    "effective_from",
    "effective_to",
    "source_kind",
)

_REPORT_OPENAPI = {
    "type": "object",
    "required": ["kind", "schema_version"],
    "properties": {
        "kind": {"type": "string", "minLength": 1, "maxLength": 160},
        "schema_version": {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_SCHEMA_VERSION,
        },
        "created_unix": {"type": "number", "exclusiveMinimum": 0},
        "observed_at": {"type": "string", "format": "date-time"},
        "recorded_at": {"type": "string", "format": "date-time"},
        "robot_id": {"type": "string", "minLength": 1, "maxLength": 160},
        "advisory_only": {"type": "boolean"},
        "motor_commands_sent": {"type": "boolean"},
        "servo_zeros_changed": {"type": "boolean"},
    },
    "allOf": [
        {
            "if": {
                "anyOf": [
                    {
                        "properties": {
                            "kind": {"const": _ADVISORY_TRACKER_KIND}
                        },
                        "required": ["kind"],
                    },
                    {
                        "properties": {"advisory_only": {"const": True}},
                        "required": ["advisory_only"],
                    },
                ]
            },
            "then": {
                "required": ["motor_commands_sent", "servo_zeros_changed"],
                "properties": {
                    "motor_commands_sent": {"const": False},
                    "servo_zeros_changed": {"const": False},
                },
            },
        }
    ],
    "additionalProperties": True,
}
_REPORT_TIME_OPENAPI = {
    "anyOf": [
        {"required": ["observed_at"]},
        {"required": ["recorded_at"]},
        {"required": ["created_unix"]},
    ]
}
_POSE_CONFIG_OPENAPI = {
    "type": "object",
    "required": ["schema_version"],
    "minProperties": 2,
    "properties": {
        "schema_version": {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_SCHEMA_VERSION,
        }
    },
    "additionalProperties": True,
}


def _envelope_openapi(report_field: str) -> Dict[str, Any]:
    return {
        "required": [report_field],
        "properties": {
            report_field: _REPORT_OPENAPI,
            "pose_config": _POSE_CONFIG_OPENAPI,
            "config": _POSE_CONFIG_OPENAPI,
            "configuration": _POSE_CONFIG_OPENAPI,
        },
        "anyOf": [
            {"required": ["observed_at"]},
            {"required": ["recorded_at"]},
            {
                "required": [report_field],
                "properties": {
                    report_field: {
                        "allOf": [_REPORT_OPENAPI, _REPORT_TIME_OPENAPI]
                    }
                },
            },
        ],
    }


_CALIBRATION_REQUEST_SCHEMA = {
    "type": "object",
    "description": (
        "A raw calibration report (optionally with a top-level pose-config "
        "sidecar), or an envelope containing the report and optional exact pose "
        "configuration. Extra envelope fields are retained as source metadata."
    ),
    "properties": {
        **_REPORT_OPENAPI["properties"],
        "report": {"type": "object"},
        "calibration": {
            "type": "object",
            "description": "Compatibility alias for report.",
        },
        "pose_config": _POSE_CONFIG_OPENAPI,
        "config": {
            "type": "object",
            "description": "Compatibility alias for pose_config.",
        },
        "configuration": {
            "type": "object",
            "description": "Compatibility alias for pose_config.",
        },
    },
    "anyOf": [
        {"allOf": [_REPORT_OPENAPI, _REPORT_TIME_OPENAPI]},
        _envelope_openapi("report"),
        _envelope_openapi("calibration"),
    ],
    "additionalProperties": True,
}
_NULLABLE_STRING_OPENAPI = {"anyOf": [{"type": "string"}, {"type": "null"}]}
_CALIBRATION_SUMMARY_SCHEMA = {
    "type": "object",
    "required": [
        "sequence",
        "id",
        "request_sha256",
        "report_sha256",
        "pose_config_sha256",
        "observed_at",
        "created_at",
        "created_by",
        "robot_id",
        "kind",
        "schema_version",
        "status",
        "current",
        "replay_ready",
        "replay_status",
        "tag_layout_revision",
    ],
    "properties": {
        "sequence": {"type": "integer", "minimum": 1},
        "id": {"type": "string"},
        "request_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "report_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "pose_config_sha256": _NULLABLE_STRING_OPENAPI,
        "observed_at": {"type": "string", "format": "date-time"},
        "created_at": {"type": "string", "format": "date-time"},
        "created_by": {"type": "string"},
        "robot_id": _NULLABLE_STRING_OPENAPI,
        "kind": {"type": "string"},
        "schema_version": {"type": "integer"},
        "status": {"type": "string", "const": "archived"},
        "current": {"type": "boolean", "const": False},
        "replay_ready": {"type": "boolean"},
        "replay_status": {
            "type": "string",
            "enum": [
                "pose_config_missing",
                "tag_layout_unresolved",
                "archived_not_activated",
            ],
        },
        "tag_layout_revision": {
            "anyOf": [{"type": "object"}, {"type": "null"}]
        },
    },
    "additionalProperties": True,
}
_CALIBRATION_DETAIL_SCHEMA = {
    "allOf": [
        _CALIBRATION_SUMMARY_SCHEMA,
        {
            "type": "object",
            "required": ["report", "pose_config", "source_metadata"],
            "properties": {
                "report": {"type": "object"},
                "pose_config": {
                    "anyOf": [{"type": "object"}, {"type": "null"}]
                },
                "source_metadata": {"type": "object"},
            },
        },
    ]
}
_CALIBRATION_SECURITY = [{"BearerAuth": []}, {"BasicAuth": []}]
_ERROR_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["detail"],
    "properties": {
        "detail": {
            "anyOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "object"}},
            ]
        }
    },
}


def _response_openapi(schema: Mapping[str, Any], description: str) -> Dict[str, Any]:
    return {
        "description": description,
        "content": {"application/json": {"schema": schema}},
    }


def _error_response_openapi(description: str) -> Dict[str, Any]:
    return _response_openapi(_ERROR_RESPONSE_SCHEMA, description)


CALIBRATION_LIST_OPENAPI = {
    "security": _CALIBRATION_SECURITY,
    "responses": {
        "200": _response_openapi(
            {"type": "array", "items": _CALIBRATION_SUMMARY_SCHEMA},
            "Immutable calibration records, newest first",
        ),
        "401": _error_response_openapi("Authentication required"),
        "422": _error_response_openapi("Invalid limit"),
        "500": _error_response_openapi("Stored calibration integrity failure"),
    },
}
CALIBRATION_DETAIL_OPENAPI = {
    "security": _CALIBRATION_SECURITY,
    "responses": {
        "200": _response_openapi(
            _CALIBRATION_DETAIL_SCHEMA, "Immutable calibration record"
        ),
        "401": _error_response_openapi("Authentication required"),
        "404": _error_response_openapi("Calibration not found"),
        "500": _error_response_openapi("Stored calibration integrity failure"),
    },
}
CALIBRATION_REQUEST_OPENAPI = {
    "security": _CALIBRATION_SECURITY,
    "parameters": [
        {
            "name": "Idempotency-Key",
            "in": "header",
            "required": False,
            "schema": {"type": "string", "maxLength": 200},
            "description": "Exact retries return the original archived record.",
        }
    ],
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {"schema": _CALIBRATION_REQUEST_SCHEMA}
        },
    },
    "responses": {
        "201": _response_openapi(
            _CALIBRATION_DETAIL_SCHEMA, "Calibration evidence archived"
        ),
        "401": _error_response_openapi("Authentication required"),
        "403": _error_response_openapi("Operator role required"),
        "409": _error_response_openapi("Idempotency or robot identity conflict"),
        "413": _error_response_openapi("Calibration request is too large"),
        "415": _error_response_openapi("Request must use application/json"),
        "422": _error_response_openapi("Invalid calibration request"),
        "500": _error_response_openapi("Stored calibration integrity failure"),
    },
}


class CalibrationError(ValueError):
    """Base class for safe calibration API errors."""


class CalibrationNotFound(CalibrationError):
    pass


class CalibrationConflict(CalibrationError):
    pass


class CalibrationTooLarge(CalibrationError):
    pass


class CalibrationIntegrityError(CalibrationError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_json(value: Any) -> str:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        )
    except (TypeError, ValueError) as exc:
        raise CalibrationError("Calibration data must be valid JSON") from exc


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_json(value: Any, *, label: str, depth: int = 0) -> None:
    if depth > 100:
        raise CalibrationError(f"{label} is nested too deeply")
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise CalibrationError(f"{label} contains an invalid Unicode surrogate")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CalibrationError(f"{label} contains a non-finite number")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json(item, label=label, depth=depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CalibrationError(f"{label} contains a non-string object key")
            _validate_json(key, label=label, depth=depth + 1)
            _validate_json(item, label=label, depth=depth + 1)
        return
    raise CalibrationError(f"{label} contains a value JSON cannot represent")


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> Dict[str, Any]:
    value: Dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CalibrationError(f"Calibration JSON repeats object key {key!r}")
        value[key] = item
    return value


def decode_calibration_json(raw: bytes) -> Dict[str, Any]:
    if not raw:
        raise CalibrationError("Calibration request body must not be empty")
    if len(raw) > MAX_CALIBRATION_BYTES:
        raise CalibrationTooLarge("Calibration request exceeds the 2 MiB limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CalibrationError("Calibration request must be UTF-8 JSON") from exc
    try:
        value = json.loads(text, object_pairs_hook=_unique_object)
    except CalibrationError:
        raise
    except (ValueError, RecursionError) as exc:
        raise CalibrationError("Calibration request is not valid JSON") from exc
    if not isinstance(value, dict):
        raise CalibrationError("Calibration request must contain a JSON object")
    _validate_json(value, label="Calibration request")
    return value


def _parse_time(value: Any, *, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise CalibrationError(f"{field} must not be empty")
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise CalibrationError(
                f"{field} must be an RFC 3339 timestamp with a timezone"
            ) from exc
    else:
        raise CalibrationError(
            f"{field} must be an RFC 3339 timestamp with a timezone"
        )
    if parsed.tzinfo is None:
        raise CalibrationError(f"{field} must include a timezone")
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise CalibrationError(f"{field} is outside the supported range") from exc


def _observed_at(
    envelope: Mapping[str, Any], report: Mapping[str, Any], now: datetime
) -> str:
    supplied = []
    for location, document in (("envelope", envelope), ("report", report)):
        supplied.extend(
            (f"{location}.{name}", document.get(name))
            for name in ("observed_at", "recorded_at")
            if document.get(name) is not None
        )

    if supplied:
        parsed_values = [_parse_time(value, field=name) for name, value in supplied]
        if any(value != parsed_values[0] for value in parsed_values[1:]):
            raise CalibrationError(
                "Explicit observed_at/recorded_at timestamps disagree"
            )
        observed = parsed_values[0]
    else:
        created_unix = report.get("created_unix")
        if (
            isinstance(created_unix, bool)
            or not isinstance(created_unix, (int, float))
        ):
            raise CalibrationError(
                "Provide timezone-aware observed_at/recorded_at or report.created_unix"
            )
        try:
            created_seconds = float(created_unix)
        except (OverflowError, ValueError) as exc:
            raise CalibrationError(
                "report.created_unix is outside the supported range"
            ) from exc
        if not math.isfinite(created_seconds) or created_seconds <= 0:
            raise CalibrationError(
                "Provide timezone-aware observed_at/recorded_at or report.created_unix"
            )
        try:
            observed = datetime.fromtimestamp(created_seconds, timezone.utc)
        except (OverflowError, OSError, ValueError) as exc:
            raise CalibrationError("report.created_unix is outside the supported range") from exc

    if observed > now + MAX_CLOCK_SKEW:
        raise CalibrationError(
            "observed_at cannot be more than five minutes in the future"
        )
    return observed.isoformat()


def _aliased_value(
    payload: Mapping[str, Any], aliases: Sequence[str], *, label: str
) -> tuple[bool, Any]:
    present = [name for name in aliases if name in payload]
    if not present:
        return False, None
    value = payload[present[0]]
    canonical = _canonical_json(value)
    for name in present[1:]:
        if _canonical_json(payload[name]) != canonical:
            raise CalibrationError(
                f"Conflicting {label} aliases: {', '.join(present)}"
            )
    return True, value


def _reject_sensitive_metadata(value: Any, *, path: str = "source_metadata") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.casefold().replace("-", "_").replace(" ", "_")
            sensitive_suffixes = (
                "authorization",
                "cookie",
                "credential",
                "credentials",
                "password",
                "private_key",
                "secret",
                "token",
            )
            sensitive_prefixes = (
                "access_token",
                "auth_token",
                "bearer_token",
                "client_secret",
                "id_token",
                "refresh_token",
            )
            if (
                normalized in _SENSITIVE_METADATA_KEYS
                or "api_key" in normalized
                or "apikey" in normalized
                or "private_key" in normalized
                or normalized.startswith(sensitive_prefixes)
                or normalized.endswith(sensitive_suffixes)
            ):
                raise CalibrationError(
                    f"Calibration documents must not contain credentials ({path}.{key})"
                )
            _reject_sensitive_metadata(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_sensitive_metadata(item, path=f"{path}[{index}]")


class CalibrationArchive:
    """Store and retrieve immutable calibration resources."""

    def __init__(
        self,
        store: Store,
        *,
        layout_provider: Optional[
            Callable[[str], Optional[Mapping[str, Any]]]
        ] = None,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self.store = store
        self.layout_provider = layout_provider
        self.clock = clock

    def _layout_snapshot(self, observed_at: str) -> Optional[Dict[str, Any]]:
        if self.layout_provider is None:
            return None
        resolved = self.layout_provider(observed_at)
        if resolved is None:
            return None
        if not isinstance(resolved, Mapping):
            raise CalibrationIntegrityError(
                "Tag layout history returned an invalid historical revision"
            )
        snapshot = {
            field: resolved.get(field)
            for field in _LAYOUT_SNAPSHOT_FIELDS
            if field in resolved
        }
        if not snapshot.get("id"):
            raise CalibrationIntegrityError(
                "Tag layout history returned a historical revision without an ID"
            )
        _validate_json(snapshot, label="Tag layout revision snapshot")
        return snapshot

    @staticmethod
    def _normalize_payload(
        payload: Mapping[str, Any], now: datetime
    ) -> tuple[
        Dict[str, Any],
        Optional[Dict[str, Any]],
        Dict[str, Any],
        str,
        Optional[str],
        str,
        int,
    ]:
        is_flat_report = "kind" in payload and "schema_version" in payload
        if is_flat_report:
            _, pose_value = _aliased_value(
                payload, _POSE_CONFIG_ALIASES, label="pose_config"
            )
            pose_fields = set(_POSE_CONFIG_ALIASES) & set(payload)
            report_value = {
                key: value for key, value in payload.items() if key not in pose_fields
            }
            envelope = {}
            requested_robot_id = report_value.get("robot_id")
            source_metadata = {}
        elif any(name in payload for name in _REPORT_ALIASES):
            has_report, report_value = _aliased_value(
                payload, _REPORT_ALIASES, label="report"
            )
            if not has_report:
                raise CalibrationError("Calibration envelope must contain report")
            _, pose_value = _aliased_value(
                payload, _POSE_CONFIG_ALIASES, label="pose_config"
            )
            envelope = payload
            requested_robot_id = payload.get("robot_id")
            source_metadata = {
                key: value
                for key, value in payload.items()
                if key not in _ENVELOPE_FIELDS
            }
            _reject_sensitive_metadata(source_metadata)
        else:
            report_value = payload
            pose_value = None
            envelope = {}
            requested_robot_id = payload.get("robot_id")
            source_metadata = {}

        if not isinstance(report_value, dict):
            raise CalibrationError("report must contain a JSON object")
        report = dict(report_value)
        _validate_json(report, label="Calibration report")
        _reject_sensitive_metadata(report, path="report")

        kind = report.get("kind")
        if not isinstance(kind, str) or not kind.strip() or len(kind) > 160:
            raise CalibrationError("report.kind must be a non-empty string")
        kind = kind.strip()
        schema_version = report.get("schema_version")
        if (
            isinstance(schema_version, bool)
            or not isinstance(schema_version, int)
            or schema_version < 1
            or schema_version > MAX_SCHEMA_VERSION
        ):
            raise CalibrationError(
                f"report.schema_version must be between 1 and {MAX_SCHEMA_VERSION}"
            )

        advisory = kind == _ADVISORY_TRACKER_KIND or report.get("advisory_only") is True
        if advisory:
            for field in ("motor_commands_sent", "servo_zeros_changed"):
                if report.get(field) is not False:
                    raise CalibrationError(
                        f"Advisory tracker report must set {field}=false"
                    )

        pose_config: Optional[Dict[str, Any]]
        if pose_value is None:
            pose_config = None
        elif isinstance(pose_value, dict):
            pose_config = dict(pose_value)
            _validate_json(pose_config, label="Pose configuration")
            _reject_sensitive_metadata(pose_config, path="pose_config")
            if not pose_config:
                raise CalibrationError("pose_config must not be empty")
            pose_schema = pose_config.get("schema_version")
            if (
                isinstance(pose_schema, bool)
                or not isinstance(pose_schema, int)
                or pose_schema < 1
                or pose_schema > MAX_SCHEMA_VERSION
            ):
                raise CalibrationError(
                    "pose_config.schema_version must be between 1 and "
                    f"{MAX_SCHEMA_VERSION}"
                )
            if not (set(pose_config) - {"schema_version"}):
                raise CalibrationError(
                    "pose_config must include configuration data"
                )
        else:
            raise CalibrationError("pose_config must contain a JSON object")

        report_robot_id = report.get("robot_id")
        if report_robot_id is not None and (
            not isinstance(report_robot_id, str)
            or not report_robot_id.strip()
            or len(report_robot_id.strip()) > 160
        ):
            raise CalibrationError("report.robot_id must be a non-empty string")
        if isinstance(report_robot_id, str):
            report_robot_id = report_robot_id.strip()
        if requested_robot_id is None:
            requested_robot_id = report_robot_id
        if requested_robot_id is not None:
            if (
                not isinstance(requested_robot_id, str)
                or not requested_robot_id.strip()
                or len(requested_robot_id.strip()) > 160
            ):
                raise CalibrationError("robot_id must be a non-empty string")
            requested_robot_id = requested_robot_id.strip()
        if (
            report_robot_id is not None
            and requested_robot_id is not None
            and report_robot_id != requested_robot_id
        ):
            raise CalibrationConflict(
                "Envelope robot_id conflicts with report.robot_id"
            )

        observed_at = _observed_at(envelope, report, now)
        return (
            report,
            pose_config,
            source_metadata,
            observed_at,
            requested_robot_id,
            kind,
            schema_version,
        )

    @staticmethod
    def _row_value(row: sqlite3.Row, *, include_documents: bool) -> Dict[str, Any]:
        report_text = row["report_json"]
        pose_text = row["pose_config_json"]
        layout_text = row["tag_layout_revision_json"]
        source_metadata_text = row["source_metadata_json"]
        if _sha256(report_text) != row["report_sha256"]:
            raise CalibrationIntegrityError(
                "Stored calibration report does not match its digest"
            )
        if (pose_text is None) != (row["pose_config_sha256"] is None):
            raise CalibrationIntegrityError(
                "Stored calibration pose config and digest disagree"
            )
        if pose_text is not None and _sha256(pose_text) != row["pose_config_sha256"]:
            raise CalibrationIntegrityError(
                "Stored calibration pose config does not match its digest"
            )
        try:
            report = json.loads(report_text)
            pose_config = json.loads(pose_text) if pose_text else None
            layout_revision = json.loads(layout_text) if layout_text else None
            source_metadata = json.loads(source_metadata_text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise CalibrationIntegrityError(
                "Stored calibration document is invalid"
            ) from exc
        if not isinstance(report, dict):
            raise CalibrationIntegrityError(
                "Stored calibration report is not an object"
            )
        if pose_config is not None and not isinstance(pose_config, dict):
            raise CalibrationIntegrityError(
                "Stored calibration pose config is not an object"
            )
        if layout_revision is not None and not isinstance(layout_revision, dict):
            raise CalibrationIntegrityError(
                "Stored calibration layout snapshot is not an object"
            )
        if not isinstance(source_metadata, dict):
            raise CalibrationIntegrityError(
                "Stored calibration source metadata is not an object"
            )
        try:
            _validate_json(report, label="Stored calibration report")
            _validate_json(pose_config, label="Stored calibration pose config")
            _validate_json(layout_revision, label="Stored calibration layout snapshot")
            _validate_json(source_metadata, label="Stored calibration source metadata")
        except CalibrationError as exc:
            raise CalibrationIntegrityError(str(exc)) from exc

        request_document = {
            "observed_at": row["observed_at"],
            "pose_config": pose_config,
            "report": report,
            "robot_id": row["robot_id"],
        }
        if source_metadata:
            request_document["source_metadata"] = source_metadata
        candidate_documents = [request_document]
        if (
            layout_revision is not None
            and report.get("robot_id") is None
            and row["robot_id"] == layout_revision.get("robot_id")
        ):
            derived_robot_document = dict(request_document)
            derived_robot_document["robot_id"] = None
            candidate_documents.append(derived_robot_document)
        request_hash = row["request_sha256"]
        if not any(
            _sha256(_canonical_json(candidate)) == request_hash
            for candidate in candidate_documents
        ):
            raise CalibrationIntegrityError(
                "Stored calibration request does not match its digest"
            )
        if row["id"] != f"cal-{request_hash}":
            raise CalibrationIntegrityError(
                "Stored calibration ID does not match its request digest"
            )
        report_kind = report.get("kind")
        if not isinstance(report_kind, str) or report_kind.strip() != row["kind"]:
            raise CalibrationIntegrityError(
                "Stored calibration kind disagrees with its report"
            )
        if report.get("schema_version") != row["schema_version"]:
            raise CalibrationIntegrityError(
                "Stored calibration schema version disagrees with its report"
            )
        if bool(row["replay_ready"]):
            raise CalibrationIntegrityError(
                "Archived calibration unexpectedly claims automatic replay readiness"
            )
        if layout_revision is not None:
            if not layout_revision.get("id"):
                raise CalibrationIntegrityError(
                    "Stored calibration layout snapshot has no revision ID"
                )
            layout_robot_id = layout_revision.get("robot_id")
            if layout_robot_id and row["robot_id"] != layout_robot_id:
                raise CalibrationIntegrityError(
                    "Stored calibration robot ID disagrees with its layout snapshot"
                )
        value: Dict[str, Any] = {
            "sequence": int(row["sequence"]),
            "id": row["id"],
            "request_sha256": row["request_sha256"],
            "report_sha256": row["report_sha256"],
            "pose_config_sha256": row["pose_config_sha256"],
            "observed_at": row["observed_at"],
            "created_at": row["created_at"],
            "created_by": row["created_by"],
            "robot_id": row["robot_id"],
            "kind": row["kind"],
            "schema_version": int(row["schema_version"]),
            "status": "archived",
            "current": False,
            "replay_ready": False,
            "replay_status": (
                "pose_config_missing"
                if pose_text is None else
                "tag_layout_unresolved"
                if layout_revision is None else
                "archived_not_activated"
            ),
            "tag_layout_revision": layout_revision,
        }
        if include_documents:
            value["report"] = report
            value["pose_config"] = pose_config
            value["source_metadata"] = source_metadata
        return value

    def import_payload(
        self,
        payload: Mapping[str, Any],
        *,
        created_by: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise CalibrationError("Calibration request must contain a JSON object")
        payload = dict(payload)
        _validate_json(payload, label="Calibration request")
        if not isinstance(created_by, str) or not created_by.strip():
            raise CalibrationError("Authenticated calibration creator is required")
        key = idempotency_key.strip() if isinstance(idempotency_key, str) else None
        if key == "":
            key = None
        if key is not None and len(key) > 200:
            raise CalibrationError("Idempotency-Key must not exceed 200 characters")

        now = self.clock().astimezone(timezone.utc)
        (
            report,
            pose_config,
            source_metadata,
            observed_at,
            robot_id,
            kind,
            schema_version,
        ) = self._normalize_payload(payload, now)
        report_text = _canonical_json(report)
        pose_text = _canonical_json(pose_config) if pose_config is not None else None
        source_metadata_text = _canonical_json(source_metadata)
        request_document = {
            "observed_at": observed_at,
            "pose_config": pose_config,
            "report": report,
            "robot_id": robot_id,
        }
        if source_metadata:
            request_document["source_metadata"] = source_metadata
        request_text = _canonical_json(request_document)
        if len(request_text.encode("utf-8")) > MAX_CALIBRATION_BYTES:
            raise CalibrationTooLarge("Canonical calibration exceeds the 2 MiB limit")
        request_hash = _sha256(request_text)
        calibration_id = f"cal-{request_hash}"
        created_at = now.isoformat()

        with self.store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if key is not None:
                receipt = connection.execute(
                    "SELECT calibration_id,request_sha256 FROM calibration_import_keys "
                    "WHERE idempotency_key=?",
                    (key,),
                ).fetchone()
                if receipt is not None:
                    if receipt["request_sha256"] != request_hash:
                        connection.execute("ROLLBACK")
                        raise CalibrationConflict(
                            "Idempotency-Key was already used for a different calibration"
                        )
                    row = connection.execute(
                        "SELECT * FROM calibrations WHERE id=?",
                        (receipt["calibration_id"],),
                    ).fetchone()
                    if row is None:
                        connection.execute("ROLLBACK")
                        raise CalibrationIntegrityError(
                            "Calibration idempotency receipt references missing evidence"
                        )
                    connection.execute("COMMIT")
                    return self._row_value(row, include_documents=True)

            existing = connection.execute(
                "SELECT * FROM calibrations WHERE request_sha256=?", (request_hash,)
            ).fetchone()
            if existing is not None:
                if key is not None:
                    connection.execute(
                        "INSERT INTO calibration_import_keys("
                        "idempotency_key,calibration_id,request_sha256,created_at"
                        ") VALUES(?,?,?,?)",
                        (key, existing["id"], request_hash, created_at),
                    )
                connection.execute("COMMIT")
                return self._row_value(existing, include_documents=True)

            layout_revision = self._layout_snapshot(observed_at)
            layout_text = (
                _canonical_json(layout_revision) if layout_revision is not None else None
            )
            layout_robot_id = (
                str(layout_revision.get("robot_id"))
                if layout_revision and layout_revision.get("robot_id") else None
            )
            if robot_id and layout_robot_id and robot_id != layout_robot_id:
                connection.execute("ROLLBACK")
                raise CalibrationConflict(
                    "robot_id conflicts with the tag layout effective at observed_at"
                )
            stored_robot_id = robot_id or layout_robot_id
            try:
                connection.execute(
                    "INSERT INTO calibrations("
                    "id,request_sha256,report_sha256,report_json,pose_config_sha256,"
                    "pose_config_json,observed_at,created_at,created_by,robot_id,kind,"
                    "schema_version,replay_ready,tag_layout_revision_json,"
                    "source_metadata_json"
                    ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        calibration_id,
                        request_hash,
                        _sha256(report_text),
                        report_text,
                        _sha256(pose_text) if pose_text is not None else None,
                        pose_text,
                        observed_at,
                        created_at,
                        created_by.strip(),
                        stored_robot_id,
                        kind,
                        schema_version,
                        0,
                        layout_text,
                        source_metadata_text,
                    ),
                )
                if key is not None:
                    connection.execute(
                        "INSERT INTO calibration_import_keys("
                        "idempotency_key,calibration_id,request_sha256,created_at"
                        ") VALUES(?,?,?,?)",
                        (key, calibration_id, request_hash, created_at),
                    )
                row = connection.execute(
                    "SELECT * FROM calibrations WHERE id=?", (calibration_id,)
                ).fetchone()
                connection.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                connection.execute("ROLLBACK")
                raise CalibrationConflict("Could not archive calibration") from exc
        assert row is not None
        return self._row_value(row, include_documents=True)

    def import_bytes(
        self,
        raw: bytes,
        *,
        created_by: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.import_payload(
            decode_calibration_json(raw),
            created_by=created_by,
            idempotency_key=idempotency_key,
        )

    def list(self, limit: int = 100) -> Sequence[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        with self.store.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM calibrations ORDER BY sequence DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_value(row, include_documents=False) for row in rows]

    def get(self, calibration_id: str) -> Dict[str, Any]:
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM calibrations WHERE id=?", (calibration_id,)
            ).fetchone()
        if row is None:
            raise CalibrationNotFound("Calibration not found")
        return self._row_value(row, include_documents=True)


__all__ = [
    "CALIBRATION_DETAIL_OPENAPI",
    "CALIBRATION_LIST_OPENAPI",
    "CALIBRATION_REQUEST_OPENAPI",
    "CalibrationArchive",
    "CalibrationConflict",
    "CalibrationError",
    "CalibrationIntegrityError",
    "CalibrationNotFound",
    "CalibrationTooLarge",
    "MAX_CALIBRATION_BYTES",
    "MAX_CLOCK_SKEW",
    "MAX_SCHEMA_VERSION",
    "decode_calibration_json",
]
