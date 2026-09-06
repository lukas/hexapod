"""CPU-only finalizer for `--defer-final-artifacts` (item 4 of
fb_20260906T032210_129bed, follow-through fb_20260906T035950_cd260e).

Runs DETACHED after the GPU-owning trainer process has exited: reads
the immutable job manifest written by `artifact_handoff.write_manifest`,
re-runs every still-outstanding background eval/video job with the SAME
worker function the trainer used (`train_ppo_sim._bg_eval_child`, real
C-MuJoCo envs, frozen per-job checkpoint snapshots), and logs the
results to the SAME W&B run via `wandb.init(id=..., resume="allow")`.

Guarantees:
- CPU only: `CUDA_VISIBLE_DEVICES=` is forced before any torch/jax
  import, in this process and (inherited) in the spawned worker.
- Single W&B writer: the trainer called `run.finish()` BEFORE spawning
  this process, and a pid lockfile (stale pids stolen) ensures at most
  one finalizer instance per run.
- Idempotent resume: per-job status/attempts live in state.json
  (atomic replace). A killed finalizer restarted later skips `done`
  jobs and retries `pending`/`in_flight`/`failed` ones up to
  --max-attempts. Delivery to W&B is at-least-once with job
  granularity: a kill in the tiny window between a wandb.log and its
  state write can duplicate ONE history row on resume — never a
  contradictory or missing artifact.
- Bounded: each job gets --max-attempts tries and a hard per-job
  timeout; a hung worker is killed and respawned; exhausted jobs are
  recorded `failed` in state.json + finalized.json rather than looping.
"""
from __future__ import annotations

import os

# MUST precede any torch/jax import chain (train_ppo_sim pulls in SB3).
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("JAX_PLATFORMS", "cpu")
# Never attach to a (dead) parent trainer's wandb-core service: scrub
# service-discovery vars so wandb.init spawns a fresh service here.
# (Belt and braces with spawn_finalizer's env scrub — also covers manual
# re-invocations from a shell that exported them.)
for _k in [k for k in os.environ if "WANDB" in k and "SERVICE" in k.upper()]:
    os.environ.pop(_k)

import argparse  # noqa: E402
import json  # noqa: E402
import pickle  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

from .artifact_handoff import (  # noqa: E402
    ARGS_PICKLE_NAME, FINALIZED_NAME, FINALIZER_PID_NAME, JOB_DONE,
    JOB_FAILED, JOB_IN_FLIGHT, MANIFEST_NAME, PHASE_EVALUATED,
    PHASE_FAILED, atomic_write_json, read_json, read_state, update_state,
)


def _pid_is_live_finalizer(pid: int) -> bool:
    """True only for a RUNNING artifact_finalizer process. os.kill(pid,0)
    alone is wrong on the train pods: pid 1 there does not reap orphans,
    so a SIGKILLed finalizer lingers as a zombie that os.kill still
    'sees' (observed on the 09-06 canary — a stale lock refused to be
    stolen). A zombie has an empty /proc/<pid>/cmdline."""
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return True  # no /proc (non-Linux): fall back to os.kill's answer
    return b"artifact_finalizer" in cmdline


