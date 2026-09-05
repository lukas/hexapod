"""Passive status must distinguish fresh evidence from a successful HTTP poll."""

from copy import deepcopy
import threading

from fastapi.testclient import TestClient
import pytest

from hexapod_lab import robot_status
from hexapod_lab.config import Settings
from hexapod_lab.main import create_app
from hexapod_lab.robot_status import RobotStatusService


ROBOT_URL = "http://robot.test:8080/api/robot"
VISION_URL = "http://vision.test:8898/api/vision/state"
DEFAULT_ROBOT_URL = "http://hexapod.local:8080/api/robot"
HUB_URL = "http://vision.test:8898/api/hub"


def hub_reading(target_url="http://192.168.4.39:8080"):
    return {
        "service": "hexapod-hub",
        "targets": {
            "robot": {
                "available": True,
                "ok": True,
                "service": "hexapod-web",
                "url": target_url,
            },
            "sim": {"available": True, "ok": True, "service": "hexapod-sim"},
        },
    }


def robot_reading(timestamp):
    return {
        "activity": "limp",
        "detail": "idle",
        "armed": False,
        "mode": "idle",
        "dry_run": False,
        "drive_status": "idle",
        "demo": {"running": False, "status": "idle"},
        "servo": {
            "ok": True,
            "ts": timestamp,
            "expected": 18,
            "live": 18,
            "missing": [],
            "missing_names": [],
            "max_temp_c": 32,
            "hot": [],
            "tripped": [],
            "tripped_names": [],
            "warn_c": 55,
            "imu_ok": True,
        },
    }


class StatusHarness:
    def __init__(self, monkeypatch, **options):
        self.now = 1_800_000_000.0
        self.robot = robot_reading(self.now - 0.25)
        self.vision = {
            "ok": True,
            "camera": {"enabled": True, "status": "running"},
            "performance": {"frame_age_ms": 50},
            "pose": {"safety": {"safe_pose": True}},
        }
        self.calls = []
        self.service = RobotStatusService(
            robot_url=ROBOT_URL,
            vision_url=VISION_URL,
            cache_seconds=options.get("cache_seconds", 0),
        )
        monkeypatch.setattr(self.service, "_now", lambda: self.now)
        monkeypatch.setattr(self.service, "_fetch_json", self.fetch)

    def fetch(self, url):
        self.calls.append(url)
        assert url in {ROBOT_URL, VISION_URL}, "Status must only read the two passive endpoints"
        payload = self.robot if url == ROBOT_URL else self.vision
        if isinstance(payload, Exception):
            raise payload
        return deepcopy(payload)

    def snapshot(self, **kwargs):
        return self.service.snapshot(**kwargs)

    def advance(self, seconds=5):
        self.now += seconds
        self.robot["servo"]["ts"] = self.now - 0.25
        return self.snapshot()

    def confirm_healthy(self):
        self.snapshot()
        self.advance()
        result = self.advance()
        assert result["health"]["state"] == "healthy"
        assert result["health"]["healthy_samples"] == 3
        return result


@pytest.fixture
def status(monkeypatch):
    return StatusHarness(monkeypatch)


def test_health_requires_three_distinct_fresh_readings(status):
    first = status.snapshot()
    assert first["health"]["state"] == "checking"
    assert first["health"]["healthy_samples"] == 1
    for _ in range(4):
        repeated = status.snapshot()
        assert repeated["health"]["state"] == "checking"
        assert repeated["health"]["healthy_samples"] == 1
    second = status.advance()
    assert second["health"]["state"] == "checking"
    assert second["health"]["healthy_samples"] == 2
    third = status.advance()
    assert third["health"]["state"] == "healthy"
    assert third["health"]["healthy_samples"] == 3
    assert third["health"]["live_motors"] == 18
    assert third["health"]["expected_motors"] == 18
    assert third["readiness"]["can_start_from_website"] is False
    assert set(status.calls) == {ROBOT_URL, VISION_URL}


