#!/usr/bin/env python3
"""E2: behaviour classification of every Robot Lab clip with a VLM served by vLLM.

For each clip in /data/manifest.jsonl: decode, sample <=N frames uniformly,
send them as timestamped images, force a JSON verdict (activity, visibility,
safety events with timestamps, outcome, timeline).  Writes
/data/results/e2_<model>.jsonl with the verdict, wall time and token usage,
then prints a confusion summary against the label implied by the plan title.
"""
from __future__ import annotations

import argparse, base64, io, json, re, sys, time
from pathlib import Path

import av
import numpy as np
from PIL import Image
from openai import OpenAI

ACTIVITIES = ["stand_hold", "stand_up", "sit_down_or_lower", "walk_forward", "walk_reverse", "turn_in_place",
              "step_in_place_or_weight_shift", "single_leg_or_joint_test", "glide_restep_shuffle",
              "carried_or_handled_by_person", "no_motion", "other"]
EVENTS = ["tip_or_roll", "fall_or_collapse", "leg_folded_under_body", "foot_slip", "cable_snag",
          "operator_hand_or_intervention", "robot_at_frame_edge_or_out", "stuck_or_stalled_mid_motion",
          "violent_oscillation_or_jitter", "other"]
OUTCOMES = ["completed_normally", "stopped_early_or_aborted", "fell_or_collapsed", "never_moved", "unclear"]

SCHEMA = {
    "type": "object",
    "properties": {
        "primary_activity": {"type": "string", "enum": ACTIVITIES},
        "secondary_activities": {"type": "array", "items": {"type": "string", "enum": ACTIVITIES}},
        "robot_visible": {"type": "string", "enum": ["fully", "partially", "not_visible"]},
        "person_or_hand_in_frame": {"type": "boolean"},
        "safety_events": {"type": "array", "items": {"type": "object", "properties": {
            "t_s": {"type": "number"}, "type": {"type": "string", "enum": EVENTS},
            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
            "which_leg_or_side": {"type": "string"}, "note": {"type": "string"}},
            "required": ["t_s", "type", "severity", "which_leg_or_side", "note"]}},
        "outcome": {"type": "string", "enum": OUTCOMES},
        "confidence": {"type": "number"},
        "timeline": {"type": "string"},
    },
    "required": ["primary_activity", "secondary_activities", "robot_visible", "person_or_hand_in_frame",
                 "safety_events", "outcome", "confidence", "timeline"],
}

SYSTEM = ("You are reviewing lab footage of a small six-legged walking robot (hexapod, about 40 cm across). Each of its "
          "six legs is a chain of three servo modules (boxes ~3 cm) with small square AprilTag fiducials glued on, ending "
          "in a thin stick-like foot; the round body hub also carries tags and a cable bundle. In colour cameras the parts "
          "are red and blue; the wide overview camera is grayscale infrared, where the robot looks like a cluster of "
          "tagged boxes on the carpet. There are TWO different hexapods in this lab: hexapod1 (tag-covered red/blue servo "
          "boxes) and hexapod2 (flat purple hexagonal top plate, red/white leg servos). Each clip names its subject; the "
          "other robot may sit idle in view and must be ignored. Loose AprilTags lie flat on the floor as markers. A human "
          "operator may be nearby. You first get reference images of the subject robot, then frames sampled from one clip "
          "with their timestamps. Answer only with the JSON object requested.")
REFS = {
    "hexapod1": [("/data/ref/robot_colour.jpg", "Reference: THE SUBJECT ROBOT (hexapod1) seen by a colour camera - red/blue servo "
                  "boxes with small square AprilTags glued on, thin stick feet; here in a low, splayed pose."),
                 ("/data/ref/robot_ir_wide.jpg", "Reference: the same subject robot seen by the grayscale wide camera, standing.")],
    "hexapod2": [("/data/ref/robot2_colour.jpg", "Reference: THE SUBJECT ROBOT (hexapod2) - a flat PURPLE hexagonal top plate with one "
                  "tag, red and white leg servos, black stick feet, no tags on the legs.")],
}
OTHER = {"hexapod1": "A second robot with a purple hexagonal top plate may also be in view; it is NOT the subject, ignore it.",
         "hexapod2": "A second robot covered in small square AprilTags (red/blue servo boxes) may also be in view, usually "
                     "idle at the edge of the frame; it is NOT the subject, ignore it."}


def ref_content(robot: str):
    out = [{"type": "text", "text": f"The subject robot in this clip is {robot}. {OTHER.get(robot, '')}"}]
    for path, text in REFS.get(robot, REFS["hexapod1"]):
        out.append({"type": "text", "text": text})
        out.append({"type": "image_url", "image_url": {"url": b64(Image.open(path).convert("RGB"))}})
    return out

