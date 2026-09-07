"""Paired CPU diagnostic of a frozen exported actor: nominal vs deployed I/O.

Run from prototype_sts3215 using uv run python -m
rl_move.sim.eval_deployed_transport --actor-json POLICY.json --out OUT.
Defaults to two matched 10-second DR-0 episodes (forward and sideways).
This is a diagnostic, never a physical-robot promotion gate. It does not
load hardware, train, publish results, or change any installed policy.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from rl_move.config import load_config


def asset_provenance(env):
    """Fingerprint the model sources actually selected plus fitted motors."""
    from .eval_checkpoint import model_identity
    from .servo_model import MESH_XML, MESH_MJX_XML, SIM_MODEL_PATH, LOADED_MODEL_PATH
    identity = model_identity(env)
    path = (MESH_XML if identity["model_variant"] == "full_mesh" else
            MESH_MJX_XML if identity["model_variant"] == "mesh_mjx_twin" else None)
    result = {}
    if path is not None:
        xml = path.read_bytes()
        result["xml_path"] = str(path)
        result["xml_sha256"] = hashlib.sha256(xml).hexdigest()
        meshes = {}
        for element in ET.fromstring(xml).findall(".//mesh[@file]"):
            name = Path(element.attrib["file"]).name
            mesh = path.parent / "assets" / name
            meshes[name] = hashlib.sha256(mesh.read_bytes()).hexdigest()
        result["referenced_mesh_sha256"] = dict(sorted(meshes.items()))
        result["referenced_mesh_aggregate_sha256"] = hashlib.sha256(
            json.dumps(meshes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    selected = (env.cfg.get("bus") or {}).get("servo_params") or ""
    motor_path = (LOADED_MODEL_PATH if selected == "loaded" else
                  Path(selected) if selected else SIM_MODEL_PATH)
    result["motor_model_path"] = str(motor_path)
    result["motor_model_sha256"] = (hashlib.sha256(motor_path.read_bytes()).hexdigest()
                                     if motor_path.is_file() else None)
    return result


def reconstructed_config(meta):
    """Known deployed canary fields; unknown training settings stay explicit."""
    cfg = load_config()
    cfg.setdefault("control", {})["hz"] = float(meta["training_hz"])
    cfg.setdefault("env", {})["model_source"] = meta["model_source"]
    cfg.setdefault("bus", {}).update(write_speed=400, write_acc=20)
    # The train.log explicitly resolves 350 counts/s despite write_speed400.
    # Retain the fitted default ceiling, rather than lifting it to400.
    cfg["bus"].pop("servo_vel_max_counts_s", None)
    cfg.setdefault("safety", {}).update(meta.get("safety", {}))
    cfg.setdefault("goal", {}).update(
        walk_pure=1, walk_obs_body_vel=meta["walk_obs_body_vel"],
        walk_phase_obs=meta["walk_phase_obs"], walk_phase_hz=meta["phase_hz"],
        walk_speed_min_m_s=meta["walk_speed_min_m_s"],
        walk_speed_max_m_s=meta["walk_speed_max_m_s"],
        walk_cmd_resample_s=0)
    return cfg


class FrozenActor:
    """Read-only adapter around the exact hardware numpy forward pass."""

    def __init__(self, path):
        from linux_control.rl_policy import NumpyPolicy
        self.policy = NumpyPolicy(path)

    def predict(self, obs, deterministic=True):
        if not deterministic:
            raise ValueError("Exported numpy actor is deterministic only")
        return self.policy.act(obs), None


class RecordingEnv:
    def __init__(self, env):
        self.env = env
        self.true_tilt = []
        self.safe_commands = []
        self.last_info = {}

    def __getattr__(self, name):
        return getattr(self.env, name)

    def reset(self, **kwargs):
        self.true_tilt = []
        self.safe_commands = []
        self.last_info = {}
        return self.env.reset(**kwargs)

    def step(self, action):
        result = self.env.step(action)
        self.safe_commands.append(self.env._cmd.copy())
        self.true_tilt.append(np.asarray(self.env._true_roll_pitch()) * 180 / np.pi)
        self.last_info = result[4]
        return result


class NoisySensorTransport:
    """Opt-in seeded sensor noise injected at the transport acquisition point.

    Wraps a DeployedTransport; every policy tick draws a FIXED-SIZE noise
    block (18 encoder + 3 gyro + 2 accel-tilt draws) from an independent RNG,
    so the sequence is bit-identical across filter arms regardless of which
    draws a given snapshot cadence actually consumes — a matched screen, not
    a robustness gate. Zero scales are exact identity. Noise enters the RAW
    frame (encoder counts, gyro rate, accel-derived tilt) BEFORE the hardware
    velocity/attitude filters, exactly where real sensor noise would.
    Default scales are the campaign's DR noise floors (domain_rand.py):
    encoder 0.09 deg (~1 LSB), gyro 0.5 deg/s, accel-tilt 0.3 deg.
    """

    ALLOWED = {"encoder_noise_deg", "gyro_noise_deg_s", "tilt_noise_deg",
               "seed"}

    def __init__(self, transport, spec: dict):
        unknown = set(spec) - self.ALLOWED
        if unknown:
            raise ValueError(f"Unknown sensor-noise keys: {sorted(unknown)}")
        self._transport = transport
        self.spec = {"encoder_noise_deg": float(spec.get("encoder_noise_deg", .09)),
                     "gyro_noise_deg_s": float(spec.get("gyro_noise_deg_s", .5)),
                     "tilt_noise_deg": float(spec.get("tilt_noise_deg", .3)),
                     "seed": int(spec.get("seed", 0))}
        if any(v < 0 for v in list(self.spec.values())[:3]):
            raise ValueError("sensor-noise scales must be nonnegative")
        self._enc = math.radians(self.spec["encoder_noise_deg"])
        self._gyro = math.radians(self.spec["gyro_noise_deg_s"])
        self._tilt = math.radians(self.spec["tilt_noise_deg"])
        self.reset()

    def __getattr__(self, name):
        return getattr(self._transport, name)

    def reset(self):
        self._rng = np.random.default_rng(self.spec["seed"] + 1_000_003)
        self._transport.reset()

    def acquire(self, raw, *, accel_tilt=None):
        from dataclasses import replace
        draws = self._rng.standard_normal(23)
        raw = replace(
            raw,
            joint_position=raw.joint_position + self._enc * draws[:18],
            imu_gyro=raw.imu_gyro + self._gyro * draws[18:21])
        if accel_tilt is not None:
            accel_tilt = (accel_tilt[0] + self._tilt * draws[21],
                          accel_tilt[1] + self._tilt * draws[22])
        return self._transport.acquire(raw, accel_tilt=accel_tilt)

    def summary(self):
        return {**self._transport.summary(), "sensor_noise": dict(self.spec)}


def run_comparison(actor_json, out, *, seconds=10., headings_deg=(0., 90.),
                   seeds=(0,), config=None, transport=None, sensor_noise=None):
    from hexapod_core.joint_frame import require_robot_abs_joint_frame
    from .eval_checkpoint import _smoothness_fields, model_identity, run_episode
    from .servo_model import motor_contract
    from .walk_task import SimHexapodJointWalkEnv

    actor_json, out = Path(actor_json), Path(out)
    blob = json.loads(actor_json.read_text())
    meta = blob["meta"]
    require_robot_abs_joint_frame(meta, source=str(actor_json))
    if meta.get("yaw_commands") is not False:
        raise ValueError("This bounded evaluator expects a declared no-yaw actor")
    if not (0 < seconds <= 120):
        raise ValueError("seconds must be in (0, 120]")
    cfg = copy.deepcopy(config) if config is not None else reconstructed_config(meta)
    if float(cfg["control"]["hz"]) != float(meta["training_hz"]):
        raise ValueError("Evaluation policy rate differs from actor training_hz")
    if float(cfg["goal"]["walk_obs_body_vel"]) != 2:
        raise ValueError("Hardware canary requires measured velocity := command")
    active = {"enabled": True, "write_hz": 50., "snapshot_hz": 10.,
              "velocity_alpha": .3, "attitude_alpha": .98, **(transport or {})}
    active["enabled"] = True
    conditions = ("nominal", "deployed")
    if sensor_noise is not None:
        # The injector lives at the transport acquisition hook, so the
        # nominal (direct-state) path cannot take matched noise; a noise
        # screen compares deployed arms against their own noise-off runs.
        conditions = ("deployed",)
    report = {
        "diagnostic_only": True, "hardware_motion": False,
        "actor": str(actor_json),
        "actor_sha256": hashlib.sha256(actor_json.read_bytes()).hexdigest(),
        "actor_meta": meta,
        "config_provenance": ("caller_supplied" if config is not None else
                              "reconstructed_from_export_and_train_log"),
        "limitations": [
            "Two short DR-0 directions are diagnostic, not a robustness gate.",
            "Training cfg was not serialized in the frozen zip; unspecified "
            "settings use the checked-out config unless --config is supplied.",
            "Transport events are quantized to policy ticks; sub-tick wire "
            "latency, corruption and robot mechanics are not reproduced.",
            "This cadence/filter diagnostic does not reproduce the live "
            "150ms freshness stop, readiness or controller transitions; "
            "custom long-gap traces are not guarded-runner parity tests.",
            "Simulated current remains an uncalibrated torque proxy.",
            "Return values are not comparable training rewards under an "
            "incompletely reconstructed training cfg.",
        ],
        "seconds": seconds, "rows": [],
    }
    checkpoint = actor_json.with_suffix(".zip")
    if checkpoint.is_file():
        report["checkpoint_sha256"] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    out.mkdir(parents=True, exist_ok=True)
    for seed in seeds:
        for heading in headings_deg:
            for condition in conditions:
                cc = copy.deepcopy(cfg)
                cc["goal"]["walk_heading_set"] = [math.radians(heading)]
                cc["transport"] = (active if condition == "deployed" else
                                   {"enabled": False})
                env = RecordingEnv(SimHexapodJointWalkEnv(
                    cfg=cc, randomize=False, seed=seed, episode_seconds=seconds,
                    render_mode=None))
                if condition == "deployed" and sensor_noise is not None:
                    env.env._deployed_transport = NoisySensorTransport(
                        env.env._deployed_transport, sensor_noise)
                try:
                    if int(env.observation_space.shape[0]) != int(meta["obs_dim"]):
                        raise ValueError("Reconstructed cfg changes actor observation width")
                    ep, _ = run_episode(env, FrozenActor(actor_json),
                                        deterministic=True, video=False, annotate=None)
                    # The generic harness samples commanded_position from
                    # RobotState; in this replay that telemetry is held at
                    # 10Hz. Measure actual safe targets at the policy clock
                    # instead, otherwise sample/hold looks like command jerk.
                    ep.update(_smoothness_fields(env.safe_commands, env))
                    row = {"condition": condition, "seed": seed,
                           "heading_deg": heading, **model_identity(env),
                           "motor_contract": motor_contract(cc, backend="servo_profile_np"),
                           "asset_provenance": asset_provenance(env),
                           "config": cc, "episode": ep,
                           "command_metrics_source": "safe_target_at_policy_rate",
                           "transport": env.last_info.get("transport", {"enabled": False})}
                    if env.true_tilt:
                        row["true_roll_peak_deg"], row["true_pitch_peak_deg"] = (
                            np.max(np.abs(env.true_tilt), axis=0).tolist())
                    report["rows"].append(row)
                    # Save after every completed cell, so a later crash does
                    # not erase the already-completed evidence.
                    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
                    print(json.dumps({"condition": condition, "seed": seed,
                                      "heading_deg": heading,
                                      "terminated": ep["terminated"],
                                      "reason": ep["term_reason"],
                                      "progress_ratio": ep.get("progress_ratio"),
                                      "slip_per_m": ep.get("slip_per_m"),
                                      "model_variant": row["model_variant"]}), flush=True)
                finally:
                    env.close()
    report["complete"] = True
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--actor-json", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--seconds", type=float, default=10)
    ap.add_argument("--headings-deg", type=float, nargs="+", default=[0., 90.])
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--config", type=Path, help="Complete resolved eval cfg JSON")
    ap.add_argument("--transport-config", type=Path,
                    help="Transport-only JSON, including measured jitter/intervals")
    ap.add_argument("--sensor-noise-json", type=str, default=None,
                    help="Opt-in matched sensor-noise JSON for deployed cells "
                         '(e.g. {"encoder_noise_deg":0.09,"gyro_noise_deg_s":'
                         '0.5,"tilt_noise_deg":0.3,"seed":0}); skips nominal')
    args = ap.parse_args()
    run_comparison(args.actor_json, args.out, seconds=args.seconds,
                   headings_deg=args.headings_deg, seeds=args.seeds,
                   config=json.loads(args.config.read_text()) if args.config else None,
                   transport=(json.loads(args.transport_config.read_text())
                              if args.transport_config else None),
                   sensor_noise=(json.loads(args.sensor_noise_json)
                                 if args.sensor_noise_json else None))


if __name__ == "__main__":
    main()
