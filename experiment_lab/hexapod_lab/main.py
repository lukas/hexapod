import base64
from contextlib import asynccontextmanager
from html import escape
import json
import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from .auth import Principal, TokenAuth
from .config import Settings
from .db import Store
from .runner import ExperimentRunner


class ExperimentIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    duration_seconds: float = Field(gt=0)
    parameters: Dict[str, Any] = Field(default_factory=dict)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    auth = TokenAuth(settings.api_keys)
    if not auth.configured:
        raise RuntimeError("HEXAPOD_API_KEYS must configure at least one bearer token")
    store = Store(settings.data_dir / "lab.sqlite3")
    runner = ExperimentRunner(store, settings)
    viewer = auth.dependency("viewer")
    operator = auth.dependency("operator")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.auto_worker:
            runner.start()
        yield
        runner.stop()

    app = FastAPI(title="Hexapod Lab", version="0.1.0", lifespan=lifespan)
    app.state.store, app.state.runner, app.state.auth = store, runner, auth

    def require_experiment(experiment_id: str):
        item = store.get(experiment_id)
        if not item:
            raise HTTPException(404, "Experiment not found")
        return item

    def artifact_path(experiment_id: str, filename: str) -> Path:
        require_experiment(experiment_id)
        if Path(filename).name != filename:
            raise HTTPException(400, "Invalid artifact name")
        path = settings.data_dir / "experiments" / experiment_id / filename
        if not path.is_file():
            raise HTTPException(404, "Artifact not found")
        return path

    def enrich(item):
        run_dir = settings.data_dir / "experiments" / item["id"]
        item = dict(item)
        item["artifacts"] = ([{"name": p.name, "size": p.stat().st_size,
                              "content_type": mimetypes.guess_type(p.name)[0] or "application/octet-stream",
                              "url": f"/api/experiments/{item['id']}/artifacts/{p.name}"}
                             for p in sorted(run_dir.iterdir()) if p.is_file()] if run_dir.exists() else [])
        item["events"] = store.events(item["id"])
        return item

    @app.get("/healthz")
    def health():
        return {"ok": True, "driver": settings.driver}

    @app.get("/api/experiments")
    def list_experiments(_: Principal = Depends(viewer)):
        return [enrich(item) for item in store.list()]

    @app.post("/api/experiments", status_code=202)
    def submit(spec: ExperimentIn, principal: Principal = Depends(operator)):
        if spec.duration_seconds > settings.max_duration_seconds:
            raise HTTPException(422, f"duration_seconds exceeds limit of {settings.max_duration_seconds}")
        item = store.create(spec.model_dump(), principal.name)
        runner.wake()
        return enrich(item)

    @app.get("/api/experiments/{experiment_id}")
    def get_experiment(experiment_id: str, _: Principal = Depends(viewer)):
        return enrich(require_experiment(experiment_id))

    @app.post("/api/experiments/{experiment_id}/cancel")
    def cancel(experiment_id: str, _: Principal = Depends(operator)):
        item = store.cancel(experiment_id)
        if not item:
            raise HTTPException(404, "Experiment not found")
        return enrich(item)

    @app.get("/api/experiments/{experiment_id}/artifacts/{filename}")
    def artifact(experiment_id: str, filename: str, _: Principal = Depends(viewer)):
        path = artifact_path(experiment_id, filename)
        return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0])

    @app.post("/mcp")
    async def mcp(request: Request, principal: Principal = Depends(viewer)):
        message = await request.json()
        rpc_id, method = message.get("id"), message.get("method")
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {"protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "hexapod-lab", "version": "0.1.0"}}}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {}}
        if method == "notifications/initialized":
            return JSONResponse(status_code=202, content={})
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": mcp_tools()}}
        if method == "tools/call":
            params = message.get("params", {})
            try:
                result = call_mcp_tool(params.get("name", ""), params.get("arguments", {}), principal,
                                       store, runner, settings, enrich, artifact_path)
                return {"jsonrpc": "2.0", "id": rpc_id, "result": result}
            except (ValueError, HTTPException) as exc:
                detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
                return {"jsonrpc": "2.0", "id": rpc_id, "result": {"isError": True,
                        "content": [{"type": "text", "text": str(detail)}]}}
        return JSONResponse(status_code=400, content={"jsonrpc": "2.0", "id": rpc_id,
                            "error": {"code": -32601, "message": "Method not found"}})

    @app.get("/", response_class=HTMLResponse)
    def dashboard(_: Principal = Depends(viewer)):
        cards = "".join(experiment_card(item) for item in store.list()) or "<p>No experiments yet.</p>"
        return page("Hexapod Lab", f"<h1>Hexapod Lab</h1><p class='lede'>Experiment queue and durable run evidence</p><main>{cards}</main>")

    @app.get("/experiments/{experiment_id}", response_class=HTMLResponse)
    def result_page(experiment_id: str, _: Principal = Depends(viewer)):
        item = enrich(require_experiment(experiment_id))
        summary_path = settings.data_dir / "experiments" / experiment_id / "summary.md"
        summary = escape(summary_path.read_text()) if summary_path.exists() else "Run summary is not available yet."
        video = next((a for a in item["artifacts"] if a["content_type"].startswith("video/")), None)
        video_html = f"<video controls preload='metadata' src='{escape(video['url'])}'></video>" if video else ""
        artifacts = "".join(f"<li><a href='{escape(a['url'])}'>{escape(a['name'])}</a> ({a['size']} bytes)</li>" for a in item["artifacts"])
        body = f"<a href='/'>← Queue</a><h1>{escape(item['name'])}</h1><span class='status {item['status']}'>{item['status']}</span>{video_html}<h2>Summary</h2><pre>{summary}</pre><h2>Artifacts</h2><ul>{artifacts}</ul>"
        return page(item["name"], body)

    return app


def mcp_tools():
    return [
        {"name": "list_experiments", "description": "List recent robot experiments and their status.",
         "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}}}},
        {"name": "get_experiment", "description": "Get one experiment, events, and artifact links.",
         "inputSchema": {"type": "object", "properties": {"experiment_id": {"type": "string"}}, "required": ["experiment_id"]}},
        {"name": "queue_experiment", "description": "Queue a bounded robot experiment (operator role required).",
         "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"},
          "duration_seconds": {"type": "number", "exclusiveMinimum": 0}, "parameters": {"type": "object"}},
          "required": ["name", "duration_seconds"]}},
        {"name": "cancel_experiment", "description": "Cancel a queued or running experiment (operator role required).",
         "inputSchema": {"type": "object", "properties": {"experiment_id": {"type": "string"}}, "required": ["experiment_id"]}},
        {"name": "read_artifact", "description": "Read a text artifact, or a small binary artifact as base64.",
         "inputSchema": {"type": "object", "properties": {"experiment_id": {"type": "string"}, "filename": {"type": "string"}},
          "required": ["experiment_id", "filename"]}},
    ]


