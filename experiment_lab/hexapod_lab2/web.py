"""Read-only dashboard for v2, mounted into the existing Robot Lab site at /v2."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from .config import Settings, load_settings
from .store import Store


def local_stamp(value, *, relative: bool = True) -> str:
    """Stored UTC -> the operator's clock, with a relative age."""
    if not value:
        return "—"
    try:
        when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return str(value)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    local = when.astimezone()
    now = datetime.now(timezone.utc)
    clock = local.strftime("%-I:%M %p")
    if local.date() != now.astimezone().date():
        clock = f"{local.strftime('%b %-d')}, {clock}"
    if not relative:
        return clock
    s = (now - when).total_seconds()
    if s < 90:
        age = "just now"
    elif s < 3600:
        age = f"{int(s // 60)} min ago"
    elif s < 86400:
        age = f"{s / 3600:.1f} h ago"
    else:
        age = f"{s / 86400:.1f} d ago"
    return f"{clock} ({age})"


def first_sentences(text, limit: int) -> str:
    flat = " ".join(str(text or "").split())
    if len(flat) <= limit:
        return flat
    kept, used = [], 0
    for piece in re.split(r"(?<=[.!?])\s+", flat):
        if kept and used + len(piece) + 1 > limit:
            break
        kept.append(piece)
        used += len(piece) + 1
    out = " ".join(kept) if kept else flat[:limit].rsplit(" ", 1)[0]
    return out.rstrip() + " …"


CSS = """
body{font:15px/1.4 -apple-system,system-ui,sans-serif;margin:0;background:#f5f5f4;color:#1c1917}
main{max-width:900px;margin:0 auto;padding:12px 16px}
.bar{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;margin:0 0 10px}
.bar h1{font-size:1.2rem;margin:0}.bar a{color:#2563eb}
.stop{background:#fee2e2;border:1px solid #fca5a5;padding:8px 12px;border-radius:6px;margin:8px 0}
.pause{background:#fef3c7;border:1px solid #fcd34d;padding:8px 12px;border-radius:6px;margin:8px 0}
article{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:10px 14px;margin:8px 0}
article h2{font-size:1rem;margin:0 0 4px}
.tag{display:inline-block;font-size:.75rem;padding:1px 7px;border-radius:10px;background:#e7e5e4;margin-right:6px;text-transform:uppercase}
.tag.ok,.tag.done{background:#dcfce7}.tag.failed,.tag.timeout{background:#fee2e2}.tag.running{background:#dbeafe}
.tag.queued{background:#fef9c3}.tag.robot{background:#cffafe}.tag.recovery{background:#fde68a}.tag.building{background:#ede9fe}.tag.unreachable{background:#fde68a}
.point b{color:#57534e;margin-right:6px}p{margin:4px 0}small{color:#78716c}
h3{font-size:.95rem;margin:18px 0 4px;color:#57534e;text-transform:uppercase;letter-spacing:.04em}
details summary{cursor:pointer;color:#57534e}pre{white-space:pre-wrap;font-size:12px;background:#fafaf9;padding:8px;border-radius:6px}
"""


