"""Hexapod integration adapter for the extracted tracker web runtime."""

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
TRACKER_ROOT = HERE.parent / "hexapod-tracker"
_TRACKER_SRC = TRACKER_ROOT / "src"
if str(_TRACKER_SRC) not in sys.path:
    sys.path.insert(0, str(_TRACKER_SRC))

from gait_survey import GaitSurveyManager  # noqa: E402
from hexapod_tracker.web_server import *  # noqa: E402,F403
from hexapod_tracker.web_server import VisionRuntime as _TrackerVisionRuntime  # noqa: E402


BASE_CONFIG = TRACKER_ROOT / "configs" / "apriltag_pose_config_20260831.json"
CURRENT_FLOOR_MAP = HERE / "floor_tag_map_20260903.json"
ROBOT_LAB_DATA_DIR = Path(os.environ.get(
    "HEXAPOD_DATA_DIR",
    Path.home() / "Library" / "Application Support" / "Hexapod Lab" / "data",
)).expanduser()
ROBOT_LAB_ACTIVE_BUNDLE = Path(os.environ.get(
    "HEXAPOD_TAG_LAYOUT_ACTIVE_BUNDLE",
    ROBOT_LAB_DATA_DIR / "tag-layout-history" / "active",
)).expanduser()
DEFAULT_CONFIG = Path(os.environ.get(
    "HEXAPOD_VISION_POSE_CONFIG",
    Path.home() / ".hexapod" / "vision_pose_config_current.json",
)).expanduser()
ACTIVE_POSE_CONFIG_NAME = "apriltag-pose-config.snapshot.json"
ACTIVE_FLOOR_MAP_NAME = "floor-tag-map.snapshot.json"
ACTIVE_BUNDLE_MANIFEST_NAME = "bundle.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_pose_sources(
        active_bundle_path: Path = ROBOT_LAB_ACTIVE_BUNDLE,
        base_config_path: Path = BASE_CONFIG,
        floor_map_path: Path = CURRENT_FLOOR_MAP,
) -> tuple[Path, Path, dict[str, Any]]:
    """Resolve one internally consistent active Robot Lab vision bundle."""
    active_bundle_path = Path(active_bundle_path)
    if not active_bundle_path.exists():
        return base_config_path, floor_map_path, {
            "kind": "repository_fallback",
            "pose_config_sha256": _sha256(base_config_path),
            "floor_map_sha256": _sha256(floor_map_path),
        }

    # Resolve the atomic `active` symlink once so an activation cannot mix
    # documents from two effective-dated revisions during service startup.
    bundle = active_bundle_path.resolve(strict=True)
    pose = bundle / ACTIVE_POSE_CONFIG_NAME
    floor = bundle / ACTIVE_FLOOR_MAP_NAME
    manifest_path = bundle / ACTIVE_BUNDLE_MANIFEST_NAME
    if not pose.is_file() or not floor.is_file() or not manifest_path.is_file():
        raise ValueError("active Robot Lab tag-layout bundle is incomplete")
    manifest = json.loads(manifest_path.read_text())
    pose_hash = _sha256(pose)
    floor_hash = _sha256(floor)
    if pose_hash != manifest.get("pose_config_sha256"):
        raise ValueError("active Robot Lab pose config does not match its digest")
    if floor_hash != manifest.get("floor_map_sha256"):
        raise ValueError("active Robot Lab floor map does not match its digest")
    return pose, floor, {
        "kind": "robot_lab_active_bundle",
        "revision_id": manifest.get("revision_id"),
        "pose_config_sha256": pose_hash,
        "floor_map_sha256": floor_hash,
    }
DEFAULT_UI_DIR = TRACKER_ROOT / "web" / "vision_ui" / "dist"
DEFAULT_REPORT_DIR = HERE / "artifacts" / "apriltag_pose" / "calibrations"


