"""Off-robot tests for safe_zero (planner geometry + executor trips).

Run locally:  uv run python linux_control/test_safe_zero.py
No hardware: the executor tests use a FakeBus that simulates servos
converging on their targets (or one stalled joint fighting a force).
"""
from __future__ import annotations

import pytest

import math
import sys
import types


from feetech_bus import (AXIS_LIMITS_DEG, N_JOINTS, deg_to_count,
                         joint_to_servo_id)
from safe_zero import (BELLY_GROUND_Z_MM, GROUND_TOL_MM,
                       IMPLAUSIBLE_CURRENT_A, LIFT_CLEAR_MM,
                       LOADED_TORQUE_LIMIT,
                       SLIDE_DEV_TOL_MM, TEMP_MAX_C, foot_r_mm, foot_z_mm,
                       ik_hip_knee, ik_leg_angles, knee_for_foot_z,
                       plan_ik_pose_transition, plan_safe_zero,
                       run_safe_zero, seg_dist_2d)


def _pose(yaw=0.0, hip=0.0, knee=0.0) -> list[float]:
    out: list[float] = []
    for _ in range(6):
        out.extend([yaw, hip, knee])
    return out


def _pose_from_rz(r_mm: float, z_mm: float,
                  yaw=0.0) -> list[float]:
    hk = ik_hip_knee(r_mm, z_mm)
    assert hk is not None
    return _pose(yaw=yaw, hip=hk[0], knee=hk[1])


def _assert_within_limits(q):
    for j, v in enumerate(q):
        lo, hi = AXIS_LIMITS_DEG[j % 3]
        assert lo - 1e-6 <= v <= hi + 1e-6, f"j{j}={v} outside {lo}..{hi}"


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

def test_already_zero():
    p = plan_safe_zero(_pose())
    assert p["ok"] and p["stages"] == [] and p.get("already_at_zero")


def test_bad_input():
    assert not plan_safe_zero([0.0] * 17)["ok"]
    bad = _pose()
    bad[5] = None  # type: ignore[call-overload]
    assert not plan_safe_zero(bad)["ok"]


def test_suspect_zero_refused():
    q = _pose()
    q[2] = 175.0  # knee far beyond limit+slop → zero frame untrustworthy
    p = plan_safe_zero(q)
    assert not p["ok"] and "set_zero" in p["error"]


def _check_plan_geometry(p, present):
    """Shared invariants: in-limit stages, zero at the end, ground clear."""
    assert p["ok"], p.get("error")
    stages = p["stages"]
    assert stages, "expected motion stages"
    assert all(1.0 <= s["seconds"] <= 12.0 for s in stages)
    for s in stages:
        _assert_within_limits(s["goal"])
    assert max(abs(v) for v in stages[-1]["goal"]) < 1e-6
    # Independent ground check on non-drag stage paths.
    prev = present
    for s in stages:
        goal = s["goal"]
        if not s["drag_ok"]:
            for k in range(1, 11):
                t = k / 10.0
                q = [a + (b - a) * t for a, b in zip(prev, goal)]
                for leg in range(6):
                    z = foot_z_mm(q[leg * 3 + 1], q[leg * 3 + 2])
                    assert z >= BELLY_GROUND_Z_MM - GROUND_TOL_MM - 0.5, (
                        f"stage '{s['label']}' foot L{leg} at {z:.1f} mm")
        prev = goal


def test_plan_from_default_stand():
    present = _pose(hip=19.0, knee=28.0)
    p = plan_safe_zero(present)
    _check_plan_geometry(p, present)
    # No yaw motion needed; first stage lifts toward zero.
    assert p["stages"][0]["drag_ok"]
    assert all("yaw" not in s["label"] for s in p["stages"])


def test_plan_with_yaws():
    present = [15.0, -20.0, 55.0, -25.0, -20.0, 55.0] * 3
    p = plan_safe_zero(present)
    _check_plan_geometry(p, present)
    assert any("yaw" in s["label"] for s in p["stages"])


def test_crossed_adjacent_yaws():
    # Legs 0/1 yawed hard toward each other, feet lifted.
    present = _pose(knee=10.0)
    present[0] = 35.0
    present[3] = -35.0
    p = plan_safe_zero(present)
    # Must either find a safe (possibly sequential) order or refuse
    # with a clear error — never crash or emit an out-of-limit stage.
    if p["ok"]:
        _check_plan_geometry(p, present)
    else:
        assert p["error"]


