"""Burn telemetry text into rendered frames (shared by the video tools)."""
from __future__ import annotations

import numpy as np


def _annotate_frame(frame: np.ndarray, lines: list[str]) -> np.ndarray:
    """Burn telemetry text into the top-left of a rendered frame."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return frame
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    y = 6
    for line in lines:
        # Cheap outline so text survives light backgrounds.
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            draw.text((8 + dx, y + dy), line, fill=(0, 0, 0))
        draw.text((8, y), line, fill=(255, 255, 80))
        y += 14
    return np.asarray(img)
