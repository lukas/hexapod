import base64
import json

import pytest

from hexapod_lab.agent_providers import (
    AgentProviderError,
    ClaudeProvider,
    CodexProvider,
    get_provider,
)
from hexapod_lab.codex_transcripts import finalize_codex_transcript
from hexapod_lab.config import Settings


def configured(tmp_path, **overrides):
    values = dict(
        data_dir=tmp_path / "data",
        api_keys="automation:codex:auto,operator:alice:operator",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="",
        auto_worker=False,
        max_duration_seconds=900,
        codex_workdir=tmp_path / "workspace",
    )
    values.update(overrides)
    return Settings(**values)


def schema():
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["summary"],
        "properties": {"summary": {"type": "string"}},
    }


def build(tmp_path, provider, role, images=()):
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)
    return provider.build(
        role,
        workdir=workdir,
        prompt="analyse this",
        schema=schema(),
        schema_path=run_dir / "output.schema.json",
        output_path=run_dir / "final.tmp.json",
        images=images,
    )


def test_default_provider_is_codex(tmp_path):
    assert get_provider(configured(tmp_path)).name == "codex"


def test_unknown_provider_is_refused(tmp_path):
    with pytest.raises(AgentProviderError):
        get_provider(configured(tmp_path, agent_provider="gemini"))


def test_claude_sealed_lanes_have_no_tools_and_no_mcp(tmp_path):
    settings = configured(
        tmp_path,
        agent_provider="claude",
        claude_mcp_config=tmp_path / "mcp.json",
    )
    provider = get_provider(settings)
    for role in ("analysis", "advance"):
        command = build(tmp_path, provider, role).command
        assert "--safe-mode" in command
        assert command[command.index("--tools") + 1] == ""
        assert "--strict-mcp-config" in command
        assert "--mcp-config" not in command
        assert command[command.index("--setting-sources") + 1] == ""
        assert command[command.index("--permission-mode") + 1] == "dontAsk"
        assert "bypassPermissions" not in command


def test_claude_sealed_environment_carries_no_service_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv("HEXAPOD_LAB_TOKEN", "lab-secret")
    monkeypatch.setenv("HEXAPOD_ORCHESTRATOR_TOKEN", "must-not-leak")
    monkeypatch.setenv("BUILDVIZ_API_KEY", "must-not-leak")
    provider = get_provider(configured(tmp_path, agent_provider="claude"))
    environment = build(tmp_path, provider, "analysis").environment
    assert "HEXAPOD_LAB_TOKEN" not in environment
    assert "HEXAPOD_ORCHESTRATOR_TOKEN" not in environment
    assert "BUILDVIZ_API_KEY" not in environment


def test_claude_engineering_lane_attaches_only_configured_mcp(tmp_path, monkeypatch):
    monkeypatch.setenv("HEXAPOD_ORCHESTRATOR_TOKEN", "orchestrator")
    monkeypatch.setenv("BUILDVIZ_API_KEY", "buildviz")
    mcp = tmp_path / "mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
    provider = get_provider(
        configured(tmp_path, agent_provider="claude", claude_mcp_config=mcp)
    )
    launch = build(tmp_path, provider, "engineering")
    command = launch.command
    assert command[command.index("--mcp-config") + 1] == str(mcp)
    assert "--strict-mcp-config" in command
    assert command[command.index("--permission-mode") + 1] == "bypassPermissions"
    assert "--safe-mode" not in command
    # The engineering lane really does need the MCP bearer values; Claude
    # expands them into headers from its own environment.
    assert launch.environment["HEXAPOD_ORCHESTRATOR_TOKEN"] == "orchestrator"
    assert launch.environment["BUILDVIZ_API_KEY"] == "buildviz"
    assert launch.cwd == tmp_path / "workdir"


def test_claude_engineering_lane_refuses_a_missing_mcp_config(tmp_path):
    provider = get_provider(
        configured(
            tmp_path, agent_provider="claude", claude_mcp_config=tmp_path / "gone.json"
        )
    )
    with pytest.raises(AgentProviderError):
        build(tmp_path, provider, "engineering")


