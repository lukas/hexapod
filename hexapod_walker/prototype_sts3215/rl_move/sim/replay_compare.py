"""Real-vs-MuJoCo side-by-side comparison for a recorded hexapod walk.

WHAT IT DOES
    Takes a hardware run folder (a gait_sweep / data-collection run with a drive
    trace CSV + the top-camera top.mp4 + top_timestamps.csv), initializes MuJoCo
    to the real pose & tilt at the start of the walk phase, feeds the EXACT
    recorded joint commands open-loop (no policy) through the fitted servo model,
    and produces:
      - <gait>_sxs.mp4 : real (left) | MuJoCo (right), time-synced, labelled
      - a divergence summary (roll/pitch peaks, joint RMSE, sim base travel)
    Optionally writes an HTML page embedding the video(s).

    This is the tool for "how does the real robot differ from MuJoCo running the
    same commands" — the qualitative view the aggregate numbers undersell (the
    real robot rocks fore-aft ~3.6 deg vs the sim's ~1 deg; roll 3-6 vs ~1).

WHY MOTION-ONSET ALIGNMENT (the gotcha that wastes an hour if you miss it)
    The drive-trace time base and the camera time base are NOT the same clock,
    and even if they were, the robot does not start stepping the instant
    /api/rl/drive/start returns: there is a per-trial stand-settle + walk-engage
    latency (seen 1.4 s on one gait, 4.5 s on another) before it physically
    moves. So aligning the real video to the recorded drive-start timestamp puts
    the real half in the pre-walk dead zone and it looks frozen. Instead we
    detect the real MOTION ONSET in the video (first sustained inter-frame
    change) and anchor the real playback there. Frames are read SEQUENTIALLY,
    not by random seek (cv2 seek snaps to keyframes and returns stale frames).

USAGE
    uv run python -m rl_move.sim.replay_compare --run <run_dir> [--gait walkteach]
        [--all] [--page] [--out-dir DIR]
    Reads the trace CSV and drive-start t0 for each gait from <run_dir>/results.json.

RELATED
    rl_move/sim/replay_trace.py  — the per-tick divergence numbers + roll/pitch
    plots this builds on (same _ReplaySim physics).
    sysid/                        — the measured hardware-to-MuJoCo calibration.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

DEG2RAD = math.pi / 180.0
FPS = 30
H, W = 360, 480


def find_motion_onset(motion: list[tuple[float, float]], thresh: float = 0.25) -> float:
    """First relative time whose inter-frame motion exceeds ``thresh`` (pure/testable).

    ``motion`` = [(rel_t, mean_absdiff), ...] in order. Returns the onset rel_t,
    or the first sample's time if nothing crosses the threshold.
    """
    for rt, m in motion:
        if m > thresh:
            return rt
    return motion[0][0] if motion else 0.0


def _quat_from_rp(roll: float, pitch: float) -> np.ndarray:
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    return np.array([cr * cp, sr * cp, cr * sp, -sr * sp])


def _label(img, txt, color):
    import cv2
    cv2.putText(img, txt, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(img, txt, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
    return img


def _load_real_window(run: Path, t0: float, t_lo: float, t_hi: float):
    """Sequentially decode real top-camera frames in [t0+t_lo, t0+t_hi]; return
    ([(rel_t, bgr_frame)], motion_onset_rel_t)."""
    import cv2
    ts = {int(r["frame"]): float(r["captured_unix"])
          for r in csv.DictReader((run / "camera" / "top_timestamps.csv").open())}
    cap = cv2.VideoCapture(str(run / "camera" / "top.mp4"))
    fno, prev, frames, motion = -1, None, [], []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        fno += 1
        tt = ts.get(fno)
        if tt is None or tt < t0 + t_lo:
            continue
        if tt > t0 + t_hi:
            break
        small = cv2.resize(im, (W, H))
        frames.append((tt - t0, small))
        g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        if prev is not None:
            motion.append((tt - t0, float(np.mean(cv2.absdiff(g, prev)))))
        prev = g
    cap.release()
    return frames, find_motion_onset(motion)


def _gait_specs(run: Path, gait: str | None, do_all: bool) -> dict:
    res = json.loads((run / "results.json").read_text())
    specs = {}
    for tr in res["trials"]:
        arm = tr["arm"].split("_r")[0]
        if tr.get("csv") and tr.get("t0_unix") and (tr.get("result") or {}).get("ticks"):
            # keep the longest exposure per gait
            if arm not in specs or (tr["result"]["ticks"] > specs[arm][2]):
                specs[arm] = (tr["csv"], tr["t0_unix"], tr["result"]["ticks"])
    if not do_all and gait:
        specs = {gait: specs[gait]} if gait in specs else {}
    return specs


def build(run: Path, gait: str | None, do_all: bool, out_dir: Path, page: bool) -> None:
    import cv2
    import mujoco
    from rl_move.sim.replay_trace import _ReplaySim, load_trace, LOADED_MODEL_PATH
    from rl_move.sim.servo_model import SimServoParams
    from hexapod_core.joint_frame import robot_abs_rad_to_mujoco_rel_rad
    out_dir.mkdir(parents=True, exist_ok=True)
    params = SimServoParams.load(LOADED_MODEL_PATH)
    specs = _gait_specs(run, gait, do_all)
    if not specs:
        sys.exit(f"no usable gait traces in {run}/results.json (need csv + t0_unix + ticks)")
    summary = {}
    for g, (cf, t0, _n) in specs.items():
        tr = load_trace(run / "telemetry" / cf, phase="walk")
        sim = _ReplaySim(params)
        out = sim.replay(tr)
        t = np.array(tr["t"]) - tr["t"][0]
        base, q = np.array(out["base_xyz"]), np.array(out["q"])
        roll, pitch = np.array(out["roll"]), np.array(out["pitch"])
        dur = float(t[-1])
        frames, onset = _load_real_window(run, t0, -1.0, dur + 8.0)
        print(f"{g}: real motion onset at t0{onset:+.2f}s (drive-start->step latency); aligning real there")

        def real_at(te):
            want = onset + te
            return (min(frames, key=lambda fr: abs(fr[0] - want))[1]
                    if frames else np.zeros((H, W, 3), np.uint8))
        ren = mujoco.Renderer(sim.model, height=H, width=W)
        qadr = sim._qadr
        cam = mujoco.MjvCamera()
        cam.distance, cam.elevation, cam.azimuth = 1.1, -22, 270
        vw = cv2.VideoWriter(str(out_dir / f"{g}_sxs.mp4"),
                             cv2.VideoWriter_fourcc(*"mp4v"), FPS, (2 * W, H))
        for f in range(int(dur * FPS)):
            te = f / FPS
            i = int(np.argmin(np.abs(t - te)))
            d = sim.data
            mujoco.mj_resetData(sim.model, d)
            d.qpos[:3] = base[i]
            d.qpos[3:7] = _quat_from_rp(roll[i] * DEG2RAD, pitch[i] * DEG2RAD)
            d.qpos[qadr] = robot_abs_rad_to_mujoco_rel_rad(q[i] * DEG2RAD)
            mujoco.mj_forward(sim.model, d)
            cam.lookat[:] = base[i]
            ren.update_scene(d, cam)
            simimg = _label(cv2.cvtColor(ren.render(), cv2.COLOR_RGB2BGR).copy(),
                            "MuJoCo  t=%.1fs" % te, (120, 200, 255))
            realimg = _label(cv2.rotate(real_at(te), cv2.ROTATE_180).copy(),
                             "REAL  t=%.1fs" % te, (120, 255, 120))
            vw.write(np.hstack([realimg, simimg]))
        vw.release()
        summary[g] = {
            "mp4": str(out_dir / f"{g}_sxs.mp4"),
            "real_roll_peak_deg": round(float(np.max(np.abs(tr["roll"]))), 1),
            "sim_roll_peak_deg": round(float(np.max(np.abs(roll))), 1),
            "real_pitch_peak_deg": round(float(np.max(np.abs(tr["pitch"]))), 1),
            "sim_pitch_peak_deg": round(float(np.max(np.abs(pitch))), 1),
            "sim_base_travel_mm": round(float(np.hypot(base[-1][0] - base[0][0],
                                                       base[-1][1] - base[0][1]) * 1000)),
            "real_motion_onset_s": round(onset, 2),
        }
        print(f"  {g}: real roll/pitch {summary[g]['real_roll_peak_deg']}/{summary[g]['real_pitch_peak_deg']} "
              f"vs sim {summary[g]['sim_roll_peak_deg']}/{summary[g]['sim_pitch_peak_deg']} deg")
    (out_dir / "compare_summary.json").write_text(json.dumps(summary, indent=1))
    if page:
        rows = ['<!doctype html><meta charset=utf-8><title>real vs MuJoCo</title>',
                '<style>body{font:14px system-ui;margin:24px;background:#111;color:#ddd}'
                'video{width:900px;max-width:100%;background:#000}.n{color:#8bd}</style>',
                '<h1>hexapod: real vs MuJoCo, same start &amp; commands, open-loop</h1>']
        for g, m in summary.items():
            rows.append(f'<h2>{g}</h2><p class=n>roll real {m["real_roll_peak_deg"]}&deg; vs sim '
                        f'{m["sim_roll_peak_deg"]}&deg; | pitch (fore-aft rock) real {m["real_pitch_peak_deg"]}&deg; '
                        f'vs sim {m["sim_pitch_peak_deg"]}&deg; | real motion onset t0{m["real_motion_onset_s"]:+}s</p>')
            rows.append(f'<video src="{Path(m["mp4"]).name}" controls loop autoplay muted playsinline></video>')
        (out_dir / "compare.html").write_text("\n".join(rows))
        print("wrote", out_dir / "compare.html")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", type=Path, required=True, help="data-collection run dir (has results.json, telemetry/, camera/)")
    ap.add_argument("--gait", default=None, help="gait name (walkteach/combo/allhead50/parent); default: all")
    ap.add_argument("--all", action="store_true", help="all gaits in the run")
    ap.add_argument("--page", action="store_true", help="also write an HTML page embedding the videos")
    ap.add_argument("--out-dir", type=Path, default=None)
    a = ap.parse_args(argv)
    build(a.run, a.gait, a.all or a.gait is None, a.out_dir or (a.run / "compare"), a.page or True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
