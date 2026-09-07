"""Observation cameras must stay optional and never substitute another device."""

import sys
import threading
import time
from types import ModuleType, SimpleNamespace

import pytest

from hexapod_lab import observation_cameras as camera_module
from hexapod_lab.observation_cameras import ObservationCameraCollection, ObservationCameras


def wait_until(predicate):
    deadline = time.monotonic() + 2.0
    while not predicate():
        if time.monotonic() > deadline:
            pytest.fail("Camera worker did not reach the expected state")
        time.sleep(0.005)


def test_unconfigured_service_never_loads_or_opens_camera(monkeypatch):
    service = ObservationCameras()
    monkeypatch.setattr(service, "_open_capture", lambda: pytest.fail("Unexpected capture"))
    service.start()
    assert service.snapshots() == []
    assert service._thread is None
    with pytest.raises(KeyError):
        service.frame("iphone")
    service.stop()


def test_http_reads_do_not_start_configured_camera(monkeypatch):
    service = ObservationCameras("Lukas's iPhone")
    monkeypatch.setattr(service, "_open_capture", lambda: pytest.fail("Unexpected capture"))
    status = service.snapshots()[0]
    assert status["id"] == "iphone"
    assert status["name"] == "iPhone"
    assert status["device_name"] == "Lukas's iPhone"
    assert not status["fresh"] and not status["available"]
    assert status["status"] == "stopped"
    with pytest.raises(ValueError):
        service.frame("iphone")
    with pytest.raises(KeyError):
        service.frame("other")
    assert service._thread is None


def test_stale_cached_image_is_rejected_at_exact_freshness_boundary(monkeypatch):
    service = ObservationCameras("Lukas's iPhone")
    now = [10.0]
    monkeypatch.setattr(service, "_now", lambda: now[0])
    service._jpeg = b"jpeg"
    service._frame_at = 10.0
    service._status = "streaming"
    now[0] = 12.0
    assert service.frame("iphone") == b"jpeg"
    assert service.snapshots()[0]["fresh"]
    now[0] = 12.0001
    with pytest.raises(ValueError):
        service.frame("iphone")
    state = service.snapshots()[0]
    assert state["available"] and not state["fresh"]
    assert state["status"] == "stale"


def install_native_fake(monkeypatch, devices):
    class Native:
        @staticmethod
        def _devices():
            return devices

        def __init__(self, index, **options):
            self.index = index
            self.options = options
            self.fps = options.get("fps")
            self.configured = []

        def _select_format(self, device):
            return "fallback"

        def _configure_device(self, device, capture_format):
            self.configured.append(capture_format)

    parent = ModuleType("hexapod_tracker")
    native = ModuleType("hexapod_tracker.avfoundation_capture")
    native.AVFoundationYuvCapture = Native
    native.CM = SimpleNamespace(
        CMFormatDescriptionGetMediaSubType=lambda description: description.subtype,
        CMVideoFormatDescriptionGetDimensions=lambda description: description,
    )
    monkeypatch.setitem(sys.modules, "hexapod_tracker", parent)
    monkeypatch.setitem(sys.modules, "hexapod_tracker.avfoundation_capture", native)
    return Native


def device(name, connected=True, suspended=False, uid="", in_use=False, formats=()):
    return SimpleNamespace(
        localizedName=lambda: name,
        uniqueID=lambda: uid,
        isConnected=lambda: connected,
        isSuspended=lambda: suspended,
        isInUseByAnotherApplication=lambda: in_use,
        formats=lambda: formats,
    )


def test_exact_name_binding_survives_enumeration_order_changes(monkeypatch):
    selected = device("Lukas's iPhone")
    devices = [device("Arducam"), selected]
    install_native_fake(monkeypatch, devices)
    service = ObservationCameras("Lukas's iPhone")
    capture = service._open_capture()
    devices[:] = [device("Studio Display"), device("Arducam")]
    assert capture.index == 0
    assert capture._devices() == [selected]
    selected.isConnected = lambda: False
    with pytest.raises(ValueError, match="disconnected"):
        capture._devices()
    with pytest.raises(ValueError, match="unavailable"):
        service._open_capture()


