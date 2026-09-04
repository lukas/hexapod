from dataclasses import dataclass
from pathlib import Path
import os
import shlex
from typing import Optional


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
    max_artifact_bytes: int = 2 * 1024 * 1024 * 1024
    tag_audit_command: tuple = ()
    tag_layout_path: Optional[Path] = None
    tag_pose_template_path: Optional[Path] = None
    tag_floor_map_path: Optional[Path] = None
    tag_part_map_path: Optional[Path] = None
    max_tag_photo_bytes: int = 8 * 1024 * 1024
    max_tag_photos: int = 36

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
            max_artifact_bytes=int(os.getenv(
                "HEXAPOD_MAX_ARTIFACT_BYTES", str(2 * 1024 * 1024 * 1024)
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
            max_tag_photos=int(os.getenv("HEXAPOD_MAX_TAG_PHOTOS", "36")),
        )


def _optional_path(name: str) -> Optional[Path]:
    value = os.getenv(name, "").strip()
    return Path(value).expanduser().resolve() if value else None
