"""The joint-ordering contract (hexapod_core/joint_frame.py) is executable.

Four locks: the indexing API round-trips; the MuJoCo model's hinge order
is the contract order under the sim-name alias; the tracker submodule
spells the 18 names identically; and no non-test source file under
prototype_sts3215 hand-rolls ``3 * leg + k`` or the ``j + 2`` servo-ID
idiom any more.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import pytest

from hexapod_core import joint_frame as JF

PROTO = Path(__file__).resolve().parents[2]
MJX_XML = PROTO / "mesh_mujoco" / "hexapod_mesh_mjx.xml"


def test_round_trip_over_all_18_joints():
    assert JF.N_LEGS == 6 and JF.AXES == ("yaw", "hip", "knee")
    assert JF.N_JOINTS == 18 and len(JF.JOINT_NAMES) == 18
    seen = []
    for leg in range(JF.N_LEGS):
        assert JF.leg_slice(leg) == slice(3 * leg, 3 * leg + 3)
        assert JF.leg_joints(leg) == tuple(range(3 * leg, 3 * leg + 3))
        for k, axis in enumerate(JF.AXES):
            j = JF.joint_index(leg, axis)
            assert j == JF.joint_index(leg, k) == 3 * leg + k
            assert (JF.leg_of(j), JF.axis_of(j)) == (leg, axis)
            assert JF.JOINT_NAMES[j] == f"L{leg}_{axis}"
            assert JF.joint_of_name(JF.JOINT_NAMES[j]) == j
            assert JF.joint_of_name(JF.SIM_JOINT_NAMES[j]) == j
            sid = JF.servo_id(j)
            assert sid == j + 2 and sid in JF.SERVO_IDS
            assert JF.joint_of_servo(sid) == j
            seen.append(j)
    assert seen == list(range(18))
    assert list(JF.SERVO_IDS) == list(range(2, 20))
    assert JF.FACTORY_SERVO_ID not in JF.SERVO_IDS
    for bad in (JF.FACTORY_SERVO_ID, 0, 20):
        with pytest.raises(ValueError):
            JF.joint_of_servo(bad)
    for bad in (-1, 18):
        with pytest.raises(ValueError):
            JF.servo_id(bad)
    with pytest.raises(ValueError):
        JF.joint_index(6, "yaw")
    with pytest.raises(ValueError):
        JF.joint_index(0, "pitch")   # robot vocabulary only


def test_mujoco_model_joint_order_is_the_contract_order(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    mujoco = pytest.importorskip("mujoco")
    model = mujoco.MjModel.from_xml_path(str(MJX_XML))
    names = [model.joint(i).name for i in range(model.njnt)]
    assert names[0] == "root"
    assert tuple(names[1:]) == JF.SIM_JOINT_NAMES
    assert [JF.joint_of_name(n) for n in names[1:]] == list(range(18))
    # The actuated (position) order matches too: one actuator per joint.
    act_joints = [model.joint(model.actuator_trnid[a][0]).name
                  for a in range(model.nu)
                  if model.actuator(a).name in JF.SIM_JOINT_NAMES]
    assert tuple(act_joints) == JF.SIM_JOINT_NAMES


def test_tracker_joint_names_equal_the_contract():
    apriltag_vision = pytest.importorskip("hexapod_tracker.apriltag_vision")
    housing_pose = pytest.importorskip("hexapod_tracker.housing_pose")
    assert tuple(apriltag_vision.BRANCH_JOINT_ORDER) == JF.JOINT_NAMES
    assert tuple(housing_pose.JOINT_NAMES) == JF.JOINT_NAMES


_HAND_ROLLED = re.compile(
    r"\b3\s*\*\s*\w+\s*\+\s*[012]\b(?!\s*\*)"     # 3 * leg + k (not 3*a + 2*b)
    r"|range\(\s*[12]\s*,\s*(?:19|20)\s*\)"      # servo-ID scan ranges
    r"|\b(?:sid|servo_id|target)\s*=\s*\w+\s*\+\s*2\b"   # sid = joint + 2
    r"|\b(?:sid|servo_id)\w*\)?\s*-\s*2\b"       # joint = sid - 2
    r"|\blambda\s+\w+\s*:\s*\w+\s*\+\s*2\b"      # lambda j: j + 2
    r"|\+\s*2\s+for\s+\w+\s+in\s+range\(N_JOINTS\)")
_SKIP_DIRS = {"hexapod_core", "archive", "hexapod-tracker", "vendor",
              "tests", ".venv", "node_modules", "__pycache__"}


def _scannable(path: Path) -> bool:
    rel = path.relative_to(PROTO).parts
    if any(part in _SKIP_DIRS or part.startswith(".") for part in rel[:-1]):
        return False
    return not path.name.startswith("test_")


def test_no_hand_rolled_joint_or_servo_index_math():
    t0 = time.perf_counter()
    hits = []
    n_files = 0
    for path in PROTO.rglob("*.py"):
        if not _scannable(path):
            continue
        n_files += 1
        for lineno, line in enumerate(
                path.read_text(errors="replace").splitlines(), 1):
            if _HAND_ROLLED.search(line):
                hits.append(f"{path.relative_to(PROTO)}:{lineno}: {line.strip()}")
    elapsed = time.perf_counter() - t0
    assert n_files > 100, "scan root looks wrong"
    assert not hits, ("hand-rolled joint/servo index math; use "
                      "hexapod_core.joint_frame:\n" + "\n".join(hits))
    # Design budget is 1 s (0.4 s warm on a laptop); the hard bound is the
    # suite rule so a cold or contended disk does not turn this red.
    assert elapsed < 5.0, f"source scan took {elapsed:.2f}s"
