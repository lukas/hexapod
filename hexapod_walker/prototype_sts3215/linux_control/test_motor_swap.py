"""motor_swap decisions: what a bus inventory means after a servo swap."""
import math

from hexapod_core.joint_frame import FACTORY_SERVO_ID, SERVO_IDS

import motor_swap


ALL = list(SERVO_IDS)


def test_full_bus_needs_nothing():
    plan = motor_swap.plan_swap(ALL)
    assert not plan["ready"] and plan["missing_ids"] == [] and not plan["factory_id_present"]


def test_one_empty_slot_plus_factory_id_is_the_swap_case():
    plan = motor_swap.plan_swap([FACTORY_SERVO_ID] + [i for i in ALL if i != 4])
    assert plan["ready"]
    assert plan["target_id"] == 4 and plan["target_joint"] == 2
    assert plan["missing_joints"] == ["L0 knee"]


def test_empty_slot_without_factory_id_points_at_the_lead():
    plan = motor_swap.plan_swap([i for i in ALL if i != 4])
    assert not plan["ready"] and "power/data" in plan["why"]


def test_factory_id_with_full_bus_means_old_servo_still_connected():
    plan = motor_swap.plan_swap([FACTORY_SERVO_ID] + ALL)
    assert not plan["ready"] and "still connected" in plan["why"]


def test_two_empty_slots_need_an_explicit_joint():
    plan = motor_swap.plan_swap([FACTORY_SERVO_ID] + [i for i in ALL if i not in (4, 7)])
    assert not plan["ready"] and "--joint" in plan["why"]


def test_stranger_ids_block_everything():
    plan = motor_swap.plan_swap(ALL + [25])
    assert not plan["ready"] and plan["stranger_ids"] == [25]


def test_flat_pose_outliers_flag_factory_offset_and_missing_reads():
    degrees = [0.0] * 18
    degrees[2] = 163.2
    degrees[5] = None
    out = motor_swap.flat_pose_outliers(degrees)
    assert [j for j, _ in out] == [2, 5]
    assert math.isnan(out[1][1])
