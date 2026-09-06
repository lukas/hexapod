"""Tests for `--defer-final-artifacts` (fb_20260906T032210_129bed item 1
implementation handoff, 09-06): additive-only instrumentation that
persists `<checkpoint>.training_complete.json` the instant
`model.learn()` returns, before the background eval/video drain that
otherwise holds the GPU-owning trainer idle for minutes doing CPU-only
work. Default OFF, no behavior change when unset; this is NOT itself a
capacity fix (the trainer still calls `bg.shutdown()` and waits) — see
the docstring on `_write_training_complete_marker` and
OPERATOR_QUESTIONS.md for the remaining steps.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from rl_move.sim.train_ppo_mjx import (  # noqa: E402
    _json_safe_config,
    _write_training_complete_marker,
)


def test_help_text_wires_flag():
    out = subprocess.run(
        [sys.executable, "-m", "rl_move.sim.train_ppo_mjx", "--help"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=60,
    )
    assert out.returncode == 0, out.stderr
    assert "--defer-final-artifacts" in out.stdout


def test_marker_written_atomically_with_expected_fields(tmp_path):
    ckpt = tmp_path / "ppo_goal_cw_test.zip"
    ckpt.write_bytes(b"fake checkpoint bytes")

    marker_path = _write_training_complete_marker(
        ckpt, steps=1_234_567, run_name="cw-test-run", task="joint_walk",
        run_id="abcd1234", resolved_config={"seed": 1, "steps": 1234567})

    assert marker_path == ckpt.parent / "ppo_goal_cw_test.training_complete.json"
    assert marker_path.exists()
    # no leftover tmp file (rename, not copy)
    assert not (marker_path.parent / (marker_path.name + ".tmp")).exists()

    payload = json.loads(marker_path.read_text())
    assert payload["run_name"] == "cw-test-run"
    assert payload["task"] == "joint_walk"
    assert payload["steps"] == 1_234_567
    assert payload["checkpoint_path"] == str(ckpt)
    assert payload["wandb_run_id"] == "abcd1234"
    assert payload["resolved_config"] == {"seed": 1, "steps": 1234567}
    # md5 of the exact bytes just written
    import hashlib
    assert payload["checkpoint_md5"] == hashlib.md5(
        ckpt.read_bytes()).hexdigest()


def test_marker_handles_missing_checkpoint_gracefully(tmp_path):
    ckpt = tmp_path / "not_yet_saved.zip"
    marker_path = _write_training_complete_marker(
        ckpt, steps=100, run_name="r", task="t", run_id=None,
        resolved_config={})
    payload = json.loads(marker_path.read_text())
    assert payload["checkpoint_md5"] is None
    assert payload["wandb_run_id"] is None


def test_json_safe_config_stringifies_non_primitives():
    ns = argparse.Namespace(
        seed=1, steps=2_000_000, run_name="r", flag=True, missing=None,
        cfg_set=["a=1", "b=2"], weird_path=Path("/tmp/x"))
    out = _json_safe_config(ns)
    assert out["seed"] == 1
    assert out["steps"] == 2_000_000
    assert out["flag"] is True
    assert out["missing"] is None
    assert out["cfg_set"] == ["a=1", "b=2"]
    assert out["weird_path"] == str(Path("/tmp/x"))
    # must round-trip through json.dumps with no surprises
    json.dumps(out)


# ---------------------------------------------------------------------------
# Items 2-5 (fb_20260906T035950_cd260e): durable manifest + registry
# phases, non-blocking _on_training_end, _BgEval deferred bookkeeping,
# and the CPU finalizer's retry/resume loop (stub job runners — the real
# worker is exercised by the opt-in canary run on a train pod).

from rl_move.sim import artifact_handoff as ah  # noqa: E402
from rl_move.sim.artifact_finalizer import (  # noqa: E402
    confirm_published, finalize, run_session)


def _mk_handoff(tmp_path, jobs, run_id="wb123"):
    d = ah.handoff_dir_for("cw-test-run", root=tmp_path)
    ah.init_training_state("cw-test-run", root=tmp_path)
    ckpt = tmp_path / "final.zip"
    ckpt.write_bytes(b"ckpt")
    for j in jobs:
        Path(j["snapshot_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(j["snapshot_path"]).write_bytes(b"snap")
    ah.write_manifest(
        d, run_name="cw-test-run", task="joint_walk",
        wandb_run_id=run_id, wandb_entity="e", wandb_project="p",
        checkpoint_path=ckpt, checkpoint_md5="beef", steps=1000,
        jobs=jobs, args_namespace=argparse.Namespace(seed=1),
        resolved_argv=["--steps", "1000"])
    return d


def _job(tmp_path, jid, kind="eval", step=100, tag=None):
    return {"job_id": jid, "kind": kind, "step": step, "tag": tag,
            "snapshot_path": str(tmp_path / "snaps" / f"{jid}.zip")}


def test_registry_phases_training_pending_logged_then_evaluated(tmp_path):
    """Publication-confirmation semantics (09-06 root review item 1):
    finalize alone leaves jobs `logged_pending_flush` and the phase at
    `artifacts_pending` — only confirm_published (called after a
    SUCCESSFUL run.finish()) flips jobs to done and the phase to
    evaluated."""
    jobs = [_job(tmp_path, "eval_100_periodic_001")]
    d = ah.handoff_dir_for("cw-test-run", root=tmp_path)
    ah.init_training_state("cw-test-run", root=tmp_path)
    assert ah.read_state(d)["phase"] == ah.PHASE_TRAINING
    d = _mk_handoff(tmp_path, jobs)
    assert ah.read_state(d)["phase"] == ah.PHASE_ARTIFACTS_PENDING
    logged = []
    summary = finalize(
        d, run_job=lambda j: {"kind": j["kind"], "step": j["step"],
                              "payload": {"ok": 1}},
        log_result=lambda j, o: logged.append(j["job_id"]))
    st = ah.read_state(d)
    # UNCONFIRMED until finish(): not evaluated, not done, no finalized
    assert st["phase"] == ah.PHASE_ARTIFACTS_PENDING
    assert (st["jobs"]["eval_100_periodic_001"]["status"]
            == ah.JOB_LOGGED_PENDING_FLUSH)
    assert logged == ["eval_100_periodic_001"]
    assert not (d / ah.FINALIZED_NAME).exists()
    # Replayable-input retention (fb_20260906T044800): the snapshot is
    # NOT deleted inside finalize (wandb.log is async — durable only
    # after run.finish()); it is listed for the caller to retire after
    # a successful finish + confirmation.
    assert Path(jobs[0]["snapshot_path"]).exists()
    assert summary["delivered_snapshots"] == [jobs[0]["snapshot_path"]]
    # Post-finish confirmation flips everything
    confirm_published(d, summary)
    st = ah.read_state(d)
    assert st["phase"] == ah.PHASE_EVALUATED
    assert st["jobs"]["eval_100_periodic_001"]["status"] == "done"
    assert (d / ah.FINALIZED_NAME).exists()


def test_manifest_reuse_rejected(tmp_path):
    """Reused-directory collision (fb_20260906T044800): a second
    write_manifest into the same dir must REFUSE, not silently mix two
    sessions' jobs (the old code renamed the manifest aside and went on)."""
    import pytest

    d = _mk_handoff(tmp_path, [])
    first = (d / ah.MANIFEST_NAME).read_text()
    with pytest.raises(RuntimeError, match="refusing to reuse"):
        ah.write_manifest(
            d, run_name="cw-test-run", task="joint_walk", wandb_run_id="x2",
            wandb_entity="e", wandb_project="p",
            checkpoint_path=tmp_path / "final.zip", checkpoint_md5="dead",
            steps=2000, jobs=[], args_namespace=argparse.Namespace())
    # original manifest untouched
    assert (d / ah.MANIFEST_NAME).read_text() == first


