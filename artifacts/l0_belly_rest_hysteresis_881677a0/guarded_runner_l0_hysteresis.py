#!/usr/bin/env python3
"""Guarded runner for experiment 881677a0 (L0 belly-rest radial shear
hysteresis, 6 repeats).

DERIVED FROM the runner that executed 9e65cca8 (L1) at 05:08Z and 05:12Z on
2026-09-10, which was itself derived from the d4908236 (L2) runner. Same
reviewed protocol FAMILY, same installed robot revision. Three kinds of
change, all deliberate and listed here so the diff is auditable:

  A. Retarget to L0 -- MOVING_LEG, the hip/knee/yaw joint indices
     (1/2/0 instead of L1's 4/5/3), the baseline-temperature key names,
     the lease owner. Nothing else.

  B. START_POSE_TOL_DEG 3.0 -> 1.0. This saved plan sets
     `preflight.verify_start_pose_within_deg_of_logical_zero: 1.0`, where
     the L1 plan allowed 6.0 (and that runner still gated at 3.0). The
     runner now gates at exactly the plan's number.

  C. ONE new interlock behaviour: the plan's /api/errors stop is written as
     "any new /api/errors row BEYOND a single self-recovered transient
     bus_timing retry". L1's runner halted on the first row of any kind,
     which is stricter than this plan. This runner implements the plan as
     written, and narrowly:

       A row is tolerated at most ONCE per window, and only when all of
       these hold -- kind == "bus_timing", src == "mcu", level != "critical",
       data.reason == "ascii_err" with data.n == 0, and
       mcu_feetech_bus.classify_bare_err_reply() attributes it to a torn
       frame on one of the bridge's two documented reject paths
       (desync_guard / checksum_or_bad_n, see MCU_BARE_ERR_ROWS.md and
       commit c1f8067c). "unattributed" is NOT tolerated.

       Tolerance is provisional until self-recovery is CONFIRMED: within
       SELF_RECOVERY_S the executor's own protocol tick must have advanced
       and /api/rl/state must still report the bus available and not
       quarantined. If either fails, the run halts on the original row.

       A second bus_timing row, or any row of any other kind, halts
       immediately -- exactly as L1 did.

     Everything the tolerated row touches is still recorded and reported;
     tolerating it is a decision about halting, not about disclosure.

Everything else is carried over unchanged: the exclusive command lease held
across the whole window, a lease refusal treated as the plan's
foreign_controller_command_observed stop, /api/errors polled live at 1 Hz on
the bus-free path (it reads the tail of the persisted errors.jsonl, it never
scans the servo bus), /api/feedback read PRE/POST only because it IS a full
18-servo bus scan and dense polling is what limped the L5 sibling, the
start-pose verification immediately before the POST, the bus-free
three-camera record with its freshness watchdog, and append-as-you-go JSONL
so a killed supervisor still leaves the evidence.

Realtime-vs-post-hoc stop coverage is declared in advance in
preflight_declaration.json, per analysis_dependencies[5].
"""
from __future__ import annotations
import hashlib, json, os, sys, threading, time, urllib.request, urllib.error

