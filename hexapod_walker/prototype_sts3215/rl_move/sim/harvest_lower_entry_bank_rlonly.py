"""Harvest a `goal.lower_start_bank` npz (q_rad robot_abs + qvel_mujoco,
v2 qvel-carrying format) from the `rl_only` WALK champion's OWN drive
episodes -- walkcurr's own root-cause finding this cycle (2026-09-24,
following the ~13:0x lifecycle-composition entry): zeroing carried
JOINT VELOCITY at the walk->lower handoff only nudges the SAC `lower`
role's composed-session fall rate (+1/12 both arms on
`lowerrole-scratch-sac-s0-drramp-acq1`, well inside noise), and even
the PLANT control arm (walk's own clean-reset drive, no rise/stance
composition at all) falls at the same rate once its OWN drive episode
hands off to `lower` -- so the gap is not a handoff-mechanic artifact,
it is that `lower`'s isolated-gate training NEVER SAW a real mid-gait
walk-ending pose/velocity at all (its own training reset is always a
static post-rise hold, never a moving leg).

CURRENT_TRUTHS 2026-09-23 ~21:3x already found and PASSED the fix for
exactly this shape of gap on the (unrelated, any_means/BC-tainted)
GRU+MLP `stand` architectures: `goal.lower_start_bank_frac=0.20` +
`goal.bank_qvel_restore=1.0` against a v2 (qvel-carrying) bank cuts
their composed-session lower-segment fall rate from ~14-17% to ~4-8%.
That bank (`lower_entry_bank_dr07dr10_2026_09_23_v2qvel.npz`) was
harvested from a DIFFERENT walk champion under a DIFFERENT cfg-set
(the any_means dr07/dr10 GRU lineage) -- per this eval tool family's
own standing caution (eval_lifecycle_handoff_rlonly.py's module
docstring) against borrowing a "superficially similar" artifact
across lineages without checking it, this harvester instead builds a
FRESH bank from the `rl_only` lineage's OWN walk champion
(`cfg_recipe_walk50hz_slew_smooth_s0`, the walkcurr hardware-transfer
REFERENCE), so the `lower` role's curriculum sees genuinely
representative entry states for ITS OWN eventual composed partner.

This is a pure state-injection/curriculum-data tool -- no BC action
labels, no scripted motion role, no demonstration: it records where
the walk champion's OWN RL-trained policy leaves its joints/velocity
at various points in a drive, nothing about WHAT ACTION to take
there. Allowed under RL_GOALS.md's "curricula and non-motion
role-selection plumbing" carve-out, same category as the already-
built `rise_start_bank`/`lower_start_bank`/`walk_entry_bank`
machinery this reuses verbatim (`_lower_start_bank`/
`_apply_bank_qvel_handoff`, sim_env.py).

Usage:
    uv run python -m rl_move.sim.harvest_lower_entry_bank_rlonly \\
        --walk rl_move/sim/policies/ppo_goal_cw_walk50hz_slew_smooth_s0.zip \\
        --episodes 30 --sample-every-s 1.0 \\
        --out rl_move/sim/park_banks/lower_entry_bank_rlonly_walk50hz_slew_smooth_s0_2026_09_24_v2qvel.npz
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

DEFAULT_SPEED = 0.06
HOLD_S = 6.0
# Matches eval_lifecycle_handoff_rlonly.schedule(): 1s settle, hold_s
# commanded, 2s stop -- sampling starts after the settle so every row
# is drawn from genuine commanded locomotion, not the reset transient.
SETTLE_S = 1.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--walk", type=Path,
                    default=Path("rl_move/sim/policies/"
                                 "ppo_goal_cw_walk50hz_slew_smooth_s0.zip"))
    ap.add_argument("--walk-recipe", default="slew_smooth_s0",
                    choices=("rlonly_v2", "slew_smooth_s0",
                             "safewiden6_acq1"))
    ap.add_argument("--episodes", type=int, default=30)
    ap.add_argument("--speed", type=float, default=DEFAULT_SPEED)
    ap.add_argument("--hold-s", type=float, default=HOLD_S)
    ap.add_argument("--sample-every-s", type=float, default=1.0,
                    help="sample a bank row this often during the "
                         "held-command window (default 1.0s -- dense "
                         "enough to cover multiple gait phases per "
                         "episode without one episode dominating the "
                         "bank)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    import mujoco

    from rl_move.robot_state import N_JOINTS
    from hexapod_core.joint_frame import (
        FRAME_ROBOT_ABS, JOINT_CONTRACT, mujoco_rel_rad_to_robot_abs_deg,
    )
    from .eval_lifecycle_handoff_rlonly import _build_env, _set_mix
    from .gru_policy import load_checkpoint_auto

    if args.walk_recipe == "slew_smooth_s0":
        from .cfg_recipe_walk50hz_slew_smooth_s0 import (
            CFG_ARGS as WALK_CFG_ARGS,
        )
    elif args.walk_recipe == "safewiden6_acq1":
        from .cfg_recipe_walk50hz_fs_bisect_drv_safewiden6_acq1 import (
            CFG_ARGS as WALK_CFG_ARGS,
        )
    else:
        from .cfg_recipe_walk50hz_rlonly_v2 import CFG_ARGS as WALK_CFG_ARGS

    episode_s = max(20.0, args.hold_s + SETTLE_S + 2.0 + 2.0)
    env = _build_env(WALK_CFG_ARGS, episode_seconds=episode_s,
                      seed=args.seed, render=False)
    walk = load_checkpoint_auto(args.walk, device="cpu")

    q_rows: list = []
    qvel_rows: list = []
    for ep in range(args.episodes):
        gen = env._goal_gen
        _set_mix(gen, walk=1.0)
        obs, _ = env.reset(seed=args.seed + ep)
        traj = env._goal_traj
        t = 0.0
        next_sample = SETTLE_S
        # schedule: SETTLE_S at (0,0), then hold_s at (vx,0), then 2s
        # at (0,0) -- same convention as eval_lifecycle_handoff_rlonly
        # .schedule(), forward-only (off-forward is this champion's
        # own already-closed, DIFFERENT pathology -- not mixed in here).
        total_s = SETTLE_S + args.hold_s + 2.0
        while t < total_s:
            vx = args.speed if SETTLE_S <= t < SETTLE_S + args.hold_s else 0.0
            if hasattr(traj, "vx"):
                traj.vx[:] = vx
                traj.vy[:] = 0.0
            if getattr(traj, "wz", None) is not None:
                traj.wz[:] = 0.0
            a, _ = walk.predict(obs, deterministic=True)
            obs, _rw, term, trunc, info = env.step(a)
            t += env.dt
            if term or trunc:
                break
            if t >= next_sample and SETTLE_S <= t <= SETTLE_S + args.hold_s:
                q_deg = mujoco_rel_rad_to_robot_abs_deg(
                    env.data.qpos[env._qadr])
                qvel = np.asarray(env.data.qvel[env._vadr], dtype=float)
                q_rows.append(np.asarray(q_deg, dtype=float))
                qvel_rows.append(qvel)
                next_sample += args.sample_every_s
        print(f"ep{ep} rows_so_far={len(q_rows)} "
              f"fall={info.get('termination_reason') if (term or trunc) else None}")

    if not q_rows:
        raise RuntimeError("harvested zero rows -- every episode fell "
                            "before the first sample point")
    q_deg_arr = np.stack(q_rows, axis=0)
    qvel_arr = np.stack(qvel_rows, axis=0)
    if q_deg_arr.shape[1] != N_JOINTS or qvel_arr.shape != q_deg_arr.shape:
        raise ValueError(
            f"shape mismatch: q_deg {q_deg_arr.shape}, qvel "
            f"{qvel_arr.shape}, expected (K,{N_JOINTS}) both")
    from rl_move.robot_state import DEG2RAD
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.out, q_rad=q_deg_arr * DEG2RAD, qvel_mujoco=qvel_arr,
             joint_frame=FRAME_ROBOT_ABS, joint_contract=JOINT_CONTRACT,
             source_walk=str(args.walk), walk_recipe=args.walk_recipe,
             episodes=args.episodes, sample_every_s=args.sample_every_s)
    print(f"wrote {args.out}: {q_deg_arr.shape[0]} rows from "
          f"{args.episodes} episode(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
