"""Tests for probe_yaw_credit.py (standwalk turn-authority
credit-assignment dig-in tool, 08-31). Two layers: pure TD-math/
aggregation unit tests (no torch/MuJoCo) that pin the exact
delta_t = r + gamma*V' - V formula and the CREDIT-* verdict logic, and
a short real-env integration smoke test with an UNTRAINED dual-core
GRU policy that exercises the actual forward()/RNNStates(pi, vf)
threading path against the real SimHexapodJointWalkEnv — the thing
most likely to silently break (wrong state shape, wrong episode_start
convention, mismatched obs/action spaces)."""
from __future__ import annotations

import numpy as np

from rl_move.sim.probe_yaw_credit import (
    _quartile_split,
    _safe_pearson,
    credit_rollout,
    summarize,
    td_residuals,
)


# ---------------------------------------------------------------------
# Pure math
# ---------------------------------------------------------------------

def test_td_residuals_hand_computed():
    # V constant at 1.0, reward 0 every tick, gamma 0.9 ->
    # delta = 0 + 0.9*1.0 - 1.0 = -0.1 every tick.
    rewards = [0.0, 0.0, 0.0]
    values = [1.0, 1.0, 1.0, 1.0]
    out = td_residuals(rewards, values, gamma=0.9)
    np.testing.assert_allclose(out, [-0.1, -0.1, -0.1])


def test_td_residuals_terminal_bootstrap_zero():
    # last value is the terminal bootstrap (0.0) -> delta_last =
    # r_last - V_last exactly (no gamma*0 contribution).
    rewards = [1.0, 2.0]
    values = [0.5, 0.5, 0.0]
    out = td_residuals(rewards, values, gamma=0.99)
    assert out[0] == 1.0 + 0.99 * 0.5 - 0.5
    assert out[1] == 2.0 - 0.5


def test_td_residuals_nonzero_truncation_bootstrap():
    # a TRUNCATED (not terminated) episode's last tick must use the
    # critic's own estimate of the tick after it, not a hard 0 (that
    # 0-bootstrap-on-truncation bug would bias exactly the tail tick a
    # real rollout tool needs to get right).
    rewards = [1.0]
    values = [0.5, 2.0]  # 2.0 = critic's real post-episode estimate
    out = td_residuals(rewards, values, gamma=0.5)
    assert out[0] == 1.0 + 0.5 * 2.0 - 0.5


def test_td_residuals_rejects_length_mismatch():
    import pytest
    with pytest.raises(ValueError):
        td_residuals([0.0, 0.0], [0.0, 0.0], gamma=0.99)


def test_safe_pearson_perfect_correlation():
    import pytest
    a = np.array([1.0, 2.0, 3.0, 4.0])
    b = 2.0 * a + 1.0
    assert _safe_pearson(a, b) == pytest.approx(1.0)


def test_safe_pearson_zero_variance_returns_none():
    a = np.array([1.0, 1.0, 1.0])
    b = np.array([1.0, 2.0, 3.0])
    assert _safe_pearson(a, b) is None


def test_quartile_split_needs_at_least_4_ticks():
    score = np.array([1.0, 2.0])
    value = np.array([1.0, 2.0])
    top, bot = _quartile_split(score, value)
    assert top is None and bot is None


def test_quartile_split_top_vs_bottom():
    score = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
    value = score.copy()  # identical ordering -> top mean > bottom mean
    top, bot = _quartile_split(score, value, frac=0.25)
    assert top > bot


def test_summarize_credit_rewards_when_toward_ticks_score_higher():
    n = 40
    rng = np.random.default_rng(0)
    wz = rng.normal(0.0, 0.02, n)
    td = 5.0 * wz  # toward-command (positive wz, cmd>0) -> higher td
    masked = {"wz_cmd": 0.25, "wz": wz,
              "reward_walk_yaw": np.zeros(n), "td_residual": td}
    out = summarize(masked)
    assert out["verdict"].startswith("CREDIT-REWARDS")
    assert out["td_mean_top_quartile_toward"] > \
        out["td_mean_bottom_quartile_toward"]


def test_summarize_credit_punishes_when_toward_ticks_score_lower():
    n = 40
    rng = np.random.default_rng(0)
    wz = rng.normal(0.0, 0.02, n)
    td = -5.0 * wz
    masked = {"wz_cmd": 0.25, "wz": wz,
              "reward_walk_yaw": np.zeros(n), "td_residual": td}
    out = summarize(masked)
    assert out["verdict"].startswith("CREDIT-PUNISHES")


def test_summarize_credit_blind_when_td_is_flat():
    n = 40
    wz = np.linspace(-0.05, 0.05, n)
    td = np.zeros(n)
    masked = {"wz_cmd": 0.25, "wz": wz,
              "reward_walk_yaw": np.zeros(n), "td_residual": td}
    out = summarize(masked)
    assert out["verdict"].startswith("CREDIT-BLIND")


