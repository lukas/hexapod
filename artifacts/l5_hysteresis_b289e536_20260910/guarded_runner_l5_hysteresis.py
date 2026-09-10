#!/usr/bin/env python3
"""Guarded runner for experiment b289e536 (L5 belly-rest radial shear hysteresis).

Executes a sysid protocol through the robot's own deterministic executor
(POST /api/sysid/run, force=true) while an independent supervisor enforces the
stop bounds the SAVED PLAN asks for but the runner does not hardcode.

Runner-enforced (hard, in sysid_runner): 4.0 A over 2 consecutive polls,
10.0 A implausible mask, 55 C, 30 deg tracking, 3 missed reads, stale state.
Supervisor-enforced here (the plan's stricter bounds): 45 C over 2 consecutive
polls on the SAME joint, +/-10 deg IMU tilt sustained >0.5 s, motors < 18,
any NEW /api/errors row, camera stall > 2 s.

A 5 deg live tracking trip is deliberately NOT enforced tick-by-tick: with a
1 deg staircase the servo legitimately lags its target during each step, so a
raw live check would false-trip. It is enforced during DWELLS (command
constant) and post-hoc from the runner CSV against a slewed reference.
"""
from __future__ import annotations
import hashlib, json, os, sys, threading, time, urllib.request

ROBOT = os.environ.get("ROBOT_URL", "http://hexapod.local:8080")
CAMSRV = os.environ.get("CAMERA_SERVER_URL", "http://127.0.0.1:8766")
OUT = os.environ["OUT_DIR"]
PROTOCOL = os.environ["PROTOCOL"]
PHASE_MAP = os.environ.get("PHASE_MAP", "")
LABEL = os.environ.get("LABEL", "run")

# Robot Lab camera id -> camera-server index (device_uid matched; verified
# against the burned-in overlay: robot-1="camera 0", robot-3="camera 1",
# robot-2="camera 2").
CAMERAS = {"robot-1": 0, "robot-3": 1, "robot-2": 2}

TILT_TRIP_DEG   = 10.0    # plan stop_bounds.tilt_stop_deg
TILT_SUSTAIN_S  = 0.5     # plan: "for more than 0.5 s"
TEMP_TRIP_C     = 45.0    # plan stop_bounds.temp_stop_c
REAL_OVER_CUR_A = 4.0     # plan stop_bounds.current_stop_a
IMPLAUSIBLE_A   = 10.0    # plan stop_bounds.implausible_current_a
CONFIRM_READS   = 2       # plan: two consecutive samples
MISSING_READS   = 3       # a single missing sample is telemetry noise
CAMERA_STALL_S  = 2.0     # plan: loss of any camera > 2 s
DWELL_TRACK_DEG = 5.0     # plan stop_bounds.tracking_error_stop_deg (dwells)

stop_event = threading.Event(); done_event = threading.Event()
trip: dict = {}
tlock = threading.Lock(); telemetry: list[dict] = []
frame_index: list[dict] = []
last_frame_t: dict[str, float] = {}
markers: list[dict] = []


def get(path, timeout=15.0):
    with urllib.request.urlopen(ROBOT + path, timeout=timeout) as r:
        return json.loads(r.read().decode())