def test_init_training_state_supersedes_stale_dir(tmp_path):
    """A leftover handoff dir from a PRIOR training of the same run name
    (has a manifest) is moved aside append-only, never mixed into the
    new session."""
    d = _mk_handoff(tmp_path, [_job(tmp_path, "eval_100_periodic_001")])
    old_manifest = (d / ah.MANIFEST_NAME).read_text()
    d2 = ah.init_training_state("cw-test-run", root=tmp_path)
    assert d2 == d
    assert not (d2 / ah.MANIFEST_NAME).exists()  # fresh dir
    assert ah.read_state(d2)["phase"] == ah.PHASE_TRAINING
    stashes = list(tmp_path.glob("cw-test-run.superseded.*"))
    assert len(stashes) == 1
    assert (stashes[0] / ah.MANIFEST_NAME).read_text() == old_manifest


def test_manifest_freezes_snapshot_md5_and_provenance(tmp_path):
    """Per-job checkpoint md5 + code/config provenance are frozen into
    the manifest at handoff (fb_20260906T044800 provenance item)."""
    import hashlib

    jobs = [_job(tmp_path, "eval_100_periodic_001")]
    d = _mk_handoff(tmp_path, jobs)
    m = json.loads((d / ah.MANIFEST_NAME).read_text())
    snap = Path(jobs[0]["snapshot_path"])
    assert m["jobs"][0]["snapshot_md5"] == hashlib.md5(
        snap.read_bytes()).hexdigest()
    prov = m["provenance"]
    # args.pkl hash must match the file actually written
    assert prov["args_pkl_sha256"] == hashlib.sha256(
        (d / ah.ARGS_PICKLE_NAME).read_bytes()).hexdigest()
    # git provenance is best-effort but present in a git checkout
    assert ("git_commit" in prov) or ("git_error" in prov)
    # runtime fingerprint (09-06 root review item 2): aggregate hash in
    # the manifest, full per-file map in fingerprint.json, both consistent
    assert m["schema"] == 3
    fp = json.loads((d / ah.FINGERPRINT_NAME).read_text())
    assert prov["code_fingerprint_sha256"] == fp["fingerprint_sha256"]
    assert prov["code_fingerprint_n_files"] == fp["n_files"] == len(
        fp["files"])
    # the map covers the real runtime surface of this checkout
    assert any(k.endswith("rl_move/sim/train_ppo_sim.py")
               for k in fp["files"])
    assert any("mesh_mujoco" in k and k.endswith(".xml")
               for k in fp["files"])
    # mutable artifact trees must NOT be in the fingerprint (they change
    # during finalization and would self-invalidate)
    assert not any("policies" in k or "wandb" in k or "__pycache__" in k
                   for k in fp["files"])


