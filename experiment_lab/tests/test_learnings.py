"""The reader-facing conclusion must be durable, attributable, and evidence-based."""

import hashlib
from html import escape
import json

from fastapi.testclient import TestClient
import pytest

from hexapod_lab.config import Settings
from hexapod_lab.main import create_app


OPERATOR = {"Authorization": "Bearer operator-secret"}
VIEWER = {"Authorization": "Bearer viewer-secret"}


def settings(tmp_path):
    return Settings(
        data_dir=tmp_path,
        api_keys="operator:alice:operator-secret,viewer:bob:viewer-secret",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="",
        auto_worker=False,
        max_duration_seconds=2,
    )


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as value:
        yield value


def completed_result(client, **extra):
    response = client.post(
        "/api/results",
        headers=OPERATOR,
        json={
            "name": "Supported joint comparison",
            "duration_seconds": 1,
            "summary_markdown": "# Detailed evidence\n\nThe second run had less error.\n",
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_completed_learnings_persist_across_service_restart(tmp_path):
    text = "The second setting tracked the target more closely. We still need to check it under load."
    with TestClient(create_app(settings(tmp_path))) as client:
        item = completed_result(client, what_we_learned=text)
        learned = item["what_we_learned"]
        assert learned["text"] == text
        assert learned["created_by"] == "alice"
        assert learned["created_at"]
        assert learned["revision"] == 1
        assert isinstance(learned["sources"], list)
        experiment_id = item["id"]

    with TestClient(create_app(settings(tmp_path))) as client:
        retrieved = client.get(f"/api/experiments/{experiment_id}", headers=VIEWER)
        assert retrieved.status_code == 200
        assert retrieved.json()["what_we_learned"] == learned
        listed = client.get("/api/experiments", headers=VIEWER).json()
        assert next(row for row in listed if row["id"] == experiment_id)["what_we_learned"] == learned


def test_operator_can_annotate_existing_result_but_viewer_cannot(client):
    item = completed_result(client)
    endpoint = f"/api/experiments/{item['id']}/learnings"
    annotation = {"text": "The second run reduced tracking error.", "sources": ["summary.md"]}
    assert client.post(endpoint, headers=VIEWER, json=annotation).status_code == 403
    before = client.get(f"/api/experiments/{item['id']}", headers=VIEWER).json()
    assert before["what_we_learned"]["status"] == "missing"

    response = client.post(endpoint, headers=OPERATOR, json=annotation)
    assert response.status_code in {200, 201}, response.text
    updated = client.get(f"/api/experiments/{item['id']}", headers=VIEWER).json()
    learned = updated["what_we_learned"]
    assert learned["text"] == annotation["text"]
    assert learned["sources"] == ["summary.md"]
    assert learned["created_by"] == "alice"
    assert learned["revision"] == 1
    for key in ("status", "parameters", "started_at", "finished_at"):
        assert updated[key] == before[key]
    summary = client.get(f"/api/experiments/{item['id']}/artifacts/summary.md", headers=VIEWER)
    assert summary.text == "# Detailed evidence\n\nThe second run had less error.\n"


@pytest.mark.parametrize("state", ["queued", "running", "waiting_for_operator"])
def test_unfinished_experiments_have_pending_conclusions_and_reject_annotations(client, state):
    proposal = "This is a hypothesis about improved tracking, not a measured result."
    queued = client.post(
        "/api/experiments",
        headers=OPERATOR,
        json={
            "name": "Pending comparison",
            "description": proposal,
            "duration_seconds": 1,
            "execution_mode": "external_guarded" if state == "waiting_for_operator" else "builtin",
        },
    )
    assert queued.status_code == 202
    experiment_id = queued.json()["id"]
    if state == "running":
        assert client.app.state.store.claim_next()["id"] == experiment_id
    before = client.get(f"/api/experiments/{experiment_id}", headers=VIEWER).json()
    assert before["status"] == state
    assert before["what_we_learned"]["status"] == "pending"
    assert before["what_we_learned"]["sources"] == []
    assert before["what_we_learned"]["text"] != proposal
    rejected = client.post(
        f"/api/experiments/{experiment_id}/learnings",
        headers=OPERATOR,
        json={"text": "The setting works better.", "sources": []},
    )
    assert rejected.status_code == 409, rejected.text
    after = client.get(f"/api/experiments/{experiment_id}", headers=VIEWER).json()
    assert after["what_we_learned"] == before["what_we_learned"]
    assert after["status"] == state


@pytest.mark.parametrize("source", ["missing.json", "../outside.txt", "/outside.txt", "nested/report.txt", "..\\outside.txt"])
def test_annotation_rejects_unavailable_or_nonflat_sources(client, tmp_path, source):
    item = completed_result(client)
    (tmp_path / "experiments" / "outside.txt").write_text("Unrelated evidence")
    response = client.post(
        f"/api/experiments/{item['id']}/learnings",
        headers=OPERATOR,
        json={"text": "A proposed conclusion.", "sources": [source]},
    )
    assert response.status_code in {400, 404, 422}, response.text
    retrieved = client.get(f"/api/experiments/{item['id']}", headers=VIEWER).json()
    assert retrieved["what_we_learned"]["status"] == "missing"


def test_conclusion_is_escaped_and_shown_before_video_and_detailed_summary(client):
    text = "Lower error <script>alert('unsafe')</script> & more testing needed."
    item = completed_result(client, what_we_learned=text)
    video = client.put(
        f"/api/experiments/{item['id']}/artifacts/video.mp4",
        headers={**OPERATOR, "Content-Type": "video/mp4"},
        content=b"video placeholder for HTML ordering",
    )
    assert video.status_code == 201, video.text
    response = client.get(f"/experiments/{item['id']}", headers=VIEWER)
    assert response.status_code == 200
    html = response.text
    assert "<section class='learnings' aria-labelledby='learnings-title'>" in html
    assert "<h2 id='learnings-title'>What we learned</h2>" in html
    assert escape(text) in html
    assert "<script>alert('unsafe')</script>" not in html
    assert html.index("<h1 ") < html.index("id='learnings-title'") < html.index("<video ") < html.index("<h2>Detailed report</h2>")


def test_completion_rejects_oversized_conclusion_without_creating_result(client):
    response = client.post(
        "/api/results",
        headers=OPERATOR,
        json={
            "name": "Too much text",
            "duration_seconds": 1,
            "summary_markdown": "Evidence.",
            "what_we_learned": "x" * 6001,
        },
    )
    assert response.status_code == 422
    assert client.get("/api/experiments", headers=VIEWER).json() == []


def test_old_external_completion_hash_remains_retryable(client):
    """An absent optional field must not invalidate receipts written before this feature."""
    legacy_result = {
        "name": "Legacy guarded comparison",
        "description": "",
        "duration_seconds": 1.0,
        "parameters": {},
        "status": "succeeded",
        "error": "",
        "summary_markdown": "# Legacy evidence\n",
        "recorded_at": None,
        "tag_layout_revision_id": None,
    }
    plan = {key: legacy_result[key] for key in ("name", "description", "duration_seconds", "parameters")}
    queued = client.post("/api/experiments", headers=OPERATOR, json={**plan, "execution_mode": "external_guarded"})
    assert queued.status_code == 202
    experiment_id = queued.json()["id"]
    legacy_digest = hashlib.sha256(json.dumps(legacy_result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    client.app.state.store.import_result(
        plan,
        "alice",
        "succeeded",
        experiment_id=experiment_id,
        completion_sha256=legacy_digest,
    )
    endpoint = f"/api/experiments/{experiment_id}/result"
    retried = client.post(endpoint, headers=OPERATOR, json=legacy_result)
    assert retried.status_code == 200, retried.text
    assert retried.json()["id"] == experiment_id
    assert retried.json()["what_we_learned"]["status"] == "missing"
    changed = client.post(endpoint, headers=OPERATOR, json={**legacy_result, "summary_markdown": "Different evidence."})
    assert changed.status_code == 409
