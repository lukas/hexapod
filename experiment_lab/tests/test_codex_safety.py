import hashlib
import json

import pytest

from hexapod_lab.codex_orchestrator import CodexOrchestrator, CodexRunError
from hexapod_lab.config import Settings
from hexapod_lab.db import Store
from hexapod_lab.runner import ExperimentRunner


def configured(tmp_path, **overrides):
    values = dict(
        data_dir=tmp_path / "data",
        api_keys="automation:codex:auto,operator:alice:operator",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="",
        auto_worker=False,
        max_duration_seconds=900,
        codex_workdir=tmp_path / "workspace",
        codex_evidence_settle_seconds=0,
    )
    values.update(overrides)
    return Settings(**values)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reviewed_workspace(tmp_path):
    root = tmp_path / "workspace" / "hexapod_walker" / "prototype_sts3215"
    walk = root / "rl_move" / "scripts" / "run_rl_walk_trial.py"
    sysid = root / "sysid" / "run_hw.py"
    policy = root / "linux_control" / "policies" / "bounded.json"
    protocol = (
        root / "sysid" / "protocols"
        / "l5_ground_radial_shear_amplitude_ladder_v1.json"
    )
    for path in (walk, sysid, policy, protocol):
        path.parent.mkdir(parents=True, exist_ok=True)
    walk.write_text("# bounded walk runner\n", encoding="utf-8")
    sysid.write_text("# bounded sysid runner\n", encoding="utf-8")
    policy.write_text('{"policy":"bounded"}\n', encoding="utf-8")
    protocol.write_text(
        json.dumps(
            {
                "sysid_protocol": 1,
                "hz": 10,
                "write_speed": 180,
                "write_acc": 10,
                "soft_torque": 700,
                "max_current_a": 0.75,
                "current_trip_polls": 3,
                "hard_current_a": 3,
                "segments": [{"kind": "traj", "t_s": [0, 1]}],
            }
        ),
        encoding="utf-8",
    )
    return root, walk, sysid, policy, protocol


def test_adaptive_physical_admission_requires_exact_verified_runner_and_bounds(tmp_path):
    root, walk, sysid, policy, protocol = reviewed_workspace(tmp_path)
    orchestrator = CodexOrchestrator(
        Store(tmp_path / "data" / "lab.sqlite3"), configured(tmp_path),
        invoker=lambda *_: {},
    )
    base = {
        "current_compatibility": {"ready": True},
        "runner": "rl_move/scripts/run_rl_walk_trial.py",
        "runner_sha256": sha256(walk),
        "policy_path": "linux_control/policies/bounded.json",
        "policy_sha256": sha256(policy),
        "speed_m_s": 0.08,
        "wz_rad_s": 0,
        "command_window_s": 3,
        "planned_repeats": 1,
        "phase": "forward",
    }
    assert orchestrator._physical_followup_rejection(base, 3) == ""

    passive_prohibitions = dict(
        base,
        excluded=["learned rise"],
        prerequisites=["Do not enable learned rise or write zero."],
        safety_notes="Never use the raw servo endpoint.",
    )
    assert orchestrator._physical_followup_rejection(passive_prohibitions, 3) == ""
    nested_action = dict(
        base,
        excluded={
            "summary": "No learned rise.",
            "command": ["uv", "run", "tool", "--learned-rise"],
        },
    )
    assert "forbidden" in orchestrator._physical_followup_rejection(
        nested_action, 3
    )

    prefixed = dict(base, runner="rl_move/scripts/run_rl_walk_trial.py.evil")
    hard_rejection, readiness_reason = orchestrator._physical_followup_review(
        prefixed, 3
    )
    assert hard_rejection == ""
    assert "trusted deterministic executor" in readiness_reason
    injected_runner = dict(base, runner="rl_move/scripts/run_rl_walk_trial.py;evil")
    assert "suspicious" in orchestrator._physical_followup_rejection(
        injected_runner, 3
    )
    fake_hash = dict(base, runner_sha256="a" * 64)
    assert "does not match" in orchestrator._physical_followup_rejection(fake_hash, 3)
    fast = dict(base, speed_m_s=0.081)
    assert "speed" in orchestrator._physical_followup_rejection(fast, 3)
    yaw = dict(base, wz_rad_s=0.1)
    assert "yaw" in orchestrator._physical_followup_rejection(yaw, 3)

    sysid_plan = {
        "current_compatibility": {"ready": True},
        "runner": "sysid.run_hw",
        "runner_sha256": sha256(sysid),
        "protocol": "sysid/protocols/l5_ground_radial_shear_amplitude_ladder_v1.json",
        "protocol_sha256": sha256(protocol),
        "motion_duration_s": 174,
        "leg": 5,
        "moving_joints": [16, 17],
        "runner_arguments": {
            "protocol": "sysid/protocols/l5_ground_radial_shear_amplitude_ladder_v1.json",
            "capture_vision": True,
            "capture_frames": True,
            "vision_hz": 10,
        },
    }
    assert "automatic sysid execution is disabled" in (
        orchestrator._physical_followup_rejection(sysid_plan, 174)
    )
    injection = dict(sysid_plan, runner="sysid.run_hw;anything")
    assert "suspicious" in orchestrator._physical_followup_rejection(injection, 174)
    unsafe_joint = dict(sysid_plan, moving_joints=[0, 16])
    assert "hip/knee" in (
        orchestrator._physical_followup_rejection(unsafe_joint, 174)
    )
    incompatible_fast = dict(base, current_compatibility={"ready": False}, speed_m_s=1)
    hard_rejection, readiness_reason = orchestrator._physical_followup_review(
        incompatible_fast, 3
    )
    assert "speed" in hard_rejection
    assert readiness_reason == ""
    false_non_motion = {"robot_motion": False, "runner": "benign.py"}
    assert "may not carry" in orchestrator._physical_followup_rejection(
        false_non_motion, 1
    )


