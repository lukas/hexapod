"""probe_turn_eventsync.py — event-based phase-synchronization SCREEN on
the frozen full-mesh plant (todaypolicy steering, 2026-09-08, operator
focus note: "screen event-based phase synchronization using actual
per-leg joint lag/contact events").

Plain English: every global timing/geometry lever on the scripted
steering plant is closed (cadence, lift lead, stance arm/posture, omega
shaping, governor rescale, command twist re-projection, fixed-duty time
multiplexing).  The one distinct untested idea is EVENT-BASED PHASE
SYNCHRONIZATION: instead of advancing each leg's gait phase on the wall
clock, advance it on measured per-leg events (touchdown/liftoff), so
legs coordinate against what actually happened.  Per the focus note and
TIME_MULTIPLEX_REVIEW.md, a phase MISMATCH alone is NOT support
(earlier timing improvements lacked body-yaw gain); this probe is a
pure measurement that asks whether event-conditioned coordination
PREDICTS a sign-consistent yaw gain not explained by prior closure,
BEFORE any mechanism is implemented.  Zero training, zero robot work,
no plant/limit/gate changes.

What it measures per frozen cell (scripted TripodGait, arcs
vx=0.08 wz=+/-0.15 + straight guard, starts 0/pi, seed 0, 15 s):

1. PER-LEG EVENT OFFSETS: actual touchdown/liftoff (touch sensor edge)
   vs planned stance/swing boundary, circular offset in ms.  Split into
   the COMMON component (median across legs — already-closed global lag
   territory) and the LEG-DIFFERENTIAL component (what an event-based
   per-leg synchronizer could uniquely act on), plus per-leg IQR (the
   noise floor of the feedback signal itself).
2. SUPPORT-STATE-CONDITIONED YAW: classify each scored tick by executed
   loaded support (tripod A = legs {0,2,4}, B = {1,3,5}; pureA / pureB
   / mixed / degenerate) and report per-state wz/vx means and medians.
3. BEST-CASE EVENT-SYNC COUNTERFACTUAL: if per-leg re-phasing turned
   every mixed/degenerate-support tick into an average pure-support
   tick, what body wz results?  This deliberately OVERESTIMATES any
   real controller (tripod handoffs can never be zero-duration), so a
   failed bar here is decisive.

PRE-REGISTERED SUPPORT BAR (written before the measurement ran;
mirrors the prior closures' both-signs discipline).  SUPPORTED only if
ALL of:
  S1 gain: counterfactual wz gain in the COMMANDED direction
     >= +10% of |measured wz| on ALL FOUR arc cells (both signs x both
     starts).
  S2 signal: the event feedback carries a usable leg-differential
     component — inter-leg touchdown-offset spread >= 50 ms on every
     arc cell, OR max per-leg sign-differential (same start, +wz vs
     -wz) >= 30 ms.  Otherwise event sync collapses to a common phase
     shift, which is CLOSED (cadence closure: fractional lag improved
     0.29->0.21 and yaw REGRESSED both signs; lift-lead closure: the
     executed gait is already internally self-aligned).
  S3 health: the same counterfactual on the straight cells predicts
     |wz| <= 0.0074 rad/s (the measured baseline straight drift cap),
     zero falls anywhere, and bit-exact body-median parity with the
     stance-arm baseline (guards that this probe measures the same
     plant/gait, not a drifted harness).
UNSUPPORTED => document the negative, no preflight, no mechanism, no
canary (the focus note's own rule).
"""
from __future__ import annotations

