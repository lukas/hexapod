#!/usr/bin/env python3
"""Stand-up hold: hip-yield repeatability and stance load/current capture.

Guarded driver for plan standup-hold-yield-repeatability-01
(experiment 51f54beb522d482a930aa750ed95368b).

Adapted from the parent experiment's sealed run_cycles.py
(922434955b35404198907c9e77cde5f6) for the longer hold and the denser
per-leg sampling this plan asks for:

  * 3 cycles, 15 s standing hold (parent: 4 cycles, 5 s).
  * The hold is sampled with /api/feedback, the one-round-trip bulk
    endpoint that returns per-joint deg/load_pct/current_a/temp_c AND
    IMU roll/pitch together. /api/status needs a full scan and is ~6 s
    on this bus; /api/feedback is ~5 s, so the hold gets ~3 live
    samples. The plan's finer points (hold entry, +1, +2 s) come from
    the robot's own 50 Hz recorder, which is the instrument the plan
    names -- every /api/feedback poll lands a `feedback` record with
    load_pct/current_a in it, and `snapshot` records carry
    position_deg + IMU continuously. Phase markers index both.
  * The first hold sample is taken the instant the stand-up reports
    done, with no settling sleep, because the yield the plan is chasing
    happened ~1 s after stance in the parent run.
  * Observation frames at pre_run, hold+1s, hold+3s, hold+10s, post_sit.

Stop handling follows EMERGENCY_HANDLING.md rather than limping on
everything: a measurement stop (hip yield over budget, loss of the
middle load-bearing pair) does a CONTROLLED sit-down, because limping
from a standing pose drops the chassis. Only a real hazard -- tip,
brownout, confirmed hot servo, sustained real current, persistent servo
loss, bus fault -- limps immediately with `X`.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import urllib.request

ROBOT = os.environ.get("HEXAPOD_URL", "http://hexapod.local:8080")
LAB = os.environ.get("LAB_URL", "http://127.0.0.1:8767")
OUT = pathlib.Path(__file__).resolve().parent
FRAMES = OUT / "frames"
FRAMES.mkdir(parents=True, exist_ok=True)

EXPERIMENT_ID = "51f54beb522d482a930aa750ed95368b"
PLAN_ID = "standup-hold-yield-repeatability-01"

CYCLES = int(os.environ.get("CYCLES", "3"))
# Continuation support. A concurrent deploy restarted the robot web
# service during cycle 2 of the first attempt; cycle 1 completed and is
# kept. CYCLE_START labels the resumed cycles correctly, and
# CYCLE1_YIELD_JSON seeds the plan's "+8 deg over cycle 1" budget with
# cycle 1's own MEASURED yield rather than re-deriving it here.
CYCLE_START = int(os.environ.get("CYCLE_START", "1"))
_C1Y = os.environ.get("CYCLE1_YIELD_JSON", "").strip()
HOLD_S = float(os.environ.get("HOLD_S", "15"))
MODE = os.environ.get("MODE", "step")
SPEED = float(os.environ.get("SPEED", "10"))
TORQUE = int(os.environ.get("TORQUE", "700"))

# Plan stop bounds.
TEMP_STOP_C = 45.0          # two consecutive samples, same joint
HOT_SERVO_LIMP_C = 55.0     # canonical confirmed-hot-servo limp
CURRENT_STOP_A = 4.0        # two consecutive samples, after plausibility
IMPLAUSIBLE_A = 10.0        # fix A's plausibility bound (STS3215 stalls 2.70)
TILT_STOP_DEG = 15.0
MIDDLE_HIP_STOP_DEG = 5.0   # L1 j4 / L4 j13 departure from command
YIELD_EXCESS_DEG = 8.0      # outer hip yield over cycle 1's own value
IMPLAUSIBLE_FAULT_READS = 3  # same joint, in a row -> bus telemetry fault

# Commanded stance from the step mode's final keyframe
# (linux_control/standup_modes.json, modes.step.keyframes[-1]):
# yaw 0 / hip +20.87 / knee +82.17 on every leg. This is the reference
# yield is measured against. Using the live L1/L4 mean instead would be
# self-referential -- the first HTTP sample lands ~5 s into the hold,
# after the yield window -- and any middle-pair sag would silently
# understate every outer leg's yield.
CMD_HIP_DEG = 20.87
CMD_KNEE_DEG = 82.17
STOOD_KNEE_DEG = 30.0       # knees past this mean the robot is up
KNEE_J = (2, 5, 8, 11, 14, 17)

# joint index -> leg/segment. hips are 1,4,7,10,13,16.
HIP_J = {0: 1, 1: 4, 2: 7, 3: 10, 4: 13, 5: 16}
MIDDLE_HIPS = (4, 13)       # L1 hip, L4 hip
OUTER_LEGS = (0, 2, 3, 5)

LAB_KEY = pathlib.Path("/tmp/.rl_key").read_text().strip()

events: list[dict] = []
log_lines: list[str] = []
record: dict = {}


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    log_lines.append(line)


def flush() -> None:
    """Persist after every phase.

    Two prior jobs on this campaign died mid-flight and lost their
    results; the record must survive this process being killed.
    """
    record["log"] = log_lines
    record["events"] = events
    tmp = OUT / "cycles.json.tmp"
    tmp.write_text(json.dumps(record, indent=1))
    tmp.replace(OUT / "cycles.json")


def req(path: str, payload=None, base: str = ROBOT, timeout: float = 30.0,
        raw: bool = False, headers: dict | None = None):
    url = base + path
    data = None
    hdrs = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode()
        hdrs["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=hdrs,
                               method="POST" if data is not None else "GET")
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        body = resp.read()
    return body if raw else json.loads(body)


def post_cmd(text: str):
    r = urllib.request.Request(ROBOT + "/cmd", data=text.encode(),
                               method="POST")
    with urllib.request.urlopen(r, timeout=15) as resp:
        return resp.read().decode()


def limp(reason: str) -> None:
    """Hard-hazard path: torque off now."""
    log(f"LIMP (hazard): {reason}")
    try:
        req("/api/standup/stop", {})
    except Exception as e:  # noqa: BLE001
        log(f"  standup/stop error: {e}")
    try:
        log(f"  /cmd X -> {post_cmd('X')[:80]}")
    except Exception as e:  # noqa: BLE001
        log(f"  /cmd X error: {e}")
    events.append({"kind": "limp", "reason": reason, "t": time.time()})


def controlled_sit(reason: str) -> dict:
    """Measurement stop: put the robot down under control, keep torque."""
    log(f"CONTROLLED STOP: {reason}")
    events.append({"kind": "controlled_stop", "reason": reason,
                   "t": time.time()})
    try:
        req("/api/standup", {"mode": MODE, "speed": SPEED,
                             "direction": "down", "torque": TORQUE},
            timeout=40)
        done = wait_demo_done(120)
        log(f"  controlled sit-down: "
            f"{str((done.get('progress') or {}).get('msg'))[:120]}")
        return done
    except Exception as e:  # noqa: BLE001
        log(f"  controlled sit failed ({e}) -- escalating to limp")
        limp(f"controlled sit failed after {reason}: {e}")
        return {"error": str(e)}


def mark(label: str, data: dict | None = None) -> str | None:
    try:
        r = req("/api/telemetry", {"action": "mark", "label": label,
                                   "data": data or {}})
        mid = r.get("marker_id") or r.get("id")
        events.append({"kind": "marker", "label": label,
                       "marker_id": mid, "t": time.time()})
        return mid
    except Exception as e:  # noqa: BLE001
        log(f"  mark({label}) failed: {e}")
        return None


def feedback_sample(tag: str) -> dict:
    """One bus round-trip: per-joint deg/load/current/temp + IMU tilt.

    Raw current count is not exposed by the API; current_a is derived on
    the robot from the count at 6.5 mA/count, so the count is recovered
    here by the inverse and labelled derived, not measured.
    """
    t0 = time.time()
    d = req("/api/feedback", timeout=40)
    js = d.get("joints") or []
    joints = {}
    for j, v in enumerate(js):
        if not v:
            continue
        cur = v.get("cur_a")
        joints[j] = {
            "deg": v.get("deg"), "load_pct": v.get("load_pct"),
            "current_a": cur, "temp_c": v.get("temp_c"),
            "volt": v.get("volt"),
            "current_raw_count_derived": (
                None if cur is None else round(float(cur) / 0.0065)),
        }
    return {"tag": tag, "t": t0, "t_unix": d.get("t_unix"),
            "rtt_s": round(time.time() - t0, 2),
            "live": d.get("live"), "roll_deg": d.get("roll_deg"),
            "pitch_deg": d.get("pitch_deg"),
            "body_roll_deg": d.get("body_roll_deg"),
            "body_pitch_deg": d.get("body_pitch_deg"),
            "gyro_dps": d.get("gyro_dps"), "joints": joints}


def contact_snapshot() -> dict:
    t = req("/api/telemetry", timeout=30)
    c = (t.get("contact") or {})
    return {"t": time.time(), "legs": c.get("legs"),
            "planted": c.get("planted"), "ready_legs": c.get("ready_legs"),
            "writer_alive": t.get("writer_alive"),
            "capture_errors": t.get("capture_errors"),
            "queue_dropped": t.get("queue_dropped")}


def pose_snapshot() -> dict:
    st = req("/api/rl/state", timeout=30)
    p = st.get("pose") or {}
    return {"t": time.time(), "degrees": p.get("degrees"),
            "live": p.get("live"), "armed": p.get("armed"),
            "bus_quarantined": st.get("bus_quarantined"),
            "bus_available": st.get("bus_available"),
            "imu_grade": (st.get("imu") or {}).get("grade")}


def grab_frames(tag: str) -> list[str]:
    got = []
    for cam in ("robot-1", "robot-2", "robot-3"):
        dest = FRAMES / f"{tag}_{cam}.jpg"
        try:
            body = req(f"/api/robot-status/cameras/{cam}/frame", base=LAB,
                       raw=True, timeout=25,
                       headers={"Authorization": f"Bearer {LAB_KEY}"})
            if body[:2] == b"\xff\xd8":
                dest.write_bytes(body)
                got.append(dest.name)
            else:
                log(f"  frame {cam} not JPEG ({len(body)}B)")
        except Exception as e:  # noqa: BLE001
            log(f"  frame {cam} failed: {e}")
    return got


# ---------------------------------------------------------------- errors

transient_bus: list[dict] = []
# /api/errors is a rolling buffer capped at 100 entries, so an index
# cursor silently misses events once it wraps. Track by (ts, seq).
seen_error_keys: set = set()


def _err_key(ev: dict):
    return (str(ev.get("ts")), ev.get("seq"))


def prime_errors() -> tuple[int, str]:
    try:
        errs = req("/api/errors", timeout=30).get("errors") or []
    except Exception as ex:  # noqa: BLE001
        log(f"  /api/errors read failed: {ex}")
        return -1, ""
    for ev in errs:
        seen_error_keys.add(_err_key(ev))
    return len(errs), (errs[-1].get("ts") if errs else "")


def check_errors(phase: str) -> tuple[str | None, bool]:
    """Return (stop_reason, is_hazard) from newly seen /api/errors rows."""
    try:
        errs = req("/api/errors", timeout=30).get("errors") or []
    except Exception as ex:  # noqa: BLE001
        log(f"  /api/errors read failed: {ex}")
        return None, False
    for ev in errs:
        k = _err_key(ev)
        if k in seen_error_keys:
            continue
        seen_error_keys.add(k)
        msg = str(ev.get("msg", ""))
        kind = str(ev.get("kind", ""))
        low = msg.lower()
        if "suspect" in low or "logical zero frame looks wrong" in low:
            return f"suspect_zero: {msg[:160]}", True
        if "outside its" in low and "range" in low:
            return f"over_range: {msg[:160]}", True
        if "overtemp" in low or "temperature" in low:
            return f"temperature_warning: {msg[:160]}", True
        if kind == "bus_timing" or "ascii_err" in low or "no_a5" in low:
            try:
                bs = req("/api/bus/status", timeout=25)
            except Exception as ex:  # noqa: BLE001
                return f"bus_error (state unreadable): {msg[:120]} / {ex}", True
            if bs.get("bus_quarantined") or not bs.get("bus_available"):
                return (f"bus_error: quarantined/unavailable after "
                        f"{msg[:120]}"), True
            transient_bus.append({"phase": phase, "msg": msg, "kind": kind,
                                  "ts": ev.get("ts"), "t": time.time()})
            log(f"  transient bus event #{len(transient_bus)} during {phase}"
                f": {msg[:90]} (bus available)")
            if len(transient_bus) >= 3:
                return (f"bus_error: {len(transient_bus)} bus_timing events "
                        f"accumulated (last: {msg[:100]})"), True
            continue
        if kind == "error" and "could not reach" in low:
            return f"error_event({kind}): {msg[:150]}", True
        log(f"  non-fatal error row during {phase}: {kind} {msg[:110]}")
    return None, False


# ------------------------------------------------------- sample checking

# Per-joint consecutive-breach counters (plan: TWO consecutive samples).
hot_streak: dict = {}
cur_streak: dict = {}
hot_limp_streak: dict = {}
imp_streak: dict = {}
discarded: list = []
tilt_since: dict = {"t": None}


def check_sample(s: dict, phase: str) -> tuple[str | None, bool]:
    """Evaluate one /api/feedback sample. Returns (reason, is_hazard)."""
    live = s.get("live")
    if isinstance(live, int) and live < 18:
        return f"persistent servo loss: {live}/18 during {phase}", True

    for j, v in (s.get("joints") or {}).items():
        t = v.get("temp_c")
        if isinstance(t, (int, float)):
            if t >= HOT_SERVO_LIMP_C:
                hot_limp_streak[j] = hot_limp_streak.get(j, 0) + 1
                if hot_limp_streak[j] >= 2:
                    return (f"hot motor: joint {j} at {t} C on "
                            f"{hot_limp_streak[j]} consecutive samples"), True
            else:
                hot_limp_streak[j] = 0
            if t >= TEMP_STOP_C:
                hot_streak[j] = hot_streak.get(j, 0) + 1
                if hot_streak[j] >= 2:
                    return (f"temperature_warning: joint {j} at {t} C on "
                            f"{hot_streak[j]} consecutive samples "
                            f"(plan bound {TEMP_STOP_C:.0f} C)"), False
            else:
                hot_streak[j] = 0

        c = v.get("current_a")
        if isinstance(c, (int, float)):
            a = abs(float(c))
            if a >= IMPLAUSIBLE_A:
                # fix A: physically impossible (STS3215 stalls at 2.70 A),
                # so this is a corrupt read, not an over-current. It is
                # kept out of the trip -- but a joint that returns three
                # in a row is a real bus telemetry fault and still stops
                # the run, with distinct wording, exactly as standup.py
                # does on the robot.
                imp_streak[j] = imp_streak.get(j, 0) + 1
                log(f"  implausible current on joint {j}: {a:.2f} A "
                    f"(>= {IMPLAUSIBLE_A} A) -- discarded, not a trip "
                    f"(streak {imp_streak[j]})")
                v["implausible"] = True
                discarded.append({"joint": j, "current_a": a,
                                  "phase": phase, "t": time.time()})
                if imp_streak[j] >= IMPLAUSIBLE_FAULT_READS:
                    return (f"bus telemetry fault: joint {j} returned "
                            f"{imp_streak[j]} impossible current readings "
                            f"in a row (peak {a:.1f} A) -- not an "
                            f"over-current"), True
                continue
            imp_streak[j] = 0
            if a > CURRENT_STOP_A:
                cur_streak[j] = cur_streak.get(j, 0) + 1
                if cur_streak[j] >= 2:
                    return (f"hard or sustained current: joint {j} at "
                            f"{a:.2f} A on {cur_streak[j]} consecutive "
                            f"plausible samples"), True
            else:
                cur_streak[j] = 0

    roll, pitch = s.get("roll_deg"), s.get("pitch_deg")
    over = False
    for name, val in (("roll", roll), ("pitch", pitch)):
        if isinstance(val, (int, float)) and abs(val) > TILT_STOP_DEG:
            over = True
            log(f"  tilt {name}={val} deg over +/-{TILT_STOP_DEG}")
    now = time.time()
    if over:
        if tilt_since["t"] is None:
            tilt_since["t"] = now
        elif now - tilt_since["t"] > 0.5:
            return (f"tip: roll {roll} / pitch {pitch} deg beyond "
                    f"+/-{TILT_STOP_DEG} for "
                    f"{now - tilt_since['t']:.1f} s"), True
    else:
        tilt_since["t"] = None
    return None, False


def check_hips(s: dict, cmd_hip: float | None, cycle1_yield: dict | None,
               phase: str) -> str | None:
    """Middle-pair loss and outer-hip yield budget. Measurement stops."""
    if cmd_hip is None:
        return None
    js = s.get("joints") or {}
    for jm in MIDDLE_HIPS:
        v = js.get(jm)
        if not v or v.get("deg") is None:
            continue
        dev = abs(float(v["deg"]) - cmd_hip)
        if dev > MIDDLE_HIP_STOP_DEG:
            return (f"loss of the load-bearing middle pair: joint {jm} is "
                    f"{dev:.1f} deg from its commanded {cmd_hip:.2f} deg "
                    f"during {phase}")
    if cycle1_yield:
        for leg in OUTER_LEGS:
            jh = HIP_J[leg]
            v = js.get(jh)
            if not v or v.get("deg") is None:
                continue
            y = cmd_hip - float(v["deg"])
            base = cycle1_yield.get(str(leg), cycle1_yield.get(leg))
            if base is None:
                continue
            if y > base + YIELD_EXCESS_DEG:
                return (f"hip yield out of budget: L{leg} yielded {y:.1f} deg "
                        f"vs cycle-1 {base:.1f} deg "
                        f"(+{YIELD_EXCESS_DEG} deg allowed) during {phase}")
    return None


def wait_demo_done(timeout_s: float = 120.0) -> dict:
    t0 = time.monotonic()
    last: dict = {}
    started = False
    while time.monotonic() - t0 < 15.0:
        try:
            last = req("/api/calibrate", timeout=25)
        except Exception as e:  # noqa: BLE001
            log(f"  calibrate poll error: {e}")
            time.sleep(0.5)
            continue
        if last.get("running"):
            started = True
            break
        time.sleep(0.3)
    if not started:
        log("  NOTE: job never reported running (fast path or refusal); "
            f"progress={str((last.get('progress') or {}).get('msg'))[:90]}")
        last["never_ran"] = True
        return last
    while time.monotonic() - t0 < timeout_s:
        try:
            last = req("/api/calibrate", timeout=25)
        except Exception as e:  # noqa: BLE001
            log(f"  calibrate poll error: {e}")
            time.sleep(1.0)
            continue
        if not last.get("running"):
            return last
        time.sleep(0.4)
    log("  demo poll TIMEOUT")
    last["poll_timeout"] = True
    return last


# ------------------------------------------------------------------ main

def main() -> int:
    base_n, base_last = prime_errors()
    log(f"baseline /api/errors count={base_n} last={base_last}")

    pre = feedback_sample("pre_run")
    mx = max((v.get("temp_c") or 0) for v in pre["joints"].values())
    log(f"pre: live={pre['live']}/18 maxtemp={mx}C "
        f"roll={pre['roll_deg']} pitch={pre['pitch_deg']}")

    record.update({
        "experiment_id": EXPERIMENT_ID, "plan_id": PLAN_ID,
        "mode": MODE, "speed": SPEED, "torque": TORQUE,
        "cycles_requested": CYCLES, "stand_hold_s": HOLD_S,
        "hip_sample_points_s": [0, 1, 2, 5, 10, 15],
        "baseline_error_count": base_n, "baseline_error_last_ts": base_last,
        "stop_bounds": {
            "temp_stop_c": TEMP_STOP_C, "hot_servo_limp_c": HOT_SERVO_LIMP_C,
            "current_stop_a": CURRENT_STOP_A,
            "implausible_current_a": IMPLAUSIBLE_A,
            "tilt_stop_deg": TILT_STOP_DEG,
            "middle_hip_stop_deg": MIDDLE_HIP_STOP_DEG,
            "yield_excess_deg": YIELD_EXCESS_DEG,
        },
        "telemetry_path": None,
        "pre_feedback": pre, "pre_pose": pose_snapshot(),
        "pre_contact": contact_snapshot(),
        "cycles": [], "events": events, "stopped_reason": None,
        "stop_disposition": None, "cycle1_yield_deg": None,
    })
    try:
        record["telemetry_path"] = (req("/api/telemetry", timeout=30)
                                    .get("paths"))
    except Exception as e:  # noqa: BLE001
        log(f"  telemetry path read failed: {e}")
    record["pre_frames"] = grab_frames("pre_run")
    flush()

    reason, hazard = check_sample(pre, "preflight")
    if reason is None:
        reason, hazard = check_errors("preflight")
    if reason:
        log(f"preflight stop: {reason}")
        record["stopped_reason"] = f"preflight: {reason}"
        record["stop_disposition"] = "hazard_limp" if hazard else "no_motion"
        if hazard:
            limp(reason)
        flush()
        return 2

    mark("experiment_start", {"plan": PLAN_ID, "mode": MODE,
                              "cycles": CYCLES, "hold_s": HOLD_S,
                              "cycle_start": CYCLE_START})
    cycle1_yield = None
    if _C1Y:
        cycle1_yield = {int(k): float(v) for k, v in json.loads(_C1Y).items()}
        record["cycle1_yield_deg"] = cycle1_yield
        record["cycle1_yield_source"] = (
            "measured in attempt 1 cycle 1 (00:36:29-00:36:45Z), carried "
            "forward as the reference for the plan's +8 deg yield budget")
        log(f"seeded cycle-1 yield reference: {cycle1_yield}")

    for ci in range(CYCLE_START, CYCLE_START + CYCLES):
        cyc: dict = {"cycle": ci, "hold_samples": [], "frames": {}}
        record["cycles"].append(cyc)
        log(f"=== cycle {ci}/{CYCLES}: stand up ({MODE}) ===")
        cyc["m_up_start"] = mark(f"cycle{ci}_up_start")
        t_up0 = time.time()
        # A transport error is not a robot fault. The canonical emergency
        # handling treats fewer than three consecutive API failures as
        # noise: keep the pose and retry. Attempt 1 limped on a single
        # connection-refused caused by someone else's deploy restarting
        # the web service; harmless there only because the robot was
        # already sitting. Retry first, and if the robot turns out to be
        # standing, sit it down under control rather than dropping it.
        up = None
        last_err = None
        for attempt in range(1, 4):
            try:
                up = req("/api/standup", {"mode": MODE, "speed": SPEED,
                                          "direction": "up",
                                          "torque": TORQUE}, timeout=40)
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
                log(f"  standup up POST attempt {attempt}/3 failed: {e}")
                time.sleep(3.0)
        if up is None:
            cyc["error"] = str(last_err)
            cyc["up_post_attempts"] = 3
            record["stopped_reason"] = (
                f"cycle{ci} up POST failed 3 consecutive attempts: "
                f"{last_err}")
            standing = False
            try:
                probe = feedback_sample(f"c{ci}_transport_fail_probe")
                cyc["transport_fail_probe"] = probe
                knees = [probe["joints"][j]["deg"] for j in KNEE_J
                         if probe["joints"].get(j)
                         and probe["joints"][j].get("deg") is not None]
                standing = bool(knees) and max(knees) > STOOD_KNEE_DEG
            except Exception as e2:  # noqa: BLE001
                log(f"  post-failure probe unreadable: {e2}")
            if standing:
                log("  robot is STANDING after transport failure -- "
                    "controlled sit rather than limp")
                record["stop_disposition"] = "controlled_sit"
                cyc["controlled_sit"] = controlled_sit(
                    f"transport failure while standing: {last_err}")
            else:
                record["stop_disposition"] = "hazard_limp"
                limp(f"standup up POST failed 3x: {last_err}")
            flush()
            break
        cyc["up_ack"] = up
        log(f"  up ack: ok={up.get('ok')} {str(up.get('error') or '')[:140]}")
        done = wait_demo_done(150)
        cyc["up_result"] = done.get("result")
        cyc["up_status_text"] = (done.get("progress") or {}).get("msg")
        cyc["up_seconds"] = round(time.time() - t_up0, 2)
        # fix A evidence: discarded implausible current samples.
        res = done.get("result") or {}
        if isinstance(res, dict):
            cyc["discarded_current_samples"] = res.get(
                "discarded_current_samples")
            cyc["discarded_peak_a"] = res.get("discarded_peak_a")
            cyc["peak_a"] = res.get("peak_a")
        log(f"  up done in {cyc['up_seconds']}s: "
            f"{str(cyc['up_status_text'])[:150]}")
        flush()

        # A refusal and a stand-up that finished between two ~5 s
        # /api/calibrate polls look identical from the poller. Deciding
        # "never ran" on the poll alone can walk away from a robot that
        # is actually standing at torque, so ask the joints.
        if done.get("never_ran") or (up.get("ok") is False):
            probe = feedback_sample(f"c{ci}_up_ambiguous")
            cyc["up_ambiguity_probe"] = probe
            knees = [probe["joints"][j]["deg"] for j in KNEE_J
                     if probe["joints"].get(j)
                     and probe["joints"][j].get("deg") is not None]
            stood = bool(knees) and max(knees) > STOOD_KNEE_DEG
            log(f"  ambiguous stand-up ack; knees={[round(k, 1) for k in knees]}"
                f" -> stood={stood}")
            cyc["up_stood_by_probe"] = stood
            if not stood:
                reason = (f"cycle{ci} stand-up refused / never ran: "
                          f"{str(cyc['up_status_text'])[:140]}")
                log(f"  {reason}")
                record["stopped_reason"] = reason
                record["stop_disposition"] = "no_motion"
                flush()
                break
            log("  robot IS standing -- continuing into the hold rather "
                "than leaving it up at torque")

        # ---- hold: first sample immediately, no settle sleep ----
        hold_t0 = time.time()
        cyc["m_hold_start"] = mark(f"cycle{ci}_hold_start",
                                   {"hold_s": HOLD_S})
        cyc["hold_t0"] = hold_t0
        cmd_hip = CMD_HIP_DEG
        cyc["cmd_hip_deg"] = CMD_HIP_DEG
        cyc["cmd_hip_source"] = (
            "standup_modes.json modes.step.keyframes[-1] hip = +20.87 deg "
            "(commanded stance, all six legs)")
        stop_reason = None
        stop_hazard = False
        frames_done = set()

        while True:
            el = time.time() - hold_t0
            if el >= HOLD_S:
                break
            s = feedback_sample(f"c{ci}_hold_t{el:.1f}")
            s["hold_elapsed_s"] = round(el, 2)
            cyc["hold_samples"].append(s)
            if "middle_pair_mean_at_entry_deg" not in cyc:
                # Recorded as a cross-check on the commanded reference,
                # not used as the reference itself.
                mids = [s["joints"][j]["deg"] for j in MIDDLE_HIPS
                        if s["joints"].get(j)
                        and s["joints"][j].get("deg") is not None]
                if mids:
                    cyc["middle_pair_mean_at_entry_deg"] = round(
                        sum(mids) / len(mids), 2)
            mxt = max((v.get("temp_c") or 0) for v in s["joints"].values())
            mxc = max((abs(v.get("current_a") or 0))
                      for v in s["joints"].values())
            hips = {f"L{leg}": s["joints"].get(HIP_J[leg], {}).get("deg")
                    for leg in range(6)}
            log(f"  hold t={el:5.1f}s live={s['live']}/18 maxT={mxt}C "
                f"maxI={mxc:.2f}A roll={s['roll_deg']} "
                f"pitch={s['pitch_deg']} hips={hips}")
            flush()

            stop_reason, stop_hazard = check_sample(s, f"cycle{ci} hold")
            if stop_reason is None:
                r2 = check_hips(s, cmd_hip, cycle1_yield, f"cycle{ci} hold")
                if r2:
                    stop_reason, stop_hazard = r2, False
            if stop_reason is None:
                stop_reason, stop_hazard = check_errors(f"cycle{ci} hold")
            if stop_reason:
                break

            el = time.time() - hold_t0
            for at, tag in ((1.0, "hold_plus_1s"), (10.0, "hold_plus_10s")):
                if tag not in frames_done and el >= at:
                    # The bus round-trip is ~5 s, so a frame nominally
                    # due at +1 s is really taken later. Record when it
                    # was actually captured so the label cannot mislead.
                    cyc["frames"][tag] = {
                        "nominal_t_rel_s": at,
                        "actual_t_rel_s": round(time.time() - hold_t0, 2),
                        "files": grab_frames(f"c{ci}_{tag}")}
                    frames_done.add(tag)
            flush()

        if stop_reason:
            log(f"  stop during cycle {ci} hold: {stop_reason}")
            cyc["stop_reason"] = stop_reason
            record["stopped_reason"] = f"cycle{ci} hold: {stop_reason}"
            record["stop_disposition"] = (
                "hazard_limp" if stop_hazard else "controlled_sit")
            flush()
            if stop_hazard:
                limp(stop_reason)
            else:
                cyc["controlled_sit"] = controlled_sit(stop_reason)
            cyc["post_feedback"] = feedback_sample(f"c{ci}_post_stop")
            cyc["post_pose"] = pose_snapshot()
            cyc["frames"]["post_sit"] = {
                "files": grab_frames(f"c{ci}_post_sit")}
            flush()
            break

        # Any frame the loop did not reach (short hold / slow bus).
        for at, tag in ((1.0, "hold_plus_1s"), (3.0, "hold_plus_3s"),
                        (10.0, "hold_plus_10s")):
            if tag not in frames_done:
                cyc["frames"][tag] = {
                    "nominal_t_rel_s": at,
                    "actual_t_rel_s": round(time.time() - hold_t0, 2),
                    "late_catch_up": True,
                    "files": grab_frames(f"c{ci}_{tag}")}
                frames_done.add(tag)

        s_exit = feedback_sample(f"c{ci}_hold_exit")
        s_exit["hold_elapsed_s"] = round(time.time() - hold_t0, 2)
        cyc["hold_samples"].append(s_exit)
        cyc["hold_exit"] = s_exit
        cyc["m_hold_end"] = mark(f"cycle{ci}_hold_end")
        cyc["hold_contact"] = contact_snapshot()

        # Per-leg yield at hold exit, against the middle-pair reference.
        if cmd_hip is not None:
            yields = {}
            for leg in range(6):
                v = s_exit["joints"].get(HIP_J[leg])
                if v and v.get("deg") is not None:
                    yields[leg] = round(cmd_hip - float(v["deg"]), 2)
            cyc["hip_yield_deg"] = yields
            log(f"  cycle {ci} hip yield at exit: {yields}")
            if ci == 1:
                cycle1_yield = dict(yields)
                record["cycle1_yield_deg"] = cycle1_yield
        flush()

        log(f"=== cycle {ci}: sit down ===")
        cyc["m_down_start"] = mark(f"cycle{ci}_down_start")
        t_dn0 = time.time()
        try:
            req("/api/standup", {"mode": MODE, "speed": SPEED,
                                 "direction": "down", "torque": TORQUE},
                timeout=40)
        except Exception as e:  # noqa: BLE001
            log(f"  standup down POST failed: {e}")
            limp(f"standup down POST failed: {e}")
            cyc["error"] = str(e)
            record["stopped_reason"] = f"cycle{ci} down POST failed: {e}"
            record["stop_disposition"] = "hazard_limp"
            flush()
            break
        done = wait_demo_done(150)
        cyc["down_result"] = done.get("result")
        cyc["down_status_text"] = (done.get("progress") or {}).get("msg")
        cyc["down_seconds"] = round(time.time() - t_dn0, 2)
        log(f"  down done in {cyc['down_seconds']}s: "
            f"{str(cyc['down_status_text'])[:150]}")
        cyc["m_down_end"] = mark(f"cycle{ci}_down_end")
        time.sleep(1.5)
        cyc["post_feedback"] = feedback_sample(f"c{ci}_post_sit")
        cyc["post_pose"] = pose_snapshot()
        cyc["frames"]["post_sit"] = {
            "files": grab_frames(f"c{ci}_post_sit")}
        flush()

        reason, hazard = check_sample(cyc["post_feedback"], f"cycle{ci} post")
        if reason is None:
            reason, hazard = check_errors(f"cycle{ci} post")
        if reason:
            log(f"  stop after sit: {reason}")
            record["stopped_reason"] = f"cycle{ci} post: {reason}"
            record["stop_disposition"] = (
                "hazard_limp" if hazard else "sat_already")
            if hazard:
                limp(reason)
            flush()
            break
        log(f"  cycle {ci} clean: live={cyc['post_feedback']['live']}/18")

    mark("experiment_end", {"cycles_done": len(record["cycles"])})
    record["post_feedback"] = feedback_sample("post_run")
    record["post_pose"] = pose_snapshot()
    record["post_contact"] = contact_snapshot()
    n, last = 0, ""
    try:
        errs = req("/api/errors", timeout=30).get("errors") or []
        n, last = len(errs), (errs[-1].get("ts") if errs else "")
    except Exception as e:  # noqa: BLE001
        log(f"  final /api/errors read failed: {e}")
    record["final_error_count"] = n
    record["final_error_last_ts"] = last
    record["transient_bus_events"] = transient_bus
    record["discarded_implausible_current_samples"] = discarded
    flush()
    log(f"WROTE cycles.json ({len(record['cycles'])} cycles); "
        f"stopped_reason={record['stopped_reason']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - always leave a record
        log(f"FATAL {type(exc).__name__}: {exc}")
        record["fatal"] = f"{type(exc).__name__}: {exc}"
        try:
            flush()
        except Exception:  # noqa: BLE001
            pass
        raise
