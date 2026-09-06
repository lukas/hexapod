"""Durable eval/video artifact handoff for `--defer-final-artifacts`.

Items 2/3/5 of the deferred-artifacts plan (operator feedback
fb_20260906T032210_129bed, follow-through fb_20260906T035950_cd260e):
when a GPU trainer finishes optimization, the eval/video jobs still
outstanding in its background worker are recorded in an IMMUTABLE
per-run job manifest here, the GPU-owning process exits (freeing ~46GB
of CUDA memory), and a CPU-only finalizer
(`rl_move.sim.artifact_finalizer`) completes the jobs and logs them to
the same W&B run afterwards.

Layout (per run, under `rl_move/sim/policies/artifact_handoff/<run>/`):

    manifest.json     immutable once written (a rewrite renames the old
                      one to manifest.<epoch>.json first): run identity,
                      final checkpoint path+md5, W&B ids, resolved argv,
                      and the outstanding job list. Provenance record.
    args.pkl          pickled resolved argparse Namespace — the exact
                      object the training-time eval/video worker used,
                      so the finalizer rebuilds byte-identical envs.
    state.json        MUTABLE, atomically replaced: registry phase
                      (`training` -> `artifacts_pending` -> `evaluated`
                      / `failed`) + per-job status/attempts. This is the
                      "training / artifacts_pending / evaluated" split a
                      verdict must consult — never the training_complete
                      marker alone.
    snapshots/        per-job frozen checkpoint zips (unique immutable
                      names; deleted only after their job is finalized).
    finalized.json    finalizer summary (job counts, wall time, errors).
    finalizer.log     stdout/stderr of the detached CPU finalizer.
    finalizer.lock    single-instance kernel flock on a PERMANENT inode
                      (never unlinked; released by the kernel on any
                      holder death incl. SIGKILL/zombie).
    finalizer.pid     ADVISORY holder pid for humans/ops.sh — not the
                      lock (legacy pre-flock finalizers used it as one;
                      the new acquire still backs off if a live legacy
                      holder is found).

Everything here is DEFAULT-OFF plumbing: nothing imports this module
unless `--defer-final-artifacts` was passed to the trainer.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

POLICY_DIR = Path(__file__).resolve().parent / "policies"
HANDOFF_ROOT = POLICY_DIR / "artifact_handoff"

MANIFEST_NAME = "manifest.json"
STATE_NAME = "state.json"
ARGS_PICKLE_NAME = "args.pkl"
FINALIZED_NAME = "finalized.json"
SNAPSHOT_DIR_NAME = "snapshots"
FINALIZER_LOG_NAME = "finalizer.log"
FINALIZER_PID_NAME = "finalizer.pid"
FINALIZER_LOCK_NAME = "finalizer.lock"

PHASE_TRAINING = "training"
PHASE_ARTIFACTS_PENDING = "artifacts_pending"
PHASE_EVALUATED = "evaluated"
PHASE_FAILED = "failed"

JOB_PENDING = "pending"
JOB_IN_FLIGHT = "in_flight"
JOB_DONE = "done"
JOB_FAILED = "failed"


def handoff_dir_for(run_name: str, root: Path | None = None) -> Path:
    return (root or HANDOFF_ROOT) / run_name


def acquire_finalizer_lock(handoff_dir: Path) -> int | None:
    """Single-writer lock: kernel ``flock`` on a PERMANENT inode.

    Replaces the pid-file steal scheme after the 09-06 canary
    (fb_20260906T044800_a59c3e): (a) unlink+O_EXCL stealing races — two
    contenders can each unlink the other's fresh pidfile and end up
    holding locks on DIFFERENT inodes; (b) a SIGKILLed-but-unreaped
    (zombie) holder wedged the pid liveness check and needed manual
    repair. ``flock`` has neither failure: the kernel releases the lock
    the moment the holder's last fd closes — on ANY death including
    SIGKILL, and for zombies too (the fd table is torn down at
    termination, before reaping). The lock file is NEVER unlinked, so
    every contender always contends on the same inode. ``O_CLOEXEC``
    means exec'ed children (the mp 'spawn' eval worker) never inherit
    the fd, so a surviving worker cannot pin the lock after the
    finalizer dies.

    Returns the open fd on success (caller keeps it open for the life of
    the process; closing it releases the lock) or None if another live
    holder has it. The holder pid written into the file is ADVISORY
    (humans/ops.sh) — correctness comes from the flock alone."""
    handoff_dir.mkdir(parents=True, exist_ok=True)
    fd = os.open(handoff_dir / FINALIZER_LOCK_NAME,
                 os.O_CREAT | os.O_RDWR | os.O_CLOEXEC, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    os.ftruncate(fd, 0)
    os.pwrite(fd, f"{os.getpid()}\n".encode(), 0)
    return fd


def snapshot_dir(handoff_dir: Path) -> Path:
    d = handoff_dir / SNAPSHOT_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def atomic_write_json(path: Path, payload: dict) -> None:
    """tmp-file + rename — same-filesystem `Path.replace` is atomic, so
    a reader (or a killed writer) never sees a half-written file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str))
    tmp.replace(path)


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def read_state(handoff_dir: Path) -> dict | None:
    return read_json(handoff_dir / STATE_NAME)


