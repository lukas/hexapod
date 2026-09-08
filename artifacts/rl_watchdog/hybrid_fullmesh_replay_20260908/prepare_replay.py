"""Prepare (never launch) the exact twin A/B's full-STL replay."""
from __future__ import annotations
import hashlib, json, math, shlex, sys
from pathlib import Path
import mujoco

ORIGINAL_OLD = Path("/workspace/hexapod_ab_20260908/hexapod_walker/prototype_sts3215")
MAIN = Path("/workspace/hexapod/hexapod_walker/prototype_sts3215")
OLD = ORIGINAL_OLD if ORIGINAL_OLD.is_dir() else MAIN
OLD_RESULTS = (ORIGINAL_OLD / "logs/ab_hybrid_20260908" if ORIGINAL_OLD.is_dir()
               else MAIN / "logs/ckpt_eval/hybridab_yawref_vs_incumbent_20260908")
SOURCE_PINS = {
    "rl_move/config.yaml": "ea90091f567e7efaff0c0614fa6eb1e76bb1b148c81d983bc6ea27571e9252d9",
    "linux_control/standup_modes.json": "4ffd4fb96fe77bc4c1685ac9ab1ca5962cd4531aaca12fb982472210524755f8",
    "rl_move/sim/hybrid_demo.py": "2eac283c1898d937c25bb8359334f427eb445f263553519a351feeea442c764d",
    "rl_move/sim/drive_video.py": "aa1f380debf18453621633dedf99c307d285ba1e498373c6e51945bb3ebf9fbb",
}
# Harness hashes measured in the original runtime tree; base config and exact
# cfg lists independently recovered from its recorded f9da69e7 checkout.
CFG_PINS = {
    "candidate": "a3be32c36215218f64ed4648fbf83e4f72eb734616428e892a62abe5f3c0d228",
    "incumbent": "a2c47394f72a9b64f98bd5ac5ad7bc627a5f98e7bc81b27cafdda8a368224430",
}
NEW = Path("/workspace/hexapod_hybrid_fullmesh_20260908/hexapod_walker/prototype_sts3215")
FROZEN = Path("/workspace/hexapod-turnphase-wt/hexapod_walker/prototype_sts3215")
OUT = NEW / "logs/ab_hybrid_fullmesh_20260908"
ARMS = {
    "candidate": ("cw-robotwalk-turns-20260907-yawref-cigate8m",
                  "61f9c20f0f72d89217a22b47037e33c8dad2f50bfaca0a3d5517f714dd0eeb10"),
    "incumbent": ("cw-walk-allheading-mlp-singleframe-acq1-stdanneal",
                  "bf19e02d569ba41bf41b3ec92f636dfbd575f3831527a6965bf6e8f7be6972a2"),
}
PINS = {
    "mesh_mujoco/hexapod_mesh.xml":
        "7efb8e8a0cb014c0b4bac27c41e7a85e683553168b87d85aac0d52d6a8e5a837",
    "mesh_mujoco/hexapod_mesh_mjx.xml":
        "a8a5ca8ada47621eb1396c841a593983df27b761f5b55cc2c36269c6e54dbe9e",
    "rl_move/sim/sim_model.json":
        "6968268e879eb95603d0801ddd25a59f37a3964eef6839e3b63be3df91fe412d",
    "rl_move/sim/sim_model_loaded.json":
        "144d43fa5dd3bae4eebf1cce47f2f6a8c6f70b3763b36f824d195ca9450273e1",
}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert Path.cwd() == NEW, f"Run from {NEW}"
sys.path.insert(0, str(NEW))
from rl_move.config import load_config
from rl_move.sim.train_ppo_sim import _parse_cfg_set
from rl_move.sim.servo_model import motor_contract

for rel, expected in SOURCE_PINS.items():
    assert sha(NEW / rel) == expected, f"ORIGINAL SOURCE PIN MISMATCH: {rel}"
for rel, expected in PINS.items():
    assert sha(NEW / rel) == expected, f"PIN MISMATCH: {rel}"
# Check every copied asset against the known frozen source, not mass alone.
assets = sorted((FROZEN / "mesh_mujoco/assets").glob("*"))
assert assets
asset_hashes = {}
for src in assets:
    if src.is_file():
        rel = src.relative_to(FROZEN)
        assert sha(NEW / rel) == sha(src), f"ASSET MISMATCH: {rel}"
        asset_hashes[str(rel)] = sha(src)
