"""Operator commands by iMessage reply: resume, pause, raise cap, status.

Messages.app keeps its history in ~/Library/Messages/chat.db. Reading it
needs Full Disk Access for the loop's python binary; without that the inbox
is simply unavailable and the loop says so once. Only messages from the
alert recipient, received after the loop started, are considered.
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from . import alerts
from .config import Settings
from .store import Store

CHAT_DB = Path.home() / "Library" / "Messages" / "chat.db"
APPLE_EPOCH_OFFSET = 978307200  # seconds between 1970 and 2001
HELP = "reply: resume | pause | raise cap [dollars] | status"


@dataclass
class Inbox:
    recipient: str
    db_path: Path = CHAT_DB
    started_unix: float = field(default_factory=time.time)
    last_rowid: int = 0
    unavailable: Optional[str] = None

    def _digits(self) -> str:
        return re.sub(r"\D", "", self.recipient)

    def poll(self) -> List[str]:
        """New inbound texts from the recipient since the last poll."""
        if not self.recipient or self.unavailable:
            return []
        try:
            con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=2)
            try:
                rows = con.execute(
                    "SELECT m.ROWID, m.text, h.id FROM message m JOIN handle h ON h.ROWID = m.handle_id"
                    " WHERE m.is_from_me = 0 AND m.ROWID > ? AND m.text IS NOT NULL"
                    " AND (m.date / 1000000000 + ?) > ? ORDER BY m.ROWID",
                    (self.last_rowid, APPLE_EPOCH_OFFSET, self.started_unix)).fetchall()
            finally:
                con.close()
        except sqlite3.Error as exc:
            self.unavailable = f"{exc}"
            return []
        out = []
        digits = self._digits()
        for rowid, text, handle in rows:
            self.last_rowid = max(self.last_rowid, int(rowid))
            hid = str(handle or "")
            body = str(text or "").strip()
            # When the recipient is the operator's own number, everything the
            # Mac sends (this loop's texts, the old monitor's alerts) comes
            # back as an inbound copy. Never treat our own voice as a command.
            if body.startswith(("Robot Lab", "Hexapod", "alert")) or "cwd1f0-new-cluster" in body:
                continue
            if hid.lower() == self.recipient.lower() or (digits and re.sub(r"\D", "", hid).endswith(digits[-10:])):
                out.append(body)
        return out


def parse(text: str, current_cap: float) -> Tuple[str, Optional[float]]:
    t = " ".join(text.lower().split())
    m = re.search(r"(?:raise|set|bump)?\s*cap(?:\s*(?:to|=))?\s*\$?(\d+(?:\.\d+)?)", t)
    if m:
        return "cap", float(m.group(1))
    if re.search(r"\braise (the )?cap\b|\bmore budget\b|\bkeep going\b", t):
        return "cap", float(int(current_cap * 1.5 + 9) // 10 * 10)
    if re.search(r"\b(resume|continue|go|unpause|restart)\b", t):
        return "resume", None
    if re.search(r"\b(pause|stop|halt|hold)\b", t):
        return "pause", None
    if re.search(r"\b(status|what.?s (going on|happening)|report)\b", t):
        return "status", None
    return "unknown", None


def status_line(settings: Settings, store: Store) -> str:
    runs = store.runs(limit=1)
    last = f"last run {runs[0]['protocol'] or runs[0]['title'][:40]}: {runs[0]['status']}" if runs else "no runs"
    paused = settings.pause_file.exists()
    why = ""
    if paused:
        try:
            why = settings.pause_file.read_text().strip()
        except OSError:
            pass
    return (f"{'PAUSED' if paused else 'running'}{' (' + why + ')' if why else ''}; "
            f"${store.spend_last_24h():.2f} of ${settings.current_cap():.0f} cap; "
            f"{store.queued_count()} queued; {last}.")


def apply(settings: Settings, store: Store, text: str, *, reply: Callable[[str], None],
          on_resume: Callable[[], None] = lambda: None) -> str:
    action, value = parse(text, settings.current_cap())
    if action == "cap":
        settings.set_cap(value)
        if settings.pause_file.exists() and "cap" in settings.pause_file.read_text():
            settings.pause_file.unlink(missing_ok=True)
            on_resume()
            reply(f"cap is now ${value:.0f}; resuming.")
        else:
            reply(f"cap is now ${value:.0f}.")
    elif action == "resume":
        settings.pause_file.unlink(missing_ok=True)
        on_resume()
        reply("resuming. " + status_line(settings, store))
    elif action == "pause":
        settings.pause_file.write_text("paused by text\n")
        reply("paused.")
    elif action == "status":
        reply(status_line(settings, store))
    else:
        reply(f"didn't understand '{text[:60]}'. {HELP}")
    store.add_event("command", f"{action}: {text[:120]}")
    return action


def poll_and_apply(settings: Settings, store: Store, inbox: Inbox, *, on_resume=lambda: None,
                   send=None, log=print) -> int:
    """Read new texts, act on them, reply. Returns the number handled."""
    texts = inbox.poll()
    if inbox.unavailable and not getattr(inbox, "_reported", False):
        inbox._reported = True
        store.add_event("note", f"text commands unavailable: cannot read Messages history ({inbox.unavailable}). "
                                "Grant Full Disk Access to the loop's python to enable replies.")
        log("text commands unavailable (no Messages access)")
    send = send or alerts.send_messages_text

    def reply(msg: str) -> None:
        try:
            send(inbox.recipient, f"Robot Lab: {msg}")
        except Exception as exc:  # noqa: BLE001
            store.add_event("text", f"reply failed: {exc}"[:300])

    for text in texts:
        log(f"text command: {text[:80]}")
        apply(settings, store, text, reply=reply, on_resume=on_resume)
    return len(texts)
