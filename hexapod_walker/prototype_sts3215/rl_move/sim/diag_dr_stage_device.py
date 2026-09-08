"""Bounded idle-GPU staged-DR device/exposure diagnostic (NO optimizer).

09-08 follow-up to the stagedr2m mechanism canary (operator focus note +
fb_20260908T104404_58b3a5): the 8-test CPU bank
(rl_move/tests/test_dr_stage_ramp.py) proves the RandRanges-level
contract, and the canary proved the trainer loop broadcasts healthily —
but neither PROVES that a staged-DR broadcast actually lands in the
per-world Warp/MJX DEVICE state (MODEL_DR_FIELDS rows + TickParams) at
episode reset, nor measures REALIZED per-world exposure vs the
requested stage fraction. Target logs / CPU RandRanges alone are
insufficient evidence. This script runs the REAL vec-env machinery
(MjxVecEnv + MjxTickStepper, the reference implementation the sharded
trainer env is bit-tested against) on one idle GPU pod, with zero
policy/optimizer work, and verifies end to end:

  A. armed-but-unbroadcast = FULL post-override ranges (eval convention)
     — object identity on every shim env + realized startup draws.
  B. ModelDR ENDPOINT DELIVERY: per-world device rows
     (stepper._dr_fields) equal a bit-exact host recomputation from
     each env's own mint-time _ep_rand draw (ModelDrScratch.rows_for),
     and the TickParams device rows equal tp_rows(env). This is the
     actual-device-delivery proof, not a host-mirror read.
  C. RESET-ONLY SEMANTICS: an apply_dr_stage_frac broadcast + pool
     flush leaves every LIVE world's device rows bit-identical; only
     worlds that subsequently RESET (pooled injection / refill mint)
     pick up draws from the new stage.
  D. REALIZED vs REQUESTED exposure per stage window: every post-
     broadcast reset draw lies inside the requested stage ranges
     (frac 0 = exactly nominal: mass/friction/torque/latency scales
     == 1, zero bad starts); per-window telemetry reports how many
     worlds still LIVE on an older stage's draw at window end — the
     "requested fraction is not realized exposure" number.
  E. frac >= 1 restores the EXACT captured full-ranges object and
     realized draws again span the full matrix.

Usage (on a GPU pod, from /workspace/prototype_sts3215):
  /workspace/venv_torchgpu/bin/python -m rl_move.sim.diag_dr_stage_device \
      --n-envs 32 --episode-seconds 4 --ticks-per-stage 500 \
      --impl warp --seed 40 --out /tmp/diag_dr_stage.json \
      --cfg-set env.model_source=mesh_mjx --cfg-set control.hz=100 \
      --cfg-set env.dr_stage_ramp_steps=20000000 --cfg-set dr....=...

--episode-seconds is deliberately SHORT (machinery diagnostic: it only
controls how often the pooled-reset path fires inside the bounded
window; DR draw semantics are untouched by episode length).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


from rl_move.config import load_config
from rl_move.sim.mjx_backend import MODEL_DR_FIELDS
from rl_move.sim.mjx_host import tp_rows
from rl_move.sim.mjx_vec_env import MjxVecEnv
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.train_ppo_sim import _parse_cfg_set
from rl_move.sim.walk_task import SimHexapodJointWalkEnv

TP_KEYS = ("latency_s", "deadband", "vel_max", "imu_off")


def _apply_overrides(cfg: dict, specs: list[str]) -> dict:
    for dotted, val in _parse_cfg_set(specs).items():
        node = cfg
        *path, leaf = dotted.split(".")
        for k in path:
            node = node.setdefault(k, {})
        node[leaf] = val
    return cfg


def _device_dr(venv) -> dict[str, np.ndarray]:
    return {f: np.asarray(venv.stepper._dr_fields[f])
            for f in MODEL_DR_FIELDS}


def _device_tp(venv) -> dict[str, np.ndarray]:
    tp = venv.stepper._tick_params
    return {"latency_s": np.asarray(tp.latency_s),
            "deadband": np.asarray(tp.deadband),
            "vel_max": np.asarray(tp.vel_max),
            "imu_off": np.asarray(tp.imu_off)}


def _rows_equal(a: dict, b: dict, idx=None) -> list[str]:
    """Names of fields whose rows differ (idx=None -> full batch)."""
    bad = []
    for k, va in a.items():
        vb = b[k]
        if idx is not None:
            va, vb = va[idx], vb[idx]
        if not np.array_equal(np.asarray(va), np.asarray(vb)):
            bad.append(k)
    return bad


def _expected_row_for(venv, i: int) -> tuple[dict, dict]:
    """Host recomputation of world i's device rows from its CURRENT
    _ep_rand draw — the same code path _choreography used at mint time
    (ModelDrScratch.rows_for + tp_rows), recomputed out-of-band."""
    env = venv.envs[i]
    dr = venv._dr_scratch.rows_for(env)
    dtyped = {}
    for f in MODEL_DR_FIELDS:
        cur = np.asarray(venv.stepper._dr_fields[f])
        dtyped[f] = np.asarray(dr[f], dtype=cur.dtype)
    tp = tp_rows(env)
    tpd = {k: np.asarray(tp[k],
                         dtype=np.asarray(
                             _device_tp(venv)[k]).dtype) for k in TP_KEYS}
    return dtyped, tpd


def _draw_stats(envs, idx) -> dict:
    """Realized _ep_rand scalars for worlds idx (their live episodes)."""
    out = {"n": len(idx)}
    for name in ("mass_scale", "friction_scale", "torque_scale",
                 "latency_scale", "deadband_scale", "vel_scale",
                 "contact_stiff_scale"):
        v = [float(getattr(envs[i]._ep_rand, name)) for i in idx]
        out[name] = {"min": min(v), "max": max(v),
                     "mean": float(np.mean(v))} if v else None
    out["bad_start_worlds"] = int(sum(
        1 for i in idx if len(envs[i]._ep_rand.bad_start_joints) > 0))
    gz = [float(-envs[i]._ep_rand.gravity_vec[2]) for i in idx]
    gxy = [float(np.hypot(*envs[i]._ep_rand.gravity_vec[:2])) for i in idx]
    out["gravity_z"] = {"min": min(gz), "max": max(gz)} if gz else None
    out["gravity_tilt_xy"] = {"min": min(gxy), "max": max(gxy)} if gxy else None
    return out


def _in_pair(v, pair, eps=1e-9):
    lo, hi = (min(pair), max(pair))
    return (lo - eps) <= v <= (hi + eps)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n-envs", type=int, default=32)
    ap.add_argument("--episode-seconds", type=float, default=4.0)
    ap.add_argument("--ticks-per-stage", type=int, default=500)
    ap.add_argument("--impl", default="warp")
    ap.add_argument("--seed", type=int, default=40)
    ap.add_argument("--fracs", default="0.0,0.5,1.0",
                    help="stage fractions broadcast in order")
    ap.add_argument("--cfg-set", action="append", default=[],
                    metavar="K=V", dest="cfg_set")
    ap.add_argument("--out", default="/tmp/diag_dr_stage_device.json")
    ap.add_argument("--max-wall-s", type=float, default=2400.0,
                    help="hard bound; exceeding it is a FAIL (unbounded "
                         "diagnostics are their own failure class)")
    a = ap.parse_args()
    t_start = time.monotonic()
    fracs = [float(x) for x in a.fracs.split(",")]

    cfg = _apply_overrides(load_config(), a.cfg_set)
    drs = float((cfg.get("env") or {}).get("dr_stage_ramp_steps", 0) or 0)
    if drs <= 0:
        print("FATAL: env.dr_stage_ramp_steps not set >0 in --cfg-set — "
              "nothing to diagnose")
        return 2

    checks: dict[str, dict] = {}
    hard_fail: list[str] = []

    def check(name: str, ok: bool, detail):
        checks[name] = {"ok": bool(ok), "detail": detail}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if not ok:
            hard_fail.append(name)

    env_kwargs = dict(cfg=cfg, randomize=True, dr_scale=0.0,
                      episode_seconds=a.episode_seconds,
                      params=SimServoParams.from_cfg(cfg))
    impl = None if a.impl in ("", "none", "None") else a.impl
    print(f"building MjxVecEnv n_envs={a.n_envs} impl={impl} "
          f"episode_seconds={a.episode_seconds} seed={a.seed}")
    venv = MjxVecEnv(SimHexapodJointWalkEnv, a.n_envs,
                     env_kwargs=env_kwargs, seed=a.seed, impl=impl)
    B = venv.num_envs
    venv.reset()
    envs = venv.envs

    # ---- A: armed-but-unbroadcast == FULL ranges ----------------------
    ident = all(e.randomizer.ranges is e._dr_stage_full for e in envs)
    full = envs[0]._dr_stage_full
    startup = _draw_stats(envs, list(range(B)))
    ok_a = (ident
            and all(_in_pair(s["min"], getattr(full, f))
                    and _in_pair(s["max"], getattr(full, f))
                    for f, s in (("mass_scale", startup["mass_scale"]),
                                 ("friction_scale",
                                  startup["friction_scale"]),
                                 ("torque_scale", startup["torque_scale"]),
                                 ("latency_scale",
                                  startup["latency_scale"]))))
    check("A_armed_unbroadcast_full", ok_a,
          {"ranges_is_full_object": ident, "startup_draws": startup,
           "requested_mass": full.mass_scale,
           "requested_friction": full.friction_scale})

    # ---- B: endpoint delivery at startup ------------------------------
    dev_dr = _device_dr(venv)
    dev_tp = _device_tp(venv)
    # host mirrors are float64; the device stores the model dtype
    # (float32 under warp) — compare after the same cast
    # set_model_fields/set_tick_params perform.
    host_dr_cast = {f: np.asarray(venv._dr_host[f], dtype=dev_dr[f].dtype)
                    for f in MODEL_DR_FIELDS}
    host_tp_cast = {k: np.asarray(venv._tp_host[k], dtype=dev_tp[k].dtype)
                    for k in TP_KEYS}
    host_ok = (not _rows_equal(host_dr_cast, dev_dr)
               and not _rows_equal(host_tp_cast, dev_tp))
    bad_fields: dict[str, list[str]] = {}
    sample = list(range(min(B, 8)))
    for i in sample:
        exp_dr, exp_tp = _expected_row_for(venv, i)
        bd = [f for f in MODEL_DR_FIELDS
              if not np.array_equal(exp_dr[f], dev_dr[f][i])]
        bd += [k for k in TP_KEYS
               if not np.array_equal(exp_tp[k], dev_tp[k][i])]
        if bd:
            bad_fields[str(i)] = bd
    check("B_device_delivery_startup", host_ok and not bad_fields,
          {"host_mirror_equals_device": host_ok,
           "recompute_mismatches": bad_fields, "sampled_worlds": sample})

    n_act = venv.action_space.shape[0]
    zeros = np.zeros((B, n_act), dtype=np.float32)
    stage_windows = []
    prev_frac = None    # None = armed/full (startup)

    for frac in fracs:
        if time.monotonic() - t_start > a.max_wall_s:
            check("bounded_wall_clock", False,
                  f"exceeded --max-wall-s={a.max_wall_s}")
            break
        # snapshot device rows BEFORE the broadcast
        d_before_dr = _device_dr(venv)
        d_before_tp = _device_tp(venv)
        rets = venv.env_method("apply_dr_stage_frac", frac)
        flushed = venv.flush_reset_pools()
        req = rets[0]
        # ---- C1: broadcast alone must not touch live device state ----
        untouched = (not _rows_equal(d_before_dr, _device_dr(venv))
                     and not _rows_equal(d_before_tp, _device_tp(venv)))
        # requested ranges object for this stage
        ranges = envs[0].randomizer.ranges
        # ---- step the window; track resets ----------------------------
        reset_worlds: set[int] = set()
        reset_draws_idx: list[int] = []
        pop_delivery_bad: dict[str, list[str]] = {}
        n_pop_checked = 0
        for t in range(a.ticks_per_stage):
            _obs, _r, dones, _infos = venv.step(zeros)
            just = np.flatnonzero(dones)
            for i in just:
                i = int(i)
                reset_worlds.add(i)
                reset_draws_idx.append(i)
                # endpoint delivery on the POOLED-INJECTION path
                if n_pop_checked < 8:
                    exp_dr, exp_tp = _expected_row_for(venv, i)
                    ddr, dtp = _device_dr(venv), _device_tp(venv)
                    bd = [f for f in MODEL_DR_FIELDS
                          if not np.array_equal(exp_dr[f], ddr[f][i])]
                    bd += [k for k in TP_KEYS
                           if not np.array_equal(exp_tp[k], dtp[k][i])]
                    if bd:
                        pop_delivery_bad[str(i)] = bd
                    n_pop_checked += 1
            if time.monotonic() - t_start > a.max_wall_s:
                break
        live_worlds = [i for i in range(B) if i not in reset_worlds]
        # ---- C2: never-reset worlds keep pre-broadcast rows -----------
        d_after_dr = _device_dr(venv)
        d_after_tp = _device_tp(venv)
        live_bad = (_rows_equal(d_before_dr, d_after_dr, idx=live_worlds)
                    + _rows_equal(d_before_tp, d_after_tp,
                                  idx=live_worlds))
        # ---- D: realized draws of reset worlds within requested -------
        uniq = sorted(set(reset_draws_idx))
        stats = _draw_stats(envs, uniq)
        out_of_range = {}
        for fld in ("mass_scale", "friction_scale", "torque_scale",
                    "latency_scale", "vel_scale"):
            pair = getattr(ranges, fld)
            s = stats[fld]
            if s and not (_in_pair(s["min"], pair)
                          and _in_pair(s["max"], pair)):
                out_of_range[fld] = {"realized": s, "requested": pair}
        nominal_bad = {}
        if frac <= 0.0 and uniq:
            for fld in ("mass_scale", "friction_scale", "torque_scale",
                        "latency_scale"):
                s = stats[fld]
                if abs(s["min"] - 1.0) > 1e-9 or abs(s["max"] - 1.0) > 1e-9:
                    nominal_bad[fld] = s
            if stats["bad_start_worlds"]:
                nominal_bad["bad_start_worlds"] = stats["bad_start_worlds"]
            if stats["gravity_tilt_xy"]["max"] > 1e-9:
                nominal_bad["gravity_tilt_xy"] = stats["gravity_tilt_xy"]
        endpoint_ok = True
        if frac >= 1.0:
            endpoint_ok = all(e.randomizer.ranges is e._dr_stage_full
                              for e in envs)
        win = {
            "frac": frac, "flushed_pool_entries": int(flushed),
            "requested": req, "worlds_reset": len(reset_worlds),
            "worlds_live_on_older_stage": len(live_worlds),
            "realized_share_at_stage": len(reset_worlds) / B,
            "reset_draw_stats": stats,
            "broadcast_left_live_rows_untouched": untouched,
            "live_world_rows_changed_fields": live_bad,
            "pop_delivery_mismatches": pop_delivery_bad,
            "n_pop_delivery_checked": n_pop_checked,
            "out_of_range": out_of_range,
            "nominal_violations": nominal_bad,
            "endpoint_object_identity": endpoint_ok,
        }
        stage_windows.append(win)
        ok = (untouched and not live_bad and not pop_delivery_bad
              and not out_of_range and not nominal_bad and endpoint_ok
              and flushed >= 0 and len(reset_worlds) >= max(4, B // 4))
        check(f"stage_frac_{frac:g}", ok, win)
        prev_frac = frac

    # frac1 breadth sanity: draws must actually SPREAD (not all nominal)
    last = stage_windows[-1] if stage_windows else None
    if last and last["frac"] >= 1.0 and last["reset_draw_stats"]["n"] >= 8:
        ms = last["reset_draw_stats"]["mass_scale"]
        fs = last["reset_draw_stats"]["friction_scale"]
        spread_ok = (ms["max"] - ms["min"] > 0.05
                     and fs["max"] - fs["min"] > 0.1)
        check("E_full_stage_breadth_realized", spread_ok,
              {"mass": ms, "friction": fs,
               "requested_mass": full.mass_scale,
               "requested_friction": full.friction_scale})

    wall = time.monotonic() - t_start
    verdict = "PASS" if not hard_fail else "FAIL"
    report = {"verdict": verdict, "failed_checks": hard_fail,
              "checks": checks, "n_envs": B,
              "episode_seconds": a.episode_seconds,
              "ticks_per_stage": a.ticks_per_stage,
              "impl": a.impl, "seed": a.seed, "fracs": fracs,
              "wall_s": wall, "cfg_set": a.cfg_set}
    Path(a.out).write_text(json.dumps(report, indent=1, default=str))
    print(f"\n=== staged-DR device diagnostic: {verdict} "
          f"({wall:.0f}s, report -> {a.out}) ===")
    if hard_fail:
        print("failed checks:", ", ".join(hard_fail))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