def test_finalizer_bounded_retry_then_failed_phase(tmp_path):
    jobs = [_job(tmp_path, "video_200_final_001", kind="video", step=200)]
    d = _mk_handoff(tmp_path, jobs)
    attempts = []
    summary = finalize(
        d, run_job=lambda j: (attempts.append(1) or
                              {"kind": "video", "step": 200,
                               "error": "boom"}),
        log_result=lambda j, o: (_ for _ in ()).throw(
            AssertionError("must not log failed jobs")),
        max_attempts=2)
    assert len(attempts) == 2  # bounded, not infinite
    st = ah.read_state(d)
    assert st["jobs"]["video_200_final_001"]["status"] == "failed"
    assert st["jobs"]["video_200_final_001"]["attempts"] == 2
    assert summary["failed"] == 1
    # failed phase is set by the post-finish confirmation
    confirm_published(d, summary)
    assert ah.read_state(d)["phase"] == ah.PHASE_FAILED


def test_finalizer_resume_skips_done_retries_in_flight(tmp_path):
    """Interrupted-finalizer semantics: a job already marked done is
    NOT re-logged (single W&B delivery), an in_flight one (killed
    mid-attempt) is retried with its attempt budget honored."""
    jobs = [_job(tmp_path, "eval_100_periodic_001"),
            _job(tmp_path, "eval_200_periodic_002", step=200)]
    d = _mk_handoff(tmp_path, jobs)
    # Simulate a prior finalizer killed after delivering job 1 and
    # mid-attempt on job 2:
    ah.update_state(d, jobs={
        "eval_100_periodic_001": {"status": "done", "attempts": 1},
        "eval_200_periodic_002": {"status": "in_flight", "attempts": 1}})
    ran, logged = [], []
    summary = finalize(
        d, run_job=lambda j: (ran.append(j["job_id"]) or
                              {"kind": "eval", "step": j["step"],
                               "payload": {}}),
        log_result=lambda j, o: logged.append(j["job_id"]), max_attempts=2)
    assert ran == ["eval_200_periodic_002"]      # done job untouched
    assert logged == ["eval_200_periodic_002"]   # exactly one delivery
    assert summary["skipped_done"] == 1
    confirm_published(d, summary)
    st = ah.read_state(d)
    assert st["phase"] == ah.PHASE_EVALUATED
    assert st["jobs"]["eval_200_periodic_002"]["status"] == "done"


def test_snapshot_md5_mismatch_fails_job_without_running(tmp_path):
    """Integrity gate: a snapshot whose bytes do not match the manifest
    md5 (corrupt / foreign / truncated) must fail WITHOUT running —
    publishing wrong-model artifacts is worse than a failed job."""
    jobs = [_job(tmp_path, "eval_100_periodic_001")]
    d = _mk_handoff(tmp_path, jobs)
    Path(jobs[0]["snapshot_path"]).write_bytes(b"CORRUPTED")  # post-manifest
    ran = []
    summary = finalize(
        d, run_job=lambda j: ran.append(j["job_id"]),
        log_result=lambda j, o: (_ for _ in ()).throw(
            AssertionError("must not log")), max_attempts=2)
    assert ran == []  # never executed
    assert summary["failed"] == 1
    st = ah.read_state(d)
    assert st["jobs"]["eval_100_periodic_001"]["status"] == "failed"
    assert "integrity" in st["jobs"]["eval_100_periodic_001"]["last_error"]
    confirm_published(d, summary)
    assert ah.read_state(d)["phase"] == ah.PHASE_FAILED


