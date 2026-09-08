"""Cartesian foot-placement action decode (walkcurr, 2026-09-08).

Bank for the ``goal.walk_cart_foot_box_{x,y,z}_m`` mechanism
(rl_move/sim/cart_foot_decode.py + the SimHexapodJointGoalEnv branch):

* mesh-accuracy of the derived analytic leg FK vs MuJoCo site FK
  in the pitch-axis frame, to numerical precision on nominal geometry;
  hidden per-episode geometry DR remains intentionally unobserved;
* zero-action parity with the lineage joint-box decode's a=0 pose;
* decode totality (finite, within axis limits, for any action) and
  self-consistency (in-range targets are hit exactly by its own FK);
* default-off bit-exactness (keys absent AND keys=0.0 both skip the
  branch; the legacy box decode is untouched);
* runtime/reset behavior + SafetyLayer joint-rate contract on the
  mesh twin walk env with the mechanism ON;
* pure-host determinism (the CPU/Warp stacks share this exact host
  decode path via _step_begin, so determinism here IS the parity
  contract; the Warp runtime itself is smoke-verified on a GPU pod).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

mujoco = pytest.importorskip("mujoco")

from rl_move.robot_state import DEG2RAD  # noqa: E402
from rl_move.sim import servo_model as SM  # noqa: E402

BIAS = {"joint_action_bias_yaw_deg": 0.0,
        "joint_action_bias_hip_deg": 40.0,
        "joint_action_bias_knee_deg": 35.0}
BOX = {"joint_action_box_yaw_deg": 15.0,
       "joint_action_box_hip_deg": 20.0,
       "joint_action_box_knee_deg": 25.0}
CART = {"walk_cart_foot_box_x_m": 0.06,
        "walk_cart_foot_box_y_m": 0.035,
        "walk_cart_foot_box_z_m": 0.04}

_JLO = np.array([-35.0, -80.0, -20.0] * 6) * DEG2RAD
_JHI = np.array([35.0, 40.0, 150.0] * 6) * DEG2RAD


def _center_q():
    from rl_move.sim.joint_task import action_to_q_rad
    half = np.array([35.0, 60.0, 85.0] * 6) * DEG2RAD
    bias = np.clip(np.array([0.0, 40.0, 35.0] * 6) * DEG2RAD / half,
                   -1.0, 1.0)
    return action_to_q_rad(bias)


@pytest.fixture(scope="module")
def mesh_model():
    return SM.build_model(source="mesh_mjx")


@pytest.fixture(scope="module")
def decoder(mesh_model):
    from rl_move.sim.cart_foot_decode import CartFootDecoder
    return CartFootDecoder(mesh_model, _center_q(),
                           [CART["walk_cart_foot_box_x_m"],
                            CART["walk_cart_foot_box_y_m"],
                            CART["walk_cart_foot_box_z_m"]])


def test_fk_matches_mujoco_mesh_twin(mesh_model, decoder):
    err = decoder.verify_fk(mesh_model, n=200, seed=0)
    # Lateral foot offsets must not rotate the frame away from the pitch plane.
    assert err < 1e-9, f"analytic FK diverges from mesh twin: {err} m"


def test_zero_action_reproduces_source_stance(decoder):
    q0 = decoder.decode(np.zeros(18))
    assert np.max(np.abs(q0 - decoder.center_q)) < 1e-9


def test_decode_total_and_within_limits(decoder):
    rng = np.random.default_rng(1)
    for _ in range(300):
        a = rng.uniform(-1.0, 1.0, 18)
        q = decoder.decode(a)
        assert np.all(np.isfinite(q))
        assert np.all(q >= _JLO - 1e-9) and np.all(q <= _JHI + 1e-9)
    for corner in (np.ones(18), -np.ones(18)):
        q = decoder.decode(corner)
        assert np.all(np.isfinite(q))
        assert np.all(q >= _JLO - 1e-9) and np.all(q <= _JHI + 1e-9)


def test_decode_self_consistent_on_reachable_targets(decoder):
    """Targets inside the box whose IK needs no clipping are hit
    EXACTLY by the decoder's own FK (parameterization consistency)."""
    rng = np.random.default_rng(2)
    checked = 0
    for _ in range(500):
        a = rng.uniform(-1.0, 1.0, 18)
        q = decoder.decode(a)
        target = decoder.center_p + a.reshape(6, 3) * decoder.box[None, :]
        hit = decoder.fk(q)
        # only score legs where no limit/annulus clip engaged
        for leg in range(6):
            ql = q[leg * 3: leg * 3 + 3]
            if np.any(np.abs(ql - _JLO[leg * 3:leg * 3 + 3]) < 1e-7) or \
               np.any(np.abs(ql - _JHI[leg * 3:leg * 3 + 3]) < 1e-7):
                continue
            err = float(np.linalg.norm(hit[leg] - target[leg]))
            assert err < 1e-9, f"leg {leg}: unclipped IK missed by {err}"
            checked += 1
    assert checked > 500, f"too few unclipped legs exercised: {checked}"


