"""Recentre: a synthetic robot under a synthetic camera walks back to the middle of the frame."""
import dataclasses
import json
import math

from hexapod_lab2 import eyes, loop, planner, recentre, robot, runner, walk
from tests_lab2.test_lab2 import GOOD_FB


def _rig(*, x=1050.0, y=450.0, yaw0=143.0, speed_ratio=0.8, drift_deg=5.0, cam_rot_deg=0.0, mirror=False,
         standing=False, lose_tag_after=None):
    """World: x right, y up, yaw counter-clockwise. Camera above the floor, image y down, rotated by
    cam_rot_deg in the picture and optionally mirrored. 1 px = 1 mm around the middle (1280x720)."""
    st = {"t": 0.0, "vx": 0.0, "vy": 0.0, "x": x, "y": y, "yaw": yaw0, "knee": 80.0 if standing else 0.0,
          "mode": "stand" if standing else "idle", "cmds": [], "posts": []}
    def clock():
        return st["t"]
    def sleep(dt):
        v = math.hypot(st["vx"], st["vy"]) * speed_ratio
        if v:
            ang = math.radians(st["yaw"] + math.degrees(math.atan2(-st["vy"], st["vx"])) + drift_deg)
            st["x"] += v * math.cos(ang) * dt
            st["y"] += v * math.sin(ang) * dt
        st["t"] += dt
    def post(url, body=None, raw=None):
        st["posts"].append(url.rsplit("/", 1)[-1])
        if url.endswith("/cmd"):
            parts = raw.decode().split()
            st["cmds"].append(raw.decode())
            st["vx"], st["vy"] = float(parts[1]), float(parts[2])
            return "J"
        if url.endswith("/api/standup"):
            st["knee"] = 80.0 if body["direction"] == "up" else 0.0
            st["mode"] = "stand" if body["direction"] == "up" else "idle"
            return {"ok": True}
        return {"ok": True}
    def pixel():
        # image y down: world +y is up in the picture
        ex, ey = (st["x"] - 700.0), -(st["y"] - 450.0)
        a = math.radians(cam_rot_deg)
        ix, iy = ex * math.cos(a) - ey * math.sin(a), ex * math.sin(a) + ey * math.cos(a)
        if mirror:
            ix = -ix
        return 0.5 + ix / 1280.0, 0.5 + iy / 720.0
    def get(url):
        if url.endswith("/api/feedback"):
            joints = [{"deg": 0.0, "cur_a": 0.3, "temp_c": 35.0} for _ in range(18)]
            for j in range(2, 18, 3):
                joints[j]["deg"] = st["knee"]
            return {"ok": True, "roll_deg": 1.0, "pitch_deg": 0.0, "joints": joints, "servo": {"tripped": [], "warn_c": 55}}
        if url.endswith("/api/rl/state"):
            return {"pose": {"mode": st["mode"]}}
        if url.endswith("/api/poses"):
            return {"markers": {"0": {"status": "tracked", "position_mm": {"x": st["x"], "y": st["y"]},
                                       "rotation_degrees": {"yaw": st["yaw"]}, "camera_indices": [2]}}}
        if url.endswith("/api/detections.json"):
            if lose_tag_after is not None and st["t"] > lose_tag_after:
                return {"cameras": [{"index": 2, "width": 1280, "height": 720, "tags": {}}]}
            fx, fy = pixel()
            c = [[fx * 1280 - 10, fy * 720 - 10], [fx * 1280 + 10, fy * 720 - 10], [fx * 1280 + 10, fy * 720 + 10], [fx * 1280 - 10, fy * 720 + 10]]
            return {"cameras": [{"index": 2, "width": 1280, "height": 720, "tags": {"0": c}}]}
        raise AssertionError(url)
    return st, post, get, sleep, clock, pixel


def _session(settings, tmp_path, rig):
    st, post, get, sleep, clock, pixel = rig
    return walk.Session(settings, tmp_path, post=post, get=get, sleep=sleep, clock=clock, log=lambda m: None), st, pixel


def test_near_the_middle_nothing_happens(settings, tmp_path):
    s, st, _ = _session(settings, tmp_path, _rig(x=760.0))
    rc = recentre.recentre(s)
    assert rc["done"] and not rc["moved"] and st["cmds"] == [] and "already" in rc["reason"]