import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent
for _p in (_PROTO, _PROTO / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.robot_state import DEG2RAD  # noqa: E402
from rl_move.sim import probe_turn_authority as pta  # noqa: E402
from rl_move.sim.eval_checkpoint import CONTACT_N, model_identity  # noqa: E402
from rl_move.sim.joint_task import q_rad_to_action  # noqa: E402
from rl_move.sim.servo_model import motor_contract  # noqa: E402
from rl_move.sim.probe_turn_stancearm import (  # noqa: E402
    LOAD_N, PIN, feasibility_guard, pin_manifest)

from hexapod_core.tripod_gait import TripodGait  # noqa: E402

TRIPOD_A = (0, 2, 4)
TRIPOD_B = (1, 3, 5)

# Pre-registered bar (see module docstring). Straight cap = measured
# baseline straight |wz| max (stance100_baseline_fm.json, phase pi).
BAR = {
    "s1_min_gain_frac": 0.10,
    "s2_min_interleg_spread_ms": 50.0,
    "s2_min_sign_differential_ms": 30.0,
    "s3_straight_wz_cap": 0.0074,
}

# Bit-exact parity references: stance-arm baseline body medians on the
# SAME frozen full-mesh plant/cells (artifacts/rl_watchdog/
# turn_stancearm_20260908/stance100_baseline_fm.json — itself bit-exact
# with the lift-lead and cadence baselines).
PARITY_REF = {
    (0.08, 0.15, 0.0): (0.06424356912738255, 0.03722226587463831, 1300),
    (0.08, 0.15, 3.141592653589793):
        (0.06322606606503198, 0.036275323376160386, 1300),
    (0.08, -0.15, 0.0): (-0.06305192853310224, 0.03636890899080783, 1300),
    (0.08, -0.15, 3.141592653589793):
        (-0.06506261172345035, 0.0369504033752522, 1300),
    (0.08, 0.0, 0.0): (-0.00015796815524232432, 0.040065720987130155, 1300),
    (0.08, 0.0, 3.141592653589793):
        (-0.007391347275148641, 0.04023429258659103, 1300),
}


def _edges(mask: np.ndarray, rising: bool) -> list[np.ndarray]:
    """Per-leg indices where a (T,6) bool mask rises (False->True) or
    falls (True->False); index is the tick AFTER the transition."""
    d = np.diff(mask.astype(np.int8), axis=0)
    want = 1 if rising else -1
    return [np.flatnonzero(d[:, f] == want) + 1 for f in range(mask.shape[1])]


def _circ_offsets(plan_idx: np.ndarray, actual_idx: np.ndarray,
                  period_ticks: float) -> np.ndarray:
    """For each planned event, signed circular offset (ticks) to the
    nearest actual event, wrapped to [-period/2, +period/2)."""
    if len(plan_idx) == 0 or len(actual_idx) == 0:
        return np.empty(0)
    half = period_ticks / 2.0
    out = []
    for tp in plan_idx:
        d = (actual_idx - tp + half) % period_ticks - half
        out.append(d[np.argmin(np.abs(d))])
    return np.asarray(out, dtype=float)


def event_offsets(plan_stance: np.ndarray, contact: np.ndarray,
                  period_ticks: float, dt_ms: float = 10.0) -> dict:
    """Per-leg touchdown/liftoff event offsets (actual vs plan), split
    into common + leg-differential components."""
    plan_td = _edges(plan_stance, rising=True)
    plan_lo = _edges(plan_stance, rising=False)
    act_td = _edges(contact, rising=True)
    act_lo = _edges(contact, rising=False)
    per_leg = {}
    med_td = []
    for f in range(plan_stance.shape[1]):
        td = _circ_offsets(plan_td[f], act_td[f], period_ticks) * dt_ms
        lo = _circ_offsets(plan_lo[f], act_lo[f], period_ticks) * dt_ms
        per_leg[f] = {
            "touchdown_med_ms": float(np.median(td)) if len(td) else None,
            "touchdown_iqr_ms": (float(np.subtract(
                *np.percentile(td, [75, 25]))) if len(td) else None),
            "touchdown_n": int(len(td)),
            "liftoff_med_ms": float(np.median(lo)) if len(lo) else None,
            "liftoff_n": int(len(lo)),
        }
        med_td.append(per_leg[f]["touchdown_med_ms"])
    med = [m for m in med_td if m is not None]
    common = float(np.median(med)) if med else None
    diffs = ([(m - common) if m is not None else None for m in med_td]
             if common is not None else [None] * 6)
    finite = [d for d in diffs if d is not None]
    return {
        "per_leg": per_leg,
        "touchdown_common_ms": common,
        "touchdown_differential_ms": diffs,
        "interleg_spread_ms": (float(max(finite) - min(finite))
                               if len(finite) >= 2 else None),
    }


def support_state_stats(loaded: np.ndarray, wz: np.ndarray,
                        vx: np.ndarray) -> dict:
    """Classify each tick by executed loaded support and compute the
    best-case event-sync counterfactual (mixed/degenerate ticks
    replaced by the pure-support average)."""
    nA = loaded[:, TRIPOD_A].sum(axis=1)
    nB = loaded[:, TRIPOD_B].sum(axis=1)
    pureA = (nA >= 2) & (nB <= 1)
    pureB = (nB >= 2) & (nA <= 1)
    mixed = (nA >= 2) & (nB >= 2)
    degen = ~(pureA | pureB | mixed)
    out = {"states": {}}
    for name, sel in (("pureA", pureA), ("pureB", pureB),
                      ("mixed", mixed), ("degenerate", degen)):
        out["states"][name] = {
            "frac": float(sel.mean()), "n": int(sel.sum()),
            "wz_mean": float(wz[sel].mean()) if sel.any() else None,
            "wz_med": float(np.median(wz[sel])) if sel.any() else None,
            "vx_mean": float(vx[sel].mean()) if sel.any() else None,
        }
    out["wz_mean_overall"] = float(wz.mean())
    out["wz_med_overall"] = float(np.median(wz))
    n_pure = int(pureA.sum() + pureB.sum())
    if n_pure:
        wz_pure_avg = float(wz[pureA | pureB].mean())
        # counterfactual: every mixed/degenerate tick performs like an
        # average pure-support tick (upper bound for any re-phaser)
        cf = float((wz[pureA | pureB].sum()
                    + (len(wz) - n_pure) * wz_pure_avg) / len(wz))
    else:
        wz_pure_avg = cf = None
    out["wz_pure_avg"] = wz_pure_avg
    out["wz_counterfactual_mean"] = cf
    out["pure_frac"] = n_pure / max(len(wz), 1)
    return out


def cell_gain(summary: dict, wz_cmd: float) -> float | None:
    """Counterfactual gain in the COMMANDED direction as a fraction of
    the measured overall |wz| (arc cells only)."""
    cf = summary.get("wz_counterfactual_mean")
    m = summary.get("wz_mean_overall")
    if cf is None or m is None or wz_cmd == 0.0 or abs(m) < 1e-9:
        return None
    return float((cf - m) * math.copysign(1.0, wz_cmd) / abs(m))


def verdict(results: list[dict], bar: dict = BAR) -> dict:
    """Mechanical pre-registered support verdict (see docstring)."""
    arcs = [r for r in results if abs(r["wz_cmd"]) > 1e-9]
    straights = [r for r in results if abs(r["wz_cmd"]) <= 1e-9]
    checks = {}
    gains = {f"({r['wz_cmd']:+.2f},{r['phase_offset']:.2f})":
             cell_gain(r["support_states"], r["wz_cmd"]) for r in arcs}
    checks["s1_gains"] = gains
    checks["s1_pass"] = (len(arcs) >= 4 and all(
        g is not None and g >= bar["s1_min_gain_frac"]
        for g in gains.values()))
    spreads = [r["events"]["interleg_spread_ms"] for r in arcs]
    checks["s2_interleg_spread_ms"] = spreads
    spread_ok = (len(spreads) > 0 and all(
        s is not None and s >= bar["s2_min_interleg_spread_ms"]
        for s in spreads))
    sign_diffs = []
    for pos in [r for r in arcs if r["wz_cmd"] > 0]:
        for neg in [r for r in arcs if r["wz_cmd"] < 0
                    and abs(r["phase_offset"] - pos["phase_offset"]) < 1e-9]:
            dp = pos["events"]["touchdown_differential_ms"]
            dn = neg["events"]["touchdown_differential_ms"]
            pair = [abs(a - b) for a, b in zip(dp, dn)
                    if a is not None and b is not None]
            if pair:
                sign_diffs.append(max(pair))
    checks["s2_sign_differential_ms"] = sign_diffs
    sign_ok = (len(sign_diffs) > 0
               and max(sign_diffs) >= bar["s2_min_sign_differential_ms"])
    checks["s2_pass"] = bool(spread_ok or sign_ok)
    cf_straight = [abs(r["support_states"]["wz_counterfactual_mean"])
                   for r in straights
                   if r["support_states"].get("wz_counterfactual_mean")
                   is not None]
    checks["s3_straight_cf_wz"] = cf_straight
    falls = any(r["fell"] for r in results)
    parity_ok = all(r.get("parity", {}).get("ok") for r in results)
    checks["s3_pass"] = (all(v <= bar["s3_straight_wz_cap"]
                             for v in cf_straight)
                         and not falls and parity_ok)
    checks["zero_falls"] = not falls
    checks["parity_ok"] = parity_ok
    return {"bar": bar, "checks": checks,
            "supported": bool(checks["s1_pass"] and checks["s2_pass"]
                              and checks["s3_pass"])}


def rollout(*, cfg_set, vx_cmd, wz_cmd, seed, episode_seconds,
            phase_offset=0.0, plant: str = "twin") -> dict:
    """Scripted-gait rollout; identical env-facing sequence to
    probe_turn_stancearm.rollout (parity asserted vs its baseline)."""
    env = pta.make_env(cfg_set, seed, episode_seconds)
    identity = model_identity(env)
    contract = motor_contract(env.cfg)
    want = "full_mesh" if plant == "fullmesh" else "mesh_mjx_twin"
    if identity["model_variant"] != want:
        raise RuntimeError(f"pin fail: variant {identity} != {want}")
    if plant == "fullmesh" and identity["model_nmesh"] != 34:
        raise RuntimeError(f"pin fail: nmesh {identity['model_nmesh']}")
    if abs(identity["model_mass_kg"] - PIN["model_mass_kg"]) > 1e-6:
        raise RuntimeError(f"pin fail: mass {identity['model_mass_kg']}")
    if abs(env.dt - 0.01) > 1e-12:
        raise RuntimeError(f"pin fail: dt {env.dt}")
    for k in ("bus.write_speed", "bus.write_acc", "safety.max_delta_q_deg",
              "slew_limit_deg_s", "resolved_vel_max_counts_s_max"):
        if abs(float(contract[k]) - PIN[k]) > 1e-9:
            raise RuntimeError(f"pin fail: contract {k}={contract[k]}")

    obs, info = env.reset()
    if phase_offset:
        env._phase = float(phase_offset) % (2 * math.pi)

    traj = env._goal_traj
    n = len(traj.vx)
    hold_n = ramp_n = int(round(1.0 / env.dt))
    traj.vx[:] = vx_cmd; traj.vy[:] = 0.0; traj.wz[:] = wz_cmd
    traj.vx[:hold_n] = 0.0; traj.wz[:hold_n] = 0.0
    traj.vx[hold_n:hold_n + ramp_n] = np.linspace(0.0, vx_cmd, ramp_n)
    traj.wz[hold_n:hold_n + ramp_n] = np.linspace(0.0, wz_cmd, ramp_n)

    gait = TripodGait(vx=0.0)
    gait.sync_plant_stance(*pta.WALK_PLANT)
    gait.reset_phase(phase=phase_offset)

    rows = []
    step = 0
    fell = False
    while True:
        cmd_wz = float(traj.wz[min(step, n - 1)])
        cmd_vx = float(traj.vx[min(step, n - 1)])
        t = step * env.dt
        gait.set_velocity(vx=cmd_vx, omega=cmd_wz)
        q_des = np.asarray(gait.desired_deg(t)) * DEG2RAD
        act = q_rad_to_action(q_des)
        plan_swing = np.array(gait.leg_swing_state())
        obs, r, term, trunc, info = env.step(act)
        if step >= hold_n + ramp_n and info.get("goal_mode") == "walk":
            force = np.array([float(env.data.sensordata[x])
                              for x in env._touch_adr])
            rows.append({"plan_swing": plan_swing, "force": force,
                         "vx_body": float(env._body_vel_xy()[0]),
                         "wz_body": float(env._body_wz())})
        step += 1
        if term:
            fell = True
        if term or trunc:
            break
    env.close()

    out = {"policy": "scripted", "vx_cmd": vx_cmd, "wz_cmd": wz_cmd,
           "seed": seed, "phase_offset": phase_offset, "fell": fell,
           "n_scored_ticks": len(rows), "model_identity": identity,
           "period_eff_s": gait.period * gait.period_scale,
           "motor_contract": {k: contract[k] for k in
                              ("bus.write_speed", "bus.write_acc",
                               "safety.max_delta_q_deg", "slew_limit_deg_s",
                               "resolved_vel_max_counts_s_max",
                               "control.hz")}}
    if len(rows) < 200:
        out["error"] = "insufficient scored ticks"
        return out

    force = np.stack([r["force"] for r in rows])
    contact = force > CONTACT_N
    loaded = force > LOAD_N
    plan_stance = ~np.stack([r["plan_swing"] for r in rows]).astype(bool)
    wz = np.array([r["wz_body"] for r in rows])
    vx = np.array([r["vx_body"] for r in rows])

    out["body"] = {"vx_med": float(np.median(vx)),
                   "wz_med": float(np.median(wz))}
    ref = PARITY_REF.get((vx_cmd, wz_cmd, phase_offset))
    if ref is not None:
        out["parity"] = {
            "ref_wz_med": ref[0], "ref_vx_med": ref[1],
            "ref_n_scored_ticks": ref[2],
            "ok": bool(out["body"]["wz_med"] == ref[0]
                       and out["body"]["vx_med"] == ref[1]
                       and len(rows) == ref[2]),
            "scope": "body medians + scored tick count vs the stance-arm "
                     "baseline (summary parity, not trajectory parity)"}
    else:
        out["parity"] = {"ok": None, "scope": "no pinned reference cell"}

    period_ticks = gait.period * gait.period_scale / env.dt
    out["events"] = event_offsets(plan_stance, contact, period_ticks)
    out["duty_contact"] = contact.mean(axis=0).round(4).tolist()
    out["duty_loaded"] = loaded.mean(axis=0).round(4).tolist()
    out["support_states"] = support_state_stats(loaded, wz, vx)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg-json", type=Path, required=True)
    ap.add_argument("--cells", required=True, help="vx:wz,...")
    ap.add_argument("--phase-offsets", default="0.0")
    ap.add_argument("--plant", choices=("twin", "fullmesh"), default="twin")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    pins = pin_manifest(args.plant)
    cfg_set = json.loads(args.cfg_json.read_text())
    cfg_set = [c for c in cfg_set if not c.startswith("env.model_source=")]
    cfg_set.append("env.model_source="
                   + ("mesh" if args.plant == "fullmesh" else "mesh_mjx"))

    cells = [tuple(float(x) for x in c.split(":"))
             for c in args.cells.split(",")]
    st_hip, st_knee = pta.WALK_PLANT
    feas = feasibility_guard(st_hip, st_knee, cells)
    print(json.dumps({"feasibility": feas}), flush=True)

    results = []
    for vx, wz in cells:
        for po in (float(x) for x in args.phase_offsets.split(",")):
            r = rollout(cfg_set=cfg_set, vx_cmd=vx, wz_cmd=wz,
                        seed=args.seed,
                        episode_seconds=args.episode_seconds,
                        phase_offset=po, plant=args.plant)
            results.append(r)
            print(json.dumps({"cell": [vx, wz], "start": po,
                              "fell": r["fell"], "body": r.get("body"),
                              "parity_ok": r.get("parity", {}).get("ok"),
                              "gain": (cell_gain(r["support_states"], wz)
                                       if "support_states" in r else None),
                              "label": args.label}), flush=True)
    v = verdict(results)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(
        {"schema": "hexapod.turn_eventsync_probe.v1", "label": args.label,
         "policy": "scripted", "plant": args.plant,
         "stance_hip_deg": st_hip, "stance_knee_deg": st_knee,
         "feasibility": feas, "pin_manifest": pins, "pin_expect": PIN,
         "cfg_set": cfg_set, "seed": args.seed,
         "episode_seconds": args.episode_seconds,
         "support_verdict": v, "results": results},
        indent=1, default=str) + "\n")
    print(json.dumps({"support_verdict": v["checks"],
                      "supported": v["supported"]}), flush=True)
    print("COMPLETE", args.out, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