def test_ik_hip_knee_roundtrip():
    for r in (20.0, 60.0, 120.0, 180.0, 210.0):
        for z in (-120.0, -80.0, -40.0, -18.0):
            hk = ik_hip_knee(r, z)
            if hk is None:
                continue  # out of reach / limits is a valid answer
            hip, knee = hk
            assert abs(foot_r_mm(hip, knee) - r) < 1e-6, (r, z)
            assert abs(foot_z_mm(hip, knee) - z) < 1e-6, (r, z)
    assert ik_hip_knee(300.0, -40.0) is None  # beyond full extension
    assert ik_hip_knee(10.0, -10.0) is None   # inside the fold limit


def test_ik_leg_angles_roundtrip():
    r, z = 160.0, -30.0
    for yaw in (-20.0, 0.0, 20.0):
        angles = ik_leg_angles(yaw, r, z)
        assert angles is not None
        yaw_out, hip, knee = angles
        assert yaw_out == yaw
        assert abs(foot_r_mm(hip, knee) - r) < 1e-6
        assert abs(foot_z_mm(hip, knee) - z) < 1e-6
    assert ik_leg_angles(50.0, r, z) is None  # outside yaw limits


def test_ik_transition_direct_clear_to_zero():
    present = _pose(hip=0.0, knee=10.0)
    goal = _pose()
    t = plan_ik_pose_transition(present, goal, label="to zero")
    assert t["ok"], t
    assert t["strategy"] == "direct_clear"
    assert len(t["stages"]) == 1
    assert t["stages"][0]["label"] == "to zero (direct clear path)"
    assert not t["stages"][0]["drag_ok"]
    assert max(abs(v) for v in t["stages"][0]["goal"]) < 1e-6


def test_ik_transition_steps_instead_of_sliding_grounded_feet():
    present = _pose_from_rz(140.0, BELLY_GROUND_Z_MM)
    goal = _pose_from_rz(180.0, BELLY_GROUND_Z_MM)
    t = plan_ik_pose_transition(present, goal, label="slide-free move")
    assert t["ok"], t
    assert t["strategy"] == "step_tripods"
    assert "slide" in t["direct_blocked_by"]
    assert len(t["stages"]) == 6
    assert all(s["drag_ok"] is False for s in t["stages"])
    labels = [s["label"] for s in t["stages"]]
    assert labels == [
        "slide-free move: step L0/L2/L4 lift",
        "slide-free move: step L0/L2/L4 swing",
        "slide-free move: step L0/L2/L4 place",
        "slide-free move: step L1/L3/L5 lift",
        "slide-free move: step L1/L3/L5 swing",
        "slide-free move: step L1/L3/L5 place",
    ]
    assert max(abs(a - b) for a, b in zip(t["stages"][-1]["goal"], goal)) < 1e-3


def test_low_drag_descent_from_plant_stand():
    # Absolute-knee low-drag descent lowers at constant foot radius, then
    # skims the feet only after the belly is carrying the robot.
    present = _pose(hip=19.0, knee=28.0)
    p = plan_safe_zero(present)
    _check_plan_geometry(p, present)
    assert p["descent"]["loaded_slide_mm"] == 0.0
    assert p["descent"]["legacy_slide_mm"] > 10.0
    labels = [s["label"] for s in p["stages"]]
    assert any("lower body" in l for l in labels), labels
    assert p["stages"][0]["drag_ok"]


def test_descent_fold_keeps_feet_planted():
    # Regression check for the absolute-knee zero path: the first stage
    # should move the feet upward, not press them deeper into the floor.
    present = _pose(hip=19.0, knee=28.0)
    p = plan_safe_zero(present)
    assert p["ok"], p
    z_start = foot_z_mm(present[1], present[2])
    prev = present
    for s in p["stages"]:
        if "straighten" not in s["label"]:
            break
        for k in range(1, 11):
            q = [a + (b - a) * (k / 10.0) for a, b in zip(prev, s["goal"])]
            for leg in range(6):
                z = foot_z_mm(q[leg * 3 + 1], q[leg * 3 + 2])
                assert z >= z_start - GROUND_TOL_MM, (
                    f"straighten stage pressed a foot to z={z:.1f} "
                    f"(start {z_start:.1f})")
        prev = s["goal"]