@pytest.mark.parametrize("offset", [-31, 3, float("nan"), float("inf")])
def test_old_future_or_invalid_feedback_time_never_becomes_healthy(status, offset):
    status.robot["servo"]["ts"] = status.now + offset
    for _ in range(4):
        result = status.snapshot()
        assert result["health"]["state"] != "healthy"
        assert result["health"]["healthy_samples"] == 0
        assert result["health"]["fresh"] is False


def test_feedback_aging_resets_confirmation_even_when_fetch_keeps_succeeding(status):
    status.confirm_healthy()
    status.now += 31
    stale = status.snapshot()
    assert stale["health"]["fresh"] is False
    assert stale["health"]["state"] != "healthy"
    assert stale["health"]["healthy_samples"] == 0
    recovered = status.advance()
    assert recovered["health"]["state"] == "checking"
    assert recovered["health"]["healthy_samples"] == 1


@pytest.mark.parametrize("flag,value", [("dry_run", True), ("dry_run", None), ("sim", True), ("simulated", True)])
def test_simulation_or_unspecified_hardware_identity_never_becomes_healthy(status, flag, value):
    status.robot[flag] = value
    status.snapshot()
    status.advance()
    result = status.advance()
    assert result["health"]["state"] != "healthy"
    assert result["health"]["healthy_samples"] == 0
    assert result["readiness"]["state"] == "needs_review"


@pytest.mark.parametrize("payload", [None, [], {}, {"servo": None}])
def test_malformed_robot_payload_is_unknown_not_healthy(status, payload):
    status.robot = payload
    result = status.snapshot()
    assert result["health"]["state"] != "healthy"
    assert result["health"]["healthy_samples"] == 0
    assert result["readiness"]["state"] == "needs_review"


@pytest.mark.parametrize(
    "field,value",
    [("ok", False), ("max_temp_c", None), ("max_temp_c", float("nan")),
     ("expected", 0), ("live", 19), ("missing", None)],
)
def test_incomplete_or_invalid_servo_health_cannot_confirm_ready(status, field, value):
    status.robot["servo"][field] = value
    status.snapshot()
    status.advance()
    result = status.advance()
    assert result["health"]["state"] != "healthy"
    assert result["health"]["healthy_samples"] == 0


def test_one_missing_sample_is_unconfirmed_and_does_not_count_repeated_fetches(status):
    status.confirm_healthy()
    status.robot["servo"].update(live=17, missing=[3], missing_names=["L1 yaw"])
    first_miss = status.advance()
    assert first_miss["health"]["state"] == "checking"
    assert first_miss["health"]["healthy_samples"] == 0
    for _ in range(4):
        assert status.snapshot()["health"]["state"] == "checking"
    assert status.advance()["health"]["state"] == "checking"
    confirmed = status.advance()
    assert confirmed["health"]["state"] == "needs_attention"


def test_good_reading_after_a_miss_restarts_three_sample_confirmation(status):
    status.confirm_healthy()
    status.robot["servo"].update(live=17, missing=[3], missing_names=["L1 yaw"])
    status.advance()
    status.robot["servo"].update(live=18, missing=[], missing_names=[])
    recovered = status.advance()
    assert recovered["health"]["state"] == "checking"
    assert recovered["health"]["healthy_samples"] == 1
    status.advance()
    assert status.advance()["health"]["state"] == "healthy"


def test_bad_fields_with_a_repeated_timestamp_discard_prior_confirmation(status):
    status.confirm_healthy()
    status.robot["servo"]["ok"] = False
    bad = status.snapshot()
    assert bad["health"]["state"] != "healthy"
    assert bad["health"]["healthy_samples"] == 0
    status.robot["servo"]["ok"] = True
    repeated = status.snapshot()
    assert repeated["health"]["state"] != "healthy"
    assert repeated["health"]["healthy_samples"] == 0
    assert status.advance()["health"]["healthy_samples"] == 1


def test_confirmed_thermal_trip_needs_immediate_attention(status):
    status.robot["servo"].update(tripped=[17], tripped_names=["L5 knee"], max_temp_c=60)
    result = status.snapshot()
    assert result["health"]["state"] == "needs_attention"
    assert result["health"]["healthy_samples"] == 0
    assert result["readiness"]["state"] == "needs_review"


