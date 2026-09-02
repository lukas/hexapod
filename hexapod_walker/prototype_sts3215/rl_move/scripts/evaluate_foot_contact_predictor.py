#!/usr/bin/env python3
"""Evaluate a camera-free foot-contact observer against MuJoCo touch sensors."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from rl_move.contact_predictor import (
    KINEMATIC_CURRENT_FEATURES,
    KINEMATIC_FEATURES,
    PHASE_FEATURES,
    PROPRIOCEPTIVE_FEATURES,
    classification_metrics,
    fit_linear_contact_model,
    load_sim_contact_dataset,
    rounded_metrics,
    transition_window_mask,
)


VARIANTS = {
    "commanded_height_baseline": PHASE_FEATURES,
    "proprioceptive_kinematics": PROPRIOCEPTIVE_FEATURES,
    "command_plus_proprioception": KINEMATIC_FEATURES,
    "command_proprioception_current": KINEMATIC_CURRENT_FEATURES,
}
SELECTED_VARIANT = "command_plus_proprioception"


def _score(truth: np.ndarray, probability: np.ndarray) -> dict[str, object]:
    metrics = classification_metrics(truth, probability >= 0.5)
    metrics["brier_score"] = float(np.mean((probability - truth.astype(float)) ** 2))
    return rounded_metrics(metrics)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim-telemetry", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--model-json", type=Path, required=True)
    parser.add_argument("--transition-window-s", type=float, default=0.15)
    parser.add_argument("--plant-hip-abs-deg", type=float, default=20.0)
    parser.add_argument("--plant-knee-abs-deg", type=float, default=80.0)
    args = parser.parse_args()
    if args.transition_window_s <= 0.0:
        parser.error("--transition-window-s must be positive")

    dataset = load_sim_contact_dataset(
        args.sim_telemetry,
        plant_hip_deg=args.plant_hip_abs_deg,
        plant_knee_deg=args.plant_knee_abs_deg,
    )
    unique_gaits = sorted(int(gait) for gait in np.unique(dataset.gait))
    if len(unique_gaits) < 2:
        parser.error("evaluation needs at least two gaits for held-out validation")
    edge_mask = transition_window_mask(dataset, args.transition_window_s)
    if not np.any(edge_mask):
        parser.error("touch labels contain no contact transitions")

    out_of_fold = {
        name: np.full(len(dataset.contact), np.nan, dtype=float)
        for name in VARIANTS
    }
    folds: list[dict[str, object]] = []
    for held_out_gait in unique_gaits:
        test = dataset.gait == held_out_gait
        train = ~test
        fold: dict[str, object] = {
            "held_out_gait": held_out_gait,
            "train_samples": int(np.sum(train)),
            "test_samples": int(np.sum(test)),
            "contact_rate": round(float(np.mean(dataset.contact[test])), 5),
            "variants": {},
        }
        for name, feature_names in VARIANTS.items():
            train_features = dataset.columns(feature_names)[train]
            test_features = dataset.columns(feature_names)[test]
            model = fit_linear_contact_model(
                train_features, dataset.contact[train], feature_names
            )
            probability = model.predict_proba(test_features)
            out_of_fold[name][test] = probability
            fold_edge = test & edge_mask
            fold["variants"][name] = {
                "all_samples": _score(dataset.contact[test], probability),
                "transition_window": _score(
                    dataset.contact[fold_edge], probability[edge_mask[test]]
                ),
            }
        folds.append(fold)

    aggregate: dict[str, object] = {}
    for name, probability in out_of_fold.items():
        if np.any(~np.isfinite(probability)):
            raise RuntimeError(f"incomplete out-of-fold predictions for {name}")
        aggregate[name] = {
            "all_samples": _score(dataset.contact, probability),
            "transition_window": _score(
                dataset.contact[edge_mask], probability[edge_mask]
            ),
        }

    baseline = aggregate["commanded_height_baseline"]
    selected = aggregate[SELECTED_VARIANT]
    with_current = aggregate["command_proprioception_current"]
    delta_all = (
        selected["all_samples"]["balanced_accuracy"]
        - baseline["all_samples"]["balanced_accuracy"]
    )
    delta_edge = (
        selected["transition_window"]["balanced_accuracy"]
        - baseline["transition_window"]["balanced_accuracy"]
    )
    current_delta = (
        with_current["all_samples"]["balanced_accuracy"]
        - selected["all_samples"]["balanced_accuracy"]
    )

    final_features = dataset.columns(KINEMATIC_FEATURES)
    final_model = fit_linear_contact_model(
        final_features, dataset.contact, KINEMATIC_FEATURES
    )
    model_payload = {
        "schema_version": 1,
        "purpose": "offline observer; not authorized for gait gating",
        "trained_from": str(args.sim_telemetry),
        "plant_robot_abs_deg": [
            0.0, args.plant_hip_abs_deg, args.plant_knee_abs_deg
        ],
        "touch_label_threshold_n": 0.5,
        "model": final_model.to_dict(),
    }
    result = {
        "schema_version": 1,
        "source": str(args.sim_telemetry),
        "validation": {
            "protocol": "leave-one-gait-out",
            "held_out_gaits": unique_gaits,
            "touch_label_threshold_n": 0.5,
            "transition_window_s": args.transition_window_s,
            "samples": int(len(dataset.contact)),
            "contact_rate": round(float(np.mean(dataset.contact)), 5),
            "transition_window_samples": int(np.sum(edge_mask)),
        },
        "variant_features": {
            name: list(features) for name, features in VARIANTS.items()
        },
        "aggregate_out_of_fold": aggregate,
        "folds": folds,
        "selected_variant": SELECTED_VARIANT,
        "comparison": {
            "balanced_accuracy_gain_over_commanded_height_all": round(
                float(delta_all), 5
            ),
            "balanced_accuracy_gain_over_commanded_height_near_transitions": round(
                float(delta_edge), 5
            ),
            "balanced_accuracy_gain_from_current_all": round(
                float(current_delta), 5
            ),
        },
        "verdict": {
            "proprioception_improves_simulated_contact_estimation": bool(
                delta_all > 0.01 and delta_edge > 0.0
            ),
            "current_is_validated_as_incremental_evidence": bool(
                current_delta > 0.005
            ),
            "ready_to_gate_hardware_gait": False,
            "why_not_hardware_ready": (
                "No independent physical foot-contact labels were used; "
                "simulator current does not establish real-servo calibration."
            ),
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.model_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2) + "\n")
    args.model_json.write_text(json.dumps(model_payload, indent=2) + "\n")
    summary = {
        "output": str(args.output_json),
        "model": str(args.model_json),
        "selected": aggregate[SELECTED_VARIANT],
        "baseline": aggregate["commanded_height_baseline"],
        "comparison": result["comparison"],
        "verdict": result["verdict"],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
