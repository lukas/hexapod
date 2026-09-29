#!/usr/bin/env python3
"""E5: improve the pose model. Full-resolution robot crops (880x360 band from the
1280x720 floor-camera frames, top 220 rows) instead of 640 px whole frames, end-to-end
fine-tuning instead of a linear probe, per-leg reporting, and temporal
median smoothing at test time.

Models:
  cnn      StateCNN (repo architecture) from scratch at 2x the E1 resolution
  vitb     DINOv2-base fine-tuned end to end + MLP head (bf16, layer-wise lr)
  vitl     DINOv2-large, same recipe (slower)
Splits: by_run (5-fold GroupKFold) and by_family (leave one protocol family out).
Writes /data/results/e5_<model>_<split>.npz (pred, true, run, family, t) and
/data/results/e5_summary.json.
"""
from __future__ import annotations

import argparse, json, re, time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as Fn
from PIL import Image
from sklearn.model_selection import GroupKFold

R = Path("/data/results"); R.mkdir(exist_ok=True)
JOINTS = [f"L{l}_{a}" for l in range(6) for a in ("yaw", "hip", "knee")]
NAMES = ["roll", "pitch"] + JOINTS
GROUPS = {"roll": [0], "pitch": [1], "yaw(coxa)": [2 + 3 * l for l in range(6)],
          "hip(femur)": [3 + 3 * l for l in range(6)], "knee": [4 + 3 * l for l in range(6)], "all": list(range(20))}
IMNET = ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])


def family(proto):
    p = proto.lower()
    for pat, f in [(r"champion_stand|stand_ground", "stand"), (r"tripod|step_in_place|weight_shift", "tripod"),
                   (r"single_leg|\bl[0-5]_|servo_spread|droop|steps_|radial|load_ladder|loaded", "single_leg"),
                   (r"bus_dropout|soak", "soak"), (r"walk", "walk")]:
        if re.search(pat, p):
            return f
    return "other"


def load(crops_dir):
    rows = [json.loads(l) for l in open("/data/labels.jsonl")]
    rows = [r for r in rows if all(k in r["joints"] for k in JOINTS)]
    Y = np.array([[r["roll"], r["pitch"]] + [(r["joints"][j] if r["joints"][j] is not None else np.nan) for j in JOINTS]
                  for r in rows], dtype=np.float32)
    ok = np.isfinite(Y).all(1)
    rows = [r for r, k in zip(rows, ok) if k]; Y = Y[ok]
    paths = [Path(crops_dir) / r["frame"].split("/", 1)[1] for r in rows]
    runs = np.array([r["run"] for r in rows]); fams = np.array([family(r["protocol"]) for r in rows])
    t = np.array([r["capture_unix"] for r in rows], dtype=np.float64)
    return paths, Y, runs, fams, t


def cache_images(paths, size_wh, tag):
    """uint8 N,H,W,3 cache of resized crops (fits RAM: 50k x 252x616x3 = 23 GB; use 192x476 for ViT-B -> 13.7 GB)."""
    cache = R / f"e5_imgs_{tag}_{size_wh[0]}x{size_wh[1]}.npy"
    if cache.exists():
        X = np.load(cache, mmap_mode="r")
        if len(X) == len(paths):
            return np.ascontiguousarray(X)
    from concurrent.futures import ThreadPoolExecutor
    def rd(p):
        return np.asarray(Image.open(p).convert("RGB").resize(size_wh, Image.BILINEAR))
    X = np.empty((len(paths), size_wh[1], size_wh[0], 3), dtype=np.uint8)
    with ThreadPoolExecutor(16) as ex:
        for i, a in enumerate(ex.map(rd, paths, chunksize=64)):
            X[i] = a
            if i % 10000 == 0:
                print(f"  cached {i}/{len(paths)}", flush=True)
    np.save(cache, X)
    return X


