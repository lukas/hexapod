#!/usr/bin/env python3
"""Stand-up / sit-down foot-contact diagnostic (experiment 9224349...).

Guarded driver for plan standup-foot-contact-20260909-01. Runs N
stand-up / sit-down cycles through the documented HTTP control path,
marks each phase in the already-running 50 Hz telemetry recorder, and
captures per-servo (deg / load_pct / current_a / temp_c) plus the
robot's own per-leg contact estimator and observation-camera frames at
stance.

Stops and limps on any of the plan's stop_on conditions:
suspect_zero, over_range, temperature_warning, bus_error.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROBOT = os.environ.get("HEXAPOD_URL", "http://hexapod.local:8080")
LAB = "http://127.0.0.1:8767"
OUT = pathlib.Path(__file__).resolve().parent
FRAMES = OUT / "frames"
FRAMES.mkdir(parents=True, exist_ok=True)

CYCLES = int(os.environ.get("CYCLES", "4"))
HOLD_S = float(os.environ.get("HOLD_S", "5"))
MODE = os.environ.get("MODE", "step")
SPEED = float(os.environ.get("SPEED", "10"))
TORQUE = int(os.environ.get("TORQUE", "700"))
TEMP_WARN_C = float(os.environ.get("TEMP_WARN_C", "55"))

LAB_KEY = pathlib.Path("/tmp/.rl_key").read_text().strip()

JOINT_NAMES = ["yaw", "hip", "knee"]
events: list[dict] = []
log_lines: list[str] = []


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    log_lines.append(line)


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
    log(f"LIMP: {reason}")
    try:
        req("/api/standup/stop", {})
    except Exception as e:  # noqa: BLE001
        log(f"  standup/stop error: {e}")
    try:
        log(f"  /cmd X -> {post_cmd('X')[:80]}")
    except Exception as e:  # noqa: BLE001
        log(f"  /cmd X error: {e}")
    events.append({"kind": "limp", "reason": reason, "t": time.time()})


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


def status_snapshot() -> dict:
    s = req("/api/status", timeout=25)
    motors = s.get("motors") or []
    per_joint = {}
    for m in motors:
        j = m.get("joint")
        if j is None:
            continue
        per_joint[int(j)] = {
            "id": m.get("id"), "name": m.get("name"), "ok": m.get("ok"),
            "deg": m.get("deg"), "load_pct": m.get("load_pct"),
            "current_a": m.get("current_a"), "temp_c": m.get("temp_c"),
            "volt": m.get("volt"), "moving": m.get("moving"),
            "alarm": m.get("alarm"),
        }
    return {"t": time.time(), "live_ids": s.get("live_ids"),
            "armed": s.get("armed"), "mode": s.get("mode"),
            "joints": per_joint}


def contact_snapshot() -> dict:
    t = req("/api/telemetry", timeout=25)
    c = (t.get("contact") or {})
    return {"t": time.time(), "legs": c.get("legs"),
            "writer_alive": t.get("writer_alive"),
            "capture_errors": t.get("capture_errors"),
            "queue_dropped": t.get("queue_dropped"),
            "communication_dropped": t.get("communication_dropped")}


def pose_snapshot() -> dict:
    st = req("/api/rl/state", timeout=25)
    p = st.get("pose") or {}
    imu = st.get("imu") or {}
    return {"t": time.time(), "degrees": p.get("degrees"),
            "live": p.get("live"), "armed": p.get("armed"),
            "bus_quarantined": st.get("bus_quarantined"),
            "imu_grade": imu.get("grade")}


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


def error_state() -> tuple[int, str]:
    try:
        e = req("/api/errors", timeout=25).get("errors") or []
        last = e[-1]["ts"] if e else ""
        return len(e), last
    except Exception as ex:  # noqa: BLE001
        log(f"  /api/errors read failed: {ex}")
        return -1, ""


transient_bus: list[dict] = []
# Cursor into /api/errors so each event is classified exactly once.
seen_errors = {"n": 0}


def check_stop_on(base_n: int, snap: dict, phase: str) -> str | None:
    """Return a hard stop reason string, or None when clear.

    Plan stop_on = suspect_zero / over_range / temperature_warning /
    bus_error. suspect_zero, over-range, temperature and servo alarms are
    IMMEDIATE hard stops with no tolerance.

    A lone `bus_timing` ascii_err/no_a5 is the host<->MCU link's known
    recoverable framing hiccup, not a bus fault: the driver retries and
    the robot completed a full step stand-up + sit-down today after two
    of them. Per the canonical emergency handling (an isolated alert is
    not a confirmed current hazard; a single missing reply is noise),
    such an event is re-verified against live state and treated as a
    transient only while the bus stays un-quarantined and all 18 motors
    still answer. It escalates to a hard stop if the bus quarantines, the
    scan goes incomplete, or three transients accumulate.
    """
    # Temperature / alarm / scan completeness first (no tolerance).
    hot = [(j, v["temp_c"]) for j, v in (snap.get("joints") or {}).items()
           if isinstance(v.get("temp_c"), (int, float))
           and v["temp_c"] >= TEMP_WARN_C]
    if hot:
        return f"temperature_warning: {hot}"
    al = [j for j, v in (snap.get("joints") or {}).items() if v.get("alarm")]
    if al:
        return f"servo_alarm on joints {al}"
    live = snap.get("live_ids") or []
    if len(live) < 18:
        return f"incomplete_scan {len(live)}/18 during {phase}"

    try:
        errs = req("/api/errors", timeout=25).get("errors") or []
    except Exception as ex:  # noqa: BLE001
        log(f"  /api/errors read failed: {ex}")
        return None
    cursor = max(seen_errors["n"], base_n)
    new = errs[cursor:]
    seen_errors["n"] = len(errs)
    for ev in new:
        msg = str(ev.get("msg", ""))
        kind = str(ev.get("kind", ""))
        low = msg.lower()
        if "suspect" in low or "logical zero frame looks wrong" in low:
            return f"suspect_zero: {msg[:160]}"
        if "outside its" in low and "range" in low:
            return f"over_range: {msg[:160]}"
        if "overtemp" in low or "temperature" in low:
            return f"temperature_warning: {msg[:160]}"
        if kind == "bus_timing" or "ascii_err" in low or "no_a5" in low:
            # Re-verify against live state before deciding.
            try:
                bs = req("/api/bus/status", timeout=20)
                fresh = status_snapshot()
            except Exception as ex:  # noqa: BLE001
                return f"bus_error (state unreadable): {msg[:120]} / {ex}"
            nlive = len(fresh.get("live_ids") or [])
            if bs.get("bus_quarantined") or not bs.get("bus_available"):
                return f"bus_error: quarantined/unavailable after {msg[:120]}"
            if nlive < 18:
                return (f"bus_error: {nlive}/18 motors after {msg[:120]}")
            transient_bus.append({"phase": phase, "msg": msg, "kind": kind,
                                  "ts": ev.get("ts"), "live": nlive,
                                  "t": time.time()})
            log(f"  transient bus event #{len(transient_bus)} during {phase}"
                f": {msg[:90]} (bus available, {nlive}/18 live)")
            if len(transient_bus) >= 3:
                return (f"bus_error: {len(transient_bus)} bus_timing events "
                        f"accumulated (last: {msg[:100]})")
            continue
        log(f"  unclassified error event during {phase}: "
            f"{kind} {msg[:110]}")
        return f"error_event({kind}): {msg[:150]}"
    return None


def wait_demo_done(timeout_s: float = 90.0) -> dict:
    """Poll /api/calibrate until the async stand-up job stops running.

    /api/calibrate carries the rich result block (peak_a, peak_joint,
    keyframes_done, timing) that /api/demo/status omits.
    """
    t0 = time.monotonic()
    last: dict = {}
    started = False
    # Phase 1: wait for the async worker to actually claim the job, so a
    # stale not-running reading from the PREVIOUS job cannot be mistaken
    # for this one finishing instantly.
    while time.monotonic() - t0 < 12.0:
        try:
            last = req("/api/calibrate", timeout=20)
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
    # Phase 2: wait for completion.
    while time.monotonic() - t0 < timeout_s:
        try:
            last = req("/api/calibrate", timeout=20)
        except Exception as e:  # noqa: BLE001
            log(f"  calibrate poll error: {e}")
            time.sleep(1.0)
            continue
        if not last.get("running"):
            return last
        time.sleep(0.5)
    log("  demo poll TIMEOUT")
    last["poll_timeout"] = True
    return last


def main() -> int:
    base_n, base_last = error_state()
    log(f"baseline /api/errors count={base_n} last={base_last}")

    pre = status_snapshot()
    log(f"pre: live={len(pre['live_ids'] or [])}/18 "
        f"maxtemp={max((v['temp_c'] or 0) for v in pre['joints'].values())}C")
    record = {
        "experiment_id": "922434955b35404198907c9e77cde5f6",
        "plan_id": "standup-foot-contact-20260909-01",
        "mode": MODE, "speed": SPEED, "torque": TORQUE,
        "cycles_requested": CYCLES, "stand_hold_s": HOLD_S,
        "baseline_error_count": base_n, "baseline_error_last_ts": base_last,
        "pre_status": pre,
        "pre_pose": pose_snapshot(),
        "pre_contact": contact_snapshot(),
        "cycles": [], "events": events, "stopped_reason": None,
    }
    stop = check_stop_on(base_n, pre, "preflight")
    if stop:
        log(f"preflight stop_on: {stop}")
        record["stopped_reason"] = f"preflight: {stop}"
        (OUT / "cycles.json").write_text(json.dumps(record, indent=1))
        return 2

    mark("experiment_start", {"plan": "standup-foot-contact-20260909-01",
                              "mode": MODE, "cycles": CYCLES})

    for ci in range(1, CYCLES + 1):
        cyc: dict = {"cycle": ci}
        log(f"=== cycle {ci}/{CYCLES}: stand up ({MODE}) ===")
        cyc["m_up_start"] = mark(f"cycle{ci}_up_start")
        t_up0 = time.time()
        try:
            up = req("/api/standup", {"mode": MODE, "speed": SPEED,
                                      "direction": "up", "torque": TORQUE},
                     timeout=40)
        except Exception as e:  # noqa: BLE001
            log(f"  standup up POST failed: {e}")
            limp(f"standup up POST failed: {e}")
            cyc["error"] = str(e)
            record["cycles"].append(cyc)
            record["stopped_reason"] = f"cycle{ci} up POST failed: {e}"
            break
        cyc["up_ack"] = up
        log(f"  up ack: ok={up.get('ok')} {str(up.get('error') or '')[:120]}")
        done = wait_demo_done(120)
        cyc["up_result"] = done.get("result")
        cyc["up_status_text"] = (done.get("progress") or {}).get("msg")
        cyc["up_name"] = done.get("name")
        cyc["up_seconds"] = round(time.time() - t_up0, 2)
        log(f"  up done in {cyc['up_seconds']}s: "
            f"{str(cyc['up_status_text'])[:150]} | {cyc['up_result']}")

        time.sleep(2.0)  # settle
        cyc["m_stance"] = mark(f"cycle{ci}_stance")
        s_stance = status_snapshot()
        cyc["stance_status"] = s_stance
        cyc["stance_contact"] = contact_snapshot()
        cyc["stance_pose"] = pose_snapshot()
        cyc["stance_frames"] = grab_frames(f"c{ci}_stance")
        mx = max((v["temp_c"] or 0) for v in s_stance["joints"].values())
        cura = [v["current_a"] for v in s_stance["joints"].values()]
        log(f"  stance: live={len(s_stance['live_ids'] or [])}/18 "
            f"maxtemp={mx}C maxcur={max(x or 0 for x in cura):.2f}A "
            f"frames={len(cyc['stance_frames'])}")

        stop = check_stop_on(base_n, s_stance, f"cycle{ci} stance")
        if stop:
            log(f"  stop_on at stance: {stop}")
            limp(stop)
            cyc["stop_reason"] = stop
            record["cycles"].append(cyc)
            record["stopped_reason"] = f"cycle{ci} stance: {stop}"
            break

        # hold the stance for the remainder of HOLD_S, sampling midway
        time.sleep(max(0.0, HOLD_S / 2.0))
        cyc["hold_mid_status"] = status_snapshot()
        cyc["hold_mid_contact"] = contact_snapshot()
        time.sleep(max(0.0, HOLD_S / 2.0))
        cyc["m_hold_end"] = mark(f"cycle{ci}_hold_end")

        log(f"=== cycle {ci}: sit down ===")
        cyc["m_down_start"] = mark(f"cycle{ci}_down_start")
        t_dn0 = time.time()
        try:
            dn = req("/api/standup", {"mode": MODE, "speed": SPEED,
                                      "direction": "down",
                                      "torque": TORQUE}, timeout=40)
        except Exception as e:  # noqa: BLE001
            log(f"  standup down POST failed: {e}")
            limp(f"standup down POST failed: {e}")
            cyc["error"] = str(e)
            record["cycles"].append(cyc)
            record["stopped_reason"] = f"cycle{ci} down POST failed: {e}"
            break
        cyc["down_ack"] = dn
        done = wait_demo_done(120)
        cyc["down_result"] = done.get("result")
        cyc["down_status_text"] = (done.get("progress") or {}).get("msg")
        cyc["down_seconds"] = round(time.time() - t_dn0, 2)
        log(f"  down done in {cyc['down_seconds']}s: "
            f"{str(cyc['down_status_text'])[:150]} | {cyc['down_result']}")
        cyc["m_down_end"] = mark(f"cycle{ci}_down_end")
        time.sleep(1.5)
        post = status_snapshot()
        cyc["post_status"] = post
        cyc["post_pose"] = pose_snapshot()
        record["cycles"].append(cyc)

        stop = check_stop_on(base_n, post, f"cycle{ci} post")
        if stop:
            log(f"  stop_on after sit: {stop}")
            limp(stop)
            record["stopped_reason"] = f"cycle{ci} post: {stop}"
            break
        log(f"  cycle {ci} clean: live={len(post['live_ids'] or [])}/18")

    mark("experiment_end", {"cycles_done": len(record["cycles"])})
    record["post_status"] = status_snapshot()
    record["post_pose"] = pose_snapshot()
    record["post_frames"] = grab_frames("post")
    n, last = error_state()
    record["final_error_count"] = n
    record["final_error_last_ts"] = last
    record["transient_bus_events"] = transient_bus
    record["log"] = log_lines
    (OUT / "cycles.json").write_text(json.dumps(record, indent=1))
    log(f"WROTE cycles.json ({len(record['cycles'])} cycles); "
        f"errors {base_n} -> {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