def build_current_pose_config(
        base_config_path: Path = BASE_CONFIG,
        floor_map_path: Path = CURRENT_FLOOR_MAP) -> dict[str, Any]:
    """Overlay the installed floor grid onto the tracker pose config.

    The tracker package intentionally owns camera and robot-tag calibration,
    while this robot checkout owns the measured floor grid.  Keeping the
    overlay here prevents the Mac vision service from silently reverting to
    the retired 12/13/15 anchors bundled with the tracker.
    """
    config = json.loads(base_config_path.read_text())
    floor_map = json.loads(floor_map_path.read_text())
    if floor_map.get("family") != config.get("tag_family"):
        raise ValueError("floor-map family does not match tracker tag family")
    if floor_map.get("units") != "millimeters":
        raise ValueError("floor-map units must be millimeters")
    marker_mm = float(floor_map["tag_black_square_size"])
    tags = floor_map.get("tags")
    if not isinstance(tags, list) or len(tags) < 2:
        raise ValueError("floor map must contain at least two anchors")
    floor_tags: dict[str, Any] = {}
    for item in tags:
        tag_id = int(item["id"])
        center_mm = [float(value) for value in item["center"]]
        if len(center_mm) != 3:
            raise ValueError(f"floor tag {tag_id} center must have 3 values")
        floor_tags[str(tag_id)] = {
            "label": f"floor anchor {tag_id}",
            "world_from_tag": {
                "translation_m": [value / 1000.0 for value in center_mm],
                "euler_xyz_deg": [0.0, 0.0, float(item["yaw_degrees"])],
            },
        }
    config["marker_size_m"] = marker_mm / 1000.0
    config["marker_size_verified"] = True
    config["floor_tags"] = floor_tags
    config["floor_map_source"] = floor_map_path.name
    return config


def _applied_visual_calibration_unix(config: dict[str, Any]) -> float:
    try:
        return float(config["visual_calibration"]["applied_unix"])
    except (KeyError, TypeError, ValueError):
        return float("-inf")


def _preserve_newer_live_visual_calibration(
        config: dict[str, Any], previous: dict[str, Any]) -> None:
    """Carry a locally applied visual-bias calibration across restarts."""
    if (_applied_visual_calibration_unix(previous)
            <= _applied_visual_calibration_unix(config)):
        return
    previous_pose = previous.get("robot_pose")
    if not isinstance(previous_pose, dict):
        raise ValueError("live vision config has no robot_pose object")
    previous_bias = previous_pose.get("visual_joint_bias_deg")
    if not isinstance(previous_bias, dict):
        raise ValueError("live vision config has no visual joint-bias map")
    config.setdefault("robot_pose", {})["visual_joint_bias_deg"] = (
        json.loads(json.dumps(previous_bias)))
    config["visual_calibration"] = json.loads(json.dumps(
        previous["visual_calibration"]))


def materialize_default_config(
        *, target_path: Path = DEFAULT_CONFIG,
        active_bundle_path: Path = ROBOT_LAB_ACTIVE_BUNDLE) -> Path:
    """Write the active effective-dated pose plus persistent live calibration."""
    base_config_path, floor_map_path, provenance = current_pose_sources(
        active_bundle_path=active_bundle_path)
    config = build_current_pose_config(base_config_path, floor_map_path)
    config["runtime_layout_source"] = provenance
    target_path = Path(target_path)
    try:
        previous = json.loads(target_path.read_text())
    except FileNotFoundError:
        previous = None
    if previous is not None:
        if not isinstance(previous, dict):
            raise ValueError("live vision config must contain a JSON object")
        _preserve_newer_live_visual_calibration(config, previous)
    rendered = json.dumps(config, indent=2, sort_keys=True) + "\n"
    if target_path.is_file() and target_path.read_text() == rendered:
        return target_path
    target_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = target_path.with_name(
        f".{target_path.name}.{os.getpid()}.tmp")
    temporary.write_text(rendered)
    temporary.chmod(0o600)
    temporary.replace(target_path)
    return target_path


class VisionRuntime(_TrackerVisionRuntime):
    """Tracker runtime wired to the main repo's guarded gait-survey adapter."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("survey_factory", GaitSurveyManager)
        super().__init__(*args, **kwargs)