def test_crash_between_log_and_state_write_is_at_least_once(tmp_path):
    """Crash-boundary semantics: a kill in the window after log_result
    but before the done-state write re-delivers that ONE job on resume
    (at-least-once — never claim exactly-once from W&B row counts), and
    the replayable snapshot is still on disk for the replay."""
    jobs = [_job(tmp_path, "eval_100_periodic_001")]
    d = _mk_handoff(tmp_path, jobs)
    logged = []

    def _log_then_die(j, o):
        logged.append(j["job_id"])
        raise KeyboardInterrupt  # simulated SIGINT in the window

    try:
        finalize(d, run_job=lambda j: {"kind": "eval", "step": 100,
                                       "payload": {}},
                 log_result=_log_then_die)
        raise AssertionError("finalize must propagate the crash")
    except KeyboardInterrupt:
        pass
    st = ah.read_state(d)
    assert st["jobs"]["eval_100_periodic_001"]["status"] == "in_flight"
    assert Path(jobs[0]["snapshot_path"]).exists()  # replayable input kept
    # resume: the job is re-run and re-delivered (duplicate row possible)
    summary = finalize(
        d, run_job=lambda j: {"kind": "eval", "step": 100, "payload": {}},
        log_result=lambda j, o: logged.append(j["job_id"]))
    assert logged == ["eval_100_periodic_001", "eval_100_periodic_001"]
    assert summary["done"] == 1
    confirm_published(d, summary)
    assert ah.read_state(d)["phase"] == ah.PHASE_EVALUATED


# ---------------------------------------------------------------------------
# 09-06 root review item 1 (operator focus note 20260906T052705Z):
# publication must be CONFIRMED by run.finish(), not assumed at wandb.log
# time. Fault injections: crash exactly between log and finish, and
# finish() raising.


def test_crash_between_log_and_finish_replays_unconfirmed(tmp_path):
    """THE reviewed bug: old code marked JOB_DONE right after the async
    wandb.log and skipped it on restart, so a crash before run.finish()
    silently lost the publication despite retained files. Now: a
    finalizer that dies after finalize() but BEFORE finish() leaves the
    job logged_pending_flush / phase artifacts_pending / no
    finalized.json, and a restarted finalizer REPLAYS it from the
    retained snapshot (at-least-once: duplicate W&B row accepted)."""
    jobs = [_job(tmp_path, "eval_100_periodic_001")]
    d = _mk_handoff(tmp_path, jobs)
    logged = []
    finalize(d, run_job=lambda j: {"kind": "eval", "step": 100,
                                   "payload": {}},
             log_result=lambda j, o: logged.append(j["job_id"]))
    # process dies HERE (before finish/confirm): simulated by simply not
    # calling confirm_published.
    st = ah.read_state(d)
    assert (st["jobs"]["eval_100_periodic_001"]["status"]
            == ah.JOB_LOGGED_PENDING_FLUSH)
    assert st["phase"] == ah.PHASE_ARTIFACTS_PENDING  # NOT evaluated
    assert not (d / ah.FINALIZED_NAME).exists()
    assert Path(jobs[0]["snapshot_path"]).exists()  # retained for replay
    # restart: unconfirmed job is replayed (not skipped as done)
    ran = []
    summary = finalize(
        d, run_job=lambda j: (ran.append(j["job_id"]) or
                              {"kind": "eval", "step": 100, "payload": {}}),
        log_result=lambda j, o: logged.append(j["job_id"]))
    assert ran == ["eval_100_periodic_001"]
    assert logged == ["eval_100_periodic_001", "eval_100_periodic_001"]
    assert summary["replayed_unconfirmed"] == 1
    confirm_published(d, summary)
    st = ah.read_state(d)
    assert st["phase"] == ah.PHASE_EVALUATED
    assert st["jobs"]["eval_100_periodic_001"]["status"] == "done"


