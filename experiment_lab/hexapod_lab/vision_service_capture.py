"""Read observation frames from the camera server instead of opening a camera.

Opening the device directly here has three costs that reading over HTTP does
not. A camera's *active format* is global to the device, so this process and
the camera server fight over size and rate and the last `setActiveFormat_`
wins. Two cameras on one USB controller cannot both stream, so a second
opener can starve one that was working. And this package bundles its own copy
of ``hexapod_tracker``, so capture fixes made there -- the frame-duration
rational the 12MP modules reject, the active-format re-apply after
``startRunning`` -- do not reach us until that venv is reinstalled.

The object below is a drop-in for the parts of ``AVFoundationYuvCapture``
that ``ObservationCameras`` uses: ``read()``, ``release()`` and
``last_error``.
"""
from __future__ import annotations

import json
import time
from urllib import error, parse, request


class VisionServiceCapture:
    """A camera-server-backed frame source addressed by device stable id."""

    # The server publishes at 10 fps by default, so a frame older than this is
    # a stalled camera rather than ordinary jitter.
    STALE_AFTER_S = 3.0

    def __init__(
        self,
        base_url: str,
        *,
        stable_id: str = "",
        device_name: str = "",
        width: int = 1280,
        timeout_s: float = 4.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.stable_id = stable_id.strip()
        self.device_name = device_name.strip()
        self.width = int(width)
        self.timeout_s = float(timeout_s)
        self.last_error: str | None = None
        self.captured_unix: float | None = None
        self.frame_sequence: int | None = None
        self.capture_image_size_px: tuple[int, int] | None = None
        self._slot: int | None = None

    # -- slot resolution -------------------------------------------------
    def _get(self, path: str, timeout: float | None = None) -> tuple[bytes, dict]:
        url = f"{self.base_url}{path}"
        with request.urlopen(url, timeout=timeout or self.timeout_s) as response:
            return response.read(), dict(response.headers)

    def _resolve_slot(self) -> int:
        """Map our device identity onto the server's current slot number.

        Resolved from the server rather than configured, because slots are
        assigned at the server's startup and a stored number goes stale
        whenever the rig is re-cabled -- the failure that left this package
        configured for four cameras that no longer existed.
        """

        payload, _headers = self._get("/status.json")
        cameras = json.loads(payload).get("cameras", [])
        if self.stable_id:
            for camera in cameras:
                if str(camera.get("requested_stable_id") or "") == self.stable_id:
                    return int(camera["index"])
            raise ValueError(
                f"camera server is not serving {self.stable_id}; it has "
                + ", ".join(
                    str(camera.get("requested_stable_id") or camera.get("index"))
                    for camera in cameras
                )
            )
        if self.device_name:
            matches = [
                camera for camera in cameras
                if str(camera.get("device_name") or "") == self.device_name
            ]
            # Two identical "12MP AF Camera" entries are ambiguous rather than
            # arbitrary, so refuse instead of guessing which one was meant.
            if len(matches) != 1:
                raise ValueError(
                    f"{len(matches)} cameras match name {self.device_name!r}; "
                    "configure a device_uid instead"
                )
            return int(matches[0]["index"])
        raise ValueError("a stable id or device name is required")

    # -- capture ---------------------------------------------------------
    def isOpened(self) -> bool:  # noqa: N802 - match the adapter's API
        return True

    def read(self):
        """Return ``(ok, bgr_image)`` for the newest frame on the server."""

        import cv2
        import numpy as np

        try:
            if self._slot is None:
                self._slot = self._resolve_slot()
            query = parse.urlencode({"w": self.width, "t": int(time.time() * 1000)})
            payload, headers = self._get(f"/preview/{self._slot}.jpg?{query}")
        except (error.URLError, OSError, ValueError, json.JSONDecodeError) as failure:
            # Re-resolve next time: a server restart renumbers slots, and a
            # cached slot would then quietly return another camera's frames.
            self._slot = None
            self.last_error = f"camera server unreachable: {failure}"
            return False, None

        age = headers.get("X-Frame-Age-Seconds")
        try:
            age_s = None if age in (None, "unknown") else float(age)
        except ValueError:
            age_s = None
        if age_s is not None and age_s > self.STALE_AFTER_S:
            self.last_error = (
                f"camera server frame is {age_s:.1f}s old; the camera is stalled"
            )
            return False, None

        captured = headers.get("X-Frame-Captured-Unix")
        try:
            # Prefer the server's capture stamp: correlating vision against
            # robot telemetry on a shared clock is the point of these frames,
            # and deriving it here would add this process's own skew.
            self.captured_unix = float(captured) if captured else None
        except ValueError:
            self.captured_unix = None
        sequence = headers.get("X-Frame-Sequence")
        self.frame_sequence = int(sequence) if (sequence or "").isdigit() else None

        image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            self.last_error = "camera server returned an undecodable frame"
            return False, None
        self.capture_image_size_px = (image.shape[1], image.shape[0])
        self.last_error = None
        return True, image

    def release(self) -> None:
        # Nothing is held: no device was opened here.
        self._slot = None