def _acquire_lock(handoff_dir: Path) -> bool:
    """One finalizer per run. O_EXCL pidfile; a dead/zombie owner is
    stolen."""
    pid_path = handoff_dir / FINALIZER_PID_NAME
    if pid_path.exists():
        try:
            old = int(pid_path.read_text().strip())
        except ValueError:
            old = -1
        if old > 0 and _pid_is_live_finalizer(old):
            print(f"[finalizer] another instance (pid {old}) is live; "
                  "exiting")
            return False
        print("[finalizer] stealing stale lock")
        pid_path.unlink(missing_ok=True)
    fd = os.open(pid_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w") as fh:
        fh.write(str(os.getpid()))
    return True


class _WorkerRunner:
    """Owns the spawned `_bg_eval_child` worker; respawns it if a job
    hangs past the timeout (the worker holds real MuJoCo envs — a wedged
    render must not stall the whole finalize)."""

    def __init__(self, task: str, args, timeout_s: float):
        self._task, self._args, self._timeout = task, args, timeout_s
        self._proc = None

    def _ensure(self):
        if self._proc is not None and self._proc.is_alive():
            return
        import multiprocessing as mp
        from .train_ppo_sim import _bg_eval_child
        ctx = mp.get_context("spawn")
        self._jobs = ctx.Queue()
        self._results = ctx.Queue()
        self._proc = ctx.Process(
            target=_bg_eval_child,
            args=(self._jobs, self._results, self._task, self._args),
            daemon=True)
        self._proc.start()

    def run(self, job: dict) -> dict:
        import queue as _queue
        self._ensure()
        self._jobs.put((job["kind"], job["snapshot_path"],
                        int(job["step"]), job.get("tag")))
        try:
            return self._results.get(timeout=self._timeout)
        except _queue.Empty:
            print(f"[finalizer] job {job['job_id']} timed out after "
                  f"{self._timeout:.0f}s — killing worker")
            self._proc.terminate()
            self._proc.join(10)
            self._proc = None
            return {"kind": job["kind"], "step": job["step"],
                    "error": f"timeout>{self._timeout:.0f}s"}

    def shutdown(self):
        if self._proc is not None and self._proc.is_alive():
            self._jobs.put(None)
            self._proc.join(15)
            if self._proc.is_alive():
                self._proc.terminate()


def finalize(handoff_dir: Path, *, run_job, log_result,
             max_attempts: int = 2) -> dict:
    """Core loop, side-effect functions injected (tested with stubs).

    `run_job(job) -> out dict` executes one eval/video job;
    `log_result(job, out)` publishes it (W&B). State is written
    atomically around every attempt so a kill at any point resumes
    without losing which jobs were already delivered."""
    manifest = read_json(handoff_dir / MANIFEST_NAME)
    if manifest is None:
        raise FileNotFoundError(f"no {MANIFEST_NAME} in {handoff_dir}")
    state = read_state(handoff_dir) or {"jobs": {}}
    summary = {"done": 0, "skipped_done": 0, "failed": 0, "errors": {}}
    for job in manifest.get("jobs", []):
        jid = job["job_id"]
        row = dict(state.get("jobs", {}).get(
            jid, {"status": "pending", "attempts": 0}))
        if row.get("status") == JOB_DONE:
            summary["skipped_done"] += 1
            continue
        while int(row.get("attempts", 0)) < max_attempts:
            row["attempts"] = int(row.get("attempts", 0)) + 1
            row["status"] = JOB_IN_FLIGHT
            update_state(handoff_dir, jobs={jid: dict(row)})
            out = run_job(job)
            if out is not None and "error" not in out:
                log_result(job, out)
                row["status"] = JOB_DONE
                update_state(handoff_dir, jobs={jid: dict(row)})
                Path(job["snapshot_path"]).unlink(missing_ok=True)
                summary["done"] += 1
                break
            err = (out or {}).get("error", "no result")
            print(f"[finalizer] job {jid} attempt {row['attempts']} "
                  f"failed: {err}")
            row["last_error"] = err
            update_state(handoff_dir, jobs={jid: dict(row)})
        else:
            row["status"] = JOB_FAILED
            update_state(handoff_dir, jobs={jid: dict(row)})
            summary["failed"] += 1
            summary["errors"][jid] = row.get("last_error", "unknown")
    phase = PHASE_EVALUATED if summary["failed"] == 0 else PHASE_FAILED
    update_state(handoff_dir, phase=phase,
                 note=f"finalizer: {summary['done']} done, "
                      f"{summary['skipped_done']} already done, "
                      f"{summary['failed']} failed")
    summary["phase"] = phase
    atomic_write_json(handoff_dir / FINALIZED_NAME,
                      {**summary, "finished_at": time.time()})
    return summary


def _make_wandb_logger(manifest: dict):
    """Mirror of `_BgEval.drain()`'s W&B publication, resumed post-hoc.
    Returns (log_result, finish) — no-ops when the run had no W&B id."""
    run_id = manifest.get("wandb_run_id")
    if not run_id:
        print("[finalizer] no W&B run id in manifest — results are "
              "executed but not logged")
        return (lambda job, out: None), (lambda: None)
    import wandb
    run = wandb.init(
        entity=manifest.get("wandb_entity"),
        project=manifest.get("wandb_project"),
        id=run_id, resume="allow")

    def log_result(job: dict, out: dict) -> None:
        if out["kind"] == "eval":
            wandb.log(out["payload"])
            print(f"[finalizer] eval @{out['step']:,}: "
                  f"{out.get('brief', '')}")
        else:
            wandb.log({"video/rollout": wandb.Video(
                           out["path"], format="mp4",
                           caption=out.get("caption", "")),
                       "global_step": out["step"]})
            print(f"[finalizer] video @{out['step']:,} logged "
                  f"({out.get('caption', '')})")
            Path(out["path"]).unlink(missing_ok=True)

    return log_result, run.finish


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--handoff-dir", type=Path, required=True)
    ap.add_argument("--max-attempts", type=int, default=2)
    ap.add_argument("--job-timeout-s", type=float, default=1800.0)
    args = ap.parse_args(argv)
    d: Path = args.handoff_dir
    if not _acquire_lock(d):
        return 0
    try:
        manifest = read_json(d / MANIFEST_NAME)
        if manifest is None:
            print(f"[finalizer] no manifest in {d}; nothing to do")
            return 1
        print(f"[finalizer] pid {os.getpid()} run "
              f"{manifest['run_name']}: {len(manifest['jobs'])} job(s), "
              f"CUDA_VISIBLE_DEVICES='{os.environ['CUDA_VISIBLE_DEVICES']}'")
        with (d / ARGS_PICKLE_NAME).open("rb") as fh:
            train_args = pickle.load(fh)
        runner = _WorkerRunner(manifest["task"], train_args,
                               args.job_timeout_s)
        log_result, finish = _make_wandb_logger(manifest)
        try:
            summary = finalize(d, run_job=runner.run,
                               log_result=log_result,
                               max_attempts=args.max_attempts)
        finally:
            runner.shutdown()
            finish()
        print(f"[finalizer] {json.dumps(summary)}")
        return 0 if summary["failed"] == 0 else 2
    finally:
        (d / FINALIZER_PID_NAME).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
