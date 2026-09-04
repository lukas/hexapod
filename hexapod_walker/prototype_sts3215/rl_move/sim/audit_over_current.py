"""Audit simulated over_current trips: estimator rail vs real stall.

OPERATOR DIRECTIVE (2026-09-04, fb_20260904T074505_6a3ac9): repeated
bit-exact 2.64 A trips are NOT dispositive evidence a policy is unsafe.
This tool makes the estimator's anatomy explicit and classifies each
alleged trip with corroborating dynamics, so current telemetry can be
reported separately from physical-quality verdicts.

ESTIMATOR ANATOMY (rl_move/sim/sim_env.py::_read_state):

    raw_current  = min(|actuator_torque| * 1.2 A/N*m, 3.0 A)
    servo_current = lowpass(raw_current, tau=0.1 s)

The actuator forcerange is +-2.2 N*m, so |torque| saturates at 2.2 and
2.2 * 1.2 = 2.64 A EXACTLY. A bit-exact 2.64 A reading therefore means
"the modeled actuator torque sat at its forcerange rail long enough for
the 0.1 s lowpass to converge" — it is the RAIL IMAGE of actuator
saturation, not an independently measured winding current. The
SafetyLayer trips `over_current` when max servo_current > safety.
max_current_a (default 2.5, cap29 lineage 2.9) for safety.
over_current_trip_s sustained. Because 2.5 < 2.64, ANY sustained
torque demand >= 2.083 N*m trips, and every deep-stall trip reads the
same 2.64 A: the bit-exact pin the operator flagged is a mechanical
consequence of clip(2.2)*1.2, confirmed here per-trace.

CLASSIFICATION per episode (needs a --rollout-trace-out npz from
eval_checkpoint.py; disable the trip sim-side with
--cfg-set safety.max_current_a=999 to see past the would-be trip):

  - NO_RAIL:            no joint ever holds >= 2.639 A.
  - RAIL_TRANSIENT:     rail dwell exists but never sustains trip_s.
  - RAIL_MOVING:        sustained rail, but the hot joint keeps moving
                        (median |qvel| >= stall_qvel) or height keeps
                        rising — high modeled load, NOT a stall.
  - CORROBORATED_STALL: sustained rail + hot joint essentially static
                        + no height progress over the window. This is
                        the only class that corroborates "unsafe".

SENSITIVITY: torque is recovered exactly at/below the rail by
deconvolving the lowpass (alpha = dt/(dt+0.1)), so trip incidence is
recomputed under a defensible (amps_per_nm, trip_threshold_a, trip_s)
grid without re-running physics.

Usage:
    uv run python -m rl_move.sim.audit_over_current trace1.npz [trace2 ...] \
        [--trip-a 2.9] [--trip-s 0.8] [--stall-qvel 0.05] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

AMPS_PER_NM = 1.2          # sim_env.py estimator constant
FORCERANGE_NM = 2.2        # actuator forcerange (both model families)
RAIL_A = AMPS_PER_NM * FORCERANGE_NM   # 2.64 exactly
CUR_CAP_A = 3.0            # estimator stall cap
LP_TAU_S = 0.1             # estimator lowpass time constant


def _windows(mask: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous True runs as [start, end) index pairs."""
    if not mask.any():
        return []
    d = np.diff(mask.astype(int))
    starts = list(np.where(d == 1)[0] + 1)
    ends = list(np.where(d == -1)[0] + 1)
    if mask[0]:
        starts = [0] + starts
    if mask[-1]:
        ends = ends + [len(mask)]
    return list(zip(starts, ends))


def deconvolve_torque(cur: np.ndarray, dt: float) -> np.ndarray:
    """Invert the estimator lowpass to per-tick |torque| (N*m).

    raw_t = (filt_t - (1-a)*filt_{t-1}) / a,  a = dt/(dt+tau); tick 0
    seeds the filter so raw_0 = filt_0. Exact inverse of the sim's
    forward filter; raw/1.2 is |torque| clipped at the 2.2 rail (the
    3.0 A cap only binds above the rail, unreachable under clip).
    """
    a = dt / (dt + LP_TAU_S)
    raw = np.empty_like(cur)
    raw[0] = cur[0]
    raw[1:] = (cur[1:] - (1.0 - a) * cur[:-1]) / a
    return np.clip(raw, 0.0, CUR_CAP_A) / AMPS_PER_NM