def test_walks_back_to_the_middle_from_the_right_edge(settings, tmp_path):
    s, st, pixel = _session(settings, tmp_path, _rig(x=1050.0, y=560.0))
    assert recentre.distance_frac(pixel()) > recentre.FAR_FRAC
    rc = recentre.recentre(s, budget_s=90.0)
    assert rc["done"], rc
    assert rc["moved"] and rc["pushes"] >= 2 and rc["seconds"] <= 90.0
    assert recentre.distance_frac(pixel()) <= recentre.CENTRE_TOL_FRAC
    assert st["cmds"][-1].startswith("J 0 0 0")               # stop went out
    assert "standup" in st["posts"]                            # stood first
    assert rc["chirality"] == 1


def _start_for(ix, iy, rot, mirror):
    """World position that puts the tag at image offset (ix, iy) px for this camera."""
    if mirror:
        ix = -ix
    a = math.radians(-rot)
    ex, ey = ix * math.cos(a) - iy * math.sin(a), ix * math.sin(a) + iy * math.cos(a)
    return 700.0 + ex, 450.0 - ey


def test_a_rotated_or_mirrored_camera_still_converges(settings, tmp_path):
    for rot, mirror in ((90.0, False), (200.0, False), (0.0, True), (135.0, True)):
        x, y = _start_for(330.0, 110.0, rot, mirror)
        rig = _rig(x=x, y=y, yaw0=-40.0, cam_rot_deg=rot, mirror=mirror)
        s, st, pixel = _session(settings, tmp_path, rig)
        assert recentre.needs_recentre(pixel()) and not s.near_edge(pixel()), (rot, mirror, pixel())
        rc = recentre.recentre(s, budget_s=120.0)
        assert rc["done"], (rot, mirror, rc)
        assert rc["chirality"] == (-1 if mirror else 1), (rot, mirror, rc)


def test_a_probe_into_the_edge_is_followed_by_a_backward_probe(settings, tmp_path):
    # Robot near the right edge with its nose pointing at that edge: forward would leave the frame.
    x, y = _start_for(400.0, 0.0, 0.0, False)
    s, st, pixel = _session(settings, tmp_path, _rig(x=x, y=y, yaw0=-5.0))
    rc = recentre.recentre(s, budget_s=120.0)
    assert rc["done"], rc
    assert any("probing backward" in n for n in s.notes)


def test_tag_lost_stops_the_push_and_says_so(settings, tmp_path):
    s, st, _ = _session(settings, tmp_path, _rig(x=1050.0, lose_tag_after=4.0))
    rc = recentre.recentre(s)
    assert not rc["done"] and rc["reason"] == "tag lost" and st["cmds"][-1].startswith("J 0 0 0")


def test_aim_turns_pixel_error_into_body_commands():
    fwd = (1.0, 0.0)                     # body +x points right in the picture
    assert recentre.aim((100.0, 0.0), fwd, 1) == (30.0, 0.0)          # middle is ahead: forward
    assert recentre.aim((-100.0, 0.0), fwd, 1) == (-30.0, 0.0)        # behind: backward
    assert recentre.aim((0.0, 100.0), fwd, 1) == (0.0, 30.0)          # down in the picture = robot's right (from above)
    assert recentre.aim((0.0, 100.0), fwd, -1) == (0.0, -30.0)        # mirrored camera: the other way


def test_walk_intent_phrases_the_first_leg():
    doc = {"walk_protocol": 1, "gait": 1, "out_and_back": True, "legs": [{"name": "fwd30", "vx_mm_s": 30, "seconds": 10}]}
    assert loop.walk_intent(doc) == "walk about 30 cm forward and then back"
    doc = {"walk_protocol": 1, "gait": 1, "legs": [{"name": "crab", "vy_mm_s": -30, "seconds": 5}]}
    assert loop.walk_intent(doc) == "walk about 15 cm to its left"
    doc = {"walk_protocol": 1, "gait": 1, "legs": [{"name": "turn", "omega_rad_s": 0.4, "seconds": 8}]}
    assert loop.walk_intent(doc) == "turn in place for about 8 s"
    assert loop.walk_intent(None) is None


def test_obstacle_line_is_read_from_the_look():
    assert eyes.obstacle_in("YES. Robot flat on the mat.\nOBSTACLE: a power cable about 20 cm ahead of it") == "a power cable about 20 cm ahead of it"
    assert eyes.obstacle_in("YES. Robot flat, nothing near it.") is None
    assert "OBSTACLE" in eyes.PATH_QUESTION and "walk about 30 cm forward" in eyes.PATH_QUESTION.format(about_to="walk about 30 cm forward")


