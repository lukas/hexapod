from fastapi.testclient import TestClient

from hexapod_lab.config import Settings
from hexapod_lab.main import create_app


def configured(tmp_path):
    return Settings(
        data_dir=tmp_path,
        api_keys=(
            "operator:alice:operator-secret,"
            "automation:codex-orchestrator:automation-secret"
        ),
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="",
        auto_worker=False,
        max_duration_seconds=30,
    )


def test_automation_token_can_finish_assigned_plan_but_cannot_create_or_cancel(tmp_path):
    app = create_app(configured(tmp_path))
    operator = {"Authorization": "Bearer operator-secret"}
    automation = {"Authorization": "Bearer automation-secret"}
    plan = {
        "name": "assigned guarded plan",
        "description": "No physical motion in this authorization test.",
        "duration_seconds": 1,
        "parameters": {"robot_motion": False},
        "execution_mode": "external_guarded",
    }
    with TestClient(app) as client:
        item = client.post("/api/experiments", headers=operator, json=plan).json()
        other = client.post(
            "/api/experiments",
            headers=operator,
            json={**plan, "name": "another guarded plan"},
        ).json()

        assert client.get("/api/experiments", headers=automation).status_code == 200
        assert client.post(
            "/api/experiments", headers=automation, json=plan
        ).status_code == 403
        assert client.post(
            f"/api/experiments/{item['id']}/cancel", headers=automation
        ).status_code == 403
        assert client.post(
            "/api/results",
            headers=automation,
            json={
                "name": "unassigned",
                "duration_seconds": 1,
                "summary_markdown": "no",
            },
        ).status_code == 403
        assert client.post(
            "/api/codex-queue/resume",
            headers={**automation, "X-Hexapod-Lab": "1"},
            json={"reason": "not an operator", "robot_inspected": True},
        ).status_code == 403

        result = {
            "name": plan["name"],
            "description": plan["description"],
            "duration_seconds": 1,
            "parameters": plan["parameters"],
            "summary_markdown": "# Result\n\nNo motion.\n",
        }
        assert client.put(
            f"/api/experiments/{item['id']}/artifacts/telemetry.csv",
            headers=automation,
            content=b"t,value\n0,1\n",
        ).status_code == 403
        assert client.post(
            f"/api/experiments/{item['id']}/result",
            headers=automation,
            json=result,
        ).status_code == 403
        assert client.post(
            f"/api/experiments/{item['id']}/evidence-seal",
            headers=automation,
        ).status_code == 403

        store = client.app.state.store
        assigned_job = next(
            job for job in store.codex_jobs_for_experiment(item["id"])
            if job["trigger_kind"] == "experiment_submission"
        )
        claimed = store.claim_codex_job(
            "advance", "advance-worker", lease_seconds=60
        )
        assert claimed["id"] == assigned_job["id"]
        assert store.acquire_hardware_lane(
            claimed["id"],
            item["id"],
            "advance-worker",
            lease_seconds=60,
            lease_token=claimed["lease_token"],
        )

        # The lease authorizes exactly one experiment, not every guarded plan.
        other_result = {**result, "name": other["name"]}
        assert client.put(
            f"/api/experiments/{other['id']}/artifacts/telemetry.csv",
            headers=automation,
            content=b"t,value\n0,2\n",
        ).status_code == 403
        assert client.post(
            f"/api/experiments/{other['id']}/result",
            headers=automation,
            json=other_result,
        ).status_code == 403
        assert client.post(
            f"/api/experiments/{other['id']}/evidence-seal",
            headers=automation,
        ).status_code == 403

        assert client.put(
            f"/api/experiments/{item['id']}/artifacts/telemetry.csv",
            headers=automation,
            content=b"t,value\n0,1\n",
        ).status_code == 201
        assert client.post(
            f"/api/experiments/{item['id']}/result",
            headers=automation,
            json=result,
        ).status_code == 200
        assert client.post(
            f"/api/experiments/{item['id']}/evidence-seal",
            headers=automation,
        ).status_code == 200