def classify_trace(npz_path: str, *, trip_a: float, trip_s: float,
                   stall_qvel: float) -> dict:
    d = np.load(npz_path, allow_pickle=True)
    ep = json.loads(str(d["ep_json"]))
    cur = np.asarray(d["servo_current"], dtype=np.float64)  # (T, 18)
    t_s = np.asarray(d["t_s"], dtype=np.float64)
    dt = float(np.median(np.diff(t_s))) if len(t_s) > 1 else 0.01
    qvel = (np.asarray(d["qvel"], dtype=np.float64)
            if "qvel" in d else None)
    height = (np.asarray(d["height_mm"], dtype=np.float64)
              if "height_mm" in d else None)

    rail = cur >= (RAIL_A - 0.001)                # per joint
    hot = int(np.argmax(cur.max(axis=0)))
    trip_ticks = max(1, int(round(trip_s / dt)))

    # Longest sustained window ABOVE the configured trip threshold on
    # the worst joint (what the SafetyLayer actually integrates).
    over = (cur > trip_a).any(axis=1)
    over_wins = _windows(over)
    longest = max((e - s for s, e in over_wins), default=0)

    out = {
        "trace": str(npz_path),
        "mode": ep.get("mode"), "start_kind": ep.get("start_kind"),
        "term_reason": ep.get("term_reason"),
        "cur_max_a": float(cur.max()),
        "rail_identity_2p64": bool(abs(cur.max() - RAIL_A) < 5e-3
                                   or cur.max() < RAIL_A),
        "hot_joint": hot,
        "rail_any_frac": float(rail.any(axis=1).mean()),
        "rail_hot_dwell_s": float(rail[:, hot].sum() * dt),
        "over_thresh_longest_s": float(longest * dt),
        "would_trip": bool(longest >= trip_ticks),
    }

    # Corroboration on the longest over-threshold window.
    if longest >= trip_ticks and over_wins:
        s, e = max(over_wins, key=lambda w: w[1] - w[0])
        w = {"win_t0_s": float(t_s[s]), "win_t1_s": float(t_s[min(e, len(t_s) - 1)])}
        if qvel is not None and qvel.shape[1] >= 6 + 18:
            vhot = np.abs(qvel[s:e, 6 + hot])
            w["hot_qvel_med_rad_s"] = float(np.median(vhot))
            w["hot_static"] = bool(np.median(vhot) < stall_qvel)
        if height is not None and np.isfinite(height[s:e]).any():
            hh = height[s:e][np.isfinite(height[s:e])]
            w["height_delta_mm"] = float(hh[-1] - hh[0]) if len(hh) > 1 else 0.0
            w["height_progressing"] = bool(len(hh) > 1
                                           and (hh[-1] - hh[0]) > 5.0)
        out["window"] = w
        static = w.get("hot_static", False)
        rising = w.get("height_progressing", False)
        out["classification"] = ("CORROBORATED_STALL"
                                 if static and not rising
                                 else "RAIL_MOVING")
    elif rail.any():
        out["classification"] = "RAIL_TRANSIENT"
    else:
        out["classification"] = "NO_RAIL"

    # Parameter sensitivity via exact torque deconvolution.
    tau_nm = deconvolve_torque(cur, dt)
    sens = {}
    for apn in (0.9, 1.05, 1.2, 1.35, 1.5):
        for th in (2.5, 2.9, 3.2):
            cur_alt = np.minimum(tau_nm * apn, CUR_CAP_A)
            # forward lowpass
            a = dt / (dt + LP_TAU_S)
            f = np.empty_like(cur_alt)
            f[0] = cur_alt[0]
            for i in range(1, len(f)):
                f[i] = (1 - a) * f[i - 1] + a * cur_alt[i]
            ov = (f > th).any(axis=1)
            lg = max((e2 - s2 for s2, e2 in _windows(ov)), default=0)
            sens[f"apn{apn}_th{th}"] = {
                "max_a": round(float(f.max()), 3),
                "longest_over_s": round(float(lg * dt), 2),
                "would_trip": bool(lg >= trip_ticks),
            }
    out["sensitivity"] = sens
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("traces", nargs="+")
    ap.add_argument("--trip-a", type=float, default=2.9,
                    help="trip threshold to audit (cap29 lineage: 2.9)")
    ap.add_argument("--trip-s", type=float, default=0.8)
    ap.add_argument("--stall-qvel", type=float, default=0.05,
                    help="median |qvel| (rad/s) below which the hot "
                         "joint counts as static")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    results = [classify_trace(t, trip_a=args.trip_a, trip_s=args.trip_s,
                              stall_qvel=args.stall_qvel)
               for t in args.traces]
    for r in results:
        print(f"{Path(r['trace']).name}: {r['classification']}"
              f"  (max {r['cur_max_a']:.3f} A, hot j{r['hot_joint']},"
              f" over-{args.trip_a}A longest {r['over_thresh_longest_s']:.2f}s,"
              f" would_trip={r['would_trip']})")
        if "window" in r:
            print("   window:", json.dumps(r["window"]))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(results, indent=1))
        print("wrote", args.json)


if __name__ == "__main__":
    main()
