"""Phone-photo capture and advisory AprilTag orientation proposals.

The Lab owns authenticated capture and durable evidence. Detection and
geometry remain in ``hexapod-tracker`` and are invoked through its read-only
``hexapod-audit-layout`` command. Nothing in this module can command the robot,
change a servo zero, or modify the canonical tracker checkout.
"""

from __future__ import annotations

from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import threading
import time
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence
import uuid


SCAN_ID_RE = re.compile(r"[0-9a-f]{32}")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
SIDE_LINK_AXIS_MIN_COSINE = 0.9
SIDE_VERTICAL_AXIS_MIN_COSINE = 0.55
AXIS_VECTORS = {
    "+x": (1.0, 0.0, 0.0),
    "-x": (-1.0, 0.0, 0.0),
    "+y": (0.0, 1.0, 0.0),
    "-y": (0.0, -1.0, 0.0),
    "+z": (0.0, 0.0, 1.0),
    "-z": (0.0, 0.0, -1.0),
}


class TagScanError(RuntimeError):
    """A safe, user-displayable scan failure."""


class TagScanNotFound(TagScanError):
    pass


class TagScanForbidden(TagScanError):
    pass


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _wrap_degrees(value: float) -> float:
    wrapped = (float(value) + 180.0) % 360.0 - 180.0
    return 180.0 if math.isclose(wrapped, -180.0) else wrapped


def _angle_difference(first: float, second: float) -> float:
    return _wrap_degrees(float(first) - float(second))


def _circular_median(values: Sequence[float], reference: float) -> float:
    unwrapped = [reference + _angle_difference(value, reference) for value in values]
    return _wrap_degrees(float(statistics.median(unwrapped)))


def _quaternion_xyzw_from_axes(axes: Mapping[str, str]) -> list[float]:
    """Convert readable tag axes (matrix columns) to a unit quaternion."""

    try:
        columns = [AXIS_VECTORS[str(axes[name])] for name in "xyz"]
    except KeyError as exc:
        raise TagScanError(f"invalid proposed tag axis {exc.args[0]!r}") from exc
    matrix = [[columns[column][row] for column in range(3)] for row in range(3)]
    determinant = (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )
    if not math.isclose(determinant, 1.0, abs_tol=1e-6):
        raise TagScanError("proposed tag axes do not form a right-handed rotation")

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
    norm = math.sqrt(sum(value * value for value in quaternion))
    quaternion = [value / norm for value in quaternion]
    if quaternion[3] < 0.0:
        quaternion = [-value for value in quaternion]
    return [round(value, 7) for value in quaternion]


def _orientation_samples(report: Mapping[str, Any]) -> dict[int, list[dict[str, Any]]]:
    samples: dict[int, list[dict[str, Any]]] = {}
    for key in ("horizontal_orientation_audit", "side_orientation_audit"):
        for item in (report.get(key) or {}).get("tags", []):
            tag_samples = [dict(sample) for sample in item.get("samples", [])]
            if key == "side_orientation_audit":
                # Mirror the tracker's own evidence thresholds. A low-angle
                # projection can suggest an axis while still being too weak to
                # support an orientation proposal.
                tag_samples = [
                    sample for sample in tag_samples
                    if float(sample.get("link_axis_cosine", 0.0))
                    >= SIDE_LINK_AXIS_MIN_COSINE
                    and float(sample.get("vertical_axis_cosine", 0.0))
                    >= SIDE_VERTICAL_AXIS_MIN_COSINE
                ]
            if tag_samples:
                samples.setdefault(int(item["id"]), []).extend(tag_samples)
    return samples


def _flatten_samples(
    frames: Iterable[Mapping[str, Any]], key: str
) -> dict[int, list[dict[str, Any]]]:
    combined: dict[int, list[dict[str, Any]]] = {}
    for frame in frames:
        for raw_id, samples in frame.get(key, {}).items():
            combined.setdefault(int(raw_id), []).extend(dict(item) for item in samples)
    return combined