def render(store: Store, settings: Settings, robot: Optional[str] = None) -> str:
    stop = store.last_stop()
    started = next((e for e in store.events(50) if e["kind"] == "note" and e["text"] == "loop started"), None)
    loop_stopped = stop and (not started or stop["created_at"] > started["created_at"])
    paused = settings.pause_file.exists()
    spent = store.spend_last_24h()
    out = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>Robot Lab v2</title><style>{CSS}</style><main>"
           f"<div class=bar><h1>Robot Lab v2</h1><span>{escape(local_stamp(datetime.now(timezone.utc).isoformat(), relative=False))}</span>"
           f"<span>${spent:.2f} last 24 h of ${settings.current_cap():.0f}</span>"
           + "".join(f"<a href='/v2/?robot={escape(r)}'>{'<b>' if r == robot else ''}{escape(r)}{'</b>' if r == robot else ''}</a>" for r in store.robots())
           + (f"<a href='/v2/'>all robots</a>" if robot else "")
           + f"<a href='/'>old lab</a><a href='/v2/api/state'>json</a></div>"]
    if paused:
        try:
            why = settings.pause_file.read_text().strip()
        except OSError:
            why = ""
        out.append(f"<div class=pause>Paused{': ' + escape(why) if why else ''}. Run <code>hexapod-lab2 resume</code> to continue.</div>")
    if loop_stopped and not paused:
        out.append(f"<div class=stop>Loop stopped {escape(local_stamp(stop['created_at']))}: {escape(stop['text'])}.</div>")
    running = [p for p in store.plans(["running"]) if not robot or p["robot"] == robot]
    queue = [p for p in store.plans(["queued", "building"]) if not robot or p["robot"] == robot]
    out.append("<h3>Now</h3>")
    if running:
        p = running[0]
        out.append(f"<article><span class='tag running'>running</span><h2>{escape(p['title'])}</h2>"
                   f"<p class=point><b>Why</b>{escape(first_sentences(p['why'], 300))}</p>"
                   f"<small>{escape(p['protocol'] or '')} · since {escape(local_stamp(p['updated_at']))}</small></article>")
    else:
        out.append("<article><p>Nothing running.</p></article>")
    out.append(f"<h3>Queue · {len(queue)}</h3>")
    for p in reversed(queue):
        note = f" · {escape(p['status_note'])}" if p.get("status_note") else ""
        kind_label = p['protocol'] or ('needs fix (engineer)' if p.get('kind') == 'needs_fix' else 'needs code')
        out.append(f"<article><span class='tag {p['status']}'>{p['status']}</span><h2>{escape(p['title'])}</h2>"
                   f"<p class=point><b>Why</b>{escape(first_sentences(p['why'], 300))}</p>"
                   f"<small>{escape(kind_label)}{note} · {escape(local_stamp(p['created_at']))}</small></article>")
    if not queue:
        out.append("<article><p>Empty. The loop will ask the planner next.</p></article>")
    out.append("<h3>Runs</h3>")
    for r in store.runs(limit=20, robot=robot):
        found = store.learning_for_run(r["id"])
        point = (f"<p class=point><b>Found</b>{escape(first_sentences(found, 320))}</p>" if found
                 else f"<p class=point><b>Why</b>{escape(first_sentences(r['why'], 240))}</p>")
        tail = escape((r.get("log_tail") or "")[-1200:])
        robot_tag = f"<span class='tag robot'>{escape(r['robot'])}</span>" if r.get("robot") != "hexapod1" else ""
        try:
            summary = json.loads(r.get("summary_json") or "{}")
        except ValueError:
            summary = {}
        if summary.get("recovery"):
            robot_tag += "<span class='tag recovery'>recovery</span>"
        seen_html = (f"<p class=point><b>Seen</b>{escape(first_sentences(summary['seen'], 320))}</p>"
                     if summary.get("seen") and not str(summary["seen"]).startswith("(") else "")
        video_link = (f" · <a href='/v2/runs/{r['id']}/wide.mp4'>video</a>" if summary.get("video") else "")
        files = store.run_files(r["id"])
        links = (" · " + " ".join(
            f"<a href='/v2/runs/{r['id']}/{escape(f)}'>{escape(f)}</a>" for f in files if not f.startswith("runner.log"))
            ) if files and not r.get("protocol") else ""
        detail = (f"<details><summary>runner log</summary><pre>{tail}</pre></details>" if tail else "")
        out.append(f"<article>{robot_tag}<span class='tag {r['status']}'>{r['status']}</span><h2>{escape(r['title'])}</h2>{point}{seen_html}"
                   f"<small>{escape(r['protocol'] or ('unplanned' if summary.get('recovery') else 'hand-run'))} · {escape(local_stamp(r['started_at']))}"
                   f"{' · exit ' + str(r['exit_code']) if r.get('exit_code') is not None else ''}{video_link}{links}</small>"
                   f"{detail}</article>")
    events = store.events(12)
    if events:
        out.append("<h3>Events</h3><article>" + "".join(
            f"<p><small>{escape(local_stamp(e['created_at']))}</small> <b>{escape(e['kind'])}</b> {escape(e['text'])}</p>"
            for e in events) + "</article>")
    out.append("</main>")
    return "".join(out)


