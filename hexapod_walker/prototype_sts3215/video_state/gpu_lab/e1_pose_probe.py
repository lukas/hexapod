#!/usr/bin/env python3
"""E1: can a frozen foundation-model backbone read the robot's pose from the lab camera?

Data: /data/labels.jsonl (one row per floor-camera frame with IMU roll/pitch and
18 joint angles from the robot's own encoders) + /data/frames/.  Steps:
  1. DINOv2-giant features (CLS ++ mean patch, 518 px) for every frame, cached
     to /data/results/e1_feats_<backbone>.npy
  2. ridge regression probe, grouped CV: split by run (5 folds) AND by protocol
     family (leave-one-family-out) -> MAE in degrees per target group
  3. baselines on the same splits: predict-the-train-mean, and the repo's
     0.55M-param StateCNN (video_state/train_state.py architecture) trained
     from scratch on full frames (no detector bbox; aux = zeros)
  4. throughput (frames/s) for the backbone on the H200
Writes /data/results/e1_summary.json and prints a table.
"""
from __future__ import annotations

import argparse, json, re, time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

R = Path("/data/results"); R.mkdir(exist_ok=True)
JOINTS = [f"L{l}_{a}" for l in range(6) for a in ("yaw", "hip", "knee")]
TARGETS = ["roll", "pitch"] + JOINTS
GROUPS = {"roll": [0], "pitch": [1], "yaw(coxa)": [2 + 3 * l for l in range(6)],
          "hip(femur)": [3 + 3 * l for l in range(6)], "knee": [4 + 3 * l for l in range(6)], "all": list(range(20))}


def family(proto: str) -> str:
    p = proto.lower()
    for pat, f in [(r"champion_stand|stand_ground", "stand"), (r"tripod|step_in_place|weight_shift", "tripod"),
                   (r"single_leg|\bl[0-5]_|servo_spread|droop|steps_|radial|load_ladder|loaded", "single_leg"),
                   (r"bus_dropout|soak", "soak"), (r"walk", "walk")]:
        if re.search(pat, p):
            return f
    return "other"


def load_labels():
    rows = [json.loads(l) for l in open("/data/labels.jsonl")]
    rows = [r for r in rows if all(k in r["joints"] for k in JOINTS)]
    Y = np.array([[r["roll"], r["pitch"]] + [r["joints"][j] for j in JOINTS] for r in rows], dtype=np.float32)
    runs = np.array([r["run"] for r in rows]); fams = np.array([family(r["protocol"]) for r in rows])
    paths = [Path("/data") / r["frame"] for r in rows]
    return rows, paths, Y, runs, fams


class Frames(torch.utils.data.Dataset):
    def __init__(self, paths, size, mean, std):
        self.paths, self.size = paths, size
        self.mean = torch.tensor(mean).view(3, 1, 1); self.std = torch.tensor(std).view(3, 1, 1)

    def __len__(self): return len(self.paths)

    def __getitem__(self, i):
        im = Image.open(self.paths[i]).convert("RGB").resize((self.size, self.size), Image.BICUBIC)
        x = torch.from_numpy(np.asarray(im).copy()).permute(2, 0, 1).float() / 255
        return (x - self.mean) / self.std


@torch.no_grad()
def dino_features(paths, name="facebook/dinov2-giant", size=518, bs=64):
    cache = R / f"e1_feats_{name.split('/')[-1]}.npy"
    if cache.exists():
        F = np.load(cache)
        if len(F) == len(paths):
            return F, None
    from transformers import AutoModel
    model = AutoModel.from_pretrained(name, torch_dtype=torch.float16).cuda().eval()
    dl = torch.utils.data.DataLoader(Frames(paths, size, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
                                     batch_size=bs, num_workers=8, pin_memory=True)
    feats = []; t0 = time.time(); n = 0
    for x in dl:
        out = model(pixel_values=x.cuda(non_blocking=True).half()).last_hidden_state
        f = torch.cat([out[:, 0], out[:, 1:].mean(1)], dim=1)
        feats.append(f.float().cpu().numpy()); n += len(x)
        if n % (bs * 50) == 0:
            print(f"  feats {n}/{len(paths)} {n/(time.time()-t0):.0f} fps", flush=True)
    F = np.concatenate(feats); np.save(cache, F)
    return F, n / (time.time() - t0)


def mae_groups(P, Y):
    e = np.abs(P - Y)
    return {g: float(e[:, idx].mean()) for g, idx in GROUPS.items()}


def ridge_cv(F, Y, groups, splits, alpha=10.0):
    P = np.zeros_like(Y)
    for tr, te in splits:
        mu, sd = F[tr].mean(0), F[tr].std(0) + 1e-6
        m = Ridge(alpha=alpha).fit((F[tr] - mu) / sd, Y[tr])
        P[te] = m.predict((F[te] - mu) / sd)
    return P


def mean_baseline(Y, splits):
    P = np.zeros_like(Y)
    for tr, te in splits:
        P[te] = Y[tr].mean(0)
    return P


class StateCNN(nn.Module):  # same architecture as video_state/train_state.py
    def __init__(self, n_out=20, n_aux=4):
        super().__init__()
        chans = [3, 24, 48, 96, 160, 224]; layers = []
        for cin, cout in zip(chans, chans[1:]):
            layers += [nn.Conv2d(cin, cout, 3, stride=2, padding=1), nn.BatchNorm2d(cout), nn.ReLU(inplace=True)]
        self.features = nn.Sequential(*layers)
        self.pool = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Flatten())
        self.head = nn.Sequential(nn.Linear(chans[-1] + n_aux, 128), nn.ReLU(inplace=True), nn.Linear(128, n_out))

    def forward(self, x, aux):
        return self.head(torch.cat([self.pool(self.features(x)), aux], dim=1))