PROMPT = ("Classify what the robot does in this clip. Activities: stand_hold = holds a static standing pose; "
          "stand_up = rises from belly/low crouch to standing; sit_down_or_lower = lowers body to belly; "
          "walk_forward/walk_reverse = translates across the floor; turn_in_place; step_in_place_or_weight_shift = "
          "legs move but body stays put; single_leg_or_joint_test = one leg or joint moves while the rest hold; "
          "glide_restep_shuffle = small repositioning shuffle; carried_or_handled_by_person; no_motion. "
          "List every safety-relevant event with the timestamp of the frame where it is first visible: a body tip or roll, "
          "a fall or collapse, a leg folded under the body, a foot slipping, a cable snag, an operator hand touching "
          "or catching the robot, the robot reaching the edge of the frame, a stall mid-motion, or violent oscillation. "
          "If nothing is wrong, return an empty safety_events list. Be concrete about which leg or side. "
          "Timeline: under 100 words describing what happened in order. confidence is 0-1 for primary_activity.")


WIDE_CROP = (0.02, 0.0, 0.62, 0.75)  # x0,y0,x1,y1 fractions; same framing the lab's own eyes use for the wide camera


def sample_frames(path: Path, n: int, max_side: int, crop: tuple | None = None) -> tuple[list[tuple[float, Image.Image]], dict]:
    with av.open(str(path)) as c:
        s = c.streams.video[0]
        fps = float(s.average_rate or s.guessed_rate or 4)
        frames = []
        for f in c.decode(s):
            frames.append((float(f.pts * s.time_base) if f.pts is not None else len(frames) / fps, f))
        total = len(frames)
        idx = np.unique(np.linspace(0, total - 1, min(n, total)).round().astype(int)) if total else []
        out = []
        for i in idx:
            t, f = frames[i]
            im = f.to_image()
            if crop:
                im = im.crop((round(crop[0] * im.width), round(crop[1] * im.height),
                              round(crop[2] * im.width), round(crop[3] * im.height)))
            sc = max_side / max(im.size)
            if sc != 1:
                im = im.resize((round(im.width * sc), round(im.height * sc)), Image.BICUBIC if sc > 1 else Image.BILINEAR)
            out.append((t, im))
    return out, {"src_frames": total, "src_fps": fps, "sent_frames": len(out)}


