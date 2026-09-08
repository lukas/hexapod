"""RL stack for prototype_sts3215: sim envs, trainers, evals, orchestrator.

See ``../RL_PLAN.md``.

Path bootstrap (the ONE shim for this package): rl_move modules import the
robot-side helpers by bare module name -- ``feetech_bus`` / ``inplace_demos``
from ``motor_setup/`` and ``motor_dynamics`` / ``imu_calibrate`` /
``mcu_feetech_bus`` from ``linux_control/`` -- because those trees also run
on the Uno Q, where the systemd unit puts them on ``PYTHONPATH`` as flat
directories. On the Mac the editable install (repo-root pyproject.toml)
already provides these directories; on the CoreWeave pods the trainers run
as ``python -m rl_move.sim.<module>`` from ``/workspace/prototype_sts3215``
with nothing but the cwd on ``sys.path``. Appending the two sibling
directories (plus ``rl_move/orchestrator``, whose scripts import each other
by bare name) here, when the package is first imported, is what lets every
``rl_move`` module drop its own per-file ``sys.path.insert`` block. The set
is identical to the editable-install .pth and pytest.ini ``pythonpath``.
``hexapod_core/__init__.py`` does the same for the prototype root.
"""
import sys as _sys
from pathlib import Path as _Path

__all__ = ["__version__"]
__version__ = "0.1.0"

_proto = _Path(__file__).resolve().parents[1]
for _d in (_proto, _proto / "linux_control", _proto / "motor_setup",
           _proto / "rl_move" / "orchestrator"):
    _s = str(_d)
    if _s not in _sys.path:
        _sys.path.append(_s)
del _sys, _Path, _proto, _d, _s
