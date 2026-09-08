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

HISTORICAL S1/S2/S3 BAR (retained descriptively, written before the first rollout): a
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
S1/S2 can also detect a COMMON wrong rigid twist; S3 can reflect feet
sampling different phases of a shared time-varying twist. None establishes
mutually incompatible foot paths. The review-added consistency check uses
the best-fit residual, separately from this unchanged historical bar.
Stage differences alone do not identify a cause or demote friction-cone
engagement: nominal FK and true mesh geometry differ, and contact selection
is from the last physics solve while positions are endpoint samples.

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
# Review-added diagnostic threshold, NOT a rewrite of the historical BAR.
PATH_RESID_NORM = 0.10
EXPECTED_KEYS = {(0.08, wz, round(phase, 6))
                 for wz in (-0.15, 0.0, 0.15) for phase in (0.0, math.pi)}


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


def _cell_key(c: dict, *, reference: bool = False):
    phase = (c.get("scripted_start_phase", c.get("phase_offset"))
             if reference else c.get("phase_offset"))
    return (round(float(c["vx_cmd"]), 6), round(float(c["wz_cmd"]), 6),
            round(float(phase) % (2 * math.pi), 6))


def _nonfinite(value) -> bool:
    if isinstance(value, dict):
        return any(_nonfinite(v) for v in value.values())
    if isinstance(value, (list, tuple, np.ndarray)):
        return any(_nonfinite(v) for v in value)
    return isinstance(value, (float, np.floating)) and not math.isfinite(value)


def _finite_number(value) -> bool:
    return (isinstance(value, (int, float, np.number))
            and not isinstance(value, (bool, np.bool_))
            and math.isfinite(float(value)))


def _feasibility_reasons(feasibility) -> list[str]:
    if not isinstance(feasibility, dict):
        return ["missing feasibility evidence"]
    reasons = []
    if (_nonfinite(feasibility) or feasibility.get("raw_ik_calls", 0) <= 0
            or feasibility.get("raw_ik_failures") != 0):
        reasons.append("invalid feasibility / raw IK evidence")
    margins = feasibility.get("joint_margins", {})
    for axis in ("yaw", "hip", "knee"):
        margin = margins.get(axis, {}).get("margin_deg")
        if not _finite_number(margin) or margin < 2.0:
            reasons.append(f"feasibility {axis} margin missing or below 2 degrees")
    return reasons


def validate_matrix(cells: list[dict], *, parity_required: bool = True,
                    feasibility=None) -> dict:
    """Fail closed for the fixed six-cell original-target diagnostic."""
    reasons = _feasibility_reasons(feasibility)
    keys = []
    for i, c in enumerate(cells):
        try:
            key = _cell_key(c)
            keys.append(key)
        except (KeyError, TypeError, ValueError):
            reasons.append(f"cell {i}: missing or invalid identity")
        if _nonfinite(c):
            reasons.append(f"cell {i}: nonfinite data")
        if c.get("fell") is not False:
            reasons.append(f"cell {i}: fall/termination status missing or failed")
        if c.get("error") or c.get("n_scored_ticks", 0) < 200:
            reasons.append(f"cell {i}: insufficient scored ticks")
        body = c.get("body", {})
        if not all(_finite_number(body.get(k)) for k in ("vx_med", "wz_med")):
            reasons.append(f"cell {i}: missing finite body measurements")
        des = c.get("stages", {}).get("des", {}).get("plan") or {}
        required = ("wz_med", "resid_norm", "cmd_exact_resid_norm",
                    "implied_wz_spread")
        if (des.get("n_fits", 0) <= 0
                or not all(_finite_number(des.get(k)) for k in required)):
            reasons.append(f"cell {i}: missing finite des-stage fits")
        if parity_required and c.get("parity", {}).get("ok") is not True:
            reasons.append(f"cell {i}: missing or failed parity")
    if len(keys) != len(set(keys)):
        reasons.append("duplicate matrix cells")
    if len(cells) != 6 or set(keys) != EXPECTED_KEYS:
        reasons.append("expected exactly four unique arc and two straight cells")
    return {"valid": not reasons, "reasons": reasons}


