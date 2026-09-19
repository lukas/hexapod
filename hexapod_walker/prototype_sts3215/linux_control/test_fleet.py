"""fleet session summary and robot->camera mapping (pure parts)."""
import fleet
from motor_swap import plan_swap
from hexapod_core.joint_frame import FACTORY_SERVO_ID, SERVO_IDS

ALL = list(SERVO_IDS)


def test_session_line_flags_a_new_motor_from_the_bus():
    robot = {"armed": False, "servo": {"live": 18, "max_temp_c": 30, "hottest": "L0 hip"}}
    plan = plan_swap([FACTORY_SERVO_ID] + [i for i in ALL if i != 4])
    line = fleet.session_line("hexapod.local", robot, plan)
    assert "NEW MOTOR" in line and "L0 knee" in line and "limp" in line


def test_session_line_says_bus_ok_for_a_full_healthy_bus():
    robot = {"armed": True, "servo": {"live": 18, "max_temp_c": 33, "hottest": "L1 knee", "tripped_names": []}}
    line = fleet.session_line("hexapod2.local", robot, plan_swap(ALL))
    assert "bus ok" in line and "ARMED" in line and "NEW MOTOR" not in line


def test_session_line_surfaces_a_trip_and_unreachable():
    robot = {"armed": False, "servo": {"live": 17, "tripped_names": ["L2 hip"]}}
    assert "TRIPPED" in fleet.session_line("r", robot, plan_swap([i for i in ALL if i != 8]))
    assert "UNREACHABLE" in fleet.session_line("r", None, None)


def test_camera_map_accepts_host_or_url_and_never_confuses_the_two_robots():
    assert fleet.camera_for("hexapod.local")["what"].startswith("red/blue")
    assert fleet.camera_for("http://hexapod2.local:8080")["what"].startswith("purple")
    assert "hexapod2" not in fleet.camera_for("hexapod.local")["how"]
    assert fleet.camera_for("nonesuch") is None
