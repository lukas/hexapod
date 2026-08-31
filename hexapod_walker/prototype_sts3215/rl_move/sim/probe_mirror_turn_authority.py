"""probe_mirror_turn_authority.py — zero-training mirror-reflection
test for the standwalk turn-authority asymmetry.

WHY (standwalk STATUS 08-31 ~10:4x): the pre-RL `dualbc5_turncap`
distilled checkpoint (and every RL canary built on top of it — 8
independently-designed mechanism classes, all FAIL) shows a starkly
ASYMMETRIC closed-loop turn-in-place response: wz_cmd=-0.25 gives a
real partial escape off frozen-body (`probe_turn_authority` wz_med
~-0.038/-0.048), wz_cmd=+0.25 stays fully frozen (~0.00003)
(RL_LOG 08-31 02:35). The 08-31 ~10:4x dataset audit refuted BOTH the
dataset-coverage-imbalance hypothesis (tip episodes 9+/8-, balanced)
AND the BC/DAgger open-loop-optimization hypothesis (per-tick action
MSE turn+ 0.00066 vs turn- 0.00062, within 8% of each other) —
leaving CLOSED-LOOP COMPOUNDING of tiny symmetric per-tick biases as
the next-named suspect (tick-by-tick hidden-state/action trace, not
yet built).

This tool tests a cheaper, more directly ACTIONABLE hypothesis first,
reusing the existing rot60/mirror walk-drift precedent (RL_PLAN queue
0.2, `mirror.py`, `probe_mirror_turn.py`): the hexapod has an
(approximate) sagittal mirror symmetry, and `mirror.MirrorPolicy`
already encodes the full obs/action relabeling including the `wz_ref`
sign flip. IF that reflection holds for this checkpoint, mirroring the
policy and feeding it wz_cmd=+0.25 is ALGEBRAICALLY the same computation
as feeding the NAKED policy wz_cmd=-0.25 (which demonstrably has a real
partial escape) and flipping the resulting action back — so the mirror
wrapper should reproduce that partial escape on the currently-frozen
`+` sign, with ZERO additional training. If it does, the fix for
turn authority is not another RL mechanism class or an architecture
rebuild — it is composition: run the mirrored policy for one commanded
sign and the naked policy for the other (exactly the existing
heading-hold precedent), immediately promotable to a canary test.
If mirroring does NOT reproduce the escape (mirror(+0.25) stays frozen
like naked(+0.25), and/or mirror(-0.25) does not reproduce naked's
frozen +0.25), the defect survives reflection — ruling out the cheap
compositional fix and pointing harder at the closed-loop-compounding /
architecture hypothesis the dataset audit already flagged as next.

Usage:
  uv run python -m rl_move.sim.probe_mirror_turn_authority \
      rl_move/sim/policies/ppo_goal_cw_standwalk_stage2_dualbc5_turncap.zip \
      --out logs/ckpt_eval/mirror_turn_authority_dualbc5_turncap.json
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import argparse
import json
from pathlib import Path

import numpy as np

from .audit_turn_dataset import TURNCAP_CFG_SET
from .probe_turn_authority import _load_model, make_env, rollout

FWD_CMD_V = 0.08  # champion-band forward speed (matches this cfg-set's
                  # walk_speed_min/max_m_s=0.08 in TURNCAP_CFG_SET)


# Campaign-standard absolute bars (probe_turn_authority's own FAIL/PASS
# convention used across all 8 mechanism-class canary verdicts this
# lineage has recorded, RL_LOG 08-31): wz_med < FAIL_FLOOR both signs is
# the "frozen-body" FAIL read every one of those canaries hit;
# wz_med >= PASS_FLOOR both signs is the mechanism-health PASS bar none
# of them cleared. A relative frozen_margin*|wz_cmd| bar (the
# probe_turn_authority.summarize() convention, built for a DIFFERENT
# question — "does this clear HALF the commanded rate") is too strict
# to be informative here: not even the naked checkpoint's own partial
# escape clears it. Use the absolute bars this campaign actually
# verdicts against instead.
FAIL_FLOOR = 0.03
PASS_FLOOR = 0.08


def run(checkpoint: Path, wz_cmds: list[float], seeds: list[int],
        episode_seconds: float, cfg_set: list[str],
        frozen_margin: float, check_straight_walk: bool = False) -> dict:
    from .mirror import MirrorPolicy

    model, obs_width = _load_model(checkpoint)
    mirror = MirrorPolicy(model, walk=True, yaw_cmd=True, phase_obs=True,
                          mode_onehot=True, obs_dim=obs_width)
    env_kwargs = {"cfg_set": cfg_set}

    results: dict[str, list[dict]] = {"naked": [], "mirror": []}
    for label, pol in (("naked", model), ("mirror", mirror)):
        for wz_cmd in wz_cmds:
            for seed in seeds:
                res = rollout(model=pol, env_cls_kwargs=env_kwargs,
                              wz_cmd=wz_cmd, seed=seed,
                              episode_seconds=episode_seconds,
                              policy="checkpoint",
                              model_obs_width=obs_width)
                results[label].append(res)

    straight_walk = None
    if check_straight_walk:
        straight_walk = straight_walk_check(
            checkpoint, seeds, episode_seconds, cfg_set, obs_width,
            model, mirror)

    def med_by_cmd(label: str, wz_cmd: float) -> float | None:
        vals = [r["wz_med"] for r in results[label]
                if r["wz_cmd"] == wz_cmd and r["wz_med"] is not None]
        return float(np.median(vals)) if vals else None

    cross = {}
    for wz_cmd in wz_cmds:
        naked_med = med_by_cmd("naked", wz_cmd)
        mirror_med = med_by_cmd("mirror", wz_cmd)
        cross[str(wz_cmd)] = {"naked_wz_med": naked_med,
                              "mirror_wz_med": mirror_med}

    # Decisive read against the CAMPAIGN'S OWN absolute bars (see
    # FAIL_FLOOR/PASS_FLOOR above), not a relative margin: for the sign
    # naked is frozen on (below FAIL_FLOOR), does mirroring produce a
    # same-signed escape that clears FAIL_FLOOR (a genuine improvement
    # over every RL mechanism class, all of which stayed <0.03 both
    # signs post-RL) and/or the full PASS_FLOOR?
    escapes = {}
    for wz_cmd in wz_cmds:
        naked_med = cross[str(wz_cmd)]["naked_wz_med"]
        mirror_med = cross[str(wz_cmd)]["mirror_wz_med"]
        if naked_med is None or mirror_med is None:
            continue
        naked_frozen = abs(naked_med) < FAIL_FLOOR
        same_sign = mirror_med * wz_cmd > 0
        mirror_clears_fail_floor = same_sign and abs(mirror_med) >= FAIL_FLOOR
        mirror_clears_pass_floor = same_sign and abs(mirror_med) >= PASS_FLOOR
        escapes[str(wz_cmd)] = {
            "naked_frozen_below_0p03": naked_frozen,
            "mirror_clears_0p03_same_sign": bool(mirror_clears_fail_floor),
            "mirror_clears_0p08_pass_same_sign": bool(mirror_clears_pass_floor),
        }

    any_escape = any(v["naked_frozen_below_0p03"]
                     and v["mirror_clears_0p03_same_sign"]
                     for v in escapes.values())
    any_pass = any(v["mirror_clears_0p08_pass_same_sign"]
                   for v in escapes.values())
    verdict = ("MIRROR-PASS" if any_pass else
               "MIRROR-ESCAPE (beats the 0.03 frozen floor, below 0.08 PASS)"
               if any_escape else
               "NO-FIX (asymmetry survives reflection)")

    return {
        "checkpoint": str(checkpoint),
        "wz_cmds": wz_cmds,
        "seeds": seeds,
        "cross": cross,
        "escapes": escapes,
        "verdict": verdict,
        "results": results,
        "straight_walk": straight_walk,
    }


def straight_walk_check(checkpoint: Path, seeds: list[int],
                        episode_seconds: float, cfg_set: list[str],
                        model_obs_width: int, model, mirror) -> dict:
    """Sanity gate for the mirror-composition idea: wz_cmd=0 is
    mirror-INVARIANT (mirroring negates wz_ref, but 0 stays 0), so a
    genuine reflection should leave ordinary forward walking basically
    intact (same gait competence, mirrored limb phasing) — exactly the
    already-validated `probe_mirror_turn.py` precedent on other
    lineages. If mirroring instead collapses/drags on THIS dual-core
    architecture, the turn-authority escape above is not composable
    with a working walk and the compositional fix is dead regardless
    of the wz numbers."""
    out = {}
    for label, pol in (("naked", model), ("mirror", mirror)):
        rows = []
        for seed in seeds:
            env = make_env(cfg_set, seed, episode_seconds,
                           mode_onehot=True)
            obs, info = env.reset()
            if hasattr(pol, "reset"):
                pol.reset()
            traj = env._goal_traj
            hold_n = ramp_n = int(round(1.0 / env.dt))
            ramp = np.linspace(0.0, 1.0, ramp_n)
            traj.vx[:] = FWD_CMD_V
            traj.vx[:hold_n] = 0.0
            traj.vx[hold_n:hold_n + ramp_n] = FWD_CMD_V * ramp
            traj.vy[:] = 0.0
            traj.wz[:] = 0.0
            p0 = env.data.xpos[env._chassis_bid][:2].copy()
            fell = False
            n_walk = 0
            while True:
                act, _ = pol.predict(obs, deterministic=True)
                obs, r, term, trunc, info = env.step(act)
                if info.get("goal_mode") == "walk":
                    n_walk += 1
                if term:
                    fell = True
                if term or trunc:
                    break
            p1 = env.data.xpos[env._chassis_bid][:2]
            travel_x = float(p1[0] - p0[0])
            env.close()
            rows.append({"seed": seed, "travel_x_m": round(travel_x, 4),
                        "fell": fell, "n_walk_ticks": n_walk})
        out[label] = rows
    naked_travel = float(np.median(
        [r["travel_x_m"] for r in out["naked"]]))
    mirror_travel = float(np.median(
        [r["travel_x_m"] for r in out["mirror"]]))
    any_fell = any(r["fell"] for rows in out.values() for r in rows)
    travel_ok = (mirror_travel >= 0.7 * naked_travel
                if naked_travel > 0 else False)
    out["summary"] = {"naked_travel_x_m": naked_travel,
                      "mirror_travel_x_m": mirror_travel,
                      "travel_ok": travel_ok, "any_fell": any_fell}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("--wz-cmds", default="0.25,-0.25")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--frozen-margin", type=float, default=0.5)
    ap.add_argument("--cfg-set", action="append", default=None,
                    help="extend the built-in TURNCAP_CFG_SET recipe")
    ap.add_argument("--check-straight-walk", action="store_true",
                    help="also run the forward-walk (wz=0, mirror-"
                         "invariant command) gait-health sanity check "
                         "— does mirroring break ordinary walking?")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    cfg_set = list(TURNCAP_CFG_SET) + list(args.cfg_set or [])
    wz_cmds = [float(x) for x in args.wz_cmds.split(",") if x.strip()]
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]

    out = run(args.checkpoint, wz_cmds, seeds, args.episode_seconds,
              cfg_set, args.frozen_margin,
              check_straight_walk=args.check_straight_walk)

    for wz_cmd in wz_cmds:
        c = out["cross"][str(wz_cmd)]
        e = out["escapes"].get(str(wz_cmd), {})
        print(f"[mirror-turn-authority] wz_cmd={wz_cmd:+.2f}  "
              f"naked_wz_med={c['naked_wz_med']}  "
              f"mirror_wz_med={c['mirror_wz_med']}  "
              f"naked_frozen<0.03={e.get('naked_frozen_below_0p03')}  "
              f"mirror_clears_0.03={e.get('mirror_clears_0p03_same_sign')}  "
              f"mirror_clears_0.08={e.get('mirror_clears_0p08_pass_same_sign')}")
    print(f"[mirror-turn-authority] VERDICT: {out['verdict']}")
    if out.get("straight_walk"):
        s = out["straight_walk"]["summary"]
        print(f"[mirror-turn-authority] straight-walk sanity: "
              f"naked_travel={s['naked_travel_x_m']}m "
              f"mirror_travel={s['mirror_travel_x_m']}m "
              f"travel_ok={s['travel_ok']} any_fell={s['any_fell']}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, indent=2))
        print(f"[mirror-turn-authority] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
