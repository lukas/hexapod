"""dr.write_speed_counts_s -- per-episode bus write PROFILE randomization.

2026-09-27: the robot's scripted gait writes servo goals at 2000/80 while RL
trained and deployed at 400/20; the 2026-09-21 sim refit had folded the
400/20 profile ramp into a 130/125 ms yaw/hip latency. The profile is now a
DR axis: speed sampled per episode, acc tied (servo_model.write_acc_for_speed),
and the ServoProfile speed CEILING follows the sample on both the CPU
(SimHexapodEnv._profile_vel_scale) and warp (mjx_host.tp_rows) paths --
the leg_torque lesson: a DR axis the tick never consumes is a silent no-op.
"""
from __future__ import annotations

import numpy as np

from rl_move.config import load_config
from rl_move.sim import mjx_host
from rl_move.sim.domain_rand import DomainRandomizer, RandRanges
from rl_move.sim.servo_model import (
    COUNTS_PER_DEG, DEG2RAD, SimServoParams, write_acc_for_speed)

CPS_TO_DEG = 360.0 / 4096.0


def test_acc_follows_speed_on_the_two_operator_contracts():
    assert write_acc_for_speed(400) == 20.0
    assert write_acc_for_speed(2000) == 80.0
    assert write_acc_for_speed(1200) == 50.0
    assert write_acc_for_speed(0) == 5.0          # clamped, never 0
    assert write_acc_for_speed(10_000) == 254.0


def test_default_off_samples_zero_and_survives_scaling():
    r = RandRanges()
    assert r.write_speed_counts_s == (0.0, 0.0)
    ep = DomainRandomizer(r).sample(np.random.default_rng(0))
    assert ep.write_speed_counts_s == 0.0
    assert r.scaled(0.0).write_speed_counts_s == (0.0, 0.0)


def test_range_is_absolute_and_sampled_inside():
    r = RandRanges(write_speed_counts_s=(400.0, 2000.0))
    assert r.scaled(0.0).write_speed_counts_s == (400.0, 2000.0)   # absolute, like every dr.* override
    rng = np.random.default_rng(1)
    vals = [DomainRandomizer(r).sample(rng).write_speed_counts_s for _ in range(50)]
    assert all(400.0 <= v <= 2000.0 for v in vals) and (max(vals) - min(vals)) > 500
    assert "write_speed_counts_s" in DomainRandomizer(r).sample(rng).summary()


def _env(dr: dict, **kw):
    from rl_move.sim.eval_checkpoint import ENV_CLASSES
    cfg = load_config()
    cfg.setdefault("dr", {}).update(dr)
    cfg.setdefault("bus", {})["write_speed"] = 400
    cfg["bus"]["write_acc"] = 20
    cfg["bus"]["servo_vel_max_counts_s"] = "write_speed"
    return ENV_CLASSES["joint_walk"](params=SimServoParams.from_cfg(cfg), randomize=True,
                                     dr_scale=0.0, episode_seconds=20, seed=3, render_mode=None,
                                     cfg=cfg, **kw)


def test_env_profile_follows_the_sample_on_cpu_and_warp_rows():
    env = _env({"write_speed_counts_s": "1000,2000"})
    seen = set()
    for seed in range(4):
        env.reset(seed=seed)
        ws = env._ep_rand.write_speed_counts_s
        assert 1000.0 <= ws <= 2000.0
        seen.add(round(ws))
        assert np.isclose(env.write_speed_deg_s, ws * CPS_TO_DEG)
        assert np.isclose(env.write_acc_units, write_acc_for_speed(ws))
        # CPU ServoProfile ceiling = sampled speed x dr.vel_scale (not the fitted 400 cps)
        want = ws * CPS_TO_DEG * DEG2RAD * env._ep_rand.vel_scale
        assert np.allclose(env._profile._vel_default, want), (env._profile._vel_default, want)
        # warp TickParams row carries the same ceiling
        assert np.allclose(mjx_host.tp_rows(env)["vel_max"], want)
    assert len(seen) > 1
    env.close()


def test_env_off_keeps_cfg_profile_bit_exact():
    env = _env({})
    env.reset(seed=0)
    assert env._ep_rand.write_speed_counts_s == 0.0
    assert np.isclose(env.write_speed_deg_s, 400 * CPS_TO_DEG) and env.write_acc_units == 20.0
    assert np.allclose(env._profile._vel_default,
                       400 / COUNTS_PER_DEG * DEG2RAD * env._ep_rand.vel_scale)
    env.close()
