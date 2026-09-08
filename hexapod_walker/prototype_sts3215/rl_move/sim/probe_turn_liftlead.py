"""probe_turn_liftlead.py — pinned-plant lift-only phase-lead comparison
(todaypolicy steering experiment, cycle 20260908T005017).

Plain English: the corrected frozen turn audit showed both the scripted
gait and the learned cont8m policy undertrack combined forward+yaw
commands, and the (superseded-in-interpretation) pipeline probe measured
65-69% of planned-swing ticks still in ground contact (commanded 25 mm
lift executes as a few mm, lagged).  The independent review
(artifacts/rl_watchdog/turnpipeline_review_20260908.md) scoped the ONE
next experiment: on a hash-pinned plant, measure per-foot actuator/
contact lag, select ONE vertical (lift-only) phase lead from it, and
compare baseline vs that lead at the original arc cells (vx=0.08,
wz=+/-0.15, starts 0/pi) plus a straight guard — preserving XY foot
path, cadence, swing duration, neutral stance, write_speed 400,
write_acc 20 and the 0.375 deg/tick slew.  Only a gain in BOTH turn
directions with retained gait/progress/slip justifies one bounded
same-seed training canary.

PLANT PINNING (the review's first correction): the prior pipeline rows
ran a stale 3.494226 kg full-mesh XML; the corrected frozen audit plant
is 4.80573 kg.  The controller has no copy of the frozen full-mesh XML
(7efb8e8a..., regenerated on the operator Mac), but the checked-in MJX
primitive-collision twin `mesh_mujoco/hexapod_mesh_mjx.xml` hash-matches
the corrected audit's own frozen manifest (a8a5ca8a...) bit-exactly,
carries the corrected 4.80573 kg mass/inertia, and is the EXACT plant
every pod training/qualification run loads (mesh -> twin fallback).
This probe therefore forces env.model_source=mesh_mjx and hard-asserts
the XML sha256, total mass, 100 Hz and the unchanged motor contract per
rollout.  Contact geometry is fitted primitives, not STL hulls — recorded
as a limit; cross-checking on the frozen full-mesh XML needs the machine
that has it.

Isolated read-only diagnostic: no shared code changed; the lift-lead is
implemented in a LOCAL TripodGait subclass that shifts ONLY the vertical
(dz) profile phase.  dx/dy (XY foot path), period, swing-window width,
stance radius, ramp and every servo/safety limit are bit-identical to
the baseline gait.
"""
from __future__ import annotations

import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent

from rl_move.robot_state import DEG2RAD
from rl_move.sim import probe_turn_authority as pta
from rl_move.sim.eval_checkpoint import CONTACT_N, model_identity
from rl_move.sim.joint_task import q_rad_to_action
from rl_move.sim.servo_model import motor_contract
from rl_move.sim.probe_turn_pipeline import fk_body_xy

from hexapod_core.tripod_gait import TripodGait

PIN = {
    # frozen corrected-audit manifest values
    # (logs/ckpt_eval/turnauth_repaired_20260907_*/manifest.json)
    "mesh_xml_sha256":
        "7efb8e8a0cb014c0b4bac27c41e7a85e683553168b87d85aac0d52d6a8e5a837",
    "mesh_mjx_xml_sha256":
        "a8a5ca8ada47621eb1396c841a593983df27b761f5b55cc2c36269c6e54dbe9e",
    "sim_model_json_sha256":
        "6968268e879eb95603d0801ddd25a59f37a3964eef6839e3b63be3df91fe412d",
    "sim_model_loaded_json_sha256":
        "144d43fa5dd3bae4eebf1cce47f2f6a8c6f70b3763b36f824d195ca9450273e1",
    "cont8m_ckpt_sha256":
        "4a902839912837168a52e7248eed983ee29e57e5db4d22eeaa827f0a5c1428a0",
    "model_mass_kg": 4.80573,
    "control_hz": 100.0,
    "bus.write_speed": 400.0,
    "bus.write_acc": 20.0,
    "safety.max_delta_q_deg": 0.375,
    "slew_limit_deg_s": 37.5,
    "resolved_vel_max_counts_s_max": 350.0,
}
LOAD_N = 2.0   # "materially loaded" pad: >2 N (static share is ~7.9 N/leg)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pin_manifest(plant: str) -> dict:
    m = {
        "mesh_mjx_xml_sha256": _sha(_PROTO / "mesh_mujoco/hexapod_mesh_mjx.xml"),
        "sim_model_json_sha256": _sha(_PROTO / "rl_move/sim/sim_model.json"),
        "sim_model_loaded_json_sha256":
            _sha(_PROTO / "rl_move/sim/sim_model_loaded.json"),
    }
    if plant == "fullmesh":
        # frozen full-STL plant (root-supplied assets.tar.gz, review
        # addendum 00:58 UTC) — must be extracted into THIS tree
        m["mesh_xml_sha256"] = _sha(_PROTO / "mesh_mujoco/hexapod_mesh.xml")
    for k, v in m.items():
        if PIN[k] != v:
            raise SystemExit(f"PIN FAIL {k}: {v} != frozen {PIN[k]}")
    return m


