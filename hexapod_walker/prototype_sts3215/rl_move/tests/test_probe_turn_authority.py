"""Tests for probe_turn_authority.py (standwalk wave-2 turn-diet gate
instrument, 08-30). Two layers: pure threshold-logic unit tests (no
MuJoCo) and a short env-integration smoke test that pins the tool
against the SCRIPTED reference gait — the sanity control that caught
a real bug (info["walk_wz"] is reward-gated off in this recipe family
and silently reads 0.0 for every policy including the scripted one;
the fix reads env._body_wz() directly, which is unconditional)."""
import numpy as np

from rl_move.sim.probe_turn_authority import summarize, rollout


def _res(wz_cmd, wz_err_med):
    return {"wz_cmd": wz_cmd, "wz_err_med": wz_err_med,
            "frozen_body_wz_err_pred": abs(wz_cmd)}


def test_summarize_flags_frozen_body():
    # achieved error ~= the commanded rate itself -> frozen prediction
    results = [_res(0.25, 0.249), _res(-0.25, 0.248)]
    out = summarize(results)
    assert out["frozen"] is True
    assert "FROZEN-BODY" in out["verdict"]


def test_summarize_passes_real_tracking():
    # achieved error well under half the commanded rate -> tracks
    results = [_res(0.25, 0.03), _res(-0.25, 0.04)]
    out = summarize(results)
    assert out["frozen"] is False
    assert "TRACKS" in out["verdict"]


def test_summarize_margin_is_configurable():
    results = [_res(0.25, 0.15)]  # 0.6x the command
    assert summarize(results, frozen_margin=0.5)["frozen"] is True
    assert summarize(results, frozen_margin=0.7)["frozen"] is False


def test_scripted_gait_env_mechanics_show_real_wz():
    """Env-integration control: a short scripted turn-in-place rollout
    must show wz_med clearly nonzero and well below the frozen-body
    prediction — the exact check that caught the info["walk_wz"] bug
    (that version read 0.0 here too, since it is reward-gated on
    reward.k_walk_yaw > 0, unset by default)."""
    res = rollout(model=None,
                  env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                  wz_cmd=0.25, seed=0, episode_seconds=3.0,
                  policy="scripted")
    assert res["n_walk_ticks"] > 50
    assert res["wz_med"] is not None
    assert abs(res["wz_med"]) > 0.1          # real rotation, not ~0
    assert res["wz_err_med"] < 0.5 * res["frozen_body_wz_err_pred"]


def test_vx_cmd_default_is_bit_exact_pure_turn():
    """09-03 COMBINED-probe extension: vx_cmd defaults to 0.0 and must
    reproduce the pre-extension pure-turn-in-place rollout exactly
    (same seed/cfg/policy, only the new kwarg touched) — additive
    capability, not a behavior change for every existing caller that
    never passes vx_cmd."""
    kwargs = dict(model=None,
                  env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                  wz_cmd=0.25, seed=0, episode_seconds=3.0,
                  policy="scripted")
    baseline = rollout(**kwargs)
    explicit_zero = rollout(vx_cmd=0.0, **kwargs)
    for key in ("wz_med", "wz_p90_abs", "wz_err_med", "n_walk_ticks",
                "n_total_ticks", "fell"):
        assert baseline[key] == explicit_zero[key], key
    # and the new fields report the (zero) forward command honestly
    assert explicit_zero["vx_cmd"] == 0.0
    assert explicit_zero["vx_med"] is not None
    assert abs(explicit_zero["vx_med"]) < 0.02   # ~stationary, not walking


def test_vx_cmd_combined_scripted_teacher_actually_walks_and_turns():
    """The scripted teacher (the BC anchor's own imitation target) run
    with a SIMULTANEOUS nonzero forward + turn command — the untried
    axis every prior anchor-coef ablation skipped (those all held
    vx_ref=0). Sanity-checks the new plumbing end-to-end: both a real
    forward body-frame speed AND a real yaw rate must show up together
    (not one axis silently zeroed by the other), on the same episode."""
    res = rollout(model=None,
                  env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                  wz_cmd=0.25, vx_cmd=0.08, seed=0, episode_seconds=3.0,
                  policy="scripted")
    assert res["n_walk_ticks"] > 50
    assert res["vx_cmd"] == 0.08
    assert res["vx_med"] is not None and res["wz_med"] is not None
    assert res["vx_med"] > 0.02        # real forward motion, not stalled
    assert abs(res["wz_med"]) > 0.05   # real rotation, not suppressed to ~0


