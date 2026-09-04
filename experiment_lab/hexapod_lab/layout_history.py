"""Immutable, effective-dated AprilTag layout history for Robot Lab.

The physical layout, the exact tracker pose configuration (with reviewed child
rotations patched), and both audit maps travel as one revision. Revisions and activations are append-only in the
database; the files under ``active-*`` are merely atomic compatibility copies
for tools which still accept filesystem paths.
"""

from __future__ import annotations

import copy
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple, Union

from .db import Store


SNAPSHOT_FILES = {
    "layout": "apriltag-layout.snapshot.json",
    "pose_config": "apriltag-pose-config.snapshot.json",
    "floor_map": "floor-tag-map.snapshot.json",
    "part_map": "hexapod-tag-map.snapshot.json",
}
CONTEXT_FILE = "vision-context.json"
_AXIS_VECTORS = {
    "+x": (1.0, 0.0, 0.0),
    "-x": (-1.0, 0.0, 0.0),
    "+y": (0.0, 1.0, 0.0),
    "-y": (0.0, -1.0, 0.0),
    "+z": (0.0, 0.0, 1.0),
    "-z": (0.0, 0.0, -1.0),
}


class LayoutHistoryError(ValueError):
    """Base class for errors safe to surface to an API caller."""


class LayoutHistoryUnavailable(LayoutHistoryError):
    """Raised when no verified layout revision is available."""


class LayoutHistoryNotFound(LayoutHistoryError):
    """Raised when a requested revision or experiment pin does not exist."""


class LayoutHistoryConflict(LayoutHistoryError):
    """Raised for a stale, non-idempotent, or integrity-breaking write."""


class LayoutHistoryIntegrityError(LayoutHistoryError):
    """Raised when stored bytes no longer match their immutable digest."""


