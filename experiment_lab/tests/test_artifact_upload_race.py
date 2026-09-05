import asyncio
import hashlib
import json

import httpx

from hexapod_lab.config import Settings
from hexapod_lab.main import create_app


def configured(tmp_path, **overrides):
    values = dict(
        data_dir=tmp_path,
        api_keys="admin:alice:secret",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="",
        auto_worker=False,
        max_duration_seconds=30,
    )
    values.update(overrides)
    return Settings(**values)


async def completed_experiment(client, headers):
    response = await client.post(
        "/api/results",
        headers=headers,
        json={
            "name": "Upload race fixture",
            "description": "Exercise evidence upload serialization.",
            "duration_seconds": 1,
            "parameters": {"robot_motion": False},
            "summary_markdown": "# Upload race fixture\n\nNo robot motion.\n",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_seal_rejects_while_an_artifact_is_streaming_then_succeeds(tmp_path):
    async def exercise():
        app = create_app(configured(tmp_path))
        transport = httpx.ASGITransport(app=app)
        headers = {"Authorization": "Bearer secret"}
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            experiment = await completed_experiment(client, headers)
            run_dir = tmp_path / "experiments" / experiment["id"]
            body_started = asyncio.Event()
            release_body = asyncio.Event()

            async def body():
                body_started.set()
                yield b"first-half"
                await release_body.wait()
                yield b"second-half"

            upload_task = asyncio.create_task(
                client.put(
                    f"/api/experiments/{experiment['id']}/artifacts/telemetry.bin",
                    headers=headers,
                    content=body(),
                )
            )
            await asyncio.wait_for(body_started.wait(), timeout=2)
            active = list(run_dir.glob(".telemetry.bin.*.upload"))
            assert len(active) == 1

            sealed = await client.post(
                f"/api/experiments/{experiment['id']}/evidence-seal",
                headers=headers,
            )
            assert sealed.status_code == 409
            release_body.set()
            upload = await asyncio.wait_for(upload_task, timeout=2)

            assert upload.status_code == 201
            assert (run_dir / "telemetry.bin").read_bytes() == b"first-halfsecond-half"
            assert list(run_dir.glob(".*.upload")) == []
            sealed = await client.post(
                f"/api/experiments/{experiment['id']}/evidence-seal",
                headers=headers,
            )
            assert sealed.status_code == 200
            manifest_path = run_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert all(not entry["name"].startswith(".") for entry in manifest["artifacts"])
            assert any(entry["name"] == "telemetry.bin" for entry in manifest["artifacts"])
            digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            assert app.state.store.get(experiment["id"])["evidence_manifest_sha256"] == digest

    asyncio.run(exercise())


def test_concurrent_uploads_commit_only_one_complete_artifact(tmp_path):
    async def exercise():
        app = create_app(configured(tmp_path))
        transport = httpx.ASGITransport(app=app)
        headers = {"Authorization": "Bearer secret"}
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            experiment = await completed_experiment(client, headers)
            run_dir = tmp_path / "experiments" / experiment["id"]
            first_started = asyncio.Event()
            second_started = asyncio.Event()
            release_bodies = asyncio.Event()

            async def body(prefix, started):
                started.set()
                yield prefix
                await release_bodies.wait()
                yield b"-complete"

            url = f"/api/experiments/{experiment['id']}/artifacts/result.bin"
            first = asyncio.create_task(
                client.put(url, headers=headers, content=body(b"first", first_started))
            )
            second = asyncio.create_task(
                client.put(url, headers=headers, content=body(b"second", second_started))
            )
            await asyncio.wait_for(
                asyncio.gather(first_started.wait(), second_started.wait()), timeout=2
            )
            assert len(list(run_dir.glob(".result.bin.*.upload"))) == 2

            release_bodies.set()
            responses = await asyncio.wait_for(
                asyncio.gather(first, second), timeout=2
            )

            assert sorted(response.status_code for response in responses) == [201, 409]
            assert (run_dir / "result.bin").read_bytes() in {
                b"first-complete",
                b"second-complete",
            }
            assert list(run_dir.glob(".*.upload")) == []
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            assert [
                entry["name"] for entry in manifest["artifacts"]
                if entry["name"] == "result.bin"
            ] == ["result.bin"]

    asyncio.run(exercise())


def test_upload_rejects_hidden_and_reserved_upload_suffix_names(tmp_path):
    app = create_app(configured(tmp_path))
    transport = httpx.ASGITransport(app=app)

    async def exercise():
        headers = {"Authorization": "Bearer secret"}
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            experiment = await completed_experiment(client, headers)
            for filename in (".hidden", "camera.upload"):
                response = await client.put(
                    f"/api/experiments/{experiment['id']}/artifacts/{filename}",
                    headers=headers,
                    content=b"data",
                )
                assert response.status_code == 400

    asyncio.run(exercise())


def test_upload_enforces_per_experiment_count_and_aggregate_quotas(tmp_path):
    async def count_exercise():
        app = create_app(configured(tmp_path, max_experiment_artifacts=3))
        headers = {"Authorization": "Bearer secret"}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            experiment = await completed_experiment(client, headers)
            first = await client.put(
                f"/api/experiments/{experiment['id']}/artifacts/first.bin",
                headers=headers,
                content=b"one",
            )
            second = await client.put(
                f"/api/experiments/{experiment['id']}/artifacts/second.bin",
                headers=headers,
                content=b"two",
            )
            assert first.status_code == 201
            assert second.status_code == 413

    async def aggregate_exercise():
        app = create_app(configured(
            tmp_path / "aggregate",
            max_experiment_artifact_bytes=1024 * 1024,
        ))
        headers = {"Authorization": "Bearer secret"}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            experiment = await completed_experiment(client, headers)
            response = await client.put(
                f"/api/experiments/{experiment['id']}/artifacts/data.bin",
                headers=headers,
                content=b"x" * (1024 * 1024),
            )
            assert response.status_code == 413

    asyncio.run(count_exercise())
    asyncio.run(aggregate_exercise())
