"""Tipped-start spawn headroom (dig-in 2026-09-23, hardstartcorr plateau).

Root cause pinned that cycle: the tipped-start fold->roll gain (shared
TIP_ROLL_PER_FOLD=0.36) overshoots ~1.33x at the current plant stance on
both model families, so a capped 7-deg target settled at 9-11 deg — inside
the 10-deg tilt_roll trip band — making ~30-40% of max-dose tipped plant
spawns unwinnable regardless of policy (terminated 0.76-1.0 s post-reset
under an idealized instant level command; 10/13 compound plant spawns
failed across the GRU dr04 / MLP dr06 owncfg evals). The fix gives the
tipped-start path its own measured gain (TIPPED_START_ROLL_PER_FOLD) so
achieved roll ~= sampled target, restoring the method's documented
invariant: spawn at <=0.7 x max_roll with recovery headroom, never
mid-trip.

Mechanics-only, mesh model, no artifacts (RESEARCH_RULES "Tests").
"""
import numpy as np

from rl_move.config import load_config
from rl_move.sim.joint_task import SimHexapodJointGoalEnv
from rl_move.sim.servo_model import SimServoParams

RAD2DEG = 180.0 / np.pi


def _make_env(seed, monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    cfg = load_config()
    ov = {("control", "hz"): 50,
          ("dr", "tipped_start_prob"): 2.5,      # x0.4 scale -> 1.0
          ("dr", "tipped_start_deg"): [18.0, 18.0],  # clips to 7-deg cap
          ("dr", "bad_start_prob"): 0.0,
          ("dr", "hard_start_correlate_frac"): 0.0}
    for (sec, leaf), val in ov.items():
        cfg.setdefault(sec, {})[leaf] = val
    env = SimHexapodJointGoalEnv(
        params=SimServoParams.from_cfg(None), randomize=True,
        dr_scale=0.4, episode_seconds=15.0, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "hold" else 0.0)
    return env


def test_shared_fold_gain_untouched():
    # rise_rock / walk_kick doses were replay-calibrated against
    # hardware tapes THROUGH the 0.36 mapping — the tipped-start fix
    # must never retune the shared constant.
    assert SimHexapodJointGoalEnv.TIP_ROLL_PER_FOLD == 0.36
    assert SimHexapodJointGoalEnv.TIPPED_START_ROLL_PER_FOLD > \
        SimHexapodJointGoalEnv.TIP_ROLL_PER_FOLD


def test_max_dose_tipped_spawn_keeps_recovery_headroom(monkeypatch):
    """A max-dose (cap-clipped 7-deg target) tipped hold spawn settles
    tipped enough to engage the recovery skill (>=4 deg) but BELOW 85%
    of the tilt_roll trip (<=8.5 deg at the 10-deg stance envelope) —
    i.e. with genuine recovery headroom, never mid-trip."""
    env = _make_env(seed=123, monkeypatch=monkeypatch)
    try:
        env.reset()
        assert getattr(env, "_tipped_applied", False), \
            "tipped start did not engage"
        trip = env.safety.max_roll * RAD2DEG
        rel0 = abs(env._state.imu_roll - env._tilt_ref0[0]) * RAD2DEG
        assert 4.0 <= rel0 <= 0.85 * trip, \
            f"spawn roll {rel0:.2f} deg vs trip {trip:.1f} deg"
        # And the passive settle transient under an idealized instant
        # level command must not cross the trip either (the failing
        # evals terminated 0.76-1.0 s post-reset).
        peak = rel0
        for _ in range(50):  # 1.0 s @ 50 Hz
            _o, _r, term, _tr, _i = env.step(np.zeros(18))
            rel = abs(env._state.imu_roll - env._tilt_ref0[0]) * RAD2DEG
            peak = max(peak, rel)
            assert not term, \
                f"tripped during settle (peak {peak:.2f} deg)"
    finally:
        env.close()
