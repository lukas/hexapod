"""goal.walk_yaw_init_wz_frac/_scale -- RSI-style initial-wz curriculum
lever for the walkyaw turn-in-place freeze.

09-17, walkcurr track. `OPERATOR_QUESTIONS.md` 2026-09-17 ~20:1x (after
the GRU architecture closed the 24th agent-doable mechanism class on
this freeze) filed the design question "which structural redesign do
you sanction" and recorded an assume-and-go answer: candidate (c), "a
curriculum that starts episodes mid-rotation (nonzero wz initial
state) so tracking reward gradient exists at the policy's own a~0", as
"clearly-legal and cheapest" and "genuinely never tried on this
freeze". This is that mechanism, built the next cycle with idle
capacity and no other runnable lever on any track.

Mechanism: on a genuine turn-in-place episode (identical gating
condition as `reward.walk_turn_kernel_neutral`/
`goal.walk_turn_yaw_bias_deg`: hypot(vx_ref,vy_ref)<=1e-3,
abs(wz_ref)>1e-3), with probability `goal.walk_yaw_init_wz_frac`
(default 0.0 = OFF), the body's qvel z-angular-velocity component is
seeded to `goal.walk_yaw_init_wz_scale * wz_ref` (sign-matched to the
command) right after the ordinary reset settle, followed by one more
real physics tick so the gyro/IMU accumulators read a fresh, physically
consistent sample. No teacher/demonstration/scripted controller is
involved anywhere -- a raw physics-state (qvel) assignment seeded from
a SCALAR (the episode's own command), not a motion clip.

The one extra tick is a FULL control tick (``_settle(self.dt)`` ==
``self._substeps`` real ``mj_step`` calls, same physics resolution as
any other tick): with all six feet planted, ground-contact friction
damps a chunk of the injected spin within that single tick (measured:
~40 % of `scale*wz_ref` survives for the tested seed/dose) -- expected,
not a bug (matches the intent that a genuinely free-standing body would
resist an externally-imposed spin exactly this way), so the seeded
tests assert direction + "clearly above the settle noise floor", not
an exact pre-damping number.

Contract under test (CPU env, `sim_env._apply_walk_yaw_init_wz`):
  - default (both keys absent/0) never touches qvel: a genuine
    turn-in-place reset settles to the same near-zero body wz noise
    floor with or without the key present;
  - frac=1.0, scale=0.5 on a genuine turn-in-place goal seeds
    qvel[5] to a clearly nonzero, correctly-signed value well above
    the settle noise floor;
  - a non-turn-in-place goal (forward walk, or wz_ref=0) never gets
    seeded regardless of how the keys are armed;
  - frac=0.0 with scale!=0 (or scale=0.0 with frac!=0) is still fully
    OFF -- both gates must clear.
"""
from __future__ import annotations

import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.walk_task import SimHexapodJointWalkEnv, WalkGoal

# Settle-noise floor observed on this env/model (six planted feet,
# quiet stand): real but small (contact micro-dither), always well
# under 1e-3 rad/s -- the "off" assertions use this as their ceiling.
_NOISE_CEILING = 1e-3
# A seeded turn-in-place tick clears this floor by 1-2 orders of
# magnitude even after one tick's worth of ground-friction damping.
_SEEDED_FLOOR = 1e-2


def _env(frac=0.0, scale=0.0, seed=0):
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_yaw_cmd"] = 1
    if frac:
        goal["walk_yaw_init_wz_frac"] = frac
    if scale:
        goal["walk_yaw_init_wz_scale"] = scale
    env = SimHexapodJointWalkEnv(cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_walk = 1.0
    env.reset()
    return env


def _force_goal_and_reset(env, vx_ref=0.0, vy_ref=0.0, wz_ref=0.0):
    env._current_goal = lambda: WalkGoal(
        roll_ref=0.0, pitch_ref=0.0, height_ref=0.0, unload_leg=None,
        lift_legs=None, vx_ref=vx_ref, vy_ref=vy_ref, wz_ref=wz_ref)
    env.reset()


def test_default_off_never_seeds_qvel():
    env = _env()
    _force_goal_and_reset(env, wz_ref=0.27)
    assert abs(env.data.qvel[5]) < _NOISE_CEILING


def test_armed_frac_zero_still_off():
    # scale alone, frac left at its own default (0.0): both gates must
    # clear -- frac is checked FIRST and short-circuits.
    env = _env(frac=0.0, scale=0.9)
    _force_goal_and_reset(env, wz_ref=0.27)
    assert abs(env.data.qvel[5]) < _NOISE_CEILING


def test_armed_scale_zero_still_off():
    env = _env(frac=1.0, scale=0.0)
    _force_goal_and_reset(env, wz_ref=0.27)
    assert abs(env.data.qvel[5]) < _NOISE_CEILING


def test_turn_in_place_gets_seeded_positive():
    env = _env(frac=1.0, scale=0.5)
    _force_goal_and_reset(env, wz_ref=0.27)
    assert env.data.qvel[5] > _SEEDED_FLOOR


def test_negative_command_seeds_negative_wz():
    env = _env(frac=1.0, scale=0.5)
    _force_goal_and_reset(env, wz_ref=-0.27)
    assert env.data.qvel[5] < -_SEEDED_FLOOR


def test_forward_walk_goal_never_seeded_even_when_armed():
    env = _env(frac=1.0, scale=0.5)
    _force_goal_and_reset(env, vx_ref=0.06, vy_ref=0.0, wz_ref=0.0)
    assert abs(env.data.qvel[5]) < _NOISE_CEILING


def test_zero_wz_goal_never_seeded_even_when_armed():
    env = _env(frac=1.0, scale=0.5)
    _force_goal_and_reset(env, vx_ref=0.0, vy_ref=0.0, wz_ref=0.0)
    assert abs(env.data.qvel[5]) < _NOISE_CEILING


def test_combined_linear_and_yaw_command_never_seeded():
    # hypot(vx_ref, vy_ref) > 1e-3 disqualifies even with a real wz_ref
    # -- matches the turn-in-place gating everywhere else in this file.
    env = _env(frac=1.0, scale=0.5)
    _force_goal_and_reset(env, vx_ref=0.03, vy_ref=0.0, wz_ref=0.27)
    assert abs(env.data.qvel[5]) < _NOISE_CEILING


def test_frac_gates_the_rng_draw_not_just_the_outcome():
    # frac just below 1.0 with a fixed seed still must be able to
    # select (this is a smoke check that the draw path is live, not
    # that a specific seed always wins -- scanning a few seeds so the
    # test isn't sensitive to exactly which seed's rng stream selects
    # first).
    hits = 0
    for seed in range(6):
        env = _env(frac=0.5, scale=0.5, seed=seed)
        _force_goal_and_reset(env, wz_ref=0.27)
        if env.data.qvel[5] > _SEEDED_FLOOR:
            hits += 1
    assert 0 < hits < 6
