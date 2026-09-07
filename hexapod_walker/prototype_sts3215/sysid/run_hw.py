"""Run a sysid protocol on the hexapod over HTTP and pull the trace.

SAFETY: this tool moves the robot. It refuses without ``--go`` and requires
an advancing camera stream.  Use the physical setup documented by the exact
protocol: the reviewed ``*_belly_rest_*`` protocols run with the chassis
resting normally on its belly and the moving foot clear of the floor; the
older ``*_air_*`` batteries require the robot suspended with every foot off
the ground. No hand-posing is needed: the on-robot runner glides the legs to
the protocol's start pose by itself (slow, trip-protected, pose-verified).
Preflight is read-only; ``Ctrl-C`` (or ``--abort``) sends
``/api/rl/stop``, and the runner limps on any trip. Never run this
outside an active campaign with standing guarded authority.

Flow: read-only preflight (pose + IMU sanity) -> POST /api/sysid/run
(protocol JSON in the body — nothing to deploy per-experiment) -> poll
until the job finishes -> download the CSV + summary into
``sysid/datasets/<protocol>_<stamp>/`` (raw traces are never
overwritten). Physical runs require an advancing vision stream. The client
admits motion only after three distinct frames and binds a stale/erroring
stream to the documented remote stop endpoint for the entire run.

Run (from prototype_sts3215/, repo .venv)::

    uv run python -m sysid.run_hw \
      --protocol sysid/protocols/steps_air_v1.json --capture-vision --go
    uv run python -m sysid.run_hw --abort          # emergency stop the job
"""
from __future__ import annotations

import argparse
import json
import math
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable

from . import DATASET_DIR, PROTO_DIR  # noqa: F401
from sysid_protocol import (  # noqa: E402
    duration_s, protocol_hash, validate,
)
from rl_move.remote import HexapodClient  # noqa: E402
from .camera_guard import CameraGuard  # noqa: E402


class VisionGuard:
    """Thread-safe advancing-frame admission and stale-stream guard."""

    def __init__(self, *, required_frames: int = 3,
                 stale_after_s: float = 2.0) -> None:
        self.required_frames = max(1, int(required_frames))
        self.stale_after_s = float(stale_after_s)
        self.ready = threading.Event()
        self.fault = threading.Event()
        self._lock = threading.Lock()
        self._last_sequence = None
        self._frames = 0
        self._last_advance = time.monotonic()
        self._reason: str | None = None

    def observe(self, sequence) -> bool:
        """Record one unique frame; return true only when it advanced."""
        if sequence is None:
            return False
        with self._lock:
            if sequence == self._last_sequence:
                return False
            self._last_sequence = sequence
            self._frames += 1
            self._last_advance = time.monotonic()
            if self._frames >= self.required_frames:
                self.ready.set()
            return True

    def check_stale(self) -> None:
        with self._lock:
            age = time.monotonic() - self._last_advance
            if age > self.stale_after_s:
                self._reason = (
                    f"vision stream did not advance for {age:.1f}s "
                    f"(limit {self.stale_after_s:.1f}s)"
                )
                self.fault.set()

    def fail(self, reason: str) -> None:
        with self._lock:
            self._reason = str(reason)
            self.fault.set()

    @property
    def failure(self) -> str | None:
        with self._lock:
            return self._reason if self.fault.is_set() else None

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "ready": self.ready.is_set(),
                "fault": self.fault.is_set(),
                "reason": self._reason,
                "advancing_frames": self._frames,
                "last_sequence": self._last_sequence,
                "last_advance_age_s": round(
                    time.monotonic() - self._last_advance, 3
                ),
            }


