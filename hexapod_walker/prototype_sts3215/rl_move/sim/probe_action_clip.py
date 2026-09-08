"""Offline action-clipping / controllability probe (walkcurr, 2026-09-08).

QUESTION (operator focus note 2026-09-08): the scratch walk champion
lineage drives absolute joint targets through a per-tick SafetyLayer
slew clip (safety.max_delta_q_deg, 3.6 deg @ 100 Hz) and its gate
telemetry shows slew_sat_frac ~0.87 (ANY-joint definition). Do small
actor corrections DISAPPEAR in the absolute-target -> safety-clip
stage, i.e. is local foot-motion controllability lost to one-sided
slew saturation? This probe measures target sensitivity and a nominal
kinematic support proxy; it does not measure dynamic foot response.

INPUTS: per-tick rollout traces (.npz) written by
``eval_checkpoint --rollout-trace-out ... --rollout-trace-index -1``
with the env's ``debug_pipeline_record`` hook active, so every tick
carries: policy action, applied (post-noise) action, proposed joint
target (decoder output, pre-safety), the SafetyLayer's pre-filter
last-safe vector, the post-safety commanded target, measured qpos and
foot contacts.

WHAT IT DOES (all on COPIED state, zero live-env mutation):
1. Parity: re-derives proposed targets from applied actions through a
   pure decoder replica, and commanded targets from (last_safe,
   proposed) through a pure SafetyLayer slew+limit replica; both must
   match the recorded stream tick-for-tick or the probe aborts.
2. Saturation census: per (tick, joint) raw delta vs the slew cap;
   per-axis-class and stance/swing splits; action-bound pinning.
3. Empirical perturbation: at sampled ticks, perturbs each of the 18
   applied-action dims by +/-budget on the copied decoder/safety
   state and measures whether the safe target moves at all
   (transmission) and by how much.
4. Foot-space directions: per leg, maps the per-joint transmitted
   intervals through the leg's foot Jacobian (nominal mesh-twin FK;
   per-episode link DR is ignored) and compares achievable
   displacement along sampled unit directions against an ideal
   unsaturated channel of the same budget -> "lost" (ratio<0.2) /
   "kept" (ratio>0.8) support fractions, stance vs swing. These are
   projection maxima, not independently reachable displacement vectors;
   motor dynamics, loaded contacts and transition timing are untested.

Pure diagnostic: no training, no shared-behavior change.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from hexapod_core.joint_frame import (
    mujoco_rel_rad_to_robot_abs_rad, robot_abs_rad_to_mujoco_rel_rad)

DEG2RAD = math.pi / 180.0
AXIS_LIMITS_DEG = {0: (-35.0, 35.0), 1: (-80.0, 40.0), 2: (-20.0, 150.0)}
N_JOINTS = 18
_CENTER = np.array([(AXIS_LIMITS_DEG[j % 3][0] + AXIS_LIMITS_DEG[j % 3][1])
                    * 0.5 * DEG2RAD for j in range(N_JOINTS)])
_HALF = np.array([(AXIS_LIMITS_DEG[j % 3][1] - AXIS_LIMITS_DEG[j % 3][0])
                  * 0.5 * DEG2RAD for j in range(N_JOINTS)])
_JLO = np.array([AXIS_LIMITS_DEG[j % 3][0] * DEG2RAD for j in range(N_JOINTS)])
_JHI = np.array([AXIS_LIMITS_DEG[j % 3][1] * DEG2RAD for j in range(N_JOINTS)])
AXIS_NAMES = ("yaw", "hip", "knee")


class Decoder:
    """Pure replica of joint_task._act_to_q with the action box active."""

    def __init__(self, bias_deg, box_deg):
        bias = np.array([bias_deg[j % 3] for j in range(N_JOINTS)]) * DEG2RAD
        bias_a = np.clip(bias / _HALF, -1.0, 1.0)
        self.center = _CENTER + bias_a * _HALF          # action_to_q_rad(bias)
        self.box = np.array([box_deg[j % 3] for j in range(N_JOINTS)]) * DEG2RAD

    def __call__(self, a):
        return np.clip(self.center + np.asarray(a, dtype=float) * self.box,
                       _JLO, _JHI)


def safe_filter(last, prop, max_dq):
    """Pure replica of SafetyLayer.filter's slew + joint-limit clip."""
    dq = np.clip(np.asarray(prop) - last, -max_dq, max_dq)
    return np.clip(last + dq, _JLO, _JHI)