@pytest.mark.parametrize("devices", [
    [device("Arducam")],
    [device("Lukas's iPhone"), device("Lukas's iPhone")],
    [device("Lukas's iPhone", connected=False)],
    [device("Lukas's iPhone", suspended=True)],
])
def test_missing_ambiguous_or_inactive_device_has_no_fallback(monkeypatch, devices):
    install_native_fake(monkeypatch, devices)
    with pytest.raises(ValueError):
        ObservationCameras("Lukas's iPhone")._open_capture()


class FakeCapture:
    def __init__(self):
        self.allow_frame = threading.Event()
        self.disconnect = threading.Event()
        self.released = False

    def read(self):
        if not self.allow_frame.wait(1.0) or self.disconnect.is_set():
            return False, None
        self.allow_frame.clear()
        return True, SimpleNamespace(shape=(720, 1280, 3))

    def release(self):
        self.released = True
        self.disconnect.set()
        self.allow_frame.set()


def test_background_reconnect_clears_old_frame_and_stop_releases(monkeypatch):
    service = ObservationCameras("Lukas's iPhone")
    service.RETRY_SECONDS = 0.01
    captures = [FakeCapture(), FakeCapture()]
    opened = []
    now = [10.0]

    def open_capture():
        capture = captures[len(opened)]
        opened.append(capture)
        return capture

    monkeypatch.setattr(service, "_open_capture", open_capture)
    monkeypatch.setattr(service, "_encode", lambda image: b"jpeg")
    monkeypatch.setattr(service, "_now", lambda: now[0])
    try:
        service.start()
        original_thread = service._thread
        service.start()
        assert service._thread is original_thread
        wait_until(lambda: len(opened) == 1)
        captures[0].allow_frame.set()
        wait_until(lambda: service.snapshots()[0]["fresh"])
        first = service.snapshots()[0]
        assert first["frame_sequence"] == 1
        assert (first["width"], first["height"]) == (1280, 720)
        captures[0].disconnect.set()
        captures[0].allow_frame.set()
        wait_until(lambda: len(opened) == 2)
        assert captures[0].released
        assert not service.snapshots()[0]["fresh"]
        with pytest.raises(ValueError):
            service.frame("iphone")
        now[0] = 11.0
        captures[1].allow_frame.set()
        wait_until(lambda: service.snapshots()[0]["fresh"])
        assert service.snapshots()[0]["frame_sequence"] == 2
    finally:
        service.stop()
    assert captures[1].released
    assert not original_thread.is_alive()
    assert service.snapshots()[0]["status"] == "stopped"
    assert not service.snapshots()[0]["fresh"]
    with pytest.raises(ValueError):
        service.frame("iphone")


def test_uid_binding_distinguishes_identically_named_cameras_and_preserves_full_format(monkeypatch):
    devices = [device("Arducam", uid="usb-" + str(index)) for index in range(3)]
    install_native_fake(monkeypatch, devices)
    services = [ObservationCameras(
        "Arducam", camera_id="robot-" + str(index), name="Robot camera " + str(index),
        device_uid="usb-" + str(index),
    ) for index in range(3)]
    captures = [service._open_capture() for service in services]
    for index, capture in enumerate(captures):
        assert capture._devices() == [devices[index]]
        assert capture.options["preferred_sizes"][0] == (1280, 800)
        assert capture.options["processing_width"] == 1280
        snapshot = services[index].snapshots()[0]
        assert snapshot["device_uid"] == "usb-" + str(index)
        assert snapshot["id"] == "robot-" + str(index)
        assert snapshot["name"] == "Robot camera " + str(index)
    selected = devices[1]
    devices[:] = [devices[1], devices[2], devices[0]]
    assert captures[1]._devices() == [selected]
    assert services[1]._open_capture()._devices() == [selected]
    selected.isSuspended = lambda: True
    with pytest.raises(ValueError, match="suspended"):
        captures[1]._devices()
    with pytest.raises(ValueError, match="suspended"):
        services[1]._open_capture()
    assert services[0]._open_capture()._devices() == [devices[2]]


