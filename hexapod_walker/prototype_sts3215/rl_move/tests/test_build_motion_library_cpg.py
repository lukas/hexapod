"""Tests for build_motion_library.py's --controller se2cpg addition
(cpg track, 08-23, rl_docs/tracks/cpg/STATUS.md Next item 3).

Keeps runs tiny (clip-seconds=1.0, seeds=[0]) -- these are real MuJoCo
CPU rollouts, not mocks, but short enough to run in a couple seconds.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
def _run(args, cwd=ROOT, timeout=60):
    return subprocess.run(
        [sys.executable, "-m", "rl_move.sim.build_motion_library"] + args,
        cwd=cwd, capture_output=True, text=True, timeout=timeout)


def test_se2cpg_requires_params_file():
    r = _run(["--controller", "se2cpg", "--out", "/tmp/_bml_test_noargs",
             "--seeds", "0", "--clip-seconds", "1.0"])
    assert r.returncode != 0
    assert "cpg-params-from" in (r.stdout + r.stderr)


def test_default_controller_unaffected(tmp_path):
    out = tmp_path / "tripod_smoke"
    r = _run(["--out", str(out), "--seeds", "0", "--clip-seconds", "1.0",
             "--min-ticks", "10"])
    assert r.returncode == 0, r.stdout + r.stderr
    manifest = json.loads(Path(str(out) + "_manifest.json").read_text())
    assert manifest["controller"] == "tripod"
    assert manifest["cpg_params"] is None


def test_se2cpg_controller_produces_clips(tmp_path):
    artifact = tmp_path / "cpg_controller_test_v2.json"
    artifact.write_text(json.dumps({
        "kind": "cpg_se2_controller",
        "joint_frame": "robot_abs",
        "joint_contract": "robot_abs_tibia_v2",
        "params": {
            "gait": "tetrapod", "period": 4.0, "swing_frac": 0.20,
            "lift_m": 0.022, "cmd_tau": 0.30,
            "workspace_margin": 0.90,
        },
    }))
    out = tmp_path / "cpg_smoke"
    r = _run(["--controller", "se2cpg", "--cpg-params-from", str(artifact),
             "--out", str(out), "--seeds", "0", "--clip-seconds", "1.0",
             "--min-ticks", "10"])
    assert r.returncode == 0, r.stdout + r.stderr
    manifest = json.loads(Path(str(out) + "_manifest.json").read_text())
    assert manifest["controller"] == "se2cpg"
    assert manifest["cpg_params"]["gait"] == "tetrapod"
    accepted = [c for c in manifest["clips"] if c["accepted"]]
    assert len(accepted) > 0
    # No clip should be dragging (sanity: se2cpg's no-slip pinned-anchor
    # scheme should read well inside the teacher's own reject band).
    for c in accepted:
        assert c["slip_per_m"] < 3.5