class _CameraGuardedLaunch:
    """Order a camera abort after this runner's launch, or prevent launch.

    A guard failure between the admission check and HTTP POST must not send
    stop first and then allow the pending POST to start an unobserved run.
    The lock covers only launch/abort ordering, never camera observation.
    """

    def __init__(self, client, guard: VisionGuard | CameraGuard | None, summary: dict):
        self.client = client
        self.guard = guard
        self.summary = summary
        self.lock = threading.Lock()
        self.launch_attempted = False
        self.stop_attempted = False
        self.stop_result = None

    def run(self, protocol: dict, *, force: bool) -> dict:
        with self.lock:
            if isinstance(self.guard, VisionGuard):
                self.guard.check_stale()
            if self.guard is not None and self.guard.failure:
                raise RuntimeError(
                    f"camera admission failed before motion: {self.guard.failure}"
                )
            self.launch_attempted = True
            return self.client._req(
                "POST", "/api/sysid/run", {"protocol": protocol, "force": force}
            )

    def camera_failed(self, error: str):
        self.summary["abort_reason"] = error
        with self.lock:
            # Failed admission belongs to no robot process yet. In particular,
            # it must not stop another process before refusing our own launch.
            if not self.launch_attempted:
                return
            if self.stop_attempted:
                return self.stop_result
            self.stop_attempted = True
            try:
                self.stop_result = self.client.stop()
            except Exception as abort_error:
                self.summary["abort_error"] = str(abort_error)
                self.stop_result = {"ok": False, "error": str(abort_error)}
            if self.stop_result is None:
                self.stop_result = {"ok": False, "error": "abort response missing"}
            return self.stop_result


def _guarded_result(result: dict, guard: VisionGuard | CameraGuard | None) -> dict:
    if guard is None or not guard.failure:
        return result
    return {
        **result,
        "ok": False,
        "error": f"camera guard failed: {guard.failure}",
        "camera_guard_failed": guard.failure,
        "hardware_result": result,
    }


def _capture_vision_sidecar(
    state_url: str,
    out_dir: Path,
    stop: threading.Event,
    *,
    hz: float,
    save_frames: bool,
    frame_url: str | None,
    summary: dict,
    guard: VisionGuard | CameraGuard,
    camera_guard: CameraGuard | None = None,
    on_guard_failure: Callable[[str], None] | None = None,
) -> None:
    """Record unique vision frames plus the worker's synchronized IMU sample."""
    vision_guard = guard if isinstance(guard, VisionGuard) else None
    if isinstance(guard, CameraGuard):
        camera_guard = guard
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "vision.jsonl"
    frames_dir = out_dir / "vision_frames"
    if save_frames:
        frames_dir.mkdir(parents=True, exist_ok=True)
    resolved_frame_url = (
        frame_url or state_url.rsplit("/", 1)[0] + "/frame.jpg"
    )
    started = time.monotonic()
    last_sequence = None
    captured = 0
    errors = 0
    last_guard_ok_at = started
    with jsonl_path.open("w", encoding="utf-8", buffering=1) as stream:
        while not stop.is_set():
            iteration = time.monotonic()
            try:
                with urllib.request.urlopen(state_url, timeout=2.0) as response:
                    state = json.loads(response.read().decode("utf-8"))
                if camera_guard is not None:
                    ok, reason = camera_guard.observe(state, now_unix=time.time())
                    if not ok:
                        summary["camera_guard_failed"] = reason
                        if vision_guard is not None:
                            vision_guard.fail(reason)
                        if on_guard_failure is not None:
                            on_guard_failure(reason)
                        stop.set()
                        break
                    last_guard_ok_at = time.monotonic()
                sequence = (state.get("performance") or {}).get(
                    "frame_sequence"
                )
                if sequence is None:
                    # The standalone multi-camera server exposes a fused
                    # pose document instead of the legacy /api/vision/state
                    # shape. Its generation timestamp is a monotonic-enough
                    # unique sample key, and retaining the whole state keeps
                    # the L4/L5 joint-pose and IMU fields available.
                    sequence = state.get("generated_at_unix_s")
                if sequence is not None and sequence != last_sequence:
                    record = {
                        "capture_unix": round(time.time(), 6),
                        "capture_elapsed_s": round(
                            time.monotonic() - started, 6
                        ),
                        "frame_sequence": sequence,
                        "camera": state.get("camera"),
                        "performance": state.get("performance"),
                        "coverage": state.get("coverage"),
                        "pose": state.get("pose"),
                        "feedback": state.get("feedback"),
                        "state": state,
                    }
                    if save_frames:
                        filename = f"frame_{captured:08d}.jpg"
                        with urllib.request.urlopen(
                            resolved_frame_url, timeout=2.0
                        ) as response:
                            (frames_dir / filename).write_bytes(response.read())
                        record["image"] = f"vision_frames/{filename}"
                    stream.write(json.dumps(record, separators=(",", ":")) + "\n")
                    last_sequence = sequence
                    captured += 1
                    if vision_guard is not None:
                        vision_guard.observe(sequence)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                errors += 1
                summary["last_error"] = str(error)
                if (camera_guard is not None
                        and time.monotonic() - last_guard_ok_at > camera_guard.max_state_age_s):
                    _, reason = camera_guard.reject("camera stream stale after repeated read failures")
                    summary["camera_guard_failed"] = reason
                    if vision_guard is not None:
                        vision_guard.fail(reason)
                    if on_guard_failure is not None:
                        on_guard_failure(reason)
                    stop.set()
                    break
            if vision_guard is not None:
                vision_guard.check_stale()
            remaining = 1.0 / hz - (time.monotonic() - iteration)
            if remaining > 0.0:
                stop.wait(remaining)
    summary.update({
        "frames": captured,
        "errors": errors,
        "jsonl": str(jsonl_path),
        "images_saved": bool(save_frames),
        "state_url": state_url,
        "frame_url": resolved_frame_url if save_frames else None,
        "guard": vision_guard.snapshot() if vision_guard is not None else None,
        "camera_guard_failed": camera_guard.failure if camera_guard is not None else None,
        "camera_guard_samples": camera_guard.accepted_samples if camera_guard is not None else None,
    })