def test_finish_raising_leaves_unconfirmed_and_replays(tmp_path):
    """run.finish() raising = publication NOT durable: run_session must
    return the finish-failure code, keep the job logged_pending_flush,
    NOT write finalized.json, NOT retire inputs, NOT report evaluated.
    A later session with a working finish replays and confirms."""
    jobs = [_job(tmp_path, "eval_100_periodic_001")]
    d = _mk_handoff(tmp_path, jobs)
    logged, shutdowns = [], []

    def _bad_finish():
        raise RuntimeError("wandb service unreachable")

    rc = run_session(
        d, run_job=lambda j: {"kind": "eval", "step": 100, "payload": {}},
        log_result=lambda j, o: logged.append(j["job_id"]),
        finish=_bad_finish, shutdown=lambda: shutdowns.append(1))
    assert rc == 3
    assert shutdowns == [1]  # worker still torn down
    st = ah.read_state(d)
    assert (st["jobs"]["eval_100_periodic_001"]["status"]
            == ah.JOB_LOGGED_PENDING_FLUSH)
    assert st["phase"] == ah.PHASE_ARTIFACTS_PENDING
    assert "UNCONFIRMED" in st["note"]
    assert not (d / ah.FINALIZED_NAME).exists()
    assert Path(jobs[0]["snapshot_path"]).exists()  # nothing retired
    # next session: replay + confirm + retire
    rc = run_session(
        d, run_job=lambda j: {"kind": "eval", "step": 100, "payload": {}},
        log_result=lambda j, o: logged.append(j["job_id"]),
        finish=lambda: None)
    assert rc == 0
    assert logged == ["eval_100_periodic_001"] * 2  # at-least-once
    st = ah.read_state(d)
    assert st["phase"] == ah.PHASE_EVALUATED
    assert st["jobs"]["eval_100_periodic_001"]["status"] == "done"
    assert (d / ah.FINALIZED_NAME).exists()
    assert not Path(jobs[0]["snapshot_path"]).exists()  # retired now


def test_run_session_success_confirms_and_retires(tmp_path):
    """Happy path through the factored session: finish OK -> confirmed
    done/evaluated, finalized.json written, snapshots + extra retire
    paths (rendered mp4s) removed."""
    jobs = [_job(tmp_path, "video_200_final_001", kind="video", step=200)]
    d = _mk_handoff(tmp_path, jobs)
    mp4 = tmp_path / "reel.mp4"
    mp4.write_bytes(b"mp4")
    rc = run_session(
        d, run_job=lambda j: {"kind": "video", "step": 200,
                              "path": str(mp4)},
        log_result=lambda j, o: None, finish=lambda: None,
        retire_paths=[str(mp4)])
    assert rc == 0
    st = ah.read_state(d)
    assert st["phase"] == ah.PHASE_EVALUATED
    assert st["jobs"]["video_200_final_001"]["status"] == "done"
    assert not Path(jobs[0]["snapshot_path"]).exists()
    assert not mp4.exists()
    assert json.loads((d / ah.FINALIZED_NAME).read_text())["done"] == 1


# ---------------------------------------------------------------------------
# 09-06 root review item 2: provenance must be ENFORCED — the finalizer
# imports the live worker and unpickles args.pkl, so code/config/XML/args
# changed between handoff and (re)start must be REFUSED, not silently
# executed. Fault injections: change code, change XML, change args.pkl.


def _mk_fake_repo(tmp_path):
    root = tmp_path / "fakerepo"
    (root / "rl_move" / "sim").mkdir(parents=True)
    (root / "mesh_mujoco").mkdir()
    (root / "rl_move" / "sim" / "train_ppo_sim.py").write_text(
        "WORKER = 1\n")
    (root / "rl_move" / "config.yaml").write_text("safety: {}\n")
    (root / "mujoco_prototype.py").write_text("XMLGEN = 1\n")
    (root / "mesh_mujoco" / "hexapod_mesh_mjx.xml").write_text(
        "<mujoco/>\n")
    return root