# --- scripted_omega_boost (09-03, standwalk branch-(a) fix candidate):
# multiplies the omega fed to TripodGait.set_velocity ONLY on a
# combined tick (mirrors sim_env.py's train.bc_anchor_teacher_omega_
# boost exactly). Default 1.0 = bit-exact identity.

def test_omega_boost_default_is_bit_exact():
    kwargs = dict(model=None,
                  env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                  wz_cmd=0.25, vx_cmd=0.08, seed=0, episode_seconds=3.0,
                  policy="scripted")
    baseline = rollout(**kwargs)
    explicit_one = rollout(scripted_omega_boost=1.0, **kwargs)
    for key in ("wz_med", "vx_med", "wz_err_med", "n_walk_ticks", "fell"):
        assert baseline[key] == explicit_one[key], key


def test_omega_boost_recovers_combined_tick_wz_at_a_vx_cost():
    """boost=2.0 on a combined tick must raise |wz_med| toward the
    commanded rate (recovering authority the unboosted teacher loses)
    while vx_med drops somewhat — the measured trade this lever
    exists to make, not a free win."""
    kwargs = dict(model=None,
                  env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                  wz_cmd=0.25, vx_cmd=0.08, seed=0, episode_seconds=3.0,
                  policy="scripted")
    plain = rollout(**kwargs)
    boosted = rollout(scripted_omega_boost=2.0, **kwargs)
    assert abs(boosted["wz_med"]) > abs(plain["wz_med"])
    assert boosted["vx_med"] <= plain["vx_med"]


def test_omega_boost_is_a_no_op_on_pure_turn_and_pure_walk():
    """The combined-only gate means boost must NOT touch a pure-turn
    (vx_cmd=0) or pure-walk (wz_cmd=0) rollout — both must match their
    boost=1.0 baseline exactly."""
    turn_kwargs = dict(model=None,
                        env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                        wz_cmd=0.25, vx_cmd=0.0, seed=0,
                        episode_seconds=3.0, policy="scripted")
    plain_turn = rollout(**turn_kwargs)
    boosted_turn = rollout(scripted_omega_boost=2.0, **turn_kwargs)
    assert plain_turn["wz_med"] == boosted_turn["wz_med"]

    walk_kwargs = dict(model=None,
                        env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                        wz_cmd=0.0, vx_cmd=0.08, seed=0,
                        episode_seconds=3.0, policy="scripted")
    plain_walk = rollout(**walk_kwargs)
    boosted_walk = rollout(scripted_omega_boost=2.0, **walk_kwargs)
    assert plain_walk["vx_med"] == boosted_walk["vx_med"]


def test_yaw_amplify_scale_desaturates_clip_but_REGRESSES_real_wz():
    """standwalk Next item 2, candidate (iii) (09-04): built after
    ``probe_leg_yaw_rate.py`` found ``combined_yaw_amplify_scale=3.0``
    fully de-saturates the per-tick yaw-command RATE against the
    SafetyLayer clip (0/6 legs over 37.5deg/s vs 3/6 unscaled) --  but
    the ACTUAL scripted-teacher body wz achieved at that same dose
    gets WORSE, not better, matching (and extending) the 09-04 05:35
    finding that the slew clip is NOT the dominant bottleneck: shrink
    the commanded yaw excursion via any atan2-denominator trick (this
    lever, or its uniform ``combined_yaw_arm_scale`` sibling past
    dose 2.0) and you shrink the PHYSICAL rotation the leg produces
    right along with it, clip or no clip. Pinned here so nobody wires
    this knob into BC-anchor training or spends an RL canary on it --
    refuted zero-training, same cycle it was built."""
    kwargs = dict(model=None,
                  env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                  wz_cmd=0.25, vx_cmd=0.08, seed=0, episode_seconds=3.0,
                  policy="scripted")
    plain = rollout(**kwargs)
    desaturated = rollout(scripted_yaw_amplify_scale=3.0, **kwargs)
    assert abs(desaturated["wz_med"]) < abs(plain["wz_med"])