class LiftLeadTripodGait(TripodGait):
    """Lift-only phase lead: the vertical (dz) swing profile is evaluated
    at phase + 2*pi*lead_s/period; dx/dy come from the base phase and are
    BIT-EXACT identical to the stock gait (lead_s=0 short-circuits)."""

    def __init__(self, *a, lift_lead_s: float = 0.0, **kw):
        super().__init__(*a, **kw)
        self.lift_lead_s = float(lift_lead_s)

    def _foot_target_in_body(self, i, vx, vy, omega):
        dx, dy, dz = super()._foot_target_in_body(i, vx, vy, omega)
        if self.lift_lead_s == 0.0:
            return dx, dy, dz
        ph = self._phase
        t_eff = max(self.period * self.period_scale, 0.05)
        self._phase = (ph + 2 * math.pi * self.lift_lead_s / t_eff) \
            % (2 * math.pi)
        try:
            _, _, dz_led = super()._foot_target_in_body(i, vx, vy, omega)
        finally:
            self._phase = ph
        return dx, dy, dz_led


def fit_twist_resid(pos: np.ndarray, vel: np.ndarray, sel: np.ndarray):
    """LSQ planar twist + PER-FOOT residual speeds (the review's fix:
    keep the disagreement instead of discarding it)."""
    idx = np.flatnonzero(sel)
    if len(idx) < 2:
        return None
    rows, rhs = [], []
    for f in idx:
        px, py = pos[f]
        rows.append([1.0, 0.0, -py]); rhs.append(-vel[f, 0])
        rows.append([0.0, 1.0, px]); rhs.append(-vel[f, 1])
    A = np.asarray(rows); b = np.asarray(rhs)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    r = (A @ sol - b).reshape(-1, 2)
    resid = {int(f): float(np.hypot(*r[j])) for j, f in enumerate(idx)}
    return sol, resid


def xcorr_lag_ticks(x: np.ndarray, y: np.ndarray, max_lag: int) -> int:
    """lag k>=0 maximizing corr(x[t-k], y[t]) — how much y LAGS x."""
    x = x - x.mean(); y = y - y.mean()
    best, bk = -np.inf, 0
    for k in range(0, max_lag + 1):
        xa = x[:len(x) - k] if k else x
        ya = y[k:]
        d = (np.linalg.norm(xa) * np.linalg.norm(ya))
        c = float(xa @ ya / d) if d > 0 else 0.0
        if c > best:
            best, bk = c, k
    return bk


