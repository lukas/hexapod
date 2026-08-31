"""audit_turn_dataset.py — standwalk turn-authority AUDIT tool
(meta-08-31 priority reorder, item 1: "AUDIT the dual-distill turn
path (CPU, no launch): count turn-in-place pairs actually in the
dualbc5 dataset; holdout action-error split straight-vs-turn ticks;
verify the wz command obs index/sign reaching the student").

WHY: 8 independently-designed RL mechanism-class canaries (turndiet,
turnpay/walkteach, turncap+RL, anchor-coef dose x2, turnskip,
PPO-side isolateoff/entboost, exploration-magnitude mild/hi,
reward-salience yawscale5x/15x) all FAILED to produce turn-in-place
authority on the dualbc5_turncap lineage. Every gate text named "audit
the base" as the next step. The pre-RL raw dualbc5_turncap checkpoint
itself (RL_LOG 08-31 02:35) already showed a real but WEAK+ASYMMETRIC
partial turn escape: wz_cmd=-0.25 gave wz_med -0.038/-0.048, wz_cmd=
+0.25 stayed frozen (~0.00003) — this tool checks the two obvious
explanations for that asymmetry BEFORE assuming an architecture limit:

1. ENV-SIDE SIGN/WIRING BUG — checked by code read (not this script):
   the yaw command draw (`draw_wz()`) is a symmetric
   ``rng.uniform(-wz_max, wz_max)``, the turn-in-place curriculum
   (`goal.walk_turn_in_place_frac`) does an explicit 50/50 sign coin
   flip, the phase-clock coupling (`goal.walk_phase_run_on_yaw`) gates
   on ``abs(wz_ref)`` (no sign dependence), and the obs tail append is
   a direct proportional ``wz_ref / WZ_SCALE`` (no sign flip anywhere
   in the pipeline) — no wiring bug found in any of the three places
   the commanded yaw rate touches env code.
2. DATASET COVERAGE IMBALANCE — this script's job: replay the EXACT
   documented dualbc5_turncap collection recipe (bc1_std25 walk-
   teacher, the walk-teacher-ledger + stance-teacher-ledger 83-key
   merged cfg union with ``walk_yaw_zero_frac`` 1.0->0.5 and
   ``walk_turn_in_place_frac`` 0.0->0.30, same seed=0) for the walk-
   mode episode count actually collected across the initial BC pass
   plus 2 DAgger rounds (30+30+30=90), and report: how many of those
   episodes are genuine whole-episode turn-in-place ("tip") demos, the
   +/- sign split among them, and the overall turn-vs-straight TICK
   fraction. A lopsided split (e.g. 2 vs 7) would explain the
   asymmetry as sampling luck in a small collection budget; a balanced
   split rules that out and points at the BC/DAgger optimization
   itself (dual-core split, shared-trunk regression-to-mean drowning
   the minority-magnitude turn deviation on the harder-to-imitate
   sign) as the next suspect.

MEASURED (this run, 08-31, walk-mode ticks/episodes only, teacher
bc1_std25, seed 0, 90 episodes): tip episodes 17/90 (+wz: 9, -wz: 8 —
BALANCED, not lopsided), turn-nonzero ticks 59.1% of all walk ticks,
0/90 teacher falls during collection. Coverage imbalance is REFUTED
as the (sole) explanation for the pre-RL asymmetry — combined with the
already-refuted env-wiring-bug hypothesis and the scripted-gait
control's own symmetric wz_med~+-0.21 (proves the sim body itself has
no CW/CCW asymmetry), the remaining suspect is the BC/DAgger
optimization dynamics on the dual-core actor, not the data or the env.

Usage:
  uv run python -m rl_move.sim.audit_turn_dataset \
      --walk-teacher rl_move/sim/policies/ppo_goal_cw_walkteach_scripted_allhead_bc1_std25.zip \
      --episodes 90 --seed 0
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

from .distill_gru import _build_cfg, DIET
from .servo_model import SimServoParams
from .walk_task import SimHexapodJointWalkEnv
from .train_ppo_sim import _parse_cfg_set

# The documented dualbc5_turncap collection recipe (STATUS 08-31 ~02:0x):
# walk-teacher-ledger 51 --cfg-set flags (28 unique) UNION stance-
# teacher-ledger 34 --cfg-set flags, 2 overlaps (control.hz,
# train.bc_anchor_coef, identical in both) = 83 keys, PLUS turncap's
# own two additions (goal.walk_yaw_zero_frac 1.0->0.5,
# goal.walk_turn_in_place_frac 0.0->0.30).
TURNCAP_CFG_SET = [
    "env.model_source=mesh",
    "control.hz=100",
    "safety.max_delta_q_deg=0.375",
    "safety.max_roll_deg=25",
    "safety.max_pitch_deg=25",
    "goal.walk_speed_min_m_s=0.08",
    "goal.walk_speed_max_m_s=0.08",
    "goal.walk_heading_max_rad=3.1415927",
    "goal.walk_stop_frac=0.15",
    "goal.walk_cmd_resample_s=6.0",
    "goal.walk_cmd_resample_jitter=0.2",
    "goal.walk_park_start_frac=0.25",
    "goal.walk_obs_body_vel=2",
    "goal.walk_phase_obs=1",
    "goal.walk_phase_hz=1.333333",
    "goal.walk_yaw_cmd=1",
    "goal.walk_phase_run_on_yaw=1",
    "goal.walk_yaw_zero_frac=0.5",
    "reward.walk_kernel_prog_gate=1.0",
    "reward.walk_anchor_gate=1.0",
    "reward.anchor_tol_mm=10.0",
    "reward.walk_height_gate=1.0",
    "reward.walk_height_sigma_mm=30.0",
    "reward.walk_loadslip_gate=1.0",
    "reward.loadslip_ok=3.0",
    "reward.loadslip_max=6.0",
    "reward.k_loadslip_excess=10.0",
    "reward.k_walk_idle_charge=20.0",
    "reward.walk_idle_speed_m_s=0.02",
    "reward.k_park_duty=2.0",
    "reward.k_drag_loaded=10.0",
    "reward.k_walk_course_income=2.0",
    "reward.walk_course_income_window_s=0.75",
    "reward.walk_course_income_deadband_deg=6.0",
    "reward.walk_course_income_sigma_deg=20.0",
    "reward.k_walk_excess_sway=2.0",
    "reward.walk_sway_window_s=0.75",
    "reward.walk_sway_allow_mm=5.0",
    "reward.k_walk_course_disp=0.15",
    "reward.walk_course_disp_window_s=1.5",
    "reward.walk_course_disp_min_speed_m_s=0.02",
    "reward.k_walk_course_disp_overspeed=4.0",
    "reward.walk_course_disp_overspeed_tol=0.05",
    "reward.walk_course_disp_overspeed_along=1.0",
    "reward.walk_course_disp_overspeed_ref_floor_m_s=0.06",
    "train.bc_anchor_coef=3.0",
    "train.bc_anchor_walk=1.0",
    "train.bc_anchor_walk_coef=1.0",
    "train.bc_anchor_phase_lock=1.0",
    "train.bc_anchor_isolate_update=1",
    "actions.max_height_mm=88",
    "goal.rise_height_mm=[79,87]",
    "goal.rise_ramp_s=6.0",
    "goal.rise_rsi_frac=0.5",
    "goal.rise_hold_min_s=0.5",
    "reward.rise_score_income=1.0",
    "reward.rise_score_strip_pen=1.0",
    "reward.k_rise_ref_track=2.0",
    "reward.rise_ref_path=rl_move/sim/refs/rise_ref_belly2plant.npz",
    "reward.rise_ref_sigma_deg=6.0",
    "reward.rise_posture_gate=1.0",
    "reward.rise_income_prog_gate=1.0",
    "reward.rise_finish_gate_signed=1.0",
    "reward.hold_still_gate=1.0",
    "reward.hold_flag_fade=1.0",
    "reward.k_current_hot=1.0",
    "reward.current_hot_a=2.0",
    "reward.term_cost_per_remaining_s=3.0",
    "reward.term_cost_max=60.0",
    "reward.hold_feet_load=1.0",
    "reward.hold_feet_load_min=1.0",
    "safety.hold_max_height_drop_mm=40.0",
    "safety.hold_height_grace_s=1.0",
    "safety.hold_min_load_terminate_s=1.0",
    "safety.hold_min_load_terminate_n=0.3",
    "safety.hold_min_load_terminate_grace_s=1.0",
    "train.bc_anchor_lower=1.0",
    "train.bc_anchor_state_aligned=1.0",
    "train.bc_anchor_lookahead_s=0.5",
    "train.bc_anchor_min_h_ahead_mm=15",
    "train.bc_anchor_foot_z=1.0",
    "train.bc_anchor_stratified=1.0",
    "goal.walk_turn_in_place_frac=0.30",
]


def build_env(seed: int, dr_scale: float, episode_seconds: float,
              cfg_set: list[str]):
    overrides = _parse_cfg_set(cfg_set)
    overrides["obs.mode_onehot"] = 1.0
    cfg = _build_cfg(overrides)
    params = SimServoParams.load()
    env = SimHexapodJointWalkEnv(params=params, randomize=True,
                                  dr_scale=dr_scale,
                                  episode_seconds=episode_seconds,
                                  seed=seed, cfg=cfg)
    # Force walk-only, exactly like probe_turn_authority.make_env —
    # env.set_goal_mix() only pokes goal.DIET (walk/rise/lower/hold)
    # p_<mode> attrs and silently leaves any other nonzero default
    # (p_lean/p_track/... ) alive, which can steer _sample_goal() into
    # a non-walk GoalTrajectory with no .vx/.vy/.wz (caught the hard
    # way: first draft crashed on 'GoalTrajectory has no attribute
    # vx' — that IS a plain stance trajectory, proof the mix wasn't
    # fully forced to walk).
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk", "getup", "recover"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env


def audit(walk_teacher_path: str, n_ep: int, seed: int,
          stochastic_frac: float, dr_scale: float,
          episode_seconds: float, cfg_set: list[str]) -> dict:
    from stable_baselines3 import PPO

    env = build_env(seed, dr_scale, episode_seconds, cfg_set)
    teacher = PPO.load(walk_teacher_path, device="cpu")
    n_t_obs = int(teacher.observation_space.shape[0])
    n_env_obs = int(env.observation_space.shape[0])

    rng = np.random.default_rng(seed)
    tip_signs: list[int] = []
    turn_ticks = 0
    straight_ticks = 0
    n_fell = 0
    for _ in range(n_ep):
        deterministic = rng.random() >= stochastic_frac
        obs, info = env.reset()
        traj = env._goal_traj
        # hold_n+ramp_n = 2s ramp-in at env.dt; sample well past it
        # (t=3s) — checking at t=0 is a guaranteed false negative
        # since EVERY episode (tip or not) is forced to vx=vy=wz=0
        # for the first 1s by construction (caught the hard way: a
        # first draft that sampled goal.wz_ref at t=0 found 0/90 tip
        # episodes against a 30% draw probability).
        idx = min(int(round(3.0 / env.dt)), len(traj.vx) - 1)
        vx_m, vy_m, wz_m = (float(traj.vx[idx]), float(traj.vy[idx]),
                            float(traj.wz[idx]))
        is_tip = (abs(vx_m) < 1e-6 and abs(vy_m) < 1e-6
                  and abs(wz_m) > 1e-3)
        if is_tip:
            tip_signs.append(1 if wz_m > 0 else -1)
        term = False
        done = False
        while not done:
            act, _ = teacher.predict(obs[:n_t_obs],
                                     deterministic=deterministic)
            obs, r, term, trunc, info = env.step(act)
            g = env._current_goal()
            if g is not None and abs(g.wz_ref) > 1e-3:
                turn_ticks += 1
            else:
                straight_ticks += 1
            done = term or trunc
        if term:
            n_fell += 1
    env.close()

    pos = sum(1 for s in tip_signs if s > 0)
    neg = sum(1 for s in tip_signs if s < 0)
    total_ticks = turn_ticks + straight_ticks
    return {
        "walk_teacher": walk_teacher_path,
        "n_episodes": n_ep,
        "seed": seed,
        "teacher_obs_width": n_t_obs,
        "env_obs_width": n_env_obs,
        "tip_episodes": len(tip_signs),
        "tip_pos": pos,
        "tip_neg": neg,
        "turn_ticks": turn_ticks,
        "straight_ticks": straight_ticks,
        "turn_tick_frac": (turn_ticks / total_ticks
                            if total_ticks else None),
        "teacher_falls": n_fell,
    }


def action_error_split(walk_teacher_path: str, student_path: str,
                       n_ep: int, seed: int, dr_scale: float,
                       episode_seconds: float, cfg_set: list[str]) -> dict:
    """Holdout action-error split (priority-reorder item 1, second
    clause): drive TEACHER-labeled rollouts (same recipe as
    ``audit()``, deterministic — no BC/DAgger training happens here,
    this only SCORES the already-saved raw distilled checkpoint), and
    at every tick compare the STUDENT's (dualbc5_turncap.zip) action
    against the teacher's own label action on that SAME state,
    bucketed by straight (wz_ref==0) vs turn+ (wz_ref>0) vs turn-
    (wz_ref<0). A per-bucket MSE gap (esp. turn+ >> turn-, matching the
    already-measured +wz-frozen/-wz-partial probe asymmetry) would
    point at the BC/DAgger optimization itself imitating one turn
    direction worse than the other on states BOTH directions cover —
    the dataset-coverage hypothesis is already refuted by ``audit()``
    above, so this isolates whether the gap is optimization-side."""
    from stable_baselines3 import PPO

    from .gru_policy import load_checkpoint_auto, RecurrentPredictor

    env = build_env(seed, dr_scale, episode_seconds, cfg_set)
    teacher = PPO.load(walk_teacher_path, device="cpu")
    n_t_obs = int(teacher.observation_space.shape[0])

    student, _ = load_checkpoint_auto(student_path, device="cpu"), None
    student_pred = RecurrentPredictor(student) \
        if getattr(student.policy, "lstm_actor", None) is not None \
        else student

    buckets = {"straight": [], "turn_pos": [], "turn_neg": []}
    rng = np.random.default_rng(seed)
    for _ in range(n_ep):
        obs, info = env.reset()
        if hasattr(student_pred, "reset"):
            student_pred.reset()
        done = False
        while not done:
            t_act, _ = teacher.predict(obs[:n_t_obs], deterministic=True)
            s_act, _ = student_pred.predict(obs, deterministic=True)
            g = env._current_goal()
            wz = float(getattr(g, "wz_ref", 0.0)) if g is not None else 0.0
            err = float(np.mean((np.asarray(t_act) - np.asarray(s_act)) ** 2))
            key = ("straight" if abs(wz) <= 1e-3
                   else "turn_pos" if wz > 0 else "turn_neg")
            buckets[key].append(err)
            # advance the env with the TEACHER's action (this scores
            # the student on genuinely teacher-visited/labeled states,
            # not a student-drifted rollout).
            obs, r, term, trunc, info = env.step(t_act)
            done = term or trunc
    env.close()

    def stats(v):
        return {"n": len(v), "mse_med": float(np.median(v)) if v else None,
                "mse_mean": float(np.mean(v)) if v else None}
    return {k: stats(v) for k, v in buckets.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--walk-teacher", type=str, default=str(
        Path(__file__).resolve().parent / "policies" /
        "ppo_goal_cw_walkteach_scripted_allhead_bc1_std25.zip"))
    ap.add_argument("--episodes", type=int, default=90,
                    help="matches the historical 30(initial)+"
                         "30(dagger r1)+30(dagger r2) walk episode "
                         "count for the dualbc5_turncap recipe.")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stochastic-frac", type=float, default=0.3)
    ap.add_argument("--dr-scale", type=float, default=0.5)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--cfg-set", action="append", default=None,
                    metavar="K=V",
                    help="override/extend the built-in TURNCAP_CFG_SET "
                         "recipe (same dotted convention as "
                         "distill_gru.py). Default None = use the "
                         "recipe as-is.")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--student-checkpoint", type=str, default=None,
                    help="if set, ALSO run the holdout action-error "
                         "split (priority-reorder item 1's second "
                         "clause) comparing this raw distilled "
                         "checkpoint's actions to the teacher's on "
                         "teacher-driven rollouts, bucketed straight/"
                         "turn+/turn-.")
    args = ap.parse_args(argv)

    cfg_set = list(TURNCAP_CFG_SET) + list(args.cfg_set or [])
    result = audit(args.walk_teacher, args.episodes, args.seed,
                   args.stochastic_frac, args.dr_scale,
                   args.episode_seconds, cfg_set)
    print(f"[audit-turn-dataset] teacher obs {result['teacher_obs_width']}"
          f", env obs {result['env_obs_width']}")
    print(f"[audit-turn-dataset] episodes {result['n_episodes']}, "
          f"tip episodes {result['tip_episodes']} "
          f"(+wz {result['tip_pos']}, -wz {result['tip_neg']})")
    frac = result["turn_tick_frac"]
    print(f"[audit-turn-dataset] turn ticks "
          f"{result['turn_ticks']}/{result['turn_ticks'] + result['straight_ticks']}"
          f" ({frac * 100:.1f}%)" if frac is not None else "n/a")
    print(f"[audit-turn-dataset] teacher falls during collection: "
          f"{result['teacher_falls']}/{result['n_episodes']}")
    if args.student_checkpoint:
        split = action_error_split(
            args.walk_teacher, args.student_checkpoint, args.episodes,
            args.seed, args.dr_scale, args.episode_seconds, cfg_set)
        result["action_error_split"] = split
        for k in ("straight", "turn_pos", "turn_neg"):
            s = split[k]
            print(f"[audit-turn-dataset] action MSE {k}: "
                  f"n={s['n']} med={s['mse_med']}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2))
        print(f"[audit-turn-dataset] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
