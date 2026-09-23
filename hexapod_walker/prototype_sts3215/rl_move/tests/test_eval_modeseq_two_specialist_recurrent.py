"""TwoSpecialistDriver -- the eval_modeseq.py two-specialist baseline's
recurrent-hidden-state mechanics (RESEARCH_RULES "Tests": fast,
mechanics-only, no rollout-ranking).

Root cause this exists: the two-specialist path used to call a bare
`PPO.load(...).predict(obs, deterministic=det)` on `--stand`/`--walk`
every tick. `PPO.load` happens to deserialize a GRU
(RecurrentPPO/GruActorCriticPolicy) checkpoint zip without raising, but
calling `.predict(obs, deterministic=det)` with no `state`/
`episode_start` silently re-zeroes the GRU's hidden state on EVERY
tick -- a recurrent policy driven this way is stateless, not the
composed baseline the tool exists to measure. Found while baselining
the tool against the standwalk track's dr=0.7 GRU stand champion and
dr=1.0 GRU walk champion for the first time (2026-09-23).

These tests use fake policy doubles (no checkpoints, no MuJoCo) that
record every state/episode_start they were called with, so they run in
well under a second.
"""
from __future__ import annotations

import numpy as np

from rl_move.sim.eval_modeseq import TwoSpecialistDriver


class _FakeRecurrentModel:
    """Mimics a loaded RecurrentPPO: `.policy.predict(obs, state=,
    episode_start=, deterministic=)` -> (action, new_state)."""

    def __init__(self):
        self.calls: list[dict] = []
        self.policy = self

    def predict(self, obs, state=None, episode_start=None,
                deterministic=True):
        self.calls.append({
            "state_was_none": state is None,
            "episode_start": bool(np.asarray(episode_start)[0]),
        })
        # "new" state distinguishable from the initial None/zero state.
        new_state = np.full((1,), len(self.calls), dtype=np.float32)
        return np.zeros(2, dtype=np.float32), new_state


class _FakeNonRecurrentModel:
    """Mimics a loaded PPO: `.predict(obs, deterministic=)` -> (action,
    state=None)."""

    def __init__(self):
        self.calls = 0

    def predict(self, obs, deterministic=True):
        self.calls += 1
        return np.zeros(2, dtype=np.float32), None


def test_recurrent_state_persists_across_mode_switches():
    """Alternating rise(stand)->walk->lower(stand) within ONE episode
    must NOT reset either policy's hidden state -- only episode_begin()
    does that. This is the exact bug: the old code passed state=None
    every call, which forces episode_start semantics on every tick."""
    stand, walk = _FakeRecurrentModel(), _FakeRecurrentModel()
    driver = TwoSpecialistDriver(stand, walk, n_stand=3, det=True,
                                  stand_rec=True, walk_rec=True)
    driver.episode_begin()
    obs = np.zeros(5, dtype=np.float32)

    driver.act(obs, "rise")   # tick 1: stand, true episode start
    driver.act(obs, "walk")   # tick 2: walk, first-ever call
    driver.act(obs, "rise")   # tick 3: stand again, SAME episode
    driver.act(obs, "walk")   # tick 4: walk again, SAME episode

    # Each policy's own 2nd call must carry its own 1st call's state
    # forward (state_was_none False) and episode_start False.
    assert stand.calls[0]["state_was_none"] is True
    assert stand.calls[0]["episode_start"] is True
    assert stand.calls[1]["state_was_none"] is False
    assert stand.calls[1]["episode_start"] is False

    assert walk.calls[0]["state_was_none"] is True
    # walk's first call is tick 2, i.e. NOT the true episode start.
    assert walk.calls[0]["episode_start"] is False
    assert walk.calls[1]["state_was_none"] is False
    assert walk.calls[1]["episode_start"] is False


def test_episode_begin_resets_both_states():
    stand, walk = _FakeRecurrentModel(), _FakeRecurrentModel()
    driver = TwoSpecialistDriver(stand, walk, n_stand=3, det=True,
                                  stand_rec=True, walk_rec=True)
    obs = np.zeros(5, dtype=np.float32)
    driver.episode_begin()
    driver.act(obs, "rise")
    driver.act(obs, "walk")

    driver.episode_begin()
    driver.act(obs, "rise")
    driver.act(obs, "walk")

    # 2nd episode's first calls must look like fresh starts again --
    # what actually matters for correctness is state_was_none (a fresh
    # hidden state); episode_start is only ever True for the very first
    # act() call of an episode (here, "rise"), which is the one that
    # matters since state is never None at that point otherwise.
    assert stand.calls[1]["state_was_none"] is True
    assert stand.calls[1]["episode_start"] is True
    assert walk.calls[1]["state_was_none"] is True


def test_non_recurrent_models_never_see_state_kwargs():
    """Non-recurrent (MLP) checkpoints must still take the plain
    `.predict(obs, deterministic=)` path -- bit-exact legacy call
    surface, no state/episode_start plumbing at all."""
    stand, walk = _FakeNonRecurrentModel(), _FakeNonRecurrentModel()
    driver = TwoSpecialistDriver(stand, walk, n_stand=3, det=True,
                                  stand_rec=False, walk_rec=False)
    obs = np.zeros(5, dtype=np.float32)
    driver.episode_begin()
    driver.act(obs, "rise")
    driver.act(obs, "walk")
    driver.act(obs, "lower")
    assert stand.calls == 2  # "rise" + "lower"
    assert walk.calls == 1


def test_stand_obs_sliced_walk_obs_full():
    """`stand` gets the obs PREFIX (`n_stand` wide), `walk` gets the
    full env obs -- unchanged two-specialist obs-width contract."""
    seen = {}

    class _Rec(_FakeRecurrentModel):
        def predict(self, obs, state=None, episode_start=None,
                     deterministic=True):
            seen["obs_len"] = len(obs)
            return super().predict(obs, state, episode_start,
                                    deterministic)

    stand, walk = _Rec(), _Rec()
    driver = TwoSpecialistDriver(stand, walk, n_stand=3, det=True,
                                  stand_rec=True, walk_rec=True)
    driver.episode_begin()
    obs = np.arange(5, dtype=np.float32)
    driver.act(obs, "rise")
    assert seen["obs_len"] == 3
    driver.act(obs, "walk")
    assert seen["obs_len"] == 5
