"""Remote MCP URL credentials stay read-only and cannot escape /mcp."""
import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from hexapod_lab2.config import Settings
from hexapod_lab2.server import create_app
from hexapod_lab2.store import Store


@pytest.fixture
def lab(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", checkout=tmp_path / "checkout")
    store = Store(settings.db_path)
    rid = store.record_historic(
        robot="hexapod1", title="A recorded run", why="fixture", found="A finding",
        started_at="2026-09-01T10:00:00", finished_at="2026-09-01T10:01:00",
        status="ok", run_dir=None, summary={}, protocol="fixture")
    secret_file = tmp_path / "sso-secret"
    secret_file.write_text("test-secret")
    app = create_app(settings, sso_secret_file=secret_file, sso_users="operator:operator", api_keys=(
        "viewer:phone:view-token,operator:operator:op-token,"
        "admin:admin:admin-token,automation:automation:auto-token"))
    with TestClient(app) as client:
        yield client, store, rid


def rpc(client, method, params=None, *, url="/mcp?key=view-token", headers=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    return client.post(url, json=body, headers=headers)


def test_url_key_handshake_discovery_and_recorded_experiment(lab):
    client, _, rid = lab
    init = rpc(client, "initialize")
    assert init.status_code == 200
    assert init.json()["result"]["serverInfo"]["name"] == "robot-lab-v2"
    assert init.headers["cache-control"] == "no-store"
    assert init.headers["referrer-policy"] == "no-referrer"
    assert rpc(client, "notifications/initialized").status_code == 202
    assert rpc(client, "ping").json()["result"] == {}
    tools = rpc(client, "tools/list").json()["result"]["tools"]
    assert {t["name"] for t in tools} == {
        "lab_status", "list_runs", "get_run", "list_learnings", "list_plans",
        "list_experiments", "get_experiment"}
    assert all(t["annotations"]["readOnlyHint"] for t in tools)
    result = rpc(client, "tools/call", {"name": "get_experiment", "arguments": {"id": rid}})
    assert json.loads(result.json()["result"]["content"][0]["text"])["found"] == "A finding"


@pytest.mark.parametrize("query,status", [
    ("", 401), ("?key=", 401), ("?key=wrong", 401),
    ("?key=view-token&key=view-token", 401),
    ("?key=view-token&key=op-token", 401),
    ("?key=op-token", 403), ("?key=admin-token", 403), ("?key=auto-token", 403),
])
def test_url_rejects_missing_invalid_ambiguous_and_privileged_keys(lab, query, status):
    client, _, _ = lab
    assert rpc(client, "initialize", url="/mcp" + query).status_code == status


@pytest.mark.parametrize("token", ["op-token", "view-token", "invalid"])
def test_url_does_not_mix_with_header_credentials(lab, token):
    client, _, _ = lab
    assert rpc(client, "initialize", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_url_key_does_not_authenticate_other_routes(lab):
    client, _, rid = lab
    assert client.get("/api/state?key=view-token").status_code == 401
    assert client.get(f"/v2/runs/{rid}/file.txt?key=view-token", follow_redirects=False).status_code == 303
    assert client.get("/?key=view-token", follow_redirects=False).status_code == 303
    assert client.post(f"/v2/api/runs/{rid}/findings?key=view-token", json={"text": "x"}).status_code == 401


@pytest.mark.parametrize("name,args", [
    ("queue_protocol", {"protocol": "fixture", "title": "t", "why": "w"}),
    ("import_experiment", {"title": "t", "why": "w"}),
    ("add_finding", {"text": "must not be saved"}),
])
def test_url_key_cannot_dispatch_mutations(lab, name, args):
    client, store, rid = lab
    before = (store.runs(), store.learnings(), store.plans(["queued", "building", "running"]))
    response = rpc(client, "tools/call", {"name": name, "arguments": {**args, "id": rid}})
    assert response.json()["result"] == {
        "isError": True, "content": [{"type": "text", "text": "operator role required"}]}
    assert (store.runs(), store.learnings(), store.plans(["queued", "building", "running"])) == before


@pytest.mark.parametrize("session", ["password", "sso"])
def test_operator_browser_cookie_cannot_promote_or_block_url_key(lab, session):
    client, _, rid = lab
    if session == "password":
        login = client.post("/login", data={"username": "operator", "password": "op-token"},
                            headers={"Origin": "http://testserver"}, follow_redirects=False)
        assert login.status_code == 303
    else:
        payload = f"operator|{int(time.time()) + 300}".encode()
        body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
        signature = hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()
        client.cookies.set("hexapod_sso", body + "." + signature)
    assert client.get("/api/state").status_code == 200
    assert rpc(client, "initialize").status_code == 200  # No browser Origin required.
    assert rpc(client, "initialize", url="/mcp?key=wrong").status_code == 401
    tools = rpc(client, "tools/list").json()["result"]["tools"]
    assert "add_finding" not in {t["name"] for t in tools}
    result = rpc(client, "tools/call", {"name": "add_finding", "arguments": {"id": rid, "text": "x"}})
    assert result.json()["result"]["isError"] is True


def test_existing_header_clients_keep_their_roles(lab):
    client, _, _ = lab
    for authorization in ("Bearer op-token", "Basic " + base64.b64encode(b"operator:op-token").decode()):
        tools = rpc(client, "tools/list", url="/mcp", headers={"Authorization": authorization}).json()["result"]["tools"]
        assert len(tools) == 10
        assert not next(t for t in tools if t["name"] == "queue_protocol")["annotations"]["readOnlyHint"]
    tools = rpc(client, "tools/list", url="/mcp", headers={"Authorization": "Bearer view-token"}).json()["result"]["tools"]
    assert len(tools) == 7
