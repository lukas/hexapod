"""Robot Lab's independently verified shared browser login.

Run with the Lab's declared dependencies:
uv run --project experiment_lab --extra dev pytest -q \
  hexapod_walker/prototype_sts3215/rl_move/tests/test_lab_sso.py
"""

import base64
from dataclasses import replace
import hashlib
import hmac
import time

import pytest

pytest.importorskip("fastapi", reason="Robot Lab has its own project environment")
pytest.importorskip("httpx", reason="Run with experiment_lab's dev extra")
pytest.importorskip("hexapod_lab", reason="Run with --project experiment_lab")

from fastapi.testclient import TestClient
from hexapod_lab.config import Settings
from hexapod_lab.main import create_app
from hexapod_lab.sso import COOKIE_NAME, SsoAuth


ORIGIN = "https://robot-lab.example.test"
SECRET = b"test-only-controller-signing-secret"


def signed_cookie(name="alice", *, secret=SECRET, expires=None):
    # Controller wire format: unpadded base64url(user|expiry).hex(HMAC-SHA256).
    payload = f"{name}|{expires if expires is not None else int(time.time()) + 3600}".encode()
    return (base64.urlsafe_b64encode(payload).decode().rstrip("=") + "."
            + hmac.new(secret, payload, hashlib.sha256).hexdigest())


@pytest.fixture
def settings(tmp_path):
    secret = tmp_path / "sso-secret"
    secret.write_bytes(SECRET)
    secret.chmod(0o600)
    return Settings(
        data_dir=tmp_path / "data", api_keys="operator:api:token,viewer:reader:read-only",
        driver="simulated", robot_command=(), camera_input="", bind="127.0.0.1",
        port=8767, public_base_url=ORIGIN, auto_worker=False, max_duration_seconds=2,
        sso_secret_file=secret, sso_users="operator:alice,viewer:bob",
        sso_cookie_domain=".example.test",
    )


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), base_url=ORIGIN, follow_redirects=False) as client:
        yield client


def add_cookie(client, token):
    client.cookies.set(COOKIE_NAME, token, domain=".example.test", path="/")


def test_shared_cookie_opens_page_and_api_without_second_login(client):
    add_cookie(client, signed_cookie())
    page = client.get("/")
    assert page.status_code == 200
    assert "Sign out" in page.text
    assert page.headers["cache-control"] == "no-store"
    assert client.get("/api/experiments").status_code == 200
    assert client.get("/login?next=%2Ftag-scan").headers["location"] == "/tag-scan"
    assert client.get("/login?next=https://evil.test").headers["location"] == "/"


@pytest.mark.parametrize("token", [
    # Expiring signatures differ across worker collection times; case IDs must not.
    pytest.param(signed_cookie(secret=b"attacker-key"), id="wrong-signing-key"),
    pytest.param(signed_cookie(expires=1), id="expired"),
    pytest.param(signed_cookie("unlisted"), id="unlisted-user"),
    pytest.param("not-a-token", id="missing-signature"),
    pytest.param("%%%%.fake", id="malformed-encoding"),
    pytest.param("x." + "f" * 64, id="invalid-signature"),
    pytest.param("x." + "f" * 513, id="oversized-signature"),
])
def test_invalid_cookie_and_forged_forwarded_identity_do_not_authenticate(client, token):
    add_cookie(client, token)
    response = client.get("/api/experiments", headers={"X-Hexapod-User": "alice"})
    assert response.status_code == 401
    assert "www-authenticate" not in response.headers


def test_forwarded_header_alone_does_not_authenticate(client):
    assert client.get("/api/experiments", headers={"X-Hexapod-User": "alice"}).status_code == 401


def test_missing_empty_unreadable_and_rotated_secret_fail_closed(client, settings):
    add_cookie(client, signed_cookie())
    assert client.get("/api/experiments").status_code == 200
    settings.sso_secret_file.write_bytes(b"rotated-test-secret")
    assert client.get("/api/experiments").status_code == 401
    settings.sso_secret_file.write_bytes(b"")
    assert client.get("/api/experiments").status_code == 401
    settings.sso_secret_file.unlink()
    assert client.get("/api/experiments").status_code == 401
    settings.sso_secret_file.mkdir()
    assert client.get("/api/experiments").status_code == 401
    assert client.get("/api/experiments", headers={"Authorization": "Bearer token"}).status_code == 200


