#!/usr/bin/env python3
"""Commission a replaced STS3215 through the robot's own web API.

A fresh servo ships as bus ID 1 (``FACTORY_SERVO_ID``) with an arbitrary
zero.  After a swap the robot stands on 17 servos plus an unnamed ID 1 and
every stand refuses with "no encoder reading from <joint>".  This tool runs
the same steps the /setup page offers, from a laptop, with the checks that
are easy to forget in between:

    status   which slot is empty, whether ID 1 is on the bus, flat-pose
             outliers (limp robot, legs straight out = all joints ~0)
    assign   scan, move ID 1 into the empty slot, re-read the bus
    zero     Feetech middle-calibrate the given ids where they sit
    check    gentle single-servo wiggle, then a bigger torque-on wiggle;
             optional --stream frame-diffs an MJPEG feed and reports where
             in the image the motion happened, so the joint can be tied to
             a physical leg without trusting the encoder alone

Robot selection: ``--host`` or ``HEXAPOD_HOST`` (default
http://hexapod.local:8080; hexapod2.local is the other robot).  Nothing here
writes EEPROM except ``assign`` (ID) and ``zero`` (offset); both refuse
while the robot is armed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

from hexapod_core.joint_frame import (
    FACTORY_SERVO_ID, N_JOINTS, SERVO_IDS, axis_of, joint_of_servo, leg_of,
    servo_id,
)

DEFAULT_HOST = os.environ.get("HEXAPOD_HOST", "http://hexapod.local:8080")
FLAT_TOL_DEG = 15.0


# --- pure decisions (tested) -------------------------------------------------

def joint_name(j: int) -> str:
    return f"L{leg_of(j)} {axis_of(j)}"


def plan_swap(live_ids: list[int]) -> dict:
    """What the bus inventory says about a motor swap.

    ``ready`` is True only when exactly one robot slot is empty and exactly
    one factory-ID servo is present: that is the single case ``assign`` will
    act on.  Anything else is described in ``why`` for the operator.
    """
    live = set(int(i) for i in live_ids)
    missing = sorted(sid for sid in SERVO_IDS if sid not in live)
    factory = FACTORY_SERVO_ID in live
    strangers = sorted(i for i in live if i not in SERVO_IDS and i != FACTORY_SERVO_ID)
    plan = {
        "missing_ids": missing,
        "missing_joints": [joint_name(joint_of_servo(sid)) for sid in missing],
        "factory_id_present": factory,
        "stranger_ids": strangers,
        "ready": False,
        "target_id": None,
        "target_joint": None,
        "why": "",
    }
    if strangers:
        plan["why"] = f"unexpected ids on the bus: {strangers}; sort those out first"
    elif not missing and not factory:
        plan["why"] = "all 18 robot ids answer and no factory id: nothing to assign"
    elif missing and not factory:
        plan["why"] = (f"missing {plan['missing_joints']} but no ID {FACTORY_SERVO_ID} on the bus: "
                       "check the new servo's power/data lead")
    elif factory and not missing:
        plan["why"] = (f"ID {FACTORY_SERVO_ID} is on the bus but every slot is full: "
                       "the old servo is still connected, or this is a spare")
    elif len(missing) > 1:
        plan["why"] = f"{len(missing)} slots empty {plan['missing_joints']}: pass --joint to pick one"
    else:
        plan.update(ready=True, target_id=missing[0], target_joint=joint_of_servo(missing[0]),
                    why=f"assign ID {FACTORY_SERVO_ID} -> ID {missing[0]} ({plan['missing_joints'][0]})")
    return plan


def flat_pose_outliers(degrees: list[float | None], tol: float = FLAT_TOL_DEG) -> list[tuple[int, float]]:
    """Joints that do not read ~0 while the robot lies limp with legs straight out."""
    out = []
    for j, d in enumerate(degrees[:N_JOINTS]):
        if d is None or abs(float(d)) > tol:
            out.append((j, float("nan") if d is None else float(d)))
    return out


# --- robot API ---------------------------------------------------------------

class Robot:
    def __init__(self, host: str):
        self.host = host.rstrip("/")

    def _req(self, path: str, data: bytes | None, timeout: float) -> dict | str:
        req = urllib.request.Request(self.host + path, data=data, method="POST" if data is not None else "GET",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                txt = r.read().decode()
        except urllib.error.HTTPError as e:
            txt = e.read().decode()
        try:
            return json.loads(txt or "{}")
        except ValueError:
            return txt.strip()

    def get(self, path: str, timeout: float = 20.0):
        return self._req(path, None, timeout)

    def post(self, path: str, body: dict | None = None, timeout: float = 60.0):
        return self._req(path, json.dumps(body or {}).encode(), timeout)

    def cmd(self, line: str):
        return self._req("/cmd", line.encode(), 15.0)

    def armed(self) -> bool:
        return bool(self.get("/api/robot").get("armed"))

    def pose(self) -> list[float | None]:
        return list(self.get("/api/pose").get("degrees") or [])


def require_limp(robot: Robot) -> None:
    if robot.armed():
        sys.exit("robot is armed; send X (limp) first")


# --- commands ----------------------------------------------------------------

def cmd_status(robot: Robot, args) -> int:
    st = robot.get("/api/status")
    live = st.get("live_ids") or []
    plan = plan_swap(live)
    print(f"{robot.host}  armed={st.get('armed')}  {st.get('status')}")
    print(f"live ids ({len(live)}): {live}")
    print(f"swap: {plan['why']}")
    print(" id  joint     deg    volt  temp  vmax  torque  alarm")
    for m in st.get("motors") or []:
        name = m.get("name") or "?"
        print(" %2d  %-8s %6.1f  %5.1f  %3d   %4.1f  %d       %s" % (
            m["id"], name, m.get("deg") or 0.0, m.get("volt") or 0.0, m.get("temp_c") or 0,
            m.get("volt_limit_max") or 0.0, m.get("torque") or 0, "ALARM " + ",".join(m.get("status_bits") or []) if m.get("alarm") else "-"))
    if not st.get("armed"):
        outl = flat_pose_outliers(robot.pose(), args.flat_tol)
        if outl:
            print(f"flat-pose outliers (>|{args.flat_tol:.0f}| deg, legs straight out should read ~0): "
                  + ", ".join(f"{joint_name(j)}={d:.1f}" for j, d in outl))
            print("  a new servo reads its factory offset here; a hand-displaced yaw is harmless")
        else:
            print(f"flat pose: all joints within {args.flat_tol:.0f} deg of zero")
    return 0 if not plan["missing_ids"] else 1


def cmd_assign(robot: Robot, args) -> int:
    require_limp(robot)
    scan = robot.post("/api/setup/scan", {})
    if not scan.get("ok"):
        sys.exit(f"scan failed: {scan}")
    plan = plan_swap(scan.get("ids") or [])
    if scan.get("new_ids") != [FACTORY_SERVO_ID]:
        sys.exit(f"scan new_ids={scan.get('new_ids')}; assign only handles a single ID {FACTORY_SERVO_ID}")
    joint = args.joint
    if joint is None:
        if not plan["ready"]:
            sys.exit(f"cannot pick the slot: {plan['why']}")
        joint = plan["target_joint"]
    target = servo_id(joint)
    if target in (scan.get("ids") or []):
        sys.exit(f"{joint_name(joint)} (ID {target}) still answers on the bus; unplug the old servo first")
    print(f"scan ok: {plan['why'] if plan['ready'] else scan}")
    res = robot.post("/api/setup/assign", {"source_id": FACTORY_SERVO_ID, "joint": joint, "replace": True})
    print("assign:", res.get("message") or res)
    if not res.get("ok"):
        return 2
    time.sleep(1.0)
    st = robot.get("/api/status")
    after = plan_swap(st.get("live_ids") or [])
    print(f"bus after: {len(st.get('live_ids') or [])} live; {after['why']}")
    deg = next((m.get("deg") for m in st.get("motors") or [] if m.get("id") == target), None)
    print(f"{joint_name(joint)} now ID {target}, reads {deg} deg -> run `zero --ids {target}` with the leg straight and flat")
    return 0 if not after["missing_ids"] else 2


def cmd_zero(robot: Robot, args) -> int:
    require_limp(robot)
    ids = sorted(set(args.ids))
    before = robot.pose()
    print("pose before:", [None if x is None else round(x, 1) for x in before])
    res = robot.post("/api/set_zero", {"ids": ids}, timeout=90)
    print(f"set_zero {ids} -> ok={res.get('ok')} {res.get('ok_n')}/{res.get('count')} plant_cleared={res.get('plant_cleared')} {res.get('error') or ''}")
    for r in res.get("results") or []:
        if not r.get("ok"):
            print("   id", r.get("id"), "FAILED", r.get("error", ""))
    after = robot.pose()
    changed = [(joint_name(j), before[j], after[j]) for j in range(min(len(before), len(after)))
               if before[j] is not None and after[j] is not None and abs(after[j] - before[j]) > 1.0]
    print("changed:", [(n, round(b, 1), round(a, 1)) for n, b, a in changed] or "nothing")
    bad = [sid for sid in ids if abs(after[joint_of_servo(sid)] or 0.0) > 2.0]
    if bad:
        print(f"WARNING ids {bad} do not read ~0 after calibrate; check for a host-side trim (feetech_trims.json)")
    return 0 if res.get("ok") and not bad else 2


def _grab_frames(url: str, frames: list, stop) -> None:
    import cv2  # optional: only for --stream
    cap = cv2.VideoCapture(url)
    while not stop.is_set():
        ok, im = cap.read()
        if ok:
            frames.append((time.time(), cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)))
    cap.release()


def _motion_report(frames: list, n_base: int, t0: float) -> str:
    import cv2
    import numpy as np
    if len(frames) < n_base + 5:
        return "too few frames"
    base = np.median(np.stack([f for _, f in frames[:n_base]]), axis=0).astype(np.uint8)
    best = None
    for ts, img in frames[n_base:]:
        d = cv2.GaussianBlur(cv2.absdiff(img, base), (7, 7), 0)
        m = (d > 30).astype(np.uint8)
        n, _lab, stats, cents = cv2.connectedComponentsWithStats(m)
        if n > 1:
            k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            area = int(stats[k, cv2.CC_STAT_AREA])
            if best is None or area > best[0]:
                best = (area, ts - t0, tuple(int(v) for v in stats[k, :4]), tuple(int(v) for v in cents[k]))
    if not best or best[0] < 200:
        return "no motion seen on the stream (is this camera looking at this robot?)"
    return "motion: %d px at t=%.1fs bbox(x,y,w,h)=%s centroid=%s" % best


def cmd_check(robot: Robot, args) -> int:
    require_limp(robot)
    j = args.joint
    frames: list = []
    stop = None
    if args.stream:
        import threading
        stop = threading.Event()
        threading.Thread(target=_grab_frames, args=(args.stream, frames, stop), daemon=True).start()
        deadline = time.time() + 10
        while len(frames) < 15 and time.time() < deadline:
            time.sleep(0.1)
        if len(frames) < 15:
            print("stream gave no frames; continuing without camera")
            stop.set(); stop = None
    n_base = len(frames)
    gentle = robot.post("/api/setup/wiggle", {"joint": j})
    print(f"gentle wiggle {joint_name(j)} (one servo, 15% torque, +-3 deg): {gentle.get('message') or gentle.get('error')}")
    if not gentle.get("ok") and "resistance" in str(gentle.get("error")):
        print("the joint met resistance: stop here, the leg needs hands")
        return 2
    t0 = time.time()
    if args.amp > 0:
        before = robot.pose()[j]
        res = robot.post("/api/wiggle", {"joint": j, "amp": args.amp})
        time.sleep(1.8)
        limp = robot.cmd("X")
        after = robot.pose()[j]
        print(f"torque-on wiggle +-{args.amp:g} deg: {res.get('result') or res.get('error')} ; X -> {limp} ; "
              f"{joint_name(j)} {before} -> {after} deg")
    if stop is not None:
        time.sleep(1.0); stop.set(); time.sleep(0.3)
        print(_motion_report(frames, n_base, t0))
    print("armed:", robot.armed())
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default=DEFAULT_HOST, help="robot web API (HEXAPOD_HOST)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status"); p.add_argument("--flat-tol", type=float, default=FLAT_TOL_DEG)
    p = sub.add_parser("assign"); p.add_argument("--joint", type=int, help="joint index 0-17 (default: the one empty slot)")
    p = sub.add_parser("zero"); p.add_argument("--ids", type=int, nargs="+", required=True, help="servo ids to middle-calibrate")
    p = sub.add_parser("check"); p.add_argument("--joint", type=int, required=True)
    p.add_argument("--amp", type=float, default=15.0, help="torque-on wiggle amplitude, 0 = gentle only")
    p.add_argument("--stream", default="", help="MJPEG url to frame-diff, e.g. http://host:8766/raw-stream/1.mjpg")
    args = ap.parse_args(argv)
    robot = Robot(args.host)
    return {"status": cmd_status, "assign": cmd_assign, "zero": cmd_zero, "check": cmd_check}[args.cmd](robot, args)


if __name__ == "__main__":
    sys.exit(main())
