"""probe_joint_tracking.py — live-sim desired-vs-actual joint tracking
during a scripted combined (walk+turn) rollout, split pure-turn vs
combined ticks.

WHY (standwalk STATUS item 2, candidate (i) groundwork, 09-03): the
09-03 zero-training groundwork found the scripted teacher's own
combined-tick IK is always feasible (47mm min workspace margin) and
that BOTH pure-turn and combined regimes already saturate the
``safety.max_delta_q_deg`` slew clip ~2.5x over cap on raw per-tick
joint deltas -- which complicates (doesn't confirm) a pure
"vx+omega superposition formula is wrong" story, since a hard per-
joint clip should saturate similarly regardless of which two command
axes produced the raw delta. That prior check used the OPEN-LOOP
``desired_deg()`` trajectory only (`hexapod_core.tripod_gait`) -- it
never touched the live sim, so it could not tell whether the combined-
tick authority loss lives in:
  (a) the SafetyLayer clip removing MORE of the rotational component
      specifically on combined ticks (a translate+rotate raw target
      clips differently than a rotate-only one), or
  (b) actuator/physics tracking holding fine post-clip, with the real
      loss showing up downstream as stance-leg contact/slip physics.

WHAT THIS ADDS: drives the LIVE MuJoCo env (mesh/100Hz) with the exact
same scripted ``TripodGait`` teacher used by the BC anchor and by
``probe_turn_authority --policy scripted``, and at every walk-mode
tick records THREE joint vectors (rad, 18-dim logical yaw/hip/knee x6
order, matching ``desired_deg()``/``env._cmd``/``RobotState.
joint_position`` exactly -- see module docstring cross-refs):
  - ``desired``: the teacher's open-loop IK target for this tick
    (bit-identical to what ``probe_turn_authority --policy scripted``
    feeds in, since the action round-trips through
    ``q_rad_to_action``/``action_to_q_rad``)
  - ``cmd``     : ``env._cmd`` immediately after ``env.step()`` --
    the SAME-tick SafetyLayer output (post per-joint slew clip +
    joint-limit clamp), i.e. what actually gets sent to the servo
    profile / physics this tick.
  - ``actual``  : ``env._state.joint_position`` after physics has
    advanced this tick -- what the simulated actuator dynamics
    (``ServoProfile``, velocity/accel-limited) actually achieved.

Two gaps are reported, per joint AXIS (yaw/hip/knee) and overall,
split PURE-TURN (vx_cmd==0, wz_cmd!=0) vs COMBINED (both nonzero):
  - ``clip_gap`` = |desired - cmd|   (SafetyLayer's own contribution)
  - ``track_gap`` = |cmd - actual|   (actuator/physics tracking lag)
plus the fraction of ticks where a joint's clip is FULLY saturated
(|desired-cmd| within 1e-4 rad of max_dq, i.e. the raw delta demanded
more than the cap allowed).

Usage (mirrors probe_turn_authority's combined-scripted invocation):
  uv run python -m rl_move.sim.probe_joint_tracking \
      --cfg-set env.model_source=mesh --cfg-set control.hz=100 \
      --wz-cmds 0.25,-0.25 --vx-cmds 0.0,0.08 --seeds 0,1 \
      --out logs/ckpt_eval/joint_tracking_cap29_09-03.json
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent
for _p in (_PROTO, _PROTO / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.robot_state import DEG2RAD, RAD2DEG  # noqa: E402
from .joint_task import q_rad_to_action  # noqa: E402
from .probe_turn_authority import make_env, WALK_PLANT  # noqa: E402

_AXIS_NAMES = ("yaw", "hip", "knee")


def rollout(*, cfg_set: list[str] | None, wz_cmd: float, vx_cmd: float,
            seed: int, episode_seconds: float,
            yaw_arm_scale: float = 1.0,
            group_duty_skew: float = 0.0) -> dict:
    """``yaw_arm_scale`` (09-03, standwalk candidate (i)-v2): forwarded
    to ``TripodGait(combined_yaw_arm_scale=...)``; the combined-tick
    gate lives inside TripodGait itself. Default 1.0 is bit-exact.

    ``group_duty_skew`` (09-05, standwalk Next item 2(i) follow-up):
    forwarded to ``TripodGait(combined_group_duty_skew=...)`` -- lets
    this probe be run at the SAME dose as the zero-training scripted
    sweep that found combined-tick wz_med monotonically WORSE with
    |skew| (STATUS 09-05 ~06:1x), so the swing/stance split below can
    test the specific root-cause hypothesis that motivated it: does a
    group's NARROWED stance window pay back (in clip saturation) what
    its WIDENED swing window saved? Default 0.0 is bit-exact."""
    from hexapod_core.tripod_gait import TripodGait

    env = make_env(cfg_set, seed, episode_seconds)
    obs, info = env.reset()
    traj = env._goal_traj
    n = len(traj.vx)
    hold_n = ramp_n = int(round(1.0 / env.dt))
    traj.vx[:] = vx_cmd
    traj.vy[:] = 0.0
    traj.wz[:] = wz_cmd
    traj.vx[:hold_n] = 0.0
    traj.wz[:hold_n] = 0.0
    traj.vx[hold_n:hold_n + ramp_n] = np.linspace(0.0, vx_cmd, ramp_n)
    traj.wz[hold_n:hold_n + ramp_n] = np.linspace(0.0, wz_cmd, ramp_n)

    gait = TripodGait(vx=0.0, combined_yaw_arm_scale=yaw_arm_scale,
                       combined_group_duty_skew=group_duty_skew)
    gait.sync_plant_stance(*WALK_PLANT)
    gait.reset_phase()

    max_dq = float(env.safety.max_dq)  # rad, current cap (post any DR/ramp)
    clip_gaps: list[np.ndarray] = []
    track_gaps: list[np.ndarray] = []
    sat_flags: list[np.ndarray] = []
    swing_flags: list[np.ndarray] = []  # (6,) bool per tick, per-leg
    heavy_group_seen: int | None = None  # constant once combined+seen
    step = 0
    fell = False
    while True:
        cmd_wz = float(traj.wz[min(step, n - 1)])
        cmd_vx = float(traj.vx[min(step, n - 1)])
        t = step * env.dt
        gait.set_velocity(vx=cmd_vx, omega=cmd_wz)
        desired_rad = np.asarray(gait.desired_deg(t), dtype=float) * DEG2RAD
        leg_swing = np.asarray(gait.leg_swing_state(), dtype=bool)  # (6,)
        heavy_now = gait.heavy_group()  # constant post-ramp; see docstring
        if heavy_now is not None:
            heavy_group_seen = heavy_now
        act = q_rad_to_action(desired_rad)
        obs, r, term, trunc, info = env.step(act)
        gm = info.get("goal_mode")
        if step >= hold_n + ramp_n and gm == "walk":
            cmd_q = np.asarray(env._cmd, dtype=float).copy()
            actual_q = np.asarray(env._state.joint_position,
                                   dtype=float).copy()
            cg = np.abs(desired_rad - cmd_q)
            tg = np.abs(cmd_q - actual_q)
            clip_gaps.append(cg)
            track_gaps.append(tg)
            sat_flags.append((cg > (max_dq - 1e-4)).astype(float))
            swing_flags.append(leg_swing)
        step += 1
        if term:
            fell = True
        if term or trunc:
            break
    env.close()

    if not clip_gaps:
        return {"wz_cmd": wz_cmd, "vx_cmd": vx_cmd, "seed": seed,
                "n_ticks": 0, "fell": fell, "max_dq_rad": max_dq}

    cg_arr = np.stack(clip_gaps) * RAD2DEG   # (T, 18) deg
    tg_arr = np.stack(track_gaps) * RAD2DEG
    sat_arr = np.stack(sat_flags)            # (T, 18) 0/1
    # (T, 6) -> (T, 18), repeated 3x per leg to match the leg-major
    # [yaw0,hip0,knee0, yaw1,...] column layout above (standwalk item
    # 2(i) follow-up, 09-05): a leg's swing/stance status applies to
    # all three of ITS axis columns identically.
    swing18 = np.repeat(np.stack(swing_flags), 3, axis=1)  # (T, 18) bool
    # standwalk item 2(i) follow-up (09-05, second pass): the pooled
    # swing/stance split above mixes the "amplified-heavy" group's
    # (widened-swing/narrowed-stance) legs with the "light" group's
    # (narrowed-swing/widened-stance) legs -- a real per-group effect
    # in opposite directions can cancel in the pooled average. Build
    # the 4-way (heavy/light x swing/stance) split too, using the
    # STRUCTURAL group classification (constant for a fixed post-ramp
    # command; exists even at group_duty_skew=0.0 as a baseline).
    group_split = None
    if heavy_group_seen is not None:
        is_heavy_leg = np.array([1.0 if (i % 2) == heavy_group_seen else 0.0
                                  for i in range(6)])
        heavy18 = np.repeat(is_heavy_leg, 3).astype(bool)  # (18,) constant
        group_split = np.broadcast_to(heavy18, swing18.shape)  # (T, 18)

    def _axis_stats(arr: np.ndarray, mask18: np.ndarray | None = None) -> dict:
        out = {}
        for k, name in enumerate(_AXIS_NAMES):
            cols = arr[:, k::3]  # this axis, all 6 legs
            out[name] = {
                "med_deg": float(np.median(cols)),
                "p90_deg": float(np.percentile(cols, 90)),
            }
        out["all"] = {"med_deg": float(np.median(arr)),
                       "p90_deg": float(np.percentile(arr, 90))}
        if mask18 is not None:
            # standwalk item 2(i) follow-up (09-05): split by whether
            # THIS leg was swinging or stancing at THIS tick, so a
            # duty-skew dose's "swing gets easier" claim can be
            # checked against "stance gets harder" in the same units.
            for regime, m in (("swing", mask18), ("stance", ~mask18)):
                vals = arr[m]
                out[f"{regime}_all_med_deg"] = (
                    float(np.median(vals)) if vals.size else None)
            for k, name in enumerate(_AXIS_NAMES):
                cols = arr[:, k::3]
                cmask = mask18[:, k::3]
                sw = cols[cmask]
                st = cols[~cmask]
                out[name]["swing_med_deg"] = (
                    float(np.median(sw)) if sw.size else None)
                out[name]["stance_med_deg"] = (
                    float(np.median(st)) if st.size else None)
        return out

    def _sat_frac_split(sat: np.ndarray, mask18: np.ndarray) -> dict:
        per_axis = {}
        for k, name in enumerate(_AXIS_NAMES):
            cols = sat[:, k::3]
            cmask = mask18[:, k::3]
            sw = cols[cmask]
            st = cols[~cmask]
            per_axis[name] = {
                "swing": float(np.mean(sw)) if sw.size else None,
                "stance": float(np.mean(st)) if st.size else None,
            }
        per_axis["all"] = {
            "swing": float(np.mean(sat[mask18])) if mask18.any() else None,
            "stance": (float(np.mean(sat[~mask18]))
                       if (~mask18).any() else None),
        }
        return per_axis

    def _group_phase_bucket(cg: np.ndarray, sat: np.ndarray,
                             phase_mask: np.ndarray, group_mask: np.ndarray,
                             label: str) -> dict:
        """One (group, phase) quadrant -- standwalk item 2(i) follow-up
        (09-05, second pass): the decisive test of "does a group's
        narrowed stance pay back what its widened swing saved", read
        per-quadrant instead of pooled across both groups."""
        m = phase_mask & group_mask
        if not m.any():
            return {"label": label, "n_cells": 0, "clip_sat_frac": None,
                    "clip_gap_all_med_deg": None, "clip_gap_yaw_med_deg": None}
        yaw_m = m[:, 0::3]
        return {
            "label": label,
            "n_cells": int(m.sum()),
            "clip_sat_frac": float(np.mean(sat[m])),
            "clip_gap_all_med_deg": float(np.median(cg[m])),
            "clip_gap_yaw_med_deg": (float(np.median(cg[:, 0::3][yaw_m]))
                                     if yaw_m.any() else None),
        }

    group_phase_split = None
    if group_split is not None:
        heavy18 = group_split
        group_phase_split = {
            "heavy_swing": _group_phase_bucket(cg_arr, sat_arr, swing18,
                                                heavy18, "heavy_swing"),
            "heavy_stance": _group_phase_bucket(cg_arr, sat_arr, ~swing18,
                                                 heavy18, "heavy_stance"),
            "light_swing": _group_phase_bucket(cg_arr, sat_arr, swing18,
                                                ~heavy18, "light_swing"),
            "light_stance": _group_phase_bucket(cg_arr, sat_arr, ~swing18,
                                                 ~heavy18, "light_stance"),
        }

    return {
        "wz_cmd": wz_cmd,
        "vx_cmd": vx_cmd,
        "seed": seed,
        "n_ticks": int(cg_arr.shape[0]),
        "fell": fell,
        "max_dq_rad": max_dq,
        "max_dq_deg": max_dq * RAD2DEG,
        "group_duty_skew": group_duty_skew,
        "clip_gap": _axis_stats(cg_arr, swing18),
        "track_gap": _axis_stats(tg_arr, swing18),
        "clip_sat_frac": {
            name: float(np.mean(sat_arr[:, k::3]))
            for k, name in enumerate(_AXIS_NAMES)
        },
        "clip_sat_frac_all": float(np.mean(sat_arr)),
        "clip_sat_frac_swing_stance": _sat_frac_split(sat_arr, swing18),
        "swing_tick_frac_all": float(np.mean(swing18)),
        "heavy_group": heavy_group_seen,
        "group_phase_split": group_phase_split,
    }


def _safe_med(vals: list) -> float | None:
    """Median over non-None entries, or None if all are missing (e.g.
    an older cached result predating the swing/stance split, or a cell
    with zero swing OR zero stance ticks -- can't happen at skew=0
    since both regimes always have ticks, but a duty_skew near the
    +-0.45 clip could in principle starve one bucket)."""
    v = [x for x in vals if x is not None]
    return float(np.median(v)) if v else None


def summarize(results: list[dict]) -> dict:
    """Split pure-turn (vx_cmd==0) vs combined (vx_cmd!=0), report the
    clip-gap and track-gap medians per regime so the two are directly
    comparable -- if clip_gap grows a lot more on combined than
    pure-turn (esp. on 'yaw', the rotational axis) that supports
    hypothesis (a); if clip_gap is similar across regimes but the
    ACHIEVED wz/vx still differs (measured separately by
    probe_turn_authority), that points at (b) downstream physics."""
    def _bucket(regime_pred):
        rows = [r for r in results if regime_pred(r) and r.get("n_ticks", 0)]
        if not rows:
            return None
        return {
            "n_cells": len(rows),
            "clip_gap_all_med_deg": float(np.median(
                [r["clip_gap"]["all"]["med_deg"] for r in rows])),
            "clip_gap_yaw_med_deg": float(np.median(
                [r["clip_gap"]["yaw"]["med_deg"] for r in rows])),
            "clip_sat_frac_all": float(np.median(
                [r["clip_sat_frac_all"] for r in rows])),
            "clip_sat_frac_yaw": float(np.median(
                [r["clip_sat_frac"]["yaw"] for r in rows])),
            "track_gap_all_med_deg": float(np.median(
                [r["track_gap"]["all"]["med_deg"] for r in rows])),
            "track_gap_yaw_med_deg": float(np.median(
                [r["track_gap"]["yaw"]["med_deg"] for r in rows])),
            # standwalk item 2(i) follow-up (09-05): swing vs stance
            # split of clip saturation -- the direct test of "does a
            # narrowed stance window pay back what a widened swing
            # window saved" for a combined_group_duty_skew dose. Only
            # present when rows carry the split (older cached JSON
            # from before 09-05 lacks the key; guarded with .get).
            "clip_sat_frac_swing": _safe_med(
                [r.get("clip_sat_frac_swing_stance", {}).get("all", {})
                  .get("swing") for r in rows]),
            "clip_sat_frac_stance": _safe_med(
                [r.get("clip_sat_frac_swing_stance", {}).get("all", {})
                  .get("stance") for r in rows]),
            "clip_gap_swing_med_deg": _safe_med(
                [r.get("clip_gap", {}).get("swing_all_med_deg")
                 for r in rows]),
            "clip_gap_stance_med_deg": _safe_med(
                [r.get("clip_gap", {}).get("stance_all_med_deg")
                 for r in rows]),
            # standwalk item 2(i) follow-up (09-05, second pass): the
            # 4-way (structural heavy/light group x swing/stance)
            # split -- the decisive read, since the pooled swing/
            # stance split above can hide two groups moving in
            # opposite directions. Only meaningful for combined rows
            # (group_phase_split is None on pure-turn/uncombined rows).
            "group_phase_split_clip_sat": {
                bucket: _safe_med(
                    [r.get("group_phase_split", {}).get(bucket, {})
                      .get("clip_sat_frac")
                     for r in rows if r.get("group_phase_split")])
                for bucket in ("heavy_swing", "heavy_stance",
                                "light_swing", "light_stance")
            },
        }
    pure = _bucket(lambda r: abs(r["vx_cmd"]) < 1e-6 and abs(r["wz_cmd"]) > 1e-6)
    combined = _bucket(lambda r: abs(r["vx_cmd"]) > 1e-6 and abs(r["wz_cmd"]) > 1e-6)
    return {"pure_turn": pure, "combined": combined}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cfg-set", action="append", default=None)
    ap.add_argument("--wz-cmds", default="0.25,-0.25")
    ap.add_argument("--vx-cmds", default="0.0,0.08")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--yaw-arm-scale", type=float, default=1.0,
                    help="TripodGait combined_yaw_arm_scale (standwalk "
                         "candidate (i)-v2), combined ticks only; "
                         "default 1.0 is bit-exact")
    ap.add_argument("--group-duty-skew", type=float, default=0.0,
                    help="TripodGait combined_group_duty_skew (standwalk "
                         "Next item 2(i) follow-up, 09-05): splits clip "
                         "saturation by swing vs stance so a dose can be "
                         "checked for stance 'paying back' what swing "
                         "saves; default 0.0 is bit-exact")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    wz_cmds = [float(x) for x in args.wz_cmds.split(",") if x.strip()]
    vx_cmds = [float(x) for x in args.vx_cmds.split(",") if x.strip()]
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]

    results = []
    for wz_cmd in wz_cmds:
        for vx_cmd in vx_cmds:
            for seed in seeds:
                res = rollout(cfg_set=args.cfg_set, wz_cmd=wz_cmd,
                               vx_cmd=vx_cmd, seed=seed,
                               episode_seconds=args.episode_seconds,
                               yaw_arm_scale=args.yaw_arm_scale,
                               group_duty_skew=args.group_duty_skew)
                results.append(res)
                print(f"[probe_joint_tracking] wz={wz_cmd} vx={vx_cmd} "
                      f"seed={seed} n={res.get('n_ticks')} "
                      f"clip_gap_all_med_deg="
                      f"{res.get('clip_gap', {}).get('all', {}).get('med_deg')} "
                      f"clip_sat_frac_yaw="
                      f"{res.get('clip_sat_frac', {}).get('yaw')} "
                      f"clip_sat_swing/stance="
                      f"{res.get('clip_sat_frac_swing_stance', {}).get('all', {})} "
                      f"track_gap_all_med_deg="
                      f"{res.get('track_gap', {}).get('all', {}).get('med_deg')} "
                      f"fell={res.get('fell')}")

    summary = summarize(results)
    print(f"[probe_joint_tracking] SUMMARY pure_turn={summary['pure_turn']}")
    print(f"[probe_joint_tracking] SUMMARY combined ={summary['combined']}")

    out = {"summary": summary, "results": results}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, indent=2))
        print(f"[probe_joint_tracking] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
