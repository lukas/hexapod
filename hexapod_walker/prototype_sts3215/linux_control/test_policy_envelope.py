"""rl_policy: the joint envelope a policy runs in on THIS robot = tightest of the runtime cfg,
the artifact's trained envelope (meta["safety"]) and the host's measured stops."""
from __future__ import annotations

import sys
import types
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.safety import SafetyLayer  # noqa: E402
import rl_policy  # noqa: E402


def _policy(meta):
    return types.SimpleNamespace(meta=meta)


def _gate(**safety):
    s = {"max_delta_q_deg": 0.75, "max_roll_deg": 10, "max_pitch_deg": 10}
    s.update(safety)
    return SafetyLayer({"safety": s, "control": {"hz": 50}})


def test_host_stops_apply_even_to_an_artifact_without_a_contract():
    gate = _gate()
    assert rl_policy._apply_policy_envelope(gate, _policy({}), host="hexapod2.local") == (-52.0, 125.0)


def test_trained_envelope_and_host_stops_combine_tightest():
    gate = _gate(hip_min_deg=-52.0, knee_hinge_max_deg=125.0)
    pol = _policy({"safety": {"max_delta_q_deg": 0.75, "hip_min_deg": -45.0, "knee_hinge_max_deg": 130.0}})
    assert rl_policy._apply_policy_envelope(gate, pol, host="hexapod2") == (-45.0, 125.0)


def test_unknown_robot_without_contract_keeps_the_servo_range():
    gate = _gate()
    assert rl_policy._apply_policy_envelope(gate, _policy({}), host="somebot") == (-80.0, 150.0)
    assert rl_policy._policy_envelope(_policy({"safety": {"hip_min_deg": "x"}})) == (None, None)


def test_unstamped_artifact_keeps_the_old_slew_contract_whatever_the_config_says():
    cfg = {"control": {"hz": 100}, "safety": {"max_delta_q_deg": 1.76}}     # today's opened default
    dq, explicit = rl_policy._policy_safety_max_delta_q_deg(_policy({}), cfg, 50.0)
    assert dq == 0.75 and not explicit                                         # 37.5 deg/s at 50 Hz, not 3.52
    dq, explicit = rl_policy._policy_safety_max_delta_q_deg(_policy({"safety": {"max_delta_q_deg": 3.52}}), cfg, 50.0)
    assert dq == 3.52 and explicit