@pytest.mark.parametrize("devices", [
    [device("Arducam", uid="different")],
    [device("Arducam", uid="selected", connected=False)],
    [device("Arducam", uid="selected", suspended=True)],
    [device("Arducam", uid="selected"), device("Arducam", uid="selected")],
])
def test_uid_missing_inactive_or_ambiguous_never_falls_back_to_matching_name(monkeypatch, devices):
    install_native_fake(monkeypatch, devices)
    with pytest.raises(ValueError):
        ObservationCameras("Arducam", device_uid="selected")._open_capture()


def test_legacy_camera_keeps_existing_format_preferences(monkeypatch):
    install_native_fake(monkeypatch, [device("Lukas's iPhone")])
    capture = ObservationCameras("Lukas's iPhone")._open_capture()
    assert capture.options["preferred_sizes"] == ((1920, 1440), (1920, 1080), (1280, 720))


def test_collection_reads_never_start_capture_and_routes_exact_ids(monkeypatch):
    cameras = ObservationCameraCollection([
        {"id": "robot-side_1", "name": "Side", "device_uid": "usb-one"},
        {"id": "robot-2", "device_name": "Named camera"},
    ], legacy_device_name="Lukas's iPhone")
    assert cameras.has_robot_cameras
    for camera in cameras._cameras.values():
        monkeypatch.setattr(camera, "_open_capture", lambda: pytest.fail("Read started capture"))
    snapshots = cameras.snapshots()
    assert [camera["id"] for camera in snapshots] == ["robot-side_1", "robot-2", "iphone"]
    for snapshot in snapshots:
        camera_id = snapshot["id"]
        assert snapshot["frame_url"] == "/api/robot-status/cameras/" + camera_id + "/frame"
        assert not snapshot["fresh"] and not snapshot["available"]
        with pytest.raises(ValueError):
            cameras.frame(camera_id)
    with pytest.raises(KeyError):
        cameras.frame("robot-1")
    assert all(camera._thread is None for camera in cameras._cameras.values())
    assert not ObservationCameraCollection(legacy_device_name="iPhone").has_robot_cameras
    assert not ObservationCameraCollection().has_robot_cameras
    assert ObservationCameraCollection().snapshots() == []


@pytest.mark.parametrize("specs", [
    [{"id": "", "device_uid": "usb-one"}],
    [{"id": "../camera", "device_uid": "usb-one"}],
    [{"id": "robot/side", "device_uid": "usb-one"}],
    [{"id": "camera?query", "device_uid": "usb-one"}],
    [{"id": 5, "device_uid": "usb-one"}],
    [{"id": "side", "device_uid": "usb-one"}, {"id": "side", "device_uid": "usb-two"}],
    [{"id": "side", "device_uid": " ", "device_name": " "}],
    [{"id": "side", "device_uid": 5}],
    ["camera"],
])
def test_collection_rejects_invalid_ids_duplicate_ids_and_empty_identity(specs):
    with pytest.raises(ValueError):
        ObservationCameraCollection(specs)


