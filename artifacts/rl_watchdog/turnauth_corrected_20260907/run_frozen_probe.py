"""Run the frozen diagnostic matrix; no training or robot code is called."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True, type=Path)
    ap.add_argument("--suffix", required=True, choices=["cont8m", "cigate8m", "scripted"])
    ap.add_argument("--code-sha", required=True)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    code_sha = Path(".code_sha").read_text().strip()
    if code_sha != args.code_sha or code_sha.endswith("-dirty"):
        raise SystemExit(f"Code marker mismatch: {code_sha} != {args.code_sha}")
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out / "report.json").exists():
        raise SystemExit("Refusing to replace an existing completed report")
    spec = json.loads(args.spec.read_text())
    source_suffix = "cont8m" if args.suffix == "scripted" else args.suffix
    entry = next(r for r in spec["policy_runs"] if r["suffix"] == source_suffix)
    sys.path.insert(0, str(Path.cwd()))
    import numpy as np
    import mujoco
    from rl_move.sim import probe_turn_authority as probe
    from rl_move.sim.eval_checkpoint import CONTACT_N, model_identity
    original_make_env = probe.make_env
    observations = []

    def instrumented_make_env(*a, **kw):
        env = original_make_env(*a, **kw)
        identity = model_identity(env)
        if identity["model_variant"] != "full_mesh" or abs(env.dt - .01) > 1e-10:
            raise RuntimeError(f"Requires full-mesh 100 Hz: {identity}, dt={env.dt}")
        rows = []
        original_step = env.step
        initial_phase = None
        resolved_cfg = env.cfg

        def observed_step(action):
            nonlocal initial_phase
            if initial_phase is None:
                initial_phase = float(env._phase)
            before_step = int(env._step_i)
            phase_before = float(env._phase)
            audit_phase_before = getattr(env._mujoco, "phase", None)
            result = original_step(action)
            info = result[4]
            if before_step >= int(round(2 / env.dt)) and info.get("goal_mode") == "walk":
                omega_local = np.zeros(6)
                omega_world = np.zeros(6)
                mujoco.mj_objectVelocity(env.model, env.data, mujoco.mjtObj.mjOBJ_BODY, env._chassis_bid, omega_local, 1)
                mujoco.mj_objectVelocity(env.model, env.data, mujoco.mjtObj.mjOBJ_BODY, env._chassis_bid, omega_world, 0)
                rotation = env.data.xmat[env._chassis_bid].reshape(3, 3)
                rows.append({
                    "contact": [float(env.data.sensordata[x]) > CONTACT_N for x in env._touch_adr],
                    "pad_xy": np.asarray(env.data.xpos[env._pad_bids, :2]).copy(),
                    "chassis_xy": np.asarray(env.data.xpos[env._chassis_bid, :2]).copy(),
                    "vx": float(env._body_vel_xy()[0]),
                    "phase": float(env._phase),
                    "phase_before": phase_before,
                    "audit_phase_before": audit_phase_before,
                    "object_body_wz": float(omega_local[2]),
                    "object_world_wz": float(omega_world[2]),
                    "body_yaw": float(np.arctan2(rotation[1, 0], rotation[0, 0])),
                    "term_reason": info.get("termination_reason", ""),
                    "roll_rel_deg": info.get("roll_rel_deg"),
                    "pitch_rel_deg": info.get("pitch_rel_deg"),
                })
            return result

        env.step = observed_step
        observations.append({"env": env, "rows": rows, "identity": identity,
                             "resolved_cfg": resolved_cfg,
                             "initial_phase": lambda: initial_phase})
        return env

    probe.make_env = instrumented_make_env
    model = width = None
    checkpoint = None if args.suffix == "scripted" else Path(entry["checkpoint"])
    if checkpoint is not None:
        model, width = probe._load_model(checkpoint)
    results = []
    start = time.time()
    for vx, wz in spec["cells"]:
        for phase in spec["phases"]:
            r = probe.rollout(
                model=model, model_obs_width=width, env_cls_kwargs={"cfg_set": entry["cfg_set"]},
                vx_cmd=vx, wz_cmd=wz, seed=spec["seed"], episode_seconds=spec["seconds"],
                policy="scripted" if args.suffix == "scripted" else "checkpoint",
                contact_audit=True, phase_offset=phase,
            )
            rec = observations[-1]
            rows = rec["rows"]
            r["model_identity"] = rec["identity"]
            r["actual_env_start_phase"] = rec["initial_phase"]()
            if rows:
                contacts = np.asarray([x["contact"] for x in rows])
                pads = np.asarray([x["pad_xy"] for x in rows])
                xy = np.asarray([x["chassis_xy"] for x in rows])
                duty = contacts.mean(axis=0)
                swings = (np.diff(contacts.astype(int), axis=0) == -1).sum(axis=0)
                slip = (np.linalg.norm(np.diff(pads, axis=0), axis=2) * contacts[:-1]).sum(axis=0)
                along = float(sum(x["vx"] for x in rows) * .01)
                sacrificed = [i for i in range(6) if duty[i] < .10 or (duty[i] > .95 and swings[i] == 0)]
                r["scored_window_gait"] = {
                    "definition": "Same >CONTACT_N touch threshold and sacrifice criteria as eval_checkpoint, restricted to probe's post-2s scored walk ticks; diagnostic, not a qualification gate rerun.",
                    "n_ticks": len(rows), "contact_threshold_N": CONTACT_N,
                    "duty_cycle": duty.tolist(), "swing_count": swings.tolist(),
                    "sacrificed_legs": sacrificed, "gait_valid": not sacrificed,
                    "slip_center_per_foot_m": slip.tolist(), "slip_center_m_total": float(slip.sum()),
                    "body_path_m": float(np.linalg.norm(np.diff(xy, axis=0), axis=1).sum()),
                    "body_forward_integral_m": along,
                    "slip_per_m_body_forward": float(slip.sum()) / max(along, .05) if abs(vx) > 1e-6 else None,
                    "termination_reason": rows[-1]["term_reason"],
                }
                yaw = np.unwrap([x["body_yaw"] for x in rows])
                r["actual_phase_first_scored_action"] = {"env": rows[0]["phase_before"], "audit": rows[0]["audit_phase_before"], "alignment_verified": False}
                r["independent_body_yaw"] = {"mujoco_object_local_wz_med": float(np.median([x["object_body_wz"] for x in rows])), "mujoco_object_world_wz_med": float(np.median([x["object_world_wz"] for x in rows])), "unwrapped_yaw_change_rad": float(yaw[-1]-yaw[0]), "yaw_change_per_s": float((yaw[-1]-yaw[0])/max((len(rows)-1)*.01,.01)), "definition": "mj_objectVelocity local/world rotational-z and unwrapped chassis Euler yaw; original historical wz metric retained separately"}
            else:
                r["scored_window_gait"] = {"n_ticks": 0, "gait_valid": None, "reason": "no scored ticks"}
            results.append(r)
            am = r.get("contact_audit", {}).get("angmom_check", {})
            print(json.dumps({"cell": [vx, wz], "phase": phase, "fell": r["fell"],
                              "wz_med": r["wz_med"], "impulse_valid": am.get("valid"),
                              "relative_residual": am.get("relative_rms_residual")}), flush=True)
    cfg = observations[-1]["resolved_cfg"]
    cfg_blob = json.dumps(cfg, sort_keys=True, default=str).encode()
    assets = [Path("mesh_mujoco/hexapod_mesh.xml"), Path("mesh_mujoco/hexapod_mesh_mjx.xml"),
              Path("rl_move/sim/sim_model.json"), Path("rl_move/sim/sim_model_loaded.json")]
    assets.extend(sorted(Path("mesh_mujoco/assets").glob("*.stl")))
    meta = {
        "code_sha": code_sha, "policy": args.suffix, "source_run": entry["run"],
        "training_code_sha": entry["original_training_code_sha"], "wandb_id": entry["wandb_id"],
        "checkpoint": str(checkpoint) if checkpoint else None,
        "checkpoint_sha256": sha256(checkpoint) if checkpoint else None,
        "cfg_set": entry["cfg_set"], "resolved_cfg": cfg,
        "resolved_cfg_sha256": hashlib.sha256(cfg_blob).hexdigest(),
        "probe_sha256": sha256(probe.__file__), "runner_sha256": sha256(__file__),
        "asset_sha256": {str(p): sha256(p) for p in assets if p.is_file()},
        "seed": spec["seed"], "phases_requested": spec["phases"], "cells": spec["cells"],
        "episode_seconds": spec["seconds"], "training_steps_added": 0,
        "elapsed_wall_s": time.time() - start,
        "environment": {k: os.environ[k] for k in ["HEXAPOD_MODEL_SOURCE", "CUDA_VISIBLE_DEVICES", "OMP_NUM_THREADS"] if k in os.environ},
        "qualification": "Frozen diagnostic only; existing acceptance limits unchanged. Zero steady-state net yaw impulse alone does not imply absent turning authority.",
    }
    (args.out / "manifest.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
    (args.out / "raw_probe_report.json").write_text(json.dumps({"metadata": meta, "results": results}, indent=2, default=str) + "\n")
    compact = []
    for r in results:
        ca = r.get("contact_audit") or {}
        compact.append({k: r.get(k) for k in ["vx_cmd", "wz_cmd", "phase_offset", "actual_env_start_phase", "scripted_start_phase", "actual_phase_first_scored_action", "independent_body_yaw", "n_walk_ticks", "fell", "wz_med", "wz_err_med", "vx_med", "scored_window_gait"]} | {
            "angmom_check": ca.get("angmom_check"), "support_force_sign_valid": ca.get("support_force_sign_valid"),
            "sum_fz_med_N": ca.get("sum_fz_med_N"), "weight_N": ca.get("weight_N"),
            "bc_anchor_resid": ca.get("bc_anchor_resid"), "per_foot": ca.get("per_foot"),
        })
    report = {"schema": "hexapod.corrected_frozen_turn_probe.v1", "metadata": {k: v for k, v in meta.items() if k not in ["resolved_cfg", "cfg_set", "asset_sha256"]}, "results": compact}
    (args.out / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print("COMPLETE", args.out, flush=True)


if __name__ == "__main__":
    main()
