import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hexapod_lab2.config import Settings  # noqa: E402
from hexapod_lab2.store import Store  # noqa: E402


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
    return Settings(data_dir=tmp_path / "data", checkout=checkout, idle_sleep_s=0)


@pytest.fixture
def store(settings):
    return Store(settings.db_path)
