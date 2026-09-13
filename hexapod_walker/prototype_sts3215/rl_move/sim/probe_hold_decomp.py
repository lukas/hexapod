"""Hold reward-decomposition probe (2026-09-13, mixreweight-canary2m
FAIL-MECHANISM follow-up).

The demonstration-free from-scratch 50 Hz stance recipe's hold role has
now failed IDENTICALLY twice: the original canary2m (goal-mix
hold=0.1/rise=0.45/lower=0.45) and mixreweight-canary2m (hold=0.4/
rise=0.3/lower=0.3, seeds 0 AND 1) both show 0/6 hold/det survived_frac
at 2M with the SAME OC-pin-freeze fingerprint (cur_max_a ~2.58-2.64A
pinned, identical-return collapse, height_err ~40mm flat/regressing).
Per that gate's own pre-registered FAIL-MECHANISM next-lever clause,
4x more hold exposure ruling out an exposure cause means the next
question is WHICH hold-specific reward term (hold_still_gate/
hold_feet_load/k_current_hot) is pricing the collapse rather than
preventing it.

This probe rolls the ACTUAL failed checkpoint through one
deterministic hold episode with the run's own launch cfg (p_hold=1 so
every episode starts at the plant/risen state, matching the gate's own
observed start_kind="plant") and prints the per-tick reward-term
decomposition sim_env.py's HOLD block computes (hold_feet_factor,
hold_still_factor, hold_load_factor, reward_task, reward_termination)
alongside current/height, so the collapse mechanism is visible directly
instead of inferred from the aggregate return. No training, no
gradient steps, no scripted/demonstration behavior anywhere -- reads
the checkpoint's own policy only.

Usage (CPU is fine, one episode ~1-15s wall):
  uv run python -m rl_move.sim.probe_hold_decomp \
      --ckpt rl_move/sim/policies/ppo_goal_cw_stance50hz_rlonly_scratch_s0_mixreweight_canary2m.zip \
      [--seed 0] [--episode-seconds 15] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from rl_move.config import load_config
from rl_move.sim.joint_task import SimHexapodJointGoalEnv
from rl_move.sim.servo_model import SimServoParams

# Verbatim from the mixreweight-canary2m / canary2m launch ledger
# extra_args (training-only knobs like --steps/--n-envs/--goal-mix
# omitted; goal-mix is applied via gen.p_* below instead, matching
# probe_stance_pricing.py's established pattern).
LAUNCH_OVERRIDES = {
    ("env", "model_source"): "mesh_mjx",
    ("control", "hz"): 50.0,
    ("safety", "max_delta_q_deg"): 0.75,
    ("actions", "max_height_mm"): 88.0,
    ("goal", "rise_height_mm"): [79.0, 87.0],
    ("goal", "rise_ramp_s"): 6.0,
    ("goal", "rise_hold_min_s"): 0.5,
    ("reward", "rise_score_income"): 1.0,
    ("reward", "rise_score_strip_pen"): 1.0,
    ("reward", "rise_posture_gate"): 1.0,
    ("reward", "rise_income_prog_gate"): 1.0,
    ("reward", "rise_finish_gate_signed"): 1.0,
    ("reward", "hold_still_gate"): 1.0,
    ("reward", "hold_flag_fade"): 1.0,
    ("reward", "k_current_hot"): 1.0,
    ("reward", "current_hot_a"): 2.0,
    ("reward", "term_cost_per_remaining_s"): 3.0,
    ("reward", "term_cost_max"): 60.0,
    ("reward", "hold_feet_load"): 1.0,
    ("reward", "hold_feet_load_min"): 1.0,
    ("safety", "hold_max_height_drop_mm"): 40.0,
    ("safety", "hold_height_grace_s"): 1.0,
    ("safety", "hold_min_load_terminate_s"): 1.0,
    ("safety", "hold_min_load_terminate_n"): 0.3,
    ("safety", "hold_min_load_terminate_grace_s"): 1.0,
}

_TRACK_KEYS = (
    "reward_task", "reward_termination", "hold_feet_factor",
    "hold_still_factor", "hold_load_factor", "max_current_a",
    "height_mm",
)


def _make_env(seed: int, episode_seconds: float) -> SimHexapodJointGoalEnv:
    cfg = load_config()
    for (sec, leaf), val in LAUNCH_OVERRIDES.items():
        cfg.setdefault(sec, {})[leaf] = val
    env = SimHexapodJointGoalEnv(
        params=SimServoParams.from_cfg(cfg), randomize=False,
        dr_scale=0.0, episode_seconds=episode_seconds, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for a in [a for a in vars(gen) if a.startswith("p_")]:
        setattr(gen, a, 0.0)
    gen.p_hold = 1.0
    return env


def _rollout(model, env, behavior: str = "policy") -> list[dict]:
    """``behavior='policy'``: the checkpoint's own actor (deterministic).
    ``behavior='hold_quiet'``: constant action == the plant pose the
    episode reset into (q0, unchanged for the whole episode) -- an
    honest, zero-intelligence "do nothing, stay put" baseline. If THIS
    also sinks and terminates, the collapse is a physics/actuator-
    authority ceiling independent of anything the policy chose (rules
    out a reward-shaping fix), not a policy failure to hold.
    """
    obs, _ = env.reset()
    state, ep_start = None, np.ones((1,), dtype=bool)
    q0_action = None
    if behavior == "hold_quiet":
        from rl_move.sim.joint_task import q_rad_to_action
        q0_action = q_rad_to_action(env._state.joint_position.copy())
    rows: list[dict] = []
    term = trunc = False
    step = 0
    while not (term or trunc):
        if behavior == "hold_quiet":
            act = q0_action
        else:
            act, state = model.policy.predict(
                obs, state=state, episode_start=ep_start, deterministic=True)
            ep_start = np.zeros((1,), dtype=bool)
        obs, r, term, trunc, info = env.step(np.asarray(act).ravel())
        row = {"t": round(step * env.dt, 3), "r": round(float(r), 3),
               "term_reason": info.get("termination_reason")}
        for k in _TRACK_KEYS:
            v = info.get(k)
            row[k] = round(float(v), 4) if v is not None else None
        rows.append(row)
        step += 1
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--behavior", choices=("policy", "hold_quiet"),
                    default="policy")
    args = ap.parse_args()

    model = None
    if args.behavior == "policy":
        from rl_move.sim.gru_policy import load_checkpoint_auto
        model = load_checkpoint_auto(args.ckpt, device="cpu")
    env = _make_env(args.seed, args.episode_seconds)
    rows = _rollout(model, env, behavior=args.behavior)

    print(f"[probe_hold_decomp] {args.ckpt.name} seed={args.seed} "
          f"{len(rows)} ticks ({rows[-1]['t'] if rows else 0}s)")
    for row in rows:
        print(row)
    if rows:
        term_row = rows[-1]
        print(f"[probe_hold_decomp] FINAL term_reason="
              f"{term_row['term_reason']} at t={term_row['t']}s")
        # First vs last non-terminal tick, so a trend is visible
        # without reading the whole per-tick dump.
        body = [r for r in rows if r.get("hold_feet_factor") is not None]
        if body:
            first, last = body[0], body[-1]
            print("[probe_hold_decomp] first tick:", first)
            print("[probe_hold_decomp] last body tick:", last)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, indent=1))
        print(f"[probe_hold_decomp] wrote {args.json}")


if __name__ == "__main__":
    main()
