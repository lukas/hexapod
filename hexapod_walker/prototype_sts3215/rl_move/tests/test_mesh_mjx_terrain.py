"""Mesh-mjx twin rough-terrain support (2026-09-24 adaptive-walker campaign).

The checked-in GPU twin (hexapod_mesh_mjx.xml) ships a flat plane; rough
terrain (env.terrain_amp > 0) swaps it for the primitive model's
``terrain`` hfield via _apply_mjx_twin_hfield. Default flat path must
stay bit-exact (no hfield, plane untouched).
"""
import mujoco
import numpy as np
import pytest

from rl_move.sim.servo_model import build_model

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


def _twin(**kw):
    # mesh resolves to the primitive-collision twin on machines without
    # the generated full-mesh assets (pods/CI); mesh_mjx forces it.
    return build_model(source="mesh_mjx", **kw)


def test_flat_default_has_no_hfield_bit_exact():
    m = _twin(flat_terrain=True)
    assert m.nhfield == 0  # XML untouched: plane floor only
    gid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "terrain")
    assert gid >= 0 and m.geom_type[gid] == mujoco.mjtGeom.mjGEOM_PLANE


def test_terrain_builds_hfield_populated():
    m = _twin(flat_terrain=False, terrain_amp=1.0, terrain_seed=3)
    hf = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_HFIELD, "terrain")
    assert hf >= 0
    gid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "terrain")
    assert m.geom_type[gid] == mujoco.mjtGeom.mjGEOM_HFIELD
    # friction / conaffinity contract preserved from the plane
    assert m.geom_friction[gid][0] == pytest.approx(1.5)
    assert m.geom_conaffinity[gid] == 5
    # 48x48 twin grid (104 mm cells) — keeps every fitted-primitive geom
    # under MuJoCo-Warp's 50-prism hfield narrowphase buffer (<=25 cells/geom).
    data = m.hfield_data
    assert data.size == 48 * 48
    # downsampled from the native 128x128 map: near-full range kept,
    # exact 1.0 peak cell may fall between coarse samples
    assert 0.5 < float(data.max()) <= 1.0
    # spawn region stays flat (heightmap fades in from ~0.32 m):
    # every cell whose center lies within 0.3 m of the origin is zero
    nrow = int(m.hfield_nrow[hf]); ncol = int(m.hfield_ncol[hf])
    grid = np.asarray(data[:nrow * ncol]).reshape(nrow, ncol)
    half = float(m.hfield_size[hf][0])
    xs = np.linspace(-half, half, ncol)
    ys = np.linspace(-half, half, nrow)
    X, Y = np.meshgrid(xs, ys, indexing="xy")
    R = np.hypot(X, Y)
    assert float(np.abs(grid[R < 0.30]).max()) < 1e-6
    # model still steps
    d = mujoco.MjData(m)
    mujoco.mj_step(m, d)


def test_terrain_amp_scales_z_extent_above_one():
    m1 = _twin(flat_terrain=False, terrain_amp=1.0, terrain_seed=0)
    m2 = _twin(flat_terrain=False, terrain_amp=2.0, terrain_seed=0)
    h1 = mujoco.mj_name2id(m1, mujoco.mjtObj.mjOBJ_HFIELD, "terrain")
    h2 = mujoco.mj_name2id(m2, mujoco.mjtObj.mjOBJ_HFIELD, "terrain")
    assert m2.hfield_size[h2][2] == pytest.approx(2.0 * m1.hfield_size[h1][2])