def call_mcp_tool(name, args, principal, store, runner, settings, enrich, artifact_path):
    if name == "list_experiments":
        data = [enrich(i) for i in store.list(min(int(args.get("limit", 25)), 100))]
    elif name == "get_experiment":
        item = store.get(args["experiment_id"])
        if not item:
            raise ValueError("Experiment not found")
        data = enrich(item)
    elif name == "queue_experiment":
        if principal.role == "viewer":
            raise ValueError("Operator role required")
        spec = ExperimentIn(**args)
        if spec.duration_seconds > settings.max_duration_seconds:
            raise ValueError("Experiment duration exceeds configured maximum")
        data = enrich(store.create(spec.model_dump(), principal.name)); runner.wake()
    elif name == "cancel_experiment":
        if principal.role == "viewer":
            raise ValueError("Operator role required")
        data = store.cancel(args["experiment_id"])
        if not data:
            raise ValueError("Experiment not found")
        data = enrich(data)
    elif name == "read_artifact":
        path = artifact_path(args["experiment_id"], args["filename"])
        if path.stat().st_size > 1024 * 1024:
            data = {"name": path.name, "size": path.stat().st_size,
                    "message": "Artifact is larger than 1 MiB; use its authenticated HTTP API URL."}
        elif (mimetypes.guess_type(path.name)[0] or "").startswith(("text/", "application/json")) or path.suffix in {".md", ".jsonl", ".log"}:
            data = {"name": path.name, "encoding": "utf-8", "data": path.read_text(errors="replace")}
        else:
            data = {"name": path.name, "encoding": "base64", "data": base64.b64encode(path.read_bytes()).decode()}
    else:
        raise ValueError("Unknown tool")
    return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}], "structuredContent": data}


def experiment_card(item):
    return f"<article><div><span class='status {item['status']}'>{item['status']}</span><h2><a href='/experiments/{item['id']}'>{escape(item['name'])}</a></h2><p>{escape(item['description'])}</p></div><small>{escape(item['created_at'])} · {item['duration_seconds']}s</small></article>"


def page(title, body):
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>%s</title><style>
    :root{color-scheme:dark;--bg:#0c1110;--panel:#141c19;--ink:#e8f1ec;--muted:#94a69d;--lime:#b7f34a;--line:#2a3932}*{box-sizing:border-box}body{max-width:980px;margin:0 auto;padding:48px 24px;background:var(--bg);color:var(--ink);font:16px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}h1{font-size:clamp(2rem,7vw,4.8rem);letter-spacing:-.06em;line-height:.95;margin:.5em 0}.lede{color:var(--muted);font-size:1.1rem;margin-bottom:3rem}a{color:var(--lime)}article{display:flex;justify-content:space-between;gap:2rem;border-top:1px solid var(--line);padding:1.5rem 0}article h2{margin:.4rem 0;font-size:1.25rem}article p,small{color:var(--muted)}.status{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:.15rem .55rem;font-size:.72rem;text-transform:uppercase}.succeeded{color:var(--lime)}.failed{color:#ff756b}.running{color:#71caff}.queued{color:#ffd56a}video{display:block;width:100%%;margin:2rem 0;border:1px solid var(--line);background:#000}pre{white-space:pre-wrap;background:var(--panel);padding:1.2rem;border:1px solid var(--line);overflow:auto}ul{line-height:2}@media(max-width:650px){article{display:block}small{display:block;margin-top:1rem}}
    </style></head><body>%s</body></html>""" % (escape(title), body)


def run():
    import uvicorn
    settings = Settings.from_env()
    uvicorn.run(create_app(settings), host=settings.bind, port=settings.port)
