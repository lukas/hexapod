from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException


RL_BASE_URL = "https://hexapod.cwd1f0-new-cluster.coreweave.app"
RL_DOCUMENTS = {
    "brief": "/llm/brief.md",
    "status": "/llm/status.md",
    "plan": "/llm/plan.md",
    "log": "/llm/log.md",
    "runs": "/llm/runs.md",
    "docs": "/llm/docs.md",
}


def fetch_rl_path(path: str, timeout: float = 15.0) -> str:
    request = Request(
        f"{RL_BASE_URL}{path}",
        headers={"User-Agent": "hexapod-mobile-gateway/1.0"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except HTTPError as exc:
        raise HTTPException(exc.code, "RL orchestrator document unavailable") from exc
    except (URLError, TimeoutError, UnicodeDecodeError) as exc:
        raise HTTPException(502, "RL orchestrator is temporarily unavailable") from exc


def fetch_rl_document(document: str) -> str:
    path = RL_DOCUMENTS.get(document)
    if path is None:
        raise HTTPException(404, "Unknown RL document")
    return fetch_rl_path(path)


def fetch_rl_doc_path(path: str) -> str:
    parts = path.split("/")
    if not parts or any(not part or part in {".", ".."} for part in parts):
        raise HTTPException(400, "Invalid document path")
    encoded = "/".join(quote(part, safe="._-") for part in parts)
    return fetch_rl_path(f"/llm/doc/{encoded}")


def action_openapi(public_base_url: str) -> dict:
    base = public_base_url or "https://robot-lab.cwd1f0-new-cluster.coreweave.app"
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Hexapod Research",
            "version": "1.0.0",
            "description": (
                "Read-only access to the Hexapod RL orchestrator and Robot Lab. "
                "This API cannot move the robot or modify either system."
            ),
        },
        "servers": [{"url": base}],
        "components": {"securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer"}
        }},
        "security": [{"bearerAuth": []}],
        "paths": {
            "/api/mobile/overview": {"get": {
                "operationId": "getHexapodOverview",
                "summary": "Get the current RL brief and recent Robot Lab experiments",
                "responses": {"200": {"description": "Combined overview"}},
            }},
            "/api/mobile/rl/{document}": {"get": {
                "operationId": "getRlDocument",
                "summary": "Read a top-level RL orchestration document",
                "parameters": [{
                    "name": "document", "in": "path", "required": True,
                    "schema": {"type": "string", "enum": list(RL_DOCUMENTS)},
                }],
                "responses": {"200": {"description": "Markdown document"}},
            }},
            "/api/mobile/rl/doc/{path}": {"get": {
                "operationId": "getRlDetailedDocument",
                "summary": "Read a detailed RL document listed by the docs index",
                "parameters": [{
                    "name": "path", "in": "path", "required": True,
                    "schema": {"type": "string"},
                }],
                "responses": {"200": {"description": "Markdown document"}},
            }},
            "/api/mobile/experiments": {"get": {
                "operationId": "listRobotLabExperiments",
                "summary": "List Robot Lab experiments and artifact metadata",
                "responses": {"200": {"description": "Experiment list"}},
            }},
            "/api/mobile/experiments/{experiment_id}": {"get": {
                "operationId": "getRobotLabExperiment",
                "summary": "Get one Robot Lab experiment and its evidence metadata",
                "parameters": [{
                    "name": "experiment_id", "in": "path", "required": True,
                    "schema": {"type": "string"},
                }],
                "responses": {"200": {"description": "Experiment detail"}},
            }},
        },
    }
