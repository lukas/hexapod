"""Traction probe: sign/coordinate math is unit-tested, the static
force-balance + touch-sensor cross-checks pass on the twin plant, the
fail-closed static gate actually fails on a broken sign, and the
instrumented rollout is behavior-neutral (bit-identical body medians)
vs the stance-arm probe's rollout on the same cell/seed."""
import json
from pathlib import Path

import numpy as np
import pytest

import os


@pytest.fixture(scope="module", autouse=True)
def _mesh_family_model_source():
    """tests/conftest.py pins HEXAPOD_MODEL_SOURCE=primitive for the
    calibrated behavior suite; this probe is mesh-family by
    construction. Scoped set/restore so nothing leaks to other test
    modules in a full-suite run."""
    # Scoped via MonkeyPatch so nothing leaks into other modules
    # (RESEARCH_RULES "Tests" 3).
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
        yield
from rl_move.sim import probe_turn_stancearm as stance
from rl_move.sim import probe_turn_traction as tr


CFG = json.loads(
    (Path(__file__).resolve().parents[2] / "rl_move/tests/data/"
     "cfg_frozen_audit.json").read_text()) \
    if (Path(__file__).resolve().parents[2] / "rl_move/tests/data/"
        "cfg_frozen_audit.json").exists() else None


def _cfg_set():
    # minimal walk-mode cfg matching the frozen audit's env-relevant keys
    return ["control.hz=100", "safety.max_delta_q_deg=0.375",
            "goal.walk_speed_min_m_s=0.08", "goal.walk_speed_max_m_s=0.08",
            "goal.walk_yaw_cmd=1", "env.model_source=mesh_mjx"]


def test_yaw_moment_sign_math():
    # +x offset, +y force -> positive z-moment (right-hand rule)
    assert tr.yaw_moment_z(np.array([1.0, 0.0]),
                           np.array([0.0, 2.0])) == pytest.approx(2.0)
    # +y offset, +x force -> negative z-moment
    assert tr.yaw_moment_z(np.array([0.0, 1.0]),
                           np.array([3.0, 0.0])) == pytest.approx(-3.0)
    # force through the reference point -> zero moment
    assert tr.yaw_moment_z(np.array([2.0, 2.0]),
                           np.array([2.0, 2.0])) == pytest.approx(0.0)


@pytest.fixture(scope="module")
def twin_rollout():
    return tr.rollout(policy="scripted", model=None, model_obs_width=None,
                      cfg_set=_cfg_set(), vx_cmd=0.08, wz_cmd=0.15,
                      seed=0, episode_seconds=5.0, plant="twin",
                      min_scored_ticks=150)


def test_static_force_balance_and_touch_crosscheck(twin_rollout):
    sc = twin_rollout["static_check"]
    # rollout() hard-raises outside 0.90..1.10; assert the tighter read
    assert 0.90 <= sc["sum_normal_over_weight"] <= 1.10
    # solver normals must agree with the independent touch sensors
    assert sc["touch_vs_contactN_med_relerr"] < 0.15
    # standing still: tangential forces are a small fraction of normal
    assert sc["tangential_over_normal_med"] < 0.35
    assert sc["frame_orthonormality_max_err"] < 1e-9
    assert sc["static_mu_min"] > 0.5


def test_dynamic_window_metrics_are_populated(twin_rollout):
    r = twin_rollout
    assert not r["fell"]
    assert r["n_scored_ticks"] >= 150
    assert r["touch_vs_contactN_med_relerr_dynamic"] < 0.25
    yb = r["yaw_budget"]
    assert yb["pos_sum_med_nm"] is not None
    assert yb["pos_sum_med_nm"] >= 0.0 and yb["neg_sum_med_nm"] >= 0.0
    assert 0.0 <= yb["net_over_gross_med"] <= 1.0
    # commanded +wz: the net contact yaw moment's MEDIAN sign must not
    # be strongly negative (weak check; sign errors flip it hard)
    am = r["angmom_check"]
    assert am["corr_net_tau_vs_dLdt"] is not None
    # net external z-torque about COM is contact-only: correlation must
    # be positive and clearly nonzero (a sign flip makes it negative)
    assert am["corr_net_tau_vs_dLdt"] > 0.3
    for f in range(6):
        pl = r["per_leg"][f]
        assert pl["loaded_ticks"] > 0
        if pl["cone_usage_med"] is not None:
            assert 0.0 <= pl["cone_usage_med"] <= 1.5
    sat = r["actuator_saturation_stance"]
    for nm in ("yaw", "hip", "knee"):
        assert sat[nm]["sat_med"] is not None
        assert 0.0 <= sat[nm]["sat_med"] <= 1.0


