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
    # NOTE (2026-09-13, holdbarrier follow-up): the sinkfence/holdgrace/
    # holdbarrier lineage tightened this envelope to 15mm/0.5s -- this
    # module's own zero-intelligence baselines (hold_quiet/noise) don't
    # depend on the bound's exact value (they either drift or don't
    # regardless of where the wall is), but any probe reading
    # term_reason/height_err against "the bound" should use THIS
    # lineage's actual value, not the older 40mm/1.0s mixreweight one.
    ("safety", "hold_max_height_drop_mm"): 15.0,
    ("safety", "hold_height_grace_s"): 0.5,
    ("safety", "hold_min_load_terminate_s"): 1.0,
    ("safety", "hold_min_load_terminate_n"): 0.3,
    ("safety", "hold_min_load_terminate_grace_s"): 1.0,
}

_TRACK_KEYS = (
    "reward_task", "reward_termination", "hold_feet_factor",
    "hold_still_factor", "hold_load_factor", "max_current_a",
    "height_mm",
)

# Mode-specific extra keys (2026-09-13, s1-holdbias-riselower15m dig-in:
# rise/lower park in a crouch attractor while hold stays solid — the
# question is WHICH terms pay for parking vs completing the motion).
# Only added when --mode != hold, so the default hold read stays
# bit-exact with every prior probe invocation.
_MODE_EXTRA_KEYS = {
    "rise": (
        "height_ref_mm", "reward_height", "reward_rise_progress",
        "reward_rise_finish", "reward_rise_milestone",
        "reward_curl_progress", "reward_curl_milestone",
        "reward_rise_score_prog", "reward_rise_score_hold", "rise_score",
        "rise_income_factor", "rise_posture_factor", "rise_feet_factor",
        "rise_plant_factor",
    ),
    "lower": (
        "height_ref_mm", "reward_height", "reward_curl_progress",
        "reward_curl_milestone",
    ),
}


def _parse_cfg_set(items: list[str]) -> dict[tuple[str, str], object]:
    """``section.leaf=value`` strings -> override dict (values parsed as
    JSON when possible, else kept as strings) — the launcher's own
    --cfg-set convention, so a probe can replay ANY run's exact launch
    cfg on top of the baked mixreweight-era LAUNCH_OVERRIDES (2026-09-13,
    s1-holdbias-riselower15m dig-in: that lineage's
    goal.joint_action_bias_*_deg centering is not in the baked dict and
    without it the checkpoint's action mapping is wrong)."""
    out: dict[tuple[str, str], object] = {}
    for item in items:
        key, _, raw = item.partition("=")
        sec, _, leaf = key.partition(".")
        try:
            val: object = json.loads(raw)
        except json.JSONDecodeError:
            val = raw
        out[(sec, leaf)] = val
    return out


