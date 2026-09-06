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
  this process, and a kernel flock on a permanent-inode lock file
  (`finalizer.lock` — released by the kernel on ANY holder death,
  SIGKILL/zombie included; no steal races) ensures at most one
  finalizer instance per run. A live LEGACY (pre-flock) holder of the
  advisory finalizer.pid is respected — the new code backs off.
- Publication is confirmed, not assumed (09-06 root review item 1):
  wandb.log is ASYNC, so a job is marked `logged_pending_flush` after
  its log call and flipped to `done` ONLY by the post-run.finish()
  confirmation (`confirm_published`). A crash between log and finish,
  or a finish() that raises, leaves the jobs unconfirmed: the registry
  phase stays `artifacts_pending` (never `evaluated`), finalized.json
  is NOT written, and a restarted finalizer REPLAYS those jobs from
  their retained snapshot inputs. Semantics are therefore
  AT-LEAST-ONCE with job granularity: every replay of an unconfirmed
  job may duplicate its W&B history rows — duplicates are accepted by
  design; never claim exactly-once from W&B row counts, and never
  treat retained files alone as publication.
- Idempotent resume: per-job status/attempts live in state.json
  (atomic replace). A killed finalizer restarted later skips `done`
  (confirmed) jobs and retries `pending`/`in_flight`/`failed`/
  `logged_pending_flush` ones up to --max-attempts (attempts reset for
  logged_pending_flush replays — the job itself already proved
  executable; the failure was publication confirmation).
- Replayable inputs survive crashes: per-job snapshot zips are
  md5-verified against the manifest before running and retired ONLY
  after run.finish() returned AND the jobs were confirmed (a kill at
  any earlier point leaves them on disk for replay).
