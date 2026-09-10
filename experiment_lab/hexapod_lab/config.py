from dataclasses import dataclass
from pathlib import Path
import json
import os
import shlex
from typing import Optional


DEFAULT_ROBOT_TELEMETRY_URL = "http://127.0.0.1:8898/api/telemetry"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_keys: str
    driver: str
    robot_command: tuple
    camera_input: str
    bind: str
    port: int
    public_base_url: str
    auto_worker: bool
    max_duration_seconds: int
    robot_command_shutdown_seconds: float = 30.0
    camera_ready_timeout_seconds: float = 10.0
    camera_stale_seconds: float = 5.0
    max_artifact_bytes: int = 2 * 1024 * 1024 * 1024
    max_experiment_artifacts: int = 256
    max_experiment_artifact_bytes: int = 4 * 1024 * 1024 * 1024
    tag_audit_command: tuple = ()
    tag_layout_path: Optional[Path] = None
    tag_pose_template_path: Optional[Path] = None
    tag_floor_map_path: Optional[Path] = None
    tag_part_map_path: Optional[Path] = None
    max_tag_photo_bytes: int = 8 * 1024 * 1024
    max_tag_photos: int = 36
    robot_status_url: str = "http://hexapod.local:8080/api/robot"
    robot_vision_url: str = "http://127.0.0.1:8898/api/vision/state"
    observation_camera_name: str = ""
    observation_camera_devices: tuple = ()
    # Read observation frames from the camera server rather than opening the
    # devices in this process. Empty keeps the direct-capture path.
    observation_vision_service_url: str = ""
    observation_vision_service_width: int = 1280
    robot_telemetry_url: str = DEFAULT_ROBOT_TELEMETRY_URL
    codex_automation: bool = False
    codex_bin: Path = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
    codex_workdir: Path = Path(".")
    codex_model: str = "gpt-5.6-sol"
    codex_reasoning_effort: str = "medium"
    codex_analysis_timeout_seconds: int = 2700
    codex_advance_timeout_seconds: int = 5400
    codex_poll_seconds: float = 2.0
    codex_evidence_settle_seconds: int = 60
    codex_evidence_deadline_seconds: int = 1800
    codex_max_evidence_snapshot_bytes: int = 512 * 1024 * 1024
    codex_max_attempts: int = 5
    codex_max_followups_per_analysis: int = 3
    codex_max_followup_depth: int = 4
    codex_max_followups_per_root: int = 20
    codex_transcript_max_capture_bytes: int = 64 * 1024 * 1024
    codex_transcript_max_event_lines: int = 100_000
    codex_transcript_max_human_bytes: int = 2 * 1024 * 1024
    codex_engineering: bool = False
    codex_engineering_workdir: Optional[Path] = None
    codex_offline_engineering_workdir: Optional[Path] = None
    codex_engineering_timeout_seconds: int = 7200
    codex_engineering_context_max_bytes: int = 256 * 1024
    codex_engineering_max_patch_bytes: int = 16 * 1024 * 1024
    codex_engineering_max_attempts: int = 3
    # Which agent CLI drives the analysis, advance, and engineering lanes.
    # "codex" keeps the historical behaviour; "claude" runs Claude Code.
    agent_provider: str = "codex"
    claude_bin: Path = Path("claude")
    claude_model: str = "claude-opus-5"
    claude_effort: str = "high"
    # Only the servers named here are reachable from the engineering lane;
    # the sealed lanes always run with no MCP servers at all.
    claude_mcp_config: Optional[Path] = None
    claude_engineering_setting_sources: str = "user,project,local"
    claude_max_budget_usd: float = 0.0
    claude_max_attachment_bytes: int = 20 * 1024 * 1024
    sso_secret_file: Optional[Path] = None
    sso_users: str = ""
    sso_cookie_domain: str = ""

    @property
    def agent_model(self) -> str:
        return (
            self.claude_model if self.agent_provider == "claude"
            else self.codex_model
        )

    @property
    def agent_reasoning_effort(self) -> str:
        return (
            self.claude_effort if self.agent_provider == "claude"
            else self.codex_reasoning_effort
        )

    @property
    def agent_label(self) -> str:
        return "Claude" if self.agent_provider == "claude" else "Codex"

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("HEXAPOD_DATA_DIR", "./lab-data")).expanduser().resolve()
        bind = os.getenv("HEXAPOD_BIND", "127.0.0.1")
        port = int(os.getenv("HEXAPOD_PORT", "8767"))
        command = tuple(shlex.split(os.getenv("HEXAPOD_ROBOT_COMMAND", "")))
        return cls(
            data_dir=data_dir,
            api_keys=os.getenv("HEXAPOD_API_KEYS", ""),
            driver=os.getenv("HEXAPOD_DRIVER", "simulated"),
            robot_command=command,
            camera_input=os.getenv("HEXAPOD_CAMERA_INPUT", ""),
            bind=bind,
            port=port,
            public_base_url=os.getenv("HEXAPOD_PUBLIC_BASE_URL", "").rstrip("/"),
            auto_worker=os.getenv("HEXAPOD_AUTO_WORKER", "true").lower() in {"1", "true", "yes"},
            max_duration_seconds=int(os.getenv("HEXAPOD_MAX_DURATION_SECONDS", "900")),
            sso_secret_file=_optional_path("HEXAPOD_SSO_SECRET_FILE"),
            sso_users=os.getenv("HEXAPOD_SSO_USERS", ""),
            sso_cookie_domain=os.getenv("HEXAPOD_SSO_COOKIE_DOMAIN", ""),
            robot_command_shutdown_seconds=float(os.getenv(
                "HEXAPOD_ROBOT_COMMAND_SHUTDOWN_SECONDS", "30"
            )),
            camera_ready_timeout_seconds=float(os.getenv(
                "HEXAPOD_CAMERA_READY_TIMEOUT_SECONDS", "10"
            )),
            camera_stale_seconds=float(os.getenv(
                "HEXAPOD_CAMERA_STALE_SECONDS", "5"
            )),
            max_artifact_bytes=int(os.getenv(
                "HEXAPOD_MAX_ARTIFACT_BYTES", str(2 * 1024 * 1024 * 1024)
            )),
            max_experiment_artifacts=int(os.getenv(
                "HEXAPOD_MAX_EXPERIMENT_ARTIFACTS", "256"
            )),
            max_experiment_artifact_bytes=int(os.getenv(
                "HEXAPOD_MAX_EXPERIMENT_ARTIFACT_BYTES",
                str(4 * 1024 * 1024 * 1024),
            )),
            tag_audit_command=tuple(shlex.split(os.getenv(
                "HEXAPOD_TAG_AUDIT_COMMAND", ""
            ))),
            tag_layout_path=_optional_path("HEXAPOD_TAG_LAYOUT"),
            tag_pose_template_path=_optional_path("HEXAPOD_TAG_POSE_TEMPLATE"),
            tag_floor_map_path=_optional_path("HEXAPOD_TAG_FLOOR_MAP"),
            tag_part_map_path=_optional_path("HEXAPOD_TAG_PART_MAP"),
            max_tag_photo_bytes=int(os.getenv(
                "HEXAPOD_MAX_TAG_PHOTO_BYTES", str(8 * 1024 * 1024)
            )),
            robot_status_url=os.getenv("HEXAPOD_ROBOT_STATUS_URL", "http://hexapod.local:8080/api/robot"),
            robot_vision_url=os.getenv("HEXAPOD_ROBOT_VISION_URL", "http://127.0.0.1:8898/api/vision/state"),
            observation_camera_name=os.getenv("HEXAPOD_OBSERVATION_CAMERA_NAME", "").strip(),
            observation_camera_devices=_camera_devices(),
            observation_vision_service_url=os.getenv(
                "HEXAPOD_OBSERVATION_VISION_SERVICE_URL", ""
            ).strip(),
            observation_vision_service_width=int(
                os.getenv("HEXAPOD_OBSERVATION_VISION_SERVICE_WIDTH", "1280")
            ),
            robot_telemetry_url=os.getenv(
                "HEXAPOD_ROBOT_TELEMETRY_URL",
                DEFAULT_ROBOT_TELEMETRY_URL,
            ),
            max_tag_photos=int(os.getenv("HEXAPOD_MAX_TAG_PHOTOS", "36")),
            codex_automation=_env_bool("HEXAPOD_CODEX_AUTOMATION", False),
            codex_bin=Path(os.getenv(
                "HEXAPOD_CODEX_BIN",
                "/Applications/ChatGPT.app/Contents/Resources/codex",
            )).expanduser(),
            codex_workdir=Path(os.getenv(
                "HEXAPOD_CODEX_WORKDIR", str(Path.cwd())
            )).expanduser().resolve(),
            codex_model=os.getenv("HEXAPOD_CODEX_MODEL", "gpt-5.6-sol"),
            codex_reasoning_effort=os.getenv(
                "HEXAPOD_CODEX_REASONING_EFFORT", "medium"
            ),
            codex_analysis_timeout_seconds=int(os.getenv(
                "HEXAPOD_CODEX_ANALYSIS_TIMEOUT_SECONDS", "2700"
            )),
            codex_advance_timeout_seconds=int(os.getenv(
                "HEXAPOD_CODEX_ADVANCE_TIMEOUT_SECONDS", "5400"
            )),
            codex_poll_seconds=float(os.getenv("HEXAPOD_CODEX_POLL_SECONDS", "2")),
            codex_evidence_settle_seconds=int(os.getenv(
                "HEXAPOD_CODEX_EVIDENCE_SETTLE_SECONDS", "60"
            )),
            codex_evidence_deadline_seconds=int(os.getenv(
                "HEXAPOD_CODEX_EVIDENCE_DEADLINE_SECONDS", "1800"
            )),
            codex_max_evidence_snapshot_bytes=int(os.getenv(
                "HEXAPOD_CODEX_MAX_EVIDENCE_SNAPSHOT_BYTES",
                str(512 * 1024 * 1024),
            )),
            codex_max_attempts=int(os.getenv("HEXAPOD_CODEX_MAX_ATTEMPTS", "5")),
            codex_max_followups_per_analysis=int(os.getenv(
                "HEXAPOD_CODEX_MAX_FOLLOWUPS_PER_ANALYSIS", "3"
            )),
            codex_max_followup_depth=int(os.getenv(
                "HEXAPOD_CODEX_MAX_FOLLOWUP_DEPTH", "4"
            )),
            codex_max_followups_per_root=int(os.getenv(
                "HEXAPOD_CODEX_MAX_FOLLOWUPS_PER_ROOT", "20"
            )),
            codex_transcript_max_capture_bytes=int(os.getenv(
                "HEXAPOD_CODEX_TRANSCRIPT_MAX_CAPTURE_BYTES",
                str(64 * 1024 * 1024),
            )),
            codex_transcript_max_event_lines=int(os.getenv(
                "HEXAPOD_CODEX_TRANSCRIPT_MAX_EVENT_LINES", "100000"
            )),
            codex_transcript_max_human_bytes=int(os.getenv(
                "HEXAPOD_CODEX_TRANSCRIPT_MAX_HUMAN_BYTES",
                str(2 * 1024 * 1024),
            )),
            codex_engineering=_env_bool("HEXAPOD_CODEX_ENGINEERING", False),
            codex_engineering_workdir=_optional_path(
                "HEXAPOD_CODEX_ENGINEERING_WORKDIR"
            ),
            codex_offline_engineering_workdir=_optional_path(
                "HEXAPOD_CODEX_OFFLINE_ENGINEERING_WORKDIR"
            ),
            codex_engineering_timeout_seconds=int(os.getenv(
                "HEXAPOD_CODEX_ENGINEERING_TIMEOUT_SECONDS", "7200"
            )),
            codex_engineering_context_max_bytes=int(os.getenv(
                "HEXAPOD_CODEX_ENGINEERING_CONTEXT_MAX_BYTES", str(256 * 1024)
            )),
            codex_engineering_max_patch_bytes=int(os.getenv(
                "HEXAPOD_CODEX_ENGINEERING_MAX_PATCH_BYTES", str(16 * 1024 * 1024)
            )),
            codex_engineering_max_attempts=int(os.getenv(
                "HEXAPOD_CODEX_ENGINEERING_MAX_ATTEMPTS", "3"
            )),
            agent_provider=_agent_provider(),
            claude_bin=Path(os.getenv("HEXAPOD_CLAUDE_BIN", "claude")).expanduser(),
            claude_model=os.getenv("HEXAPOD_CLAUDE_MODEL", "claude-opus-5"),
            claude_effort=_claude_effort(),
            claude_mcp_config=_optional_path("HEXAPOD_CLAUDE_MCP_CONFIG"),
            claude_engineering_setting_sources=os.getenv(
                "HEXAPOD_CLAUDE_ENGINEERING_SETTING_SOURCES", "user,project,local"
            ),
            claude_max_budget_usd=float(os.getenv(
                "HEXAPOD_CLAUDE_MAX_BUDGET_USD", "0"
            )),
            claude_max_attachment_bytes=int(os.getenv(
                "HEXAPOD_CLAUDE_MAX_ATTACHMENT_BYTES", str(20 * 1024 * 1024)
            )),
        )


