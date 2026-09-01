"""hexapod_core — the shared robot/sim contract (canonical copies).

Single home for the modules BOTH the robot stack (``linux_control``,
``motor_setup``) and the sim/RL stack (``rl_move``) depend on:

- ``joint_frame``       canonical robot coordinates and the private MuJoCo
                        boundary conversion
- ``tripod_gait``       leg geometry constants, ``_leg_ik``, the tripod gait
- ``noslip_gait``       world-pinned zero-scrub gait engine
- ``se2_foot_gait``     SE(2) foot-frame gait
- ``middle_tuck_quad_gait``  level four-leg crawl with middle pair tucked
- ``walk_ready_transition``  scripted plant-stance transition
- ``quad_walk``         tip-back quadruped gaits
- ``dance_script``      dance/choreography script compiler

Import as ``from hexapod_core.tripod_gait import ...``. The former duplicate
and re-export locations were removed; all code imports ``hexapod_core.*``.

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
