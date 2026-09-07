"""Run one command under an OS process that owns its independent deadline.

Its supervisor can be killed abruptly. This wrapper deliberately survives that
parent long enough to terminate the guarded child process group at the saved
timeout; a restarted supervisor can also identify it by its persisted marker.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
from typing import Optional
import uuid


_stop_signal: Optional[int] = None
_launch_gate_fd: Optional[int] = None
_launch_child_pid: Optional[int] = None


def _request_stop(signum, _frame) -> None:
    global _launch_gate_fd, _stop_signal
    _stop_signal = signum
    # If termination lands in the narrow interval between spawning the gated
    # helper and authorizing it, close the gate before the helper can exec the
    # actual command. If authorization has already been written, also signal
    # the helper/command directly; the wrapper's finally block still sweeps
    # the complete process group.
    gate_fd = _launch_gate_fd
    _launch_gate_fd = None
    if gate_fd is not None:
        try:
            os.close(gate_fd)
        except OSError:
            pass
    child_pid = _launch_child_pid
    if child_pid is not None:
        try:
            os.kill(child_pid, signal.SIGTERM)
        except OSError:
            pass


def _group_members(pgid: int) -> list[int]:
    """List this wrapper group's processes other than the wrapper itself."""
    try:
        inspected = subprocess.run(
            ["/bin/ps", "-axo", "pid=,pgid="],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        # Failing closed here means the caller proceeds to signal the child
        # leader and then rechecks; it never treats an inspection error as a
        # clean process tree.
        return [-1]
    members = []
    for line in inspected.stdout.splitlines():
        fields = line.split()
        if len(fields) != 2:
            continue
        try:
            pid, process_group = map(int, fields)
        except ValueError:
            continue
        if process_group == pgid and pid != os.getpid():
            members.append(pid)
    return members


def _terminate_group(process: subprocess.Popen, grace_seconds: float = 2.0) -> None:
    """Terminate every other process in the wrapper-owned process group.

    The Lab starts this wrapper in a new session. Its child stays in the same
    process group, so the persisted wrapper PGID remains an externally usable
    kill handle even if the wrapper itself is SIGKILLed.
    """
    pgid = os.getpgrp()
    members = _group_members(pgid)
    if members:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except OSError:
            pass
        deadline = time.monotonic() + max(0.0, grace_seconds)
        while time.monotonic() < deadline:
            members = _group_members(pgid)
            if not members:
                break
            time.sleep(0.05)
    members = _group_members(pgid)
    for pid in members:
        if pid <= 1:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        process.wait(timeout=max(0.1, grace_seconds))
    except subprocess.TimeoutExpired:
        # The independent deadline process must not wait forever on an
        # uncooperative child.  SIGKILL was already sent to the whole group.
        pass


def _write_start_state(path: Path, marker: str, timeout_seconds: float) -> None:
    """Atomically adopt a parent-written launch intent before child start."""
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600)
    try:
        payload = {}
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("marker") != marker:
                raise RuntimeError("guarded process marker does not match launch intent")
        payload.update({
            "schema_version": 1,
            "pid": os.getpid(),
            "pgid": os.getpgrp(),
            "marker": marker,
            "started_unix": time.time(),
            "deadline_seconds": timeout_seconds,
        })
        with os.fdopen(descriptor, "w", encoding="utf-8", closefd=False) as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def main(argv: Optional[list[str]] = None) -> int:
    global _launch_child_pid, _launch_gate_fd, _stop_signal
    _stop_signal = None
    _launch_gate_fd = None
    _launch_child_pid = None
    parser = argparse.ArgumentParser()
    parser.add_argument("--marker", required=True)
    parser.add_argument("--state-path", type=Path)
    parser.add_argument("--timeout-seconds", type=float, required=True)
    parser.add_argument("--max-file-bytes", type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if (
        not command
        or args.timeout_seconds <= 0
        or (args.max_file_bytes is not None and args.max_file_bytes <= 0)
    ):
        parser.error("a command and positive timeout are required")

    # The marker intentionally remains in this wrapper's argv.  A restarted
    # supervisor uses it to distinguish a genuine orphan from PID reuse.
    if args.state_path is not None:
        _write_start_state(args.state_path, args.marker, args.timeout_seconds)
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    if _stop_signal is not None:
        return 128 + _stop_signal
    if args.max_file_bytes is not None:
        # The wrapper and guarded child inherit this per-file kernel limit.
        # It puts a hard ceiling on captured stdout/stderr (and any accidental
        # giant file emitted by a tool-enabled Codex run) even if the parent
        # supervisor is killed or stops polling.
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (args.max_file_bytes, args.max_file_bytes),
        )
    # The child deliberately remains in the wrapper-owned process group. The
    # Lab can therefore recover the complete group using the synchronously
    # persisted launch intent even if this wrapper is SIGKILLed.
    go_read, go_write = os.pipe()
    _launch_gate_fd = go_write
    try:
        child = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "hexapod_lab.guarded_exec",
                "--go-fd",
                str(go_read),
                "--",
                *command,
            ],
            pass_fds=(go_read,),
        )
        _launch_child_pid = child.pid
    finally:
        os.close(go_read)
    try:
        if _stop_signal is None and child.poll() is None:
            try:
                os.write(go_write, b"G")
            except OSError:
                # A signal handler may have closed the gate between the stop
                # check and this write. In that case the guarded helper sees
                # EOF and refuses to exec the command.
                pass
    finally:
        if _launch_gate_fd is not None:
            try:
                os.close(_launch_gate_fd)
            except OSError:
                pass
        _launch_gate_fd = None
    deadline = time.monotonic() + args.timeout_seconds
    try:
        while True:
            if _stop_signal is not None:
                return 128 + _stop_signal
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return 124
            try:
                return child.wait(timeout=min(0.5, remaining))
            except subprocess.TimeoutExpired:
                continue
    finally:
        # This also sweeps descendants if the direct child already exited, and
        # runs for internal wrapper errors as well as normal/timeout returns.
        _terminate_group(child)
        _launch_child_pid = None


if __name__ == "__main__":
    raise SystemExit(main())