def test_loop_asks_the_path_question_for_walks_and_shortens_legs_on_an_obstacle(settings, store, monkeypatch):
    asked = {}
    monkeypatch.setattr(eyes, "ready_to_move", lambda s, **k: asked.update(k) or (True, "YES flat.\nOBSTACLE: a cable ahead", 0.0))
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    got = {}

    def run_protocol(s, p, rid, force=False, **kw):
        got.update(kw)
        return runner.RunResult(status="ok", exit_code=0, run_dir=None, summary={}, log_tail="", motion_s=1.0)
    monkeypatch.setattr(runner, "run_protocol", run_protocol)
    (settings.protocols_dir / "walk_t_v1.json").write_text(json.dumps(
        {"name": "walk_t_v1", "walk_protocol": 1, "gait": 1, "out_and_back": True, "legs": [{"name": "f", "vx_mm_s": 30, "seconds": 10}]}))
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="walk_t_v1", build_spec=None)
    assert loop.run_once(settings, store, store.plan(pid), log=lambda m: None)["status"] == "ok"
    assert asked["about_to"] == "walk about 30 cm forward and then back"
    assert got["obstacle"] == "a cable ahead"
    assert any("obstacle" in e["text"] for e in store.events(5) if e["kind"] == "look")
    # a belly ladder gets no path question and no obstacle kwarg
    got.clear(); asked.clear()
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    loop.run_once(settings, store, store.plan(pid), log=lambda m: None)
    assert asked["about_to"] is None and got == {}


def test_run_walk_cuts_legs_when_an_obstacle_was_seen_and_recentres_at_the_end(settings, tmp_path):
    from tests_lab2.test_walk import _doc, _rig as walk_rig
    state, post, get, sleep, clock = walk_rig(speed_ratio=0.8)
    on = dataclasses.replace(settings, recentre=True)
    res = walk.run_walk(on, _doc(legs=[{"name": "fwd30", "vx_mm_s": 30, "seconds": 20}]), tmp_path,
                        post=post, get=get, sleep=sleep, clock=clock, log=lambda m: None, obstacle="a cable ahead")
    assert res["status"] == "ok"
    legs = res["summary"]["legs"]
    assert all(l["seconds"] <= walk.OBSTACLE_LEG_S + 0.5 for l in legs), legs
    assert res["summary"]["obstacle"] == "a cable ahead"
    assert "recentre" in res["summary"] and res["summary"]["recentre"]["reason"]
    assert state["posts"][-1][0] == "standup" and state["posts"][-1][1]["direction"] == "down"   # still sits at the end


def test_loop_recentres_before_camera_measured_protocols_only(settings, store, monkeypatch):
    calls = []
    monkeypatch.setattr(loop, "pixel_of", lambda s, run_dir: (0.85, 0.5))
    monkeypatch.setattr(loop, "recentre_before", lambda s, run_dir, walk, log: calls.append(walk) or
                        {"moved": True, "done": True, "reason": "centred", "start": [0.8, 0.5], "end": [0.5, 0.5], "seconds": 30.0})
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    monkeypatch.setattr(runner, "run_protocol", lambda s, p, rid, force=False, **kw: runner.RunResult(
        status="ok", exit_code=0, run_dir=None, summary={}, log_tail="", motion_s=1.0))
    on = dataclasses.replace(settings, recentre=True)
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="champion_stand_ground_v1", build_spec=None)
    run = loop.run_once(on, store, store.plan(pid), log=lambda m: None)
    assert calls == [False] and json.loads(run["summary_json"])["recentre_before"]["moved"] is True
    assert any(e["kind"] == "recentre" for e in store.events(5))
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    run = loop.run_once(on, store, store.plan(pid), log=lambda m: None)
    assert calls == [False] and "recentre_before" not in json.loads(run["summary_json"])
    assert loop.camera_measured("whole_body_single_leg_lift_v3") and loop.camera_measured("tripod_weight_shift_static_v2")
    assert not loop.camera_measured("l4_vertical_ground_load_ladder_v1")


