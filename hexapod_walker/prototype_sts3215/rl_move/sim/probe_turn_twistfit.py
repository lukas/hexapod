"""probe_turn_twistfit.py — same-phase commanded vs actual stance XY
path twist-consistency measurement (todaypolicy steering diagnostic,
2026-09-08 focus-note follow-up to the full-cone rerun).

Plain English: the corrected full-cone audit (root_fullcone_20260908)
measured heavy friction-cone engagement and opposing per-leg yaw
moments on the frozen steering plant, but opposing moments alone do
not prove the COMMANDED stance paths are inconsistent with a single
rigid-body twist.  This probe measures that directly: at every scored
control tick it reconstructs the stance-foot XY paths in the body
frame at four pipeline stages —

  des  : the gait's commanded foot targets (FK of desired joints)
  safe : the post-SafetyLayer slew-clipped command (FK of q_safe)
  act  : the measured servo response (FK of joint_position)
  pads : the true mesh foot pads straight from MuJoCo

— and least-squares fits ONE planar rigid twist (vx, vy, wz) per tick
across the same-phase stance feet, recording per-foot residuals and
per-foot implied yaw rates.  For the commanded stage it additionally
scores the residual against the EXACT commanded twist evaluated at
the current commanded foot positions (the direct chord-vs-arc /
anchor-vs-current-position inconsistency of TripodGait's stance law,
which freezes each stance foot's velocity at its nominal anchor).

PRE-REGISTERED SUPPORT BAR (written before the first rollout): a
command-side stance-sweep correction (re-projecting stance sweeps
onto the exact commanded twist; swing/touchdown retained) is
SUPPORTED only if on ALL FOUR arc cells (wz=+/-0.15 at starts 0 and
pi) the COMMANDED (des-stage, plan-stance) paths are themselves
twist-inconsistent:
  S1  fitted wz / commanded wz outside [0.90, 1.10], or
  S2  normalized residual vs the exact commanded twist at current
      commanded positions > 0.10, or
  S3  per-foot implied-wz spread (max-min of per-foot medians)
      > 0.20 * |wz_cmd|.
Attenuation that first appears at safe/act/pads (execution) does NOT
support a command re-projection and is reported as the measured
outcome instead.

Isolated read-only diagnostic: no shared code changed, no training,
scripted TripodGait only, stock stance/cadence, frozen plant pins
(fullmesh34 / 4.80573 kg / 100 Hz / unchanged servo contract)
hard-asserted per rollout, fail-closed IK/limit feasibility guard,
and a behavior-parity check against the root_fullcone scripted
baseline medians (instrumentation must not change behavior).

Usage (from the frozen prototype dir):
  uv run python -m rl_move.sim.probe_turn_twistfit \
      --cfg-json cfg_frozen_audit.json \
      --cells 0.08:0.15,0.08:-0.15,0.08:0 \
      --phase-offsets 0.0,3.14159265 --seed 0 --episode-seconds 15 \
      --parity-json logs/ckpt_eval/root_fullcone_20260908/scripted_audit_fm.json \
      --out twistfit.json
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
from rl_move.sim.probe_turn_pipeline import fk_body_xy  # noqa: E402

from hexapod_core.tripod_gait import TripodGait  # noqa: E402

PIN = {
    "model_mass_kg": 4.80573,
    "model_nmesh": 34,
    "control_hz": 100.0,
    "bus.write_speed": 400.0,
    "bus.write_acc": 20.0,
    "safety.max_delta_q_deg": 0.375,
    "slew_limit_deg_s": 37.5,
    "resolved_vel_max_counts_s_max": 350.0,
}

# pre-registered support bar (see module docstring)
BAR = {"wz_gain_lo": 0.90, "wz_gain_hi": 1.10,
       "cmd_resid_norm": 0.10, "implied_wz_spread_frac": 0.20}
EDGE_ERODE_TICKS = 2   # drop this many ticks at each stance-segment edge
MIN_FEET = 3           # per-tick twist fit needs >= 3 same-phase stance feet


# ---------------------------------------------------------------- pure math
def twist_pred_vel(pos_xy: np.ndarray, twist) -> np.ndarray:
    """Body-frame velocity of world-fixed points under twist (vx,vy,wz):
    p_dot = -(v + w x p)."""
    vx, vy, wz = float(twist[0]), float(twist[1]), float(twist[2])
    out = np.empty_like(pos_xy, dtype=float)
    out[:, 0] = -(vx - wz * pos_xy[:, 1])
    out[:, 1] = -(vy + wz * pos_xy[:, 0])
    return out


def fit_twist_resid(pos_xy: np.ndarray, vel_xy: np.ndarray,
                    sel: np.ndarray):
    """LSQ planar twist over selected feet; returns (twist, resid(6,2))
    with residual = vel - predicted (NaN where unselected), or None."""
    idx = np.flatnonzero(sel)
    if len(idx) < MIN_FEET:
        return None
    rows, rhs = [], []
    for f in idx:
        px, py = pos_xy[f]
        rows.append([1.0, 0.0, -py]); rhs.append(-vel_xy[f, 0])
        rows.append([0.0, 1.0, px]); rhs.append(-vel_xy[f, 1])
    sol, *_ = np.linalg.lstsq(np.asarray(rows), np.asarray(rhs), rcond=None)
    resid = np.full((len(pos_xy), 2), np.nan)
    resid[idx] = (vel_xy[idx] - twist_pred_vel(pos_xy[idx], sol))
    return sol, resid


def implied_wz(pos_xy: np.ndarray, vel_xy: np.ndarray, vxy_fit) -> np.ndarray:
    """Per-foot yaw rate implied by each foot's own velocity given the
    fitted linear part: w x p = -(vel) - v  =>  wz = cross(p, -vel-v)/|p|^2."""
    ex = -vel_xy[:, 0] - vxy_fit[0]
    ey = -vel_xy[:, 1] - vxy_fit[1]
    d2 = np.maximum((pos_xy ** 2).sum(axis=1), 1e-12)
    return (pos_xy[:, 0] * ey - pos_xy[:, 1] * ex) / d2


def erode_segments(sel_col: np.ndarray, erode: int) -> np.ndarray:
    """Boolean stance column -> eroded copy (drop `erode` ticks at each
    edge of every contiguous True run)."""
    sel = np.asarray(sel_col, dtype=bool)
    if erode <= 0:
        return sel.copy()
    out = sel.copy()
    n = len(sel)
    starts = np.flatnonzero(sel & ~np.roll(sel, 1))
    ends = np.flatnonzero(sel & ~np.roll(sel, -1))
    if sel[0]:
        starts = np.unique(np.append(starts, 0))
    if sel[-1]:
        ends = np.unique(np.append(ends, n - 1))
    for s in starts:
        out[s:min(s + erode, n)] = False
    for e in ends:
        out[max(e - erode + 1, 0):e + 1] = False
    return out


def segments(sel_col: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous True runs as (start, end_inclusive)."""
    sel = np.asarray(sel_col, dtype=bool)
    out, s = [], None
    for i, v in enumerate(sel):
        if v and s is None:
            s = i
        elif not v and s is not None:
            out.append((s, i - 1)); s = None
    if s is not None:
        out.append((s, len(sel) - 1))
    return out


