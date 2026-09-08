"""Bounded Cartesian decoder integration bank; run from prototype root.

No policy, optimizer, checkpoint load, W&B run or training launch.
A real file and main guard are required by MjxShardedVecEnv's spawn workers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
from pathlib import Path
import sys
import time

SOURCE_FILES = (
    "rl_move/sim/cart_foot_decode.py", "rl_move/sim/joint_task.py",
    "rl_move/sim/mjx_host.py", "rl_move/sim/mjx_sharded_vec_env.py",
    "rl_move/sim/mjx_backend.py", "rl_move/sim/sim_env.py",
    "hexapod_core/joint_frame.py", "mesh_mujoco/hexapod_mesh_mjx.xml",
    "rl_move/config.yaml", "rl_move/sim/servo_model.py",
    "rl_move/sim/walk_task.py", "rl_move/sim/goal_task.py", "rl_move/safety.py",
)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recipe", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--expected-hashes", type=Path)
    ap.add_argument("--ticks", type=int, default=130)
    a = ap.parse_args()
    if not 10 <= a.ticks <= 260:
        ap.error("ticks must be in [10, 260]")
    root = Path.cwd()
    if not (root / "rl_move" / "sim").is_dir():
        ap.error("run from the synchronized prototype_sts3215 root")
    sys.path.insert(0, str(root))
    os.environ["HEXAPOD_MODEL_SOURCE"] = "mesh_mjx"
    os.environ["HEXAPOD_CONTROL_HZ"] = "100"
    os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    recipe = json.loads(a.recipe.read_text())
    assert len(recipe["cfg_overrides"]) == 78, "not the reviewed source recipe"
    assert recipe["seed"] == 2 and recipe["dr_scale"] == 0.0
    hashes = {name: file_hash(root / name) for name in SOURCE_FILES}
    expected = json.loads(a.expected_hashes.read_text()) if a.expected_hashes else {}
    for name, digest in expected.items():
        assert hashes.get(name) == digest, f"source mismatch: {name}"
    result = {
        "scope": "Warp runtime + host decode parity; no physics-trajectory parity claim",
        "recipe": recipe, "recipe_sha256": file_hash(a.recipe),
        "bank_sha256": file_hash(__file__),
        "source_sha256": hashes,
        "code_marker": ((root / ".code_sha").read_text().strip()
                        if (root / ".code_sha").exists() else None),
        "n_envs": 4, "host_workers": 2, "pool_per_env": 1,
        "episode_seconds": 1.2, "requested_ticks": a.ticks,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    def timeout_signal(_signum, _frame):
        raise TimeoutError("external bounded timeout")

    signal.signal(signal.SIGTERM, timeout_signal)
    started = time.monotonic()
    v = cpu = None
    try:
        import numpy as np
        import jax
        from rl_move.config import load_config
        from rl_move.sim.train_ppo_sim import _parse_cfg_set
        from rl_move.sim.walk_task import SimHexapodJointWalkEnv
        from rl_move.sim.mjx_sharded_vec_env import MjxShardedVecEnv
        from rl_move.sim.mjx_host import FakeData
        assert jax.default_backend() == "gpu", jax.devices()
        result["jax_devices"] = [str(d) for d in jax.devices()]
        cfg = load_config()
        for key, value in _parse_cfg_set(
                recipe["cfg_overrides"] + recipe["cartesian_overrides"]).items():
            section, leaf = key.split(".", 1)
            cfg.setdefault(section, {})[leaf] = value
        result["resolved_overrides"] = {key: cfg[key.split(".", 1)[0]][key.split(".", 1)[1]]
            for key in _parse_cfg_set(recipe["cfg_overrides"] + recipe["cartesian_overrides"])}
        kw = dict(cfg=cfg, randomize=True, dr_scale=0.0, episode_seconds=1.2)
        cpu = SimHexapodJointWalkEnv(seed=2, **kw)
        assert cpu._model_source == "mesh_mjx" and cpu._cart_foot_active
        print("BUILD Warp, B=4 workers=2; source hashes recorded", flush=True)
        v = MjxShardedVecEnv(
            SimHexapodJointWalkEnv, 4, env_kwargs=kw, seed=2, impl="warp",
            host_workers=2, pool_per_env=1, desync_episodes=False)
        assert v.stepper.impl == "warp" and v.stepper.model_dr
        assert v.get_attr("_model_source") == ["mesh_mjx"] * 4
        assert all(v.get_attr("_cart_foot_active"))
        assert all(isinstance(d, FakeData) for d in v.get_attr("data"))
        parity = []

        def check_decode(label):
            worst = 0.0
            for action in (np.zeros(18), np.linspace(-0.15, 0.15, 18),
                           np.linspace(0.15, -0.15, 18)):
                ref = cpu._act_to_q(action)[0]
                for q, ok, reason in v.env_method("_act_to_q", action):
                    assert ok and reason == ""
                    worst = max(worst, float(np.max(np.abs(q - ref))))
                    np.testing.assert_allclose(q, ref, atol=1e-12, rtol=0)
            parity.append({"phase": label, "max_target_error_rad": worst})

        check_decode("constructor")
        print("RESET: initial pool plus live episode", flush=True)
        obs = v.reset()
        assert np.all(np.isfinite(obs))
        check_decode("after_reset_and_model_dr")
        body_pos = np.asarray(v.stepper._dr_fields["body_pos"])
        result["geometry_dr_max_world_spread_m"] = float(
            np.max(np.ptp(body_pos, axis=0)))
        assert result["geometry_dr_max_world_spread_m"] > 1e-8
        result["initial_pool_counts"] = [len(x) for x in v._pool_dev]
        assert result["initial_pool_counts"] == [1] * 4
        rng = np.random.default_rng(2)
        forced_pops = natural_done = truncations = 0
        max_reward_abs = 0.0
        print("STEP: 130 ticks by default; forced pops at ticks 2 and 6", flush=True)
        for tick in range(a.ticks):
            actions = rng.uniform(-0.025, 0.025, (4, 18)).astype(np.float32)
            force = tick in (2, 6)
            if force:
                actions[0] = np.nan  # existing rejected-action/pool regression route
            obs, rewards, dones, infos = v.step(actions)
            assert np.all(np.isfinite(obs)) and np.all(np.isfinite(rewards))
            max_reward_abs = max(max_reward_abs, float(np.max(np.abs(rewards))))
            if force:
                assert dones[0] and "terminal_observation" in infos[0]
                assert not infos[0].get("TimeLimit.truncated", False)
                forced_pops += 1
                check_decode(f"after_forced_pop_{forced_pops}")
            natural_done += int(np.sum(dones)) - int(force)
            truncations += sum(bool(i.get("TimeLimit.truncated", False)) for i in infos)
            if tick in (7, a.ticks - 1):
                print(f"PROGRESS tick={tick+1} forced_pops={forced_pops} "
                      f"truncations={truncations}", flush=True)
        assert forced_pops == 2  # one-entry pool therefore exercised refill
        check_decode("after_runtime_and_pool_refill")
        # Full reset rebuilds the pool/live choreography using later RNG draws.
        print("RESET again: rebuild pools with later geometry draws", flush=True)
        obs = v.reset()
        assert np.all(np.isfinite(obs))
        check_decode("after_second_full_reset")
        obs, rewards, dones, infos = v.step(np.zeros((4, 18), dtype=np.float32))
        assert np.all(np.isfinite(obs)) and np.all(np.isfinite(rewards))
        result.update(status="PASS", decode_parity=parity, forced_pops=forced_pops,
                      natural_done=natural_done, truncations=truncations,
                      max_reward_abs=max_reward_abs, completed_ticks=a.ticks + 1,
                      exercised="FakeData worker decode; model DR; pool pop/refill; full reset")
        assert {name: file_hash(root / name) for name in SOURCE_FILES} == hashes
        print("PASS: runtime and decode parity; no physics bit-parity claim", flush=True)
    except BaseException as exc:
        result.update(status="FAIL", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        # Close the environment before writing final evidence, even on failure.
        try:
            if v is not None:
                v.close()
        finally:
            if cpu is not None:
                cpu.close()
            result["elapsed_seconds"] = time.monotonic() - started
            a.out.write_text(json.dumps(result, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
