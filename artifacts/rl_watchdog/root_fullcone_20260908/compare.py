"""Compare the matched original-plant full-cone rerun to retained raw baselines."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
SCALARS = (
    "wz_cmd", "vx_cmd", "phase_offset", "scripted_start_phase",
    "scripted_stance_radius_scale", "scripted_foot_radius_m", "seed",
    "n_walk_ticks", "n_total_ticks", "modes", "wz_med", "wz_p90_abs",
    "wz_err_med", "frozen_body_wz_err_pred", "vx_med", "vx_err_med", "fell", "cell")


def load(name):
    return json.loads((ROOT / name).read_text())


def pooled_fraction(foot_rows, fraction_key, count_key):
    pairs = [(f[fraction_key], f[count_key]) for f in foot_rows.values()
             if f[fraction_key] is not None and f[count_key] > 0]
    total = sum(n for _, n in pairs)
    return sum(frac * n for frac, n in pairs) / total if total else None


def compare(old, new, name):
    for key in ("engine", "policy", "plant", "seed", "episode_seconds",
                "cfg_set", "checkpoint_sha256", "pin_manifest"):
        assert old[key] == new[key], (name, key, "top-level identity mismatch")
    assert new["engine"] == "audit"
    assert new.get("foot_torsion_mu") is None, "original-plant comparison only"
    assert len(old["results"]) == len(new["results"]) == 6
    rows = []
    for a, b in zip(old["results"], new["results"]):
        for key in SCALARS:
            assert a[key] == b[key], (name, b["cell"], b["phase_offset"], key)
        audit_a, audit = a["contact_audit"], b["contact_audit"]
        for key in audit_a:
            if key != "traction":
                assert audit_a[key] == audit[key], (name, key, "legacy audit mismatch")
        for key in audit_a["traction"]:
            assert audit_a["traction"][key] == audit["traction"][key], (
                name, key, "legacy planar traction mismatch")
        assert audit["angmom_check"]["valid"]
        full = audit["traction"]["full_cone"]
        assert full["valid"] and full["invalid_contact_samples"] == 0
        assert full["observed_condim"] == [6]
        assert full["cone_type"] in ("pyramidal", "elliptic")
        assert audit["model_nmesh"] == 34
        frows = full["per_foot"]
        legacy = audit["traction"]["per_foot"]
        rows.append({
            "controller": name, "cell": b["cell"], "phase_offset": b["phase_offset"],
            "wz_med": b["wz_med"], "vx_med": b["vx_med"], "fell": b["fell"],
            "behavior_bit_identical": True, "legacy_audit_bit_identical": True,
            "full_cone_valid": full["valid"], "cone_type": full["cone_type"],
            "observed_condim": full["observed_condim"],
            "impulse_relative_rms": audit["angmom_check"]["relative_rms_residual"],
            "full_usage_max_med_per_foot": [f["usage_max_med"] for f in frows.values()],
            "normalized_component_max_p90_per_foot": [
                f["normalized_component_max_p90"] for f in frows.values()],
            "full_near_when_slipping_per_foot": [
                f["frac_slip_near_cone"] for f in frows.values()],
            "planar_near_when_slipping_per_foot": [
                f["frac_slip_near_cone"] for f in legacy.values()],
            "full_near_when_slipping_pooled_foot_substep_fraction": pooled_fraction(
                frows, "frac_slip_near_cone", "slip_substeps"),
            "planar_near_when_slipping_pooled_foot_substep_fraction": pooled_fraction(
                legacy, "frac_slip_near_cone", "slip_substeps"),
            "full_low_when_slipping_pooled_foot_substep_fraction": pooled_fraction(
                frows, "frac_slip_low_cone", "slip_substeps"),
            "contact_yaw_force_impulse_per_foot_Nms": audit["per_foot"]["yaw_imp_force_Nms"],
            "contact_yaw_couple_impulse_per_foot_Nms": audit["per_foot"]["yaw_imp_couple_Nms"],
        })
    return rows


def main():
    rows = []
    files = [
        ("original_scripted_audit_fm.json", "scripted_audit_fm.json", "scripted"),
        ("original_ckpt_audit_fm.json", "ckpt_audit_fm.json", "retained_checkpoint"),
    ]
    for old, new, name in files:
        rows.extend(compare(load(old), load(new), name))
    result = {
        "scope": "12 original frozen full-mesh audit cells; no training or changed friction",
        "behavior_and_legacy_audit_bit_identical": True,
        "all_full_cone_and_momentum_checks_valid": True,
        "component_order": ["tangent1", "tangent2", "spin", "roll1", "roll2"],
        "fraction_definition": (
            "pooled across feet, weighted by slipping foot-substep counts; "
            "any positive compressive contact; not independent trials"),
        "limits": [
            "Per-foot material-point slip speed conditions a maximum over that foot's contacts.",
            "Per-component p90 values need not occur at the same contact or time.",
            "Full-cone usage describes solved force budget, not a unique cause of the yaw deficit.",
            "No hardware calibration or changed-plant qualification claim.",
        ],
        "source_files_sha256": {
            fn: hashlib.sha256((ROOT / fn).read_bytes()).hexdigest()
            for pair in files for fn in pair[:2]},
        "rows": rows,
    }
    (ROOT / "comparison.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "rows": len(rows), "all_parity_valid": True,
        "near_full_range": [min(r["full_near_when_slipping_pooled_foot_substep_fraction"]
                               for r in rows),
                            max(r["full_near_when_slipping_pooled_foot_substep_fraction"]
                               for r in rows)],
        "near_planar_range": [min(r["planar_near_when_slipping_pooled_foot_substep_fraction"]
                                 for r in rows),
                              max(r["planar_near_when_slipping_pooled_foot_substep_fraction"]
                                 for r in rows)]}, indent=2))


if __name__ == "__main__":
    main()