def test_three_camera_workers_route_frames_and_fail_and_recover_independently(monkeypatch):
    monkeypatch.setattr(camera_module, "_ROTATING_CAPTURE_SLOT", threading.Semaphore(1))
    specs = [{"id": "robot-" + str(index), "name": "View " + str(index),
              "device_name": "Arducam", "device_uid": "usb-" + str(index)}
             for index in range(3)]
    allowed = threading.Event()
    allowed.set()
    cameras = ObservationCameraCollection(specs, capture_allowed=allowed.is_set)
    opened, active = [], set()
    failing = set()

    class SnapshotCapture:
        def __init__(self, key):
            assert not active, "Another native capture still owns the shared slot"
            active.add(key)
            self.key = key
            self.released = False
            opened.append(self)

        def read(self):
            if self.key in failing:
                return False, None
            return True, SimpleNamespace(shape=(800, 1280, 3), payload=self.key.encode())

        def release(self):
            if not self.released:
                active.remove(self.key)
                self.released = True

    for camera_id, worker in cameras._cameras.items():
        worker.ROTATION_SECONDS = 0.02
        worker.PAUSED_SECONDS = 0.01
        monkeypatch.setattr(worker, "_encode", lambda image: image.payload)
        monkeypatch.setattr(worker, "_open_capture", lambda key=camera_id: SnapshotCapture(key))
    try:
        cameras.start()
        wait_until(lambda: all(snapshot["fresh"] for snapshot in cameras.snapshots()))
        threads = [worker._thread for worker in cameras._cameras.values()]
        cameras.start()
        assert threads == [worker._thread for worker in cameras._cameras.values()]
        for spec in specs:
            assert cameras.frame(spec["id"]) == spec["id"].encode()
        first_sequences = [snapshot["frame_sequence"] for snapshot in cameras.snapshots()]
        failing.add("robot-1")
        wait_until(lambda: cameras.snapshots()[1]["status"] == "unavailable")
        wait_until(lambda: cameras.snapshots()[0]["frame_sequence"] > first_sequences[0]
                   and cameras.snapshots()[2]["frame_sequence"] > first_sequences[2])
        with pytest.raises(ValueError):
            cameras.frame("robot-1")
        for key in ("robot-0", "robot-2"):
            assert cameras.frame(key) == key.encode()
        failing.clear()
        wait_until(lambda: all(snapshot["fresh"] for snapshot in cameras.snapshots()))
        assert cameras.frame("robot-1") == b"robot-1"
        assert cameras.snapshots()[1]["frame_sequence"] > first_sequences[1]
        assert all((snapshot["width"], snapshot["height"]) == (1280, 800)
                   for snapshot in cameras.snapshots())
        allowed.clear()
        wait_until(lambda: all(snapshot["status"] == "paused" for snapshot in cameras.snapshots()))
        paused_opens = len(opened)
        time.sleep(0.04)
        assert len(opened) == paused_opens
        for spec in specs:
            with pytest.raises(ValueError):
                cameras.frame(spec["id"])
        allowed.set()
        wait_until(lambda: all(snapshot["fresh"] for snapshot in cameras.snapshots()))
    finally:
        cameras.stop()
    assert all(not thread.is_alive() for thread in threads)
    assert not active
    assert all(capture.released for capture in opened)
    assert all(snapshot["status"] == "stopped" and not snapshot["fresh"]
               for snapshot in cameras.snapshots())
    for spec in specs:
        with pytest.raises(ValueError):
            cameras.frame(spec["id"])


def test_rotating_snapshot_freshness_and_retention_do_not_change_legacy_camera(monkeypatch):
    worker = ObservationCameras(device_uid="usb-one")
    monkeypatch.setattr(worker, "_now", lambda: 30.0)
    worker._jpeg, worker._frame_at, worker._status = b"snapshot", 10.0, "streaming"
    assert worker.FRESH_SECONDS == 20.0
    assert ObservationCameras("iPhone").FRESH_SECONDS == 2.0
    assert worker.frame("iphone") == b"snapshot"
    assert worker.snapshots()[0]["age_seconds"] == 20.0
    monkeypatch.setattr(worker, "_now", lambda: 30.001)
    with pytest.raises(ValueError):
        worker.frame("iphone")
    assert not worker.snapshots()[0]["fresh"]


@pytest.mark.parametrize("raises", [False, True])
def test_rotating_pause_guard_blocks_open_and_discards_old_snapshot(monkeypatch, raises):
    def allowed():
        if raises:
            raise RuntimeError("Lease status unavailable")
        return False
    worker = ObservationCameras(device_uid="usb-one", capture_allowed=allowed)
    worker._jpeg, worker._frame_at, worker._status = b"old", worker._now(), "streaming"
    monkeypatch.setattr(worker, "_open_capture", lambda: pytest.fail("Paused capture opened a camera"))
    try:
        worker.start()
        wait_until(lambda: worker.snapshots()[0]["status"] == "paused")
        assert not worker.snapshots()[0]["available"]
        assert not worker.snapshots()[0]["fresh"]
        with pytest.raises(ValueError):
            worker.frame("iphone")
    finally:
        worker.stop()
    assert not worker._thread.is_alive()


