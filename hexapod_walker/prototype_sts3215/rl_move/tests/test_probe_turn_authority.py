"""Tests for probe_turn_authority.py (standwalk wave-2 turn-diet gate
instrument, 08-30). Two layers: pure threshold-logic unit tests (no
MuJoCo) and a short env-integration smoke test that pins the tool
against the SCRIPTED reference gait — the sanity control that caught
a real bug (info["walk_wz"] is reward-gated off in this recipe family
and silently reads 0.0 for every policy including the scripted one;
the fix reads env._body_wz() directly, which is unconditional)."""
import numpy as np
import pytest
from types import SimpleNamespace

from rl_move.sim.probe_turn_authority import (
    summarize, rollout, _ContactAudit, _support_point, _material_slip)


def _rigid_audit_env(*, gravity="0 0 0", floor=False, floor_first=True):
    """A free rigid body with six named pads; no policy or robot task logic."""
    import mujoco
    floor_xml = '<geom type="box" size="2 2 .01" pos="0 0 -.01" friction="1 .01 .01"/>'
    pads = ''.join(
        f'<body name="L{i}_pad" pos="{.15 if i == 1 else 0} 0 0">'
        f'<geom type="box" size=".05 .04 .02" mass=".1" '
        f'contype="{1 if floor and i == 0 else 0}" '
        f'conaffinity="{1 if floor and i == 0 else 0}"/></body>'
        for i in range(6))
    m = mujoco.MjModel.from_xml_string(f'''<mujoco>
      <option timestep=".0005" gravity="{gravity}" integrator="Euler"/>
      <worldbody>{floor_xml if floor and floor_first else ''}
        <body name="chassis" pos="0 0 .0199"><freejoint/>
          <inertial pos="0 0 0" mass="1" diaginertia=".03 .04 .05"/>
          {pads}
        </body>
        {'<body>' + floor_xml + '</body>' if floor and not floor_first else ''}
      </worldbody></mujoco>''')
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    return SimpleNamespace(model=m, data=d, _mujoco=mujoco,
                           _chassis_bid=m.body("chassis").id, dt=.005)


def _accept(audit):
    audit.tick(q_prop=None, q_safe=None, q_act=None)


def test_substep_torque_pulse_integral_is_independent_of_control_grouping():
    """Last-substep sampling misses these pulses; true impulse must not."""
    summaries = []
    for group in (1, 5):
        env = _rigid_audit_env()
        audit = _ContactAudit(env)
        for start in range(0, 100, group):
            audit.begin_interval(phase=0)
            for i in range(start, start + group):
                # Final step of each five-step block is zero force.
                env.data.xfrc_applied[env._chassis_bid, 5] = 2 if i % 5 == 0 else 0
                audit.mj_step(env.model, env.data)
            _accept(audit)
        out = audit.summary()
        summaries.append(out)
        assert out["n_substeps"] == 100
        assert out["n_ticks"] == 100 // group
        assert out["applied_yaw_imp_Nms"] == pytest.approx(.02, abs=1e-12)
        assert out["angmom_check"]["delta_lz_Nms"] == pytest.approx(.02, rel=1e-9)
        assert out["angmom_check"]["valid"]
        assert out["angmom_check"]["slope"] == pytest.approx(1, rel=1e-9)
        # A control-rate last-sample estimator reports zero at group=5.
        if group == 5:
            assert sum(r["external_tau"] for r in audit.rows[4::5]) == 0
    assert summaries[0]["angmom_check"] == summaries[1]["angmom_check"]


def test_applied_force_at_offset_body_is_shifted_to_whole_robot_com():
    env = _rigid_audit_env()
    audit = _ContactAudit(env)
    b = env.model.body("L1_pad").id
    audit.begin_interval(phase=0)
    com = env.data.subtree_com[audit.root].copy()
    force = np.array([0., 3., 0.])
    expected = np.cross(env.data.xipos[b] - com, force)[2] * env.model.opt.timestep
    env.data.xfrc_applied[b, :3] = force
    audit.mj_step(env.model, env.data)
    _accept(audit)
    out = audit.summary()
    assert out["applied_yaw_imp_Nms"] == pytest.approx(expected, abs=1e-12)
    assert out["angmom_check"]["delta_lz_Nms"] == pytest.approx(expected, rel=1e-8)
    assert out["angmom_check"]["valid"]