def update_state(handoff_dir: Path, *, phase: str | None = None,
                 jobs: dict[str, dict] | None = None,
                 note: str | None = None) -> dict:
    """Merge-update state.json atomically (phase and/or per-job rows)."""
    state = read_state(handoff_dir) or {
        "schema": 1, "phase": PHASE_TRAINING, "jobs": {}}
    if phase is not None:
        state["phase"] = phase
    if jobs:
        state.setdefault("jobs", {}).update(jobs)
    if note is not None:
        state["note"] = note
    state["updated_at"] = time.time()
    atomic_write_json(handoff_dir / STATE_NAME, state)
    return state


def init_training_state(run_name: str, root: Path | None = None) -> Path:
    """Arm the handoff dir at trainer start (registry phase=training).

    Reused-directory collision guard (fb_20260906T044800_a59c3e): if the
    dir already holds a manifest or finalizer output from a PRIOR
    training of the same run name, mixing that session's snapshots/state
    with this one corrupts both. The whole stale dir is renamed aside to
    `<run>.superseded.<epoch>` (append-only — nothing deleted) and a
    fresh dir is armed. The launcher forbids duplicate run names, so
    hitting this at all is already an anomaly worth the loud print."""
    d = handoff_dir_for(run_name, root)
    if (d / MANIFEST_NAME).exists() or (d / FINALIZED_NAME).exists():
        stash = d.with_name(f"{d.name}.superseded.{int(time.time())}")
        d.rename(stash)
        print(f"[artifact-handoff] stale handoff dir for {run_name} "
              f"superseded -> {stash.name} (reused-directory collision "
              "guard)")
    d.mkdir(parents=True, exist_ok=True)
    snapshot_dir(d)
    update_state(d, phase=PHASE_TRAINING,
                 note="trainer running with --defer-final-artifacts")
    return d


def _git_provenance() -> dict:
    """Best-effort code/config/XML freeze: the repo commit pins every
    checked-in source (env code, reward code, the generated-model XML
    inputs); ``git_dirty`` flags when the working tree diverged from it.
    Never fails the handoff — errors are recorded, not raised."""
    out: dict = {}
    repo = Path(__file__).resolve().parents[2]
    try:
        out["git_commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
            text=True, timeout=15).stdout.strip() or None
        out["git_dirty"] = bool(subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=repo, capture_output=True, text=True,
            timeout=30).stdout.strip())
    except Exception as ex:  # noqa: BLE001 — provenance must not kill handoff
        out["git_error"] = str(ex)
    return out


