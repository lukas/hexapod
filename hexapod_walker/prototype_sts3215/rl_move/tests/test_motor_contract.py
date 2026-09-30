"""Motor-contract logging + resolved-ceiling integration (fb_20260820T000059).

After the steer5-fastprof1 profile-headroom canary the operator's
follow-up note asked for two guarantees:

1. every train/eval path RECORDS the resolved motor contract
   (bus.write_speed / write_acc / servo_vel_max_counts_s, the resolved
   vel_max_deg_s ceiling, safety.max_delta_q_deg, control.hz, backend
   profile mode) — servo_model.motor_contract();
2. integration proof that the TRAINER paths see the resolved velocity
   ceiling — not just SimServoParams.from_cfg in isolation.

Writing these found (and now guards against) two real latent gaps:
train_ppo_sim._build_env only re-resolved params when bus.servo_params
was set (a vel-ceiling-only run through the CPU trainer would have
silently trained WITHOUT the raise), and MjxVecEnv resolved default
params via load() instead of from_cfg (the sharded env already did it
right). Both fixed 08-20, bit-exact when the overrides are absent.
"""
import numpy as np
import pytest

from rl_move.config import load_config
from rl_move.sim.servo_model import (
    COUNTS_PER_DEG, SimServoParams, motor_contract, motor_contract_line)

RAISED = {"bus": {"servo_vel_max_counts_s": "write_speed",
                  "write_speed": 1500, "write_acc": 80},
          "safety": {"max_delta_q_deg": 5.0}}


# ---------------------------------------------------------------- helper

def test_contract_default_reports_stock_config(monkeypatch):
    # This test's whole point is the REAL config.yaml stock value, not
    # this suite's HEXAPOD_SAFETY_MAX_DELTA_Q_DEG pin (2026-09-30,
    # tests/conftest.py -- pins the PRIMITIVE-family calibrated suite
    # back to the legacy 0.375 slew; irrelevant here, same reasoning as
    # why HEXAPOD_CONTROL_HZ is deliberately never set by conftest).
    monkeypatch.delenv("HEXAPOD_SAFETY_MAX_DELTA_Q_DEG", raising=False)
    c = motor_contract()
    base = SimServoParams.load().per_joint("vel_max_deg_s")
    # 2026-09-27: stock config = the 2000/80 write contract with the
    # ceiling tied to write_speed.
    assert c["bus.write_speed"] == 2000.0
    assert c["bus.write_acc"] == 80.0
    assert c["bus.servo_vel_max_counts_s"] == "write_speed"
    assert c["resolved_vel_max_counts_s_max"] == pytest.approx(2000.0)
    # 2026-08-24 100 Hz flip (fb_20260824T174619_c49b7e): rate x4,
    # per-tick slew /4 — the PHYSICAL 37.5 deg/s contract is unchanged.
    assert c["control.hz"] == 100.0
    assert c["safety.max_delta_q_deg"] == 1.76   # 2026-09-27: slew follows the 2000-count bus (175.8 deg/s)
    assert c["slew_limit_deg_s"] == pytest.approx(176.0)   # 1.76 deg/tick x 100 Hz = the 2000-count bus
    assert c["resolved_vel_max_deg_s_max"] == pytest.approx(base.max())
    assert c["backend_profile"] == "servo_profile_np"


def test_contract_reports_raised_profile():
    c = motor_contract(RAISED)
    assert c["bus.write_speed"] == 1500.0
    assert c["bus.servo_vel_max_counts_s"] == "write_speed"
    assert c["resolved_vel_max_counts_s_max"] == pytest.approx(1500.0)
    assert c["resolved_vel_max_deg_s_min"] == pytest.approx(
        1500.0 / COUNTS_PER_DEG)
    assert c["slew_limit_deg_s"] == pytest.approx(500.0)
    assert "+vel_max=1500cps" in c["servo_params_source"]


def test_contract_uses_given_params_not_reresolved():
    # When a path hands over its ACTUAL params object, the contract
    # must report that object's ceiling (ground truth), even if cfg
    # would resolve differently.
    stale = SimServoParams.load()
    c = motor_contract(RAISED, params=stale)
    assert c["resolved_vel_max_counts_s_max"] == pytest.approx(
        stale.per_joint("vel_max_deg_s").max() * COUNTS_PER_DEG)
    # ...while the cfg fields still tell the requested story — so a
    # mismatch between requested and resolved is VISIBLE in the log.
    assert c["bus.write_speed"] == 1500.0


def test_contract_line_is_greppable():
    line = motor_contract_line(motor_contract(RAISED))
    assert line.startswith("[motor-contract] ")
    assert "write_speed=1500" in line and "1500 counts/s" in line


def test_contract_fail_closed_on_bad_override():
    with pytest.raises(ValueError):
        motor_contract({"bus": {"servo_vel_max_counts_s": "fast"}})


