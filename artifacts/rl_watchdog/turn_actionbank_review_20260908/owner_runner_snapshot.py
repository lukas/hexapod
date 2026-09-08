"""probe_action_response_bank.py — frozen per-joint action-impulse authority bank.

09-08 operator focus note (assisted steering action-authority diagnostic).
Runs the preregistered bank in artifacts/rl_watchdog/turn_actionbank_20260908/
prereg_spec.json (main repo): on the frozen yawref-cigate8m checkpoint and
frozen 4.80573 kg full-mesh plant, measure the REAL dynamic response
(integrated signed yaw, heading-frame forward displacement, loaded-foot slip,
safety/terminations) to +/-0.05 normalized-action pulses on each of the 18
action dims, 5 ticks then unchanged policy for 0.75 s, at two half-cycle-
separated settled states per (wz sign x start phase) cell. Every branch is an
identical fresh-construction reset + deterministic prefix replay (controller
hidden state + history preserved by replay); the zero-delta branch must match
the continuous baseline bit-exactly or the whole bank is invalid.

Diagnostic only: no training, no robot, no shared-code changes.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
import hashlib
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent
for _p in (_PROTO, _PROTO / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.sim import probe_turn_authority as pta  # noqa: E402
from rl_move.sim.eval_checkpoint import CONTACT_N, model_identity  # noqa: E402

PULSE_TICKS = 5
WINDOW_TICKS = 80          # 5 pulse + 75 follow = 0.80 s at 100 Hz
SETTLE_TICK = 600          # t = 6.0 s
P2_SEARCH = (25, 50)       # half cycle at 1.333333 Hz = 37.5 ticks
DELTA = 0.05

_MODEL_CACHE: dict = {}


def _get_model(ckpt: str):
    if ckpt not in _MODEL_CACHE:
        _MODEL_CACHE[ckpt] = pta._load_model(Path(ckpt))
    return _MODEL_CACHE[ckpt]


def _yaw_of(env) -> float:
    r = env.data.xmat[env._chassis_bid].reshape(3, 3)
    return math.atan2(r[1, 0], r[0, 0])


def _setup_traj(env, vx: float, wz: float) -> int:
    traj = env._goal_traj
    hold_n = ramp_n = int(round(1.0 / env.dt))
    traj.vx[:] = vx
    traj.vy[:] = 0.0
    traj.wz[:] = wz
    traj.vx[:hold_n] = 0.0
    traj.wz[:hold_n] = 0.0
    traj.vx[hold_n:hold_n + ramp_n] = np.linspace(0.0, vx, ramp_n)
    traj.wz[hold_n:hold_n + ramp_n] = np.linspace(0.0, wz, ramp_n)
    return hold_n + ramp_n


def _fresh_env(spec: dict, phase_offset: float, vx: float, wz: float):
    """Identical construction/reset path for baseline and every branch."""
    model, width = _get_model(spec["checkpoint"])
    env = pta.make_env(spec["cfg_set"], spec["seed"], spec["episode_seconds"])
    n_env = int(env.observation_space.shape[0])
    mode_onehot = False
    if width != n_env:
        from rl_move.sim.walk_task import N_MODE_OBS
        if width == n_env + N_MODE_OBS:
            env.close()
            mode_onehot = True
            env = pta.make_env(spec["cfg_set"], spec["seed"],
                               spec["episode_seconds"], mode_onehot=True)
        else:
            raise SystemExit(f"obs width mismatch: ckpt {width} env {n_env}")
    obs, _ = env.reset()
    if hasattr(model, "reset"):
        model.reset()
    if phase_offset != 0.0:
        env._phase = float(phase_offset) % (2.0 * math.pi)
    _setup_traj(env, vx, wz)
    return env, model, obs, mode_onehot


def _rollout(spec: dict, *, vx: float, wz: float, phase_offset: float,
             n_ticks: int, pulse_tick: int | None = None,
             pulse_joint: int | None = None, pulse_delta: float = 0.0,
             identity_out: dict | None = None,
             record_qpos: bool = False) -> dict:
    env, model, obs, mode_onehot = _fresh_env(spec, phase_offset, vx, wz)
    if identity_out is not None:
        ident = model_identity(env)
        req = spec["required_identity"]
        for k, v in req.items():
            got = ident[k]
            ok = (abs(got - v) < 1e-6) if isinstance(v, float) else (got == v)
            if not ok:
                env.close()
                raise SystemExit(f"identity mismatch {k}: {got} != {v}")
        if abs(env.dt - 0.01) > 1e-12:
            env.close()
            raise SystemExit(f"dt {env.dt} != 0.01")
        identity_out.update(ident)
        identity_out["mode_onehot"] = mode_onehot
        identity_out["max_dq_rad_per_tick"] = float(env.safety.max_dq)
        prm = getattr(env, "_params", None) or getattr(env, "params", None)
        if prm is not None:
            identity_out["servo_params"] = {
                k: float(getattr(prm, k)) for k in
                ("speed_counts_s", "vel_max_deg_s") if hasattr(prm, k)}
    lo = np.asarray(env.action_space.low, dtype=np.float32)
    hi = np.asarray(env.action_space.high, dtype=np.float32)
    yaws, xys, vxs, phases, modes = [], [], [], [], []
    contacts, pad_xy, rolls, pitches = [], [], [], []
    qpos_all: list[np.ndarray] = []
    clip_hits = 0
    fell, term_reason, term_tick = False, "", None
    try:
        for step in range(n_ticks):
            act, _ = model.predict(obs, deterministic=True)
            if (pulse_tick is not None and pulse_joint is not None
                    and pulse_tick <= step < pulse_tick + PULSE_TICKS):
                act = np.asarray(act, dtype=np.float32).copy()
                raw = float(act[pulse_joint]) + pulse_delta
                act[pulse_joint] = np.clip(raw, lo[pulse_joint],
                                           hi[pulse_joint])
                if abs(act[pulse_joint] - raw) > 1e-9:
                    clip_hits += 1
            obs, r, term, trunc, info = env.step(act)
            yaws.append(_yaw_of(env))
            xys.append(np.asarray(
                env.data.xpos[env._chassis_bid, :2], dtype=float).copy())
            vxs.append(float(env._body_vel_xy()[0]))
            phases.append(float(env._phase))
            modes.append(info.get("goal_mode"))
            contacts.append([float(env.data.sensordata[a]) > CONTACT_N
                             for a in env._touch_adr])
            pad_xy.append(np.asarray(
                env.data.xpos[env._pad_bids, :2], dtype=float).copy())
            rolls.append(float(info.get("roll_rel_deg") or 0.0))
            pitches.append(float(info.get("pitch_rel_deg") or 0.0))
            if record_qpos:
                qpos_all.append(np.asarray(env.data.qpos, dtype=float).copy())
            if term:
                fell = True
                term_reason = str(info.get("termination_reason", ""))
                term_tick = step
            if term or trunc:
                break
        final_qpos = np.asarray(env.data.qpos, dtype=float).copy()
    finally:
        env.close()
    return {
        "yaw": np.unwrap(np.asarray(yaws)), "xy": np.asarray(xys),
        "vx": np.asarray(vxs), "phase": np.asarray(phases), "modes": modes,
        "contact": np.asarray(contacts, dtype=bool),
        "pad_xy": np.asarray(pad_xy),
        "roll": np.asarray(rolls), "pitch": np.asarray(pitches),
        "fell": fell, "term_reason": term_reason, "term_tick": term_tick,
        "n_ticks_done": len(yaws), "clip_hits": clip_hits,
        "final_qpos": final_qpos, "qpos_all": qpos_all,
    }


def _window_metrics(tr: dict, p: int) -> dict:
    """Score the 80-tick window starting at branch tick p (0-based ticks).

    Tick arrays index post-step states; state at the branch point is index
    p-1 (end of prefix). Window covers post-step states p .. p+79.
    """
    end = min(p + WINDOW_TICKS, tr["n_ticks_done"])
    yaw0 = tr["yaw"][p - 1]
    xy0 = tr["xy"][p - 1]
    heading = np.array([math.cos(yaw0), math.sin(yaw0)])
    lateral = np.array([-heading[1], heading[0]])
    if end <= p - 1:
        return {"invalid": "terminated before window start"}
    d = tr["xy"][end - 1] - xy0
    seg_pads = tr["pad_xy"][p - 1:end]
    seg_con = tr["contact"][p - 1:end]
    step_slip = (np.linalg.norm(np.diff(seg_pads, axis=0), axis=2)
                 * seg_con[:-1]).sum()
    term_in = (tr["term_tick"] is not None and p - 1 <= tr["term_tick"] < end)
    return {
        "d_yaw_rad": float(tr["yaw"][end - 1] - yaw0),
        "fwd_disp_m": float(d @ heading),
        "lat_disp_m": float(d @ lateral),
        "loaded_slip_m": float(step_slip),
        "mean_wz": float(np.mean(np.diff(tr["yaw"][p - 1:end]) / 0.01))
        if end - p >= 1 else None,
        "max_abs_roll_deg": float(np.max(np.abs(tr["roll"][p - 1:end]))),
        "max_abs_pitch_deg": float(np.max(np.abs(tr["pitch"][p - 1:end]))),
        "nonwalk_ticks": int(sum(m != "walk" for m in tr["modes"][p - 1:end])),
        "terminated_in_window": bool(term_in),
        "term_reason": tr["term_reason"] if term_in else "",
        "window_ticks": int(end - (p - 1)),
        "phase_at_branch": float(tr["phase"][p - 1]),
    }


def _window_hash(tr: dict, p: int) -> str:
    end = min(p + WINDOW_TICKS, tr["n_ticks_done"])
    h = hashlib.sha256()
    for arr in (tr["yaw"][p - 1:end], tr["xy"][p - 1:end],
                tr["pad_xy"][p - 1:end],
                tr["contact"][p - 1:end].astype(np.uint8)):
        h.update(np.ascontiguousarray(arr).tobytes())
    return h.hexdigest()


def _branch_task(args):
    spec, cell, p, joint, sign = args
    t0 = time.time()
    delta = 0.0 if joint is None else sign * DELTA
    tr = _rollout(spec, vx=cell["vx"], wz=cell["wz"],
                  phase_offset=cell["phase_offset"], n_ticks=p + WINDOW_TICKS,
                  pulse_tick=None if joint is None else p,
                  pulse_joint=joint, pulse_delta=delta)
    m = _window_metrics(tr, p)
    return {
        "cell": {k: cell[k] for k in ("vx", "wz", "phase_offset")},
        "branch_tick": p, "joint": joint, "pulse_delta": delta,
        "clip_hits": tr["clip_hits"],
        "metrics": m,
        "window_hash": _window_hash(tr, p),
        "final_qpos_sha256": hashlib.sha256(
            np.ascontiguousarray(tr["final_qpos"]).tobytes()).hexdigest(),
        "final_qpos": tr["final_qpos"].tolist(),
        "wall_s": round(time.time() - t0, 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True, type=Path,
                    help="preregistered spec JSON (read-only)")
    ap.add_argument("--checkpoint", required=True, type=Path)
    ap.add_argument("--cfg-json", required=True, type=Path,
                    help="JSON list of cfg_set strings (frozen training cfg)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--smoke", action="store_true",
                    help="one cell, zero branch + 2 pulses only")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out / "bank.json").exists():
        raise SystemExit("Refusing to replace an existing completed bank")
    prereg = json.loads(args.spec.read_text())
    ck_sha = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    if ck_sha != prereg["frozen_assets"]["checkpoint_sha256"]:
        raise SystemExit(f"checkpoint sha mismatch: {ck_sha}")
    xml = _PROTO / "mesh_mujoco" / "hexapod_mesh.xml"
    xml_sha = hashlib.sha256(xml.read_bytes()).hexdigest()
    if xml_sha != prereg["frozen_assets"]["full_mesh_xml_sha256"]:
        raise SystemExit(f"mesh xml sha mismatch: {xml_sha}")
    spec = {
        "checkpoint": str(args.checkpoint),
        "cfg_set": json.loads(args.cfg_json.read_text()),
        "seed": prereg["design"]["seed"],
        "episode_seconds": prereg["design"]["episode_seconds"],
        "required_identity": prereg["frozen_assets"]["required_identity"],
    }
    cells = []
    for c in prereg["design"]["cells"]:
        for ph in prereg["design"]["starts_phase_offset"]:
            cells.append({"vx": c["vx"], "wz": c["wz"], "phase_offset": ph})
    if args.smoke:
        cells = cells[:1]
    t_start = time.time()
    baselines, identity = [], {}
    for cell in cells:
        ident = identity if not identity else None
        tr = _rollout(spec, vx=cell["vx"], wz=cell["wz"],
                      phase_offset=cell["phase_offset"],
                      n_ticks=SETTLE_TICK + P2_SEARCH[1] + WINDOW_TICKS,
                      identity_out=ident, record_qpos=True)
        if tr["fell"]:
            raise SystemExit(f"baseline fell in cell {cell}: "
                             f"{tr['term_reason']} @ {tr['term_tick']}")
        # P1: first tick index >= SETTLE_TICK with walk mode (branch tick p
        # means prefix of p ticks; state index p-1). P2 by phase.
        p1 = next(i + 1 for i in range(SETTLE_TICK - 1, tr["n_ticks_done"])
                  if tr["modes"][i] == "walk")
        ph1 = tr["phase"][p1 - 1]
        target = (ph1 + math.pi) % (2 * math.pi)
        cands = range(p1 + P2_SEARCH[0], p1 + P2_SEARCH[1] + 1)
        p2 = min(cands, key=lambda q: abs(
            (tr["phase"][q - 1] - target + math.pi) % (2 * math.pi) - math.pi))
        base = {"cell": cell, "p1": p1, "p2": p2,
                "phase_p1": float(tr["phase"][p1 - 1]),
                "phase_p2": float(tr["phase"][p2 - 1]),
                "trace": tr}
        for p in (p1, p2):
            base[f"metrics_{p}"] = _window_metrics(tr, p)
            base[f"hash_{p}"] = _window_hash(tr, p)
        baselines.append(base)
        print(f"baseline cell {cell}: p1={p1} p2={p2} "
              f"phases {base['phase_p1']:.3f}/{base['phase_p2']:.3f} "
              f"yaw80@p1={base[f'metrics_{p1}']['d_yaw_rad']:.4f}",
              flush=True)
    # Baseline final-qpos references for exactness: re-run baseline cells as
    # length-limited rollouts so zero-branch final qpos is comparable.
    tasks = []
    for base in baselines:
        cell = base["cell"]
        for p in (base["p1"], base["p2"]):
            tasks.append((spec, cell, p, None, 0))          # zero branch
            joints = range(2) if args.smoke else range(18)
            for j in joints:
                for s in (+1, -1):
                    tasks.append((spec, cell, p, j, s))
    print(f"{len(tasks)} branch tasks on {args.workers} workers", flush=True)
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, res in enumerate(ex.map(_branch_task, tasks, chunksize=1)):
            results.append(res)
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{len(tasks)} done "
                      f"({time.time() - t_start:.0f}s)", flush=True)
    # Exactness gate: zero branches vs continuous baseline window hash.
    exact = []
    for base in baselines:
        for p in (base["p1"], base["p2"]):
            zb = next(r for r in results
                      if r["cell"] == {k: base["cell"][k] for k in
                                       ("vx", "wz", "phase_offset")}
                      and r["branch_tick"] == p and r["joint"] is None)
            base_qpos = base["trace"]["qpos_all"][p + WINDOW_TICKS - 1]
            qpos_ok = (np.asarray(zb["final_qpos"]) == base_qpos).all()
            ok = zb["window_hash"] == base[f"hash_{p}"] and qpos_ok
            exact.append({"cell": zb["cell"], "p": p, "match": bool(ok),
                          "qpos_bitexact": bool(qpos_ok),
                          "baseline_hash": base[f"hash_{p}"],
                          "zero_branch_hash": zb["window_hash"]})
    all_exact = all(e["match"] for e in exact)
    out = {
        "schema": "hexapod.action_response_bank.v1",
        "prereg_spec_sha256": hashlib.sha256(
            args.spec.read_bytes()).hexdigest(),
        "checkpoint_sha256": ck_sha, "mesh_xml_sha256": xml_sha,
        "identity": identity,
        "smoke": bool(args.smoke),
        "wall_s": round(time.time() - t_start, 1),
        "exactness": {"all_match": all_exact, "detail": exact},
        "baselines": [{k: v for k, v in b.items() if k != "trace"}
                      for b in baselines],
        "branches": results,
    }
    (args.out / "bank.json").write_text(json.dumps(out, indent=1))
    print(f"EXACTNESS {'PASS' if all_exact else 'FAIL'}; "
          f"wrote {args.out / 'bank.json'} in {out['wall_s']}s", flush=True)
    if not all_exact:
        sys.exit(3)


if __name__ == "__main__":
    main()
