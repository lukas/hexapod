"""Shared browser assets and page routes for robot, hub, and MuJoCo servers."""
from pathlib import Path

WEBUI_DIR = Path(__file__).resolve().parent / "webui"
PAGE_PATHS = ("/", "/index.html", "/debug", "/motors", "/setup", "/vision", "/demos",
              "/dance", "/rock", "/quad", "/rl", "/experiments", "/measure",
              "/calibrate", "/touchdown")
STATIC_FILES = {
    "/style.css": ("style.css", "text/css; charset=utf-8", "no-store"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8", "no-store"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml", "max-age=86400"),
}
