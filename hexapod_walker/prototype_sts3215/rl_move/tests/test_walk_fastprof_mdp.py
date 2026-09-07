"""Fast-profile command-tracking MDP prep (08-20, operator note
fb_20260820T000059 item 3 — pre-launch code for any funded fast-gait
run; the steer5-fastprof1 canary showed every checkpoint overruns a
0.05-0.06 m/s command 2.5x and drifts 50-60 deg off heading under the
raised servo profile):

  - reward.k_walk_overspeed / walk_overspeed_tol (walk_task): opt-in
    charge on commanded-band EXCEEDANCE (not progress shortfall) —
    -k * min(over/s_ref, 3), over = max(0, |v| - (1+tol)*s_ref).
  - reward.k_walk_heading / walk_heading_min_speed_m_s: opt-in charge
    -k * (1 - cos(heading error)) on ticks actually moving.
  - goal.walk_obs_body_vel=3: DEPLOYABLE leg-odometry estimator obs
    (rl_move.estimator.LegOdometryVelocity on the DR-corrupted observed
    state). Before 08-20 a cfg value of 3 silently fell into the
    PRIVILEGED branch; mode 2 (the cw-dep contract) carries zero
    body-velocity information by construction.
  - eval_checkpoint.pinned_speed_cfg: the pinned-speed panel's command
    pinning must actually pin (speed exact, pure forward, no resample).

All default-off; the default path must stay bit-exact (no new info
keys, same rewards). Fast (~seconds): short episodes, scripted or
forced velocities, no PPO.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control",
           ROOT / "linux_control" / "urt2_setup"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

pytest.importorskip("mujoco")

from rl_move.config import load_config  # noqa: E402
from rl_move.sim.servo_model import SimServoParams  # noqa: E402

CMD = 0.05
NEW_INFO_KEYS = ("reward_walk_overspeed", "walk_overspeed_m_s",
                 "reward_walk_heading", "walk_heading_cos")
HEIGHT_INFO_KEYS = (
    "reward_foot_slip_height",
    "walk_height_quasi_planted_feet",
    "walk_height_slip_vel_mean_m_s",
    "walk_height_slip_vel_max_m_s",
)
SLIP_INFO_KEYS = (
    "reward_foot_slip_tangent",
    "walk_contact_feet",
    "walk_contact_meaningful_feet",
    "walk_tangent_contact_vel_mean_m_s",
    "walk_tangent_contact_vel_max_m_s",
    "walk_touchdown_count",
    "walk_liftoff_count",
    "walk_swinging_feet",
)


def _walk_env(extra=None, seed=0, episode_seconds=6.0):
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = load_config()
    for (sec, leaf), val in (extra or {}).items():
        cfg.setdefault(sec, {})[leaf] = val
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=False,
        dr_scale=0.0, episode_seconds=episode_seconds, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env


def _pin_forward(env, speed=CMD):
    """Constant forward command from tick 0 (no hold/ramp)."""
    traj = env._goal_traj
    traj.vx[:] = speed
    traj.vy[:] = 0.0
    if getattr(traj, "wz", None) is not None:
        traj.wz[:] = 0.0


def _force_vel(env, vx, vy):
    env._body_vel_xy = lambda: np.array([vx, vy], dtype=float)


def _step_info(env):
    act = np.zeros(env.action_space.shape, dtype=np.float32)
    _obs, r, _term, _trunc, info = env.step(act)
    return float(r), info


def _prime_slip_latches(env, offset_m=0.02, prev_force=10.0):
    """Seed previous planted-foot positions without perturbing physics."""
    current_contacts = 0
    for f, bid in enumerate(env._pad_bids):
        adr = env._touch_adr[f]
        force = (float(env.data.sensordata[adr]) if adr >= 0 else 0.0)
        current_contacts += int(force > 0.5)
        xy = env.data.xpos[bid, :2]
        env._foot_prev_xy[f] = xy - np.array([offset_m, 0.0])
        env._foot_prev_force[f] = prev_force
        env._foot_on[f] = True
    assert current_contacts > 0, "probe expects at least one planted foot"


def _prime_height_latches(env, offset_m=0.02, thresh_m=0.006):
    """Seed previous quasi-planted-foot positions for the CONTACT-
    INDEPENDENT height-gated mechanism (_lsh_prev_xy/_lsh_prev_planted)
    -- mirrors _prime_slip_latches above but for
    reward.k_foot_slip_height, which reads kinematic ground clearance
    against _pad_z_ref and never touches self.data.sensordata/
    _touch_adr at all."""
    count = 0
    for f, bid in enumerate(env._pad_bids):
        z_ref = env._pad_z_ref[f] if env._pad_z_ref is not None else 0.0
        clearance = float(env.data.xpos[bid, 2]) - z_ref
        if clearance < thresh_m:
            count += 1
        xy = env.data.xpos[bid, :2]
        env._lsh_prev_xy[f] = xy - np.array([offset_m, 0.0])
        env._lsh_prev_planted[f] = True
    assert count > 0, "probe expects at least one quasi-planted foot"


# ------------------------------------------------------------------ #
# default-off bit-exactness
# ------------------------------------------------------------------ #

def test_default_off_emits_no_new_keys_and_matches_zero_k():
    env_a = _walk_env(seed=3)
    env_b = _walk_env(seed=3, extra={
        ("reward", "k_walk_overspeed"): 0.0,
        ("reward", "k_walk_heading"): 0.0,
        ("reward", "k_foot_slip_tangent"): 0.0,
        ("goal", "walk_contact_diagnostics"): 0.0,
    })
    env_a.reset()
    env_b.reset()
    _pin_forward(env_a)
    _pin_forward(env_b)
    for _ in range(10):
        ra, ia = _step_info(env_a)
        rb, ib = _step_info(env_b)
        assert ra == pytest.approx(rb, abs=0.0)
        for k in NEW_INFO_KEYS:
            assert k not in ia and k not in ib
        for k in SLIP_INFO_KEYS:
            assert k not in ia and k not in ib
    env_a.close()
    env_b.close()


def test_action_space_stays_raw_18_joint_targets():
    env = _walk_env()
    assert env.action_space.shape == (18,)
    env.close()


# ------------------------------------------------------------------ #
# planted-foot tangent slip charge + diagnostics
# ------------------------------------------------------------------ #

def test_contact_diagnostics_emit_without_reward_charge():
    env = _walk_env(extra={("goal", "walk_contact_diagnostics"): 1.0})
    env.reset()
    _pin_forward(env)
    _r, info = _step_info(env)
    assert "reward_foot_slip_tangent" not in info
    for k in SLIP_INFO_KEYS[1:]:
        assert k in info
    for f in range(6):
        assert f"walk_foot{f}_contact" in info
        assert f"walk_foot{f}_contact_force" in info
        assert f"walk_foot{f}_tangent_vel_m_s" in info
        assert f"walk_foot{f}_tangent_slip_m_total" in info
        assert f"walk_foot{f}_swinging" in info
    env.close()


def test_foot_slip_tangent_reduces_return_modestly_when_contact_slides():
    """Same physics, k on vs off: only the new slip charge separates."""
    extra_on = {
        ("reward", "k_foot_slip_tangent"): 0.05,
        ("reward", "foot_slip_contact_n"): 0.0,
        ("reward", "foot_slip_deadband_m_s"): 0.0,
        ("reward", "foot_slip_max_m_s"): 0.25,
    }
    env_on = _walk_env(seed=7, extra=extra_on)
    env_off = _walk_env(seed=7, extra={
        ("reward", "k_foot_slip_tangent"): 0.0,
        ("reward", "foot_slip_contact_n"): 0.0,
        ("reward", "foot_slip_deadband_m_s"): 0.0,
        ("reward", "foot_slip_max_m_s"): 0.25,
    })
    for env in (env_on, env_off):
        env.reset()
        _pin_forward(env)
        _prime_slip_latches(env)
    r_on, i_on = _step_info(env_on)
    r_off, _i_off = _step_info(env_off)
    assert i_on["reward_foot_slip_tangent"] < 0.0
    assert i_on["reward_foot_slip_tangent"] >= -0.05 * 0.25
    assert r_on - r_off == pytest.approx(
        i_on["reward_foot_slip_tangent"], abs=1e-6)
    env_on.close()
    env_off.close()


def test_foot_slip_tangent_requires_meaningful_current_contact():
    env = _walk_env(extra={
        ("reward", "k_foot_slip_tangent"): 0.05,
        ("reward", "foot_slip_contact_n"): 1e9,
        ("reward", "foot_slip_deadband_m_s"): 0.0,
        ("reward", "foot_slip_max_m_s"): 0.25,
    })
    env.reset()
    _pin_forward(env)
    _prime_slip_latches(env, prev_force=1e9)
    _r, info = _step_info(env)
    assert info["reward_foot_slip_tangent"] == pytest.approx(0.0)
    assert info["walk_contact_meaningful_feet"] == pytest.approx(0.0)
    env.close()


# ------------------------------------------------------------------ #
# CONTACT-INDEPENDENT foot-slip-height charge (walkcurr item(4),
# 2026-09-06 follow-up to the CLOSED tangent-contact lever: 4
# independently-designed doses/accountings of the touch-sensor-gated
# mechanism above all read within ~0-8% of the champion's 5.065 slip/m
# baseline, see rl_docs/tracks/walkcurr/STATUS.md 09-06 ~19:1x..~22:4x.
# reward.k_foot_slip_height (walk_task.py) never reads
# self.data.sensordata/_touch_adr: a foot is "quasi-planted" purely
# from kinematic ground clearance against the already-proven _pad_z_ref
# reference (same primitive the rise/lower posture gates use), with
# its own independent prev-XY/gate latch (_lsh_prev_xy/
# _lsh_prev_planted). Default 0.0 = off, bit-exact.
# ------------------------------------------------------------------ #

def test_foot_slip_height_default_off_is_bit_exact():
    """k_foot_slip_height=0.0 (the default) must emit none of its new
    info keys and leave the reward untouched, even with the tangent
    lever's own knobs exercised on the same tick (proves the new
    mechanism's insertion point does not perturb the pre-existing
    tangent-charge code path)."""
    tangent_extra = {
        ("reward", "k_foot_slip_tangent"): 0.05,
        ("reward", "foot_slip_contact_n"): 0.0,
        ("reward", "foot_slip_deadband_m_s"): 0.0,
        ("reward", "foot_slip_max_m_s"): 0.25,
    }
    off_extra = dict(tangent_extra)
    off_extra[("reward", "k_foot_slip_height")] = 0.0
    env_a = _walk_env(seed=9, extra=tangent_extra)
    env_b = _walk_env(seed=9, extra=off_extra)
    for env in (env_a, env_b):
        env.reset()
        _pin_forward(env)
        _prime_slip_latches(env)
    r_a, i_a = _step_info(env_a)
    r_b, i_b = _step_info(env_b)
    assert r_a == pytest.approx(r_b, abs=0.0)
    for k in HEIGHT_INFO_KEYS:
        assert k not in i_a and k not in i_b
    env_a.close()
    env_b.close()


def test_foot_slip_height_reduces_return_when_quasi_planted_foot_slides():
    """Same physics, k on vs off: only the new height-gated charge
    separates -- mirrors
    test_foot_slip_tangent_reduces_return_modestly_when_contact_slides
    but primed via the kinematic latch, not the contact-sensor one."""
    extra_on = {
        ("reward", "k_foot_slip_height"): 0.05,
        ("reward", "foot_slip_height_deadband_m_s"): 0.0,
        ("reward", "foot_slip_height_max_m_s"): 0.25,
    }
    env_on = _walk_env(seed=7, extra=extra_on)
    env_off = _walk_env(seed=7, extra={
        ("reward", "k_foot_slip_height"): 0.0,
        ("reward", "foot_slip_height_deadband_m_s"): 0.0,
        ("reward", "foot_slip_height_max_m_s"): 0.25,
    })
    for env in (env_on, env_off):
        env.reset()
        _pin_forward(env)
        _prime_height_latches(env)
    r_on, i_on = _step_info(env_on)
    r_off, _i_off = _step_info(env_off)
    assert i_on["reward_foot_slip_height"] < 0.0
    assert i_on["reward_foot_slip_height"] >= -0.05 * 0.25
    assert r_on - r_off == pytest.approx(
        i_on["reward_foot_slip_height"], abs=1e-6)
    env_on.close()
    env_off.close()


def test_foot_slip_height_ignores_real_swing_clearance():
    """A foot with real kinematic clearance at or above the threshold
    (an ordinary lifted/swinging foot, not a forced-latch artifact)
    must never be charged: force fsh_thresh_m deeply negative (no
    foot's live clearance can ever read below -1m), so every foot's
    live clearance this tick reads NOT-quasi-planted and the charge
    must stay exactly zero even with a large injected latch offset."""
    env = _walk_env(seed=11, extra={
        ("reward", "k_foot_slip_height"): 0.05,
        ("reward", "foot_slip_height_thresh_m"): -1.0,
        ("reward", "foot_slip_height_deadband_m_s"): 0.0,
        ("reward", "foot_slip_height_max_m_s"): 0.25,
    })
    env.reset()
    _pin_forward(env)
    for f, bid in enumerate(env._pad_bids):
        xy = env.data.xpos[bid, :2]
        env._lsh_prev_xy[f] = xy - np.array([0.05, 0.0])
        env._lsh_prev_planted[f] = True
    _r, info = _step_info(env)
    assert info["reward_foot_slip_height"] == pytest.approx(0.0)
    assert info["walk_height_quasi_planted_feet"] == pytest.approx(0.0)
    env.close()


def test_foot_slip_height_charges_despite_tangent_contact_n_blind_spot():
    """Direct proof of independence: the SAME contact-force threshold
    that makes the tangent lever blind to a real, firmly-planted foot
    (foot_slip_contact_n=1e9, exactly
    test_foot_slip_tangent_requires_meaningful_current_contact's own
    setup just above) never even applies to the height-gated lever --
    it reads no contact-sensor/force/`meaningful` state whatsoever.
    Both mechanisms armed on the SAME physics/seed/tick, so this is a
    like-for-like comparison, not a coincidence of different envs."""
    env = _walk_env(seed=13, extra={
        ("reward", "k_foot_slip_tangent"): 0.05,
        ("reward", "foot_slip_contact_n"): 1e9,
        ("reward", "foot_slip_deadband_m_s"): 0.0,
        ("reward", "foot_slip_max_m_s"): 0.25,
        ("reward", "k_foot_slip_height"): 0.05,
        ("reward", "foot_slip_height_deadband_m_s"): 0.0,
        ("reward", "foot_slip_height_max_m_s"): 0.25,
    })
    env.reset()
    _pin_forward(env)
    _prime_slip_latches(env, prev_force=1e9)
    _prime_height_latches(env)
    _r, info = _step_info(env)
    assert info["reward_foot_slip_tangent"] == pytest.approx(0.0), (
        "setup check: the tangent lever must be blind here, matching "
        f"test_foot_slip_tangent_requires_meaningful_current_contact: "
        f"{info}")
    assert info["walk_contact_meaningful_feet"] == pytest.approx(0.0)
    assert info["reward_foot_slip_height"] < 0.0, (
        f"height-gated charge did not fire despite the SAME physics "
        f"where the contact-gated lever is structurally blind: {info}")
    env.close()


# ------------------------------------------------------------------ #
# overspeed charge semantics (forced velocity — exact operating points)
# ------------------------------------------------------------------ #

def test_overspeed_charge_zero_in_band_and_linear_beyond():
    env = _walk_env(extra={("reward", "k_walk_overspeed"): 2.0})
    env.reset()
    _pin_forward(env)

    _force_vel(env, CMD, 0.0)             # perfect tracking
    _r, info = _step_info(env)
    assert info["walk_overspeed_m_s"] == pytest.approx(0.0)
    assert "reward_walk_overspeed" not in info

    _force_vel(env, 1.05 * CMD, 0.0)      # inside the 10% band
    _r, info = _step_info(env)
    assert info["walk_overspeed_m_s"] == pytest.approx(0.0)
    assert "reward_walk_overspeed" not in info

    _force_vel(env, 0.14, 0.0)            # the canary's overshoot
    _r, info = _step_info(env)
    over = 0.14 - 1.10 * CMD
    assert info["walk_overspeed_m_s"] == pytest.approx(over, abs=1e-9)
    assert info["reward_walk_overspeed"] == pytest.approx(
        -2.0 * min(over / CMD, 3.0), abs=1e-9)

    _force_vel(env, 0.50, 0.0)            # absurd — cap must bound it
    _r, info = _step_info(env)
    assert info["reward_walk_overspeed"] == pytest.approx(-6.0)
    env.close()


def test_overspeed_reward_actually_reduces_return():
    """Same forced velocity, k on vs off: the charge lands in reward."""
    env_on = _walk_env(extra={("reward", "k_walk_overspeed"): 2.0})
    env_off = _walk_env()
    for env in (env_on, env_off):
        env.reset()
        _pin_forward(env)
        _force_vel(env, 0.14, 0.0)
    r_on, i_on = _step_info(env_on)
    r_off, i_off = _step_info(env_off)
    assert r_on < r_off - 1.0
    assert r_on - r_off == pytest.approx(
        i_on["reward_walk_overspeed"], abs=1e-6)
    env_on.close()
    env_off.close()


# ------------------------------------------------------------------ #
# heading-error charge semantics
# ------------------------------------------------------------------ #

def test_heading_charge_zero_aligned_scales_with_angle():
    env = _walk_env(extra={("reward", "k_walk_heading"): 2.0})
    env.reset()
    _pin_forward(env)

    _force_vel(env, CMD, 0.0)             # aligned
    _r, info = _step_info(env)
    assert info["walk_heading_cos"] == pytest.approx(1.0)
    assert info["reward_walk_heading"] == pytest.approx(0.0, abs=1e-12)

    c45 = CMD * np.cos(np.radians(45)), CMD * np.sin(np.radians(45))
    _force_vel(env, *c45)                 # 45 deg off
    _r, info = _step_info(env)
    r45 = info["reward_walk_heading"]
    assert r45 == pytest.approx(-2.0 * (1 - np.cos(np.radians(45))),
                                abs=1e-9)

    _force_vel(env, 0.0, CMD)             # 90 deg off — worse
    _r, info = _step_info(env)
    assert info["reward_walk_heading"] < r45
    assert info["reward_walk_heading"] == pytest.approx(-2.0, abs=1e-9)
    env.close()


def test_heading_charge_skips_near_stationary_ticks():
    env = _walk_env(extra={("reward", "k_walk_heading"): 2.0})
    env.reset()
    _pin_forward(env)
    _force_vel(env, 0.0, 0.005)           # below 0.01 m/s floor
    _r, info = _step_info(env)
    assert "reward_walk_heading" not in info
    env.close()


def test_charges_skip_stop_segments():
    env = _walk_env(extra={("reward", "k_walk_overspeed"): 2.0,
                           ("reward", "k_walk_heading"): 2.0})
    env.reset()
    _pin_forward(env, speed=0.0)          # commanded stop
    _force_vel(env, 0.10, 0.0)            # creeping through it
    _r, info = _step_info(env)
    for k in NEW_INFO_KEYS:
        assert k not in info
    env.close()


# ------------------------------------------------------------------ #
# estimator-sourced velocity obs (goal.walk_obs_body_vel=3)
# ------------------------------------------------------------------ #

def test_vel_obs_mode3_feeds_estimator_output():
    from rl_move.sim.walk_task import VEL_SCALE
    env = _walk_env(extra={("goal", "walk_obs_body_vel"): 3.0,
                           ("obs", "history_frames"): 1.0})
    obs, _ = env.reset()
    assert env._vel_est is not None
    # Velocity slots sit right after the base frame; with every other
    # optional tail off they are the last two dims.
    assert obs[-2:] == pytest.approx([0.0, 0.0])   # fresh estimator
    _pin_forward(env)

    seen = []
    orig = env._vel_est.update

    def rec(*a, **kw):
        out = orig(*a, **kw)
        seen.append(np.array(out, dtype=float))
        return out

    env._vel_est.update = rec
    act = np.zeros(env.action_space.shape, dtype=np.float32)
    for _ in range(8):
        obs, _r, term, trunc, _info = env.step(act)
        assert not (term or trunc)
        assert obs[-2:] == pytest.approx(seen[-1] / VEL_SCALE)
    env.close()


def test_vel_obs_mode3_differs_from_privileged_and_keeps_width():
    ex = {("obs", "history_frames"): 1.0}
    env1 = _walk_env(extra={("goal", "walk_obs_body_vel"): 1.0, **ex},
                     seed=5)
    env3 = _walk_env(extra={("goal", "walk_obs_body_vel"): 3.0, **ex},
                     seed=5)
    o1, _ = env1.reset()
    o3, _ = env3.reset()
    assert o1.shape == o3.shape           # warm-start compatible width
    _pin_forward(env1)
    _pin_forward(env3)
    act = np.zeros(env1.action_space.shape, dtype=np.float32)
    d = 0.0
    for _ in range(12):
        o1 = env1.step(act)[0]
        o3 = env3.step(act)[0]
        # identical seeds/actions -> same physics; only the velocity
        # slots' SOURCE differs, everything else identical.
        assert o1[:-2] == pytest.approx(o3[:-2], abs=1e-6)
        d = max(d, float(np.max(np.abs(o1[-2:] - o3[-2:]))))
    assert d > 0.0                        # estimator is not privileged
    env1.close()
    env3.close()


def test_vel_obs_mode3_resets_between_episodes():
    env = _walk_env(extra={("goal", "walk_obs_body_vel"): 3.0,
                           ("obs", "history_frames"): 1.0},
                    episode_seconds=1.0)
    env.reset()
    est_first = env._vel_est
    act = np.zeros(env.action_space.shape, dtype=np.float32)
    for _ in range(30):
        _obs, _r, term, trunc, _info = env.step(act)
        if term or trunc:
            break
    obs, _ = env.reset()
    assert env._vel_est is not est_first  # fresh per episode
    assert obs[-2:] == pytest.approx([0.0, 0.0])
    env.close()


# ------------------------------------------------------------------ #
# pinned-speed panel command pinning
# ------------------------------------------------------------------ #

def test_pinned_speed_cfg_pins_the_sampled_command():
    from rl_move.sim.eval_checkpoint import (PINNED_SPEED_DEFAULTS,
                                             pinned_speed_cfg)
    assert PINNED_SPEED_DEFAULTS == (0.04, 0.06, 0.08, 0.10)
    for speed in (0.04, 0.10):
        extra = {("goal", k): v
                 for k, v in pinned_speed_cfg(speed).items()}
        env = _walk_env(extra=extra, seed=7)
        env.reset()
        traj = env._goal_traj
        late = slice(int(2.5 / env.dt), None)   # past hold+ramp
        assert np.allclose(traj.vx[late], speed, atol=1e-12)
        assert np.allclose(traj.vy[late], 0.0, atol=1e-12)
        if getattr(traj, "wz", None) is not None:
            assert np.allclose(traj.wz[late], 0.0, atol=1e-12)
        env.close()


def test_pinned_speed_cfg_is_applyable_to_a_live_env():
    """The panel mutates a LIVE env's cfg between episodes; the next
    sampled episode must obey the new pin (sample-time keys only)."""
    from rl_move.sim.eval_checkpoint import pinned_speed_cfg
    env = _walk_env(seed=9)
    env.reset()
    for k, val in pinned_speed_cfg(0.08).items():
        env.cfg.setdefault("goal", {})[k] = val
    env.reset()
    traj = env._goal_traj
    late = slice(int(2.5 / env.dt), None)
    assert np.allclose(traj.vx[late], 0.08, atol=1e-12)
    assert np.allclose(traj.vy[late], 0.0, atol=1e-12)
    env.close()


# ------------------------------------------------------------------ #
# direct loaded-slip excess penalty (reward.k_loadslip_excess —
# operator order fb_20260820T075230_4a90c6, fast anti-skate V5: the
# loadslip GATE only zeroes income; skating must be CHARGED)
# ------------------------------------------------------------------ #

LSE_OK_DEFAULT = 0.75   # reward.loadslip_ok default


def test_loadslip_excess_default_off_is_bit_exact():
    env_a = _walk_env(seed=11)
    env_b = _walk_env(seed=11, extra={
        ("reward", "k_loadslip_excess"): 0.0,
    })
    for env in (env_a, env_b):
        env.reset()
        _pin_forward(env)
    for _ in range(8):
        ra, ia = _step_info(env_a)
        rb, ib = _step_info(env_b)
        assert ra == pytest.approx(rb, abs=0.0)
        assert "reward_loadslip_excess" not in ia
        assert "reward_loadslip_excess" not in ib
    env_a.close()
    env_b.close()


def test_loadslip_excess_charges_ratio_above_ok_only():
    env = _walk_env(seed=12, extra={
        ("reward", "k_loadslip_excess"): 6.0,
        ("reward", "loadslip_ok"): 1.2,
    })
    env.reset()
    _pin_forward(env)
    _step_info(env)                      # warm one tick (prev-contact)

    # clean walking: accumulated ratio far below loadslip_ok -> 0
    env._ls_slip_m, env._ls_prog_m = 0.01, 0.50
    _r, info = _step_info(env)
    assert info["walk_loadslip_ratio"] < 1.2
    assert info["reward_loadslip_excess"] == pytest.approx(0.0)

    # skating: ratio ~3 -> pays k * (ratio - ok) * dt this tick,
    # exactly (dt-scaled like every other per-second reward charge in
    # this file, e.g. c_time -- 2026-08-20 q_20260820T0830Z realign to
    # match the authored desktop commit 2cb2a7b7).
    env._ls_slip_m, env._ls_prog_m = 0.30, 0.10
    _r, info = _step_info(env)
    ratio = info["walk_loadslip_ratio"]
    assert ratio > 1.2
    assert info["reward_loadslip_excess"] == pytest.approx(
        -6.0 * (ratio - 1.2) * env.dt, abs=1e-9)
    env.close()


def test_loadslip_excess_actually_reduces_return():
    """Same forced accumulators, k on vs off: the charge lands in
    reward (skating is punished, not merely income-gated)."""
    env_on = _walk_env(seed=13, extra={
        ("reward", "k_loadslip_excess"): 6.0,
        ("reward", "loadslip_ok"): 1.2,
    })
    env_off = _walk_env(seed=13)
    for env in (env_on, env_off):
        env.reset()
        _pin_forward(env)
        _step_info(env)
        env._ls_slip_m, env._ls_prog_m = 0.30, 0.10
    r_on, i_on = _step_info(env_on)
    r_off, i_off = _step_info(env_off)
    assert i_on["walk_loadslip_ratio"] == pytest.approx(
        i_off["walk_loadslip_ratio"], abs=1e-9)
    assert r_on < r_off
    assert r_on - r_off == pytest.approx(
        i_on["reward_loadslip_excess"], abs=1e-6)
    env_on.close()
    env_off.close()


# ------------------------------------------------------------------ #
# windowed (EMA) loadslip ratio (reward.walk_loadslip_window_s,
# 2026-09-06 walkcurr item(4) follow-up to the `loadslip-c1` canary
# FAIL -- see walk_task.py's own comment at the walk_loadslip_gate
# block for the full rationale: the episode-cumulative ratio above is
# diluted by however much clean history precedes the current tick, so
# a late-episode skate can hide behind an early-episode clean stretch
# for many ticks before the ratio catches up. Default 0.0 = OFF, must
# stay bit-exact (no new info keys, same rewards, same
# walk_loadslip_ratio formula) -- checked first, before the
# responsiveness claim.
# ------------------------------------------------------------------ #

def _prime_loadslip_latch(env, offset_m=0.05):
    """Seed the loadslip previous-contact XY so the NEXT tick's foot
    movement reads as one large injected slip, without perturbing
    physics -- mirrors _prime_slip_latches (the tangent-charge
    mechanism's own latch-priming helper) but for the
    walk_loadslip_gate/window bookkeeping (_ls_prev_xy/_ls_prev_on)."""
    current_contacts = 0
    for f, bid in enumerate(env._pad_bids):
        adr = env._touch_adr[f]
        force = (float(env.data.sensordata[adr]) if adr >= 0 else 0.0)
        on = force > 0.5
        current_contacts += int(on)
        xy = env.data.xpos[bid, :2]
        env._ls_prev_xy[f] = xy - np.array([offset_m, 0.0])
        env._ls_prev_on[f] = True
    assert current_contacts > 0, "probe expects at least one planted foot"


def test_loadslip_window_default_off_is_bit_exact():
    """window_s=0.0 (the default) must reproduce the legacy episode-
    cumulative ratio exactly -- no new info key, same reward, even
    after the mechanism has been exercised by a forced accumulator
    state (matches test_loadslip_excess_charges_ratio_above_ok_only's
    own forced values so this is a real like-for-like comparison, not
    just an untouched-mechanism check)."""
    env_a = _walk_env(seed=21, extra={
        ("reward", "walk_loadslip_gate"): 1.0,
        ("reward", "loadslip_ok"): 1.2,
        ("reward", "loadslip_max"): 3.0,
    })
    env_b = _walk_env(seed=21, extra={
        ("reward", "walk_loadslip_gate"): 1.0,
        ("reward", "loadslip_ok"): 1.2,
        ("reward", "loadslip_max"): 3.0,
        ("reward", "walk_loadslip_window_s"): 0.0,
    })
    for env in (env_a, env_b):
        env.reset()
        _pin_forward(env)
        _step_info(env)
        env._ls_slip_m, env._ls_prog_m = 0.30, 0.10
    ra, ia = _step_info(env_a)
    rb, ib = _step_info(env_b)
    assert ra == pytest.approx(rb, abs=0.0)
    assert ia["walk_loadslip_ratio"] == pytest.approx(
        ib["walk_loadslip_ratio"], abs=0.0)
    assert "walk_loadslip_ratio_cumulative" not in ia
    assert "walk_loadslip_ratio_cumulative" not in ib
    env_a.close()
    env_b.close()


def test_loadslip_window_ratio_reacts_faster_than_cumulative():
    """The core claim: with an identical long, perfectly clean
    walking HISTORY (lots of accumulated progress, negligible
    accumulated slip) baked into both envs, injecting ONE large slip
    tick must move the windowed ratio sharply while the episode-
    cumulative ratio stays diluted near zero -- exactly the
    unresponsiveness the `loadslip-c1` canary's FAIL verdict
    diagnosed (env/walk_loadslip_ratio bounced 6.28->7.88->7.11->6.87
    across 4 quarters, no clean downtrend despite a bank-proven
    dose)."""
    env_cum = _walk_env(seed=22, extra={
        ("reward", "walk_loadslip_gate"): 0.0,
    })
    env_win = _walk_env(seed=22, extra={
        ("reward", "walk_loadslip_gate"): 0.0,
        ("reward", "walk_loadslip_window_s"): 0.5,
    })
    for env in (env_cum, env_win):
        env.reset()
        _pin_forward(env)
        _step_info(env)  # warm one tick (prev-contact latches)
        # Long clean-walking history: lots of accumulated progress,
        # negligible accumulated slip.
        env._ls_slip_m, env._ls_prog_m = 0.05, 50.0
    # The windowed env's EMA is the windowed analogue of that same
    # clean-walking history: already settled at the clean-walk rate.
    env_win._ls_slip_ema, env_win._ls_prog_ema = 0.0, CMD

    for env in (env_cum, env_win):
        _prime_loadslip_latch(env, offset_m=0.05)
    _r_cum, i_cum = _step_info(env_cum)
    _r_win, i_win = _step_info(env_win)

    assert i_cum["walk_loadslip_ratio"] < 0.05, (
        "control check: the cumulative ratio should still read near-"
        f"zero, diluted by its 50m clean history: {i_cum}")
    assert i_win["walk_loadslip_ratio"] > i_cum["walk_loadslip_ratio"] * 5, (
        "windowed ratio does not react faster than the diluted "
        f"cumulative ratio: cumulative={i_cum['walk_loadslip_ratio']} "
        f"windowed={i_win['walk_loadslip_ratio']}")
    env_cum.close()
    env_win.close()


    # NOTE: a "settles low under real clean walking" sanity check
    # belongs in test_task_semantics.py's WALKCURR_ITEM4_LOADSLIP_
    # WINDOWED bank, not here -- this file's `_step_info` drives the
    # env with a constant ZERO action (isolates the reward-accounting
    # math from any actual gait), so there is no real walking
    # behavior here to settle against; a real scripted-tripod-gait
    # rollout is required for that property and test_task_semantics.py
    # already has the TripodGait rollout machinery this needs.
