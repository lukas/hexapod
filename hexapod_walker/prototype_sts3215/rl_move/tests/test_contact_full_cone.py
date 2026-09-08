"""Full contact-cone regressions through the CLI's actual _ContactAudit engine.

Synthetic solved wrenches isolate contact accounting; the short real rollout
checks the same pta.rollout path used by probe_turn_traction --engine audit.
"""
from types import SimpleNamespace
import json

import mujoco
import numpy as np
import pytest

from rl_move.sim import probe_turn_authority as pta


def _audit_snapshot(wrenches, *, friction=(.5, .25, .02, .01, .005),
                    dim=6, cone="pyramidal"):
    pads = "".join(
        f'<body name="L{i}_pad"><geom size=".01" mass=".1" '
        'contype="0" conaffinity="0"/></body>' for i in range(6))
    m = mujoco.MjModel.from_xml_string(f'''<mujoco>
      <option gravity="0 0 0" timestep=".001" cone="{cone}"/>
      <worldbody><body name="chassis"><freejoint/>{pads}</body></worldbody>
    </mujoco>''')
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    env = SimpleNamespace(model=m, data=d, _mujoco=mujoco,
                          _chassis_bid=m.body("chassis").id, dt=.01)
    audit = pta._ContactAudit(env)
    foot = next(g for g, f in audit.geom_foot.items() if f == 0)
    records = [SimpleNamespace(
        geom1=999, geom2=foot, efc_address=0,
        frame=np.eye(3).ravel(), pos=np.array([0., 0., .02]),
        wrench=np.asarray(w, dtype=float), friction=np.asarray(friction),
        dim=dim) for w in wrenches]
    solver = SimpleNamespace(
        time=0., ncon=len(records), contact=records,
        subtree_com=d.subtree_com.copy(), xpos=d.xpos.copy(),
        xmat=d.xmat.copy(), xipos=d.xipos.copy(),
        xfrc_applied=d.xfrc_applied.copy(), qfrc_applied=d.qfrc_applied.copy(),
        qfrc_passive=d.qfrc_passive.copy(), actuator_force=np.zeros(m.nu))
    env.data = solver
    audit._endpoint = lambda: (
        0., d.xpos[audit.pads].copy(),
        d.xmat[audit.pads].reshape(6, 3, 3).copy())

    def step(model, data):
        data.time += model.opt.timestep

    def force(model, data, ci, out):
        out[:] = data.contact[ci].wrench

    audit.mj = SimpleNamespace(mj_step=step, mj_contactForce=force)
    audit.begin_interval(phase=0)
    audit.mj_step(m, solver)
    row = audit.pending[0]
    audit.tick(q_prop=None, q_safe=None, q_act=None)
    return row, audit.summary()


@pytest.mark.parametrize("wrench, component", [
    ([10, 0, 0, .2, 0, 0], 2),       # torsion alone reaches its cap
    ([10, 0, 0, 0, .1, 0], 3),       # first rolling axis
    ([10, 0, 0, 0, 0, .05], 4),      # second rolling axis
    ([10, 0, 2.5, 0, 0, 0], 1),      # anisotropic second tangent
])
def test_full_cone_detects_saturation_missed_by_planar_ratio(wrench, component):
    row, out = _audit_snapshot([wrench])
    assert row["u_max"][0] <= .5  # old estimator falsely looks sub-cone
    full = out["traction"]["full_cone"]
    assert full["valid"]
    foot = full["per_foot"][0]
    assert foot["usage_max_med"] == pytest.approx(1.)
    assert foot["frac_loaded_near_cone"] == 1.
    assert foot["normalized_component_max_p90"][component] == pytest.approx(1.)


@pytest.mark.parametrize("cone, expected", [
    ("pyramidal", 1.), ("elliptic", np.sqrt(.5))
])
def test_contact_cone_shape_changes_diagonal_utilization(cone, expected):
    row, out = _audit_snapshot([[10, 2.5, 1.25, 0, 0, 0]], cone=cone)
    assert row["u_max"][0] < .6
    full = out["traction"]["full_cone"]
    assert full["cone_type"] == cone
    assert full["per_foot"][0]["usage_max_med"] == pytest.approx(expected)
    assert full["observed_condim"] == [6]