@pytest.mark.parametrize("floor_first", [True, False])
def test_real_contacts_support_weight_with_either_geom_order(floor_first):
    env = _rigid_audit_env(gravity="0 0 -9.81", floor=True, floor_first=floor_first)
    # Settle to support equilibrium before measuring, with the real solver.
    for _ in range(2000):
        env._mujoco.mj_step(env.model, env.data)
    audit = _ContactAudit(env)
    audit.begin_interval(phase=0)
    for _ in range(50):
        audit.mj_step(env.model, env.data)
    _accept(audit)
    out = audit.summary()
    assert out["sign_flipped"] is False
    assert out["sum_fz_med_N"] == pytest.approx(out["weight_N"], rel=.01)
    assert out["support_force_sign_valid"]
    foot_geom = next(g for g, f in audit.geom_foot.items() if f == 0)
    contact = next(c for c in env.data.contact if foot_geom in (c.geom1, c.geom2))
    assert (contact.geom2 == foot_geom) == floor_first


def test_contact_geometry_and_material_slip_are_permutation_invariant():
    from itertools import permutations
    contacts = [(np.array([.1, 0, 0]), 1.),
                (np.array([-.1, 0, 0]), 2.),
                (np.array([0, .2, 0]), 3.)]
    r0 = np.eye(3)
    theta = .1
    r1 = np.array([[np.cos(theta), -np.sin(theta), 0],
                   [np.sin(theta), np.cos(theta), 0], [0, 0, 1]])
    expected_point = np.array([-.1 / 6, .1, 0])
    expected_slip = 2 * np.sin(theta / 2) * (.1 * 3 + .2 * 3) / 6
    for order in permutations(contacts):
        np.testing.assert_allclose(_support_point(order), expected_point)
        assert _material_slip(order, np.zeros(3), r0, np.zeros(3), r1) == pytest.approx(expected_slip)
    # Opposite sliding material points must not cancel into zero slip.
    opposite = [(np.array([.1, 0, 0]), 1.), (np.array([-.1, 0, 0]), 1.)]
    assert np.linalg.norm(_support_point(opposite)) == 0
    assert _material_slip(opposite, np.zeros(3), r0, np.zeros(3), r1) > .009


def test_contact_audit_does_not_repair_a_reversed_force_sign():
    env = _rigid_audit_env(gravity="0 0 -9.81", floor=True)
    audit = _ContactAudit(env)
    audit.begin_interval(phase=0)
    audit.mj_step(env.model, env.data)
    _accept(audit)
    assert audit.rows[0]["fz"].sum() > 0
    audit.rows[0]["fz"] *= -1
    out = audit.summary()
    assert out["sum_fz_med_N"] < 0
    assert not out["support_force_sign_valid"]
    assert not out["sign_flipped"]


def test_momentum_validation_rejects_wrong_scale_even_at_perfect_correlation():
    env = _rigid_audit_env()
    audit = _ContactAudit(env)
    audit.begin_interval(phase=0)
    for i in range(20):
        env.data.xfrc_applied[env._chassis_bid, 5] = i % 4
        audit.mj_step(env.model, env.data)
    _accept(audit)
    for row in audit.rows:
        row["delta_lz"] *= .3
    out = audit.summary()["angmom_check"]
    assert out["corr"] == pytest.approx(1)
    assert out["slope"] == pytest.approx(.3)
    assert not out["valid"]


def test_empty_probe_is_insufficient_data():
    assert "INSUFFICIENT DATA" in summarize([_res(.25, None)])["verdict"]
    assert not _ContactAudit(_rigid_audit_env()).summary()["angmom_check"]["valid"]


