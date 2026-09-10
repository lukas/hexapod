"""Text the operator through Messages when the loop needs a hand or stops.

Same mechanism the old blocker monitor used (osascript → Messages.app,
recipient and text passed through private temp files, never argv). The
recipient comes from HEXAPOD_LAB2_ALERT_RECIPIENT; with it unset the alert
is only logged, and nothing here ever raises into the loop.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .store import Store

APPLE_SCRIPT = r'''
on run argv
    set targetAddress to read POSIX file (item 1 of argv) as «class utf8»
    set messageText to read POSIX file (item 2 of argv) as «class utf8»
    tell application "Messages"
        set targetService to first service whose service type = iMessage
        set targetBuddy to buddy targetAddress of targetService
        send messageText to targetBuddy
    end tell
end run
'''

DASHBOARD = "https://robot-lab.cwd1f0-new-cluster.coreweave.app/v2"
RATE_LIMIT = timedelta(minutes=30)


def send_messages_text(recipient: str, message: str) -> None:
    with tempfile.TemporaryDirectory(prefix="hexapod-lab2-alert-") as tmp:
        rp, mp = Path(tmp) / "recipient", Path(tmp) / "message"
        rp.write_text(recipient, encoding="utf-8")
        mp.write_text(message, encoding="utf-8")
        rp.chmod(0o600)
        mp.chmod(0o600)
        result = subprocess.run(["/usr/bin/osascript", "-", str(rp), str(mp)],
                                input=APPLE_SCRIPT, text=True, capture_output=True,
                                timeout=20, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Messages rejected the send").strip()[:300])


def _recently_sent(store: Store, reason: str) -> bool:
    since = datetime.now(timezone.utc) - RATE_LIMIT
    for e in store.events(50):
        if e["kind"] == "text" and e["text"].startswith(f"{reason}:"):
            when = datetime.fromisoformat(e["created_at"])
            return when >= since
    return False


def text(store: Store, reason: str, message: str, *, sender=None,
         recipient: str | None = None) -> bool:
    """One text per reason per 30 minutes. Returns True if a message went out."""
    if _recently_sent(store, reason):
        return False
    recipient = recipient if recipient is not None else os.getenv("HEXAPOD_LAB2_ALERT_RECIPIENT", "").strip()
    body = f"Robot Lab: {message}\n{DASHBOARD}"
    if not recipient:
        store.add_event("text", f"{reason}: (no recipient configured) {message}"[:400])
        return False
    try:
        (sender or send_messages_text)(recipient, body)
    except Exception as exc:  # noqa: BLE001 - alerts never take the loop down
        store.add_event("text", f"{reason}: send failed: {exc}"[:400])
        return False
    store.add_event("text", f"{reason}: {message}"[:400])
    return True