class LegJac:
    """(6,3,3) foot-site Jacobian columns for each leg's 3 joints,
    chassis frame (free joint pinned to identity), finite differences
    with respect to ROBOT ABSOLUTE targets. Input positions remain in
    MuJoCo relative-hinge coordinates, as stored by rollout traces.
    One model load per process; one MjData reused."""

    def __init__(self, model_xml: Path):
        import mujoco
        self._mj = mujoco
        self.m = mujoco.MjModel.from_xml_path(str(model_xml))
        self.d = mujoco.MjData(self.m)
        self.sids = [mujoco.mj_name2id(
            self.m, mujoco.mjtObj.mjOBJ_SITE, f"L{i}_foot_site")
            for i in range(6)]

    def _fk(self, q18):
        self.d.qpos[:] = 0.0
        self.d.qpos[3] = 1.0            # identity quat
        self.d.qpos[7:25] = q18
        self._mj.mj_kinematics(self.m, self.d)
        return np.array([self.d.site_xpos[s].copy() for s in self.sids])

    def __call__(self, qpos_joints: np.ndarray):
        eps = 1e-5
        q_logical = mujoco_rel_rad_to_robot_abs_rad(qpos_joints)
        J = np.zeros((6, 3, 3))
        for leg in range(6):
            for k in range(3):
                j = leg * 3 + k
                qp = q_logical.copy(); qp[j] += eps
                qm = q_logical.copy(); qm[j] -= eps
                # knee_rel = knee_abs - hip_abs: changing an absolute
                # hip target also changes the relative knee hinge.
                fp = self._fk(robot_abs_rad_to_mujoco_rel_rad(qp))[leg]
                fm = self._fk(robot_abs_rad_to_mujoco_rel_rad(qm))[leg]
                J[leg, :, k] = (fp - fm) / (2 * eps)
        return J


def tracking_lag_med_deg(qpos: np.ndarray, commanded_position: np.ndarray) -> float:
    """Median post-step target error in the shared robot-absolute frame.

    The historical output key says lag; this is a position-error summary,
    not a measurement of latency or counterfactual dynamic response.
    """
    measured = np.stack([
        mujoco_rel_rad_to_robot_abs_rad(q) for q in qpos[:, 7:25]])
    return float(np.median(np.abs(measured - commanded_position)) / DEG2RAD)