def support_verdict(cells: list[dict], *, validation=None) -> dict:
    """Preserve historical diagnostics; support requires valid evidence AND
    incompatible paths, rather than merely a common wrong rigid twist."""
    checks = []
    for c in cells:
        if not _finite_number(c.get("wz_cmd")) or abs(c["wz_cmd"]) <= 1e-9:
            continue
        des = (c.get("stages", {}).get("des", {}) or {}).get("plan") or {}
        required = ("wz_med", "cmd_exact_resid_norm", "implied_wz_spread",
                    "resid_norm")
        if not all(_finite_number(des.get(k)) for k in required):
            checks.append({"cell": [c.get("vx_cmd"), c["wz_cmd"]],
                           "start": c.get("phase_offset"), "breach": None,
                           "path_inconsistent": None,
                           "reason": "no finite des-stage fits"})
            continue
        gain = des["wz_med"] / c["wz_cmd"]
        s1 = not (BAR["wz_gain_lo"] <= gain <= BAR["wz_gain_hi"])
        s2 = des["cmd_exact_resid_norm"] > BAR["cmd_resid_norm"]
        spread = des["implied_wz_spread"]
        s3 = spread > BAR["implied_wz_spread_frac"] * abs(c["wz_cmd"])
        checks.append({"cell": [c["vx_cmd"], c["wz_cmd"]],
                       "start": c["phase_offset"], "des_wz_gain": gain,
                       "cmd_exact_resid_norm": des["cmd_exact_resid_norm"],
                       "implied_wz_spread": spread,
                       "S1": s1, "S2": s2, "S3": s3,
                       "breach": bool(s1 or s2 or s3),
                       "best_fit_resid_norm": des["resid_norm"],
                       "path_inconsistent": des["resid_norm"] > PATH_RESID_NORM})
    legacy = len(checks) == 4 and all(c["breach"] is True for c in checks)
    inconsistent = (len(checks) == 4
                    and all(c["path_inconsistent"] is True for c in checks))
    valid = validation is not None and validation.get("valid") is True
    return {"bar": BAR, "checks": checks, "legacy_bar_supported": legacy,
            "path_inconsistency_threshold": PATH_RESID_NORM,
            "path_inconsistency_rule": "review-added best-fit residual; historical S1/S2/S3 unchanged",
            "supported": bool(valid and inconsistent and legacy),
            "validation_passed": valid,
            "interpretation": ("Command consistency is a kinematic diagnostic, not a causal "
                               "friction or execution localization test. A common wrong "
                               "rigid twist is distinct from incompatible foot paths.")}


class _EndpointKinematics:
    """Read endpoint transforms on private MjData without touching live state.

    Live contact sensors remain the last solved substep at endpoint time-h.
    They select a solve-time contact population, not endpoint contacts.
    """
    def __init__(self, env):
        self.env = env
        self.mj = env._mujoco
        self.scratch = self.mj.MjData(env.model)

    def sample(self) -> dict:
        e, s = self.env, self.scratch
        d = e.data
        s.qpos[:] = d.qpos
        s.mocap_pos[:] = d.mocap_pos
        s.mocap_quat[:] = d.mocap_quat
        self.mj.mj_kinematics(e.model, s)
        R = s.xmat[e._chassis_bid].reshape(3, 3)
        pads = (s.xpos[e._pad_bids] - s.xpos[e._chassis_bid]) @ R
        return {"q_act": e._state.joint_position.copy(),
                "pads_xy": pads[:, :2].copy(),
                "contact": np.asarray([a >= 0 and float(d.sensordata[a]) > CONTACT_N
                                        for a in e._touch_adr]),
                "endpoint_time_s": float(d.time),
                "contact_solve_time_s": float(d.time - e.model.opt.timestep)}


# ---------------------------------------------------------------- rollout
def _assert_frozen_env(env) -> dict:
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

    return identity