def analyze_stage(pos_seq: np.ndarray, sel_seq: np.ndarray, dt: float,
                  cmd_twists: np.ndarray | None = None) -> dict | None:
    """Per-tick twist fits over stance feet for one pipeline stage.

    pos_seq (T,6,2), sel_seq (T,6) bool (already edge-eroded),
    cmd_twists (T,3) optional exact commanded twist per tick."""
    T = len(pos_seq)
    fits, resids, speeds = [], [], []
    imp_rows = np.full((T, 6), np.nan)
    cmd_resid, cmd_speed = [], []
    for t in range(1, T):
        sel = sel_seq[t] & sel_seq[t - 1]
        if sel.sum() < MIN_FEET:
            continue
        vel = (pos_seq[t] - pos_seq[t - 1]) / dt
        pos = 0.5 * (pos_seq[t] + pos_seq[t - 1])
        fr = fit_twist_resid(pos, vel, sel)
        if fr is None:
            continue
        twist, resid = fr
        fits.append(twist)
        resids.append(resid[sel])
        speeds.append(np.linalg.norm(vel[sel], axis=1))
        iw = implied_wz(pos, vel, twist[:2])
        imp_rows[t, sel] = iw[sel]
        if cmd_twists is not None:
            pred = twist_pred_vel(pos[sel], cmd_twists[t])
            cmd_resid.append(np.linalg.norm(vel[sel] - pred, axis=1))
            cmd_speed.append(np.linalg.norm(pred, axis=1))
    if not fits:
        return None
    f = np.asarray(fits)
    rr = np.concatenate([np.linalg.norm(r, axis=1) for r in resids])
    sp = np.concatenate(speeds)
    med_speed = float(np.median(sp)) if len(sp) else float("nan")
    per_foot_iw = [float(np.nanmedian(imp_rows[:, k]))
                   if np.isfinite(imp_rows[:, k]).any() else None
                   for k in range(6)]
    iw_ok = [v for v in per_foot_iw if v is not None]
    out = {
        "n_fits": len(fits),
        "vx_med": float(np.median(f[:, 0])),
        "vy_med": float(np.median(f[:, 1])),
        "wz_med": float(np.median(f[:, 2])),
        "resid_rms_mps": float(np.sqrt(np.mean(rr ** 2))),
        "resid_norm": float(np.sqrt(np.mean(rr ** 2)) / max(med_speed, 1e-9)),
        "med_foot_speed_mps": med_speed,
        "per_foot_implied_wz_med": per_foot_iw,
        "implied_wz_spread": (float(max(iw_ok) - min(iw_ok))
                              if len(iw_ok) >= 2 else None),
    }
    if cmd_twists is not None and cmd_resid:
        cr = np.concatenate(cmd_resid)
        cs = np.concatenate(cmd_speed)
        out["cmd_exact_resid_rms_mps"] = float(np.sqrt(np.mean(cr ** 2)))
        out["cmd_exact_resid_norm"] = float(
            np.sqrt(np.mean(cr ** 2)) / max(float(np.median(cs)), 1e-9))
    return out


