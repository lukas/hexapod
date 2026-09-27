"""export_policy_np stamps the TRAINED bus write profile into every artifact
(bus_write_speed / bus_write_acc), from the run's launch command when the
ledger knows it, else the config default -- so the robot's RL drive path
(linux_control/rl_policy._policy_bus_profile) runs the profile the policy
trained with instead of a fallback that may differ (2026-09-27 finding)."""
from rl_move.sim import export_policy_np as ex


def test_command_parse_takes_the_pinned_values():
    cmd = ["python", "-m", "x", "--cfg-set", "bus.write_speed=400", "--cfg-set",
           "bus.write_acc=20", "--cfg-set", "dr.x=1"]
    assert ex._bus_profile_from_command(cmd) == {"bus_write_speed": 400, "bus_write_acc": 20}
    assert ex._bus_profile_from_command(" ".join(cmd)) == {"bus_write_speed": 400, "bus_write_acc": 20}
    assert ex._bus_profile_from_command("--cfg-set bus.write_speed=800") == {"bus_write_speed": 800}
    assert ex._bus_profile_from_command(None) == {}
    assert ex._bus_profile_from_command("--cfg-set dr.latency_scale=1,1") == {}


def test_default_profile_is_the_config_default(monkeypatch):
    monkeypatch.setattr(ex, "_ledger_entry_for", lambda p: (None, None))
    prof = ex._bus_profile_for("ppo_goal_nope.zip", None)
    assert prof["bus_write_speed"] == 2000 and prof["bus_write_acc"] == 80
    assert prof["bus_profile_origin"] == "config.yaml default"


def test_ledger_command_overrides_default(monkeypatch):
    entry = {"run": "r1", "command": "train --cfg-set bus.write_speed=400 --cfg-set bus.write_acc=20"}
    monkeypatch.setattr(ex, "_ledger_entry_for", lambda p: ("r1", entry))
    prof = ex._bus_profile_for("ppo_goal_r1.zip", "r1")
    assert (prof["bus_write_speed"], prof["bus_write_acc"]) == (400, 20)
    assert "r1" in prof["bus_profile_origin"]


def test_training_sidecar_wins(tmp_path, monkeypatch):
    import json
    from rl_move.sim import trained_profile as tp
    ck = tmp_path / "ppo_goal_r2.zip"
    ck.write_bytes(b"x")
    # exactly how the trainer writes it: repr(dict) whose _motor_contract
    # value is itself a repr'd dict string
    contract = repr({"bus.write_speed": 400.0, "bus.write_acc": 20.0, "x": 1})
    resolved = repr({"task": "joint_walk", "_motor_contract": contract})
    (tmp_path / "ppo_goal_r2.training_complete.json").write_text(
        json.dumps({"resolved_config": resolved}))
    assert tp.trained_bus_profile(ck) == {
        "bus_write_speed": 400, "bus_write_acc": 20,
        "bus_profile_origin": "training sidecar ppo_goal_r2.training_complete.json"}
    assert tp.trained_bus_profile(tmp_path / "ppo_goal_r2_best.zip")["bus_write_speed"] == 400
    monkeypatch.setattr(ex, "_ledger_entry_for", lambda p: (None, None))
    prof = ex._bus_profile_for(str(ck), None)
    assert (prof["bus_write_speed"], prof["bus_write_acc"]) == (400, 20)
    # eval pin: only when the caller did not set bus.* itself
    cfg = {}
    assert tp.pin_trained_bus_profile(cfg, ck, log=None)["bus_write_speed"] == 400
    assert cfg["bus"] == {"write_speed": 400, "write_acc": 20,
                          "servo_vel_max_counts_s": "write_speed"}
    cfg2 = {"bus": {"write_speed": 2000}}
    assert tp.pin_trained_bus_profile(cfg2, ck, log=None) is None
    assert cfg2["bus"] == {"write_speed": 2000}
    assert tp.trained_bus_profile(tmp_path / "nothing.zip") is None