class ImportIn(BaseModel):
    """A hand-run experiment sent from another device. Files follow as PUTs."""
    title: str = Field(min_length=1, max_length=200)
    why: str = Field(min_length=1, max_length=2000)
    found: str = Field(default="", max_length=4000)
    robot: str = Field(default="hexapod2", pattern=r"^[a-z0-9_-]{1,32}$")
    status: str = Field(default="ok", pattern=r"^(ok|failed)$")


def build_router(viewer_dependency: Callable, operator_dependency: Optional[Callable] = None,
                 settings: Optional[Settings] = None) -> APIRouter:
    settings = settings or load_settings()
    operator_dependency = operator_dependency or viewer_dependency
    router = APIRouter(prefix="/v2")

    def store() -> Store:
        return Store(settings.db_path)

    @router.post("/api/import", status_code=201)
    def import_experiment(spec: ImportIn, _=Depends(operator_dependency)):
        s = store()
        rid = s.import_run(robot=spec.robot, title=spec.title, why=spec.why, found=spec.found,
                           source_dir=None, runs_dir=settings.runs_dir, status=spec.status)
        return {"run_id": rid, "files_url": f"/v2/api/runs/{rid}/files/", "page": f"/v2/?robot={spec.robot}"}

    @router.put("/api/runs/{run_id}/files/{filename}", status_code=201)
    async def upload_file(run_id: str, filename: str, request: Request, _=Depends(operator_dependency)):
        s = store()
        run = s.run(run_id)
        if not run or not json.loads(run.get("summary_json") or "{}").get("imported"):
            raise HTTPException(404, "not an imported run")
        # Body streams to disk in chunks; a phone video should not sit in RAM.
        root = Path(run["run_dir"])
        name = Path(filename).name
        if not name or name.startswith(".") or name == "runner.log":
            raise HTTPException(400, "bad filename")
        root.mkdir(parents=True, exist_ok=True)
        size = 0
        with (root / name).open("wb") as out:
            async for chunk in request.stream():
                out.write(chunk)
                size += len(chunk)
        return {"run_id": run_id, "file": name, "bytes": size, "url": f"/v2/runs/{run_id}/{name}"}

    @router.get("", response_class=HTMLResponse, include_in_schema=False)
    @router.get("/", response_class=HTMLResponse)
    def dashboard(robot: Optional[str] = None, _=Depends(viewer_dependency)):
        return render(store(), settings, robot=robot or None)

    @router.get("/api/state")
    def state(_=Depends(viewer_dependency)):
        s = store()
        return JSONResponse({
            "paused": settings.pause_file.exists(),
            "last_stop": s.last_stop(),
            "spend_24h_usd": s.spend_last_24h(),
            "plans": s.plans(limit=30),
            "runs": s.runs(limit=20),
            "learnings": s.learnings(limit=10),
            "events": s.events(20),
        })

    @router.get("/runs/{run_id}/{filename}")
    def artifact(run_id: str, filename: str, _=Depends(viewer_dependency)):
        s = store()
        run = s.run(run_id)
        if not run or not run.get("run_dir"):
            raise HTTPException(404)
        root = Path(run["run_dir"]).resolve()
        target = (root / filename).resolve()
        if root not in target.parents or not target.is_file():
            raise HTTPException(404)
        from fastapi.responses import FileResponse
        return FileResponse(str(target), filename=None)

    return router