def _make_env(seed: int, episode_seconds: float, mode: str = "hold",
              rise_start: str | None = None,
              cfg_set: dict[tuple[str, str], object] | None = None,
              ) -> SimHexapodJointGoalEnv:
    cfg = load_config()
    for (sec, leaf), val in LAUNCH_OVERRIDES.items():
        cfg.setdefault(sec, {})[leaf] = val
    for (sec, leaf), val in (cfg_set or {}).items():
        cfg.setdefault(sec, {})[leaf] = val
    env = SimHexapodJointGoalEnv(
        params=SimServoParams.from_cfg(cfg), randomize=False,
        dr_scale=0.0, episode_seconds=episode_seconds, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for a in [a for a in vars(gen) if a.startswith("p_")]:
        setattr(gen, a, 0.0)
    setattr(gen, f"p_{mode}", 1.0)
    if rise_start is not None:
        gen.force_rise_start = rise_start
    return env


def _rollout(model, env, behavior: str = "policy",
             noise_std: float = 0.0, noise_seed: int = 0,
             extra_keys: tuple[str, ...] = ()) -> list[dict]:
    """``behavior='policy'``: the checkpoint's own actor (deterministic).
    ``behavior='hold_quiet'``: constant action == the plant pose the
    episode reset into (q0, unchanged for the whole episode) -- an
    honest, zero-intelligence "do nothing, stay put" baseline. If THIS
    also sinks and terminates, the collapse is a physics/actuator-
    authority ceiling independent of anything the policy chose (rules
    out a reward-shaping fix), not a policy failure to hold.
    ``behavior='noise'``: no policy at all -- ``q0_action`` (the SAME
    correct absolute-joint target ``hold_quiet`` holds constant) plus
    i.i.d. Gaussian jitter of std ``noise_std`` per joint per tick,
    clipped to [-1, 1] (2026-09-13, holdbarrier FAIL-MECHANISM
    follow-up). Answers the question ``hold_quiet`` alone cannot:
    how much of the PPO exploration std (``--log-std-init``, a
    training-only knob, not a reward term) is survivable if the
    policy's MEAN were already correct? Sweep ``noise_std`` across a
    checkpoint's own logged ``train/std`` trajectory (1.0 at
    ``log_std_init=0`` down to the annealed final) to find the
    survivable threshold independent of any reward-shaping question.
    """
    obs, _ = env.reset()
    state, ep_start = None, np.ones((1,), dtype=bool)
    q0_action = None
    rng = None
    if behavior in ("hold_quiet", "noise"):
        from rl_move.sim.joint_task import q_rad_to_action
        q0_action = q_rad_to_action(env._state.joint_position.copy())
    if behavior == "noise":
        rng = np.random.default_rng(noise_seed)
    rows: list[dict] = []
    term = trunc = False
    step = 0
    while not (term or trunc):
        if behavior == "hold_quiet":
            act = q0_action
        elif behavior == "noise":
            act = np.clip(q0_action + rng.normal(0.0, noise_std,
                                                  size=q0_action.shape),
                          -1.0, 1.0)
        else:
            act, state = model.policy.predict(
                obs, state=state, episode_start=ep_start, deterministic=True)
            ep_start = np.zeros((1,), dtype=bool)
        obs, r, term, trunc, info = env.step(np.asarray(act).ravel())
        row = {"t": round(step * env.dt, 3), "r": round(float(r), 3),
               "term_reason": info.get("termination_reason")}
        for k in _TRACK_KEYS + tuple(extra_keys):
            v = info.get(k)
            row[k] = round(float(v), 4) if v is not None else None
        # Per-leg ground-truth touch forces (2026-09-13, holdgraceslow
        # hold_min_load dig-in): the SAME measurement the hold_min_load
        # termination EMA tracks (_minload_min_force_now), but kept
        # per-leg so WHICH foot unloads (and whether it is one flag leg
        # or a rocking set) is visible directly. Read-only diagnostic.
        try:
            legf = []
            for i in range(6):
                if env._touch_adr[i] >= 0:
                    legf.append(round(max(float(
                        env.data.sensordata[env._touch_adr[i]]), 0.0), 2))
                else:
                    legf.append(None)
            row["leg_f_n"] = legf
            row["min_f_n"] = (min(f for f in legf if f is not None)
                              if any(f is not None for f in legf) else None)
            row["minload_ema"] = round(float(
                getattr(env, "_hold_minload_ema", float("nan"))), 3)
        except Exception:
            pass
        rows.append(row)
        step += 1
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--behavior", choices=("policy", "hold_quiet", "noise"),
                    default="policy")
    ap.add_argument("--noise-std", type=float, default=0.0,
                     help="only for --behavior noise: per-joint Gaussian "
                          "jitter std added to the correct q0 action")
    ap.add_argument("--mode", choices=("hold", "rise", "lower"),
                    default="hold",
                    help="episode goal mode (default hold = legacy "
                         "bit-exact probe behavior)")
    ap.add_argument("--rise-start", choices=("flat", "bridge", "crouch"),
                    default=None,
                    help="pin the rise start kind (only --mode rise)")
    ap.add_argument("--cfg-set", action="append", default=[],
                    metavar="SEC.LEAF=VAL",
                    help="extra cfg overrides applied AFTER the baked "
                         "LAUNCH_OVERRIDES (launcher convention); pass "
                         "the probed run's own cfg_set here")
    args = ap.parse_args()

    model = None
    if args.behavior == "policy":
        from rl_move.sim.gru_policy import load_checkpoint_auto
        model = load_checkpoint_auto(args.ckpt, device="cpu")
    env = _make_env(args.seed, args.episode_seconds, mode=args.mode,
                    rise_start=args.rise_start,
                    cfg_set=_parse_cfg_set(args.cfg_set))
    rows = _rollout(model, env, behavior=args.behavior,
                     noise_std=args.noise_std, noise_seed=args.seed,
                     extra_keys=_MODE_EXTRA_KEYS.get(args.mode, ()))

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
        # Per-term episode totals (2026-09-13): what actually pays over
        # the whole episode, so "parking is/isn't reward-optimal" is a
        # single read instead of eyeballing per-tick dumps.
        totals: dict[str, float] = {}
        for r_ in rows:
            for k, v in r_.items():
                if isinstance(v, float) and (k.startswith("reward")
                                             or k == "r"):
                    totals[k] = totals.get(k, 0.0) + v
        print("[probe_hold_decomp] episode term totals:",
              {k: round(v, 2) for k, v in sorted(totals.items())})
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, indent=1))
        print(f"[probe_hold_decomp] wrote {args.json}")


if __name__ == "__main__":
    main()
