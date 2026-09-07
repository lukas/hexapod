import json

from fastapi.testclient import TestClient
import pytest

from hexapod_lab.config import Settings
from hexapod_lab.main import create_app


def test_explicit_camera_configuration(monkeypatch):
    cameras = [
        {"id": f"robot-{i}", "name": f"Robot camera {i}",
         "device_uid": f"usb-{i}", "device_name": "Arducam"}
        for i in range(1, 5)
    ]
    monkeypatch.setenv("HEXAPOD_OBSERVATION_CAMERAS", json.dumps(cameras))
    assert Settings.from_env().observation_camera_devices == tuple(cameras)


@pytest.mark.parametrize("value", ['{}', 'null', '["camera"]'])
def test_camera_configuration_requires_objects(monkeypatch, value):
    monkeypatch.setenv("HEXAPOD_OBSERVATION_CAMERAS", value)
    with pytest.raises(ValueError):
        Settings.from_env()


def test_gallery_exposes_every_registered_camera_without_primary_alias(tmp_path, monkeypatch):
    specs = tuple({"id": f"robot-{i}", "name": f"Robot camera {i}",
                   "device_uid": f"usb-{i}", "device_name": "Arducam"}
                  for i in range(1, 5))
    settings = Settings(
        data_dir=tmp_path, api_keys="viewer:bob:read-only", driver="simulated",
        robot_command=(), camera_input="", bind="127.0.0.1", port=8767,
        public_base_url="", auto_worker=False, max_duration_seconds=2,
        observation_camera_devices=specs,
    )
    app = create_app(settings)
    service = app.state.observation_cameras
    snapshots = [dict(item, available=True, fresh=True,
                      frame_url=f"/api/robot-status/cameras/{item['id']}/frame")
                 for item in specs]
    monkeypatch.setattr(service, "start", lambda: None)
    monkeypatch.setattr(service, "stop", lambda: None)
    monkeypatch.setattr(service, "snapshots", lambda: snapshots)
    monkeypatch.setattr(app.state.robot_status, "_read_sources",
                        lambda: (({}, "unavailable"), ({}, "unavailable")))
    with TestClient(app) as client:
        auth = {"Authorization": "Bearer read-only"}
        status = client.get('/api/robot-status', headers=auth).json()
        assert status['cameras'] == snapshots
        assert len(status['cameras']) == 4
        assert status['observation_cameras'] == snapshots
        assert status['camera']['fresh'] is False
        assert status['readiness']['guarded_runner_ready'] is False
        assert client.get('/api/robot-status/cameras', headers=auth).json()['cameras'] == snapshots
        assert client.get('/api/robot-status/cameras').status_code == 401


@pytest.mark.parametrize('parameters,blocked', [
    ({'robot_motion': True}, True),
    ({'robot_motion': False}, False),
    ({'simulation_only': True}, False),
    ({'simulation_only': True, 'robot_motion': True}, True),
    ({}, True),
    (None, True),
])
def test_camera_previews_yield_to_hardware_engineering_owner(tmp_path, monkeypatch, parameters, blocked):
    from contextlib import contextmanager
    from datetime import datetime, timedelta, timezone
    import sqlite3

    settings = Settings(
        data_dir=tmp_path, api_keys='viewer:bob:read-only', driver='simulated',
        robot_command=(), camera_input='', bind='127.0.0.1', port=8767,
        public_base_url='', auto_worker=False, max_duration_seconds=2,
        observation_camera_devices=({'id': 'robot-1', 'device_uid': 'usb-1'},),
    )
    app = create_app(settings)
    allowed = app.state.observation_cameras._cameras['robot-1'].capture_allowed
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript('''
        CREATE TABLE codex_hardware_lane (lease_expires_at TEXT);
        CREATE TABLE experiments (execution_mode TEXT, status TEXT);
        CREATE TABLE codex_engineering_jobs (
            source_context_json TEXT, status TEXT, lease_expires_at TEXT);
    ''')

    @contextmanager
    def connect():
        yield connection

    monkeypatch.setattr(app.state.store, 'connect', connect)
    try:
        assert allowed()
        future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        source = json.dumps({'experiment': {'parameters': parameters}})
        connection.execute('INSERT INTO codex_engineering_jobs VALUES (?,?,?)',
                           (source, 'running', future))
        assert allowed() is (not blocked)
        connection.execute('UPDATE codex_engineering_jobs SET lease_expires_at=?', (past,))
        assert allowed()
        connection.execute('INSERT INTO codex_hardware_lane VALUES (?)', (future,))
        assert not allowed()
        connection.execute('DELETE FROM codex_hardware_lane')
        connection.execute("INSERT INTO experiments VALUES ('builtin','running')")
        assert not allowed()
    finally:
        connection.close()


def test_paused_collection_keeps_existing_vision_preview_without_new_capture(monkeypatch):
    from types import SimpleNamespace
    from hexapod_lab.robot_status import RobotStatusService

    cameras = [{'id': 'robot-1', 'available': False, 'fresh': False, 'status': 'paused'}]
    service = RobotStatusService(observation_cameras=SimpleNamespace(
        has_robot_cameras=True, snapshots=lambda: cameras,
    ), cache_seconds=0)
    vision = {'ok': True, 'camera': {'enabled': True, 'status': 'running'},
              'performance': {'frame_age_ms': 50}}
    monkeypatch.setattr(service, '_read_sources', lambda: (({}, 'unavailable'), (vision, None)))
    gallery = service.snapshot()['cameras']
    assert gallery[-1]['id'] == 'selected-vision'
    assert gallery[-1]['frame_url'] == '/api/robot-status/frame'
    assert len(gallery) == 2
    cameras[0]['status'] = 'in_use'
    cameras.append({'id': 'robot-2', 'available': True, 'fresh': True, 'status': 'streaming'})
    assert service.snapshot()['cameras'][-1]['id'] == 'selected-vision'
    vision['performance']['frame_age_ms'] = 3000
    assert service.snapshot()['cameras'] == cameras
