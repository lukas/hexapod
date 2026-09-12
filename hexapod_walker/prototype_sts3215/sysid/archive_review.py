"""Step-back review of everything the lab and the hand runners recorded.

Reads the Robot Lab v2 database and run directories and writes, into --out:

  index.csv / index.md   one row per run: robot, source, protocol, status,
                         failure class, tracking error, peak current, tilt,
                         walk speed, what the eyes saw
  events.csv             trips and in-run peaks (tracking, current, tilt)
                         with tick, time and whether frames exist
  sheets/*.jpg           contact sheets: the 6 s before and 2 s after each
                         physical trip (dataset vision frames, ~5 Hz), and
                         one sheet per hexapod-2 grid walk from its cam mkv
  plots/*.png            tracking error per run over time, peak current per
                         run over time, walk speed vs command per policy

Failure classes come from the runner's error text, not from exit codes:
  plumbing    never ran a tick and the error is about the harness (no trace
              CSV, robot not ready, state stream incomplete, empty)
  start_pose  glide-to-start verify failed (joint off by > tol)
  overcurrent joint N overcurrent
  tracking    joint N tracking error > 30 deg
  comms       missed reads, not answering, bus write timeout
  other       anything else

    /Users/lukas/hexapod/.venv/bin/python -m sysid.archive_review \
        --lab-dir "$HOME/Library/Application Support/Hexapod Lab/v2" \
        --out "$HOME/Library/Application Support/Hexapod Lab/v2/review-20260911"

Written 2026-09-11 for docs/STATE_OF_THE_ROBOT_2026-09-11.md.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sysid.gait_metrics import load as load_csv, metrics as gait_metrics  # noqa: E402

WILD_A = 3.0          # current reads above this are bus garbage, not physics
CUR_SPIKE_A = 1.0     # in-run current peak worth an event row
TRACK_PEAK_DEG = 20.0  # in-run tracking peak worth an event row
TILT_PEAK_DEG = 12.0   # body roll/pitch peak worth an event row
SHEET_BEFORE_S, SHEET_AFTER_S, SHEET_N = 6.0, 2.0, 8


def classify(status: str, ticks_done: int, error: str, tail: str) -> str:
    e = (error or "").lower()
    if status == "ok":
        return "ok"
    if status in ("held", "unreachable", "timeout", "explored"):
        return status
    if "overcurrent" in e:
        return "overcurrent"
    if "tracking error" in e:
        return "tracking"
    if any(k in e for k in ("missed", "not answering", "bus write", "write timeout")):
        return "comms"
    if "did not verify" in e:
        return "start_pose"
    if ticks_done > 0:
        return "other"
    return "plumbing"


def error_joint(error: str) -> int | None:
    m = re.search(r"joint[s]? \[?(\d+)", error or "")
    return int(m.group(1)) if m else None


def family(protocol: str) -> str:
    if not protocol:
        return "?"
    p = protocol.lower()
    for key, fam in (("champion_stand", "stand"), ("tripod", "tripod"), ("walk", "walk"), ("servo_spread", "servo_spread"),
                     ("steps", "steps"), ("whole_body", "whole_body")):
        if p.startswith(key):
            return fam
    p = re.sub(r"_v\d+$", "", p)
    p = re.sub(r"^l\d_", "leg_", p)          # one family for the six per-leg copies of a ladder
    p = re.sub(r"_\d{8}_\d{6}$", "", p)
    return p[:32]


def local_iso_to_unix(s: str) -> float | None:
    """runner_summary.json writes naive UTC timestamps (checked against vision.jsonl capture_unix)."""
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return None


def sysid_csv_metrics(csv_path: Path) -> dict | None:
    try:
        d = load_csv(csv_path)
        if "q0_deg" not in d or len(d["t_s"]) < 3:
            return None
        m = gait_metrics(d)
    except Exception as ex:  # noqa: BLE001
        return {"error": str(ex)[:80]}
    if "cur_a" in d:
        cur = d["cur_a"][d["cur_a"] < WILD_A]
        m["cur_peak_sane_a"] = round(float(np.nanmax(cur)), 2) if cur.size else None
        m["wild_current_reads"] = int(np.sum(d["cur_a"] >= WILD_A))
    m["_d"] = d
    return m


def vision_tilt(vj: Path) -> tuple[list[dict], dict]:
    recs = [json.loads(l) for l in vj.read_text().splitlines() if l.strip()]
    roll, pitch = [], []
    for r in recs:
        imu = ((r.get("state") or {}).get("imu")) or {}
        roll.append(imu.get("body_roll_deg", np.nan))
        pitch.append(imu.get("body_pitch_deg", np.nan))
    roll, pitch = np.array(roll, float), np.array(pitch, float)
    tilt = np.sqrt(roll ** 2 + pitch ** 2)
    out = {}
    if np.isfinite(tilt).any():
        out = {"tilt_max_deg": round(float(np.nanmax(tilt)), 1), "tilt_rms_deg": round(float(np.sqrt(np.nanmean(tilt ** 2))), 1),
               "tilt_peak_unix": float(recs[int(np.nanargmax(tilt))]["capture_unix"]), "frames": len(recs)}
    return recs, out


def contact_sheet(frames: list[tuple[Path, str]], out: Path, title: str) -> bool:
    import cv2
    tiles = []
    for p, label in frames:
        im = cv2.imread(str(p))
        if im is None:
            continue
        h, w = im.shape[:2]
        im = cv2.resize(im, (480, int(480 * h / w)))
        cv2.rectangle(im, (0, 0), (im.shape[1], 26), (0, 0, 0), -1)
        cv2.putText(im, label, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(im)
    if not tiles:
        return False
    hh = min(t.shape[0] for t in tiles)
    tiles = [t[:hh] for t in tiles]
    cols = 4
    rows = [np.hstack(tiles[i:i + cols] + [np.zeros_like(tiles[0])] * (cols - len(tiles[i:i + cols]))) for i in range(0, len(tiles), cols)]
    grid = np.vstack(rows)
    banner = np.zeros((34, grid.shape[1], 3), np.uint8)
    cv2.putText(banner, title[:150], (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(str(out), np.vstack([banner, grid]), [cv2.IMWRITE_JPEG_QUALITY, 80])
    return True


def sheet_from_vision(recs: list[dict], base: Path, t_event: float, out: Path, title: str) -> bool:
    ts = np.array([r["capture_unix"] for r in recs], float)
    want = np.linspace(t_event - SHEET_BEFORE_S, t_event + SHEET_AFTER_S, SHEET_N)
    picked, seen = [], set()
    for tw in want:
        i = int(np.argmin(np.abs(ts - tw)))
        if abs(ts[i] - tw) > 1.5 or i in seen:
            continue
        seen.add(i)
        picked.append((base / recs[i]["image"], f"{ts[i] - t_event:+.1f} s"))
    return contact_sheet(picked, out, title) if len(picked) >= 3 else False


def sheet_from_wide(wide: Path, t_event: float, out: Path, title: str) -> bool:
    """The lab's 1 Hz wide frames; their mtimes are the capture clock."""
    frames = sorted(wide.glob("*.jpg"))
    if not frames:
        return False
    ts = np.array([f.stat().st_mtime for f in frames])
    want = np.linspace(t_event - SHEET_BEFORE_S, t_event + SHEET_AFTER_S, SHEET_N)
    picked, seen = [], set()
    for tw in want:
        i = int(np.argmin(np.abs(ts - tw)))
        if abs(ts[i] - tw) > 1.5 or i in seen:
            continue
        seen.add(i)
        picked.append((frames[i], f"{ts[i] - t_event:+.1f} s"))
    return contact_sheet(picked, out, title) if len(picked) >= 3 else False


