"""probe_rot60_np_export_parity.py -- one-off evidence: does the numpy
np-JSON export, wrapped in Rot60Policy, give the SAME actions as the
original SB3 checkpoint wrapped in Rot60Policy, for a specific champion
pair?

Why this exists (2026-09-14, walkcurr, closes the "np-JSON export/
runtime wrapper parity" follow-up item's own remaining ask): rot60.py's
own docstring already argues from export_policy_np.py's generic
``_parity_mlp`` check (identical actions for ANY obs, elu/N-layer path,
run through the real ``NumpyMLPNLayerModel`` production loader) that
no NEW numeric re-derivation is needed once ``Rot60Policy`` only ever
calls ``model.predict`` -- permutation happens OUTSIDE predict(), so it
cannot interact with the numpy-vs-torch numerics. This script makes
that argument concrete for the actual bundle_rlonly_v2 champion pair
(the one named in the open STATUS caveat) instead of leaving it as a
general claim: it wraps BOTH the SB3 zip and its own exported JSON in
TWO INDEPENDENT ``Rot60Policy`` instances, feeds both the SAME
sequence of random 72-obs frames with commanded (vx_ref, vy_ref) swept
across every sector (so ``k`` actually changes mid-sequence, exactly
like a real joystick sweep), and reports the worst elementwise action
difference plus every k value visited.

Zero GPU, zero training, <5s. Not a permanent pytest test (depends on
a specific large champion artifact pair, not a repo-wide invariant);
run once per champion pair that needs this confirmation, evidence goes
under logs/ckpt_eval/.

Usage::

    uv run python -m rl_move.sim.probe_rot60_np_export_parity \
        --zip rl_move/sim/policies/<champion>.zip \
        --np-json linux_control/policies/<champion>.json \
        --out logs/ckpt_eval/<name>_rot60_np_parity/report.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .rot60 import OBS_VREF_X, OBS_VREF_Y, Rot60Policy


def sweep_and_compare(model_a, model_b, *, obs_dim: int, samples: int = 400,
                      seed: int = 0, tilt_scale: float = 0.2,
                      tol: float = 1e-4) -> dict:
    """Compare two ``model.predict``-compatible actors, EACH wrapped in
    its own ``Rot60Policy``, on the identical sequence of synthetic
    obs whose commanded heading sweeps every 60deg sector (so ``k``
    changes mid-sequence on both sides identically, since
    ``sector_from_cmd`` is a pure function of ``(vx, vy, last_k)``).

    Pure/model-agnostic (no I/O, no argparse) so it is unit-testable
    with fake stub models -- see test_probe_rot60_np_export_parity.py.
    """
    wrapped_a = Rot60Policy(model_a, tilt_scale=tilt_scale)
    wrapped_b = Rot60Policy(model_b, tilt_scale=tilt_scale)
    rng = np.random.default_rng(seed)
    headings = np.linspace(-np.pi, np.pi, samples, endpoint=False)
    worst = 0.0
    worst_i = -1
    ks_a, ks_b = [], []
    for i, theta in enumerate(headings):
        obs = rng.normal(0, 1, obs_dim).astype(np.float32)
        speed = 0.06
        obs[OBS_VREF_X] = speed * np.cos(theta)
        obs[OBS_VREF_Y] = speed * np.sin(theta)
        a_a, _ = wrapped_a.predict(obs, deterministic=True)
        a_b, _ = wrapped_b.predict(obs, deterministic=True)
        ks_a.append(wrapped_a.k)
        ks_b.append(wrapped_b.k)
        diff = float(np.max(np.abs(np.asarray(a_a) - np.asarray(a_b))))
        if diff > worst:
            worst, worst_i = diff, i
    return {
        "samples": samples,
        "worst_abs_action_diff": worst,
        "worst_sample_index": worst_i,
        "k_sequence_matches": ks_a == ks_b,
        "distinct_k_values_visited": sorted(set(ks_a)),
        "PASS": bool(worst < tol and ks_a == ks_b),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, required=True)
    ap.add_argument("--np-json", type=Path, required=True)
    ap.add_argument("--samples", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tilt-scale", type=float, default=0.2)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    from stable_baselines3 import PPO

    from ..np_policy import load_np_policy

    sb3_model = PPO.load(args.zip, device="cpu")
    np_model = load_np_policy(args.np_json)

    obs_dim = int(sb3_model.observation_space.shape[0])
    assert obs_dim == int(np_model.observation_space.shape[0]), (
        f"obs_dim mismatch: sb3={obs_dim} "
        f"np={np_model.observation_space.shape[0]}")

    report = sweep_and_compare(sb3_model, np_model, obs_dim=obs_dim,
                               samples=args.samples, seed=args.seed,
                               tilt_scale=args.tilt_scale)
    report["zip"] = str(args.zip)
    report["np_json"] = str(args.np_json)
    print(json.dumps(report, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2))
    return 0 if report["PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