def test_robot_connection_loss_discards_previous_good_confirmation(status):
    status.confirm_healthy()
    status.robot = TimeoutError("robot unavailable")
    offline = status.snapshot()
    assert offline["health"]["state"] != "healthy"
    assert offline["health"]["fresh"] is False
    assert offline["health"]["healthy_samples"] == 0
    status.robot = robot_reading(status.now)
    assert status.snapshot()["health"]["state"] == "checking"


def test_fresh_camera_cannot_hide_stale_robot_feedback(status):
    status.robot["servo"]["ts"] = status.now - 60
    result = status.snapshot()
    assert result["camera"]["fresh"] is True
    assert result["camera"]["age_seconds"] == 0.05
    assert result["health"]["fresh"] is False
    assert result["health"]["state"] != "healthy"
    assert result["readiness"]["state"] == "needs_review"


@pytest.mark.parametrize("frame_age_ms", [2001, None, -1, float("nan")])
def test_successful_camera_request_does_not_make_an_old_frame_fresh(status, frame_age_ms):
    status.vision["performance"]["frame_age_ms"] = frame_age_ms
    result = status.confirm_healthy()
    assert result["health"]["fresh"] is True
    assert result["camera"]["fresh"] is False
    assert result["camera"]["pose_review_required"] is True
    assert result["readiness"]["state"] == "needs_review"


def test_camera_connection_loss_preserves_independent_motor_health(status):
    status.vision = TimeoutError("camera unavailable")
    result = status.confirm_healthy()
    assert result["camera"]["available"] is False
    assert result["camera"]["fresh"] is False
    assert result["readiness"]["state"] == "needs_review"


def test_previous_timing_stop_is_context_not_a_live_blocker(status):
    status.robot["detail"] = "EMERGENCY STOP"
    status.robot["demo"].update(
        status="stand timing overrun",
        progress={"error": "stand timing overrun"},
    )
    result = status.confirm_healthy()
    assert result["robot"]["last_issue"]
    assert "timing" in result["robot"]["last_issue"].lower()
    assert result["readiness"]["state"] == "guarded_ready"
    assert result["readiness"]["guarded_runner_ready"] is True
    assert result["readiness"]["can_start_from_website"] is False


def test_an_active_robot_operation_is_not_ready_for_another_test(status):
    status.robot["demo"]["running"] = True
    status.robot["activity"] = "demo"
    result = status.confirm_healthy()
    assert result["robot"]["busy"] is True
    assert result["readiness"]["state"] == "busy"
    assert result["readiness"]["can_start_from_website"] is False


def test_good_camera_and_telemetry_are_guarded_runner_supervision(status):
    result = status.confirm_healthy()
    assert result["camera"]["fresh"] is True
    assert result["readiness"]["state"] == "guarded_ready"
    assert result["readiness"]["guarded_runner_ready"] is True
    assert result["readiness"]["reasons"] == []
    assert result["readiness"]["can_start_from_website"] is False


def test_nonessential_imu_does_not_block_generic_motor_readiness(status):
    status.robot["servo"]["imu_ok"] = False
    result = status.confirm_healthy()
    assert result["health"]["state"] == "healthy"
    assert result["health"]["imu_ok"] is False
    assert result["readiness"]["state"] == "guarded_ready"


def test_status_cache_limits_source_reads_and_does_not_duplicate_health_samples(monkeypatch):
    status = StatusHarness(monkeypatch, cache_seconds=5)
    monkeypatch.setattr(robot_status.time, "monotonic", lambda: status.now)
    first = status.snapshot()
    assert len(status.calls) == 2
    status.now += 4
    cached = status.snapshot()
    assert cached["observed_at"] == first["observed_at"]
    assert cached["health"]["healthy_samples"] == 1
    assert cached["camera"]["fresh"] is False
    assert cached["camera"]["age_seconds"] >= 4
    assert first["camera"]["fresh"] is True
    assert len(status.calls) == 2
    status.now += 1
    refreshed = status.snapshot()
    assert len(status.calls) == 4
    assert refreshed["health"]["healthy_samples"] == 1


