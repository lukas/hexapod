"""Optional local camera observations, independent of robot readiness and control."""

import logging
import math
import re
import threading
import time


_LOGGER = logging.getLogger(__name__)
_CAMERA_ID = re.compile(r"[a-zA-Z0-9_-]+\Z")
_ROTATING_CAPTURE_SLOT = threading.Semaphore(1)


class _CapturePaused(ValueError):
    pass


class _CaptureInUse(ValueError):
    pass


class ObservationCameras:
    """Capture only the configured device; HTTP readers never activate a camera."""

    FRESH_SECONDS = 2.0
    RETRY_SECONDS = 2.0
    OUTPUT_SECONDS = 0.125
    ROTATION_SECONDS = 0.25
    PAUSED_SECONDS = 0.5

    def __init__(self, device_name="", *, camera_id="iphone", name="iPhone", device_uid="",
                 capture_allowed=None, min_frame_detail=0.0):
        if not isinstance(camera_id, str) or not _CAMERA_ID.fullmatch(camera_id):
            raise ValueError("Camera id must contain only letters, digits, underscores, or hyphens")
        self.camera_id = camera_id
        self.name = name.strip() or camera_id
        self.device_name = device_name.strip()
        self.device_uid = device_uid.strip()
        self.capture_allowed = capture_allowed
        if (isinstance(min_frame_detail, bool)
                or not isinstance(min_frame_detail, (int, float))
                or not math.isfinite(min_frame_detail) or min_frame_detail < 0):
            raise ValueError("Minimum frame detail must be a finite nonnegative number")
        self.min_frame_detail = float(min_frame_detail)
        if self.device_uid:
            self.FRESH_SECONDS = 20.0
        self._lock = threading.Lock()
        self._release_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._capture = None
        self._jpeg = None
        self._frame_at = None
        self._sequence = 0
        self._width = 0
        self._height = 0
        self._status = "stopped"
        self._last_error = None
        self._permission_status = "unknown"

    @staticmethod
    def _now():
        return time.monotonic()

    def start(self):
        if not (self.device_name or self.device_uid):
            return
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._status = "connecting"
            self._thread = threading.Thread(
                target=self._run_rotating if self.device_uid else self._run,
                name="robot-lab-camera-" + self.camera_id, daemon=True,
            )
            self._thread.start()

    def stop(self):
        self._stop.set()
        with self._lock:
            capture, thread = self._capture, self._thread
            self._clear_locked("stopped")
        if capture is not None:
            self._release(capture)
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=10.0)
            if thread.is_alive():
                _LOGGER.warning("Observation camera thread has not finished shutdown")

    def _clear_locked(self, status, error=None):
        self._jpeg = None
        self._frame_at = None
        self._width = 0
        self._height = 0
        self._status = status
        self._last_error = error

    def snapshots(self):
        if not (self.device_name or self.device_uid):
            return []
        with self._lock:
            age = None if self._frame_at is None else max(0.0, self._now() - self._frame_at)
            fresh = self._jpeg is not None and age is not None and age <= self.FRESH_SECONDS
            return [{
                "id": self.camera_id, "name": self.name,
                "device_name": self.device_name, "device_uid": self.device_uid,
                "available": self._status == "streaming", "fresh": fresh,
                "age_seconds": None if age is None else round(age, 3),
                "status": "stale" if self._status == "streaming" and not fresh else self._status,
                "frame_sequence": self._sequence,
                "error": self._last_error,
                "permission_status": self._permission_status,
                "width": self._width, "height": self._height,
                "frame_url": "/api/robot-status/cameras/" + self.camera_id + "/frame",
            }]

    def frame(self, camera_id):
        if not (self.device_name or self.device_uid) or camera_id != self.camera_id:
            raise KeyError(camera_id)
        with self._lock:
            if (self._jpeg is None or self._frame_at is None
                    or self._now() - self._frame_at > self.FRESH_SECONDS):
                raise ValueError("A fresh observation frame is not available")
            return self._jpeg

    def _open_capture(self):
        # These macOS dependencies are optional unless a camera is configured.
        from hexapod_tracker.avfoundation_capture import AVFoundationYuvCapture
        from hexapod_tracker import avfoundation_capture as native

        framework = getattr(native, "AV", None)
        if framework is not None:
            authorization = int(framework.AVCaptureDevice.authorizationStatusForMediaType_(
                framework.AVMediaTypeVideo))
            permission = {0: "not_determined", 1: "restricted", 2: "denied", 3: "authorized"}.get(
                authorization, "unknown")
            with self._lock:
                self._permission_status = permission
            if permission in {"restricted", "denied"}:
                raise PermissionError("macOS camera access is " + permission + " for the capture service")

        self._ensure_capture_allowed()

        devices = AVFoundationYuvCapture._devices()
        if self.device_uid:
            matches = [device for device in devices
                       if hasattr(device, "uniqueID") and str(device.uniqueID()) == self.device_uid]
        else:
            matches = [device for device in devices
                       if str(device.localizedName()) == self.device_name]
        if len(matches) != 1:
            raise ValueError("Configured camera is unavailable or ambiguous")
        selected = matches[0]
        rotating = bool(self.device_uid)

        def check_device():
            self._ensure_capture_allowed()
            if self._stop.is_set():
                raise _CapturePaused("Camera capture stopped")
            if (not selected.isConnected()
                    or (hasattr(selected, "isSuspended") and selected.isSuspended())):
                raise ValueError("Configured camera is disconnected or suspended")
            if (hasattr(selected, "isInUseByAnotherApplication")
                    and selected.isInUseByAnotherApplication()):
                raise _CaptureInUse("Configured camera is in use by another application")

        check_device()

        class BoundCapture(AVFoundationYuvCapture):
            @staticmethod
            def _devices():
                # Bind the device object itself. An index can change between
                # discovery and the adapter's lazy capture-session startup.
                check_device()
                return [selected]

            def _select_format(self, device):
                if rotating:
                    from hexapod_tracker import avfoundation_capture as native

                    # The Arducam's full sensor yuvs mode supports 10 fps;
                    # its native NV12 modes require much more USB bandwidth.
                    for candidate in device.formats():
                        description = candidate.formatDescription()
                        subtype = native.CM.CMFormatDescriptionGetMediaSubType(description)
                        size = native.CM.CMVideoFormatDescriptionGetDimensions(description)
                        if (subtype == int.from_bytes(b"yuvs", "big")
                                and (size.width, size.height) == (1280, 800)
                                and any(float(rate.minFrameRate()) <= 10 <= float(rate.maxFrameRate())
                                        for rate in candidate.videoSupportedFrameRateRanges())):
                            self.capture_image_size_px = (1280, 800)
                            self.fps = 10.0
                            return candidate
                return super()._select_format(device)

            def _configure_device(self, device, capture_format):
                check_device()
                return super()._configure_device(device, capture_format)

        # UID-configured robot cameras include the Arducam's full 16:10 sensor
        # format. Keep the legacy iPhone's existing format preference intact.
        preferred_sizes = ((1920, 1440), (1920, 1080), (1280, 720))
        if self.device_uid:
            preferred_sizes = ((1280, 800),) + preferred_sizes
        return BoundCapture(
            0, preferred_sizes=preferred_sizes,
            processing_width=1280, fps=30.0, frame_timeout_s=3.0 if rotating else 6.0,
        )

    def _check_frame_detail(self, frame):
        if not self.min_frame_detail:
            return
        import cv2

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        if width > 320:
            gray = cv2.resize(gray, (320, max(1, round(height * 320 / width))),
                              interpolation=cv2.INTER_AREA)
        if cv2.Laplacian(gray, cv2.CV_64F).var() < self.min_frame_detail:
            raise ValueError("Camera image has no useful detail; view may be covered")

    @staticmethod
    def _encode(frame):
        import cv2

        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            raise ValueError("Could not encode observation frame")
        return encoded.tobytes()

    def _release(self, capture):
        with self._release_lock:
            try:
                capture.release()
                native_thread = getattr(capture, "_thread", None)
                return native_thread is None or not native_thread.is_alive()
            except Exception:
                _LOGGER.warning("Could not release observation camera", exc_info=True)
                return False

    def _ensure_capture_allowed(self):
        if not self.device_uid or self.capture_allowed is None:
            return
        try:
            allowed = self.capture_allowed()
        except Exception:
            allowed = False
        if not allowed:
            raise _CapturePaused("Observation capture is paused")

    def _defer_slot_release(self, capture, slot):
        native_thread = getattr(capture, "_thread", None)
        if native_thread is None or not callable(getattr(native_thread, "join", None)):
            return False

        def finish_shutdown():
            # The adapter's bounded release may return while native shutdown
            # is still running. Keep USB ownership until that thread exits.
            native_thread.join()
            slot.release()

        threading.Thread(target=finish_shutdown, daemon=True,
                         name="robot-lab-camera-shutdown-" + self.camera_id).start()
        return True

    def _run_rotating(self):
        while not self._stop.is_set():
            acquired = False
            slot = _ROTATING_CAPTURE_SLOT
            capture = None
            released = True
            deferred_release = False
            paused = False
            try:
                self._ensure_capture_allowed()
                while not self._stop.is_set():
                    self._ensure_capture_allowed()
                    if slot.acquire(timeout=0.1):
                        acquired = True
                        break
                if self._stop.is_set():
                    break
                self._ensure_capture_allowed()
                capture = self._open_capture()
                with self._lock:
                    self._capture = capture
                if self._stop.is_set():
                    break
                self._ensure_capture_allowed()
                ok, image = capture.read()
                captured_at = self._now()
                self._ensure_capture_allowed()
                if not ok or image is None:
                    raise ValueError(getattr(capture, "last_error", None) or "Configured camera stopped delivering frames")
                self._check_frame_detail(image)
                jpeg = self._encode(image)
                self._ensure_capture_allowed()
                height, width = image.shape[:2]
                with self._lock:
                    if not self._stop.is_set():
                        self._jpeg = jpeg
                        self._frame_at = captured_at
                        self._sequence += 1
                        self._width, self._height = int(width), int(height)
                        self._status = "streaming"
                        self._last_error = None
            except _CaptureInUse:
                with self._lock:
                    self._clear_locked("stopped" if self._stop.is_set() else "in_use")
            except _CapturePaused:
                paused = True
                with self._lock:
                    self._clear_locked("stopped" if self._stop.is_set() else "paused")
            except Exception as error:
                with self._lock:
                    self._clear_locked("stopped" if self._stop.is_set() else "unavailable", str(error)[:1000])
                _LOGGER.debug("Observation camera %s unavailable: %s", self.camera_id, error)
            finally:
                if capture is not None:
                    released = self._release(capture)
                with self._lock:
                    self._capture = None
                if acquired and released:
                    slot.release()
                elif acquired:
                    deferred_release = self._defer_slot_release(capture, slot)
            if not released:
                # A timed-out native shutdown may still own USB bandwidth.
                # Quarantine its slot rather than overlap another camera.
                with self._lock:
                    self._clear_locked("unavailable")
                _LOGGER.warning("Camera %s is waiting for native capture release", self.camera_id)
                if not deferred_release:
                    return
            if self._stop.wait(self.PAUSED_SECONDS if paused else self.ROTATION_SECONDS):
                break
        with self._lock:
            self._clear_locked("stopped")

    def _run(self):
        while not self._stop.is_set():
            capture = None
            try:
                capture = self._open_capture()
                with self._lock:
                    self._capture = capture
                    stopped = self._stop.is_set()
                if stopped:
                    break
                next_output = 0.0
                while not self._stop.is_set():
                    if self._stop.wait(max(0.0, next_output - self._now())):
                        break
                    ok, image = capture.read()
                    if not ok or image is None:
                        raise ValueError(getattr(capture, "last_error", None) or "Configured camera stopped delivering frames")
                    now = self._now()
                    if now < next_output:
                        continue
                    jpeg = self._encode(image)
                    height, width = image.shape[:2]
                    with self._lock:
                        if self._stop.is_set():
                            break
                        self._jpeg = jpeg
                        self._frame_at = now
                        self._sequence += 1
                        self._width, self._height = int(width), int(height)
                        self._status = "streaming"
                        self._last_error = None
                    next_output = now + self.OUTPUT_SECONDS
            except Exception as error:
                with self._lock:
                    self._clear_locked("stopped" if self._stop.is_set() else "unavailable", str(error)[:1000])
                _LOGGER.debug("Observation camera unavailable: %s", error)
            finally:
                if capture is not None:
                    self._release(capture)
                with self._lock:
                    self._capture = None
            if self._stop.wait(self.RETRY_SECONDS):
                break
        with self._lock:
            self._clear_locked("stopped")


