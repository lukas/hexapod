"""Posture-recovery reward functions (getup / recover_to_plant), moved out of SimHexapodJointWalkEnv.

Each function here is the whole body of one reward method
moved mechanically: ``env`` is the env instance (the former ``self``), the
remaining parameters are the block's live inputs and the return values its
own, so the method that remains on the class is a one-line delegate.
Bodies are byte-identical to the original apart from ``self`` -> ``env``
and re-indentation; the header comments travelled with the code.
"""
from __future__ import annotations

import math

import numpy as np

from rl_move.config import cfg_get


def recover_reward(env, reward, term, trunc, info):
    r_strip = (info.get("reward_task", 0.0)
               + info.get("reward_roll", 0.0)
               + info.get("reward_pitch", 0.0))
    if r_strip != 0.0:
        reward -= r_strip
        info["reward_task"] = 0.0
        info["reward_roll"] = 0.0
        info["reward_pitch"] = 0.0

    # 2) Bounded features.
    x = np.zeros(6)
    for f in range(6):
        adr = env._touch_adr[f]
        if adr >= 0:
            t_n = max(float(env.data.sensordata[adr]), 0.0)
            x[f] = min(t_n, 1.0)
    feat_l = float(np.mean(x))
    tau = 0.15
    feat_m = float(min(max(
        -tau * math.log(float(np.mean(np.exp(-x / tau)))),
        0.0), 1.0))
    t_roll, t_pitch = env._true_roll_pitch()
    cos_t = math.cos(t_roll) * math.cos(t_pitch)
    feat_u = min(max((1.0 + cos_t) / 2.0, 0.0), 1.0)
    z_plant, _weight_n = env._getup_geom()
    z_belly = 38.0 * 0.001
    z_full = z_belly + 0.80 * max(z_plant - z_belly, 1e-3)
    z = float(env.data.xpos[env._chassis_bid, 2])
    feat_h = min(max((z - z_belly) / max(z_full - z_belly, 1e-3),
                     0.0), 1.0)
    over = z - (z_plant + 0.02)
    if over > 0.0:
        feat_h *= min(max(1.0 - over / 0.06, 0.0), 1.0)
    curl = env._curl_dist()
    fp_ok = 40.0 * 0.001
    fp_hi = 120.0 * 0.001
    feat_p = min(max((fp_hi - curl) / max(fp_hi - fp_ok, 1e-6),
                     0.0), 1.0)
    g_u = env._rec_gate(feat_u)
    g_h = env._rec_gate(feat_h)
    phi = (0.15 * feat_u + 0.15 * g_u * feat_l
           + 0.30 * g_u * feat_l * feat_h
           + 0.30 * g_u * g_h * feat_m
           + 0.10 * g_u * g_h * feat_p)

    # 3) Potential difference (PBRS). Seeded at the first
    #    post-settle tick — no income for the spawn posture.
    r_pot = 0.0
    if env._rec_phi_prev is not None:
        r_pot = 20.0 * (0.995 * phi - env._rec_phi_prev)
    env._rec_phi_prev = phi
    reward += r_pot

    # 4) Success detection + 0.5 s continuous hold.
    h_tol = 15.0 * 0.001
    spread_max = 30.0 * 0.001
    tilt_deg = max(abs(t_roll), abs(t_pitch)) * 180.0 / math.pi
    pad_z = np.array([float(env.data.xpos[b, 2])
                      for b in env._pad_bids])
    spread = float(np.max(pad_z) - np.min(pad_z))
    qd_rms = float(np.sqrt(np.mean(
        np.square(env._state.joint_velocity))))
    v = env._body_vel_xy()
    cur = getattr(env._state, "servo_current", None)
    cur_ok = cur is None or float(np.max(cur)) <= 3.0
    ok = (abs(z - z_full) <= h_tol
          and tilt_deg <= 6.0
          and float(np.min(x)) >= 0.35
          and spread <= spread_max
          and feat_p >= 0.5
          and qd_rms <= 0.7
          and float(np.hypot(v[0], v[1])) <= 0.08
          and cur_ok)
    env._rec_hold_n = env._rec_hold_n + 1 if ok else 0
    hold_need = max(int(round(0.5 / env.dt)), 1)
    success = env._rec_hold_n >= hold_need

    # 5) Time tax — every tick until termination, INCLUDING the
    #    success hold (the directive's speed incentive; a normal
    #    ~4 s recovery costs ~8% of the success bonus at defaults).
    reward -= env.dt

    # 6) Terminal handling.
    r_bonus = 0.0
    if success:
        r_bonus = 50.0
        reward += r_bonus
        term = True
        info["termination_reason"] = "recover_success"
    elif term or trunc:
        # timeout / safety-envelope end without success: pay at
        # least the maximum remaining time tax so aborting early
        # (or coasting into the horizon) never beats recovering.
        fail = 1.25 * env.episode_steps * env.dt
        reward -= fail
        info["reward_recover_fail"] = -fail
    if term or trunc:
        # Stochastic rollout bookkeeping is diagnostic only.  The
        # adaptive sampler/admission state is updated exclusively by
        # apply_recover_certification() from deterministic MJX passes.
        kind = getattr(env._goal_traj, "start_kind", "?")
        bucket = env.RECOVER_KIND_BUCKETS.get(kind, -1)
        if (getattr(env._goal_traj, "recover_rsi", False)
                or getattr(env._goal_traj, "recover_rsi_bank",
                          False)):
            # RSI episodes (ref-path goal.recover_rsi_frac OR
            # harvested-bank goal.recover_rsi_bank_frac) practice
            # on-path waypoints, not the family's own start: keep
            # them OUT of the rollout EMA/counters and the
            # C-trainer self-cert stats so no curriculum or
            # diagnostic signal is inflated by easier on-path
            # spawns. Each logs under its own suffix.
            suffix = ("_rsi" if getattr(env._goal_traj,
                                        "recover_rsi", False)
                     else "_rsibank")
            info[f"recover_episode_{kind}{suffix}"] = 1.0
            info[f"recover_success_{kind}{suffix}"] = (
                1.0 if success else 0.0)
        else:
            # Do not use the strict stochastic success bit as replay
            # error: exploration noise can interrupt an otherwise good
            # 0.5 s hold.  Terminal potential shortfall preserves a
            # graded signal; a true safety termination is maximal error.
            training_error = (0.0 if success else
                              (1.0 if term and not trunc else
                               float(np.clip(1.0 - phi, 0.0, 1.0))))
            info["recover_training_error"] = training_error
            ema, n = env._rec_rollout_stats.get(kind, (0.5, 0))
            beta = float(cfg_get(env.cfg, "goal",
                                 "recover_ema_beta", default=0.25))
            updated = (
                (1.0 - beta) * ema
                + beta * (1.0 if success else 0.0),
                n + 1)
            env._rec_rollout_stats[kind] = updated
            successes, episodes = env._rec_rollout_counts.get(
                kind, (0, 0))
            env._rec_rollout_counts[kind] = (
                successes + int(success), episodes + 1)
            # Preserve the legacy self-certified curriculum for the
            # C trainer.  MJX recovery runs opt into external
            # certification in train_ppo_mjx._env_kwargs, so their
            # noisy PPO actions can never mutate _rec_stats.
            if not env._rec_external_certification:
                cert_successes, cert_episodes = env._rec_stats.get(
                    kind, (0, 0))
                env._rec_stats[kind] = (
                    cert_successes + int(success), cert_episodes + 1)
                if bucket >= 0:
                    env.apply_recover_training_error_batch({
                        bucket: (training_error, 1)})
            info[f"recover_episode_{kind}"] = 1.0
            info[f"recover_success_{kind}"] = (
                1.0 if success else 0.0)
            if bucket >= 0:
                info[f"recover_episode_bucket_{bucket}"] = 1.0
                info[f"recover_success_bucket_{bucket}"] = (
                    1.0 if success else 0.0)

    info["reward_recover_pot"] = r_pot
    info["reward_recover_bonus"] = r_bonus
    info["reward_recover_time"] = -env.dt
    info["recover_phi"] = phi
    info["recover_U"] = feat_u
    info["recover_L"] = feat_l
    info["recover_H"] = feat_h
    info["recover_M"] = feat_m
    info["recover_P"] = feat_p
    info["recover_hold_n"] = float(env._rec_hold_n)
    info["recover_success"] = 1.0 if success else 0.0
    info["recover_rsi_episode"] = (
        1.0 if getattr(env._goal_traj, "recover_rsi", False)
        else 0.0)
    info["recover_rsi_bank_episode"] = (
        1.0 if getattr(env._goal_traj, "recover_rsi_bank", False)
        else 0.0)
    info["recover_min_load"] = float(np.min(x))
    info["recover_tilt_deg"] = tilt_deg
    kind = getattr(env._goal_traj, "start_kind", "?")
    bucket = env.RECOVER_KIND_BUCKETS.get(kind, -1)
    info["recover_start_kind_id"] = float(
        env.RECOVER_KIND_IDS.get(kind, -1))
    info["recover_start_bucket"] = float(bucket)
    info["recover_active_families"] = float(env._rec_active_n)
    info["recover_frontier_bucket"] = float(env._rec_active_n - 1)
    info["recover_max_unlocked_bucket"] = float(
        env._rec_active_n - 1)
    info["recover_focus_bucket"] = float(env._rec_focus_bucket)
    info["recover_weakest_bucket"] = float(
        -1 if env._rec_weak_bucket is None else env._rec_weak_bucket)
    info[f"recover_reset_height_mm_{kind}"] = float(
        env._rec_reset_height_mm)
    info[f"recover_reset_tilt_deg_{kind}"] = float(
        env._rec_reset_tilt_deg)
    info[f"recover_reset_min_load_n_{kind}"] = float(
        env._rec_reset_min_load_n)
    info[f"recover_reset_pad_spread_mm_{kind}"] = float(
        env._rec_reset_pad_spread_mm)
    for rec_kind in env._recover_active_kinds():
        cert_successes, cert_episodes = env._rec_stats.get(
            rec_kind, (0, 0))
        cert_fraction = (cert_successes / cert_episodes
                         if cert_episodes else 0.0)
        info[f"recover_curriculum_fraction_{rec_kind}"] = float(
            cert_fraction)
        info[f"recover_curriculum_successes_{rec_kind}"] = float(
            cert_successes)
        info[f"recover_curriculum_episodes_{rec_kind}"] = float(
            cert_episodes)
        roll_ema, roll_n = env._rec_rollout_stats.get(
            rec_kind, (0.5, 0))
        info[f"recover_rollout_ema_{rec_kind}"] = float(roll_ema)
        info[f"recover_rollout_n_{rec_kind}"] = float(roll_n)
        roll_successes, roll_episodes = env._rec_rollout_counts.get(
            rec_kind, (0, 0))
        info[f"recover_rollout_fraction_{rec_kind}"] = float(
            roll_successes / roll_episodes if roll_episodes else 0.0)
    error_priority = env._recover_training_error_distribution()
    if error_priority is None:
        error_priority = np.zeros(env._rec_active_n, dtype=float)
    for rec_bucket in range(env._rec_active_n):
        stats = [env._rec_stats.get(k, (0, 0))
                 for k in env._recover_family_kinds(rec_bucket)]
        if stats:
            successes = sum(v[0] for v in stats)
            episodes = sum(v[1] for v in stats)
            info[
                f"recover_curriculum_bucket_{rec_bucket}_success_fraction"
            ] = float(successes / episodes if episodes else 0.0)
            info[f"recover_curriculum_bucket_{rec_bucket}_successes"] = (
                float(successes))
            info[f"recover_curriculum_bucket_{rec_bucket}_episodes"] = (
                float(episodes))
        error_ema, error_episodes = (
            env._rec_training_error_stats.get(rec_bucket, (0.0, 0)))
        info[f"recover_training_error_ema_bucket_{rec_bucket}"] = (
            float(error_ema))
        info[f"recover_training_error_n_bucket_{rec_bucket}"] = (
            float(error_episodes))
        info[f"recover_training_error_priority_bucket_{rec_bucket}"] = (
            float(error_priority[rec_bucket]))
    for rec_bucket, probability in enumerate(
            env._recover_bucket_weights()):
        info[f"recover_sample_probability_bucket_{rec_bucket}"] = (
            float(probability))
    return reward, term, info