def b64(im: Image.Image) -> str:
    b = io.BytesIO(); im.save(b, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def expected_label(m: dict) -> str | None:
    t = " ".join(str(x or "") for x in (m.get("title"), m.get("protocol"), m.get("source"),
                                       (m.get("sidecar") or {}).get("label"))).lower()
    rules = [
        (r"glide|re-?step", "glide_restep_shuffle"),
        (r"stand-?ups? from belly|rise up|stand-up and sit-down|paced stand", "stand_up"),
        (r"sit/crash|drops through safe_zero|sit-down", "sit_down_or_lower"),
        (r"reverse|rev\b", "walk_reverse"),
        (r"fwd|forward|goto|meander|centre|center|walk|drive|gait|allheading|speed ps|rl100|multi", "walk_forward"),
        (r"step_in_place|tripod_step|weight_shift|tripod", "step_in_place_or_weight_shift"),
        (r"single_leg|\bl[0-5]_|servo_spread|droop|step response|steps_loaded|radial_shear|load_ladder|loaded_cycles|bus_dropout|soak", "single_leg_or_joint_test"),
        (r"champion_stand|stand_ground|hold90|stand01|stand", "stand_hold"),
    ]
    for pat, lab in rules:
        if re.search(pat, t):
            return lab
    return None


COARSE = {"walk_forward": "locomotion", "walk_reverse": "locomotion", "turn_in_place": "locomotion",
          "glide_restep_shuffle": "locomotion", "stand_up": "posture_change", "sit_down_or_lower": "posture_change",
          "stand_hold": "static", "no_motion": "static", "step_in_place_or_weight_shift": "in_place",
          "single_leg_or_joint_test": "in_place", "carried_or_handled_by_person": "other", "other": "other"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3vl-32b")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--max-side", type=int, default=1280)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="substring filter on clip path")
    ap.add_argument("--tag", default="")
    ap.add_argument("--max-video-s", type=float, default=200.0, help="longer clips go through images mode")
    ap.add_argument("--mode", default="video", choices=["video", "images"],
                    help="video = hand the whole clip to the model as a video (native temporal sampling); "
                         "images = sample --frames stills with timestamps")
    a = ap.parse_args()
    client = OpenAI(base_url=f"http://127.0.0.1:{a.port}/v1", api_key="x", timeout=600)
    man = [json.loads(l) for l in open("/data/manifest.jsonl")]
    if a.only:
        man = [m for m in man if a.only in m["clip"]]
    if a.limit:
        man = man[: a.limit]
    out_path = Path(f"/data/results/e2_{a.model}{a.tag}.jsonl")
    done = set()
    if out_path.exists():
        done = {json.loads(l)["clip"] for l in open(out_path)}
    fo = open(out_path, "a")
    for k, m in enumerate(man):
        if m["clip"] in done:
            continue
        is_wide = m["clip"].endswith("wide.mp4")
        p = Path("/data/clips_widecrop" if is_wide else "/data/clips") / m["clip"]
        if not p.exists():
            p = Path("/data/clips") / m["clip"]
        t0 = time.time()
        clip_note = (f"Clip length {m['duration_s']:.1f} s, recorded at {m['fps']:.1f} fps"
                     + (" (timelapse: 1 frame per second of real time, played at 4 fps; cropped to the working area)" if is_wide else "") + ".")
        refs = ref_content(m.get("robot") or "hexapod1")
        verdict, usage, err, mode, info = None, None, None, a.mode, {}
        t1 = time.time()
        if a.mode == "video" and m["duration_s"] > a.max_video_s:
            mode = "images"  # a 41 min clip decoded whole by the video processor OOM-killed the pod once
        if mode == "video":
            content = refs + [{"type": "text", "text": "Now the clip. " + clip_note},
                              {"type": "video_url", "video_url": {"url": "file://" + str(p)}},
                              {"type": "text", "text": PROMPT}]
            try:
                r = client.chat.completions.create(
                    model=a.model, temperature=0, max_tokens=900,
                    messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}],
                    response_format={"type": "json_schema", "json_schema": {"name": "verdict", "schema": SCHEMA}})
                verdict = json.loads(r.choices[0].message.content)
                usage = {"prompt_tokens": r.usage.prompt_tokens, "completion_tokens": r.usage.completion_tokens}
                info = {"src_frames": m.get("frames"), "src_fps": m.get("fps"), "sent_frames": None}
            except Exception as e:
                err = str(e)[:300]; mode = "images"  # e.g. clip too long for the context: fall back to stills
        if verdict is None:
            try:
                frames, info = sample_frames(p, a.frames, a.max_side, None)
            except Exception as e:
                print("decode failed", m["clip"], e, flush=True); continue
            if not frames:
                continue
            content = refs + [{"type": "text", "text": f"Now the clip. {clip_note} {len(frames)} frames follow."}]
            for t, im in frames:
                content.append({"type": "text", "text": f"t={t:.1f}s"})
                content.append({"type": "image_url", "image_url": {"url": b64(im)}})
            content.append({"type": "text", "text": PROMPT})
            t1 = time.time()
            try:
                r = client.chat.completions.create(
                    model=a.model, temperature=0, max_tokens=900,
                    messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}],
                    response_format={"type": "json_schema", "json_schema": {"name": "verdict", "schema": SCHEMA}})
                verdict = json.loads(r.choices[0].message.content)
                usage = {"prompt_tokens": r.usage.prompt_tokens, "completion_tokens": r.usage.completion_tokens}
                err = None
            except Exception as e:
                verdict, usage, err = None, None, (err or "") + " | " + str(e)[:300]
        t2 = time.time()
        row = {"clip": m["clip"], "run": m["run"], "title": m.get("title"), "status": m.get("status"),
               "review_cls": (m.get("review") or {}).get("cls"), "expected": expected_label(m),
               "seen_incumbent": m.get("seen") if m["clip"].endswith("wide.mp4") else None,
               "model": a.model, "mode": mode, "decode_s": round(t1 - t0, 2), "infer_s": round(t2 - t1, 2), **info,
               "usage": usage, "verdict": verdict, "error": err}
        fo.write(json.dumps(row) + "\n"); fo.flush()
        print(f"[{k+1}/{len(man)}] {m['clip']} exp={row['expected']} got={(verdict or {}).get('primary_activity')} "
              f"events={len((verdict or {}).get('safety_events', []))} infer={row['infer_s']}s err={err}", flush=True)
    fo.close()
    summarize(out_path)


def summarize(path: Path):
    rows = [json.loads(l) for l in open(path)]
    rows = [r for r in rows if r.get("verdict")]
    n = len(rows); hit = 0; chit = 0; scored = 0
    conf = {}
    for r in rows:
        e, g = r["expected"], r["verdict"]["primary_activity"]
        if e:
            scored += 1; hit += e == g; chit += COARSE.get(e) == COARSE.get(g)
            conf.setdefault(e, {}).setdefault(g, 0); conf[e][g] += 1
    inf = sorted(r["infer_s"] for r in rows)
    print(f"\n== {path.name}: {n} clips, {scored} with expected label: exact {hit}/{scored}, coarse {chit}/{scored}")
    print(f"infer_s median {inf[len(inf)//2]:.1f} p90 {inf[int(len(inf)*.9)]:.1f}; "
          f"tokens/clip median {sorted(r['usage']['prompt_tokens'] for r in rows)[n//2]}")
    for e, d in sorted(conf.items()):
        print(f"  {e:32s} -> " + ", ".join(f"{g}:{c}" for g, c in sorted(d.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--summarize":
        summarize(Path(sys.argv[2]))
    else:
        main()
