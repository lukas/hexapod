"""Servo-current prices of the balance env's _step_finish: per-servo hot-
current penalty, the rise pre-tuck current price and the current rate-
of-rise penalty; moved verbatim out of sim_env.py.
"""
from __future__ import annotations

import numpy as np

from rl_move.config import cfg_get
from rl_move.robot_state import over_current_reading

from .balance_helpers import current_streak_ticks_step


def current_penalties(env, parts, reward):
    """Per-servo hot-current, pre-tuck and current-rate prices; moved
    verbatim from SimHexapodBalanceEnv._step_finish.
    """
    # Per-servo hot-current penalty (RL_PLAN_NEXT.md §4 in git history, default OFF).
    # The aggregate current penalty lets the policy park all load on
    # one knee; visual eval of the cw champions found tripod stances
    # with one servo above 1.5 A for most of the episode. Charge
    # concentration directly: quadratic above a soft per-servo
    # threshold, so 6 legs at 0.4 A cost nothing while one at 1.8 A
    # hurts. Enable with --cfg-set reward.k_current_hot=<k>.
    k_hot = float(cfg_get(env.cfg, "reward", "k_current_hot",
                          default=0.0))
    if k_hot > 0.0 and env._state.servo_current is not None:
        hot_a = float(cfg_get(env.cfg, "reward", "current_hot_a",
                              default=1.0))
        # Per-servo hotspot price is trip-proximity shaping: read the
        # stall-sensitive current (default power model reads ~0 at a stall),
        # falling back to servo_current on hardware / legacy model.
        over = np.maximum(over_current_reading(env._state) - hot_a, 0.0)
        r_hot = -k_hot * float(np.sum(over ** 2))
        parts["reward_current_hot"] = r_hot
        reward += r_hot
    # Pre-tuck current price (walkcurr rise track, 2026-09-14 --
    # escalation from probe_rise_current_envelope.py's own finding:
    # the mesh-native scripted rise reference clears the corrected
    # +66%-mass mesh's over_current trip, with real ~16% margin,
    # ONLY because it stays near-zero-torque while tucking the feet
    # under the body and only draws real current AFTER the bridge
    # pose is reached, then presses. Every rise-pricing lever tried
    # before this (current-headroom-gate, curl-geometry-gate ON THE
    # HEIGHT RAMP via `_rise_gate_tick`, two-phase-freeze,
    # curl-pretrain) targeted "reach the target height/curl
    # faster/gentler"; none separately priced "don't draw current AT
    # ALL until tucked" -- the specific sequencing fact the
    # diagnostic isolated. This term does exactly that, using the
    # SAME state-conditioned progress signal `_rise_gate_tick`
    # already reads (`_curl_dist()`, live FK-measured feet-to-plant-
    # footprint distance -- NOT a scripted clock, NOT a motion
    # prior): while curl_dist has not yet reached the bridge-pose
    # threshold, any per-servo current above a TIGHT bar is charged
    # quadratically (same over-threshold-squared shape as
    # `k_current_hot` above, just a separate coefficient/threshold
    # so the two can be tuned independently); once tucked, this term
    # goes silent for the rest of the episode (a one-way latch, like
    # the curl gate's own "unlock permanently" rule) so the
    # legitimate press afterward is untaxed by it -- only the
    # existing (looser) k_current_hot/current_hot_a price, if any,
    # still applies during the press. Crouch starts are exempt
    # (curl_dist already ~0, nothing to gate, matches
    # `_rise_gate_tick`'s own exemption). Bit-exact OFF by default
    # (reward.k_current_pretuck=0): no state allocated, no behavior
    # change for any existing checkpoint/lineage. Enable:
    # --cfg-set reward.k_current_pretuck=<k>
    # [--cfg-set reward.current_pretuck_hot_a=<amps>]
    # [--cfg-set reward.current_pretuck_curl_mm=<mm>].
    # Tests: rl_move/tests/test_current_pretuck_reward.py.
    k_pretuck = float(cfg_get(
        env.cfg, "reward", "k_current_pretuck", default=0.0))
    if (k_pretuck > 0.0 and env._is_rise
            and env._state.servo_current is not None
            and getattr(env._goal_traj, "start_at", None)
            != "crouch"):
        if getattr(env, "_pretuck_latched", False):
            tucked = True
        else:
            th_m = float(cfg_get(
                env.cfg, "reward", "current_pretuck_curl_mm",
                default=40.0)) * 0.001
            tucked = env._curl_dist() <= th_m
            if tucked:
                env._pretuck_latched = True
        if not tucked:
            pretuck_a = float(cfg_get(
                env.cfg, "reward", "current_pretuck_hot_a",
                default=0.3))
            over_pt = np.maximum(
                over_current_reading(env._state) - pretuck_a, 0.0)
            r_pretuck = -k_pretuck * float(np.sum(over_pt ** 2))
            parts["reward_current_pretuck"] = r_pretuck
            reward += r_pretuck
    # Current RATE-of-rise penalty (walkcurr rise track, 2026-09-14 --
    # CURRENT_TRUTHS.md's own named next escalation once the 10/10
    # cap-based action-space gates (height ceiling + joint-rate/slew
    # ceiling) closed null: "suppressing the action space ... cannot
    # fix flat-start rise, because the policy's own chosen bad
    # trajectory just replays in slow motion under a tighter cap ...
    # Viable directions stay demonstration-free: a reward term on a
    # property the POLICY'S OWN rollout can self-referentially
    # measure (e.g. bounding the rate-of-current-RISE, not matching
    # a target profile)". Structurally different from every current-
    # pricing lever already closed (`k_current_hot`/
    # `k_current_pretuck`/`k_current_income` all price the *level*
    # of servo_current, or an EMA-scaled level) AND from the closed
    # cap-based gates (which capped the *rate the JOINT ANGLE can
    # move*, so a policy that pushes all six legs' current up
    # together just did it more slowly under a tighter cap -- the
    # cap cannot tell "six legs slowly" from "one leg quickly"
    # apart). This instead prices the *rate the CURRENT ITSELF
    # rises*, tick over tick, directly targeting the confirmed
    # failure mode (`probe_rise_current_envelope.py`'s per-tick
    # trace: a simultaneous six-leg max-current push, not a paced
    # ramp) regardless of how the underlying joint sweep is timed.
    # Self-referential only (this env's own previous-tick current,
    # never a scripted/target profile), so this stays `rl_only`-
    # clean per the same contract `k_current_pretuck` already
    # satisfies. Bit-exact OFF by default (reward.k_current_rate=0):
    # no state allocated, no behavior change for any existing
    # checkpoint/lineage. Enable: --cfg-set reward.k_current_rate=<k>
    # [--cfg-set reward.current_rate_a_per_s=<threshold A/s>].
    # Tests: rl_move/tests/test_current_rate_reward.py.
    k_cur_rate = float(cfg_get(
        env.cfg, "reward", "k_current_rate", default=0.0))
    if (k_cur_rate > 0.0 and env._is_rise
            and env._state.servo_current is not None):
        _cur_now = env._state.servo_current
        _prev_cr = getattr(env, "_prev_current_rate", None)
        if _prev_cr is None or _prev_cr.shape != _cur_now.shape:
            _prev_cr = _cur_now.copy()
        _rate = (_cur_now - _prev_cr) / max(env.dt, 1e-6)
        env._prev_current_rate = _cur_now.copy()
        rate_a_per_s = float(cfg_get(
            env.cfg, "reward", "current_rate_a_per_s",
            default=3.0))
        over_rate = np.maximum(_rate - rate_a_per_s, 0.0)
        r_cur_rate = -k_cur_rate * float(np.sum(over_rate ** 2))
        parts["reward_current_rate"] = r_cur_rate
        reward += r_cur_rate
    # Current-streak (hard-reset consecutive-tick) debt (walkcurr
    # track, 2026-10-05 -- the lower-role L2+L5 terminal-support
    # forensics, `lowerrole_terminal_support_forensics_2026-10-02`:
    # the converged 2-leg stance's per-leg force/current magnitudes
    # are IDENTICAL in passing vs over_current-failing episodes, and
    # the trip itself (`SafetyLayer._over_current_ticks`) is a
    # CONSECUTIVE-tick counter that hard-resets to 0 on any tick the
    # max per-joint current drops back at/under the rail -- so a
    # policy that periodically relieves the loaded leg(s) for even a
    # single tick never trips, with NO change to its average current
    # or support-leg identity. Every reward lever tried against this
    # habit before this one priced MAGNITUDE (`k_current_hot`,
    # instantaneous) or a smoothly-decaying EMA (`k_torque_headroom`,
    # `k_load_rotate`) or load DISTRIBUTION across legs (`k_load_even`,
    # `k_stance_count`) -- all closed. None of those are the same
    # mathematical object as this: an EMA barely moves on a single
    # relief tick in EITHER direction (the same "a brief spike barely
    # moves it" symmetry also means "a brief relief barely un-moves
    # it"), so it cannot differentially reward the exact
    # break-the-streak strategy that actually avoids the real trip;
    # concentration/count terms fight the policy's only discovered
    # stable support config instead of letting it keep that config and
    # just interrupt the streak. This term instead mirrors the
    # SAFETY LAYER'S OWN counter exactly (`current_streak_ticks_step`,
    # same hard-reset-on-dip semantics as `SafetyLayer.
    # _over_current_ticks`) and prices its fraction of the real trip
    # duration with a steep power, so cost stays ~0 until the streak
    # is a large fraction of the trip window and then rises sharply --
    # directly rewarding "interrupt the streak before it trips"
    # without taxing ordinary sustained-but-broken current use
    # anywhere else. Bit-exact OFF by default (reward.k_current_streak
    # =0): no state allocated, no behavior change for any existing
    # checkpoint/lineage. Enable: --cfg-set reward.k_current_streak=<k>
    # [--cfg-set reward.current_streak_a=<amps, default 2.5 = safety.
    # max_current_a>] [--cfg-set reward.current_streak_trip_s=<s,
    # default 2.0 = safety.over_current_trip_s>]
    # [--cfg-set reward.current_streak_power=<p, default 4.0>].
    # Tests: rl_move/tests/test_current_streak_reward.py.
    k_streak = float(cfg_get(
        env.cfg, "reward", "k_current_streak", default=0.0))
    if k_streak > 0.0 and env._state.servo_current is not None:
        streak_a = float(cfg_get(
            env.cfg, "reward", "current_streak_a", default=2.5))
        trip_s = float(cfg_get(
            env.cfg, "reward", "current_streak_trip_s", default=2.0))
        power = float(cfg_get(
            env.cfg, "reward", "current_streak_power", default=4.0))
        trip_ticks = max(1, int(round(trip_s / max(env.dt, 1e-9))))
        prev_ticks = int(getattr(env, "_current_streak_ticks", 0))
        env._current_streak_ticks = current_streak_ticks_step(
            prev_ticks, over_current_reading(env._state), streak_a)
        frac = min(float(env._current_streak_ticks) / trip_ticks, 1.0)
        r_streak = -k_streak * (frac ** power)
        parts["reward_current_streak"] = r_streak
        parts["current_streak_frac"] = frac
        reward += r_streak
    return reward
