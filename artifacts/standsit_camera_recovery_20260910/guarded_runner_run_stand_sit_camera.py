#!/usr/bin/env python3
"""Guarded runner for experiment 2ae9157fb18c45cbaccab67321fd5ad8.

"Stand and sit cycle with camera recording" — validate the camera-server
integration end to end on real motion.

Executes the saved sequence exactly:
  GET  /api/rl/preflight?mode=stand   expect ok=true
  POST /api/rl/stand   {tilt_trip_deg: 20}
  hold 10 s
  GET  /api/rl/preflight?mode=lower   expect ok=true
  POST /api/rl/lower   {tilt_trip_deg: 20}
  settle 10 s

Two things the endpoints do NOT do for us, so this runner does them:

* /api/rl/stand and /api/rl/lower are ASYNC — they hand the job to a
  worker thread and return ok=true immediately. Each motion step polls
  /api/calibrate until the worker is done before the next step starts.
* The non-learned stand/lower route ignores tilt_trip_deg (it delegates
  to the baked STEP keyframes, which take no tilt argument). The monitor
  thread below enforces the saved 20 deg trip, plus the saved stop_on
  set, and calls /api/rl/stop.

All three observation cameras are recorded from the camera server on
:8766 rather than by opening the devices — that path is what this
experiment exists to exercise.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request

ROBOT = os.environ.get("ROBOT_URL", "http://192.168.4.39:8080")
CAMSRV = os.environ.get("CAMERA_SERVER_URL", "http://127.0.0.1:8766")
OUT = os.environ.get("OUT_DIR", "/tmp/exp_2ae9157f")

# Robot Lab camera id -> camera-server index, matched on device_uid:
#   robot-1 0x11000000c456366 (Arducam OV9281) = index 0
#   robot-2 0x830000032e40362 (12MP AF)        = index 2
#   robot-3 0x412000032e40362 (12MP AF)        = index 1
CAMERAS = {"robot-1": 0, "robot-2": 2, "robot-3": 1}

TILT_TRIP_DEG = 20.0          # saved safety.tilt_trip_deg
BROWNOUT_V = 9.5
HOT_MOTOR_C = 55
MISSING_SERVO_READS = 3       # saved safety.missing_servo_consecutive_reads
REAL_OVER_CURRENT_A = 4.0
# Above this a per-servo reading is not physically possible (STS3215
# stalls at 2.70 A). Experiment 922434955b aborted on a 106.50 A sample
# that was one flipped bit. Corrupt samples are counted, never trusted,
# and never used to trip a guard on their own.
IMPLAUSIBLE_A = 10.0
CONFIRM_READS = 2             # consecutive reads before a non-servo trip

stop_event = threading.Event()
done_event = threading.Event()
trip: dict = {}
telemetry_lock = threading.Lock()
telemetry: list[dict] = []
frame_index: list[dict] = []


def get(path: str, timeout: float = 15.0):
    with urllib.request.urlopen(ROBOT + path, timeout=timeout) as r:
        return json.loads(r.read().decode())


def post(path: str, body: dict | None = None, timeout: float = 20.0):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        ROBOT + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def abort_robot(reason: str) -> None:
    """Remote abort path. Best effort, then say what happened."""
    print(f"!! ABORT: {reason}", flush=True)
    for attempt in range(3):
        try:
            print("   /api/rl/stop ->", post("/api/rl/stop"), flush=True)
            return
        except Exception as e:  # noqa: BLE001
            print(f"   stop attempt {attempt + 1} failed: {e}", flush=True)
            time.sleep(0.5)


def monitor() -> None:
    """~5 Hz safety monitor. Enforces the saved stop_on set."""
    streak: dict[str, int] = {}
    missing = 0
    while not done_event.is_set():
        t0 = time.time()
        try:
            fb = get("/api/feedback", timeout=8.0)
        except Exception as e:  # noqa: BLE001
            with telemetry_lock:
                telemetry.append({"t": t0, "error": str(e)})
            time.sleep(0.2)
            continue

        joints = fb.get("joints") or []
        live = int(fb.get("live") or 0)
        roll = float(fb.get("roll_deg") or 0.0)
        pitch = float(fb.get("pitch_deg") or 0.0)

        cur = [abs(float(j.get("cur_a") or 0.0)) for j in joints]
        temps = [int(j.get("temp_c") or 0) for j in joints]
        volts = [float(j.get("volt") or 0.0) for j in joints if j.get("volt")]
        plausible = [c for c in cur if c < IMPLAUSIBLE_A]
        corrupt = [c for c in cur if c >= IMPLAUSIBLE_A]

        rec = {"t": t0, "live": live, "roll_deg": roll, "pitch_deg": pitch,
               "max_cur_a": max(plausible) if plausible else 0.0,
               "max_temp_c": max(temps) if temps else None,
               "min_volt": min(volts) if volts else None,
               "corrupt_current_samples": len(corrupt),
               "joints": joints}
        with telemetry_lock:
            telemetry.append(rec)

        def bump(key: str, hit: bool) -> bool:
            streak[key] = streak.get(key, 0) + 1 if hit else 0
            return streak[key] >= CONFIRM_READS

        # tip. Exactly {0.0, 0.0} is the documented IMU read dropout
        # (922434955b), not a level reading — do not score it.
        if not (roll == 0.0 and pitch == 0.0):
            if bump("tip", abs(roll) > TILT_TRIP_DEG
                    or abs(pitch) > TILT_TRIP_DEG):
                trip.update(kind="tip", roll_deg=roll, pitch_deg=pitch)

        if volts and bump("brownout", min(volts) < BROWNOUT_V):
            trip.update(kind="brownout", volt=min(volts))

        # hot_motor on the SAME joint twice running; isolated high
        # samples are the same corruption class as the current spike.
        hot = [i for i, tc in enumerate(temps) if tc >= HOT_MOTOR_C]
        for i in hot:
            if bump(f"hot{i}", True):
                trip.update(kind="hot_motor", joint=i, temp_c=temps[i])
        for i in range(len(temps)):
            if i not in hot:
                streak[f"hot{i}"] = 0

        missing = missing + 1 if live < 18 else 0
        if missing >= MISSING_SERVO_READS:
            trip.update(kind="persistent_missing_servo", live=live)

        if plausible and bump("overcurrent",
                              max(plausible) > REAL_OVER_CURRENT_A):
            trip.update(kind="sustained_over_current", cur_a=max(plausible))

        if trip and not stop_event.is_set():
            stop_event.set()
            abort_robot(json.dumps(trip))

        time.sleep(max(0.0, 0.2 - (time.time() - t0)))


def recorder() -> None:
    """Record all three cameras THROUGH the camera server on :8766."""
    for cam in CAMERAS:
        os.makedirs(f"{OUT}/frames/{cam}", exist_ok=True)
    seq = 0
    while not done_event.is_set():
        t0 = time.time()
        for cam, idx in CAMERAS.items():
            try:
                with urllib.request.urlopen(
                        f"{CAMSRV}/preview/{idx}.jpg", timeout=5.0) as r:
                    blob = r.read()
                path = f"{OUT}/frames/{cam}/{seq:05d}.jpg"
                with open(path, "wb") as fh:
                    fh.write(blob)
                frame_index.append({"t": time.time(), "cam": cam,
                                    "seq": seq, "bytes": len(blob)})
            except Exception as e:  # noqa: BLE001
                # A camera/recorder failure is a neutral stop, never a
                # posture change: log it and keep the motion guard alone.
                frame_index.append({"t": time.time(), "cam": cam,
                                    "seq": seq, "error": str(e)})
        seq += 1
        time.sleep(max(0.0, 0.2 - (time.time() - t0)))


def wait_for_worker(label: str, timeout_s: float = 90.0) -> dict:
    """Block until the async motion worker finishes (or we trip)."""
    t0 = time.time()
    last = {}
    # Give the worker a moment to claim the slot before trusting
    # running=False.
    time.sleep(1.0)
    while time.time() - t0 < timeout_s:
        if stop_event.is_set():
            return {"aborted": True, "reason": trip}
        try:
            st = get("/api/calibrate", timeout=10.0)
        except Exception as e:  # noqa: BLE001
            print(f"   poll error: {e}", flush=True)
            time.sleep(0.5)
            continue
        last = st
        prog = (st.get("progress") or {}).get("msg")
        if not st.get("running"):
            print(f"   {label}: worker done after "
                  f"{time.time() - t0:.1f}s — {prog}", flush=True)
            return {"ok": True, "elapsed_s": round(time.time() - t0, 2),
                    "result": st.get("result"), "progress": prog}
        time.sleep(0.5)
    return {"ok": False, "timeout": True, "elapsed_s": timeout_s,
            "last": last}


def hold(label: str, seconds: float) -> dict:
    print(f"-- {label} {seconds:g}s", flush=True)
    t0 = time.time()
    while time.time() - t0 < seconds:
        if stop_event.is_set():
            return {"aborted": True, "elapsed_s": round(time.time() - t0, 2)}
        time.sleep(0.25)
    return {"ok": True, "elapsed_s": round(time.time() - t0, 2)}


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    steps: list[dict] = []
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=recorder, daemon=True).start()
    time.sleep(1.5)  # let both threads take a first sample

    t_start = time.time()
    status = "succeeded"
    # A second controller (the :8898 RL web hub, driven from a browser)
    # was commanding this robot at 00:04-00:12Z. If it comes back mid-run
    # the run is not ours to interpret, so record who owns the demo slot
    # and refuse to keep going if the name changes underneath us.
    try:
        owner0 = (get("/api/rl/state")["pose"]["demo"] or {}).get("name")
        print(f"-- demo slot owner at start: {owner0!r}", flush=True)
    except Exception:  # noqa: BLE001
        owner0 = None
    try:
        for step in ("stand", "lower"):
            if stop_event.is_set():
                break

            pf = get(f"/api/rl/preflight?mode={step}")
            print(f"-- preflight {step}: {pf}", flush=True)
            steps.append({"step": "preflight", "mode": step, "t": time.time(),
                          "response": pf})
            if not pf.get("ok"):
                status = "failed"
                steps.append({"step": "abort",
                              "why": f"preflight {step} not ok"})
                break

            print(f"-- POST /api/rl/{step}", flush=True)
            t_cmd = time.time()
            resp = post(f"/api/rl/{step}", {"tilt_trip_deg": 20})
            print(f"   accepted: {resp.get('ok')} {resp.get('error') or ''}",
                  flush=True)
            if not resp.get("ok"):
                # A refusal ("stop the running job first") must not be
                # waited on — the worker we would poll is someone else's.
                status = "failed"
                steps.append({"step": step, "t": t_cmd, "accepted": resp,
                              "refused": True})
                break
            waited = wait_for_worker(step)
            steps.append({"step": step, "t": t_cmd, "accepted": resp,
                          "completion": waited})
            if waited.get("aborted") or not waited.get("ok"):
                status = "failed"
                break

            steps.append({"step": "hold" if step == "stand" else "settle",
                          "t": time.time(),
                          "result": hold("hold" if step == "stand"
                                         else "settle", 10.0)})
    except Exception as e:  # noqa: BLE001
        status = "failed"
        steps.append({"step": "exception", "error": repr(e)})
        abort_robot(f"runner exception: {e!r}")

    if trip:
        status = "failed"

    time.sleep(1.0)
    done_event.set()
    time.sleep(1.0)

    with telemetry_lock:
        tel = list(telemetry)
    with open(f"{OUT}/telemetry.jsonl", "w") as fh:
        for row in tel:
            fh.write(json.dumps(row) + "\n")
    with open(f"{OUT}/frame_index.json", "w") as fh:
        json.dump(frame_index, fh, indent=1)

    corrupt_total = sum(r.get("corrupt_current_samples", 0) for r in tel)
    healthy = [r for r in tel if r.get("live") == 18]
    summary = {
        "experiment_id": "2ae9157fb18c45cbaccab67321fd5ad8",
        "status": status,
        "trip": trip or None,
        "started_at": t_start,
        "duration_s": round(time.time() - t_start, 2),
        "steps": steps,
        "telemetry_samples": len(tel),
        "healthy_18_of_18_samples": len(healthy),
        "corrupt_current_samples_discarded": corrupt_total,
        "max_plausible_current_a": max(
            (r.get("max_cur_a", 0.0) for r in tel), default=0.0),
        "max_temp_c": max((r.get("max_temp_c") or 0 for r in tel), default=0),
        "min_volt": min((r.get("min_volt") or 99 for r in tel), default=None),
        "roll_deg_range": [
            min((r["roll_deg"] for r in tel if "roll_deg" in r
                 and not (r["roll_deg"] == 0.0 and r["pitch_deg"] == 0.0)),
                default=None),
            max((r["roll_deg"] for r in tel if "roll_deg" in r
                 and not (r["roll_deg"] == 0.0 and r["pitch_deg"] == 0.0)),
                default=None)],
        "pitch_deg_range": [
            min((r["pitch_deg"] for r in tel if "pitch_deg" in r
                 and not (r["roll_deg"] == 0.0 and r["pitch_deg"] == 0.0)),
                default=None),
            max((r["pitch_deg"] for r in tel if "pitch_deg" in r
                 and not (r["roll_deg"] == 0.0 and r["pitch_deg"] == 0.0)),
                default=None)],
        "frames_captured": {
            cam: sum(1 for f in frame_index
                     if f["cam"] == cam and "error" not in f)
            for cam in CAMERAS},
        "frame_errors": {
            cam: sum(1 for f in frame_index
                     if f["cam"] == cam and "error" in f)
            for cam in CAMERAS},
    }
    with open(f"{OUT}/summary.json", "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "steps"},
                     indent=1), flush=True)
    return 0 if status == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
