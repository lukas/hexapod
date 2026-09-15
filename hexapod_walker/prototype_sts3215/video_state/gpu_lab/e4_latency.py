#!/usr/bin/env python3
"""E4: how close to live could a VLM safety gate run?  Single-frame and 8-frame
window requests against each served model, sequential, p50/p90 wall time.
Run with the GPU otherwise idle.  Writes /data/results/e4_latency.json."""
import base64, io, json, sys, time, av
from PIL import Image
from openai import OpenAI

SCHEMA = {"type": "object", "properties": {"risk": {"type": "string", "enum": ["none", "watch", "intervene_now"]},
          "state": {"type": "string"}, "note": {"type": "string"}}, "required": ["risk", "state", "note"]}
Q = ("hexapod2 is the robot with the purple top plate. In one word each: risk level for a human spotter "
     "(none/watch/intervene_now), the robot's state, and a short note.")


def frames(path, n, t0=5.0, step=0.5, max_side=960):
    out = []
    with av.open(path) as c:
        s = c.streams.video[0]; want = [t0 + i * step for i in range(n)]
        for f in c.decode(s):
            t = float(f.pts * s.time_base)
            if want and t >= want[0]:
                want.pop(0); im = f.to_image(); sc = max_side / max(im.size)
                out.append(im.resize((round(im.width * sc), round(im.height * sc))) if sc < 1 else im)
            if not want:
                break
    return out


def b64(im):
    b = io.BytesIO(); im.save(b, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def bench(client, model, imgs, reps):
    content = [{"type": "image_url", "image_url": {"url": b64(im)}} for im in imgs] + [{"type": "text", "text": Q}]
    ts = []
    for _ in range(reps):
        t = time.time()
        r = client.chat.completions.create(model=model, temperature=0, max_tokens=60,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_schema", "json_schema": {"name": "g", "schema": SCHEMA}})
        ts.append(time.time() - t)
    ts.sort()
    return {"p50_s": ts[len(ts) // 2], "p90_s": ts[int(len(ts) * .9)], "prompt_tokens": r.usage.prompt_tokens,
            "sample": json.loads(r.choices[0].message.content)}


res = {}
clip = "/data/clips/82461d6ac452/194030Z_glide_cam2.mp4"
for model, port in (("qwen3vl-8b", 8001), ("qwen3vl-32b", 8000)):
    cl = OpenAI(base_url=f"http://127.0.0.1:{port}/v1", api_key="x")
    for n in (1, 8):
        imgs = frames(clip, n)
        bench(cl, model, imgs, 2)  # warm-up
        res[f"{model}_{n}frame"] = bench(cl, model, imgs, 10)
        print(model, n, "frames:", res[f"{model}_{n}frame"], flush=True)
json.dump(res, open("/data/results/e4_latency.json", "w"), indent=1)
