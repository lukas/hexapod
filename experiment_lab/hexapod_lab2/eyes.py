"""Eyes: record the wide camera through every run and look at the footage.

The runner's own frame dump is the floor-tag camera, which frames whole-body
work as legs at the top edge. This module records the wide camera at 1 Hz
for the length of a run into runs/<id>/wide/, assembles it into an mp4 the
operator can click, samples twelve frames (eight spread evenly, the last
four dense, because trips happen at the end), and asks a vision model for a
timeline and anything abnormal. The text goes into the run summary as
`seen`, into the planner's digest, and onto the dashboard card.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional
from urllib.request import Request, urlopen

from .config import Settings
from .store import Store

FFMPEG = "/opt/homebrew/bin/ffmpeg" if Path("/opt/homebrew/bin/ffmpeg").exists() else "ffmpeg"


class WideCapture:
    """Grab one wide-camera JPEG per second while a run is in progress."""

    def __init__(self, frame_url: str, out_dir: Path, *, hz: float = 1.0, fetch: Optional[Callable] = None):
        self.frame_url, self.out_dir, self.period = frame_url, out_dir, 1.0 / hz
        self.fetch = fetch or self._fetch
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.count = 0

    @staticmethod
    def _fetch(url: str) -> bytes:
        with urlopen(url, timeout=3) as resp:
            return resp.read()

    def _loop(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                data = self.fetch(self.frame_url)
                (self.out_dir / f"{self.count:05d}.jpg").write_bytes(data)
                self.count += 1
            except Exception:  # noqa: BLE001 - a missed frame is just a gap
                pass
            self._stop.wait(max(0.0, self.period - (time.monotonic() - started)))

    def __enter__(self) -> "WideCapture":
        self._thread = threading.Thread(target=self._loop, name="wide-capture", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)


def sample_frames(frames: List[Path], n: int = 12, dense_tail: int = 4) -> List[Path]:
    """Eight spread across the run plus the last four; fewer if there are fewer."""
    frames = sorted(frames)
    if len(frames) <= n:
        return frames
    tail = frames[-dense_tail:]
    head_pool = frames[:-dense_tail]
    spread = n - dense_tail
    step = (len(head_pool) - 1) / max(1, spread - 1)
    head = [head_pool[round(i * step)] for i in range(spread)]
    return head + tail


def make_video(wide_dir: Path, out: Path, *, fps: int = 4) -> Optional[Path]:
    frames = sorted(wide_dir.glob("*.jpg"))
    if len(frames) < 2:
        return None
    cmd = [FFMPEG, "-v", "error", "-y", "-framerate", str(fps), "-pattern_type", "glob",
           "-i", str(wide_dir / "*.jpg"), "-vf", "scale=960:-2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    return out


def _scaled_jpeg(path: Path, width: int = 640) -> bytes:
    try:
        proc = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-vf", f"scale={width}:-1",
                               "-f", "image2", "-vcodec", "mjpeg", "-q:v", "6", "pipe:1"],
                              check=True, capture_output=True, timeout=20)
        return proc.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return path.read_bytes()


def describe(frames: List[Path], context: str, *, model: str, api_key: str,
             post: Optional[Callable] = None) -> tuple[str, float]:
    """One vision call. Returns (text, approx_cost_usd)."""
    if not frames:
        return "", 0.0
    content = []
    for i, f in enumerate(frames):
        content.append({"type": "text", "text": f"frame {i + 1} of {len(frames)}"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.b64encode(_scaled_jpeg(f)).decode()}})
    content.append({"type": "text", "text": (
        "These are wide-camera frames from one run on a cheap 18-servo hexapod, in time order; the last four are "
        "the final seconds. Context from the lab:\n" + context.strip()[:2000] +
        "\n\nIn under 120 words: describe what the robot did over the run as a timeline, then anything that looks "
        "wrong (a leg folded under the body, the chassis tilted or propped, a foot slipping, a cable snag, a person "
        "in frame, the robot not where it started). Be concrete about which leg or side. If nothing moved, say so.")})
    body = {"model": model, "max_tokens": 300, "messages": [{"role": "user", "content": content}]}
    post = post or _post_messages
    doc = post(body, api_key)
    text = " ".join(part.get("text", "") for part in doc.get("content", []) if part.get("type") == "text").strip()
    usage = doc.get("usage", {})
    cost = usage.get("input_tokens", 0) * 3e-6 + usage.get("output_tokens", 0) * 15e-6
    return text, cost


def _post_messages(body: dict, api_key: str) -> dict:
    req = Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                  headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                           "content-type": "application/json"}, method="POST")
    with urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode())


def see_run(settings: Settings, store: Store, run_id: str, context: str, *, log=print,
            post: Optional[Callable] = None) -> str:
    """Video + description for a finished run. Never raises into the loop."""
    run = store.run(run_id)
    if not run or not run.get("run_dir"):
        return ""
    run_dir = Path(run["run_dir"])
    wide = run_dir / "wide"
    frames = sorted(wide.glob("*.jpg")) if wide.exists() else []
    if not frames:
        return ""
    video = make_video(wide, run_dir / "wide.mp4")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        store.update_run_summary(run_id, seen="(no ANTHROPIC_API_KEY for the eyes)", wide_frames=len(frames))
        return ""
    try:
        text, cost = describe(sample_frames(frames), context, model=settings.eyes_model, api_key=api_key, post=post)
    except Exception as exc:  # noqa: BLE001
        store.update_run_summary(run_id, seen=f"(eyes failed: {type(exc).__name__}: {exc})"[:300], wide_frames=len(frames))
        log(f"eyes failed: {exc}")
        return ""
    if cost:
        store.add_spend("eyes", cost, run_id)
    store.update_run_summary(run_id, seen=text, wide_frames=len(frames), video="wide.mp4" if video else None)
    log(f"seen: {text[:160]}")
    return text