def sheet_from_video(mkv: Path, out: Path, title: str, n: int = SHEET_N, tmp: Path | None = None) -> bool:
    tmp = tmp or out.parent / "_tmp"
    tmp.mkdir(exist_ok=True)
    try:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mkv)],
                                   capture_output=True, text=True, check=True).stdout.strip())
    except Exception:
        return False
    frames = []
    for k in range(n):
        t = dur * (k + 0.5) / n
        fp = tmp / f"{mkv.stem}_{k}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(mkv), "-frames:v", "1", str(fp)], check=False)
        if fp.exists():
            frames.append((fp, f"{t:.1f} s / {dur:.0f} s"))
    ok = contact_sheet(frames, out, title)
    for fp, _ in frames:
        fp.unlink(missing_ok=True)
    return ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--lab-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default=None, help="run id prefix: process just this run (debug)")
    ap.add_argument("--no-sheets", action="store_true")
    ap.add_argument("--no-plots", action="store_true")
    a = ap.parse_args(argv)
    out = a.out
    (out / "sheets").mkdir(parents=True, exist_ok=True)
    (out / "plots").mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(a.lab_dir / "lab2.sqlite3"))
    con.row_factory = sqlite3.Row
    rows = con.execute("""SELECT r.id, r.robot, r.started_at, r.finished_at, r.status, r.run_dir, r.summary_json, r.log_tail,
                                 p.protocol, p.title, p.kind, p.intent
                          FROM runs r LEFT JOIN plans p ON p.id = r.plan_id ORDER BY r.started_at""").fetchall()
    index, events = [], []
    for r in rows:
        if a.only and not r["id"].startswith(a.only):
            continue
        s = json.loads(r["summary_json"] or "{}")
        rd = Path(r["run_dir"]) if r["run_dir"] else None
        rec = {"run": r["id"], "robot": r["robot"], "started": (r["started_at"] or "")[:19], "status": r["status"],
               "protocol": r["protocol"] or "", "family": family(r["protocol"] or ""), "title": (r["title"] or "")[:80],
               "intent": r["intent"] or "", "source": "v2", "cls": "", "error": "", "joint": "", "ticks": "", "ticks_planned": "",
               "hz": "", "dur_s": "", "track_mean": "", "track_max": "", "cur_mean": "", "cur_peak": "", "wild_cur": "",
               "overruns": "", "tilt_max": "", "tilt_rms": "", "speed_mm_s": "", "cmd_mm_s": "", "heading_change_deg": "",
               "policy": "", "frames": "", "wide_frames": "", "seen": (s.get("seen") or "")[:200].replace("\n", " "),
               "learned": (s.get("learned") or "")[:200].replace("\n", " "), "sheet": ""}
        if not rd or not rd.exists():
            rec["cls"] = "no_dir"
            index.append(rec)
            continue
        rec["wide_frames"] = len(list((rd / "wide").glob("*.jpg"))) if (rd / "wide").exists() else 0
        if s.get("old_lab"):
            rec["source"] = "old_lab"
            summ = (rd / "summary.md").read_text(errors="ignore") if (rd / "summary.md").exists() else ""
            exp = json.loads((rd / "experiment.json").read_text()) if (rd / "experiment.json").exists() else {}
            rec["title"] = (exp.get("name") or "")[:80]
            if "Driver: simulated" in summ or "no_motion" in json.dumps(exp.get("parameters", {})):
                rec["cls"] = "simulated"
                index.append(rec)
                continue
            csvs = [p for p in rd.glob("*.csv") if "summary" not in p.name]
            rec["cls"] = "hardware"
            best = None
            for c in csvs:
                m = sysid_csv_metrics(c)
                if m and "_d" in m and (best is None or m["rows"] > best["rows"]):
                    best = m
                    rec["protocol"] = re.sub(r"^(run\d__)?sysid_", "", c.stem)
                    rec["protocol"] = re.sub(r"_\d{8}_\d{6}$", "", rec["protocol"])
                    rec["family"] = family(rec["protocol"])
            if best:
                rec.update(dur_s=best["dur_s"], hz=best["tick_hz"], track_mean=best["track_err_deg"]["mean"], track_max=best["track_err_deg"]["max"],
                           cur_mean=best.get("cur_a", {}).get("mean", ""), cur_peak=best.get("cur_peak_sane_a", ""),
                           wild_cur=best.get("wild_current_reads", ""), overruns=best.get("overruns", ""), ticks=best["rows"])
            index.append(rec)
            continue
        if r["robot"] == "hexapod2":
            rec["source"] = "h2_import"
            rec["cls"] = "import_" + r["status"]
            for j in rd.glob("*.json"):
                try:
                    d = json.loads(j.read_text())
                except Exception:
                    continue
                if isinstance(d, dict) and "speed_mm_s" in d:
                    vx = float((d.get("cmd") or {}).get("vx", 0) or 0)
                    rec.update(speed_mm_s=d["speed_mm_s"], cmd_mm_s=round(vx if abs(vx) > 5 else 1000 * vx, 0),  # scripted gait logs mm/s, RL logs m/s
                               heading_change_deg=d.get("heading_change_deg", ""), policy=(d.get("policy") or "")[:60],
                               dur_s=d.get("seconds", ""), error=d.get("stop_reason", ""), title=(d.get("label") or rec["title"])[:80])
                    rec["cls"] = "grid_walk"
            for c in sorted(rd.glob("rl_*.csv")):
                m = sysid_csv_metrics(c)
                if m and "_d" in m:
                    d = m["_d"]
                    if "roll_deg" in d:
                        tilt = np.sqrt(d["roll_deg"] ** 2 + d["pitch_deg"] ** 2)
                        rec["tilt_max"], rec["tilt_rms"] = round(float(np.nanmax(tilt)), 1), round(float(np.sqrt(np.nanmean(tilt ** 2))), 1)
                    rec.update(track_mean=m["track_err_deg"]["mean"], track_max=m["track_err_deg"]["max"], cur_peak=m.get("max_cur_a", ""),
                               hz=m["tick_hz"], ticks=m["rows"])
                    if not rec["dur_s"]:
                        rec["dur_s"] = m["dur_s"]
                    break
            if not a.no_sheets and rec["cls"] == "grid_walk":
                mkvs = sorted(rd.glob("*.mkv")) + sorted(rd.glob("*.mp4"))
                if mkvs:
                    sp = out / "sheets" / f"h2_{r['id']}_{re.sub(r'[^a-z0-9]+', '_', rec['title'].lower())[:30]}.jpg"
                    if sheet_from_video(mkvs[0], sp, f"hexapod2 {rec['title']} speed {rec['speed_mm_s']} mm/s cmd {rec['cmd_mm_s']} stop={rec['error']}"):
                        rec["sheet"] = sp.name
            index.append(rec)
            continue
        # Robot Lab v2 hexapod1 run
        err = str(s.get("error") or "")
        ticks = int(s.get("ticks_done") or 0)
        rec.update(error=err[:120], ticks=ticks, ticks_planned=s.get("ticks_planned", ""), joint=error_joint(err) if error_joint(err) is not None else "")
        rec["cls"] = classify(r["status"], ticks, err, r["log_tail"] or "")
        if s.get("recovery"):
            rec["cls"] = "recovery"
        rs = next(rd.rglob("runner_summary.json"), None)
        ds = rs.parent if rs else None
        vj = next(rd.rglob("vision.jsonl"), None)
        t0 = None
        if rs:
            rsj = json.loads(rs.read_text())
            t0 = local_iso_to_unix(rsj.get("started", ""))
            rec["hz"] = rsj.get("hz", "")
        m = None
        if ds:
            csvs = [p for p in ds.glob("*.csv") if "summary" not in p.name and not p.name.startswith("camera")]
            for c in csvs:
                m = sysid_csv_metrics(c)
                if m and "_d" in m:
                    break
                m = None
        if m:
            d = m["_d"]
            rec.update(dur_s=m["dur_s"], track_mean=m["track_err_deg"]["mean"], track_max=m["track_err_deg"]["max"],
                       cur_mean=m.get("cur_a", {}).get("mean", ""), cur_peak=m.get("cur_peak_sane_a", ""),
                       wild_cur=m.get("wild_current_reads", ""), overruns=m.get("overruns", ""))
            q = np.stack([d[f"q{i}_deg"] for i in range(18)], 1)
            c = np.stack([d[f"cmd{i}_deg"] for i in range(18)], 1)
            errm = np.abs(c - q)
            i, j = np.unravel_index(np.nanargmax(errm), errm.shape)
            if errm[i, j] >= TRACK_PEAK_DEG and rec["cls"] != "tracking":
                events.append({"run": r["id"], "protocol": rec["protocol"], "kind": "track_peak", "joint": int(j), "value": round(float(errm[i, j]), 1),
                               "t_s": round(float(d["t_s"][i]), 1), "unix": (t0 + float(d["t_s"][i])) if t0 else "", "frames": bool(vj)})
            if "cur_a" in d:
                cur = np.where(d["cur_a"] < WILD_A, d["cur_a"], np.nan)
                if np.isfinite(cur).any() and np.nanmax(cur) >= CUR_SPIKE_A and rec["cls"] != "overcurrent":
                    k = int(np.nanargmax(cur))
                    events.append({"run": r["id"], "protocol": rec["protocol"], "kind": "current_peak", "joint": "", "value": round(float(cur[k]), 2),
                                   "t_s": round(float(d["t_s"][k]), 1), "unix": (t0 + float(d["t_s"][k])) if t0 else "", "frames": bool(vj)})
        recs = []
        if vj:
            recs, tl = vision_tilt(vj)
            rec["frames"] = len(recs)
            if tl:
                rec["tilt_max"], rec["tilt_rms"] = tl["tilt_max_deg"], tl["tilt_rms_deg"]
                if tl["tilt_max_deg"] >= TILT_PEAK_DEG:
                    events.append({"run": r["id"], "protocol": rec["protocol"], "kind": "tilt_peak", "joint": "", "value": tl["tilt_max_deg"],
                                   "t_s": round(tl["tilt_peak_unix"] - t0, 1) if t0 else "", "unix": tl["tilt_peak_unix"], "frames": True})
        if rec["cls"] in ("overcurrent", "tracking", "comms", "other", "start_pose"):
            t_trip = (t0 + float(m["_d"]["t_s"][-1])) if (m and t0) else (local_iso_to_unix(rsj.get("ended", "")) if rs else None)
            events.append({"run": r["id"], "protocol": rec["protocol"], "kind": "trip_" + rec["cls"], "joint": rec["joint"], "value": err[:100],
                           "t_s": round(float(m["_d"]["t_s"][-1]), 1) if m else "", "unix": t_trip or "", "frames": bool(recs)})
            if not a.no_sheets and t_trip:
                ttl = f"{r['id']} {rec['protocol']} tick {ticks}/{rec['ticks_planned']}: {err[:90]}"
                made = []
                if recs:
                    sp = out / "sheets" / f"trip_{r['id']}_{rec['cls']}_j{rec['joint']}_tracker.jpg"
                    if sheet_from_vision(recs, vj.parent, t_trip, sp, ttl + " [tracker cam]"):
                        made.append(sp.name)
                if (rd / "wide").exists():
                    sp = out / "sheets" / f"trip_{r['id']}_{rec['cls']}_j{rec['joint']}_wide.jpg"
                    if sheet_from_wide(rd / "wide", t_trip, sp, ttl + " [wide cam]"):
                        made.append(sp.name)
                rec["sheet"] = " ".join(made)
        index.append(rec)

    # ---------- tables ----------
    cols = list(index[0].keys())
    with open(out / "index.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(index)
    with open(out / "events.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["run", "protocol", "kind", "joint", "value", "t_s", "unix", "frames"])
        w.writeheader()
        w.writerows(events)

    v2 = [x for x in index if x["source"] == "v2" and x["cls"] != "recovery"]
    per_proto = defaultdict(Counter)
    for x in v2:
        per_proto[x["protocol"]][x["cls"]] += 1
    cls_total = Counter(x["cls"] for x in v2)
    joints = Counter(str(x["joint"]) for x in v2 if x["joint"] != "" and x["cls"] in ("overcurrent", "tracking", "comms", "start_pose"))
    lines = ["# Archive review " + datetime.now().strftime("%Y-%m-%d %H:%M"), "",
             f"Runs in DB: {len(index)}. Robot Lab v2 hexapod1 protocol runs: {len(v2)}. "
             f"Old-lab records: {sum(1 for x in index if x['source']=='old_lab')} ({sum(1 for x in index if x['cls']=='simulated')} simulated). "
             f"hexapod2 imports: {sum(1 for x in index if x['source']=='h2_import')} ({sum(1 for x in index if x['cls']=='grid_walk')} camera-measured walks).", "",
             "## v2 hexapod1 outcome classes", "", "| class | runs |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in cls_total.most_common()]
    lines += ["", "## Joints named in trips (overcurrent, tracking, comms, start-pose)", "", "| joint | leg/type | trips |", "|---|---|---:|"]
    jt = {0: "yaw", 1: "hip", 2: "knee"}
    lines += [f"| {j} | L{int(j)//3} {jt[int(j)%3]} | {n} |" for j, n in joints.most_common()]
    lines += ["", "## Per protocol", "", "| protocol | " + " | ".join(cls_total) + " |", "|---|" + "---:|" * len(cls_total)]
    for p, c in sorted(per_proto.items(), key=lambda kv: -sum(kv[1].values())):
        lines.append(f"| {p} | " + " | ".join(str(c.get(k, 0)) for k in cls_total) + " |")
    lines += ["", "## Events", "", "| run | protocol | kind | joint | value | t (s) | frames |", "|---|---|---|---|---|---:|---|"]
    lines += [f"| {e['run']} | {e['protocol'][:40]} | {e['kind']} | {e['joint']} | {str(e['value'])[:70]} | {e['t_s']} | {'yes' if e['frames'] else 'no'} |" for e in events]
    lines += ["", "## Sheets", ""] + [f"- {x['run']} {x['protocol'] or x['title']}: " + ", ".join(f"`sheets/{n}`" for n in x["sheet"].split()) for x in index if x["sheet"]]
    (out / "REVIEW.md").write_text("\n".join(lines) + "\n")

    # ---------- plots ----------
    if not a.no_plots:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        pts = [x for x in index if x["track_mean"] != "" and x["robot"] == "hexapod1"]
        fams = sorted({x["family"] for x in pts})
        cmap = plt.get_cmap("tab20")
        fig, axs = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
        for k, f in enumerate(fams):
            xs = [datetime.fromisoformat(x["started"]) for x in pts if x["family"] == f]
            axs[0].scatter(xs, [x["track_mean"] for x in pts if x["family"] == f], color=cmap(k % 20), label=f, s=28)
            axs[1].scatter(xs, [x["track_max"] for x in pts if x["family"] == f], color=cmap(k % 20), s=28,
                           marker=["o" if x["cls"] in ("ok", "hardware") else "x" for x in pts if x["family"] == f][0])
        for x in pts:
            if x["cls"] not in ("ok", "hardware"):
                axs[1].scatter([datetime.fromisoformat(x["started"])], [x["track_max"]], facecolors="none", edgecolors="red", s=120)
        axs[0].set_ylabel("mean |cmd - q| deg (all 18 joints)")
        axs[1].set_ylabel("max |cmd - q| deg (red ring = run failed)")
        axs[0].legend(fontsize=7, ncol=3)
        axs[0].set_title("hexapod1 tracking error per run (sysid CSVs, old lab + v2)")
        axs[1].xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(out / "plots" / "tracking_error_per_run.png", dpi=110)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(13, 4.5))
        for k, f in enumerate(fams):
            sel = [x for x in pts if x["family"] == f and x["cur_peak"] != ""]
            ax.scatter([datetime.fromisoformat(x["started"]) for x in sel], [x["cur_peak"] for x in sel], color=cmap(k % 20), label=f, s=28)
        for x in pts:
            if x["cls"] == "overcurrent" and x["cur_peak"] != "":
                ax.scatter([datetime.fromisoformat(x["started"])], [x["cur_peak"]], facecolors="none", edgecolors="red", s=120)
        h2p = [x for x in index if x["robot"] == "hexapod2" and x["cur_peak"] != ""]
        ax.scatter([datetime.fromisoformat(x["started"]) for x in h2p], [x["cur_peak"] for x in h2p], color="k", marker="^", s=30, label="hexapod2 max_cur_a")
        ax.set_ylabel("peak bus current A (reads >= 3 A dropped)")
        ax.set_title("peak current per run (red ring = overcurrent trip)")
        ax.legend(fontsize=7, ncol=4)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(out / "plots" / "peak_current_per_run.png", dpi=110)
        plt.close(fig)

        walks = [x for x in index if x["cls"] == "grid_walk" and x["speed_mm_s"] != ""]
        hand = a.lab_dir / "hand-walk-20260911" / "walk_summary.json"
        fig, axs = plt.subplots(1, 2, figsize=(13, 5))
        pols = sorted({x["policy"] for x in walks})
        for k, p in enumerate(pols):
            sel = [x for x in walks if x["policy"] == p]
            axs[0].scatter([abs(x["cmd_mm_s"]) for x in sel], [x["speed_mm_s"] for x in sel], color=cmap(k % 20), label=p[:40], s=40)
            axs[1].scatter([abs(x["cmd_mm_s"]) for x in sel], [x["heading_change_deg"] for x in sel], color=cmap(k % 20), s=40)
        if hand.exists():
            hw = json.loads(hand.read_text())
            for leg in hw.get("legs", []):
                if leg.get("measured"):
                    axs[0].scatter([abs(leg["vx_mm_s"])], [leg["mean_speed_mm_s"]], color="k", marker="*", s=160, label="hexapod1 hand walk 2026-09-11" if leg is hw["legs"][0] else None)
                    axs[1].scatter([abs(leg["vx_mm_s"])], [leg["heading_change_deg"]], color="k", marker="*", s=160)
        lim = max([abs(x["cmd_mm_s"]) for x in walks] + [60])
        axs[0].plot([0, lim], [0, lim], "k:", lw=1, label="measured = commanded")
        axs[0].set_xlabel("commanded |vx| mm/s")
        axs[0].set_ylabel("camera-measured mean speed mm/s")
        axs[0].legend(fontsize=7)
        axs[0].set_title("walk speed vs command (hexapod2 grid walks + hexapod1 hand walk)")
        axs[1].set_xlabel("commanded |vx| mm/s")
        axs[1].set_ylabel("heading change over the walk, deg")
        axs[1].axhline(0, color="k", lw=0.5)
        axs[1].set_title("yaw drift during straight walks")
        fig.tight_layout()
        fig.savefig(out / "plots" / "walk_speed_vs_command.png", dpi=110)
        plt.close(fig)

    print(f"{len(index)} runs, {len(events)} events, {sum(1 for x in index if x['sheet'])} sheets -> {out}")
    print("classes:", dict(cls_total))
    print("trip joints:", dict(joints))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
