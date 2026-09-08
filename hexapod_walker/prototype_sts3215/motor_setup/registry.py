"""Motor assignments are local robot data, never a deployment asset."""
from pathlib import Path

REGISTRY_PATH = Path.home() / ".local" / "share" / "hexapod" / "motor_setup_registry.json"
