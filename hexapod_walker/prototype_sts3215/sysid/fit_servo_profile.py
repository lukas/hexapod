#!/usr/bin/env python3
"""Fit ONE servo-profile model to every cmd->q tape we have, across profiles.

The question (2026-09-26): does the sim's ServoProfile structure (latency
queue + Feetech trapezoid + deadband, ``rl_move/sim/servo_model.py``) predict
the real STS3215 joint motion for BOTH the RL runner profile (write_speed 400 /
acc 20, 50 Hz jittery setpoints) and the scripted-gait profile (2000 / 80,
20 Hz smooth strokes) with one parameter set?  The record so far measured a
"lag" per tape (330 ms at 400/20 RL, 130 ms at 2000 RL, <=30 ms at 2000/80
scripted) and concluded the profile SHAPE must be wrong -- but xcorr lag of a
nonlinear rate/accel-limited system depends on the input, so that is not a
test.  This IS the test: simulate the recorded command stream through the
model and compare the predicted joint angle with the measured one.

Tapes (all robot_abs logical degrees, cmd and q in the same frame):
- unloaded hip Bode / small-fast sysid CSVs (sysid/datasets, 50 Hz, cmd+q),
- RL walk tapes ``rl_drive_*.csv`` (50 Hz, 18 joints, write_speed 400..2000),
- scripted stance tapes: robot ``telemetry_*.jsonl`` with ``sync_write``
  (goal + speed + acc, 20 Hz) and ``step`` (position_deg, ~30 Hz) records.

The simulator here is a vectorised numpy port of ``ServoProfile.tick`` over
all channels (one channel = one joint on one tape window), plus optional
structural variants:
  --lowpass   first-order lag (tau) between the profile target and the shaft
  --restart   the servo re-plans from zero velocity whenever a new goal lands
              (a candidate reading of the Feetech firmware)

Run (from prototype_sts3215/):
    PYTHONPATH=$PWD ~/hexapod/.venv/bin/python sysid/fit_servo_profile.py \
        --out ~/.hexapod/analysis/servo_profile_fit [--fit] [--lowpass] [--restart]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

COUNTS_PER_DEG = 4096.0 / 360.0
ACC_UNIT_DEG_S2 = 100.0 * 360.0 / 4096.0   # Feetech acc register unit
AXES = ("yaw", "hip", "knee")
HOME = Path.home()
DATASETS = (HOME / "hexapod/.claude/worktrees/gru-headroom/hexapod_walker/"
            "prototype_sts3215/sysid/datasets")
LAB_RUNS = HOME / ".hexapod/lab_runs"
SIM_MODEL = Path(__file__).resolve().parents[1] / "rl_move/sim/sim_model.json"


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

@dataclass
class Channel:
    tape: str            # tape label (used for grouping + holdout)
    joint: int           # 0..17 robot joint index
    profile: str         # e.g. "400/20"
    loaded: bool
    t_cmd: np.ndarray    # (E,) command write times [s]
    goal: np.ndarray     # (E,) goal deg
    speed: np.ndarray    # (E,) counts/s
    acc: np.ndarray      # (E,) acc units
    t_q: np.ndarray      # (M,) measurement times [s]
    q: np.ndarray        # (M,) measured deg

    @property
    def axis(self) -> str:
        return AXES[self.joint % 3]


def _window_channels(tape, joints, t_cmd, C, S, A, t_q, Q, *, profile,
                     loaded, t0, t1, min_cmd_std=0.4, tag=""):
    """Cut [t0, t1] out of a multi-joint tape into per-joint channels."""
    out = []
    mc = (t_cmd >= t0) & (t_cmd <= t1)
    mq = (t_q >= t0) & (t_q <= t1)
    if mc.sum() < 10 or mq.sum() < 10:
        return out
    for j in joints:
        c = C[mc, j]
        if np.nanstd(c) < min_cmd_std:
            continue
        ok = np.isfinite(Q[mq, j])
        out.append(Channel(tape=tape + tag, joint=j, profile=profile,
                           loaded=loaded, t_cmd=t_cmd[mc], goal=c,
                           speed=S[mc], acc=A[mc], t_q=t_q[mq][ok],
                           q=Q[mq, j][ok]))
    return out


def load_sysid_csv(path: Path, *, speed: float, acc: float, tape: str,
                   loaded: bool = False, cmd_offset_s: float = 0.0):
    """Unloaded sysid battery: per segment, the one moving joint."""
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    t_send = np.array([float(r["t_send_s"]) for r in rows]) + cmd_offset_s
    t_recv = np.array([float(r["t_recv_s"]) for r in rows])
    C = np.array([[float(r[f"cmd{j}_deg"]) for j in range(18)] for r in rows])
    Q = np.array([[float(r[f"q{j}_deg"]) for j in range(18)] for r in rows])
    S = np.full(len(rows), speed)
    A = np.full(len(rows), acc)
    segs = {}
    for i, r in enumerate(rows):
        segs.setdefault(int(r["seg"]), []).append(i)
    chans = []
    for seg, idx in segs.items():
        idx = np.array(idx)
        j = int(rows[idx[0]]["joint"])
        t0, t1 = t_send[idx[0]], t_send[idx[-1]]
        chans += _window_channels(tape, [j], t_send, C, S, A, t_recv, Q,
                                  profile=f"{speed:g}/{acc:g}", loaded=loaded,
                                  t0=t0, t1=t1, tag=f":seg{seg}")
    return chans


def load_rl_csv(path: Path, *, tape: str, max_s: float = 30.0):
    with path.open(newline="") as fh:
        rows = [r for r in csv.DictReader(fh)]
    summ = json.loads(path.with_name(path.stem + "_summary.json").read_text())
    p = summ["params"]
    speed, acc = float(p["write_speed"]), float(p["write_acc"])
    walk = [r for r in rows if r["phase"] == "walk"]
    if len(walk) < 100:
        raise SystemExit(f"{path}: too few walk ticks")

    def f(r, k, default=0.0):
        try:
            return float(r[k])
        except (KeyError, ValueError, TypeError):
            return default
    mono = np.array([f(r, "mono_s") for r in walk])
    # runner order per tick: read q -> obs -> policy -> safety -> write.
    t_cmd = mono + np.array([(f(r, "obs_ms") + f(r, "policy_ms")
                              + f(r, "safety_ms")) / 1e3 for r in walk])
    t_q = mono - np.array([f(r, "position_age_ms") / 1e3 for r in walk])
    C = np.array([[float(r[f"cmd{j}_deg"]) for j in range(18)] for r in walk])
    Q = np.array([[float(r[f"q{j}_deg"]) for j in range(18)] for r in walk])
    S = np.full(len(walk), speed)
    A = np.full(len(walk), acc)
    t0 = mono[0] + 1.0
    t1 = min(mono[-1], t0 + max_s)
    return _window_channels(tape, range(18), t_cmd, C, S, A, t_q, Q,
                            profile=f"{speed:g}/{acc:g}", loaded=True,
                            t0=t0, t1=t1)


def load_scripted_raw(run_dir: Path) -> dict:
    """Robot telemetry of a scripted lab session: the SyncWrite command
    stream (goal deg, speed counts/s, acc units per write), the position
    reads, the body gyro, and the walking bouts (index ranges into the
    command stream where the hips oscillate at the scripted profile)."""
    files = sorted((run_dir / "robot_telemetry").glob("telemetry_*.jsonl"))
    # The robot-side telemetry file is copied into EVERY session whose
    # window overlaps its mtime, so it usually spans the neighbouring
    # sessions too: keep only this session's window (index.json), on the
    # unix clock the lab's events.jsonl also uses.
    win = None
    idx_json = run_dir / "robot_telemetry" / "index.json"
    if idx_json.is_file():
        win = json.loads(idx_json.read_text()).get("session_window_unix")
    sw, st, imu = [], [], []
    for fp in files:
        with fp.open() as fh:
            for line in fh:
                if '"sync_write"' in line:
                    r = json.loads(line)
                    tu = r["time_unix_ns"] / 1e9
                    if win and not (win[0] <= tu <= win[1]):
                        continue
                    sw.append((tu, r["command_deg"],
                               r["speed_counts_s"], r["acc_units"]))
                elif ('"record_type":"step"' in line
                      or '"record_type":"snapshot"' in line):
                    r = json.loads(line)
                    tu = r["time_unix_ns"] / 1e9
                    if win and not (win[0] <= tu <= win[1]):
                        continue
                    if '"record_type":"step"' in line:
                        st.append((tu, r["position_deg"],
                                   r.get("position_age_ms") or 0.0))
                    g = r.get("imu") or {}
                    if g.get("gx_dps") is not None:
                        imu.append((tu, g["gx_dps"], g["gy_dps"], g["gz_dps"]))
    sw.sort(key=lambda x: x[0])
    st.sort(key=lambda x: x[0])
    imu.sort(key=lambda x: x[0])
    t_cmd = np.array([s[0] for s in sw])
    C = np.array([[np.nan if v is None else float(v) for v in s[1]]
                  for s in sw])
    # speed/acc None = "unchanged": carry forward (first write defaults 400/20)
    S = np.zeros(len(sw))
    A = np.zeros(len(sw))
    cs, ca = 400.0, 20.0
    for i, s in enumerate(sw):
        sp = s[2][0] if s[2] and s[2][0] is not None else None
        ac = s[3][0] if s[3] and s[3][0] is not None else None
        if sp is not None:
            cs = float(sp)
        if ac is not None:
            ca = float(ac)
        S[i], A[i] = cs, ca
    # fill NaN goals forward per joint
    for j in range(18):
        col = C[:, j]
        for i in range(1, len(col)):
            if not np.isfinite(col[i]):
                col[i] = col[i - 1]
    t_q = np.array([s[0] for s in st]) - np.array([float(s[2]) / 1e3
                                                   for s in st])
    Q = np.array([[np.nan if v is None else float(v) for v in s[1]]
                  for s in st])
    # Walking bouts = the lab's drive legs (events.jsonl move_start/
    # move_end pairs that are not the recentre walk); fallback = where the
    # hip commands oscillate at the scripted profile, split at > 2 s gaps.
    bouts, labels = [], []
    ev = run_dir / "events.jsonl"
    if ev.is_file():
        start = None
        for line in ev.open():
            r = json.loads(line)
            if r.get("kind") == "move_start":
                start = (float(r["t"]), str(r.get("label", "")))
            elif r.get("kind") == "move_end" and start is not None:
                t0, lab = start
                start = None
                if lab.startswith("recentre"):
                    continue
                bi = np.where((t_cmd >= t0) & (t_cmd <= float(r["t"])))[0]
                if len(bi) >= 50:
                    bouts.append(bi)
                    labels.append(lab)
    if not bouts:
        hip = C[:, 1]
        moving = np.zeros(len(sw), bool)
        for i in range(1, len(sw)):
            moving[i] = abs(hip[i] - hip[i - 1]) > 0.3 and S[i] >= 1000
        idx = np.where(moving)[0]
        if len(idx) < 50:
            raise SystemExit(f"{run_dir}: no scripted walking window found")
        gaps = np.where(np.diff(t_cmd[idx]) > 2.0)[0]
        bouts = [b for b in np.split(idx, gaps + 1) if len(b) >= 50]
        labels = [f"bout{i}" for i in range(len(bouts))]
    return dict(t_cmd=t_cmd, C=C, S=S, A=A, t_q=t_q, Q=Q,
                imu=np.array(imu) if imu else np.zeros((0, 4)), bouts=bouts,
                labels=labels)


def load_scripted_jsonl(run_dir: Path, *, tape: str, max_s: float = 30.0):
    raw = load_scripted_raw(run_dir)
    t_cmd, C, S, A, t_q, Q, bouts = (raw[k] for k in
                                      ("t_cmd", "C", "S", "A", "t_q", "Q", "bouts"))
    chans = []
    for b, bi in enumerate(bouts):
        t0 = t_cmd[bi[0]] - 0.3
        t1 = min(t_cmd[bi[-1]] + 0.5, t0 + max_s)
        prof = f"{S[bi[0]]:g}/{A[bi[0]]:g}"
        chans += _window_channels(tape, range(18), t_cmd, C, S, A, t_q, Q,
                                  profile=prof, loaded=True, t0=t0, t1=t1,
                                  tag=f":leg{b}")
    return chans


# ---------------------------------------------------------------------------
# Vectorised profile simulator
# ---------------------------------------------------------------------------

@dataclass
class Params:
    latency_ms: dict = field(default_factory=lambda: {"yaw": 130.0, "hip": 125.0, "knee": 8.6})
    deadband_deg: dict = field(default_factory=lambda: {"yaw": 0.432, "hip": 0.353, "knee": 0.494})
    acc_scale: float = 1.0      # multiplies the Feetech acc register -> deg/s^2
    vel_scale: float = 1.0      # multiplies the write_speed -> deg/s ceiling
    read_delay_ms: float = 0.0  # extra delay between shaft and logged reading
    tau_ms: float = 0.0         # first-order shaft lag (0 = off)
    restart: bool = False       # re-plan from v=0 on each new goal
    pvel: bool = False          # P-velocity servo: v_des = clip(kp*err, +-vmax), dv <= acc*dt
    kp: float = 20.0            # 1/s, P-velocity gain (pvel only)

    def vec(self, names):
        return np.array([getattr(self, n) if not isinstance(getattr(self, n), dict)
                         else 0.0 for n in names])


class BatchSim:
    """All channels on one fine grid; the trapezoid loop runs over the grid
    with (C,) vectors.  Command streams are pre-rasterised at latency 0 and
    shifted per channel by the axis latency at evaluation time."""

    def __init__(self, chans: list[Channel], dt: float = 0.002,
                 max_s: float = 32.0):
        self.chans = chans
        self.dt = dt
        C = len(chans)
        self.t0 = np.array([min(c.t_cmd[0], c.t_q[0]) - 0.02 for c in chans])
        span = np.array([max(c.t_cmd[-1], c.t_q[-1]) for c in chans]) - self.t0
        self.L = int(math.ceil(min(span.max(), max_s) / dt)) + 2
        L = self.L
        self.goal0 = np.zeros((C, L))
        self.spd0 = np.zeros((C, L))
        self.acc0 = np.zeros((C, L))
        self.q_init = np.zeros(C)
        self.axis_idx = np.array([AXES.index(c.axis) for c in chans])
        for i, c in enumerate(chans):
            k = np.clip(np.round((c.t_cmd - self.t0[i]) / dt).astype(int), 0, L - 1)
            # step function: value of the latest write at/before each grid step
            g = np.full(L, np.nan)
            s = np.full(L, np.nan)
            a = np.full(L, np.nan)
            g[k] = c.goal
            s[k] = c.speed
            a[k] = c.acc
            # forward fill
            for arr, init in ((g, c.q[0]), (s, c.speed[0]), (a, c.acc[0])):
                arr[0] = arr[0] if np.isfinite(arr[0]) else init
                idx = np.where(np.isfinite(arr), np.arange(L), 0)
                np.maximum.accumulate(idx, out=idx)
                arr[:] = arr[idx]
            self.goal0[i] = g
            self.spd0[i] = s
            self.acc0[i] = a
            self.q_init[i] = c.q[0]
        self.n_meas = sum(len(c.q) for c in chans)

    def _shift(self, arr, steps):
        """arr[c, k - steps[c]] with clamp at 0."""
        C, L = arr.shape
        k = np.arange(L)[None, :] - steps[:, None]
        k = np.clip(k, 0, L - 1)
        return np.take_along_axis(arr, k, axis=1)

    def run(self, p: Params) -> np.ndarray:
        """Return Y (C, L): predicted shaft angle on the grid."""
        dt = self.dt
        lat = np.array([p.latency_ms[a] for a in AXES])[self.axis_idx] / 1e3
        db = np.array([p.deadband_deg[a] for a in AXES])[self.axis_idx]
        steps = np.round(lat / dt).astype(int)
        G = self._shift(self.goal0, steps)
        V = self._shift(self.spd0, steps) / COUNTS_PER_DEG * p.vel_scale
        Acc = np.maximum(self._shift(self.acc0, steps) * ACC_UNIT_DEG_S2
                         * p.acc_scale, 1e-6)
        C, L = G.shape
        target = self.q_init.copy()
        v = np.zeros(C)
        y = self.q_init.copy()
        Y = np.empty((C, L))
        alpha = dt / (p.tau_ms / 1e3) if p.tau_ms > 0 else None
        prev_goal = G[:, 0].copy()
        for k in range(L):
            goal = G[:, k]
            if p.restart:
                changed = goal != prev_goal
                v = np.where(changed, 0.0, v)
                prev_goal = goal
            vel_now = V[:, k]
            acc = Acc[:, k]
            err = goal - target
            active = np.abs(err) > db
            if p.pvel:
                # Feetech-style position loop: the velocity setpoint is
                # proportional to the error, clipped to the profile speed,
                # and may only change at the profile acceleration.  No
                # "decelerate to stop at the goal" pre-planning.
                v_des = np.where(active, np.clip(p.kp * err, -vel_now, vel_now), 0.0)
                v_new = v + np.clip(v_des - v, -acc * dt, acc * dt)
                step = v_new * dt
                cross = (np.abs(step) >= np.abs(err)) & (step * err > 0)
                target = np.where(cross, goal, target + step)
                v = np.where(cross, 0.0, v_new)
            else:
                direction = np.sign(err)
                stop_dist = v * v / (2.0 * acc)
                toward = v * direction > 0
                decel = toward & (stop_dist >= np.abs(err))
                dv = np.where(decel, -np.sign(v) * acc, direction * acc) * dt
                v_new = np.clip(v + dv, -vel_now, vel_now)
                step = v_new * dt
                arrive = np.abs(step) >= np.abs(err)
                move = active & ~arrive
                target = np.where(move, target + step,
                                  np.where(active, goal, target))
                v = np.where(move, v_new, 0.0)
            if alpha is not None:
                y = y + np.clip(alpha, 0.0, 1.0) * (target - y)
            else:
                y = target
            Y[:, k] = y
        return Y

    def predict(self, p: Params) -> list[np.ndarray]:
        Y = self.run(p)
        out = []
        grid = np.arange(self.L) * self.dt
        for i, c in enumerate(self.chans):
            tq = c.t_q - self.t0[i] - p.read_delay_ms / 1e3
            out.append(np.interp(tq, grid, Y[i]))
        return out

    def residuals(self, p: Params, weights: dict[str, float]) -> np.ndarray:
        preds = self.predict(p)
        res = []
        for c, pr in zip(self.chans, preds):
            w = weights.get(c.tape.split(":")[0], 1.0)
            res.append((pr - c.q) * w)
        return np.concatenate(res)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def xcorr_lag(a, b, dt, max_lag_s=0.6):
    """lag (s) of b relative to a maximising the correlation; positive = b later."""
    a = a - a.mean()
    b = b - b.mean()
    if a.std() < 1e-9 or b.std() < 1e-9:
        return float("nan"), float("nan")
    n = int(max_lag_s / dt)
    best = (0.0, -2.0)
    for k in range(-n // 4, n + 1):
        if k >= 0:
            x, y = a[:len(a) - k], b[k:]
        else:
            x, y = a[-k:], b[:k]
        if len(x) < 20:
            continue
        r = float(np.corrcoef(x, y)[0, 1])
        if r > best[1]:
            best = (k * dt, r)
    return best


def tape_metrics(chans, preds, dt=0.005):
    """Per (tape, axis): rmse, gain (std q / std cmd) for meas + pred, lag."""
    groups = {}
    for c, pr in zip(chans, preds):
        key = (c.tape.split(":")[0], c.profile, c.axis)
        g = groups.setdefault(key, {"se": 0.0, "n": 0, "gain_m": [], "gain_p": [],
                                    "lag_m": [], "lag_p": [], "loaded": c.loaded})
        g["se"] += float(np.sum((pr - c.q) ** 2))
        g["n"] += len(c.q)
        # resample cmd + q + pred on a common grid for gain/lag
        tt = np.arange(max(c.t_cmd[0], c.t_q[0]), min(c.t_cmd[-1], c.t_q[-1]), dt)
        if len(tt) < 100:
            continue
        cmd = np.interp(tt, c.t_cmd, c.goal)
        qm = np.interp(tt, c.t_q, c.q)
        qp = np.interp(tt, c.t_q, pr)
        cs = cmd.std()
        if cs < 0.3:
            continue
        g["gain_m"].append(qm.std() / cs)
        g["gain_p"].append(qp.std() / cs)
        g["lag_m"].append(xcorr_lag(cmd, qm, dt)[0])
        g["lag_p"].append(xcorr_lag(cmd, qp, dt)[0])
    rows = []
    for (tape, prof, axis), g in sorted(groups.items()):
        rows.append(dict(tape=tape, profile=prof, axis=axis, loaded=g["loaded"],
                         n=g["n"], rmse=math.sqrt(g["se"] / max(g["n"], 1)),
                         gain_meas=float(np.nanmedian(g["gain_m"])) if g["gain_m"] else float("nan"),
                         gain_pred=float(np.nanmedian(g["gain_p"])) if g["gain_p"] else float("nan"),
                         lag_meas_ms=1e3 * float(np.nanmedian(g["lag_m"])) if g["lag_m"] else float("nan"),
                         lag_pred_ms=1e3 * float(np.nanmedian(g["lag_p"])) if g["lag_p"] else float("nan")))
    return rows


def fmt_rows(rows):
    hdr = f"{'tape':28s} {'prof':9s} {'axis':5s} {'n':>6s} {'rmse':>6s} {'gain m/p':>12s} {'lag ms m/p':>14s}"
    lines = [hdr, "-" * len(hdr)]
    for r in rows:
        lines.append(f"{r['tape']:28s} {r['profile']:9s} {r['axis']:5s} {r['n']:6d} "
                     f"{r['rmse']:6.2f} {r['gain_meas']:5.2f}/{r['gain_pred']:5.2f} "
                     f"{r['lag_meas_ms']:6.0f}/{r['lag_pred_ms']:6.0f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tape registry
# ---------------------------------------------------------------------------

def default_tapes():
    ds = DATASETS
    tapes = []
    def sysid(name, speed, acc, tape):
        d = next(ds.glob(name + "*"))
        f = next(d.glob("sysid_*[0-9].csv"))
        tapes.append(("sysid", f, dict(speed=speed, acc=acc, tape=tape)))
    sysid("hip_unloaded_bode_all6_rlprofile_v1", 400, 20, "U_bode3_400")
    sysid("hip_unloaded_bode_all6_amp5_rlprofile_v1", 400, 20, "U_bode5_400")
    sysid("hip_unloaded_smallfast_rlprofile_v1", 400, 20, "U_small_400")
    sysid("hip_unloaded_smallfast_scriptedprofile_v1", 2000, 80, "U_small_2000")
    rl = {"W_rl_400": "20260923-202355-fac7", "W_rl_800": "20260924-070555-9f05",
          "W_rl_1400": "20260924-071000-2a82", "W_rl_2000": "20260924-071144-b318"}
    for tape, run in rl.items():
        f = sorted((LAB_RUNS / run / "robot_telemetry").glob("rl_drive_*[0-9].csv"))[0]
        tapes.append(("rl", f, dict(tape=tape)))
    sc = {"S_knee80": "20260926-142633-ecbc", "S_knee100": "20260926-142741-a394",
          "S_knee84": "20260926-142837-f5ff"}
    for tape, run in sc.items():
        tapes.append(("scripted", LAB_RUNS / run, dict(tape=tape)))
    return tapes


def load_all(names=None):
    chans = []
    for kind, path, kw in default_tapes():
        if names and kw["tape"] not in names:
            continue
        t = time.time()
        if kind == "sysid":
            cs = load_sysid_csv(path, **kw)
        elif kind == "rl":
            cs = load_rl_csv(path, **kw)
        else:
            cs = load_scripted_jsonl(path, **kw)
        print(f"  {kw['tape']:14s} {len(cs):3d} channels  ({time.time()-t:.1f}s)",
              file=sys.stderr)
        chans += cs
    return chans


# ---------------------------------------------------------------------------
# Fit
# ---------------------------------------------------------------------------

FIT_KEYS_BASE = ["lat_yaw", "lat_hip", "lat_knee", "db_yaw", "db_hip", "db_knee",
                 "acc_scale", "vel_scale", "read_delay_ms"]


def params_from_vec(x, keys, base: Params) -> Params:
    p = Params(latency_ms=dict(base.latency_ms), deadband_deg=dict(base.deadband_deg),
               acc_scale=base.acc_scale, vel_scale=base.vel_scale,
               read_delay_ms=base.read_delay_ms, tau_ms=base.tau_ms,
               restart=base.restart, pvel=base.pvel, kp=base.kp)
    for k, v in zip(keys, x):
        if k == "lat_all":
            for a in AXES:
                p.latency_ms[a] = float(v)
        elif k.startswith("lat_"):
            p.latency_ms[k[4:]] = float(v)
        elif k.startswith("db_"):
            p.deadband_deg[k[3:]] = float(v)
        else:
            setattr(p, k, float(v))
    return p


def vec_from_params(p: Params, keys):
    out = []
    for k in keys:
        if k == "lat_all":
            out.append(p.latency_ms["hip"])
        elif k.startswith("lat_"):
            out.append(p.latency_ms[k[4:]])
        elif k.startswith("db_"):
            out.append(p.deadband_deg[k[3:]])
        else:
            out.append(getattr(p, k))
    return np.array(out, float)


BOUNDS = {"lat_all": (0, 300), "lat_yaw": (0, 300), "lat_hip": (0, 300), "lat_knee": (0, 300),
          "db_yaw": (0, 1.5), "db_hip": (0, 1.5), "db_knee": (0, 1.5),
          "acc_scale": (0.05, 40.0), "vel_scale": (0.3, 4.0),
          "read_delay_ms": (-40, 80), "tau_ms": (1, 400), "kp": (1.0, 200.0)}


def fit(sim: BatchSim, base: Params, keys, weights, *, max_nfev=400,
        verbose=1, method="powell"):
    """Derivative-free fit: the latency parameters are quantised to the grid
    step, so finite-difference Jacobians see zero slope (least_squares stalled
    at nfev 6 on the first attempt).  Powell on the scalar RMS works on the
    piecewise-constant landscape; parameters are normalised to their bounds."""
    from scipy.optimize import minimize
    x0 = vec_from_params(base, keys)
    lo = np.array([BOUNDS[k][0] for k in keys], float)
    hi = np.array([BOUNDS[k][1] for k in keys], float)
    x0 = np.clip(x0, lo + 1e-6, hi - 1e-6)
    z0 = (x0 - lo) / (hi - lo)
    n_eval = [0]
    t_start = time.time()
    best = [None, np.inf]

    def fun(z):
        n_eval[0] += 1
        x = lo + np.clip(z, 0.0, 1.0) * (hi - lo)
        p = params_from_vec(x, keys, base)
        r = sim.residuals(p, weights)
        rms = math.sqrt(np.mean(r * r)) + 1e3 * float(np.sum(np.clip(np.abs(z - 0.5) - 0.5, 0, None)))
        if rms < best[1]:
            best[0], best[1] = x.copy(), rms
        if verbose and n_eval[0] % 25 == 1:
            print(f"    eval {n_eval[0]:4d}  rms {rms:.4f}  {time.time()-t_start:5.0f}s  "
                  f"x={np.round(x, 3).tolist()}", file=sys.stderr)
        return rms
    res = minimize(fun, z0, method="Powell",
                   options=dict(maxfev=max_nfev, xtol=1e-3, ftol=1e-5))
    res.nfev = n_eval[0]
    res.cost = best[1]
    return params_from_vec(best[0], keys, base), res


def load_sim_model_params() -> Params:
    blob = json.loads(SIM_MODEL.read_text())
    return Params(latency_ms={a: blob["axes"][a]["latency_ms"] for a in AXES},
                  deadband_deg={a: blob["axes"][a]["deadband_deg"] for a in AXES})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HOME / ".hexapod/analysis/servo_profile_fit")
    ap.add_argument("--fit", action="store_true")
    ap.add_argument("--lowpass", action="store_true", help="fit a first-order shaft lag tau")
    ap.add_argument("--restart", action="store_true", help="re-plan from v=0 on each new goal")
    ap.add_argument("--pvel", action="store_true", help="P-velocity servo loop instead of the trapezoid planner")
    ap.add_argument("--holdout", default="W_rl_1400,S_knee84",
                    help="tapes excluded from the fit (still reported)")
    ap.add_argument("--tapes", default="", help="comma list to restrict the tapes loaded")
    ap.add_argument("--dt", type=float, default=0.002)
    ap.add_argument("--max-nfev", type=int, default=3000)
    ap.add_argument("--label", default="")
    ap.add_argument("--init", type=Path, default=None, help="params json to start from")
    ap.add_argument("--sim-json", type=Path, default=None,
                    help="evaluate a rl_move/sim/sim_model*.json (latency/deadband per axis, "
                         "lowpass_tau_ms, acc_scale, vel_of_write_speed) as the sim would run it")
    ap.add_argument("--fixed", default="", help="comma list of fit keys to hold at their start value")
    ap.add_argument("--shared-latency", action="store_true", help="one latency for yaw/hip/knee")
    ap.add_argument("--start", default="", help="comma list key=value start overrides (lat_hip=60,tau_ms=120,...)")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    print("loading tapes", file=sys.stderr)
    chans = load_all(set(args.tapes.split(",")) if args.tapes else None)
    holdout = set(filter(None, args.holdout.split(",")))
    print(f"{len(chans)} channels total", file=sys.stderr)
    sim = BatchSim(chans, dt=args.dt)
    print(f"grid {sim.L} steps x {len(chans)} channels", file=sys.stderr)

    base = load_sim_model_params()
    if args.init:
        blob = json.loads(args.init.read_text())
        base = Params(**{k: v for k, v in blob.items() if k in Params.__dataclass_fields__})
    if args.sim_json:
        blob = json.loads(args.sim_json.read_text())
        base = Params(latency_ms={a: blob["axes"][a]["latency_ms"] for a in AXES},
                      deadband_deg={a: blob["axes"][a]["deadband_deg"] for a in AXES},
                      acc_scale=float(blob.get("acc_scale", 1.0)),
                      vel_scale=float(blob.get("vel_of_write_speed", 0.0)) or 1.0,
                      read_delay_ms=0.0, tau_ms=float(blob.get("lowpass_tau_ms", 0.0)))
        if not blob.get("vel_of_write_speed"):
            print("note: json has no vel_of_write_speed; vel ceiling modelled as the write speed "
                  "(the sim would clamp at vel_max_deg_s)", file=sys.stderr)
    base.restart = args.restart
    base.pvel = args.pvel
    if args.start:
        kv = [x.split("=") for x in args.start.split(",") if x]
        base = params_from_vec([float(v) for _, v in kv], [k for k, _ in kv], base)
    if args.lowpass and base.tau_ms <= 0:
        base.tau_ms = 60.0

    # per-tape weights: each tape counts equally in the loss (1/sqrt(n_tape))
    counts = {}
    for c in chans:
        counts[c.tape.split(":")[0]] = counts.get(c.tape.split(":")[0], 0) + len(c.q)
    weights = {t: (0.0 if t in holdout else 1.0 / math.sqrt(n)) for t, n in counts.items()}

    t = time.time()
    preds = sim.predict(base)
    print(f"one evaluation: {time.time()-t:.1f}s", file=sys.stderr)
    rows = tape_metrics(chans, preds)
    label = args.label or ("fit" if args.fit else "baseline")
    label += ("+lowpass" if args.lowpass else "") + ("+restart" if args.restart else "") + ("+pvel" if args.pvel else "")
    report = [f"# servo profile model check  ({label})",
              f"start params: {json.dumps(base.__dict__)}", "",
              "## before fit", fmt_rows(rows)]
    print("\n".join(report))

    if args.fit:
        keys = list(FIT_KEYS_BASE) + (["tau_ms"] if args.lowpass else []) + (["kp"] if args.pvel else [])
        if args.shared_latency:
            keys = ["lat_all"] + [k for k in keys if not k.startswith("lat_")]
            base.latency_ms = {a: base.latency_ms["hip"] for a in AXES}
        fixed = set(filter(None, args.fixed.split(",")))
        keys = [k for k in keys if k not in fixed]
        best, res = fit(sim, base, keys, weights, max_nfev=args.max_nfev)
        preds = sim.predict(best)
        rows2 = tape_metrics(chans, preds)
        report += ["", f"## after fit  (nfev {res.nfev}, cost {res.cost:.4f}, status {res.status})",
                   f"fitted params: {json.dumps(best.__dict__)}",
                   f"holdout tapes: {sorted(holdout)}", fmt_rows(rows2)]
        print("\n".join(report[-5:]))
        (args.out / f"params_{label}.json").write_text(json.dumps(best.__dict__, indent=1))
        rows = rows2
    (args.out / f"metrics_{label}.json").write_text(json.dumps(rows, indent=1))
    (args.out / f"report_{label}.md").write_text("\n".join(report) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