class StateCNN(nn.Module):
    def __init__(self, n_out=20):
        super().__init__()
        chans = [3, 24, 48, 96, 160, 224, 288]; layers = []
        for cin, cout in zip(chans, chans[1:]):
            layers += [nn.Conv2d(cin, cout, 3, stride=2, padding=1), nn.BatchNorm2d(cout), nn.ReLU(inplace=True)]
        self.features = nn.Sequential(*layers)
        self.pool = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Flatten())
        self.head = nn.Sequential(nn.Linear(chans[-1], 256), nn.ReLU(inplace=True), nn.Linear(256, n_out))

    def forward(self, x):
        return self.head(self.pool(self.features(x)))


class ViTReg(nn.Module):
    def __init__(self, name, n_out=20):
        super().__init__()
        from transformers import AutoModel
        self.backbone = AutoModel.from_pretrained(name)
        d = self.backbone.config.hidden_size
        self.head = nn.Sequential(nn.LayerNorm(2 * d), nn.Linear(2 * d, 512), nn.GELU(), nn.Linear(512, n_out))

    def forward(self, x):
        h = self.backbone(pixel_values=x).last_hidden_state
        return self.head(torch.cat([h[:, 0], h[:, 1:].mean(1)], 1))


def augment(x):
    # x float N,3,H,W in [0,1]; photometric jitter + small shift; no flips (left/right legs are distinct labels)
    n = x.shape[0]
    x = x * (0.75 + 0.5 * torch.rand(n, 1, 1, 1, device=x.device)) + 0.1 * (torch.rand(n, 3, 1, 1, device=x.device) - 0.5)
    dx, dy = np.random.randint(-12, 13), np.random.randint(-8, 9)
    return torch.roll(x.clamp(0, 1), (dy, dx), (2, 3))