model = mujoco.MjModel.from_xml_path(str(NEW / "mesh_mujoco/hexapod_mesh.xml"))
assert model.nmesh == 34 and model.ngeom == 159, (model.nmesh, model.ngeom)
assert abs(float(model.body_subtreemass[1]) - 4.80573) < 1e-8
ledger = json.loads((OLD / "rl_move/orchestrator/experiments.json").read_text())
manifest = {
    "purpose": "Matched full-STL replay of completed simplified-twin A/B; no training",
    "original_twin_root": str(ORIGINAL_OLD), "old_twin_results": str(OLD_RESULTS),
    "ledger_checkpoint_source": str(OLD), "source_pins": SOURCE_PINS,
    "cfg_pins": CFG_PINS, "new_fullmesh_root": str(NEW),
    "pin_hashes": PINS, "asset_hashes": asset_hashes,
    "model": {"nmesh": model.nmesh, "ngeom": model.ngeom,
              "mass_kg": float(model.body_subtreemass[1]),
              "physics_dt": float(model.opt.timestep)},
    "arms": {},
}
OUT.mkdir(parents=True, exist_ok=True)
for arm, (run, ckpt_sha) in ARMS.items():
    # EXACT selector copied from ops.sh hybriddemo at the completed A/B.
    entry = fallback = None
    for e in ledger:
        if isinstance(e, dict) and e.get("run") == run and e.get("extra_args"):
            fallback = e
            if e.get("wandb_id") or e.get("checks", {}).get("pid"):
                entry = e
    entry = entry or fallback
    assert entry is not None
    args = entry["extra_args"]
    cfgs, ck, task = [], None, "joint_walk"
    for i, a in enumerate(args):
        if a == "--cfg-set": cfgs.append(args[i + 1])
        elif a == "--out-name": ck = args[i + 1]
        elif a == "--task": task = args[i + 1]
    assert task == "joint_walk"
    cfg_digest = hashlib.sha256(json.dumps(cfgs, separators=(",", ":")).encode()).hexdigest()
    assert cfg_digest == CFG_PINS[arm], (arm, "original cfg-set list changed", cfg_digest)
    ck = ck or "ppo_goal_" + run.replace("-", "_")
    ckpt = Path("rl_move/sim/policies") / (ck + ".zip")
    assert sha(OLD / ckpt) == ckpt_sha and sha(NEW / ckpt) == ckpt_sha
    cfg = load_config()
    for key, value in _parse_cfg_set(cfgs).items():
        section, name = key.split(".", 1)
        cfg.setdefault(section, {})[name] = value
    # Match hybrid_demo's documented runtime overrides.
    cfg.setdefault("env", {})["model_source"] = "mesh"
    cfg.setdefault("goal", {})["walk_park_start_frac"] = 0.0
    contract = motor_contract(cfg, backend="servo_profile_np")
    expected = {"bus.write_speed": 400.0, "bus.write_acc": 20.0,
                "safety.max_delta_q_deg": 0.375, "control.hz": 100.0,
                "resolved_vel_max_counts_s_max": 350.0}
    for key, value in expected.items():
        assert contract[key] == value, (arm, key, contract[key], value)
    old_summary = json.loads((OLD_RESULTS / arm / "summary.json").read_text())
    assert contract == old_summary["motor_contract"], (arm, "motor changed")
    cargs = [x for c in cfgs for x in ("--cfg-set", c)]
    argv = ["uv", "run", "python", "-m", "rl_move.sim.hybrid_demo", str(ckpt),
            *cargs, "--name", run + " hybrid", "--out-dir", str(OUT / arm),
            "--model-source", "mesh", "--stand-mode", "tuck", "--lower-mode", "tuck",
            "--script", "human", "--walk-seconds", "28", "--speed", "0.08",
            "--seed", "0", "--dr-scale", "0", "--policy-mode", "deterministic"]
    record = {"run": run, "checkpoint": str(ckpt), "checkpoint_sha256": ckpt_sha,
              "cfg_set": cfgs, "effective_cfg": cfg, "motor_contract": contract,
              "argv": argv}
    manifest["arms"][arm] = record
    (OUT / (arm + "_argv.json")).write_text(json.dumps(argv, indent=2) + "\n")
    (OUT / (arm + "_effective_cfg.json")).write_text(json.dumps(cfg, indent=2) + "\n")
    # Preparation only. Root explicitly invokes each separate bounded script.
    run_sh = ("#!/usr/bin/env bash\nset -euo pipefail\n"
              + "cd " + shlex.quote(str(NEW)) + "\n"
              + "export HEXAPOD_MODEL_SOURCE=mesh HEXAPOD_CONTROL_HZ=100\n"
              + "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1\n"
              + "exec timeout --signal=TERM --kill-after=30s 600s "
              + shlex.join(argv) + " > " + shlex.quote(str(OUT / (arm + ".log"))) + " 2>&1\n")
    (OUT / ("run_" + arm + ".sh")).write_text(run_sh)
manifest["source_hashes"] = {p: sha(NEW / p) for p in (
    "rl_move/sim/hybrid_demo.py", "rl_move/sim/drive_video.py",
    "rl_move/sim/play_core.py", "rl_move/sim/sim_env.py",
    "rl_move/sim/joint_task.py", "rl_move/sim/servo_model.py",
    "rl_move/config.yaml", "linux_control/standup_modes.json")}
(OUT / "replay_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"prepared": str(OUT), "launched": False,
                  "arms": list(manifest["arms"])}, indent=2))
