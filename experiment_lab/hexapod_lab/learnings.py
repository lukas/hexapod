"""Plain-language findings, kept separate from the original run evidence."""

from html import escape
import re
from urllib.parse import quote


def pending_learnings(item):
    status = item["status"]
    messages = {
        "waiting_for_operator": "This experiment has not run yet. It is waiting for the guarded runner, so there are no findings yet.",
        "queued": "This experiment is waiting to start. There are no findings yet.",
        "running": "This experiment is still running. It is too early to draw a conclusion.",
        "cancelled": "This experiment was cancelled. Any partial results still need to be reviewed before we can say what we learned.",
        "failed": "The experiment stopped with an error. Its findings and the reason it stopped have not been written up yet.",
        "succeeded": "The experiment finished. Its findings have not been written up in plain language yet.",
    }
    return {
        "text": messages.get(status, "There are no findings available yet."),
        "sources": [],
        "status": "pending" if status in {"queued", "running", "waiting_for_operator"} else "missing",
    }


def learnings_section(item):
    note = item["what_we_learned"]
    paragraphs = "".join(
        f"<p>{escape(paragraph.strip())}</p>"
        for paragraph in re.split(r"\n\s*\n", note["text"])
        if paragraph.strip()
    )
    sources = []
    artifacts = {entry["name"]: entry for entry in item.get("artifacts", [])}
    for index, name in enumerate(note.get("sources", []), 1):
        if name not in artifacts:
            continue
        label = "Run report" if name == "summary.md" else f"Supporting evidence {index}"
        url = f"/api/experiments/{quote(item['id'], safe='')}/artifacts/{quote(name, safe='')}"
        sources.append(f"<a href='{escape(url, quote=True)}'>{label}</a>")
    links = "<p class='learnings-sources'>" + " · ".join(sources) + "</p>" if sources else ""
    return (
        "<section class='learnings' aria-labelledby='learnings-title'>"
        "<h2 id='learnings-title'>What we learned</h2>"
        f"{paragraphs}{links}</section>"
    )
