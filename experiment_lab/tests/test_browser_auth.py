"""Regression coverage for browser login and retained API authentication."""

import pytest
from fastapi.testclient import TestClient

from hexapod_lab import browser_auth
from hexapod_lab.config import Settings
from hexapod_lab.main import create_app


ORIGIN = "https://lab.example"


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        data_dir=tmp_path, api_keys="operator:alice:secret,viewer:bob:read-only",
        driver="simulated", robot_command=(), camera_input="", bind="127.0.0.1",
        port=8767, public_base_url=ORIGIN, auto_worker=False,
        max_duration_seconds=2,
    )
    with TestClient(create_app(settings), base_url=ORIGIN, follow_redirects=False) as test_client:
        yield test_client


def login(client, username="alice", password="secret", next_path="/"):
    return client.post("/login", headers={"Origin": ORIGIN}, data={
        "username": username, "password": password, "next": next_path,
    })


def test_browser_redirect_and_api_challenge_remain_distinct(client):
    response = client.get("/")
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2F"
    assert "www-authenticate" not in response.headers
    api = client.get("/api/experiments")
    assert api.status_code == 401
    assert api.headers["www-authenticate"] == 'Basic realm="Hexapod Lab"'
    assert client.get("/api/experiments", auth=("alice", "secret")).status_code == 200
    assert client.get("/api/experiments", headers={"Authorization": "Bearer secret"}).status_code == 200


def test_login_page_ignores_stale_basic_and_invalid_login_has_no_popup(client):
    response = client.get("/login", auth=("alice", "old-password"))
    assert response.status_code == 200
    assert response.headers["referrer-policy"] == "same-origin"
    assert response.headers["cache-control"] == "no-store"
    response = login(client, password="secret ")
    assert response.status_code == 401
    assert "www-authenticate" not in response.headers
    assert "wasn’t accepted" in response.text
    assert "set-cookie" not in response.headers


def test_session_authenticates_page_api_and_overrides_stale_basic(client):
    response = login(client)
    assert response.status_code == 303
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert "max-age" not in cookie and "expires=" not in cookie
    assert "secret" not in cookie
    page = client.get("/", auth=("alice", "old-password"))
    assert page.status_code == 200
    assert "Sign out" in page.text
    assert client.get("/api/experiments").status_code == 200


def test_session_writes_need_same_origin_and_keep_role_limits(client):
    assert login(client).status_code == 303
    payload = {"name": "Browser test", "duration_seconds": .1}
    for headers in ({}, {"Origin": "https://evil.example"},
                    {"Origin": ORIGIN, "Sec-Fetch-Site": "cross-site"}):
        assert client.post("/api/experiments", headers=headers, json=payload).status_code == 403
    assert client.post("/api/experiments", headers={"Origin": ORIGIN}, json=payload).status_code == 202
    assert login(client, "bob", "read-only").status_code == 303
    assert client.post("/api/experiments", headers={"Origin": ORIGIN}, json=payload).status_code == 403


def test_logout_revokes_copied_cookie_and_stale_cookie_does_not_challenge(client):
    assert login(client).status_code == 303
    token = client.cookies.get(browser_auth.COOKIE_NAME)
    assert client.post("/logout", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.get("/").status_code == 200
    assert client.post("/logout", headers={"Origin": ORIGIN}).status_code == 303
    client.cookies.set(browser_auth.COOKIE_NAME, token)
    assert client.get("/").status_code == 303
    response = client.get("/api/experiments")
    assert response.status_code == 401
    assert "www-authenticate" not in response.headers


def test_expired_session_redirects_without_reopening_basic(client, monkeypatch):
    now = browser_auth.time.monotonic()
    assert login(client).status_code == 303
    monkeypatch.setattr(browser_auth.time, "monotonic", lambda: now + browser_auth.SESSION_SECONDS + 10)
    assert client.get("/").status_code == 303
    response = client.get("/api/experiments")
    assert response.status_code == 401
    assert "www-authenticate" not in response.headers


@pytest.mark.parametrize("destination", ["https://evil.example", "//evil.example", "/\\evil.example", "/api/experiments", "/login"])
def test_login_rejects_external_and_nonpage_redirects(client, destination):
    response = login(client, next_path=destination)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_login_preserves_local_destination_and_blocks_cross_origin_submission(client):
    payload = {"username": "alice", "password": "secret", "next": "/tag-scan"}
    assert client.post("/login", data=payload).status_code == 403
    assert client.post("/login", headers={"Origin": "https://evil.example"}, data=payload).status_code == 403
    response = login(client, next_path="/tag-scan")
    assert response.status_code == 303
    assert response.headers["location"] == "/tag-scan"
