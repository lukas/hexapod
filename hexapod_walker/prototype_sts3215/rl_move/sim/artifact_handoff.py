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
    finalizer.pid     single-instance lock (stale pids are stolen).

Everything here is DEFAULT-OFF plumbing: nothing imports this module
unless `--defer-final-artifacts` was passed to the trainer.
"""
from __future__ import annotations

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
    """Arm the handoff dir at trainer start (registry phase=training)."""
    d = handoff_dir_for(run_name, root)
    d.mkdir(parents=True, exist_ok=True)
    snapshot_dir(d)
    update_state(d, phase=PHASE_TRAINING,
                 note="trainer running with --defer-final-artifacts")
    return d


def write_manifest(handoff_dir: Path, *, run_name: str, task: str,
                   wandb_run_id: str | None, wandb_entity: str,
                   wandb_project: str, checkpoint_path: Path,
                   checkpoint_md5: str | None, steps: int,
                   jobs: list[dict], args_namespace,
                   resolved_argv: list[str] | None = None) -> Path:
    """Write the immutable job manifest + pickled args at handoff time,
    then flip the registry phase to `artifacts_pending`.

    An existing manifest is never mutated in place: it is renamed to
    `manifest.<epoch>.json` first (this only happens if the same run
    name trains twice, which the launcher forbids anyway)."""
    handoff_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = handoff_dir / MANIFEST_NAME
    if manifest_path.exists():
        manifest_path.rename(
            handoff_dir / f"manifest.{int(time.time())}.json")
    with (handoff_dir / ARGS_PICKLE_NAME).open("wb") as fh:
        pickle.dump(args_namespace, fh)
    payload = {
        "schema": 1,
        "run_name": run_name,
        "task": task,
        "steps": int(steps),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_md5": checkpoint_md5,
        "wandb_run_id": wandb_run_id,
        "wandb_entity": wandb_entity,
        "wandb_project": wandb_project,
        "resolved_argv": resolved_argv,
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
