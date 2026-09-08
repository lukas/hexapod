"""Physics regressions for the opt-in sphere-radius construction path."""
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import pytest


from rl_move.config import load_config
from rl_move.sim.servo_model import _compile_with_foot_radius, build_model
from rl_move.sim.sim_env import SimHexapodBalanceEnv, set_foot_geom_radius


def xml(radius=.0045, surface="plane"):
    ground = {
        "plane": '<geom name="floor" type="plane" size="1 1 .1"/>',
        "box": '<geom name="floor" type="box" size="1 1 .1" pos="0 0 -.1"/>',
        "sphere": '<geom name="floor" type="sphere" size=".1" pos="0 0 -.1"/>',
    }[surface]
    return f"""<mujoco><option timestep=".001"/><worldbody>{ground}
      <body name="foot" pos="0 0 .01"><freejoint/>
        <geom name="L0_foot" type="sphere" size="{radius}"
          density="900" condim="6" friction="1.7 .03 .001"/>
        <geom name="decoy" type="sphere" size=".003" pos=".04 0 .04"
          density="100" contype="1" conaffinity="1"/>
      </body></worldbody></mujoco>"""


def reference_xml(text, radius):
    """Independent XML edit with explicit original compiled inertial values."""
    original = mujoco.MjModel.from_xml_string(text)
    tree = ET.fromstring(text)
    body = tree.find("worldbody/body")
    ET.SubElement(body, "inertial", {
        "mass": repr(float(original.body_mass[1])),
        "pos": " ".join(map(repr, map(float, original.body_ipos[1]))),
        "quat": " ".join(map(repr, map(float, original.body_iquat[1]))),
        "diaginertia": " ".join(map(repr, map(float, original.body_inertia[1]))),
    })
    body.find("geom[@name='L0_foot']").set("size", str(radius))
    return ET.tostring(tree, encoding="unicode")


def contacts(model, z):
    data = mujoco.MjData(model)
    data.qpos[2] = z
    mujoco.mj_forward(model, data)
    foot = model.geom("L0_foot").id
    return sorted((tuple(sorted((int(c.geom1), int(c.geom2)))), float(c.dist))
                  for c in data.contact if foot in (c.geom1, c.geom2))


@pytest.mark.parametrize("surface", ["plane", "box", "sphere"])
@pytest.mark.parametrize("radius", [.002, .012, .0135])
def test_resize_matches_independently_compiled_collision_reference(surface, radius):
    text = xml(surface=surface)
    original = mujoco.MjModel.from_xml_string(text)
    changed = _compile_with_foot_radius(text, radius_m=radius)
    reference = mujoco.MjModel.from_xml_string(reference_xml(text, radius))
    for field in ("geom_size", "geom_rbound", "geom_aabb", "bvh_aabb",
                  "bvh_child", "bvh_nodeid"):
        np.testing.assert_allclose(getattr(changed, field),
                                   getattr(reference, field), rtol=0, atol=1e-14)
    for field in ("body_mass", "body_inertia", "body_ipos", "body_iquat",
                  "geom_friction", "geom_solref", "geom_solimp"):
        np.testing.assert_allclose(getattr(changed, field),
                                   getattr(original, field), rtol=0, atol=1e-15)
    for z in (radius - .002, radius - 1e-5, radius + 1e-5, radius + .002):
        actual, expected = contacts(changed, z), contacts(reference, z)
        assert len(actual) == len(expected)
        assert [v[0] for v in actual] == [v[0] for v in expected]
        np.testing.assert_allclose([v[1] for v in actual],
                                   [v[1] for v in expected], rtol=0, atol=1e-14)
    assert contacts(changed, radius - .002)
    assert not contacts(changed, radius + .002)


def test_size_only_historical_mutation_misses_real_contact():
    text = xml()
    stale = mujoco.MjModel.from_xml_string(text)
    stale.geom_size[stale.geom("L0_foot").id, 0] = .012
    assert not contacts(stale, .010)
    repaired = _compile_with_foot_radius(text, radius_m=.012)
    assert contacts(repaired, .010)[0][1] == pytest.approx(-.002)


@pytest.mark.parametrize("radius", [-.001, float("nan"), float("inf"), -float("inf")])
def test_invalid_radius_fails_closed(radius):
    with pytest.raises(ValueError, match="finite and >= 0"):
        _compile_with_foot_radius(xml(), radius_m=radius)
    cfg = load_config()
    cfg.setdefault("env", {})["foot_geom_radius_m"] = radius
    with pytest.raises(ValueError, match="finite and >= 0"):
        SimHexapodBalanceEnv(cfg=cfg, randomize=False)


def test_unsupported_or_missing_target_fails_closed():
    box = xml().replace('name="L0_foot" type="sphere" size="0.0045"',
                        'name="L0_foot" type="box" size=".0045 .0045 .0045"')
    with pytest.raises(ValueError, match="sphere geoms only"):
        _compile_with_foot_radius(box, radius_m=.012)
    with pytest.raises(ValueError, match="no named foot spheres"):
        _compile_with_foot_radius(xml().replace("L0_foot", "unrelated"), radius_m=.012)


def test_runtime_helper_rejects_without_partial_mutation():
    model = mujoco.MjModel.from_xml_string(xml())
    old = model.geom_size.copy()
    set_foot_geom_radius(model, 0)
    with pytest.raises(ValueError, match="cannot resize a compiled model"):
        set_foot_geom_radius(model, .012)
    np.testing.assert_array_equal(model.geom_size, old)


