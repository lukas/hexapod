import argparse
import ast
import json
from pathlib import Path

import pytest

import rl_move.scripts.run_motionless_health_gate as runner_module
from rl_move.scripts.run_motionless_health_gate import GateRejected, run_gate


def _robot(*, armed=False, tripped=None, missing=None, ts=1):
    return {
        "armed": armed,
        "servo": {"ts": ts, "tripped": tripped or [], "missing": missing or []},
    }


def _feedback(timestamp, *, live=18, temperature=35, voltage=12, current=0.1):
    return {
        "ok": True,
        "t_unix": timestamp,
        "live": live,
        "joints": [
            {"temp_c": temperature, "volt": voltage, "cur_a": current}
            for _ in range(18)
        ],
    }


def _args(tmp_path):
    return argparse.Namespace(
        robot_url="http://robot.test:8080",
        vision_frame_url="http://camera.test/frame.jpg",
        output_dir=tmp_path / "evidence",
        samples=3,
        sample_interval_s=0,
        max_state_age_s=1.5,
        max_camera_age_s=2,
        max_temperature_c=55,
        min_voltage_v=10.8,
        max_voltage_v=13,
        max_joint_current_a=0.9,
        max_bus_current_a=5,
    )


def _getter(responses):
    values = iter(responses)

    def get(_url, *, timeout):
        del timeout
        value = next(values)
        if isinstance(value, tuple):
            return value
        return json.dumps(value).encode(), {}

    return get


def test_runner_collects_three_advancing_unarmed_samples(tmp_path):
    responses = []
    for stamp in (100.0, 100.5, 101.0):
        responses.extend([
            _robot(ts=stamp),
            _feedback(stamp),
            (b"jpeg", {"X-Capture-Unix-S": str(stamp)}),
        ])
    times = iter((100.0, 100.1, 100.6, 101.1, 101.2))

    result = run_gate(
        _args(tmp_path), getter=_getter(responses), clock=lambda: next(times),
        sleeper=lambda _seconds: None,
    )

    assert result["passed"] is True
    assert result["sample_count"] == 3
    assert result["robot_motion"] is False
    assert result["motor_commands_emitted"] is False
    assert [row["motor_id"] for row in result["samples"][0]["servos"]] == list(range(1, 19))
    assert len(list((tmp_path / "evidence").glob("camera_*.jpg"))) == 3


@pytest.mark.parametrize(
    "robot,feedback,error",
    [
        (_robot(armed=True), _feedback(100), "armed"),
        (_robot(missing=[7]), _feedback(100), "missing"),
        (_robot(tripped=[7]), _feedback(100), "tripped"),
        (_robot(), _feedback(100, live=17), "18/18"),
        (_robot(), _feedback(100, temperature=55), "temperature"),
        (_robot(), _feedback(100, voltage=10), "voltage"),
        (_robot(), _feedback(100, current=1), "current"),
    ],
)
def test_runner_fails_closed_before_accepting_bad_health(
    tmp_path, robot, feedback, error
):
    responses = [
        robot,
        feedback,
        (b"jpeg", {"X-Capture-Unix-S": "100"}),
    ]
    with pytest.raises(GateRejected, match=error):
        run_gate(
            _args(tmp_path), getter=_getter(responses), clock=lambda: 100.1,
            sleeper=lambda _seconds: None,
        )


def test_runner_rejects_nonadvancing_feedback_and_camera(tmp_path):
    responses = []
    for stamp, camera_stamp in ((100.0, 100.0), (100.0, 100.5)):
        responses.extend([
            _robot(ts=stamp), _feedback(stamp),
            (b"jpeg", {"X-Capture-Unix-S": str(camera_stamp)}),
        ])
    times = iter((100.0, 100.1, 100.6))
    with pytest.raises(GateRejected, match="feedback timestamp did not advance"):
        run_gate(
            _args(tmp_path), getter=_getter(responses), clock=lambda: next(times),
            sleeper=lambda _seconds: None,
        )


def test_runner_rejects_credentialed_or_parameterized_urls(tmp_path):
    args = _args(tmp_path)
    args.robot_url = "http://user:secret@robot.test:8080?cmd=bad"
    with pytest.raises(ValueError, match="credentials"):
        run_gate(args, getter=_getter([]), clock=lambda: 100, sleeper=lambda _: None)


def test_runner_source_has_no_robot_bus_or_http_post_path():
    source = Path(runner_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name.startswith(("feetech_bus", "serial", "subprocess")) for name in imported)
    assert 'method="GET"' in source
    assert 'method="POST"' not in source
    assert "/cmd" not in source
    assert "/api/arm" not in source
