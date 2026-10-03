"""Locks rl_move/sim/rot60_lower.py -- the sector-aware `lower`-role
composition wrapper (walkcurr, 2026-10-03 heading-sign forensics ->
scoped fix). Thin pad/truncate shim around the already-tested
rot60.frame_transform/action_from_canonical (see rot60_lower.py's own
module docstring for why the `lower` role's obs/action turned out to
share rot60.FRAME_WALK's exact contract): these tests lock the
pad/truncate bookkeeping and the width contract against the real
checkpoint, not re-derive transform math `test_rot60.py` already
proves.
"""
from __future__ import annotations

import numpy as np
import pytest

from rl_move.sim import rot60, rot60_lower as rl


def _frame68(rng):
    x = rng.normal(0, 0.3, rl.LOWER_FRAME_WIDTH).astype(np.float32)
    x[36:38] = rng.normal(0, 0.1, 2) / 0.2    # measured tilt, scaled
    x[59:61] = rng.normal(0, 0.1, 2) / 0.2    # goal roll/pitch ref
    x[62:68] = 0.0
    x[64] = 1.0                               # one-hot on real leg 2
    return x


def test_matches_frame_transform_on_the_shared_prefix():
    """lower_obs_transform must be IDENTICAL to calling
    rot60.frame_transform on a 72-wide frame whose vref/vmeas tail is
    zero, truncated back to 68 -- i.e. padding/truncating is inert."""
    rng = np.random.default_rng(0)
    x68 = _frame68(rng)
    x72 = np.zeros(rot60.FRAME_WALK, dtype=np.float32)
    x72[:68] = x68
    for k in range(6):
        got = rl.lower_obs_transform(x68, k)
        want = rot60.frame_transform(x72, k)[:68]
        np.testing.assert_array_equal(got, want)


def test_obs_roundtrip_and_identity():
    rng = np.random.default_rng(1)
    x = _frame68(rng)
    assert np.array_equal(rl.lower_obs_transform(x, 0), x)
    for k in range(6):
        y = rl.lower_obs_transform(x, k)
        z = rl.lower_obs_transform(y, (6 - k) % 6)
        np.testing.assert_allclose(z, x, atol=1e-5)


def test_obs_wrong_width_rejected():
    with pytest.raises(ValueError):
        rl.lower_obs_transform(np.zeros(56, dtype=np.float32), 1)
    with pytest.raises(ValueError):
        rl.lower_obs_transform(np.zeros(72, dtype=np.float32), 1)


def test_q_qd_permute_like_rot60():
    rng = np.random.default_rng(2)
    x = _frame68(rng)
    for k in range(6):
        y = rl.lower_obs_transform(x, k)
        jp = rot60.leg_perm(k)
        np.testing.assert_array_equal(y[0:18], x[0:18][jp])
        np.testing.assert_array_equal(y[18:36], x[18:36][jp])


def test_prev_action_permutes_like_walk_frame():
    """prev_action here is 18-wide (per-joint, same as the walk
    frame's own _SL_PREV) -- NOT a 6-wide body-offset vector."""
    rng = np.random.default_rng(3)
    x = _frame68(rng)
    for k in range(6):
        y = rl.lower_obs_transform(x, k)
        jp = rot60.leg_perm(k)
        np.testing.assert_array_equal(y[41:59], x[41:59][jp])


def test_goal_onehot_permutes():
    for m in range(6):
        x = np.zeros(rl.LOWER_FRAME_WIDTH, dtype=np.float32)
        x[62 + m] = 1.0
        for k in range(6):
            y = rl.lower_obs_transform(x, k)
            onehot = y[62:68]
            hot = int(np.argmax(onehot))
            assert onehot[hot] == pytest.approx(1.0)
            assert hot == (m - k) % 6


def test_action_is_rot60_action_from_canonical():
    rng = np.random.default_rng(4)
    act = rng.normal(0, 1, 18)
    for k in range(6):
        np.testing.assert_array_equal(
            rl.lower_action_from_canonical(act, k),
            rot60.action_from_canonical(act, k))


def test_real_checkpoint_obs_width_matches_contract():
    """Pins the width contract against the actual registered
    `lower`-role champion checkpoint -- a future training-cfg change
    that widens its obs (e.g. turning on obs.current_sense) must
    update rot60_lower.py deliberately, not silently mis-slice."""
    policy_path = (
        "rl_move/sim/policies/"
        "ppo_goal_cw_stance50hz_rlonly_lowerrole_scratch_sac_s3_"
        "drramp_holdonly100_acq1.zip")
    import os
    if not os.path.exists(policy_path):
        pytest.skip("champion checkpoint not present in this checkout")
    from rl_move.sim.gru_policy import load_checkpoint_auto
    model = load_checkpoint_auto(policy_path, device="cpu")
    assert int(model.observation_space.shape[0]) == rl.LOWER_FRAME_WIDTH


def test_rot60_lower_policy_k0_is_passthrough():
    """At k=0, Rot60LowerPolicy must be bit-exact vs the raw model."""
    class _Stub:
        def predict(self, obs, deterministic=True):
            del obs, deterministic
            return np.arange(18, dtype=np.float32), None

    rng = np.random.default_rng(5)
    x = _frame68(rng)
    wrapped = rl.Rot60LowerPolicy(_Stub(), 0)
    a_wrapped, _ = wrapped.predict(x)
    np.testing.assert_array_equal(a_wrapped, np.arange(18, dtype=np.float32))


def test_rot60_lower_policy_wraps_obs_and_unwraps_action():
    """At k!=0, the wrapper must feed the model the CANONICAL obs and
    map its action back with `action_from_canonical` -- checked
    against directly-called `lower_obs_transform`/
    `lower_action_from_canonical` (no duplicate logic inside the
    wrapper to drift out of sync)."""
    seen = {}

    class _Stub:
        def predict(self, obs, deterministic=True):
            del deterministic
            seen["obs"] = np.asarray(obs).copy()
            return np.arange(18, dtype=np.float32), None

    rng = np.random.default_rng(6)
    x = _frame68(rng)
    k = 2
    wrapped = rl.Rot60LowerPolicy(_Stub(), k)
    a_wrapped, _ = wrapped.predict(x)
    np.testing.assert_array_equal(seen["obs"], rl.lower_obs_transform(x, k))
    np.testing.assert_array_equal(
        a_wrapped,
        rl.lower_action_from_canonical(np.arange(18, dtype=np.float32), k))
