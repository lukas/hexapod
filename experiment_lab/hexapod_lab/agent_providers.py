"""Pluggable coding-agent CLI backends for the Robot Lab automation lanes.

The Lab drives an external agent CLI for its ``analysis``, ``advance``, and
``engineering`` lanes.  Historically that CLI was always ``codex exec``.  This
module isolates every provider-specific detail — argv, stdin payload,
structured-output extraction, environment allowlist, and event-stream
vocabulary — so the same lease, deadline-wrapper, transcript, and redaction
machinery can drive Claude Code instead.

Nothing here starts a process or touches the database.  The orchestrator keeps
ownership of the deadline wrapper, process markers, and lease fencing; a
provider only describes *what* to launch and *how to read what came back*.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .engineering_lane import ENGINEERING_LANE_HARDWARE, engineering_environment


SEALED_ROLES = ("analysis", "advance")
IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class AgentProviderError(RuntimeError):
    """The configured provider cannot be built or its output cannot be read."""


@dataclass(frozen=True)
class AgentLaunch:
    """One fully described child process for a single attempt."""

    command: List[str]
    stdin_payload: bytes
    environment: Dict[str, str]
    cwd: Optional[Path] = None
    # What the model was actually shown. Written to ``prompt.md`` so the
    # archived transcript matches the request instead of the pre-attachment
    # draft of it.
    prompt_text: str = ""


def base_environment(extra: Sequence[str] = ()) -> Dict[str, str]:
    names = {
        "HOME",
        "USER",
        "LOGNAME",
        "PATH",
        "SHELL",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        *extra,
    }
    return {name: os.environ[name] for name in names if os.environ.get(name)}


class AgentProvider:
    """Describe one agent CLI to the orchestrator."""

    #: Stable identifier persisted in run metadata.
    name = "agent"
    #: Human label used in errors, transcripts, and the results page.
    label = "Agent"

    def __init__(self, settings: Any):
        self.settings = settings

    # -- identity -----------------------------------------------------------

    @property
    def model(self) -> str:
        raise NotImplementedError

    @property
    def reasoning_effort(self) -> str:
        raise NotImplementedError

    # -- launch -------------------------------------------------------------

    def build(
        self,
        role: str,
        *,
        workdir: Path,
        prompt: str,
        schema: Dict[str, Any],
        schema_path: Path,
        output_path: Path,
        images: Sequence[Path],
        engineering_lane: str = ENGINEERING_LANE_HARDWARE,
    ) -> AgentLaunch:
        raise NotImplementedError

    # -- results ------------------------------------------------------------

    def materialize_output(self, run_dir: Path, output_path: Path) -> str:
        """Ensure ``output_path`` holds the structured result.

        Called once the child is reaped and before the transcript is sealed,
        so a provider that only streams its answer can still recover it from
        the raw event capture.  Returns an error message instead of raising:
        a completed nondeterministic run must always get its transcript
        finalized before the attempt is failed.
        """
        return ""

    # -- transcripts --------------------------------------------------------

    @property
    def transcript_title(self) -> str:
        return f"# {self.label} run transcript"

    @property
    def transcript_note(self) -> str:
        return (
            f"This transcript is generated from the redacted {self.label} JSON "
            "event stream. The JSONL file is the complete machine-readable record."
        )

    def transcript_reader(self) -> "AgentProvider":
        """Return a reader for one ordered pass over an event stream.

        Providers whose events are individually self-describing read as
        themselves.  A provider that must correlate events across a stream
        returns a fresh object so two renders never share state.
        """
        return self

    def event_blocks(
        self, event: Dict[str, Any], *, agent_messages_only: bool = False
    ) -> List[Tuple[str, str]]:
        """Extract the user-visible ``(label, text)`` pairs from one event."""
        raise NotImplementedError


class CodexProvider(AgentProvider):
    """``codex exec`` — the original and default backend."""

    name = "codex"
    label = "Codex"

    @property
    def model(self) -> str:
        return self.settings.codex_model

    @property
    def reasoning_effort(self) -> str:
        return self.settings.codex_reasoning_effort

    def build(
        self,
        role: str,
        *,
        workdir: Path,
        prompt: str,
        schema: Dict[str, Any],
        schema_path: Path,
        output_path: Path,
        images: Sequence[Path],
        engineering_lane: str = ENGINEERING_LANE_HARDWARE,
    ) -> AgentLaunch:
        settings = self.settings
        if role == "engineering":
            command = [
                str(settings.codex_bin),
                "--ask-for-approval", "never", "--sandbox", "danger-full-access",
                "--search",
                "exec", "--ephemeral", "--strict-config", "--json", "--color", "never",
                "-C", str(workdir), "-m", settings.codex_model,
                "-c", f"model_reasoning_effort={json.dumps(settings.codex_reasoning_effort)}",
                "-c", "project_doc_max_bytes=65536",
                # The Codex MCP client needs these two Keychain-backed bearer
                # values, but model-generated shell commands do not. Keep the
                # values in the parent only while allowing the configured
                # robot_lab and rl_orchestrator MCP servers to authenticate.
                "-c", (
                    'shell_environment_policy.exclude=['
                    '"HEXAPOD_LAB_TOKEN","HEXAPOD_ORCHESTRATOR_TOKEN"]'
                ),
            ]
            environment = engineering_environment(workdir, engineering_lane)
        else:
            command = [
                str(settings.codex_bin),
                "--ask-for-approval", "never",
                "exec", "--ephemeral", "--ignore-user-config",
                "--strict-config", "--skip-git-repo-check", "--ignore-rules",
                "--json", "--color", "never", "--sandbox", "read-only",
                "-C", str(workdir), "-m", settings.codex_model,
                "-c", f"model_reasoning_effort={json.dumps(settings.codex_reasoning_effort)}",
                "-c", "project_doc_max_bytes=0",
            ]
            command.extend(codex_no_tool_arguments())
            environment = base_environment(("CODEX_HOME",))
        for image in images:
            command.extend(["-i", str(image)])
        command.extend([
            "--output-schema", str(schema_path),
            "-o", str(output_path),
            "-",
        ])
        return AgentLaunch(
            command=command,
            stdin_payload=prompt.encode("utf-8"),
            environment=environment,
            cwd=None,
            prompt_text=prompt,
        )

    def event_blocks(
        self, event: Dict[str, Any], *, agent_messages_only: bool = False
    ) -> List[Tuple[str, str]]:
        item = event.get("item")
        if agent_messages_only and not (
            isinstance(item, dict) and item.get("type") == "agent_message"
        ):
            return []
        event_type = str(event.get("type") or "event")
        if isinstance(item, dict):
            item_type = str(item.get("type") or "")
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                labels = {
                    "agent_message": "Assistant",
                    "reasoning": "Assistant reasoning summary",
                    "error": "Error",
                }
                return [(
                    labels.get(item_type, item_type.replace("_", " ").title()),
                    text,
                )]
        error = event.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return [("Error", error["message"])]
        if event_type in {"error", "turn.failed"}:
            message = event.get("message")
            if isinstance(message, str) and message.strip():
                return [("Error", message)]
        return []


def codex_no_tool_arguments() -> List[str]:
    """Return the explicit strict-config shutdown for sealed-data Codex runs."""
    arguments = [
        "-c",
        'web_search="disabled"',
        "-c",
        "tools.web_search=false",
    ]
    for feature in (
        "shell_tool",
        "unified_exec",
        "unified_exec_zsh_fork",
        "code_mode_host",
        "multi_agent",
        "view_image",
        "apps",
        "plugins",
        "remote_plugin",
        "tool_suggest",
        "skill_search",
        "browser_use",
        "browser_use_full_cdp_access",
        "browser_use_external",
        "computer_use",
        "image_generation",
    ):
        arguments.extend(["--disable", feature])
    return arguments


class ClaudeProvider(AgentProvider):
    """Claude Code in print mode.

    Sealed lanes run with ``--safe-mode --tools ""``: the only tool the model
    is given is ``StructuredOutput``, and safe mode independently disables
    CLAUDE.md discovery, skills, plugins, hooks, and every MCP server.  The
    engineering lane keeps the normal tool set and attaches exactly the MCP
    servers named in the configured ``--mcp-config`` file.
    """

    name = "claude"
    label = "Claude"

    @property
    def model(self) -> str:
        return self.settings.claude_model

    @property
    def reasoning_effort(self) -> str:
        return self.settings.claude_effort

    def build(
        self,
        role: str,
        *,
        workdir: Path,
        prompt: str,
        schema: Dict[str, Any],
        schema_path: Path,
        output_path: Path,
        images: Sequence[Path],
        engineering_lane: str = ENGINEERING_LANE_HARDWARE,
    ) -> AgentLaunch:
        settings = self.settings
        command = [
            str(settings.claude_bin),
            "--print",
            "--model", settings.claude_model,
            "--effort", settings.claude_effort,
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--verbose",
            "--no-session-persistence",
            "--json-schema", json.dumps(schema, sort_keys=True),
        ]
        if role == "engineering":
            mcp_config = settings.claude_mcp_config
            if mcp_config is not None and not Path(mcp_config).is_file():
                raise AgentProviderError(
                    f"Claude MCP config is missing: {mcp_config}"
                )
            command.extend([
                "--permission-mode", "bypassPermissions",
                "--setting-sources", settings.claude_engineering_setting_sources,
                "--add-dir", str(workdir),
                # Only the servers this file names are reachable, whatever the
                # operator's own Claude configuration happens to contain.
                "--strict-mcp-config",
            ])
            if mcp_config is not None:
                command.extend(["--mcp-config", str(mcp_config)])
            if settings.claude_max_budget_usd > 0:
                command.extend([
                    "--max-budget-usd", f"{settings.claude_max_budget_usd:g}"
                ])
            environment = engineering_environment(
                workdir,
                engineering_lane,
                extra=self._engineering_environment_names(),
            )
            cwd: Optional[Path] = workdir
        else:
            command.extend([
                # Safe mode is what makes this lane sealed: no CLAUDE.md, no
                # skills, plugins, hooks, custom agents, or MCP servers. The
                # empty --tools set removes every built-in tool, leaving only
                # the StructuredOutput channel the schema needs.
                "--safe-mode",
                "--tools", "",
                "--strict-mcp-config",
                "--setting-sources", "",
                "--disable-slash-commands",
                "--permission-mode", "dontAsk",
                "--permission-prompts", "none",
            ])
            environment = base_environment(self._sealed_environment_names())
            cwd = workdir
        payload, prompt_text = self._user_message(
            prompt, images, settings.claude_max_attachment_bytes
        )
        return AgentLaunch(
            command=command,
            stdin_payload=payload,
            environment=environment,
            cwd=cwd,
            prompt_text=prompt_text,
        )

    @staticmethod
    def _sealed_environment_names() -> Tuple[str, ...]:
        # Credentials the CLI needs to authenticate itself, and nothing that
        # would let a sealed analysis reach a robot, queue, or hub.
        return (
            "CLAUDE_CONFIG_DIR",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_BASE_URL",
        )

    @classmethod
    def _engineering_environment_names(cls) -> Tuple[str, ...]:
        # BUILDVIZ_API_KEY joins the two Hexapod bearer values already allowed
        # by engineering_environment; Claude expands all three into MCP
        # headers via ${VAR} so no token is written to disk or into argv.
        return (*cls._sealed_environment_names(), "BUILDVIZ_API_KEY")

    @staticmethod
    def _user_message(
        prompt: str, images: Sequence[Path], max_attachment_bytes: int
    ) -> Tuple[bytes, str]:
        """Build the single stream-json user turn, with images inline.

        Claude Code has no ``-i`` flag; images travel as base64 content blocks
        on stdin.  The evidence manifest already caps attachments at 64 MB,
        which is larger than one request may carry, so the budget here is a
        second bound and any omission is stated in the prompt the model sees.
        """
        blocks: List[Dict[str, Any]] = []
        omitted: List[str] = []
        total = 0
        for path in images:
            media_type = IMAGE_MEDIA_TYPES.get(path.suffix.lower())
            try:
                size = path.stat().st_size
            except OSError:
                omitted.append(path.name)
                continue
            if media_type is None or total + size > max_attachment_bytes:
                omitted.append(path.name)
                continue
            blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                },
            })
            total += size
        text = prompt
        if omitted:
            text += (
                "\n\nAttachment note: these evidence images exceeded the model "
                "attachment budget and are NOT attached to this request: "
                + ", ".join(sorted(omitted))
                + ". Do not cite them as if you had seen them."
            )
        message = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": text}, *blocks],
            },
        }
        payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        return payload, text

    def materialize_output(self, run_dir: Path, output_path: Path) -> str:
        """Recover the structured answer from the streamed event capture."""
        events_path = run_dir / ".events.raw.jsonl"
        if not events_path.is_file():
            events_path = run_dir / "events.jsonl"
        if not events_path.is_file():
            return "Claude produced no event stream to read a result from"
        result_event: Optional[Dict[str, Any]] = None
        with events_path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict) and event.get("type") == "result":
                    result_event = event
        if result_event is None:
            return "Claude did not emit a terminal result event"
        if result_event.get("is_error"):
            subtype = str(result_event.get("subtype") or "error")
            detail = str(result_event.get("result") or "")[:500]
            return f"Claude reported {subtype}: {detail}".strip()
        structured = result_event.get("structured_output")
        if not isinstance(structured, dict):
            # A run that stopped early (budget, max turns, refusal) returns
            # prose in `result` and no structured output.
            text = result_event.get("result")
            if not isinstance(text, str):
                return "Claude returned no structured output"
            try:
                structured = json.loads(text)
            except json.JSONDecodeError:
                return "Claude returned no structured output"
            if not isinstance(structured, dict):
                return "Claude structured output is not a JSON object"
        payload = json.dumps(structured, ensure_ascii=False, sort_keys=True)
        output_path.write_text(payload, encoding="utf-8")
        output_path.chmod(0o600)
        return ""

    def transcript_reader(self) -> "ClaudeTranscriptReader":
        return ClaudeTranscriptReader()


class ClaudeTranscriptReader:
    """One ordered pass over a Claude ``stream-json`` capture.

    The schema answer arrives as a ``StructuredOutput`` tool call and is
    published separately as ``final.json``.  Suppressing that call means also
    suppressing the acknowledgement it provokes, which is only identifiable
    by the id recorded here as the stream is read.
    """

    def __init__(self) -> None:
        self._structured_output_ids: set = set()

    def event_blocks(
        self, event: Dict[str, Any], *, agent_messages_only: bool = False
    ) -> List[Tuple[str, str]]:
        kind = str(event.get("type") or "")
        message = event.get("message")
        blocks: List[Tuple[str, str]] = []
        if kind == "assistant" and isinstance(message, dict):
            for block in message.get("content") or []:
                if not isinstance(block, dict):
                    continue
                block_type = str(block.get("type") or "")
                if block_type == "text":
                    text = block.get("text")
                    if isinstance(text, str) and text.strip():
                        blocks.append(("Assistant", text))
                    continue
                if block_type == "tool_use" and block.get("name") == "StructuredOutput":
                    identifier = block.get("id")
                    if isinstance(identifier, str):
                        self._structured_output_ids.add(identifier)
                    continue
                if agent_messages_only:
                    continue
                if block_type == "thinking":
                    text = block.get("thinking")
                    if isinstance(text, str) and text.strip():
                        blocks.append(("Assistant reasoning summary", text))
                elif block_type == "tool_use":
                    blocks.append((
                        f"Tool use: {block.get('name') or 'tool'}",
                        json.dumps(
                            block.get("input"),
                            ensure_ascii=False,
                            indent=2,
                            sort_keys=True,
                        ),
                    ))
            return blocks
        if agent_messages_only:
            return []
        if kind == "user" and isinstance(message, dict):
            for block in message.get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                if block.get("tool_use_id") in self._structured_output_ids:
                    continue
                content = block.get("content")
                text = content if isinstance(content, str) else json.dumps(
                    content, ensure_ascii=False, sort_keys=True
                )
                if text.strip():
                    blocks.append(("Tool result", text))
            return blocks
        if kind == "result" and event.get("is_error"):
            subtype = str(event.get("subtype") or "error")
            detail = event.get("result")
            text = detail if isinstance(detail, str) and detail.strip() else subtype
            return [("Error", f"{subtype}: {text}")]
        if kind == "system" and event.get("subtype") == "error":
            detail = event.get("message")
            if isinstance(detail, str) and detail.strip():
                return [("Error", detail)]
        return []


PROVIDERS = {
    CodexProvider.name: CodexProvider,
    ClaudeProvider.name: ClaudeProvider,
}


def get_provider(settings: Any) -> AgentProvider:
    """Resolve the configured backend, refusing an unknown name outright."""
    name = str(getattr(settings, "agent_provider", CodexProvider.name) or "").strip().lower()
    try:
        return PROVIDERS[name](settings)
    except KeyError:
        raise AgentProviderError(
            f"Unknown HEXAPOD_AGENT_PROVIDER {name!r}; "
            f"expected one of {', '.join(sorted(PROVIDERS))}"
        ) from None
