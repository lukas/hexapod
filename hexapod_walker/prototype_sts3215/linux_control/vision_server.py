"""Hexapod integration adapter for the extracted tracker web runtime."""

import json
import os
from pathlib import Path
import sys
import tempfile
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
DEFAULT_CONFIG = (
    Path(tempfile.gettempdir()) / "hexapod_vision_pose_config_current.json"
)
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


def materialize_default_config() -> Path:
    """Atomically write the deterministic merged config used by the service."""
    rendered = json.dumps(
        build_current_pose_config(), indent=2, sort_keys=True,
    ) + "\n"
    try:
        if DEFAULT_CONFIG.read_text() == rendered:
            return DEFAULT_CONFIG
    except FileNotFoundError:
        pass
    temporary = DEFAULT_CONFIG.with_name(
        f".{DEFAULT_CONFIG.name}.{os.getpid()}.tmp")
    temporary.write_text(rendered)
    temporary.replace(DEFAULT_CONFIG)
    return DEFAULT_CONFIG


class VisionRuntime(_TrackerVisionRuntime):
    """Tracker runtime wired to the main repo's guarded gait-survey adapter."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("survey_factory", GaitSurveyManager)
        super().__init__(*args, **kwargs)
