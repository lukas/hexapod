#!/usr/bin/env python
"""Stage Robot Lab v2 footage for the GPU vision lab pod.

Reads ~/Library/Application Support/Hexapod Lab/v2 (runs/, lab2.sqlite3,
review-*/index.csv) and writes to OUT (default ~/hexapod-vision-data):

  clips/<run>/<stem>.mp4      constant-fps H.264 (<=720p) re-encodes of every
                              mp4/mkv under runs/ (mkv streams have no duration
                              and one claims 1000 fps; VLM frame samplers need CFR)
  manifest.jsonl              one row per clip: run, plan title/why, status,
                              review class, camera sidecar, incumbent 'seen' text
  frames/<run>__<proto>/*.jpg vision_frames downscaled to max side 640
  labels.jsonl                one row per frame with IMU roll/pitch + 18 joints
                              (from vision.jsonl state.imu / state.motor_feedback)

Run with the repo venv (needs cv2): ~/hexapod/.venv/bin/python prep_upload_data.py
"""
from __future__ import annotations

import csv
import glob
import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

AS = Path.home() / "Library/Application Support/Hexapod Lab/v2"
RUNS = AS / "runs"
OUT = Path(os.environ.get("VISION_OUT", Path.home() / "hexapod-vision-data"))
MAX_SIDE = 640


def ffprobe(path: Path) -> dict:
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
           "-show_entries", "stream=width,height,avg_frame_rate,r_frame_rate,nb_read_frames:format=duration",
           "-of", "json", str(path)]
    d = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout or "{}")
    s = (d.get("streams") or [{}])[0]
    dur = float((d.get("format") or {}).get("duration") or 0)
    n = int(s.get("nb_read_frames") or 0)

    def rate(x):
        try:
            a, b = x.split("/")
            return float(a) / float(b) if float(b) else 0.0
        except Exception:
            return 0.0
    fps = rate(s.get("avg_frame_rate", "0/1"))
    if not (0.2 <= fps <= 60) and dur > 0 and n > 0:
        fps = n / dur
    if not (0.2 <= fps <= 60):
        fps = rate(s.get("r_frame_rate", "0/1"))
    if not (0.2 <= fps <= 60):
        fps = 4.0
    return {"width": s.get("width"), "height": s.get("height"), "fps": round(fps, 3),
            "frames": n, "duration_s": round(dur if dur else (n / fps if fps else 0), 3)}


def encode_clip(job):
    src, dst, fps = job
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0:
        return src, dst, "cached"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src),
           "-vf", f"fps={fps},scale='min(1280,iw)':-2", "-fps_mode", "cfr",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", "-an", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return src, dst, "ok" if r.returncode == 0 else f"ERR {r.stderr[-300:]}"


def build_manifest() -> list[dict]:
    db = sqlite3.connect(f"file:{AS / 'lab2.sqlite3'}?mode=ro", uri=True)
    runs = {}
    for row in db.execute(
        "select r.id, r.status, r.started_at, r.summary_json, p.title, p.why, p.protocol, p.intent, p.source, r.robot "
        "from runs r join plans p on p.id=r.plan_id"):
        rid, status, started, summ, title, why, proto, intent, source, robot = row
        seen = None
        try:
            seen = (json.loads(summ) if summ else {}).get("seen")
        except Exception:
            pass
        runs[rid] = dict(run=rid, status=status, started_at=started, title=title, why=why,
                         protocol=proto, intent=intent, plan_source=source, robot=robot, seen=seen)
    learnings = {}
    for rid, text in db.execute("select run_id, text from learnings where run_id is not null"):
        learnings.setdefault(rid, []).append(text)
    review = {}
    for idx in sorted(AS.glob("review-*/index.csv")):
        with open(idx) as f:
            for row in csv.DictReader(f):
                review[row["run"]] = {k: row[k] for k in ("family", "cls", "error", "joint", "tilt_max", "tilt_rms",
                                                          "speed_mm_s", "heading_change_deg", "policy") if k in row}
    clips = []
    for src in sorted(list(RUNS.glob("**/*.mp4")) + list(RUNS.glob("**/*.mkv"))):
        rel = src.relative_to(RUNS)
        rid = rel.parts[0]
        side = src.with_suffix(".json")
        if src.stem.endswith(("_cam1", "_cam2")):
            side = src.with_name(src.stem[:-5] + ".json")
        sidecar = None
        if side.exists():
            try:
                j = json.load(open(side))
                sidecar = {k: j.get(k) for k in ("policy", "label", "stop_reason", "lost_why", "seconds", "path_mm",
                                                 "speed_mm_s", "heading_change_deg", "camera", "fixes") if k in j}
            except Exception:
                sidecar = {"error": "unreadable"}
        meta = ffprobe(src)
        stem = "__".join(rel.parts[1:])  # keep nested dirs unique (several runs have attempt*/camera_raw.mp4)
        clips.append(dict(clip=f"{rid}/{Path(stem).stem}.mp4", source=str(rel), **meta,
                          **runs.get(rid, {"run": rid}), review=review.get(rid),
                          learnings=learnings.get(rid, [])[:6], sidecar=sidecar))
    return clips


