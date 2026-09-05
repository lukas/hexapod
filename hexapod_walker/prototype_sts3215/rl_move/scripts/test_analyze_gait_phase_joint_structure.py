import csv
import hashlib
import json
import math

import pytest

from rl_move.scripts.analyze_gait_phase_joint_structure import AnalysisError, analyze


def _fixture(tmp_path):
    names = ("robot_rl_drive_20260905_192627.csv",
             "robot_rl_drive_20260905_192626_debug.jsonl", "events.csv")
    fields = ["phase", "t_s", "vx_ref_mps", "vy_ref_mps", "max_cur_a"]
    fields += [f"obs{i}" for i in (72, 73, 74)]
    fields += [f"q{i}_deg" for i in range(18)]
    fields += [f"cmd{i}_deg" for i in range(18)]
    fields += [f"cur{i}_a" for i in range(18)]
    with (tmp_path / names[0]).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for tick in range(312):
            phase = 2 * math.pi * 1.333333 * tick / 100
            error = 6.0 if tick in {160, 161, 162, 168, 169, 170, 171,
                                   274, 275, 276, 277, 278, 279, 280, 281, 282} else 1.0
            row = {"phase": "walk", "t_s": tick / 100, "vx_ref_mps": 0.08,
                   "vy_ref_mps": 0.0, "max_cur_a": 0.4,
                   "obs72": math.sin(phase), "obs73": math.cos(phase), "obs74": 0.0}
            row.update({f"q{i}_deg": error for i in range(18)})
            row.update({f"cmd{i}_deg": math.sin(phase + i) for i in range(18)})
            row.update({f"cur{i}_a": 0.01 * i for i in range(18)})
            writer.writerow(row)
    (tmp_path / names[1]).write_text(json.dumps({
        "event": "debug_start", "context": {"walk_obs_dim": 75,
        "walk_policy_name": "fixture", "phase_hz": 1.333333,
        "timing": {"training_hz": 100}, "write_speed": 400, "write_acc": 20}
    }) + "\n")
    (tmp_path / names[2]).write_text("unix_s,elapsed_s,phase,event,detail\n")
    artifacts = []
    for name in names:
        data = (tmp_path / name).read_bytes()
        artifacts.append({"name": name, "bytes": len(data),
                          "sha256": hashlib.sha256(data).hexdigest()})
    (tmp_path / "manifest.json").write_text(json.dumps({"schema_version": 2, "artifacts": artifacts}))
    return hashlib.sha256((tmp_path / "manifest.json").read_bytes()).hexdigest()


def test_analysis_is_deterministic_and_structured(tmp_path):
    manifest = _fixture(tmp_path)
    first = analyze(tmp_path, expected_manifest_sha256=manifest, bootstrap_resamples=100)
    second = analyze(tmp_path, expected_manifest_sha256=manifest, bootstrap_resamples=100)
    assert first == second
    phase, clusters, bootstrap = first
    assert phase["command"]["unique_vx_ref_mps"] == [0.08]
    assert sum(item["outlier_rows"] for item in phase["phase_bins"]) == 16
    assert len([row for row in clusters if row["group"] == "joint"]) == 18
    assert bootstrap["block_lengths_rows"] == [38]
    assert bootstrap["block_comparisons"]["38"]["global"]["observed_outlier_minus_background_deg"] > 0
    assert bootstrap["phase_stratified_null"]["phase_bins"] == 8
    assert bootstrap["phase_stratified_null"]["comparisons"]["global"]["valid_resamples"] > 0


def test_explicit_block_length_reconciliation(tmp_path):
    manifest = _fixture(tmp_path)
    _, _, bootstrap = analyze(
        tmp_path, expected_manifest_sha256=manifest, bootstrap_resamples=100,
        block_lengths_rows=(37, 38), phase_bins=8,
    )
    assert bootstrap["block_lengths_rows"] == [37, 38]
    assert set(bootstrap["block_comparisons"]) == {"37", "38"}
    for comparison in bootstrap["block_comparisons"].values():
        assert set(comparison) == {"global", "coxa", "femur", "tibia"}


def test_manifest_mismatch_fails_closed(tmp_path):
    _fixture(tmp_path)
    with pytest.raises(AnalysisError, match="manifest SHA-256 mismatch"):
        analyze(tmp_path, expected_manifest_sha256="0" * 64, bootstrap_resamples=10)