def test_contact_audit_preserves_every_step_of_scripted_rollout(monkeypatch):
    import rl_move.sim.probe_turn_authority as probe
    original = probe.make_env
    traces = []
    envs = []

    def make_traced(*args, **kwargs):
        env = original(*args, **kwargs)
        envs.append(env)
        trace = []
        traces.append(trace)
        step = env.step

        def traced(act):
            result = step(act)
            trace.append((env.data.qpos.copy(), env.data.qvel.copy(),
                          env.data.ctrl.copy(), np.asarray(act).copy(),
                          result[1:4]))
            return result
        env.step = traced
        return env
    monkeypatch.setattr(probe, "make_env", make_traced)
    kwargs = dict(model=None, env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                  wz_cmd=.25, vx_cmd=.08, seed=0, episode_seconds=3., policy="scripted")
    baseline = rollout(**kwargs)
    audited = rollout(contact_audit=True, **kwargs)
    assert {k: v for k, v in baseline.items() if k != "contact_audit"} == {
        k: v for k, v in audited.items() if k != "contact_audit"}
    assert len(traces[0]) == len(traces[1])
    for a, b in zip(*traces):
        for av, bv in zip(a, b):
            np.testing.assert_array_equal(av, bv)
    out = audited["contact_audit"]
    assert out["n_ticks"] == audited["n_walk_ticks"]
    assert out["n_substeps"] == out["n_ticks"] * envs[1]._substeps
    assert out["duration_s"] == pytest.approx(out["n_ticks"] * envs[1].dt)
    assert envs[1]._mujoco is envs[0]._mujoco  # proxy restored on close


def test_scripted_offsets_change_real_gait_and_audit_uses_its_phase(monkeypatch):
    import rl_move.sim.probe_turn_authority as probe
    from hexapod_core.tripod_gait import TripodGait
    original = TripodGait.desired_deg
    phase_sequences, commands = [], []
    resets = []
    reset = TripodGait.reset_phase

    def record_reset(self, **kwargs):
        result = reset(self, **kwargs)
        resets.append(self._phase)
        return result

    def desired(self, t):
        result = original(self, t)
        commands[-1].append(np.asarray(result).copy())
        phase_sequences[-1].append(self._phase)
        return result
    monkeypatch.setattr(TripodGait, "reset_phase", record_reset)
    monkeypatch.setattr(TripodGait, "desired_deg", desired)
    accepted_phases = []
    begin = _ContactAudit.begin_interval

    def record_begin(self, *, phase, record=True):
        assert phase == phase_sequences[-1][-1]
        accepted_phases.append(phase)
        return begin(self, phase=phase, record=record)
    monkeypatch.setattr(_ContactAudit, "begin_interval", record_begin)
    for offset in (0, np.pi):
        phase_sequences.append([])
        commands.append([])
        result = probe.rollout(model=None, env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                               wz_cmd=.25, vx_cmd=.08, seed=0, episode_seconds=3.,
                               policy="scripted", contact_audit=True, phase_offset=offset)
        assert result["scripted_start_phase"] == offset
    assert 0 in resets and np.pi in resets
    assert accepted_phases
    assert not np.allclose(commands[0][150], commands[1][150])


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