# ------------------------------------------- trainer path integration

CFG_SET = ["bus.write_speed=1500", "bus.write_acc=80",
           "bus.servo_vel_max_counts_s=write_speed",
           "safety.max_delta_q_deg=5.0"]


def test_train_ppo_sim_build_env_resolves_ceiling():
    """CPU-trainer path: _build_env must re-resolve params from cfg for
    ANY bus.* override — a vel-ceiling-only cfg-set raises the env's
    actuator ceiling even though callers pass stale params."""
    from rl_move.sim import train_ppo_sim as T

    class Args:  # minimal _build_env surface
        cfg_set = list(CFG_SET)
        no_dr = True
        dr_scale = 0.0
        episode_seconds = 5
        friction_range = None
        goal_mix = None

    captured = {}

    def fake_env_cls(**kw):
        captured.update(kw)

        class E:
            _goal_gen = None
        return E()

    stale = SimServoParams.load()
    T._build_env(fake_env_cls, stale, Args())
    got = captured["params"].per_joint("vel_max_deg_s")
    assert np.allclose(got, 1500.0 / COUNTS_PER_DEG), (
        "bus.servo_vel_max_counts_s did not reach the training env")


def test_train_ppo_sim_build_env_default_bit_exact():
    from rl_move.sim import train_ppo_sim as T

    class Args:
        cfg_set = ["reward.k_drag_loaded=10.0"]  # overrides, no bus.*
        no_dr = True
        dr_scale = 0.0
        episode_seconds = 5
        friction_range = None
        goal_mix = None

    captured = {}

    def fake_env_cls(**kw):
        captured.update(kw)

        class E:
            _goal_gen = None
        return E()

    stale = SimServoParams.load()
    T._build_env(fake_env_cls, stale, Args())
    # Since 2026-09-27 the stock config itself pins the ceiling sentinel
    # (bus.servo_vel_max_counts_s=write_speed), so _build_env re-resolves
    # params from cfg on every path; object identity is no longer the
    # contract. The guarantee that matters: a non-bus override must not
    # CHANGE the resolved actuator set vs. the stock config.
    got = captured["params"]
    stock = SimServoParams.from_cfg(load_config())
    for ax in ("yaw", "hip", "knee"):
        assert got.axes[ax] == stock.axes[ax], (ax, got.axes[ax], stock.axes[ax])
    assert np.allclose(got.per_joint("vel_max_deg_s"),
                       stale.per_joint("vel_max_deg_s"))


def test_train_ppo_mjx_env_kwargs_resolves_ceiling():
    """MJX/warp trainer path: _env_kwargs resolves the run's params via
    from_cfg — the TickParams.vel_max source — so the raised ceiling
    reaches GPU training (this is the path steer5-fastprof1 used)."""
    from rl_move.sim import train_ppo_mjx as M

    class Args:
        cfg_set = list(CFG_SET)
        no_dr = True
        dr_scale = 0.0
        episode_seconds = 5
        training_episode_seconds = 5
        recover_cert_every = 0
        recover_cert_envs = 0
        goal_mix = None

    kw = M._env_kwargs(Args())
    got = kw["params"].per_joint("vel_max_deg_s")
    assert np.allclose(got, 1500.0 / COUNTS_PER_DEG)


def test_vec_env_default_params_use_from_cfg():
    """MjxVecEnv + MjxShardedVecEnv resolve default params from the
    env_kwargs cfg (from_cfg), never bare load() — source guard, since
    constructing either needs jax/GPU."""
    import inspect

    from rl_move.sim import mjx_sharded_vec_env, mjx_vec_env
    for mod in (mjx_vec_env, mjx_sharded_vec_env):
        src = inspect.getsource(mod)
        assert 'setdefault("params", SimServoParams.load())' not in src, (
            f"{mod.__name__}: default params bypass cfg resolution")
        assert 'SimServoParams.from_cfg(env_kwargs.get("cfg"))' in src, (
            f"{mod.__name__}: expected from_cfg default-params resolution")


def test_eval_checkpoint_records_contract():
    """Eval path: report.json carries motor_contract, resolved from the
    same cfg the eval envs are built from (source guard)."""
    import inspect

    from rl_move.sim import eval_checkpoint as E
    src = inspect.getsource(E)
    assert '"motor_contract": contract' in src
    assert 'motor_contract(cfg_kw.get("cfg")' in src
    assert 'params=SimServoParams.from_cfg(kw.get("cfg"))' in src


def test_trainers_log_contract():
    import inspect

    from rl_move.sim import train_ppo_mjx as M
    from rl_move.sim import train_ppo_sim as T
    assert 'config["motor_contract"]' in inspect.getsource(T._init_wandb)
    assert '"motor_contract": _contract' in inspect.getsource(M._init_wandb)
