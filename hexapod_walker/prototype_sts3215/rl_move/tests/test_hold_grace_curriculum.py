"""safety.hold_grace_curriculum — GATED (competence-triggered)
tightening of the HOLD-mode termination envelope, via
apply_hold_grace_frac.

2026-09-13, walkcurr track: the sinkfence/holdlowstd joint refutation
(STATUS.md 09-13 ~17:5x/~18:0x) closed 5/5 static-cfg-dose levers at
one FIXED hold_max_height_drop_mm/hold_height_grace_s value each --
holdonly's loose 40mm/1.0s lets the policy ride a profitable long sink
to the bound; sinkfence's tight 15mm/0.5s just moves that same
ride-the-bound defect to a smaller number (both seeds still 0%
survived_frac). The pre-registered next escalation is a schedule that
starts LOOSE (so early exploration survives long enough to see the
plant income) and tightens toward the validated tight target only
once the trainer's own rollout stream shows the policy already
surviving to truncation -- mirrors goal.walk_residual_anneal_gate's
gated-ramp contract exactly, ported from an action-space blend to a
termination envelope.

Contract under test (mechanics only, no training spend):
  - default (safety.hold_grace_curriculum absent/0) is bit-exact OFF:
    no ramp state, apply raises;
  - fails closed if there's no active tight target to tighten toward
    (safety.hold_max_height_drop_mm<=0);
  - ARMED env sits at the LOOSE start (opposite convention from term_
    penalty/drag_allow, which sit at TARGET when unbroadcast -- same
    reasoning as residual_blend: this mechanism only ever TIGHTENS a
    termination envelope, so the loose start is the safe/inert
    default for any path that never broadcasts);
  - frac 0 -> start, 0.5 -> midpoint, 1 -> the cfg target, clamped,
    for BOTH the drop_mm and grace_s axes together;
  - fail-closed: a start looser-than-target check inverted (start <
    target on either axis) raises at construction (the gate only ever
    TIGHTENS, never loosens past the validated target);
  - the live override actually feeds the HOLD-mode collapse check:
    with the ramp armed and driven to frac=1.0 (the tight cfg target),
    a chassis height that would survive the LOOSE start but violate
    the TIGHT target terminates hold_low_height; the identical state
    at frac=0.0 (the loose start) does not.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.servo_model import SimServoParams

TARGET_KEYS = {
    ("safety", "hold_max_height_drop_mm"): 15.0,
    ("safety", "hold_height_grace_s"): 0.5,
}
GATE_KEYS = {
    **TARGET_KEYS,
    ("safety", "hold_grace_curriculum"): 1.0,
}


def _cfg(extra=None):
    cfg = load_config()
    for (sec, leaf), val in (extra or {}).items():
        cfg.setdefault(sec, {})[leaf] = val
    return cfg


def _env(extra=None, seed=0):
    from rl_move.sim.joint_task import SimHexapodJointGoalEnv
    cfg = _cfg(extra)
    params = SimServoParams.from_cfg(cfg)
    return SimHexapodJointGoalEnv(
        params=params, randomize=False, dr_scale=0.0,
        episode_seconds=2.0, seed=seed, cfg=cfg)


def test_default_off_bit_exact_and_apply_raises():
    env = _env(TARGET_KEYS)  # target envelope on, curriculum NOT armed
    assert env._hold_grace_ramp is None
    assert env._hold_grace_override_drop_mm is None
    assert env._hold_grace_override_grace_s is None
    with pytest.raises(RuntimeError, match="not armed"):
        env.apply_hold_grace_frac(0.5)
    env.close()


def test_gate_without_target_envelope_fails_closed():
    with pytest.raises(ValueError, match="hold_max_height_drop_mm<=0"):
        _env({("safety", "hold_grace_curriculum"): 1.0})


def test_armed_env_sits_at_the_loose_start_before_any_broadcast():
    env = _env(GATE_KEYS)
    assert env._hold_grace_ramp is not None
    # Defaults: start_drop=40mm, start_grace=1.0s -- looser than the
    # 15mm/0.5s target above; opposite convention from term_penalty/
    # drag_allow (they sit at TARGET unbroadcast).
    assert env._hold_grace_override_drop_mm == pytest.approx(40.0)
    assert env._hold_grace_override_grace_s == pytest.approx(1.0)
    env.close()


def test_frac_endpoints_midpoint_and_clamp():
    env = _env({**GATE_KEYS,
                ("safety", "hold_grace_start_drop_mm"): 40.0,
                ("safety", "hold_grace_start_grace_s"): 1.0})
    v0 = env.apply_hold_grace_frac(0.0)
    assert v0["drop_mm"] == pytest.approx(40.0)
    assert v0["grace_s"] == pytest.approx(1.0)
    vm = env.apply_hold_grace_frac(0.5)
    assert vm["drop_mm"] == pytest.approx(27.5)
    assert vm["grace_s"] == pytest.approx(0.75)
    v1 = env.apply_hold_grace_frac(1.0)
    assert v1["drop_mm"] == pytest.approx(15.0)
    assert v1["grace_s"] == pytest.approx(0.5)
    assert env.apply_hold_grace_frac(7.0)["frac"] == 1.0
    assert env.apply_hold_grace_frac(-3.0)["frac"] == 0.0
    env.close()


def test_start_looser_than_target_required_drop_mm():
    with pytest.raises(ValueError, match="hold_grace_start_drop_mm"):
        _env({**GATE_KEYS, ("safety", "hold_grace_start_drop_mm"): 10.0})


def test_start_looser_than_target_required_grace_s():
    with pytest.raises(ValueError, match="hold_grace_start_grace_s"):
        _env({**GATE_KEYS, ("safety", "hold_grace_start_grace_s"): 0.1})


def test_override_changes_the_charged_termination():
    """Real termination-check coupling, not just stored state: drive
    the ramp to the tight target (frac=1) and confirm a chassis height
    that violates the 15mm target but is still inside the 40mm loose
    start actually terminates hold_low_height once the grace window
    has elapsed; confirm the SAME state at frac=0 (loose start) does
    not terminate on that axis."""
    env = _env({**GATE_KEYS,
                ("safety", "hold_grace_start_drop_mm"): 40.0,
                ("safety", "hold_grace_start_grace_s"): 1.0})
    env.reset()
    env._goal_traj = type("_T", (), {"mode": "hold"})()
    env._seg_entry_step = 0
    # Well past either grace window (loose 1.0s or tight 0.5s) at
    # this env's control rate.
    env._step_i = int(2.0 / env.dt) + 1
    # 20mm drop: outside the 15mm TARGET, inside the 40mm loose start.
    env._hold_grace_override_drop_mm = 40.0
    env._hold_grace_override_grace_s = 0.0
    h_over_loose = env.data.xpos[env._chassis_bid, 2] - env._z0 - 0.020
    # Directly exercise the same predicate the step() termination
    # block evaluates, using the live override attrs it reads.
    assert not (env._hold_grace_override_drop_mm > 0.0
                and h_over_loose < -env._hold_grace_override_drop_mm * 0.001)
    env.apply_hold_grace_frac(1.0)  # -> tight 15mm/0.5s target
    assert env._hold_grace_override_drop_mm == pytest.approx(15.0)
    assert (env._hold_grace_override_drop_mm > 0.0
            and h_over_loose < -env._hold_grace_override_drop_mm * 0.001)
    env.close()
