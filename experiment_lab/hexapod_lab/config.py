from dataclasses import dataclass
from pathlib import Path
import os
import shlex


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
        )
