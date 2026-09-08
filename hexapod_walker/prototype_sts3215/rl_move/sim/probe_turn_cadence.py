"""probe_turn_cadence.py — cadence (period_scale) vs turn authority, on
the frozen full-mesh plant (todaypolicy steering, 2026-09-08 follow-up
after the stance-arm closure).

Plain English: two prior bounded, zero-training experiments closed the
same yaw deficit as NOT an arm/rate/timing problem: the lift-lead
closure showed the executed gait is already internally phase-aligned
(uniform ~0.21s pipeline delay, not a lift/sweep misalignment), and the
stance-arm closure showed a genuinely bigger moment arm (+19% yaw-arm
gain) sheds its whole gain into loaded-pad slip instead of body
rotation (traction-limited conversion, both directions inside noise).
Both point at stride FREQUENCY: a fixed first-order servo-profile lag
attenuates a FRACTION of each cycle's commanded sweep, and that
fraction — plus the tangential acceleration a fixed sweep amplitude
needs — shrinks at a slower cadence. `TripodGait.set_scales
(period_scale=...)` already exists and is bounded (SCALE_PERIOD
0.40..2.00); this probe doses ONE slower cadence (period_scale 1.5,
inside bounds) vs baseline (1.0) at the SAME arc/straight cells as the
stance-arm and lift-lead closures, and requires the SAME both-signs
gain bar before any GPU canary is justified.

Independent review (fb_20260908T014636_88b7c1) flagged three things
this probe must do, all satisfied:
  1. FIX THE DIAGNOSTIC GUARD FIRST (`feasibility_guard` must reject a
     `raw_leg_ik`-returns-None case instead of silently accepting
     TripodGait's finite neutral-pose fallback) — landed in the shared
     `probe_turn_stancearm.feasibility_guard` (commit 975d6c36,
     `test_probe_turn_stancearm.py` 5/5 green); this probe reuses that
     exact guard (generalized here to accept `period_scale` too, still
     bit-exact at 1.0 — see `test_probe_turn_cadence.py`).
  2. A slower period_scale stretches the WHOLE cycle: "ideal" (fixed
     tangential foot speed) stance-foot velocity and XY reversal
     jumps are UNCHANGED by design (same commanded stride per cycle,
     just spread over more time) — the honest test is fewer
     reversals-per-second / vertical-lift tracking / FRACTIONAL lag,
     not a generic "everything gets easier at a lower rate" read. This
     probe reports `reversal_rate_hz`, `achieved_lift_p90_mm`, and
     `contact_lag_frac` (lag as a fraction of the EFFECTIVE period, not
     absolute ms) precisely so a genuine per-cycle improvement can be
     told apart from "fewer, noisier cycles measured".
  3. Pad-origin finite-difference speeds and LSQ residuals alone do
     NOT prove a unique traction limit — this probe's own claims stay
     scoped to what it actually measures (wz gain/loss, slip, lift,
     lag, reversal rate) and do not re-assert the stance-arm closure's
     traction-limit interpretation as settled physics.

Same pre-registered bar as both prior closures: only a measured wz
gain in BOTH turn directions, with gait/progress/slip retained and
zero new falls, justifies one bounded 2M existing-seed training
canary. Scripted controller only (a frozen policy cannot take a
cadence dose); single seed (0), starts 0/pi, arcs +/-0.15 + straight
guard, matching the stance-arm/lift-lead cell set exactly.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent
for _p in (_PROTO, _PROTO / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.sim import probe_turn_authority as pta  # noqa: E402
from rl_move.sim.probe_turn_stancearm import (  # noqa: E402
    PIN, feasibility_guard, pin_manifest, rollout)

from hexapod_core.tripod_gait import TripodGait  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", choices=("scripted",), default="scripted",
                    help="cadence is a scripted-gait dose only")
    ap.add_argument("--cfg-json", type=Path, required=True)
    ap.add_argument("--cells", required=True, help="vx:wz,...")
    ap.add_argument("--phase-offsets", default="0.0")
    ap.add_argument("--period-scale", type=float, default=1.0,
                    help="TripodGait.set_scales(period_scale=...), "
                         "bounded SCALE_PERIOD 0.40..2.00 (default 1.0 = "
                         "stock cadence, bit-exact with the stance-arm "
                         "baseline)")
    ap.add_argument("--plant", choices=("twin", "fullmesh"), default="twin",
                    help="twin: checked-in hexapod_mesh_mjx.xml (the pod "
                         "training plant); fullmesh: the frozen 7efb8e8a "
                         "full-STL XML (must be present in this tree)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    if not (TripodGait.SCALE_PERIOD_MIN <= args.period_scale
            <= TripodGait.SCALE_PERIOD_MAX):
        raise SystemExit(f"period_scale {args.period_scale} outside "
                         f"[{TripodGait.SCALE_PERIOD_MIN}, "
                         f"{TripodGait.SCALE_PERIOD_MAX}]")

    pins = pin_manifest(args.plant)
    cfg_set = json.loads(args.cfg_json.read_text())
    cfg_set = [c for c in cfg_set if not c.startswith("env.model_source=")]
    cfg_set.append("env.model_source="
                   + ("mesh" if args.plant == "fullmesh" else "mesh_mjx"))

    cells = [tuple(float(x) for x in c.split(":"))
             for c in args.cells.split(",")]
    st_hip, st_knee = pta.WALK_PLANT
    feas = feasibility_guard(st_hip, st_knee, cells,
                             period_scale=args.period_scale)
    print(json.dumps({"feasibility": feas}), flush=True)

    results = []
    for vx, wz in cells:
        for po in (float(x) for x in args.phase_offsets.split(",")):
            r = rollout(policy="scripted", model=None, model_obs_width=None,
                        cfg_set=cfg_set, vx_cmd=vx, wz_cmd=wz,
                        seed=args.seed, episode_seconds=args.episode_seconds,
                        phase_offset=po, stance_hip_deg=st_hip,
                        stance_knee_deg=st_knee,
                        period_scale=args.period_scale, plant=args.plant)
            results.append(r)
            print(json.dumps({"cell": [vx, wz], "start": po,
                              "fell": r["fell"], "body": r.get("body"),
                              "label": args.label}), flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(
        {"schema": "hexapod.turn_cadence_probe.v1", "label": args.label,
         "policy": "scripted", "period_scale": args.period_scale,
         "stance_hip_deg": st_hip, "stance_knee_deg": st_knee,
         "feasibility": feas, "plant": args.plant,
         "pin_manifest": pins, "pin_expect": PIN, "cfg_set": cfg_set,
         "seed": args.seed, "episode_seconds": args.episode_seconds,
         "results": results},
        indent=1, default=str) + "\n")
    print("COMPLETE", args.out, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
