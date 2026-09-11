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


def crop_filter(crop: str) -> str:
    """'x,y,w,h' fractions -> an ffmpeg crop filter; '' for the whole frame."""
    try:
        x, y, w, h = [float(v) for v in crop.split(",")]
        if not (0 < w <= 1 and 0 < h <= 1):
            return ""
        return f"crop=iw*{w:.3f}:ih*{h:.3f}:iw*{x:.3f}:ih*{y:.3f},"
    except (ValueError, AttributeError):
        return ""


def _scaled_jpeg(path: Path, width: int = 768, crop: str = "") -> bytes:
    try:
        proc = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-vf", f"{crop_filter(crop)}scale={width}:-1",
                               "-f", "image2", "-vcodec", "mjpeg", "-q:v", "5", "pipe:1"],
                              check=True, capture_output=True, timeout=20)
        return proc.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return path.read_bytes()


def describe(frames: List[Path], context: str, *, model: str, api_key: str,
             post: Optional[Callable] = None, crop: str = "") -> tuple[str, float]:
    """One vision call. Returns (text, approx_cost_usd)."""
    if not frames:
        return "", 0.0
    content = []
    for i, f in enumerate(frames):
        content.append({"type": "text", "text": f"frame {i + 1} of {len(frames)}"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.b64encode(_scaled_jpeg(f, crop=crop)).decode()}})
    content.append({"type": "text", "text": (
        "These are wide-camera frames from one run on a cheap 18-servo hexapod, in time order; the last four are "
        "the final seconds, cropped to the robot. The robot's motions are small (a foot lift is 20 mm); compare leg "
        "positions between frames carefully before saying nothing moved. Context from the lab:\n" + context.strip()[:2000] +
        "\n\nIn under 120 words: describe what the robot did over the run as a timeline, then anything that looks "
        "wrong (a leg folded under the body, the chassis tilted or propped, a foot slipping, a cable snag, a person "
        "in frame, the robot not where it started). Be concrete about which leg or side. If nothing moved, say so.")})
    body = {"model": model, "max_tokens": 1200, "messages": [{"role": "user", "content": content}]}
    post = post or _post_messages
    doc = post(body, api_key)
    text = " ".join(part.get("text", "") for part in doc.get("content", []) if part.get("type") == "text").strip()
    usage = doc.get("usage", {})
    cost = usage.get("input_tokens", 0) * 3e-6 + usage.get("output_tokens", 0) * 15e-6
    return text, cost


def _post_messages(body: dict, api_key: str, timeout: float = 90.0) -> dict:
    req = Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                  headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                           "content-type": "application/json"}, method="POST")
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


LOOK_QUESTION = (
    "This is the wide camera over a cheap 18-servo hexapod that lives on the floor of a home lab. "
    "The first image is the whole frame, the second is the part of it where the robot usually sits. "
    "Can you see the robot, and does it look ready to move right now? Use your judgement: a person, "
    "hands or tools near it, a leg detached, propped or missing, the robot lifted, tipped, tangled or "
    "out of view all mean no. Answer YES or NO on the first line, then one short sentence on what you see."
)


def ready_to_move(settings: Settings, *, post: Optional[Callable] = None, fetch: Optional[Callable] = None,
                  budget_s: Optional[float] = None) -> tuple[bool, str, float]:
    """One look at the wide camera before the robot moves.

    Returns (ready, what the eyes said, cost). Anything that stops the look
    from happening (no camera frame, no key, the model not answering in
    time) is a no: if we cannot see the robot we do not move it. The frame
    is kept at <data_dir>/look.jpg.
    """
    budget = float(budget_s or settings.health_budget_s)
    t0 = time.monotonic()
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return False, "no ANTHROPIC_API_KEY for the eyes", 0.0
    try:
        data = (fetch or WideCapture._fetch)(settings.wide_frame_url)
    except Exception as exc:  # noqa: BLE001
        return False, f"no camera frame ({type(exc).__name__}: {exc})"[:200], 0.0
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    frame = settings.data_dir / "look.jpg"
    frame.write_bytes(data)
    content = []
    for label, jpeg in (("whole frame", _scaled_jpeg(frame, width=1024)),
                        ("robot area", _scaled_jpeg(frame, width=768, crop=settings.wide_crop))):
        content.append({"type": "text", "text": label})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.b64encode(jpeg).decode()}})
    content.append({"type": "text", "text": LOOK_QUESTION})
    # The model reasons before answering and that counts against max_tokens;
    # 120 left "NO" and nothing else on 2026-09-11. Leave room for the sentence.
    body = {"model": settings.eyes_model, "max_tokens": 600, "messages": [{"role": "user", "content": content}]}
    remaining = max(3.0, budget - (time.monotonic() - t0))
    try:
        doc = (post or _post_messages)(body, api_key, timeout=remaining)
    except Exception as exc:  # noqa: BLE001
        return False, f"eyes did not answer ({type(exc).__name__}: {exc})"[:200], 0.0
    text = " ".join(part.get("text", "") for part in doc.get("content", []) if part.get("type") == "text").strip()
    usage = doc.get("usage", {})
    cost = usage.get("input_tokens", 0) * 3e-6 + usage.get("output_tokens", 0) * 15e-6
    first = text.split("\n", 1)[0].strip().upper()
    return first.startswith("YES"), text or "(no answer)", cost


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
        text, cost = describe(sample_frames(frames), context, model=settings.eyes_model, api_key=api_key, post=post,
                              crop=settings.wide_crop)
    except Exception as exc:  # noqa: BLE001
        store.update_run_summary(run_id, seen=f"(eyes failed: {type(exc).__name__}: {exc})"[:300], wide_frames=len(frames))
        log(f"eyes failed: {exc}")
        return ""
    if cost:
        store.add_spend("eyes", cost, run_id)
    store.update_run_summary(run_id, seen=text, wide_frames=len(frames), video="wide.mp4" if video else None)
    log(f"seen: {text[:160]}")
    return text