def test_active_contact_attribution_is_invariant_to_order_and_rejects_gap_contacts():
    from itertools import permutations
    env = _rigid_audit_env()
    audit = _ContactAudit(env)
    d = env.data
    foot_geom = next(g for g, f in audit.geom_foot.items() if f == 0)
    # Contact frame has normal +z, first tangent +x, second tangent +y.
    frame = np.array([[0., 0., 1.], [1., 0., 0.], [0., 1., 0.]])
    points = [np.array([.1, .02, 0]), np.array([-.03, .1, 0]),
              np.array([.02, -.07, 0]), np.array([100., 100., 0])]
    loads = [1., 2., 3., 1000.]
    records = []
    for i, (p, load) in enumerate(zip(points, loads)):
        c = SimpleNamespace(geom1=999, geom2=foot_geom,
                            efc_address=0 if i < 3 else -1,
                            frame=frame.ravel(), pos=p,
                            wrench=np.array([load, .2 * load, -.1 * load,
                                             .01 * load, 0., 0.]))
        records.append(c)
    solver = SimpleNamespace(time=0., ncon=4, contact=records,
                             subtree_com=d.subtree_com.copy(),
                             xpos=d.xpos.copy(), xmat=d.xmat.copy(),
                             xipos=d.xipos.copy(),
                             xfrc_applied=d.xfrc_applied.copy(),
                             qfrc_applied=d.qfrc_applied.copy(),
                             qfrc_passive=d.qfrc_passive.copy())
    env.data = solver
    pad_x = d.xpos[audit.pads].copy()
    pad_x[:, 0] += .001
    audit._endpoint = lambda: (0., pad_x.copy(), d.xmat[audit.pads].reshape(6, 3, 3).copy())

    def step(m, data):
        data.time += m.opt.timestep

    def force(m, data, ci, out):
        assert data.contact[ci].efc_address >= 0  # inactive contacts never queried
        out[:] = data.contact[ci].wrench
    audit.mj = SimpleNamespace(mj_step=step, mj_contactForce=force)
    com = solver.subtree_com[audit.root]
    expected_tau = sum(np.cross(p - com, np.array([.2, -.1, 1.]) * load)[2]
                       for p, load in zip(points[:3], loads[:3]))
    expected_support = _support_point(list(zip(points[:3], loads[:3])))
    for order in permutations(records):
        solver.contact = order
        audit.begin_interval(phase=.5)
        audit.mj_step(env.model, solver)
        row = audit.pending[0]
        assert row["fz"][0] == pytest.approx(6.)
        assert row["tau_f"][0] == pytest.approx(expected_tau)
        assert row["tau_c"][0] == pytest.approx(.06)
        np.testing.assert_allclose(row["rel_body"][0], (expected_support - com)[:2])
        assert row["slip_material"][0] == pytest.approx(.001)
        assert row["loaded"].tolist() == [True, False, False, False, False, False]


def test_scored_interval_does_not_include_prior_unaccepted_impulses():
    env = _rigid_audit_env()
    audit = _ContactAudit(env)
    env.data.xfrc_applied[env._chassis_bid, 5] = 4.
    audit.begin_interval(phase=0)
    audit.mj_step(env.model, env.data)  # a mode-filtered interval: not accepted
    audit.begin_interval(phase=1)
    env.data.xfrc_applied[env._chassis_bid, 5] = 1.
    audit.mj_step(env.model, env.data)
    _accept(audit)
    out = audit.summary()
    assert out["n_ticks"] == out["n_substeps"] == 1
    assert out["applied_yaw_imp_Nms"] == pytest.approx(env.model.opt.timestep)
    assert out["angmom_check"]["delta_lz_Nms"] == pytest.approx(env.model.opt.timestep)


def test_mesh_family_at_100hz_closes_momentum_with_hinge_armature(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    out = rollout(model=None, env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1", "control.hz=100"]},
                  wz_cmd=.15, vx_cmd=.08, seed=0, episode_seconds=3.,
                  policy="scripted", contact_audit=True)["contact_audit"]
    assert out["angmom_check"]["unaccounted"] == []
    assert out["angmom_check"]["valid"]
    assert out["angmom_check"]["relative_rms_residual"] < .01
    assert out["angmom_check"]["slope"] == pytest.approx(1, abs=.01)
    assert out["n_substeps"] > out["n_ticks"]
    assert out["control_timestep_s"] == .01
    assert out["support_force_sign_valid"]
    assert out["bc_anchor_resid"]["available"] is False


def test_resolved_scripted_radius_is_reported_and_doses_remain_distinct():
    rows = [rollout(model=None, env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                    wz_cmd=.15, vx_cmd=.08, seed=0, episode_seconds=2.1,
                    policy="scripted", scripted_stance_radius_scale=scale)
            for scale in (1.10, 1.15)]
    assert [r["scripted_stance_radius_scale"] for r in rows] == [1.10, 1.15]
    assert rows[1]["scripted_foot_radius_m"] > rows[0]["scripted_foot_radius_m"]