def test_stop_interrupts_a_worker_waiting_for_shared_capture_slot(monkeypatch):
    monkeypatch.setattr(camera_module, "_ROTATING_CAPTURE_SLOT", threading.Semaphore(0))
    waiting = threading.Event()
    worker = ObservationCameras(device_uid="usb-one", capture_allowed=lambda: waiting.set() or True)
    monkeypatch.setattr(worker, "_open_capture", lambda: pytest.fail("Worker acquired unavailable slot"))
    worker.start()
    assert waiting.wait(1.0)
    started = time.monotonic()
    worker.stop()
    assert time.monotonic() - started < 0.5
    assert not worker._thread.is_alive()


def test_slot_remains_owned_until_capture_release_finishes(monkeypatch):
    monkeypatch.setattr(camera_module, "_ROTATING_CAPTURE_SLOT", threading.Semaphore(1))
    release_started, finish_release, second_opened = threading.Event(), threading.Event(), threading.Event()

    class Capture:
        def __init__(self, first):
            self.first = first
        def read(self):
            return True, SimpleNamespace(shape=(800, 1280, 3))
        def release(self):
            if self.first:
                release_started.set()
                assert finish_release.wait(1.0)

    first = ObservationCameras(device_uid="first")
    second = ObservationCameras(device_uid="second")
    monkeypatch.setattr(first, "_open_capture", lambda: Capture(True))
    monkeypatch.setattr(second, "_open_capture", lambda: second_opened.set() or Capture(False))
    for worker in (first, second):
        monkeypatch.setattr(worker, "_encode", lambda image: b"snapshot")
    try:
        first.start()
        assert release_started.wait(1.0)
        second.start()
        assert not second_opened.wait(0.05)
        assert first.snapshots()[0]["fresh"]
        assert first.frame("iphone") == b"snapshot"
        finish_release.set()
        assert second_opened.wait(1.0)
    finally:
        finish_release.set()
        first.stop()
        second.stop()


def test_unfinished_native_release_quarantines_slot_instead_of_overlapping(monkeypatch):
    slot = threading.Semaphore(1)
    monkeypatch.setattr(camera_module, "_ROTATING_CAPTURE_SLOT", slot)
    worker = ObservationCameras(device_uid="first")
    capture = SimpleNamespace(
        read=lambda: (True, SimpleNamespace(shape=(800, 1280, 3))),
        release=lambda: None,
        _thread=SimpleNamespace(is_alive=lambda: True),
    )
    monkeypatch.setattr(worker, "_open_capture", lambda: capture)
    monkeypatch.setattr(worker, "_encode", lambda image: b"snapshot")
    worker.start()
    wait_until(lambda: not worker._thread.is_alive())
    assert not slot.acquire(blocking=False)
    assert worker.snapshots()[0]["status"] == "unavailable"
    assert not worker.snapshots()[0]["fresh"]
    worker.stop()


def test_in_use_device_is_rejected_at_discovery_lazy_start_and_configuration(monkeypatch):
    selected = device("Arducam", uid="selected", in_use=True)
    install_native_fake(monkeypatch, [selected])
    worker = ObservationCameras(device_uid="selected")
    with pytest.raises(ValueError, match="in use"):
        worker._open_capture()
    selected.isInUseByAnotherApplication = lambda: False
    capture = worker._open_capture()
    assert capture.options["frame_timeout_s"] == 3.0
    selected.isInUseByAnotherApplication = lambda: True
    with pytest.raises(ValueError, match="in use"):
        capture._devices()
    with pytest.raises(ValueError, match="in use"):
        capture._configure_device(selected, "format")
    assert capture.configured == []


def test_pause_guard_is_rechecked_before_native_configuration(monkeypatch):
    allowed = [True]
    selected = device("Arducam", uid="selected")
    install_native_fake(monkeypatch, [selected])
    worker = ObservationCameras(device_uid="selected", capture_allowed=lambda: allowed[0])
    capture = worker._open_capture()
    allowed[0] = False
    with pytest.raises(ValueError, match="paused"):
        capture._devices()
    with pytest.raises(ValueError, match="paused"):
        capture._configure_device(selected, "format")
    assert capture.configured == []


def native_format(subtype, width, height, minimum, maximum):
    return SimpleNamespace(
        formatDescription=lambda: SimpleNamespace(
            subtype=int.from_bytes(subtype, "big"), width=width, height=height),
        videoSupportedFrameRateRanges=lambda: [SimpleNamespace(
            minFrameRate=lambda: minimum, maxFrameRate=lambda: maximum)],
    )