def test_recentre_before_sits_again_unless_a_walk_follows(settings, tmp_path, monkeypatch):
    rig = _rig(x=1050.0, y=560.0)
    st, post, get, sleep, clock, pixel = rig
    monkeypatch.setattr(walk, "_http_post", post)
    monkeypatch.setattr(walk, "_http_get", get)
    # Session defaults bind the module functions at class definition; build one by hand instead
    made = {}
    real_session = walk.Session

    def session(settings_, run_dir, **kw):
        s = real_session(settings_, run_dir, post=post, get=get, sleep=sleep, clock=clock, log=lambda m: None)
        made["s"] = s
        return s
    monkeypatch.setattr(walk, "Session", session)
    rc = loop.recentre_before(settings, tmp_path, walk=False, log=lambda m: None)
    assert rc["done"] and st["knee"] == 0.0 and st["mode"] == "idle"       # sat back down
    st2 = _rig(x=1050.0, y=560.0)
    monkeypatch.setattr(walk, "Session", lambda settings_, run_dir, **kw: real_session(
        settings_, run_dir, post=st2[1], get=st2[2], sleep=st2[3], clock=st2[4], log=lambda m: None))
    rc = loop.recentre_before(settings, tmp_path, walk=True, log=lambda m: None)
    assert rc["done"] and st2[0]["knee"] == 80.0                              # left standing for the walk


def test_look_is_told_the_pose_when_the_encoders_read_flat_zero(settings, store, monkeypatch):
    asked = {}
    monkeypatch.setattr(eyes, "ready_to_move", lambda s, **k: asked.update(k) or (True, "YES", 0.0))
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    monkeypatch.setattr(runner, "run_protocol", lambda s, p, rid, force=False, **kw: runner.RunResult(
        status="ok", exit_code=0, run_dir=None, summary={}, log_tail="", motion_s=1.0))
    flat_fb = {"ok": True, "live": 18, "roll_deg": 0.3, "pitch_deg": 3.0, "joints": [{"deg": 0.4, "temp_c": 31.0} for _ in range(18)]}
    monkeypatch.setattr(robot, "health", lambda url, budget: flat_fb)
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    loop.run_once(settings, store, store.plan(pid), log=lambda m: None)
    assert asked["pose_known"] is True
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)      # no joint angles: pose not known
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="steps_air_v1", build_spec=None)
    loop.run_once(settings, store, store.plan(pid), log=lambda m: None)
    assert asked["pose_known"] is False
    assert "do not answer NO because of how the legs look" in eyes.POSE_KNOWN


def test_a_pending_recentre_is_told_to_the_look_and_skipped_on_an_obstacle(settings, store, monkeypatch):
    asked = {}
    monkeypatch.setattr(eyes, "ready_to_move", lambda s, **k: asked.update(k) or (True, "YES flat.\nOBSTACLE: cable bundle between it and the middle", 0.0))
    monkeypatch.setattr(robot, "health", lambda url, budget: GOOD_FB)
    monkeypatch.setattr(runner, "sync_checkout", lambda s: "synced")
    monkeypatch.setattr(runner, "run_protocol", lambda s, p, rid, force=False, **kw: runner.RunResult(
        status="ok", exit_code=0, run_dir=None, summary={}, log_tail="", motion_s=1.0))
    monkeypatch.setattr(loop, "pixel_of", lambda s, run_dir: (0.85, 0.5))       # far right of the frame
    moved = []
    monkeypatch.setattr(loop, "recentre_before", lambda *a, **k: moved.append(1) or {"moved": True, "done": True, "reason": "centred",
                                                                                     "start": None, "end": None, "seconds": 1.0})
    on = dataclasses.replace(settings, recentre=True)
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="champion_stand_ground_v1", build_spec=None)
    run = loop.run_once(on, store, store.plan(pid), log=lambda m: None)
    assert run["status"] == "ok"
    assert "toward the middle" in asked["about_to"]
    assert moved == []                                                          # did not walk into the cable
    rc = json.loads(run["summary_json"])["recentre_before"]
    assert rc["moved"] is False and "cable" in rc["reason"]
    # near the middle already: no move is announced and the walk intent stands alone
    monkeypatch.setattr(loop, "pixel_of", lambda s, run_dir: (0.52, 0.5))
    (settings.protocols_dir / "walk_t_v1.json").write_text(json.dumps(
        {"name": "walk_t_v1", "walk_protocol": 1, "gait": 1, "legs": [{"name": "f", "vx_mm_s": 30, "seconds": 10}]}))
    pid = store.add_plan(title="p", why="w", kind="existing", protocol="walk_t_v1", build_spec=None)
    loop.run_once(on, store, store.plan(pid), log=lambda m: None)
    assert asked["about_to"] == "walk about 30 cm forward"