def _camera_devices() -> tuple:
    value = json.loads(os.getenv("HEXAPOD_OBSERVATION_CAMERAS", "[]"))
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("HEXAPOD_OBSERVATION_CAMERAS must be a JSON list of camera definitions")
    return tuple(value)
AGENT_PROVIDERS = ("codex", "claude")
CLAUDE_EFFORTS = ("low", "medium", "high", "xhigh", "max")


def _agent_provider() -> str:
    value = os.getenv("HEXAPOD_AGENT_PROVIDER", "codex").strip().lower()
    if value not in AGENT_PROVIDERS:
        raise ValueError(
            "HEXAPOD_AGENT_PROVIDER must be one of " + ", ".join(AGENT_PROVIDERS)
        )
    return value


def _claude_effort() -> str:
    """Claude names effort levels differently from Codex; do not guess.

    A misspelled level would otherwise silently downgrade every analysis.
    """
    value = os.getenv("HEXAPOD_CLAUDE_EFFORT", "high").strip().lower()
    if value not in CLAUDE_EFFORTS:
        raise ValueError(
            "HEXAPOD_CLAUDE_EFFORT must be one of " + ", ".join(CLAUDE_EFFORTS)
        )
    return value


def _optional_path(name: str) -> Optional[Path]:
    value = os.getenv(name, "").strip()
    return Path(value).expanduser().resolve() if value else None


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
