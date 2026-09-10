#!/usr/bin/env python3
"""Guarded runner for experiment 376bea38 (L1 belly-rest radial shear
hysteresis, 6 repeats).

DERIVED FROM the runner that executed d4908236 (L2) and 413d5402 at 03:45Z and
02:58Z the same day, against the same reviewed protocol FAMILY and the same
installed robot revision. Two kinds of change, both deliberate and listed here
so the diff is auditable:

  A. Retarget to L1 -- MOVING_LEG, the hip/knee/yaw joint indices, the
     baseline-temperature key names, the lease owner. Nothing else.

  B. ONE new interlock: /api/errors is now polled LIVE, once a second, and any
     row newer than the pre-run baseline trips the run. The saved plan lists
     "Brownout, any /api/errors row, or any alarm - halt and hold, do not
     retry" as a stop condition, and its analysis dependencies ask for that
     condition to be "watched during the window on a bus-free path ... so the
     saved stop condition is enforced in real time rather than post-hoc, as it
     was not on f477caa8". It is enforceable here because /api/errors is NOT a
     bus scan: web_drive.py serves it by reading the tail of the persisted
     errors.jsonl off disk (web_drive.py, the "/api/errors" branch), and it was
     measured at 0.33-0.54 s over five consecutive calls before arming. The L2
     run's own disclosure assumed it cost ~5-6 s like /api/feedback and so left
     it post-hoc; that assumption was wrong, and this is the correction.
     /api/feedback is still read PRE/POST only, for exactly the reason the L2
     and L5 runs found: it IS a full 18-servo bus scan and dense polling is
     what limped the L5 sibling's first attempt.

Everything else is carried over unchanged: the exclusive command lease held
across the whole window, a lease refusal treated as the plan's
foreign_controller_command_observed stop, the start-pose verification
immediately before the POST, the bus-free three-camera record with its
freshness watchdog, and append-as-you-go JSONL so a killed supervisor still
leaves the evidence.
"""
from __future__ import annotations
import hashlib, json, os, sys, threading, time, urllib.request, urllib.error

ROBOT = os.environ.get("ROBOT_URL", "http://192.168.4.39:8080")
CAMSRV = os.environ.get("CAMERA_SERVER_URL", "http://127.0.0.1:8766")
OUT = os.environ["OUT_DIR"]
PROTOCOL = os.environ["PROTOCOL"]
LABEL = os.environ.get("LABEL", "run")
LEASE_OWNER = os.environ.get("LEASE_OWNER", "guarded-runner-376bea38")

# Robot Lab camera id -> camera-server index (verified against the burned-in
# overlay by the L5 run: robot-1="camera 0", robot-3="camera 1",
# robot-2="camera 2").
CAMERAS = {"robot-1": 0, "robot-3": 1, "robot-2": 2}

MOVING_LEG = "L1"
HIP_J, KNEE_J, YAW_J = 4, 5, 3          # L1 hip/knee/yaw logical joints
KNEE_RISE_TRIP_C = 8.0                  # plan: L1 knee > +8 C over baseline
TEMP_TRIP_C = 55.0
TILT_TRIP_DEG = 10.0
CURRENT_TRIP_A = 3.0
CAMERA_STALL_S = 2.0
START_POSE_TOL_DEG = 3.0
LEASE_TTL_S = 900.0

stop_event = threading.Event(); done_event = threading.Event()
trip: dict = {}
frame_index: list[dict] = []
last_frame_t: dict[str, float] = {}
markers: list[dict] = []
lease_token = ""
_jsonl_lock = threading.Lock()


def jl(name: str, obj: dict) -> None:
    """Append one record to disk immediately (survives a killed supervisor)."""
    with _jsonl_lock:
        try:
            with open(f"{OUT}/{name}.jsonl", "a") as fh:
                fh.write(json.dumps(obj, default=str) + "\n")
                fh.flush()
        except Exception:
            pass


