"""Walk protocols: a synthetic robot and camera drive the runner through its branches."""
import json
import math

from hexapod_lab2 import runner, walk


def _rig(*, speed_ratio=0.8, drift_deg=5.0, tilt=4.0, tag_visible=True, trip_at=None, edge_at=None,
         standing=False, yaw0=143.0):
    """Fake robot + camera. The tag moves along the commanded direction at speed_ratio of the command,
    rotated by drift_deg, from a start pose; the pixel position starts mid-frame and slides."""
    state = {"t": 0.0, "vx": 0.0, "vy": 0.0, "om": 0.0, "x": 700.0, "y": 450.0, "yaw": yaw0,
             "knee": 80.0 if standing else 0.0, "mode": "stand" if standing else "idle", "cmds": [], "posts": []}
    def clock():
        return state["t"]
    def sleep(dt):
        # integrate motion while time passes
        v = math.hypot(state["vx"], state["vy"]) * speed_ratio
        if v:
            ang = math.radians(state["yaw"] + math.degrees(math.atan2(-state["vy"], state["vx"])) + drift_deg)
            state["x"] += v * math.cos(ang) * dt
            state["y"] += v * math.sin(ang) * dt
        state["yaw"] += -math.degrees(state["om"] * dt) * speed_ratio       # + omega is clockwise = negative yaw
        state["t"] += dt
    def post(url, body=None, raw=None):
        state["posts"].append((url.rsplit("/", 1)[-1], body, raw))
        if url.endswith("/cmd"):
            parts = raw.decode().split()
            state["cmds"].append(raw.decode())
            state["vx"], state["vy"], state["om"] = float(parts[1]), float(parts[2]), float(parts[3])
            return "J"
        if url.endswith("/api/standup"):
            state["knee"] = 80.0 if body["direction"] == "up" else 0.0
            state["mode"] = "stand" if body["direction"] == "up" else "idle"
            return {"ok": True}
        return {"ok": True}
    def get(url):
        if url.endswith("/api/feedback"):
            joints = [{"deg": 0.0, "cur_a": 0.3, "temp_c": 35.0} for _ in range(18)]
            for j in range(2, 18, 3):
                joints[j]["deg"] = state["knee"]
            servo = {"tripped": [], "warn_c": 55}
            if trip_at is not None and state["t"] >= trip_at:
                servo = {"tripped": [7], "tripped_names": ["L2 hip"], "warn_c": 55}
            return {"ok": True, "roll_deg": tilt, "pitch_deg": 0.0, "joints": joints, "servo": servo}
        if url.endswith("/api/rl/state"):
            return {"pose": {"mode": state["mode"]}}
        if url.endswith("/api/poses"):
            if not tag_visible:
                return {"markers": {}}
            return {"markers": {"0": {"status": "tracked", "position_mm": {"x": state["x"], "y": state["y"]},
                                       "rotation_degrees": {"yaw": state["yaw"]}, "camera_indices": [2]}}}
        if url.endswith("/api/detections.json"):
            fx = 0.5 + (state["x"] - 700.0) / 1200.0
            if edge_at is not None and state["t"] >= edge_at:
                fx = 0.95
            c = [[fx * 1280 - 10, 350], [fx * 1280 + 10, 350], [fx * 1280 + 10, 370], [fx * 1280 - 10, 370]]
            return {"cameras": [{"index": 2, "width": 1280, "height": 720, "tags": {"0": c}}]}
        raise AssertionError(url)
    return state, post, get, sleep, clock


def _doc(**kw):
    d = {"walk_protocol": 1, "name": "walk_test", "gait": 1, "out_and_back": True,
         "legs": [{"name": "fwd30", "vx_mm_s": 30, "seconds": 4}]}
    d.update(kw)
    return d


def test_legs_expand_out_and_back_and_clip_to_caps():
    legs = walk.legs_of(_doc(legs=[{"name": "fast", "vx_mm_s": 500, "omega_rad_s": -3, "seconds": 900}]))
    assert [l.name for l in legs] == ["fast", "fast_back"]
    assert legs[0].vx == 60.0 and legs[0].omega == -0.5 and legs[0].seconds == 40.0
    assert legs[1].vx == -60.0 and legs[1].omega == 0.5
    assert legs[0].command() == "J 60.0 0.0 -0.500 1" and legs[0].stop_command() == "J 0 0 0 1"


