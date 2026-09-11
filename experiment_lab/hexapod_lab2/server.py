"""Robot Lab v2's own web server: dashboard, JSON API, artifacts, and /mcp.

Replaces the original Robot Lab process on :8767 (2026-09-11). Same
credentials (HEXAPOD_API_KEYS), same browser sign-in and controller SSO
cookie, same public URL through the same tunnel, and the same /mcp
JSON-RPC shape the outside assistants already call. The dashboard is served
at / and at /v2 (old bookmarks), artifacts at /runs/<id>/<file>.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse

from .auth import Principal, TokenAuth
from .browser_auth import install_browser_auth
from .config import Settings, load_settings
from .store import Store
from .web import ImportIn, build_router, render

MCP_PROTOCOL = "2025-03-26"


def create_app(settings: Optional[Settings] = None, *, api_keys: Optional[str] = None,
               public_base_url: str = "", sso_secret_file: Optional[Path] = None,
               sso_users: str = "", sso_cookie_domain: str = "") -> FastAPI:
    settings = settings or load_settings()
    auth = TokenAuth(api_keys if api_keys is not None else os.getenv("HEXAPOD_API_KEYS", ""))
    if not auth.configured:
        raise RuntimeError("HEXAPOD_API_KEYS must configure at least one bearer token")
    viewer, operator = auth.dependency("viewer"), auth.dependency("operator")
    app = FastAPI(title="Robot Lab v2", version="2.0.0")
    install_browser_auth(app, auth, public_base_url, sso_secret_file=sso_secret_file,
                         sso_users=sso_users, sso_cookie_domain=sso_cookie_domain)

    def store() -> Store:
        return Store(settings.db_path)

    # The /v2 router as before, plus the same pages at the root.
    app.include_router(build_router(viewer, operator, settings=settings))

    @app.get("/", response_class=HTMLResponse)
    def home(robot: Optional[str] = None, _: Principal = Depends(viewer)):
        return render(store(), settings, robot=robot or None)

    @app.get("/runs/{run_id}/{filename}")
    def artifact(run_id: str, filename: str, _: Principal = Depends(viewer)):
        return RedirectResponse(f"/v2/runs/{run_id}/{filename}", status_code=307)

    @app.get("/api/state")
    def api_state(_: Principal = Depends(viewer)):
        return JSONResponse(state_document(settings, store()))

    @app.get("/api/runs")
    def api_runs(limit: int = 50, robot: Optional[str] = None, _: Principal = Depends(viewer)):
        return JSONResponse({"runs": [run_document(store(), r) for r in store().runs(limit=min(limit, 200), robot=robot)]})

    @app.get("/api/runs/{run_id}")
    def api_run(run_id: str, _: Principal = Depends(viewer)):
        doc = get_run(store(), run_id)
        if not doc:
            raise HTTPException(404, "unknown run")
        return JSONResponse(doc)

    @app.get("/api/learnings")
    def api_learnings(limit: int = 30, _: Principal = Depends(viewer)):
        return JSONResponse({"learnings": store().learnings(limit=min(limit, 200))})

    @app.get("/api/plans")
    def api_plans(_: Principal = Depends(viewer)):
        return JSONResponse({"plans": store().plans(["queued", "building", "running"])})

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        return {"ok": True, "service": "robot-lab-v2"}

    @app.get("/robots.txt", include_in_schema=False)
    def robots():
        return PlainTextResponse("User-agent: *\nDisallow: /\n")

    @app.post("/mcp")
    async def mcp(request: Request, principal: Principal = Depends(viewer)):
        try:
            message = await request.json()
        except (UnicodeDecodeError, ValueError):
            return JSONResponse(status_code=400, content={"jsonrpc": "2.0", "id": None,
                                                          "error": {"code": -32700, "message": "Parse error"}})
        if not isinstance(message, Mapping):
            return JSONResponse(status_code=400, content={"jsonrpc": "2.0", "id": None,
                                                          "error": {"code": -32600, "message": "Invalid Request"}})
        rpc_id, method = message.get("id"), message.get("method")
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {
                "protocolVersion": MCP_PROTOCOL, "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "robot-lab-v2", "version": "2.0.0"}}}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {}}
        if method == "notifications/initialized":
            return JSONResponse(status_code=202, content={})
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": mcp_tools()}}
        if method == "tools/call":
            params = message.get("params", {})
            try:
                if not isinstance(params, Mapping):
                    raise ValueError("Tool params must be an object")
                result = call_tool(settings, store(), principal, str(params.get("name", "")),
                                   params.get("arguments") or {})
                return {"jsonrpc": "2.0", "id": rpc_id, "result": result}
            except (ValueError, KeyError, HTTPException) as exc:
                detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
                return {"jsonrpc": "2.0", "id": rpc_id,
                        "result": {"isError": True, "content": [{"type": "text", "text": str(detail)}]}}
        return JSONResponse(status_code=400, content={"jsonrpc": "2.0", "id": rpc_id,
                                                      "error": {"code": -32601, "message": "Method not found"}})

    app.state.store_factory = store
    return app


# ---------------------------------------------------------------- documents

def run_document(store: Store, r: Dict[str, Any]) -> Dict[str, Any]:
    try:
        summary = json.loads(r.get("summary_json") or "{}")
    except ValueError:
        summary = {}
    return {
        "id": r["id"], "robot": r.get("robot"), "title": r.get("title"), "why": r.get("why"),
        "protocol": r.get("protocol"), "status": r["status"], "exit_code": r.get("exit_code"),
        "started_at": r["started_at"], "finished_at": r.get("finished_at"),
        "found": store.learning_for_run(r["id"]),
        "findings": store.learnings_for_run(r["id"]),
        "seen": summary.get("seen"),
        "recovery": bool(summary.get("recovery")), "old_lab": bool(summary.get("old_lab")),
        "old_id": summary.get("old_id"),
        "files": [f"/v2/runs/{r['id']}/{f}" for f in store.run_files(r["id"])],
    }


def get_run(store: Store, run_id: str) -> Optional[Dict[str, Any]]:
    joined = store.run_joined(run_id)
    if joined is None:
        return None
    doc = run_document(store, joined)
    doc["log_tail"] = joined.get("log_tail")
    try:
        doc["summary"] = json.loads(joined.get("summary_json") or "{}")
    except ValueError:
        doc["summary"] = {}
    return doc


def state_document(settings: Settings, store: Store) -> Dict[str, Any]:
    paused = settings.pause_file.exists()
    why = ""
    if paused:
        try:
            why = settings.pause_file.read_text().strip()
        except OSError:
            pass
    return {
        "service": "robot-lab-v2",
        "paused": paused, "pause_reason": why,
        "robot_held_by_engineer": settings.robot_held.exists(),
        "spend_24h_usd": round(store.spend_last_24h(), 2), "cap_usd": settings.current_cap(),
        "last_stop": store.last_stop(),
        "running": [p for p in store.plans(["running"])],
        "queue": store.plans(["queued", "building"]),
        "recent_runs": [run_document(store, r) for r in store.runs(limit=10)],
        "learnings": store.learnings(limit=10),
        "events": store.events(15),
        "robots": store.robots(),
    }


# ---------------------------------------------------------------- MCP tools

def mcp_tools() -> list:
    obj = {"type": "object", "properties": {}}
    return [
        {"name": "lab_status", "description": "Robot Lab v2 status: paused/running, spend vs cap, queue, recent runs, latest findings, events.", "inputSchema": obj},
        {"name": "list_runs", "description": "Recent runs (experiments) with their finding ('found'), what the camera saw ('seen'), and artifact URLs. Optional robot filter (hexapod1, hexapod2).",
         "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}, "robot": {"type": "string"}}}},
        {"name": "get_run", "description": "One run in full: finding, camera description, runner log tail, summary, files. Accepts a v2 run id or an old Robot Lab experiment id.",
         "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
        {"name": "list_learnings", "description": "What the lab has learned, newest first, with the run each paragraph came from.",
         "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
        {"name": "list_plans", "description": "Queued, building (code jobs) and running plans.", "inputSchema": obj},
        {"name": "queue_protocol", "description": "Queue an existing sysid protocol for hexapod 1 with a title and why (operator role).",
         "inputSchema": {"type": "object", "properties": {"protocol": {"type": "string"}, "title": {"type": "string"}, "why": {"type": "string"}}, "required": ["protocol", "title", "why"]}},
        {"name": "add_finding", "description": "File further analysis against an existing run (operator role): a paragraph that joins the run's findings and the learnings the planner reads. Accepts a v2 run id or an old lab experiment id. Files can be added with PUT /v2/api/runs/<id>/files/<name>.",
         "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "text": {"type": "string"}}, "required": ["id", "text"]}},
        {"name": "import_experiment", "description": "Record a hand-run experiment on any robot (operator role): title, why, found, robot, status. status is optional: explored (default) for a run done to learn with no pass/fail, ok if the robot did what was asked and met the criterion, failed if it did not run as asked. Files can be added with PUT /v2/api/runs/<id>/files/<name>.",
         "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}, "why": {"type": "string"}, "found": {"type": "string"}, "robot": {"type": "string"}, "status": {"type": "string", "enum": ["explored", "ok", "failed"]}}, "required": ["title", "why"]}},
        # Names the outside assistants learned from the original lab.
        {"name": "list_experiments", "description": "Alias of list_runs.", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}, "robot": {"type": "string"}}}},
        {"name": "get_experiment", "description": "Alias of get_run; accepts old Robot Lab experiment ids.",
         "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "experiment_id": {"type": "string"}}}},
    ]


def _text(payload: Any) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=1, default=str)}]}


def call_tool(settings: Settings, store: Store, principal: Principal, name: str, args: Mapping[str, Any]) -> Dict[str, Any]:
    if name == "lab_status":
        return _text(state_document(settings, store))
    if name in ("list_runs", "list_experiments"):
        limit = min(int(args.get("limit") or 30), 200)
        return _text({"runs": [run_document(store, r) for r in store.runs(limit=limit, robot=args.get("robot") or None)]})
    if name in ("get_run", "get_experiment"):
        rid = str(args.get("id") or args.get("experiment_id") or "")
        doc = get_run(store, rid)
        if not doc:
            raise ValueError(f"unknown run {rid}")
        return _text(doc)
    if name == "list_learnings":
        return _text({"learnings": store.learnings(limit=min(int(args.get("limit") or 30), 200))})
    if name == "list_plans":
        return _text({"plans": store.plans(["queued", "building", "running"])})
    if name in ("queue_protocol", "import_experiment", "add_finding") and principal.role not in ("operator", "admin"):
        raise HTTPException(403, "operator role required")
    if name == "add_finding":
        joined = store.run_joined(str(args.get("id") or ""))
        if not joined:
            raise ValueError(f"unknown run {args.get('id')}")
        text = str(args.get("text") or "").strip()
        if not text:
            raise ValueError("text is required")
        lid = store.add_learning(text[:6000], run_id=joined["id"])
        return _text({"run_id": joined["id"], "learning_id": lid, "findings": len(store.learnings_for_run(joined["id"]))})
    if name == "queue_protocol":
        from .runner import protocol_exists
        protocol = str(args.get("protocol") or "").removesuffix(".json")
        if not protocol_exists(settings, protocol):
            raise ValueError(f"no such protocol on disk: {protocol}")
        pid = store.add_plan(title=str(args["title"])[:120], why=str(args["why"])[:600], kind="existing",
                             protocol=protocol, build_spec=None, source=f"mcp:{principal.name}")
        return _text({"plan_id": pid, "status": "queued"})
    if name == "import_experiment":
        spec = ImportIn(**{k: v for k, v in args.items() if k in ImportIn.model_fields})
        rid = store.import_run(robot=spec.robot, title=spec.title, why=spec.why, found=spec.found,
                               source_dir=None, runs_dir=settings.runs_dir, status=spec.status)
        return _text({"run_id": rid, "files_url": f"/v2/api/runs/{rid}/files/"})
    raise ValueError(f"unknown tool {name}")


# ---------------------------------------------------------------- entry point

def run() -> None:
    import uvicorn
    settings = load_settings()
    secret = os.getenv("HEXAPOD_SSO_SECRET_FILE", "").strip()
    app = create_app(
        settings,
        public_base_url=os.getenv("HEXAPOD_PUBLIC_BASE_URL", ""),
        sso_secret_file=Path(secret) if secret else None,
        sso_users=os.getenv("HEXAPOD_SSO_USERS", ""),
        sso_cookie_domain=os.getenv("HEXAPOD_SSO_COOKIE_DOMAIN", ""),
    )
    uvicorn.run(app, host=os.getenv("HEXAPOD_BIND", "127.0.0.1"), port=int(os.getenv("HEXAPOD_PORT", "8767")),
                log_level="warning")
