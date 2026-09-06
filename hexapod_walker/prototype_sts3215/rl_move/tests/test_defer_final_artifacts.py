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
from rl_move.sim.artifact_finalizer import finalize  # noqa: E402


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


def test_registry_phases_training_pending_evaluated(tmp_path):
    jobs = [_job(tmp_path, "eval_100_periodic_001")]
    d = ah.handoff_dir_for("cw-test-run", root=tmp_path)
    ah.init_training_state("cw-test-run", root=tmp_path)
    assert ah.read_state(d)["phase"] == ah.PHASE_TRAINING
    d = _mk_handoff(tmp_path, jobs)
    assert ah.read_state(d)["phase"] == ah.PHASE_ARTIFACTS_PENDING
    logged = []
    finalize(d, run_job=lambda j: {"kind": j["kind"], "step": j["step"],
                                   "payload": {"ok": 1}},
             log_result=lambda j, o: logged.append(j["job_id"]))
    st = ah.read_state(d)
    assert st["phase"] == ah.PHASE_EVALUATED
    assert st["jobs"]["eval_100_periodic_001"]["status"] == "done"
    assert logged == ["eval_100_periodic_001"]
    assert (d / ah.FINALIZED_NAME).exists()
    # snapshot retired after successful delivery
    assert not Path(jobs[0]["snapshot_path"]).exists()


def test_manifest_is_immutable_rewrite_backs_up(tmp_path):
    d = _mk_handoff(tmp_path, [])
    first = (d / ah.MANIFEST_NAME).read_text()
    ah.write_manifest(
        d, run_name="cw-test-run", task="joint_walk", wandb_run_id="x2",
        wandb_entity="e", wandb_project="p",
        checkpoint_path=tmp_path / "final.zip", checkpoint_md5="dead",
        steps=2000, jobs=[], args_namespace=argparse.Namespace())
    backups = list(d.glob("manifest.*.json"))
    assert len(backups) == 1 and backups[0].read_text() == first


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
    assert st["phase"] == ah.PHASE_FAILED
    assert st["jobs"]["video_200_final_001"]["status"] == "failed"
    assert st["jobs"]["video_200_final_001"]["attempts"] == 2
    assert summary["failed"] == 1


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
    assert ah.read_state(d)["phase"] == ah.PHASE_EVALUATED


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
    assert not Path(done_ckpt).exists()  # retired after delivery
    out = list(bge._deferred_pending.values())
    assert out[0]["job_id"] == "video_200_final_002"
    assert Path(out[0]["snapshot_path"]).exists()  # survives for finalizer