def test_yaw_amplify_scale_is_a_no_op_on_pure_turn_and_pure_walk():
    turn_kwargs = dict(model=None,
                        env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                        wz_cmd=0.25, vx_cmd=0.0, seed=0,
                        episode_seconds=3.0, policy="scripted")
    plain_turn = rollout(**turn_kwargs)
    dosed_turn = rollout(scripted_yaw_amplify_scale=3.0, **turn_kwargs)
    assert plain_turn["wz_med"] == dosed_turn["wz_med"]

    walk_kwargs = dict(model=None,
                        env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                        wz_cmd=0.0, vx_cmd=0.08, seed=0,
                        episode_seconds=3.0, policy="scripted")
    plain_walk = rollout(**walk_kwargs)
    dosed_walk = rollout(scripted_yaw_amplify_scale=3.0, **walk_kwargs)
    assert plain_walk["vx_med"] == dosed_walk["vx_med"]


def test_selective_omega_boost_default_is_bit_exact():
    kwargs = dict(model=None,
                  env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                  wz_cmd=0.25, vx_cmd=0.08, seed=0, episode_seconds=3.0,
                  policy="scripted")
    baseline = rollout(**kwargs)
    explicit_one = rollout(scripted_selective_omega_boost=1.0, **kwargs)
    for key in ("wz_med", "vx_med", "wz_err_med", "n_walk_ticks", "fell"):
        assert baseline[key] == explicit_one[key], key


def test_selective_omega_boost_recovers_combined_tick_wz_at_a_vx_cost():
    """standwalk Next item 2, "selective per-leg omega boost"
    candidate (09-04): dose=3.0 must raise |wz_med| toward the
    commanded rate on BOTH signs (unlike the uniform omega_boost/
    yaw_arm_scale/yaw_amplify_scale levers, which all showed a
    sign-asymmetric response at the RL stage) while vx_med drops
    somewhat -- the measured trade, not a free win."""
    for wz_cmd in (0.25, -0.25):
        kwargs = dict(model=None,
                      env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                      wz_cmd=wz_cmd, vx_cmd=0.08, seed=0, episode_seconds=3.0,
                      policy="scripted")
        plain = rollout(**kwargs)
        boosted = rollout(scripted_selective_omega_boost=3.0, **kwargs)
        assert abs(boosted["wz_med"]) > abs(plain["wz_med"]), wz_cmd
        assert boosted["vx_med"] <= plain["vx_med"], wz_cmd


def test_selective_omega_boost_beats_uniform_boost_at_matched_dose():
    """Pinned zero-training finding motivating the RL canary: at
    dose=3.0 the selective (per-leg) boost achieves a LARGER wz gain
    than the already-RL-tested uniform ``scripted_omega_boost`` at the
    same dose, on the same command -- the uniform lever's gain nearly
    saturates by dose 2.0-3.0 (0.165->0.168 rad/s) while the selective
    lever keeps climbing (0.160->0.231 rad/s)."""
    kwargs = dict(model=None,
                  env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                  wz_cmd=0.25, vx_cmd=0.08, seed=0, episode_seconds=3.0,
                  policy="scripted")
    uniform = rollout(scripted_omega_boost=3.0, **kwargs)
    selective = rollout(scripted_selective_omega_boost=3.0, **kwargs)
    assert abs(selective["wz_med"]) > abs(uniform["wz_med"])


def test_selective_omega_boost_is_a_no_op_on_pure_turn_and_pure_walk():
    """The combined-only gate (inside TripodGait itself) means this
    boost must NOT touch a pure-turn (vx_cmd=0) or pure-walk
    (wz_cmd=0) rollout -- both must match their boost=1.0 baseline
    exactly."""
    turn_kwargs = dict(model=None,
                        env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                        wz_cmd=0.25, vx_cmd=0.0, seed=0,
                        episode_seconds=3.0, policy="scripted")
    plain_turn = rollout(**turn_kwargs)
    boosted_turn = rollout(scripted_selective_omega_boost=2.0, **turn_kwargs)
    assert plain_turn["wz_med"] == boosted_turn["wz_med"]

    walk_kwargs = dict(model=None,
                        env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                        wz_cmd=0.0, vx_cmd=0.08, seed=0,
                        episode_seconds=3.0, policy="scripted")
    plain_walk = rollout(**walk_kwargs)
    boosted_walk = rollout(scripted_selective_omega_boost=2.0, **walk_kwargs)
    assert plain_walk["vx_med"] == boosted_walk["vx_med"]