def test_sso_requires_explicit_user_configuration(settings):
    for secret_file, users in [(None, settings.sso_users), (settings.sso_secret_file, "")]:
        with TestClient(create_app(replace(settings, sso_secret_file=secret_file, sso_users=users)),
                        base_url=ORIGIN) as client:
            add_cookie(client, signed_cookie())
            assert client.get("/api/experiments").status_code == 401


def test_cookie_writes_require_same_origin_and_preserve_viewer_role(client):
    add_cookie(client, signed_cookie())
    payload = {"name": "SSO test", "duration_seconds": 0.1}
    for headers in ({}, {"Origin": "https://evil.test"},
                    {"Origin": ORIGIN, "Sec-Fetch-Site": "cross-site"}):
        assert client.post("/api/experiments", headers=headers, json=payload).status_code == 403
    assert client.post("/api/experiments", headers={"Origin": ORIGIN}, json=payload).status_code == 202
    add_cookie(client, signed_cookie("bob"))
    assert client.get("/api/experiments").status_code == 200
    assert client.post("/api/experiments", headers={"Origin": ORIGIN}, json=payload).status_code == 403


def test_explicit_api_credentials_keep_their_own_role(client):
    add_cookie(client, signed_cookie())
    payload = {"name": "API test", "duration_seconds": 0.1}
    assert client.post("/api/experiments", json=payload,
                       headers={"Authorization": "Bearer token"}).status_code == 202
    assert client.post("/api/experiments", json=payload,
                       headers={"Authorization": "Bearer read-only"}).status_code == 403
    assert client.get("/api/experiments", headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert client.get("/api/experiments", auth=("reader", "read-only")).status_code == 200
    # Stale browser Basic credentials must not create a /login -> / -> /login loop.
    assert client.get("/login", auth=("alice", "stale")).status_code == 200


def test_logout_clears_domain_cookie_and_rejects_cross_origin(client):
    add_cookie(client, signed_cookie())
    assert client.post("/logout", headers={"Origin": "https://evil.test"}).status_code == 403
    assert client.get("/api/experiments").status_code == 200
    logout = client.post("/logout", headers={"Origin": ORIGIN})
    assert logout.status_code == 303
    shared = [value for value in logout.headers.get_list("set-cookie") if value.startswith(COOKIE_NAME + "=")]
    assert len(shared) == 1
    assert "Domain=.example.test" in shared[0] and "Max-Age=0" in shared[0]
    assert client.get("/api/experiments").status_code == 401


def test_secret_and_cookie_parsing_reject_non_ascii_inputs(settings):
    verifier = SsoAuth(settings.sso_secret_file, settings.sso_users)
    assert verifier.authenticate("eA.\N{SNOWMAN}") is None
    settings.sso_secret_file.write_bytes(b"\xff")
    assert verifier.authenticate(signed_cookie()) is None


@pytest.mark.parametrize("users", ["alice", "root:alice", "operator:", "operator:alice,admin:alice", "operator:a|b"])
def test_invalid_role_map_rejected(settings, users):
    with pytest.raises(ValueError, match="HEXAPOD_SSO_USERS"):
        SsoAuth(settings.sso_secret_file, users)


def test_environment_settings(monkeypatch, tmp_path):
    path = tmp_path / "key"
    monkeypatch.setenv("HEXAPOD_SSO_SECRET_FILE", str(path))
    monkeypatch.setenv("HEXAPOD_SSO_USERS", "viewer:bob")
    monkeypatch.setenv("HEXAPOD_SSO_COOKIE_DOMAIN", ".example.test")
    settings = Settings.from_env()
    assert settings.sso_secret_file == path
    assert settings.sso_users == "viewer:bob"
    assert settings.sso_cookie_domain == ".example.test"
