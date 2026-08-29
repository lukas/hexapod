"""PENDING_SLOTS ring-buffer sizing vs control.hz (mjx_backend.py).

Regression for the LAUNCH_CRASH hit three times (standwalk-stance-mesh1
08-25, walkcurr decleg-sv/central-sv wave 08-29): ``bus.servo_params=
loaded`` measures ~85-106 ms per-axis latency (up to ~190 ms with DR
latency_scale <= 1.8). ``set_tick_params`` requires
``PENDING_SLOTS * dt_ctrl >= 2 * max_latency`` so the ring buffer never
overwrites a not-yet-matured pending write. ``PENDING_SLOTS`` was a
module constant sized for the 25 Hz-era tick (dt_ctrl=0.04s); the
08-24 mesh/100Hz default flip (dt_ctrl=0.01s) shrank the buffer's real
time window 4x with no corresponding bump, so any 100Hz run with
loaded-servo latency crashed in ``set_tick_params`` before a single
training step (0 steps, no science — a LAUNCH_CRASH, not a FAIL).
PENDING_SLOTS=40 restores >=2x margin at 100Hz (40*10ms=400ms >=
2*190ms) while keeping legacy 25Hz margin. Skipped where jax/mjx isn't
installed (controller sandbox); runs for real on any pod (train pods
all have jax/mjx).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

_PROTO = Path(__file__).resolve().parents[2]
if str(_PROTO) not in sys.path:
    sys.path.insert(0, str(_PROTO))

from rl_move.sim.mjx_backend import mjx_is_available  # noqa: E402

if not mjx_is_available():  # pragma: no cover
    pytest.skip("mujoco-mjx / jax not installed", allow_module_level=True)

from rl_move.sim.mjx_backend import MjxTickStepper, PENDING_SLOTS  # noqa: E402
from rl_move.sim.servo_model import N_JOINTS, SimServoParams  # noqa: E402
import jax.numpy as jnp  # noqa: E402


def _fake_stepper():
    """A bare MjxTickStepper with only what set_tick_params touches."""
    s = object.__new__(MjxTickStepper)
    s._jnp = jnp
    return s


def _tp_for(latency_s: float, n_envs: int = 1) -> dict:
    return dict(
        latency_s=np.full((n_envs, N_JOINTS), latency_s, np.float32),
        deadband=np.zeros((n_envs, N_JOINTS), np.float32),
        vel_max=np.ones((n_envs, N_JOINTS), np.float32),
        imu_off=np.zeros((n_envs, 3), np.float32),
    )


def test_pending_slots_covers_loaded_latency_at_100hz():
    # Real "loaded" fit measured max per-axis latency (~106-125 ms
    # depending on axis) — the exact scenario that crashed both the
    # standwalk mesh1 and walkcurr decleg-sv/central-sv launches.
    loaded = SimServoParams.load()
    loaded_alt = SimServoParams.from_cfg({"bus": {"servo_params": "loaded"}})
    max_lat = float(max(loaded.per_joint("latency_ms").max(),
                        loaded_alt.per_joint("latency_ms").max())) / 1000.0
    s = _fake_stepper()
    s.set_tick_params(_tp_for(max_lat), dt_ctrl=0.01)  # must not raise


def test_pending_slots_still_covers_dr_scaled_worst_case():
    # Documented worst case: ~190 ms (loaded latency x DR latency_scale
    # <= 1.8). Must still clear the 2x margin at the 100 Hz floor.
    s = _fake_stepper()
    s.set_tick_params(_tp_for(0.190), dt_ctrl=0.01)  # must not raise


def test_pending_slots_still_refuses_a_genuinely_too_large_latency():
    # The guard must still fire for latencies actually beyond the
    # buffer's real margin — this isn't a "raise the ceiling to
    # infinity" fix.
    s = _fake_stepper()
    too_big = (PENDING_SLOTS * 0.01) / 2.0 + 0.05
    with pytest.raises(ValueError, match="pending-command slots"):
        s.set_tick_params(_tp_for(too_big), dt_ctrl=0.01)


def test_pending_slots_legacy_25hz_margin_unchanged():
    # 25 Hz-era dt: was fine before, must stay fine (bit-exact
    # behavior for every already-passing legacy-rate recipe).
    s = _fake_stepper()
    s.set_tick_params(_tp_for(0.190), dt_ctrl=0.04)  # must not raise