def test_uid_capture_prefers_full_sensor_low_bandwidth_yuvs_mode(monkeypatch):
    fast = native_format(b"420v", 1280, 800, 100, 120)
    cropped = native_format(b"yuvs", 1280, 720, 10, 30)
    full = native_format(b"yuvs", 1280, 800, 10, 30)
    selected = device("Arducam", uid="selected", formats=[fast, cropped, full])
    install_native_fake(monkeypatch, [selected])
    capture = ObservationCameras(device_uid="selected")._open_capture()
    assert capture._select_format(selected) is full
    assert capture.capture_image_size_px == (1280, 800)
    assert capture.fps == 10.0
    legacy = ObservationCameras("Arducam")._open_capture()
    assert legacy._select_format(selected) == "fallback"
    assert legacy.options["frame_timeout_s"] == 6.0


def test_uid_capture_keeps_adapter_fallback_if_no_supported_low_rate_full_sensor_mode(monkeypatch):
    selected = device("Arducam", uid="selected", formats=[
        native_format(b"yuvs", 1280, 800, 30, 60)])
    install_native_fake(monkeypatch, [selected])
    capture = ObservationCameras(device_uid="selected")._open_capture()
    assert capture._select_format(selected) == "fallback"
    assert capture.options["preferred_sizes"] == ((1280, 800), (1920, 1440), (1920, 1080), (1280, 720))


def test_permission_change_during_encoding_discards_snapshot(monkeypatch):
    monkeypatch.setattr(camera_module, "_ROTATING_CAPTURE_SLOT", threading.Semaphore(1))
    allowed = [True]
    worker = ObservationCameras(device_uid="selected", capture_allowed=lambda: allowed[0])
    released = threading.Event()
    capture = SimpleNamespace(
        read=lambda: (True, SimpleNamespace(shape=(800, 1280, 3))),
        release=released.set,
    )
    monkeypatch.setattr(worker, "_open_capture", lambda: capture)
    def encode(image):
        allowed[0] = False
        return b"must-not-publish"
    monkeypatch.setattr(worker, "_encode", encode)
    try:
        worker.start()
        wait_until(lambda: worker.snapshots()[0]["status"] == "paused")
        assert released.is_set()
        assert worker.snapshots()[0]["frame_sequence"] == 0
        with pytest.raises(ValueError):
            worker.frame("iphone")
    finally:
        worker.stop()


def test_delayed_native_shutdown_eventually_restores_shared_slot(monkeypatch):
    slot = threading.Semaphore(1)
    monkeypatch.setattr(camera_module, "_ROTATING_CAPTURE_SLOT", slot)
    native_finished = threading.Event()
    native_thread = threading.Thread(target=native_finished.wait, daemon=True)
    native_thread.start()
    released = threading.Event()
    worker = ObservationCameras(device_uid="selected")
    capture = SimpleNamespace(
        read=lambda: (True, SimpleNamespace(shape=(800, 1280, 3))),
        release=released.set,
        _thread=native_thread,
    )
    monkeypatch.setattr(worker, "_open_capture", lambda: capture)
    monkeypatch.setattr(worker, "_encode", lambda image: b"snapshot")
    try:
        worker.start()
        assert released.wait(1.0)
        wait_until(lambda: worker.snapshots()[0]["status"] == "unavailable")
        assert not slot.acquire(blocking=False)
        worker.stop()
        assert not worker._thread.is_alive()
        assert not slot.acquire(blocking=False)
        native_finished.set()
        assert slot.acquire(timeout=1.0)
        slot.release()
    finally:
        native_finished.set()
        native_thread.join(timeout=1.0)
        worker.stop()


@pytest.mark.parametrize("minimum", [-1, float("nan"), float("inf"), -float("inf"), True, "5", None])
def test_minimum_frame_detail_rejects_invalid_values(minimum):
    with pytest.raises(ValueError, match="finite nonnegative"):
        ObservationCameras(device_uid="selected", min_frame_detail=minimum)
    with pytest.raises(ValueError, match="finite nonnegative"):
        ObservationCameraCollection([{
            "id": "side", "device_uid": "selected", "min_frame_detail": minimum,
        }])