def _wait_idle_guarded(client: HexapodClient, *, timeout_s: float,
                       poll_s: float, guard: VisionGuard,
                       stop_callback: Callable[[str], dict] | None = None) -> dict:
    """Poll the robot and issue one remote stop if the vision guard faults."""
    started = time.monotonic()
    last: dict = {}
    stop_result = None
    def stop_owned_job():
        if stop_callback is not None:
            return stop_callback(guard.failure or "vision guard stop")
        return client.stop()

    while time.monotonic() - started < timeout_s:
        guard.check_stale()
        if guard.fault.is_set() and stop_result is None:
            stop_result = stop_owned_job()
        last = client.state()
        # Camera failure may arrive while the status request is in flight.
        # Bind it before accepting an idle result from the same poll.
        if guard.fault.is_set() and stop_result is None:
            stop_result = stop_owned_job()
        cal = last.get("calibrate") or {}
        robot = last.get("robot") or {}
        demo = robot.get("demo") or cal.get("demo") or {}
        running = bool(cal.get("running") or demo.get("running"))
        if not running:
            if cal.get("result") is not None:
                last["result"] = cal["result"]
            if guard.fault.is_set():
                last["ok"] = False
                last["guard_stop"] = guard.snapshot()
                last["stop_result"] = stop_result
            return last
        time.sleep(poll_s)
    last = dict(last)
    last["ok"] = False
    last["error"] = f"timeout after {timeout_s:.0f}s"
    return last


def _pull(client: HexapodClient, name: str, dst_dir: Path) -> Path | None:
    url = f"{client.base}/api/logs/{name}"
    dst = dst_dir / name
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=30) as resp:
            dst.write_bytes(resp.read())
        return dst
    except Exception as e:
        print(f"  !! pull failed ({name}): {e}")
        return None


