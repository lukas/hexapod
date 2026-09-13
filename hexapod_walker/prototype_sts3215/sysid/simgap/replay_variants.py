"""Replay the 25 pinned hexapod2 traces through physics VARIANTS and score each
variant on what the RL policies feel: body roll (peak, waveform, rank order across
runs), joint tracking, and per-foot stance/swing statistics.

Built on rl_move.sim.replay_trace._ReplaySim (same plant, servo model and IMU
estimator as rl_move.sim.replay_hexapod2_matrix).  Adds to that tool:

* Spearman/Pearson correlation of hardware vs simulated peak roll across runs
  (the lab's 2026-09-13 note: the twin's roll was uncorrelated with the robot's,
  rho = -0.43 on 9 runs; a candidate that only shifts the median has learned
  nothing transferable).
* foot stance statistics from simulated pad velocity, with the same thresholds
  the side-camera motion labels use (stance < 30 mm/s, swing > 77 mm/s), so the
  vision timelines in /data/results/simgap on the vision pod can be compared.
* per-tick time series dumped to an .npz per run for spectra and plots.
* a static hold probe: torque per joint at the recorded hold pose, to turn the
  measured hold droop into a per-joint stiffness estimate.

Usage (from prototype_sts3215, data fetched by replay_hexapod2_matrix --fetch-only):

    uv run python -m sysid.simgap.replay_variants --variant baseline
    uv run python -m sysid.simgap.replay_variants --variant mu0.6
    uv run python -m sysid.simgap.replay_variants --variant series:sysid/simgap/variants/backlash_1deg.json
    uv run python -m sysid.simgap.replay_variants --hold-probe

Variant grammar: comma-separated tokens
    baseline | air | mu<float> | com<x>,<y>,<z>(mm) | series:<json> | mount:<json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from rl_move.sim.replay_hexapod2_matrix import (
    DEFAULT_DATA_DIR, DEFAULT_MANIFEST, _entry_path, _passes_attitude_gate,
    load_manifest)
from rl_move.sim.replay_trace import _ReplaySim, analyze, load_trace
from rl_move.sim.servo_model import (LOADED_MODEL_PATH, SIM_MODEL_PATH,
                                     SimServoParams)

HERE = Path(__file__).resolve().parent
OUT_ROOT = Path("/tmp/simgap/variants")
STANCE_MM_S = 30.0   # vision label: tip speed < 0.7 px/frame at 30 fps, ~0.7 px/mm
SWING_MM_S = 77.0    # vision label: > 1.8 px/frame


def parse_variant(spec: str) -> dict:
    v = {"name": spec.replace("/", "_").replace(":", "-"), "mu": 0.0, "params": "loaded",
         "com": (0., 0., 0.), "series": None, "mount": None, "torque": 1.0, "kp": 1.0, "friction": None}
    for tok in spec.split(","):
        tok = tok.strip()
        if tok in ("", "baseline"):
            continue
        if tok == "air":
            v["params"] = "air"
        elif tok.startswith("mu"):
            v["mu"] = float(tok[2:])
        elif tok.startswith("com"):
            v["com"] = tuple(float(x) for x in tok[3:].split("/"))
        elif tok.startswith("series:"):
            v["series"] = Path(tok[7:])
        elif tok.startswith("mount:"):
            v["mount"] = Path(tok[6:])
        elif tok.startswith("torque"):
            v["torque"] = float(tok[6:])      # scale the 2.2 N m actuator clamp
        elif tok.startswith("kp"):
            v["kp"] = float(tok[2:])          # scale fitted kp (all axes)
        elif tok.startswith("friction"):
            v["friction"] = float(tok[8:])    # joint frictionloss N m (stiction proxy)
        else:
            raise SystemExit(f"unknown variant token {tok!r}")
    return v


def build_sim(v: dict) -> _ReplaySim:
    params = SimServoParams.load(LOADED_MODEL_PATH if v["params"] == "loaded" else SIM_MODEL_PATH)
    series = mount = None
    if v["series"] is not None:
        from rl_move.sim.joint_series_flex import from_cfg
        blob = json.loads(Path(v["series"]).read_text())
        section = blob.get("joint_series_flex", blob)
        series = from_cfg({"joint_series_flex": {**section, "enabled": 1}})
    if v["mount"] is not None:
        from rl_move.sim.leg_mount_flex import from_cfg as mount_from_cfg
        blob = json.loads(Path(v["mount"]).read_text())
        section = blob.get("leg_mount_flex", blob)
        mount = mount_from_cfg({"leg_mount_flex": {**section, "enabled": 1}})
    if v["kp"] != 1.0:
        for ax in params.axes.values():
            ax.kp *= v["kp"]
    sim = _ReplaySim(params, mu=v["mu"], com_shift_mm=v["com"], model_source="mesh",
                     leg_mount_flex=mount, joint_series_flex=series)
    if v["torque"] != 1.0:
        from rl_move.sim.servo_model import apply_params_to_model
        apply_params_to_model(sim.model, params, torque_scale=v["torque"])
    if v["friction"] is not None:
        from rl_move.sim.servo_model import joint_ids
        import mujoco
        for jid in joint_ids(sim.model):
            sim.model.dof_frictionloss[sim.model.jnt_dofadr[jid]] = v["friction"]
    return sim


def stance_stats(t: np.ndarray, foot_xyz: np.ndarray, foot_f: np.ndarray) -> dict:
    """Per-foot stance/swing from pad speed (vision-comparable) and from contact force."""
    dt = np.gradient(t)
    vel = np.gradient(foot_xyz, axis=0) / dt[:, None, None]
    speed = np.linalg.norm(vel[:, :, :2], axis=2) * 1000.0  # horizontal mm/s (camera sees mostly this)
    stance = speed < STANCE_MM_S
    swing = speed > SWING_MM_S
    contact = foot_f > 0.05
    n_contact = contact.sum(1)
    n_stance = stance.sum(1)
    return {
        "stance_duty_per_foot": [round(float(x), 3) for x in stance.mean(0)],
        "contact_duty_per_foot": [round(float(x), 3) for x in contact.mean(0)],
        "mean_feet_in_contact": round(float(n_contact.mean()), 2),
        "frac_ticks_contact_le3": round(float(np.mean(n_contact <= 3)), 3),
        "frac_ticks_contact_le2": round(float(np.mean(n_contact <= 2)), 3),
        "frac_ticks_all_stationary": round(float(np.mean(n_stance == 6)), 3),
        "mean_feet_stationary": round(float(n_stance.mean()), 2),
        "mean_feet_swinging": round(float(swing.sum(1).mean()), 2),
        # contact but sliding: a foot on the ground moving faster than the swing threshold
        "frac_contact_sliding": round(float(np.mean(swing & contact)), 4),
        "foot_z_min_mm_per_foot": [round(float(x), 1) for x in (foot_xyz[:, :, 2].min(0) * 1000)],
        "foot_lift_p95_mm": [round(float(x), 1) for x in (np.percentile(foot_xyz[:, :, 2], 95, axis=0) * 1000)],
    }


def spectrum(t: np.ndarray, x: np.ndarray, stride_hz: float) -> dict:
    x = np.nan_to_num(x - np.nanmean(x))
    dt = float(np.median(np.diff(t)))
    f = np.fft.rfftfreq(len(x), dt)
    P = np.abs(np.fft.rfft(x)) ** 2
    tot = P[f > 0.2].sum() + 1e-9

    def band(a, b):
        return round(float(P[(f >= a) & (f < b)].sum() / tot), 3)
    m = (f >= 0.3) & (f <= 12)
    dom = float(f[np.argmax(P * m)]) if m.any() else float("nan")
    return {"dom_hz": round(dom, 2), "sub": band(0.2, 0.7 * stride_hz),
            "stride": band(0.7 * stride_hz, 1.4 * stride_hz),
            "x2": band(1.4 * stride_hz, 2.6 * stride_hz), "hi": band(2.6 * stride_hz, 12.0)}


def stride_hz_of(t: np.ndarray, cmd_deg: np.ndarray) -> float:
    dt = float(np.median(np.diff(t)))
    f = np.fft.rfftfreq(len(t), dt)
    vals = []
    for j in range(2, 18, 3):
        x = cmd_deg[:, j] - cmd_deg[:, j].mean()
        P = np.abs(np.fft.rfft(x)) ** 2
        P[f < 0.3] = 0
        vals.append(f[np.argmax(P)])
    return float(np.median(vals))


def rank_corr(a, b) -> tuple[float, float]:
    a = np.asarray(a, float); b = np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    if len(a) < 3:
        return float("nan"), float("nan")
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    rho = float(np.corrcoef(ra, rb)[0, 1])
    r = float(np.corrcoef(a, b)[0, 1])
    return rho, r


def run_variant(spec: str, entries: list[dict], data_dir: Path, out_root: Path, limit: int = 0) -> dict:
    v = parse_variant(spec)
    out_dir = out_root / v["name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    sim = build_sim(v)
    records = []
    for i, e in enumerate(entries, 1):
        if limit and i > limit:
            break
        path = _entry_path(data_dir, e)
        tr = load_trace(path)
        res = sim.replay(tr)
        an = analyze(tr, res)
        stride = stride_hz_of(tr["t"], tr["cmd"])
        hw_roll_rel = tr["roll"] - tr["ref_roll"]
        sim_roll_rel = res["imu_roll"] - res["ref_imu_roll"]
        rec = {
            "run_id": e["run_id"], "filename": e["filename"], "family": e.get("family"),
            "split": e["split"], "command": e.get("command"), "stride_hz": round(stride, 2),
            **{k: an[k] for k in ("q_rmse_moving_deg", "hw_peak_roll_rel_deg", "sim_peak_roll_rel_deg",
                                  "sim_true_peak_roll_rel_deg", "roll_waveform_rmse_deg",
                                  "pitch_waveform_rmse_deg", "sim_speed_mm_s")},
            "hw_roll_rms": round(float(np.std(hw_roll_rel)), 2),
            "sim_roll_rms": round(float(np.std(sim_roll_rel)), 2),
            "hw_pitch_rms": round(float(np.std(tr["pitch"] - tr["ref_pitch"])), 2),
            "sim_pitch_rms": round(float(np.std(res["imu_pitch"] - res["ref_imu_pitch"])), 2),
            "hw_roll_spec": spectrum(tr["t"], hw_roll_rel, stride),
            "sim_roll_spec": spectrum(tr["t"], sim_roll_rel, stride),
            "hw_gyro_x_rms": round(float(np.sqrt(np.mean(tr["gyro_x"] ** 2))), 1),
            "sim_gyro_x_rms": round(float(np.sqrt(np.mean(res["gyro_x"] ** 2))), 1),
            "sim_stance": stance_stats(tr["t"], res["foot_xyz"], res["foot_f"]),
            "sim_tau_abs_p95_hip_knee": [round(float(np.percentile(np.abs(res["tau_nm"][:, 1::3]), 95)), 2),
                                         round(float(np.percentile(np.abs(res["tau_nm"][:, 2::3]), 95)), 2)],
            "sim_max_series_flex_deg": an.get("sim_max_series_flex_deg"),
        }
        rec["attitude_gate_pass"] = _passes_attitude_gate(rec)
        records.append(rec)
        np.savez_compressed(out_dir / f"{e['run_id']}__{Path(e['filename']).stem}.npz",
                            t=tr["t"], hw_roll=hw_roll_rel, hw_pitch=tr["pitch"] - tr["ref_pitch"],
                            hw_gyro_x=tr["gyro_x"], hw_q=tr["q"], cmd=tr["cmd"],
                            sim_roll=sim_roll_rel, sim_true_roll=res["roll"] - res["ref_roll"],
                            sim_pitch=res["imu_pitch"] - res["ref_imu_pitch"], sim_gyro_x=res["gyro_x"],
                            sim_q=res["q"], foot_f=res["foot_f"], foot_xyz=res["foot_xyz"],
                            tau=res["tau_nm"], base_xyz=res["base_xyz"])
        print(f"[{i:02d}/{len(entries)}] {spec:<28} {rec['split']:<7} {rec['family'][:20]:<20} "
              f"roll sim/hw={rec['sim_peak_roll_rel_deg']:.1f}/{rec['hw_peak_roll_rel_deg']:.1f} "
              f"rms={rec['sim_roll_rms']:.2f}/{rec['hw_roll_rms']:.2f} q={rec['q_rmse_moving_deg']:.1f} "
              f"feet={rec['sim_stance']['mean_feet_in_contact']:.2f} "
              f"{'PASS' if rec['attitude_gate_pass'] else 'fail'}", flush=True)
    summ = summarize(records)
    out = {"variant": spec, "parsed": {k: (str(x) if isinstance(x, Path) else x) for k, x in v.items()},
           "summary": summ, "records": records}
    (out_dir / "result.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(summ, indent=1))
    return out


def summarize(records: list[dict]) -> dict:
    out = {}
    for split in ("fit", "holdout", "all"):
        rows = [r for r in records if split == "all" or r["split"] == split]
        if not rows:
            continue
        hw = [r["hw_peak_roll_rel_deg"] for r in rows]
        sm = [r["sim_peak_roll_rel_deg"] for r in rows]
        rho, r_ = rank_corr(hw, sm)
        rho_rms, _ = rank_corr([r["hw_roll_rms"] for r in rows], [r["sim_roll_rms"] for r in rows])
        out[split] = {
            "n": len(rows), "gate": int(sum(r["attitude_gate_pass"] for r in rows)),
            "median_peak_abs_err": round(float(np.median([abs(a - b) for a, b in zip(hw, sm)])), 2),
            "median_wave_rmse": round(float(np.median([r["roll_waveform_rmse_deg"] for r in rows])), 2),
            "median_q_rmse": round(float(np.median([r["q_rmse_moving_deg"] for r in rows])), 2),
            "spearman_peak": round(rho, 2), "pearson_peak": round(r_, 2), "spearman_rms": round(rho_rms, 2),
            "median_sim_over_hw_peak": round(float(np.median(np.array(sm) / np.maximum(np.array(hw), 1e-6))), 2),
            "median_sim_over_hw_rms": round(float(np.median([r["sim_roll_rms"] / max(r["hw_roll_rms"], 1e-6) for r in rows])), 2),
            "mean_feet_in_contact": round(float(np.mean([r["sim_stance"]["mean_feet_in_contact"] for r in rows])), 2),
        }
    fam = {}
    for r in records:
        fam.setdefault(r["family"], []).append(r)
    out["per_family"] = {f: {"n": len(rs),
                             "hw_peak_med": round(float(np.median([r["hw_peak_roll_rel_deg"] for r in rs])), 2),
                             "sim_peak_med": round(float(np.median([r["sim_peak_roll_rel_deg"] for r in rs])), 2),
                             "hw_rms_med": round(float(np.median([r["hw_roll_rms"] for r in rs])), 2),
                             "sim_rms_med": round(float(np.median([r["sim_roll_rms"] for r in rs])), 2),
                             "gate": int(sum(r["attitude_gate_pass"] for r in rs))}
                         for f, rs in fam.items()}
    return out


def hold_probe(entries: list[dict], data_dir: Path, variant: str = "baseline") -> dict:
    """Static torque per joint at each trace's recorded hold pose (rigid model), so the
    measured hold droop (q - cmd during 'hold') becomes k = tau / droop per joint."""
    import csv
    v = parse_variant(variant)
    sim = build_sim(v)
    rows_out = []
    for e in entries:
        path = _entry_path(data_dir, e)
        with path.open(newline="") as fh:
            rows = list(csv.DictReader(fh))
        hold = [r for r in rows if r.get("phase") == "hold"]
        if len(hold) < 20:
            continue
        hold = hold[len(hold) // 2:]
        q = np.array([[float(r[f"q{j}_deg"]) for j in range(18)] for r in hold])
        cmd = np.array([[float(r[f"cmd{j}_deg"]) for j in range(18)] for r in hold])
        if np.abs(q - cmd).max() > 8.0:   # not a settled hold (transition rows)
            continue
        droop = (q - cmd).mean(0)
        pose = cmd.mean(0)
        n = 150
        tr = {"t": np.arange(n) / 50.0, "q": np.repeat(pose[None], n, 0), "cmd": np.repeat(pose[None], n, 0)}
        res = sim.replay(tr, settle_s=1.0)
        tau = res["tau_nm"][-25:].mean(0)
        ff = res["foot_f"][-25:].mean(0)
        sim_droop = (res["q"][-25:].mean(0) - pose)
        rows_out.append({"run_id": e["run_id"], "family": e.get("family"), "pose_hip": [round(float(x), 1) for x in pose[1::3]],
                         "pose_knee": [round(float(x), 1) for x in pose[2::3]],
                         "hw_droop_hip": [round(float(x), 2) for x in droop[1::3]],
                         "hw_droop_knee": [round(float(x), 2) for x in droop[2::3]],
                         "hw_droop_yaw": [round(float(x), 2) for x in droop[0::3]],
                         "sim_droop_hip": [round(float(x), 2) for x in sim_droop[1::3]],
                         "sim_droop_knee": [round(float(x), 2) for x in sim_droop[2::3]],
                         "tau_hip_nm": [round(float(x), 3) for x in tau[1::3]],
                         "tau_knee_nm": [round(float(x), 3) for x in tau[2::3]],
                         "tau_yaw_nm": [round(float(x), 3) for x in tau[0::3]],
                         "foot_force_n": [round(float(x), 2) for x in ff],
                         "k_hip_nm_rad": [round(float(abs(t) / max(abs(np.radians(d)), 1e-4)), 1) if abs(d) > 0.3 else None for t, d in zip(tau[1::3], droop[1::3])],
                         "k_knee_nm_rad": [round(float(abs(t) / max(abs(np.radians(d)), 1e-4)), 1) if abs(d) > 0.3 else None for t, d in zip(tau[2::3], droop[2::3])]})
        r = rows_out[-1]
        print(f"{r['run_id']} {str(r['family'])[:16]:<16} hipdroop={r['hw_droop_hip']} tau_hip={r['tau_hip_nm']} kneedroop={r['hw_droop_knee']} tau_knee={r['tau_knee_nm']} F={r['foot_force_n']} simdroopH={r['sim_droop_hip']}", flush=True)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / f"hold_probe_{v['name']}.json").write_text(json.dumps(rows_out, indent=1))
    return rows_out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--variant", action="append", default=[])
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    ap.add_argument("--out-root", type=Path, default=OUT_ROOT)
    ap.add_argument("--split", choices=("fit", "holdout", "all"), default="all")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--hold-probe", action="store_true")
    a = ap.parse_args(argv)
    man = load_manifest(a.manifest)
    entries = [e for e in man["entries"] if a.split == "all" or e["split"] == a.split]
    if a.hold_probe:
        hold_probe(entries, a.data_dir, a.variant[0] if a.variant else "baseline")
        return 0
    for spec in (a.variant or ["baseline"]):
        run_variant(spec, entries, a.data_dir, a.out_root, a.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
