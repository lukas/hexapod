"""probe_walk_drag_econ.py — per-term walk-mode reward economics for
the standwalk dualbc7/anchor14coef1 freeze diagnosis (2026-09-11).

WHY (rl_docs/tracks/standwalk/STATUS.md ~23:5x): the BC-only clone
already walks (real forward v=0.023-0.055 m/s, positive mid-episode
reward) before any RL fine-tune; the RL wrapper (`anchor14coef1`, +2M
steps) turns that into a near-frozen 'plant' (v=0.003-0.02 m/s) whose
FULL-EPISODE reward collapses to -1189..-2726 by t=30s — a genuine
reward-economics question, not a plumbing bug (bc_anchor_fill/loss
wiring confirmed nonzero). Two suspects were named (BC-anchor tick
selection; over_current termination pricing) but neither was checked
against the run's own reward-term breakdown first.

CODE-READ FINDING (this script's companion note, recorded in
STATUS.md): unlike the RISE BC-anchor, which can index by
STATE-ALIGNED nearest-reference-pose match (`train.bc_anchor_state_
aligned`) and therefore CAN stall on a near-static reference window,
the WALK BC-anchor (`self._walk_bc_gait`, sim_env.py ~L5636) always
drives a live scripted TripodGait clock gated on the GOAL's COMMANDED
velocity (`_bc_cmd`/`_bc_clock_run`), never on achieved state — with
a FIXED walk_speed_min=max=0.08 command for the whole episode, that
clock cannot degenerate into a static target. Suspect (1) as literally
stated ("anchor locks onto a near-static reference window") does not
apply mechanically to walk ticks; it is rise-specific machinery.

THIS SCRIPT checks a third, previously-unexamined candidate raised by
the run's OWN already-logged W&B summary (env/reward_drag_stance
~-1.25/tick vs env/reward_walk ~+0.30/tick and env/reward_walk_prog
~-0.04/tick, at k_drag_stance=8000.0 vs k_walk_prog=2.0 — a
BY-DESIGN 4000x price ratio): does the STANCE-DRAG penalty
(reward.k_drag_stance / drag_stance_allow_mm, priced to punish a
loaded foot sliding more than 24mm) dominate the walk-mode income
enough that ANY real stepping attempt (weight briefly still on a foot
mid-transfer) costs more than the forward-progress term pays, making
near-zero motion the locally cheaper policy?

Rolls BOTH checkpoints (the BC base and the RL retry1 checkpoint)
through IDENTICAL walk-only episodes (same cfg-set stack as the
retry1 launch, forced p_walk=1.0, fixed forward command) and sums
every `info["reward_*"]` term plus net displacement — a direct,
no-new-mechanism decomposition (every summed field is already emitted
by sim_env._step_finish; this script adds no reward/env code).

    uv run python -m rl_move.sim.probe_walk_drag_econ
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]

from rl_move.config import load_config
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.walk_task import SimHexapodJointWalkEnv
from rl_move.sim.gru_policy import is_recurrent_checkpoint, load_checkpoint_auto

# Exact --cfg-set stack of cw-standwalk-stage2-dualbc7-massfix-
# anchor14coef1-canary-retry1 (extracted from its own launch command,
# ops.sh entry, 2026-09-11 — copy verbatim if the recipe ever moves).
CFG_SET = [
    "reward.k_drag_loaded=10.0", "reward.k_park_duty=1.0",
    "reward.walk_kernel_prog_gate=1.0", "goal.walk_park_start_frac=0.25",
    "reward.walk_anchor_gate=1.0", "reward.anchor_tol_mm=10.0",
    "goal.walk_speed_min_m_s=0.08", "goal.walk_speed_max_m_s=0.08",
    "goal.walk_obs_body_vel=2", "safety.max_roll_deg=25",
    "safety.max_pitch_deg=25", "dr.tipped_start_prob=0.30",
    "reward.walk_height_gate=1.0", "reward.walk_height_sigma_mm=30.0",
    "goal.walk_phase_obs=1", "goal.walk_phase_hz=1.1",
    "goal.walk_heading_max_rad=-1.0", "reward.k_walk_course=2.0",
    "reward.walk_course_tau_s=0.75", "reward.k_walk_course_overspeed=4.0",
    "reward.walk_course_overspeed_tol=0.05", "reward.k_walk_idle_charge=1.0",
    "reward.walk_idle_speed_m_s=0.04", "reward.walk_loadslip_gate=1.0",
    "reward.loadslip_ok=3.0", "reward.loadslip_max=6.0",
    "reward.k_loadslip_excess=10.0", "reward.walk_course_overspeed_along=1",
    "reward.walk_course_min_speed_m_s=0.04", "reward.k_drag_stance=8000.0",
    "reward.drag_stance_allow_mm=24.0", "reward.drag_stance_tick_floor_mm=0.25",
    "reward.walk_kernel_vel_ema=1", "reward.walk_kernel_vel_tau_s=0.75",
    "reward.k_walk_prog=2.0", "reward.walk_course_overspeed_ref_floor_m_s=0.06",
    "actions.max_height_mm=88", "goal.rise_height_mm=[79,87]",
    "goal.rise_ramp_s=6.0", "goal.rise_rsi_frac=0.5",
    "goal.rise_hold_min_s=0.5", "reward.rise_score_income=1.0",
    "reward.rise_score_strip_pen=1.0", "reward.k_rise_ref_track=2.0",
    "reward.rise_ref_path=rl_move/sim/refs/rise_ref_mesh_scripted.npz",
    "reward.rise_ref_sigma_deg=6.0", "reward.rise_posture_gate=1.0",
    "reward.rise_income_prog_gate=1.0", "reward.rise_finish_gate_signed=1.0",
    "reward.hold_still_gate=1.0", "reward.hold_flag_fade=1.0",
    "reward.k_current_hot=12.0", "reward.current_hot_a=2.3",
    "reward.term_cost_per_remaining_s=3.0", "reward.term_cost_max=60.0",
    "reward.hold_feet_load=1.0", "reward.hold_feet_load_min=1.0",
    "safety.hold_max_height_drop_mm=40.0", "safety.hold_height_grace_s=1.0",
    "safety.hold_min_load_terminate_s=1.0",
    "safety.hold_min_load_terminate_n=0.3",
    "safety.hold_min_load_terminate_grace_s=1.0", "env.model_source=mesh",
    "control.hz=50", "obs.mode_onehot=1", "goal.mode_seq=0.75",
    "train.bc_anchor_coef=3.0", "train.bc_anchor_lower=1.0",
    "train.bc_anchor_state_aligned=1.0", "train.bc_anchor_lookahead_s=0.25",
    "train.bc_anchor_min_h_ahead_mm=8", "train.bc_anchor_foot_z=1.0",
    "train.bc_anchor_stratified=1.0", "train.bc_anchor_flat_time_indexed=1.0",
    "train.bc_anchor_walk=1.0", "train.bc_anchor_isolate_update=1",
    "train.bc_anchor_phase_lock=1.0", "train.bc_anchor_knee_abs=1.0",
    "train.bc_anchor_walk_coef=1.0", "safety.max_delta_q_deg=0.75",
]

CKPTS = {
    "bc_base": "rl_move/sim/policies/ppo_goal_cw_standwalk_stage2_dualbc7_m2plainteacher_massfix.zip",
    "retry1": "rl_move/sim/policies/ppo_goal_cw_standwalk_stage2_dualbc7_massfix_anchor14coef1_canary_retry1.zip",
}


def _parse_cfg_set(specs):
    out = {}
    for part in specs:
        k, _, v = part.partition("=")
        v = v.strip()
        if v.startswith("["):
            out[k.strip()] = json.loads(v)
            continue
        try:
            out[k.strip()] = float(v)
        except ValueError:
            out[k.strip()] = v
    return out


def make_env(seed: int, episode_seconds: float):
    cfg = load_config()
    for key, val in _parse_cfg_set(CFG_SET).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = val
    # WALK MODE ONLY (matches the 09-11 ~23:5x precheck's own
    # "walk mode only" isolation): the launched recipe draws 75% of
    # episodes as a full rise->walk->lower->hold mode_seq chain
    # regardless of gen.p_* — force that off so a short window is
    # guaranteed to actually be in the walk segment, not stuck in an
    # early rise/hold segment of a sequence draw.
    cfg.setdefault("goal", {})["mode_seq"] = 0.0
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg), randomize=False, dr_scale=0.0,
        episode_seconds=episode_seconds, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise", "lower",
              "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env


def pin_forward(env, vx: float = 0.08) -> None:
    traj = env._goal_traj
    hold_n = ramp_n = int(round(1.0 / env.dt))
    ramp = np.linspace(0.0, 1.0, ramp_n)
    traj.vx[:] = vx
    traj.vx[:hold_n] = 0.0
    traj.vx[hold_n:hold_n + ramp_n] = vx * ramp
    traj.vy[:] = 0.0
    if getattr(traj, "wz", None) is not None:
        traj.wz[:] = 0.0


def rollout(ckpt_key: str, seed: int, episode_seconds: float,
            deterministic: bool = True) -> dict:
    path = str(ROOT / CKPTS[ckpt_key])
    env = make_env(seed, episode_seconds)
    obs, _ = env.reset()
    n_env_obs = int(env.observation_space.shape[0])
    model = load_checkpoint_auto(path, device="cpu")
    n_model_obs = int(model.observation_space.shape[0])
    if n_model_obs != n_env_obs:
        raise SystemExit(f"[{ckpt_key}] obs mismatch: model={n_model_obs} "
                          f"env={n_env_obs} (mode_onehot cfg drifted?)")
    pin_forward(env)
    recurrent = is_recurrent_checkpoint(path)
    state = None
    ep_start = np.ones((1,), dtype=bool)

    sums: dict[str, float] = defaultdict(float)
    n = int(round(episode_seconds / env.dt))
    x0 = float(env.data.xpos[env._chassis_bid, 0])
    y0 = float(env.data.xpos[env._chassis_bid, 1])
    term_reason = None
    steps_run = 0
    for t in range(n):
        if recurrent:
            act, state = model.policy.predict(
                obs, state=state, episode_start=ep_start,
                deterministic=deterministic)
            ep_start = np.zeros((1,), dtype=bool)
        else:
            act, _ = model.predict(obs, deterministic=deterministic)
        obs, r, term, trunc, info = env.step(act)
        sums["reward_total"] += float(r)
        for k, v in info.items():
            if k.startswith("reward_") and isinstance(v, (int, float)):
                sums[k] += float(v)
        steps_run += 1
        if term or trunc:
            term_reason = info.get("termination_reason")
            break
    x1 = float(env.data.xpos[env._chassis_bid, 0])
    y1 = float(env.data.xpos[env._chassis_bid, 1])
    disp = float(np.hypot(x1 - x0, y1 - y0))
    env.close()
    return {"ckpt": ckpt_key, "seed": seed, "steps": steps_run,
            "elapsed_s": round(steps_run * env.dt, 2),
            "net_disp_m": round(disp, 4),
            "net_v_m_s": round(disp / max(steps_run * env.dt, 1e-6), 4),
            "term_reason": term_reason, "sums": dict(sums)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode-seconds", type=float, default=20.0)
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--out", type=Path,
                     default=Path("/tmp/probe_walk_drag_econ.json"))
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]

    results = []
    for ckpt_key in ("bc_base", "retry1"):
        for seed in seeds:
            res = rollout(ckpt_key, seed, args.episode_seconds,
                           deterministic=not args.stochastic)
            results.append(res)
            top = sorted(res["sums"].items(), key=lambda kv: kv[1])
            print(f"\n== {ckpt_key} seed={seed}: disp={res['net_disp_m']}m "
                  f"v={res['net_v_m_s']}m/s steps={res['steps']} "
                  f"term={res['term_reason']}")
            print(f"   total_reward={res['sums'].get('reward_total', 0):.1f}")
            for k, v in top:
                if k == "reward_total":
                    continue
                if abs(v) > 1.0:
                    print(f"   {k:28s} {v:10.2f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=1))
    print(f"\n[probe_walk_drag_econ] wrote {args.out}")


if __name__ == "__main__":
    main()