def _walk_env(extra_goal: dict, seed: int = 0):
    # the suite-wide conftest pins HEXAPOD_MODEL_SOURCE=primitive (legacy
    # behavior tests); the mechanism's lineage is mesh_mjx — callers
    # monkeypatch the env var before building.
    from rl_move.config import load_config
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = load_config()
    cfg.setdefault("env", {})["model_source"] = "mesh_mjx"
    cfg.setdefault("control", {})["hz"] = 100
    g = cfg.setdefault("goal", {})
    g["walk_pure"] = 1
    g["walk_speed_min_m_s"] = 0.06
    g["walk_speed_max_m_s"] = 0.06
    g["walk_heading_max_rad"] = 0.0
    g.update(BIAS); g.update(BOX); g.update(extra_goal)
    cfg.setdefault("safety", {})["max_delta_q_deg"] = 3.6
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=False,
        dr_scale=0.0, episode_seconds=4.0, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env


def test_default_off_bit_exact(monkeypatch):
    """Keys absent and keys=0.0 take the identical legacy decode path
    and produce identical rollouts."""
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    zeros = {k: 0.0 for k in CART}
    env_a = _walk_env({}, seed=7)
    env_b = _walk_env(zeros, seed=7)
    assert not env_a._cart_foot_active
    assert not env_b._cart_foot_active
    rng = np.random.default_rng(3)
    obs_a, _ = env_a.reset(seed=7)
    obs_b, _ = env_b.reset(seed=7)
    assert np.array_equal(obs_a, obs_b)
    for _ in range(30):
        act = rng.uniform(-1, 1, 18).astype(np.float32)
        oa, ra, ta, tra, _ = env_a.step(act)
        ob, rb, tb, trb, _ = env_b.step(act)
        assert np.array_equal(oa, ob) and ra == rb
        assert ta == tb and tra == trb
        if ta:
            break


def test_runtime_reset_and_joint_rate(monkeypatch):
    """Mechanism ON: episodes run/reset cleanly and the commanded
    target NEVER violates the SafetyLayer per-tick slew contract."""
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    env = _walk_env(dict(CART), seed=11)
    assert env._cart_foot_active
    max_dq = 3.6 * DEG2RAD + 1e-9
    rng = np.random.default_rng(4)
    for ep in range(2):
        obs, _ = env.reset(seed=11 + ep)
        assert np.all(np.isfinite(obs))
        last_cmd = None
        for _ in range(60):
            act = rng.uniform(-1, 1, 18).astype(np.float32)
            obs, r, term, trunc, info = env.step(act)
            assert np.all(np.isfinite(obs)) and np.isfinite(r)
            cmd = env._cmd.copy()
            if last_cmd is not None and not term:
                assert np.max(np.abs(cmd - last_cmd)) <= max_dq
            last_cmd = cmd
            if term or trunc:
                break


def test_decode_deterministic_across_instances(mesh_model):
    """Pure-host decode: two independent instances agree bit-for-bit
    (the CPU and Warp stacks share this host-side path)."""
    from rl_move.sim.cart_foot_decode import CartFootDecoder
    box = [CART["walk_cart_foot_box_x_m"], CART["walk_cart_foot_box_y_m"],
           CART["walk_cart_foot_box_z_m"]]
    d1 = CartFootDecoder(mesh_model, _center_q(), box)
    d2 = CartFootDecoder(SM.build_model(source="mesh_mjx"),
                         _center_q(), box)
    rng = np.random.default_rng(5)
    for _ in range(50):
        a = rng.uniform(-1, 1, 18)
        assert np.array_equal(d1.decode(a), d2.decode(a))


def test_nonparallel_pitch_pair_fail_closed():
    """Reject an actually nonparallel pitch pair, independent of leg-frame choice."""
    from rl_move.sim.cart_foot_decode import CartFootDecoder
    model = SM.build_model(source="mesh_mjx")
    jk = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "L0_knee")
    model.jnt_axis[jk] = [1.0, 0.0, 0.0]
    with pytest.raises(ValueError, match="planar decode unsupported"):
        CartFootDecoder(model, _center_q(), [0.05, 0.05, 0.05])
