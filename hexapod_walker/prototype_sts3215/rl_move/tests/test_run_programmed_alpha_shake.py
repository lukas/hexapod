from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from rl_move.scripts import run_programmed_alpha_shake as runner
from rl_move.scripts.run_programmed_alpha_shake import (
    CONDITIONS,
    _selected_conditions,
)


def test_selected_conditions_defaults_to_proven_four_cell_order() -> None:
    assert _selected_conditions(None) == CONDITIONS


def test_selected_conditions_preserves_requested_bounded_subset_order() -> None:
    selected = _selected_conditions(["low_alpha_40", "high_alpha_40"])

    assert [condition["name"] for condition in selected] == [
        "low_alpha_40",
        "high_alpha_40",
    ]
    assert [condition["vx_mm_s"] for condition in selected] == [40.0, 40.0]


def test_selected_conditions_rejects_duplicate_walking_cells() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        _selected_conditions(["low_alpha_40", "low_alpha_40"])


@pytest.mark.parametrize("camera_failure", [None, "missing final video frame", "stop raises"])
def test_result_waits_for_recorder_finalization(tmp_path, monkeypatch, camera_failure):
    class Trial:
        def __init__(self, _args, output_dir):
            self.output_dir = output_dir
            self.communication_capture = {"errors": []}
            self.motion_started = False
            self.completed = False
            self.recorder = SimpleNamespace(
                frames=3, error=None, OUTPUT_FPS=30,
                start=lambda: None, stop=self.stop_recorder,
            )

        def stop_recorder(self):
            if camera_failure == "stop raises":
                raise RuntimeError(camera_failure)
            self.recorder.error = camera_failure

        def planned_lower(self):
            self.completed = True
            self.motion_started = False

        def event(self, *_args):
            pass

        start_communication_capture = collect_communication_capture = lambda self: None
        communication_mark = snapshot = lambda self, *_args: None
        close = lambda self: None

    monkeypatch.setattr(runner, "Trial", Trial)
    monkeypatch.setattr(runner, "_verified_zero", lambda *_: None)
    monkeypatch.setattr(runner, "_stand", lambda trial: setattr(trial, "motion_started", True))
    monkeypatch.setattr(runner, "_run_condition", lambda *_: None)
    monkeypatch.setattr(runner.signal, "signal", lambda *_: None)
    monkeypatch.setattr("sys.argv", ["runner", "--output-dir", str(tmp_path)])

    exit_code = runner.main()
    result = json.loads(next(tmp_path.glob("*/run_summary.json")).read_text())

    assert exit_code == (1 if camera_failure else 0)
    assert result["ok"] is (camera_failure is None)
    assert result["completed"] is True
    assert result["motion_started"] is True
    assert result["camera_error"] == camera_failure
    if camera_failure:
        assert camera_failure in result["error"]
