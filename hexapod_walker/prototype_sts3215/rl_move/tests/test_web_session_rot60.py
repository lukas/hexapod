"""``SimWebSession._maybe_rot60_wrap`` -- the interactive web session's
own opt-in rot60 canonicalization wrapper (2026-09-14, closes
DESIGN_NOTE_2026-09-13_rot60_fullgait_stance.md's "np-JSON export/
runtime wrapper parity" follow-up: Canary A proved the mechanism
offline via ``eval_checkpoint.py --rot60``, but the interactive
joystick sim demo -- the actual RL_GOALS sim-demo requirement -- never
wired it in).

Fast/mechanics-only (RESEARCH_RULES "Tests"): no MuJoCo/PPO boot, no
rollout, a bare ``SimWebSession.__new__`` + a duck-typed stand-in
model, same pattern as ``test_sim_web_server.py``'s
``_bare_session_for_vel_contract``.
"""
from __future__ import annotations

import numpy as np
import pytest

from rl_move.sim import rot60
from rl_move.sim.web_session import SimWebConfig, SimWebSession


class _Space:
    def __init__(self, n: int):
        self.shape = (n,)


class _StubWalkModel:
    """Bare stand-in for a loaded plain-frame (width-72) walk policy --
    only the attributes ``_maybe_rot60_wrap``/its callers touch."""

    def __init__(self, obs_dim: int = 72):
        self.observation_space = _Space(obs_dim)
        self.action_space = _Space(18)
        self.meta = {"activation": "tanh"}
        self.hidden = [64, 64]

    def predict(self, obs, deterministic: bool = True, **kw):
        return np.arange(18, dtype=np.float64), None


def _bare_session(*, rot60_walk: bool, walk_kind: str = "plain",
                  tilt_scale: float = 0.2) -> SimWebSession:
    session = SimWebSession.__new__(SimWebSession)
    session.cfg = SimWebConfig(
        policy_dir=None, stance=None, walk=None, recover=None,
        log_dir=None, rot60_walk=rot60_walk)
    session.walk_kind = walk_kind

    class _StubEnv:
        pass

    session.env = _StubEnv()
    session.env.cfg = {"obs": {"tilt_scale": tilt_scale}}
    return session


def test_default_off_is_bit_exact_noop():
    """``rot60_walk=False`` (the dataclass default) must return the
    exact same object, untouched -- every pre-2026-09-14 session."""
    session = _bare_session(rot60_walk=False)
    model = _StubWalkModel()
    out = session._maybe_rot60_wrap(model, 72, "some_champion")
    assert out is model


def test_none_model_passes_through_even_when_flag_is_on():
    session = _bare_session(rot60_walk=True)
    assert session._maybe_rot60_wrap(None, 72, "scripted") is None


def test_flag_on_wraps_a_plain_72obs_model_in_rot60_policy():
    session = _bare_session(rot60_walk=True)
    model = _StubWalkModel(obs_dim=72)
    out = session._maybe_rot60_wrap(model, 72, "bundle_rlonly_v2")
    assert isinstance(out, rot60.Rot60Policy)
    assert out.model is model
    assert out.tilt_scale == pytest.approx(0.2)


def test_wrapped_model_proxies_missing_attributes_to_the_inner_model():
    """``Rot60Policy.__getattr__`` passthrough: the web session's own
    model-info endpoint (``_model_info``) reads ``observation_space``/
    ``action_space``/``meta``/``hidden`` straight off whatever
    ``self.walk`` is -- must keep working once wrapped."""
    session = _bare_session(rot60_walk=True)
    model = _StubWalkModel(obs_dim=72)
    out = session._maybe_rot60_wrap(model, 72, "bundle_rlonly_v2")
    assert out.observation_space.shape == (72,)
    assert out.action_space.shape == (18,)
    assert out.meta == {"activation": "tanh"}
    assert out.hidden == [64, 64]


def test_custom_tilt_scale_threads_through_from_env_cfg():
    session = _bare_session(rot60_walk=True, tilt_scale=0.35)
    out = session._maybe_rot60_wrap(_StubWalkModel(), 72, "x")
    assert out.tilt_scale == pytest.approx(0.35)


@pytest.mark.parametrize("walk_kind,n_walk", [
    ("gru", 78), ("hist", 1152), ("plain", 74),
])
def test_flag_on_raises_a_clear_error_for_incompatible_widths(
        walk_kind, n_walk):
    """rot60 only supports the plain FRAME_WALK=72 layout (no phase/
    mode tail, no recurrent hidden state) -- an explicit ask for an
    incompatible checkpoint must fail loudly, not silently no-op or
    (worse) crash deep inside ``rot60.obs_transform``'s own width
    assertion with a confusing traceback."""
    session = _bare_session(rot60_walk=True, walk_kind=walk_kind)
    model = _StubWalkModel(obs_dim=n_walk)
    with pytest.raises(ValueError, match="rot60-walk"):
        session._maybe_rot60_wrap(model, n_walk, "some_checkpoint")


def test_wrapped_model_predict_end_to_end_matches_manual_transform():
    """Full composition sanity: driving the wrapped model through
    ``.predict()`` on an off-axis-command obs vector must equal doing
    the canonicalize -> inner-predict -> de-canonicalize steps by
    hand (the same math ``eval_checkpoint.py --rot60`` already
    exercises against a real SB3 model in ``test_rot60.py``, repeated
    here through the session's own wrapping entry point)."""
    session = _bare_session(rot60_walk=True)
    model = _StubWalkModel()
    wrapped = session._maybe_rot60_wrap(model, 72, "bundle_rlonly_v2")

    rng = np.random.default_rng(0)
    frame = rng.normal(0, 1, 72).astype(np.float32)
    # +120deg command -> sector k=2 (matches test_rot60.py's own case)
    import math
    vx, vy = math.cos(math.radians(120)), math.sin(math.radians(120))
    frame[68:70] = [vx, vy]
    frame[70:72] = [vx, vy]

    act, _ = wrapped.predict(frame)
    k = rot60.sector_from_cmd(vx, vy)
    assert k == 2
    np.testing.assert_array_equal(
        act, np.arange(18)[rot60.leg_perm(-k)])
