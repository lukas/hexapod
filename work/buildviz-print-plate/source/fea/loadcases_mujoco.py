#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["mujoco", "numpy"]
# ///
"""Extract worst-case load cases for fea/weakspots.py.

Two modes:

1. MuJoCo simulation (needs an MJCF model of the robot):
       uv run fea/loadcases_mujoco.py --mjcf robot.xml [--duration 4] [--drop-mm 150]
   Simulates the model (optionally dropped from a height), records the peak
   contact force on every body and peak actuator torques, and prints the worst
   cases plus a loadcase JSON skeleton with the peak force filled in.

2. Static estimate (no MJCF needed — uses the BuildViz mass estimate):
       uv run fea/loadcases_mujoco.py --static --from-build prototype_sts3215 [--feet 6] [--impact-g 3]
       uv run fea/loadcases_mujoco.py --static --mass-kg 5.1 --feet 6 --impact-g 3
   Worst cases reported: all feet sharing an impact-g landing, and the classic
   killer — the full impact on ONE foot (bad step / obstacle strike).

Both modes print loadcase JSON for weakspots.py. Coordinates ("at", fixtures)
must be filled in by you in the PART's own frame (mm) — run
`uv run fea/weakspots.py part.stl --inspect` for the part's bbox.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

G = 9.81


def loadcase_template(name: str, force_n: float) -> dict:
    return {
        "name": name,
        "material": {"name": "PLA", "youngMPa": 3500, "poisson": 0.36, "yieldMPa": 50},
        "fixtures": [{"type": "sphere", "center": ["FILL_X", "FILL_Y", "FILL_Z"], "radiusMm": 6}],
        "loads": [{"type": "force", "at": ["FILL_X", "FILL_Y", "FILL_Z"], "radiusMm": 5,
                   "forceN": [0, 0, -round(force_n, 1)]}],
    }


def static_mode(args: argparse.Namespace) -> None:
    mass_kg = args.mass_kg
    if args.from_build:
        result = subprocess.run(
            ["npx", "buildviz", "mass", args.from_build, "--json"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            sys.exit(f"buildviz mass failed:\n{result.stderr[-500:]}")
        payload = json.loads(result.stdout)
        report = payload.get("results") or payload.get("result") or payload
        grams = report.get("totalGrams")
        if grams is None:
            sys.exit("Could not read totalGrams from buildviz mass --json output")
        mass_kg = grams / 1000
        print(f"mass from BuildViz estimate: {mass_kg:.2f} kg "
              "(configure checksConfig.partMassesGrams for bought parts if you haven't)")
    if not mass_kg:
        sys.exit("--static needs --mass-kg or --from-build")

    weight = mass_kg * G
    shared = weight * args.impact_g / args.feet
    single = weight * args.impact_g

    print(f"\nweight: {weight:.1f} N · impact factor {args.impact_g}g · {args.feet} feet")
    print(f"case A  landing, all feet share:   {shared:.1f} N per foot")
    print(f"case B  bad step, ONE foot takes:  {single:.1f} N  <- usually the design driver")
    print("\nloadcase JSON for case B (fill in coordinates in the part frame):")
    print(json.dumps(loadcase_template(
        f"single-foot landing {args.impact_g}g x {mass_kg:.2f}kg", single), indent=2))


def mujoco_mode(args: argparse.Namespace) -> None:
    import mujoco
    import numpy as np

    model = mujoco.MjModel.from_xml_path(args.mjcf)
    data = mujoco.MjData(model)
    if args.drop_mm:
        # Lift the free joint root by the drop height (expects a floating base).
        if model.nq >= 3:
            data.qpos[2] += args.drop_mm / 1000
    mujoco.mj_forward(model, data)

    steps = int(args.duration / model.opt.timestep)
    body_peak: dict[str, tuple[float, np.ndarray, np.ndarray]] = {}
    torque_peak: dict[str, float] = {}
    force6 = np.zeros(6)

    for _ in range(steps):
        mujoco.mj_step(model, data)
        for c in range(data.ncon):
            contact = data.contact[c]
            mujoco.mj_contactForce(model, data, c, force6)
            magnitude = float(np.linalg.norm(force6[:3]))
            geom = contact.geom2 if contact.geom2 >= 0 else contact.geom1
            body = model.body(model.geom_bodyid[geom]).name or f"body{geom}"
            if magnitude > body_peak.get(body, (0.0, None, None))[0]:
                body_peak[body] = (magnitude, contact.pos.copy(), force6[:3].copy())
        for j in range(model.nu):
            name = model.actuator(j).name or f"act{j}"
            torque_peak[name] = max(torque_peak.get(name, 0.0), abs(float(data.actuator_force[j])))

    print(f"simulated {args.duration}s ({steps} steps)"
          + (f" with {args.drop_mm}mm drop" if args.drop_mm else ""))
    print("\npeak contact force per body:")
    worst_name, worst = "", (0.0, None, None)
    for body, peak in sorted(body_peak.items(), key=lambda kv: -kv[1][0]):
        print(f"  {body:24s} {peak[0]:9.1f} N  at {np.round(peak[1] * 1000, 1).tolist()} mm (world)")
        if peak[0] > worst[0]:
            worst_name, worst = body, peak
    if torque_peak:
        print("\npeak actuator torques (joint checks):")
        for name, torque in sorted(torque_peak.items(), key=lambda kv: -kv[1])[:8]:
            print(f"  {name:24s} {torque:9.2f} Nm")

    if worst[1] is not None:
        print(f"\nworst case: {worst[0]:.1f} N on {worst_name}")
        template = loadcase_template(f"mujoco worst contact ({worst_name})", worst[0])
        template["loads"][0]["forceN"] = [round(-float(f), 1) for f in worst[2]]
        print("loadcase JSON (translate 'at'/fixture coords into the part frame):")
        print(json.dumps(template, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Worst-case load extraction for weakspots.py")
    parser.add_argument("--mjcf", help="MuJoCo MJCF model path (simulation mode)")
    parser.add_argument("--duration", type=float, default=4.0, help="sim seconds (default 4)")
    parser.add_argument("--drop-mm", type=float, default=0.0, help="drop the robot from this height")
    parser.add_argument("--static", action="store_true", help="static estimate instead of simulation")
    parser.add_argument("--mass-kg", type=float, help="robot mass for --static")
    parser.add_argument("--from-build", help="BuildViz build id: read mass from `buildviz mass --json`")
    parser.add_argument("--feet", type=int, default=6, help="feet sharing a landing (default 6)")
    parser.add_argument("--impact-g", type=float, default=3.0, help="impact factor in g (default 3)")
    args = parser.parse_args()

    if args.mjcf:
        mujoco_mode(args)
    elif args.static:
        static_mode(args)
    else:
        parser.error("pick a mode: --mjcf robot.xml, or --static")


if __name__ == "__main__":
    main()