def get(path, timeout=25.0):
    req = urllib.request.Request(ROBOT + path, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def post(path, body=None, timeout=30.0, lease=True):
    hdr = {"Content-Type": "application/json",
           "X-Hexapod-Controller": LEASE_OWNER}
    if lease and lease_token:
        hdr["X-Hexapod-Command-Lease"] = lease_token
    req = urllib.request.Request(
        ROBOT + path, data=json.dumps(body or {}).encode(),
        headers=hdr, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return {"_http": e.code, **json.loads(raw or "{}")}
        except ValueError:
            return {"_http": e.code, "raw": raw[:300]}


def abort_robot(reason: str) -> None:
    print(f"!! ABORT: {reason}", flush=True)
    jl("events", {"t": time.time(), "kind": "abort", "reason": reason})
    for a in range(3):
        try:
            print("   /api/rl/stop ->", post("/api/rl/stop"), flush=True)
            return
        except Exception as e:
            print(f"   stop attempt {a+1} failed: {e}", flush=True)
            time.sleep(0.5)


def mark(label: str, **data):
    try:
        r = post("/api/telemetry", {"action": "mark", "label": label,
                                    "data": data or None}, timeout=15.0)
    except Exception as e:
        r = {"ok": False, "error": str(e)}
    rec = {"t": time.time(), "label": label, "data": data, "ack": r}
    markers.append(rec); jl("markers", rec)
    return rec


def err_baseline() -> str:
    try:
        rows = get("/api/errors", timeout=25.0).get("errors") or []
        return max((str(r.get("ts") or "") for r in rows), default="")
    except Exception:
        return ""


def lease_acquire(reason: str) -> dict:
    global lease_token
    r = post("/api/command-lease/acquire",
             {"owner": LEASE_OWNER, "ttl_s": LEASE_TTL_S, "reason": reason,
              "command_lease": lease_token}, lease=False)
    if r.get("ok"):
        lease_token = r["token"]
    jl("events", {"t": time.time(), "kind": "lease_acquire",
                  "ok": r.get("ok"), "lease": r.get("lease")})
    return r


def lease_watch():
    """Refresh the lease, and treat a refused foreign motion command as the
    plan's `foreign_controller_command_observed` stop.

    ``recent_refusals`` is a persistent ring on the server, so refusals that
    predate this run (e.g. the exclusivity demonstration) must be excluded --
    otherwise the runner aborts on its own history.  Both a snapshot of the
    pre-existing entries and a wall-clock floor are used, because the ring
    keys are timestamps and a clock is not a durable identity on its own.
    """
    try:
        seen = {(r.get("ts"), r.get("path"))
                for r in (get("/api/command-lease", timeout=10.0)
                          .get("recent_refusals") or [])}
    except Exception:
        seen = set()
    floor_iso = os.environ.get("REFUSAL_FLOOR_ISO", "")
    jl("events", {"t": time.time(), "kind": "refusal_baseline",
                  "pre_existing": len(seen), "floor_iso": floor_iso})
    last_refresh = time.monotonic()
    while not done_event.is_set():
        try:
            st = get("/api/command-lease", timeout=10.0)
        except Exception:
            time.sleep(0.5); continue
        if not st.get("held") or st.get("owner") != LEASE_OWNER:
            trip.setdefault("kind", "command_lease_lost")
            trip["lease_state"] = st
        for ref in st.get("recent_refusals") or []:
            key = (ref.get("ts"), ref.get("path"))
            if key in seen:
                continue
            seen.add(key)
            if floor_iso and str(ref.get("ts") or "") <= floor_iso:
                continue
            jl("events", {"t": time.time(), "kind": "foreign_command_refused",
                          "refusal": ref})
            trip.setdefault("kind", "foreign_controller_command_observed")
            trip.setdefault("refusal", ref)
        if trip and not stop_event.is_set():
            stop_event.set(); abort_robot(json.dumps(trip, default=str))
        if time.monotonic() - last_refresh > 120.0:
            lease_acquire("periodic refresh during the guarded run")
            last_refresh = time.monotonic()
        time.sleep(0.5)


def error_watch(base_ts: str):
    """Enforce the plan's `any /api/errors row` stop IN REAL TIME.

    Bus-free by construction: the endpoint reads the tail of the persisted
    errors.jsonl, it never touches the servo bus (web_drive.py).  Polled at
    1 Hz, which is two orders of magnitude below the endpoint's own measured
    cost and cannot starve the runner's position reads.
    """
    seen: set[tuple] = set()
    while not done_event.is_set():
        try:
            rows = get("/api/errors", timeout=20.0).get("errors") or []
        except Exception:
            time.sleep(1.0); continue
        for r in rows:
            ts = str(r.get("ts") or "")
            key = (ts, r.get("seq"), r.get("kind"))
            if key in seen or (base_ts and ts <= base_ts):
                continue
            seen.add(key)
            jl("events", {"t": time.time(), "kind": "api_error_row", "row": r})
            trip.setdefault("kind", "api_errors_row")
            trip.setdefault("error_row", r)
            if not stop_event.is_set():
                stop_event.set(); abort_robot(json.dumps(trip, default=str))
        time.sleep(1.0)


def camera_watchdog():
    streak: dict[str, int] = {}
    while not done_event.is_set():
        now = time.time()
        for cam in CAMERAS:
            lt = last_frame_t.get(cam)
            hit = bool(lt) and (now - lt) > CAMERA_STALL_S
            streak[cam] = streak.get(cam, 0) + 1 if hit else 0
            if streak[cam] >= 2:
                trip.setdefault("kind", "camera_lost")
                trip.update(camera=cam, stale_s=round(now - lt, 2))
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
                rec = {"t": time.time(), "cam": cam, "seq": seq,
                       "bytes": len(blob),
                       "sha256": hashlib.sha256(blob).hexdigest(), "path": p}
                last_frame_t[cam] = rec["t"]
            except Exception as e:
                # A camera/recorder failure is a neutral stop, never a
                # posture transition.
                rec = {"t": time.time(), "cam": cam, "seq": seq,
                       "error": str(e)}
            frame_index.append(rec); jl("frame_index", rec)
        time.sleep(0.5)


def healthy_samples(n=3, tries_max=12, tag="prearm"):
    """n DISTINCT advancing clean 18/18 samples. One incomplete scan is
    telemetry noise, not a fault -- resample, and require them consecutive."""
    got, tries = [], 0
    while len(got) < n and tries < tries_max:
        tries += 1
        try:
            fb = get("/api/feedback", timeout=30.0)
            js = fb.get("joints") or []
        except Exception as e:
            print(f"   {tag} read error: {e}", flush=True)
            time.sleep(1.0); continue
        clean = (len(js) == 18 and int(fb.get("live") or 0) == 18
                 and all(isinstance(j, dict) and j.get("temp_c") is not None
                         and j.get("deg") is not None for j in js))
        if not clean:
            bad = [i for i, j in enumerate(js)
                   if not (isinstance(j, dict) and j.get("temp_c") is not None)]
            print(f"   {tag} sample incomplete (live={fb.get('live')} "
                  f"null={bad}) -- resampling", flush=True)
            got = []
            time.sleep(1.2); continue
        s = {"t": time.time(), "live": 18,
             "roll_deg": fb.get("roll_deg"), "pitch_deg": fb.get("pitch_deg"),
             "max_temp_c": max(j["temp_c"] for j in js),
             "max_cur_a": max(abs(float(j["cur_a"] or 0.0)) for j in js),
             "l1_knee_temp_c": js[KNEE_J]["temp_c"],
             "l1_hip_temp_c": js[HIP_J]["temp_c"],
             "deg": [j["deg"] for j in js],
             "temps_c": [j["temp_c"] for j in js]}
        got.append(s); jl(f"{tag}_samples", s)
        time.sleep(1.2)
    return got, tries


def main() -> int:
    global lease_token
    if os.environ.get("DETACH") == "1":
        # Own process group: a terminal hang-up or a group-wide SIGTERM aimed
        # at the launching shell cannot take the supervisor down mid-run (the
        # L5 sibling lost its runner to exactly that at 00:16:42.191Z).
        try:
            os.setsid()
        except OSError:
            pass
        import signal
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
    os.makedirs(OUT, exist_ok=True)
    proto = json.load(open(PROTOCOL))
    hz = float(proto.get("hz", 10.0))
    q = proto["segments"][0]["q_deg"]
    proto_s = len(q) / hz
    print(f"== {LABEL}: {proto['name']} ticks={len(q)} hz={hz} "
          f"({proto_s:.1f}s)", flush=True)

    os.environ.setdefault(
        "REFUSAL_FLOOR_ISO",
        time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + ".000Z")
    base_err = err_baseline()
    jl("events", {"t": time.time(), "kind": "start", "label": LABEL,
                  "protocol": proto["name"], "baseline_error_ts": base_err})

    # 1) exclusive command path FIRST, so nothing can command into the window
    got = lease_acquire(f"guarded run {LABEL}: {proto['name']}")
    if not got.get("ok"):
        print(f"!! could not take the command lease: {got}", flush=True)
        return 2
    print(f"   command lease held by {LEASE_OWNER}", flush=True)

    try:
        # 2) three advancing healthy 18/18 samples
        pre, tries = healthy_samples(tag="prearm")
        json.dump(pre, open(f"{OUT}/prearm_samples.json", "w"), indent=1)
        if len(pre) < 3:
            print(f"!! no 3 consecutive clean 18/18 samples in {tries} tries "
                  f"-- refusing to arm", flush=True)
            return 2
        knee_base = min(s["l1_knee_temp_c"] for s in pre)
        print(f"   pre-arm 18/18 x3, maxtemp="
              f"{max(s['max_temp_c'] for s in pre)}C, L1 knee baseline "
              f"{knee_base}C, hip {pre[-1]['deg'][HIP_J]:.2f} "
              f"knee {pre[-1]['deg'][KNEE_J]:.2f}", flush=True)

        st0 = get("/api/rl/state")
        if st0.get("bus_quarantined") or not st0.get("bus_available"):
            print("!! bus not available/quarantined -- refusing", flush=True)
            return 2

        # 3) start pose. The runner glides to home_deg from WHEREVER it is,
        #    so a robot standing at POST time would make this a lower.
        worst = max((abs(float(d)), i) for i, d in enumerate(pre[-1]["deg"]))
        if worst[0] > START_POSE_TOL_DEG:
            print(f"!! start pose is not belly_rest_logical_zero: joint "
                  f"{worst[1]} at {worst[0]:.2f} deg (tol "
                  f"{START_POSE_TOL_DEG}) -- refusing", flush=True)
            return 2
        print(f"   start pose verified: worst joint {worst[1]} at "
              f"{worst[0]:.2f} deg of logical zero", flush=True)

        # 4) cameras + supervision
        threading.Thread(target=recorder, daemon=True).start()
        threading.Thread(target=camera_watchdog, daemon=True).start()
        threading.Thread(target=lease_watch, daemon=True).start()
        # Live enforcement starts from a baseline taken HERE, at arming,
        # not from the pre-preflight one: the plan asks for the window to
        # be watched, and our own pre-arm 18-servo /api/feedback scans sit
        # before it.  Any row they produced is still reported afterwards
        # via the base_err diff -- it just does not retro-abort the run.
        arm_err = err_baseline() or base_err
        jl("events", {"t": time.time(), "kind": "error_watch_baseline",
                      "arm_baseline_ts": arm_err,
                      "preflight_baseline_ts": base_err})
        threading.Thread(target=error_watch, args=(arm_err,),
                         daemon=True).start()
        time.sleep(2.0)
        live_cams = [c for c in CAMERAS if last_frame_t.get(c)]
        if len(live_cams) < 3:
            print(f"!! only {live_cams} serving frames -- refusing", flush=True)
            done_event.set()
            return 2
        print(f"   live frames on {sorted(live_cams)}", flush=True)
        mark(f"{LABEL}_pre_run", protocol=proto["name"], hz=hz,
             l1_knee_baseline_c=knee_base)

        if os.environ.get("DRY_STOP") == "1":
            # Zero-motion rehearsal of every gate above: proves the lease,
            # pre-arm, pose check, cameras and markers work before the run
            # that actually moves a leg.
            print("   DRY_STOP=1 -- all preflight gates passed, "
                  "returning before the run POST", flush=True)
            done_event.set()
            json.dump({"ok": True, "dry_stop": True, "prearm": pre,
                       "l1_knee_baseline_c": knee_base,
                       "live_cameras": sorted(live_cams),
                       "start_pose_worst": {"joint": worst[1],
                                            "abs_deg": worst[0]}},
                      open(f"{OUT}/dry_stop.json", "w"), indent=1)
            return 0

        # 5) run
        t_start = time.time()
        resp = post("/api/sysid/run", {"protocol": proto, "force": True},
                    timeout=60.0)
        print(f"   POST /api/sysid/run -> {json.dumps(resp)[:300]}", flush=True)
        jl("events", {"t": time.time(), "kind": "submit", "resp": resp})
        if resp.get("_http") or (not resp.get("ok", True) and resp.get("error")):
            done_event.set()
            json.dump({"ok": False, "stage": "submit", "resp": resp},
                      open(f"{OUT}/result.json", "w"), indent=1)
            return 3

        result = None
        t_proto0 = None
        time.sleep(1.0)
        while True:
            if stop_event.is_set():
                result = {"ok": False, "aborted": True, "trip": trip}
                break
            try:
                st = get("/api/calibrate", timeout=15.0)
            except Exception as e:
                print(f"   poll error: {e}", flush=True)
                time.sleep(0.4); continue
            msg = str((st.get("progress") or {}).get("msg") or "")
            if t_proto0 is None and msg.startswith("seg 1/"):
                t_proto0 = time.time()
                mark("protocol_tick0", progress=msg)
                print(f"   protocol tick0 latched at +"
                      f"{t_proto0 - t_start:.1f}s ({msg[:60]})", flush=True)
            if "TRIP" in msg or msg.startswith("error"):
                trip.update(kind="runner_trip", progress=msg)
                stop_event.set()
                result = {"ok": False, "trip": trip, "progress": msg,
                          "elapsed_s": round(time.time() - t_start, 2)}
                print(f"   runner TRIP: {msg[:140]}", flush=True)
                break
            # Only believe "not running" once the deterministic protocol
            # duration has actually elapsed since tick 0 (the L5 attempt-2
            # bug: a false early finish cut the camera record by 98 s).
            proto_done = (t_proto0 is not None
                          and time.time() - t_proto0 >= proto_s + 3.0)
            if not st.get("running") and (
                    proto_done or time.time() - t_start > proto_s + 120):
                result = {"ok": True,
                          "elapsed_s": round(time.time() - t_start, 2),
                          "t_proto0_offset_s": (round(t_proto0 - t_start, 2)
                                                if t_proto0 else None),
                          "result": st.get("result"), "progress": msg}
                print(f"   worker done after {result['elapsed_s']}s -- "
                      f"{msg[:90]}", flush=True)
                break
            if time.time() - t_start > proto_s + 240:
                abort_robot("supervisor timeout")
                result = {"ok": False, "timeout": True}
                break
            time.sleep(0.15)

        mark(f"{LABEL}_post_run")
        time.sleep(2.0)
        done_event.set()
        time.sleep(0.8)

        post_s, _ = healthy_samples(tag="post")
        json.dump(post_s, open(f"{OUT}/post_samples.json", "w"), indent=1)
        knee_peak = max((s["l1_knee_temp_c"] for s in post_s), default=None)
        knee_rise = (knee_peak - knee_base) if knee_peak is not None else None

        try:
            rows = get("/api/errors", timeout=30.0).get("errors") or []
            new_err = [r for r in rows if str(r.get("ts") or "") > base_err]
        except Exception as e:
            new_err = [{"read_error": str(e)}]
        json.dump(new_err, open(f"{OUT}/new_error_rows.json", "w"), indent=1)

        summary = {
            "label": LABEL, "protocol_name": proto["name"],
            "moving_leg": MOVING_LEG,
            "started_unix": t_start, "result": result, "trip": trip or None,
            "lease_owner": LEASE_OWNER,
            "prearm": pre, "post": post_s,
            "l1_knee_baseline_c": knee_base, "l1_knee_post_peak_c": knee_peak,
            "l1_knee_rise_c": knee_rise,
            "l1_knee_rise_trip_c": KNEE_RISE_TRIP_C,
            "frames_captured": {c: sum(1 for f in frame_index
                                       if f["cam"] == c and "error" not in f)
                                for c in CAMERAS},
            "frame_errors": {c: sum(1 for f in frame_index
                                    if f["cam"] == c and "error" in f)
                             for c in CAMERAS},
            "markers": len(markers),
            "baseline_error_ts": base_err,
            "live_error_watch_baseline_ts": arm_err,
            "new_error_rows": new_err,
            "prearm_tries": tries,
        }
        json.dump(summary, open(f"{OUT}/result.json", "w"), indent=1)
        json.dump(frame_index, open(f"{OUT}/frame_index.json", "w"), indent=1)
        json.dump(markers, open(f"{OUT}/markers.json", "w"), indent=1)
        print(json.dumps({k: v for k, v in summary.items()
                          if k not in ("prearm", "post")}, indent=1)[:2200],
              flush=True)
        return 0 if (result or {}).get("ok") else 1
    finally:
        done_event.set()
        if lease_token:
            r = post("/api/command-lease/release",
                     {"command_lease": lease_token}, lease=False)
            print(f"   lease released -> {json.dumps(r)[:160]}", flush=True)
            jl("events", {"t": time.time(), "kind": "lease_release",
                          "resp": r})


if __name__ == "__main__":
    sys.exit(main())
