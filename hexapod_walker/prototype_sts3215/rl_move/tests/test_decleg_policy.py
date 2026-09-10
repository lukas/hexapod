"""Unit tests for the decentralized per-leg actor policy (walkcurr
rung-1, Schilling IROS 2020 lever — operator ruling
fb_20260829T145710).  Fast, CPU-only, no MuJoCo."""
from __future__ import annotations

import math

import numpy as np
import pytest


torch = pytest.importorskip("torch")
gym = pytest.importorskip("gymnasium")

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from rl_move.sim.decleg_policy import (
    ACT_PER_LEG, LEG_MOUNT_ANGLES_DEG, N_LEGS, DecLegActorCriticPolicy,
    heading_rel_cos_sin, joint_walk_leg_slices, leg_mount_unit_vectors,
)
from rl_move.sim.heading_selfdistill import heading_vref_index

OBS_W = 72   # joint_walk env width (59 base + 11 goal + 2 vel feedback)
ACT_W = 18
_VREF_IDX = heading_vref_index(ACT_W)
_HEADING_IDX = (_VREF_IDX, _VREF_IDX + 1)   # (vx_ref, vy_ref) = 68, 69


def _policy(seed: int = 0) -> DecLegActorCriticPolicy:
    torch.manual_seed(seed)
    legs, shared = joint_walk_leg_slices(OBS_W)
    obs_space = gym.spaces.Box(-np.inf, np.inf, shape=(OBS_W,),
                               dtype=np.float32)
    act_space = gym.spaces.Box(-1.0, 1.0, shape=(ACT_W,),
                               dtype=np.float32)
    return DecLegActorCriticPolicy(
        obs_space, act_space, lambda _: 3e-4,
        net_arch=[128, 64, 32], leg_obs_idx=legs, shared_obs_idx=shared,
        leg_hidden=(64, 64))


def test_slices_partition():
    legs, shared = joint_walk_leg_slices(OBS_W)
    assert len(legs) == N_LEGS and all(len(ix) == 9 for ix in legs)
    flat = [j for ix in legs for j in ix]
    assert len(set(flat)) == 54          # disjoint locals
    # every obs dim is either local-to-exactly-one-leg or shared, never both
    assert not (set(flat) & set(shared))
    assert sorted(set(flat) | set(shared)) == list(range(OBS_W))
    # leg 2 owns q 6:9, qd 24:27, prev 47:50
    assert legs[2] == [6, 7, 8, 24, 25, 26, 47, 48, 49]


def test_slices_other_widths():
    for w in (68, 74):
        legs, shared = joint_walk_leg_slices(w)
        assert sorted({j for ix in legs for j in ix} | set(shared)) \
            == list(range(w))
    with pytest.raises(ValueError):
        joint_walk_leg_slices(47)


def test_strict_per_leg_decentralization():
    """Perturbing a leg-local obs dim must change ONLY that leg's
    action mean; a shared dim may change everything."""
    pol = _policy()
    pol.eval()
    legs, shared = joint_walk_leg_slices(OBS_W)
    base = torch.zeros(1, OBS_W)
    with torch.no_grad():
        a0 = pol.action_net(pol.mlp_extractor.forward_actor(base))
    for leg in range(N_LEGS):
        for dim in legs[leg]:
            obs = base.clone()
            obs[0, dim] = 1.7
            with torch.no_grad():
                a = pol.action_net(pol.mlp_extractor.forward_actor(obs))
            delta = (a - a0).abs().numpy().ravel()
            own = delta[leg * ACT_PER_LEG:(leg + 1) * ACT_PER_LEG]
            others = np.delete(delta,
                               range(leg * ACT_PER_LEG,
                                     (leg + 1) * ACT_PER_LEG))
            assert others.max() == 0.0, (
                f"obs dim {dim} (leg {leg} local) leaked into other "
                f"legs' actions: max |delta| {others.max()}")
            assert own.max() > 0.0, (
                f"obs dim {dim} did not reach its own leg {leg}")
    # shared dim reaches every leg (sanity that modules aren't blind)
    obs = base.clone()
    obs[0, shared[0]] = 1.7
    with torch.no_grad():
        a = pol.action_net(pol.mlp_extractor.forward_actor(obs))
    delta = (a - a0).abs().reshape(N_LEGS, ACT_PER_LEG).numpy()
    assert (delta.max(axis=1) > 0.0).all()


