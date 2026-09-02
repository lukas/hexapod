"""Strict deployed-policy profile and coordinate-contract tests."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "linux_control") not in sys.path:
    sys.path.insert(0, str(ROOT / "linux_control"))

import rl_policy  # noqa: E402
from hexapod_core.joint_frame import (  # noqa: E402
    FRAME_ROBOT_ABS, JOINT_CONTRACT,
)


def _policy(**meta):
    return SimpleNamespace(meta={
        "joint_frame": FRAME_ROBOT_ABS,
        "joint_contract": JOINT_CONTRACT,
        **meta,
    })


def test_profile_is_exactly_the_declared_training_profile():
    stand = {"hold_s": 5, "ramp_s": 6, "target_m": 0.111,
             "total_s": 12.5}
    policy = _policy(profile={"stand": stand})
    assert rl_policy.policy_profile(policy, "stand") == stand


@pytest.mark.parametrize("profile", [None, {}, {"stand": {}},
    {"stand": {"hold_s": 5, "ramp_s": 6, "target_m": 0.111}}])
def test_missing_or_partial_profile_is_rejected(profile):
    with pytest.raises(ValueError, match="profile"):
        rl_policy.policy_profile(_policy(profile=profile), "stand")


def test_noncanonical_policy_metadata_is_rejected():
    for meta in ({}, {"joint_frame": FRAME_ROBOT_ABS},
                 {"joint_frame": "model_rel",
                  "joint_contract": JOINT_CONTRACT}):
        with pytest.raises(ValueError):
            rl_policy.policy_joint_frame(SimpleNamespace(meta=meta))