def test_manifest_verification_rejects_files_added_after_sealing(tmp_path):
    run_dir = tmp_path / "evidence"
    run_dir.mkdir()
    (run_dir / "summary.md").write_text("measured\n", encoding="utf-8")
    ExperimentRunner._write_manifest(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    CodexOrchestrator._verify_manifest_artifacts(run_dir, manifest)

    (run_dir / "late.csv").write_text("not sealed\n", encoding="utf-8")
    with pytest.raises(CodexRunError, match="unsealed additions"):
        CodexOrchestrator._verify_manifest_artifacts(run_dir, manifest)


def test_reconciler_does_not_seal_while_upload_lease_exists(tmp_path):
    settings = configured(tmp_path)
    store = Store(settings.data_dir / "lab.sqlite3")
    item = store.create({"name": "external", "duration_seconds": 1}, "test")
    store.finish(item["id"], "succeeded")
    run_dir = settings.data_dir / "experiments" / item["id"]
    run_dir.mkdir(parents=True)
    (run_dir / "experiment.json").write_text("{}\n", encoding="utf-8")
    (run_dir / "summary.md").write_text("result\n", encoding="utf-8")
    lease = run_dir / ".telemetry.csv.active.upload"
    lease.write_bytes(b"partial")
    orchestrator = CodexOrchestrator(store, settings, invoker=lambda *_: {})

    assert orchestrator.reconcile_evidence() == 0
    assert store.get(item["id"])["evidence_sealed_at"] is None
    lease.unlink()
    assert orchestrator.reconcile_evidence() == 1


def test_reconciler_dead_letters_missing_evidence_at_deadline(tmp_path):
    settings = configured(tmp_path, codex_evidence_deadline_seconds=0)
    store = Store(settings.data_dir / "lab.sqlite3")
    item = store.create({"name": "crashed result", "duration_seconds": 1}, "test")
    store.finish(item["id"], "succeeded")
    orchestrator = CodexOrchestrator(store, settings, invoker=lambda *_: {})

    assert orchestrator.reconcile_evidence() == 0
    jobs = store.codex_jobs_for_experiment(item["id"])
    assert {job["kind"]: job["status"] for job in jobs} == {
        "analysis": "dead",
        "advance": "blocked",
    }
    assert store.codex_queue_control()["paused"] is True