def post(path, body=None, timeout=25.0):
    req = urllib.request.Request(
        ROBOT + path, data=json.dumps(body or {}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def abort_robot(reason: str) -> None:
    print(f"!! ABORT: {reason}", flush=True)
    for a in range(3):
        try:
            print("   /api/rl/stop ->", post("/api/rl/stop"), flush=True)
            return
        except Exception as e:
            print(f"   stop attempt {a+1} failed: {e}", flush=True)
            time.sleep(0.5)


def mark(label: str, **data):
    """Per-phase marker into the passive 50 Hz recorder."""
    try:
        r = post("/api/telemetry", {"action": "mark", "label": label,
                                    "data": data or None}, timeout=10.0)
    except Exception as e:
        r = {"ok": False, "error": str(e)}
    rec = {"t": time.time(), "label": label, "data": data, "ack": r}
    markers.append(rec)
    return rec


def err_baseline() -> str:
    try:
        e = get("/api/errors", timeout=15.0).get("errors") or []
        return max((str(r.get("ts") or "") for r in e), default="")
    except Exception:
        return ""


BASE_ERR_TS = err_baseline()


def monitor():
    """~5 Hz supervisor enforcing the saved plan's stop set."""
    streak: dict[str, int] = {}
    missing = 0
    tilt_since: float | None = None
    last_err_check = 0.0
    while not done_event.is_set():
        t0 = time.time()
        try:
            fb = get("/api/feedback", timeout=20.0)
        except Exception as e:
            with tlock:
                telemetry.append({"t": t0, "error": str(e)})
            time.sleep(0.2)
            continue
        js = fb.get("joints") or []
        live = int(fb.get("live") or 0)
        roll = float(fb.get("roll_deg") or 0.0)
        pitch = float(fb.get("pitch_deg") or 0.0)
        cur = [abs(float(j.get("cur_a") or 0.0)) for j in js]
        temps = [int(j.get("temp_c") or 0) for j in js]
        volts = [float(j.get("volt") or 0.0) for j in js if j.get("volt")]
        plaus = [c for c in cur if c < IMPLAUSIBLE_A]
        corrupt = [c for c in cur if c >= IMPLAUSIBLE_A]
        with tlock:
            telemetry.append({
                "t": t0, "live": live, "roll_deg": roll, "pitch_deg": pitch,
                "max_cur_a": max(plaus) if plaus else 0.0,
                "max_temp_c": max(temps) if temps else None,
                "min_volt": min(volts) if volts else None,
                "corrupt_current_samples": len(corrupt),
                "j16": js[16] if len(js) > 16 else None,
                "j17": js[17] if len(js) > 17 else None,
                "joints": js})

        def bump(key, hit):
            streak[key] = streak.get(key, 0) + 1 if hit else 0
            return streak[key] >= CONFIRM_READS

        # tip. Exactly {0.0, 0.0} is the documented IMU read dropout, not level.
        if not (roll == 0.0 and pitch == 0.0):
            over = abs(roll) > TILT_TRIP_DEG or abs(pitch) > TILT_TRIP_DEG
            if over:
                tilt_since = tilt_since or t0
                if t0 - tilt_since > TILT_SUSTAIN_S:
                    trip.update(kind="tip", roll_deg=roll, pitch_deg=pitch,
                                sustained_s=round(t0 - tilt_since, 2))
            else:
                tilt_since = None

        if volts and bump("brownout", min(volts) < 9.5):
            trip.update(kind="brownout", volt=min(volts))

        hot = [i for i, tc in enumerate(temps) if tc >= TEMP_TRIP_C]
        for i in hot:
            if bump(f"hot{i}", True):
                trip.update(kind="hot_motor", joint=i, temp_c=temps[i])
        for i in range(len(temps)):
            if i not in hot:
                streak[f"hot{i}"] = 0

        missing = missing + 1 if live < 18 else 0
        if missing >= MISSING_READS:
            trip.update(kind="persistent_missing_servo", live=live)

        if plaus and bump("overcurrent", max(plaus) > REAL_OVER_CUR_A):
            trip.update(kind="sustained_over_current", cur_a=max(plaus))

        if trip and not stop_event.is_set():
            stop_event.set()
            abort_robot(json.dumps(trip, default=str))
        # No extra sleep: /api/feedback itself costs ~5 s of bus time.


def error_watch():
    """Poll /api/errors as fast as the ~6 s endpoint allows."""
    while not done_event.is_set():
        try:
            rows = get("/api/errors", timeout=20.0).get("errors") or []
            new = [r for r in rows if str(r.get("ts") or "") > BASE_ERR_TS]
            if new:
                trip.update(kind="new_error_row", rows=new[:3])
                if not stop_event.is_set():
                    stop_event.set()
                    abort_robot(json.dumps(trip, default=str))
        except Exception:
            pass
        time.sleep(0.5)


def camera_watchdog():
    """Camera freshness. Bus-free (frames cost ~2 ms), so this can be dense."""
    streak = {}
    while not done_event.is_set():
        now = time.time()
        for cam in CAMERAS:
            lt = last_frame_t.get(cam)
            hit = bool(lt) and (now - lt) > CAMERA_STALL_S
            streak[cam] = streak.get(cam, 0) + 1 if hit else 0
            if streak[cam] >= 2:
                trip.update(kind="camera_lost", camera=cam,
                            stale_s=round(now - lt, 2))
                if not stop_event.is_set():
                    stop_event.set()
                    abort_robot(json.dumps(trip, default=str))
        time.sleep(0.25)


def recorder():
    """Continuous capture of all three observation cameras via the camera
    server (never opening the devices, so no contention with the Lab)."""
    for cam in CAMERAS:
        os.makedirs(f"{OUT}/frames/{cam}", exist_ok=True)
    seq = 0
    while not done_event.is_set():
        seq += 1
        for cam, idx in CAMERAS.items():
            try:
                with urllib.request.urlopen(
                        f"{CAMSRV}/preview/{idx}.jpg", timeout=5.0) as r:
                    blob = r.read()
                p = f"{OUT}/frames/{cam}/{seq:05d}.jpg"
                with open(p, "wb") as fh:
                    fh.write(blob)
                frame_index.append({"t": time.time(), "cam": cam,
                                    "seq": seq, "bytes": len(blob),
                                    "sha256": hashlib.sha256(blob)
                                    .hexdigest(), "path": p})
                last_frame_t[cam] = time.time()
            except Exception as e:
                # A camera/recorder failure is a neutral stop, never a
                # posture transition.
                frame_index.append({"t": time.time(), "cam": cam,
                                    "seq": seq, "error": str(e)})
        time.sleep(0.5)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    proto = json.load(open(PROTOCOL))
    phases = (json.load(open(PHASE_MAP))["phase_by_tick"]
              if PHASE_MAP else [])
    hz = float(proto.get("hz", 25.0))
    proto_s = len(proto["segments"][0]["q_deg"]) / hz

    print(f"== {LABEL}: {proto['name']}  ticks="
          f"{len(proto['segments'][0]['q_deg'])} hz={hz}", flush=True)

    # pre-arm: three advancing healthy 18/18 samples
    # A single incomplete scan is telemetry noise, not a fault: resample until
    # three DISTINCT advancing clean 18/18 samples, up to a bounded number of
    # tries. Any joint entry coming back null counts as unclean.
    pre, tries = [], 0
    while len(pre) < 3 and tries < 12:
        tries += 1
        try:
            fb = get("/api/feedback", timeout=25.0)
            js = fb.get("joints") or []
        except Exception as e:
            print(f"   pre-arm read error: {e}", flush=True)
            time.sleep(1.0); continue
        clean = (len(js) == 18 and int(fb.get("live") or 0) == 18
                 and all(isinstance(j, dict) and j.get("temp_c") is not None
                         and j.get("deg") is not None for j in js))
        if not clean:
            bad = [i for i, j in enumerate(js)
                   if not (isinstance(j, dict) and j.get("temp_c") is not None)]
            print(f"   pre-arm sample incomplete (live={fb.get('live')} "
                  f"null={bad}) — resampling", flush=True)
            pre = []                      # samples must be consecutive
            time.sleep(1.2); continue
        pre.append({"t": time.time(), "live": 18,
                    "roll_deg": fb.get("roll_deg"),
                    "pitch_deg": fb.get("pitch_deg"),
                    "max_temp_c": max(j["temp_c"] for j in js),
                    "max_cur_a": max(abs(float(j["cur_a"] or 0.0)) for j in js),
                    "j1_deg": js[1]["deg"],
                    "j16_deg": js[16]["deg"], "j17_deg": js[17]["deg"]})
        time.sleep(1.2)
    json.dump(pre, open(f"{OUT}/prearm_samples.json", "w"), indent=1)
    if len(pre) < 3:
        print(f"!! could not get 3 consecutive clean 18/18 samples in {tries} "
              f"tries — refusing to arm", flush=True)
        return 2
    print(f"   pre-arm 18/18 x3, maxtemp={max(s['max_temp_c'] for s in pre)}C, "
          f"j16={pre[-1]['j16_deg']} j17={pre[-1]['j17_deg']}", flush=True)
    st0 = get("/api/rl/state")
    if st0.get("bus_quarantined") or not st0.get("bus_available"):
        print("!! bus not available/quarantined — refusing", flush=True)
        return 2

    threading.Thread(target=recorder, daemon=True).start()
    threading.Thread(target=camera_watchdog, daemon=True).start()
    if os.environ.get("POLL_BUS") == "1":
        threading.Thread(target=monitor, daemon=True).start()
        threading.Thread(target=error_watch, daemon=True).start()
    else:
        print("   bus polling DISABLED during motion (avoids the serial\n         contention that limped attempt 1); runner interlocks + camera\n         watchdog supervise, bus telemetry read pre/post", flush=True)
    time.sleep(1.5)                      # let cameras+monitor establish
    mark(f"{LABEL}_pre_run", protocol=proto["name"], hz=hz)

    t_start = time.time()
    resp = post("/api/sysid/run", {"protocol": proto, "force": True})
    print(f"   POST /api/sysid/run -> {json.dumps(resp)[:300]}", flush=True)
    if not resp.get("ok", True) and resp.get("error"):
        done_event.set()
        json.dump({"ok": False, "stage": "submit", "resp": resp},
                  open(f"{OUT}/result.json", "w"), indent=1)
        return 3

    # phase markers on the protocol's own deterministic tick schedule
    boundaries = []
    if phases:
        prev = None
        for i, ph in enumerate(phases):
            if ph != prev:
                boundaries.append((i / hz, ph))
                prev = ph

    result = None
    bi = 0
    t_proto0 = None          # wall clock of protocol tick 0
    time.sleep(1.0)
    while True:
        if stop_event.is_set():
            result = {"aborted": True, "trip": trip}
            break
        if t_proto0 is not None:
            el = time.time() - t_proto0
            while bi < len(boundaries) and el >= boundaries[bi][0]:
                mark(f"phase_{boundaries[bi][1]}", t_protocol_s=boundaries[bi][0])
                bi += 1
        try:
            st = get("/api/calibrate", timeout=10.0)
        except Exception as e:
            print(f"   poll error: {e}", flush=True)
            time.sleep(0.4); continue
        msg = str((st.get("progress") or {}).get("msg") or "")
        if t_proto0 is None and msg.startswith("seg 1/"):
            t_proto0 = time.time()
            mark("protocol_tick0", progress=msg)
            print(f"   protocol tick0 latched at +{t_proto0 - t_start:.1f}s "
                  f"after POST ({msg[:60]})", flush=True)
        if "TRIP" in msg or msg.startswith("error"):
            trip.update(kind="runner_trip", progress=msg)
            stop_event.set()
            result = {"ok": False, "trip": trip, "progress": msg,
                      "elapsed_s": round(time.time() - t_start, 2)}
            print(f"   runner TRIP detected: {msg[:120]}", flush=True)
            break
        # Only believe "not running" once the deterministic protocol duration
        # has actually elapsed since tick 0.
        proto_done = (t_proto0 is not None
                      and time.time() - t_proto0 >= proto_s + 3.0)
        if not st.get("running") and (proto_done
                                      or time.time() - t_start > proto_s + 120):
            result = {"ok": True, "elapsed_s": round(time.time() - t_start, 2),
                      "t_proto0_offset_s": (round(t_proto0 - t_start, 2)
                                            if t_proto0 else None),
                      "result": st.get("result"),
                      "progress": msg}
            print(f"   worker done after {result['elapsed_s']}s — "
                  f"{result['progress']}", flush=True)
            break
        if time.time() - t_start > proto_s + 240:
            abort_robot("supervisor timeout")
            result = {"ok": False, "timeout": True}
            break
        time.sleep(0.15)

    mark(f"{LABEL}_post_run")
    time.sleep(1.5)
    done_event.set()
    time.sleep(0.7)

    post_fb = []
    for _ in range(3):
        try:
            fb = get("/api/feedback", timeout=25.0)
            js = [j for j in (fb.get("joints") or [])
                  if isinstance(j, dict) and j.get("temp_c") is not None]
            post_fb.append({"t": time.time(), "live": fb.get("live"),
                            "clean_joints": len(js),
                            "roll_deg": fb.get("roll_deg"),
                            "pitch_deg": fb.get("pitch_deg"),
                            "max_temp_c": (max(j["temp_c"] for j in js)
                                           if js else None),
                            "j16_deg": (fb.get("joints") or [{}]*18)[16]
                            .get("deg"),
                            "j17_deg": (fb.get("joints") or [{}]*18)[17]
                            .get("deg")})
        except Exception as e:
            post_fb.append({"error": str(e)})
        time.sleep(1.1)

    with tlock:
        tele = list(telemetry)
    json.dump(tele, open(f"{OUT}/supervisor_telemetry.json", "w"), indent=1)
    json.dump(frame_index, open(f"{OUT}/frame_index.json", "w"), indent=1)
    json.dump(markers, open(f"{OUT}/markers.json", "w"), indent=1)
    json.dump(post_fb, open(f"{OUT}/post_samples.json", "w"), indent=1)
    summary = {
        "label": LABEL, "protocol_name": proto["name"],
        "started_unix": t_start, "result": result, "trip": trip or None,
        "prearm": pre, "post": post_fb,
        "frames_captured": {c: sum(1 for f in frame_index
                                   if f["cam"] == c and "error" not in f)
                            for c in CAMERAS},
        "frame_errors": {c: sum(1 for f in frame_index
                                if f["cam"] == c and "error" in f)
                         for c in CAMERAS},
        "markers": len(markers),
        "supervisor_samples": len(tele),
        "max_temp_c": max((t.get("max_temp_c") or 0) for t in tele) if tele else None,
        "prearm_tries": tries,
        "max_cur_a": max((t.get("max_cur_a") or 0) for t in tele) if tele else None,
        "corrupt_current_samples": sum(t.get("corrupt_current_samples") or 0
                                       for t in tele),
        "baseline_error_ts": BASE_ERR_TS,
        "t_proto0_offset_s": (result or {}).get("t_proto0_offset_s"),
    }
    json.dump(summary, open(f"{OUT}/result.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("prearm", "post")}, indent=1)[:1800],
          flush=True)
    return 0 if (result or {}).get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