def rollout(*, cfg_set, vx_cmd, wz_cmd, seed, episode_seconds,
            phase_offset=0.0) -> dict:
    env = pta.make_env(cfg_set, seed, episode_seconds)
    identity = _assert_frozen_env(env)

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

    endpoint = _EndpointKinematics(env)
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
                sample = endpoint.sample()
                rows.append({
                    **sample,
                    "q_des": q_des.copy(),
                    "q_safe": env.safety._last_safe.copy(),
                    "plan_stance": plan_stance,
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
           "edge_erode_ticks": EDGE_ERODE_TICKS,
           "sampling": {
               "control_dt_s": float(env.dt),
               "physics_dt_s": float(env.model.opt.timestep),
               "joint_and_pad_positions": "post-step endpoint; pad transforms from private kinematics",
               "contact": "last solved physics substep at endpoint minus physics_dt_s; touch > CONTACT_N",
               "contact_threshold_N": CONTACT_N,
               "command_phase": "phase used to command the completed control interval",
               "geometry": "des/safe/act use nominal FK; pads use true mesh body origins"}}
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
    plan_contact = plan_st & contact
    sel_plan_contact = np.stack([
        erode_segments(plan_contact[:, f], EDGE_ERODE_TICKS)
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
            "plan_contact": analyze_stage(p, sel_plan_contact, dt),
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
    out["duty_plan_contact"] = np.mean(plan_contact, axis=0).tolist()
    out["scuff_frac_planswing_in_contact"] = float(
        np.mean(contact[~plan_st])) if (~plan_st).any() else None
    return out


def _json_safe(value):
    """Invalid numbers are rejected before serialization; write strict JSON."""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (float, np.floating)) and not math.isfinite(value):
        return None
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg-json", type=Path, required=True)
    ap.add_argument("--cells", required=True, help="vx:wz list")
    ap.add_argument("--phase-offsets", default="0.0")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--parity-json", type=Path, default=None,
                    help="required for valid support: complete six-cell scripted reference")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg_set = json.loads(args.cfg_json.read_text())
    cfg_set = [c for c in cfg_set if not c.startswith("env.model_source=")]
    cfg_set.append("env.model_source=mesh")
    cells = [tuple(map(float, c.split(":"))) for c in args.cells.split(",")]
    offsets = [float(x) for x in args.phase_offsets.split(",")]
    errors, results = [], []
    requested = [{"vx_cmd": vx, "wz_cmd": wz, "phase_offset": po}
                 for po in offsets for vx, wz in cells]
    try:
        keys = [_cell_key(c) for c in requested]
        if len(keys) != 6 or len(set(keys)) != 6 or set(keys) != EXPECTED_KEYS:
            errors.append("expected exactly four unique arc and two straight cells")
    except (TypeError, ValueError):
        errors.append("invalid/nonfinite requested matrix identity")
    if not math.isfinite(args.episode_seconds) or args.episode_seconds <= 2.0:
        errors.append("invalid episode duration")
    from rl_move.sim.probe_turn_stancearm import feasibility_guard
    feas = None
    if not errors:
        try:
            feas = feasibility_guard(*pta.WALK_PLANT, cells)
            errors.extend(_feasibility_reasons(feas))
        except (SystemExit, RuntimeError, ValueError) as exc:
            errors.append(f"feasibility failed: {exc}")
    parity_ref = {}
    if args.parity_json is None:
        errors.append("missing parity reference")
    else:
        try:
            ref = json.loads(args.parity_json.read_text())
            if _nonfinite(ref):
                errors.append("nonfinite parity reference")
            if ref.get("policy") != "scripted":
                errors.append("parity policy mismatch")
            for field, expected in (("seed", args.seed),
                                    ("episode_seconds", args.episode_seconds)):
                if field in ref and ref[field] != expected:
                    errors.append(f"parity {field} mismatch")
            if "cfg_set" in ref:
                def config_map(items):
                    return {k: v for item in items for k, v in [item.split("=", 1)]
                            if k != "env.model_source"}
                if config_map(ref["cfg_set"]) != config_map(cfg_set):
                    errors.append("parity configuration mismatch")
            for row in ref["results"]:
                key = _cell_key(row, reference=True)
                if key in parity_ref:
                    errors.append("duplicate parity reference cell")
                parity_ref[key] = row
                if row.get("seed") != args.seed:
                    errors.append("parity row seed mismatch")
            if set(parity_ref) != EXPECTED_KEYS or len(ref["results"]) != 6:
                errors.append("missing or unexpected parity reference cells")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(f"invalid parity reference: {exc}")
    if not errors:
        for po in offsets:
            for vx, wz in cells:
                r = rollout(cfg_set=cfg_set, vx_cmd=vx, wz_cmd=wz,
                            seed=args.seed, episode_seconds=args.episode_seconds,
                            phase_offset=po)
                ref = parity_ref[_cell_key(r)]
                body = r.get("body", {})
                values = [body.get("wz_med"), body.get("vx_med"),
                          ref.get("wz_med"), ref.get("vx_med")]
                ok = (all(_finite_number(v) for v in values)
                      and values[0] == values[2] and values[1] == values[3]
                      and r.get("fell") is False and ref.get("fell") is False
                      and _finite_number(r.get("n_scored_ticks"))
                      and r.get("n_scored_ticks") == ref.get("n_walk_ticks"))
                r["parity"] = {"ok": bool(ok), "ref_wz_med": ref.get("wz_med"),
                               "ref_vx_med": ref.get("vx_med"),
                               "scope": "exact body medians, scored count and fall status; not full trace parity"}
                results.append(r)
                print(json.dumps(_json_safe({"cell": [vx, wz], "start": po,
                    "body": body, "parity": r["parity"]}), allow_nan=False), flush=True)
    validation = validate_matrix(results, feasibility=feas)
    validation["reasons"] = errors + validation["reasons"]
    validation["valid"] = not validation["reasons"]
    verdict = support_verdict(results, validation=validation)
    out = {"schema": "probe_turn_twistfit/2", "label": args.label,
           "policy": "scripted", "seed": args.seed,
           "episode_seconds": args.episode_seconds, "cfg_set": cfg_set,
           "feasibility": feas, "pin": PIN, "bar": BAR,
           "validation": validation,
           "parity_fail_cells": sum(r.get("parity", {}).get("ok") is not True
                                    for r in results),
           "support_verdict": verdict, "results": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(_json_safe(out), indent=1, default=float,
                                  allow_nan=False))
    print(json.dumps({"support_verdict": verdict, "validation": validation}), flush=True)
    return 0 if validation["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