def test_cone_budget_couples_sliding_and_spin_per_contact():
    # Each component consumes half the pyramidal normal-force budget.
    _, out = _audit_snapshot([[10, 2.5, 0, .1, 0, 0]])
    foot = out["traction"]["full_cone"]["per_foot"][0]
    assert foot["usage_max_med"] == pytest.approx(1.)
    np.testing.assert_allclose(foot["normalized_component_max_p90"],
                               [.5, 0, .5, 0, 0])


def test_contact_order_and_opposing_contact_forces_do_not_hide_saturation():
    w = [[10, 5, 0, 0, 0, 0], [20, -10, 0, 0, 0, 0]]
    _, first = _audit_snapshot(w)
    _, second = _audit_snapshot(w[::-1])
    assert first["traction"]["full_cone"] == second["traction"]["full_cone"]
    foot = first["traction"]["full_cone"]["per_foot"][0]
    assert foot["usage_wmean_med"] == pytest.approx(1.)
    assert foot["usage_max_med"] == pytest.approx(1.)


@pytest.mark.parametrize("dim", [1, 3, 4, 6])
def test_only_active_condim_components_consume_budget(dim):
    wrench = [10, 0, 0, 0, 0, 0]
    if dim < 6:
        wrench[dim] = 99  # inactive component must be ignored
    _, out = _audit_snapshot([wrench], dim=dim)
    full = out["traction"]["full_cone"]
    assert full["observed_condim"] == [dim]
    assert full["per_foot"][0]["usage_max_med"] == 0.


@pytest.mark.parametrize("normal", [0., -1.])
def test_no_compressive_load_has_no_defined_utilization(normal):
    _, out = _audit_snapshot([[normal, 0, 0, 0, 0, 0]])
    foot = out["traction"]["full_cone"]["per_foot"][0]
    assert foot["loaded_substeps"] == 0
    assert foot["usage_max_med"] is None
    # New fields remain strict JSON, even with no compressive contact.
    json.dumps(out["traction"]["full_cone"], allow_nan=False)


def test_zero_friction_is_valid_only_when_its_force_component_is_zero():
    _, quiet = _audit_snapshot([[10, 0, 0, 0, 0, 0]], friction=[0] * 5)
    assert quiet["traction"]["full_cone"]["valid"]
    assert quiet["traction"]["full_cone"]["per_foot"][0]["usage_max_med"] == 0.
    _, broken = _audit_snapshot([[10, 1, 0, 0, 0, 0]], friction=[0] * 5)
    full = broken["traction"]["full_cone"]
    assert not full["valid"]
    assert full["invalid_contact_samples"] == 1
    assert "zero friction" in " ".join(full["invalid_reasons"])
    assert full["per_foot"][0]["usage_max_med"] is None
    json.dumps(full, allow_nan=False)


def test_actual_cli_audit_rollout_populates_full_cone_without_changing_behavior(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    kw = dict(model=None, env_cls_kwargs={"cfg_set": [
        "goal.walk_yaw_cmd=1", "control.hz=100"]}, wz_cmd=.15, vx_cmd=.08,
        seed=0, episode_seconds=2.2, policy="scripted")
    plain = pta.rollout(contact_audit=False, **kw)
    audited = pta.rollout(contact_audit=True, **kw)
    for key in ("wz_med", "vx_med", "wz_err_med", "n_walk_ticks", "fell"):
        assert audited[key] == plain[key]
    a = audited["contact_audit"]
    assert a["angmom_check"]["valid"]
    tr = a["traction"]
    assert "planar" in tr["legacy_cone_usage_definition"]
    full = tr["full_cone"]
    assert full["valid"]
    assert full["observed_condim"]
    assert full["invalid_contact_samples"] == 0
    for foot in full["per_foot"].values():
        if foot["loaded_substeps"]:
            assert foot["usage_max_med"] is not None
            assert 0 <= foot["usage_max_med"] <= 1.0001
    json.dumps(full, allow_nan=False)