def test_wide_stance_descends_without_slide():
    # Feet already far out: belly contact is reachable at constant
    # radius, so the descent should plan zero loaded slide.
    present = _pose(hip=10.0, knee=25.0)
    p = plan_safe_zero(present)
    _check_plan_geometry(p, present)
    assert p["descent"]["loaded_slide_mm"] == 0.0


def test_belly_start_uses_clearance_checked_non_drag_plan():
    present = _pose(hip=-10.0, knee=20.0)  # feet near the belly plane
    p = plan_safe_zero(present)
    _check_plan_geometry(p, present)
    assert "descent" not in p
    assert p["stages"][0]["label"].startswith("straighten")
    assert p["stages"][0]["drag_ok"] is False
    assert any("IK transition to lift pose: direct_clear" in n
               for n in p.get("notes", []))


def test_knee_for_foot_z_roundtrip():
    for z in (-70.0, -40.0, -18.0, 0.0, 25.0):
        k = knee_for_foot_z(0.0, z)
        assert k is not None
        assert abs(foot_z_mm(0.0, k) - z) < 1e-6
    lift = knee_for_foot_z(0.0, BELLY_GROUND_Z_MM + LIFT_CLEAR_MM)
    assert lift is not None and 0.0 < lift < 30.0


def test_seg_dist():
    assert seg_dist_2d((0, -1), (0, 1), (-1, 0), (1, 0)) == 0.0
    assert abs(seg_dist_2d((0, 0), (1, 0), (0, 1), (1, 1)) - 1.0) < 1e-9


def test_fuzz_random_poses():
    import random
    rng = random.Random(42)
    planned = 0
    for _ in range(200):
        q = []
        for j in range(N_JOINTS):
            lo, hi = AXIS_LIMITS_DEG[j % 3]
            q.append(rng.uniform(lo, hi))
        p = plan_safe_zero(q)
        assert "ok" in p
        if p["ok"] and p["stages"]:
            planned += 1
            for s in p["stages"]:
                _assert_within_limits(s["goal"])
            assert max(abs(v) for v in p["stages"][-1]["goal"]) < 1e-6
    assert planned > 100, f"only {planned}/200 poses got a plan"


# ---------------------------------------------------------------------------
# Executor (FakeBus)
# ---------------------------------------------------------------------------

class _FakeGroupSync:
    def __init__(self, bus):
        self._bus = bus

    def txPacket(self):
        self._bus._commit()
        return 0

    def clearParam(self):
        pass


class _FakePkt:
    def __init__(self, bus):
        self._bus = bus
        self.groupSyncWrite = _FakeGroupSync(bus)

    def SyncWritePosEx(self, sid, count, speed, acc):
        self._bus._pending[sid] = count

    def ReadPos(self, sid):
        self._bus._advance()
        j = sid - 2
        return deg_to_count(j, self._bus.pos[j], 0.0), 0, 0

    def write1ByteTxRx(self, sid, addr, val):
        if addr == 40:  # ADDR_TORQUE_ENABLE
            if val == 0:
                self._bus.torque_off.add(sid)
            else:
                self._bus.torque_off.discard(sid)
        return 0, 0

    def write2ByteTxRx(self, sid, addr, val):
        if addr == 48:  # ADDR_TORQUE_LIMIT
            self._bus.torque_limits.append(int(val))
        return 0, 0