def downscale(job):
    import cv2
    src, dst = job
    if dst.exists():
        return True
    im = cv2.imread(str(src))
    if im is None:
        return False
    h, w = im.shape[:2]
    s = MAX_SIDE / max(h, w)
    if s < 1:
        im = cv2.resize(im, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst), im, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return True


def build_labels() -> tuple[list[dict], list[tuple[Path, Path]]]:
    rows, jobs = [], []
    for vj in sorted(RUNS.glob("*/*/vision.jsonl")):
        rid = vj.parts[-3]
        proto_dir = vj.parent
        proto = proto_dir.name
        key = f"{rid}__{proto}"
        for line in open(vj):
            try:
                r = json.loads(line)
            except Exception:
                continue
            img = r.get("image")
            if not img:
                continue
            st = r.get("state") or {}
            imu = st.get("imu") or {}
            mf = st.get("motor_feedback") or {}
            joints = mf.get("joints") or []
            if imu.get("body_roll_deg") is None or len(joints) != 18:
                continue
            src = proto_dir / img
            dst = OUT / "frames" / key / Path(img).name
            jobs.append((src, dst))
            rows.append(dict(frame=f"frames/{key}/{Path(img).name}", run=rid, protocol=proto,
                             capture_unix=r.get("capture_unix"), sample_age_s=mf.get("sample_age_s"),
                             roll=imu["body_roll_deg"], pitch=imu["body_pitch_deg"], gyro=imu.get("gyro_dps"),
                             joints={j["name"]: j["degrees"] for j in joints}))
    return rows, jobs


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    clips_only = "--clips-only" in sys.argv
    print("building manifest…", flush=True)
    clips = build_manifest()
    with open(OUT / "manifest.jsonl", "w") as f:
        for c in clips:
            f.write(json.dumps(c) + "\n")
    print(f"{len(clips)} clips; encoding…", flush=True)
    jobs = [(RUNS / c["source"], OUT / "clips" / c["clip"], c["fps"]) for c in clips]
    bad = 0
    with ProcessPoolExecutor(8) as ex:
        for i, fut in enumerate(as_completed([ex.submit(encode_clip, j) for j in jobs]), 1):
            src, dst, status = fut.result()
            if status.startswith("ERR"):
                bad += 1
                print("  encode failed:", src, status, flush=True)
            if i % 50 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)
    print(f"clips done, {bad} failures", flush=True)
    if clips_only:
        return

    print("building frame labels…", flush=True)
    rows, fjobs = build_labels()
    with open(OUT / "labels.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"{len(rows)} labeled frames; downscaling…", flush=True)
    miss = 0
    with ProcessPoolExecutor(16) as ex:
        for i, ok in enumerate(ex.map(downscale, fjobs, chunksize=64), 1):
            miss += not ok
            if i % 5000 == 0:
                print(f"  {i}/{len(fjobs)}", flush=True)
    print(f"frames done, {miss} unreadable", flush=True)


if __name__ == "__main__":
    sys.exit(main())
