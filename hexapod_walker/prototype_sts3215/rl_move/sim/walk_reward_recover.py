"""Posture-recovery reward functions (getup / recover_to_plant), moved out of SimHexapodJointWalkEnv.

Each function here is the whole body of one reward method moved
mechanically: ``env`` is the env instance (the former ``self``), the other
parameters are the method's own and the return statements are its own, so
the method that remains on the class is a one-line delegate.  Bodies are
byte-identical to the original apart from ``self`` -> ``env`` and
re-indentation; the section comments travelled with the code.
"""
from __future__ import annotations

import math

import numpy as np

from rl_move.config import cfg_get
from rl_move.robot_state import over_current_reading
from .walk_task import (
    K_PROG, K_WALK, SIGMA_V, WALK_DIRECTION_MIN_SPEED_M_S,
    _add_walk_direction_info,
)


def recover_reward(env, reward, term, trunc, info):
    # 1) Strip kernel + tilt shaping (same rationale as getup).
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
    # Recovery strain gate: don't declare recovery while a motor is over
    # ~3 A. Read the stall-sensitive current (default power model reads ~0
    # at a strain/stall, which would make this gate vacuous); falls back to
    # servo_current on hardware / legacy model.
    cur = over_current_reading(env._state)
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


def getup_reward(env, reward, info):
    r_strip = (info.get("reward_task", 0.0)
               + info.get("reward_roll", 0.0)
               + info.get("reward_pitch", 0.0))
    if r_strip != 0.0:
        reward -= r_strip
        info["reward_task"] = 0.0
        info["reward_roll"] = 0.0
        info["reward_pitch"] = 0.0

    # 2) Supported-stand score S in [0, 1] — the structural
    #    height<->contact coupling. Every factor is a fade with a
    #    downhill slope; only genuinely carried height scores.
    # Graded per-foot load saturation (bank-measured: an honest
    # plant carries its light tripod at only ~0.7-1.2 N, so a hard
    # threshold reads a REAL stand as 4/6 feet). An airborne flag
    # leg contributes exactly 0 either way; grading just keeps the
    # slope (holdstill1 lesson) and reads honest stands as ~0.95.
    load_sat = 0.0
    touch_sum_n = 0.0
    for f in range(6):
        adr = env._touch_adr[f]
        if adr >= 0:
            t_n = max(float(env.data.sensordata[adr]), 0.0)
            touch_sum_n += t_n
            load_sat += min(t_n, 1.0)
    f_feet = (load_sat / 6.0) ** 2
    z_plant, weight_n = env._getup_geom()
    z_belly = 38.0 * 0.001
    z = float(env.data.xpos[env._chassis_bid, 2])
    # Full height credit at a FRACTION of the rigid-FK plant span:
    # servo/contact compliance sags the physical stance ~15-25 mm
    # below the FK height (bank-measured 148.5 vs 170.8 mm), and a
    # real stand must be able to score 1.0.
    z_full = z_belly + 0.80 * max(z_plant - z_belly, 1e-3)
    f_h = min(max((z - z_belly) / max(z_full - z_belly, 1e-3),
                  0.0), 1.0)
    # Symmetric ceiling: a stilt pop overshoots the plant height —
    # fade to 0 between +20 and +80 mm above it, so "higher" is
    # never a strategy.
    over = z - (z_plant + 0.02)
    if over > 0.0:
        f_h *= min(max(1.0 - over / 0.06, 0.0), 1.0)
    t_roll, t_pitch = env._true_roll_pitch()
    tilt_deg = max(abs(t_roll), abs(t_pitch)) * 180.0 / math.pi
    f_level = min(max(1.0 - tilt_deg / 20.0, 0.0), 1.0)
    curl = env._curl_dist()
    fp_ok = 40.0 * 0.001
    fp_hi = 120.0 * 0.001
    f_fp = min(max((fp_hi - curl) / max(fp_hi - fp_ok, 1e-6),
                   0.0), 1.0)
    # No-flag fade on the pad-height SPREAD (highest minus lowest
    # pad, world z) — ground-reference-free, so it works from
    # arbitrary spawn poses where _pad_z_ref means nothing. The
    # mean-footprint factor above barely notices ONE straightened
    # leg; the video-confirmed flag poses ride 100-160 mm of
    # spread and fade to ~0 here, while honest gait swings
    # (~25-40 mm) keep exactly 1.0. Fade over [flag, 2*flag]
    # (PLANT_SPEC.flag_leg_mm 60 -> 120), never a hard zero.
    pad_z = np.array([float(env.data.xpos[b, 2])
                      for b in env._pad_bids])
    spread = float(np.max(pad_z) - np.min(pad_z))
    flag_m = 60.0 * 0.001
    f_flag = min(max((2.0 * flag_m - spread) / max(flag_m, 1e-6),
                     0.0), 1.0)
    s_stand = f_h * f_feet * f_level * f_fp * f_flag

    # 3) Staged pipeline potential P (weighted SUM along untangle
    #    -> weight-on-feet -> supported stand; the curl itself is
    #    unpaid but never punished — the ratchet banks bests, and
    #    the "any" start distribution backward-chains across it) +
    #    one-shot ratchet income. The baseline seeds at the
    #    episode's FIRST tick so the spawn posture is never income
    #    (the _score_best convention).
    w_z, w_l, w_s = 0.15, 0.25, 0.60
    q_now = env._mujoco_to_logical_q(env.data.qpos[env._qadr])
    mean_q_deg = float(np.mean(np.abs(q_now))) * 180.0 / math.pi
    f_unt = min(max(1.0 - mean_q_deg / 60.0, 0.0), 1.0)
    # Middle stage = fraction of BODY WEIGHT carried by the feet
    # (measured ground reaction, saturating at 85% of m*g — the
    # honest plant's tripod imbalance never quite reads 100%).
    # Bank-measured to be the only scalar monotone along an honest
    # rise from the crouch on (0.07 belly -> 0.68 crouch-hold ->
    # 1.0 ramp/stand): footprint distance barely moves during the
    # curl (152->130 mm) and the reference crouch is joint-wise
    # FARTHER from the plant than the zero pose is (35 vs 30 deg),
    # so both of those metrics leave the honest path a reward
    # desert. Newton caps this one at m*g — pressing harder is not
    # a strategy, and carrying weight on feet IS the task.
    f_load = min(touch_sum_n / (0.85 * weight_n), 1.0)
    p_now = w_z * f_unt + w_l * f_load + w_s * s_stand
    if env._getup_best is None:
        env._getup_best = p_now
    d_p = max(p_now - env._getup_best, 0.0)
    if d_p > 0.0:
        env._getup_best = p_now
    # Recalibrated 08-22 (getup_honest_ordering dig-in,
    # the retired pre-v2 GETUP bank): at the old default 60
    # a genuine partial rise (holding a real mid-ramp crouch, feet
    # loaded) earned LESS than freezing at the untouched spawn
    # pose (partial -12.16 vs freeze -11.26, bank-measured 3
    # seeds) — not a values-need-remeasuring drift, a real
    # under-pricing: the one-shot ratchet credit for the honest
    # partial-stand's potential gain (~+10 at k=60) was smaller
    # than the ADDITIONAL regularizer (gyro/action/current) cost
    # of actually executing the rise motion the freeze never pays
    # (measured other-than-prog totals -21.6 partial vs -11.7
    # freeze, seed 11). Those regularizers are intentionally left
    # untouched (they price real physics, not this task's shape;
    # see the strip comment above) so the fix is sizing the
    # progress ratchet to clear that physical cost with margin,
    # not editing the physics charges. 200 gave partial +10.8 >
    # freeze -11.5 (>=20 margin) while leaving every other GETUP
    # bank ordering intact (replay/flagleg/stilt/thrash all keep
    # their required gaps at this value, swept 60->500).
    #
    # RE-RECALIBRATED 09-03 (test_getup_honest_ordering went RED
    # from the SAME-DAY q0-frame fix, not a new task-shape bug):
    # `freeze`'s q0 used to feed MuJoCo's raw knee-relative qpos
    # straight into q_rad_to_action, double-shifting the knee into
    # a genuinely worse held pose; fixing that (see `_q0_robot_abs`
    # call above, OPERATOR_QUESTIONS.md 09-03) made freeze cheaper
    # to hold (mean ret -40.4 -> -30.3, bank-measured 3 seeds) —
    # correct, since a physically-consistent frozen pose really
    # does cost less gyro/action/current than the old bugged one —
    # while `partial` is untouched by that fix (-35.1). That
    # erodes the 08-22 margin entirely (partial's ratchet credit at
    # k=200 no longer clears freeze's now-accurate, lower physical
    # cost) without any change to the honest partial-rise's own
    # cost or progress. d_p is ~0 for a held `freeze` pose (its
    # potential P never rises after the first tick), so r_prog for
    # freeze is ~flat in k_prog while r_prog for partial scales
    # with it (measured slope ~0.18 return/unit-k for partial vs
    # ~0.006 for freeze) — raising k_prog is still the right lever
    # (partial's cost is real physics, per the 08-22 note; the fix
    # is sizing the credit, not the charges). 350 gives partial
    # -8.2 > freeze -29.3 (>=20 margin again) while every other
    # GETUP bank ordering stays intact at this value (replay/
    # flagleg/stilt/thrash margins all widen, swept 250->350;
    # ratchet `best` fractions are potential-only and untouched).
    r_prog = 350.0 * d_p

    # 4) Gated steady income. Zero-command ticks: quiet-stand pay,
    #    gated hard (S^3) so partial/flagged stands earn scraps
    #    with a slope. Commanded ticks: the walk kernel + linear
    #    progress, gated by a gait-tolerant stand score (a tripod
    #    of loaded feet is full credit mid-stride) TIMES achieved
    #    progress (the walk_kernel_prog_gate lesson, baked in from
    #    the start — a parked robot earns ~0). A belly-shuffle
    #    earns ~0 through f_h regardless of its progress.
    goal = env._current_goal()
    vx_ref = float(getattr(goal, "vx_ref", 0.0)) if goal else 0.0
    vy_ref = float(getattr(goal, "vy_ref", 0.0)) if goal else 0.0
    s_ref = float(np.hypot(vx_ref, vy_ref))
    r_hold = 0.0
    r_walk = 0.0
    if s_ref <= 1e-3:
        k_hold = 0.8
        sig_qd = 0.3
        qd2 = float(np.mean(np.square(env._state.joint_velocity)))
        still = math.exp(-qd2 / (2.0 * sig_qd ** 2))
        r_hold = k_hold * (s_stand ** 3) * still
    else:
        s_gait = (f_h * f_level * f_fp * f_flag
                  * min(load_sat / 3.0, 1.0) ** 2)
        v = env._body_vel_xy()
        err = float(np.hypot(v[0] - vx_ref, v[1] - vy_ref))
        along = (v[0] * vx_ref + v[1] * vy_ref) / s_ref
        frac = along / s_ref
        kern = (K_WALK * math.exp(-(err ** 2) / (2.0 * SIGMA_V ** 2))
                * min(max(frac, 0.0), 1.0))
        prog = K_PROG * min(frac, 1.25)
        r_walk = s_gait * (kern + prog)
        info["walk_vel_err"] = err
        info["walk_speed"] = float(np.hypot(v[0], v[1]))
        _add_walk_direction_info(
            info, float(v[0]), float(v[1]), vx_ref, vy_ref,
            min_speed_m_s=WALK_DIRECTION_MIN_SPEED_M_S)
        info["getup_gait_gate"] = s_gait

    reward += r_prog + r_hold + r_walk
    info["reward_getup_prog"] = r_prog
    info["reward_getup_hold"] = r_hold
    info["reward_getup_walk"] = r_walk
    info["getup_S"] = s_stand
    info["getup_P"] = p_now
    info["getup_best"] = float(env._getup_best)
    info["getup_feet_loaded"] = load_sat
    info["getup_f_load"] = f_load
    info["getup_f_height"] = f_h
    info["getup_f_level"] = f_level
    info["getup_f_footprint"] = f_fp
    info["getup_f_flag"] = f_flag
    return reward, info
