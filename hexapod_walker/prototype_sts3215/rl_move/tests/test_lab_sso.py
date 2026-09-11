"""Robot Lab v2's independently verified shared browser login.

Run with the Lab's declared dependencies:
uv run --project experiment_lab --extra dev pytest -q \
  hexapod_walker/prototype_sts3215/rl_move/tests/test_lab_sso.py
"""

import base64
import hashlib
import hmac
import time

import pytest

pytest.importorskip("fastapi", reason="Robot Lab has its own project environment")
pytest.importorskip("httpx", reason="Run with experiment_lab's dev extra")
pytest.importorskip("hexapod_lab2", reason="Run with --project experiment_lab")

from fastapi.testclient import TestClient
from hexapod_lab2.config import Settings
from hexapod_lab2.server import create_app
from hexapod_lab2.sso import COOKIE_NAME, SsoAuth  # noqa: F401  (COOKIE_NAME is the wire contract)


ORIGIN = "https://robot-lab.example.test"
SECRET = b"test-only-controller-signing-secret"
KEYS = "operator:api:token,viewer:reader:read-only"


def signed_cookie(name="alice", *, secret=SECRET, expires=None):
    # Controller wire format: unpadded base64url(user|expiry).hex(HMAC-SHA256).
    payload = f"{name}|{expires if expires is not None else int(time.time()) + 3600}".encode()
    return (base64.urlsafe_b64encode(payload).decode().rstrip("=") + "."
            + hmac.new(secret, payload, hashlib.sha256).hexdigest())


@pytest.fixture
def secret_file(tmp_path):
    secret = tmp_path / "sso-secret"
    secret.write_bytes(SECRET)
    secret.chmod(0o600)
    return secret


def make_app(tmp_path, secret_file, users="operator:alice,viewer:bob"):
    settings = Settings(data_dir=tmp_path / "data", checkout=tmp_path / "checkout")
    return create_app(settings, api_keys=KEYS, public_base_url=ORIGIN, sso_secret_file=secret_file,
                      sso_users=users, sso_cookie_domain=".example.test")


@pytest.fixture
def client(tmp_path, secret_file):
    with TestClient(make_app(tmp_path, secret_file), base_url=ORIGIN, follow_redirects=False) as client:
        yield client


def add_cookie(client, token):
    client.cookies.set(COOKIE_NAME, token, domain=".example.test", path="/")


def test_shared_cookie_opens_page_and_api_without_second_login(client):
    add_cookie(client, signed_cookie())
    page = client.get("/")
    assert page.status_code == 200
    assert "Sign out" in page.text
    assert page.headers["cache-control"] == "no-store"
    assert client.get("/api/state").status_code == 200
    assert client.get("/login?next=%2Fv2%2F").headers["location"] == "/v2/"
    assert client.get("/login?next=https://evil.test").headers["location"] == "/"


@pytest.mark.parametrize("token", [
    pytest.param(signed_cookie(secret=b"attacker-key"), id="wrong-signing-key"),
    pytest.param(signed_cookie(expires=1), id="expired"),
    pytest.param(signed_cookie("unlisted"), id="unlisted-user"),
    pytest.param("not-a-token", id="missing-signature"),
    pytest.param("%%%%.fake", id="malformed-encoding"),
    pytest.param("x." + "f" * 64, id="invalid-signature"),
])
def test_invalid_cookie_and_forged_forwarded_identity_do_not_authenticate(client, token):
    add_cookie(client, token)
    response = client.get("/api/state", headers={"X-Hexapod-User": "alice"})
    assert response.status_code == 401
    assert "www-authenticate" not in response.headers


def test_rotated_or_missing_secret_fails_closed(client, secret_file):
    add_cookie(client, signed_cookie())
    assert client.get("/api/state").status_code == 200
    secret_file.write_bytes(b"rotated-test-secret")
    assert client.get("/api/state").status_code == 401
    secret_file.unlink()
    assert client.get("/api/state").status_code == 401
    assert client.get("/api/state", headers={"Authorization": "Bearer token"}).status_code == 200


def test_sso_requires_explicit_user_configuration(tmp_path, secret_file):
    for secret, users in [(None, "operator:alice"), (secret_file, "")]:
        with TestClient(make_app(tmp_path, secret, users), base_url=ORIGIN) as client:
            add_cookie(client, signed_cookie())
            assert client.get("/api/state").status_code == 401


def test_cookie_writes_require_same_origin_and_preserve_viewer_role(client):
    add_cookie(client, signed_cookie())
    payload = {"title": "SSO test", "why": "check", "robot": "hexapod2"}
    for headers in ({}, {"Origin": "https://evil.test"},
                    {"Origin": ORIGIN, "Sec-Fetch-Site": "cross-site"}):
        assert client.post("/v2/api/import", headers=headers, json=payload).status_code == 403
    assert client.post("/v2/api/import", headers={"Origin": ORIGIN}, json=payload).status_code == 201
    add_cookie(client, signed_cookie("bob"))
    assert client.get("/api/state").status_code == 200
    assert client.post("/v2/api/import", headers={"Origin": ORIGIN}, json=payload).status_code == 403


def test_explicit_api_credentials_keep_their_own_role(client):
    payload = {"title": "API test", "why": "check"}
    assert client.post("/v2/api/import", json=payload, headers={"Authorization": "Bearer token"}).status_code == 201
    assert client.post("/v2/api/import", json=payload, headers={"Authorization": "Bearer read-only"}).status_code == 403
    assert client.get("/api/state", headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert client.get("/api/state", auth=("reader", "read-only")).status_code == 200
    assert client.get("/login", auth=("alice", "stale")).status_code == 200