def _newest_sysid_csv(client: HexapodClient, after_unix: float,
                      wait_s: float = 15.0) -> str | None:
    """Newest sysid_*.csv written after ``after_unix``, size-stable."""
    deadline = time.time() + wait_s
    last = None
    while True:
        logs = client._req("GET", "/api/logs")
        found = None
        for f in logs.get("files", []):
            n = f.get("name", "")
            if (n.startswith("sysid_") and n.endswith(".csv")
                    and f.get("mtime_unix", 0) > after_unix):
                found = (n, int(f.get("bytes", 0)))
                break
        if found is not None and found == last:
            return found[0]
        last = found
        if time.time() >= deadline:
            return found[0] if found else None
        time.sleep(1.5)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--protocol", type=Path)
    ap.add_argument("--url", default=None)
    ap.add_argument("--go", action="store_true",
                    help="actually move the robot (default: dry-run plan)")
    ap.add_argument("--force", action="store_true",
                    help="required for whole-body traj protocols")
    ap.add_argument("--abort", action="store_true",
                    help="just send /api/rl/stop and exit")
    ap.add_argument("--capture-vision", action="store_true",
                    help=("record and continuously guard /api/vision/state "
                          "beside the hardware trace; required with --go"))
    ap.add_argument("--capture-frames", action="store_true",
                    help="also save one JPEG for every captured vision frame")
    ap.add_argument("--vision-url",
                    default="http://127.0.0.1:8898/api/vision/state")
    ap.add_argument(
        "--vision-frame-url",
        default=None,
        help=("JPEG endpoint paired with --vision-url; needed when using "
              "the standalone camera server, e.g. "
              "http://127.0.0.1:8766/snapshot/1.jpg"),
    )
    ap.add_argument("--vision-hz", type=float, default=10.0)
    ap.add_argument("--vision-stale-seconds", type=float, default=2.0,
                    help="remote-stop after this long without a new frame")
    ap.add_argument("--required-target-tag", type=int, action="append", default=[])
    ap.add_argument("--minimum-target-tag-coverage-fraction", type=float, default=0.9)
    ap.add_argument("--camera-max-state-age-s", type=float, default=1.5)
    args = ap.parse_args(argv)

    if args.abort:
        client = HexapodClient(args.url)
        print(json.dumps(client.stop(), indent=2))
        return 0
    if not args.protocol:
        ap.error("need --protocol (or --abort)")

    doc = json.loads(args.protocol.read_text())
    errs = validate(doc)
    if errs:
        raise SystemExit("invalid protocol: " + "; ".join(errs))
    secs = duration_s(doc)
    has_traj = any(s.get("kind") in ("traj", "rel_traj") for s in doc["segments"])
    print(f"protocol '{doc['name']}' hash {protocol_hash(doc)}: "
          f"{len(doc['segments'])} segments, {secs:.0f} s @ "
          f"{doc.get('hz', 25)} Hz"
          + (" — WHOLE-BODY traj (needs --force)" if has_traj else ""))
    print(f"posture: {doc.get('description', '(none)')}")

    if not args.go:
        print("\nDRY RUN (no motion). Re-run with --go in the exact physical "
              "setup documented by this protocol and with its camera stream "
              "available. Belly-rest protocols do not require a stand.")
        return 0

    if not args.capture_vision:
        raise SystemExit(
            "physical sysid requires --capture-vision so camera admission "
            "and the continuous stale-frame abort are bound"
        )

    if not 0.5 <= args.vision_hz <= 30.0:
        raise SystemExit("--vision-hz must be between 0.5 and 30")
    if not 0.5 <= args.vision_stale_seconds <= 10.0:
        raise SystemExit("--vision-stale-seconds must be between 0.5 and 10")

    if not 0.0 < args.minimum_target_tag_coverage_fraction <= 1.0:
        raise SystemExit("minimum target tag coverage must be in (0, 1]")
    if not math.isfinite(args.camera_max_state_age_s) or args.camera_max_state_age_s <= 0:
        raise SystemExit("camera max state age must be finite and positive")

    # Read-only preflight: bus + IMU answering, robot idle.
    client = HexapodClient(args.url)
    fb = client.feedback()
    if not fb.get("ok") or fb.get("live", 0) < 18:
        raise SystemExit(f"preflight failed: feedback={fb}")
    print(f"preflight: {fb['live']}/18 servos, roll {fb.get('roll_deg')} "
          f"pitch {fb.get('pitch_deg')}")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = DATASET_DIR / f"{doc['name']}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    vision_stop = threading.Event()
    vision_summary: dict = {}
    vision_thread = None
    vision_guard = VisionGuard(stale_after_s=args.vision_stale_seconds)
    camera_guard = (CameraGuard(
        required_tag_ids=frozenset(args.required_target_tag),
        minimum_coverage=args.minimum_target_tag_coverage_fraction,
        max_state_age_s=args.camera_max_state_age_s,
    ) if args.required_target_tag else None)
    guarded_launch = _CameraGuardedLaunch(client, vision_guard, vision_summary)
    def camera_abort(reason: str) -> None:
        vision_guard.fail(reason)
        guarded_launch.camera_failed(reason)

    if args.capture_vision:
        vision_thread = threading.Thread(
            target=_capture_vision_sidecar,
            args=(args.vision_url, out_dir, vision_stop),
            kwargs={
                "hz": args.vision_hz,
                "save_frames": bool(args.capture_frames),
                "frame_url": args.vision_frame_url,
                "summary": vision_summary,
                "guard": vision_guard,
                "camera_guard": camera_guard,
                "on_guard_failure": camera_abort,
            },
            name="sysid-vision-capture",
            daemon=True,
        )
        vision_thread.start()
        admission_deadline = time.monotonic() + max(
            5.0, 3.0 / args.vision_hz + args.vision_stale_seconds
        )
        while (not vision_guard.ready.is_set()
               and not vision_guard.fault.is_set()
               and time.monotonic() < admission_deadline):
            time.sleep(0.05)
        if not vision_guard.ready.is_set():
            vision_stop.set()
            vision_thread.join(timeout=4.0)
            raise SystemExit(
                "vision admission failed before motion: "
                + str(vision_guard.snapshot())
            )

    t_start = time.time()
    try:
        kick = guarded_launch.run(doc, force=bool(args.force))
    except BaseException:
        if vision_thread is not None:
            vision_stop.set()
            vision_thread.join(timeout=4.0)
        raise
    print(json.dumps({k: v for k, v in kick.items()
                      if k != "calibrate"}, indent=2))
    if not kick.get("ok"):
        if vision_thread is not None:
            vision_stop.set()
            vision_thread.join(timeout=4.0)
        return 1

    try:
        try:
            # Avoid accepting a stale idle/result snapshot before the newly
            # spawned async worker has published its running state.
            # A camera fault wakes this delay so its stop is not postponed.
            vision_guard.fault.wait(timeout=1.0)
            res = _wait_idle_guarded(
                client,
                timeout_s=secs + 120.0,
                poll_s=0.25,
                guard=vision_guard,
                stop_callback=guarded_launch.camera_failed,
            )
        except KeyboardInterrupt:
            print("\n^C — sending stop (robot limps)")
            client.stop()
            res = client.wait_idle(timeout_s=15.0)
    finally:
        if vision_thread is not None:
            # Keep one post-motion observation before closing the sidecar.
            time.sleep(0.25)
            vision_stop.set()
            vision_thread.join(timeout=4.0)
            if vision_thread.is_alive():
                vision_guard.fail("camera supervision did not finish")
    result = res.get("result") or {}
    guard_stop = res.get("guard_stop")
    if guard_stop:
        result = {
            **result,
            "ok": False,
            "guard_stop": guard_stop,
            "error": str(guard_stop.get("reason") or "vision guard stop"),
        }
    print(f"result: ok={result.get('ok')} "
          f"ticks {result.get('ticks_done')}/{result.get('ticks_planned')}"
          f" overruns={result.get('overruns')} "
          f"error={result.get('error')}")

    csv_name = (Path(result["csv"]).name if result.get("csv")
                else _newest_sysid_csv(client, t_start))
    if not csv_name:
        print("no trace CSV found on the robot")
        return 1
    got = _pull(client, csv_name, out_dir)
    sum_name = csv_name.replace(".csv", "_summary.json")
    got_summary = _pull(client, sum_name, out_dir)
    # ``/api/rl/state`` has historically substituted the latest full
    # calibration report after a sysid worker goes idle.  The sidecar summary
    # written by that worker is the authoritative result for this exact CSV;
    # prefer it so a trip cannot be misreported as a successful old checkup.
    if got_summary is not None:
        try:
            pulled_result = json.loads(got_summary.read_text())
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"  !! invalid pulled summary ({sum_name}): {error}")
        else:
            if isinstance(pulled_result, dict):
                result = pulled_result
                print(f"hardware summary: ok={result.get('ok')} "
                      f"ticks {result.get('ticks_done')}/"
                      f"{result.get('ticks_planned')} "
                      f"overruns={result.get('overruns')} "
                      f"error={result.get('error')}")
    # A downloaded successful hardware result cannot erase a camera stop.
    result = _guarded_result(
        result, camera_guard if camera_guard is not None and camera_guard.failure
        else vision_guard,
    )
    print(f"runner: ok={result.get('ok')} error={result.get('error')}")
    (out_dir / "runner_summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    (out_dir / "protocol.json").write_text(json.dumps(doc, indent=1,
                                                      sort_keys=True))
    if vision_thread is not None:
        (out_dir / "vision_summary.json").write_text(
            json.dumps(vision_summary, indent=2, sort_keys=True) + "\n"
        )
        print(f"vision: {vision_summary.get('frames', 0)} frames, "
              f"{vision_summary.get('errors', 0)} errors")
    print(f"dataset: {out_dir}" + (f" ({got.name})" if got else ""))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
