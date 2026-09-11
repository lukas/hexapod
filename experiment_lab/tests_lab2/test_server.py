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


def test_runs_take_later_findings_and_files(client, settings):
    c, rid = client
    # A paragraph of later analysis joins the run's findings and the planner's learnings.
    r = c.post(f"/v2/api/runs/{rid}/findings", json={"text": "Sim comparison: hardware stride 1.1 Hz vs 1.4 Hz in MuJoCo."},
               headers=OP)
    assert r.status_code == 201 and r.json()["findings"] == 2
    assert c.post(f"/v2/api/runs/{rid}/findings", json={"text": "x"}, headers=VIEW).status_code in (401, 403)
    assert c.post("/v2/api/runs/nope/findings", json={"text": "x"}, headers=OP).status_code == 404
    doc = c.get(f"/api/runs/{rid}", headers=VIEW).json()
    assert [f["text"][:4] for f in doc["findings"]] == ["[old", "Sim "]
    page = c.get("/", headers=VIEW).text
    assert "Analysis" in page and "MuJoCo" in page
    # Files can be attached to any run, even one that never had a folder; nothing is overwritten.
    up = c.put(f"/v2/api/runs/{rid}/files/stride_plot.png", content=b"\x89PNG", headers=OP)
    assert up.status_code == 201
    assert c.put(f"/v2/api/runs/{rid}/files/stride_plot.png", content=b"other", headers=OP).status_code == 409
    assert c.get(f"/v2/runs/{rid}/stride_plot.png", headers=VIEW).content == b"\x89PNG"
    # Same through MCP, by old id.
    res = rpc(c, "tools/call", {"name": "add_finding", "arguments": {"id": "exp-old-123", "text": "Third note."}}).json()["result"]
    assert json.loads(res["content"][0]["text"])["findings"] == 3
    assert rpc(c, "tools/call", {"name": "add_finding", "arguments": {"id": rid, "text": "no"}}, headers=VIEW).json()["result"]["isError"]


def test_cli_note_and_attach(settings, store, tmp_path, monkeypatch):
    from hexapod_lab2 import cli
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    rid = store.record_historic(robot="hexapod2", title="t", why="w", found="", started_at="2026-09-01T00:00:00",
                                finished_at=None, status="ok", run_dir=None, summary={"old_lab": True, "old_id": "old-9"})
    plot = tmp_path / "plot.png"; plot.write_bytes(b"\x89PNG")
    assert cli.main(["note", "old-9", "[analysis] stride 1.3 Hz"]) == 0
    assert cli.main(["attach", rid, str(plot)]) == 0
    assert cli.main(["attach", rid, str(plot)]) == 3          # never overwrites
    assert cli.main(["note", "nope", "x"]) == 2
    assert store.learnings_for_run(rid)[0]["text"].startswith("[analysis]")
    assert store.run_files(rid) == ["plot.png"]
