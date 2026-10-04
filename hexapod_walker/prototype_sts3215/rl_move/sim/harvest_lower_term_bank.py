"""Harvest a `goal.lower_term_bank` npz (q_rad robot_abs + qvel_mujoco +
target_m, v2 qvel-carrying + height-target-carrying format) of ALREADY-
CONVERGED post-ramp terminal states from a trained `lower`-role
champion's OWN successful rollouts -- the data-collection half of the
"composed sub-controller dedicated to the terminal-hold phase" lever
named in walkcurr/STATUS.md Next item 6 (the one remaining escalation
after 7 named reward/curriculum/perturbation mechanisms against the
converged 2-leg(L2+L5) terminal-support habit all CLOSED, see
`lowerrole_terminal_support_forensics_2026-10-02/SUMMARY.md` item 1 for
the specific "hold-phase-only training variant" this bank feeds).

Runs N standalone `lower`-mode episodes with the given checkpoint
(goal-mix lower=1.0, the SAME cfg-set as training), and on every
episode that ends `lower_ok` (not terminated, |height_err_end_mm|<=15,
same rule of thumb as eval_lifecycle_handoff_rlonly.py's lower_phase),
samples rows from the LATE window of the episode (after the ramp has
provably completed -- goal.lower_hold_s + lower_ramp_s, plus a settle
margin -- so every row is drawn from the genuine converged hold
dynamics the forensics doc found, not the transient descent). Each row
carries q_rad (robot_abs), qvel_mujoco (MuJoCo-native) AND target_m
(this tick's commanded height-ref, env._goal_traj.height[i] -- these
BOTH matter equally for this bank, unlike the "standing-height-ish"
lower_start_bank, because a term-start specialist must spawn at a pose
whose own commanded target the flat height ref will match exactly).

This is a pure state-injection/curriculum-data tool -- no BC action
labels, no scripted motion role, no demonstration: it records where the
champion's OWN RL-trained policy already stably sits, nothing about
WHAT ACTION to take there. Same allowed category (RL_GOALS.md
"curricula and non-motion role-selection plumbing") as
harvest_lower_entry_bank_rlonly.py, which this mirrors structurally.

Usage:
    uv run python -m rl_move.sim.harvest_lower_term_bank \\
        --lower rl_move/sim/policies/ppo_goal_cw_stance50hz_rlonly_\\
lowerrole_scratch_sac_s0_drramp_acq1.zip \\
        --episodes 40 --sample-every-s 0.3 \\
        --out rl_move/sim/park_banks/lower_term_bank_s0_drramp_acq1_2026_10_04.npz
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

# Matches cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp's
# own implied schedule: goal.lower_hold_s=1.0 (fixed) + lower_ramp_s
# (default 5.0, not overridden by that recipe) = 6.0s nominal ramp-end;
# SETTLE_S is extra margin so even a jittered ramp (goal.
# lower_ramp_jitter, unset here = 0 = no jitter) is provably done
# before the first sample.
LOWER_HOLD_S = 1.0
LOWER_RAMP_S = 5.0
SETTLE_S = 1.5
EPISODE_S = 15.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lower", type=Path,
                    default=Path("rl_move/sim/policies/"
                                 "ppo_goal_cw_stance50hz_rlonly_"
                                 "lowerrole_scratch_sac_s0_drramp_"
                                 "acq1.zip"))
    ap.add_argument("--episodes", type=int, default=40)
    ap.add_argument("--sample-every-s", type=float, default=0.3,
                    help="sample a bank row this often during the "
                         "post-ramp converged window (default 0.3s)")
    ap.add_argument("--deterministic", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    from hexapod_core.joint_frame import (
        FRAME_ROBOT_ABS, JOINT_CONTRACT, mujoco_rel_rad_to_robot_abs_deg,
    )
    from rl_move.robot_state import DEG2RAD, N_JOINTS
    from .cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp import (
        CFG_ARGS as LOWER_CFG_ARGS,
    )
    from .eval_lifecycle_handoff_rlonly import _build_env, _set_mix
    from .gru_policy import load_checkpoint_auto

    env = _build_env(LOWER_CFG_ARGS, episode_seconds=EPISODE_S,
                      seed=args.seed, render=False)
    lower = load_checkpoint_auto(args.lower, device="cpu")
    # The champion's own obs width may be a PREFIX of this env's full
    # obs (same `obs[:n_lower]` slice eval_lifecycle_handoff_rlonly.py
    # uses for a cross-recipe obs-width mismatch) -- this standalone
    # single-role run happens to build a slightly wider obs than the
    # checkpoint's own training env did, same convention applies.
    n_lower = int(lower.observation_space.shape[0])

    sample_window_start_s = LOWER_HOLD_S + LOWER_RAMP_S + SETTLE_S
    q_rows: list = []
    qvel_rows: list = []
    target_rows: list = []
    n_ok = 0
    for ep in range(args.episodes):
        gen = env._goal_gen
        _set_mix(gen, lower=1.0)
        obs, _ = env.reset(seed=args.seed + ep)
        ep_rows: list = []
        ep_qvel_rows: list = []
        ep_target_rows: list = []
        term = trunc = False
        info: dict = {}
        next_sample = sample_window_start_s
        n_steps = max(1, int(round(EPISODE_S / env.dt)))
        for _ in range(n_steps):
            a, _ = lower.predict(obs[:n_lower],
                                 deterministic=args.deterministic)
            obs, _rw, term, trunc, info = env.step(a)
            t = env._step_i * env.dt
            if t >= next_sample and t < EPISODE_S:
                q_deg = mujoco_rel_rad_to_robot_abs_deg(
                    env.data.qpos[env._qadr])
                qvel = np.asarray(env.data.qvel[env._vadr], dtype=float)
                target_m = float(env._goal_traj.height[
                    min(env._step_i, len(env._goal_traj.height) - 1)])
                ep_rows.append(np.asarray(q_deg, dtype=float))
                ep_qvel_rows.append(qvel)
                ep_target_rows.append(target_m)
                next_sample += args.sample_every_s
            if term or trunc:
                break
        h_err_mm = 1000.0 * (
            float(env.data.xpos[env._chassis_bid, 2])
            - (env._z0 + env._h_target))
        lower_ok = (not term) and abs(h_err_mm) <= 15.0
        print(f"ep{ep} lower_ok={lower_ok} h_err_mm={h_err_mm:.1f} "
              f"rows={len(ep_rows)} "
              f"fall={info.get('termination_reason') if term else None}")
        if lower_ok:
            n_ok += 1
            q_rows.extend(ep_rows)
            qvel_rows.extend(ep_qvel_rows)
            target_rows.extend(ep_target_rows)

    if not q_rows:
        raise RuntimeError("harvested zero rows -- no lower_ok episode "
                            "reached the post-ramp sample window")
    q_deg_arr = np.stack(q_rows, axis=0)
    qvel_arr = np.stack(qvel_rows, axis=0)
    target_arr = np.asarray(target_rows, dtype=float)
    if q_deg_arr.shape[1] != N_JOINTS or qvel_arr.shape != q_deg_arr.shape:
        raise ValueError(
            f"shape mismatch: q_deg {q_deg_arr.shape}, qvel "
            f"{qvel_arr.shape}, expected (K,{N_JOINTS}) both")
    if len(target_arr) != len(q_deg_arr):
        raise ValueError(
            f"shape mismatch: target_m {target_arr.shape} vs q_rad "
            f"{q_deg_arr.shape}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.out, q_rad=q_deg_arr * DEG2RAD, qvel_mujoco=qvel_arr,
             target_m=target_arr, joint_frame=FRAME_ROBOT_ABS,
             joint_contract=JOINT_CONTRACT, source_lower=str(args.lower),
             episodes=args.episodes, episodes_ok=n_ok,
             sample_every_s=args.sample_every_s)
    print(f"wrote {args.out}: {q_deg_arr.shape[0]} rows from "
          f"{n_ok}/{args.episodes} lower_ok episode(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
