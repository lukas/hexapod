"""Zero-spend loaded-foot-slip decomposition + knee-frame provenance audit.

Built 2026-09-07 (walkcurr operator focus note 20260907T150325Z): the
easy0905 campaign's frozen full-realism no-crutch champion carries a
persistent ~4-5 slip/m gate reading that survived every reward-dose and
DR-band variant (7/7 closed reads).  Before any further training spend,
this tool answers two questions on a FROZEN checkpoint, zero training:

1. MEASUREMENT: how much of the gate's slip number is genuine
   contact-point sliding (skating) vs artifacts of the metric itself?
   The gate (eval_checkpoint.run_episode) sums |d pad_body_xy| on loaded
   ticks — the PAD BODY CENTER, not the contact point.  A foot that
   ROLLS/ROCKS about a static contact point translates its center
   without skating; low-force chatter ticks (touch barely > 0.5 N)
   count fully.  Decomposition per loaded tick, same 100 Hz sampling as
   the gate:
     A  pad-center slip     = |d pad_xy|                (the gate metric)
     B  material-point slip = |XY of (x(t+1) + R(t+1)R(t)^T (pc - x(t))
                              - pc)|  — displacement of the pad-fixed
                              material point that sat at the MuJoCo
                              contact position pc at tick t.  Pure
                              rolling/rocking about a static contact
                              gives ~0; true skating gives ~A.
     A_lowF / A_highF       = A split at touch force 2 N (chatter share).
2. FRAME PROVENANCE: every sharded MJX walk run trained before the
   2026-09-07 07:2x fix (commit dd248bd8, mjx_sharded_vec_env knee-frame
   sites) saw obs q_nom KNEE slots in the raw mujoco-rel frame (shifted
   by -hip_nom vs the robot_abs contract), while every CPU gate eval
   feeds the corrected frame.  --shim trainframe reproduces the
   training-era frame at eval (instance-level patch of
   env._q_nom_for_obs, no shared-code change) so the policy can be
   scored under its own training obs distribution.  If the gate slip
   gap is (partly) train/eval obs mismatch, the shim arm reads lower
   slip / better gait than the control arm on identical seeds.

Diagnostic only: no reward, no cfg-key, no shared-default change.
Run it on the checkpoint's own pod (ops.sh podeval convention).

3. STANCE-PHASE LOCATION (added 09-07, walkcurr lswin closure follow-up):
   the direct-slip-reward-pricing family closed 5/5 (flat/ratio/windowed/
   escape-closed charges all converge on the same ~5-6/m floor) without
   ever answering WHERE in the stance cycle the loaded drift happens.
   --phase-bins K bins each stance bout (touchdown=0 .. liftoff=1) into
   K equal-width phases and reports, per phase, the mean per-tick
   material slip (mm/tick), mean touch force, and mean concurrent body
   forward speed, pooled across all loaded ticks of all 6 legs. A flat
   profile across phases means uniform creep (a genuine kinematic/gait-
   style mismatch); a spike at phase 0 means impact/touchdown skid; a
   spike at phase K-1 means toe-drag/late push-off — each points at a
   different next mechanism (touchdown velocity matching vs a push-off
   liftoff timing fix) instead of another reward-pricing dose.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from .servo_model import SimServoParams
from .walk_task import SimHexapodJointWalkEnv

CONTACT_N = 0.5   # gate's touch-force contact threshold (eval_checkpoint)
CHATTER_N = 2.0   # low-force bin upper edge for the chatter split


def _floor_geoms(model) -> set[int]:
    import mujoco
    return {g for g in range(model.ngeom)
            if model.geom_bodyid[g] == 0}


def _pad_geoms(model, bid: int) -> set[int]:
    return {g for g in range(model.ngeom) if model.geom_bodyid[g] == bid}


def _bout_runs(mask: np.ndarray) -> list:
    """Contiguous runs of True in a 1-D bool array -> [(start, length)]."""
    runs = []
    n = len(mask)
    i = 0
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while j < n and mask[j]:
            j += 1
        runs.append((i, j - i))
        i = j
    return runs


def _phase_profile(loaded_by_leg: list, slip_tick_by_leg: list,
                    force_by_leg: list, body_speed: np.ndarray,
                    k_bins: int) -> dict:
    """Bin every loaded tick of every leg by its normalized position
    within its own stance bout (0=touchdown .. 1=liftoff) into k_bins
    equal-width phases; pool across legs. Returns per-bin (slip mm/tick,
    force N, body forward speed m/s) means and the pooled tick count."""
    slip_sum = np.zeros(k_bins)
    force_sum = np.zeros(k_bins)
    speed_sum = np.zeros(k_bins)
    count = np.zeros(k_bins, dtype=int)
    for leg in range(6):
        loaded = loaded_by_leg[leg]
        slip_t = slip_tick_by_leg[leg]
        force_t = force_by_leg[leg]
        for start, length in _bout_runs(loaded):
            for off in range(length):
                idx = start + off
                frac = off / (length - 1) if length > 1 else 0.0
                b = min(k_bins - 1, int(frac * k_bins))
                slip_sum[b] += float(slip_t[idx])
                force_sum[b] += float(force_t[idx])
                speed_sum[b] += float(body_speed[idx])
                count[b] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        slip_mean = np.where(count > 0, slip_sum / np.maximum(count, 1), 0.0)
        force_mean = np.where(count > 0, force_sum / np.maximum(count, 1), 0.0)
        speed_mean = np.where(count > 0, speed_sum / np.maximum(count, 1), 0.0)
    return {
        "slip_mm_per_tick": [round(1000.0 * float(x), 3) for x in slip_mean],
        "force_n": [round(float(x), 3) for x in force_mean],
        "body_speed_m_s": [round(float(x), 4) for x in speed_mean],
        "tick_count": [int(x) for x in count],
    }


def run_episode(env, model, *, deterministic: bool, pads, pad_geoms,
                floor, knee_shift_probe: list, phase_bins: int = 0) -> dict:
    obs, info0 = env.reset()
    if hasattr(model, "reset"):
        model.reset()
    # actual knee-frame shift this episode (hip slots of q_nom): the
    # magnitude the pre-fix sharded worker bug displaced knee obs by.
    qn = env._q_nom
    knee_shift_probe.append([round(float(qn[3 * l + 1]), 4)
                             for l in range(6)])
    T = env._max_steps if hasattr(env, "_max_steps") else 10 ** 6
    contact_hist, force_hist = [], []
    pad_x_hist, pad_R_hist, cpos_hist = [], [], []
    body_speed_hist = []
    cmd_dist_m, along_dist_m = 0.0, 0.0
    term = trunc = False
    term_reason = ""
    ret = 0.0
    while not (term or trunc):
        act, _ = model.predict(obs, deterministic=deterministic)
        obs, r, term, trunc, info = env.step(act)
        ret += float(r)
        force_hist.append([float(env.data.sensordata[a])
                           for a in env._touch_adr])
        contact_hist.append([f > CONTACT_N for f in force_hist[-1]])
        pad_x_hist.append(np.array(
            [env.data.xpos[b].copy() for b in pads]))
        pad_R_hist.append(np.array(
            [env.data.xmat[b].reshape(3, 3).copy() for b in pads]))
        # mean MuJoCo contact position per foot this tick (None if the
        # touch sensor fired but no matching pad-floor contact exists)
        cp = [None] * 6
        for ci in range(env.data.ncon):
            c = env.data.contact[ci]
            for f in range(6):
                if ((c.geom1 in pad_geoms[f] and c.geom2 in floor)
                        or (c.geom2 in pad_geoms[f] and c.geom1 in floor)):
                    p = c.pos.copy()
                    cp[f] = p if cp[f] is None else 0.5 * (cp[f] + p)
        cpos_hist.append(cp)
        vb = env._body_vel_xy()
        body_speed_hist.append(float(math.hypot(vb[0], vb[1])))
        g = env._current_goal()
        if g is not None:
            s_ref = math.hypot(g.vx_ref, g.vy_ref)
            if s_ref > 1e-3:
                cmd_dist_m += s_ref * env.dt
                along_dist_m += ((vb[0] * g.vx_ref + vb[1] * g.vy_ref)
                                 / s_ref) * env.dt
        if term:
            term_reason = info.get("termination_reason", "")

    contact = np.asarray(contact_hist, dtype=bool)          # (T,6)
    force = np.asarray(force_hist)                          # (T,6)
    pad_x = np.stack(pad_x_hist)                            # (T,6,3)
    pad_R = np.stack(pad_R_hist)                            # (T,6,3,3)
    body_speed = np.asarray(body_speed_hist)                # (T,)
    n = len(contact)
    slip_center = np.zeros(6)
    slip_material = np.zeros(6)
    slip_lowF = np.zeros(6)
    slip_highF = np.zeros(6)
    untracked = np.zeros(6)   # loaded ticks with no mj contact point
    swings = [0] * 6
    loaded_by_leg, slip_tick_by_leg, force_tick_by_leg = [], [], []
    for f in range(6):
        cf = contact[:, f]
        d = np.diff(cf.astype(int))
        swings[f] = int(np.sum(d == -1))
        dxy = np.linalg.norm(np.diff(pad_x[:, f, :2], axis=0), axis=1)
        loaded = cf[:-1]
        slip_center[f] = float(dxy[loaded].sum())
        lowF = loaded & (force[:-1, f] < CHATTER_N)
        slip_lowF[f] = float(dxy[lowF].sum())
        slip_highF[f] = float(
            dxy[loaded & (force[:-1, f] >= CHATTER_N)].sum())
        slip_material_tick = np.zeros(n - 1)
        for t in range(n - 1):
            if not cf[t]:
                continue
            pc = cpos_hist[t][f]
            if pc is None:
                untracked[f] += float(dxy[t])
                continue
            x0, x1 = pad_x[t, f], pad_x[t + 1, f]
            R0, R1 = pad_R[t, f], pad_R[t + 1, f]
            p_mat = x1 + R1 @ (R0.T @ (pc - x0))
            slip_material_tick[t] = float(np.linalg.norm((p_mat - pc)[:2]))
        slip_material[f] = float(slip_material_tick.sum())
        loaded_by_leg.append(loaded)
        slip_tick_by_leg.append(slip_material_tick)
        force_tick_by_leg.append(force[:-1, f])
    duty = contact.mean(axis=0)
    sacrificed = [f for f in range(6)
                  if duty[f] < 0.10 or (duty[f] > 0.95 and swings[f] == 0)]
    denom = max(along_dist_m, 0.05)
    phase_profile = (_phase_profile(loaded_by_leg, slip_tick_by_leg,
                                    force_tick_by_leg, body_speed[:-1],
                                    phase_bins)
                     if phase_bins > 0 else None)
    return {
        "return": round(ret, 2),
        "terminated": bool(term),
        "term_reason": term_reason,
        "cmd_dist_m": round(float(cmd_dist_m), 3),
        "along_dist_m": round(float(along_dist_m), 3),
        "progress_ratio": (round(float(along_dist_m / cmd_dist_m), 3)
                           if cmd_dist_m > 1e-6 else None),
        "gait_valid": not sacrificed,
        "sacrificed_legs": sacrificed,
        "duty_cycle": [round(float(x), 2) for x in duty],
        "swing_count": swings,
        "slip_center_m": round(float(slip_center.sum()), 4),
        "slip_material_m": round(float(slip_material.sum()), 4),
        "slip_untracked_m": round(float(untracked.sum()), 4),
        "slip_lowF_m": round(float(slip_lowF.sum()), 4),
        "slip_highF_m": round(float(slip_highF.sum()), 4),
        "slip_center_per_m": round(float(slip_center.sum()) / denom, 3),
        "slip_material_per_m": round(float(slip_material.sum()) / denom, 3),
        "slip_center_per_leg": [round(float(x), 4) for x in slip_center],
        "slip_material_per_leg": [round(float(x), 4) for x in slip_material],
        "phase_profile": phase_profile,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("--episodes", type=int, default=6)
    ap.add_argument("--episode-seconds", type=float, default=20.0)
    ap.add_argument("--dr-scale", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--cfg-set", action="append", default=None)
    ap.add_argument("--shim", choices=("none", "trainframe"),
                    default="none")
    ap.add_argument("--phase-bins", type=int, default=0,
                    help="bin loaded ticks by normalized stance-bout "
                         "position (0=touchdown..1=liftoff) into this "
                         "many phases; 0 (default) skips the profile")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    from .train_ppo_sim import _parse_cfg_set
    cfg_kw = {}
    if args.cfg_set:
        from rl_move.config import load_config
        cfg = load_config()
        for key, parsed in _parse_cfg_set(args.cfg_set).items():
            sect, name = key.split(".", 1)
            cfg.setdefault(sect, {})[name] = parsed
        cfg_kw["cfg"] = cfg
    has_dr_ov = bool(cfg_kw.get("cfg", {}).get("dr"))
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg_kw.get("cfg")),
        randomize=(args.dr_scale > 0 or has_dr_ov),
        dr_scale=args.dr_scale,
        episode_seconds=args.episode_seconds, seed=args.seed,
        render_mode=None, **cfg_kw)
    # force walk-only episodes, same as eval_checkpoint's mode loop
    gen = env._goal_gen
    for a in list(vars(type(gen))) + list(vars(gen)):
        if a.startswith("p_"):
            setattr(gen, a, 1.0 if a == "p_walk" else 0.0)

    if args.shim == "trainframe":
        from hexapod_core.joint_frame import robot_abs_rad_to_mujoco_rel_rad
        orig = env._q_nom_for_obs
        env._q_nom_for_obs = (
            lambda: robot_abs_rad_to_mujoco_rel_rad(orig()))
        print("[shim] obs q_nom served in TRAINING-ERA mujoco-rel knee "
              "frame (pre-dd248bd8 sharded-worker reproduction)")

    from .gru_policy import load_checkpoint_auto
    model = load_checkpoint_auto(args.checkpoint, device="cpu")
    n_model = int(model.observation_space.shape[0])
    n_env = int(env.observation_space.shape[0])
    if n_model != n_env:
        raise SystemExit(f"obs width mismatch: ckpt {n_model} env {n_env}")

    pads = [env.model.body(f"L{i}_pad").id for i in range(6)]
    floor = _floor_geoms(env.model)
    pad_geoms = [_pad_geoms(env.model, b) for b in pads]
    knee_shift_probe: list = []
    eps = []
    for k in range(args.episodes):
        ep = run_episode(env, model,
                         deterministic=not args.stochastic,
                         pads=pads, pad_geoms=pad_geoms, floor=floor,
                         knee_shift_probe=knee_shift_probe,
                         phase_bins=args.phase_bins)
        eps.append(ep)
        print(f"ep{k}: term={ep['terminated']} gv={ep['gait_valid']} "
              f"along={ep['along_dist_m']:.3f} "
              f"slipC/m={ep['slip_center_per_m']:.2f} "
              f"slipM/m={ep['slip_material_per_m']:.2f} "
              f"lowF={ep['slip_lowF_m']:.3f} highF={ep['slip_highF_m']:.3f} "
              f"untracked={ep['slip_untracked_m']:.3f}")

    def med(key):
        vals = [e[key] for e in eps if e.get(key) is not None]
        return round(float(np.median(vals)), 3) if vals else None

    phase_agg = None
    if args.phase_bins > 0:
        K = args.phase_bins
        slip_sum = np.zeros(K)
        force_sum = np.zeros(K)
        speed_sum = np.zeros(K)
        count = np.zeros(K)
        for e in eps:
            pp = e.get("phase_profile")
            if not pp:
                continue
            c = np.asarray(pp["tick_count"], dtype=float)
            slip_sum += np.asarray(pp["slip_mm_per_tick"]) * c
            force_sum += np.asarray(pp["force_n"]) * c
            speed_sum += np.asarray(pp["body_speed_m_s"]) * c
            count += c
        with np.errstate(invalid="ignore", divide="ignore"):
            phase_agg = {
                "slip_mm_per_tick": [round(float(x), 3) for x in
                                    np.where(count > 0,
                                             slip_sum / np.maximum(count, 1),
                                             0.0)],
                "force_n": [round(float(x), 3) for x in
                           np.where(count > 0,
                                    force_sum / np.maximum(count, 1), 0.0)],
                "body_speed_m_s": [round(float(x), 4) for x in
                                  np.where(count > 0,
                                           speed_sum / np.maximum(count, 1),
                                           0.0)],
                "tick_count": [int(x) for x in count],
            }
        print("phase profile (pooled across episodes, bin0=touchdown "
              f"binN-1=liftoff): {json.dumps(phase_agg)}")

    report = {
        "checkpoint": str(args.checkpoint),
        "shim": args.shim,
        "deterministic": not args.stochastic,
        "dr_scale": args.dr_scale, "seed": args.seed,
        "episodes": eps,
        "knee_shift_rad_per_ep": knee_shift_probe,
        "medians": {k: med(k) for k in (
            "slip_center_per_m", "slip_material_per_m", "along_dist_m",
            "progress_ratio", "slip_center_m", "slip_material_m",
            "slip_lowF_m", "slip_highF_m", "slip_untracked_m")},
        "gait_valid_count": sum(1 for e in eps if e["gait_valid"]),
        "falls": sum(1 for e in eps if e["terminated"]),
        "phase_bins": args.phase_bins,
        "phase_profile_agg": phase_agg,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1))
    print(f"medians: {json.dumps(report['medians'])}")
    print(f"gait_valid {report['gait_valid_count']}/{len(eps)} "
          f"falls {report['falls']}  -> {args.out}")


if __name__ == "__main__":
    main()
