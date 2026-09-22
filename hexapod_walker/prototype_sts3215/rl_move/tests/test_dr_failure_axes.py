"""Functional tests for the 2026-09-22 hardware-failure DR axes:
servo command drop-BURSTS (dr.cmd_drop_burst_len) and IMU dropout/freeze
(dr.imu_dropout_*). Bit-exactness when OFF is proven separately by the
fingerprint2 harness; these tests prove the axes actually FIRE when ON and
that enabling them never shifts the base draws."""
import numpy as np
from types import SimpleNamespace

from rl_move.sim.domain_rand import RandRanges, DomainRandomizer
from rl_move.sim.walk_task import SimHexapodJointWalkEnv


def test_scaled_scales_prob_but_not_dose():
    r = RandRanges(imu_dropout_prob_max=0.4, imu_dropout_ticks=10.0,
                   imu_dropout_dead_frac=0.5, cmd_drop_burst_len=6.0)
    s = r.scaled(0.5)
    # probability follows the curriculum
    assert abs(s.imu_dropout_prob_max - 0.2) < 1e-12
    # dose (length / dead-fraction) does NOT shrink
    assert s.imu_dropout_ticks == 10.0
    assert s.imu_dropout_dead_frac == 0.5
    assert s.cmd_drop_burst_len == 6.0


def test_sample_enabled_vs_disabled():
    # disabled -> imu_dropout_prob stays 0; enabled -> in (0, max]
    off = DomainRandomizer(ranges=RandRanges()).sample(np.random.default_rng(3))
    assert off.imu_dropout_prob == 0.0
    assert off.cmd_drop_burst_len == 0.0
    on = DomainRandomizer(
        ranges=RandRanges(imu_dropout_prob_max=0.4, imu_dropout_ticks=12.0,
                          cmd_drop_burst_len=6.0)
    ).sample(np.random.default_rng(3))
    assert 0.0 < on.imu_dropout_prob <= 0.4
    assert on.imu_dropout_ticks == 12.0
    assert on.cmd_drop_burst_len == 6.0


def test_enabling_does_not_shift_base_draws():
    """The guarded imu_dropout_prob draw happens LAST, so enabling the axis
    must leave every pre-existing base field byte-identical for a given seed."""
    base = RandRanges(mass_scale=(0.8, 1.2), cmd_drop_prob_max=0.05)
    a = DomainRandomizer(ranges=base).sample(np.random.default_rng(7))
    b = DomainRandomizer(
        ranges=RandRanges(mass_scale=(0.8, 1.2), cmd_drop_prob_max=0.05,
                          imu_dropout_prob_max=0.3, imu_dropout_ticks=10.0)
    ).sample(np.random.default_rng(7))
    assert a.mass_scale == b.mass_scale
    assert a.cmd_drop_prob == b.cmd_drop_prob
    assert np.array_equal(a.kp_scale, b.kp_scale)
    assert np.array_equal(a.start_offset_rad, b.start_offset_rad)
    # only the newly-enabled axis differs
    assert a.imu_dropout_prob == 0.0 and b.imu_dropout_prob > 0.0


def _stub_env():
    e = SimpleNamespace()
    e.rng = np.random.default_rng(0)
    e._imu_hold_rp = None
    e._imu_hold_gyro = None
    e._imu_dropping = False
    e._imu_drop_dead = False
    return e


def test_imu_dropout_freezes_while_truth_moves():
    e = _stub_env()
    er = SimpleNamespace(imu_dropout_prob=1.0, imu_dropout_ticks=1000.0,
                         imu_dropout_dead_frac=0.0)  # always-freeze, long burst
    fn = SimHexapodJointWalkEnv._apply_imu_dropout
    r0, p0, g0 = fn(e, er, 0.10, 0.20, np.array([1.0, 2.0, 3.0]))
    assert (r0, p0) == (0.10, 0.20)  # tick-0 dropout freezes the REAL read
    # feed CHANGING truth; obs must stay pinned to the tick-0 values
    for i in range(25):
        r, p, g = fn(e, er, 5.0 + i, -5.0 - i, np.array([9.0, 9.0, 9.0]))
        assert (r, p) == (0.10, 0.20), "IMU freeze did not hold"
        assert np.allclose(g, [1.0, 2.0, 3.0])


def test_imu_dropout_dead_returns_zero():
    e = _stub_env()
    er = SimpleNamespace(imu_dropout_prob=1.0, imu_dropout_ticks=1000.0,
                         imu_dropout_dead_frac=1.0)  # always-dead
    fn = SimHexapodJointWalkEnv._apply_imu_dropout
    fn(e, er, 0.10, 0.20, np.array([1.0, 2.0, 3.0]))
    r, p, g = fn(e, er, 5.0, 5.0, np.array([5.0, 5.0, 5.0]))
    assert (r, p) == (0.0, 0.0)
    assert np.allclose(g, [0.0, 0.0, 0.0])


def test_imu_dropout_recovers_to_truth():
    e = _stub_env()
    # short bursts (ticks=1 -> exit prob 1.0 -> single-tick dropouts), low prob
    er = SimpleNamespace(imu_dropout_prob=0.05, imu_dropout_ticks=4.0,
                         imu_dropout_dead_frac=0.0)
    fn = SimHexapodJointWalkEnv._apply_imu_dropout
    seen_healthy_after_drop = False
    dropped_any = False
    prev_true = None
    for i in range(4000):
        true_r = np.sin(i * 0.1)
        r, p, g = fn(e, er, true_r, 0.0, np.array([float(i), 0.0, 0.0]))
        if not e._imu_dropping and r == true_r:
            seen_healthy_after_drop = True
        if e._imu_dropping:
            dropped_any = True
        prev_true = true_r
    assert dropped_any, "no dropout ever fired at prob 0.05 over 4000 ticks"
    assert seen_healthy_after_drop, "never recovered to the true reading"


def _cpu_walk_env(cfg, seed=1, episode_seconds=30.0):
    from rl_move.sim.servo_model import SimServoParams
    return SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=True,
        dr_scale=1.0, episode_seconds=episode_seconds, seed=seed, cfg=cfg)


def _drop_run_lengths(cfg, n_steps=800):
    from rl_move.config import load_config
    base = load_config()
    base.setdefault("dr", {}).update(cfg)
    env = _cpu_walk_env(base)
    env.reset()
    act = np.zeros(env.action_space.shape, dtype=np.float32)
    runs, cur = [], 0
    for _ in range(n_steps):
        out = env.step(act)
        if getattr(env, "_cmd_dropping", False):
            cur += 1
        elif cur > 0:
            runs.append(cur)
            cur = 0
        done = out[2] if len(out) >= 4 else False
        if done:
            env.reset()
            if cur > 0:
                runs.append(cur)
                cur = 0
    if cur > 0:
        runs.append(cur)
    return runs


def test_cmd_drop_bursts_are_longer_than_iid():
    # bursty: mean run length should clearly exceed 1
    bursty = _drop_run_lengths(
        {"cmd_drop_prob_max": 0.6, "cmd_drop_burst_len": 8.0})
    assert bursty, "bursty config produced no drops"
    mean_bursty = float(np.mean(bursty))
    assert mean_bursty > 2.0, f"bursts too short: mean run {mean_bursty:.2f}"
    # i.i.d. (burst_len default 0): runs are essentially single ticks
    iid = _drop_run_lengths({"cmd_drop_prob_max": 0.6})
    if iid:
        mean_iid = float(np.mean(iid))
        assert mean_iid < mean_bursty, (
            f"i.i.d. mean {mean_iid:.2f} not < bursty {mean_bursty:.2f}")
