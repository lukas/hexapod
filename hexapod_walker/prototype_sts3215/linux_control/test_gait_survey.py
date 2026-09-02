"""Off-robot validation checks for the Vision UI gait-survey launcher."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gait_survey import GaitSurveyManager


class _Vision:
    def public_state(self) -> dict:
        return {
            "camera": {"enabled": True, "status": "running", "active_index": 1},
            "coverage": {"robot_tag_ids": [0], "floor_tags": 2},
            "pose": {"safety": {"verdict": "safe"}},
        }


def test_survey_config_requires_explicit_motion_acknowledgement():
    with pytest.raises(ValueError, match="acknowledgement"):
        GaitSurveyManager._validated_config({"gaits": [1, 11]})


def test_survey_config_is_bounded_and_deduplicated():
    config = GaitSurveyManager._validated_config({
        "acknowledge_motion": True,
        "gaits": [11, 1, 11],
        "speed_mm_s": 30,
        "direction_s": 8,
        "max_recoveries": 2,
    })
    assert config["gaits"] == [11, 1]
    assert config["adaptive_centering"] is True
    assert config["soft_recovery"] is True

    no_retry = GaitSurveyManager._validated_config({
        "acknowledge_motion": True,
        "gaits": [1],
        "max_recoveries": 0,
    })
    assert no_retry["soft_recovery"] is False


def test_survey_preflight_requires_robot_and_direct_vision(tmp_path):
    manager = GaitSurveyManager(
        robot_url="http://robot.invalid:8080",
        vision_runtime=_Vision(),
        output_root=tmp_path,
    )
    camera, state = manager._preflight()
    assert camera == 1
    assert state["pose"]["safety"]["verdict"] == "safe"
