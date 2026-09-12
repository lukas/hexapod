#!/usr/bin/env python3
"""E3: dense safety timeline over the real-time (>=10 fps) clips.

Slides an 8 s window (4 s stride) over each clip, sends 16 frames per window
to the VLM and asks only about safety-relevant events inside that window.
Merges per-window events into a per-clip timeline in
/data/results/e3_<model>.jsonl (with per-window latency), and prints
windows/s so we know how far from live this is.
"""
from __future__ import annotations

import argparse, base64, io, json, time
from pathlib import Path

import av
import numpy as np
from PIL import Image
from openai import OpenAI

EVENTS = ["tip_or_roll", "fall_or_collapse", "leg_folded_under_body", "foot_slip", "cable_snag",
          "operator_hand_or_intervention", "robot_at_frame_edge_or_out", "stuck_or_stalled_mid_motion",
          "violent_oscillation_or_jitter", "leg_collision_or_tangle", "none"]
STATES = ["standing_stable", "walking", "turning", "standing_up", "lowering_or_sitting", "on_belly_or_collapsed",
          "tilted_or_propped", "being_handled", "not_visible", "other"]
SCHEMA = {"type": "object", "properties": {
    "robot_state_end": {"type": "string", "enum": STATES},
    "risk": {"type": "string", "enum": ["none", "watch", "intervene_now"]},
    "events": {"type": "array", "items": {"type": "object", "properties": {
        "t_s": {"type": "number"}, "type": {"type": "string", "enum": EVENTS},
        "severity": {"type": "string", "enum": ["low", "medium", "high"]}, "note": {"type": "string"}},
        "required": ["t_s", "type", "severity", "note"]}},
    "note": {"type": "string"}}, "required": ["robot_state_end", "risk", "events", "note"]}
SYSTEM = ("You are a safety spotter watching a small six-legged robot (hexapod, about 40 cm across; each leg is three "
          "servo boxes with small square AprilTags glued on and a thin stick foot; red/blue parts in colour cameras, a "
          "cluster of tagged boxes in the grayscale infrared wide camera) on a floor with loose AprilTag markers. Other "
          "robot chassis may sit nearby; only the six-legged tagged robot counts. A human operator may stand by. You first "
          "get two reference images of the robot, then consecutive frames from one short window of video with timestamps. "
          "Report only what is visible in these frames. Answer with the JSON object requested.")
REFS = [("/data/ref/robot_colour.jpg", "Reference 1: the robot seen by a colour camera (low, splayed pose)."),
        ("/data/ref/robot_ir_wide.jpg", "Reference 2: the robot seen by the grayscale wide camera, standing.")]


def ref_content():
    out = []
    for path, text in REFS:
        out += [{"type": "text", "text": text}, {"type": "image_url", "image_url": {"url": b64(Image.open(path).convert("RGB"))}}]
    return out
PROMPT = ("For this window: what state is the robot in at the end, would a human spotter need to intervene (risk), and "
          "list each safety-relevant event with the timestamp where it first appears: body tip/roll, fall or collapse, "
          "a leg folded under the body, foot slip, cable snag, operator hand touching the robot, robot at the frame edge, "
          "a stall mid-motion, violent oscillation, or legs colliding/tangling. Empty events list if nothing is wrong. "
          "One short note.")


def b64(im):
    b = io.BytesIO(); im.save(b, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def decode(path, max_side):
    out = []
    with av.open(str(path)) as c:
        s = c.streams.video[0]
        for f in c.decode(s):
            t = float(f.pts * s.time_base) if f.pts is not None else len(out) / float(s.average_rate or 10)
            im = f.to_image(); sc = max_side / max(im.size)
            if sc < 1:
                im = im.resize((round(im.width * sc), round(im.height * sc)), Image.BILINEAR)
            out.append((t, im))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3vl-32b"); ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--window", type=float, default=8.0); ap.add_argument("--stride", type=float, default=4.0)
    ap.add_argument("--per-window", type=int, default=16); ap.add_argument("--max-side", type=int, default=640)
    ap.add_argument("--min-fps", type=float, default=9.0); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    client = OpenAI(base_url=f"http://127.0.0.1:{a.port}/v1", api_key="x", timeout=600)
    man = [json.loads(l) for l in open("/data/manifest.jsonl")]
    man = [m for m in man if m["fps"] >= a.min_fps and (not a.only or a.only in m["clip"])]
    man.sort(key=lambda m: m["duration_s"])
    if a.limit:
        man = man[: a.limit]
    out_path = Path(f"/data/results/e3_{a.model}.jsonl")
    done = {json.loads(l)["clip"] for l in open(out_path)} if out_path.exists() else set()
    fo = open(out_path, "a")
    for k, m in enumerate(man):
        if m["clip"] in done:
            continue
        frames = decode(Path("/data/clips") / m["clip"], a.max_side)
        if not frames:
            continue
        T = frames[-1][0]; windows = []; t0 = time.time()
        starts = np.arange(0, max(T - a.window, 0) + 1e-6, a.stride).tolist() or [0.0]
        for ws in starts:
            sel = [(t, im) for t, im in frames if ws <= t < ws + a.window]
            if len(sel) > a.per_window:
                sel = [sel[i] for i in np.linspace(0, len(sel) - 1, a.per_window).round().astype(int)]
            content = ref_content() + [{"type": "text", "text": f"Now the clip. Window {ws:.1f}-{ws + a.window:.1f} s of a {T:.1f} s clip."}]
            for t, im in sel:
                content += [{"type": "text", "text": f"t={t:.1f}s"}, {"type": "image_url", "image_url": {"url": b64(im)}}]
            content.append({"type": "text", "text": PROMPT})
            t1 = time.time()
            try:
                r = client.chat.completions.create(model=a.model, temperature=0, max_tokens=500,
                    messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}],
                    response_format={"type": "json_schema", "json_schema": {"name": "w", "schema": SCHEMA}})
                v = json.loads(r.choices[0].message.content); err = None
            except Exception as e:
                v, err = None, str(e)[:300]
            windows.append({"start": ws, "n_frames": len(sel), "infer_s": round(time.time() - t1, 2), "verdict": v, "error": err})
        events = []
        for w in windows:
            for e in (w["verdict"] or {}).get("events", []):
                if e["type"] != "none":
                    events.append(e)
        events.sort(key=lambda e: e["t_s"])
        row = {"clip": m["clip"], "run": m["run"], "title": m.get("title"), "duration_s": T, "fps": m["fps"],
               "learnings": m.get("learnings"), "model": a.model, "n_windows": len(windows),
               "wall_s": round(time.time() - t0, 1), "windows": windows, "events": events,
               "risk_max": max((w["verdict"] or {}).get("risk", "none") for w in windows) if windows else None,
               "states": [(w["verdict"] or {}).get("robot_state_end") for w in windows]}
        fo.write(json.dumps(row) + "\n"); fo.flush()
        print(f"[{k+1}/{len(man)}] {m['clip']} {T:.0f}s {len(windows)} windows in {row['wall_s']}s "
              f"({row['wall_s']/max(T,1):.2f}x realtime) events={len(events)} states={row['states'][:8]}", flush=True)
    fo.close()


if __name__ == "__main__":
    main()
