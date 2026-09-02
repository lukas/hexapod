"""Run a sysid protocol on the hexapod over HTTP and pull the trace.

SAFETY: this tool moves the robot. It refuses without ``--go``, and the
default posture for every standard protocol is *robot on a stand, feet
off the ground, operator watching*. No hand-posing is needed: the
on-robot runner glides the legs to the protocol's start pose by itself
(slow, trip-protected, pose-verified) before the experiment starts.
Preflight is read-only; ``Ctrl-C`` (or ``--abort``) sends
``/api/rl/stop``, and the runner limps on any trip. Never run this
unless the operator asked for this exact experiment.

Flow: read-only preflight (pose + IMU sanity) -> POST /api/sysid/run
(protocol JSON in the body — nothing to deploy per-experiment) -> poll
until the job finishes -> download the CSV + summary into
``sysid/datasets/<protocol>_<stamp>/`` (raw traces are never
overwritten).

Run (from prototype_sts3215/, repo .venv)::

    uv run python -m sysid.run_hw --protocol sysid/protocols/steps_air_v1.json --go
    uv run python -m sysid.run_hw --abort          # emergency stop the job
"""
from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.request
from pathlib import Path

from . import DATASET_DIR, PROTO_DIR  # noqa: F401
from sysid_protocol import (  # noqa: E402
    duration_s, protocol_hash, validate,
)
from rl_move.remote import HexapodClient  # noqa: E402


def _capture_vision_sidecar(
    state_url: str,
    out_dir: Path,
    stop: threading.Event,
    *,
    hz: float,
    save_frames: bool,
    summary: dict,
) -> None:
    """Record unique vision frames plus the worker's synchronized IMU sample."""
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "vision.jsonl"
    frames_dir = out_dir / "vision_frames"
    if save_frames:
        frames_dir.mkdir(parents=True, exist_ok=True)
    frame_url = state_url.rsplit("/", 1)[0] + "/frame.jpg"
    started = time.monotonic()
    last_sequence = None
    captured = 0
    errors = 0
    with jsonl_path.open("w", encoding="utf-8", buffering=1) as stream:
        while not stop.is_set():
            iteration = time.monotonic()
            try:
                with urllib.request.urlopen(state_url, timeout=2.0) as response:
                    state = json.loads(response.read().decode("utf-8"))
                sequence = (state.get("performance") or {}).get(
                    "frame_sequence"
                )
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
                    }
                    if save_frames:
                        filename = f"frame_{int(sequence):08d}.jpg"
                        with urllib.request.urlopen(
                            frame_url, timeout=2.0
                        ) as response:
                            (frames_dir / filename).write_bytes(response.read())
                        record["image"] = f"vision_frames/{filename}"
                    stream.write(json.dumps(record, separators=(",", ":")) + "\n")
                    last_sequence = sequence
                    captured += 1
            except (OSError, ValueError, json.JSONDecodeError) as error:
                errors += 1
                summary["last_error"] = str(error)
            remaining = 1.0 / hz - (time.monotonic() - iteration)
            if remaining > 0.0:
                stop.wait(remaining)
    summary.update({
        "frames": captured,
        "errors": errors,
        "jsonl": str(jsonl_path),
        "images_saved": bool(save_frames),
    })


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
                    help="record /api/vision/state beside the hardware trace")
    ap.add_argument("--capture-frames", action="store_true",
                    help="also save one JPEG for every captured vision frame")
    ap.add_argument("--vision-url",
                    default="http://127.0.0.1:8898/api/vision/state")
    ap.add_argument("--vision-hz", type=float, default=10.0)
    args = ap.parse_args(argv)

    client = HexapodClient(args.url)
    if args.abort:
        print(json.dumps(client.stop(), indent=2))
        return 0
    if not args.protocol:
        ap.error("need --protocol (or --abort)")

    doc = json.loads(args.protocol.read_text())
    errs = validate(doc)
    if errs:
        raise SystemExit("invalid protocol: " + "; ".join(errs))
    secs = duration_s(doc)
    has_traj = any(s.get("kind") == "traj" for s in doc["segments"])
    print(f"protocol '{doc['name']}' hash {protocol_hash(doc)}: "
          f"{len(doc['segments'])} segments, {secs:.0f} s @ "
          f"{doc.get('hz', 25)} Hz"
          + (" — WHOLE-BODY traj (needs --force)" if has_traj else ""))
    print(f"posture: {doc.get('description', '(none)')}")

    if not args.go:
        print("\nDRY RUN (no motion). Re-run with --go when the robot is "
              "on the stand, feet off the ground, and you are watching.")
        return 0

    if not 0.5 <= args.vision_hz <= 30.0:
        raise SystemExit("--vision-hz must be between 0.5 and 30")

    # Read-only preflight: bus + IMU answering, robot idle.
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
    if args.capture_vision:
        vision_thread = threading.Thread(
            target=_capture_vision_sidecar,
            args=(args.vision_url, out_dir, vision_stop),
            kwargs={
                "hz": args.vision_hz,
                "save_frames": bool(args.capture_frames),
                "summary": vision_summary,
            },
            name="sysid-vision-capture",
            daemon=True,
        )
        vision_thread.start()

    t_start = time.time()
    kick = client._req("POST", "/api/sysid/run",
                       {"protocol": doc, "force": bool(args.force)})
    print(json.dumps({k: v for k, v in kick.items()
                      if k != "calibrate"}, indent=2))
    if not kick.get("ok"):
        if vision_thread is not None:
            vision_stop.set()
            vision_thread.join(timeout=4.0)
        return 1

    try:
        try:
            res = client.wait_idle(timeout_s=secs + 120.0, poll_s=1.0)
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
    result = res.get("result") or {}
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
    _pull(client, sum_name, out_dir)
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