@pytest.mark.parametrize("source", ["primitive", "mesh_mjx"])
def test_actual_env_path_compiles_radius_before_data_and_retains_physics(monkeypatch, source):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", source)
    cfg = load_config()
    plain = SimHexapodBalanceEnv(cfg=cfg, randomize=False, seed=0, mesh_visuals=False)
    cfg.setdefault("env", {})["foot_geom_radius_m"] = .012
    changed = SimHexapodBalanceEnv(cfg=cfg, randomize=False, seed=0, mesh_visuals=False)
    try:
        for field in ("body_mass", "body_inertia", "body_ipos", "body_iquat", "geom_friction"):
            np.testing.assert_allclose(getattr(changed.model, field),
                                       getattr(plain.model, field), rtol=0, atol=1e-14)
        for i in range(6):
            gid = changed.model.geom(f"L{i}_foot").id
            assert changed.model.geom_rbound[gid] == pytest.approx(.012)
            np.testing.assert_allclose(changed.model.geom_aabb[gid, 3:], .012)
        changed.reset(seed=0)
        gid = changed.model.geom("L0_foot").id
        mujoco.mj_forward(changed.model, changed.data)
        # Position this actual foot sphere at10mm, between old and new bounds.
        changed.data.qpos[2] += .010 - changed.data.geom_xpos[gid, 2]
        mujoco.mj_forward(changed.model, changed.data)
        foot_contacts = [c for c in changed.data.contact if gid in (c.geom1, c.geom2)]
        assert foot_contacts
        assert min(c.dist for c in foot_contacts) <= -.0019
        changed.reset(seed=0)
        assert changed.model.geom_rbound[gid] == pytest.approx(.012)
    finally:
        plain.close()
        changed.close()


@pytest.mark.parametrize("source", ["primitive", "mesh_mjx"])
def test_default_off_model_and_short_actual_env_trace_are_exact(monkeypatch, source):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", source)
    cfg = load_config()
    absent = SimHexapodBalanceEnv(cfg=cfg, randomize=False, seed=8, mesh_visuals=False)
    cfg.setdefault("env", {})["foot_geom_radius_m"] = 0.0
    zero = SimHexapodBalanceEnv(cfg=cfg, randomize=False, seed=8, mesh_visuals=False)
    try:
        for name in dir(absent.model):
            a = getattr(absent.model, name)
            if isinstance(a, np.ndarray):
                np.testing.assert_array_equal(a, getattr(zero.model, name), err_msg=name)
        x, _ = absent.reset(seed=8)
        y, _ = zero.reset(seed=8)
        np.testing.assert_array_equal(x, y)
        rng = np.random.default_rng(3)
        for _ in range(20):
            action = rng.uniform(-.2, .2, absent.action_space.shape)
            x = absent.step(action)
            y = zero.step(action)
            np.testing.assert_array_equal(x[0], y[0])
            assert x[1:4] == y[1:4]
            np.testing.assert_array_equal(absent.data.qpos, zero.data.qpos)
            np.testing.assert_array_equal(absent.data.qvel, zero.data.qvel)
    finally:
        absent.close()
        zero.close()


def test_shared_model_positive_cfg_is_not_silently_ignored():
    model = build_model(mesh_visuals=False)
    cfg = load_config()
    cfg.setdefault("env", {})["foot_geom_radius_m"] = .012
    with pytest.raises(ValueError, match="shared foot radius must be compiled"):
        SimHexapodBalanceEnv(cfg=cfg, model=model, randomize=False)


@pytest.mark.parametrize("source", ["primitive", "mesh_mjx"])
def test_shared_precompiled_radius_is_accepted_without_mutating_model(monkeypatch, source):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", source)
    from rl_move.sim.mjx_host import prepare_shared_model
    from rl_move.sim.servo_model import SimServoParams
    model = prepare_shared_model(SimServoParams.defaults(), iterations=10,
                                 ls_iterations=10, foot_geom_radius=.0135)
    before = {k: getattr(model, k).copy() for k in
              ("geom_size", "geom_rbound", "geom_aabb", "bvh_aabb",
               "body_mass", "body_inertia", "geom_friction", "geom_solref")}
    cfg = load_config()
    cfg.setdefault("env", {})["foot_geom_radius_m"] = .0135
    shim = SimHexapodBalanceEnv(cfg=cfg, model=model, randomize=False)
    try:
        for field, value in before.items():
            np.testing.assert_array_equal(getattr(model, field), value)
        gid = model.geom("L0_foot").id
        mujoco.mj_forward(model, shim.data)
        shim.data.qpos[2] += .010 - shim.data.geom_xpos[gid, 2]
        mujoco.mj_forward(model, shim.data)
        assert any(gid in (c.geom1, c.geom2) for c in shim.data.contact)
    finally:
        shim.close()


def test_shared_stale_radius_is_rejected_even_if_size_matches():
    model = build_model(mesh_visuals=False)
    for i in range(6):
        model.geom_size[model.geom(f"L{i}_foot").id, 0] = .012
    cfg = load_config()
    cfg.setdefault("env", {})["foot_geom_radius_m"] = .012
    with pytest.raises(ValueError, match="shared foot radius must be compiled"):
        SimHexapodBalanceEnv(cfg=cfg, model=model, randomize=False)
