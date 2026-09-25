"""reward.k_hold_duty_deficit (2026-09-25, standwalk STATUS ~03:2x
follow-up to the CLOSED reward.k_hold_churn FAIL-MECHANISM canary):
prices a per-foot EMA duty-cycle DEFICIT continuously during `hold`,
rather than the discrete per-liftoff-event count the closed lever
tried. Contract under test (pure function, no mujoco needed --
SimpleNamespace fakes, mirrors the codebase's own convention for
reward-function unit tests):
  - default off (k=0) is a true no-op: no parts key, no state write;
  - a foot unloaded on the FIRST tick of a segment IS priced (unlike
    the closed churn lever, which needed a prior tick to detect a
    flip and so was blind on tick 1 -- this term is state-based, not
    diff-based, and the EMA is freshly (re-)seeded at 1.0 every
    segment entry, so tick 1 is never blind);
  - the EMA moves toward the instantaneous loaded state by the
    expected dt/tau step each tick;
  - multiple simultaneously-unloaded feet scale the deficit
    proportionally (mean over 6, not summed);
  - a RELOAD (unloaded -> loaded) is priced LESS over time as the EMA
    recovers -- the deliberate mirror of the closed churn lever, which
    never priced reloads at all;
  - non-hold modes never charge, regardless of contact state;
  - a second hold segment inside one composed episode does not
    inherit the first segment's end-of-segment EMA (fresh reseed to
    1.0, not carried state).
"""
from __future__ import annotations

from types import SimpleNamespace

from rl_move.sim.balance_reward_hold import hold_duty_deficit_reward


def _env(step_i=1, seg_entry_step=0, mode="hold", loaded=(True,) * 6,
         cfg_over=None, ema=None, dt=0.02, tau=1.0):
    cfg = {"reward": {"k_hold_duty_deficit": 5.0,
                       "hold_duty_deficit_tau_s": tau}}
    if cfg_over:
        cfg["reward"].update(cfg_over)
    import numpy as np
    sensordata = np.array([1.0 if v else 0.0 for v in loaded])
    return SimpleNamespace(
        cfg=cfg,
        _goal_traj=SimpleNamespace(mode=mode),
        _pad_z_ref=np.zeros(6),
        _touch_adr=list(range(6)),
        data=SimpleNamespace(sensordata=sensordata),
        _step_i=step_i,
        _seg_entry_step=seg_entry_step,
        _hold_duty_ema=ema,
        dt=dt,
    )


def test_default_off_is_true_noop():
    e = _env(cfg_over={"k_hold_duty_deficit": 0.0}, ema=[1.0] * 6,
              loaded=(False,) * 6)
    parts = {}
    r = hold_duty_deficit_reward(e, object(), parts, 10.0)
    assert r == 10.0
    assert parts == {}
    # state untouched: an inert lever must not even overwrite bookkeeping
    assert e._hold_duty_ema == [1.0] * 6


def test_first_segment_tick_is_priced_unlike_churn():
    # since_seg == 0: fresh reseed to 1.0 THEN updated by this tick's
    # own reading -- deficit is nonzero and charged on tick 1, since
    # this term is state-based (not a diff needing a prior tick).
    e = _env(step_i=3, seg_entry_step=3, loaded=(False,) * 6,
              dt=0.1, tau=1.0)
    parts = {}
    r = hold_duty_deficit_reward(e, object(), parts, 10.0)
    alpha = 0.1 / 1.0
    expected_ema = 1.0 + alpha * (0.0 - 1.0)  # = 1 - alpha = 0.9
    expected_deficit = (1.0 - expected_ema)  # same for all 6 feet
    assert e._hold_duty_ema == [expected_ema] * 6
    assert abs(r - (10.0 - 5.0 * expected_deficit * 0.1)) < 1e-9
    assert parts["hold_duty_deficit_pen"] < 0.0
    assert abs(parts["hold_duty_ema_mean"] - expected_ema) < 1e-9


def test_ema_step_matches_dt_over_tau():
    e = _env(step_i=10, seg_entry_step=3, ema=[0.5] * 6,
              loaded=(True,) * 6, dt=0.25, tau=1.0)
    parts = {}
    hold_duty_deficit_reward(e, object(), parts, 0.0)
    alpha = 0.25
    expected = 0.5 + alpha * (1.0 - 0.5)
    assert abs(e._hold_duty_ema[0] - expected) < 1e-9


def test_multiple_unloaded_feet_scale_deficit_by_mean_not_sum():
    e = _env(step_i=10, seg_entry_step=3, ema=[1.0] * 6,
              loaded=(False, False, False, True, True, True),
              dt=0.1, tau=1.0)
    parts_half = {}
    hold_duty_deficit_reward(e, object(), parts_half, 0.0)

    e2 = _env(step_i=10, seg_entry_step=3, ema=[1.0] * 6,
               loaded=(False,) * 6, dt=0.1, tau=1.0)
    parts_all = {}
    hold_duty_deficit_reward(e2, object(), parts_all, 0.0)
    # half the feet unloaded -> half the penalty of all feet unloaded
    assert abs(parts_half["hold_duty_deficit_pen"] * 2
               - parts_all["hold_duty_deficit_pen"]) < 1e-9


def test_reload_recovers_and_is_priced_less_over_time():
    # Foot has been down (ema already recovering toward 1) for a
    # while; unlike churn (which never prices a reload at all), this
    # continuous term keeps charging a SMALLER amount as duty heals.
    e_early = _env(step_i=10, seg_entry_step=3, ema=[0.2] * 6,
                    loaded=(True,) * 6, dt=0.1, tau=1.0)
    parts_early = {}
    hold_duty_deficit_reward(e_early, object(), parts_early, 0.0)

    e_later = _env(step_i=10, seg_entry_step=3, ema=[0.8] * 6,
                    loaded=(True,) * 6, dt=0.1, tau=1.0)
    parts_later = {}
    hold_duty_deficit_reward(e_later, object(), parts_later, 0.0)
    assert (abs(parts_later["hold_duty_deficit_pen"])
            < abs(parts_early["hold_duty_deficit_pen"]))


def test_non_hold_mode_never_charges():
    for mode in ("walk", "track", "lower", "rise"):
        e = _env(step_i=5, seg_entry_step=3, mode=mode,
                  ema=[1.0] * 6, loaded=(False,) * 6)
        parts = {}
        r = hold_duty_deficit_reward(e, object(), parts, 10.0)
        assert r == 10.0, mode
        assert parts == {}, mode


def test_second_hold_segment_does_not_inherit_prior_segment_ema():
    # Composed episode: a first hold segment ended with feet depressed
    # (ema low from fidgeting), then an intervening segment ran, then
    # hold resumes -- the segment-boundary marker must force a fresh
    # 1.0 reseed rather than comparing against the stale low EMA.
    e = _env(step_i=40, seg_entry_step=40, mode="hold",
              ema=[0.1] * 6, loaded=(True,) * 6, dt=0.1, tau=1.0)
    parts = {}
    hold_duty_deficit_reward(e, object(), parts, 0.0)
    # reseeded to 1.0 then updated toward loaded=1.0 -> stays 1.0,
    # NOT continuing to climb from the stale 0.1 (which would still be
    # well below 1.0 after one 0.1/1.0 alpha step: 0.1+0.1*(1-0.1)=0.19)
    assert e._hold_duty_ema == [1.0] * 6
    assert "hold_duty_deficit_pen" not in parts
