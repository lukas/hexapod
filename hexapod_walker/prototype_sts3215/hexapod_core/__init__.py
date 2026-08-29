"""hexapod_core — the shared robot/sim contract (canonical copies).

Single home for the modules BOTH the robot stack (``linux_control``,
``motor_setup``) and the sim/RL stack (``rl_move``) depend on:

- ``joint_frame``       joint-space conventions (robot absolute-tibia vs
                        MuJoCo femur-relative) and converters
- ``tripod_gait``       leg geometry constants, ``_leg_ik``, the tripod gait
- ``noslip_gait``       world-pinned zero-scrub gait engine
- ``se2_foot_gait``     SE(2) foot-frame gait
- ``walk_ready_transition``  scripted plant-stance transition
- ``sim_gait_compat``   the ONE sim/robot knee-convention boundary
- ``quad_walk``         tip-back quadruped gaits
- ``dance_script``      dance/choreography script compiler

Import as ``from hexapod_core.tripod_gait import ...``. The old module
locations (``linux_control/tripod_gait.py`` etc.) are 6-line legacy
stubs that re-export from here so historical bare imports keep working;
new code must import ``hexapod_core.*``.

Path bootstrap: this package lives directly under the prototype root
(next to ``rl_move``, ``linux_control``, ``motor_setup``) on every
platform — Mac checkout, pod ``/workspace/prototype_sts3215``, robot
``/home/arduino/hexapod_sts``. The insert below makes the sibling
packages importable no matter how the process found ``hexapod_core``,
replacing the dozens of per-file ``sys.path`` shims this package
retired. It is the single sanctioned path shim.
"""
import sys as _sys
from pathlib import Path as _Path

_root = str(_Path(__file__).resolve().parents[1])
if _root not in _sys.path:
    _sys.path.insert(0, _root)
del _sys, _Path, _root
