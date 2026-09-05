"""eval_command_envelope.py — paired CPU scripted-gait evaluation of the
opt-in measured-feasibility command governor (``command_envelope.py``).

todaypolicy hardware-delivery item (operator MCP note
fb_20260905T071610_749846, 09-05). Runs the SAME scripted ``TripodGait``
teacher through the live mesh/100 Hz MuJoCo env under a suite of
stepped joystick command scripts, once per arm with IDENTICAL seeds:

  - ``baseline``      : requested commands go straight to
                        ``gait.set_velocity`` (the legacy path, incl.
                        TripodGait's own tau=0.15 smoothing) — the
                        pure-turn and straight-line baselines the
                        operator note says to retain.
  - ``env_shared``    : CommandEnvelope, mode='shared' (all axes share
                        one authority scalar; path curvature kept).
  - ``env_yawpri``    : CommandEnvelope, mode='yaw_priority' (only
                        translation demand is shed; yaw passes intact).

HONESTY CONTRACT: requested and applied commands are recorded
SEPARATELY every tick (traces/*.npz keeps both full histories) and all
tracking/progress scores are computed against the ORIGINAL requested
script — an envelope that throttles or parks scores WORSE on
progress/tracking, never better. Slip is additionally reported per
achieved meter so lower demand cannot silently launder slip either.

Scenarios (each starts with a 1 s zero-command settle):
  pure translations (fwd/rev/lat), pure turns (ccw/cw), combined
  vx=0.08 & wz=+/-0.25, stop/restart, forward->reverse reversal, and a
  yaw sign reversal — the exact list in the operator note.

Metrics per rollout: progress ratio vs requested, per-axis
requested-vs-applied authority, per-axis achieved-vs-REQUESTED
tracking error (full + steady windows), actual yaw course error, slip
(per commanded m, BML convention, and per achieved m), slew-clip
saturation (all / yaw axis / peak ratio), support (mean feet in
contact, frac ticks <3), falls, and applied-command continuity.

CPU-only, zero PPO. Nothing here changes any shared default: the env,
safety limits (``safety.max_delta_q_deg`` untouched), gait, and
checkpoint contracts are all read-only inputs.

Usage (controller pod, ~40 rollouts, run backgrounded):
  uv run python -m rl_move.sim.eval_command_envelope \
      --out-dir logs/ckpt_eval/command_envelope_v1_09-05
Smoke: add ``--quick`` (one scenario, 3 s, 1 seed).
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
import time
from collections import Counter
from pathlib import Path

import numpy as np

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent
for _p in (_PROTO, _PROTO / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.robot_state import DEG2RAD  # noqa: E402
from .command_envelope import CommandEnvelope, EnvelopeConfig  # noqa: E402
from .joint_task import q_rad_to_action  # noqa: E402
# Reuse the exact env constructor + plant pose the existing scripted
# probes use (probe_turn_authority / probe_joint_tracking) so numbers
# are comparable across tools.
from .probe_turn_authority import WALK_PLANT, make_env  # noqa: E402

RAD2DEG = 180.0 / math.pi
DEFAULT_CFG_SET = ["env.model_source=mesh", "control.hz=100"]
# Loaded-foot slip's rotation-as-speed proxy — same constant/convention
# as build_motion_library.py so slip/m stays comparable to the
# teacher's measured 1.4-2.9 band.
TURN_RADIUS_APPROX_M = 0.115
SLIP_METRIC_VERSION = "commanded_intervals_v2_stop_history_advanced"

# Each scenario: (duration_s, [(t_start, vx, vy, wz), ...]); segments
# hold until the next boundary. All start with a 1 s zero settle.
SCENARIOS: dict[str, tuple[float, list[tuple[float, float, float, float]]]] = {
    "fwd": (11.0, [(0.0, 0.0, 0.0, 0.0), (1.0, 0.08, 0.0, 0.0)]),
    "rev": (11.0, [(0.0, 0.0, 0.0, 0.0), (1.0, -0.08, 0.0, 0.0)]),
    "lat": (11.0, [(0.0, 0.0, 0.0, 0.0), (1.0, 0.0, 0.08, 0.0)]),
    "turn_ccw": (11.0, [(0.0, 0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.25)]),
    "turn_cw": (11.0, [(0.0, 0.0, 0.0, 0.0), (1.0, 0.0, 0.0, -0.25)]),
    "combo_ccw": (11.0, [(0.0, 0.0, 0.0, 0.0), (1.0, 0.08, 0.0, 0.25)]),
    "combo_cw": (11.0, [(0.0, 0.0, 0.0, 0.0), (1.0, 0.08, 0.0, -0.25)]),
    "stop_restart": (11.0, [(0.0, 0.0, 0.0, 0.0), (1.0, 0.08, 0.0, 0.0),
                            (5.0, 0.0, 0.0, 0.0), (7.0, 0.08, 0.0, 0.0)]),
    "rev_fwdrev": (11.0, [(0.0, 0.0, 0.0, 0.0), (1.0, 0.08, 0.0, 0.0),
                          (6.0, -0.08, 0.0, 0.0)]),
    "rev_yaw": (11.0, [(0.0, 0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.25),
                       (6.0, 0.0, 0.0, -0.25)]),
}

ARMS = ("baseline", "env_shared", "env_yawpri")


def command_at(segments: list[tuple[float, float, float, float]],
               t: float) -> tuple[float, float, float]:
    """Requested (vx, vy, wz) at time t: last segment whose start <= t."""
    cmd = (0.0, 0.0, 0.0)
    for t0, vx, vy, wz in segments:
        if t >= t0 - 1e-9:
            cmd = (vx, vy, wz)
        else:
            break
    return cmd


def _envelope_for_arm(arm: str) -> CommandEnvelope | None:
    if arm == "baseline":
        return None
    mode = {"env_shared": "shared", "env_yawpri": "yaw_priority"}[arm]
    return CommandEnvelope(EnvelopeConfig(enabled=True, mode=mode))


def _quat_yaw(q: np.ndarray) -> float:
    return math.atan2(2.0 * (q[0] * q[3] + q[1] * q[2]),
                      1.0 - 2.0 * (q[2] * q[2] + q[3] * q[3]))


def run_scenario(*, name: str, seed: int, arm: str,
                 cfg_set: list[str] | None = None,
                 duration_s: float | None = None,
                 trace_dir: Path | None = None) -> dict:
    from hexapod_core.tripod_gait import TripodGait

    dur, segments = SCENARIOS[name]
    if duration_s is not None:
        dur = float(duration_s)
    env = make_env(cfg_set if cfg_set is not None else list(DEFAULT_CFG_SET),
                   seed, dur)
    obs, info = env.reset()
    # Mirror the requested script into the env's own goal trajectory so
    # any goal-conditioned env internals see the same demand in every
    # arm (identical across arms; the gait gets its commands directly).
    traj = env._goal_traj
    n = len(traj.vx)
    if traj.wz is None:
        # Default walk cfg carries no yaw channel (goal wz_max=0 ->
        # traj.wz None); materialize one so the env's goal mirrors the
        # requested script identically in every arm. WalkTrajectory
        # reads it through `is not None` guards, so this is safe.
        traj.wz = np.zeros(n)
    for k in range(n):
        vx, vy, wz = command_at(segments, k * env.dt)
        traj.vx[k] = vx
        traj.vy[k] = vy
        traj.wz[k] = wz

    gait = TripodGait(vx=0.0)
    gait.sync_plant_stance(*WALK_PLANT)
    gait.reset_phase()
    envlp = _envelope_for_arm(arm)

    max_dq = float(env.safety.max_dq)
    rows: dict[str, list] = {k: [] for k in (
        "t", "req", "applied", "authority", "body_v", "wz", "yaw",
        "sat_frac", "sat_frac_yaw", "peak_ratio", "n_contact", "walk")}
    prev_sat: float | None = None
    prev_on = [False] * 6
    prev_xy: list[np.ndarray | None] = [None] * 6
    slip_m = 0.0
    cmd_prog_m = 0.0   # commanded-progress denominator (BML convention)
    fell = False
    modes: list[str] = []
    step = 0
    while True:
        t = step * env.dt
        req = command_at(segments, t)
        if envlp is None:
            applied = req
            authority = 1.0
        else:
            out = envlp.step(env.dt, req, prev_sat)
            applied = out.applied
            authority = out.authority
        gait.set_velocity(vx=applied[0], vy=applied[1], omega=applied[2])
        desired_rad = np.asarray(gait.desired_deg(t), dtype=float) * DEG2RAD
        prev_cmd = getattr(env, "_cmd", None)
        prev_cmd = (np.asarray(prev_cmd, dtype=float).copy()
                    if prev_cmd is not None
                    else np.asarray(env._state.joint_position, dtype=float).copy())
        act = q_rad_to_action(desired_rad)
        obs, r, term, trunc, info = env.step(act)
        cmd_q = np.asarray(env._cmd, dtype=float).copy()
        cg = np.abs(desired_rad - cmd_q)
        sat = (cg > (max_dq - 1e-4))
        sat_frac = float(np.mean(sat))
        prev_sat = sat_frac
        raw_dq = np.abs(desired_rad - prev_cmd)
        peak_ratio = float(np.max(raw_dq) / max_dq) if max_dq > 0 else 0.0
        gm = info.get("goal_mode")
        modes.append(gm)

        quat = env.data.xquat[env._chassis_bid].copy()
        bv = env._body_vel_xy()
        n_on = 0
        s_cmd = math.hypot(req[0], req[1]) + abs(req[2]) * TURN_RADIUS_APPROX_M
        for f in range(6):
            adr = env._touch_adr[f]
            on = bool(adr >= 0 and env.data.sensordata[adr] > 0.5)
            n_on += int(on)
            xy_world = env.data.xpos[env._pad_bids[f], :2].copy()
            if s_cmd > 1e-3:
                if prev_on[f] and prev_xy[f] is not None:
                    slip_m += float(np.linalg.norm(xy_world - prev_xy[f]))
            # Advance history even while requested velocity is zero. Holding
            # it through a stop falsely charges all unscored stop displacement
            # to the first commanded restart interval.
            prev_xy[f] = xy_world.copy()
            prev_on[f] = on
        if s_cmd > 1e-3:
            cmd_prog_m += s_cmd * env.dt

        rows["t"].append(t)
        rows["req"].append(req)
        rows["applied"].append(tuple(applied))
        rows["authority"].append(authority)
        rows["body_v"].append((float(bv[0]), float(bv[1])))
        rows["wz"].append(float(env._body_wz()))
        rows["yaw"].append(_quat_yaw(quat))
        rows["sat_frac"].append(sat_frac)
        rows["sat_frac_yaw"].append(float(np.mean(sat[0::3])))
        rows["peak_ratio"].append(peak_ratio)
        rows["n_contact"].append(n_on)
        rows["walk"].append(1.0 if gm == "walk" else 0.0)
        step += 1
        if term:
            fell = True
        if term or trunc:
            break
    env.close()

    traces = {k: np.asarray(v, dtype=float) for k, v in rows.items()
              if k != "t"}
    traces["t"] = np.asarray(rows["t"], dtype=float)
    metrics = score_traces(traces, dt=env.dt, segments=segments,
                           slip_m=slip_m, cmd_prog_m=cmd_prog_m, fell=fell)
    metrics.update({"scenario": name, "seed": seed, "arm": arm,
                    "modes": dict(Counter(modes)),
                    "max_dq_deg": max_dq * RAD2DEG})
    if trace_dir is not None:
        trace_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(trace_dir / f"{name}_s{seed}_{arm}.npz", **traces)
    return metrics


def score_traces(traces: dict, *, dt: float,
                 segments: list[tuple[float, float, float, float]],
                 slip_m: float, cmd_prog_m: float, fell: bool,
                 t_score_start: float = 1.0,
                 steady_settle_s: float = 1.5) -> dict:
    """Pure scoring math (unit-testable without MuJoCo). All tracking/
    progress terms are vs the ORIGINAL requested commands in
    ``traces['req']`` — never vs applied."""
    t = traces["t"]
    req = traces["req"]
    applied = traces["applied"]
    body_v = traces["body_v"]
    wz = traces["wz"]
    yaw = np.unwrap(traces["yaw"])
    walk = traces["walk"].astype(bool)
    T = len(t)
    score = (t >= t_score_start - 1e-9) & walk
    steady = score.copy()
    for t0, *_cmd in segments:
        steady &= ~((t >= t0 - 1e-9) & (t < t0 + steady_settle_s - 1e-9))

    def _axis_err(ach: np.ndarray, ref: np.ndarray, m: np.ndarray):
        if not m.any():
            return None
        return float(np.median(np.abs(ach[m] - ref[m])))

    achieved = {"vx": body_v[:, 0], "vy": body_v[:, 1], "wz": wz}
    out: dict = {"fell": bool(fell), "n_ticks": int(T),
                 "slip_metric_version": SLIP_METRIC_VERSION,
                 "n_score_ticks": int(score.sum()),
                 "n_steady_ticks": int(steady.sum())}
    for i, ax in enumerate(("vx", "vy", "wz")):
        r = req[:, i]
        a = applied[:, i]
        active = score & (np.abs(r) > 1e-6)
        out[f"{ax}_err_med_full"] = _axis_err(achieved[ax], r, score)
        out[f"{ax}_err_med_steady"] = _axis_err(achieved[ax], r, steady)
        out[f"{ax}_req_med_active"] = (float(np.median(np.abs(r[active])))
                                       if active.any() else None)
        out[f"{ax}_ach_med_active"] = (
            float(np.median(achieved[ax][steady & (np.abs(r) > 1e-6)]))
            if (steady & (np.abs(r) > 1e-6)).any() else None)
        # requested-vs-applied authority: how much of the ORIGINAL
        # demand the governor actually forwarded (1.0 = everything).
        if active.any():
            ratio = np.abs(a[active]) / np.abs(r[active])
            out[f"{ax}_authority_med"] = float(np.median(ratio))
            out[f"{ax}_authority_min"] = float(np.min(ratio))
        else:
            out[f"{ax}_authority_med"] = None
            out[f"{ax}_authority_min"] = None

    # Translation progress vs request: achieved body-frame velocity
    # projected on the requested unit direction, integrated, over the
    # requested distance. Parking -> ratio ~0; drifting sideways earns
    # nothing.
    v_req_mag = np.hypot(req[:, 0], req[:, 1])
    m_tr = score & (v_req_mag > 1e-6)
    if m_tr.any():
        u = req[m_tr, :2] / v_req_mag[m_tr, None]
        along = np.sum((body_v[m_tr] * u).sum(axis=1) * dt)
        req_dist = float(np.sum(v_req_mag[m_tr]) * dt)
        out["progress_along_m"] = float(along)
        out["progress_req_m"] = req_dist
        out["progress_ratio"] = float(along / req_dist) if req_dist > 1e-6 else None
    else:
        out["progress_along_m"] = None
        out["progress_req_m"] = None
        out["progress_ratio"] = None

    # Yaw course vs request (integral of requested wz over the scoring
    # window vs actual yaw change over the same ticks).
    if score.any():
        idx = np.where(score)[0]
        req_yaw = float(np.sum(req[idx, 2]) * dt)
        act_yaw = float(yaw[idx[-1]] - yaw[idx[0]])
        out["yaw_req_deg"] = req_yaw * RAD2DEG
        out["yaw_act_deg"] = act_yaw * RAD2DEG
        out["course_err_final_deg"] = (act_yaw - req_yaw) * RAD2DEG
        out["yaw_ratio"] = (float(act_yaw / req_yaw)
                            if abs(req_yaw) > math.radians(5.0) else None)
    else:
        out["yaw_req_deg"] = out["yaw_act_deg"] = None
        out["course_err_final_deg"] = out["yaw_ratio"] = None

    out["slip_m"] = float(slip_m)
    out["slip_per_cmd_m"] = float(slip_m / max(cmd_prog_m, 0.05))
    ach_dist = (abs(out["progress_along_m"])
                if out["progress_along_m"] is not None else 0.0)
    # add rotation proxy so pure turns keep a meaningful denominator
    if score.any():
        ach_dist += abs(float(np.sum(wz[score]) * dt)) * TURN_RADIUS_APPROX_M
    out["slip_per_ach_m"] = float(slip_m / max(ach_dist, 0.05))

    for key in ("sat_frac", "sat_frac_yaw", "peak_ratio"):
        vals = traces[key][score]
        out[f"{key}_mean"] = float(np.mean(vals)) if vals.size else None
    nc = traces["n_contact"][score]
    out["contact_mean"] = float(np.mean(nc)) if nc.size else None
    out["support_lt3_frac"] = float(np.mean(nc < 3)) if nc.size else None

    d_applied = np.abs(np.diff(applied, axis=0))
    out["applied_step_max"] = {ax: float(np.max(d_applied[:, i]))
                               if T > 1 else 0.0
                               for i, ax in enumerate(("vx", "vy", "wz"))}
    out["authority_min_seen"] = float(np.min(traces["authority"]))
    return out


HEADLINE = ("progress_ratio", "vx_err_med_steady", "wz_err_med_steady",
            "course_err_final_deg", "slip_per_cmd_m", "slip_per_ach_m",
            "sat_frac_mean", "sat_frac_yaw_mean", "support_lt3_frac",
            "fell")


def pair_deltas(results: list[dict]) -> list[dict]:
    """envelope-arm minus baseline for headline metrics, per
    (scenario, seed)."""
    base = {(r["scenario"], r["seed"]): r for r in results
            if r["arm"] == "baseline"}
    out = []
    for r in results:
        if r["arm"] == "baseline":
            continue
        b = base.get((r["scenario"], r["seed"]))
        if b is None:
            continue
        row = {"scenario": r["scenario"], "seed": r["seed"], "arm": r["arm"]}
        for k in HEADLINE:
            rv, bv = r.get(k), b.get(k)
            if isinstance(rv, (int, float)) and isinstance(bv, (int, float)):
                row[k] = {"base": bv, "cand": rv, "delta": rv - bv}
        out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cfg-set", action="append", default=None,
                    help=f"default: {DEFAULT_CFG_SET}")
    ap.add_argument("--scenarios", default=",".join(SCENARIOS),
                    help="comma-separated subset")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--quick", action="store_true",
                    help="smoke: fwd+combo_ccw only, 4 s, seed 0")
    args = ap.parse_args()

    scenarios = [s for s in args.scenarios.split(",") if s.strip()]
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    arms = [a for a in args.arms.split(",") if a.strip()]
    duration = None
    if args.quick:
        scenarios = ["fwd", "combo_ccw"]
        seeds = [0]
        duration = 4.0
    for s in scenarios:
        if s not in SCENARIOS:
            raise SystemExit(f"unknown scenario {s!r}")
    for a in arms:
        if a not in ARMS:
            raise SystemExit(f"unknown arm {a!r}")

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    trace_dir = out_dir / "traces"
    results = []
    t0 = time.time()
    for name in scenarios:
        for seed in seeds:
            for arm in arms:
                r = run_scenario(name=name, seed=seed, arm=arm,
                                 cfg_set=args.cfg_set, duration_s=duration,
                                 trace_dir=trace_dir)
                results.append(r)
                print(f"[{time.time()-t0:7.1f}s] {name} s{seed} {arm}: "
                      f"prog={r.get('progress_ratio')} "
                      f"wz_err={r.get('wz_err_med_steady')} "
                      f"sat={r.get('sat_frac_mean')} fell={r['fell']}",
                      flush=True)
    summary = {
        "cfg_set": args.cfg_set or DEFAULT_CFG_SET,
        "envelope_defaults": vars(EnvelopeConfig(enabled=True)),
        "scenarios": scenarios, "seeds": seeds, "arms": arms,
        "results": results,
        "paired_deltas": pair_deltas(results),
        "elapsed_s": time.time() - t0,
    }
    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=1, default=str)
    print(f"wrote {out_dir}/summary.json "
          f"({len(results)} rollouts, {time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