class FakeBus:
    """18 servos that glide toward SyncWrite targets on every read.

    ``stalled`` joints never move and report ``stall_a`` amps.
    """

    def __init__(self, start_deg, *, stalled=(), stall_a=3.2):
        self.pos = list(start_deg)
        self.target = list(start_deg)
        self.stalled = set(stalled)
        self.stall_a = stall_a
        self.trims = [0.0] * N_JOINTS
        self.torque_off: set[int] = set()
        self.torque_limits: list[int] = []
        self._pending: dict[int, int] = {}
        self.pkt = _FakePkt(self)
        self.scs = types.SimpleNamespace(COMM_SUCCESS=0)

    def scan(self, rng):
        return [sid for sid in rng]

    def _commit(self):
        from feetech_bus import count_to_deg
        for sid, count in self._pending.items():
            self.target[sid - 2] = count_to_deg(sid - 2, count)
        self._pending.clear()

    def _advance(self):
        for j in range(N_JOINTS):
            if j in self.stalled:
                continue
            err = self.target[j] - self.pos[j]
            if abs(err) < 0.05:
                continue
            step = min(abs(err), max(0.3 * abs(err), 1.0))
            self.pos[j] += math.copysign(step, err)

    def read_all_feedback(self):
        self._advance()
        out = {}
        for j in range(N_JOINTS):
            stalled = j in self.stalled
            moving = (not stalled
                      and abs(self.target[j] - self.pos[j]) > 0.5)
            out[j] = {
                "joint": j, "id": joint_to_servo_id(j),
                "deg": self.pos[j],
                "current_a": self.stall_a if stalled else 0.4,
                "speed_deg_s": 45.0 if moving else 0.0,
                "load_pct": 55.0 if stalled else 15.0,
                "temp_c": 35, "moving": int(moving),
            }
        return out


@pytest.mark.slow  # >5 s: sim rollout; default loop is -m "not slow"
def test_executor_reaches_zero():
    start = _pose(hip=10.0, knee=25.0)
    plan = plan_safe_zero(start)
    assert plan["ok"] and plan["stages"]
    bus = FakeBus(start)
    res = run_safe_zero(bus, plan["stages"])
    assert res["ok"], res
    assert max(abs(v) for v in bus.pos) < 4.0
    assert not bus.torque_off, "healthy run must not limp"


def _untrap_fold_pose() -> list[float]:
    """What the pinned-tip untrap leaves behind: hips ~-49.5, knees deep."""
    q: list[float] = []
    for knee in (121.0, 140.0, 133.0, 140.0, 128.0, 135.0):
        q.extend([0.0, -49.5, knee])
    return q


def test_deep_fold_straighten_gets_full_torque():
    """Unfolding from the untrap fold lifts the body — it needs the
    servos' full torque, not safe_zero's reduced air-stage limit."""
    plan = plan_safe_zero(_untrap_fold_pose())
    assert plan["ok"], plan
    by_label = {s["label"]: s for s in plan["stages"]}
    straighten = by_label["straighten hips/knees (feet to lift height)"]
    assert straighten["torque_limit"] == LOADED_TORQUE_LIMIT, straighten
    # Air/geometry stages keep the caller's limit (no override key).
    for st in plan["stages"]:
        if st is not straighten:
            assert "torque_limit" not in st, st


@pytest.mark.slow  # >5 s: sim rollout; default loop is -m "not slow"
def test_executor_raises_torque_only_for_the_loaded_stage():
    start = _untrap_fold_pose()
    plan = plan_safe_zero(start)
    assert plan["ok"] and plan["stages"]
    bus = FakeBus(start)
    res = run_safe_zero(bus, plan["stages"], torque_limit=700)
    assert res["ok"], res
    # 700 up front, LOADED_TORQUE_LIMIT for the straighten stage, back to
    # 700 for the air extend, then the finally-clause restore to 1000.
    seen = [v for i, v in enumerate(bus.torque_limits)
            if i == 0 or v != bus.torque_limits[i - 1]]
    assert seen == [700, LOADED_TORQUE_LIMIT, 700, 1000], seen


def test_executor_limps_on_stall():
    start = _pose(hip=10.0, knee=25.0)
    plan = plan_safe_zero(start)
    assert plan["ok"] and plan["stages"]
    bus = FakeBus(start, stalled={2}, stall_a=3.2)  # L0 knee fights
    res = run_safe_zero(bus, plan["stages"])
    assert not res["ok"] and res.get("limp"), res
    assert "L0 knee" in res["error"]
    assert bus.torque_off == {joint_to_servo_id(j)
                              for j in range(N_JOINTS)}, "must limp ALL"


