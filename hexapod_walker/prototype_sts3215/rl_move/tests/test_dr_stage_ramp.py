"""env.dr_stage_ramp_steps — trainer-driven staged-DR curriculum.

09-08, staged-DR-breadth fresh-acquisition design (walkcurr/easy0905
fresh-init line): the failed fresh-init recipes (widen8 crutchoff
seed40/41, torqueretain pair) carry their ENTIRE DR matrix as explicit
--cfg-set dr.* overrides. Those overrides are ABSOLUTE, applied AFTER
--dr-scale scaling (sim_env.__init__), and the walkcurr bucket ladder
re-applies the same absolute overrides per bucket — so NO pre-existing
knob can ramp DR exposure for these recipes: they train at the full
matrix from step 0. This mechanism stages the episode-reset DR
distribution from the calibrated nominal sim (frac 0) to the run's
full post-override ranges (frac 1), trainer-driven per rollout,
mirroring bus.profile_ramp_steps' construction exactly (cfg-armed,
default OFF = bit-exact legacy, armed-but-unbroadcast = full ranges so
eval_checkpoint judges checkpoints at full DR).

Contract under test:
  - default (key absent/0) is bit-exact OFF: no ramp state, apply raises;
  - ARMED env sits at the FULL post-override ranges until broadcast;
  - frac >= 1 restores the EXACT captured full-ranges object (endpoint
    is bit-identical to the un-staged recipe);
  - frac 0 -> nominal structural DR with sensor-noise floors kept;
    pinned override pairs (e.g. dr.torque_scale=1,1) stay pinned at
    every frac; probabilities ramp, per-event doses do not
    (RandRanges.scaled semantics);
  - the live override actually changes what reset() DRAWS (reset-
    distribution verification, not just stored state);
  - fail-closed: armed with randomize=False raises; armed together
    with goal.walk_curriculum raises.
"""
from __future__ import annotations


import numpy as np
import pytest


pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.servo_model import SimServoParams

# The failed fresh-init recipes' DR-override shape (subset): full
# structural ranges as absolute overrides, pinned latency/deadband/
# torque, sensor-noise floors, event probabilities.
DR_OVERRIDES = {
    ("dr", "mass_scale"): "0.85,1.20",
    ("dr", "friction_scale"): "0.6,1.4",
    ("dr", "ground_tilt_deg"): 2.0,
    ("dr", "bad_start_prob"): 0.25,
    ("dr", "bad_start_deg"): "8.0,35.0",
    ("dr", "torque_scale"): "1,1",
    ("dr", "latency_scale"): "1,1",
    ("dr", "encoder_noise_deg"): 0.09,
    ("dr", "tilt_noise_deg"): 0.3,
    ("dr", "fault_prob"): 0.3,
    ("dr", "walk_push_prob"): 0.3,
}
ARM = {("env", "dr_stage_ramp_steps"): 1_000_000}


def _cfg(extra=None):
    cfg = load_config()
    for (sec, leaf), val in (extra or {}).items():
        cfg.setdefault(sec, {})[leaf] = val
    return cfg


def _env(extra=None, seed=0, randomize=True, dr_scale=0.0):
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = _cfg(extra)
    params = SimServoParams.from_cfg(cfg)
    return SimHexapodJointWalkEnv(
        params=params, randomize=randomize, dr_scale=dr_scale,
        episode_seconds=2.0, seed=seed, cfg=cfg)


def test_default_off_bit_exact_and_apply_raises():
    env = _env(DR_OVERRIDES)
    assert env._dr_stage_full is None
    assert env._dr_stage_frac is None
    with pytest.raises(RuntimeError, match="not armed"):
        env.apply_dr_stage_frac(0.5)
    env.close()


def test_armed_unbroadcast_sits_at_full_ranges():
    plain = _env(DR_OVERRIDES)
    armed = _env({**DR_OVERRIDES, **ARM})
    # Armed-but-unbroadcast must expose the identical post-override
    # ranges a non-staged env has (eval/play judge at full DR).
    assert armed.randomizer.ranges == plain.randomizer.ranges
    assert armed._dr_stage_full is armed.randomizer.ranges
    plain.close()
    armed.close()


