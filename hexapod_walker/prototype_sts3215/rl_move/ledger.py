"""Read-only access to the orchestrator's experiment ledger for sim tools.

The ledger (one JSON object per entry, ``<state>/ledger/NNNNNN-<run>.json``)
is written by the RL orchestrator, which lives in its own repo,
https://github.com/lukas/hexapod-orchestrator (``orchestrator/state_dir.py``
is the writer; ``orchestrator/state_sync.sh pull`` fetches a copy of the
live state). Sim tools here only need to READ a run's entry (its
``extra_args`` / ``--cfg-set`` stack), so this module is the reader and
nothing else: no locking, no writes, no migration.

The state directory is ``$HEXAPOD_STATE_DIR`` when set, else
``<checkout>/.state``. The file name's seq prefix is the entry's identity
and the list order (LAST matching entry wins; run names repeat for
retries), so entries are returned in seq order, never in mtime or name
order.
"""
from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]          # checkout root
SEQ_KEY = "ledger_seq"
_ENTRY_RE = re.compile(r"^(\d{6,})-(.*)\.json$")
SYNC_HINT = ("the ledger is written by the orchestrator "
             "(https://github.com/lukas/hexapod-orchestrator): run its "
             "`orchestrator/state_sync.sh pull` and point HEXAPOD_STATE_DIR "
             "at the resulting state directory")


def state_dir() -> Path:
    env = os.environ.get("HEXAPOD_STATE_DIR")
    return Path(env).expanduser() if env else REPO / ".state"


def _entry_seq(entry) -> int | None:
    v = entry.get(SEQ_KEY) if isinstance(entry, dict) else None
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else None


def load_ledger() -> list[dict]:
    """All ledger entries in seq order; loud when the state is missing."""
    d = state_dir() / "ledger"
    if not d.is_dir():
        raise FileNotFoundError(
            f"orchestrator ledger dir missing: {d} -- {SYNC_HINT}")
    if (d.parent / "experiments.json").exists():
        raise RuntimeError(
            f"{d.parent} still holds the legacy single-file experiments.json "
            f"next to {d.name}/; the orchestrator repo's `state_dir.py "
            f"migrate-ledger` converts it")
    files: dict[int, Path] = {}
    for p in d.iterdir():
        if p.suffix != ".json":
            continue                      # *.json.tmp<pid> mid-write files
        m = _ENTRY_RE.match(p.name)
        if not m:
            raise RuntimeError(
                f"ledger dir {d} holds a file that is not NNNNNN-<run>.json: "
                f"{p.name} -- move it out")
        seq = int(m.group(1))
        if seq in files:
            raise RuntimeError(
                f"ledger dir {d} has two files for seq {seq}: "
                f"{files[seq].name} and {p.name} -- an interrupted save")
        files[seq] = p
    out = []
    for seq in sorted(files):
        e = json.loads(files[seq].read_bytes())
        if _entry_seq(e) != seq:
            raise RuntimeError(
                f"{files[seq]}: {SEQ_KEY}={e.get(SEQ_KEY)!r} inside does not "
                f"match the file name -- the file name is the identity")
        out.append(e)
    return out


def current_entries(entries: Iterable[object]) -> dict[str, dict]:
    """Select each run's latest substantive attempt without hiding failures.

    Only an unexecuted REFUSED row for a distinct attempt can be skipped.
    Later INTENT, FAILED, KILLED, or recovered attempts still replace earlier
    rows regardless of execution evidence. All-refused runs retain their
    latest refusal; an explicit same-attempt status update remains authoritative.
    The input and its full attempt history are never modified.
    """
    latest: dict[str, dict] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("run"):
            continue
        run = entry["run"]
        previous = latest.get(run)
        checks = entry.get("checks") or {}
        launch_evidence = (entry.get("wandb_id")
                           or checks.get("wandb_id")
                           or checks.get("pid")
                           or checks.get("trainer_pid"))
        same_attempt = (previous is not None and entry.get("created")
                        and entry.get("created") == previous.get("created"))
        if (entry.get("status") == "REFUSED" and not launch_evidence
                and previous is not None
                and previous.get("status") != "REFUSED"
                and not same_attempt):
            continue
        latest[run] = entry
    return latest