def rollout(*, policy: str, model, model_obs_width, cfg_set, vx_cmd, wz_cmd,
            seed, episode_seconds, phase_offset=0.0,
            lift_lead_s=0.0, plant: str = "twin") -> dict:
    env = pta.make_env(cfg_set, seed, episode_seconds)
    if model_obs_width is not None:
        n_env = int(env.observation_space.shape[0])
        if model_obs_width != n_env:
            raise SystemExit(f"obs width {model_obs_width} != env {n_env}")
    identity = model_identity(env)
    contract = motor_contract(env.cfg)
    # hard plant/contract pin (review correction #1)
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
    if policy == "scripted":
        gait = LiftLeadTripodGait(vx=0.0, lift_lead_s=lift_lead_s)
        gait.sync_plant_stance(*pta.WALK_PLANT)
        gait.reset_phase(phase=phase_offset)

    rows = []
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
            q_des = None
            plan_swing = None
        obs, r, term, trunc, info = env.step(act)
        if step >= hold_n + ramp_n and info.get("goal_mode") == "walk":
            d = env.data
            R = d.xmat[env._chassis_bid].reshape(3, 3)
            cx = d.xpos[env._chassis_bid]
            pads_w = np.array([d.xpos[b] for b in env._pad_bids])
            pads_b = (pads_w - cx) @ R
            force = np.array([float(d.sensordata[x]) for x in env._touch_adr])
            rows.append({
                "q_des": q_des,
                "q_safe": env.safety._last_safe.copy(),
                "q_act": env._state.joint_position.copy(),
                "plan_swing": plan_swing,
                "force": force,
                "pads_w": pads_w.copy(),
                "pads_b": pads_b[:, :2].copy(),
                "pads_wz": pads_w[:, 2].copy(),
                "vx_body": float(env._body_vel_xy()[0]),
                "wz_body": float(env._body_wz()),
            })
        step += 1
        if term:
            fell = True
        if term or trunc:
            break
    env.close()

    dt = 0.01
    out = {"policy": policy, "vx_cmd": vx_cmd, "wz_cmd": wz_cmd,
           "seed": seed, "phase_offset": phase_offset,
           "lift_lead_s": lift_lead_s, "fell": fell,
           "n_scored_ticks": len(rows), "model_identity": identity,
           "motor_contract": {k: contract[k] for k in
                              ("bus.write_speed", "bus.write_acc",
                               "safety.max_delta_q_deg", "slew_limit_deg_s",
                               "resolved_vel_max_counts_s_max",
                               "control.hz")}}
    if len(rows) < 200:
        out["error"] = "insufficient scored ticks"
        return out

    contact = np.stack([r["force"] for r in rows]) > CONTACT_N
    loaded = np.stack([r["force"] for r in rows]) > LOAD_N
    pads_b = np.stack([r["pads_b"] for r in rows])
    pads_w = np.stack([r["pads_w"] for r in rows])
    pads_wz = np.stack([r["pads_wz"] for r in rows])
    qa = np.stack([r["q_act"] for r in rows])
    qs = np.stack([r["q_safe"] for r in rows])
    plan_sw = (np.stack([r["plan_swing"] for r in rows]).astype(bool)
               if rows[0]["plan_swing"] is not None else None)

    out["body"] = {"vx_med": float(np.median([r["vx_body"] for r in rows])),
                   "wz_med": float(np.median([r["wz_body"] for r in rows]))}
    out["duty_contact"] = np.mean(contact, axis=0).round(4).tolist()

    # material-contact slip: world-frame pad XY speed while loaded/contact
    v_w = np.linalg.norm(np.diff(pads_w[:, :, :2], axis=0), axis=2) / dt
    def _slipstats(sel):
        s = {}
        for f in range(6):
            m = sel[1:, f] & sel[:-1, f]
            v = v_w[m, f]
            s[f] = ({"med": float(np.median(v)),
                     "p90": float(np.percentile(v, 90)), "n": int(len(v))}
                    if len(v) else None)
        return s
    out["slip_contact_mps"] = _slipstats(contact)
    out["slip_loaded_mps"] = _slipstats(loaded)

    # LSQ twists on des(FK)/act(FK)/true pads with BOTH selectors + residuals
    def _stage(pos_seq, sel_seq):
        fits, resid = [], {f: [] for f in range(6)}
        for t in range(1, len(pos_seq)):
            sel = sel_seq[t] & sel_seq[t - 1]
            v = (pos_seq[t] - pos_seq[t - 1]) / dt
            fr = fit_twist_resid(pos_seq[t - 1], v, sel)
            if fr is None:
                continue
            sol, res = fr
            fits.append(sol)
            for f, rv in res.items():
                resid[f].append(rv)
        if not fits:
            return None
        f = np.asarray(fits)
        return {"vx_med": float(np.median(f[:, 0])),
                "vy_med": float(np.median(f[:, 1])),
                "wz_med": float(np.median(f[:, 2])), "n": len(fits),
                "per_foot_resid_med_mps": {
                    k: (float(np.median(v)) if v else None)
                    for k, v in resid.items()}}
    tw = {"pads_contactsel": _stage(pads_b, contact),
          "pads_loadedsel": _stage(pads_b, loaded)}
    if plan_sw is not None:
        tw["pads_planstancesel"] = _stage(pads_b, ~plan_sw)
        qd = np.stack([r["q_des"] for r in rows])
        des_xy = np.stack([fk_body_xy(q) for q in qd])
        tw["fk_des_planstancesel"] = _stage(des_xy, ~plan_sw)
        tw["fk_des_contactsel"] = _stage(des_xy, contact)
    act_xy = np.stack([fk_body_xy(q) for q in qa])
    tw["fk_act_contactsel"] = _stage(act_xy, contact)
    out["stage_twists"] = tw

    # per-leg measurements
    per = {}
    max_lag = 40
    for f in range(6):
        e = {}
        if plan_sw is not None:
            qd = np.stack([r["q_des"] for r in rows])
            for nm, j in (("yaw", 3 * f), ("hip", 3 * f + 1),
                          ("knee", 3 * f + 2)):
                dd = np.diff(qd[:, j]); da = np.diff(qa[:, j])
                e[f"lag_{nm}_ms"] = 10 * xcorr_lag_ticks(dd, da, max_lag)
            # contact-timing lag: how much "airborne" LAGS planned swing
            e["contact_lag_ms"] = 10 * xcorr_lag_ticks(
                plan_sw[:, f].astype(float),
                (~contact[:, f]).astype(float), max_lag)
            e["scuff_frac"] = float(np.mean(contact[plan_sw[:, f], f])) \
                if plan_sw[:, f].any() else None
            st_med = (np.median(pads_wz[~plan_sw[:, f], f])
                      if (~plan_sw[:, f]).any() else np.nan)
            sw = pads_wz[plan_sw[:, f], f]
            e["achieved_lift_p90_mm"] = (
                float(np.percentile(sw - st_med, 90) * 1000)
                if len(sw) and np.isfinite(st_med) else None)
        per[f] = e
    out["per_leg"] = per
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", choices=("scripted", "checkpoint"),
                    required=True)
    ap.add_argument("--checkpoint", type=Path, default=None)
    ap.add_argument("--cfg-json", type=Path, required=True)
    ap.add_argument("--cells", required=True, help="vx:wz,...")
    ap.add_argument("--phase-offsets", default="0.0")
    ap.add_argument("--lift-lead-s", type=float, default=0.0)
    ap.add_argument("--plant", choices=("twin", "fullmesh"), default="twin",
                    help="twin: checked-in hexapod_mesh_mjx.xml (the pod "
                         "training plant); fullmesh: the frozen 7efb8e8a "
                         "full-STL XML (must be present in this tree)")
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

    model = width = None
    ckpt_sha = None
    if args.policy == "checkpoint":
        ckpt_sha = _sha(args.checkpoint)
        if ckpt_sha != PIN["cont8m_ckpt_sha256"]:
            raise SystemExit(f"PIN FAIL checkpoint sha {ckpt_sha}")
        model, width = pta._load_model(args.checkpoint)

    results = []
    for c in args.cells.split(","):
        vx, wz = (float(x) for x in c.split(":"))
        for po in (float(x) for x in args.phase_offsets.split(",")):
            r = rollout(policy=args.policy, model=model,
                        model_obs_width=width, cfg_set=cfg_set,
                        vx_cmd=vx, wz_cmd=wz, seed=args.seed,
                        episode_seconds=args.episode_seconds,
                        phase_offset=po, lift_lead_s=args.lift_lead_s,
                        plant=args.plant)
            results.append(r)
            print(json.dumps({"cell": [vx, wz], "start": po,
                              "fell": r["fell"], "body": r.get("body"),
                              "label": args.label}), flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(
        {"schema": "hexapod.turn_liftlead_probe.v1", "label": args.label,
         "policy": args.policy, "lift_lead_s": args.lift_lead_s,
         "plant": args.plant,
         "checkpoint": str(args.checkpoint) if args.checkpoint else None,
         "checkpoint_sha256": ckpt_sha, "pin_manifest": pins,
         "pin_expect": PIN, "cfg_set": cfg_set, "seed": args.seed,
         "episode_seconds": args.episode_seconds, "results": results},
        indent=1, default=str) + "\n")
    print("COMPLETE", args.out, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
