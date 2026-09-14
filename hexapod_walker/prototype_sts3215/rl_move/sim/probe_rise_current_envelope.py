"""Actuator-current-envelope diagnostic for the `walkcurr` rise gap.

Context (2026-09-14): the `cw-stance50hz-rlonly-risecurlpretrain-s1-
acq15m` acquisition was mechanically SEED-PRUNED (flat reward/ep_len
stagnation) with the flat-start rise corridor never moving off its
47-53mm footprint_err_end_mm band, over_current every episode. That
run's own pre-registered fallback ("if curl-only pretraining also
fails, escalate to a direct actuator-envelope diagnostic ... replacing
the stale BC-anchor-era Imax=0.575A reading which predates the
corrected mesh mass/geometry") is exactly this script: does a purely
geometric, OPEN-LOOP tuck-then-rise trajectory trip `over_current`
under THIS lineage's actual stack (`env.model_source=mesh_mjx`,
`control.hz=50`, raw 18-joint `joint_goal` action space, `safety.
max_delta_q_deg` as launched) — or is the 2.5 A trip still reachable
without ever fighting the task, meaning the walkcurr rise failures are
an RL exploration/timing problem, not a miscalibrated safety cap on
the +66%-mass corrected mesh?

This is a DIAGNOSTIC PROBE ONLY: it replays an existing scripted
reference open-loop (no policy in the loop, nothing trained here, no
motion prior fed to any actor) purely to measure physics. Per
`RL_GOALS.md` rl_only rules this never touches any training lineage;
it answers a physics question about the corrected mesh model.

Usage (CPU, no GPU, no checkpoint):
    uv run python -m rl_move.sim.probe_rise_current_envelope
    uv run python -m rl_move.sim.probe_rise_current_envelope --ref rl_move/sim/refs/rise_ref_belly2plant.npz
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from rl_move.config import load_config
from rl_move.sim.joint_task import SimHexapodJointGoalEnv, q_rad_to_action
from rl_move.sim.servo_model import SimServoParams

ROOT = Path(__file__).resolve().parents[2]

# The cw-stance50hz-rlonly-* lineage's launch stack (verbatim from the
# ledger extra_args of risecurlpretrain-s1-acq15m / -canary2m), minus
# training-only knobs and minus the goal.joint_action_bias_* trim
# (that bias only shifts what a POLICY's raw output means -- applying
# it here, where we command an absolute q_rad target directly via
# q_rad_to_action, would silently offset our intended pose instead of
# reflecting real physics). Only physics-load-bearing keys kept.
LAUNCH_OVERRIDES = {
    ("env", "model_source"): "mesh_mjx",
    ("control", "hz"): 50.0,
    ("safety", "max_delta_q_deg"): 0.75,
}

EPISODE_SECONDS = 15.0


def _make_rise_env(seed: int, episode_seconds: float
                    ) -> SimHexapodJointGoalEnv:
    cfg = load_config()
    for (sec, leaf), val in LAUNCH_OVERRIDES.items():
        cfg.setdefault(sec, {})[leaf] = val
    env = SimHexapodJointGoalEnv(
        params=SimServoParams.from_cfg(cfg), randomize=False,
        dr_scale=0.0, episode_seconds=episode_seconds, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for a in [a for a in vars(gen) if a.startswith("p_")]:
        setattr(gen, a, 0.0)
    gen.p_rise = 1.0
    gen.force_rise_start = "flat"
    return env


def replay_open_loop(ref_path: Path, seed: int,
                      episode_seconds: float = EPISODE_SECONDS) -> dict:
    """Absolute-time (script-clock) open-loop replay of `ref_path`
    through a flat-start rise episode on the walkcurr launch stack.
    Mirrors `probe_stance_pricing.py`'s `replay_script` behavior."""
    env = _make_rise_env(seed, episode_seconds)
    obs, _ = env.reset()
    ref = np.load(ref_path)
    q_ref = ref["q_rad"]
    ref_dt = float(ref["dt"])
    n_ref = len(q_ref)
    cur_max, cur_p95_samples, step = 0.0, [], 0
    term = trunc = False
    reason = None
    while not (term or trunc):
        j = int(round(step * env.dt / ref_dt))
        act = q_rad_to_action(q_ref[min(max(j, 0), n_ref - 1)])
        obs, r, term, trunc, info = env.step(np.asarray(act).ravel())
        cur = env._state.servo_current
        if cur is not None:
            cur_max = max(cur_max, float(np.max(np.abs(cur))))
            cur_p95_samples.append(float(np.max(np.abs(cur))))
        step += 1
        if term:
            reason = info.get("termination_reason")
    h_err = (float(env.data.xpos[env._chassis_bid, 2]) - env._z0
             - env._h_target)
    plant_ok = False
    if not term:
        plant_ok = bool(env.plant_report(height_err_m=h_err)[0])
    p95 = float(np.percentile(cur_p95_samples, 95)) if cur_p95_samples \
        else 0.0
    return {
        "ref": ref_path.name, "seed": seed, "steps": step,
        "term": bool(term), "reason": reason,
        "cur_max_a": round(cur_max, 3), "cur_p95_a": round(p95, 3),
        "h_err_mm": round(1000 * h_err, 1), "plant_ok": plant_ok,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, default=None,
                     help="rise ref npz(s), comma-separated; default = "
                          "both rise_ref_mesh_scripted.npz (mesh-native, "
                          "built post-08-24 correction) and "
                          "rise_ref_belly2plant.npz (legacy, primitive-"
                          "extracted, for contrast)")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--episode-seconds", type=float, default=EPISODE_SECONDS)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    if args.ref is not None:
        refs = [args.ref]
    else:
        refs = [ROOT / "rl_move/sim/refs/rise_ref_mesh_scripted.npz",
                ROOT / "rl_move/sim/refs/rise_ref_belly2plant.npz"]
    seeds = [int(s) for s in args.seeds.split(",")]

    rows = []
    for ref_path in refs:
        for seed in seeds:
            row = replay_open_loop(ref_path, seed, args.episode_seconds)
            rows.append(row)
            print(json.dumps(row))

    out = args.out or (ROOT / "logs/probe_rise_current_envelope.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