TimeValue = Union[str, datetime, date]
JsonInput = Union[str, bytes, Path, Mapping[str, Any]]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: TimeValue, *, field: str = "timestamp") -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise LayoutHistoryError(f"{field} must not be empty")
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise LayoutHistoryError(f"{field} must be an RFC 3339 timestamp") from exc
    else:
        raise LayoutHistoryError(f"{field} must be an RFC 3339 timestamp")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _time_text(value: TimeValue, *, field: str = "timestamp") -> str:
    return _parse_time(value, field=field).isoformat()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _pretty_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _object_from_text(value: str, *, label: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LayoutHistoryError(f"{label} is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise LayoutHistoryError(f"{label} must contain a JSON object")
    return parsed


def _read_exact_json(path: Path, *, label: str) -> Tuple[str, Dict[str, Any]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise LayoutHistoryUnavailable(f"Cannot read {label}: {path}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LayoutHistoryError(f"{label} must be UTF-8 JSON") from exc
    return text, _object_from_text(text, label=label)


def _json_input(value: JsonInput, *, label: str) -> Tuple[str, Dict[str, Any]]:
    if isinstance(value, Path):
        return _read_exact_json(value, label=label)
    if isinstance(value, bytes):
        try:
            text = value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LayoutHistoryError(f"{label} must be UTF-8 JSON") from exc
        return text, _object_from_text(text, label=label)
    if isinstance(value, str):
        return value, _object_from_text(value, label=label)
    if isinstance(value, Mapping):
        document = copy.deepcopy(dict(value))
        return _pretty_json_text(document), document
    raise LayoutHistoryError(f"{label} must be a JSON object, string, bytes, or path")


def _write_once(path: Path, text: str) -> bool:
    """Atomically create immutable evidence, accepting exact retries only."""

    path.parent.mkdir(parents=True, exist_ok=True)
    expected = text.encode("utf-8")
    if path.exists():
        if path.is_file() and path.read_bytes() == expected:
            return False
        raise LayoutHistoryConflict(f"Refusing to replace differing evidence: {path.name}")

    descriptor, temporary_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(expected)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        try:
            os.link(temporary, path)
        except FileExistsError:
            if not path.is_file() or path.read_bytes() != expected:
                raise LayoutHistoryConflict(
                    f"Refusing to replace differing evidence: {path.name}"
                )
            return False
        return True
    finally:
        temporary.unlink(missing_ok=True)


def _finite_sequence(value: Any, length: int, *, label: str) -> Sequence[float]:
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise LayoutHistoryConflict(f"{label} must contain {length} numbers")
    try:
        numbers = [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise LayoutHistoryConflict(f"{label} must contain {length} numbers") from exc
    if not all(math.isfinite(item) for item in numbers):
        raise LayoutHistoryConflict(f"{label} must contain finite numbers")
    return numbers


def _quaternion_from_axes(value: Any, *, tag_id: int) -> Sequence[float]:
    if not isinstance(value, dict) or set(value) != {"x", "y", "z"}:
        raise LayoutHistoryConflict(f"tag {tag_id} has invalid readable axes")
    axes = list(value.values())
    if any(item not in _AXIS_VECTORS for item in axes):
        raise LayoutHistoryConflict(f"tag {tag_id} has invalid readable axes")
    if {item[-1] for item in axes} != {"x", "y", "z"}:
        raise LayoutHistoryConflict(f"tag {tag_id} readable axes are not orthogonal")
    columns = [_AXIS_VECTORS[str(value[name])] for name in "xyz"]
    matrix = [[columns[column][row] for column in range(3)] for row in range(3)]
    determinant = (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )
    if not math.isclose(determinant, 1.0, abs_tol=1e-6):
        raise LayoutHistoryConflict(f"tag {tag_id} readable axes are not right-handed")

    trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * scale
        qx = (matrix[2][1] - matrix[1][2]) / scale
        qy = (matrix[0][2] - matrix[2][0]) / scale
        qz = (matrix[1][0] - matrix[0][1]) / scale
    elif matrix[0][0] > matrix[1][1] and matrix[0][0] > matrix[2][2]:
        scale = math.sqrt(1.0 + matrix[0][0] - matrix[1][1] - matrix[2][2]) * 2.0
        qw = (matrix[2][1] - matrix[1][2]) / scale
        qx = 0.25 * scale
        qy = (matrix[0][1] + matrix[1][0]) / scale
        qz = (matrix[0][2] + matrix[2][0]) / scale
    elif matrix[1][1] > matrix[2][2]:
        scale = math.sqrt(1.0 + matrix[1][1] - matrix[0][0] - matrix[2][2]) * 2.0
        qw = (matrix[0][2] - matrix[2][0]) / scale
        qx = (matrix[0][1] + matrix[1][0]) / scale
        qy = 0.25 * scale
        qz = (matrix[1][2] + matrix[2][1]) / scale
    else:
        scale = math.sqrt(1.0 + matrix[2][2] - matrix[0][0] - matrix[1][1]) * 2.0
        qw = (matrix[1][0] - matrix[0][1]) / scale
        qx = (matrix[0][2] + matrix[2][0]) / scale
        qy = (matrix[1][2] + matrix[2][1]) / scale
        qz = 0.25 * scale
    quaternion = [qx, qy, qz, qw]
    norm = math.sqrt(sum(item * item for item in quaternion))
    return [item / norm for item in quaternion]


def _orientation_only_changes(
    parent: Mapping[str, Any], candidate: Mapping[str, Any]
) -> Sequence[int]:
    """Validate a phone proposal and return its actually changed tag IDs."""

    parent_document = copy.deepcopy(dict(parent))
    candidate_document = copy.deepcopy(dict(candidate))
    candidate_document.pop("proposal_metadata", None)
    parent_document.pop("proposal_metadata", None)

    parent_tags = parent_document.pop("robot_tags", None)
    candidate_tags = candidate_document.pop("robot_tags", None)
    if parent_document != candidate_document:
        raise LayoutHistoryConflict(
            "A phone proposal may change tag orientation only, not layout metadata"
        )
    if not isinstance(parent_tags, list) or not isinstance(candidate_tags, list):
        raise LayoutHistoryConflict("Both layouts must contain robot_tags arrays")
    if len(parent_tags) != len(candidate_tags):
        raise LayoutHistoryConflict("A phone proposal may not add or remove robot tags")

    changed = []
    for parent_tag, candidate_tag in zip(parent_tags, candidate_tags):
        if not isinstance(parent_tag, dict) or not isinstance(candidate_tag, dict):
            raise LayoutHistoryConflict("Every robot tag must be a JSON object")
        try:
            tag_id = int(parent_tag["id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise LayoutHistoryConflict("Every robot tag must have an integer ID") from exc
        if candidate_tag.get("id") != parent_tag.get("id"):
            raise LayoutHistoryConflict("A phone proposal may not reorder or rename tag IDs")

        parent_copy = copy.deepcopy(parent_tag)
        candidate_copy = copy.deepcopy(candidate_tag)
        parent_transform = parent_copy.pop("frame_from_tag", None)
        candidate_transform = candidate_copy.pop("frame_from_tag", None)
        if parent_copy != candidate_copy:
            raise LayoutHistoryConflict(
                f"A phone proposal changed tag {tag_id} identity or mount assignment"
            )
        if not isinstance(parent_transform, dict) or not isinstance(candidate_transform, dict):
            raise LayoutHistoryConflict(f"tag {tag_id} must have frame_from_tag")

        parent_rotation_keys = {
            key for key in ("euler_xyz_deg", "quaternion_xyzw") if key in parent_transform
        }
        candidate_rotation_keys = {
            key for key in ("euler_xyz_deg", "quaternion_xyzw") if key in candidate_transform
        }
        if len(parent_rotation_keys) != 1 or candidate_rotation_keys != parent_rotation_keys:
            raise LayoutHistoryConflict(
                f"tag {tag_id} changed orientation representation"
            )
        rotation_key = next(iter(parent_rotation_keys))
        allowed = {rotation_key}
        if rotation_key == "quaternion_xyzw":
            allowed.add("tag_axes_in_frame")
        if {
            key: value for key, value in parent_transform.items() if key not in allowed
        } != {
            key: value for key, value in candidate_transform.items() if key not in allowed
        }:
            raise LayoutHistoryConflict(
                f"A phone proposal changed tag {tag_id} translation or transform metadata"
            )

        if rotation_key == "euler_xyz_deg":
            old = _finite_sequence(
                parent_transform[rotation_key], 3, label=f"tag {tag_id} Euler rotation"
            )
            new = _finite_sequence(
                candidate_transform[rotation_key], 3, label=f"tag {tag_id} Euler rotation"
            )
            if old[:2] != new[:2]:
                raise LayoutHistoryConflict(
                    f"A phone proposal may change only tag {tag_id} in-plane rotation"
                )
        else:
            _finite_sequence(
                parent_transform[rotation_key], 4, label=f"tag {tag_id} quaternion"
            )
            quaternion = _finite_sequence(
                candidate_transform[rotation_key], 4, label=f"tag {tag_id} quaternion"
            )
            norm = math.sqrt(sum(item * item for item in quaternion))
            if abs(norm - 1.0) > 1e-5:
                raise LayoutHistoryConflict(f"tag {tag_id} quaternion is not normalized")
            expected_quaternion = _quaternion_from_axes(
                candidate_transform.get("tag_axes_in_frame"), tag_id=tag_id
            )
            same = math.sqrt(
                sum((left - right) ** 2 for left, right in zip(quaternion, expected_quaternion))
            )
            negated = math.sqrt(
                sum((left + right) ** 2 for left, right in zip(quaternion, expected_quaternion))
            )
            if min(same, negated) > 1e-5:
                raise LayoutHistoryConflict(
                    f"tag {tag_id} quaternion does not match its readable axes"
                )

        if parent_transform != candidate_transform:
            changed.append(tag_id)
    return changed


def _patch_pose_orientations(
    parent_pose: Mapping[str, Any],
    candidate_layout: Mapping[str, Any],
    changed_tag_ids: Sequence[int],
) -> Dict[str, Any]:
    """Patch only supported tag rotations in an otherwise exact pose config."""

    result = copy.deepcopy(dict(parent_pose))
    robot_pose = result.get("robot_pose")
    pose_tags = robot_pose.get("tags") if isinstance(robot_pose, dict) else None
    if not isinstance(pose_tags, dict):
        raise LayoutHistoryError("pose config robot_pose.tags must be an object")
    physical_tags = candidate_layout.get("robot_tags")
    if not isinstance(physical_tags, list):
        raise LayoutHistoryError("layout.robot_tags must be an array")
    by_id = {int(item["id"]): item for item in physical_tags}
    for tag_id in changed_tag_ids:
        pose_tag = pose_tags.get(str(tag_id))
        # The physical inventory includes uncalibrated yoke tags. Do not turn
        # those into metric tracker inputs just because their rotation is known.
        if pose_tag is None:
            continue
        if not isinstance(pose_tag, dict):
            raise LayoutHistoryError(f"pose config tag {tag_id} must be an object")
        physical = by_id[tag_id]
        physical_transform = physical.get("frame_from_tag")
        pose_transform = pose_tag.get("frame_from_tag")
        if not isinstance(physical_transform, dict) or not isinstance(
            pose_transform, dict
        ):
            raise LayoutHistoryError(f"tag {tag_id} must have frame_from_tag")
        rotation_keys = [
            key for key in ("euler_xyz_deg", "quaternion_xyzw")
            if key in physical_transform
        ]
        if len(rotation_keys) != 1:
            raise LayoutHistoryError(f"tag {tag_id} has an ambiguous rotation")
        rotation_key = rotation_keys[0]
        for key in ("euler_xyz_deg", "quaternion_xyzw"):
            if key != rotation_key:
                pose_transform.pop(key, None)
        pose_transform[rotation_key] = copy.deepcopy(
            physical_transform[rotation_key]
        )
        if physical.get("frame"):
            pose_tag["frame"] = physical["frame"]
    return result


def _recording_time_from_artifacts(run_dir: Path) -> Optional[str]:
    """Find the earliest trusted camera timestamp without using file mtimes."""

    candidates = []
    for path in sorted(run_dir.glob("*camera_timestamps.csv")):
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                row = next(csv.DictReader(stream), None)
            if row:
                for field in ("capture_unix_s", "unix_s"):
                    if row.get(field):
                        candidates.append(float(row[field]))
                        break
        except (OSError, ValueError, TypeError, csv.Error):
            continue
    for path in sorted(run_dir.glob("*.jsonl")):
        try:
            with path.open("r", encoding="utf-8") as stream:
                line = stream.readline()
            row = json.loads(line)
            if isinstance(row, dict):
                for field in ("capture_unix_s", "capture_unix"):
                    if row.get(field) is not None:
                        candidates.append(float(row[field]))
                        break
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    if not candidates:
        return None
    value = min(candidates)
    if not math.isfinite(value) or value <= 0:
        return None
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


class TagLayoutHistory:
    """Own the Robot Lab's immutable AprilTag history and evidence snapshots."""

    def __init__(
        self,
        store: Store,
        data_dir: Path,
        *,
        layout_path: Optional[Path],
        pose_template_path: Optional[Path],
        floor_map_path: Optional[Path],
        part_map_path: Optional[Path],
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self.store = store
        self.data_dir = Path(data_dir)
        self.layout_path = Path(layout_path) if layout_path else None
        self.pose_template_path = Path(pose_template_path) if pose_template_path else None
        self.floor_map_path = Path(floor_map_path) if floor_map_path else None
        self.part_map_path = Path(part_map_path) if part_map_path else None
        self.clock = clock
        self.root = self.data_dir / "tag-layout-history"
        self.active_bundle_path = self.root / "active"
        self.revision_bundles_path = self.root / "revision-bundles-v2"
        self.active_layout_path = (
            self.active_bundle_path / SNAPSHOT_FILES["layout"]
        )
        self.active_pose_config_path = (
            self.active_bundle_path / SNAPSHOT_FILES["pose_config"]
        )
        self.active_floor_map_path = (
            self.active_bundle_path / SNAPSHOT_FILES["floor_map"]
        )
        self.active_part_map_path = (
            self.active_bundle_path / SNAPSHOT_FILES["part_map"]
        )

    @property
    def available(self) -> bool:
        return self.current() is not None

    def _configured_sources_available(self) -> bool:
        return all(
            path is not None and path.is_file()
            for path in (
                self.layout_path,
                self.pose_template_path,
                self.floor_map_path,
                self.part_map_path,
            )
        )

    def _repair_legacy_document_columns(self) -> None:
        """Complete rows written by the short-lived pre-release schema.

        That preview stored layouts/pose data but had no floor/part document
        columns. The migration is done before serving requests and restores the
        immutability trigger in the same transaction.
        """

        with self.store.connect() as connection:
            schema_version = int(
                connection.execute("PRAGMA user_version").fetchone()[0]
            )
            total = connection.execute(
                "SELECT COUNT(*) AS value FROM tag_layout_revisions"
            ).fetchone()["value"]
            incomplete = connection.execute(
                "SELECT COUNT(*) AS value FROM tag_layout_revisions WHERE "
                "pose_config_sha256 IS NULL OR pose_config_json IS NULL OR "
                "floor_map_sha256 IS NULL OR floor_map_json IS NULL OR "
                "part_map_sha256 IS NULL OR part_map_json IS NULL"
            ).fetchone()["value"]
        if not total:
            with self.store.connect() as connection:
                connection.execute("PRAGMA user_version=2")
            return
        if not incomplete and schema_version >= 2:
            with self.store.connect() as connection:
                connection.execute("PRAGMA user_version=2")
            return
        if not self._configured_sources_available():
            raise LayoutHistoryIntegrityError(
                "Legacy layout history needs all four configured vision files to migrate"
            )
        assert self.pose_template_path is not None
        assert self.floor_map_path is not None
        assert self.part_map_path is not None
        source_pose_text, _ = _read_exact_json(
            self.pose_template_path, label="AprilTag pose template"
        )
        source_floor_text, _ = _read_exact_json(
            self.floor_map_path, label="floor tag map"
        )
        source_part_text, _ = _read_exact_json(
            self.part_map_path, label="hexapod tag map"
        )
        with self.store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute("DROP TRIGGER IF EXISTS tag_layout_revisions_no_update")
                rows = connection.execute(
                    "SELECT * FROM tag_layout_revisions ORDER BY sequence"
                ).fetchall()
                repaired_pose: Dict[str, str] = {}
                for row in rows:
                    pose_text = row["pose_config_json"]
                    pose_hash = row["pose_config_sha256"]
                    if schema_version < 2 or pose_text is None or pose_hash is None:
                        if row["source_kind"] == "baseline" or not row["parent_revision_id"]:
                            pose_text = source_pose_text
                        else:
                            parent_text = repaired_pose.get(str(row["parent_revision_id"]))
                            if parent_text is None:
                                parent = connection.execute(
                                    "SELECT pose_config_json FROM tag_layout_revisions WHERE id=?",
                                    (row["parent_revision_id"],),
                                ).fetchone()
                                parent_text = parent["pose_config_json"] if parent else None
                            if not parent_text:
                                raise LayoutHistoryIntegrityError(
                                    "Legacy candidate has no recoverable parent pose config"
                                )
                            pose_text = _pretty_json_text(
                                _patch_pose_orientations(
                                    _object_from_text(
                                        parent_text, label="legacy parent pose config"
                                    ),
                                    _object_from_text(
                                        row["layout_json"], label="legacy candidate layout"
                                    ),
                                    json.loads(row["changed_tag_ids_json"]),
                                )
                            )
                        pose_hash = _sha256_text(pose_text)
                    elif _sha256_text(pose_text) != pose_hash:
                        raise LayoutHistoryIntegrityError(
                            "Legacy pose config does not match its stored digest"
                        )
                    floor_text = row["floor_map_json"] or source_floor_text
                    floor_hash = row["floor_map_sha256"] or _sha256_text(floor_text)
                    part_text = row["part_map_json"] or source_part_text
                    part_hash = row["part_map_sha256"] or _sha256_text(part_text)
                    if _sha256_text(floor_text) != floor_hash or _sha256_text(
                        part_text
                    ) != part_hash:
                        raise LayoutHistoryIntegrityError(
                            "Legacy audit map does not match its stored digest"
                        )
                    connection.execute(
                        "UPDATE tag_layout_revisions SET pose_config_sha256=?,"
                        "pose_config_json=?,floor_map_sha256=?,floor_map_json=?,"
                        "part_map_sha256=?,part_map_json=? WHERE id=?",
                        (
                            pose_hash,
                            pose_text,
                            floor_hash,
                            floor_text,
                            part_hash,
                            part_text,
                            row["id"],
                        ),
                    )
                    repaired_pose[str(row["id"])] = pose_text
                connection.execute(
                    "CREATE TRIGGER tag_layout_revisions_no_update "
                    "BEFORE UPDATE ON tag_layout_revisions BEGIN "
                    "SELECT RAISE(ABORT, 'tag layout revisions are immutable'); END"
                )
                connection.execute("PRAGMA user_version=2")
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    @staticmethod
    def _document_columns(row: sqlite3.Row) -> Dict[str, str]:
        documents = {
            "layout": row["layout_json"],
            "pose_config": row["pose_config_json"],
            "floor_map": row["floor_map_json"],
            "part_map": row["part_map_json"],
        }
        hashes = {
            "layout": row["layout_sha256"],
            "pose_config": row["pose_config_sha256"],
            "floor_map": row["floor_map_sha256"],
            "part_map": row["part_map_sha256"],
        }
        for name, text in documents.items():
            if not isinstance(text, str) or _sha256_text(text) != hashes[name]:
                raise LayoutHistoryIntegrityError(
                    f"Stored {name.replace('_', ' ')} bytes do not match revision digest"
                )
        return documents

    def _bootstrap(self) -> None:
        if not self._configured_sources_available():
            return
        assert self.layout_path is not None
        assert self.pose_template_path is not None
        assert self.floor_map_path is not None
        assert self.part_map_path is not None
        layout_text, layout = _read_exact_json(self.layout_path, label="AprilTag layout")
        pose_text, _pose_template = _read_exact_json(
            self.pose_template_path, label="AprilTag pose template"
        )
        floor_text, _floor_map = _read_exact_json(self.floor_map_path, label="floor tag map")
        part_text, _part_map = _read_exact_json(self.part_map_path, label="hexapod tag map")
        captured = layout.get("captured")
        if not captured:
            raise LayoutHistoryError(
                "The initial AprilTag layout needs a captured date before it can become history"
            )
        effective_from = _time_text(captured, field="layout.captured")
        if _parse_time(effective_from) > self.clock().astimezone(timezone.utc):
            raise LayoutHistoryError("The initial layout captured date cannot be in the future")
        robot_id = str(layout.get("robot_id", "")).strip()
        if not robot_id:
            raise LayoutHistoryError("The initial AprilTag layout needs a robot_id")

        layout_hash = _sha256_text(layout_text)
        pose_hash = _sha256_text(pose_text)
        floor_hash = _sha256_text(floor_text)
        part_hash = _sha256_text(part_text)
        revision_id = f"baseline-{layout_hash[:24]}"
        activation_key = f"bootstrap:{revision_id}"
        request = {
            "revision_id": revision_id,
            "effective_from": effective_from,
            "activated_by": "system:bootstrap",
            "note": "Initial configured Robot Lab AprilTag layout",
        }
        request_hash = _sha256_bytes(_canonical_json_bytes(request))
        created_at = self.clock().astimezone(timezone.utc).isoformat()

        with self.store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            active = connection.execute(
                "SELECT revision_id FROM tag_layout_activations LIMIT 1"
            ).fetchone()
            if active is not None:
                connection.execute("COMMIT")
                return
            existing = connection.execute(
                "SELECT * FROM tag_layout_revisions WHERE id=?", (revision_id,)
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO tag_layout_revisions("
                    "id,robot_id,layout_sha256,pose_config_sha256,floor_map_sha256,"
                    "part_map_sha256,layout_json,pose_config_json,floor_map_json,"
                    "part_map_json,observed_at,created_at,created_by,source_kind,"
                    "source_experiment_id,parent_revision_id,baseline_sha256,"
                    "review_ready,changed_tag_ids_json"
                    ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        revision_id,
                        robot_id,
                        layout_hash,
                        pose_hash,
                        floor_hash,
                        part_hash,
                        layout_text,
                        pose_text,
                        floor_text,
                        part_text,
                        effective_from,
                        created_at,
                        "system:bootstrap",
                        "baseline",
                        None,
                        None,
                        None,
                        1,
                        "[]",
                    ),
                )
            else:
                documents = self._document_columns(existing)
                if (
                    existing["layout_sha256"] != layout_hash
                    or existing["robot_id"] != robot_id
                    or documents["layout"] != layout_text
                ):
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict("Existing baseline revision has different content")
            connection.execute(
                "INSERT INTO tag_layout_activations("
                "revision_id,effective_from,activated_at,activated_by,note,"
                "idempotency_key,request_sha256"
                ") VALUES(?,?,?,?,?,?,?)",
                (
                    revision_id,
                    effective_from,
                    created_at,
                    "system:bootstrap",
                    request["note"],
                    activation_key,
                    request_hash,
                ),
            )
            connection.execute("COMMIT")

    @staticmethod
    def _resolve_row(connection: sqlite3.Connection, at: str) -> Optional[sqlite3.Row]:
        return connection.execute(
            "SELECT r.*,a.effective_from,a.activated_at,a.activated_by,a.note "
            "FROM tag_layout_activations a "
            "JOIN tag_layout_revisions r ON r.id=a.revision_id "
            "WHERE a.effective_from<=? "
            "ORDER BY a.effective_from DESC,r.sequence DESC LIMIT 1",
            (at,),
        ).fetchone()

    @staticmethod
    def _next_effective(
        connection: sqlite3.Connection, effective_from: Optional[str]
    ) -> Optional[str]:
        if effective_from is None:
            return None
        row = connection.execute(
            "SELECT MIN(effective_from) AS value FROM tag_layout_activations "
            "WHERE effective_from>?",
            (effective_from,),
        ).fetchone()
        return row["value"] if row else None

    def _row_dict(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        *,
        include_documents: bool,
    ) -> Dict[str, Any]:
        effective_from = row["effective_from"] if "effective_from" in row.keys() else None
        if effective_from is None:
            activation = connection.execute(
                "SELECT effective_from,activated_at,activated_by,note "
                "FROM tag_layout_activations WHERE revision_id=?", (row["id"],)
            ).fetchone()
            effective_from = activation["effective_from"] if activation else None
            activated_at = activation["activated_at"] if activation else None
            activated_by = activation["activated_by"] if activation else None
            note = activation["note"] if activation else None
        else:
            activated_at = row["activated_at"]
            activated_by = row["activated_by"]
            note = row["note"]

        now_text = self.clock().astimezone(timezone.utc).isoformat()
        current_row = self._resolve_row(connection, now_text)
        current_id = current_row["id"] if current_row else None
        if effective_from is not None:
            status = "current" if row["id"] == current_id else "superseded"
        elif not bool(row["review_ready"]):
            status = "incomplete"
        elif row["parent_revision_id"] != current_id:
            status = "stale"
        else:
            status = "ready_for_review"

        effective_to = self._next_effective(connection, effective_from)
        value: Dict[str, Any] = {
            "sequence": int(row["sequence"]),
            "revision_number": int(row["sequence"]),
            "id": row["id"],
            "robot_id": row["robot_id"],
            "layout_sha256": row["layout_sha256"],
            "pose_config_sha256": row["pose_config_sha256"],
            "floor_map_sha256": row["floor_map_sha256"],
            "part_map_sha256": row["part_map_sha256"],
            "observed_at": row["observed_at"],
            "created_at": row["created_at"],
            "created_by": row["created_by"],
            "source_kind": row["source_kind"],
            "source_experiment_id": row["source_experiment_id"],
            "parent_revision_id": row["parent_revision_id"],
            "baseline_sha256": row["baseline_sha256"],
            "review_ready": bool(row["review_ready"]),
            "changed_tag_ids": json.loads(row["changed_tag_ids_json"]),
            "status": status,
            "active": effective_from is not None,
            "current": row["id"] == current_id,
            "effective_from": effective_from,
            "effective_to": effective_to,
            "effective_until": effective_to,
            "activated_at": activated_at,
            "activated_by": activated_by,
            "activation_note": note,
        }
        if include_documents:
            documents = self._document_columns(row)
            value.update(
                {
                    "layout": _object_from_text(documents["layout"], label="stored layout"),
                    "pose_config": _object_from_text(
                        documents["pose_config"], label="stored pose config"
                    ),
                    "floor_map": _object_from_text(
                        documents["floor_map"], label="stored floor map"
                    ),
                    "part_map": _object_from_text(
                        documents["part_map"], label="stored part map"
                    ),
                }
            )
        return value

    def _write_active(self, row: sqlite3.Row) -> None:
        documents = self._document_columns(row)
        revision_id = str(row["id"])
        if not revision_id or any(
            character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
            for character in revision_id
        ):
            raise LayoutHistoryIntegrityError("Stored revision ID is not path-safe")
        version_dir = self.revision_bundles_path / revision_id
        for name, filename in SNAPSHOT_FILES.items():
            _write_once(version_dir / filename, documents[name])
        pointer = {
            "schema_version": 1,
            "revision_id": revision_id,
            "layout_sha256": row["layout_sha256"],
            "pose_config_sha256": row["pose_config_sha256"],
            "floor_map_sha256": row["floor_map_sha256"],
            "part_map_sha256": row["part_map_sha256"],
        }
        _write_once(version_dir / "bundle.json", _pretty_json_text(pointer))

        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.root / f".active.{os.getpid()}.{id(row)}"
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(
            Path(self.revision_bundles_path.name) / revision_id,
            target_is_directory=True,
        )
        try:
            os.replace(temporary, self.active_bundle_path)
        finally:
            temporary.unlink(missing_ok=True)

    def _backfill_pins(self) -> Sequence[str]:
        pinned = []
        pinned_at = self.clock().astimezone(timezone.utc).isoformat()
        with self.store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT e.id,COALESCE(e.started_at,e.created_at) AS recorded_at,"
                "EXISTS(SELECT 1 FROM events v WHERE v.experiment_id=e.id "
                "AND v.kind='imported') AS is_imported "
                "FROM experiments e LEFT JOIN experiment_tag_layouts p "
                "ON p.experiment_id=e.id WHERE p.experiment_id IS NULL "
                "AND e.status<>'queued' "
                "ORDER BY e.created_at,e.id"
            ).fetchall()
            for experiment in rows:
                artifact_time = _recording_time_from_artifacts(
                    self.data_dir / "experiments" / experiment["id"]
                )
                if bool(experiment["is_imported"]) and artifact_time is None:
                    # Import/registration time is not evidence capture time.
                    # Leave the run explicitly unpinned rather than assigning
                    # today's layout to an old recording.
                    continue
                try:
                    recorded_at = _time_text(
                        artifact_time or experiment["recorded_at"],
                        field="experiment recorded_at",
                    )
                except LayoutHistoryError:
                    continue
                revision = self._resolve_row(connection, recorded_at)
                # In particular, never assign the first known configuration to
                # evidence that predates its effective time.
                if revision is None:
                    continue
                connection.execute(
                    "INSERT INTO experiment_tag_layouts("
                    "experiment_id,revision_id,recorded_at,pinned_at,pin_basis"
                    ") VALUES(?,?,?,?,?)",
                    (
                        experiment["id"],
                        revision["id"],
                        recorded_at,
                        pinned_at,
                        (
                            "legacy_backfill_camera_timestamp"
                            if artifact_time
                            else "legacy_backfill_by_recorded_time"
                        ),
                    ),
                )
                pinned.append(experiment["id"])
            connection.execute("COMMIT")
        return pinned

    def initialize(self) -> Sequence[str]:
        """Bootstrap history, repair active copies, and backfill safe old pins.

        The returned experiment IDs had evidence sidecars newly materialized and
        are therefore the manifests a caller should refresh.
        """

        self.root.mkdir(parents=True, exist_ok=True)
        self._repair_legacy_document_columns()
        with self.store.connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS value FROM tag_layout_activations"
            ).fetchone()["value"]
        if not count:
            self._bootstrap()

        at = self.clock().astimezone(timezone.utc).isoformat()
        with self.store.connect() as connection:
            current = self._resolve_row(connection, at)
            if current is None:
                return []
            self._write_active(current)
        newly_pinned = set(self._backfill_pins())

        with self.store.connect() as connection:
            pins = connection.execute(
                "SELECT experiment_id FROM experiment_tag_layouts ORDER BY experiment_id"
            ).fetchall()
        for pin in pins:
            experiment_id = pin["experiment_id"]
            run_dir = self.data_dir / "experiments" / experiment_id
            missing = any(
                not (run_dir / filename).is_file()
                for filename in (*SNAPSHOT_FILES.values(), CONTEXT_FILE)
            )
            self.materialize_experiment(run_dir, experiment_id)
            if missing:
                newly_pinned.add(experiment_id)
        return sorted(newly_pinned)

    def current(self) -> Optional[Dict[str, Any]]:
        return self.resolve(self.clock())

    def resolve(self, at: TimeValue) -> Optional[Dict[str, Any]]:
        at_text = _time_text(at, field="at")
        with self.store.connect() as connection:
            row = self._resolve_row(connection, at_text)
            if row is None:
                return None
            return self._row_dict(connection, row, include_documents=False)

    def list_revisions(self, limit: int = 100) -> Sequence[Dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        with self.store.connect() as connection:
            rows = connection.execute(
                "SELECT r.*,a.effective_from,a.activated_at,a.activated_by,a.note "
                "FROM tag_layout_revisions r LEFT JOIN tag_layout_activations a "
                "ON a.revision_id=r.id ORDER BY r.sequence DESC LIMIT ?", (limit,)
            ).fetchall()
            return [
                self._row_dict(connection, row, include_documents=False) for row in rows
            ]

    def get_revision(
        self, revision_id: str, *, include_documents: bool = True
    ) -> Dict[str, Any]:
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT r.*,a.effective_from,a.activated_at,a.activated_by,a.note "
                "FROM tag_layout_revisions r LEFT JOIN tag_layout_activations a "
                "ON a.revision_id=r.id WHERE r.id=?", (revision_id,)
            ).fetchone()
            if row is None:
                raise LayoutHistoryNotFound("AprilTag layout revision not found")
            return self._row_dict(
                connection, row, include_documents=include_documents
            )

    def baseline_for_scan(self) -> Dict[str, Any]:
        with self.store.connect() as connection:
            row = self._resolve_row(
                connection, self.clock().astimezone(timezone.utc).isoformat()
            )
            if row is None:
                raise LayoutHistoryUnavailable("No active AprilTag layout is available")
            documents = self._document_columns(row)
            return {
                "revision_id": row["id"],
                "layout_sha256": row["layout_sha256"],
                "canonical_json_sha256": row["layout_sha256"],
                "pose_config_sha256": row["pose_config_sha256"],
                "floor_map_sha256": row["floor_map_sha256"],
                "part_map_sha256": row["part_map_sha256"],
                "effective_from": row["effective_from"],
                "robot_id": row["robot_id"],
                "layout_text": documents["layout"],
                "pose_config_text": documents["pose_config"],
                "floor_map_text": documents["floor_map"],
                "part_map_text": documents["part_map"],
            }

    def experiment_revision(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        with self.store.connect() as connection:
            pin = connection.execute(
                "SELECT * FROM experiment_tag_layouts WHERE experiment_id=?",
                (experiment_id,),
            ).fetchone()
            if pin is None:
                return None
            row = connection.execute(
                "SELECT r.*,a.effective_from,a.activated_at,a.activated_by,a.note "
                "FROM tag_layout_revisions r LEFT JOIN tag_layout_activations a "
                "ON a.revision_id=r.id WHERE r.id=?", (pin["revision_id"],)
            ).fetchone()
            if row is None:
                raise LayoutHistoryIntegrityError(
                    "Experiment references a missing AprilTag revision"
                )
            result = self._row_dict(connection, row, include_documents=False)
            result.update(
                {
                    "experiment_id": experiment_id,
                    "recorded_at": pin["recorded_at"],
                    "pinned_at": pin["pinned_at"],
                    "pin_basis": pin["pin_basis"],
                }
            )
            return result

    def pin_experiment(
        self,
        experiment_id: str,
        recorded_at: Optional[TimeValue] = None,
        pin_basis: str = "recording_start",
        revision_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pin once, transactionally, and never reinterpret an existing pin.

        Supplying ``revision_id`` is intended for a tag scan which must retain
        the baseline chosen when the scan began even if a new revision becomes
        current before the scan is saved.
        """

        if not experiment_id or not pin_basis:
            raise LayoutHistoryError("experiment ID and pin basis are required")
        recorded_text = _time_text(
            recorded_at or self.clock(), field="recorded_at"
        )
        pinned_at = self.clock().astimezone(timezone.utc).isoformat()
        with self.store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT revision_id FROM experiment_tag_layouts WHERE experiment_id=?",
                (experiment_id,),
            ).fetchone()
            if existing is not None:
                connection.execute("COMMIT")
                result = self.experiment_revision(experiment_id)
                assert result is not None
                return result
            experiment = connection.execute(
                "SELECT id FROM experiments WHERE id=?", (experiment_id,)
            ).fetchone()
            if experiment is None:
                connection.execute("ROLLBACK")
                raise LayoutHistoryNotFound("Experiment not found")

            if revision_id is None:
                revision = self._resolve_row(connection, recorded_text)
                if revision is None:
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryUnavailable(
                        "No verified AprilTag layout covers this recording time"
                    )
            else:
                revision = connection.execute(
                    "SELECT r.* FROM tag_layout_revisions r "
                    "JOIN tag_layout_activations a ON a.revision_id=r.id "
                    "WHERE r.id=?", (revision_id,)
                ).fetchone()
                if revision is None:
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict(
                        "An experiment may only pin an activated AprilTag revision"
                    )
            try:
                connection.execute(
                    "INSERT INTO experiment_tag_layouts("
                    "experiment_id,revision_id,recorded_at,pinned_at,pin_basis"
                    ") VALUES(?,?,?,?,?)",
                    (
                        experiment_id,
                        revision["id"],
                        recorded_text,
                        pinned_at,
                        pin_basis,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                connection.execute("ROLLBACK")
                raise LayoutHistoryConflict("Could not pin AprilTag revision") from exc
            connection.execute("COMMIT")
        result = self.experiment_revision(experiment_id)
        assert result is not None
        return result

    def _revision_row_for_experiment(
        self, connection: sqlite3.Connection, experiment_id: str
    ) -> Tuple[sqlite3.Row, sqlite3.Row]:
        pin = connection.execute(
            "SELECT * FROM experiment_tag_layouts WHERE experiment_id=?",
            (experiment_id,),
        ).fetchone()
        if pin is None:
            raise LayoutHistoryNotFound("Experiment has no AprilTag layout pin")
        row = connection.execute(
            "SELECT r.*,a.effective_from,a.activated_at,a.activated_by,a.note "
            "FROM tag_layout_revisions r LEFT JOIN tag_layout_activations a "
            "ON a.revision_id=r.id WHERE r.id=?", (pin["revision_id"],)
        ).fetchone()
        if row is None:
            raise LayoutHistoryIntegrityError(
                "Experiment references a missing AprilTag revision"
            )
        return pin, row

    def materialize_experiment(
        self, run_dir: Path, experiment_id: str
    ) -> Dict[str, Any]:
        """Write exact, immutable replay inputs beside an experiment's video."""

        with self.store.connect() as connection:
            pin, row = self._revision_row_for_experiment(connection, experiment_id)
            documents = self._document_columns(row)
            effective_from = row["effective_from"]
            effective_to = self._next_effective(connection, effective_from)
            revision_number = int(row["sequence"])
            experiment = connection.execute(
                "SELECT duration_seconds FROM experiments WHERE id=?",
                (experiment_id,),
            ).fetchone()
            duration_seconds = float(experiment["duration_seconds"]) if experiment else 0.0

        recording_start = _parse_time(pin["recorded_at"])
        recording_end = recording_start + timedelta(seconds=duration_seconds)
        crosses_boundary = bool(
            effective_to
            and recording_start < _parse_time(effective_to) < recording_end
        )

        run_dir = Path(run_dir)
        for name, filename in SNAPSHOT_FILES.items():
            _write_once(run_dir / filename, documents[name])
        context = {
            "schema_version": 1,
            "kind": "hexapod_vision_context",
            "experiment_id": experiment_id,
            "recorded_at": pin["recorded_at"],
            "pinned_at": pin["pinned_at"],
            "pin_basis": pin["pin_basis"],
            "tag_layout_revision": {
                "id": row["id"],
                "revision_number": revision_number,
                "robot_id": row["robot_id"],
                "effective_from": effective_from,
                "effective_to_known_at_pin": effective_to,
                "observed_at": row["observed_at"],
                "source_kind": row["source_kind"],
                "source_experiment_id": row["source_experiment_id"],
                "parent_revision_id": row["parent_revision_id"],
            },
            "recording_interval": {
                "start": recording_start.isoformat(),
                "end": recording_end.isoformat(),
                "duration_seconds": duration_seconds,
                "crosses_known_revision_boundary": crosses_boundary,
            },
            "snapshots": {
                name: {
                    "filename": SNAPSHOT_FILES[name],
                    "sha256": {
                        "layout": row["layout_sha256"],
                        "pose_config": row["pose_config_sha256"],
                        "floor_map": row["floor_map_sha256"],
                        "part_map": row["part_map_sha256"],
                    }[name],
                }
                for name in SNAPSHOT_FILES
            },
        }
        _write_once(run_dir / CONTEXT_FILE, _pretty_json_text(context))
        return context

    def record_candidate(
        self,
        source_experiment_id: str,
        proposal: Mapping[str, Any],
        candidate_layout: JsonInput,
        created_by: str,
        *,
        observed_at: Optional[TimeValue] = None,
    ) -> Dict[str, Any]:
        """Store a phone proposal as an immutable, not-yet-active revision."""

        if not source_experiment_id or not created_by:
            raise LayoutHistoryError("source experiment and creator are required")
        baseline = proposal.get("baseline")
        if not isinstance(baseline, Mapping):
            raise LayoutHistoryConflict("Proposal does not identify its baseline revision")
        parent_id = baseline.get("revision_id") or baseline.get("id")
        baseline_hash = (
            baseline.get("layout_sha256")
            or baseline.get("canonical_json_sha256")
        )
        if not isinstance(parent_id, str) or not parent_id:
            raise LayoutHistoryConflict("Proposal does not identify its baseline revision")
        if not isinstance(baseline_hash, str) or not baseline_hash:
            raise LayoutHistoryConflict("Proposal does not include its exact baseline hash")

        _candidate_text, candidate = _json_input(
            candidate_layout, label="candidate AprilTag layout"
        )
        candidate.pop("proposal_metadata", None)
        candidate_text = _pretty_json_text(candidate)
        candidate_hash = _sha256_text(candidate_text)
        proposed_changes = sorted({int(value) for value in proposal.get("changed_tag_ids", [])})
        unresolved_fields = (
            "unresolved_tag_ids",
            "missing_tag_ids",
            "unexpected_tag_ids",
            "duplicate_tag_ids",
        )
        has_completion_evidence = all(
            field in proposal and isinstance(proposal.get(field), (list, tuple))
            for field in unresolved_fields
        )
        review_ready = (
            bool(proposal.get("ready_for_human_review"))
            and has_completion_evidence
            and not any(proposal.get(field) for field in unresolved_fields)
        )
        observed_value = (
            observed_at
            or proposal.get("observed_at")
            or proposal.get("created_at")
            or self.clock()
        )
        observed_text = _time_text(observed_value, field="observed_at")
        created_at = self.clock().astimezone(timezone.utc).isoformat()
        revision_id = str(proposal.get("scan_id") or source_experiment_id)
        if revision_id != source_experiment_id:
            raise LayoutHistoryConflict(
                "Proposal scan ID does not match its Robot Lab experiment ID"
            )

        with self.store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM tag_layout_revisions WHERE source_experiment_id=? OR id=?",
                (source_experiment_id, revision_id),
            ).fetchone()
            if existing is not None:
                if (
                    existing["source_experiment_id"] == source_experiment_id
                    and existing["id"] == revision_id
                    and existing["layout_sha256"] == candidate_hash
                    and existing["parent_revision_id"] == parent_id
                    and existing["baseline_sha256"] == baseline_hash
                    and existing["observed_at"] == observed_text
                    and bool(existing["review_ready"]) == review_ready
                    and json.loads(existing["changed_tag_ids_json"])
                    == proposed_changes
                ):
                    connection.execute("COMMIT")
                    return self.get_revision(revision_id)
                connection.execute("ROLLBACK")
                raise LayoutHistoryConflict(
                    "This scan already recorded a different immutable candidate"
                )

            parent = connection.execute(
                "SELECT * FROM tag_layout_revisions WHERE id=?", (parent_id,)
            ).fetchone()
            if parent is None:
                connection.execute("ROLLBACK")
                raise LayoutHistoryConflict("Proposal baseline revision does not exist")
            if parent["layout_sha256"] != baseline_hash:
                connection.execute("ROLLBACK")
                raise LayoutHistoryConflict("Proposal baseline hash does not match history")
            parent_documents = self._document_columns(parent)
            parent_layout = _object_from_text(
                parent_documents["layout"], label="baseline AprilTag layout"
            )
            actual_changes = sorted(_orientation_only_changes(parent_layout, candidate))
            if actual_changes != proposed_changes:
                connection.execute("ROLLBACK")
                raise LayoutHistoryConflict(
                    "Candidate changes do not match the proposal's changed tag IDs"
                )
            if str(candidate.get("robot_id", "")) != parent["robot_id"]:
                connection.execute("ROLLBACK")
                raise LayoutHistoryConflict("Candidate robot_id differs from its baseline")

            parent_pose = _object_from_text(
                parent_documents["pose_config"], label="baseline pose config"
            )
            pose_text = _pretty_json_text(
                _patch_pose_orientations(parent_pose, candidate, actual_changes)
            )
            try:
                connection.execute(
                    "INSERT INTO tag_layout_revisions("
                    "id,robot_id,layout_sha256,pose_config_sha256,floor_map_sha256,"
                    "part_map_sha256,layout_json,pose_config_json,floor_map_json,"
                    "part_map_json,observed_at,created_at,created_by,source_kind,"
                    "source_experiment_id,parent_revision_id,baseline_sha256,"
                    "review_ready,changed_tag_ids_json"
                    ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        revision_id,
                        parent["robot_id"],
                        candidate_hash,
                        _sha256_text(pose_text),
                        parent["floor_map_sha256"],
                        parent["part_map_sha256"],
                        candidate_text,
                        pose_text,
                        parent_documents["floor_map"],
                        parent_documents["part_map"],
                        observed_text,
                        created_at,
                        created_by,
                        "phone_scan",
                        source_experiment_id,
                        parent_id,
                        baseline_hash,
                        int(review_ready),
                        json.dumps(actual_changes, separators=(",", ":")),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                connection.execute("ROLLBACK")
                raise LayoutHistoryConflict("Could not record immutable scan candidate") from exc
            connection.execute("COMMIT")
        return self.get_revision(revision_id)

    def activate(
        self,
        revision_id: str,
        *,
        activated_by: str,
        expected_parent_revision_id: str,
        expected_layout_sha256: str,
        idempotency_key: str,
        effective_from: Optional[TimeValue] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Activate a ready candidate from approval time onward.

        Historical backdating is intentionally unsupported: doing it after a
        video has already been pinned would make timestamp lookup disagree with
        that video's immutable record.
        """

        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                revision_id,
                activated_by,
                expected_parent_revision_id,
                expected_layout_sha256,
                idempotency_key,
            )
        ):
            raise LayoutHistoryError(
                "revision, expected parent/hash, operator, and idempotency key are required"
            )
        if effective_from is not None:
            raise LayoutHistoryConflict(
                "Historical activation is not supported; revisions become effective at approval time"
            )

        with self.store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM tag_layout_revisions WHERE id=?", (revision_id,)
            ).fetchone()
            if row is None:
                connection.execute("ROLLBACK")
                raise LayoutHistoryNotFound("AprilTag layout revision not found")
            # Fail closed before appending an activation if any of the four
            # immutable documents has been damaged outside the application.
            self._document_columns(row)
            request = {
                "revision_id": revision_id,
                "activated_by": activated_by,
                "expected_parent_revision_id": expected_parent_revision_id,
                "expected_layout_sha256": expected_layout_sha256,
                "effective_from_basis": "activation_time",
                "note": note,
            }
            request_hash = _sha256_bytes(_canonical_json_bytes(request))
            prior_key = connection.execute(
                "SELECT revision_id,request_sha256 FROM tag_layout_activations "
                "WHERE idempotency_key=?", (idempotency_key,)
            ).fetchone()
            if prior_key is not None:
                if (
                    prior_key["revision_id"] == revision_id
                    and prior_key["request_sha256"] == request_hash
                ):
                    connection.execute("COMMIT")
                else:
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict(
                        "Idempotency key was already used for a different activation"
                    )
            else:
                if connection.execute(
                    "SELECT 1 FROM tag_layout_activations WHERE revision_id=?",
                    (revision_id,),
                ).fetchone():
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict("This revision is already active")
                if row["source_kind"] != "phone_scan" or not bool(row["review_ready"]):
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict(
                        "Only a complete reviewed phone scan can be activated"
                    )
                if row["parent_revision_id"] != expected_parent_revision_id:
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict(
                        "Activation expected the wrong baseline revision"
                    )
                if row["layout_sha256"] != expected_layout_sha256:
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict(
                        "Activation candidate hash does not match history"
                    )
                parent = connection.execute(
                    "SELECT layout_sha256 FROM tag_layout_revisions WHERE id=?",
                    (expected_parent_revision_id,),
                ).fetchone()
                if parent is None or parent["layout_sha256"] != row["baseline_sha256"]:
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict(
                        "Candidate baseline hash no longer validates"
                    )
                latest = connection.execute(
                    "SELECT revision_id,effective_from FROM tag_layout_activations "
                    "ORDER BY effective_from DESC LIMIT 1"
                ).fetchone()
                if latest is None or latest["revision_id"] != expected_parent_revision_id:
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict(
                        "Candidate is stale because another layout was activated first"
                    )
                running = connection.execute(
                    "SELECT id FROM experiments WHERE status='running' LIMIT 1"
                ).fetchone()
                if running is not None:
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict(
                        "Wait for the running experiment to finish before activating a layout"
                    )
                activated_at = self.clock().astimezone(timezone.utc).isoformat()
                if _parse_time(activated_at) <= _parse_time(latest["effective_from"]):
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict(
                        "Activation time must follow the current revision"
                    )
                try:
                    connection.execute(
                        "INSERT INTO tag_layout_activations("
                        "revision_id,effective_from,activated_at,activated_by,note,"
                        "idempotency_key,request_sha256"
                        ") VALUES(?,?,?,?,?,?,?)",
                        (
                            revision_id,
                            activated_at,
                            activated_at,
                            activated_by,
                            note,
                            idempotency_key,
                            request_hash,
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    connection.execute("ROLLBACK")
                    raise LayoutHistoryConflict(
                        "Could not append layout activation"
                    ) from exc
                connection.execute("COMMIT")

        with self.store.connect() as connection:
            activated = connection.execute(
                "SELECT * FROM tag_layout_revisions WHERE id=?", (revision_id,)
            ).fetchone()
            assert activated is not None
            self._write_active(activated)
        return self.get_revision(revision_id)


__all__ = [
    "CONTEXT_FILE",
    "SNAPSHOT_FILES",
    "LayoutHistoryConflict",
    "LayoutHistoryError",
    "LayoutHistoryIntegrityError",
    "LayoutHistoryNotFound",
    "LayoutHistoryUnavailable",
    "TagLayoutHistory",
]