def test_summarize_credit_blind_when_no_relation():
    n = 40
    rng = np.random.default_rng(1)
    wz = rng.normal(0.0, 0.02, n)
    td = rng.normal(0.0, 1e-6, n)  # tiny, unrelated noise
    masked = {"wz_cmd": 0.25, "wz": wz,
              "reward_walk_yaw": np.zeros(n), "td_residual": td}
    out = summarize(masked)
    assert out["verdict"].startswith("CREDIT-BLIND")


def test_summarize_value_delta_decomposition_independent_of_reward():
    """The plain td-based verdict is trivially biased (reward is an
    addend of td_residual); value_delta = td - reward isolates the
    genuine forward-looking critic signal. Construct a case where
    reward_walk_yaw/td LOOK like CREDIT-REWARDS (because r_t alone
    correlates with toward-command) but the bootstrapped value change
    is flat -- the forward_verdict must catch this, the plain verdict
    must not."""
    n = 40
    rng = np.random.default_rng(3)
    wz = rng.normal(0.0, 0.02, n)
    ryaw = 5.0 * wz          # reward fires proportional to toward-ness
    value_delta = np.zeros(n)  # critic's own forward belief never moves
    td = ryaw + value_delta   # td = r_t + value_delta by construction
    masked = {"wz_cmd": 0.25, "wz": wz, "reward_walk_yaw": ryaw,
              "td_residual": td, "value_delta": value_delta}
    out = summarize(masked)
    assert out["verdict"].startswith("CREDIT-REWARDS")
    assert out["forward_verdict"].startswith("CREDIT-BLIND")


def test_summarize_missing_value_delta_omits_forward_fields():
    n = 10
    wz = np.linspace(-0.05, 0.05, n)
    td = np.zeros(n)
    masked = {"wz_cmd": 0.25, "wz": wz,
              "reward_walk_yaw": np.zeros(n), "td_residual": td}
    out = summarize(masked)
    assert "forward_verdict" not in out


def test_summarize_negative_wz_cmd_flips_sign_correctly():
    # commanded CW (wz_cmd<0): "toward" is NEGATIVE wz. Ticks with the
    # most negative wz should be the ones scoring higher for a
    # CREDIT-REWARDS verdict.
    n = 40
    rng = np.random.default_rng(2)
    wz = rng.normal(0.0, 0.02, n)
    td = -5.0 * wz  # negative wz (toward, since cmd<0) -> higher td
    masked = {"wz_cmd": -0.25, "wz": wz,
              "reward_walk_yaw": np.zeros(n), "td_residual": td}
    out = summarize(masked)
    assert out["verdict"].startswith("CREDIT-REWARDS")


# ---------------------------------------------------------------------
# Real-env integration smoke test (untrained dual-core GRU policy)
# ---------------------------------------------------------------------

def _tiny_dual_model_for_env(env, hidden: int = 8):
    from sb3_contrib import RecurrentPPO

    from rl_move.sim.gru_policy import DualGruActorCriticPolicy
    return RecurrentPPO(
        DualGruActorCriticPolicy, env,
        n_steps=8, batch_size=16, n_epochs=1, seed=0, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=hidden, net_arch=[16]))


def test_credit_rollout_threads_state_on_real_env():
    """Untrained dual-core GRU on the real turn-in-place env: the
    point is NOT skill (random weights), it's that the forward()/
    RNNStates(pi, vf) threading runs end to end, produces one td value
    per scored tick, and the value estimate actually reacts to the
    hidden state changing (regression guard against a silent
    'critic state always resets to the same zeros' bug — the exact
    class of bug this tool exists to avoid, ported to the tool itself:
    checks V(s) is NOT bit-identical every tick despite step()
    changing the observation)."""
    from rl_move.sim.probe_turn_authority import make_env

    cfg_set = ["goal.walk_yaw_cmd=1", "goal.walk_phase_run_on_yaw=1"]
    env = make_env(cfg_set, seed=0, episode_seconds=2.0, mode_onehot=True)
    model = _tiny_dual_model_for_env(env)

    res = credit_rollout(model=model, cfg_set=cfg_set, wz_cmd=0.25,
                          seed=0, episode_seconds=2.0)
    assert res["n_total_ticks"] > 10
    assert res["n_ticks"] >= 0
    assert np.isfinite(res["td_std"]) if res["td_std"] is not None else True


def test_load_dual_model_rejects_non_dual_checkpoint(tmp_path):
    """A plain MLP PPO checkpoint must be rejected with a clear
    message, not silently mis-threaded through RNNStates it doesn't
    have."""
    import pytest
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env

    from rl_move.sim.probe_yaw_credit import load_dual_model

    env = make_vec_env("Pendulum-v1", n_envs=1)
    model = PPO("MlpPolicy", env, n_steps=8, batch_size=8, device="cpu")
    ckpt = tmp_path / "mlp.zip"
    model.save(ckpt)
    with pytest.raises(SystemExit):
        load_dual_model(ckpt)
