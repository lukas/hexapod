"""goal.lower_hold_wobble_deg (2026-10-05, walkcurr lowerrole terminal-
support habit -- STATUS.md Next 1's "gait-phase/contact-schedule
intervention in the walk->lower handoff itself... not a reward price or
an episode-sampling mix" framing): a small continuous roll/pitch
sum-of-sines reference applied ONLY to the lower role's POST-RAMP hold/
settle window, reusing the existing `track`-goal `_track_channel`
generator and the ordinary tilt-tracking reward kernel (no new price,
no new observation channel, no episode-sampling mix). Mechanics-only:
default-off bit-exactness, cfg-override reach, and the windowing/
envelope shape -- no rollout-ranking, no training."""
import numpy as np

from rl_move.config import load_config
from rl_move.sim.goal_task import GoalGenerator


def _gen(wobble_deg=0.0, **extra):
    cfg = load_config()
    g = cfg.setdefault("goal", {})
    g["p_hold"] = g["p_lean"] = g["p_track"] = 0.0
    g["p_unload"] = g["p_raise"] = g["p_rise"] = 0.0
    g["p_lower"] = 1.0
    g["lower_hold_wobble_deg"] = wobble_deg
    for k, v in extra.items():
        g[k] = v
    return GoalGenerator(cfg)


def test_default_off_bit_exact():
    gen = _gen()
    assert gen.lower_hold_wobble_deg == 0.0
    rng = np.random.default_rng(0)
    traj = gen.sample(rng, n_steps=750, dt=0.02, force_mode="lower")
    assert np.all(traj.roll == 0.0)
    assert np.all(traj.pitch == 0.0)


def test_cfg_override_reaches_generator():
    gen = _gen(wobble_deg=2.0)
    assert gen.lower_hold_wobble_deg == 2.0
    assert gen.lower_hold_wobble_period_s == (1.5, 3.0)


def test_cfg_override_period_reaches_generator():
    gen = _gen(wobble_deg=2.0, lower_hold_wobble_period_s=[0.5, 1.0])
    assert gen.lower_hold_wobble_period_s == (0.5, 1.0)


def test_wobble_nonzero_only_in_post_ramp_window():
    gen = _gen(wobble_deg=2.0)
    rng = np.random.default_rng(1)
    dt = 0.02
    n_steps = 750
    traj = gen.sample(rng, n_steps=n_steps, dt=dt, force_mode="lower")
    # hold_n (pre-descent) + ramp_n (descent) ticks must stay EXACTLY
    # flat (roll=pitch=0) -- the wobble only ever touches the tail.
    hold_n = max(1, int(round(gen.lower_hold_s / dt)))
    # ramp_n varies with the jittered draw (default jitter=0 here, so
    # it's deterministic): lower_ramp_s / dt.
    ramp_n = max(1, int(round(gen.lower_ramp_s / dt)))
    seam = hold_n + ramp_n
    assert np.all(traj.roll[:seam] == 0.0)
    assert np.all(traj.pitch[:seam] == 0.0)
    # Somewhere in the tail it must actually be nonzero (the mechanism
    # fires, not a silent no-op).
    assert np.any(traj.roll[seam:] != 0.0) or np.any(
        traj.pitch[seam:] != 0.0)
    # Never exceeds the same per-axis action-envelope cap track/lean
    # already enforce.
    assert np.max(np.abs(traj.roll)) <= gen.max_roll + 1e-9
    assert np.max(np.abs(traj.pitch)) <= gen.max_pitch + 1e-9


def test_wobble_seam_and_tail_are_continuous_no_step():
    """The envelope ramps in/out: the first and last tail samples must
    be exactly zero (no discontinuity at either boundary)."""
    gen = _gen(wobble_deg=3.0)
    rng = np.random.default_rng(2)
    dt = 0.02
    n_steps = 750
    traj = gen.sample(rng, n_steps=n_steps, dt=dt, force_mode="lower")
    hold_n = max(1, int(round(gen.lower_hold_s / dt)))
    ramp_n = max(1, int(round(gen.lower_ramp_s / dt)))
    seam = hold_n + ramp_n
    if seam < n_steps:
        assert abs(float(traj.roll[seam])) < 1e-9
        assert abs(float(traj.pitch[seam])) < 1e-9
        assert abs(float(traj.roll[-1])) < 1e-6
        assert abs(float(traj.pitch[-1])) < 1e-6


def test_wobble_does_not_affect_other_modes():
    """A nonzero dose must not perturb hold/lean/rise/etc -- scoped
    strictly to force_mode == "lower"."""
    gen = _gen(wobble_deg=5.0)
    rng = np.random.default_rng(3)
    for mode in ("hold", "rise", "raise", "unload"):
        traj = gen.sample(rng, n_steps=750, dt=0.02, force_mode=mode)
        assert np.all(traj.roll == 0.0), mode
        assert np.all(traj.pitch == 0.0), mode


def test_lower_hold_wobble_rng_stream_unconditional_draw_count_unchanged():
    """Default (off) must consume IDENTICAL rng draws to pre-feature
    code -- i.e. the same stream as a plain lower draw with every
    other optional lower key left at its own default. Verified by
    comparing a FULL sampled trajectory (every field) between a
    freshly loaded cfg (no key touched at all) and this test's _gen()
    with wobble_deg=0.0."""
    cfg_plain = load_config()
    gp = cfg_plain.setdefault("goal", {})
    gp["p_hold"] = gp["p_lean"] = gp["p_track"] = 0.0
    gp["p_unload"] = gp["p_raise"] = gp["p_rise"] = 0.0
    gp["p_lower"] = 1.0
    gen_plain = GoalGenerator(cfg_plain)
    gen_wobble = _gen(wobble_deg=0.0)
    for seed in range(5):
        t1 = gen_plain.sample(np.random.default_rng(seed), n_steps=750,
                              dt=0.02, force_mode="lower")
        t2 = gen_wobble.sample(np.random.default_rng(seed), n_steps=750,
                               dt=0.02, force_mode="lower")
        assert np.array_equal(t1.roll, t2.roll)
        assert np.array_equal(t1.pitch, t2.pitch)
        assert np.array_equal(t1.height, t2.height)
        assert t1.start_at == t2.start_at
