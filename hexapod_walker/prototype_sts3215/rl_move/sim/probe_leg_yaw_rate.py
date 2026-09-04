"""probe_leg_yaw_rate.py — per-leg scripted-TripodGait yaw-COMMAND
rate + foot-placement-consistency instrument (standwalk Next item 2
sub-step, 09-04).

WHY: the 09-03 combined-tick slew-clip finding
(``probe_joint_tracking.py``) measured only an AGGREGATE saturation
FRACTION across all six legs together (~48% of combined ticks vs ~0%
of pure-turn ticks). That number can't distinguish "every leg is
moderately over the clip" from "half the legs are wildly over and
half are fine" — which matters because a UNIFORM correction
(``TripodGait.combined_yaw_arm_scale``, all 4 dose x seed cells
FAIL'd at the RL stage) spends correction budget on legs that may not
need it. This tool:

1. Replays the scripted ``TripodGait`` at a fixed (vx, omega) command
   at the true control rate (100Hz) and reports, PER LEG, the max/p90
   commanded-yaw RATE (deg/s, finite difference of consecutive ticks)
   against the SafetyLayer's physically-pinned yaw slew clip
   (0.375deg/tick @ 100Hz = 37.5deg/s, operator order
   fb_20260824T174619_c49b7e — never raise this in production; this
   tool only compares against it as a read-only reference).
2. Supports the SAME ``combined_yaw_arm_scale`` (uniform) dose the
   production gait already has, plus the new SELECTIVE
   ``combined_yaw_amplify_scale`` (candidate (iii), only applied to
   legs whose true combined tangential magnitude exceeds their own
   pure-omega-only magnitude — see ``TripodGait.__init__``
   docstring), by importing and driving the REAL ``TripodGait`` class
   (never a re-implementation) so a probe result cannot silently
   drift from production behavior.
3. Reports a foot-placement CONSISTENCY metric per leg: the angle
   between the commanded (possibly dose-corrected) yaw-frame vector
   and the TRUE (dose=1.0-equivalent) target vector — 0deg means the
   correction didn't move the foot's intended direction at all, large
   values flag a candidate that silently reorients the foot away from
   its true target (caught THIS cycle: a "detangle the vx cross term
   out of the yaw numerator" idea was rejected zero-training this way
   — at any dose that meaningfully de-saturates it also flips sign on
   the previously-near-cancelled legs, and at full dose it creates a
   NEW saturated leg (4/6 over clip vs the legacy 3/6), so it was
   never wired into TripodGait/tests at all).

RESULT (09-04, same cycle): this tool's own headline metric — per-tick
commanded-yaw RATE vs. the SafetyLayer clip — is a RED HERRING for
turn authority. ``combined_yaw_amplify_scale=3.0`` fully de-saturates
it (0/6 legs over 37.5deg/s, was 3/6) but
``probe_turn_authority.py``'s scripted-teacher body ``wz_med`` gets
WORSE at that same dose (0.0723->0.0295 rad/s at
vx=0.08/wz_cmd=0.25), extending the 09-04 05:35 finding (raising the
clip itself 0.375->8.0deg also barely moved wz) to the OTHER side of
the same claim: neither raising the clip nor de-saturating below it
changes the real bottleneck. Keep this tool for future per-leg
candidates, but a low ``legs_over_clip``/``max_rate_deg_s`` reading
alone is NOT evidence of a real turn-authority win — always cross-
check with ``probe_turn_authority.py``'s actual body ``wz_med``
before proposing an RL canary.

Usage:
  uv run python -m rl_move.sim.probe_leg_yaw_rate \
      --vx-cmds 0.08 --omega-cmds 0.25,-0.25 \
      --amplify-scales 1.0,1.5,2.0,3.0 \
      --out logs/ckpt_eval/leg_yaw_rate_probe.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent
for _p in (_PROTO, _PROTO / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from hexapod_core.tripod_gait import TripodGait  # noqa: E402

# Physically-pinned SafetyLayer yaw slew clip (operator order
# fb_20260824T174619_c49b7e, NOT to be raised in production) expressed
# as a rate: 0.375 deg/tick @ 100Hz.
CLIP_DEG_PER_TICK = 0.375
CONTROL_HZ = 100.0
CLIP_DEG_PER_S = CLIP_DEG_PER_TICK * CONTROL_HZ

WALK_PLANT = (20.0, 100.0)


def sample(*, vx_cmd: float, omega_cmd: float, seconds: float = 3.0,
           hz: float = CONTROL_HZ, yaw_arm_scale: float = 1.0,
           amplify_scale: float = 1.0) -> dict[int, dict]:
    """Drives the REAL ``TripodGait`` at a fixed (vx, omega) command
    and returns, per leg index 0-5: max/p90 commanded-yaw rate
    (deg/s) and max/median foot-placement direction error (deg)
    against a dose=1.0/1.0 (legacy) reference run.
    """
    gait = TripodGait(vx=0.0, combined_yaw_arm_scale=yaw_arm_scale,
                       combined_yaw_amplify_scale=amplify_scale)
    gait.sync_plant_stance(*WALK_PLANT)
    gait.reset_phase()
    gait.set_velocity(vx=vx_cmd, omega=omega_cmd)

    ref = TripodGait(vx=0.0)
    ref.sync_plant_stance(*WALK_PLANT)
    ref.reset_phase()
    ref.set_velocity(vx=vx_cmd, omega=omega_cmd)

    dt = 1.0 / hz
    n = int(seconds * hz)
    yaw_hist: dict[int, list[float]] = {i: [] for i in range(6)}
    dir_err_hist: dict[int, list[float]] = {i: [] for i in range(6)}
    for k in range(1, n + 1):
        t = k * dt
        dosed_deg = gait.desired_deg(t)
        true_deg = ref.desired_deg(t)
        for i in range(6):
            yaw_hist[i].append(dosed_deg[3 * i])
            # foot-placement direction error: compare the DOSED yaw
            # angle against the TRUE (undosed) yaw angle for the same
            # leg/tick -- a proxy for "did this correction reorient
            # the foot's intended direction" (small for a pure
            # magnitude scale, large for something that changes sign).
            dir_err_hist[i].append(
                abs(_angle_diff_deg(dosed_deg[3 * i], true_deg[3 * i])))
    out = {}
    for i in range(6):
        ys = yaw_hist[i]
        rates = [abs(ys[k] - ys[k - 1]) / dt for k in range(1, len(ys))]
        rates_sorted = sorted(rates)
        derr_sorted = sorted(dir_err_hist[i])
        out[i] = {
            "max_rate_deg_s": max(rates) if rates else 0.0,
            "p90_rate_deg_s": (rates_sorted[int(0.9 * len(rates_sorted))]
                               if rates_sorted else 0.0),
            "max_dir_err_deg": max(derr_sorted) if derr_sorted else 0.0,
            "med_dir_err_deg": (derr_sorted[len(derr_sorted) // 2]
                                if derr_sorted else 0.0),
        }
    return out


def _angle_diff_deg(a: float, b: float) -> float:
    d = (a - b + 180.0) % 360.0 - 180.0
    return d


def summarize(per_leg: dict[int, dict]) -> dict:
    n_over = sum(1 for v in per_leg.values()
                 if v["max_rate_deg_s"] > CLIP_DEG_PER_S)
    return {
        "legs_over_clip": n_over,
        "clip_deg_per_s": CLIP_DEG_PER_S,
        "max_rate_deg_s": max(v["max_rate_deg_s"] for v in per_leg.values()),
        "max_dir_err_deg": max(v["max_dir_err_deg"] for v in per_leg.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vx-cmds", default="0.08")
    ap.add_argument("--omega-cmds", default="0.25,-0.25")
    ap.add_argument("--yaw-arm-scales", default="1.0",
                     help="TripodGait.combined_yaw_arm_scale doses (uniform)")
    ap.add_argument("--amplify-scales", default="1.0",
                     help="TripodGait.combined_yaw_amplify_scale doses (selective)")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    vx_cmds = [float(x) for x in args.vx_cmds.split(",") if x.strip()]
    omega_cmds = [float(x) for x in args.omega_cmds.split(",") if x.strip()]
    yaw_arm_scales = [float(x) for x in args.yaw_arm_scales.split(",") if x.strip()]
    amplify_scales = [float(x) for x in args.amplify_scales.split(",") if x.strip()]

    rows = []
    for vx_cmd in vx_cmds:
        for omega_cmd in omega_cmds:
            for yas in yaw_arm_scales:
                for ams in amplify_scales:
                    per_leg = sample(vx_cmd=vx_cmd, omega_cmd=omega_cmd,
                                      seconds=args.seconds,
                                      yaw_arm_scale=yas, amplify_scale=ams)
                    summ = summarize(per_leg)
                    row = {"vx_cmd": vx_cmd, "omega_cmd": omega_cmd,
                           "yaw_arm_scale": yas, "amplify_scale": ams,
                           **summ, "per_leg": per_leg}
                    rows.append(row)
                    print(f"[probe_leg_yaw_rate] vx={vx_cmd} omega={omega_cmd} "
                          f"yaw_arm_scale={yas} amplify_scale={ams} -> "
                          f"legs_over_clip={summ['legs_over_clip']}/6 "
                          f"max_rate={summ['max_rate_deg_s']:.1f}deg/s "
                          f"max_dir_err={summ['max_dir_err_deg']:.1f}deg")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=2))
        print(f"[probe_leg_yaw_rate] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