def test_cached_health_loses_green_and_metrics_when_feedback_ages_past_30_seconds(monkeypatch):
    status = StatusHarness(monkeypatch)
    monkeypatch.setattr(robot_status.time, "monotonic", lambda: status.now)
    status.confirm_healthy()
    status.now += 28.75
    last_fresh = status.snapshot()
    assert last_fresh["health"]["state"] == "healthy"
    assert last_fresh["health"]["age_seconds"] == 29
    status.service.cache_seconds = 5
    previous_calls = len(status.calls)
    status.now += 2
    aged = status.snapshot()
    assert len(status.calls) == previous_calls
    assert aged["observed_at"] == last_fresh["observed_at"]
    assert aged["health"]["fresh"] is False
    assert aged["health"]["state"] != "healthy"
    assert aged["health"]["healthy_samples"] == 0
    assert aged["health"]["live_motors"] is None
    assert aged["health"]["max_temperature_c"] is None
    assert aged["readiness"]["state"] == "needs_review"
    assert last_fresh["health"]["state"] == "healthy"


def test_saved_experiment_queue_does_not_claim_the_physical_robot_is_running(status):
    status.confirm_healthy()
    result = status.snapshot(experiments=[
        {"id": "sim", "status": "running", "parameters": {"simulated": True}},
        {"id": "blocked", "status": "waiting_for_operator", "parameters": {
            "current_compatibility": {"ready": False},
        }},
        {"id": "waiting", "status": "waiting_for_operator", "parameters": {}},
        {"id": "done", "status": "succeeded"},
    ])
    assert result["robot"]["busy"] is False
    assert result["readiness"]["state"] == "guarded_ready"
    assert result["queue"] == {
        "waiting": 2,
        "software_blocked": 0,
        "recorded_software_requirements": 1,
    }


@pytest.mark.parametrize("robot_url,vision_url", [
    (ROBOT_URL + "?zero=1", VISION_URL),
    ("http://robot.test:8080/api/status", VISION_URL),
    (ROBOT_URL, VISION_URL + "?start=1"),
    (ROBOT_URL, "http://vision.test:8898/api/vision/start"),
])
def test_configuration_rejects_endpoints_that_are_not_the_passive_status_paths(robot_url, vision_url):
    with pytest.raises(ValueError):
        RobotStatusService(robot_url=robot_url, vision_url=vision_url)


@pytest.mark.parametrize("endpoint", ["/api/robot-status", "/api/robot-status/frame"])
def test_robot_status_and_frame_require_viewer_authentication(tmp_path, monkeypatch, endpoint):
    settings = Settings(
        data_dir=tmp_path,
        api_keys="operator:alice:operator-secret,viewer:bob:viewer-secret",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="",
        auto_worker=False,
        max_duration_seconds=2,
    )
    app = create_app(settings)
    calls = []

    def snapshot(experiments=()):
        calls.append("status")
        return {"health": {"state": "unknown"}}

    def frame():
        calls.append("frame")
        return b"\xff\xd8stub-frame\xff\xd9"

    monkeypatch.setattr(app.state.robot_status, "snapshot", snapshot)
    monkeypatch.setattr(app.state.robot_status, "camera_frame", frame)
    with TestClient(app) as client:
        unauthenticated = client.get(endpoint, follow_redirects=False)
        assert unauthenticated.status_code == 401
        assert calls == []
        response = client.get(endpoint, headers={"Authorization": "Bearer viewer-secret"})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        if endpoint.endswith("/frame"):
            assert response.headers["content-type"] == "image/jpeg"
            assert response.content == b"\xff\xd8stub-frame\xff\xd9"
            assert calls == ["frame"]
        else:
            assert response.json()["health"] == {"state": "unknown"}
            assert response.json()["execution"]["state"] == "unknown"
            assert calls == ["status"]


