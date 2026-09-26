"""Always-on training telemetry callback for ``train_ppo_mjx``.

``_Track`` charts fps, episode stats, env/reward-part means, termination
counts, exact recover-bucket outcomes and the optimisation reward-per-tick
series to W&B every rollout, and writes the periodic / step-tagged
checkpoints. It used to be defined inside ``train_ppo_mjx.main`` and
closed over four of its locals; those are now constructor arguments
(``args``, ``venv``, ``run``, ``out_path``) held on the instance and read
at the same points as before. The gate/anneal/cert callbacks stay in
``main`` -- they close over run-specific state that is rebuilt per flag.
"""
from __future__ import annotations

import time

import numpy as np
from stable_baselines3.common.callbacks import BaseCallback

from .recover_curriculum import (
    _recover_episode_outcome, _recover_episode_training_error)


class _Track(BaseCallback):
    """fps, ep stats, env/reward-part means (campaign parity, sampled
    across envs to stay cheap at B=4096), termination-reason counts,
    periodic checkpoints. Mirrors train_ppo_sim's
    _make_reward_parts_callback so MJX runs chart like C runs."""

    PART_KEYS = (
        "reward_task", "reward_roll", "reward_pitch", "reward_height",
        "reward_gyro", "reward_action", "reward_action_delta",
        "reward_current", "reward_unload", "reward_rise_progress",
        "reward_rise_milestone", "reward_rise_finish",
        "reward_curl_progress", "reward_curl_milestone", "reward_walk",
        "reward_walk_prog", "reward_swing", "reward_current_hot",
        "reward_stance", "reward_clearance", "reward_flag_leg",
        "reward_current_max", "reward_termination",
        "reward_phase_contact", "reward_support_margin",
        "reward_load_even", "reward_step_event", "reward_drag",
        "reward_park_duty",
        "reward_end_posture", "reward_effort",
        "reward_walk_yaw", "reward_quad_clear", "reward_quad_plant",
        "reward_hold_barrier",
        # Gate factors (08-10 postgate1 dig-in: rise_posture_factor
        # was computed in-env but never logged, blinding triage to
        # the gate's live value).
        "rise_posture_factor", "rise_income_factor")
    AUX_ABS = ("roll_deg", "pitch_deg")       # logged as abs_<k>
    AUX = ("track_err_deg", "height_err_mm", "mean_current_a",
           "walk_vel_err", "walk_speed",
           "walk_direction_err_deg",
           "phase_agreement",
           "walk_anchor_frac",
           "walk_step_denied", "walk_step_bank_m",
           "walk_loadslip_ratio", "walk_loadslip_factor",
           "walk_yaw_err",
           "quad_clear_mm", "quad_fronts_off",
           "quad_planted_frac")  # own names
    # Any OTHER numeric scalar the env drops into info is logged
    # as a plain mean under env/<k> (operator 08-10: the whitelist
    # above kept drifting behind the envs — reward_rise_ref,
    # walk_wz, rise_plant_factor etc. were computed but invisible
    # in W&B, and W&B is the primary triage surface). The lists
    # stay for their special semantics (AUX* means abs()).
    SKIP = ("TimeLimit.truncated", "terminal_observation",
            "termination_reason", "goal_mode", "walk_bucket",
            "episode", "bc_target", "amp_obs_style")
    SAMPLE = 256      # envs sampled per step for the means

    def __init__(self, args, venv, run, out_path):
        super().__init__()
        self._args = args
        self._venv = venv
        self._run = run
        self._out_path = out_path
        self._t0 = time.monotonic()
        self._last_save = 0
        self._last_snapshot = 0
        self._sum: dict[str, float] = {}
        self._cnt: dict[str, int] = {}
        self._terms: dict[str, int] = {}
        # Mode-experts active-tick accounting (directive
        # fb_20260815T013349_488ffd: report ACTIVE ticks per
        # expert, not just total env steps). Cumulative over the
        # whole run; indices follow gru_policy.EXPERTS_ORDER.
        self._exp_ticks = np.zeros(4, dtype=np.float64)
        # Joystick command telemetry (08-15, operator directive
        # fb_20260815T114414, SIMPLIFIED by fb_20260815T115650):
        # cumulative ACTIVE-TICK accounting of the env's
        # goal.walk_cmd_metrics info keys — raw signed v_along and
        # ratio-of-sums (NOT mean of per-tick ratios). No
        # per-heading bins in training: uniform [-pi,pi] heading
        # sampling + the signed average already zeroes out
        # command-ignorant motion; fixed-direction panels are
        # held-out EVAL tools. Zero-cost when the env never emits
        # the keys.
        self._cmd_cum = {"along": 0.0, "cmd": 0.0, "cross": 0.0,
                         "wrong": 0.0, "n": 0.0}
        self._cmd_stride = 1
        # Overall optimization-progress metric (operator feedback
        # fb_20260815T131225_c8442f, 08-15): "is PPO still getting
        # more total reward per real transition" — computed
        # directly from the raw per-step scalar rewards SB3 hands
        # the callback (self.locals["rewards"], the actual PPO
        # training signal, captured before the truncation-bootstrap
        # adjustment further down collect_rollouts), NOT from
        # ep_rew_mean/ep_len_mean (those distort under changing
        # episode length / partial episodes). Per-rollout sum+count
        # reset every _on_rollout_end; cumulative + EMA never reset.
        self._reward_sum = 0.0
        self._reward_n = 0
        self._reward_sum_cum = 0.0
        self._reward_n_cum = 0
        self._reward_ema: float | None = None
        # Exact completed-episode recovery scores. These inspect every
        # env terminal, not the 256-env telemetry sample above.
        self._recover_window: dict[int, list[int]] = {}
        self._recover_cumulative: dict[int, list[int]] = {}
        self._recover_error_window: dict[int, list[float]] = {}
        self._recover_error_cumulative: dict[int, list[float]] = {}

    def _acc(self, k: str, v: float) -> None:
        self._sum[k] = self._sum.get(k, 0.0) + v
        self._cnt[k] = self._cnt.get(k, 0) + 1

    def _on_step(self) -> bool:
        rewards = self.locals.get("rewards")
        if rewards is not None:
            arr = np.asarray(rewards)
            self._reward_sum += float(arr.sum())
            self._reward_n += int(arr.size)
        if self._args.gru_experts:
            no = self.locals.get("new_obs")
            if no is not None and getattr(no, "ndim", 0) == 2 \
                    and no.shape[1] >= 6:
                tail = no[:, -6:]
                # EXPERTS_ORDER = (rise, hold, lower, loco);
                # obs tail = (hold, rise, lower, walk, turn, quad)
                self._exp_ticks[0] += float(tail[:, 1].sum())
                self._exp_ticks[1] += float(tail[:, 0].sum())
                self._exp_ticks[2] += float(tail[:, 2].sum())
                self._exp_ticks[3] += float(tail[:, 3:].sum())
        infos = self.locals.get("infos", ())
        stride = max(1, len(infos) // self.SAMPLE)
        for info in infos[::stride]:
            for k in self.PART_KEYS:
                if k in info:
                    self._acc(k, float(info[k]))
            for k in self.AUX_ABS:
                if k in info:
                    self._acc(f"abs_{k}", abs(float(info[k])))
            for k in self.AUX:
                if k in info:
                    self._acc(k, abs(float(info[k])))
            for k, v in info.items():
                if (k in self.PART_KEYS or k in self.AUX
                        or k in self.AUX_ABS or k in self.SKIP):
                    continue
                if isinstance(v, bool) or not isinstance(
                        v, (int, float, np.integer, np.floating)):
                    continue
                self._acc(k, float(v))
            if "track_err_deg" in info:
                self._acc("pct_within_1deg",
                          1.0 if float(info["track_err_deg"]) <= 1.0
                          else 0.0)
            if "v_along_cmd_m_s" in info:
                # Cumulative active-tick command telemetry (see
                # __init__); sums, so ratios come out as
                # sum(v_along)/sum(cmd_speed), never mean-of-ratios.
                self._cmd_stride = stride
                al = float(info["v_along_cmd_m_s"])
                self._cmd_cum["along"] += al
                self._cmd_cum["cmd"] += float(
                    info.get("cmd_speed_m_s", 0.0))
                self._cmd_cum["cross"] += float(
                    info.get("v_cross_abs_m_s", 0.0))
                self._cmd_cum["wrong"] += float(
                    info.get("wrong_way", 0.0))
                self._cmd_cum["n"] += 1.0
        dones = self.locals.get("dones")
        if dones is not None and np.any(dones):
            for i in np.flatnonzero(dones):
                outcome = _recover_episode_outcome(infos[i])
                if outcome is not None:
                    bucket, success = outcome
                    for bank in (self._recover_window,
                                 self._recover_cumulative):
                        counts = bank.setdefault(bucket, [0, 0])
                        counts[0] += int(success)
                        counts[1] += 1
                training_error = _recover_episode_training_error(
                    infos[i])
                if training_error is not None:
                    bucket, error = training_error
                    for bank in (self._recover_error_window,
                                 self._recover_error_cumulative):
                        values = bank.setdefault(bucket, [0.0, 0.0])
                        values[0] += error
                        values[1] += 1.0
                r = infos[i].get("termination_reason") or (
                    "truncated"
                    if infos[i].get("TimeLimit.truncated")
                    else "done")
                self._terms[r] = self._terms.get(r, 0) + 1
        return True

    def _on_rollout_end(self) -> None:
        if self._recover_error_window:
            # Every host env receives the same aggregate, avoiding 512
            # tiny local EMAs whose sparse bucket histories diverge.
            self._venv.env_method(
                "apply_recover_training_error_batch",
                {bucket: (values[0], int(values[1]))
                 for bucket, values in self._recover_error_window.items()})
        fps = self.num_timesteps / max(time.monotonic() - self._t0,
                                       1e-9)
        payload = {"time/env_steps_per_s": fps,
                   "time/total_env_steps": self.num_timesteps,
                   "global_step": self.num_timesteps}
        payload.update({f"env/{k}": self._sum[k] / self._cnt[k]
                        for k in self._sum})
        payload.update({f"terminations/{k}": v
                        for k, v in self._terms.items()})
        for bucket, (successes, episodes) in sorted(
                self._recover_window.items()):
            stem = f"TRAIN/recover_bucket_{bucket}"
            payload[f"{stem}_success_fraction"] = successes / episodes
            payload[f"{stem}_successes"] = successes
            payload[f"{stem}_episodes"] = episodes
        for bucket, (successes, episodes) in sorted(
                self._recover_cumulative.items()):
            stem = f"TRAIN/recover_bucket_{bucket}"
            payload[f"{stem}_success_fraction_cumulative"] = (
                successes / episodes)
            payload[f"{stem}_episodes_cumulative"] = episodes
        for bucket, (error_sum, episodes) in sorted(
                self._recover_error_window.items()):
            stem = f"TRAIN/recover_bucket_{bucket}"
            payload[f"{stem}_training_error_mean"] = (
                error_sum / max(episodes, 1.0))
            payload[f"{stem}_training_error_episodes"] = episodes
        for bucket, (error_sum, episodes) in sorted(
                self._recover_error_cumulative.items()):
            stem = f"TRAIN/recover_bucket_{bucket}"
            payload[f"{stem}_training_error_mean_cumulative"] = (
                error_sum / max(episodes, 1.0))
        if self._reward_n > 0:
            # optimization/* (fb_20260815T131225_c8442f): "is PPO
            # continuing to get more total reward per real
            # transition" — an OPTIMIZATION/objective score, not a
            # behavioral-success claim; read it beside the task
            # (joystick/v_along_m_s) and safety (terminations/*)
            # metrics, never alone. reward/tick rising + task
            # rising = useful learning; reward/tick rising + task
            # falling = exploiting/prioritizing a different reward
            # term; reward/tick flat = optimization stalled.
            rpt = self._reward_sum / self._reward_n
            payload["optimization/reward_per_tick"] = rpt
            self._reward_sum_cum += self._reward_sum
            self._reward_n_cum += self._reward_n
            payload["optimization/reward_per_tick_cumulative"] = (
                self._reward_sum_cum / self._reward_n_cum)
            self._reward_ema = (rpt if self._reward_ema is None else
                                0.9 * self._reward_ema + 0.1 * rpt)
            payload["optimization/reward_per_tick_ema"] = (
                self._reward_ema)
        self._reward_sum, self._reward_n = 0.0, 0
        if self._cmd_cum["n"] > 0:
            # Operator-named joystick command-following metrics
            # (fb_20260815T114414, simplified fb_20260815T115650).
            # HEADLINE (joystick/*): raw signed m/s along the
            # requested direction over active ticks — per-rollout
            # mean, active-tick-weighted cumulative mean, and the
            # active-tick audit count. Everything else (cross-track,
            # wrong-way, ratio-of-sums) is secondary under train/.
            # NO per-heading series here — fixed-direction checks
            # live in held-out EVAL only.
            c = self._cmd_cum
            n_r = self._cnt.get("v_along_cmd_m_s", 0)
            if n_r:
                s_al = self._sum["v_along_cmd_m_s"]
                s_cmd = self._sum.get("cmd_speed_m_s", 0.0)
                payload["joystick/v_along_m_s"] = s_al / n_r
                payload["train/cmd_speed_active_m_s"] = (
                    s_cmd / max(self._cnt.get("cmd_speed_m_s", 1), 1))
                if s_cmd > 0.0:
                    payload["train/v_along_ratio_active"] = (
                        s_al / s_cmd)
            payload["joystick/v_along_m_s_cumulative"] = (
                c["along"] / c["n"])
            if c["cmd"] > 0.0:
                payload["train/v_along_ratio_active_cumulative"] = (
                    c["along"] / c["cmd"])
            payload["train/v_cross_abs_m_s"] = c["cross"] / c["n"]
            payload["train/wrong_way_frac"] = c["wrong"] / c["n"]
            # Estimate: sampled count x sample stride (the info
            # sweep reads every stride-th env).
            payload["joystick/active_ticks"] = (
                c["n"] * self._cmd_stride)
        if self._args.gru_experts:
            from .gru_policy import EXPERTS_ORDER
            tot = max(float(self._exp_ticks.sum()), 1.0)
            for i, name in enumerate(EXPERTS_ORDER):
                payload[f"experts/active_ticks_{name}"] = float(
                    self._exp_ticks[i])
                payload[f"experts/tick_frac_{name}"] = float(
                    self._exp_ticks[i]) / tot
            pol = self.model.policy
            if hasattr(pol, "_log_stds"):
                for name, ls in zip(EXPERTS_ORDER,
                                    pol._log_stds()):
                    payload[f"experts/std_{name}"] = float(
                        ls.detach().exp().mean())
        buf = self.model.ep_info_buffer
        if buf:
            payload["rollout/ep_rew_mean"] = float(
                np.mean([e["r"] for e in buf]))
            payload["rollout/ep_len_mean"] = float(
                np.mean([e["l"] for e in buf]))
        # heading_selfdistill diagnostics (walkcurr, 09-09): see
        # heading_selfdistill.heading_selfdistill_wandb_payload's
        # own docstring -- this callback is the only place SB3-
        # logger keys reach W&B in this file, so these 3 keys were
        # otherwise silent on W&B even while the mechanism fired
        # (gap flagged CURRENT_TRUTHS/walkcurr STATUS 09-09 ~17:1x).
        # Zero-cost / additive-only when the module is off/absent.
        from .heading_selfdistill import heading_selfdistill_wandb_payload
        payload.update(heading_selfdistill_wandb_payload(
            getattr(self.model, "logger", None)))
        # heading_adv_norm diagnostics (walkcurr, 09-09): same W&B
        # forwarding gap as heading_selfdistill above.
        from .heading_adv_norm import heading_adv_norm_wandb_payload
        payload.update(heading_adv_norm_wandb_payload(
            getattr(self.model, "logger", None)))
        # goal_mode_adv_norm diagnostics (walkcurr, 09-13): same
        # W&B forwarding gap as heading_adv_norm above.
        from .goal_mode_adv_norm import goal_mode_adv_norm_wandb_payload
        payload.update(goal_mode_adv_norm_wandb_payload(
            getattr(self.model, "logger", None)))
        # goal_mode_batch_split diagnostics (walkcurr, 09-14): same
        # W&B forwarding gap as goal_mode_adv_norm above.
        from .goal_mode_batch_split import (
            goal_mode_batch_split_wandb_payload)
        payload.update(goal_mode_batch_split_wandb_payload(
            getattr(self.model, "logger", None)))
        if self._run is not None:
            import wandb
            wandb.log(payload)
        self._sum, self._cnt, self._terms = {}, {}, {}
        self._recover_window = {}
        self._recover_error_window = {}
        if (self._args.save_every and self.num_timesteps - self._last_save
                >= self._args.save_every):
            self._last_save = self.num_timesteps
            self.model.save(self._out_path)
            print(f"[mjx-train] checkpoint @ {self.num_timesteps:,} "
                  f"-> {self._out_path} ({fps:,.0f} env-steps/s)")
        if (self._args.snapshot_every and self.num_timesteps
                - self._last_snapshot >= self._args.snapshot_every):
            self._last_snapshot = self.num_timesteps
            snap_path = self._out_path.with_name(
                f"{self._out_path.stem}_s{self.num_timesteps}.zip")
            self.model.save(snap_path)
            print(f"[mjx-train] erosion snapshot @ "
                  f"{self.num_timesteps:,} -> {snap_path}")
