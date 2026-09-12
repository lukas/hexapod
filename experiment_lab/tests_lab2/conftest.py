import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hexapod_lab2 import eyes  # noqa: E402
from hexapod_lab2.config import Settings  # noqa: E402
from hexapod_lab2.store import Store  # noqa: E402

REAL_READY_TO_MOVE = eyes.ready_to_move


@pytest.fixture
def settings(tmp_path):
    checkout = tmp_path / "checkout"
    protos = checkout / "hexapod_walker" / "prototype_sts3215" / "sysid" / "protocols"
    protos.mkdir(parents=True)
    (protos / "steps_air_v1.json").write_text(json.dumps(
        {"name": "steps_air_v1", "description": "leg in the air", "segments": [{"kind": "step"}]}))
    (protos / "champion_stand_ground_v1.json").write_text(json.dumps(
        {"name": "champion_stand_ground_v1", "description": "stand",
         "segments": [{"kind": "traj", "q_deg": [], "t_s": []}]}))
    (protos / "steps_air_L5_v1.json").write_text(json.dumps(
        {"name": "steps_air_L5_v1", "description": "Step ladders. Robot on stand, feet OFF the ground.",
         "segments": [{"kind": "step"}]}))
    # Never touch the live camera or the paid eyes from a test.
    return Settings(data_dir=tmp_path / "data", checkout=checkout, idle_sleep_s=0,
                    wide_frame_url="http://127.0.0.1:9/none.jpg")


@pytest.fixture(autouse=True)
def _no_paid_calls(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # The pre-run look says yes unless a test is about the look itself.
    monkeypatch.setattr(eyes, "ready_to_move", lambda settings, **k: (True, "YES robot on the floor, legs in place", 0.0))
    # No tracker subprocess from a test: the camera half of the zero check is blind
    # unless a test replaces it.
    from hexapod_lab2 import zero_check
    monkeypatch.setattr(zero_check, "camera", lambda settings, out_dir, **k: {"ok": False, "error": "no camera in tests"})


@pytest.fixture
def store(settings):
    return Store(settings.db_path)