@pytest.mark.parametrize("target", ["http://192.168.4.39:8080", "https://10.1.2.3:8080"])
def test_default_robot_hostname_discovers_verified_physical_target_from_vision_hub(monkeypatch, target):
    service = RobotStatusService(vision_url=VISION_URL, cache_seconds=0)
    calls = []

    def fetch(url):
        calls.append(url)
        assert url == HUB_URL
        return hub_reading(target)

    monkeypatch.setattr(service, "_fetch_json", fetch)
    assert service._resolve_robot_url() == target + "/api/robot"
    assert calls == [HUB_URL]


@pytest.mark.parametrize("target", [
    "http://8.8.8.8:8080",
    "http://robot.local:8080",
    "http://[::1]:8080",
    "ftp://192.168.4.39:8080",
    "http://192.168.4.39:8898",
    "http://192.168.4.39:8080/",
    "http://192.168.4.39:8080/api/robot",
    "http://operator:secret@192.168.4.39:8080",
    "http://192.168.4.39:8080?zero=1",
    "http://192.168.4.39:8080#fragment",
])
def test_discovery_rejects_targets_outside_the_exact_local_robot_origin(monkeypatch, target):
    service = RobotStatusService(vision_url=VISION_URL)
    monkeypatch.setattr(service, "_fetch_json", lambda url: hub_reading(target))
    assert service._resolve_robot_url() == DEFAULT_ROBOT_URL


@pytest.mark.parametrize("case", ["unavailable", "not_ok", "wrong_service", "wrong_hub", "sim_only", "malformed", "offline"])
def test_invalid_or_simulation_hub_data_falls_back_to_the_original_physical_hostname(monkeypatch, case):
    payload = hub_reading()
    if case == "unavailable":
        payload["targets"]["robot"]["available"] = False
    elif case == "not_ok":
        payload["targets"]["robot"]["ok"] = False
    elif case == "wrong_service":
        payload["targets"]["robot"]["service"] = "hexapod-sim"
    elif case == "wrong_hub":
        payload["service"] = "hexapod-sim"
    elif case == "sim_only":
        del payload["targets"]["robot"]
    elif case == "malformed":
        payload = None

    def fetch(url):
        assert url == HUB_URL
        if case == "offline":
            raise TimeoutError("hub unavailable")
        return payload

    service = RobotStatusService(vision_url=VISION_URL)
    monkeypatch.setattr(service, "_fetch_json", fetch)
    assert service._resolve_robot_url() == DEFAULT_ROBOT_URL


def test_custom_robot_source_bypasses_discovery(monkeypatch):
    service = RobotStatusService(robot_url=ROBOT_URL, vision_url=VISION_URL)

    def unexpected_fetch(url):
        pytest.fail("An explicitly configured robot source must not query the discovery hub")

    monkeypatch.setattr(service, "_fetch_json", unexpected_fetch)
    assert service._resolve_robot_url() == ROBOT_URL


def test_robot_status_wait_ages_an_already_received_camera_frame(monkeypatch):
    service = RobotStatusService(robot_url=ROBOT_URL, vision_url=VISION_URL, cache_seconds=0)
    now = 1_800_000_000.0
    elapsed = [0.0]
    vision_timed = threading.Event()
    local = threading.local()
    vision = {
        "ok": True,
        "camera": {"enabled": True, "status": "running"},
        "performance": {"frame_age_ms": 50},
        "pose": {"safety": {"safe_pose": True}},
    }

    def monotonic():
        value = elapsed[0]
        if getattr(local, "returned_vision", False):
            vision_timed.set()
        return value

    def fetch(url):
        if url == VISION_URL:
            local.returned_vision = True
            return vision
        assert url == ROBOT_URL
        assert vision_timed.wait(timeout=2), "Camera completion time was not captured"
        elapsed[0] = 3.0
        return robot_reading(now - 0.25)

    monkeypatch.setattr(service, "_now", lambda: now)
    monkeypatch.setattr(service, "_fetch_json", fetch)
    monkeypatch.setattr(robot_status.time, "monotonic", monotonic)
    result = service.snapshot()
    assert result["health"]["fresh"] is True
    assert result["camera"]["fresh"] is False
    assert result["camera"]["age_seconds"] == pytest.approx(3.05)
    assert result["readiness"]["state"] == "needs_review"
    assert vision["performance"]["frame_age_ms"] == 50