def _public_summary(layout: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:
    robot_tags = {int(tag["id"]): tag for tag in layout["robot_tags"]}
    floor_ids = {int(tag["id"]) for tag in layout["floor"]["tags"]}
    frames = state.get("frames", [])
    detected = {
        int(tag_id) for frame in frames for tag_id in frame.get("detected_ids", [])
    }
    duplicates = sorted({
        int(tag_id) for frame in frames for tag_id in frame.get("duplicate_ids", [])
    })
    orientation = _flatten_samples(frames, "orientation_samples")
    floor_samples = _flatten_samples(frames, "floor_samples")
    robot_seen = sorted(set(robot_tags) & detected)
    robot_missing = sorted(set(robot_tags) - detected)
    measured = sorted(set(robot_tags) & set(orientation))
    orientation_missing = sorted(set(robot_tags) - set(orientation))
    second_look = sorted(
        tag_id for tag_id in measured if len(orientation[tag_id]) < 2
    )
    unexpected = sorted(detected - set(robot_tags) - floor_ids)

    horizontal_missing = [
        tag_id for tag_id in orientation_missing
        if robot_tags[tag_id].get("surface") == "horizontal"
    ]
    if duplicates:
        instruction = (
            "Duplicate tag ID visible: "
            + ", ".join(f"#{value}" for value in duplicates[:5])
            + ". Remove the duplicate or note which mount is wrong."
        )
    elif horizontal_missing:
        instruction = (
            "Go high for one overhead view: whole robot, every lid, and at "
            "least four floor cards."
        )
    elif orientation_missing:
        tag = robot_tags[orientation_missing[0]]
        side = f" {tag.get('mount_side')} face" if tag.get("mount_side") else ""
        instruction = (
            f"Move low to L{tag.get('leg')} {tag.get('joint')}{side}; keep "
            f"both lid tags on that leg in view with tag #{tag['id']}."
        )
    elif robot_missing:
        instruction = "Find the remaining robot tag" + (
            f" #{robot_missing[0]}." if len(robot_missing) == 1
            else "s: " + ", ".join(f"#{value}" for value in robot_missing[:5]) + "."
        )
    elif second_look:
        instruction = (
            "Everything is measured. Keep circling for a second view, or "
            "finish now to save a provisional record."
        )
    else:
        instruction = "Coverage complete. Finish and save the scan."

    return {
        "id": state["id"],
        "status": state["status"],
        "created_at": state["created_at"],
        "photo_count": len(frames),
        "attempt_count": int(state.get("attempt_count", 0)),
        "robot_tags": {
            "seen": len(robot_seen),
            "total": len(robot_tags),
            "missing_ids": robot_missing,
        },
        "orientations": {
            "measured": len(measured),
            "total": len(robot_tags),
            "missing_ids": orientation_missing,
            "second_view_needed_ids": second_look,
            "sample_counts": {
                str(tag_id): len(orientation.get(tag_id, []))
                for tag_id in sorted(robot_tags)
            },
        },
        "floor_reference": {
            "seen": len(floor_ids & detected),
            "total": len(floor_ids),
            "orientation_samples": len(floor_samples),
        },
        "unexpected_ids": unexpected,
        "duplicate_ids": duplicates,
        "ready_for_review": (
            not robot_missing and not orientation_missing
            and not unexpected and not duplicates
        ),
        "instruction": instruction,
        "last_capture": state.get("last_capture"),
        "experiment_id": state.get("experiment_id"),
        "baseline_revision_id": state.get("baseline_revision_id"),
        "baseline_effective_from": state.get("baseline_effective_from"),
    }


def _sanitize_audit_paths(report: dict[str, Any]) -> dict[str, Any]:
    cleaned = copy.deepcopy(report)
    for image in cleaned.get("images", []):
        if image.get("path"):
            image["path"] = Path(str(image["path"])).name
        if image.get("annotation"):
            image["annotation"] = Path(str(image["annotation"])).name
    return cleaned


def build_orientation_proposal(
    layout: Mapping[str, Any],
    report: Mapping[str, Any],
    *,
    scan_id: str,
    baseline_revision_id: Optional[str] = None,
    baseline_sha256: Optional[str] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create an advisory proposal and a non-canonical candidate layout."""

    tag_by_id = {int(tag["id"]): tag for tag in layout["robot_tags"]}
    duplicate_ids = sorted({
        int(tag_id)
        for image in report.get("images", [])
        for tag_id in image.get("duplicate_ids", [])
    })
    horizontal = {
        int(item["id"]): list(item.get("samples", []))
        for item in (report.get("horizontal_orientation_audit") or {}).get("tags", [])
    }
    side_items = {
        int(item["id"]): item
        for item in (report.get("side_orientation_audit") or {}).get("tags", [])
    }
    side = {
        tag_id: [
            sample for sample in item.get("samples", [])
            if float(sample.get("link_axis_cosine", 0.0))
            >= SIDE_LINK_AXIS_MIN_COSINE
            and float(sample.get("vertical_axis_cosine", 0.0))
            >= SIDE_VERTICAL_AXIS_MIN_COSINE
        ]
        for tag_id, item in side_items.items()
    }
    records: list[dict[str, Any]] = []
    updates: dict[int, dict[str, Any]] = {}

    for tag_id, tag in sorted(tag_by_id.items()):
        previous = copy.deepcopy(tag.get("frame_from_tag", {}))
        samples = horizontal.get(tag_id, []) if tag.get("surface") == "horizontal" else side.get(tag_id, [])
        record: dict[str, Any] = {
            "id": tag_id,
            "kind": tag.get("kind"),
            "frame": tag.get("frame"),
            "leg": tag.get("leg"),
            "joint": tag.get("joint"),
            "mount_side": tag.get("mount_side"),
            "sample_count": len(samples),
            "previous_frame_from_tag": previous,
        }
        if tag.get("surface") != "horizontal":
            raw_side_samples = list(side_items.get(tag_id, {}).get("samples", []))
            record["tracker_audit_status"] = side_items.get(tag_id, {}).get("status")
            record["rejected_weak_sample_count"] = len(raw_side_samples) - len(samples)
        if tag_id in duplicate_ids:
            record.update(status="duplicate_id", confidence="none")
            records.append(record)
            continue
        if not samples:
            record.update(status="unmeasured", confidence="none")
            records.append(record)
            continue

        if tag.get("surface") == "horizontal":
            values = [float(sample["measured_euler_z_deg"]) for sample in samples]
            previous_z = float(previous["euler_xyz_deg"][2])
            if tag.get("kind") == "chassis_tag":
                candidate_z = round(_circular_median(values, previous_z), 3)
                agreeing = sum(abs(_angle_difference(value, candidate_z)) <= 5.0 for value in values)
                changed = abs(_angle_difference(candidate_z, previous_z)) > 5.0
            else:
                normalized = [round(_wrap_degrees(value), 3) for value in values]
                candidate_z, agreeing = Counter(normalized).most_common(1)[0]
                changed = abs(_angle_difference(candidate_z, previous_z)) > 1e-6
            consistency = agreeing / len(values)
            proposed = copy.deepcopy(previous)
            euler = list(proposed.get("euler_xyz_deg", [0.0, 0.0, 0.0]))
            euler[2] = candidate_z
            proposed["euler_xyz_deg"] = euler
        else:
            choices = [
                tuple(str(sample["predicted_tag_axes_in_frame"][axis]) for axis in "xyz")
                for sample in samples
            ]
            candidate_axes, agreeing = Counter(choices).most_common(1)[0]
            consistency = agreeing / len(choices)
            readable = dict(zip("xyz", candidate_axes))
            proposed = copy.deepcopy(previous)
            proposed["tag_axes_in_frame"] = readable
            proposed["quaternion_xyzw"] = _quaternion_xyzw_from_axes(readable)
            changed = readable != previous.get("tag_axes_in_frame")

        conflict = consistency < (2.0 / 3.0)
        status = "conflict" if conflict else ("change" if changed else "unchanged")
        record.update(
            status=status,
            confidence=(
                "conflicting_views" if conflict else
                "single_view" if len(samples) == 1 else "consistent_views"
            ),
            consistency=round(consistency, 3),
            proposed_frame_from_tag=proposed,
            evidence_images=sorted({str(sample.get("image", "")) for sample in samples}),
        )
        if status == "change":
            updates[tag_id] = proposed
        records.append(record)

    missing_ids = sorted(int(value) for value in report.get("missing_ids", []) if int(value) in tag_by_id)
    unexpected_ids = sorted(int(value) for value in report.get("unexpected_ids", []))
    unresolved = [
        record["id"] for record in records
        if record["status"] in {"unmeasured", "conflict", "duplicate_id"}
    ]
    ready = not missing_ids and not unexpected_ids and not unresolved and not duplicate_ids
    changed = [record["id"] for record in records if record["status"] == "change"]
    proposal = {
        "schema_version": 1,
        "kind": "apriltag_orientation_proposal",
        "scan_id": scan_id,
        "created_at": _utcnow(),
        "baseline": {
            "name": layout.get("name"),
            "captured": layout.get("captured"),
            "revision_id": baseline_revision_id,
            "canonical_json_sha256": baseline_sha256 or hashlib.sha256(
                (json.dumps(layout, sort_keys=True) + "\n").encode("utf-8")
            ).hexdigest(),
        },
        "ready_for_human_review": ready,
        "safe_to_auto_apply": False,
        "changed_tag_ids": changed,
        "unresolved_tag_ids": unresolved,
        "missing_tag_ids": missing_ids,
        "unexpected_tag_ids": unexpected_ids,
        "duplicate_tag_ids": duplicate_ids,
        "orientations": records,
        "limitations": [
            "This proposal measures discrete orientation on each tag's currently recorded mount.",
            "A tag moved to another leg, joint, or face requires a human mount-assignment review.",
            "Robot-tag translations remain unmeasured and are not proposed.",
            "No servo zero, motor command, or canonical tracker file was changed.",
        ],
    }

    candidate = copy.deepcopy(layout)
    for tag in candidate["robot_tags"]:
        tag_id = int(tag["id"])
        if tag_id in updates:
            tag["frame_from_tag"] = updates[tag_id]
    candidate["proposal_metadata"] = {
        "advisory_only": True,
        "source_scan_id": scan_id,
        "created_at": proposal["created_at"],
        "changed_tag_ids": changed,
        "canonical_configuration_changed": False,
    }
    return proposal, candidate


def proposal_summary_markdown(
    proposal: Mapping[str, Any], summary: Mapping[str, Any]
) -> str:
    changed = list(proposal.get("changed_tag_ids", []))
    unresolved = list(proposal.get("unresolved_tag_ids", []))
    ready = bool(proposal.get("ready_for_human_review"))
    lines = [
        "# AprilTag orientation walk-around",
        "",
        f"- Robot tags found: **{summary['robot_tags']['seen']}/{summary['robot_tags']['total']}**",
        f"- Robot orientations measured: **{summary['orientations']['measured']}/{summary['orientations']['total']}**",
        f"- Useful phone photos retained: **{summary['photo_count']}**",
        f"- Review state: **{'ready for human review' if ready else 'incomplete'}**",
        f"- Proposed orientation changes: **{len(changed)}**",
        "",
        "## Proposed changes",
        "",
    ]
    lines.append(
        ", ".join(f"tag #{value}" for value in changed)
        if changed else "No orientation changes were proposed."
    )
    if unresolved:
        lines += ["", "## Still unresolved", "", ", ".join(f"tag #{value}" for value in unresolved)]
    lines += [
        "",
        "## Safety and scope",
        "",
        "This is an advisory, immutable Robot Lab record. It did not move the robot, "
        "change servo zeros, or modify the canonical tracker configuration. A tag "
        "that moved to another physical mount still needs a human assignment check.",
    ]
    return "\n".join(lines) + "\n"


class TagScanService:
    def __init__(
        self,
        data_dir: Path,
        *,
        audit_command: Sequence[str],
        layout_path: Optional[Path],
        floor_map_path: Optional[Path],
        part_map_path: Optional[Path],
        max_photo_bytes: int,
        max_photos: int,
        baseline_provider: Optional[Callable[[], Mapping[str, Any]]] = None,
    ) -> None:
        self.root = data_dir / "tag-scans"
        self.command = tuple(audit_command)
        self.layout_path = layout_path
        self.floor_map_path = floor_map_path
        self.part_map_path = part_map_path
        self.max_photo_bytes = int(max_photo_bytes)
        self.max_photos = int(max_photos)
        self.baseline_provider = baseline_provider
        self._lock = threading.RLock()

    @property
    def available(self) -> bool:
        return bool(
            self.command
            and self.layout_path and self.layout_path.is_file()
            and self.floor_map_path and self.floor_map_path.is_file()
            and self.part_map_path and self.part_map_path.is_file()
        )

    def _require_available(self) -> None:
        if not self.available:
            raise TagScanError("Tag scanning is not configured on this Robot Lab host")

    def _directory(self, scan_id: str) -> Path:
        if not SCAN_ID_RE.fullmatch(scan_id):
            raise TagScanNotFound("Tag scan not found")
        return self.root / scan_id

    def _state(self, scan_id: str, principal_name: str, role: str) -> tuple[Path, dict[str, Any]]:
        directory = self._directory(scan_id)
        path = directory / "scan.json"
        if not path.is_file():
            raise TagScanNotFound("Tag scan not found")
        state = _read_json(path)
        if state.get("created_by") != principal_name and role not in {"operator", "admin"}:
            raise TagScanForbidden("This scan belongs to another Robot Lab user")
        return directory, state

    @staticmethod
    def _snapshot_paths(directory: Path) -> tuple[Path, Path, Path]:
        return (
            directory / "baseline-apriltag-layout.json",
            directory / "baseline-floor-tag-map.json",
            directory / "baseline-hexapod-tag-map.json",
        )

    def _baseline(self) -> dict[str, Any]:
        if self.baseline_provider:
            baseline = dict(self.baseline_provider())
            required = {"layout_text", "floor_map_text", "part_map_text"}
            missing = sorted(required - baseline.keys())
            if missing:
                raise TagScanError(
                    "Tag layout history returned an incomplete baseline: "
                    + ", ".join(missing)
                )
            return baseline
        assert self.layout_path is not None
        assert self.floor_map_path is not None
        assert self.part_map_path is not None
        layout_text = self.layout_path.read_text(encoding="utf-8")
        return {
            "revision_id": None,
            "effective_from": None,
            "layout_text": layout_text,
            "layout_sha256": hashlib.sha256(layout_text.encode("utf-8")).hexdigest(),
            "pose_config_text": None,
            "floor_map_text": self.floor_map_path.read_text(encoding="utf-8"),
            "part_map_text": self.part_map_path.read_text(encoding="utf-8"),
        }

    @staticmethod
    def _scan_layout(directory: Path) -> dict[str, Any]:
        return _read_json(directory / "baseline-apriltag-layout.json")

    def create(self, principal_name: str) -> dict[str, Any]:
        self._require_available()
        with self._lock:
            baseline = self._baseline()
            layout = json.loads(str(baseline["layout_text"]))
            scan_id = uuid.uuid4().hex
            directory = self.root / scan_id
            directory.mkdir(parents=True, exist_ok=False)
            layout_path, floor_path, part_path = self._snapshot_paths(directory)
            layout_path.write_text(str(baseline["layout_text"]), encoding="utf-8")
            floor_path.write_text(str(baseline["floor_map_text"]), encoding="utf-8")
            part_path.write_text(str(baseline["part_map_text"]), encoding="utf-8")
            pose_text = baseline.get("pose_config_text")
            if pose_text is not None:
                (directory / "baseline-apriltag-pose-config.json").write_text(
                    str(pose_text), encoding="utf-8"
                )
            now = time.time()
            state: dict[str, Any] = {
                "id": scan_id,
                "status": "capturing",
                "created_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                "created_unix": now,
                "created_by": principal_name,
                "attempt_count": 0,
                "frames": [],
                "baseline_revision_id": baseline.get("revision_id"),
                "baseline_effective_from": baseline.get("effective_from"),
                "baseline_layout_sha256": baseline.get("layout_sha256"),
            }
            _write_json(directory / "scan.json", state)
            return _public_summary(layout, state)

    def get(self, scan_id: str, principal_name: str, role: str) -> dict[str, Any]:
        self._require_available()
        with self._lock:
            directory, state = self._state(scan_id, principal_name, role)
            return _public_summary(self._scan_layout(directory), state)

    def _run_audit(
        self,
        images: Sequence[Path],
        report_path: Path,
        output_dir: Path,
        layout_path: Path,
        floor_map_path: Path,
        part_map_path: Path,
    ) -> dict[str, Any]:
        command = [
            *self.command,
            "--layout", str(layout_path),
            "--floor-map", str(floor_map_path),
            "--part-map", str(part_map_path),
            "--output-dir", str(output_dir),
            "--report", str(report_path),
            *[str(path) for path in images],
        ]
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=90,
                check=False,
            )
        except FileNotFoundError as exc:
            raise TagScanError("The AprilTag audit tool is not installed") from exc
        except subprocess.TimeoutExpired as exc:
            raise TagScanError("AprilTag analysis timed out; try a closer photo") from exc
        if completed.returncode != 0 or not report_path.is_file():
            detail = (completed.stderr or "").strip().splitlines()
            suffix = f": {detail[-1]}" if detail else ""
            raise TagScanError(f"AprilTag analysis failed{suffix}")
        return _read_json(report_path)

    @staticmethod
    def _frame_record(
        report: Mapping[str, Any], filename: str, captured_at: str
    ) -> dict[str, Any]:
        image = report.get("images", [{}])[0]
        orientation = _orientation_samples(report)
        floor = {
            int(item["id"]): list(item.get("samples", []))
            for item in (report.get("floor_orientation_audit") or {}).get("tags", [])
            if item.get("samples")
        }
        return {
            "photo": filename,
            "captured_at": captured_at,
            "detected_ids": list(report.get("detected_ids", [])),
            "duplicate_ids": list(image.get("duplicate_ids", [])),
            "orientation_samples": {str(key): value for key, value in orientation.items()},
            "floor_samples": {str(key): value for key, value in floor.items()},
        }

    @staticmethod
    def _is_useful(
        before: Mapping[str, Any], after: Mapping[str, Any], frame: Mapping[str, Any]
    ) -> tuple[bool, str]:
        if not frame.get("detected_ids"):
            return False, "No AprilTags found—move closer and hold steady"
        before_seen = set(before["robot_tags"]["missing_ids"])
        after_seen = set(after["robot_tags"]["missing_ids"])
        if after_seen < before_seen:
            return True, "New tag found"
        before_missing = set(before["orientations"]["missing_ids"])
        after_missing = set(after["orientations"]["missing_ids"])
        if after_missing < before_missing:
            return True, "New orientation measured"
        before_second = set(before["orientations"]["second_view_needed_ids"])
        after_second = set(after["orientations"]["second_view_needed_ids"])
        if after_second < before_second:
            return True, "Second view added"
        before_counts = before["orientations"]["sample_counts"]
        after_counts = after["orientations"]["sample_counts"]
        if any(
            int(before_counts[tag_id]) < 3
            and int(after_counts[tag_id]) > int(before_counts[tag_id])
            for tag_id in before_counts
        ):
            return True, "Confirming view added"
        if set(after["unexpected_ids"]) > set(before["unexpected_ids"]):
            return True, "Unexpected tag recorded for review"
        if set(after["duplicate_ids"]) > set(before["duplicate_ids"]):
            return True, "Duplicate tag ID recorded for review"
        if after["floor_reference"]["orientation_samples"] > before["floor_reference"]["orientation_samples"]:
            return True, "Reference view added"
        return False, "Already covered—keep walking"

    def add_photo(
        self,
        scan_id: str,
        principal_name: str,
        role: str,
        content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        self._require_available()
        if content_type.split(";", 1)[0].lower() not in ALLOWED_IMAGE_TYPES:
            raise TagScanError("Upload a JPEG, PNG, or WebP image")
        if not content:
            raise TagScanError("The camera returned an empty image")
        if len(content) > self.max_photo_bytes:
            raise TagScanError("Photo is too large; use the live scanner or a smaller image")
        with self._lock:
            directory, state = self._state(scan_id, principal_name, role)
            layout_path, floor_path, part_path = self._snapshot_paths(directory)
            if state["status"] != "capturing":
                raise TagScanError("This tag scan is already finished")
            if len(state["frames"]) >= self.max_photos:
                raise TagScanError("Photo limit reached; finish this scan and review it")
            state["attempt_count"] = int(state.get("attempt_count", 0)) + 1
            sequence = state["attempt_count"]
            suffix = {"image/png": ".png", "image/webp": ".webp"}.get(
                content_type.split(";", 1)[0].lower(), ".jpg"
            )
            filename = f"capture-{sequence:03d}{suffix}"
            photo_path = directory / filename
            captured_at = _utcnow()
            temporary = directory / f".{filename}.{uuid.uuid4().hex}.upload"
            temporary.write_bytes(content)
            temporary.replace(photo_path)
            audit_path = directory / f"capture-{sequence:03d}-audit.json"
            annotated_dir = directory / "annotated"
            try:
                report = self._run_audit(
                    [photo_path], audit_path, annotated_dir,
                    layout_path, floor_path, part_path,
                )
            except Exception:
                photo_path.unlink(missing_ok=True)
                audit_path.unlink(missing_ok=True)
                raise
            frame = self._frame_record(report, filename, captured_at)
            layout = _read_json(layout_path)
            before = _public_summary(layout, state)
            candidate_state = copy.deepcopy(state)
            candidate_state["frames"].append(frame)
            after = _public_summary(layout, candidate_state)
            useful, message = self._is_useful(before, after, frame)
            annotation = annotated_dir / f"{photo_path.stem}-annotated.jpg"
            audit_path.unlink(missing_ok=True)
            if useful:
                state = candidate_state
            else:
                photo_path.unlink(missing_ok=True)
                annotation.unlink(missing_ok=True)
            state["last_capture"] = {
                "kept": useful,
                "message": message,
                "detected_ids": frame["detected_ids"],
            }
            _write_json(directory / "scan.json", state)
            return _public_summary(layout, state)

    def finalize(
        self, scan_id: str, principal_name: str, role: str
    ) -> dict[str, Any]:
        self._require_available()
        with self._lock:
            directory, state = self._state(scan_id, principal_name, role)
            layout_path, floor_path, part_path = self._snapshot_paths(directory)
            if state.get("experiment_id"):
                return {
                    "state": _public_summary(_read_json(layout_path), state),
                    "summary_markdown": (directory / "summary.md").read_text(encoding="utf-8"),
                    "duration_seconds": max(
                        0.001, float(state.get("finished_unix", time.time()))
                        - float(state["created_unix"]),
                    ),
                    "proposal": _read_json(directory / "tag-orientation-proposal.json"),
                    "candidate": _read_json(
                        directory / "proposed-hexapod-1-apriltag-layout.json"
                    ),
                }
            photos = [directory / frame["photo"] for frame in state.get("frames", [])]
            if not photos:
                raise TagScanError("Take at least one useful tag photo before finishing")
            audit_path = directory / "tag-orientation-audit.json"
            report = _sanitize_audit_paths(
                self._run_audit(
                    photos, audit_path, directory / "annotated",
                    layout_path, floor_path, part_path,
                )
            )
            _write_json(audit_path, report)
            layout = _read_json(layout_path)
            proposal, candidate = build_orientation_proposal(
                layout,
                report,
                scan_id=scan_id,
                baseline_revision_id=state.get("baseline_revision_id"),
                baseline_sha256=state.get("baseline_layout_sha256"),
            )
            proposal_path = directory / "tag-orientation-proposal.json"
            candidate_path = directory / "proposed-hexapod-1-apriltag-layout.json"
            _write_json(proposal_path, proposal)
            _write_json(candidate_path, candidate)
            state["status"] = "ready_for_review"
            state["finished_at"] = _utcnow()
            state["finished_unix"] = time.time()
            public = _public_summary(layout, state)
            summary_markdown = proposal_summary_markdown(proposal, public)
            (directory / "summary.md").write_text(summary_markdown, encoding="utf-8")
            _write_json(directory / "scan.json", state)
            return {
                "state": public,
                "summary_markdown": summary_markdown,
                "duration_seconds": max(
                    0.001, float(state["finished_unix"])
                    - float(state["created_unix"]),
                ),
                "proposal": proposal,
                "candidate": candidate,
            }

    def attach_to_experiment(
        self,
        scan_id: str,
        principal_name: str,
        role: str,
        experiment_id: str,
        run_dir: Path,
    ) -> dict[str, Any]:
        with self._lock:
            directory, state = self._state(scan_id, principal_name, role)
            proposal_path = directory / "tag-orientation-proposal.json"
            proposal = _read_json(proposal_path)
            proposal["robot_lab_experiment_id"] = experiment_id
            _write_json(proposal_path, proposal)
            saved_state = {
                **state,
                "experiment_id": experiment_id,
                "status": "saved",
            }
            _write_json(directory / "tag-scan-state.json", saved_state)
            for path in sorted(directory.iterdir()):
                if path.is_file() and path.name not in {"scan.json", "summary.md"}:
                    self._copy_evidence(path, run_dir / path.name)
            annotated = directory / "annotated"
            if annotated.is_dir():
                for path in sorted(annotated.glob("*-annotated.jpg")):
                    self._copy_evidence(path, run_dir / path.name)
            # Commit only after every artifact is present. A failed copy can
            # then be retried safely without claiming a partial result is saved.
            state = saved_state
            _write_json(directory / "scan.json", state)
            return _public_summary(self._scan_layout(directory), state)

    @staticmethod
    def _copy_evidence(source: Path, destination: Path) -> None:
        if destination.exists():
            if source.read_bytes() != destination.read_bytes():
                raise TagScanError(
                    f"Existing experiment artifact differs: {destination.name}"
                )
            return
        temporary = destination.with_name(
            f".{destination.name}.{uuid.uuid4().hex}.copy"
        )
        shutil.copy2(source, temporary)
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if source.read_bytes() != destination.read_bytes():
                raise TagScanError(
                    f"Existing experiment artifact differs: {destination.name}"
                )
        finally:
            temporary.unlink(missing_ok=True)
