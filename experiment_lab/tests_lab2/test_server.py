"""The standalone v2 web server: auth, pages, JSON API and /mcp."""
import json

import pytest
from fastapi.testclient import TestClient

from hexapod_lab2.server import create_app

KEYS = "operator:lukas:op-token,viewer:phone:view-token"
OP = {"Authorization": "Bearer op-token"}
VIEW = {"Authorization": "Bearer view-token"}


@pytest.fixture
def client(settings, store):
    rid = store.record_historic(robot="hexapod1", title="Old lab stand", why="port", found="[old-lab] It stood.",
                                started_at="2026-09-01T10:00:00", finished_at="2026-09-01T10:05:00", status="ok",
                                run_dir=None, summary={"old_lab": True, "old_id": "exp-old-123"},
                                protocol="champion_stand_ground_v1")
    assert store.learnings(limit=1)[0]["created_at"] == "2026-09-01T10:05:00"
    assert store.consecutive_failed_runs() == 0
    app = create_app(settings, api_keys=KEYS, public_base_url="https://lab.example")
    return TestClient(app), rid


def rpc(c, method, params=None, headers=OP, id_=1):
    body = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        body["params"] = params
    return c.post("/mcp", json=body, headers=headers)


def test_no_token_is_401_and_browser_redirects_to_login(client):
    c, _ = client
    assert c.get("/api/state").status_code == 401
    r = c.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")
    assert c.get("/login").status_code == 200


def test_pages_and_api_with_bearer(client):
    c, rid = client
    assert c.get("/", headers=VIEW).status_code == 200
    assert c.get("/v2/", headers=VIEW).status_code == 200
    state = c.get("/api/state", headers=VIEW).json()
    assert state["service"] == "robot-lab-v2" and state["recent_runs"][0]["id"] == rid
    assert c.get(f"/api/runs/exp-old-123", headers=VIEW).json()["id"] == rid
    assert c.get("/healthz").status_code == 200


def test_mcp_handshake_and_tools(client):
    c, rid = client
    init = rpc(c, "initialize").json()["result"]
    assert init["protocolVersion"] == "2025-03-26"
    assert rpc(c, "notifications/initialized").status_code == 202
    assert rpc(c, "ping").json()["result"] == {}
    names = {t["name"] for t in rpc(c, "tools/list").json()["result"]["tools"]}
    assert {"lab_status", "list_runs", "get_run", "list_learnings", "list_experiments", "get_experiment"} <= names
    runs = json.loads(rpc(c, "tools/call", {"name": "list_experiments", "arguments": {}}).json()["result"]["content"][0]["text"])
    assert runs["runs"][0]["found"] == "[old-lab] It stood."
    one = rpc(c, "tools/call", {"name": "get_experiment", "arguments": {"experiment_id": "exp-old-123"}}).json()["result"]
    assert json.loads(one["content"][0]["text"])["id"] == rid
    bad = rpc(c, "tools/call", {"name": "get_run", "arguments": {"id": "nope"}}).json()["result"]
    assert bad["isError"]
    assert rpc(c, "nonsense").status_code == 400


def test_mcp_operator_tools_are_gated(client, settings):
    c, _ = client
    denied = rpc(c, "tools/call", {"name": "import_experiment", "arguments": {"title": "t", "why": "w"}}, headers=VIEW).json()
    assert denied["result"]["isError"]
    ok = rpc(c, "tools/call", {"name": "import_experiment",
                               "arguments": {"title": "Hand run", "why": "w", "found": "f", "robot": "hexapod2"}}).json()
    rid = json.loads(ok["result"]["content"][0]["text"])["run_id"]
    assert c.get(f"/api/runs/{rid}", headers=VIEW).json()["robot"] == "hexapod2"
    queued = rpc(c, "tools/call", {"name": "queue_protocol",
                                   "arguments": {"protocol": "steps_air_v1", "title": "t", "why": "w"}}).json()
    assert json.loads(queued["result"]["content"][0]["text"])["status"] == "queued"
    missing = rpc(c, "tools/call", {"name": "queue_protocol",
                                    "arguments": {"protocol": "nope", "title": "t", "why": "w"}}).json()
    assert missing["result"]["isError"]
