"""Hexapod integration adapter for the extracted tracker web runtime."""

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


DEFAULT_CONFIG = TRACKER_ROOT / "configs" / "apriltag_pose_config_20260831.json"
DEFAULT_UI_DIR = TRACKER_ROOT / "web" / "vision_ui" / "dist"
DEFAULT_REPORT_DIR = HERE / "artifacts" / "apriltag_pose" / "calibrations"


class VisionRuntime(_TrackerVisionRuntime):
    """Tracker runtime wired to the main repo's guarded gait-survey adapter."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("survey_factory", GaitSurveyManager)
        super().__init__(*args, **kwargs)