def proxy_fallback_status(monkeypatch):
    service = RobotStatusService(vision_url=VISION_URL, cache_seconds=0)
    hub = hub_reading()
    hub.update(target="robot", active={"robot": True, "sim": False})
    state = {
        "now": 1_800_000_000.0,
        "calls": [],
        "hub_reads": 0,
        "initial_hub": deepcopy(hub),
        "followup_hub": deepcopy(hub),
        "simulated_proxy": False,
    }
    proxy_url = "http://vision.test:8898/api/robot"

    def fetch(url):
        state["calls"].append(url)
        if url == HUB_URL:
            state["hub_reads"] += 1
            return deepcopy(state["initial_hub"] if state["hub_reads"] == 1 else state["followup_hub"])
        if url in {DEFAULT_ROBOT_URL, "http://192.168.4.39:8080/api/robot"}:
            raise TimeoutError("direct robot route unavailable")
        if url == VISION_URL:
            return {
                "ok": True,
                "camera": {"enabled": True, "status": "running"},
                "performance": {"frame_age_ms": 50},
                "pose": {"safety": {"safe_pose": True}},
            }
        assert url == proxy_url, "Fallback must only read the existing passive robot proxy"
        result = robot_reading(state["now"] - 0.25)
        if state["simulated_proxy"]:
            result["sim"] = True
        return result

    monkeypatch.setattr(service, "_fetch_json", fetch)
    monkeypatch.setattr(service, "_now", lambda: state["now"])
    return service, state, proxy_url


def test_direct_route_failure_can_use_a_verified_physical_robot_hub_proxy(monkeypatch):
    service, state, proxy_url = proxy_fallback_status(monkeypatch)
    for _ in range(3):
        result = service.snapshot()
        state["now"] += 5
    assert result["health"]["state"] == "healthy"
    assert result["health"]["healthy_samples"] == 3
    assert state["calls"].count(proxy_url) == 3
    assert state["calls"].count("http://192.168.4.39:8080/api/robot") == 3
    assert state["hub_reads"] == 6  # each fallback verifies the hub again after direct failure
    assert result["readiness"]["can_start_from_website"] is False


def test_hub_switched_to_simulation_after_discovery_is_never_used_as_robot_proxy(monkeypatch):
    service, state, proxy_url = proxy_fallback_status(monkeypatch)
    state["followup_hub"].update(target="sim", active={"robot": False, "sim": True})
    result = service.snapshot()
    assert state["hub_reads"] == 2
    assert proxy_url not in state["calls"]
    assert result["health"]["state"] != "healthy"
    assert result["health"]["fresh"] is False
    assert result["health"]["healthy_samples"] == 0


def test_proxy_target_race_returning_simulation_never_confirms_physical_health(monkeypatch):
    service, state, proxy_url = proxy_fallback_status(monkeypatch)
    state["simulated_proxy"] = True
    for _ in range(3):
        result = service.snapshot()
        state["now"] += 5
    assert state["calls"].count(proxy_url) == 3
    assert result["health"]["state"] != "healthy"
    assert result["health"]["fresh"] is False
    assert result["health"]["healthy_samples"] == 0
    assert result["readiness"]["state"] == "needs_review"


def test_quarantined_connection_is_a_specific_blocker_even_with_normal_motor_readings(status):
    status.confirm_healthy()
    status.robot["bus_quarantined"] = True
    result = status.advance()
    assert result["health"]["state"] == "needs_attention"
    assert result["health"]["healthy_samples"] == 0
    assert "reader has not finished" in result["robot"]["last_issue"]
    assert "power unverified" in result["robot"]["headline"]
    assert result["readiness"]["state"] == "needs_review"
