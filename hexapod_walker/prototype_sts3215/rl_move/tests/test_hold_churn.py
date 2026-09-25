"""reward.k_hold_churn (2026-09-25, standwalk STATUS ~02:1x follow-up):
prices the exact event eval_modeseq.py's swing_count metric counts (a
previously-loaded foot going airborne) directly and densely during the
`hold` mode, since the `hold_start_bank` canary showed the composed-
session hold-fall gap is NOT an entry-state problem -- the same
leg-fidget signature persists at the identical magnitude regardless of
starting pose/momentum. Contract under test (pure function, no mujoco
needed -- SimpleNamespace fakes, mirrors the codebase's own
SimpleNamespace-fake convention for reward-function unit tests):
  - default off (k=0) is a true no-op: no parts key, no state write;
  - a liftoff (loaded->unloaded) on a real hold tick is priced;
  - a reload (unloaded->loaded) is NOT priced -- only the swing_count
    direction counts;
  - the very first tick of a segment never charges (no prior state to
    compare against), including the boundary of a SECOND hold segment
    inside one composed episode (prior segment's foot state must never
    masquerade as a hold-phase fidget);
  - non-hold modes (walk/track) never charge, regardless of contact
    changes.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from rl_move.sim.balance_reward_hold import hold_churn_reward


def _env(step_i=1, seg_entry_step=0, mode="hold", loaded=(True,) * 6,
         cfg_over=None, prev_on=None):
    cfg = {"reward": {"k_hold_churn": 5.0}}
    if cfg_over:
        cfg["reward"].update(cfg_over)
    sensordata = np.array([1.0 if v else 0.0 for v in loaded])
    return SimpleNamespace(
        cfg=cfg,
        _goal_traj=SimpleNamespace(mode=mode),
        _pad_z_ref=np.zeros(6),
        _touch_adr=list(range(6)),
        data=SimpleNamespace(sensordata=sensordata),
        _step_i=step_i,
        _seg_entry_step=seg_entry_step,
        _hold_churn_prev_on=prev_on,
    )


def test_default_off_is_true_noop():
    e = _env(cfg_over={"k_hold_churn": 0.0}, prev_on=[True] * 6,
              loaded=(False,) * 6)
    parts = {}
    r = hold_churn_reward(e, object(), parts, 10.0)
    assert r == 10.0
    assert parts == {}
    # state untouched: an inert lever must not even overwrite bookkeeping
    assert e._hold_churn_prev_on == [True] * 6


def test_first_segment_tick_never_charges():
    # since_seg == 0 (step_i == seg_entry_step): no prior tick to
    # compare against, even though prev_on (leftover from init) claims
    # every foot was loaded and this tick sees every foot unloaded.
    e = _env(step_i=3, seg_entry_step=3, prev_on=[True] * 6,
              loaded=(False,) * 6)
    parts = {}
    r = hold_churn_reward(e, object(), parts, 10.0)
    assert r == 10.0
    assert "hold_churn_pen" not in parts
    # bookkeeping now warmed for the NEXT tick's comparison
    assert e._hold_churn_prev_on == [False] * 6


def test_single_liftoff_is_priced_by_k():
    e = _env(step_i=5, seg_entry_step=3, prev_on=[True] * 6,
              loaded=(False, True, True, True, True, True))
    parts = {}
    r = hold_churn_reward(e, object(), parts, 10.0)
    assert r == 10.0 - 5.0
    assert parts["hold_churn_pen"] == -5.0
    assert parts["hold_churn_flips"] == 1


def test_multiple_simultaneous_liftoffs_scale_linearly():
    e = _env(step_i=5, seg_entry_step=3, prev_on=[True] * 6,
              loaded=(False, False, False, True, True, True))
    parts = {}
    r = hold_churn_reward(e, object(), parts, 10.0)
    assert r == 10.0 - 15.0
    assert parts["hold_churn_flips"] == 3


def test_reload_is_not_priced():
    # unloaded -> loaded is the OPPOSITE of swing_count's own
    # definition (diff == -1, a contact->no-contact transition); a
    # foot re-planting must never be charged as churn.
    e = _env(step_i=5, seg_entry_step=3, prev_on=[False] * 6,
              loaded=(True,) * 6)
    parts = {}
    r = hold_churn_reward(e, object(), parts, 10.0)
    assert r == 10.0
    assert "hold_churn_pen" not in parts


def test_non_hold_mode_never_charges():
    for mode in ("walk", "track", "lower", "rise"):
        e = _env(step_i=5, seg_entry_step=3, mode=mode,
                  prev_on=[True] * 6, loaded=(False,) * 6)
        parts = {}
        r = hold_churn_reward(e, object(), parts, 10.0)
        assert r == 10.0, mode
        assert "hold_churn_pen" not in parts, mode


def test_second_hold_segment_does_not_inherit_prior_segment_state():
    # Composed episode: a first hold segment ended with a foot
    # unloaded (prev_on has a False), then an intervening non-hold
    # segment ran, then hold resumes -- the segment-boundary marker
    # (_step_i == _seg_entry_step) must force a fresh baseline rather
    # than comparing against the stale end-of-prior-hold-segment state.
    e = _env(step_i=40, seg_entry_step=40, mode="hold",
              prev_on=[False, True, True, True, True, True],
              loaded=(True, True, True, True, True, True))
    parts = {}
    r = hold_churn_reward(e, object(), parts, 10.0)
    assert r == 10.0
    assert "hold_churn_pen" not in parts