class _GuardBus(FakeBus):
    """Injects a per-joint fault on a chosen list of sweeps.

    ``pattern`` is one entry per sweep: True = fault present. Sweeps past
    the end of the pattern are healthy. Lets a test assert that two
    consecutive bad reads pass and three limp.
    """

    def __init__(self, start_deg, *, joint, pattern, field, value,
                 speed_deg_s=None):
        super().__init__(start_deg)
        self.joint = joint
        self.pattern = list(pattern)
        self.field = field
        self.value = value
        # None = the classic "stopped dead" fault. A number simulates a
        # joint that is still turning while it shows the force.
        self.speed_deg_s = speed_deg_s
        self.sweeps = 0

    def read_all_feedback(self):
        out = super().read_all_feedback()
        i = self.sweeps
        self.sweeps += 1
        if i < len(self.pattern) and self.pattern[i]:
            fb = out[self.joint]
            fb[self.field] = self.value
            if self.field in ("current_a", "load_pct"):
                # stall/load guards only fire on a joint that is stuck
                fb["speed_deg_s"] = (0.0 if self.speed_deg_s is None
                                     else self.speed_deg_s)
                fb["deg"] = fb["deg"] + 30.0
        return out


def _guard_run(**kw):
    start = _pose(hip=10.0, knee=25.0)
    plan = plan_safe_zero(start)
    assert plan["ok"] and plan["stages"]
    bus = _GuardBus(start, **kw)
    return run_safe_zero(bus, plan["stages"])


def test_two_bad_current_reads_do_not_trip():
    """A corrupted byte, and even two split by a good read, must not limp."""
    res = _guard_run(joint=2, pattern=[True, True, False, True],
                     field="current_a", value=106.5)
    assert res["ok"], res
    assert res["peak_a"] < IMPLAUSIBLE_CURRENT_A, "wild read poisoned peak_a"


def test_three_consecutive_wild_current_reads_trip():
    res = _guard_run(joint=2, pattern=[True] * 3,
                     field="current_a", value=106.5)
    assert not res["ok"] and res.get("limp"), res
    assert "L0 knee" in res["error"] and "implausible" in res["error"]


def test_two_hard_cap_reads_do_not_trip():
    """Real overcurrent under the implausible ceiling also confirms x3."""
    res = _guard_run(joint=2, pattern=[True, True, False],
                     field="current_a", value=7.0)
    assert res["ok"], res


def test_three_hard_cap_reads_trip():
    res = _guard_run(joint=2, pattern=[True] * 3,
                     field="current_a", value=7.0)
    assert not res["ok"] and res.get("limp"), res
    assert "hard cap" in res["error"], res


def test_two_hot_reads_do_not_trip():
    res = _guard_run(joint=4, pattern=[True, True, False],
                     field="temp_c", value=TEMP_MAX_C + 60)
    assert res["ok"], res


def test_three_hot_reads_trip():
    res = _guard_run(joint=4, pattern=[True] * 3,
                     field="temp_c", value=TEMP_MAX_C + 60)
    assert not res["ok"] and res.get("limp"), res
    assert "°C" in res["error"], res


def test_two_overload_reads_do_not_trip():
    res = _guard_run(joint=4, pattern=[True, True, False],
                     field="load_pct", value=95.0)
    assert res["ok"], res


def test_three_overload_reads_trip():
    res = _guard_run(joint=4, pattern=[True] * 3,
                     field="load_pct", value=95.0)
    assert not res["ok"] and res.get("limp"), res
    assert "load" in res["error"] or "stall" in res["error"], res


def test_loaded_knee_turning_slowly_does_not_trip_drag_stage():
    """The belly-down straighten blend, at full torque.

    A knee lifting the body reports a big load and the smallest non-zero
    speed the STS register can express (50 counts/s = 4.39 deg/s). That is
    tracking, not a jam, and 4.39 sits under the 8.0 air threshold — the
    drag stage has to judge it by DRAG_SLOW_DPS instead.
    """
    start = _pose(hip=10.0, knee=25.0)
    plan = plan_safe_zero(start)
    assert plan["ok"] and plan["stages"][0]["drag_ok"], plan
    bus = _GuardBus(start, joint=2, pattern=[True] * 6,
                    field="load_pct", value=92.0, speed_deg_s=4.39)
    res = run_safe_zero(bus, plan["stages"])
    assert res["ok"], res