def train_eval(model_kind, X, Y, tr, te, epochs, bs, lr, device="cuda"):
    mean = torch.tensor(IMNET[0], device=device).view(1, 3, 1, 1); std = torch.tensor(IMNET[1], device=device).view(1, 3, 1, 1)
    Xt = torch.from_numpy(X).permute(0, 3, 1, 2)  # uint8 N,3,H,W (view; no copy)
    Yt = torch.from_numpy(Y); ymu, ysd = Yt[tr].mean(0), Yt[tr].std(0) + 0.5
    if model_kind == "cnn":
        net = StateCNN().to(device); params = [{"params": net.parameters(), "lr": lr}]
    else:
        net = ViTReg({"vitb": "facebook/dinov2-base", "vitl": "facebook/dinov2-large"}[model_kind]).to(device)
        params = [{"params": net.backbone.parameters(), "lr": lr}, {"params": net.head.parameters(), "lr": lr * 20}]
    opt = torch.optim.AdamW(params, weight_decay=0.05)
    steps = epochs * ((len(tr) + bs - 1) // bs)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, [g["lr"] for g in params], total_steps=steps, pct_start=0.1)
    tr_t = torch.from_numpy(tr); t0 = time.time()
    for ep in range(epochs):
        net.train(); perm = tr_t[torch.randperm(len(tr_t))]; tot = 0.0
        for i in range(0, len(perm), bs):
            idx = perm[i:i + bs]
            x = Xt[idx].to(device, non_blocking=True).float() / 255
            x = (augment(x) - mean) / std
            y = ((Yt[idx] - ymu) / ysd).to(device)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                out = net(x)
            loss = Fn.smooth_l1_loss(out.float(), y)
            opt.zero_grad(set_to_none=True); loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step(); sched.step(); tot += loss.item() * len(idx)
        print(f"    ep {ep+1}/{epochs} loss {tot/len(tr):.4f} {time.time()-t0:.0f}s", flush=True)
    net.eval(); preds = []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        for i in range(0, len(te), 256):
            idx = torch.from_numpy(te[i:i + 256])
            x = (Xt[idx].to(device).float() / 255 - mean) / std
            preds.append((net(x).float().cpu() * ysd + ymu).numpy())
    # batch-1 latency
    x1 = torch.zeros(1, 3, X.shape[1], X.shape[2], device=device)
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        for _ in range(5): net(x1)
        torch.cuda.synchronize(); t1 = time.time()
        for _ in range(20): net(x1)
        torch.cuda.synchronize()
    lat = (time.time() - t1) / 20 * 1000
    del net, opt; torch.cuda.empty_cache()
    return np.concatenate(preds), time.time() - t0, lat


def smooth(P, runs, t, k=2):
    """temporal median over +-k neighbouring frames of the same run (frames sorted by capture time)."""
    S = P.copy()
    for r in np.unique(runs):
        idx = np.where(runs == r)[0]; idx = idx[np.argsort(t[idx])]
        seq = P[idx]
        for j in range(len(idx)):
            S[idx[j]] = np.median(seq[max(0, j - k):j + k + 1], 0)
    return S


def mae_groups(P, Y):
    e = np.abs(P - Y); out = {g: float(e[:, i].mean()) for g, i in GROUPS.items()}
    out["per_joint"] = {n: float(e[:, i].mean()) for i, n in enumerate(NAMES)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="cnn", choices=["cnn", "vitb", "vitl"])
    ap.add_argument("--splits", default="by_family,by_run")
    ap.add_argument("--epochs", type=int, default=8); ap.add_argument("--bs", type=int, default=64)
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--crops", default="/data/crops220")
    ap.add_argument("--size", default=None, help="WxH; default cnn 440x180, vit 476x196 (multiples of 14)")
    a = ap.parse_args()
    size = a.size or {"cnn": "704x176", "vitb": "700x168", "vitl": "700x168"}[a.model]
    w, h = map(int, size.split("x"))
    lr = a.lr or {"cnn": 2e-3, "vitb": 3e-5, "vitl": 2e-5}[a.model]
    paths, Y, runs, fams, t = load(a.crops)
    print(f"{len(Y)} frames; caching {w}x{h}", flush=True)
    X = cache_images(paths, (w, h), "crops")
    summ_path = R / "e5_summary.json"
    summ = json.load(open(summ_path)) if summ_path.exists() else {}
    for split in a.splits.split(","):
        if split == "by_run":
            folds = list(GroupKFold(5).split(X, Y, runs))
        else:
            fam_names = sorted(set(fams)); folds = [(np.where(fams != f)[0], np.where(fams == f)[0]) for f in fam_names]
        P = np.zeros_like(Y); secs = 0; lat = None
        for fi, (tr, te) in enumerate(folds):
            print(f"== {a.model} {split} fold {fi}: train {len(tr)} test {len(te)}", flush=True)
            P[te], s, lat = train_eval(a.model, X, Y, tr, te, a.epochs, a.bs, lr); secs += s
            print(f"   fold all-MAE {np.abs(P[te]-Y[te]).mean():.2f} knee {np.abs(P[te][:, GROUPS['knee']]-Y[te][:, GROUPS['knee']]).mean():.2f}", flush=True)
        Ps = smooth(P, runs, t)
        res = {"raw": mae_groups(P, Y), "smoothed_k2": mae_groups(Ps, Y), "mean_baseline": mae_groups(
            np.concatenate([np.repeat(Y[tr].mean(0, keepdims=True), len(te), 0) for tr, te in folds])[np.argsort(np.concatenate([te for _, te in folds]))], Y),
            "train_s_total": secs, "batch1_ms": lat, "size": size, "epochs": a.epochs}
        if split == "by_family":
            res["per_family_raw"] = {f: mae_groups(P[te], Y[te])["all"] for f, (_, te) in zip(sorted(set(fams)), folds)}
        np.savez_compressed(R / f"e5_{a.model}_{split}.npz", pred=P, true=Y, runs=runs, fams=fams, t=t)
        summ[f"{a.model}_{split}"] = res
        json.dump(summ, open(summ_path, "w"), indent=1)
        for k in ("mean_baseline", "raw", "smoothed_k2"):
            v = res[k]; print(f"  {split:10s} {k:12s} " + " ".join(f"{g}={v[g]:.2f}" for g in GROUPS), flush=True)
        print("  per-leg knee:", {f"L{l}": round(res["raw"]["per_joint"][f"L{l}_knee"], 1) for l in range(6)}, flush=True)


if __name__ == "__main__":
    main()