LINUX_CONTROL_DIR = os.environ.get(
    "LINUX_CONTROL_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                 "hexapod_walker", "prototype_sts3215", "linux_control"))


def _load_bare_err_classifier():
    """Load the reviewed bare-ERR classifier from linux_control, or None.

    `mcu_feetech_bus` imports `feetech_bus`, which only exists on the robot,
    so the module cannot be imported here.  Rather than restate its timing
    bands -- which would be a second copy free to drift from the reviewed
    one -- lift `classify_bare_err_reply` and the three MCU_* constants it
    reads straight out of that file's source by AST.

    Returns None if anything about the extraction is not exactly as
    expected.  A None classifier means NO /api/errors row is tolerable and
    the runner halts on the first one, which is the stricter L1 behaviour.
    """
    import ast
    try:
        src = open(os.path.join(LINUX_CONTROL_DIR,
                                "mcu_feetech_bus.py")).read()
        tree = ast.parse(src)
        wanted_c = {"MCU_DESYNC_GUARD_MS", "MCU_FB_PERIOD_MS",
                    "MCU_ERR_BAND_TOL_MS"}
        keep = [n for n in tree.body
                if (isinstance(n, ast.Assign)
                    and any(getattr(t, "id", None) in wanted_c
                            for t in n.targets))
                or (isinstance(n, ast.FunctionDef)
                    and n.name == "classify_bare_err_reply")]
        names = {getattr(t, "id", None) for n in keep
                 if isinstance(n, ast.Assign) for t in n.targets}
        if wanted_c - names or not any(isinstance(n, ast.FunctionDef)
                                       for n in keep):
            return None
        ns: dict = {}
        exec(compile(ast.Module(body=keep, type_ignores=[]),
                     "mcu_feetech_bus(extract)", "exec"), ns)
        fn = ns.get("classify_bare_err_reply")
        # Prove the extraction against the bands commit c1f8067c pinned.
        if not (fn(12.904, ["ERR"]).get("mcu_frame_reject_path")
                == "desync_guard"
                and fn(104.0, ["ERR"]).get("mcu_torn_frame_suspected")
                and fn(400.0, ["ERR"]).get("mcu_frame_reject_path")
                == "unattributed"
                and not fn(12.9, ["ERR wake"]).get("mcu_reply_err_bare")):
            return None
        return fn
    except Exception:
        return None


classify_bare_err_reply = _load_bare_err_classifier()

ROBOT = os.environ.get("ROBOT_URL", "http://192.168.4.39:8080")
CAMSRV = os.environ.get("CAMERA_SERVER_URL", "http://127.0.0.1:8766")
OUT = os.environ["OUT_DIR"]
PROTOCOL = os.environ["PROTOCOL"]
LABEL = os.environ.get("LABEL", "run")
LEASE_OWNER = os.environ.get("LEASE_OWNER", "guarded-runner-881677a0")

# Robot Lab camera id -> camera-server index (verified against the burned-in
# overlay by the L5 run: robot-1="camera 0", robot-3="camera 1",
# robot-2="camera 2").
CAMERAS = {"robot-1": 0, "robot-3": 1, "robot-2": 2}

MOVING_LEG = "L0"
HIP_J, KNEE_J, YAW_J = 1, 2, 0          # L0 hip/knee/yaw logical joints
KNEE_RISE_TRIP_C = 8.0                  # plan: L0 knee > +8 C over baseline
TEMP_TRIP_C = 55.0
TILT_TRIP_DEG = 10.0
CURRENT_TRIP_A = 3.0
CAMERA_STALL_S = 2.0
START_POSE_TOL_DEG = 1.0
LEASE_TTL_S = 900.0
# Plan: "any new /api/errors row BEYOND a single self-recovered
# transient bus_timing retry".  At most this many, narrowly qualified.
TOLERATED_BUS_TIMING_ROWS = 1
SELF_RECOVERY_S = 4.0                   # tick must advance within this
# Chassis-tag-versus-floor-tags watch.  The plan makes it conditional on the
# arena lighting being restored; it is, so it is enabled.  Thresholds are set
# from a measured 40 s at-rest baseline (tagwatch_baseline.json: max radial
# excursion 39.7 mm, yaw ptp 3.7 deg, 17/40 samples resolved), roughly 3x the
# observed noise, and require 3 CONSECUTIVE resolved samples over the bound so
# one bad detection cannot abort the run.
CHASSIS_TAG_ID = "0"
CHASSIS_SHIFT_TRIP_MM = 120.0
CHASSIS_YAW_TRIP_DEG = 15.0
CHASSIS_TRIP_STREAK = 3

stop_event = threading.Event(); done_event = threading.Event()
trip: dict = {}
frame_index: list[dict] = []
last_frame_t: dict[str, float] = {}
markers: list[dict] = []
lease_token = ""
tolerated_rows: list[dict] = []
tag_samples: list[dict] = []
# Written by the main poll loop, read by error_watch() to confirm that
# the executor's own protocol stream kept advancing across a tolerated row.
progress_state: dict = {"tick": -1, "t": 0.0, "msg": "", "running": None,
                        "csv_name": None, "csv_bytes": None, "csv_t": 0.0}
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


def _tolerable_bus_timing(row: dict) -> tuple[bool, dict]:
    """Is this row the ONE transient bus_timing retry the plan allows?

    Narrow by construction. Everything the plan did not name -- a different
    kind, a different source, a critical level, a framed (n>0) transaction,
    or a wait the reviewed classifier cannot attribute to one of the two
    documented torn-frame reject paths -- is NOT tolerable and halts.
    """
    why: dict = {}
    data = row.get("data") or {}
    why["kind"] = row.get("kind")
    why["src"] = row.get("src")
    why["level"] = row.get("level")
    why["reason"] = data.get("reason")
    why["n"] = data.get("n")
    if row.get("kind") != "bus_timing":
        why["verdict"] = "not a bus_timing row"
        return False, why
    if row.get("src") != "mcu":
        why["verdict"] = "bus_timing but not the host-MCU path"
        return False, why
    if str(row.get("level") or "") == "critical":
        why["verdict"] = "critical level is never a transient"
        return False, why
    if data.get("reason") != "ascii_err" or data.get("n") not in (0, None):
        why["verdict"] = "not the bare-ERR n=0 signature"
        return False, why
    if classify_bare_err_reply is None:
        why["verdict"] = ("reviewed bare-ERR classifier unavailable; "
                          "no row is tolerable")
        return False, why
    cls = classify_bare_err_reply(data.get("first_byte_wait_ms"),
                                  data.get("pre_a5_lines") or [])
    why["classifier"] = cls
    if not cls.get("mcu_reply_err_bare"):
        why["verdict"] = "not a bare ERR reply"
        return False, why
    if not cls.get("mcu_torn_frame_suspected"):
        why["verdict"] = (f"reject path "
                          f"{cls.get('mcu_frame_reject_path')!r} is not an "
                          f"attributed torn frame")
        return False, why
    if len(tolerated_rows) >= TOLERATED_BUS_TIMING_ROWS:
        why["verdict"] = (f"already tolerated "
                          f"{len(tolerated_rows)} row(s) this window; the "
                          f"plan allows {TOLERATED_BUS_TIMING_ROWS}")
        return False, why
    why["verdict"] = "tolerable pending confirmed self-recovery"
    return True, why


def _self_recovered() -> tuple[bool, dict]:
    """Confirm the executor kept going after a tolerated /api/errors row.

    Primary signal: the on-robot sysid CSV keeps GROWING (csv_watch), i.e.
    the executor's own 10 Hz command/read loop is still turning.  If the CSV
    does not exist yet -- the row landed during the pre-run glide -- fall
    back to the worker still reporting `running` with no TRIP in its message.
    Either way the bus must still be available and not quarantined.
    """
    base_bytes = progress_state.get("csv_bytes")
    deadline = time.monotonic() + SELF_RECOVERY_S
    grew = False
    while time.monotonic() < deadline and not done_event.is_set():
        cur = progress_state.get("csv_bytes")
        if cur is not None and (base_bytes is None or cur > base_bytes):
            grew = True
            break
        time.sleep(0.2)
    ev = {"csv_name": progress_state.get("csv_name"),
          "csv_bytes_at_row": base_bytes,
          "csv_bytes_after": progress_state.get("csv_bytes"),
          "csv_grew": grew}
    if grew:
        ev["signal"] = "csv_growth"
        advancing = True
    else:
        # No CSV yet (glide) or it stalled -- fall back to worker liveness.
        msg = str(progress_state.get("msg") or "")
        running = progress_state.get("running")
        ev["signal"] = "executor_running"
        ev["running"] = running
        ev["progress_msg"] = msg[:160]
        advancing = bool(running) and "TRIP" not in msg and (
            not msg.startswith("error"))
        if base_bytes is not None:
            # The CSV existed and did NOT grow: that is a stall, and the
            # fallback must not paper over it.
            ev["signal"] = "csv_stalled"
            advancing = False
    try:
        st = get("/api/rl/state", timeout=15.0)
        ev["bus_available"] = bool(st.get("bus_available"))
        ev["bus_quarantined"] = bool(st.get("bus_quarantined"))
    except Exception as e:
        ev["bus_state_error"] = str(e)
        ev["bus_available"] = False
        ev["bus_quarantined"] = True
    ok = advancing and ev.get("bus_available") and not ev.get("bus_quarantined")
    ev["self_recovered"] = bool(ok)
    return bool(ok), ev


def error_watch(base_ts: str):
    """Enforce the plan's /api/errors stop IN REAL TIME.

    Bus-free by construction: the endpoint reads the tail of the persisted
    errors.jsonl, it never touches the servo bus (web_drive.py).  Polled at
    1 Hz, which is two orders of magnitude below the endpoint's own measured
    cost and cannot starve the runner's position reads.

    The plan allows exactly one self-recovered transient bus_timing retry;
    see _tolerable_bus_timing / _self_recovered and the module docstring.
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
            tolerable, why = _tolerable_bus_timing(r)
            if tolerable:
                ok, ev = _self_recovered()
                rec = {"t": time.time(), "row": r, "why": why,
                       "recovery": ev, "tolerated": ok}
                jl("events", {"t": time.time(),
                              "kind": ("api_error_row_tolerated" if ok
                                       else "api_error_row_not_recovered"),
                              **rec})
                if ok:
                    tolerated_rows.append(rec)
                    print(f"   /api/errors row TOLERATED (plan allows one "
                          f"self-recovered transient bus_timing): "
                          f"{r.get('msg')} -- recovery via "
                          f"{ev.get('signal')}",
                          flush=True)
                    continue
                why = dict(why, verdict="tolerable row did NOT self-recover")
                trip.setdefault("recovery", ev)
            trip.setdefault("kind", "api_errors_row")
            trip.setdefault("error_row", r)
            trip.setdefault("tolerance_check", why)
            if not stop_event.is_set():
                stop_event.set(); abort_robot(json.dumps(trip, default=str))
        time.sleep(1.0)


def sysid_csv_names(proto_name: str) -> set[str]:
    """Names of this protocol's CSVs already on the robot. Bus-free."""
    prefix = f"sysid_{proto_name}_"
    try:
        listing = get("/api/logs", timeout=20.0)
    except Exception:
        return set()
    files = listing.get("files") or listing.get("logs") or []
    return {str(f.get("name")) for f in files if isinstance(f, dict)
            and str(f.get("name", "")).startswith(prefix)
            and str(f.get("name", "")).endswith(".csv")}


def csv_watch(proto_name: str, pre_existing: set[str]):
    """Track the growing on-robot sysid CSV as a BUS-FREE liveness signal.

    /api/logs is a directory stat (web_drive.py: `f.stat()` per entry) -- it
    never touches the servo bus.  The executor flushes the CSV once per
    second (every `int(hz)` ticks), so its size advancing is direct evidence
    that the 10 Hz command/read loop is still turning.  This is what
    _self_recovered() checks after a tolerated /api/errors row; the sysid
    progress message only fires at segment boundaries and this protocol has
    exactly one segment, so it cannot serve as a liveness signal.

    The run's own CSV is identified as the newest name NOT in the pre-arm
    snapshot, rather than by a timestamp floor: the stamp in the filename is
    the ROBOT's local clock, which is not this supervisor's.
    """
    prefix = f"sysid_{proto_name}_"
    while not done_event.is_set():
        try:
            listing = get("/api/logs", timeout=15.0)
            files = listing.get("files") or listing.get("logs") or []
            cands = [f for f in files
                     if isinstance(f, dict)
                     and str(f.get("name", "")).startswith(prefix)
                     and str(f.get("name", "")).endswith(".csv")
                     and str(f.get("name")) not in pre_existing]
            if cands:
                newest = max(cands, key=lambda f: str(f.get("name")))
                progress_state.update(csv_name=newest.get("name"),
                                      csv_bytes=int(newest.get("bytes") or 0),
                                      csv_t=time.time())
        except Exception:
            pass
        time.sleep(1.0)


def tag_watch(base_xy: tuple[float, float] | None, base_yaw: float | None):
    """Watch the chassis tag against the floor-tag world frame.

    Bus-free: /api/pose-state is served by the LOCAL camera server from its
    own AprilTag pass; it never touches the robot's servo bus, so this adds
    no bus load at all (analysis_dependencies[5]).

    The plan's stop is "the chassis tag moving relative to the floor tags in
    any camera when tags are resolvable".  Tags are resolvable this run, so
    it is enforced -- but only as a GROSS-motion bound: the measured at-rest
    scatter of this tag is ~40 mm / ~4 deg, so a trip is set at 120 mm /
    15 deg over 3 consecutive resolved samples.  Fine stillness is answered
    by the joint telemetry, as the plan itself says it was for L2.
    """
    streak = 0
    while not done_event.is_set():
        try:
            with urllib.request.urlopen(CAMSRV + "/api/pose-state",
                                        timeout=8.0) as r:
                d = json.loads(r.read().decode())
            m = ((d.get("camera_pose") or {}).get("markers")
                 or {}).get(CHASSIS_TAG_ID)
        except Exception:
            time.sleep(1.0); continue
        if not m or m.get("status") != "tracked":
            rec = {"t": time.time(), "resolved": False}
            tag_samples.append(rec); jl("tag_watch", rec)
            time.sleep(1.0); continue
        pos = m.get("position_mm") or {}
        yaw = (m.get("rotation_degrees") or {}).get("yaw")
        rec = {"t": time.time(), "resolved": True,
               "x": pos.get("x"), "y": pos.get("y"), "yaw": yaw,
               "err95_mm": (m.get("error_95_estimate") or {}).get(
                   "position_mm"),
               "cams": m.get("camera_indices")}
        over = False
        if base_xy and pos.get("x") is not None:
            rec["shift_mm"] = round(((pos["x"] - base_xy[0]) ** 2
                                     + (pos["y"] - base_xy[1]) ** 2) ** 0.5, 2)
            over = rec["shift_mm"] > CHASSIS_SHIFT_TRIP_MM
        if base_yaw is not None and yaw is not None:
            dy = abs((yaw - base_yaw + 180.0) % 360.0 - 180.0)
            rec["yaw_delta_deg"] = round(dy, 2)
            over = over or dy > CHASSIS_YAW_TRIP_DEG
        streak = streak + 1 if over else 0
        rec["over_bound_streak"] = streak
        tag_samples.append(rec); jl("tag_watch", rec)
        if streak >= CHASSIS_TRIP_STREAK:
            trip.setdefault("kind", "chassis_tag_moved_vs_floor_tags")
            trip.setdefault("tag_sample", rec)
            if not stop_event.is_set():
                stop_event.set(); abort_robot(json.dumps(trip, default=str))
        time.sleep(1.0)


def chassis_tag_baseline(n=12):
    """Resolved chassis-tag samples at rest, for the tag_watch reference."""
    got = []
    for _ in range(n):
        try:
            with urllib.request.urlopen(CAMSRV + "/api/pose-state",
                                        timeout=8.0) as r:
                d = json.loads(r.read().decode())
            m = ((d.get("camera_pose") or {}).get("markers")
                 or {}).get(CHASSIS_TAG_ID)
            if m and m.get("status") == "tracked":
                got.append({"x": m["position_mm"]["x"],
                            "y": m["position_mm"]["y"],
                            "yaw": (m.get("rotation_degrees") or {}).get("yaw")})
        except Exception:
            pass
        time.sleep(0.6)
    if not got:
        return None, None, got
    bx = sum(g["x"] for g in got) / len(got)
    by = sum(g["y"] for g in got) / len(got)
    ys = [g["yaw"] for g in got if g["yaw"] is not None]
    return (bx, by), (sum(ys) / len(ys) if ys else None), got


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
             "l0_knee_temp_c": js[KNEE_J]["temp_c"],
             "l0_hip_temp_c": js[HIP_J]["temp_c"],
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
        knee_base = min(s["l0_knee_temp_c"] for s in pre)
        print(f"   pre-arm 18/18 x3, maxtemp="
              f"{max(s['max_temp_c'] for s in pre)}C, L0 knee baseline "
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
        # Bus-free liveness for the tolerated-row self-recovery check.
        pre_csvs = sysid_csv_names(proto["name"])
        jl("events", {"t": time.time(), "kind": "csv_watch_baseline",
                      "pre_existing_csvs": sorted(pre_csvs)})
        threading.Thread(target=csv_watch,
                         args=(proto["name"], pre_csvs),
                         daemon=True).start()
        # Chassis-tag-vs-floor-tags watch: the plan enables it when the arena
        # lighting makes the tags resolvable.  It is bus-free (local camera
        # server), so an unresolvable tag costs nothing and simply records
        # the condition as unmeasured.
        tag_base_xy, tag_base_yaw, tag_base = chassis_tag_baseline()
        jl("events", {"t": time.time(), "kind": "chassis_tag_baseline",
                      "resolved_samples": len(tag_base),
                      "base_xy_mm": tag_base_xy, "base_yaw_deg": tag_base_yaw,
                      "shift_trip_mm": CHASSIS_SHIFT_TRIP_MM,
                      "yaw_trip_deg": CHASSIS_YAW_TRIP_DEG})
        json.dump({"resolved": len(tag_base), "samples": tag_base,
                   "base_xy_mm": tag_base_xy, "base_yaw_deg": tag_base_yaw},
                  open(f"{OUT}/chassis_tag_baseline.json", "w"), indent=1)
        if tag_base_xy is None:
            print("   chassis tag NOT resolvable -- the tag watch records "
                  "the condition as unmeasured (plan allows this)", flush=True)
        else:
            print(f"   chassis tag baseline from {len(tag_base)} resolved "
                  f"samples at ({tag_base_xy[0]:.0f}, {tag_base_xy[1]:.0f}) mm"
                  f", yaw {tag_base_yaw:.1f} deg", flush=True)
        threading.Thread(target=tag_watch,
                         args=(tag_base_xy, tag_base_yaw),
                         daemon=True).start()
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
             l0_knee_baseline_c=knee_base)

        if os.environ.get("DRY_STOP") == "1":
            # Zero-motion rehearsal of every gate above: proves the lease,
            # pre-arm, pose check, cameras and markers work before the run
            # that actually moves a leg.
            print("   DRY_STOP=1 -- all preflight gates passed, "
                  "returning before the run POST", flush=True)
            done_event.set()
            json.dump({"ok": True, "dry_stop": True, "prearm": pre,
                       "l0_knee_baseline_c": knee_base,
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
            prog = st.get("progress") or {}
            msg = str(prog.get("msg") or "")
            # Shared with error_watch(): a tolerated /api/errors row is only
            # treated as self-recovered if this tick keeps advancing.
            try:
                _tk = int(prog.get("tick"))
            except (TypeError, ValueError):
                _tk = progress_state.get("tick", -1)
            progress_state.update(msg=msg, t=time.time(),
                                  running=bool(st.get("running")))
            if _tk > progress_state.get("tick", -1):
                progress_state.update(tick=_tk)
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
        knee_peak = max((s["l0_knee_temp_c"] for s in post_s), default=None)
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
            "l0_knee_baseline_c": knee_base, "l0_knee_post_peak_c": knee_peak,
            "l0_knee_rise_c": knee_rise,
            "l0_knee_rise_trip_c": KNEE_RISE_TRIP_C,
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
            "chassis_tag_watch": {
                "enabled": tag_base_xy is not None,
                "baseline_xy_mm": tag_base_xy,
                "baseline_yaw_deg": tag_base_yaw,
                "baseline_resolved_samples": len(tag_base),
                "shift_trip_mm": CHASSIS_SHIFT_TRIP_MM,
                "yaw_trip_deg": CHASSIS_YAW_TRIP_DEG,
                "samples": len(tag_samples),
                "resolved_samples": sum(1 for r in tag_samples
                                        if r.get("resolved")),
                "max_shift_mm": max((r["shift_mm"] for r in tag_samples
                                     if "shift_mm" in r), default=None),
                "max_yaw_delta_deg": max((r["yaw_delta_deg"]
                                          for r in tag_samples
                                          if "yaw_delta_deg" in r),
                                         default=None),
            },
            "tolerated_error_rows": tolerated_rows,
            "tolerated_error_rows_allowance": TOLERATED_BUS_TIMING_ROWS,
            "final_protocol_tick": progress_state.get("tick"),
            "prearm_tries": tries,
        }
        json.dump(summary, open(f"{OUT}/result.json", "w"), indent=1)
        json.dump(frame_index, open(f"{OUT}/frame_index.json", "w"), indent=1)
        json.dump(markers, open(f"{OUT}/markers.json", "w"), indent=1)
        json.dump(tag_samples, open(f"{OUT}/tag_watch.json", "w"), indent=1)
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
