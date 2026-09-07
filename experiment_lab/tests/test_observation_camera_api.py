from dataclasses import replace

from fastapi.testclient import TestClient
import pytest

from hexapod_lab.config import Settings
from hexapod_lab.main import create_app
from hexapod_lab.robot_status import RobotStatusService


def settings(tmp_path):
    return Settings(
        data_dir=tmp_path, api_keys="viewer:bob:read-only", driver="simulated",
        robot_command=(), camera_input="", bind="127.0.0.1", port=8767,
        public_base_url="", auto_worker=False, max_duration_seconds=2,
    )


def test_observation_frames_require_auth_and_never_start_capture_on_read(tmp_path, monkeypatch):
    app = create_app(settings(tmp_path))
    cameras = app.state.observation_cameras
    calls = []
    monkeypatch.setattr(cameras, "start", lambda: calls.append("start"))
    monkeypatch.setattr(cameras, "stop", lambda: calls.append("stop"))
    monkeypatch.setattr(cameras, "snapshots", lambda: [{
        "id": "iphone", "name": "iPhone", "fresh": True,
        "frame_url": "/api/robot-status/cameras/iphone/frame",
    }])
    monkeypatch.setattr(cameras, "frame", lambda camera_id: b"\xff\xd8frame\xff\xd9")
    auth = {"Authorization": "Bearer read-only"}
    with TestClient(app) as client:
        assert calls == ["start"]
        for path in ("/api/robot-status/cameras", "/api/robot-status/cameras/iphone/frame"):
            assert client.get(path).status_code == 401
            response = client.get(path, headers=auth)
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
        assert response.headers["content-type"] == "image/jpeg"
        assert response.content == b"\xff\xd8frame\xff\xd9"
        assert calls == ["start"]
    assert calls == ["start", "stop"]


@pytest.mark.parametrize("error,status", [(KeyError("unknown"), 404), (ValueError("stale"), 503)])
def test_unknown_or_stale_camera_never_returns_image(tmp_path, monkeypatch, error, status):
    app = create_app(settings(tmp_path))
    def fail(camera_id):
        raise error
    monkeypatch.setattr(app.state.observation_cameras, "frame", fail)
    with TestClient(app) as client:
        response = client.get("/api/robot-status/cameras/iphone/frame",
                              headers={"Authorization": "Bearer read-only"})
    assert response.status_code == status
    assert response.headers["content-type"] == "application/json"


def test_observation_camera_is_opt_in_and_reads_exact_name(tmp_path, monkeypatch):
    monkeypatch.delenv("HEXAPOD_OBSERVATION_CAMERA_NAME", raising=False)
    assert Settings.from_env().observation_camera_name == ""
    monkeypatch.setenv("HEXAPOD_OBSERVATION_CAMERA_NAME", "lukas's iPhone Camera")
    assert Settings.from_env().observation_camera_name == "lukas's iPhone Camera"
    app = create_app(replace(settings(tmp_path), observation_camera_name=""))
    assert app.state.observation_cameras.snapshots() == []


def test_extra_camera_is_visible_to_status_consumers_without_changing_readiness(monkeypatch):
    class Cameras:
        def snapshots(self):
            return [{"id": "iphone", "fresh": True}]
    service = RobotStatusService(cache_seconds=0, observation_cameras=Cameras())
    monkeypatch.setattr(service, "_read_sources", lambda: (({}, "unavailable"), ({}, "unavailable")))
    status = service.snapshot()
    assert status["observation_cameras"] == [{"id": "iphone", "fresh": True}]
    assert status["camera"]["fresh"] is False
    assert status["readiness"]["guarded_runner_ready"] is False
