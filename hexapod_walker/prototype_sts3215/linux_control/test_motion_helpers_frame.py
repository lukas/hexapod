"""The motion helper layer (motor_setup/inplace_demos, motion_telemetry) speaks robot_abs
and converts knees to the servo hinge frame at deg_to_count -- the same boundary as the bus.

Regression guard for 2026-09-27: the stand-up keyframes were converted to robot_abs but
_write_pose still wrote them as hinge degrees, so every knee target landed hip degrees too
flexed (sit-down dragged the feet 55 mm inward, STEP stand ended at hinge 103 not 82), and
_hold_here read robot_abs from the MCU snapshot and wrote it back raw."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
for _p in (_HERE, _ROOT, _ROOT / "motor_setup"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import inplace_demos as demo  # noqa: E402
from feetech_bus import (  # noqa: E402
    N_JOINTS, deg_to_count, joint_to_servo_id, robot_pose_to_raw_degrees,
    raw_degree_to_count, robot_abs_to_servo_relative, servo_relative_to_robot_abs)

STANCE_ABS = [0.0, 20.87, 103.04] * 6          # the baked STEP stance: hinge (20.87, 82.17)
TRIMS = [0.0, 1.5, -2.0] * 6


class _Pkt:
    def __init__(self, bus):
        self.bus = bus
        self.writes: list[tuple[int, int, int, int]] = []
        self.tx = 0

        class _G:
            def txPacket(_s):
                bus.pkt.tx += 1

            def clearParam(_s):
                pass
        self.groupSyncWrite = _G()

    def SyncWritePosEx(self, sid, count, speed, acc):
        self.writes.append((sid, int(count), int(speed), int(acc)))
        return 0

    def write1ByteTxRx(self, *_a):
        return 0, 0

    def ReadPos(self, sid):
        return self.bus.present_counts[sid], 0, 0


class _Scs:
    COMM_SUCCESS = 0


class FakeBus:
    """Plain (non-MCU) bus: ReadPos counts; optionally an MCU-style snapshot."""

    def __init__(self, present_abs, *, snapshot=False, trims=None):
        self.trims = list(TRIMS if trims is None else trims)
        self.scs = _Scs()
        self.pkt = _Pkt(self)
        raw = robot_pose_to_raw_degrees(present_abs, self.trims)
        self.present_counts = {joint_to_servo_id(j): raw_degree_to_count(j, raw[j]) for j in range(N_JOINTS)}
        self.present_abs = list(present_abs)
        if snapshot:
            self.read_snapshot = lambda: {"pos_deg": {j: self.present_abs[j] for j in range(N_JOINTS)}}


LIVE = {joint_to_servo_id(j) for j in range(N_JOINTS)}


def _expected_counts(pose_abs, trims):
    raw = robot_pose_to_raw_degrees(pose_abs, trims)
    return {joint_to_servo_id(j): raw_degree_to_count(j, raw[j]) for j in range(N_JOINTS)}


def test_write_pose_converts_robot_abs_knees_to_hinge_counts():
    bus = FakeBus(STANCE_ABS)
    demo._write_pose(bus, STANCE_ABS, LIVE, speed=200, acc=20)
    got = {sid: c for sid, c, _s, _a in bus.pkt.writes}
    assert got == _expected_counts(STANCE_ABS, bus.trims)
    # the servo knee sits at 82.17 + trim, NOT at 103 (the 2026-09-27 regression)
    knee0 = got[joint_to_servo_id(2)]
    assert knee0 == deg_to_count(2, 82.17, bus.trims[2])
    assert knee0 != deg_to_count(2, 103.04, bus.trims[2])
    assert bus.pkt.tx == 1


@pytest.mark.parametrize("snapshot", [False, True])
def test_hold_here_never_moves_a_joint(snapshot):
    """Read robot_abs -> write: the counts written must equal the present counts."""
    bus = FakeBus(STANCE_ABS, snapshot=snapshot)
    demo._hold_here(bus, LIVE)
    got = {sid: c for sid, c, _s, _a in bus.pkt.writes}
    assert got == bus.present_counts


def test_read_pose_returns_robot_abs_from_raw_counts_with_trims_removed():
    pose = [0.0, -20.74, 103.08] * 6                # a descent frame: hip negative
    bus = FakeBus(pose)
    got = demo._read_pose(bus, LIVE)
    assert got == pytest.approx(pose, abs=0.1)


def test_pose_streamer_first_frame_and_hip_only_motion_rewrite_the_knee():
    bus = FakeBus(STANCE_ABS)
    st = demo.PoseStreamer()
    st.write(bus, STANCE_ABS, LIVE, dt=0.05)
    assert {sid: c for sid, c, *_ in bus.pkt.writes} == _expected_counts(STANCE_ABS, bus.trims)
    bus.pkt.writes.clear()
    # hip moves 5 deg, absolute tibia angle unchanged -> hinge changes -5 -> the knee MUST be written
    nxt = list(STANCE_ABS)
    for leg in range(6):
        nxt[leg * 3 + 1] += 5.0
    wrote = st.write(bus, nxt, LIVE, dt=0.05)
    assert all(joint_to_servo_id(leg * 3 + 2) in {w[0] for w in bus.pkt.writes} for leg in range(6))
    assert set(wrote) == {j for j in range(N_JOINTS) if j % 3 in (1, 2)}
    got = {sid: c for sid, c, *_ in bus.pkt.writes}
    exp = _expected_counts(nxt, bus.trims)
    assert all(got[s] == exp[s] for s in got)


def test_show_vocabulary_is_hinge_and_lands_as_robot_abs():
    # a literal (hip 19, knee 28) stance is the same physical pose as before the boundary
    pose = demo._elevated_stand_pose(hip=19.0, knee=28.0)
    assert pose[1:3] == [19.0, 47.0]
    assert robot_abs_to_servo_relative(pose)[1:3] == pytest.approx([19.0, 28.0])
    # "hip -6 / knee +6" (the re-plant lift) keeps the absolute tibia angle
    p2 = list(pose)
    demo._yaw_hip_knee(0, p2, hip=-6.0, knee=6.0)
    assert p2[1:3] == pytest.approx([13.0, 47.0])
    # _set_leg with hinge literals; hip-only keeps the hinge
    p3 = list(pose)
    demo._set_leg(p3, 1, hip=-40.0, knee=120.0)
    assert p3[4:6] == pytest.approx([-40.0, 80.0])
    demo._set_leg(p3, 1, hip=-30.0)
    assert p3[4:6] == pytest.approx([-30.0, 90.0])
    # the sit/air home is frame-invariant
    assert demo._zero_pose() == servo_relative_to_robot_abs([0.0] * N_JOINTS)


_RAW_CALLS = ("deg_to_count(", "count_to_deg(", "SyncWritePosEx(", ".ReadPos(", "WritePosEx(")
# Every file allowed to touch raw servo counts, with the number of call sites it may have.
# A new raw writer anywhere else is a boundary leak: add the conversion, not an entry.
_ALLOWED = {
    "motor_setup/feetech_bus.py": None,            # the boundary itself
    "linux_control/mcu_feetech_bus.py": None,      # the boundary itself (MCU bridge)
    "motor_setup/inplace_demos.py": 8,             # _write_pose, PoseStreamer.write, _read_pose (converted)
    "motor_setup/motion_telemetry.py": 6,          # run_hold_log (converted)
    "linux_control/drive_controller.py": 2,        # fallback SyncWrite via raw_degree_to_count
    "linux_control/motor_setup_api.py": 2,         # servo-level setup (counts, no joint frame)
    "motor_setup/urt2_motor_setup.py": 7,          # single-servo bench tools
    "motor_setup/urt2_bench.py": 4,
}


def test_no_raw_servo_call_outside_the_boundary_allowlist():
    hits: dict[str, int] = {}
    for sub in ("linux_control", "motor_setup"):
        for f in (_ROOT / sub).rglob("*.py"):
            rel = f.relative_to(_ROOT).as_posix()
            if "/vendor/" in rel or f.name.startswith("test_") or "/tests/" in rel:
                continue
            text = f.read_text(errors="ignore")
            n = sum(len(re.findall(re.escape(c), text)) for c in _RAW_CALLS)
            if n:
                hits[rel] = n
    leaks = {k: v for k, v in hits.items() if k not in _ALLOWED}
    assert not leaks, f"raw servo calls outside the servo boundary: {leaks}"
    grown = {k: (v, _ALLOWED[k]) for k, v in hits.items() if _ALLOWED[k] is not None and v > _ALLOWED[k]}
    assert not grown, f"new raw servo call sites (add a conversion, not an allowlist bump): {grown}"