def test_walk_stands_streams_measures_and_sits(settings, tmp_path):
    state, post, get, sleep, clock = _rig(speed_ratio=0.8, drift_deg=5.0)
    res = walk.run_walk(settings, _doc(), tmp_path, post=post, get=get, sleep=sleep, clock=clock, log=lambda m: None)
    assert res["status"] == "ok", res
    s = res["summary"]
    assert [l["leg"] for l in s["legs"]] == ["fwd30", "fwd30_back"]
    out = s["legs"][0]
    assert out["stopped"] == "duration" and out["ticks_sent"] >= 35
    assert abs(out["mean_speed_mm_s"] - 24.0) < 2.0             # 0.8 x 30
    assert abs(out["travel_ratio"] - 0.8) < 0.05
    assert abs(out["drift_deg"] - 5.0) < 1.5
    assert out["commanded_dir_rel_deg"] == 0.0 and out["tilt_max_deg"] == 4.0
    assert out["current_total_mean_a"] == 5.4 and out["tag_lost_s"] == 0.0
    # the back leg comes home
    back = s["legs"][1]
    assert back["command"] == "J -30.0 0.0 0.000 1" and abs(back["travel_ratio"] - 0.8) < 0.05
    kinds = [p[0] for p in state["posts"]]
    assert kinds[0] == "standup" and kinds[-1] == "standup"
    assert state["posts"][-1][1]["direction"] == "down"
    assert state["cmds"].count("J 0 0 0 1") == 2
    assert (tmp_path / "walk_summary.json").exists() and (tmp_path / "walk_pose.csv").read_text().count("\n") > 20
    assert "commanded_rot_deg" in out and out["commanded_rot_deg"] == 0.0


def test_turn_leg_reports_heading_change_against_commanded_rotation(settings, tmp_path):
    state, post, get, sleep, clock = _rig(speed_ratio=0.5, standing=True)
    doc = _doc(legs=[{"name": "turn", "omega_rad_s": 0.4, "seconds": 5}], out_and_back=False)
    res = walk.run_walk(settings, doc, tmp_path, post=post, get=get, sleep=sleep, clock=clock, log=lambda m: None)
    leg = res["summary"]["legs"][0]
    assert leg["commanded_rot_deg"] == round(-math.degrees(0.4 * leg["seconds"]), 1)
    assert abs(leg["turn_ratio"] - 0.5) < 0.05
    assert [p[0] for p in state["posts"] if p[0] == "standup"] == ["standup"]   # already standing: only the sit


def test_tripped_servo_stops_the_run_and_sits(settings, tmp_path):
    state, post, get, sleep, clock = _rig(trip_at=1.0)
    res = walk.run_walk(settings, _doc(), tmp_path, post=post, get=get, sleep=sleep, clock=clock, log=lambda m: None)
    assert res["status"] == "failed" and res["exit_code"] == 4
    assert res["summary"]["aborted"].startswith("servo tripped")
    assert len(res["summary"]["legs"]) == 1 and res["summary"]["legs"][0]["stopped"] == "tripped"
    assert state["cmds"][-1] == "J 0 0 0 1" and state["posts"][-1][1]["direction"] == "down"


def test_frame_edge_and_lost_tag_end_the_leg_but_not_the_run(settings, tmp_path):
    state, post, get, sleep, clock = _rig(edge_at=1.5)
    res = walk.run_walk(settings, _doc(), tmp_path, post=post, get=get, sleep=sleep, clock=clock, log=lambda m: None)
    assert res["status"] == "ok"
    assert res["summary"]["legs"][0]["stopped"] == "frame_edge" and res["summary"]["legs"][0]["seconds"] < 2.5
    assert len(res["summary"]["legs"]) == 2
    state, post, get, sleep, clock = _rig(tag_visible=False)
    res = walk.run_walk(settings, _doc(), tmp_path, post=post, get=get, sleep=sleep, clock=clock, log=lambda m: None)
    # the detector still sees the tag, so this is an uncalibrated view, not a hidden tag
    assert res["status"] == "ok" and res["summary"]["legs"][0]["stopped"] == "uncalibrated"
    assert res["summary"]["legs"][0]["measured"] is False


def test_runner_dispatches_walk_protocols_in_process(settings, tmp_path, monkeypatch):
    settings.protocols_dir.mkdir(parents=True, exist_ok=True)
    (settings.protocols_dir / "walk_unit_v1.json").write_text(json.dumps(_doc(name="walk_unit_v1")))
    listed = {p["name"]: p for p in runner.list_protocols(settings)}
    assert listed["walk_unit_v1"]["walk"] and not listed["walk_unit_v1"]["needs_stand"]
    state, post, get, sleep, clock = _rig()
    monkeypatch.setattr(walk, "_http_post", post)
    monkeypatch.setattr(walk, "_http_get", get)
    monkeypatch.setattr(walk.time, "sleep", sleep)
    monkeypatch.setattr(walk.time, "monotonic", clock)
    res = runner.run_protocol(settings, "walk_unit_v1", "run1")
    assert res.status == "ok" and res.summary["walk"] and (res.run_dir / "runner.log").exists()
    assert "fwd30" in res.log_tail


