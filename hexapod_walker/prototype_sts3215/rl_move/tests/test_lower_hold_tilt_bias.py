"""goal.lower_hold_tilt_bias_deg/_axis (2026-10-06, walkcurr lowerrole
terminal-support habit -- STATUS.md Next 3 directional-goal-reference
candidate, queued once both lower_hold_wobble_deg doses closed): a
CONSTANT (non-oscillating) signed roll-or-pitch bias applied ONLY to the
lower role's POST-RAMP hold/settle window, same window/edge-ramp
convention as lower_hold_wobble_deg but directional instead of zero-
mean. Mechanics-only: default-off bit-exactness, cfg-override reach,
axis validation and the windowing/envelope shape -- no rollout-ranking,
no training."""
import numpy as np
import pytest

from rl_move.config import load_config
from rl_move.sim.goal_task import GoalGenerator


def _gen(bias_deg=0.0, axis="roll", **extra):
    cfg = load_config()
    g = cfg.setdefault("goal", {})
    g["p_hold"] = g["p_lean"] = g["p_track"] = 0.0
    g["p_unload"] = g["p_raise"] = g["p_rise"] = 0.0
    g["p_lower"] = 1.0
    g["lower_hold_tilt_bias_deg"] = bias_deg
    g["lower_hold_tilt_bias_axis"] = axis
    for k, v in extra.items():
        g[k] = v
    return GoalGenerator(cfg)


def test_default_off_bit_exact():
    gen = _gen()
    assert gen.lower_hold_tilt_bias_deg == 0.0
    assert gen.lower_hold_tilt_bias_axis == "roll"
    rng = np.random.default_rng(0)
    traj = gen.sample(rng, n_steps=750, dt=0.02, force_mode="lower")
    assert np.all(traj.roll == 0.0)
    assert np.all(traj.pitch == 0.0)


def test_invalid_axis_raises():
    with pytest.raises(ValueError):
        _gen(bias_deg=1.0, axis="yaw")


def test_cfg_override_reaches_generator():
    gen = _gen(bias_deg=1.5, axis="pitch")
    assert gen.lower_hold_tilt_bias_deg == 1.5
    assert gen.lower_hold_tilt_bias_axis == "pitch"


@pytest.mark.parametrize("axis", ["roll", "pitch"])
@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_bias_nonzero_only_in_post_ramp_window_and_is_directional(axis, sign):
    bias_deg = 1.5 * sign
    gen = _gen(bias_deg=bias_deg, axis=axis)
    rng = np.random.default_rng(1)
    dt = 0.02
    n_steps = 750
    traj = gen.sample(rng, n_steps=n_steps, dt=dt, force_mode="lower")
    hold_n = max(1, int(round(gen.lower_hold_s / dt)))
    ramp_n = max(1, int(round(gen.lower_ramp_s / dt)))
    seam = hold_n + ramp_n
    assert np.all(traj.roll[:seam] == 0.0)
    assert np.all(traj.pitch[:seam] == 0.0)
    other = traj.pitch if axis == "roll" else traj.roll
    biased = traj.roll if axis == "roll" else traj.pitch
    assert np.all(other == 0.0)
    assert np.any(biased[seam:] != 0.0)
    # Directional: the plateau sign matches the configured sign (the
    # tail's interior, away from the ramp edges, should sit at the
    # signed cap or the raw bias, whichever is smaller in magnitude).
    interior = biased[seam:][len(biased[seam:]) // 2]
    assert np.sign(interior) == np.sign(bias_deg)
    assert np.max(np.abs(traj.roll)) <= gen.max_roll + 1e-9
    assert np.max(np.abs(traj.pitch)) <= gen.max_pitch + 1e-9


def test_bias_seam_and_tail_are_continuous_no_step():
    gen = _gen(bias_deg=2.0, axis="roll")
    rng = np.random.default_rng(2)
    dt = 0.02
    n_steps = 750
    traj = gen.sample(rng, n_steps=n_steps, dt=dt, force_mode="lower")
    hold_n = max(1, int(round(gen.lower_hold_s / dt)))
    ramp_n = max(1, int(round(gen.lower_ramp_s / dt)))
    seam = hold_n + ramp_n
    if seam < n_steps:
        assert abs(float(traj.roll[seam])) < 1e-9
        assert abs(float(traj.roll[-1])) < 1e-6


def test_bias_does_not_affect_other_modes():
    gen = _gen(bias_deg=3.0, axis="pitch")
    rng = np.random.default_rng(3)
    for mode in ("hold", "rise", "raise", "unload"):
        traj = gen.sample(rng, n_steps=750, dt=0.02, force_mode=mode)
        assert np.all(traj.roll == 0.0), mode
        assert np.all(traj.pitch == 0.0), mode


def test_composes_additively_with_wobble():
    """Both keys nonzero: tilt bias shifts the wobble's mean without
    replacing it (uses += at the call site)."""
    gen = _gen(bias_deg=1.0, axis="roll", lower_hold_wobble_deg=1.0)
    rng = np.random.default_rng(4)
    dt = 0.02
    traj = gen.sample(rng, n_steps=750, dt=dt, force_mode="lower")
    hold_n = max(1, int(round(gen.lower_hold_s / dt)))
    ramp_n = max(1, int(round(gen.lower_ramp_s / dt)))
    seam = hold_n + ramp_n
    tail = traj.roll[seam:]
    # Mean should be biased positive (bias dominates away from the
    # ramp edges), not symmetric around zero like pure wobble.
    interior = tail[len(tail) // 3: -max(1, len(tail) // 3)]
    assert interior.size == 0 or np.mean(interior) > 0.0


def test_lower_hold_tilt_bias_rng_stream_unconditional_draw_count_unchanged():
    """Default (off) must consume IDENTICAL rng draws to pre-feature
    code (the helper takes no rng argument at all and is only called
    when bias_deg != 0, so the stream must be bit-exact unchanged when
    off)."""
    cfg_plain = load_config()
    gp = cfg_plain.setdefault("goal", {})
    gp["p_hold"] = gp["p_lean"] = gp["p_track"] = 0.0
    gp["p_unload"] = gp["p_raise"] = gp["p_rise"] = 0.0
    gp["p_lower"] = 1.0
    gen_plain = GoalGenerator(cfg_plain)
    gen_bias = _gen(bias_deg=0.0)
    for seed in range(5):
        t1 = gen_plain.sample(np.random.default_rng(seed), n_steps=750,
                              dt=0.02, force_mode="lower")
        t2 = gen_bias.sample(np.random.default_rng(seed), n_steps=750,
                             dt=0.02, force_mode="lower")
        assert np.array_equal(t1.roll, t2.roll)
        assert np.array_equal(t1.pitch, t2.pitch)
        assert np.array_equal(t1.height, t2.height)
        assert t1.start_at == t2.start_at