def _mk_handoff_fp(tmp_path, repo_root, jobs=()):
    d = ah.handoff_dir_for("cw-fp-run", root=tmp_path)
    ah.init_training_state("cw-fp-run", root=tmp_path)
    ckpt = tmp_path / "final.zip"
    ckpt.write_bytes(b"ckpt")
    for j in jobs:
        Path(j["snapshot_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(j["snapshot_path"]).write_bytes(b"snap")
    ah.write_manifest(
        d, run_name="cw-fp-run", task="joint_walk", wandb_run_id=None,
        wandb_entity="e", wandb_project="p", checkpoint_path=ckpt,
        checkpoint_md5="beef", steps=1000, jobs=list(jobs),
        args_namespace=argparse.Namespace(seed=1),
        fingerprint_root=repo_root)
    return d


def test_fingerprint_matches_when_nothing_changed(tmp_path):
    repo = _mk_fake_repo(tmp_path)
    d = _mk_handoff_fp(tmp_path, repo)
    m = json.loads((d / ah.MANIFEST_NAME).read_text())
    ok, msg = ah.verify_runtime_fingerprint(d, m, repo_root=repo)
    assert ok and "verified" in msg


def test_fingerprint_refuses_code_change_between_handoff_and_restart(
        tmp_path):
    repo = _mk_fake_repo(tmp_path)
    d = _mk_handoff_fp(tmp_path, repo)
    m = json.loads((d / ah.MANIFEST_NAME).read_text())
    (repo / "rl_move" / "sim" / "train_ppo_sim.py").write_text(
        "WORKER = 2  # changed reward semantics\n")
    ok, msg = ah.verify_runtime_fingerprint(d, m, repo_root=repo)
    assert not ok
    assert "MISMATCH" in msg
    assert "train_ppo_sim.py" in msg  # names the changed file


def test_fingerprint_refuses_xml_and_config_change(tmp_path):
    repo = _mk_fake_repo(tmp_path)
    d = _mk_handoff_fp(tmp_path, repo)
    m = json.loads((d / ah.MANIFEST_NAME).read_text())
    (repo / "mesh_mujoco" / "hexapod_mesh_mjx.xml").write_text(
        "<mujoco><option gravity='0 0 -1'/></mujoco>\n")
    ok, msg = ah.verify_runtime_fingerprint(d, m, repo_root=repo)
    assert not ok and "hexapod_mesh_mjx.xml" in msg
    # config file added/changed also refuses (set union of both maps)
    (repo / "mesh_mujoco" / "hexapod_mesh_mjx.xml").write_text("<mujoco/>\n")
    (repo / "rl_move" / "config.yaml").write_text("safety: {max: 1}\n")
    ok, msg = ah.verify_runtime_fingerprint(d, m, repo_root=repo)
    assert not ok and "config.yaml" in msg


def test_fingerprint_refuses_args_pkl_change(tmp_path):
    """args.pkl is verified against its recorded sha256 BEFORE anything
    unpickles it (finalizer previously loaded it unchecked)."""
    repo = _mk_fake_repo(tmp_path)
    d = _mk_handoff_fp(tmp_path, repo)
    m = json.loads((d / ah.MANIFEST_NAME).read_text())
    import pickle
    (d / ah.ARGS_PICKLE_NAME).write_bytes(
        pickle.dumps(argparse.Namespace(seed=999, task="other")))
    ok, msg = ah.verify_runtime_fingerprint(d, m, repo_root=repo)
    assert not ok and "args.pkl" in msg


def test_fingerprint_legacy_manifest_warns_not_verified(tmp_path):
    """A pre-schema-3 manifest (no fingerprint recorded) is not a
    mismatch, but must NEVER be reported as verified — documented
    at-most 'metadata-only' provenance."""
    repo = _mk_fake_repo(tmp_path)
    d = _mk_handoff_fp(tmp_path, repo)
    m = json.loads((d / ah.MANIFEST_NAME).read_text())
    del m["provenance"]["code_fingerprint_sha256"]
    ok, msg = ah.verify_runtime_fingerprint(d, m, repo_root=repo)
    assert ok
    assert "NOT verified" in msg


def test_finalizer_main_refuses_on_fingerprint_mismatch(tmp_path):
    """End-to-end wiring: artifact_finalizer.main() must exit 4 and
    refuse job execution/publication when the tree changed after
    handoff — and succeed (confirm + evaluated) when it matches."""
    from rl_move.sim.artifact_finalizer import main as fmain

    repo = _mk_fake_repo(tmp_path)
    d = _mk_handoff_fp(tmp_path, repo)  # no jobs, no wandb id
    # untampered: runs through session, confirms, evaluates
    rc = fmain(["--handoff-dir", str(d), "--fingerprint-root", str(repo)])
    assert rc == 0
    assert ah.read_state(d)["phase"] == ah.PHASE_EVALUATED
    # tamper the code -> a fresh session refuses before executing
    repo2 = _mk_fake_repo(tmp_path / "second")
    d2 = _mk_handoff_fp(tmp_path / "second", repo2)
    (repo2 / "mujoco_prototype.py").write_text("XMLGEN = 999\n")
    rc = fmain(["--handoff-dir", str(d2),
                "--fingerprint-root", str(repo2)])
    assert rc == 4
    st = ah.read_state(d2)
    assert st["phase"] == ah.PHASE_ARTIFACTS_PENDING  # never evaluated
    assert "REFUSED" in st["note"]
    assert not (d2 / ah.FINALIZED_NAME).exists()
    # operator override runs anyway (logged loudly)
    rc = fmain(["--handoff-dir", str(d2), "--fingerprint-root",
                str(repo2), "--allow-fingerprint-mismatch"])
    assert rc == 0


def test_video_callback_training_end_nonblocking_when_deferred():
    """Ordering fix: with the flag set, _on_training_end submits the
    final reel WITHOUT bg.wait() — the pre-fix blocking wait inside
    model.learn() made the training_complete marker meaningless."""
    from rl_move.sim.train_ppo_sim import _make_video_callback

    class _StubBg:
        def __init__(self):
            self.calls = []

        def wait(self, *a, **k):
            self.calls.append("wait")

        def submit(self, kind, model, step, tag=None):
            self.calls.append(("submit", kind, tag))

        def busy(self, kind):
            return True  # would force the callback to skip periodics

    class _M:
        num_timesteps = 999

    # deferred: submit only, no wait
    bg = _StubBg()
    cb = _make_video_callback(
        bg, 10**9, argparse.Namespace(defer_final_artifacts=True))
    cb.model = _M()
    object.__setattr__(cb, "num_timesteps", 999)
    cb._on_training_end()
    assert bg.calls == [("submit", "video", "final")]

    # default OFF (attribute absent entirely, like train_ppo_sim args):
    bg2 = _StubBg()
    cb2 = _make_video_callback(bg2, 10**9, argparse.Namespace())
    cb2.model = _M()
    object.__setattr__(cb2, "num_timesteps", 999)
    cb2._on_training_end()
    assert bg2.calls == ["wait", ("submit", "video", "final")]


def test_bgeval_deferred_bookkeeping_without_worker(tmp_path):
    """submit() records durable pending jobs; drain() retires delivered
    ones; handoff() returns the rest. Worker/queues are stubbed — the
    real spawn path is covered by the opt-in canary."""
    import queue as _q

    from rl_move.sim.train_ppo_sim import _BgEval

    bge = object.__new__(_BgEval)  # no __init__: no child process
    bge._busy = {"eval": 0, "video": 0}
    bge._canaries = []
    from collections import deque
    bge._evals = deque(maxlen=4)
    bge._defer_dir = tmp_path
    bge._deferred_pending = {}
    bge._deferred_delivered = []
    bge._deferred_seq = 0
    (tmp_path / "snapshots").mkdir()

    class _Q:
        def __init__(self):
            self.items = []

        def put(self, x):
            self.items.append(x)

        def get_nowait(self):
            raise _q.Empty

    bge._jobs = _Q()
    bge._results = _Q()

    class _Model:
        def save(self, p):
            Path(p).write_bytes(b"snap")

    bge.submit("eval", _Model(), 100)
    bge.submit("video", _Model(), 200, tag="final")
    assert len(bge._deferred_pending) == 2
    snaps = sorted(p.name for p in (tmp_path / "snapshots").iterdir())
    assert snaps == ["eval_100_periodic_001.zip", "video_200_final_002.zip"]
    # snapshot identity frozen at save time for the finalizer's check
    import hashlib as _hl
    for rec in bge._deferred_pending.values():
        assert rec["snapshot_md5"] == _hl.md5(
            Path(rec["snapshot_path"]).read_bytes()).hexdigest()

    # deliver the eval result (child echoes ckpt), keep video outstanding
    done_ckpt = str(tmp_path / "snapshots" / "eval_100_periodic_001.zip")
    results = [{"kind": "eval", "step": 100, "ckpt": done_ckpt,
                "payload": {"global_step": 100}, "brief": "ok"}]

    def _get_nowait():
        if results:
            return results.pop(0)
        raise _q.Empty

    bge._results.get_nowait = _get_nowait
    import unittest.mock as _mock
    with _mock.patch("wandb.log"):
        bge.drain()
    assert len(bge._deferred_pending) == 1
    # Delivered snapshot is RETAINED until run.finish() (async wandb.log,
    # fb_20260906T044800): drain moves it to the delivered list; the
    # trainer retires it via pop_delivered() after finish.
    assert Path(done_ckpt).exists()
    assert bge._deferred_delivered == [done_ckpt]
    out = list(bge._deferred_pending.values())
    assert out[0]["job_id"] == "video_200_final_002"
    assert Path(out[0]["snapshot_path"]).exists()  # survives for finalizer
    assert bge.pop_delivered() == [done_ckpt]
    assert bge.pop_delivered() == []  # drained exactly once


# ---------------------------------------------------------------------------
# Single-writer flock lock (fb_20260906T044800_a59c3e /
# 09-06 operator focus note): permanent-inode kernel flock replaces the
# pid-file steal scheme. Real-subprocess tests: contention, SIGKILL with
# an UNREAPED (zombie) holder, and a surviving exec'ed child must NOT
# inherit the lock (O_CLOEXEC).

import os  # noqa: E402
import signal  # noqa: E402
import time  # noqa: E402

from rl_move.sim.artifact_handoff import (  # noqa: E402
    FINALIZER_LOCK_NAME, acquire_finalizer_lock)

_HOLDER = """
import subprocess, sys, time
from pathlib import Path
sys.path.insert(0, {root!r})
from rl_move.sim.artifact_handoff import acquire_finalizer_lock
fd = acquire_finalizer_lock(Path(sys.argv[1]))
if fd is None:
    print("refused", flush=True)
    sys.exit(3)
mode = sys.argv[2]
if mode == "spawn_child_and_exit":
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(120)"])
    print(f"acquired child={{child.pid}}", flush=True)
    sys.exit(0)  # holder dies, exec'ed child lives on
print("acquired", flush=True)
time.sleep(float(mode))
"""


def _start_holder(tmp_path, mode):
    proc = subprocess.Popen(
        [sys.executable, "-c", _HOLDER.format(root=str(ROOT)),
         str(tmp_path), mode],
        stdout=subprocess.PIPE, text=True)
    line = proc.stdout.readline().strip()
    assert line.startswith("acquired"), line
    return proc, line


def _try_acquire(tmp_path, timeout_s=10.0):
    """Poll-acquire (kernel release after a kill is quick but not
    instantaneous). Returns fd or None."""
    deadline = time.monotonic() + timeout_s
    while True:
        fd = acquire_finalizer_lock(tmp_path)
        if fd is not None or time.monotonic() > deadline:
            return fd
        time.sleep(0.1)


def test_lock_contention_two_processes(tmp_path):
    proc, _ = _start_holder(tmp_path, "30")
    try:
        # in-process contender refused while holder lives
        assert acquire_finalizer_lock(tmp_path) is None
        # a second subprocess contender is refused too (exit 3)
        rival = subprocess.run(
            [sys.executable, "-c", _HOLDER.format(root=str(ROOT)),
             str(tmp_path), "1"], capture_output=True, text=True)
        assert rival.returncode == 3 and "refused" in rival.stdout
    finally:
        proc.kill()
    proc.wait()
    fd = _try_acquire(tmp_path)
    assert fd is not None  # released on holder death
    os.close(fd)


def test_lock_released_on_sigkill_even_as_zombie(tmp_path):
    """The 09-06 canary failure mode: SIGKILLed holder lingers unreaped
    (train-pod pid 1 does not reap orphans). flock is released by the
    kernel at termination — BEFORE reaping — so a zombie never wedges
    the lock. We deliberately do NOT wait() before acquiring."""
    proc, _ = _start_holder(tmp_path, "60")
    os.kill(proc.pid, signal.SIGKILL)
    fd = _try_acquire(tmp_path)  # holder is a zombie right now
    try:
        assert fd is not None, "zombie holder wedged the flock"
    finally:
        if fd is not None:
            os.close(fd)
        proc.wait()  # reap only after the assertion


def test_lock_not_inherited_by_surviving_child(tmp_path):
    """O_CLOEXEC: an exec'ed grandchild (like the mp 'spawn' eval worker)
    spawned by the holder must not pin the lock after the holder exits."""
    proc, line = _start_holder(tmp_path, "spawn_child_and_exit")
    child_pid = int(line.split("child=")[1])
    try:
        proc.wait(timeout=10)  # holder exits; grandchild still sleeping
        # grandchild is alive
        os.kill(child_pid, 0)
        fd = _try_acquire(tmp_path)
        assert fd is not None, "exec'ed child inherited the flock"
        os.close(fd)
    finally:
        try:
            os.kill(child_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def test_lock_file_is_a_permanent_inode(tmp_path):
    """Acquire/release cycles must reuse the SAME inode and never unlink
    it — unlink+recreate is exactly the race the pid-file scheme had."""
    fd1 = acquire_finalizer_lock(tmp_path)
    ino1 = os.stat(tmp_path / FINALIZER_LOCK_NAME).st_ino
    os.close(fd1)
    fd2 = acquire_finalizer_lock(tmp_path)
    ino2 = os.stat(tmp_path / FINALIZER_LOCK_NAME).st_ino
    os.close(fd2)
    assert ino1 == ino2
    assert (tmp_path / FINALIZER_LOCK_NAME).exists()


def test_mjx_trainer_guards_double_save_when_deferred():
    """Tripwire for the marker double-save inconsistency
    (fb_20260906T044800): the deferred path saves out_path ONCE, before
    the md5 is frozen into the marker/manifest; the trailing
    model.save(out_path) must stay guarded by the flag or the recorded
    checksums silently stop matching the file."""
    src = (ROOT / "rl_move" / "sim" / "train_ppo_mjx.py").read_text()
    assert ("if not args.defer_final_artifacts:\n        model.save(out_path)"
            in src)
