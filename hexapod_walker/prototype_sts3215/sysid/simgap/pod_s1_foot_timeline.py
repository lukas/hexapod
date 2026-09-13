#!/usr/bin/env python3
"""S1: 30 fps per-foot timelines from the static side camera (cam2) for the hexapod2 RL runs.
Same red-boot-tip detector + nearest-neighbour tracker as c5_motion_labels.py, but emits the full per-frame
track table (x, y, speed px/frame, state) and per-frame counts of stance/swing/ambiguous feet, plus the
plate box (body) centre y per frame as a crude body-bounce signal. Output: /data/results/simgap/<run>__<clip>.json"""
import av, json, sys, numpy as np
from pathlib import Path
from scipy import ndimage
LO, HI, SMOOTH = 0.7, 1.8, 4
OUT = Path("/data/results/simgap"); OUT.mkdir(exist_ok=True)
CLIPS = [
 "cc274e771141/20260911_163626_speed_ps200_fwd_0_10_cam2.mp4",
 "8263389349f6/20260911_163402_speed_ps200_fwd_0_08_cam2.mp4",
 "10f90c2597f3/20260911_160643_walkteach_fwd_cam2.mp4",
 "e6e216c01d62/20260911_145612_walkteach_reverse_cam2.mp4",
 "ca3e7039d1d6/20260911_152126_allheading_fwd_cam2.mp4",
 "867eb750b497/20260911_145839_stotight45_fwd_0_06_cam2.mp4",
]
if len(sys.argv) > 1: CLIPS = sys.argv[1:]

def plate_box(hsv):
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = (h > 170) & (h < 205) & (s > 70) & (v > 40) & (v < 200)
    m = ndimage.binary_opening(m, iterations=2); lab, n = ndimage.label(m)
    if n == 0: return None
    sizes = ndimage.sum(m, lab, range(1, n + 1)); k = int(np.argmax(sizes)) + 1
    if sizes[k - 1] < 1500: return None
    ys, xs = np.nonzero(lab == k); return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())

def boot_tips(hsv, box):
    x0, y0, x1, y1 = box; pw = x1 - x0
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    red = ((h < 14) | (h > 240)) & (s > 90) & (v > 110)
    reg = np.zeros_like(red); rx0, rx1 = max(0, int(x0 - 1.1 * pw)), min(red.shape[1], int(x1 + 1.1 * pw))
    ry0, ry1 = y1, min(red.shape[0], int(y1 + 1.6 * pw)); reg[ry0:ry1, rx0:rx1] = True
    m = red & reg; lab, n = ndimage.label(m); tips = []
    for k in range(1, n + 1):
        ys, xs = np.nonzero(lab == k); area = len(xs)
        if area < 40 or area > 1400: continue
        w, hgt = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
        if w > 60 or hgt > 80 or hgt < 8: continue
        cx = int(np.median(xs)); top = int(ys.min())
        col = slice(max(0, cx - 6), cx + 7); rows_ = slice(max(0, top - 80), max(0, top - 10))
        dark = (v[rows_, col] < 95) & (s[rows_, col] < 130)
        if dark.size == 0 or dark.mean() < 0.22: continue
        if ys.max() < y1 + 0.5 * pw: continue
        tips.append((float(xs[ys.argmax()]), float(ys.max()), int(area)))
    return tips

for clip in CLIPS:
    p = Path("/data/clips") / clip
    if not p.exists(): print("missing", clip); continue
    cont = av.open(str(p)); st = cont.streams.video[0]; fps = float(st.average_rate or 30)
    dets, boxes = [], []
    for i, fr in enumerate(cont.decode(st)):
        hsv = np.asarray(fr.to_image().convert("HSV")).astype(int)
        b = plate_box(hsv); boxes.append(b); dets.append(boot_tips(hsv, b) if b else [])
    cont.close()
    tracks, active = [], {}
    for i, tips in enumerate(dets):
        used, new_active = set(), {}
        for tid, (px, py, last) in active.items():
            best, bd = None, 45.0
            for j, (x, y, a) in enumerate(tips):
                d = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
                if j not in used and d < bd: best, bd = j, d
            if best is not None and i - last <= 3:
                used.add(best); x, y, a = tips[best]; tracks[tid][i] = (x, y); new_active[tid] = (x, y, i)
        for j, (x, y, a) in enumerate(tips):
            if j not in used:
                tracks.append({i: (x, y)}); new_active[len(tracks) - 1] = (x, y, i)
        active = new_active
    n = len(dets); per_frame = []
    for fi in range(n):
        feet = []
        for ti, tr in enumerate(tracks):
            if fi not in tr or len(tr) < 2 * SMOOTH + 1: continue
            sp = [((tr[k + 1][0] - tr[k][0]) ** 2 + (tr[k + 1][1] - tr[k][1]) ** 2) ** 0.5 for k in range(fi - SMOOTH, fi + SMOOTH) if k in tr and k + 1 in tr]
            if len(sp) < SMOOTH: continue
            v = float(np.median(sp)); x, y = tr[fi]
            if max(sp) > 14: continue
            state = "stance" if v < LO else ("swing" if v > HI else "ambiguous")
            feet.append([ti, round(x, 1), round(y, 1), round(v, 2), state])
        b = boxes[fi]
        per_frame.append({"f": fi, "t": round(fi / fps, 3), "box": b, "feet": feet,
                          "n_stance": sum(f[4] == "stance" for f in feet), "n_swing": sum(f[4] == "swing" for f in feet), "n_amb": sum(f[4] == "ambiguous" for f in feet)})
    # duplicated-frame detection (cam2 froze at start on some clips): identical detections + box for many frames
    dup = 0
    for fi in range(1, n):
        if boxes[fi] == boxes[fi - 1] and dets[fi] == dets[fi - 1]: dup += 1
    long_tracks = [{"id": ti, "n": len(tr), "f0": min(tr), "f1": max(tr), "y_med": float(np.median([v[1] for v in tr.values()])), "x_med": float(np.median([v[0] for v in tr.values()]))} for ti, tr in enumerate(tracks) if len(tr) >= 15]
    out = {"clip": clip, "fps": fps, "frames": n, "dup_frames": dup, "tracks_long": long_tracks, "per_frame": per_frame}
    name = clip.replace("/", "__").replace(".mp4", "") + ".json"
    json.dump(out, open(OUT / name, "w"))
    ns = np.array([pf["n_stance"] for pf in per_frame]); nw = np.array([pf["n_swing"] for pf in per_frame])
    print(clip, f"fps={fps:.1f} frames={n} dup={dup} tracks>=15f={len(long_tracks)} mean_stance_feet={ns.mean():.2f} mean_swing={nw.mean():.2f} frames_with_0_swing={np.mean(nw==0):.2f}", flush=True)
