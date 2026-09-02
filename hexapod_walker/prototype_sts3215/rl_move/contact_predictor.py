"""Camera-free foot-contact features and a small linear predictor.

This module deliberately does not alter a gait or write to a servo.  It is an
offline/observer building block: commanded joint angles, encoder angles, and
servo current are converted into per-foot features that can be scored by a
linear logistic model.  Ground-truth touch force is used only while evaluating
the model in MuJoCo.
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT
from hexapod_core.tripod_gait import foot_rz_from_hip_knee


PHASE_FEATURES = ("command_clearance_mm",)
PROPRIOCEPTIVE_FEATURES = (
    "measured_clearance_mm",
    "abs_vertical_speed_mm_s",
    "vertical_speed_mm_s",
    "tracking_error_deg",
)
KINEMATIC_FEATURES = PHASE_FEATURES + PROPRIOCEPTIVE_FEATURES
KINEMATIC_CURRENT_FEATURES = KINEMATIC_FEATURES + (
    "current_sum_a",
    "current_max_a",
)


@dataclass(frozen=True)
class ContactDataset:
    """Flat per-foot samples extracted from a simulator replay."""

    feature_names: tuple[str, ...]
    features: np.ndarray
    contact: np.ndarray
    contact_force_n: np.ndarray
    time_s: np.ndarray
    phase: np.ndarray
    gait: np.ndarray
    direction: np.ndarray
    leg: np.ndarray

    def columns(self, names: Sequence[str]) -> np.ndarray:
        indices = [self.feature_names.index(name) for name in names]
        return self.features[:, indices]


@dataclass(frozen=True)
class LinearContactModel:
    """Standardized logistic-regression contact confidence."""

    feature_names: tuple[str, ...]
    mean: np.ndarray
    scale: np.ndarray
    weights: np.ndarray

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        values = np.asarray(features, dtype=float)
        if values.ndim == 1:
            values = values.reshape(1, -1)
        if values.shape[1] != len(self.feature_names):
            raise ValueError(
                f"expected {len(self.feature_names)} features, "
                f"got {values.shape[1]}"
            )
        standardized = (values - self.mean) / self.scale
        logits = (
            np.column_stack((np.ones(len(values)), standardized)) @ self.weights
        )
        return 1.0 / (1.0 + np.exp(np.clip(-logits, -40.0, 40.0)))

    def to_dict(self) -> dict[str, object]:
        return {
            "model_type": "standardized_logistic_regression",
            "feature_names": list(self.feature_names),
            "mean": self.mean.tolist(),
            "scale": self.scale.tolist(),
            "weights_intercept_first": self.weights.tolist(),
            "probability_threshold": 0.5,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "LinearContactModel":
        return cls(
            feature_names=tuple(str(item) for item in payload["feature_names"]),
            mean=np.asarray(payload["mean"], dtype=float),
            scale=np.asarray(payload["scale"], dtype=float),
            weights=np.asarray(payload["weights_intercept_first"], dtype=float),
        )


@dataclass
class ContactLatch:
    """Turn noisy confidence into a confirmed planted/not-planted state."""

    on_threshold: float = 0.65
    off_threshold: float = 0.35
    confirm_s: float = 0.03
    planted: bool = False
    _candidate: bool | None = None
    _candidate_s: float = 0.0

    def update(self, probability: float, dt_s: float) -> bool:
        probability = float(probability)
        dt_s = max(float(dt_s), 0.0)
        target: bool | None = None
        if not self.planted and probability >= self.on_threshold:
            target = True
        elif self.planted and probability <= self.off_threshold:
            target = False
        if target is None:
            self._candidate = None
            self._candidate_s = 0.0
            return self.planted
        if target != self._candidate:
            self._candidate = target
            self._candidate_s = 0.0
        self._candidate_s += dt_s
        if self._candidate_s + 1e-12 >= self.confirm_s:
            self.planted = target
            self._candidate = None
            self._candidate_s = 0.0
        return self.planted


def leg_feature_values(
    command_deg: Sequence[float],
    measured_deg: Sequence[float],
    current_a: Sequence[float],
    *,
    vertical_speed_mm_s: float,
    plant_hip_deg: float = 20.0,
    plant_knee_deg: float = 80.0,
) -> dict[str, float]:
    """Compute camera-free features for one yaw/hip/knee leg triplet."""
    command = np.asarray(command_deg, dtype=float)
    measured = np.asarray(measured_deg, dtype=float)
    current = np.abs(np.asarray(current_a, dtype=float))
    if command.shape != (3,) or measured.shape != (3,) or current.shape != (3,):
        raise ValueError("command, measured, and current must each have 3 values")
    neutral_z_m = foot_rz_from_hip_knee(plant_hip_deg, plant_knee_deg)[1]
    command_z_m = foot_rz_from_hip_knee(command[1], command[2])[1]
    measured_z_m = foot_rz_from_hip_knee(measured[1], measured[2])[1]
    return {
        "command_clearance_mm": 1000.0 * (command_z_m - neutral_z_m),
        "measured_clearance_mm": 1000.0 * (measured_z_m - neutral_z_m),
        "abs_vertical_speed_mm_s": abs(float(vertical_speed_mm_s)),
        "vertical_speed_mm_s": float(vertical_speed_mm_s),
        "tracking_error_deg": float(np.max(np.abs(measured - command))),
        "current_sum_a": float(np.sum(current)),
        "current_max_a": float(np.max(current)),
    }


def fit_linear_contact_model(
    features: np.ndarray,
    contact: np.ndarray,
    feature_names: Sequence[str],
    *,
    iterations: int = 1000,
    learning_rate: float = 0.08,
    l2: float = 0.02,
) -> LinearContactModel:
    """Fit deterministic class-balanced logistic regression using NumPy."""
    values = np.asarray(features, dtype=float)
    labels = np.asarray(contact, dtype=bool)
    if values.ndim != 2 or values.shape[0] != len(labels):
        raise ValueError("features must be N x F and align with contact labels")
    if not np.any(labels) or np.all(labels):
        raise ValueError("training data must contain contact and non-contact samples")
    mean = values.mean(axis=0)
    scale = values.std(axis=0)
    scale[scale < 1e-9] = 1.0
    design = np.column_stack((np.ones(len(values)), (values - mean) / scale))
    weights = np.zeros(design.shape[1], dtype=float)
    positive_rate = float(np.mean(labels))
    sample_weight = np.where(
        labels, 0.5 / positive_rate, 0.5 / (1.0 - positive_rate)
    )
    numeric_labels = labels.astype(float)
    for _ in range(int(iterations)):
        logits = design @ weights
        probability = 1.0 / (1.0 + np.exp(np.clip(-logits, -40.0, 40.0)))
        gradient = design.T @ ((probability - numeric_labels) * sample_weight)
        gradient /= len(labels)
        gradient[1:] += float(l2) * weights[1:]
        weights -= float(learning_rate) * gradient
    return LinearContactModel(
        feature_names=tuple(feature_names),
        mean=mean,
        scale=scale,
        weights=weights,
    )


def classification_metrics(
    contact: np.ndarray, predicted: np.ndarray
) -> dict[str, object]:
    truth = np.asarray(contact, dtype=bool)
    estimate = np.asarray(predicted, dtype=bool)
    if truth.shape != estimate.shape or truth.size == 0:
        raise ValueError("contact and predicted must be non-empty aligned arrays")
    tp = int(np.sum(truth & estimate))
    tn = int(np.sum(~truth & ~estimate))
    fp = int(np.sum(~truth & estimate))
    fn = int(np.sum(truth & ~estimate))
    recall = tp / max(tp + fn, 1)
    specificity = tn / max(tn + fp, 1)
    precision = tp / max(tp + fp, 1)
    return {
        "samples": int(len(truth)),
        "accuracy": (tp + tn) / len(truth),
        "balanced_accuracy": 0.5 * (recall + specificity),
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": 2.0 * tp / max(2 * tp + fp + fn, 1),
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


def transition_window_mask(dataset: ContactDataset, radius_s: float = 0.15) -> np.ndarray:
    """Select samples close to an actual touch-sensor state transition."""
    mask = np.zeros(len(dataset.contact), dtype=bool)
    groups: dict[tuple[str, int], list[int]] = {}
    for index, (phase, leg) in enumerate(zip(dataset.phase, dataset.leg)):
        groups.setdefault((str(phase), int(leg)), []).append(index)
    for indices in groups.values():
        previous = bool(dataset.contact[indices[0]])
        for index in indices[1:]:
            current = bool(dataset.contact[index])
            if current != previous:
                event_t = float(dataset.time_s[index])
                for nearby in indices:
                    if abs(float(dataset.time_s[nearby]) - event_t) <= radius_s:
                        mask[nearby] = True
            previous = current
    return mask


def load_sim_contact_dataset(
    telemetry_csv: Path,
    *,
    plant_hip_deg: float = 20.0,
    plant_knee_deg: float = 80.0,
) -> ContactDataset:
    """Read a touch-labeled scripted replay into per-foot feature samples."""
    with Path(telemetry_csv).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"no telemetry rows in {telemetry_csv}")
    required = {
        "sim_t_s", "phase", "gait", "direction", "joint_degrees",
        "joint_command_degrees", "joint_currents_a", "foot_contact_force_n",
        "joint_frame", "joint_contract",
    }
    missing = required - set(rows[0])
    if missing:
        raise ValueError(
            f"{telemetry_csv} lacks touch-labeled replay columns: {sorted(missing)}"
        )

    all_feature_names = KINEMATIC_CURRENT_FEATURES
    features: list[list[float]] = []
    contact: list[bool] = []
    contact_force_n: list[float] = []
    times: list[float] = []
    phases: list[str] = []
    gaits: list[int] = []
    directions: list[str] = []
    legs: list[int] = []
    previous: dict[tuple[str, int], tuple[float, float]] = {}
    for row in rows:
        if row["joint_frame"] != FRAME_ROBOT_ABS:
            raise ValueError(f"expected {FRAME_ROBOT_ABS}, got {row['joint_frame']}")
        if row["joint_contract"] != JOINT_CONTRACT:
            raise ValueError(f"expected {JOINT_CONTRACT}, got {row['joint_contract']}")
        time_s = float(row["sim_t_s"])
        measured = np.asarray(json.loads(row["joint_degrees"]), dtype=float)
        command = np.asarray(json.loads(row["joint_command_degrees"]), dtype=float)
        current = np.asarray(json.loads(row["joint_currents_a"]), dtype=float)
        forces = np.asarray(json.loads(row["foot_contact_force_n"]), dtype=float)
        if measured.shape != (18,) or command.shape != (18,) or current.shape != (18,):
            raise ValueError("joint telemetry rows must contain 18 values")
        if forces.shape != (6,):
            raise ValueError("foot_contact_force_n must contain 6 values")
        for leg in range(6):
            joint_slice = slice(3 * leg, 3 * leg + 3)
            measured_z_m = foot_rz_from_hip_knee(
                measured[joint_slice][1], measured[joint_slice][2]
            )[1]
            key = (row["phase"], leg)
            vertical_speed_mm_s = 0.0
            if key in previous:
                previous_t, previous_z_m = previous[key]
                dt_s = time_s - previous_t
                if dt_s > 1e-9:
                    vertical_speed_mm_s = 1000.0 * (
                        measured_z_m - previous_z_m
                    ) / dt_s
            previous[key] = (time_s, measured_z_m)
            values = leg_feature_values(
                command[joint_slice], measured[joint_slice], current[joint_slice],
                vertical_speed_mm_s=vertical_speed_mm_s,
                plant_hip_deg=plant_hip_deg,
                plant_knee_deg=plant_knee_deg,
            )
            features.append([values[name] for name in all_feature_names])
            force = max(float(forces[leg]), 0.0)
            contact.append(force > 0.5)
            contact_force_n.append(force)
            times.append(time_s)
            phases.append(row["phase"])
            gaits.append(int(row["gait"]))
            directions.append(row["direction"])
            legs.append(leg)
    return ContactDataset(
        feature_names=all_feature_names,
        features=np.asarray(features, dtype=float),
        contact=np.asarray(contact, dtype=bool),
        contact_force_n=np.asarray(contact_force_n, dtype=float),
        time_s=np.asarray(times, dtype=float),
        phase=np.asarray(phases, dtype=object),
        gait=np.asarray(gaits, dtype=int),
        direction=np.asarray(directions, dtype=object),
        leg=np.asarray(legs, dtype=int),
    )


def rounded_metrics(payload: dict[str, object], digits: int = 5) -> dict[str, object]:
    """Round metric floats while leaving counts and nested structure intact."""
    output: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(value, (float, np.floating)) and math.isfinite(float(value)):
            output[key] = round(float(value), digits)
        elif isinstance(value, dict):
            output[key] = rounded_metrics(value, digits)
        else:
            output[key] = value
    return output
