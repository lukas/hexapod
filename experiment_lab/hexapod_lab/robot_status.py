"""Read-only dashboard observations; never starts or authorizes robot motion."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from ipaddress import IPv4Address, IPv4Network
import json
import logging
import math
import threading
import time
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .run_requirements import run_requirements


_LOGGER = logging.getLogger(__name__)
_DEFAULT_ROBOT_URL = "http://hexapod.local:8080/api/robot"
_PRIVATE_ROBOT_NETWORKS = tuple(IPv4Network(network) for network in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
))


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _dict(value):
    return value if isinstance(value, dict) else {}


class RobotStatusService:
    def __init__(
        self, robot_url="http://hexapod.local:8080/api/robot",
        vision_url="http://127.0.0.1:8898/api/vision/state", *, cache_seconds=1.0,
    ):
        for url, path in ((robot_url, "/api/robot"), (vision_url, "/api/vision/state")):
            parsed = urlsplit(url)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or parsed.username or parsed.password or parsed.query
                    or parsed.fragment or parsed.path != path):
                raise ValueError("Robot dashboard sources must use their exact passive status endpoints")
        self.robot_url = robot_url
        self.vision_url = vision_url
        self.cache_seconds = max(0, cache_seconds)
        self._lock = threading.Lock()
        self._cached = None
        self._cached_at = float("-inf")
        self._last_sample_ts = None
        self._healthy_samples = 0
        self._missing_samples = 0
        self._hot_counts = {}

    def _now(self):
        return time.time()

    @staticmethod
    def _fetch_bytes(url, limit):
        request = Request(url, headers={"User-Agent": "robot-lab-status/1.0"})
        with build_opener(ProxyHandler({}), _NoRedirect).open(request, timeout=2.5) as response:
            data = response.read(limit + 1)
            if len(data) > limit:
                raise ValueError("Status source response too large")
            return data

    def _fetch_json(self, url):
        data = json.loads(self._fetch_bytes(url, 1024 * 1024))
        if not isinstance(data, dict):
            raise ValueError("Status source must be a JSON object")
        return data

    @staticmethod
    def _warn_source(source, error):
        # Source labels are fixed strings, not URLs or request headers.
        reason = getattr(error, "reason", None) or getattr(error, "msg", None)
        _LOGGER.warning("Robot Lab %s source unavailable: %s: %s",
                        source, type(error).__name__, reason or str(error))

    def _resolve_robot_url(self):
        """Reuse the hub's validated physical target without routing through sim."""
        if self.robot_url != _DEFAULT_ROBOT_URL:
            return self.robot_url
        parsed_vision = urlsplit(self.vision_url)
        hub_url = urlunsplit((parsed_vision.scheme, parsed_vision.netloc, "/api/hub", "", ""))
        try:
            hub = self._fetch_json(hub_url)
        except Exception as error:
            self._warn_source("hub metadata", error)
            return self.robot_url
        try:
            target = _dict(_dict(_dict(hub).get("targets")).get("robot"))
            if (_dict(hub).get("service") != "hexapod-hub"
                    or target.get("available") is not True
                    or target.get("ok") is not True
                    or target.get("service") != "hexapod-web"):
                return self.robot_url
            target_url = target.get("url")
            if not isinstance(target_url, str):
                return self.robot_url
            parsed = urlsplit(target_url)
            if (parsed.scheme not in {"http", "https"} or parsed.port != 8080
                    or parsed.username or parsed.password or parsed.path
                    or parsed.query or parsed.fragment):
                return self.robot_url
            address = IPv4Address(parsed.hostname)
            if not (address.is_loopback or any(address in network for network in _PRIVATE_ROBOT_NETWORKS)):
                return self.robot_url
            return urlunsplit((parsed.scheme, parsed.netloc, "/api/robot", "", ""))
        except (TypeError, ValueError):
            # Invalid metadata may contain credentials in its raw URL. Do not
            # log parsing exceptions, which can reproduce the original text.
            return self.robot_url

    def _fetch_robot(self):
        try:
            return self._fetch_json(self._resolve_robot_url())
        except Exception as direct_error:
            if self.robot_url != _DEFAULT_ROBOT_URL:
                raise
            # The Mac hub can have LAN access when this background process
            # does not. Recheck its current target before using its passive
            # proxy; never change hub selection or fall back to simulated data.
            parsed = urlsplit(self.vision_url)
            hub_url = urlunsplit((parsed.scheme, parsed.netloc, "/api/hub", "", ""))
            proxy_url = urlunsplit((parsed.scheme, parsed.netloc, "/api/robot", "", ""))
            try:
                hub = _dict(self._fetch_json(hub_url))
                target = _dict(_dict(hub.get("targets")).get("robot"))
                if (hub.get("service") != "hexapod-hub"
                        or hub.get("target") not in {"robot", "both"}
                        or _dict(hub.get("active")).get("robot") is not True
                        or target.get("available") is not True
                        or target.get("ok") is not True
                        or target.get("service") != "hexapod-web"):
                    raise ValueError("The hub is not currently targeting a verified physical robot")
                # _assess also requires real telemetry, so a target change
                # between metadata and this request cannot report sim as ready.
                return self._fetch_json(proxy_url)
            except Exception:
                raise direct_error from None

    def _read_sources(self):
        def read(source, url):
            try:
                data = self._fetch_robot() if source == "robot" else self._fetch_json(url)
                if not isinstance(data, dict):
                    raise ValueError("Status source must be a JSON object")
                result = data, None
            except Exception as error:
                # A dashboard must degrade to unknown, including DNS/timeouts.
                self._warn_source(source, error)
                result = {}, "unavailable"
            return result, time.monotonic()
        with ThreadPoolExecutor(max_workers=2) as pool:
            robot = pool.submit(read, "robot", self.robot_url)
            vision = pool.submit(read, "vision", self.vision_url)
            robot_result, robot_completed_at = robot.result()
            vision_result, vision_completed_at = vision.result()
        # A quick camera response may have waited for slower robot discovery or
        # status. Include that time before deciding whether the camera is live.
        assessed_at = max(time.monotonic(), robot_completed_at, vision_completed_at)
        vision_data, vision_error = vision_result
        vision_data = deepcopy(vision_data)
        performance = _dict(vision_data.get("performance"))
        frame_age_ms = _number(performance.get("frame_age_ms"))
        if frame_age_ms is not None and frame_age_ms >= 0:
            performance["frame_age_ms"] = frame_age_ms + max(0, assessed_at - vision_completed_at) * 1000
        return robot_result, (vision_data, vision_error)

    def snapshot(self, experiments=()):
        with self._lock:
            if self._cached is None or time.monotonic() - self._cached_at >= self.cache_seconds:
                (robot, robot_error), (vision, vision_error) = self._read_sources()
                self._cached = self._assess(robot, vision, robot_error, vision_error)
                self._cached_at = time.monotonic()
            result = deepcopy(self._cached)
            elapsed = max(0, time.monotonic() - self._cached_at)
            health, camera = result["health"], result["camera"]
            for observation in (health, camera):
                if observation["age_seconds"] is not None:
                    observation["age_seconds"] = round(observation["age_seconds"] + elapsed, 2)
            if health["fresh"] and health["age_seconds"] > 30:
                self._healthy_samples = 0
                health.update(
                    state="unknown", fresh=False, healthy_samples=0,
                    headline="Robot readings are stale or missing",
                    detail="Waiting for a current motor-health sample.",
                    live_motors=None, max_temperature_c=None,
                )
                result["robot"].update(activity=None, armed=None, headline="Robot status unavailable")
                result["readiness"]["reasons"].insert(0, health["detail"])
                result["readiness"]["guarded_runner_ready"] = False
            if camera["fresh"] and camera["age_seconds"] > 2:
                camera.update(fresh=False, headline="Camera unavailable or stale", pose_review_required=True)
                result["readiness"]["reasons"].insert(0, "A fresh camera view is needed to check the robot’s position.")
                result["readiness"]["guarded_runner_ready"] = False
            if not result["robot"]["busy"] and (not health["fresh"] or not camera["fresh"]):
                result["readiness"].update(state="needs_review", headline="Review before another physical test")
        waiting = [item for item in experiments if item.get("status") == "waiting_for_operator"]
        recorded_requirements = sum(
            bool(
                (run_requirements(item) or {}).get(
                    "recorded_software_requirements"
                )
            )
            for item in waiting
        )
        result["queue"] = {
            "waiting": len(waiting),
            # Retain the old field for API compatibility, but do not infer a
            # live blocker from an immutable saved plan.
            "software_blocked": 0,
            "recorded_software_requirements": recorded_requirements,
        }
        return result

    def _assess(self, robot, vision, robot_error, vision_error):
        now = self._now()
        servo = _dict(robot.get("servo"))
        sample_ts = _number(servo.get("ts"))
        age = now - sample_ts if sample_ts is not None else None
        physical = (robot.get("dry_run") is False and robot.get("sim") is not True
                    and robot.get("simulated") is not True)
        fresh = bool(physical and not robot_error and sample_ts and age is not None
                     and -2 <= age <= 30 and servo.get("stale") is not True)
        live = _number(servo.get("live"))
        expected = _number(servo.get("expected"))
        temperature = _number(servo.get("max_temp_c"))
        warn = _number(servo.get("warn_c")) or 55.0
        missing = servo.get("missing")
        hot = servo.get("hot")
        tripped = servo.get("tripped")
        valid_lists = all(isinstance(value, list) for value in (missing, hot, tripped))
        missing_now = live is not None and (live != 18 or bool(missing))
        has_hot = (temperature is not None and temperature >= warn) or bool(hot)
        complete = (fresh and servo.get("ok") is True and valid_lists
                    and robot.get("bus_quarantined") is not True
                    and live == expected == 18 and not missing and not hot and not tripped
                    and temperature is not None and 0 <= temperature < warn)
        if not complete:
            self._healthy_samples = 0
        new_sample = fresh and sample_ts != self._last_sample_ts
        if not fresh or (new_sample and self._last_sample_ts is not None and sample_ts < self._last_sample_ts):
            self._healthy_samples = self._missing_samples = 0
            self._hot_counts = {}
        if new_sample:
            self._last_sample_ts = sample_ts
            self._healthy_samples = min(3, self._healthy_samples + 1) if complete else 0
            self._missing_samples = min(3, self._missing_samples + 1) if missing_now else 0
            current_hot = {
                str(value.get("joint")) for value in (hot or [])
                if isinstance(value, dict) and _number(value.get("temp_c")) is not None
                and value["temp_c"] >= warn
            } if isinstance(hot, list) else set()
            if has_hot and not current_hot and servo.get("hottest"):
                current_hot = {str(servo["hottest"])}
            self._hot_counts = {key: min(3, self._hot_counts.get(key, 0) + 1) for key in current_hot}
        if not robot_error and not physical:
            state, headline, detail = "unknown", "Physical robot not verified", "The source did not identify real robot telemetry."
        elif robot_error:
            state, headline, detail = "offline", "Robot connection unavailable", "Live robot health cannot be checked right now."
        elif not fresh:
            state, headline, detail = "unknown", "Robot readings are stale or missing", "Waiting for a current motor-health sample."
        elif robot.get("bus_quarantined") is True:
            state, headline, detail = "needs_attention", "Motor communication is locked", "A controller reader still owns the motor connection. Its recovery must finish before another test."
        elif isinstance(tripped, list) and tripped:
            state, headline, detail = "needs_attention", "Motor protection has tripped", "The controller reports a temperature protection stop. Inspect the robot before moving it."
        elif self._missing_samples >= 3:
            state, headline, detail = "needs_attention", "Motor replies are missing", "Three distinct recent health samples were incomplete."
        elif any(count >= 3 for count in self._hot_counts.values()):
            state, headline, detail = "needs_attention", "A motor is too warm", "The same motor has been above the warning temperature in three recent samples."
        elif self._healthy_samples >= 3 and complete:
            state, headline, detail = "healthy", "Motor health checks look normal", "All 18 motors responded in three recent samples; temperatures are below the warning level."
        elif complete:
            state, headline, detail = "checking", "Confirming motor health", f"{self._healthy_samples} of 3 distinct healthy samples received."
        else:
            state, headline, detail = "checking", "Motor health needs another check", (
                "An incomplete or unusual reading is being checked against later samples."
            )
        # Never retain an old green metric when the feed is stale or simulated.
        health = {
            "state": state, "headline": headline, "detail": detail,
            "fresh": fresh, "age_seconds": round(max(0, age), 1) if age is not None else None,
            "live_motors": int(live) if fresh and live is not None and live.is_integer() else None,
            "expected_motors": 18,
            "max_temperature_c": temperature if fresh else None,
            "healthy_samples": self._healthy_samples,
            "imu_ok": servo.get("imu_ok") if fresh and isinstance(servo.get("imu_ok"), bool) else None,
        }
        demo = _dict(robot.get("demo"))
        progress = _dict(demo.get("progress"))
        activity = robot.get("activity") if physical and not robot_error and isinstance(robot.get("activity"), str) else None
        armed = robot.get("armed") if physical and not robot_error and isinstance(robot.get("armed"), bool) else None
        busy = bool(physical and not robot_error and (
            demo.get("running") is True or activity in {"demo", "rl", "zeroing", "stopping", "driving"}
        ))
        issue_text = " ".join(str(value or "") for value in (robot.get("detail"), demo.get("status"), progress.get("error")))
        issue = None
        if physical and not robot_error and not busy:
            if robot.get("bus_quarantined") is True:
                issue = "The controller locked motor communication because a previous reader has not finished."
            elif "timing" in issue_text.lower() and any(word in issue_text.lower() for word in ("error", "overrun", "deadline")):
                issue = "The last operation stopped because the controller missed its timing deadline."
            elif "emergency stop" in issue_text.lower() or progress.get("error"):
                issue = "The controller reports a previous stop that needs review before another physical test."
        robot_headline = (
            "Robot status unavailable" if not physical or robot_error else
            "A robot operation is active" if busy else
            "Disarmed · motor power unverified" if robot.get("bus_quarantined") is True or robot.get("torque_state") == "unverified" else
            "Stopped · motor power disabled" if armed is False else
            "Stationary · motor power enabled" if armed is True else "Motor power state unknown"
        )
        performance = _dict(vision.get("performance"))
        frame_age_ms = _number(performance.get("frame_age_ms"))
        camera_info = _dict(vision.get("camera"))
        camera_fresh = bool(not vision_error and vision.get("ok") is True
                            and camera_info.get("enabled") is True
                            and camera_info.get("status") == "running"
                            and frame_age_ms is not None and 0 <= frame_age_ms <= 2000)
        safety = _dict(_dict(vision.get("pose")).get("safety"))
        pose_review = not camera_fresh or safety.get("safe_pose") is not True
        camera = {
            "available": not bool(vision_error), "fresh": camera_fresh,
            "age_seconds": round(frame_age_ms / 1000, 2) if frame_age_ms is not None else None,
            "headline": "Live camera" if camera_fresh else "Camera unavailable or stale",
            "pose_review_required": pose_review,
        }
        reasons = []
        if issue:
            reasons.append(
                issue + " Live camera and telemetry determine whether it is still active."
            )
        if state != "healthy":
            reasons.append(detail)
        if not camera_fresh:
            reasons.append("A fresh camera view is needed to check the robot’s position.")
        elif pose_review:
            reasons.append("Review the live camera frame before motion; a guarded agent may perform this check.")
        ready_state = "busy" if busy else "needs_review" if state != "healthy" or pose_review else "guarded_ready"
        guarded_ready = ready_state == "guarded_ready"
        return {
            "observed_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            "health": health,
            "robot": {
                "activity": activity, "armed": armed, "headline": robot_headline,
                "last_issue": issue, "busy": busy,
                "process_name": demo.get("name") if physical and not robot_error and isinstance(demo.get("name"), str) else None,
                "process_detail": demo.get("status") if physical and not robot_error and isinstance(demo.get("status"), str) else None,
            },
            "camera": camera,
            "readiness": {
                "state": ready_state,
                "headline": "Wait for the current operation" if busy else "Review live evidence before another physical test" if ready_state == "needs_review" else "Camera and telemetry checks are normal",
                "reasons": reasons,
                "guarded_runner_ready": guarded_ready,
                "can_start_from_website": False,
            },
            "refresh_seconds": 5,
        }

    def camera_frame(self):
        if not self.snapshot()["camera"]["fresh"]:
            raise ValueError("Camera frame is stale or unavailable")
        parsed = urlsplit(self.vision_url)
        url = urlunsplit((parsed.scheme, parsed.netloc, "/api/vision/frame.jpg", "", ""))
        data = self._fetch_bytes(url, 8 * 1024 * 1024)
        if not data.startswith(b"\xff\xd8"):
            raise ValueError("Camera source did not return a JPEG")
        return data