def test_endpoint_restores_exact_full_ranges_object():
    env = _env({**DR_OVERRIDES, **ARM})
    full = env.randomizer.ranges
    env.apply_dr_stage_frac(0.5)
    assert env.randomizer.ranges is not full
    vals = env.apply_dr_stage_frac(1.0)
    assert vals["frac"] == 1.0
    assert env.randomizer.ranges is full          # bit-identical endpoint
    # Overshoot clamps.
    env.apply_dr_stage_frac(2.0)
    assert env.randomizer.ranges is full
    env.close()


def test_midpoint_interpolation_and_pinned_pairs():
    env = _env({**DR_OVERRIDES, **ARM})
    vals = env.apply_dr_stage_frac(0.5)
    r = env.randomizer.ranges
    # pair(lo,hi) interpolates toward (1,1): midpoint of (0.85,1.20).
    assert np.allclose(r.mass_scale, (0.925, 1.10))
    assert np.allclose(r.friction_scale, (0.8, 1.2))
    # Scalars scale linearly.
    assert np.isclose(r.ground_tilt_deg, 1.0)
    # Probabilities ramp; per-event doses do not.
    assert np.isclose(r.bad_start_prob, 0.125)
    assert np.allclose(r.bad_start_deg, (4.0, 17.5))
    assert np.isclose(r.fault_prob, 0.15)
    assert np.isclose(r.walk_push_prob, 0.15)
    # Pinned override pairs stay pinned at every frac.
    assert tuple(r.torque_scale) == (1.0, 1.0)
    assert tuple(r.latency_scale) == (1.0, 1.0)
    # Sensor-noise floors never shrink (real sensors are always noisy).
    assert np.isclose(r.encoder_noise_deg, 0.09)
    assert np.isclose(r.tilt_noise_deg, 0.3)
    assert vals["mass_scale_lo"] == pytest.approx(0.925)
    env.close()


def test_frac0_is_nominal_with_noise_floors():
    env = _env({**DR_OVERRIDES, **ARM})
    env.apply_dr_stage_frac(0.0)
    r = env.randomizer.ranges
    assert tuple(r.mass_scale) == (1.0, 1.0)
    assert tuple(r.friction_scale) == (1.0, 1.0)
    assert r.ground_tilt_deg == 0.0
    assert r.bad_start_prob == 0.0
    assert r.fault_prob == 0.0
    assert np.isclose(r.encoder_noise_deg, 0.09)
    assert np.isclose(r.gyro_noise_deg_s, 0.5)
    env.close()


def test_reset_distribution_actually_changes():
    """The stage must change what reset() DRAWS, not just stored state."""
    # Pure-walk diet: the default goal mix can sample rise goals that
    # do not fit a short test episode (unrelated to the ramp).
    env = _env({**DR_OVERRIDES, **ARM, ("goal", "walk_pure"): 1},
               seed=3)
    env.apply_dr_stage_frac(0.0)
    for _ in range(8):
        env.reset()
        er = env._ep_rand
        assert er.mass_scale == pytest.approx(1.0)
        assert er.friction_scale == pytest.approx(1.0)
        assert er.torque_scale == pytest.approx(1.0)
        assert np.allclose(er.gravity_vec[:2], 0.0)   # no ground tilt
    env.apply_dr_stage_frac(1.0)
    masses, frictions = [], []
    for _ in range(24):
        env.reset()
        er = env._ep_rand
        masses.append(er.mass_scale)
        frictions.append(er.friction_scale)
        assert 0.85 - 1e-9 <= er.mass_scale <= 1.20 + 1e-9
        assert 0.6 - 1e-9 <= er.friction_scale <= 1.4 + 1e-9
    # Full ranges are actually exercised (spread, not pinned nominal).
    assert max(masses) - min(masses) > 0.05
    assert max(frictions) - min(frictions) > 0.1
    env.close()


def test_armed_without_randomizer_raises():
    with pytest.raises(ValueError, match="nothing to stage"):
        _env(ARM, randomize=False)


def test_armed_with_walk_curriculum_raises():
    with pytest.raises(ValueError, match="walk_curriculum"):
        _env({**DR_OVERRIDES, **ARM,
              ("goal", "walk_curriculum"): 1,
              ("goal", "p_walk"): 1.0})