def test_loaded_knee_at_a_dead_stop_still_trips_drag_stage():
    """Same load, zero speed: still the jam the guard exists for, and the
    trip names the speed it fired on so the next run can be judged."""
    start = _pose(hip=10.0, knee=25.0)
    plan = plan_safe_zero(start)
    assert plan["ok"] and plan["stages"][0]["drag_ok"], plan
    bus = _GuardBus(start, joint=2, pattern=[True] * 4,
                    field="load_pct", value=92.0, speed_deg_s=0.0)
    res = run_safe_zero(bus, plan["stages"])
    assert not res["ok"] and res.get("limp"), res
    assert "unexpected force" in res["error"], res
    assert "0.0 deg/s" in res["error"], res


class _GroundLoadedKneeBus(FakeBus):
    """A knee that cannot be driven past ``floor_deg`` and shows no force.

    The 2026-09-10 l4_vertical_ground_load_ladder_v1 pre-roll: belly-down,
    the knee carries body weight, stops short of its goal and reports
    0 A / 0 % load. That is compliance, not a jam.
    """

    def __init__(self, start_deg, *, joint, floor_deg, load_pct=0.0,
                 current_a=0.0):
        super().__init__(start_deg)
        self.joint = joint
        self.floor_deg = floor_deg
        self.stuck_load_pct = load_pct
        self.stuck_current_a = current_a

    def read_all_feedback(self):
        out = super().read_all_feedback()
        j = self.joint
        if self.pos[j] < self.floor_deg:
            self.pos[j] = self.floor_deg
        fb = out[j]
        fb["deg"] = self.pos[j]
        if self.pos[j] <= self.floor_deg:
            fb["current_a"] = self.stuck_current_a
            fb["load_pct"] = self.stuck_load_pct
            fb["speed_deg_s"] = 0.0
            fb["moving"] = 0
        return out


def _loaded_knee_run(floor_deg, **kw):
    start = _pose(hip=10.0, knee=25.0)
    plan = plan_safe_zero(start)
    assert plan["ok"] and plan["stages"]
    bus = _GroundLoadedKneeBus(start, joint=2, floor_deg=floor_deg, **kw)
    return run_safe_zero(bus, plan["stages"])


@pytest.mark.slow  # >5 s: the loaded stage runs to its timeout
def test_ground_loaded_knee_residual_does_not_limp():
    """11 deg of loaded knee residual at 0 A / 0 % load must not limp."""
    res = _loaded_knee_run(11.0)
    assert res["ok"], res
    assert "not turning" not in str(res.get("error") or "")


@pytest.mark.slow  # >5 s: the loaded stage runs to its timeout
def test_unreachable_knee_still_trips_but_not_as_a_jam():
    """No force behind it -> the honest timeout, not a jam claim."""
    res = _loaded_knee_run(60.0)
    assert not res["ok"], res
    assert "timed out" in res["error"], res
    assert "not turning" not in res["error"], res


@pytest.mark.slow  # >5 s: the loaded stage runs to its timeout
def test_measured_ground_load_band_does_not_limp():
    """The 09-10 tripod_weight_shift_static_v2 numbers: a hip carrying
    body weight peaked at 1.07 A / 52 % load while merely compliant.
    The no-progress floors must sit above that whole band."""
    res = _loaded_knee_run(11.0, load_pct=52.0, current_a=1.07)
    assert res["ok"], res
    assert "not turning" not in str(res.get("error") or "")


@pytest.mark.slow  # >5 s: the loaded stage runs until the guard confirms
def test_stuck_knee_with_force_behind_it_still_limps():
    """The quiet-stall case: a servo giving up AT its torque limit
    reports that limit as load (70 % at 700) with no current spike —
    above the compliant band, so still a jam."""
    res = _loaded_knee_run(60.0, load_pct=70.0, current_a=0.4)
    assert not res["ok"] and res.get("limp"), res
    assert "L0 knee not turning" in res["error"], res


@pytest.mark.slow  # >5 s: the loaded stage runs to its timeout
def test_timeout_names_the_worst_joints_force():
    """The lab records a zero job's terminal status, not the per-sweep
    progress line, so the backstop message carries the numbers the
    floors get re-tuned from."""
    res = _loaded_knee_run(60.0, load_pct=52.0, current_a=1.07)
    assert not res["ok"] and "timed out" in res["error"], res
    assert "L0 knee 1.07 A / 52% load" in res["error"], res


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  ok    {name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {name}: {e}")
    print(f"{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
