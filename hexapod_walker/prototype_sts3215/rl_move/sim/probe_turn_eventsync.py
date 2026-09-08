"""probe_turn_eventsync.py — event-based phase-synchronization SCREEN on
the frozen full-mesh plant (todaypolicy steering, 2026-09-08, operator
focus note: "screen event-based phase synchronization using actual
per-leg joint lag/contact events").

Plain English: every global timing/geometry lever on the scripted
steering plant is closed (cadence, lift lead, stance arm/posture, omega
shaping, governor rescale, command twist re-projection, fixed-duty time
multiplexing).  The one distinct untested idea is EVENT-BASED PHASE
SYNCHRONIZATION: instead of advancing each leg's gait phase on the wall
clock, advance it on measured per-leg events (touchdown/liftoff), so
legs coordinate against what actually happened.  Per the focus note and
TIME_MULTIPLEX_REVIEW.md, a phase MISMATCH alone is NOT support
(earlier timing improvements lacked body-yaw gain); this probe is a
pure measurement of associations between event-conditioned coordination
and yaw, without identifying the causal effect of any controller.
It screens a hypothesis BEFORE any mechanism is implemented.  Zero training, zero robot work,
no plant/limit/gate changes.

What it measures per frozen cell (scripted TripodGait, arcs
vx=0.08 wz=+/-0.15 + straight guard, starts 0/pi, seed 0, 15 s):

1. PER-LEG EVENT OFFSETS: actual touchdown/liftoff (touch sensor edge)
   vs planned stance/swing boundary, circular offset in ms.  Split into
   the COMMON component (median across legs — already-closed global lag
   territory) and the LEG-DIFFERENTIAL component (what an event-based
   per-leg synchronizer could uniquely act on), plus per-leg IQR (the
   noise floor of the feedback signal itself).
2. SUPPORT-STATE-CONDITIONED YAW: classify each scored tick by executed
   loaded support (tripod A = legs {0,2,4}, B = {1,3,5}; pureA / pureB
   / mixed / degenerate) and report per-state wz/vx means and medians.
3. OBSERVATIONAL SUPPORT-STATE REWEIGHTING: replacing the observed
   mixed/degenerate population by the observed majority-tripod population
   simply yields that population's mean yaw. This is association, not an
   intervention prediction or a causal upper bound. Failure of this
   descriptive screen does not close event-based control as a class.

HISTORICAL PRE-REGISTERED BAR (retained descriptively, before measurement;
not an efficacy or qualification gate). The original bar checked
ALL of:
  S1 gain: counterfactual wz gain in the COMMANDED direction
     >= +10% of |measured wz| on ALL FOUR arc cells (both signs x both
     starts).
  S2 signal: the event feedback carries a usable leg-differential
     component — inter-leg touchdown-offset spread >= 50 ms on every
     arc cell, OR max per-leg sign-differential (same start, +wz vs
     -wz) >= 30 ms.  Otherwise event sync collapses to a common phase
     shift, which is CLOSED (cadence closure: fractional lag improved
     0.29->0.21 and yaw REGRESSED both signs; lift-lead closure: the
     executed gait is already internally self-aligned).
  S3 health: the same counterfactual on the straight cells predicts
     |wz| <= 0.0074 rad/s (the measured baseline straight drift cap),
     zero falls anywhere, and bit-exact body-median parity with the
     stance-arm baseline (guards that this probe measures the same
     plant/gait, not a drifted harness).
The bar is preserved in historical_bar_supported. Only complete validated
matrices can pass observational_screen_passed; supported remains false
because observation alone cannot establish an intervention's benefit.
No mechanism, preflight, or canary follows automatically from this screen.
The original continuous joystick request and qualification gates remain
unchanged; no actual joint-lag measurement is made by this contact-only probe.
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
from rl_move.sim.probe_turn_stancearm import (  # noqa: E402
    LOAD_N, PIN, feasibility_guard, pin_manifest)
from rl_move.sim.probe_turn_twistfit import (  # noqa: E402
    _finite_number, _nonfinite, _feasibility_reasons, _json_safe)

from hexapod_core.tripod_gait import TripodGait  # noqa: E402

TRIPOD_A = (0, 2, 4)
TRIPOD_B = (1, 3, 5)

# Pre-registered bar (see module docstring). Straight cap = measured
# baseline straight |wz| max (stance100_baseline_fm.json, phase pi).
BAR = {
    "s1_min_gain_frac": 0.10,
    "s2_min_interleg_spread_ms": 50.0,
    "s2_min_sign_differential_ms": 30.0,
    "s3_straight_wz_cap": 0.0074,
}

# Bit-exact parity references: stance-arm baseline body medians on the
# SAME frozen full-mesh plant/cells (artifacts/rl_watchdog/
# turn_stancearm_20260908/stance100_baseline_fm.json — itself bit-exact
# with the lift-lead and cadence baselines).
PARITY_REF = {
    (0.08, 0.15, 0.0): (0.06424356912738255, 0.03722226587463831, 1300),
    (0.08, 0.15, 3.141592653589793):
        (0.06322606606503198, 0.036275323376160386, 1300),
    (0.08, -0.15, 0.0): (-0.06305192853310224, 0.03636890899080783, 1300),
    (0.08, -0.15, 3.141592653589793):
        (-0.06506261172345035, 0.0369504033752522, 1300),
    (0.08, 0.0, 0.0): (-0.00015796815524232432, 0.040065720987130155, 1300),
    (0.08, 0.0, 3.141592653589793):
        (-0.007391347275148641, 0.04023429258659103, 1300),
}


def _edges(mask: np.ndarray, rising: bool) -> list[np.ndarray]:
    """Per-leg indices where a (T,6) bool mask rises (False->True) or
    falls (True->False); index is the tick AFTER the transition."""
    d = np.diff(mask.astype(np.int8), axis=0)
    want = 1 if rising else -1
    return [np.flatnonzero(d[:, f] == want) + 1 for f in range(mask.shape[1])]


def _wrap(value, period):
    return (np.asarray(value) + period / 2.0) % period - period / 2.0


def _match_events(plan_idx: np.ndarray, actual_idx: np.ndarray,
                  period_ticks: float) -> dict:
    """Chronological one-to-one matching within half a period in REAL time.

    Maximize matched events, then minimize total absolute time offset.
    Missing events stay missing; a different cycle cannot fill the hole.
    Order is preserved and each actual event is used at most once.
    """
    if not math.isfinite(period_ticks) or period_ticks <= 0:
        raise ValueError("period_ticks must be finite and positive")
    plan = np.asarray(plan_idx, dtype=float)
    actual = np.asarray(actual_idx, dtype=float)
    if (plan.ndim != 1 or actual.ndim != 1 or not np.isfinite(plan).all()
            or not np.isfinite(actual).all()
            or (np.diff(plan) <= 0).any() or (np.diff(actual) <= 0).any()):
        raise ValueError("event indices must be finite, sorted and unique")
    n, m = len(plan), len(actual)
    counts = np.zeros((n + 1, m + 1), dtype=int)
    costs = np.zeros((n + 1, m + 1))
    choices = np.zeros((n, m), dtype=np.int8)
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            # deterministic tie break: match, then skip actual, then plan
            options = [(counts[i+1, j], costs[i+1, j], 0),
                       (counts[i, j+1], costs[i, j+1], 1)]
            delta = actual[j] - plan[i]
            if abs(delta) < period_ticks / 2.0:
                options.append((1 + counts[i+1, j+1],
                                abs(delta) + costs[i+1, j+1], 2))
            count, cost, choice = max(options, key=lambda x: (x[0], -x[1], x[2]))
            counts[i, j], costs[i, j], choices[i, j] = count, cost, choice
    pairs, used_plan, used_actual = [], set(), set()
    i = j = 0
    while i < n and j < m:
        choice = choices[i, j]
        if choice == 2:
            pairs.append([int(plan[i]), int(actual[j])])
            used_plan.add(i); used_actual.add(j)
            i += 1; j += 1
        elif choice == 1:
            j += 1
        else:
            i += 1
    return {"offset_ticks": np.asarray([a - p for p, a in pairs], dtype=float),
            "matched_pairs": pairs,
            "missing_planned_idx": [int(plan[k]) for k in range(n) if k not in used_plan],
            "unmatched_actual_idx": [int(actual[k]) for k in range(m) if k not in used_actual],
            "planned_n": n, "actual_n": m,
            "max_abs_offset_ticks_exclusive": period_ticks / 2.0}


def _circ_offsets(plan_idx: np.ndarray, actual_idx: np.ndarray,
                  period_ticks: float) -> np.ndarray:
    """Compatibility helper: offsets of local one-to-one event matches."""
    return _match_events(plan_idx, actual_idx, period_ticks)["offset_ticks"]


def _circular_median(values, period):
    values = np.asarray(values, dtype=float)
    if not len(values):
        return None
    distances = np.abs(_wrap(values[:, None] - values[None, :], period))
    anchor = values[np.argmin(distances.sum(axis=1))]
    return float(_wrap(anchor + np.median(_wrap(values - anchor, period)), period))


def _circular_spread(values, period):
    if len(values) < 2:
        return None
    v = np.sort(np.asarray(values) % period)
    gaps = np.diff(np.r_[v, v[0] + period])
    return float(period - max(gaps))


def event_offsets(plan_stance: np.ndarray, contact: np.ndarray,
                  period_ticks: float, dt_ms: float = 10.0) -> dict:
    """Contact-threshold events, not joint lag. Matching is local in time;
    phase summaries use circular statistics only AFTER unique event pairing.
    """
    plan_stance, contact = np.asarray(plan_stance), np.asarray(contact)
    if (plan_stance.shape != contact.shape or plan_stance.ndim != 2
            or plan_stance.shape[1] != 6 or len(plan_stance) < 2
            or not math.isfinite(dt_ms) or dt_ms <= 0):
        raise ValueError("expected matching (T,6) masks and positive finite dt")
    plan_edges = (_edges(plan_stance, True), _edges(plan_stance, False))
    actual_edges = (_edges(contact, True), _edges(contact, False))
    per_leg, med_td = {}, []
    period_ms = period_ticks * dt_ms
    for f in range(6):
        leg = {}
        for k, label in enumerate(("touchdown", "liftoff")):
            matched = _match_events(plan_edges[k][f], actual_edges[k][f], period_ticks)
            offsets = matched.pop("offset_ticks") * dt_ms
            median = _circular_median(offsets, period_ms)
            centered = _wrap(offsets - median, period_ms) if median is not None else []
            leg.update({f"{label}_med_ms": median,
                        f"{label}_iqr_ms": (float(np.subtract(*np.percentile(centered, [75, 25])))
                                             if len(centered) else None),
                        f"{label}_n": len(offsets),
                        f"{label}_matching": matched})
        per_leg[f] = leg
        med_td.append(leg["touchdown_med_ms"])
    finite = [m for m in med_td if m is not None]
    common = _circular_median(finite, period_ms)
    diffs = [float(_wrap(m - common, period_ms)) if m is not None else None
             for m in med_td] if common is not None else [None]*6
    return {"per_leg": per_leg, "touchdown_common_ms": common,
            "touchdown_differential_ms": diffs,
            "interleg_spread_ms": _circular_spread(finite, period_ms),
            "period_ms": period_ms,
            "matching_definition": "chronological one-to-one, abs time difference < half period; unmatched events explicit",
            "observation_definition": "last-solve touch threshold edges sampled at control rate; not endpoint contact or measured joint lag"}


def support_state_stats(loaded: np.ndarray, wz: np.ndarray,
                        vx: np.ndarray) -> dict:
    """Observed support-conditioned statistics and descriptive reweighting.
    Historical 'pureA/B' names mean >=2 of that tripod and <=1 of the
    other; they do not require a complete three-foot tripod.
    """
    nA = loaded[:, TRIPOD_A].sum(axis=1)
    nB = loaded[:, TRIPOD_B].sum(axis=1)
    pureA = (nA >= 2) & (nB <= 1)
    pureB = (nB >= 2) & (nA <= 1)
    mixed = (nA >= 2) & (nB >= 2)
    degen = ~(pureA | pureB | mixed)
    out = {"states": {},
           "population_definition": "pureA/B legacy labels: >=2 loaded feet of one tripod, <=1 of other; includes two-foot support",
           "reweighting_scope": "observed majority-tripod population mean; association only, not a causal upper bound",
           "n_total": len(wz)}
    for name, sel in (("pureA", pureA), ("pureB", pureB),
                      ("mixed", mixed), ("degenerate", degen)):
        out["states"][name] = {
            "frac": float(sel.mean()), "n": int(sel.sum()),
            "wz_mean": float(wz[sel].mean()) if sel.any() else None,
            "wz_med": float(np.median(wz[sel])) if sel.any() else None,
            "vx_mean": float(vx[sel].mean()) if sel.any() else None,
        }
    out["wz_mean_overall"] = float(wz.mean())
    out["wz_med_overall"] = float(np.median(wz))
    n_pure = int(pureA.sum() + pureB.sum())
    if n_pure:
        wz_pure_avg = float(wz[pureA | pureB].mean())
        # Preserve the historical statistic numerically. This algebra
        # equals wz_pure_avg; it does NOT bound an intervention.
        cf = float((wz[pureA | pureB].sum()
                    + (len(wz) - n_pure) * wz_pure_avg) / len(wz))
    else:
        wz_pure_avg = cf = None
    out["wz_pure_avg"] = wz_pure_avg
    out["wz_counterfactual_mean"] = cf  # legacy field retained
    out["wz_observational_reweighted_mean"] = cf
    out["pure_frac"] = n_pure / max(len(wz), 1)
    return out


def cell_gain(summary: dict, wz_cmd: float) -> float | None:
    """Historical descriptive reweighting contrast in the commanded direction.
    This association is not a predicted causal controller gain.
    """
    cf = summary.get("wz_counterfactual_mean")
    m = summary.get("wz_mean_overall")
    if cf is None or m is None or wz_cmd == 0.0 or abs(m) < 1e-9:
        return None
    return float((cf - m) * math.copysign(1.0, wz_cmd) / abs(m))


def verdict(results: list[dict], bar: dict = BAR, *, validation=None) -> dict:
    """Historical descriptive bar, separated from validated observation."""
    if validation is not None and validation.get("valid") is not True:
        return {"bar": bar, "checks": {}, "historical_bar_supported": None,
                "observational_screen_passed": False, "supported": False,
                "scope": "invalid descriptive screen; no causal or class-closure inference"}
    arcs = [r for r in results if abs(r["wz_cmd"]) > 1e-9]
    straights = [r for r in results if abs(r["wz_cmd"]) <= 1e-9]
    checks = {}
    gains = {f"({r['wz_cmd']:+.2f},{r['phase_offset']:.2f})":
             cell_gain(r["support_states"], r["wz_cmd"]) for r in arcs}
    checks["s1_gains"] = gains
    checks["s1_pass"] = (len(arcs) >= 4 and all(
        g is not None and g >= bar["s1_min_gain_frac"]
        for g in gains.values()))
    spreads = [r["events"]["interleg_spread_ms"] for r in arcs]
    checks["s2_interleg_spread_ms"] = spreads
    spread_ok = (len(spreads) > 0 and all(
        s is not None and s >= bar["s2_min_interleg_spread_ms"]
        for s in spreads))
    sign_diffs = []
    for pos in [r for r in arcs if r["wz_cmd"] > 0]:
        for neg in [r for r in arcs if r["wz_cmd"] < 0
                    and abs(r["phase_offset"] - pos["phase_offset"]) < 1e-9]:
            dp = pos["events"]["touchdown_differential_ms"]
            dn = neg["events"]["touchdown_differential_ms"]
            period_ms = pos["events"].get("period_ms", 750.0)
            pair = [abs(float(_wrap(a - b, period_ms))) for a, b in zip(dp, dn)
                    if a is not None and b is not None]
            if pair:
                sign_diffs.append(max(pair))
    checks["s2_sign_differential_ms"] = sign_diffs
    sign_ok = (len(sign_diffs) > 0
               and max(sign_diffs) >= bar["s2_min_sign_differential_ms"])
    checks["s2_pass"] = bool(spread_ok or sign_ok)
    cf_straight = [abs(r["support_states"]["wz_counterfactual_mean"])
                   for r in straights
                   if r["support_states"].get("wz_counterfactual_mean")
                   is not None]
    checks["s3_straight_cf_wz"] = cf_straight
    falls = any(r["fell"] for r in results)
    parity_ok = all(r.get("parity", {}).get("ok") for r in results)
    checks["s3_pass"] = (all(v <= bar["s3_straight_wz_cap"]
                             for v in cf_straight)
                         and not falls and parity_ok)
    checks["zero_falls"] = not falls
    checks["parity_ok"] = parity_ok
    historical = bool(checks["s1_pass"] and checks["s2_pass"] and checks["s3_pass"])
    valid = validation is not None and validation.get("valid") is True
    return {"bar": bar, "checks": checks,
            "historical_bar_supported": historical,
            "observational_screen_passed": bool(valid and historical),
            "supported": False,
            "scope": "historical observational reweighting bar only; no causal upper bound, efficacy support, class closure or qualification claim"}


def rollout(*, cfg_set, vx_cmd, wz_cmd, seed, episode_seconds,
            phase_offset=0.0, plant: str = "twin") -> dict:
    """Scripted-gait rollout; identical env-facing sequence to
    probe_turn_stancearm.rollout (parity asserted vs its baseline)."""
    env = pta.make_env(cfg_set, seed, episode_seconds)
    identity = model_identity(env)
    contract = motor_contract(env.cfg)
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

    rows = []
    step = 0
    fell = False
    while True:
        cmd_wz = float(traj.wz[min(step, n - 1)])
        cmd_vx = float(traj.vx[min(step, n - 1)])
        t = step * env.dt
        gait.set_velocity(vx=cmd_vx, omega=cmd_wz)
        q_des = np.asarray(gait.desired_deg(t)) * DEG2RAD
        act = q_rad_to_action(q_des)
        plan_swing = np.array(gait.leg_swing_state())
        obs, r, term, trunc, info = env.step(act)
        if step >= hold_n + ramp_n and info.get("goal_mode") == "walk":
            force = np.array([float(env.data.sensordata[x]) if x >= 0 else float("nan")
                              for x in env._touch_adr])
            rows.append({"plan_swing": plan_swing, "force": force,
                         "vx_body": float(env._body_vel_xy()[0]),
                         "wz_body": float(env._body_wz())})
        step += 1
        if term:
            fell = True
        if term or trunc:
            break
    env.close()

    out = {"policy": "scripted", "vx_cmd": vx_cmd, "wz_cmd": wz_cmd,
           "seed": seed, "phase_offset": phase_offset, "fell": fell,
           "n_scored_ticks": len(rows), "model_identity": identity,
           "period_eff_s": gait.period * gait.period_scale,
           "sampling": {"control_dt_s": float(env.dt),
                        "physics_dt_s": float(env.model.opt.timestep),
                        "contact_threshold_N": CONTACT_N, "loaded_threshold_N": LOAD_N,
                        "contact_time": "last physics solve at post-step data.time minus physics_dt_s",
                        "plan_time": "gait phase used to command the completed control interval",
                        "velocity_scope": "legacy body velocity helpers preserved for parity; not endpoint course integration",
                        "joint_lag_measured": False},
           "motor_contract": {k: contract[k] for k in
                              ("bus.write_speed", "bus.write_acc",
                               "safety.max_delta_q_deg", "slew_limit_deg_s",
                               "resolved_vel_max_counts_s_max",
                               "control.hz")}}
    if len(rows) < 200:
        out["error"] = "insufficient scored ticks"
        return out

    force = np.stack([r["force"] for r in rows])
    contact = force > CONTACT_N
    loaded = force > LOAD_N
    plan_stance = ~np.stack([r["plan_swing"] for r in rows]).astype(bool)
    wz = np.array([r["wz_body"] for r in rows])
    vx = np.array([r["vx_body"] for r in rows])

    out["body"] = {"vx_med": float(np.median(vx)),
                   "wz_med": float(np.median(wz))}
    ref = next((v for k, v in PARITY_REF.items()
                if _key(*k) == _key(vx_cmd, wz_cmd, phase_offset)), None)
    if ref is not None:
        out["parity"] = {
            "ref_wz_med": ref[0], "ref_vx_med": ref[1],
            "ref_n_scored_ticks": ref[2],
            "ok": bool(out["body"]["wz_med"] == ref[0]
                       and out["body"]["vx_med"] == ref[1]
                       and len(rows) == ref[2]),
            "scope": "body medians + scored tick count vs the stance-arm "
                     "baseline (summary parity, not trajectory parity)"}
    else:
        out["parity"] = {"ok": None, "scope": "no pinned reference cell"}

    period_ticks = gait.period * gait.period_scale / env.dt
    out["events"] = event_offsets(plan_stance, contact, period_ticks)
    out["duty_contact"] = contact.mean(axis=0).round(4).tolist()
    out["duty_loaded"] = loaded.mean(axis=0).round(4).tolist()
    out["support_states"] = support_state_stats(loaded, wz, vx)
    return out


def _key(vx, wz, phase):
    return round(float(vx), 6), round(float(wz), 6), round(float(phase) % (2*math.pi), 6)


def validate_matrix(results, *, feasibility=None, plant="fullmesh", seed=0,
                    episode_seconds=15.0):
    reasons = _feasibility_reasons(feasibility)
    expected = {_key(*k): ref for k, ref in PARITY_REF.items()}
    keys = []
    if plant != "fullmesh" or seed != 0 or episode_seconds != 15.0:
        reasons.append("validation requires frozen fullmesh, seed0, 15-second matrix")
    for i, r in enumerate(results):
        try:
            key = _key(r["vx_cmd"], r["wz_cmd"], r["phase_offset"])
            keys.append(key)
            ref = expected.get(key)
        except (KeyError, ValueError, TypeError):
            reasons.append(f"cell {i}: invalid identity"); ref = None
        if _nonfinite(r):
            reasons.append(f"cell {i}: nonfinite data")
        if r.get("error") or r.get("fell") is not False or r.get("seed") != seed:
            reasons.append(f"cell {i}: error, fall, or seed mismatch")
        ident = r.get("model_identity", {})
        if (ident.get("model_variant") != "full_mesh" or ident.get("model_nmesh") != 34
                or ident.get("model_mass_kg") != PIN["model_mass_kg"]):
            reasons.append(f"cell {i}: frozen model identity mismatch")
        body = r.get("body", {})
        if (ref is None or r.get("parity", {}).get("ok") is not True
                or body.get("wz_med") != ref[0] or body.get("vx_med") != ref[1]
                or r.get("n_scored_ticks") != ref[2]):
            reasons.append(f"cell {i}: missing or failed exact parity")
        states, events = r.get("support_states", {}), r.get("events", {})
        if not all(_finite_number(states.get(k)) for k in
                   ("wz_mean_overall", "wz_counterfactual_mean")):
            reasons.append(f"cell {i}: missing finite support-state measurements")
        if (not _finite_number(events.get("interleg_spread_ms"))
                or len(events.get("touchdown_differential_ms", [])) != 6
                or not all(_finite_number(v) for v in events.get("touchdown_differential_ms", []))):
            reasons.append(f"cell {i}: incomplete event signal")
        per_leg = events.get("per_leg", {})
        if len(per_leg) != 6 or any(v.get("touchdown_n", 0) < 2 for v in per_leg.values()):
            reasons.append(f"cell {i}: fewer than two matched touchdown events on a leg")
    if len(keys) != len(set(keys)):
        reasons.append("duplicate matrix cells")
    if len(results) != 6 or set(keys) != set(expected):
        reasons.append("expected exactly four unique arcs plus two straight cells")
    return {"valid": not reasons, "reasons": reasons}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg-json", type=Path, required=True)
    ap.add_argument("--cells", required=True, help="vx:wz,...")
    ap.add_argument("--phase-offsets", default="0.0")
    ap.add_argument("--plant", choices=("twin", "fullmesh"), default="twin")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg_set = json.loads(args.cfg_json.read_text())
    cfg_set = [c for c in cfg_set if not c.startswith("env.model_source=")]
    cfg_set.append("env.model_source=" + ("mesh" if args.plant == "fullmesh" else "mesh_mjx"))
    cells = [tuple(float(x) for x in c.split(":")) for c in args.cells.split(",")]
    phases = [float(x) for x in args.phase_offsets.split(",")]
    results, errors = [], []
    feas = pins = None
    try:
        requested = [_key(vx, wz, po) for vx, wz in cells for po in phases]
        expected = {_key(*k) for k in PARITY_REF}
        if len(requested) != 6 or len(set(requested)) != 6 or set(requested) != expected:
            errors.append("expected exactly four unique arcs plus two straight cells")
    except (ValueError, TypeError):
        errors.append("invalid requested matrix")
    if not errors:
        try:
            pins = pin_manifest(args.plant)
            feas = feasibility_guard(*pta.WALK_PLANT, cells)
            errors.extend(_feasibility_reasons(feas))
        except (SystemExit, RuntimeError, ValueError) as exc:
            errors.append(f"pin/feasibility failed: {exc}")
    if not errors:
        for vx, wz in cells:
            for po in phases:
                r = rollout(cfg_set=cfg_set, vx_cmd=vx, wz_cmd=wz, seed=args.seed,
                            episode_seconds=args.episode_seconds, phase_offset=po,
                            plant=args.plant)
                results.append(r)
    validation = validate_matrix(results, feasibility=feas, plant=args.plant,
                                 seed=args.seed, episode_seconds=args.episode_seconds)
    validation["reasons"] = errors + validation["reasons"]
    validation["valid"] = not validation["reasons"]
    # Malformed results must not enter the descriptive arithmetic. Invalid
    # numeric outputs still yield a strict JSON receipt and failed validation.
    v = (verdict(results, validation=validation) if validation["valid"] else
         {"bar": BAR, "checks": {}, "historical_bar_supported": None,
          "observational_screen_passed": False, "supported": False,
          "scope": "invalid descriptive screen; no causal or class-closure inference"})
    out = {"schema": "hexapod.turn_eventsync_probe.v2", "label": args.label,
           "policy": "scripted", "plant": args.plant, "cfg_set": cfg_set,
           "seed": args.seed, "episode_seconds": args.episode_seconds,
           "stance_hip_deg": pta.WALK_PLANT[0], "stance_knee_deg": pta.WALK_PLANT[1],
           "feasibility": feas, "pin_manifest": pins, "pin_expect": PIN,
           "validation": validation, "support_verdict": v, "results": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(_json_safe(out), indent=1, default=float, allow_nan=False)+"\n")
    print(json.dumps({"validation": validation, "support_verdict": v}), flush=True)
    print("COMPLETE", args.out, flush=True)
    return 0 if validation["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