def _rl_rig(**kw):
    """The scripted rig plus the RL drive API: policy_select, roles, preflight, stand, drive start/cmd/stop."""
    state, post, get, sleep, clock = _rig(**kw)
    rl = {"policy": None, "roles": [], "ready": False, "drive": False, "cmds": [], "starts": 0, "stops": 0, "standing_job": False}
    state["rl"] = rl

    def post2(url, body=None, raw=None):
        if "/api/rl/" in url:
            state["posts"].append((url.rsplit("/", 1)[-1], body, raw))
            if url.endswith("/api/rl/policy_select"):
                rl["policy"] = body["file"]; return {"ok": True}
            if url.endswith("/api/rl/roles"):
                rl["roles"].append((body["role"], body["file"])); return {"ok": True}
            if url.endswith("/api/rl/stand"):
                rl["ready"] = True; state["knee"] = 80.0; state["mode"] = "stand"; return {"ok": True}
            if url.endswith("/api/rl/drive/start"):
                rl["drive"] = True; rl["starts"] += 1; return {"ok": True}
            if url.endswith("/api/rl/drive/cmd"):
                rl["cmds"].append(body)
                if rl["drive"]:
                    state["vx"], state["vy"], state["om"] = body["vx"] * 1000.0, body["vy"] * 1000.0, body["wz"]
                return {"ok": rl["drive"], "active": rl["drive"]}
            if url.endswith("/api/rl/drive/stop"):
                rl["drive"] = False; rl["stops"] += 1; state["vx"] = state["vy"] = state["om"] = 0.0; return {"ok": True}
            raise AssertionError(url)
        return post(url, body, raw)

    def get2(url):
        if url.endswith("/api/rl/preflight?mode=walk"):
            return {"ok": rl["ready"], "error": None if rl["ready"] else "pose is not the sim walk-ready start"}
        if url.endswith("/api/rl/drive"):
            return {"ok": True, "active": rl["drive"]}
        if url.endswith("/api/rl/state"):
            return {"pose": {"mode": state["mode"]},
                    "calibrate": {"running": False, "result": {"mode": "drive", "ok": True, "ticks": 1400, "overruns": 3,
                                                               "fell": False, "timing": {"mean_service_ms": 9.6, "max_service_ms": 28.0}}}}
        return get(url)
    return state, post2, get2, sleep, clock


def test_rl_walk_selects_policy_stands_ready_drives_in_m_per_s_and_reports_drive_stats(settings, tmp_path):
    state, post, get, sleep, clock = _rl_rig(speed_ratio=0.5)
    doc = _doc(legs=[{"name": "fwd80", "vx_mm_s": 80, "seconds": 6}], rl_policy="walkteach_allhead_acq12m_100hz.json")
    res = walk.run_walk(settings, doc, tmp_path, post=post, get=get, sleep=sleep, clock=clock, log=lambda m: None)
    assert res["status"] == "ok", res["log_tail"]
    rl = state["rl"]
    assert rl["policy"] == "walkteach_allhead_acq12m_100hz.json" and ("walk", rl["policy"]) in rl["roles"]
    assert rl["starts"] == 2 and rl["stops"] == 2                       # out and back: one session per leg
    moving = [c for c in rl["cmds"] if c["vx"]]
    assert moving and abs(moving[0]["vx"] - 0.08) < 1e-6 and moving[-1]["vx"] == -0.08   # m/s, not mm/s
    assert not any(c[0] == "cmd" and c[2] for c in state["posts"])        # never the raw J gait line
    legs = res["summary"]["legs"]
    assert legs[0]["drive"]["ticks"] == 1400 and legs[0]["drive"]["mean_service_ms"] == 9.6
    assert legs[0]["mean_speed_mm_s"] and legs[0]["mean_speed_mm_s"] > 20
    assert res["summary"]["rl_policy"] == "walkteach_allhead_acq12m_100hz.json"
    assert state["posts"][-1][0] == "standup"                            # still sits at the end


def test_rl_caps_are_wider_and_a_refused_policy_fails_cleanly(settings, tmp_path):
    legs = walk.legs_of(_doc(legs=[{"name": "fast", "vx_mm_s": 500, "vy_mm_s": 500}], rl_policy="x.json"))
    assert legs[0].vx == walk.RL_MAX_VX and legs[0].vy == walk.RL_MAX_VY and legs[0].rl
    assert walk.legs_of(_doc(legs=[{"name": "fast", "vx_mm_s": 500}]))[0].vx == walk.MAX_VX
    state, post, get, sleep, clock = _rl_rig()

    def refuse(url, body=None, raw=None):
        if url.endswith("/api/rl/policy_select"):
            return {"ok": False, "error": "no such policy"}
        return post(url, body, raw)
    res = walk.run_walk(settings, _doc(rl_policy="missing.json"), tmp_path, post=refuse, get=get, sleep=sleep, clock=clock, log=lambda m: None)
    assert res["status"] == "failed" and res["summary"]["aborted"] == "rl_prepare"
    assert state["rl"]["starts"] == 0