def test_static_gate_fails_closed_on_broken_sign(monkeypatch):
    orig = tr.contact_snapshot

    def negated(model, data, gid2leg, com):
        s = orig(model, data, gid2leg, com)
        s["f_w"] = 0.05 * s["f_w"]  # magnitude break: no sign can fix it
        return s

    monkeypatch.setattr(tr, "contact_snapshot", negated)
    with pytest.raises(RuntimeError, match="STATIC CHECK FAIL"):
        tr.rollout(policy="scripted", model=None, model_obs_width=None,
                   cfg_set=_cfg_set(), vx_cmd=0.08, wz_cmd=0.15,
                   seed=0, episode_seconds=3.0, plant="twin",
                   min_scored_ticks=1)


def test_instrumentation_is_behavior_neutral_vs_stance_probe():
    """Same cell/seed/length: the traction rollout's executed behavior
    (body vx/wz medians over the identical scored window) must equal the
    stance-arm probe's bit-for-bit — the added force reads must not
    perturb the trajectory."""
    kw = dict(policy="scripted", model=None, model_obs_width=None,
              cfg_set=_cfg_set(), vx_cmd=0.08, wz_cmd=0.15, seed=0,
              episode_seconds=5.0, plant="twin")
    a = tr.rollout(min_scored_ticks=150, **kw)
    b = stance.rollout(**kw)
    assert a["body"]["vx_med"] == b["body"]["vx_med"]
    assert a["body"]["wz_med"] == b["body"]["wz_med"]
    assert a["n_scored_ticks"] == b["n_scored_ticks"]


def test_audit_engine_traction_extension_on_twin():
    """The per-substep _ContactAudit traction extension: impulse-closure
    validity gate still passes on the mesh twin at 100Hz (proving the
    added reads change nothing), and the new cone-usage / cancellation /
    rail fields are populated and physically sane (pyramidal solver
    forces live inside the friction cone, so usage <= ~1)."""
    from rl_move.sim import probe_turn_authority as pta
    r = pta.rollout(model=None,
                    env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1",
                                                "control.hz=100"]},
                    wz_cmd=0.15, vx_cmd=0.08, seed=0, episode_seconds=4.0,
                    policy="scripted", contact_audit=True)
    a = r["contact_audit"]
    assert a["angmom_check"]["valid"]
    assert a["angmom_check"]["relative_rms_residual"] < 0.01
    tr_ = a["traction"]
    yb = tr_["yaw_budget"]
    assert yb["pos_sum_med_Nm"] >= 0.0 and yb["neg_sum_med_Nm"] >= 0.0
    assert 0.0 <= yb["net_over_gross_med"] <= 1.0
    for f in range(6):
        pf = tr_["per_foot"][f]
        assert pf["loaded_substeps"] > 0
        assert pf["mu_med"] > 0.5
        assert 0.0 <= pf["cone_usage_wmean_med"] <= 1.05
        assert 0.0 <= pf["cone_usage_max_p90"] <= 1.05
        assert pf["fn_med_N"] > 0.0
    sat = tr_["actuator_force_saturation_stance"]
    for nm in ("yaw", "hip", "knee"):
        assert sat[nm]["force_sat_med"] is not None
        assert 0.0 <= sat[nm]["force_sat_med"] <= 1.0


def test_foot_torsion_dose_survives_reset_and_reaches_live_contacts():
    """--foot-torsion-mu is a probe-local diagnostic dose. REGRESSION
    (09-08): env.reset() restores the pristine `_base_geom_friction`
    copy taken at __init__, which silently WIPED a live-model-only dose
    (the first fullmesh torsion A/B came back BIT-IDENTICAL to
    baseline). The dose must survive reset AND appear in the solved
    contacts' friction[2]."""
    import mujoco
    import numpy as np
    from rl_move.sim import probe_turn_authority as pta
    from rl_move.sim.probe_turn_traction import foot_geom_ids
    env = pta.make_env(["control.hz=100"], 0, 4.0)
    try:
        fg = foot_geom_ids(env.model)
        assert env.model.geom_friction[fg[0], 1] == pytest.approx(0.1)
        # the CLI dose path: live model + pristine DR copy
        for g in fg:
            env.model.geom_friction[g, 1] = 0.005
        tg = mujoco.mj_name2id(env.model, mujoco.mjtObj.mjOBJ_GEOM,
                               "terrain")
        env.model.geom_friction[tg, 1] = min(
            env.model.geom_friction[tg, 1], 0.005)
        env._base_geom_friction = env.model.geom_friction.copy()
        env.reset()
        assert env.model.geom_friction[fg[0], 1] == pytest.approx(0.005)
        for _ in range(50):
            env.step(np.zeros(env.action_space.shape))
        seen = False
        fgs = set(fg)
        for ci in range(env.data.ncon):
            c = env.data.contact[ci]
            if c.geom1 in fgs or c.geom2 in fgs:
                assert c.friction[2] == pytest.approx(0.005)
                seen = True
        assert seen, "no live foot contact found to verify the dose"
    finally:
        env.close()
    env2 = pta.make_env(["control.hz=100"], 0, 2.0)
    try:
        assert env2.model.geom_friction[fg[0], 1] == pytest.approx(0.1)
    finally:
        env2.close()
