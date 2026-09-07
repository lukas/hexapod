"""Hardware-runner integration tests for portable walk artifacts."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT
from rl_move.np_policy import ARCH_DUAL_GRU, MODE_ONEHOT_ORDER, pack_f32

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "linux_control") not in sys.path:
    sys.path.insert(0, str(_ROOT / "linux_control"))

import rl_policy  # noqa: E402
from api.rl import RlApi  # noqa: E402


def _zeros(shape) -> dict:
    return pack_f32(np.zeros(shape, dtype=np.float32))


def _tiny_dual_gru_payload() -> dict:
    hidden = 2
    core = {
        "weight_ih": _zeros((3 * hidden, 81)),
        "weight_hh": _zeros((3 * hidden, hidden)),
        "bias_ih": pack_f32(np.array([0, 0, 0, 0, 1, 1], np.float32)),
        "bias_hh": _zeros((3 * hidden,)),
    }
    head = {
        "W1": _zeros((2, hidden)), "b1": _zeros((2,)),
        "W2": _zeros((2, 2)), "b2": _zeros((2,)),
        "Wout": _zeros((18, 2)), "bout": _zeros((18,)),
    }
    return {
        "meta": {
            "obs_dim": 81,
            "act_dim": 18,
            "activation": "tanh",
            "architecture": ARCH_DUAL_GRU,
            "training_hz": 100.0,
            "phase_hz": 1.333333,
            "walk_yaw_cmd": True,
            "walk_phase_run_on_yaw": True,
            "mode_onehot_order": list(MODE_ONEHOT_ORDER),
            "recurrent_hidden_size": hidden,
            "joint_frame": FRAME_ROBOT_ABS,
            "joint_contract": JOINT_CONTRACT,
        },
        "dual_gru": {
            "core_a": core,
            "core_b": core,
            "head_a": head,
            "head_b": head,
        },
    }


def test_runner_walk_tails_cover_phase_yaw_and_mode():
    obs75 = rl_policy._walk_obs_tail(  # noqa: SLF001
        75, 0.06, -0.03, math.pi / 2, 0.25)
    np.testing.assert_allclose(
        obs75, [0.4, -0.2, 0.4, -0.2, 1.0, 0.0, 0.5], atol=1e-7)

    hold81 = rl_policy._walk_obs_tail(  # noqa: SLF001
        81, 0.0, 0.0, 0.0, 0.0, mode="hold")
    walk81 = rl_policy._walk_obs_tail(  # noqa: SLF001
        81, 0.0, 0.0, 0.0, 0.0, mode="walk")
    np.testing.assert_array_equal(hold81[-6:], [1, 0, 0, 0, 0, 0])
    np.testing.assert_array_equal(walk81[-6:], [0, 0, 0, 1, 0, 0])


def test_runner_yaw_only_drive_uses_each_yaw_capable_contract():
    for obs_dim in (75, 81, 93):
        assert rl_policy._drive_command_is_moving(  # noqa: SLF001
            0.0, 0.0, 0.01, walk_obs=obs_dim)


def test_robot_picker_and_roles_expose_new_contracts():
    assert RlApi._SLOT_OBS[75] == "walk"  # noqa: SLF001
    assert RlApi._SLOT_OBS[81] == "walk"  # noqa: SLF001
    assert 75 in RlApi._ROLE_OBS["walk"]  # noqa: SLF001
    assert 81 in RlApi._ROLE_OBS["hold"]  # noqa: SLF001
    assert 81 not in RlApi._ROLE_OBS["stand"]  # noqa: SLF001
    for obs_dim in (72, 74):
        assert not rl_policy._drive_command_is_moving(  # noqa: SLF001
            0.0, 0.0, 0.01, walk_obs=obs_dim)


def test_runner_loads_dual_gru_and_resets_only_at_episode_boundary(tmp_path):
    artifact = tmp_path / "unified.json"
    artifact.write_text(json.dumps(_tiny_dual_gru_payload()))
    slot_copy = tmp_path / "rl_walk_weights.json"
    slot_copy.write_bytes(artifact.read_bytes())

    walk = rl_policy.NumpyPolicy(slot_copy)
    assert walk.recurrent is True
    obs = np.zeros(81, dtype=np.float32)
    obs[-3] = 1.0  # walk slot in the frozen one-hot tail
    assert walk.act(obs).shape == (18,)
    assert np.linalg.norm(walk._model.h_a) > 0.0  # noqa: SLF001

    hold = rl_policy._load_drive_hold_policy(  # noqa: SLF001
        slot_copy, walk, artifact)
    assert hold is walk
    hold.act(obs)
    walk.reset()
    np.testing.assert_array_equal(walk._model.h_a, np.zeros(2))  # noqa: SLF001
    np.testing.assert_array_equal(walk._model.h_b, np.zeros(2))  # noqa: SLF001