def test_claude_attaches_images_inline_and_names_what_it_dropped(tmp_path):
    small = tmp_path / "frame.png"
    small.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    huge = tmp_path / "huge.jpg"
    huge.write_bytes(b"\xff\xd8" + b"0" * 4096)
    unsupported = tmp_path / "trace.svg"
    unsupported.write_bytes(b"<svg/>")
    provider = get_provider(
        configured(
            tmp_path, agent_provider="claude", claude_max_attachment_bytes=1024
        )
    )
    launch = build(tmp_path, provider, "analysis", images=[small, huge, unsupported])
    message = json.loads(launch.stdin_payload.decode("utf-8"))
    content = message["message"]["content"]
    assert message["type"] == "user"
    images = [block for block in content if block["type"] == "image"]
    assert len(images) == 1
    assert images[0]["source"]["media_type"] == "image/png"
    assert base64.b64decode(images[0]["source"]["data"]) == small.read_bytes()
    text = content[0]["text"]
    assert "huge.jpg" in text and "trace.svg" in text
    # The archived prompt must match what the model was actually sent.
    assert launch.prompt_text == text


def test_claude_result_event_becomes_the_structured_output(tmp_path):
    provider = get_provider(configured(tmp_path, agent_provider="claude"))
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    (run_dir / ".events.raw.jsonl").write_text(
        "\n".join([
            json.dumps({"type": "system", "subtype": "init"}),
            json.dumps({
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "result": '{"summary":"ok"}',
                "structured_output": {"summary": "ok"},
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    output = run_dir / "final.tmp.json"
    assert provider.materialize_output(run_dir, output) == ""
    assert json.loads(output.read_text()) == {"summary": "ok"}


def test_claude_error_result_is_reported_and_writes_no_output(tmp_path):
    provider = get_provider(configured(tmp_path, agent_provider="claude"))
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    (run_dir / ".events.raw.jsonl").write_text(
        json.dumps({
            "type": "result",
            "subtype": "error_max_budget",
            "is_error": True,
            "result": "budget exhausted",
        }) + "\n",
        encoding="utf-8",
    )
    output = run_dir / "final.tmp.json"
    message = provider.materialize_output(run_dir, output)
    assert "error_max_budget" in message
    assert not output.exists()


def test_claude_run_without_a_result_event_is_not_silently_accepted(tmp_path):
    provider = get_provider(configured(tmp_path, agent_provider="claude"))
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    (run_dir / ".events.raw.jsonl").write_text("", encoding="utf-8")
    assert provider.materialize_output(run_dir, run_dir / "final.tmp.json")


def test_codex_materialize_output_leaves_the_cli_written_file_alone(tmp_path):
    provider = get_provider(configured(tmp_path))
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    output = run_dir / "final.tmp.json"
    output.write_text('{"summary":"from codex"}', encoding="utf-8")
    assert provider.materialize_output(run_dir, output) == ""
    assert json.loads(output.read_text()) == {"summary": "from codex"}


def test_claude_transcript_renders_messages_reasoning_and_tools(tmp_path):
    provider = ClaudeProvider(configured(tmp_path, agent_provider="claude"))
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    (run_dir / "prompt.md").write_text("the prompt", encoding="utf-8")
    (run_dir / ".events.raw.jsonl").write_text(
        "\n".join([
            json.dumps({"type": "system", "subtype": "init"}),
            json.dumps({"type": "assistant", "message": {"content": [
                {"type": "thinking", "thinking": "weighing the evidence"},
                {"type": "text", "text": "the gait is asymmetric"},
                {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}},
                {"type": "tool_use", "id": "t2", "name": "StructuredOutput",
                 "input": {"summary": "x"}},
            ]}}),
            json.dumps({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "scene.json"},
                {"type": "tool_result", "tool_use_id": "t2",
                 "content": "Structured output provided successfully"},
            ]}}),
            json.dumps({
                "type": "result", "subtype": "success", "is_error": False,
                "structured_output": {"summary": "x"},
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    finalize_codex_transcript(
        run_dir,
        job_id="job-1",
        experiment_id="exp-1",
        kind="analysis",
        attempt=1,
        redact=lambda value: value,
        redact_text=lambda value: value,
        provider=provider,
    )
    transcript = (run_dir / "transcript.md").read_text()
    assert "# Claude run transcript" in transcript
    assert "the gait is asymmetric" in transcript
    assert "weighing the evidence" in transcript
    assert "Tool use: Bash" in transcript
    assert "scene.json" in transcript
    # The schema answer is published as final.json, not replayed as narrative,
    # and neither is the acknowledgement that call provokes.
    assert "Tool use: StructuredOutput" not in transcript
    assert "Structured output provided successfully" not in transcript


def test_claude_engineering_transcript_shows_only_assistant_messages(tmp_path):
    provider = ClaudeProvider(configured(tmp_path, agent_provider="claude"))
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    (run_dir / ".events.raw.jsonl").write_text(
        "\n".join([
            json.dumps({"type": "assistant", "message": {"content": [
                {"type": "thinking", "thinking": "private reasoning"},
                {"type": "text", "text": "published the new BuildViz version"},
                {"type": "tool_use", "name": "Bash", "input": {"command": "secret"}},
            ]}}),
            json.dumps({"type": "user", "message": {"content": [
                {"type": "tool_result", "content": "internal tool output"},
            ]}}),
        ]) + "\n",
        encoding="utf-8",
    )
    finalize_codex_transcript(
        run_dir,
        job_id="job-2",
        experiment_id="exp-1",
        kind="engineering",
        attempt=1,
        redact=lambda value: value,
        redact_text=lambda value: value,
        provider=provider,
    )
    transcript = (run_dir / "transcript.md").read_text()
    assert "published the new BuildViz version" in transcript
    assert "private reasoning" not in transcript
    assert "internal tool output" not in transcript
    assert "secret" not in transcript


def test_codex_transcript_rendering_is_unchanged_by_default(tmp_path):
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    (run_dir / ".events.raw.jsonl").write_text(
        json.dumps({
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "codex finding"},
        }) + "\n",
        encoding="utf-8",
    )
    finalize_codex_transcript(
        run_dir,
        job_id="job-3",
        experiment_id="exp-1",
        kind="analysis",
        attempt=1,
        redact=lambda value: value,
        redact_text=lambda value: value,
    )
    transcript = (run_dir / "transcript.md").read_text()
    assert "# Codex run transcript" in transcript
    assert "codex finding" in transcript


def test_settings_reject_an_unknown_provider_or_effort(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXAPOD_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HEXAPOD_API_KEYS", "operator:alice:secret")
    monkeypatch.setenv("HEXAPOD_AGENT_PROVIDER", "gpt")
    with pytest.raises(ValueError):
        Settings.from_env()
    monkeypatch.setenv("HEXAPOD_AGENT_PROVIDER", "claude")
    monkeypatch.setenv("HEXAPOD_CLAUDE_EFFORT", "ultra")
    with pytest.raises(ValueError):
        Settings.from_env()
    monkeypatch.setenv("HEXAPOD_CLAUDE_EFFORT", "high")
    settings = Settings.from_env()
    assert settings.agent_provider == "claude"
    assert settings.agent_label == "Claude"
    assert settings.agent_model == settings.claude_model


def test_codex_provider_argv_is_unchanged(tmp_path):
    provider = CodexProvider(configured(tmp_path))
    launch = build(tmp_path, provider, "analysis")
    command = launch.command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "--ignore-user-config" in command
    assert command[-1] == "-"
    assert launch.stdin_payload == b"analyse this"
    assert launch.cwd is None


def test_web_pages_name_the_configured_backend(tmp_path):
    from hexapod_lab import main

    main.create_app(configured(tmp_path, agent_provider="claude"))
    assert main.agent_label() == "Claude"
    assert "Claude experiment loop" in main.codex_queue_panel({}, False)
    assert "Claude follow-through" in main.automation_section(
        {"codex_jobs": [{"kind": "analysis", "status": "queued", "attempts": 1}]}
    )

    main.create_app(configured(tmp_path / "codex", agent_provider="codex"))
    assert main.agent_label() == "Codex"
    assert "Codex experiment loop" in main.codex_queue_panel({}, False)


def test_a_backfilled_attempt_renders_with_the_backend_that_recorded_it(tmp_path):
    """Switching providers must not blank out an older run's transcript."""
    from hexapod_lab.codex_orchestrator import CodexOrchestrator
    from hexapod_lab.db import Store

    settings = configured(tmp_path, agent_provider="claude")
    settings.data_dir.mkdir(parents=True)
    orchestrator = CodexOrchestrator(
        Store(settings.data_dir / "lab.sqlite3"), settings, invoker=lambda *_: {}
    )
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()

    # No metadata yet: the configured backend is the only reasonable guess.
    assert orchestrator._attempt_provider(run_dir).name == "claude"

    (run_dir / "metadata.json").write_text(
        json.dumps({"provider": "codex"}), encoding="utf-8"
    )
    assert orchestrator._attempt_provider(run_dir).name == "codex"

    # An attempt recorded before the field existed can only have been Codex.
    (run_dir / "metadata.json").write_text(
        json.dumps({"model": "gpt-5.6-sol"}), encoding="utf-8"
    )
    assert orchestrator._attempt_provider(run_dir).name == "codex"

    # An unreadable or absent record falls back to the configured backend.
    (run_dir / "metadata.json").write_text("{not json", encoding="utf-8")
    assert orchestrator._attempt_provider(run_dir).name == "claude"


def test_claude_offline_engineering_keeps_mcp_but_not_deploy_channels(
    tmp_path, monkeypatch
):
    """The offline lane narrows ambient access; provider vars ride with it."""
    from hexapod_lab.engineering_lane import ENGINEERING_LANE_OFFLINE

    monkeypatch.setenv("BUILDVIZ_API_KEY", "buildviz")
    monkeypatch.setenv("HEXAPOD_ORCHESTRATOR_TOKEN", "orchestrator")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/agent.sock")
    monkeypatch.setenv("KUBECONFIG", "/tmp/kubeconfig")
    mcp = tmp_path / "mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
    provider = get_provider(
        configured(tmp_path, agent_provider="claude", claude_mcp_config=mcp)
    )
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)
    launch = provider.build(
        "engineering",
        workdir=workdir,
        prompt="do the work",
        schema=schema(),
        schema_path=run_dir / "output.schema.json",
        output_path=run_dir / "final.tmp.json",
        images=(),
        engineering_lane=ENGINEERING_LANE_OFFLINE,
    )
    assert launch.environment["BUILDVIZ_API_KEY"] == "buildviz"
    assert launch.environment["HEXAPOD_ORCHESTRATOR_TOKEN"] == "orchestrator"
    assert "SSH_AUTH_SOCK" not in launch.environment
    assert "KUBECONFIG" not in launch.environment
    assert launch.environment["HEXAPOD_ENGINEERING_LANE"] == ENGINEERING_LANE_OFFLINE


def test_large_prompt_is_delivered_when_the_child_reads_stdin_late(tmp_path):
    """A prompt bigger than the OS pipe buffer must not deadlock the attempt.

    macOS gives a pipe 16 KiB. Any agent that does not drain stdin the moment
    it starts leaves the parent's write blocked partway, and `communicate()`
    cannot be resumed once its first call has timed out.
    """
    import sys

    from hexapod_lab.codex_orchestrator import CodexOrchestrator
    from hexapod_lab.db import Store

    fake_agent = tmp_path / "fake-agent"
    fake_agent.write_text(
        f"#!{sys.executable}\n"
        "import json, pathlib, sys, time\n"
        "time.sleep(2)\n"
        "data = sys.stdin.buffer.read()\n"
        "pathlib.Path(sys.argv[sys.argv.index('-o') + 1]).write_text(\n"
        "    json.dumps({'received': len(data)}))\n"
    )
    fake_agent.chmod(0o700)
    settings = configured(
        tmp_path, codex_bin=fake_agent, codex_analysis_timeout_seconds=60
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    orchestrator = CodexOrchestrator(Store(settings.data_dir / "lab.sqlite3"), settings)

    prompt = "x" * (256 * 1024)
    result = orchestrator._invoke(
        "analysis", {"id": "big-prompt-job", "attempts": 1}, prompt, {"type": "object"}
    )
    assert result["received"] == len(prompt)


def test_claude_usage_is_read_from_the_result_event(tmp_path):
    provider = get_provider(configured(tmp_path, agent_provider="claude"))
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    (run_dir / ".events.raw.jsonl").write_text(
        json.dumps({
            "type": "result", "subtype": "success", "is_error": False,
            "structured_output": {"summary": "ok"},
            "total_cost_usd": 0.42, "duration_ms": 1234, "num_turns": 3,
            "usage": {"input_tokens": 10, "output_tokens": 20,
                      "cache_read_input_tokens": 5},
        }) + "\n",
        encoding="utf-8",
    )
    usage = provider.usage(run_dir)
    assert usage["cost_usd"] == 0.42
    assert usage["output_tokens"] == 20
    assert usage["cache_read_tokens"] == 5
    assert usage["turns"] == 3
    # Codex reports nothing here; absence must not be an error.
    assert get_provider(configured(tmp_path)).usage(run_dir) == {}