def cnn_cv(paths, Y, splits, size=160, epochs=12, bs=128):
    """Train the repo CNN from scratch per fold on cached uint8 tensors (fast on one GPU)."""
    cache = R / f"e1_frames_u8_{size}.npy"
    if cache.exists() and len(np.load(cache, mmap_mode="r")) == len(paths):
        X = np.load(cache)
    else:
        X = np.stack([np.asarray(Image.open(p).convert("RGB").resize((size, size), Image.BILINEAR)) for p in paths])
        np.save(cache, X)
    Xt = torch.from_numpy(X).permute(0, 3, 1, 2).contiguous()  # N,3,H,W uint8
    Yt = torch.from_numpy(Y)
    P = np.zeros_like(Y)
    for fi, (tr, te) in enumerate(splits):
        ymu, ysd = Yt[tr].mean(0), Yt[tr].std(0) + 1e-3
        net = StateCNN().cuda(); opt = torch.optim.AdamW(net.parameters(), 1e-3, weight_decay=1e-4)
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, 2e-3, total_steps=epochs * ((len(tr) + bs - 1) // bs))
        tr_t = torch.from_numpy(tr)
        for ep in range(epochs):
            net.train(); perm = tr_t[torch.randperm(len(tr_t))]
            for i in range(0, len(perm), bs):
                idx = perm[i:i + bs]
                x = Xt[idx].cuda(non_blocking=True).float() / 255
                if True:  # light augmentation: brightness jitter + small shift
                    x = x * (0.8 + 0.4 * torch.rand(len(x), 1, 1, 1, device=x.device))
                    dx, dy = np.random.randint(-8, 9, 2); x = torch.roll(x, (int(dy), int(dx)), (2, 3))
                y = ((Yt[idx] - ymu) / ysd).cuda()
                loss = nn.functional.smooth_l1_loss(net(x, torch.zeros(len(x), 4, device=x.device)), y)
                opt.zero_grad(set_to_none=True); loss.backward(); opt.step(); sched.step()
        net.eval(); preds = []
        with torch.no_grad():
            for i in range(0, len(te), 512):
                idx = torch.from_numpy(te[i:i + 512])
                x = Xt[idx].cuda().float() / 255
                preds.append((net(x, torch.zeros(len(x), 4, device=x.device)).cpu() * ysd + ymu).numpy())
        P[te] = np.concatenate(preds)
        print(f"  cnn fold {fi}: all-MAE {np.abs(P[te]-Y[te]).mean():.2f}", flush=True)
    return P


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--skip-cnn", action="store_true"); a = ap.parse_args()
    rows, paths, Y, runs, fams = load_labels()
    print(f"{len(rows)} frames, {len(set(runs))} runs, families: {dict(zip(*np.unique(fams, return_counts=True)))}", flush=True)
    F, fps = dino_features(paths)
    print(f"features {F.shape}, backbone throughput {fps} fps", flush=True)
    by_run = list(GroupKFold(5).split(F, Y, runs))
    fam_names = sorted(set(fams))
    by_fam = [(np.where(fams != f)[0], np.where(fams == f)[0]) for f in fam_names]
    res = {"n_frames": len(rows), "n_runs": len(set(runs)), "backbone_fps": fps, "families": fam_names}
    for split_name, splits in (("by_run", by_run), ("by_family", by_fam)):
        res[split_name] = {}
        res[split_name]["mean_baseline"] = mae_groups(mean_baseline(Y, splits), Y)
        P = ridge_cv(F, Y, runs, splits)
        res[split_name]["dinov2g_ridge"] = mae_groups(P, Y)
        if split_name == "by_family":
            res[split_name]["dinov2g_ridge_per_family"] = {f: mae_groups(P[te], Y[te]) for f, (_, te) in zip(fam_names, splits)}
        if not a.skip_cnn:
            t0 = time.time(); Pc = cnn_cv(paths, Y, splits)
            res[split_name]["statecnn_scratch"] = mae_groups(Pc, Y); res[split_name]["statecnn_train_s"] = time.time() - t0
        print(f"\n== split {split_name}")
        for k, v in res[split_name].items():
            if isinstance(v, dict) and "all" in v:
                print(f"  {k:18s} " + " ".join(f"{g}={v[g]:.2f}" for g in GROUPS))
    json.dump(res, open(R / "e1_summary.json", "w"), indent=1)
    # probe timing: ridge on one frame is free; report backbone latency at batch 1
    from transformers import AutoModel
    m = AutoModel.from_pretrained("facebook/dinov2-giant", torch_dtype=torch.float16).cuda().eval()
    x = torch.randn(1, 3, 518, 518, device="cuda", dtype=torch.float16)
    with torch.no_grad():
        for _ in range(5): m(pixel_values=x)
        torch.cuda.synchronize(); t0 = time.time()
        for _ in range(20): m(pixel_values=x)
        torch.cuda.synchronize()
    res["backbone_batch1_ms"] = (time.time() - t0) / 20 * 1000
    print("batch-1 latency ms", res["backbone_batch1_ms"])
    json.dump(res, open(R / "e1_summary.json", "w"), indent=1)


if __name__ == "__main__":
    main()
