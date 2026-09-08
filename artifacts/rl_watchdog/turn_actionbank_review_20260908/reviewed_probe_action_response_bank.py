"""probe_action_response_bank.py — frozen per-joint action-impulse authority bank.

09-08 operator focus note (assisted steering action-authority diagnostic).
Runs the preregistered bank in artifacts/rl_watchdog/turn_actionbank_20260908/
prereg_spec.json (main repo): on the frozen yawref-cigate8m checkpoint and
frozen 4.80573 kg full-mesh plant, measure the REAL dynamic response
(integrated signed yaw, body-command forward progress, loaded-foot slip,
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
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

_PROTO = Path(os.environ.get("HEXAPOD_PROTOTYPE_ROOT", Path.cwd())).resolve()
if not (_PROTO / "rl_move").is_dir():
    raise RuntimeError("Run from current prototype or set HEXAPOD_PROTOTYPE_ROOT")
_RL = _PROTO / "rl_move"
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



def _finite(value, name):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"unavailable gate metric: {name}")
    if not math.isfinite(value):
        raise ValueError(f"nonfinite gate metric: {name}")
    return value


def _relative_tilt(info, tilt_ref_rad):
    """Use real emitted values; an absent pitch key is never a healthy zero."""
    ref = np.asarray(tilt_ref_rad, dtype=float)
    if ref.shape != (2,) or not np.isfinite(ref).all():
        raise ValueError("unavailable tilt reference")
    values = []
    for i, axis in enumerate(("roll", "pitch")):
        relative = axis + "_rel_deg"
        absolute = axis + "_deg"
        if relative in info:
            values.append(_finite(info[relative], relative))
        elif absolute in info:
            values.append(_finite(info[absolute], absolute) - math.degrees(ref[i]))
        else:
            raise ValueError(f"unavailable gate metric: {axis} angle")
    return tuple(values)


def _frozen_value(value):
    """Canonical value serialization, independent of pickle reference aliases."""
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject:
            return ["array_object", value.shape, _frozen_value(value.tolist())]
        return ["array", value.dtype.str, value.shape,
                np.ascontiguousarray(value).tobytes().hex()]
    if isinstance(value, np.generic):
        return _frozen_value(value.item())
    if isinstance(value, np.random.Generator):
        return ["rng", _frozen_value(value.bit_generator.state)]
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        return ["float", value.hex()]
    if isinstance(value, dict):
        return ["dict", [[str(k), _frozen_value(v)]
                         for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))]]
    if isinstance(value, deque):
        return ["deque", value.maxlen, [_frozen_value(v) for v in value]]
    if isinstance(value, (list, tuple)):
        return [type(value).__name__, [_frozen_value(v) for v in value]]
    if isinstance(value, (set, frozenset)):
        return ["set", sorted((_frozen_value(v) for v in value), key=repr)]
    if isinstance(value, Path):
        return ["Path", str(value)]
    if hasattr(value, "__dict__"):
        return [type(value).__module__ + "." + type(value).__qualname__,
                _frozen_value(vars(value))]
    raise TypeError(f"unsupported state fingerprint value: {type(value)}")


def _digest(value):
    raw = json.dumps(_frozen_value(value), separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _capture_state(env, model, obs):
    """Actual integration state plus registered episode/controller state."""
    from rl_move.sim.mjx_host import snap_attrs_for
    mj = env._mujoco
    mask = mj.mjtState.mjSTATE_INTEGRATION
    physics = np.empty(mj.mj_stateSize(env.model, mask))
    mj.mj_getState(env.model, env.data, physics, mask)
    names = set(snap_attrs_for(type(env)))
    names.update(("_profile", "_goal_gen", "_phase", "rng"))
    missing = sorted(n for n in names if not hasattr(env, n))
    if missing:
        raise ValueError(f"state fingerprint missing attrs: {missing}")
    episode = {n: getattr(env, n) for n in sorted(names)}
    recurrent = {n: getattr(model, n) for n in ("_state", "_episode_start")
                 if hasattr(model, n)}
    qpos = np.asarray(env.data.qpos).copy()
    return {
        "qpos": qpos.tolist(), "qpos_sha256": _digest(qpos),
        "physics_state_sha256": _digest(physics),
        "complete_state_sha256": _digest({
            "physics": physics, "episode": episode, "obs": np.asarray(obs),
            "recurrent": recurrent}),
    }


def _material_interval(rows, expected_dt):
    """Distance at material contact points, normal-load weighted per foot."""
    if not rows:
        raise ValueError("unavailable gate metric: no audited physics substeps")
    distances, times = np.zeros(6), np.zeros(6)
    forward = elapsed = 0.0
    for row in rows:
        h = _finite(row["h"], "physics dt")
        if h <= 0:
            raise ValueError("nonpositive physics dt")
        fn = np.asarray(row["fn"], dtype=float)
        slip = np.asarray(row["slip_material"], dtype=float)
        if (fn.shape != (6,) or slip.shape != (6,)
                or not np.isfinite(fn).all() or not np.isfinite(slip).all()
                or np.any(slip < 0)):
            raise ValueError("unavailable/nonfinite material contact slip")
        loaded = fn > CONTACT_N
        distances += np.where(loaded, slip, 0.0)
        times += loaded * h
        forward += _finite(row["body_vx"], "body-frame velocity") * h
        elapsed += h
    if not math.isclose(elapsed, expected_dt, rel_tol=0.0, abs_tol=1e-10):
        raise ValueError(f"incomplete physics interval {elapsed} != {expected_dt}")
    return distances, times, forward


class _DynamicsAudit(pta._ContactAudit):
    """Existing read-only substep contact audit plus body-frame velocity."""
    def __init__(self, env):
        super().__init__(env)
        if int(env.model.opt.integrator) != int(self.mj.mjtIntegrator.mjINT_EULER):
            raise ValueError("material-slip timing is validated for Euler only")
        other_geoms = set(range(env.model.ngeom)) - self.robot_geoms
        if any(int(env.model.body_rootid[env.model.geom_bodyid[g]]) != 0
               for g in other_geoms):
            raise ValueError("material-slip metric requires stationary surroundings")

    def mj_step(self, m, d):
        super().mj_step(m, d)  # Exactly one real step; never refresh live data.
        if self.recording:
            if not self.pending:
                raise ValueError("missing physics audit row")
            vel = np.empty(6)
            self.mj.mj_objectVelocity(
                m, self.scratch, self.mj.mjtObj.mjOBJ_BODY,
                self.env._chassis_bid, vel, 0)
            R = self.scratch.xmat[self.env._chassis_bid].reshape(3, 3)
            self.pending[-1]["body_vx"] = float(vel[3:] @ R[:, 0])

    def endpoint_yaw(self):
        self._endpoint()
        R = self.scratch.xmat[self.env._chassis_bid].reshape(3, 3)
        return math.atan2(R[1, 0], R[0, 0])


def _state_match(a, b):
    return (np.array_equal(a["qpos"], b["qpos"])
            and a["physics_state_sha256"] == b["physics_state_sha256"]
            and a["complete_state_sha256"] == b["complete_state_sha256"])


def _window_hash(tr, p):
    end = min(p + WINDOW_TICKS, tr["n_ticks_done"])
    h = hashlib.sha256()
    for key in ("yaw", "xy", "pad_xy", "contact", "endpoint_yaw",
                "material_slip", "loaded_time", "body_forward"):
        h.update(np.ascontiguousarray(tr[key][p - 1:end]).tobytes())
    return h.hexdigest()


def _legacy_window_hash(tr, p):
    end = min(p + WINDOW_TICKS, tr["n_ticks_done"])
    h = hashlib.sha256()
    for arr in (tr["yaw"][p - 1:end], tr["xy"][p - 1:end],
                tr["pad_xy"][p - 1:end], tr["contact"][p - 1:end].astype(np.uint8)):
        h.update(np.ascontiguousarray(arr).tobytes())
    return h.hexdigest()


def _rollout(spec, *, vx, wz, phase_offset, n_ticks, pulse_tick=None,
             pulse_joint=None, pulse_delta=0.0, identity_out=None,
             capture_ticks=None):
    env, model, obs, mode_onehot = _fresh_env(spec, phase_offset, vx, wz)
    audit = None
    out = {k: [] for k in ("yaw", "xy", "vx", "phase", "modes", "contact",
                          "pad_xy", "roll", "pitch", "endpoint_yaw",
                          "material_slip", "loaded_time", "body_forward")}
    out.update({"fell": False, "term_reason": "", "term_tick": None,
                "truncated": False, "clip_hits": 0, "states": {}})
    try:
        from rl_move.sim.servo_model import motor_contract
        ident = model_identity(env)
        for k, v in spec["required_identity"].items():
            got = ident[k]
            ok = math.isclose(got, v, abs_tol=1e-6) if isinstance(v, float) else got == v
            if not ok:
                raise ValueError(f"identity mismatch {k}: {got} != {v}")
        contract = motor_contract(env.cfg, backend="servo_profile_np")
        expected = {"control.hz": 100.0, "bus.write_speed": 400.0,
                    "bus.write_acc": 20.0, "safety.max_delta_q_deg": .375,
                    "resolved_vel_max_counts_s_max": 350.0}
        for k, v in expected.items():
            if contract.get(k) != v:
                raise ValueError(f"motor contract mismatch {k}: {contract.get(k)}")
        if abs(env.dt - .01) > 1e-12:
            raise ValueError("control dt is not 0.01")
        hz = _finite(env.cfg["goal"]["walk_phase_hz"], "walk phase frequency")
        if (hz <= 0 or float(env.cfg["goal"].get("walk_phase_speed_scale", 0)) != 0
                or round(1 / hz / env.dt) != WINDOW_TICKS - PULSE_TICKS):
            raise ValueError("75-tick followup no longer matches configured phase clock")
        if identity_out is not None:
            identity_out.update(ident)
            identity_out.update({"motor_contract": contract, "mode_onehot": mode_onehot,
                                 "phase_hz": hz, "phase_period_s": 1 / hz,
                                 "followup_ticks": 75, "pulse_layer":
                                 "after SB3 predict clipping; before env safety"})
        audit = _DynamicsAudit(env)
        env._mujoco = audit
        lo, hi = np.asarray(env.action_space.low), np.asarray(env.action_space.high)
        for step in range(n_ticks):
            act, _ = model.predict(obs, deterministic=True)
            if (pulse_tick is not None and pulse_joint is not None
                    and pulse_tick <= step < pulse_tick + PULSE_TICKS):
                act = np.asarray(act, dtype=np.float32).copy()
                raw = float(act[pulse_joint]) + pulse_delta
                act[pulse_joint] = np.clip(raw, lo[pulse_joint], hi[pulse_joint])
                out["clip_hits"] += int(abs(act[pulse_joint] - raw) > 1e-9)
            record = step >= SETTLE_TICK - 1
            audit.begin_interval(phase=float(env._phase), record=record)
            obs, reward, term, trunc, info = env.step(act)
            # Preserve original live last-solve yaw/positions for exact old-bank
            # comparison. True endpoint yaw and corrected metrics are additional.
            out["yaw"].append(_yaw_of(env))
            out["xy"].append(env.data.xpos[env._chassis_bid, :2].copy())
            out["vx"].append(float(env._body_vel_xy()[0]))
            out["phase"].append(float(env._phase))
            out["modes"].append(info.get("goal_mode"))
            if any(a < 0 for a in env._touch_adr):
                raise ValueError("unavailable foot touch sensor")
            out["contact"].append([env.data.sensordata[a] > CONTACT_N for a in env._touch_adr])
            out["pad_xy"].append(env.data.xpos[env._pad_bids, :2].copy())
            roll, pitch = _relative_tilt(info, env._tilt_ref0)
            out["roll"].append(roll)
            out["pitch"].append(pitch)
            out["endpoint_yaw"].append(audit.endpoint_yaw())
            if record:
                ds, ts, forward = _material_interval(audit.pending, env.dt)
            else:
                ds, ts, forward = np.zeros(6), np.zeros(6), 0.0
            out["material_slip"].append(ds)
            out["loaded_time"].append(ts)
            out["body_forward"].append(forward)
            count = step + 1
            capture = (count >= SETTLE_TICK - 1 if capture_ticks is None
                       else count in capture_ticks)
            if capture:
                out["states"][count] = _capture_state(env, model, obs)
            if term:
                out.update(fell=True, term_reason=str(info.get("termination_reason", "")),
                           term_tick=step)
            if trunc:
                out["truncated"] = True
            if term or trunc:
                break
        out["final_qpos"] = env.data.qpos.copy()
    finally:
        if audit is not None:
            env._mujoco = audit.mj
        env.close()
    out["n_ticks_done"] = len(out["yaw"])
    for k in ("yaw", "xy", "vx", "phase", "contact", "pad_xy", "roll",
              "pitch", "endpoint_yaw", "material_slip", "loaded_time", "body_forward"):
        out[k] = np.asarray(out[k])
    out["yaw"] = np.unwrap(out["yaw"])
    out["endpoint_yaw"] = np.unwrap(out["endpoint_yaw"])
    return out


def _window_metrics(tr, p):
    end = min(p + WINDOW_TICKS, tr["n_ticks_done"])
    if end < p:
        return {"valid": False, "invalid": "terminated before window"}
    yaw0, xy0 = tr["yaw"][p - 1], tr["xy"][p - 1]
    heading = np.array([math.cos(yaw0), math.sin(yaw0)])
    delta = tr["xy"][end - 1] - xy0
    pads = tr["pad_xy"][p - 1:end]
    contacts = tr["contact"][p - 1:end]
    legacy_slip = float((np.linalg.norm(np.diff(pads, axis=0), axis=2)
                         * contacts[:-1]).sum())
    distances = tr["material_slip"][p:end].sum(axis=0)
    times = tr["loaded_time"][p:end].sum(axis=0)
    loaded_seconds = float(times.sum())
    if loaded_seconds <= 0:
        raise ValueError("unavailable gate metric: no loaded material contact time")
    metrics = {
        "valid": end == p + WINDOW_TICKS,
        # Original primary outcome retained, including its last-solve timing.
        "d_yaw_rad": float(tr["yaw"][end - 1] - yaw0),
        "endpoint_d_yaw_rad": float(tr["endpoint_yaw"][end - 1] - tr["endpoint_yaw"][p - 1]),
        "fwd_disp_m": float(tr["body_forward"][p:end].sum()),
        "loaded_slip_m": float(distances.sum()),
        "loaded_material_mean_speed_m_s": float(distances.sum() / loaded_seconds),
        "loaded_material_per_foot_m": distances.tolist(),
        "loaded_per_foot_seconds": times.tolist(),
        "loaded_foot_seconds": loaded_seconds,
        "legacy_initial_heading_fwd_disp_m": float(delta @ heading),
        "legacy_pad_center_touch_slip_m": legacy_slip,
        "lat_disp_m": float(delta @ np.array([-heading[1], heading[0]])),
        "max_abs_roll_deg": float(np.max(np.abs(tr["roll"][p:end]))),
        "max_abs_pitch_deg": float(np.max(np.abs(tr["pitch"][p:end]))),
        "nonwalk_ticks": sum(m != "walk" for m in tr["modes"][p:end]),
        "terminated_in_window": tr["term_tick"] is not None and p <= tr["term_tick"] < end,
        "term_reason": tr["term_reason"],
        "window_ticks": end - p,
        "window_state_samples": end - (p - 1),
        "phase_at_branch": float(tr["phase"][p - 1]),
    }
    for key in ("d_yaw_rad", "endpoint_d_yaw_rad", "fwd_disp_m", "loaded_slip_m",
                "max_abs_roll_deg", "max_abs_pitch_deg"):
        _finite(metrics[key], key)
    return metrics





def _branch_task(args):
    spec, cell, p, joint, sign = args
    delta = 0.0 if joint is None else sign * DELTA
    started = time.time()
    tr = _rollout(spec, vx=cell["vx"], wz=cell["wz"],
                  phase_offset=cell["phase_offset"], n_ticks=p + WINDOW_TICKS,
                  pulse_tick=None if joint is None else p,
                  pulse_joint=joint, pulse_delta=delta,
                  capture_ticks={p, p + WINDOW_TICKS})
    return {"cell": cell, "branch_tick": p, "joint": joint, "pulse_delta": delta,
            "clip_hits": tr["clip_hits"], "metrics": _window_metrics(tr, p),
            "window_hash": _window_hash(tr, p),
            "legacy_window_hash": _legacy_window_hash(tr, p),
            "prefix_state": tr["states"].get(p),
            "endpoint_state": tr["states"].get(p + WINDOW_TICKS),
            "final_qpos": tr["final_qpos"].tolist(),
            "wall_s": round(time.time() - started, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True, type=Path)
    ap.add_argument("--checkpoint", required=True, type=Path)
    ap.add_argument("--cfg-json", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--original-bank", type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out / "bank.json").exists():
        raise SystemExit("Refusing to overwrite a completed reviewed bank")
    prereg = json.loads(args.spec.read_text())
    pins = prereg["frozen_assets"]
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    if sha(args.spec) != "847db884d21b74b6452704d86ae13f30f7e59892ee3245df81d7475813cebdba":
        raise SystemExit("original preregistration SHA mismatch")
    if sha(args.cfg_json) != "aabf4cc25f78ebf3b28ff7b4a46fba85c109f4061becaf4212e8842b5c550e40":
        raise SystemExit("original 64-key cfg SHA mismatch")
    if sha(args.checkpoint) != pins["checkpoint_sha256"]:
        raise SystemExit("checkpoint SHA mismatch")
    if sha(_PROTO / "mesh_mujoco/hexapod_mesh.xml") != pins["full_mesh_xml_sha256"]:
        raise SystemExit("full-mesh XML SHA mismatch")
    spec = {"checkpoint": str(args.checkpoint.resolve()),
            "cfg_set": json.loads(args.cfg_json.read_text()),
            "seed": prereg["design"]["seed"],
            "episode_seconds": prereg["design"]["episode_seconds"],
            "required_identity": pins["required_identity"]}
    cells = [dict(vx=c["vx"], wz=c["wz"], phase_offset=ph)
             for c in prereg["design"]["cells"]
             for ph in prereg["design"]["starts_phase_offset"]]
    if args.smoke:
        cells = cells[:1]
    if spec["seed"] != 0:
        raise SystemExit("this review preserves original seed 0")
    started = time.time()
    baselines, identity = [], {}
    for cell in cells:
        tr = _rollout(spec, **cell,
                      n_ticks=SETTLE_TICK + P2_SEARCH[1] + WINDOW_TICKS,
                      identity_out=identity if not identity else None)
        if tr["fell"] or tr["truncated"]:
            raise SystemExit(f"baseline ended early: {cell}")
        p1 = next(i + 1 for i in range(SETTLE_TICK - 1, tr["n_ticks_done"])
                  if tr["modes"][i] == "walk")
        ph1 = tr["phase"][p1 - 1]
        target = (ph1 + math.pi) % (2 * math.pi)
        p2 = min(range(p1 + P2_SEARCH[0], p1 + P2_SEARCH[1] + 1),
                 key=lambda p: abs((tr["phase"][p - 1] - target + math.pi)
                                   % (2 * math.pi) - math.pi))
        base = {"cell": cell, "p1": p1, "p2": p2,
                "phase_p1": float(ph1), "phase_p2": float(tr["phase"][p2 - 1]),
                "half_cycle_phase_error_rad": float(
                    (tr["phase"][p2 - 1] - target + math.pi) % (2 * math.pi) - math.pi)}
        for p in (p1, p2):
            base[f"metrics_{p}"] = _window_metrics(tr, p)
            base[f"hash_{p}"] = _window_hash(tr, p)
            base[f"legacy_hash_{p}"] = _legacy_window_hash(tr, p)
            base[f"prefix_{p}"] = tr["states"][p]
            base[f"endpoint_{p}"] = tr["states"][p + WINDOW_TICKS]
        baselines.append(base)
        print(f"baseline {cell}: {p1}/{p2}, phases {base['phase_p1']:.6f}/{base['phase_p2']:.6f}", flush=True)
    zeros, pulses = [], []
    for b in baselines:
        for p in (b["p1"], b["p2"]):
            zeros.append((spec, b["cell"], p, None, 0))
            for j in (range(2) if args.smoke else range(18)):
                for sign in (1, -1):
                    pulses.append((spec, b["cell"], p, j, sign))
    def reference(res):
        return next(b for b in baselines if b["cell"] == res["cell"])
    results, exact = [], []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        # Zero-control parity is required BEFORE launching any pulse branches.
        for res in pool.map(_branch_task, zeros):
            b, p = reference(res), res["branch_tick"]
            checks = {"window": res["window_hash"] == b[f"hash_{p}"],
                      "prefix": _state_match(res["prefix_state"], b[f"prefix_{p}"]),
                      "endpoint": (res["endpoint_state"] is not None and
                                   _state_match(res["endpoint_state"], b[f"endpoint_{p}"]))}
            exact.append({"cell": res["cell"], "p": p, **checks,
                          "match": all(checks.values())})
            results.append(res)
        if not all(e["match"] for e in exact):
            (args.out / "parity_failure.json").write_text(json.dumps(exact, indent=2))
            raise SystemExit("zero-branch state parity failed; no pulse branches run")
        print(f"zero parity PASS; {len(pulses)} pulse branches", flush=True)
        for i, res in enumerate(pool.map(_branch_task, pulses, chunksize=1)):
            b, p = reference(res), res["branch_tick"]
            if res["prefix_state"] is None or not _state_match(res["prefix_state"], b[f"prefix_{p}"]):
                raise SystemExit(f"pulse prefix state parity failed: {res['cell']} {p} {res['joint']}")
            base_metrics = b[f"metrics_{p}"]
            gain = math.copysign(1.0, res["cell"]["wz"]) * (
                res["metrics"]["d_yaw_rad"] - base_metrics["d_yaw_rad"])
            res["original_primary_signed_yaw_gain_rad"] = gain
            res["original_primary_effect_pass"] = bool(
                res["metrics"]["valid"] and gain >= .005)
            results.append(res)
            if (i + 1) % 20 == 0:
                print(f"{i + 1}/{len(pulses)} pulses done", flush=True)
    comparison = None
    if args.original_bank:
        original = json.loads(args.original_bank.read_text())
        key = lambda r: (r["cell"]["vx"], r["cell"]["wz"], r["cell"]["phase_offset"],
                         r["branch_tick"], r["joint"], r["pulse_delta"])
        lookup = {key(r): r for r in original["branches"]}
        compared = []
        for res in results:
            old = lookup.get(key(res))
            if old is None:
                raise SystemExit("original comparison missing matching branch")
            res["owner_original_metrics"] = old["metrics"]
            compared.append({
                "key": key(res),
                "observed_yaw_exact": res["metrics"]["d_yaw_rad"] == old["metrics"]["d_yaw_rad"],
                "legacy_window_exact": res["legacy_window_hash"] == old["window_hash"],
                "final_qpos_exact": np.array_equal(res["final_qpos"], old["final_qpos"])})
        comparison = {"all_match": all(all(r[k] for k in
                      ("observed_yaw_exact", "legacy_window_exact", "final_qpos_exact"))
                      for r in compared), "detail": compared}
    source_paths = ["rl_move/sim/probe_turn_authority.py", "rl_move/sim/sim_env.py",
                    "rl_move/sim/walk_task.py", "rl_move/sim/joint_task.py",
                    "rl_move/sim/gru_policy.py", "rl_move/sim/servo_model.py",
                    "rl_move/sim/mjx_host.py", "rl_move/config.yaml",
                    "mesh_mujoco/hexapod_mesh.xml", "mesh_mujoco/hexapod_mesh_mjx.xml"]
    out = {"schema": "hexapod.action_response_bank.review.v1",
           "prereg_spec_sha256": sha(args.spec), "runner_sha256": sha(__file__),
           "checkpoint_sha256": sha(args.checkpoint),
           "mesh_xml_sha256": sha(_PROTO / "mesh_mujoco/hexapod_mesh.xml"),
           "source_hashes": {p: sha(_PROTO / p) for p in source_paths},
           "asset_hashes": {str(p.relative_to(_PROTO)): sha(p) for p in
                           sorted((_PROTO / "mesh_mujoco/assets").glob("*")) if p.is_file()},
           "cfg_set": spec["cfg_set"], "cfg_json_sha256": sha(args.cfg_json),
           "identity": identity, "smoke": args.smoke,
           "wall_s": round(time.time() - started, 2),
           "review_scope": {
               "original_primary": "unchanged 5mrad observed last-solve yaw; true endpoint yaw additional",
               "pulse_layer": "after SB3 predict clipping, clipped to action space, then normal env safety",
               "corrected_retention": "post-review screen; not retroactively original preregistration",
               "material_slip": "substep normal-load-weighted material contact displacement, foot fn>.5N, static ground",
               "progress": "sum actual body-frame forward velocity * physics dt",
               "legacy_proxies_preserved": ["legacy_initial_heading_fwd_disp_m", "legacy_pad_center_touch_slip_m"],
               "numerical_thresholds_unchanged": "5mrad yaw, .9 forward ratio, 1.25 slip ratio, +3deg tilt",
               "non_claim": "finite pulse-class sensitivity only; no sustained steering or whole-class closure"},
           "exactness": {"all_match": all(e["match"] for e in exact), "detail": exact,
                         "all_pulse_prefixes_match": True},
           "original_comparison": comparison, "baselines": baselines, "branches": results}
    (args.out / "bank.json").write_text(json.dumps(out, indent=1, allow_nan=False))
    print(f"wrote {args.out / 'bank.json'}; primary threshold passes "
          f"{sum(r.get('original_primary_effect_pass', False) for r in results)}/{len(pulses)}", flush=True)
    if comparison is not None and not comparison["all_match"]:
        raise SystemExit("reviewed/owner raw trajectory difference; interpret separately")


if __name__ == "__main__":
    main()