def test_critic_is_centralized():
    pol = _policy()
    base = torch.zeros(1, OBS_W)
    obs = base.clone()
    obs[0, 0] = 2.0   # leg-0 local dim
    with torch.no_grad():
        v0 = pol.predict_values(base)
        v1 = pol.predict_values(obs)
    assert (v0 - v1).abs().item() > 0.0


class _DummyJointEnv(gym.Env):
    observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(OBS_W,),
                                       dtype=np.float32)
    action_space = gym.spaces.Box(-1.0, 1.0, shape=(ACT_W,),
                                  dtype=np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        return np.zeros(OBS_W, dtype=np.float32), {}

    def step(self, action):
        return (np.zeros(OBS_W, dtype=np.float32), 0.0, False, False,
                {})


def test_ppo_save_load_roundtrip(tmp_path):
    legs, shared = joint_walk_leg_slices(OBS_W)
    venv = DummyVecEnv([_DummyJointEnv])
    model = PPO(DecLegActorCriticPolicy, venv, n_steps=8, batch_size=8,
                seed=3, device="cpu",
                policy_kwargs=dict(net_arch=[128, 64, 32],
                                   leg_obs_idx=legs,
                                   shared_obs_idx=shared,
                                   leg_hidden=(64, 64)))
    obs = np.random.RandomState(0).randn(1, OBS_W).astype(np.float32)
    a_before, _ = model.predict(obs, deterministic=True)
    p = tmp_path / "decleg.zip"
    model.save(p)
    loaded = PPO.load(p, device="cpu")
    a_after, _ = loaded.predict(obs, deterministic=True)
    np.testing.assert_allclose(a_before, a_after, rtol=0, atol=0)
    assert isinstance(loaded.policy, DecLegActorCriticPolicy)


# ---------------------------------------------------------------------
# Addendum (DESIGN_NOTE_2026-09-10_offaxis_frontpair.md, 13th mechanism
# class): --decleg-share-legs / --decleg-heading-rel. Both default OFF
# (heading_rel_idx=None, share_leg_weights=False) and every test above
# already covers that path unchanged; these cover the new opt-in path.
# ---------------------------------------------------------------------

def _policy_addendum(share_leg_weights=False, heading_rel_idx=None,
                     seed=0):
    torch.manual_seed(seed)
    legs, shared = joint_walk_leg_slices(OBS_W)
    obs_space = gym.spaces.Box(-np.inf, np.inf, shape=(OBS_W,),
                               dtype=np.float32)
    act_space = gym.spaces.Box(-1.0, 1.0, shape=(ACT_W,),
                               dtype=np.float32)
    return DecLegActorCriticPolicy(
        obs_space, act_space, lambda _: 3e-4,
        net_arch=[128, 64, 32], leg_obs_idx=legs, shared_obs_idx=shared,
        leg_hidden=(64, 64), share_leg_weights=share_leg_weights,
        heading_rel_idx=heading_rel_idx)


def test_heading_rel_cos_sin_matches_hand_rotation():
    # forward command (cos=1, sin=0): rel angle = -mount_angle for
    # every leg (leg0 mount +30 -> rel -30; leg3 mount -150 -> rel 150).
    for mount_deg, (mc, ms) in zip(LEG_MOUNT_ANGLES_DEG,
                                   leg_mount_unit_vectors()):
        cos_rel, sin_rel = heading_rel_cos_sin(1.0, 0.0, mc, ms)
        rel_deg = math.degrees(math.atan2(sin_rel, cos_rel))
        assert rel_deg == pytest.approx(-mount_deg, abs=1e-6)


def test_heading_rel_cos_sin_leg0_180_matches_leg3_forward():
    # The whole point of the mechanism: leg0 (mount +30) commanded 180
    # degrees, and leg3 (mount -150) commanded forward (0 degrees),
    # both land at the SAME mount-relative angle (150 degrees) -- the
    # precondition for a shared tower to transfer skill between them.
    mounts = dict(zip(range(N_LEGS), leg_mount_unit_vectors()))
    leg0_at_180 = heading_rel_cos_sin(-1.0, 0.0, *mounts[0])
    leg3_at_fwd = heading_rel_cos_sin(1.0, 0.0, *mounts[3])
    assert leg0_at_180 == pytest.approx(leg3_at_fwd, abs=1e-9)


def test_heading_rel_idx_none_is_bit_exact_original_in_dim():
    pol = _policy_addendum()
    first_linear = pol.mlp_extractor.leg_nets[0][0]
    legs, shared = joint_walk_leg_slices(OBS_W)
    assert first_linear.in_features == len(shared) + len(legs[0])


def test_heading_rel_idx_adds_two_input_dims():
    pol = _policy_addendum(heading_rel_idx=_HEADING_IDX)
    first_linear = pol.mlp_extractor.leg_nets[0][0]
    legs, shared = joint_walk_leg_slices(OBS_W)
    assert first_linear.in_features == len(shared) + len(legs[0]) + 2


def test_share_leg_weights_ties_the_same_parameter_object():
    pol = _policy_addendum(share_leg_weights=True)
    w0 = pol.mlp_extractor.leg_nets[0][0].weight
    w3 = pol.mlp_extractor.leg_nets[3][0].weight
    assert w0 is w3   # literally the same Parameter, not just equal
    # named_parameters() must not double-count it (optimizer sanity)
    n_shared_tower_params = sum(
        1 for n, _ in pol.named_parameters()
        if n.startswith("mlp_extractor.leg_nets.0."))
    pol_indep = _policy_addendum(share_leg_weights=False)
    n_indep_tower_params = sum(
        1 for n, _ in pol_indep.named_parameters()
        if n.startswith("mlp_extractor.leg_nets."))
    assert n_shared_tower_params * N_LEGS == n_indep_tower_params


def test_share_leg_weights_gradient_accumulates_across_legs():
    pol = _policy_addendum(share_leg_weights=True)
    obs = torch.randn(4, OBS_W)
    latent = pol.mlp_extractor.forward_actor(obs)
    loss = latent.pow(2).sum()
    loss.backward()
    w = pol.mlp_extractor.leg_nets[0][0].weight
    assert w.grad is not None
    assert torch.isfinite(w.grad).all()
    assert w.grad.abs().sum().item() > 0.0


def test_shared_heading_rel_leg0_at_180_matches_leg3_at_forward():
    """The core mechanism claim, isolated at the tied-tower level:
    given the SAME (zeroed) shared/local state, feeding leg0 its own
    mount-relative rotation of a 180-degree command produces the
    IDENTICAL output leg3 gets from ITS mount-relative rotation of a
    forward (0-degree) command -- same shared-weight tower, same
    rotated feature value, so literally the same function call. This
    is what makes cross-leg skill transfer possible in principle
    (decleg's plain independent-tower default cannot do this even in
    theory: leg_nets[0] and leg_nets[3] are different objects with
    different weights no matter what you feed them).

    (The full ``forward_actor`` path additionally feeds the RAW
    absolute heading through the ``shared`` block alongside this
    rotated feature -- a deliberate augmentation, not a replacement --
    so it does not itself produce bit-identical leg0/leg3 outputs;
    this test isolates the rotated-feature-plus-tied-weights claim
    directly at the tower level, which the higher-level bit-exact/
    extra-input-dims tests above confirm is exactly what
    ``forward_actor`` feeds each leg alongside the shared block.)"""
    pol = _policy_addendum(share_leg_weights=True,
                          heading_rel_idx=_HEADING_IDX)
    pol.eval()
    legs, shared = joint_walk_leg_slices(OBS_W)
    mounts = leg_mount_unit_vectors()
    shared_vec = torch.zeros(1, len(shared))
    local_vec = torch.zeros(1, len(legs[0]))

    def _rel(vx_ref: float, vy_ref: float, leg: int) -> torch.Tensor:
        cos_rel, sin_rel = heading_rel_cos_sin(vx_ref, vy_ref, *mounts[leg])
        return torch.tensor([[cos_rel, sin_rel]], dtype=torch.float32)

    in_leg0_at_180 = torch.cat(
        [shared_vec, local_vec, _rel(-1.0, 0.0, 0)], dim=-1)
    in_leg3_at_fwd = torch.cat(
        [shared_vec, local_vec, _rel(1.0, 0.0, 3)], dim=-1)
    with torch.no_grad():
        out_leg0_at_180 = pol.mlp_extractor.leg_nets[0](in_leg0_at_180)
        out_leg3_at_fwd = pol.mlp_extractor.leg_nets[3](in_leg3_at_fwd)
    torch.testing.assert_close(out_leg0_at_180, out_leg3_at_fwd)
    # sanity: leg0 at forward (not rotated to the leg3-equivalent
    # angle) must give a DIFFERENT output -- the feature/tying isn't
    # trivially constant regardless of input.
    in_leg0_at_fwd = torch.cat(
        [shared_vec, local_vec, _rel(1.0, 0.0, 0)], dim=-1)
    with torch.no_grad():
        out_leg0_at_fwd = pol.mlp_extractor.leg_nets[0](in_leg0_at_fwd)
    assert not torch.allclose(out_leg0_at_fwd, out_leg0_at_180)


def test_share_legs_alone_ppo_save_load_roundtrip(tmp_path):
    """Combined addendum kwargs still round-trip through PPO save/load
    (policy_kwargs persistence), matching the existing plain-decleg
    roundtrip test."""
    legs, shared = joint_walk_leg_slices(OBS_W)
    venv = DummyVecEnv([_DummyJointEnv])
    model = PPO(DecLegActorCriticPolicy, venv, n_steps=8, batch_size=8,
                seed=3, device="cpu",
                policy_kwargs=dict(net_arch=[128, 64, 32],
                                   leg_obs_idx=legs,
                                   shared_obs_idx=shared,
                                   leg_hidden=(64, 64),
                                   share_leg_weights=True,
                                   heading_rel_idx=_HEADING_IDX))
    obs = np.random.RandomState(0).randn(1, OBS_W).astype(np.float32)
    a_before, _ = model.predict(obs, deterministic=True)
    p = tmp_path / "decleg_addendum.zip"
    model.save(p)
    loaded = PPO.load(p, device="cpu")
    a_after, _ = loaded.predict(obs, deterministic=True)
    np.testing.assert_allclose(a_before, a_after, rtol=0, atol=0)
    assert loaded.policy.share_leg_weights is True
    assert loaded.policy.heading_rel_idx == _HEADING_IDX


def test_optimizer_covers_all_params():
    """The swapped-in per-leg head must be optimizer-registered (the
    stock action_net was registered by super()._build and then
    replaced — a stale optimizer would silently freeze the head)."""
    pol = _policy()
    opt_params = {id(p) for g in pol.optimizer.param_groups
                  for p in g["params"]}
    model_params = {id(p) for p in pol.parameters()}
    assert model_params <= opt_params
    head_params = {id(p) for p in pol.action_net.parameters()}
    assert head_params <= opt_params
