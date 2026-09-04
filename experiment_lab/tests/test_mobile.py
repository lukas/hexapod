from fastapi.testclient import TestClient

from hexapod_lab.config import Settings
from hexapod_lab.main import create_app


def configured(tmp_path):
    return Settings(
        data_dir=tmp_path,
        api_keys="viewer:phone:read-only",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="https://robot-lab.example",
        auto_worker=False,
        max_duration_seconds=2,
    )


def test_mobile_surface_is_read_only_and_authenticated(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "hexapod_lab.main.fetch_rl_document",
        lambda document: f"# {document}\nhealthy",
    )
    app = create_app(configured(tmp_path))
    with TestClient(app) as client:
        assert client.get("/api/mobile/overview").status_code == 401
        response = client.get(
            "/api/mobile/overview",
            headers={"Authorization": "Bearer read-only"},
        )
        assert response.status_code == 200
        assert response.json()["read_only"] is True

        schema = client.get("/api/mobile/openapi.json").json()
        assert schema["servers"][0]["url"] == "https://robot-lab.example"
        assert all(set(methods) == {"get"} for methods in schema["paths"].values())


def test_mobile_document_path_rejects_traversal():
    from fastapi import HTTPException
    from hexapod_lab.mobile import fetch_rl_doc_path

    try:
        fetch_rl_doc_path("../secret")
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("path traversal was accepted")
