#!/usr/bin/env python3
"""Repeatable gait comparison on one robot, measured by the floor-fitted top camera.

    gait_sweep.py run     --host URL --name hexapod2 --out DIR [--arms ...] [--rounds 2]
                          [--exposure-s 6] [--vx 0.10] [--chassis-tag 119] [--no-camera]
    gait_sweep.py analyze DIR [--chassis-tag 119]
    gait_sweep.py table   DIR [DIR ...]

``run`` refuses to move if the top camera's saved floor fit no longer matches the
anchors (`hexapod-cameras check`), records the top camera for the whole sweep,
then for every (arm, round): sets hold/walk roles, re-stands to the sim
walk-ready pose, drives |vx| for exposure_s (direction alternates, and heads back
once the chassis tag has drifted --max-drift-mm from the start, so long passes
stay under the camera), stops, and reads back servo temps/volts.  A start that
dies on a stale MCU snapshot is retried three times with a pause.  Any servo bus
voltage under 10.8 V aborts (the Sep 13/14 brownout band).  The robot is lowered
and limped at the end, always.

``analyze`` writes analysis.json, TABLE.md and gaits.json (the Lab's scorecard
shape, `hexapod-lab2 import --gaits`).  Roll/pitch rms come from the drive CSV
walk phase; ground speed and heading change come from the chassis tag's
floor-referenced track over the active window (lid tags swing with the legs and
vanish under the overhead cable, so they are only a fallback).  An arm is
"inconclusive" unless at least two exposures ran for 70 % of the planned time.

History: this replaces the Sep 14-18 ~/.hexapod/dr_sweep*.py, gait_sweep*.py,
dr_analyze.py, gait_cam.py copies, which drifted apart per run.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import os
import shutil
import statistics as st
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

# (arm, walk policy file, hold policy file). The hold must match the walk's training Hz.
DEFAULT_ARMS = [
    ("walkteach", "walkteach_allhead_acq12m_100hz.json", "walkteach_allhead_acq12m_100hz.json"),
    ("allhead50", "walk_allheading_mlp_singleframe_scratch_50hz.json", "ps200_parent.json"),
    ("combo", "speed50hz_ps200dr_armcombo_cont8m.json", "ps200_parent.json"),
    ("parent", "ps200_parent.json", "ps200_parent.json"),
]
MIN_BUS_VOLT = 10.8
HB_HZ = 5.0
STALE_RETRIES = 3
# Surveyed/taped floor tags seen from the top camera (2026-09-18). 119 is hexapod2's chassis lid: never floor.
FLOOR_TAG_FALLBACK = frozenset({100, 101, 102, 103, 104, 105, 106, 110, 111, 112, 115, 116, 118})
CAMERAS_BIN = os.environ.get("HEXAPOD_CAMERAS_BIN") or shutil.which("hexapod-cameras") \
    or str(Path.home() / "hexapod-tracker" / ".venv" / "bin" / "hexapod-cameras")
TRACKER_DIR = os.environ.get("HEXAPOD_TRACKER_DIR", str(Path.home() / "hexapod-tracker"))


# --- pure analysis (tested) --------------------------------------------------

def imu_metrics(rows: list[dict]) -> dict:
    """Roll/pitch peak+rms over the walk phase of a drive CSV (all rows if no phase column)."""
    if not rows:
        return {}
    walk = [r for r in rows if str(r.get("phase", "")).startswith("walk")] or rows
    def col(name):
        return [float(r[name]) for r in walk if r.get(name) not in (None, "")]
    roll, pitch = col("roll_deg"), col("pitch_deg")
    out = {"walk_ticks": len(walk)}
    if roll:
        out.update(roll_peak=round(max(map(abs, roll)), 2), roll_rms=round(math.sqrt(st.mean(v * v for v in roll)), 2))
    if pitch:
        out.update(pitch_peak=round(max(map(abs, pitch)), 2), pitch_rms=round(math.sqrt(st.mean(v * v for v in pitch)), 2))
    cur = col("max_cur_a")
    if cur:
        out["max_cur_a"] = round(max(cur), 2)
    return out


def chassis_track(vision: list[dict], t0: float, t1: float, floor: set[int],
                  chassis: str | None = None) -> dict | None:
    """Net displacement / speed / heading change of one tag over [t0, t1].

    Prefers ``chassis``; otherwise the non-floor tag tracked for the largest share of
    the window. Coverage < 0.7 is reported, not hidden.
    """
    tracks = collections.defaultdict(list)
    for s in vision:
        ts = s.get("capture_unix") or 0
        if not (t0 <= ts <= t1 + 0.3):
            continue
        for k, m in (s.get("markers") or {}).items():
            if not str(k).isdigit() or int(k) in floor or not isinstance(m, dict):
                continue
            p = m.get("position_mm") or {}
            if m.get("status") == "tracked" and p.get("x") is not None:
                tracks[str(k)].append((ts, float(p["x"]), float(p["y"]), m.get("yaw")))
    cands = {k: v for k, v in tracks.items() if len(v) >= 3}
    if chassis is not None and str(chassis) in floor_ids_str(floor):
        raise ValueError(f"chassis tag {chassis} is listed as a floor tag")
    if not cands:
        return None
    key = chassis if chassis in cands else max(cands, key=lambda k: (len(cands[k]), k))
    pts = cands[key]
    (ta, xa, ya, ha), (tb, xb, yb, hb) = pts[0], pts[-1]
    span = tb - ta
    net = math.hypot(xb - xa, yb - ya)
    dh = None if ha is None or hb is None else round(((float(hb) - float(ha) + 180) % 360) - 180, 1)
    return {"tag": key, "samples": len(pts), "coverage": round(span / max(t1 - t0, 1e-3), 2),
            "net_mm": round(net, 1), "mm_s": round(net / span, 1) if span > 0 else None,
            "heading_chg_deg": dh, "chassis": key == chassis}


def verdict(rows: list[dict], exposure_s: float) -> tuple[str, str]:
    """Scorecard verdict for one arm from its per-exposure rows."""
    full = [r for r in rows if (r.get("active_s") or 0) >= 0.7 * exposure_s]
    if len(full) < 2:
        return "inconclusive", f"only {len(full)} of {len(rows)} exposures ran >= 70 % of {exposure_s:g} s"
    roll = st.mean(r["roll_rms"] for r in full if r.get("roll_rms") is not None)
    speeds = [r["cam"]["mm_s"] for r in full if r.get("cam") and r["cam"].get("mm_s") is not None]
    speed = st.mean(speeds) if speeds else None
    heads = [abs(r["cam"]["heading_chg_deg"]) for r in full if r.get("cam") and r["cam"].get("heading_chg_deg") is not None]
    veer = max(heads) if heads else None
    why = f"roll rms {roll:.2f} deg" + (f", {speed:.0f} mm/s" if speed is not None else "") + (f", veer up to {veer:.0f} deg" if veer is not None else "")
    if roll > 4.0 or (speed is not None and speed < 10):
        return "poor", why
    if roll < 2.0 and (speed is None or speed >= 30) and (veer is None or veer <= 15):
        return "promising", why
    return "ok", why


def next_direction(last_sign: float, start_xy, now_xy, moved_away: bool | None, max_drift_mm: float) -> float:
    """Direction of the next exposure: alternate, unless the chassis has drifted more
    than ``max_drift_mm`` from where the sweep began; then head back (repeat the last
    direction if it brought the robot closer, reverse it if it took it away)."""
    if start_xy is None or now_xy is None or moved_away is None:
        return -last_sign
    if math.hypot(now_xy[0] - start_xy[0], now_xy[1] - start_xy[1]) <= max_drift_mm:
        return -last_sign
    return -last_sign if moved_away else last_sign


def wrap180(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0


def steer_command(chassis_xy, yaw_deg, target_xy, cal, vx_max=0.09, wz_max=0.25, k=0.06):
    """(vx, wz) to walk toward ``target_xy`` given the chassis pose and a calibration.

    ``cal`` = {"heading_offset_deg": float, "yaw_sign": +/-1}. When driving vx>0
    with wz=0 the chassis moves along floor bearing ``yaw + heading_offset`` (both
    measured live during a calibration phase, so no direction is ever guessed).
    Commanding +wz changes yaw by ``yaw_sign``. Returns vx=0 unless the robot is
    within 90 deg of facing the target, so it turns in place before advancing.
    """
    bx, by = target_xy[0] - chassis_xy[0], target_xy[1] - chassis_xy[1]
    bearing = math.degrees(math.atan2(by, bx))
    err = wrap180(bearing - cal["heading_offset_deg"] - yaw_deg)
    wz = max(-wz_max, min(wz_max, cal["yaw_sign"] * k * err))
    vx = vx_max * max(0.0, math.cos(math.radians(err)))
    return round(vx, 3), round(wz, 3)


def reached(chassis_xy, target_xy, tol_mm=180.0) -> bool:
    return math.hypot(target_xy[0] - chassis_xy[0], target_xy[1] - chassis_xy[1]) <= tol_mm


def inside_box(xy, box) -> bool:
    """xy = (x, y) floor mm; box = (xmin, xmax, ymin, ymax) or None (no limit)."""
    if xy is None or box is None:
        return True
    return box[0] <= xy[0] <= box[1] and box[2] <= xy[1] <= box[3]


def floor_ids_str(floor: set[int]) -> set[str]:
    return {str(i) for i in floor}


def floor_tags(chassis: str | None = None) -> set[int]:
    p = Path(TRACKER_DIR) / "configs" / "floor_tag_map.json"
    try:
        d = json.loads(p.read_text())
        ids = {int(t["id"]) for t in d.get("tags", [])} | {int(i) for i in d.get("active_anchor_ids", [])}
        ids |= set(FLOOR_TAG_FALLBACK)
    except Exception:
        ids = set(FLOOR_TAG_FALLBACK)
    if chassis is not None and chassis.isdigit():
        ids.discard(int(chassis))
    return ids


# --- robot ---------------------------------------------------------------------

class Robot:
    def __init__(self, host: str):
        self.host = host.rstrip("/")

    def _req(self, path, data, timeout):
        req = urllib.request.Request(self.host + path, data=data, method="POST" if data is not None else "GET",
                                     headers={"Content-Type": "application/json", "X-Hexapod-Controller": "gait_sweep"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                txt = r.read().decode()
        except urllib.error.HTTPError as e:
            txt = e.read().decode()
        try:
            return json.loads(txt or "{}")
        except ValueError:
            return {"_text": txt.strip()}

    def get(self, path, timeout=20.0):
        return self._req(path, None, timeout)

    def post(self, path, body=None, timeout=40.0):
        return self._req(path, json.dumps(body if body is not None else {}).encode(), timeout)

    def cmd(self, line: str):
        return self._req("/cmd", line.encode(), 15.0)

    def wait_idle(self, max_s=30.0) -> float:
        t0 = time.time()
        while time.time() - t0 < max_s:
            ds, stt = self.get("/api/rl/drive"), self.get("/api/demo/status")
            dm = stt.get("demo") or {}
            if not ds.get("active") and not dm.get("running") and stt.get("mode") != "demo":
                break
            time.sleep(0.5)
        return round(time.time() - t0, 1)


def read_chassis_pose(out: Path, tag: str):
    """Latest (x_mm, y_mm, yaw_deg) of ``tag`` from a running camera session, or None."""
    try:
        lines = (Path(out) / "camera" / "vision.jsonl").read_text().splitlines()[-12:]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            m = (json.loads(line).get("markers") or {}).get(str(tag)) or {}
        except ValueError:
            continue
        pos = m.get("position_mm") or {}
        if m.get("status") == "tracked" and pos.get("x") is not None and m.get("yaw") is not None:
            return (float(pos["x"]), float(pos["y"]), float(m["yaw"]))
    return None


def calibrate_heading(robot, read_pose, log, vx_probe=0.06, w_probe=0.15) -> dict | None:
    """Learn the vx->floor-bearing offset and the wz->yaw sign by moving and watching.

    Never guesses direction: drives a short forward probe and a short turn probe and
    measures what the chassis tag actually did. Returns None if the robot did not move
    (tangled / not on open floor), so the caller can stop instead of steering on noise.
    """
    owner = str(uuid.uuid4())
    def hb(vx, wz, secs):
        end = time.time() + secs
        while time.time() < end:
            robot.post("/api/rl/drive/cmd", {"vx": vx, "vy": 0, "wz": wz, "dh": 0, "command_owner": owner}, timeout=5)
            time.sleep(0.2)
    r = robot.post("/api/rl/drive/start", {"vx": vx_probe, "vy": 0, "wz": 0, "dh": 0, "command_owner": owner}, timeout=40)
    if not r.get("ok"):
        log(f"  calibrate: drive start refused: {r.get('error')}"); return None
    p0 = read_pose()
    hb(vx_probe, 0.0, 2.5)
    p1 = read_pose()
    if p0 is None or p1 is None:
        robot.post("/api/rl/drive/stop", {}); log("  calibrate: chassis tag not visible; put the robot on open floor"); return None
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    if math.hypot(dx, dy) < 30.0:
        robot.post("/api/rl/drive/stop", {}); log(f"  calibrate: robot moved only {math.hypot(dx, dy):.0f} mm on a forward probe; tangled or stuck"); return None
    heading_offset = wrap180(math.degrees(math.atan2(dy, dx)) - p0[2])
    y0 = read_pose()[2]
    hb(0.0, w_probe, 2.0)
    y1 = read_pose()[2]
    robot.post("/api/rl/drive/stop", {}, timeout=20)
    dyaw = wrap180(y1 - y0)
    yaw_sign = 1.0 if dyaw >= 0 else -1.0
    log(f"  calibrate: moved {math.hypot(dx, dy):.0f} mm, heading_offset {heading_offset:.0f} deg, +wz -> {dyaw:+.0f} deg (yaw_sign {yaw_sign:+.0f})")
    return {"heading_offset_deg": round(heading_offset, 1), "yaw_sign": yaw_sign}


class Sweep:
    def __init__(self, args):
        self.a = args
        self.robot = Robot(args.host)
        self.out = Path(args.out)
        (self.out / "camera").mkdir(parents=True, exist_ok=True)
        self.results = {"robot": args.name, "base": args.host, "vx": args.vx, "exposure_s": args.exposure_s,
                        "arms": args.arms, "rounds": args.rounds, "started_unix": time.time(), "trials": []}
        self.cam_proc = None
        self.start_xy = None      # chassis position at the first exposure (floor mm)
        self.last_sign = None
        self.moved_away = None

    def log(self, msg):
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        with (self.out / "sweep.log").open("a") as fh:
            fh.write(line + "\n")

    def save(self):
        (self.out / "results.json").write_text(json.dumps(self.results, indent=1))

    # camera ------------------------------------------------------------------
    def camera_check(self) -> None:
        if self.a.no_camera:
            return
        if not Path(CAMERAS_BIN).exists():
            sys.exit(f"hexapod-cameras not found at {CAMERAS_BIN}; set HEXAPOD_CAMERAS_BIN or pass --no-camera")
        r = subprocess.run([CAMERAS_BIN, "check", "--role", self.a.camera_role], capture_output=True, text=True, timeout=120)
        try:
            j = json.loads(r.stdout[r.stdout.index("{"):])
        except Exception:
            sys.exit(f"camera check gave no JSON: {r.stdout[-300:]} {r.stderr[-300:]}")
        (self.out / "camera_check.json").write_text(json.dumps(j, indent=1))
        if not j.get("ok"):
            sys.exit(f"top camera floor fit is off (drift {j.get('drift_rms_px')} px): {j.get('reason')}. "
                     f"Run `hexapod-cameras calibrate floor --role {self.a.camera_role}` and retry.")
        self.log(f"camera {self.a.camera_role} floor fit ok (drift {j.get('drift_rms_px')} px, anchors {j.get('anchors_seen')})")

    def camera_start(self) -> None:
        if self.a.no_camera:
            return
        seconds = int(60 + len(self.a.arms) * self.a.rounds * (self.a.exposure_s + 40))
        env = dict(os.environ, OPENCV_AVFOUNDATION_SKIP_AUTH="1")
        self.cam_proc = subprocess.Popen(
            [CAMERAS_BIN, "session", "--out", str(self.out / "camera"), "--roles", self.a.camera_role,
             "--hz", "6", "--fps", "30", "--seconds", str(seconds), "--no-stdin"],
            stdout=(self.out / "camera_session.log").open("w"), stderr=subprocess.STDOUT, env=env)
        deadline = time.time() + 30
        while time.time() < deadline and not (self.out / "camera" / "state.json").exists():
            time.sleep(0.5)
        self.log(f"camera session pid {self.cam_proc.pid} ({'streaming' if (self.out / 'camera' / 'state.json').exists() else 'no state yet'})")

    def camera_stop(self) -> None:
        if self.cam_proc is None:
            return
        (self.out / "camera" / "STOP").write_text("stop")
        try:
            self.cam_proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.cam_proc.terminate()

    def chassis_xy(self):
        """Latest floor-referenced chassis position from the running camera session."""
        if self.a.no_camera or not self.a.chassis_tag:
            return None
        vp = self.out / "camera" / "vision.jsonl"
        try:
            lines = vp.read_text().splitlines()[-12:]
        except OSError:
            return None
        for line in reversed(lines):
            try:
                m = (json.loads(line).get("markers") or {}).get(str(self.a.chassis_tag)) or {}
            except ValueError:
                continue
            p = m.get("position_mm") or {}
            if m.get("status") == "tracked" and p.get("x") is not None:
                return (float(p["x"]), float(p["y"]))
        return None

    # robot -------------------------------------------------------------------
    def status_after(self, trial: dict, arm: str) -> None:
        ms = self.robot.get("/api/status").get("motors") or []
        temps = sorted(((m.get("temp_c") or 0), m.get("name")) for m in ms)
        volts = [m.get("volt") for m in ms if m.get("volt")]
        trial["temps_top3"] = [(n, t) for t, n in temps[-3:][::-1]]
        trial["min_volt"] = min(volts) if volts else None
        trial["knees"] = [(m.get("name"), m.get("temp_c"), m.get("current_a"), m.get("load_pct")) for m in ms if "knee" in (m.get("name") or "")]
        if trial["min_volt"] is not None and trial["min_volt"] < MIN_BUS_VOLT:
            self.abort(f"{arm}: servo bus {trial['min_volt']} V under load (brownout band)")

    def abort(self, msg: str) -> None:
        self.log("ABORT: " + msg)
        try:
            self.robot.cmd("X")
        finally:
            self.camera_stop()
            self.save()
        sys.exit(1)

    def healthy(self, rb: dict) -> tuple[bool, str]:
        d = (rb.get("detail") or "").lower()
        return bool(rb.get("armed")) and not any(k in d for k in ("jam", "brownout", "stuck", "tip", "overtemp", "thermal")), d

    def start_drive(self, vx: float) -> tuple[dict, str, float]:
        """Start a drive session; retry when the MCU snapshot is stale (hexapod1 IMU flake)."""
        for attempt in range(STALE_RETRIES + 1):
            owner = str(uuid.uuid4())
            t0 = time.time()
            r = self.robot.post("/api/rl/drive/start", {"vx": vx, "vy": 0, "wz": 0, "dh": 0, "command_owner": owner}, timeout=40)
            time.sleep(1.0)
            ds = self.robot.get("/api/rl/drive")
            err = str(((ds.get("result") or {}) if not ds.get("active") else {}).get("error") or r.get("error") or "")
            if ds.get("active") or "snapshot" not in err:
                return r, owner, t0
            if attempt < STALE_RETRIES:
                self.log(f"  transport stale ({err[:70]}); retry {attempt + 1}/{STALE_RETRIES} in 6 s")
                time.sleep(6.0)
                self.robot.wait_idle(10)
        return r, owner, t0

    def run_trial(self, arm: str, walk: str, hold: str) -> None:
        R, a = self.robot, self.a
        self.log(f"--- {arm}: {walk} (hold {hold})")
        trial = {"arm": arm, "base_arm": arm.rsplit("_r", 1)[0], "file": walk, "hold": hold}
        for role, f in (("hold", hold), ("walk", walk)):
            r = R.post("/api/rl/roles", {"role": role, "file": f})
            if not r.get("ok"):
                trial["skipped"] = f"{role} role: {r.get('error')}"
                self.results["trials"].append(trial); self.save()
                self.log(f"  skipped: {trial['skipped']}"); return
            if role == "hold":
                R.wait_idle(30)
                r = R.post("/api/rl/policy_select", {"file": walk})
                if not r.get("ok"):
                    trial["skipped"] = f"policy_select: {r.get('error')}"
                    self.results["trials"].append(trial); self.save()
                    self.log(f"  skipped: {trial['skipped']}"); return
        R.post("/api/rl/stand", {})
        for _ in range(45):
            time.sleep(1)
            stt = R.get("/api/demo/status")
            if not (stt.get("demo") or {}).get("running") and stt.get("mode") == "stand":
                break
        rb = R.get("/api/robot")
        ok, det = self.healthy(rb)
        if not ok:
            self.abort(f"{arm}: unhealthy after stand: {det}")
        pf = R.get("/api/rl/preflight?mode=walk")
        trial["preflight"] = {k: pf.get(k) for k in ("ok", "roll_deg", "pitch_deg", "max_pose_delta_deg", "error")}
        self.log(f"  preflight ok={pf.get('ok')} tilt={pf.get('roll_deg')}/{pf.get('pitch_deg')} poseΔ={pf.get('max_pose_delta_deg')}")
        if not pf.get("ok"):
            self.abort(f"{arm}: walk preflight: {pf.get('error')}")
        here = self.chassis_xy()
        if self.start_xy is None and here is not None:
            self.start_xy = here
        if self.last_sign is None:
            sign = -1.0 if a.first_direction == "reverse" else 1.0
        else:
            sign = next_direction(self.last_sign, self.start_xy, here, self.moved_away, a.max_drift_mm)
        if here is not None and self.start_xy is not None:
            drift = math.hypot(here[0] - self.start_xy[0], here[1] - self.start_xy[1])
            self.log(f"  chassis {drift:.0f} mm from sweep start; next direction {'forward' if sign > 0 else 'reverse'}")
        trial["chassis_before_xy"] = here
        vx = a.vx * sign
        r, owner, t0 = self.start_drive(vx)
        trial.update(vx=vx, owner=owner, t0_unix=t0, samples=[])
        if not r.get("ok"):
            trial["start_refused"] = r.get("error")
            self.log(f"  drive start refused: {r.get('error')}")
        else:
            end = t0 + a.exposure_s
            while time.time() < end:
                hb = R.post("/api/rl/drive/cmd", {"vx": vx, "vy": 0, "wz": 0, "dh": 0, "command_owner": owner}, timeout=5)
                live = hb.get("live") or {}
                trial["samples"].append({"t": round(time.time() - t0, 2), "roll": live.get("roll_deg"), "pitch": live.get("pitch_deg"),
                                         "maxI": live.get("max_current_a"), "loop_hz": live.get("measured_loop_hz"), "overruns": live.get("overruns")})
                if hb.get("active") is False:
                    trial["ended_early"] = hb.get("error") or hb.get("end_reason") or "no drive session"
                    break
                if a.keep_in is not None:
                    xy = self.chassis_xy()
                    if xy is not None and not inside_box(xy, a.keep_in):
                        trial["ended_early"] = f"keep-in box left at {xy[0]:.0f},{xy[1]:.0f} mm"
                        self.log(f"  {trial['ended_early']}; stopping this pass")
                        break
                time.sleep(1.0 / HB_HZ)
            R.post("/api/rl/drive/stop", {}, timeout=20)
            trial["t1_unix"] = time.time()
            trial["wind_down_s"] = R.wait_idle(30)
            res = (R.get("/api/rl/drive").get("result") or {})
            trial["result"] = {k: res.get(k) for k in ("ok", "ended", "error", "ticks", "max_current_a", "active_wall_time_s", "training_hz") if k in res}
            trial["active_s"] = round(float(res.get("active_wall_time_s") or 0), 2)
            try:
                names = sorted(x["name"] for x in (R.get("/api/logs").get("files") or [])
                               if x["name"].startswith("rl_drive_") and x["name"].endswith(".csv"))
                trial["csv"] = names[-1] if names and res.get("ticks") else None
            except Exception as e:
                trial["csv_err"] = str(e)
        self.status_after(trial, arm)
        after = self.chassis_xy()
        trial["chassis_after_xy"] = after
        self.last_sign = sign
        if here is not None and after is not None and self.start_xy is not None:
            d0 = math.hypot(here[0] - self.start_xy[0], here[1] - self.start_xy[1])
            d1 = math.hypot(after[0] - self.start_xy[0], after[1] - self.start_xy[1])
            self.moved_away = d1 > d0
        rb = R.get("/api/robot")
        trial["robot_after"] = {k: rb.get(k) for k in ("armed", "mode", "activity", "detail")}
        self.results["trials"].append(trial); self.save()
        ok, det = self.healthy(rb)
        if not ok:
            self.abort(f"{arm}: unhealthy after exposure: {det}")
        res = trial.get("result") or {}
        self.log(f"  done {arm}: active {trial.get('active_s')} s ended={res.get('ended')} err={str(res.get('error') or '')[:50]} "
                 f"maxI={res.get('max_current_a')} minV={trial.get('min_volt')} hottest={trial['temps_top3'][:1]}")

    def pull_logs(self) -> None:
        tel = self.out / "telemetry"; tel.mkdir(exist_ok=True)
        R = self.robot
        try:
            names = {x["name"] for x in (R.get("/api/logs").get("files") or [])}
            for t in self.results["trials"]:
                c = t.get("csv") or ""
                if not c:
                    continue
                stem = c[:-4]
                for cand in (c, stem + "_summary.json", stem + "_debug.jsonl"):
                    if cand in names and not (tel / cand).exists():
                        urllib.request.urlretrieve(f"{R.host}/api/logs/{cand}", tel / cand)
            for name, nbytes in (("commands.jsonl", 400000), ("errors.jsonl", 200000), ("events.jsonl", 1500000)):
                req = urllib.request.Request(f"{R.host}/api/logs/{name}", headers={"Range": f"bytes=-{nbytes}"})
                (tel / f"robot_{name}").write_bytes(urllib.request.urlopen(req, timeout=60).read())
            self.log(f"robot logs pulled into telemetry/ ({len(list(tel.iterdir()))} files)")
        except Exception as e:
            self.log(f"robot log pull failed: {e}")

    def lower_and_limp(self) -> None:
        R = self.robot
        try:
            R.post("/api/rl/lower", {}, timeout=40)
            for _ in range(45):
                time.sleep(1)
                if not ((R.get("/api/demo/status").get("demo") or {}).get("running")):
                    break
        finally:
            self.log(f"lowered; X -> {R.cmd('X')}")

    def run(self) -> int:
        a, R = self.a, self.robot
        self.camera_check()
        rb = R.get("/api/robot")
        if rb.get("armed"):
            sys.exit("robot is armed; limp it (X) and start from a known flat pose")
        self.camera_start()
        order = []
        for rnd in range(a.rounds):
            seq = a.arms if rnd % 2 == 0 else list(reversed(a.arms))
            order += [(f"{n}_r{rnd + 1}", w, h) for n, w, h in seq]
        self.log(f"gait sweep start {a.host} name={a.name} exposure={a.exposure_s}s vx={a.vx} order={[o[0] for o in order]}")
        try:
            for _ in range(3):
                if rb.get("armed"):
                    break
                R.cmd("ARM"); time.sleep(2); rb = R.get("/api/robot")
            ok, det = self.healthy(rb)
            if not ok:
                self.abort(f"robot not healthy before sweep: {det}")
            for arm, walk, hold in order:
                self.run_trial(arm, walk, hold)
                time.sleep(1.0)
        finally:
            self.camera_stop()
            self.save()
            self.pull_logs()
            self.lower_and_limp()
        self.log("sweep complete")
        analyze(self.out, a.chassis_tag)
        return 0


# --- analysis over a run dir ---------------------------------------------------

def analyze(run: Path, chassis: str | None) -> list[dict]:
    run = Path(run)
    res = json.loads((run / "results.json").read_text())
    exposure = float(res.get("exposure_s") or 3.0)
    vision = []
    vp = run / "camera" / "vision.jsonl"
    if vp.exists():
        for line in vp.read_text().splitlines():
            try:
                vision.append(json.loads(line))
            except ValueError:
                pass
    floor = floor_tags(chassis)
    rows = []
    for tr in res["trials"]:
        r = tr.get("result") or {}
        row = {"arm": tr["arm"], "base_arm": tr.get("base_arm") or tr["arm"].rsplit("_r", 1)[0], "file": tr.get("file"),
               "active_s": round(float(r.get("active_wall_time_s") or tr.get("active_s") or 0.0), 2), "ended": r.get("ended"), "error": r.get("error") or tr.get("start_refused") or tr.get("skipped"),
               "ticks": r.get("ticks"), "max_current_a": r.get("max_current_a"), "min_volt": tr.get("min_volt"), "hottest": (tr.get("temps_top3") or [None])[0]}
        csvp = run / "telemetry" / (tr.get("csv") or "")
        if tr.get("csv") and r.get("ticks") and csvp.exists():
            row.update(imu_metrics(list(csv.DictReader(csvp.open()))))
        live = [s.get("loop_hz") for s in tr.get("samples") or [] if s.get("loop_hz")]
        row["loop_hz"] = round(st.mean(live), 1) if live else None
        if vision and tr.get("t0_unix") and r.get("ticks"):
            row["cam"] = chassis_track(vision, tr["t0_unix"], tr["t0_unix"] + max(row["active_s"], 0.5), floor, chassis)
        rows.append(row)
    (run / "analysis.json").write_text(json.dumps(rows, indent=1))
    groups = collections.defaultdict(list)
    for r in rows:
        if r.get("ticks") and r.get("roll_rms") is not None:
            groups[r["base_arm"]].append(r)
    files = {r["base_arm"]: r.get("file") for r in rows}
    gaits, table = [], []
    for arm, rs in groups.items():
        v, why = verdict(rs, exposure)
        speeds = [r["cam"]["mm_s"] for r in rs if r.get("cam") and r["cam"].get("mm_s") is not None]
        heads = [r["cam"]["heading_chg_deg"] for r in rs if r.get("cam") and r["cam"].get("heading_chg_deg") is not None]
        tags = sorted({r["cam"]["tag"] for r in rs if r.get("cam")})
        metrics = {"roll_rms_deg": round(st.mean(r["roll_rms"] for r in rs), 2), "roll_peak_deg": round(max(r["roll_peak"] for r in rs), 2),
                   "pitch_rms_deg": round(st.mean(r["pitch_rms"] for r in rs), 2), "pitch_peak_deg": round(max(r["pitch_peak"] for r in rs), 2),
                   "max_current_a": max((r.get("max_current_a") or 0) for r in rs), "loop_hz": round(st.mean(r["loop_hz"] for r in rs if r.get("loop_hz")), 1) if any(r.get("loop_hz") for r in rs) else None,
                   "chassis_speed_mm_s": round(st.mean(speeds), 1) if speeds else None, "speed_each_mm_s": speeds,
                   "abs_heading_change_deg": round(max(abs(h) for h in heads), 1) if heads else None,
                   "active_s_each": [r["active_s"] for r in rs], "exposure_s": exposure, "vx_mps": res.get("vx"), "speed_tags": tags}
        note = f"{res.get('robot')}: {len(rs)} exposures at |vx| {res.get('vx')} m/s, planned {exposure:g} s each; {why}; speed from tag(s) {tags}."
        gaits.append({"gait": arm, "file": files.get(arm), "controller": "rl", "exposures": len(rs), "metrics": metrics, "verdict": v, "note": note})
        table.append((arm, len(rs), metrics, v))
    (run / "gaits.json").write_text(json.dumps(gaits, indent=1))
    lines = [f"# {res.get('robot')} gait sweep {run.name}", "",
             "| gait | n | s walked | roll rms deg | roll peak | pitch rms | speed mm/s | veer deg | max A | verdict |", "|---|---:|---|---:|---:|---:|---:|---:|---:|---|"]
    for arm, n, m, v in sorted(table, key=lambda t: t[2]["roll_rms_deg"]):
        lines.append(f"| {arm} | {n} | {'/'.join(f'{s:.1f}' for s in m['active_s_each'])} | {m['roll_rms_deg']} | {m['roll_peak_deg']} | {m['pitch_rms_deg']} | "
                     f"{m['chassis_speed_mm_s'] if m['chassis_speed_mm_s'] is not None else '-'} | {m['abs_heading_change_deg'] if m['abs_heading_change_deg'] is not None else '-'} | {m['max_current_a']} | {v} |")
    (run / "TABLE.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return rows


def table(runs: list[str]) -> None:
    lines = ["| robot | run | gait | n | s walked | roll rms deg | roll peak | pitch rms | speed mm/s | veer deg | max A | verdict |",
             "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|"]
    for run in runs:
        run = Path(run)
        if not (run / "gaits.json").exists():
            analyze(run, None)
        res = json.loads((run / "results.json").read_text())
        for g in sorted(json.loads((run / "gaits.json").read_text()), key=lambda g: g["metrics"]["roll_rms_deg"]):
            m = g["metrics"]
            lines.append(f"| {res.get('robot')} | {run.name[:13]} | {g['gait']} | {g['exposures']} | {'/'.join(f'{s:.1f}' for s in m.get('active_s_each', []))} | "
                         f"{m['roll_rms_deg']} | {m['roll_peak_deg']} | {m['pitch_rms_deg']} | {m['chassis_speed_mm_s'] if m.get('chassis_speed_mm_s') is not None else '-'} | "
                         f"{m['abs_heading_change_deg'] if m.get('abs_heading_change_deg') is not None else '-'} | {m['max_current_a']} | {g['verdict']} |")
    print("\n".join(lines))


class WalkAround:
    """Stand the robot and walk it between open-floor waypoints, steering by the top camera."""

    def __init__(self, args):
        self.a = args
        self.robot = Robot(args.host)
        self.out = Path(args.out)
        (self.out / "camera").mkdir(parents=True, exist_ok=True)
        self.cam_proc = None

    def log(self, msg):
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        with (self.out / "walk.log").open("a") as fh:
            fh.write(line + "\n")

    def pose(self):
        return read_chassis_pose(self.out, self.a.chassis_tag)

    def run(self) -> int:
        a, R = self.a, self.robot
        # camera up first: steering needs the chassis tag in view
        if not Path(CAMERAS_BIN).exists():
            sys.exit(f"hexapod-cameras not found at {CAMERAS_BIN}")
        chk = subprocess.run([CAMERAS_BIN, "check", "--role", a.camera_role], capture_output=True, text=True, timeout=120)
        try:
            j = json.loads(chk.stdout[chk.stdout.index("{"):])
        except Exception:
            sys.exit(f"camera check gave no JSON: {chk.stdout[-200:]}")
        if not j.get("ok"):
            sys.exit(f"top camera floor fit off ({j.get('drift_rms_px')} px); run `hexapod-cameras calibrate floor --role {a.camera_role}`")
        env = dict(os.environ, OPENCV_AVFOUNDATION_SKIP_AUTH="1")
        self.cam_proc = subprocess.Popen(
            [CAMERAS_BIN, "session", "--out", str(self.out / "camera"), "--roles", a.camera_role,
             "--hz", "8", "--fps", "30", "--seconds", str(int(a.max_s + 60)), "--no-stdin"],
            stdout=(self.out / "camera_session.log").open("w"), stderr=subprocess.STDOUT, env=env)
        for _ in range(60):
            if self.pose() is not None:
                break
            time.sleep(0.5)
        if self.pose() is None:
            self.cam_proc.terminate()
            sys.exit(f"chassis tag {a.chassis_tag} not visible from the {a.camera_role} camera; "
                     "the robot must be on the open floor, clear of cords, before I can steer it")
        try:
            return self._drive()
        finally:
            (self.out / "camera" / "STOP").write_text("stop")
            try:
                self.cam_proc.wait(timeout=20)
            except Exception:
                self.cam_proc.terminate()

    def _stand(self) -> bool:
        R = self.robot
        for role in ("hold", "walk"):
            R.post("/api/rl/roles", {"role": role, "file": self.a.gait})
        R.post("/api/rl/policy_select", {"file": self.a.gait})
        t0 = time.time()
        R.post("/api/rl/stand", {})
        while time.time() - t0 < 45:
            time.sleep(1)
            st = R.get("/api/demo/status")
            if not (st.get("demo") or {}).get("running") and st.get("mode") == "stand":
                break
        rb = R.get("/api/robot")
        pf = R.get("/api/rl/preflight?mode=walk")
        self.log(f"stood: armed={rb.get('armed')} tilt={pf.get('roll_deg')}/{pf.get('pitch_deg')}")
        if not rb.get("armed"):
            self.log("stand did not arm; stopping"); return False
        if abs(pf.get("roll_deg") or 0) > 12 or abs(pf.get("pitch_deg") or 0) > 15:
            self.log("robot is tilted after standing (pinned leg?); stopping"); return False
        return True

    def _drive(self) -> int:
        a, R = self.a, self.robot
        if R.get("/api/robot").get("armed"):
            self.log("robot already armed; limp it first"); return 1
        if not self._stand():
            self.robot.cmd("X"); return 2
        cal = calibrate_heading(R, self.pose, self.log)
        if cal is None:
            self.robot.cmd("X"); return 2
        waypoints = a.waypoints or [(300.0, 450.0), (300.0, 900.0)]
        self.log(f"patrol waypoints (floor mm): {waypoints}")
        owner = str(uuid.uuid4())
        R.post("/api/rl/drive/start", {"vx": 0.05, "vy": 0, "wz": 0, "dh": 0, "command_owner": owner}, timeout=40)
        t0 = time.time(); wi = 0; lost = 0; last_prog = time.time(); best = None
        try:
            while time.time() - t0 < a.max_s:
                pz = self.pose()
                if pz is None:
                    lost += 1
                    if lost >= 8:
                        self.log("lost the chassis tag for 8 reads; stopping"); break
                    time.sleep(0.2); continue
                lost = 0
                x, y, yaw = pz
                tgt = waypoints[wi]
                if a.keep_in and not inside_box((x, y), a.keep_in):
                    self.log(f"chassis left keep-in box at {x:.0f},{y:.0f}; stopping"); break
                if reached((x, y), tgt):
                    wi = (wi + 1) % len(waypoints)
                    self.log(f"reached waypoint; next -> {waypoints[wi]}"); continue
                d = math.hypot(tgt[0] - x, tgt[1] - y)
                if best is None or d < best - 20:
                    best = d; last_prog = time.time()
                elif time.time() - last_prog > 12:
                    self.log("no progress toward the waypoint for 12 s; stopping"); break
                vx, wz = steer_command((x, y), yaw, tgt, cal, vx_max=a.vx)
                hb = R.post("/api/rl/drive/cmd", {"vx": vx, "vy": 0, "wz": wz, "dh": 0, "command_owner": owner}, timeout=5)
                if hb.get("active") is False:
                    self.log(f"drive ended: {hb.get('error')}"); break
                time.sleep(0.25)
            R.post("/api/rl/drive/stop", {}, timeout=20)
        finally:
            try:
                R.post("/api/rl/lower", {}, timeout=40)
                for _ in range(45):
                    time.sleep(1)
                    if not ((R.get("/api/demo/status").get("demo") or {}).get("running")):
                        break
            finally:
                self.log(f"lowered; X -> {R.cmd('X')}")
        return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--host", default=os.environ.get("HEXAPOD_HOST", "http://hexapod.local:8080"))
    p.add_argument("--name", required=True, help="robot label for the results (hexapod1 / hexapod2)")
    p.add_argument("--out", required=True)
    p.add_argument("--arms", nargs="*", help="arm=walk.json[:hold.json] (default: the four catalogued gaits)")
    p.add_argument("--rounds", type=int, default=2)
    p.add_argument("--exposure-s", type=float, default=6.0)
    p.add_argument("--vx", type=float, default=0.10)
    p.add_argument("--chassis-tag", default=None, help="AprilTag id on this robot's chassis lid (hexapod2: 119)")
    p.add_argument("--camera-role", default="top")
    p.add_argument("--keep-in", default=None,
                   help="floor-mm box xmin,xmax,ymin,ymax the chassis tag must stay in; a pass stops when it leaves")
    p.add_argument("--first-direction", choices=("forward", "reverse"), default="forward",
                   help="which way the first pass goes (pick the one with the most floor ahead)")
    p.add_argument("--max-drift-mm", type=float, default=300.0,
                   help="beyond this distance from the sweep start the next exposure heads back (needs --chassis-tag)")
    p.add_argument("--no-camera", action="store_true")
    p = sub.add_parser("walk", help="stand, learn direction from the camera, patrol open-floor waypoints")
    p.add_argument("--host", default=os.environ.get("HEXAPOD_HOST", "http://hexapod.local:8080"))
    p.add_argument("--out", required=True)
    p.add_argument("--chassis-tag", required=True, help="AprilTag id on this robot's chassis lid (hexapod2: 119)")
    p.add_argument("--gait", default="walkteach_allhead_acq12m_100hz.json")
    p.add_argument("--waypoints", default=None, help="floor-mm x,y;x,y;... to patrol between (default two open-floor points)")
    p.add_argument("--keep-in", default=None, help="floor-mm box xmin,xmax,ymin,ymax the chassis must stay in")
    p.add_argument("--vx", type=float, default=0.09)
    p.add_argument("--max-s", type=float, default=120.0)
    p.add_argument("--camera-role", default="top")
    p = sub.add_parser("analyze"); p.add_argument("run"); p.add_argument("--chassis-tag", default=None)
    p = sub.add_parser("table"); p.add_argument("runs", nargs="+")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        arms = []
        for spec in args.arms or []:
            name, _, files = spec.partition("=")
            walk, _, hold = files.partition(":")
            arms.append((name, walk, hold or "ps200_parent.json"))
        args.arms = arms or DEFAULT_ARMS
        if args.keep_in:
            args.keep_in = tuple(float(v) for v in args.keep_in.split(","))
            if len(args.keep_in) != 4 or not args.chassis_tag:
                sys.exit("--keep-in needs xmin,xmax,ymin,ymax and --chassis-tag")
        return Sweep(args).run()
    if args.cmd == "walk":
        args.waypoints = [tuple(float(v) for v in wp.split(",")) for wp in args.waypoints.split(";")] if args.waypoints else None
        args.keep_in = tuple(float(v) for v in args.keep_in.split(",")) if args.keep_in else None
        return WalkAround(args).run()
    if args.cmd == "analyze":
        analyze(Path(args.run), args.chassis_tag)
        return 0
    table(args.runs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