def sweep_segments(des_xy: np.ndarray, pads_xy: np.ndarray,
                   plan_st: np.ndarray, min_len: int = 8) -> list[dict]:
    """Per stance segment per foot: commanded vs actual net XY sweep
    (body frame). Direct amplitude/heading attenuation evidence."""
    rows = []
    for foot in range(6):
        for s, e in segments(plan_st[:, foot]):
            if e - s + 1 < min_len:
                continue
            dc = des_xy[e, foot] - des_xy[s, foot]
            da = pads_xy[e, foot] - pads_xy[s, foot]
            nc, na = float(np.linalg.norm(dc)), float(np.linalg.norm(da))
            ang = None
            if nc > 1e-6 and na > 1e-6:
                ang = float(math.degrees(
                    math.atan2(dc[0] * da[1] - dc[1] * da[0],
                               float(dc @ da))))
            rows.append({"foot": foot, "start": int(s), "end": int(e),
                         "cmd_sweep_m": nc, "act_sweep_m": na,
                         "amp_ratio": (na / nc) if nc > 1e-6 else None,
                         "heading_err_deg": ang})
    return rows


def support_verdict(cells: list[dict]) -> dict:
    """Mechanically evaluate the pre-registered support bar over the
    arc cells (wz_cmd != 0)."""
    arc = [c for c in cells if abs(c["wz_cmd"]) > 1e-9]
    checks = []
    for c in arc:
        des = (c.get("stages", {}).get("des", {}) or {}).get("plan")
        if not des:
            checks.append({"cell": [c["vx_cmd"], c["wz_cmd"]],
                           "start": c["phase_offset"], "breach": None,
                           "reason": "no des-stage fits"})
            continue
        gain = des["wz_med"] / c["wz_cmd"]
        s1 = not (BAR["wz_gain_lo"] <= gain <= BAR["wz_gain_hi"])
        s2 = des.get("cmd_exact_resid_norm", 0.0) > BAR["cmd_resid_norm"]
        spread = des.get("implied_wz_spread")
        s3 = (spread is not None
              and spread > BAR["implied_wz_spread_frac"] * abs(c["wz_cmd"]))
        checks.append({"cell": [c["vx_cmd"], c["wz_cmd"]],
                       "start": c["phase_offset"],
                       "des_wz_gain": gain,
                       "cmd_exact_resid_norm":
                           des.get("cmd_exact_resid_norm"),
                       "implied_wz_spread": spread,
                       "S1": s1, "S2": s2, "S3": s3,
                       "breach": bool(s1 or s2 or s3)})
    supported = (len(checks) == 4
                 and all(c["breach"] is True for c in checks))
    return {"bar": BAR, "checks": checks, "supported": supported}