def write_manifest(handoff_dir: Path, *, run_name: str, task: str,
                   wandb_run_id: str | None, wandb_entity: str,
                   wandb_project: str, checkpoint_path: Path,
                   checkpoint_md5: str | None, steps: int,
                   jobs: list[dict], args_namespace,
                   resolved_argv: list[str] | None = None,
                   extra_provenance: dict | None = None) -> Path:
    """Write the immutable job manifest + pickled args at handoff time,
    then flip the registry phase to `artifacts_pending`.

    A pre-existing manifest is a hard ERROR (reused-directory collision,
    fb_20260906T044800_a59c3e): `init_training_state` supersedes stale
    dirs at trainer start, so a manifest appearing between then and
    handoff means a concurrent writer — refusing beats silently mixing
    two sessions' jobs. Every job row is frozen with the md5 of its
    snapshot zip (the finalizer verifies before running), and a
    `provenance` block pins the code/config: git commit + dirty flag,
    sha256 of the pickled args, the resolved argv."""
    handoff_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = handoff_dir / MANIFEST_NAME
    if manifest_path.exists():
        raise RuntimeError(
            f"{manifest_path} already exists — refusing to reuse a "
            "handoff directory (two trainings of the same run name, or "
            "a concurrent writer). init_training_state supersedes stale "
            "dirs at trainer start; investigate before overwriting.")
    args_pkl = pickle.dumps(args_namespace)
    (handoff_dir / ARGS_PICKLE_NAME).write_bytes(args_pkl)
    jobs = [dict(j) for j in jobs]
    for j in jobs:
        if not j.get("snapshot_md5"):
            p = Path(j["snapshot_path"])
            j["snapshot_md5"] = (hashlib.md5(p.read_bytes()).hexdigest()
                                 if p.exists() else None)
    provenance = {
        **_git_provenance(),
        "args_pkl_sha256": hashlib.sha256(args_pkl).hexdigest(),
        **(extra_provenance or {}),
    }
    payload = {
        "schema": 2,
        "run_name": run_name,
        "task": task,
        "steps": int(steps),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_md5": checkpoint_md5,
        "wandb_run_id": wandb_run_id,
        "wandb_entity": wandb_entity,
        "wandb_project": wandb_project,
        "resolved_argv": resolved_argv,
        "provenance": provenance,
        "written_at": time.time(),
        "jobs": jobs,
    }
    atomic_write_json(manifest_path, payload)
    update_state(
        handoff_dir, phase=PHASE_ARTIFACTS_PENDING,
        jobs={j["job_id"]: {"status": JOB_PENDING, "attempts": 0}
              for j in jobs},
        note=f"{len(jobs)} eval/video job(s) handed to the CPU finalizer")
    return manifest_path


def spawn_finalizer(handoff_dir: Path) -> int:
    """Launch the CPU-only finalizer as a DETACHED process (survives the
    trainer's exit; `CUDA_VISIBLE_DEVICES=` so it can never take GPU
    memory) and return its pid. Output goes to finalizer.log."""
    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = ""
    env.setdefault("JAX_PLATFORMS", "cpu")
    # The trainer's live W&B session exports service-discovery vars
    # (WANDB_SERVICE / WANDB__SERVICE_TOKEN ...). Inheriting them makes
    # the finalizer attach to the trainer's wandb-core service, which
    # dies with the trainer -> HandleAbandonedError (observed on the
    # 09-06 canary). The finalizer must always start its OWN service.
    for k in [k for k in env if "WANDB" in k and "SERVICE" in k.upper()]:
        env.pop(k)
    log_path = handoff_dir / FINALIZER_LOG_NAME
    with log_path.open("ab") as fh:
        proc = subprocess.Popen(
            [sys.executable, "-m", "rl_move.sim.artifact_finalizer",
             "--handoff-dir", str(handoff_dir)],
            stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            start_new_session=True, env=env,
            cwd=str(Path(__file__).resolve().parents[2]))
    return proc.pid