def unit_dirs(n_rand=20, seed=0):
    rng = np.random.default_rng(seed)
    axes = np.vstack([np.eye(3), -np.eye(3)])
    r = rng.normal(size=(n_rand, 3))
    r /= np.linalg.norm(r, axis=1, keepdims=True)
    return np.vstack([axes, r])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("traces", nargs="+", type=Path)
    ap.add_argument("--model-xml", type=Path,
                    default=Path("mesh_mujoco/hexapod_mesh_mjx.xml"))
    ap.add_argument("--bias-deg", type=float, nargs=3,
                    default=[0.0, 40.0, 35.0], help="yaw hip knee")
    ap.add_argument("--box-deg", type=float, nargs=3,
                    default=[15.0, 20.0, 25.0], help="yaw hip knee")
    ap.add_argument("--max-delta-q-deg", type=float, default=3.6)
    ap.add_argument("--budgets", type=float, nargs="+",
                    default=[0.05, 0.10, 0.25, 0.50])
    ap.add_argument("--perturb-every", type=int, default=5)
    ap.add_argument("--foot-every", type=int, default=10)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    dec = Decoder(args.bias_deg, args.box_deg)
    max_dq = args.max_delta_q_deg * DEG2RAD
    dirs = unit_dirs()
    summary = {"traces": [str(t) for t in args.traces],
               "max_delta_q_deg": args.max_delta_q_deg,
               "budgets": args.budgets, "episodes": [],
               "n_dirs": int(len(dirs)),
               "analysis_contract": {
                   "version": 2,
                   "joint_target_frame": "robot_abs_tibia_v2",
                   "jacobian_columns": "robot_abs",
                   "foot_response": "nominal_kinematic_support_only",
                   "trace_state_timing": "post-step qpos/contact; pre-filter safety state",
                   "margin_exceeds_budget_denominator": "all joint/tick samples",
               }}

    # pooled accumulators
    pool = {
        "sat": [],          # (T,18) bool one-sided saturation
        "sat_dir": [],      # (T,18) sign of raw delta where saturated
        "pin": [],          # (T,18) |a|>=0.999
        "contact": [],      # (T,6)
        "margin": [],       # action-units margin where saturated
        "trans": {},        # (budget, sign) -> list of bool per (tick,joint)
        "ratio": {},        # (budget, cs) -> list of per-direction ratios
        "upz": {},          # (budget, cs) -> achievable +z mm at budget
    }

    for tp in args.traces:
        z = np.load(tp, allow_pickle=True)
        need = ("action", "applied_action", "proposed_position",
                "presafe_last_position", "commanded_position", "qpos",
                "contact")
        missing = [k for k in need if k not in z]
        if missing:
            raise SystemExit(f"{tp}: missing trace fields {missing} — "
                             f"rerun eval with debug_pipeline_record")
        act = z["action"]; app = z["applied_action"]
        prop = z["proposed_position"]; last = z["presafe_last_position"]
        cmd = z["commanded_position"]; qpos = z["qpos"]
        contact = z["contact"].astype(bool)
        T = len(act)
        ep_meta = json.loads(str(z["ep_json"]))

        # ---- 1. parity ------------------------------------------------
        errA = float(np.abs(dec(app) - prop).max())
        rec = np.stack([safe_filter(last[t], prop[t], max_dq)
                        for t in range(T)])
        errB = float(np.abs(rec - cmd).max())
        # last_safe continuity: last[t] == cmd[t-1]
        errC = float(np.abs(last[1:] - cmd[:-1]).max())
        noise = float(np.abs(app - np.clip(act, -1, 1)).max())
        if errA > 1e-9 or errB > 1e-9:
            raise SystemExit(
                f"{tp}: pure-replica parity FAILED (decoder {errA:.3e}, "
                f"safety {errB:.3e}) — offline model does not reproduce "
                f"the recorded pipeline; aborting rather than reporting "
                f"fiction")

        # ---- 2. saturation census -------------------------------------
        dq_raw = prop - last
        sat = np.abs(dq_raw) >= max_dq * (1 - 1e-9)
        satdir = np.sign(dq_raw) * sat
        pin = np.abs(app) >= 0.999
        legs_contact = contact  # (T,6)

        # margin (action units) to regain effect against saturation dir
        margin = np.where(sat, (np.abs(dq_raw) - max_dq) / dec.box, np.nan)

        # ---- 3. empirical perturbation on copied state ----------------
        ticks = np.arange(0, T, args.perturb_every)
        trans_counts = {}
        for b in args.budgets:
            for sign in (+1, -1):
                moved = np.zeros((len(ticks), N_JOINTS), dtype=bool)
                for i, t in enumerate(ticks):
                    base_safe = rec[t]
                    for j in range(N_JOINTS):
                        a2 = app[t].copy()
                        a2[j] = np.clip(a2[j] + sign * b, -1.0, 1.0)
                        q2 = safe_filter(last[t], dec(a2), max_dq)
                        moved[i, j] = abs(q2[j] - base_safe[j]) > 1e-9
                trans_counts[(b, sign)] = moved
                pool["trans"].setdefault((b, sign), []).append(moved)

        # ---- 4. foot-space direction analysis -------------------------
        fticks = np.arange(0, T, args.foot_every)
        jac = LegJac(args.model_xml)
        Jcache = {int(t): jac(qpos[t, 7:25]) for t in fticks}
        for b in args.budgets:
            for t in fticks:
                J = Jcache[int(t)]
                # per-joint transmitted interval at budget b
                hi = np.zeros(N_JOINTS); lo = np.zeros(N_JOINTS)
                base_safe = rec[t]
                for j in range(N_JOINTS):
                    outs = []
                    for sign in (+1, -1):
                        a2 = app[t].copy()
                        a2[j] = np.clip(a2[j] + sign * b, -1.0, 1.0)
                        q2 = safe_filter(last[t], dec(a2), max_dq)
                        outs.append(q2[j] - base_safe[j])
                    hi[j] = max(outs + [0.0]); lo[j] = min(outs + [0.0])
                # ideal unsaturated channel, same budget/action bounds
                av_p = np.minimum(b, 1.0 - app[t]); av_m = np.minimum(b, 1.0 + app[t])
                ihi = np.minimum(dec.box * np.maximum(av_p, 0), max_dq)
                ilo = -np.minimum(dec.box * np.maximum(av_m, 0), max_dq)
                for leg in range(6):
                    cs = "stance" if legs_contact[t, leg] else "swing"
                    Jl = J[leg]
                    s = slice(leg * 3, leg * 3 + 3)
                    A = np.array([
                        sum(max(u @ Jl[:, k] * hi[s][k], u @ Jl[:, k] * lo[s][k])
                            for k in range(3)) for u in dirs])
                    I = np.array([
                        sum(max(u @ Jl[:, k] * ihi[s][k], u @ Jl[:, k] * ilo[s][k])
                            for k in range(3)) for u in dirs])
                    ratio = A / np.maximum(I, 1e-12)
                    pool["ratio"].setdefault((b, cs), []).append(ratio)
                    uz = np.array([0.0, 0.0, 1.0])
                    Az = sum(max(uz @ Jl[:, k] * hi[s][k], uz @ Jl[:, k] * lo[s][k])
                             for k in range(3))
                    pool["upz"].setdefault((b, cs), []).append(Az * 1000.0)

        pool["sat"].append(sat); pool["sat_dir"].append(satdir)
        pool["pin"].append(pin); pool["contact"].append(legs_contact)
        pool["margin"].append(margin)

        summary["episodes"].append({
            "trace": tp.name, "ticks": int(T),
            "parity_decoder_max_rad": errA,
            "parity_safety_max_rad": errB,
            "parity_lastsafe_chain_max_rad": errC,
            "action_noise_max": noise,
            "ep_return": ep_meta.get("return"),
            "slip_m_total": ep_meta.get("slip_m_total"),
            "slew_sat_frac_reported": ep_meta.get("slew_sat_frac"),
            "any_joint_sat_frac": float(sat.any(axis=1).mean()),
            "mean_joints_sat_per_tick": float(sat.sum(axis=1).mean()),
            "tracking_lag_med_deg": tracking_lag_med_deg(qpos, cmd),
        })
        print(f"[probe] {tp.name}: T={T} parity ok "
              f"(dec {errA:.1e}, safe {errB:.1e}, chain {errC:.1e}, "
              f"noise {noise:.3f}); any-sat "
              f"{sat.any(axis=1).mean():.3f}, mean sat joints/tick "
              f"{sat.sum(axis=1).mean():.2f}")

    # ---------- pooled aggregation ------------------------------------
    sat = np.concatenate(pool["sat"]); pin = np.concatenate(pool["pin"])
    contact = np.concatenate(pool["contact"])
    margin = np.concatenate(pool["margin"])
    leg_contact_j = np.repeat(contact, 3, axis=1)  # (T,18)

    def _axis(m):  # per-axis-class mean over (tick,joint)
        return {AXIS_NAMES[k]: float(np.nanmean(m[:, k::3])) for k in range(3)}

    agg = {
        "per_joint_sat_frac": [float(x) for x in sat.mean(axis=0)],
        "sat_frac_by_axis": _axis(sat.astype(float)),
        "sat_frac_stance_joints": float(sat[leg_contact_j].mean()),
        "sat_frac_swing_joints": float(sat[~leg_contact_j].mean()),
        "any_joint_sat_frac": float(sat.any(axis=1).mean()),
        "all_joint_sat_frac": float(sat.all(axis=1).mean()),
        "mean_joints_sat_per_tick": float(sat.sum(axis=1).mean()),
        "hist_joints_sat_per_tick": np.bincount(
            sat.sum(axis=1), minlength=19).tolist(),
        "action_pin_frac_by_axis": _axis(pin.astype(float)),
        "margin_action_units_quartiles": [
            float(x) for x in np.nanpercentile(margin, [25, 50, 75, 95])],
        "margin_exceeds_budget_frac": {
            str(b): float(np.nanmean(margin > b)) for b in args.budgets},
        "transmission": {}, "foot_dirs": {},
    }
    for (b, sign), lst in pool["trans"].items():
        m = np.concatenate(lst)
        agg["transmission"][f"b{b}_sign{'+' if sign > 0 else '-'}"] = {
            "moved_frac": float(m.mean()),
            "by_axis": _axis(m.astype(float))}
    # either-sign transmission
    for b in args.budgets:
        mp = np.concatenate(pool["trans"][(b, 1)])
        mm = np.concatenate(pool["trans"][(b, -1)])
        both = mp | mm
        agg["transmission"][f"b{b}_either"] = {
            "moved_frac": float(both.mean()),
            "by_axis": _axis(both.astype(float)),
            "dead_both_dirs_frac": float((~both).mean())}
    for (b, cs), lst in pool["ratio"].items():
        r = np.concatenate(lst)
        z = pool["upz"][(b, cs)]
        agg["foot_dirs"][f"b{b}_{cs}"] = {
            "n": int(r.size),
            "ratio_quartiles": [float(x) for x in
                                np.percentile(r, [25, 50, 75])],
            "lost_frac_ratio_lt_0.2": float((r < 0.2).mean()),
            "kept_frac_ratio_gt_0.8": float((r > 0.8).mean()),
            "up_z_mm_med": float(np.median(z)),
        }
    summary["pooled"] = agg
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "probe_summary.json", "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps(agg, indent=1))
    print(f"[probe] summary -> {args.out / 'probe_summary.json'}")


if __name__ == "__main__":
    main()