def test_frame_detail_defaults_to_disabled_and_collection_passes_configuration(monkeypatch):
    worker = ObservationCameras(device_uid="selected")
    monkeypatch.setitem(sys.modules, "cv2", None)
    worker._check_frame_detail(object())
    assert worker.min_frame_detail == 0
    cameras = ObservationCameraCollection([{
        "id": "side", "device_uid": "selected", "min_frame_detail": 5,
    }])
    assert cameras._cameras["side"].min_frame_detail == 5.0


def test_covered_frame_clears_old_snapshot_and_recovers_on_later_good_frame(monkeypatch):
    monkeypatch.setattr(camera_module, "_ROTATING_CAPTURE_SLOT", threading.Semaphore(1))
    worker = ObservationCameras(device_uid="selected", min_frame_detail=5)
    worker.ROTATION_SECONDS = 0.01
    covered = threading.Event()
    captures = []

    class Capture:
        def __init__(self):
            self.released = False
            captures.append(self)
        def read(self):
            return True, SimpleNamespace(shape=(800, 1280, 3))
        def release(self):
            self.released = True

    def check_frame(frame):
        if covered.is_set():
            raise ValueError("Camera image has no useful detail; view may be covered")

    monkeypatch.setattr(worker, "_open_capture", Capture)
    monkeypatch.setattr(worker, "_check_frame_detail", check_frame)
    monkeypatch.setattr(worker, "_encode", lambda image: b"clear robot view")
    try:
        worker.start()
        wait_until(lambda: worker.snapshots()[0]["fresh"])
        assert worker.frame("iphone") == b"clear robot view"
        covered.set()
        wait_until(lambda: worker.snapshots()[0]["status"] == "unavailable")
        failed_sequence = worker.snapshots()[0]["frame_sequence"]
        assert not worker.snapshots()[0]["fresh"]
        with pytest.raises(ValueError):
            worker.frame("iphone")
        covered.clear()
        wait_until(lambda: worker.snapshots()[0]["frame_sequence"] > failed_sequence)
        assert worker.frame("iphone") == b"clear robot view"
        assert worker.snapshots()[0]["fresh"]
    finally:
        worker.stop()
    assert not worker._thread.is_alive()
    assert all(capture.released for capture in captures)


@pytest.mark.parametrize('authorization,expected', [(1, 'restricted'), (2, 'denied')])
def test_denied_camera_permission_is_reported_without_discovering_or_opening(monkeypatch, authorization, expected):
    install_native_fake(monkeypatch, [])
    native = sys.modules['hexapod_tracker.avfoundation_capture']
    native.AV = SimpleNamespace(
        AVMediaTypeVideo='video',
        AVCaptureDevice=SimpleNamespace(authorizationStatusForMediaType_=lambda media: authorization),
    )
    monkeypatch.setattr(native.AVFoundationYuvCapture, '_devices',
                        lambda: pytest.fail('Permission-denied service must not discover/open cameras'))
    camera = ObservationCameras(device_uid='robot-usb', camera_id='robot-1')
    with pytest.raises(PermissionError, match=expected):
        camera._open_capture()
    assert camera.snapshots()[0]['permission_status'] == expected


def test_native_error_is_preserved_and_cleared_after_recovery(monkeypatch):
    camera = ObservationCameras('Phone')
    camera.RETRY_SECONDS = 0.005
    first = SimpleNamespace(read=lambda: (False, None), release=lambda: None,
                            last_error='AVFoundation -11852: application not authorized')
    second = FakeCapture()
    captures = iter([first, second])
    monkeypatch.setattr(camera, '_open_capture', lambda: next(captures))
    monkeypatch.setattr(camera, '_encode', lambda image: b'jpeg')
    try:
        camera.start()
        wait_until(lambda: camera.snapshots()[0]['error'] is not None)
        assert '-11852' in camera.snapshots()[0]['error']
        second.allow_frame.set()
        wait_until(lambda: camera.snapshots()[0]['fresh'])
        assert camera.snapshots()[0]['error'] is None
    finally:
        camera.stop()