- Frozen provenance is enforced, not just recorded (09-06 root review
  item 2): before any job executes, the manifest's runtime code
  fingerprint (byte-hashes of the worker's code/config/XML surface)
  and the args.pkl sha256 are re-verified against the live tree
  (`artifact_handoff.verify_runtime_fingerprint`). A mismatch REFUSES
  execution/publication (exit 4) unless the operator passes
  --allow-fingerprint-mismatch. Pre-fingerprint manifests run with an
  explicit 'code identity NOT verified' warning.
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
import hashlib  # noqa: E402
import json  # noqa: E402
import pickle  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

from .artifact_handoff import (  # noqa: E402
    ARGS_PICKLE_NAME, FINALIZED_NAME, FINALIZER_PID_NAME, JOB_DONE,
    JOB_FAILED, JOB_IN_FLIGHT, JOB_LOGGED_PENDING_FLUSH, MANIFEST_NAME,
    PHASE_EVALUATED, PHASE_FAILED, acquire_finalizer_lock,
    atomic_write_json, read_json, read_state, update_state,
    verify_runtime_fingerprint,
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


def _acquire_lock(handoff_dir: Path) -> int | None:
    """One finalizer per run: kernel flock on the permanent-inode lock
    file (`acquire_finalizer_lock` — SIGKILL/zombie-safe, no steal
    races; fb_20260906T044800_a59c3e). Returns the lock fd (held open
    for the life of the process) or None.

    Legacy compatibility: a finalizer running PRE-flock code holds only
    the finalizer.pid file, which the flock cannot see. If a LIVE legacy
    holder is found, back off even though the flock succeeded — never
    deploy an incompatible lock scheme over a live legacy finalizer.
    The pid file itself is now purely advisory (humans/ops.sh)."""
    fd = acquire_finalizer_lock(handoff_dir)
    if fd is None:
        print("[finalizer] another instance holds the flock; exiting")
        return None
    pid_path = handoff_dir / FINALIZER_PID_NAME
    if pid_path.exists():
        try:
            old = int(pid_path.read_text().strip())
        except ValueError:
            old = -1
        if old > 0 and old != os.getpid() and _pid_is_live_finalizer(old):
            print(f"[finalizer] LEGACY finalizer (pid {old}, pre-flock "
                  "code) is live; backing off")
            os.close(fd)
            return None
    pid_path.write_text(str(os.getpid()))
    return fd


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
    without losing progress. After a successful log_result the job is
    marked `logged_pending_flush` — NOT `done`: wandb.log is async, so
    the row is durable only after run.finish() returns. The caller must
    invoke `confirm_published` after a SUCCESSFUL finish to flip logged
    jobs to `done`, set the registry phase and write finalized.json.
    finalize() itself never reports `evaluated`.

    Resume semantics: `done` (confirmed) jobs are skipped;
    `logged_pending_flush` jobs from a crashed/unflushed session are
    REPLAYED from their retained inputs (attempts reset — execution
    already proved out; the failure was publication). Delivery is
    AT-LEAST-ONCE with job granularity: any replay may duplicate that
    job's W&B rows; never claim exactly-once from W&B row counts.

    Replayable inputs are RETAINED here: snapshot zips of logged jobs
    are NOT deleted. They are listed in summary["delivered_snapshots"]
    for the caller to retire AFTER a successful finish + confirmation
    (fb_20260906T044800_a59c3e async-publication risk). Each job's
    snapshot is md5-verified against the manifest before running — a
    corrupt/foreign snapshot fails the job immediately instead of
    publishing wrong-model artifacts."""
    manifest = read_json(handoff_dir / MANIFEST_NAME)
    if manifest is None:
        raise FileNotFoundError(f"no {MANIFEST_NAME} in {handoff_dir}")
    state = read_state(handoff_dir) or {"jobs": {}}
    summary = {"done": 0, "skipped_done": 0, "failed": 0, "errors": {},
               "delivered_snapshots": [], "logged_job_ids": [],
               "replayed_unconfirmed": 0}
    for job in manifest.get("jobs", []):
        jid = job["job_id"]
        row = dict(state.get("jobs", {}).get(
            jid, {"status": "pending", "attempts": 0}))
        if row.get("status") == JOB_DONE:
            summary["skipped_done"] += 1
            continue
        if row.get("status") == JOB_LOGGED_PENDING_FLUSH:
            # Logged in a prior session whose run.finish() never
            # confirmed: the wandb.log may or may not have flushed.
            # Replay from retained inputs (at-least-once — a duplicate
            # W&B row is possible and accepted); reset the attempt
            # budget since execution itself already succeeded once.
            print(f"[finalizer] job {jid} was logged but never "
                  "flush-confirmed — replaying from retained inputs")
            row["attempts"] = 0
            summary["replayed_unconfirmed"] += 1
        snap = Path(job["snapshot_path"])
        want_md5 = job.get("snapshot_md5")
        if want_md5:
            have_md5 = (hashlib.md5(snap.read_bytes()).hexdigest()
                        if snap.exists() else None)
            if have_md5 != want_md5:
                row["status"] = JOB_FAILED
                row["last_error"] = (
                    f"snapshot integrity check failed: manifest md5 "
                    f"{want_md5}, on-disk {have_md5} — not running a "
                    "wrong/corrupt checkpoint")
                update_state(handoff_dir, jobs={jid: dict(row)})
                summary["failed"] += 1
                summary["errors"][jid] = row["last_error"]
                print(f"[finalizer] job {jid}: {row['last_error']}")
                continue
        while int(row.get("attempts", 0)) < max_attempts:
            row["attempts"] = int(row.get("attempts", 0)) + 1
            row["status"] = JOB_IN_FLIGHT
            update_state(handoff_dir, jobs={jid: dict(row)})
            out = run_job(job)
            if out is not None and "error" not in out:
                log_result(job, out)
                # NOT done yet: wandb.log is async. Confirmed to `done`
                # only after run.finish() returns (confirm_published).
                row["status"] = JOB_LOGGED_PENDING_FLUSH
                update_state(handoff_dir, jobs={jid: dict(row)})
                summary["delivered_snapshots"].append(str(snap))
                summary["logged_job_ids"].append(jid)
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
    # Phase/finalized.json deliberately NOT written here: publication is
    # unconfirmed until run.finish() returns. confirm_published() does it.
    update_state(handoff_dir,
                 note=f"finalizer: {summary['done']} logged (awaiting "
                      f"flush confirmation), {summary['skipped_done']} "
                      f"already done, {summary['failed']} failed")
    return summary


def confirm_published(handoff_dir: Path, summary: dict) -> dict:
    """Publication confirmation — call ONLY after run.finish() returned
    (or when the run has no W&B id, i.e. nothing to flush): flips this
    session's logged_pending_flush jobs to `done`, sets the registry
    phase (`evaluated` iff no job failed execution) and writes
    finalized.json. Until this runs, nothing may report `evaluated`."""
    state = read_state(handoff_dir) or {"jobs": {}}
    rows = {}
    for jid in summary.get("logged_job_ids", []):
        row = dict(state.get("jobs", {}).get(jid, {}))
        row["status"] = JOB_DONE
        rows[jid] = row
    phase = PHASE_EVALUATED if summary["failed"] == 0 else PHASE_FAILED
    update_state(handoff_dir, phase=phase, jobs=rows,
                 note=f"finalizer: {summary['done']} done (publication "
                      f"flush confirmed), {summary['skipped_done']} "
                      f"already done, {summary['failed']} failed")
    summary["phase"] = phase
    atomic_write_json(handoff_dir / FINALIZED_NAME,
                      {**summary, "finished_at": time.time()})
    return summary


def run_session(handoff_dir: Path, *, run_job, log_result, finish,
                retire_paths=(), shutdown=lambda: None,
                max_attempts: int = 2) -> int:
    """One finalizer session end-to-end (post-lock, post-fingerprint):
    execute/log outstanding jobs, flush W&B via `finish`, then CONFIRM
    publication and retire replayable inputs. Factored out of main() so
    the crash-between-log-and-finish and finish-raising fault injections
    are directly testable.

    Exit codes: 0 all jobs confirmed; 2 some jobs failed execution
    (still confirmed + finalized); 3 finish() raised — publication
    UNCONFIRMED, nothing retired, phase stays artifacts_pending, logged
    jobs replay on the next start."""
    finish_error = None
    try:
        summary = finalize(handoff_dir, run_job=run_job,
                           log_result=log_result,
                           max_attempts=max_attempts)
    finally:
        shutdown()
        # Always try to flush — even when finalize raised, rows already
        # wandb.log'ed should get their chance to publish. Confirmation
        # below still only happens when BOTH finalize and finish
        # succeeded.
        try:
            finish()
        except Exception as ex:  # noqa: BLE001 — recorded, never masks
            finish_error = ex
    if finish_error is not None:
        msg = (f"run.finish() FAILED: {finish_error!r} — publication "
               "UNCONFIRMED; logged_pending_flush jobs will be replayed "
               "from retained inputs on the next finalizer start")
        print(f"[finalizer] {msg}")
        update_state(handoff_dir, note=f"finalizer: {msg}")
        return 3
    confirm_published(handoff_dir, summary)
    # Only now is publication durable: retire the replayable inputs of
    # confirmed jobs (snapshots + rendered mp4s). A crash before this
    # point leaves them on disk for replay — at-least-once, never lost.
    retired = 0
    for p in list(summary.get("delivered_snapshots", [])) + list(retire_paths):
        Path(p).unlink(missing_ok=True)
        retired += 1
    print(f"[finalizer] retired {retired} replayable input file(s) "
          "after durable W&B finish + confirmation")
    print(f"[finalizer] {json.dumps(summary)}")
    return 0 if summary["failed"] == 0 else 2


def _make_wandb_logger(manifest: dict):
    """Mirror of `_BgEval.drain()`'s W&B publication, resumed post-hoc.
    Returns (log_result, finish, retire_paths) — no-ops when the run had
    no W&B id. Rendered mp4s go on `retire_paths` instead of being
    unlinked at log time: wandb.log is async, so inputs stay replayable
    until run.finish() has durably published (the caller retires them
    together with the delivered snapshots)."""
    run_id = manifest.get("wandb_run_id")
    retire_paths: list[str] = []
    if not run_id:
        print("[finalizer] no W&B run id in manifest — results are "
              "executed but not logged")
        return (lambda job, out: None), (lambda: None), retire_paths
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
            retire_paths.append(out["path"])

    return log_result, run.finish, retire_paths


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--handoff-dir", type=Path, required=True)
    ap.add_argument("--max-attempts", type=int, default=2)
    ap.add_argument("--job-timeout-s", type=float, default=1800.0)
    ap.add_argument("--fingerprint-root", type=Path, default=None,
                    help="repo root for the runtime fingerprint check "
                         "(default: this checkout; tests/ops only)")
    ap.add_argument("--allow-fingerprint-mismatch", action="store_true",
                    help="operator override: run jobs despite a runtime "
                         "code/args fingerprint mismatch (logged loudly; "
                         "results carry unrecorded-code provenance)")
    args = ap.parse_args(argv)
    d: Path = args.handoff_dir
    lock_fd = _acquire_lock(d)
    if lock_fd is None:
        return 0
    try:
        manifest = read_json(d / MANIFEST_NAME)
        if manifest is None:
            print(f"[finalizer] no manifest in {d}; nothing to do")
            return 1
        prov = manifest.get("provenance") or {}
        print(f"[finalizer] pid {os.getpid()} run "
              f"{manifest['run_name']}: {len(manifest['jobs'])} job(s), "
              f"CUDA_VISIBLE_DEVICES='{os.environ['CUDA_VISIBLE_DEVICES']}'"
              f", provenance commit={prov.get('git_commit', '?')[:12]} "
              f"dirty={prov.get('git_dirty', '?')}")
        # Provenance ENFORCEMENT (09-06 root review item 2): this process
        # imports the LIVE worker and unpickles args.pkl — refuse both if
        # the recorded runtime fingerprint no longer matches the tree.
        fp_ok, fp_msg = verify_runtime_fingerprint(
            d, manifest, repo_root=args.fingerprint_root)
        print(f"[finalizer] provenance check: {fp_msg}")
        if not fp_ok:
            if args.allow_fingerprint_mismatch:
                print("[finalizer] --allow-fingerprint-mismatch set: "
                      "PROCEEDING WITH UNRECORDED CODE (operator "
                      "override)")
            else:
                update_state(d, note=f"finalizer REFUSED: {fp_msg}")
                print("[finalizer] refusing to execute/publish jobs "
                      "(rerun with --allow-fingerprint-mismatch to "
                      "override after review)")
                return 4
        with (d / ARGS_PICKLE_NAME).open("rb") as fh:
            train_args = pickle.load(fh)
        runner = _WorkerRunner(manifest["task"], train_args,
                               args.job_timeout_s)
        log_result, finish, retire_paths = _make_wandb_logger(manifest)
        return run_session(
            d, run_job=runner.run, log_result=log_result, finish=finish,
            retire_paths=retire_paths, shutdown=runner.shutdown,
            max_attempts=args.max_attempts)
    finally:
        # The advisory pid file is cleaned up; the LOCK FILE is never
        # unlinked (permanent inode — the kernel releases the flock when
        # this process exits and lock_fd closes).
        (d / FINALIZER_PID_NAME).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
