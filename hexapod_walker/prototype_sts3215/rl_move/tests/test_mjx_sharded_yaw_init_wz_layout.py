"""_shm_layout(yaw_init=...) -- the walkyaw RSI initial-wz curriculum
lever's sharded shared-memory row is allocated on demand, mirroring
the existing seq/handoff allocate-on-demand rules exactly.

Pure host-side dataclass logic, no jax/mujoco-mjx dependency -- runs
everywhere (including this controller sandbox where mjx itself is not
installed), unlike the rest of the mjx_sharded_vec_env test suite.
"""
from __future__ import annotations

from rl_move.sim.mjx_sharded_vec_env import _shm_layout


def _base(**kw):
    return _shm_layout(4, 18, 50, 25, 24, 10, "t", **kw)


def test_default_off_allocates_no_yaw_init_row():
    layout = _base()
    assert "yaw_init_wz" not in layout


def test_yaw_init_true_allocates_one_row_per_env():
    layout = _base(yaw_init=True)
    spec = layout["yaw_init_wz"]
    assert spec.shape == (4,)
    assert spec.dtype == "float64"


def test_yaw_init_independent_of_seq_and_handoff_gates():
    # Each allocate-on-demand feature is independently gated -- arming
    # one must not silently arm (or require) another.
    layout = _base(seq=True, handoff=False, yaw_init=True)
    assert "yaw_init_wz" in layout
    assert "handoff_q" not in layout
    assert "seq_q_plant" in layout

    layout2 = _base(seq=False, handoff=True, yaw_init=False)
    assert "yaw_init_wz" not in layout2
    assert "handoff_q" in layout2
