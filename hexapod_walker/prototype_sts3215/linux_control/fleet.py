#!/usr/bin/env python3
"""First command of a hardware session: what state is every robot in, and which
camera actually sees it.

    fleet.py status [--hosts a,b]          one line per robot + a bus/new-motor verdict
    fleet.py eye <robot>                    the camera source that shows THIS robot

Why this exists (2026-09-18 session): 40 minutes were lost identifying "the new
motor" on the wrong robot because the operator note said a laptop camera showed
hexapod2 when it shows hexapod1, and because the fresh servo's signature (bus
ID 1) was never checked first.  ``status`` answers "does this robot have an
un-set-up motor" from ``plan_swap`` and prints the last few attributed commands
so a stray drive from the hub or another session is visible at a glance.
``eye`` encodes the robot->camera mapping so the wrong-camera mistake cannot
repeat.  Both are read-only; nothing here moves a servo.

Robot names are ambiguous in this lab -- the operator has said "hexapod2" for
the .39 robot the code calls hexapod1 -- so ``status`` always polls the whole
fleet and labels rows by host, never trusts a single name.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from motor_swap import Robot, joint_name, plan_swap

# host -> the camera that actually frames that robot (verified 2026-09-18).
# The laptop server's cam 1 shows hexapod1 (red/blue) + the green donor chassis;
# its cam 0 points at a workbench.  hexapod2 (purple lid) is only in the Studio
# ELP side view.  The floor-fitted Studio top camera sees whichever robot is in
# the tag area (use it for metric gait sweeps).
DEFAULT_HOSTS = ["http://hexapod.local:8080", "http://hexapod2.local:8080"]
CAMERA_FOR = {
    "hexapod.local": {
        "what": "red/blue, AprilTag lids (+ green donor chassis in frame)",
        "how": "laptop server: curl -sf http://Lukass-MacBook-Pro-2.local:8766/snapshot/1.jpg (stream: /raw-stream/1.mjpg)",
    },
    "hexapod2.local": {
        "what": "purple lid, chassis tag 119",
        "how": "Studio side (ELP): (cd ~/hexapod-tracker && ./.venv/bin/hexapod-cameras snapshot --role side out.jpg)  [partial, bottom-right]",
    },
}
CAMERA_NOTE = ("Studio top camera (floor-fitted) frames whichever robot is in the tag area; "
               "use it for gait sweeps and run `hexapod-cameras check --role top` first. "
               "The laptop server cam 0 is a workbench, not a robot.")


def _host_key(host: str) -> str:
    """`http://hexapod2.local:8080` -> `hexapod2.local`."""
    h = host.split("://", 1)[-1]
    return h.split(":", 1)[0].split("/", 1)[0]


def session_line(name: str, robot: dict | None, plan: dict | None) -> str:
    """One human line summarising a robot's readiness for a hardware session.

    ``robot`` is the ``/api/robot`` body (or None if unreachable); ``plan`` is
    ``plan_swap(live_ids)`` (or None).  Pure: no I/O, so it is unit-tested.
    """
    if robot is None:
        return f"{name:16s} UNREACHABLE"
    servo = robot.get("servo") or {}
    live = servo.get("live")
    armed = "ARMED" if robot.get("armed") else "limp"
    temp = servo.get("max_temp_c")
    hot = servo.get("hottest")
    bits = [f"{name:16s}", f"{armed:5s}", f"{live}/18 servos"]
    if plan is not None:
        if plan.get("factory_id_present") or plan.get("missing_ids"):
            bits.append(f"NEW MOTOR: {plan['why']}")
        elif plan.get("stranger_ids"):
            bits.append(f"STRANGE BUS: {plan['why']}")
        else:
            bits.append("bus ok")
    if temp is not None:
        bits.append(f"hottest {hot} {temp}C")
    tripped = servo.get("tripped_names")
    if tripped:
        bits.append(f"TRIPPED {tripped}")
    return "  ".join(bits)


def camera_for(name: str) -> dict | None:
    """Camera source that shows the given robot (accepts host or hostname)."""
    return CAMERA_FOR.get(_host_key(name))


def _min_volt(robot: dict) -> float | None:
    volts = [m.get("volt") for m in (robot.get("motors") or []) if m.get("volt")]
    return min(volts) if volts else None


def cmd_status(args) -> int:
    hosts = args.hosts.split(",") if args.hosts else DEFAULT_HOSTS
    any_action_needed = False
    for host in hosts:
        name = _host_key(host)
        r = Robot(host)
        try:
            robot = r.get("/api/robot", timeout=6.0)
            if not isinstance(robot, dict):
                robot = None
        except (urllib.error.URLError, OSError, TimeoutError):
            robot = None
        plan = None
        if robot is not None:
            try:
                st = r.get("/api/status", timeout=6.0)
                if isinstance(st, dict) and st.get("live_ids") is not None:
                    plan = plan_swap(st["live_ids"])
                    robot = {**robot, "motors": st.get("motors") or []}
            except (urllib.error.URLError, OSError, TimeoutError):
                pass
        print(session_line(name, robot, plan))
        if robot is None or (plan and (plan.get("missing_ids") or plan.get("factory_id_present") or plan.get("stranger_ids"))):
            any_action_needed = True
        if robot is not None:
            mv = _min_volt(robot)
            if mv is not None:
                print(f"                   bus {mv:.1f} V" + ("  <-- below 10.8 V brownout band" if mv < 10.8 else ""))
            try:
                cj = r.get("/api/commands", timeout=6.0)
                entries = (cj.get("entries") or cj.get("commands") or []) if isinstance(cj, dict) else []
                for e in entries[-args.commands:]:
                    print(f"                   last: {e.get('ts','')[:19]} {e.get('controller','?')} {e.get('method','')} {e.get('path','')}")
            except (urllib.error.URLError, OSError, TimeoutError):
                pass
    return 1 if any_action_needed else 0


def cmd_eye(args) -> int:
    cam = camera_for(args.robot)
    if cam is None:
        print(f"no camera mapping for {args.robot!r}; known: {sorted(CAMERA_FOR)}", file=sys.stderr)
        print(CAMERA_NOTE, file=sys.stderr)
        return 2
    print(f"{_host_key(args.robot)} = {cam['what']}")
    print(f"  {cam['how']}")
    print(f"  note: {CAMERA_NOTE}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status", help="fleet readiness at a glance")
    p.add_argument("--hosts", default="", help="comma-separated robot base URLs (default: both robots)")
    p.add_argument("--commands", type=int, default=3, help="how many recent attributed commands to show")
    p = sub.add_parser("eye", help="which camera shows this robot")
    p.add_argument("robot", help="robot name or base URL (hexapod.local / hexapod2.local)")
    args = ap.parse_args(argv)
    return {"status": cmd_status, "eye": cmd_eye}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
