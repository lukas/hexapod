"""Bounded, passive diagnostics for macOS privacy-service resource failures."""

from copy import deepcopy
import os
import re
import subprocess
import sys
import threading
import time


class MacOSPrivacyStatus:
    """Probe off the HTTP thread, at most once per minute while access fails."""

    def __init__(self):
        self._lock = threading.Lock()
        self._next_check = 0.0
        self._running = False
        self._status = {"state": "unchecked"}

    def snapshot(self):
        if sys.platform != "darwin":
            return {"state": "unsupported"}
        with self._lock:
            if not self._running and time.monotonic() >= self._next_check:
                self._running = True
                threading.Thread(target=self._refresh, daemon=True).start()
            return deepcopy(self._status)

    def _refresh(self):
        try:
            status = self._probe()
        except (OSError, ValueError, subprocess.SubprocessError):
            # A failed diagnostic is not evidence of a denied grant or a leak.
            status = {"state": "unknown"}
        finally:
            with self._lock:
                self._status = locals().get("status", {"state": "unknown"})
                self._running = False
                self._next_check = time.monotonic() + 60

    @staticmethod
    def _run(arguments):
        return subprocess.run(arguments, capture_output=True, text=True, timeout=2, check=True).stdout

    def _probe(self):
        uid = str(os.getuid())
        pids = self._run(["/usr/bin/pgrep", "-u", uid, "-x", "tccd"]).split()
        if len(pids) != 1 or not pids[0].isdigit():
            return {"state": "unknown"}
        pid = pids[0]
        # Do not collect or publish filenames, process environment, or credentials.
        descriptors = self._run(["/usr/sbin/lsof", "-nP", "-a", "-u", uid, "-p", pid, "-Fpf"])
        count = sum(bool(re.fullmatch(r"f\d+", line)) for line in descriptors.splitlines())
        if count == 0:
            return {"state": "unknown"}
        if count < 240:
            return {"state": "normal", "open_file_count": count}
        predicate = (f'processID == {pid} AND subsystem == "com.apple.TCC" AND '
                     '(eventMessage CONTAINS[c] "too many open files" OR eventMessage CONTAINS "100024")')
        logs = self._run(["/usr/bin/log", "show", "--last", "3m", "--style", "compact",
                          "--predicate", predicate, "--info", "--debug"])
        confirmed = ("too many open files" in logs.lower() or
                     any("SecStaticCodeCreateWithPath" in line and re.search(r"\b100024\b", line)
                         for line in logs.splitlines()))
        return {"state": "exhausted" if confirmed else "unconfirmed", "open_file_count": count}