class ObservationCameraCollection:
    """Independent configured cameras, routed by stable public identifiers."""

    def __init__(self, specs=(), *, legacy_device_name="", capture_allowed=None):
        self._cameras = {}
        configurations = list(specs)
        self.has_robot_cameras = bool(configurations)
        if legacy_device_name.strip():
            configurations.append({
                "id": "iphone", "name": "iPhone", "device_name": legacy_device_name,
            })
        for spec in configurations:
            if not isinstance(spec, dict):
                raise ValueError("Each camera configuration must be an object")
            camera_id = spec.get("id")
            if not isinstance(camera_id, str) or not _CAMERA_ID.fullmatch(camera_id):
                raise ValueError("Camera id must contain only letters, digits, underscores, or hyphens")
            if camera_id in self._cameras:
                raise ValueError("Camera ids must be unique")
            for field in ("name", "device_name", "device_uid"):
                if not isinstance(spec.get(field, ""), str):
                    raise ValueError("Camera names and device identities must be strings")
            device_name = spec.get("device_name", "").strip()
            device_uid = spec.get("device_uid", "").strip()
            if not (device_name or device_uid):
                raise ValueError("A camera needs an exact device name or unique device id")
            self._cameras[camera_id] = ObservationCameras(
                device_name, camera_id=camera_id, name=spec.get("name", camera_id),
                device_uid=device_uid, capture_allowed=capture_allowed if device_uid else None,
                min_frame_detail=spec.get("min_frame_detail", 0.0),
            )

    def start(self):
        for camera in self._cameras.values():
            camera.start()

    def stop(self):
        for camera in self._cameras.values():
            camera.stop()

    def snapshots(self):
        return [snapshot for camera in self._cameras.values() for snapshot in camera.snapshots()]

    def frame(self, camera_id):
        return self._cameras[camera_id].frame(camera_id)