# ---------------------------------------------------------------- rollout
def rollout(*, cfg_set, vx_cmd, wz_cmd, seed, episode_seconds,
            phase_offset=0.0) -> dict:
    env = pta.make_env(cfg_set, seed, episode_seconds)
    identity = model_identity(env)
    contract = motor_contract(env.cfg)
    if identity["model_variant"] != "full_mesh":
        raise RuntimeError(f"pin fail: variant {identity}")
    if identity["model_nmesh"] != PIN["model_nmesh"]:
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

    d = env.data
    rows = []
    step = 0
    fell = False
    try:
        while True:
            cmd_wz = float(traj.wz[min(step, n - 1)])
            cmd_vx = float(traj.vx[min(step, n - 1)])
            t = step * env.dt
            gait.set_velocity(vx=cmd_vx, omega=cmd_wz)
            q_des = np.asarray(gait.desired_deg(t)) * DEG2RAD
            act = q_rad_to_action(q_des)
            plan_stance = np.array([not s for s in gait.leg_swing_state()])
            sm = (float(gait._vx_smooth), float(gait._vy_smooth),
                  float(gait._om_smooth))
            obs, r, term, trunc, info = env.step(act)
            if step >= hold_n + ramp_n and info.get("goal_mode") == "walk":
                R = d.xmat[env._chassis_bid].reshape(3, 3)
                cx = d.xpos[env._chassis_bid]
                pads_b = (d.xpos[env._pad_bids] - cx) @ R
                rows.append({
                    "q_des": q_des.copy(),
                    "q_safe": env.safety._last_safe.copy(),
                    "q_act": env._state.joint_position.copy(),
                    "pads_xy": pads_b[:, :2].copy(),
                    "plan_stance": plan_stance,
                    "contact": np.array(
                        [float(d.sensordata[x]) > CONTACT_N
                         for x in env._touch_adr]),
                    "cmd_twist": (sm[0], sm[1], sm[2]),
                    "vx_body": float(env._body_vel_xy()[0]),
                    "wz_body": float(env._body_wz()),
                })
            step += 1
            if term:
                fell = True
            if term or trunc:
                break
    finally:
        env.close()

    dt = 0.01
    out = {"vx_cmd": vx_cmd, "wz_cmd": wz_cmd, "seed": seed,
           "phase_offset": phase_offset, "fell": fell,
           "n_scored_ticks": len(rows), "model_identity": identity,
           "edge_erode_ticks": EDGE_ERODE_TICKS}
    if len(rows) < 200:
        out["error"] = "insufficient scored ticks"
        return out
    out["body"] = {
        "wz_med": float(np.median([r["wz_body"] for r in rows])),
        "vx_med": float(np.median([r["vx_body"] for r in rows]))}

    plan_st = np.stack([r["plan_stance"] for r in rows])
    contact = np.stack([r["contact"] for r in rows])
    cmd_tw = np.asarray([r["cmd_twist"] for r in rows])
    sel_plan = np.stack([erode_segments(plan_st[:, f], EDGE_ERODE_TICKS)
                         for f in range(6)], axis=1)
    sel_cont = np.stack([erode_segments(contact[:, f], EDGE_ERODE_TICKS)
                         for f in range(6)], axis=1)
    pos = {"des": np.stack([fk_body_xy(r["q_des"]) for r in rows]),
           "safe": np.stack([fk_body_xy(r["q_safe"]) for r in rows]),
           "act": np.stack([fk_body_xy(r["q_act"]) for r in rows]),
           "pads": np.stack([r["pads_xy"] for r in rows])}
    stages = {}
    for name, p in pos.items():
        stages[name] = {
            "plan": analyze_stage(p, sel_plan, dt,
                                  cmd_twists=(cmd_tw if name == "des"
                                              else None)),
            "contact": analyze_stage(p, sel_cont, dt),
        }
    out["stages"] = stages
    segs = sweep_segments(pos["des"], pos["pads"], plan_st)
    ratios = [s["amp_ratio"] for s in segs if s["amp_ratio"] is not None]
    heads = [s["heading_err_deg"] for s in segs
             if s["heading_err_deg"] is not None]
    out["sweep"] = {
        "n_segments": len(segs),
        "amp_ratio_med": float(np.median(ratios)) if ratios else None,
        "heading_err_deg_med": float(np.median(heads)) if heads else None,
        "per_foot_amp_ratio_med": [
            (float(np.median([s["amp_ratio"] for s in segs
                              if s["foot"] == f
                              and s["amp_ratio"] is not None]))
             if any(s["foot"] == f and s["amp_ratio"] is not None
                    for s in segs) else None) for f in range(6)],
        "segments": segs,
    }
    out["duty_contact"] = np.mean(contact, axis=0).tolist()
    out["scuff_frac_planswing_in_contact"] = float(
        np.mean(contact[~plan_st])) if (~plan_st).any() else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg-json", type=Path, required=True)
    ap.add_argument("--cells", required=True, help="vx:wz list")
    ap.add_argument("--phase-offsets", default="0.0")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--parity-json", type=Path, default=None,
                    help="root_fullcone scripted audit JSON; body medians "
                         "must match bit-for-bit (behavior neutrality)")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    cfg_set = json.loads(args.cfg_json.read_text())
    cfg_set = [c for c in cfg_set if not c.startswith("env.model_source=")]
    cfg_set.append("env.model_source=mesh")
    cells = []
    for c in args.cells.split(","):
        vx, wz = c.split(":")
        cells.append((float(vx), float(wz)))
    offsets = [float(x) for x in args.phase_offsets.split(",")]

    # fail-closed kinematic feasibility (stock stance, all cells)
    from rl_move.sim.probe_turn_stancearm import feasibility_guard
    feas = feasibility_guard(*pta.WALK_PLANT, cells)
    print(json.dumps({"feasibility": feas}), flush=True)

    parity_ref = {}
    if args.parity_json is not None:
        ref = json.loads(args.parity_json.read_text())
        for r in ref["results"]:
            key = (round(r["vx_cmd"], 6), round(r["wz_cmd"], 6),
                   round(r.get("scripted_start_phase") or 0.0, 6))
            parity_ref[key] = (r["wz_med"], r["vx_med"])

    results = []
    parity_fail = 0
    for po in offsets:
        for vx, wz in cells:
            r = rollout(cfg_set=cfg_set, vx_cmd=vx, wz_cmd=wz,
                        seed=args.seed,
                        episode_seconds=args.episode_seconds,
                        phase_offset=po)
            key = (round(vx, 6), round(wz, 6), round(po, 6))
            if key in parity_ref and "body" in r:
                ref_wz, ref_vx = parity_ref[key]
                ok = (abs(r["body"]["wz_med"] - ref_wz) < 1e-9
                      and abs(r["body"]["vx_med"] - ref_vx) < 1e-9)
                r["parity"] = {"ref_wz_med": ref_wz, "ref_vx_med": ref_vx,
                               "ok": bool(ok)}
                if not ok:
                    parity_fail += 1
            results.append(r)
            print(json.dumps({"cell": [vx, wz], "start": po,
                              "fell": r.get("fell"),
                              "body": r.get("body"),
                              "des": (r.get("stages", {})
                                      .get("des", {}) or {}).get("plan"),
                              "pads": (r.get("stages", {})
                                       .get("pads", {}) or {}).get("plan"),
                              "parity": r.get("parity")}),
                  flush=True)

    verdict = support_verdict(results)
    out = {"schema": "probe_turn_twistfit/1", "label": args.label,
           "policy": "scripted", "seed": args.seed,
           "episode_seconds": args.episode_seconds,
           "cfg_set": cfg_set, "feasibility": feas,
           "pin": PIN, "bar": BAR,
           "parity_fail_cells": parity_fail,
           "support_verdict": verdict, "results": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({"support_verdict": verdict,
                      "parity_fail_cells": parity_fail}), flush=True)
    return 0 if parity_fail == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
