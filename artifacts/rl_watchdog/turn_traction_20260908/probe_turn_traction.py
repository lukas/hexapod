"""probe_turn_traction.py — DIRECT contact-force / traction-budget
diagnostic on the frozen full-mesh plant (todaypolicy steering,
2026-09-08, operator focus note 20260908T025454Z).

Plain English: three in-limits scripted-gait dials (lift-phase lead,
stance-posture yaw arm, cadence) each closed against the identical
both-signs-gain bar, and each closure INFERRED (but never measured)
that the leftover yaw deficit is a traction-limited conversion of the
executed foot sweep into body rotation.  That inference rested on
finite-difference pad speeds and LSQ twist residuals — indirect
evidence the pipeline review explicitly disclaimed as not proving a
unique traction limit.  This probe measures the actual quantity in
question for the first time: per-contact normal/tangential forces from
the constraint solver (``mj_contactForce``), friction-cone usage
|F_t|/(mu*N) per loaded pad, per-leg yaw moments about the body COM
(sign-resolved, world frame), torsional-friction contributions,
loaded-pad slip velocities, and actuator force-rail saturation — all
on the SAME pinned plant/cells/seed as the three closures.

The two competing mechanisms it must distinguish (focus note):
  A. FRICTION-CONE SATURATION — loaded pads slip while their tangential
     force sits near mu*N (cone usage ~1).  Then the budget itself is
     the wall and only levers that change the budget (normal-force
     redistribution, foot material/geometry contract changes) can help.
  B. OPPOSING-STANCE CANCELLATION — pads slip at LOW cone usage because
     simultaneous stance legs command mutually inconsistent foot paths
     (not a rigid twist), so internal forces fight each other and the
     net yaw moment is a small difference of large opposing terms.
     Then an in-limits gait/policy lever (arc-consistent stance paths,
     per-leg load shaping) is still on the table — distinct from the
     three closed dials.

Coordinate/sign validation is built in and fail-closed (focus note:
"validate coordinate/sign math"):
  1. STATIC CHECK — during the 1 s zero-command hold, the summed
     world-frame vertical contact force on the six feet must equal the
     pinned model weight (4.80573 kg * g) within 10%; the global force
     sign convention is CALIBRATED there (not assumed from geom order)
     and recorded.
  2. TOUCH CROSS-CHECK — per-pad solver normal-force sums must agree
     with the independent MuJoCo touch sensors (L{i}_foot_t) the whole
     eval stack already trusts.
  3. ANGULAR-MOMENTUM CHECK — d(L_z)/dt of the whole robot about its
     COM (mj_subtreeVel) is regressed against the net contact yaw
     moment (gravity has no z-moment about the COM, so contact is the
     only external z-torque): a sign error flips the slope.

Zero training, zero robot work, no shared-code changes.  Instrumenting
reads happen strictly AFTER env.step() (pure reads + mj_subtreeVel's
diagnostic-only fields), so the executed trajectory is bit-identical
to probe_turn_stancearm's baseline — asserted by test and by
reproducing the pinned baseline wz/vx medians.

Pre-registered decision rule (unchanged bar): only if the measured
mechanism nominates an in-limits lever DISTINCT from the closed
phase/posture/cadence dials does a trajectory-bank + single bounded 2M
existing-seed canary follow, and only after the unchanged
both-signs-gain / straight-health preflight passes; otherwise record
the concrete measured next experiment.  No universal class closure
either way.
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

import mujoco
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
    LOAD_N, PIN, _sha, feasibility_guard, pin_manifest)

from hexapod_core.tripod_gait import TripodGait  # noqa: E402

GRAV = 9.81
SLIP_MPS = 0.02        # loaded-pad XY speed that counts as "slipping"
                       # (~2x the baseline loaded-resid median 0.0108)
NEAR_CONE = 0.90       # |Ft|/(mu*N) above this = near-saturation
LOW_CONE = 0.50        # below this while slipping = NOT cone-limited
RAIL_FRAC = 0.95       # |actuator_force| >= 0.95*rail = saturated


def yaw_moment_z(r_xy: np.ndarray, f_xy: np.ndarray) -> float:
    """z-moment of planar force f applied at planar offset r from the
    reference point: tau_z = rx*Fy - ry*Fx (right-handed, world z up).
    Kept as a tiny named helper so the sign math is unit-testable."""
    return float(r_xy[0] * f_xy[1] - r_xy[1] * f_xy[0])


def foot_geom_ids(model) -> list[int]:
    gids = []
    for i in range(6):
        g = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, f"L{i}_foot")
        if g < 0:
            raise SystemExit(f"foot geom L{i}_foot not found")
        gids.append(g)
    return gids


def contact_snapshot(model, data, foot_gid_to_leg: dict, com: np.ndarray):
    """Per-leg contact wrench readout for the CURRENT data snapshot.

    Returns per-leg arrays (world frame, sign convention 'raw': the
    mj_contactForce result mapped to world and negated when the foot is
    geom1 so all legs share ONE global convention; the global up/down
    sign is calibrated later from the static hold):
      N[6]        summed normal-force magnitude (always >=0)
      f_w[6,3]    summed world contact force on the foot (raw sign)
      tau_z[6]    summed z-moment about `com` from the linear forces
      tors_z[6]   summed z-component of contact torques (torsion/roll)
      mu[6]       min slide friction coefficient among the pad's contacts
      ncon[6]     contact count with terrain
      other[6]    contact count with anything that is NOT the terrain
      frame_err   max |R R^T - I| over the pad contacts (orthonormality)
    """
    N = np.zeros(6)
    f_w = np.zeros((6, 3))
    tau_z = np.zeros(6)
    tors_z = np.zeros(6)
    mu = np.full(6, np.inf)
    ncon = np.zeros(6, dtype=int)
    other = np.zeros(6, dtype=int)
    frame_err = 0.0
    f6 = np.zeros(6)
    for ci in range(data.ncon):
        c = data.contact[ci]
        leg = s = None
        if c.geom1 in foot_gid_to_leg:
            leg, s = foot_gid_to_leg[c.geom1], -1.0
            partner = c.geom2
        elif c.geom2 in foot_gid_to_leg:
            leg, s = foot_gid_to_leg[c.geom2], 1.0
            partner = c.geom1
        else:
            continue
        pname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, partner)
        if pname != "terrain":
            other[leg] += 1
            continue
        mujoco.mj_contactForce(model, data, ci, f6)
        R = np.asarray(c.frame).reshape(3, 3)   # rows = axes in world
        frame_err = max(frame_err,
                        float(np.abs(R @ R.T - np.eye(3)).max()))
        fw = s * (R.T @ f6[:3])
        tw = s * (R.T @ f6[3:])
        N[leg] += float(abs(f6[0]))
        f_w[leg] += fw
        r = np.asarray(c.pos) - com
        tau_z[leg] += yaw_moment_z(r[:2], fw[:2])
        tors_z[leg] += float(tw[2])
        mu[leg] = min(mu[leg], float(c.friction[0]))
        ncon[leg] += 1
    mu[~np.isfinite(mu)] = 0.0
    return dict(N=N, f_w=f_w, tau_z=tau_z, tors_z=tors_z, mu=mu,
                ncon=ncon, other=other, frame_err=frame_err)


def _med(v):
    return float(np.median(v)) if len(v) else None


def rollout(*, policy: str, model, model_obs_width, cfg_set, vx_cmd, wz_cmd,
            seed, episode_seconds, phase_offset=0.0,
            plant: str = "twin", min_scored_ticks: int = 200) -> dict:
    env = pta.make_env(cfg_set, seed, episode_seconds)
    if model_obs_width is not None:
        n_env = int(env.observation_space.shape[0])
        if model_obs_width != n_env:
            raise SystemExit(f"obs width {model_obs_width} != env {n_env}")
    identity = model_identity(env)
    contract = motor_contract(env.cfg)
    want = "full_mesh" if plant == "fullmesh" else "mesh_mjx_twin"
    if identity["model_variant"] != want:
        raise RuntimeError(f"pin fail: variant {identity} != {want}")
    if plant == "fullmesh" and identity["model_nmesh"] != 34:
        raise RuntimeError(f"pin fail: nmesh {identity['model_nmesh']}")
    if abs(identity["model_mass_kg"] - PIN["model_mass_kg"]) > 1e-6 \
            and plant == "fullmesh":
        raise RuntimeError(f"pin fail: mass {identity['model_mass_kg']}")
    if abs(env.dt - 0.01) > 1e-12:
        raise RuntimeError(f"pin fail: dt {env.dt}")
    for k in ("bus.write_speed", "bus.write_acc", "safety.max_delta_q_deg",
              "slew_limit_deg_s", "resolved_vel_max_counts_s_max"):
        if abs(float(contract[k]) - PIN[k]) > 1e-9:
            raise RuntimeError(f"pin fail: contract {k}={contract[k]}")

    m, d = env.model, env.data
    fgids = foot_geom_ids(m)
    gid2leg = {g: i for i, g in enumerate(fgids)}
    root = int(m.body_rootid[env._chassis_bid])
    weight = float(np.sum(m.body_mass)) * GRAV
    rail = float(np.abs(m.actuator_forcerange).max(initial=0.0))
    if rail <= 0:
        raise RuntimeError("actuator forcerange rail not found")

    obs, info = env.reset()
    if policy == "checkpoint" and hasattr(model, "reset"):
        model.reset()
    if phase_offset:
        env._phase = float(phase_offset) % (2 * math.pi)

    traj = env._goal_traj
    n = len(traj.vx)
    hold_n = ramp_n = int(round(1.0 / env.dt))
    traj.vx[:] = vx_cmd; traj.vy[:] = 0.0; traj.wz[:] = wz_cmd
    traj.vx[:hold_n] = 0.0; traj.wz[:hold_n] = 0.0
    traj.vx[hold_n:hold_n + ramp_n] = np.linspace(0.0, vx_cmd, ramp_n)
    traj.wz[hold_n:hold_n + ramp_n] = np.linspace(0.0, wz_cmd, ramp_n)

    gait = None
    st_hip, st_knee = pta.WALK_PLANT
    if policy == "scripted":
        gait = TripodGait(vx=0.0)
        gait.sync_plant_stance(st_hip, st_knee)
        gait.reset_phase(phase=phase_offset)

    static_rows, rows = [], []
    step = 0
    fell = False
    while True:
        cmd_wz = float(traj.wz[min(step, n - 1)])
        cmd_vx = float(traj.vx[min(step, n - 1)])
        if policy == "scripted":
            t = step * env.dt
            gait.set_velocity(vx=cmd_vx, omega=cmd_wz)
            q_des = np.asarray(gait.desired_deg(t)) * DEG2RAD
            act = q_rad_to_action(q_des)
            plan_swing = np.array(gait.leg_swing_state())
        else:
            act, _ = model.predict(obs, deterministic=True)
            plan_swing = None
        obs, r, term, trunc, info = env.step(act)
        com = d.subtree_com[root].copy()
        in_hold_tail = hold_n // 2 <= step < hold_n
        scored = (step >= hold_n + ramp_n
                  and info.get("goal_mode") == "walk")
        if in_hold_tail or scored:
            snap = contact_snapshot(m, d, gid2leg, com)
            snap["touch"] = np.array(
                [float(d.sensordata[x]) for x in env._touch_adr])
            if in_hold_tail:
                static_rows.append(snap)
            else:
                mujoco.mj_subtreeVel(m, d)
                snap["angmom_z"] = float(d.subtree_angmom[root][2])
                snap["pads_w"] = np.array(
                    [d.xpos[b] for b in env._pad_bids])
                snap["plan_swing"] = plan_swing
                snap["act_sat"] = np.abs(d.actuator_force.copy()) / rail
                snap["vx_body"] = float(env._body_vel_xy()[0])
                snap["wz_body"] = float(env._body_wz())
                rows.append(snap)
        step += 1
        if term:
            fell = True
        if term or trunc:
            break
    env.close()

    dt = 0.01
    out = {"policy": policy, "vx_cmd": vx_cmd, "wz_cmd": wz_cmd,
           "seed": seed, "phase_offset": phase_offset, "fell": fell,
           "n_scored_ticks": len(rows), "n_static_ticks": len(static_rows),
           "model_identity": identity, "weight_n": weight,
           "actuator_rail_nm": rail,
           "motor_contract": {k: contract[k] for k in
                              ("bus.write_speed", "bus.write_acc",
                               "safety.max_delta_q_deg", "slew_limit_deg_s",
                               "resolved_vel_max_counts_s_max",
                               "control.hz")}}
    if len(static_rows) < 20:
        out["error"] = "insufficient static ticks"
        return out
    if len(rows) < min_scored_ticks:
        out["error"] = "insufficient scored ticks"
        return out

    # ---- 1) SIGN CALIBRATION + STATIC VALIDATION (fail closed) ----
    fz_raw = np.array([s["f_w"][:, 2].sum() for s in static_rows])
    sign = 1.0 if fz_raw.mean() > 0 else -1.0
    fz = sign * fz_raw
    sum_over_w = float(fz.mean() / weight)
    if not (0.90 <= sum_over_w <= 1.10):
        raise RuntimeError(
            f"STATIC CHECK FAIL: mean vertical contact force / weight = "
            f"{sum_over_w:.4f} (sign={sign:+.0f}) — coordinate/sign math "
            f"is wrong or the robot is not standing during the hold")
    stat_N = np.stack([s["N"] for s in static_rows])
    stat_touch = np.stack([s["touch"] for s in static_rows])
    m_ld = stat_N > LOAD_N
    rel = np.abs(stat_N[m_ld] - stat_touch[m_ld]) / stat_N[m_ld]
    ft_static = np.stack(
        [np.linalg.norm(s["f_w"][:, :2], axis=1) for s in static_rows])
    out["static_check"] = {
        "sign_convention": sign,
        "sum_normal_over_weight": sum_over_w,
        "touch_vs_contactN_med_relerr": _med(rel),
        "tangential_over_normal_med": float(
            np.median(ft_static[m_ld] / stat_N[m_ld])),
        "frame_orthonormality_max_err": float(
            max(s["frame_err"] for s in static_rows)),
        "static_mu_min": float(min(s["mu"][s["N"] > LOAD_N].min()
                                   for s in static_rows
                                   if (s["N"] > LOAD_N).any())),
    }
    if out["static_check"]["touch_vs_contactN_med_relerr"] is not None and \
            out["static_check"]["touch_vs_contactN_med_relerr"] > 0.15:
        raise RuntimeError("STATIC CHECK FAIL: solver normal forces "
                           "disagree with touch sensors "
                           f"({out['static_check']})")

    # ---- 2) scored-window arrays (all forces now sign-corrected) ----
    N = np.stack([s["N"] for s in rows])                      # (T,6)
    f_w = sign * np.stack([s["f_w"] for s in rows])           # (T,6,3)
    tau_z = sign * np.stack([s["tau_z"] for s in rows])       # (T,6)
    tors_z = sign * np.stack([s["tors_z"] for s in rows])     # (T,6)
    mu = np.stack([s["mu"] for s in rows])
    pads_w = np.stack([s["pads_w"] for s in rows])
    angmom = np.array([s["angmom_z"] for s in rows])
    act_sat = np.stack([s["act_sat"] for s in rows])          # (T,18)
    touch = np.stack([s["touch"] for s in rows])
    other = np.stack([s["other"] for s in rows])

    out["body"] = {"vx_med": _med([s["vx_body"] for s in rows]),
                   "wz_med": _med([s["wz_body"] for s in rows])}
    out["foot_nonterrain_contact_ticks"] = int((other > 0).any(axis=1).sum())

    loaded = N > LOAD_N
    ft = np.linalg.norm(f_w[:, :, :2], axis=2)
    with np.errstate(divide="ignore", invalid="ignore"):
        usage = np.where(loaded & (mu > 0), ft / (mu * N), np.nan)
    v_w = np.full((len(rows), 6), np.nan)
    v_w[1:] = np.linalg.norm(np.diff(pads_w[:, :, :2], axis=0), axis=2) / dt
    loaded2 = loaded.copy(); loaded2[1:] &= loaded[:-1]
    slip = loaded2 & (v_w > SLIP_MPS)

    # touch cross-check during the dynamic window too
    m_ld = loaded & (N > LOAD_N)
    rel_dyn = np.abs(N[m_ld] - touch[m_ld]) / N[m_ld]
    out["touch_vs_contactN_med_relerr_dynamic"] = _med(rel_dyn)

    per = {}
    for f in range(6):
        u = usage[loaded[:, f], f]
        u = u[np.isfinite(u)]
        us = usage[slip[:, f], f]; us = us[np.isfinite(us)]
        per[f] = {
            "loaded_ticks": int(loaded[:, f].sum()),
            "normal_med_n": _med(N[loaded[:, f], f]),
            "mu_med": _med(mu[loaded[:, f], f]),
            "cone_usage_med": _med(u),
            "cone_usage_p90": (float(np.percentile(u, 90))
                               if len(u) else None),
            "frac_loaded_near_cone": (float(np.mean(u > NEAR_CONE))
                                      if len(u) else None),
            "slip_ticks": int(slip[:, f].sum()),
            "slip_speed_med_mps": _med(v_w[slip[:, f], f]),
            "cone_usage_med_on_slip": _med(us),
            "frac_slip_near_cone": (float(np.mean(us > NEAR_CONE))
                                    if len(us) else None),
            "frac_slip_low_cone": (float(np.mean(us < LOW_CONE))
                                   if len(us) else None),
            "tau_z_med_loaded_nm": _med(tau_z[loaded[:, f], f]),
            "tors_z_med_loaded_nm": _med(tors_z[loaded[:, f], f]),
        }
    out["per_leg"] = per

    # ---- 3) yaw-moment budget / cancellation decomposition ----
    tau_all = tau_z + tors_z
    pos = np.where(tau_all > 0, tau_all, 0.0).sum(axis=1)
    neg = np.where(tau_all < 0, tau_all, 0.0).sum(axis=1)
    net = tau_all.sum(axis=1)
    gross = pos - neg
    with np.errstate(divide="ignore", invalid="ignore"):
        cancel = np.where(gross > 1e-9, np.abs(net) / gross, np.nan)
    out["yaw_budget"] = {
        "net_tau_z_med_nm": _med(net),
        "pos_sum_med_nm": _med(pos),
        "neg_sum_med_nm": _med(-neg),
        "net_over_gross_med": _med(cancel[np.isfinite(cancel)]),
        "tors_share_of_net_med": _med(
            np.abs(tors_z.sum(axis=1)) /
            np.maximum(np.abs(net), 1e-9)),
    }

    # ---- 4) angular-momentum cross-validation (sign check #3) ----
    dl = np.diff(angmom) / dt
    tz = net[:-1]
    if np.std(tz) > 1e-9 and np.std(dl) > 1e-9:
        corr = float(np.corrcoef(tz, dl)[0, 1])
        slope = float(np.polyfit(tz, dl, 1)[0])
    else:
        corr = slope = None
    out["angmom_check"] = {"corr_net_tau_vs_dLdt": corr,
                           "slope_dLdt_per_tau": slope}

    # ---- 5) actuator rail saturation, stance legs, per axis ----
    stance_any = loaded  # contact-based stance
    sat = {}
    for ax, nm in ((0, "yaw"), (1, "hip"), (2, "knee")):
        vals = []
        for f in range(6):
            sel = stance_any[:, f]
            if sel.any():
                vals.append(act_sat[sel, 3 * f + ax])
        v = np.concatenate(vals) if vals else np.array([])
        sat[nm] = {"sat_med": _med(v),
                   "frac_at_rail": (float(np.mean(v >= RAIL_FRAC))
                                    if len(v) else None)}
    out["actuator_saturation_stance"] = sat
    return out


def preflight_pins(cfg_set, plant: str) -> dict:
    """Hard-assert the plant identity + motor contract once (the audit
    engine's rollout builds its env internally; identity is a pure
    function of cfg_set so a preflight env is equivalent)."""
    env = pta.make_env(cfg_set, 0, 2.0)
    try:
        identity = model_identity(env)
        contract = motor_contract(env.cfg)
        want = "full_mesh" if plant == "fullmesh" else "mesh_mjx_twin"
        if identity["model_variant"] != want:
            raise SystemExit(f"pin fail: variant {identity} != {want}")
        if plant == "fullmesh":
            if identity["model_nmesh"] != 34:
                raise SystemExit(f"pin fail: nmesh {identity['model_nmesh']}")
            if abs(identity["model_mass_kg"] - PIN["model_mass_kg"]) > 1e-6:
                raise SystemExit(f"pin fail: mass {identity['model_mass_kg']}")
        if abs(env.dt - 0.01) > 1e-12:
            raise SystemExit(f"pin fail: dt {env.dt}")
        for k in ("bus.write_speed", "bus.write_acc",
                  "safety.max_delta_q_deg", "slew_limit_deg_s",
                  "resolved_vel_max_counts_s_max"):
            if abs(float(contract[k]) - PIN[k]) > 1e-9:
                raise SystemExit(f"pin fail: contract {k}={contract[k]}")
        return identity
    finally:
        env.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", choices=("scripted", "checkpoint"),
                    required=True)
    ap.add_argument("--checkpoint", type=Path, default=None)
    ap.add_argument("--cfg-json", type=Path, required=True)
    ap.add_argument("--cells", required=True, help="vx:wz,...")
    ap.add_argument("--phase-offsets", default="0.0")
    ap.add_argument("--plant", choices=("twin", "fullmesh"), default="twin")
    ap.add_argument("--engine", choices=("tick", "audit"), default="tick",
                    help="tick: this module's per-control-tick sampler "
                         "with static-hold weight/touch sign validation; "
                         "audit: probe_turn_authority._ContactAudit "
                         "per-substep wrench integration with the "
                         "impulse-closure validity gate (the traction "
                         "extension adds cone-usage/cancellation/rail "
                         "fields to it)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--foot-torsion-mu", type=float, default=None,
                    help="DIAGNOSTIC-ONLY sensitivity dose: override the "
                         "foot+terrain geoms' TORSIONAL friction "
                         "coefficient (meters; MuJoCo pairs combine by "
                         "elementwise max, so both sides are set). The "
                         "pinned plant ships mu_t=0.1 m, ~20x a physical "
                         "estimate for the 9 mm boot ((2/3)*a*mu_slide "
                         "~= 0.005 m); this flag measures how much of "
                         "the yaw budget rides on that phantom torsion. "
                         "Applied post-construction to the probe env "
                         "models only — no shared default changes, no "
                         "training, nothing deployed.")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    if args.foot_torsion_mu is not None:
        _orig_make_env = pta.make_env

        def _dosed_make_env(cfg_set_, seed_, episode_seconds_,
                            mode_onehot=False):
            env = _orig_make_env(cfg_set_, seed_, episode_seconds_,
                                 mode_onehot=mode_onehot)
            gf = env.model.geom_friction
            for g in foot_geom_ids(env.model):
                gf[g, 1] = args.foot_torsion_mu
            tg = mujoco.mj_name2id(env.model, mujoco.mjtObj.mjOBJ_GEOM,
                                   "terrain")
            if tg >= 0:
                gf[tg, 1] = min(gf[tg, 1], args.foot_torsion_mu)
            return env

        pta.make_env = _dosed_make_env

    pins = pin_manifest(args.plant)
    cfg_set = json.loads(args.cfg_json.read_text())
    cfg_set = [c for c in cfg_set if not c.startswith("env.model_source=")]
    cfg_set.append("env.model_source="
                   + ("mesh" if args.plant == "fullmesh" else "mesh_mjx"))

    model = width = None
    ckpt_sha = None
    if args.policy == "checkpoint":
        ckpt_sha = _sha(args.checkpoint)
        if ckpt_sha != PIN["cont8m_ckpt_sha256"]:
            raise SystemExit(f"PIN FAIL checkpoint sha {ckpt_sha}")
        model, width = pta._load_model(args.checkpoint)

    cells = [tuple(float(x) for x in c.split(":"))
             for c in args.cells.split(",")]
    st_hip, st_knee = pta.WALK_PLANT
    feas = feasibility_guard(st_hip, st_knee, cells)
    print(json.dumps({"feasibility": feas}), flush=True)

    identity = preflight_pins(cfg_set, args.plant)
    print(json.dumps({"preflight_identity": identity}), flush=True)

    results = []
    for vx, wz in cells:
        for po in (float(x) for x in args.phase_offsets.split(",")):
            if args.engine == "audit":
                r = pta.rollout(model=model, model_obs_width=width,
                                env_cls_kwargs={"cfg_set": cfg_set},
                                wz_cmd=wz, vx_cmd=vx, seed=args.seed,
                                episode_seconds=args.episode_seconds,
                                policy=args.policy, contact_audit=True,
                                phase_offset=po)
                brief = {"cell": [vx, wz], "start": po, "fell": r["fell"],
                         "body": {"vx_med": r["vx_med"],
                                  "wz_med": r["wz_med"]},
                         "angmom": r["contact_audit"]["angmom_check"],
                         "yaw_budget": r["contact_audit"]
                         .get("traction", {}).get("yaw_budget"),
                         "label": args.label}
            else:
                r = rollout(policy=args.policy, model=model,
                            model_obs_width=width, cfg_set=cfg_set,
                            vx_cmd=vx, wz_cmd=wz, seed=args.seed,
                            episode_seconds=args.episode_seconds,
                            phase_offset=po, plant=args.plant)
                brief = {"cell": [vx, wz], "start": po, "fell": r["fell"],
                         "body": r.get("body"),
                         "static": r.get("static_check"),
                         "yaw_budget": r.get("yaw_budget"),
                         "label": args.label}
            r["cell"] = [vx, wz]
            results.append(r)
            print(json.dumps(brief), flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(
        {"schema": "hexapod.turn_traction_probe.v1", "label": args.label,
         "engine": args.engine, "foot_torsion_mu": args.foot_torsion_mu,
         "policy": args.policy, "feasibility": feas, "plant": args.plant,
         "checkpoint": str(args.checkpoint) if args.checkpoint else None,
         "checkpoint_sha256": ckpt_sha, "pin_manifest": pins,
         "pin_expect": PIN, "cfg_set": cfg_set, "seed": args.seed,
         "episode_seconds": args.episode_seconds,
         "thresholds": {"SLIP_MPS": SLIP_MPS, "NEAR_CONE": NEAR_CONE,
                        "LOW_CONE": LOW_CONE, "LOAD_N": LOAD_N,
                        "RAIL_FRAC": RAIL_FRAC},
         "results": results}, indent=1, default=str) + "\n")
    print("COMPLETE", args.out, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
