"""probe_turn_compose.py -- zero-training test of a non-RL turn-in-place
COMPOSITION on the amp/50Hz turncurr lineage's own closed freeze gap.

WHY (amp track, rl_docs/tracks/amp/STATUS.md 2026-09-11 ~23:4x): six
independent RL-side single-lever mechanisms (price, dose, budget, risk-
curriculum ramp, direct freeze-charge, RND state-novelty) all failed to
unfreeze the same turn-in-place command class on the
``cw-walk50hz-amp-mesh-m2plain-styleoff-pushfaultturncurr-capsevprob70``
lineage -- a static splayed freeze-crouch every time, video-confirmed
at every lever/dose. That entry's own text names the one remaining,
untried alternative: "a non-RL turn-in-place composition per
any_means ... not a further RND dose or any other reward-side lever".
This is that composition, built as a probe before any packaging
decision (this track's own binding rule: "do not launch another
canary on this axis without that composition design first").

WHAT IT DOES: wraps a real trained checkpoint (the walk role) with a
``_ComposedPolicy`` that swaps ONLY the action on ticks the env itself
already classifies as live turn-in-place (``s_ref<=1e-3 and
abs(wz_ref)>1e-3`` -- the IDENTICAL gating condition as
``walk_task.py``'s ``walk_turn_in_place_tick`` info flag / every
reward-side lever this probe follows up on) for the SAME scripted
``hexapod_core.tripod_gait.TripodGait`` teacher this lineage's own
reward/BC-anchor machinery already treats as ground-truth turn
behavior elsewhere in this codebase (``probe_walk_income.py``,
``probe_turn_authority.py``). Straight-walk ticks are untouched --
the real policy drives them exactly as trained. No new gait code, no
training: this either validates or refutes the composition idea for
a few CPU minutes before any glue/packaging effort is spent on it.

Runs the SAME seed/goal draw twice per episode index: RAW (policy
only, the closed baseline) and COMPOSED (this wrapper), using the
checkpoint's OWN natural walk-mode goal generator (stress_mix +
walk_turn_in_place_frac, matching training/eval distribution -- NOT a
hand-pinned single-segment command) so a single ~20 s episode already
contains a realistic mix of forward and turn-in-place segments.
Reports, per condition: turn ticks seen, mean |achieved wz| during
those ticks (``env._body_wz()``, sampled at predict-time so it
reflects the immediately-prior tick's physics, exactly like
``probe_turn_authority.py``'s own accounting), and the standard
``run_episode`` gait_valid/progress_ratio/slip_per_m/fall fields
(reused verbatim, not reimplemented) plus a frame-strip video pair for
visual confirmation.

Usage (CPU, no GPU, no training):
    uv run --with imageio --with imageio-ffmpeg python -m rl_move.sim.probe_turn_compose \
        rl_move/sim/policies/ppo_goal_cw_walk50hz_amp_mesh_m2plain_styleoff_pushfaultturncurr_capsevprob70_canary2m.zip \
        --episodes 3 --out logs/probe_turn_compose/capsevprob70_canary2m
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]

from hexapod_core.tripod_gait import TripodGait
from rl_move.config import load_config
from rl_move.robot_state import DEG2RAD
from rl_move.sim.eval_checkpoint import (ENV_CLASSES, _save_video,
                                          run_episode)
from rl_move.sim.joint_task import q_rad_to_action
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.train_ppo_sim import _annotate_frame, _parse_cfg_set

# Same constant every scripted-teacher probe in this codebase uses
# (probe_walk_income.py, probe_turn_authority.py, build_motion_library.py
# ...) -- a standing plant angle, model-source-agnostic (pure IK on the
# fixed hardware geometry, not the mesh-vs-primitive collision model).
WALK_PLANT = (20.0, 100.0)
# Commanded-wz -> teacher-omega realization gain (probe_walk_income.py
# TURN_OMEGA_GAIN, the same "scripted turner reference" conversion
# every prior turn-authority/income probe on this exact reward stack
# uses -- not a new constant invented for this tool).
TURN_OMEGA_GAIN = 2.5


class _ComposedPolicy:
    """Wraps a loaded SB3 model; on live turn-in-place ticks (per the
    env's own goal state, not a re-derived heuristic), substitutes the
    scripted TripodGait teacher's action for the policy's. ``compose=
    False`` reduces to a transparent passthrough (the RAW/baseline
    condition), so both conditions replay through the exact same
    ``run_episode`` call with a single boolean flipped.

    ``blend_s`` (default 0.0, bit-exact with the original hard switch
    when left at 0) ramps the teacher/policy mix linearly over that many
    seconds at each mode transition instead of snapping the action
    discontinuously on the tick the gate flips (todaypolicy STATUS,
    2026-09-12: "build a real handoff (smooth blend over the mode-
    transition window, not the probe's hard switch)"). The ramp direction
    is symmetric: it climbs toward the teacher on turn-entry and decays
    back toward the policy on turn-exit at the same per-tick rate
    (``dt / blend_s`` per tick), so a rapid re-toggle can never overshoot
    past [0, 1] or jump discontinuously in either direction."""

    use_sde = False  # tells eval_checkpoint._maybe_reset_gsde_noise to skip

    def __init__(self, model, env, *, compose: bool,
                 omega_gain: float = TURN_OMEGA_GAIN,
                 blend_s: float = 0.0):
        self.model = model
        self.env = env
        self.compose = compose
        self.omega_gain = omega_gain
        self.blend_s = float(blend_s)
        self.gait = TripodGait(vx=0.0)
        self.gait.sync_plant_stance(*WALK_PLANT)
        self.gait.reset_phase()
        self.turn_ticks = 0
        self.total_ticks = 0
        self.wz_turn_abs_sum = 0.0
        self.wz_walk_abs_sum = 0.0
        self.walk_ticks = 0
        self._blend_w = 0.0

    def reset(self) -> None:
        if hasattr(self.model, "reset"):
            self.model.reset()
        self.gait.reset_phase()
        self.turn_ticks = 0
        self.total_ticks = 0
        self.wz_turn_abs_sum = 0.0
        self.wz_walk_abs_sum = 0.0
        self.walk_ticks = 0
        self._blend_w = 0.0

    def predict(self, obs, deterministic: bool = True):
        pol_act, state = self.model.predict(obs, deterministic=deterministic)
        self.total_ticks += 1
        goal = self.env._current_goal()
        turn_tick = False
        wz_ref = 0.0
        if goal is not None:
            s_ref = math.hypot(float(goal.vx_ref), float(goal.vy_ref))
            wz_ref = float(getattr(goal, "wz_ref", 0.0) or 0.0)
            turn_tick = s_ref <= 1e-3 and abs(wz_ref) > 1e-3
        # Keep the teacher continuously synced to the AMBIENT command
        # every tick (turn or not) so a turn segment never starts from
        # a stale/zeroed smoothed velocity -- mirrors how the env's own
        # live BC-anchor teacher (sim_env.py _walk_bc_gait) is driven.
        try:
            wz_body = float(self.env._body_wz())
        except Exception:
            wz_body = float("nan")
        if turn_tick:
            self.turn_ticks += 1
            self.wz_turn_abs_sum += abs(wz_body)
        else:
            self.walk_ticks += 1
            self.wz_walk_abs_sum += abs(wz_body)
        if goal is not None:
            self.gait.set_velocity(vx=float(goal.vx_ref),
                                    vy=float(goal.vy_ref),
                                    omega=wz_ref * self.omega_gain)
        target_w = 1.0 if (self.compose and turn_tick) else 0.0
        if self.blend_s > 0.0:
            dt = float(getattr(self.env, "dt", 0.02))
            step = dt / self.blend_s
            if target_w > self._blend_w:
                self._blend_w = min(target_w, self._blend_w + step)
            else:
                self._blend_w = max(target_w, self._blend_w - step)
        else:
            # blend_s=0: bit-exact hard switch, identical to the
            # original (pre-blend) behavior below.
            self._blend_w = target_w
        if self._blend_w <= 0.0:
            return pol_act, state
        t = self.env._step_i * self.env.dt
        q = np.asarray(self.gait.desired_deg(t)) * DEG2RAD
        teacher_act = q_rad_to_action(q)
        if self._blend_w >= 1.0:
            return teacher_act, state
        pol_arr = np.asarray(pol_act, dtype=np.float64)
        teach_arr = np.asarray(teacher_act, dtype=np.float64)
        blended = (1.0 - self._blend_w) * pol_arr + self._blend_w * teach_arr
        out_dtype = getattr(pol_act, "dtype", np.float32)
        return blended.astype(out_dtype), state

    def summary(self) -> dict:
        return {
            "total_ticks": self.total_ticks,
            "turn_ticks": self.turn_ticks,
            "walk_ticks": self.walk_ticks,
            "mean_abs_wz_turn": (self.wz_turn_abs_sum / self.turn_ticks
                                 if self.turn_ticks else None),
            "mean_abs_wz_walk": (self.wz_walk_abs_sum / self.walk_ticks
                                 if self.walk_ticks else None),
            "blend_s": self.blend_s,
            "final_blend_w": self._blend_w,
        }


def _build_env(cfg_sets: list[str], *, episode_seconds: float, seed: int,
              dr_scale: float):
    cfg = load_config()
    for key, parsed in _parse_cfg_set(cfg_sets).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    env_cls = ENV_CLASSES["joint_walk"]
    env = env_cls(params=SimServoParams.from_cfg(cfg),
                  randomize=dr_scale > 0.0, dr_scale=dr_scale,
                  episode_seconds=episode_seconds, seed=seed, cfg=cfg,
                  render_mode="rgb_array")
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ckpt")
    ap.add_argument("--cfg-set", action="append", default=None)
    ap.add_argument("--episode-seconds", type=float, default=20.0)
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--dr-scale", type=float, default=0.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--deterministic", action=argparse.BooleanOptionalAction,
                    default=True)
    ap.add_argument("--blend-s", type=float, default=0.0,
                    help="mode-transition blend window in seconds "
                         "(0.0 = original hard switch, bit-exact default)")
    args = ap.parse_args()

    from stable_baselines3 import PPO
    model = PPO.load(str(ROOT / args.ckpt) if not Path(args.ckpt).is_absolute()
                     else args.ckpt, device="cpu")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"ckpt": args.ckpt, "episodes": []}

    for k in range(args.episodes):
        seed = args.seed0 + k
        ep_row = {"seed": seed}
        for tag, compose in (("raw", False), ("composed", True)):
            env = _build_env(args.cfg_set or [], episode_seconds=args.episode_seconds,
                             seed=seed, dr_scale=args.dr_scale)
            wrapped = _ComposedPolicy(model, env, compose=compose,
                                      blend_s=args.blend_s)
            ep, frames = run_episode(env, wrapped, deterministic=args.deterministic,
                                     video=True, annotate=_annotate_frame)
            _save_video(frames, out_dir / f"{tag}_{k}")
            ep_row[tag] = {
                "gait_valid": ep.get("gait_valid"),
                "sacrificed_legs": ep.get("sacrificed_legs"),
                "progress_ratio": ep.get("progress_ratio"),
                "slip_per_m": ep.get("slip_per_m"),
                "term_reason": ep.get("term_reason"),
                "terminated": ep.get("terminated"),
                "forward_dist_m": ep.get("forward_dist_m"),
                **wrapped.summary(),
            }
            env.close()
        report["episodes"].append(ep_row)
        print(f"[probe_turn_compose] episode {k} (seed {seed}):")
        for tag in ("raw", "composed"):
            r = ep_row[tag]
            print(f"  {tag:9s} gait_valid={r['gait_valid']} "
                 f"sacrificed={r['sacrificed_legs']} "
                 f"turn_ticks={r['turn_ticks']} "
                 f"mean|wz|_turn={r['mean_abs_wz_turn']} "
                 f"mean|wz|_walk={r['mean_abs_wz_walk']} "
                 f"term={r['term_reason']}")

    (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    print(f"[probe_turn_compose] wrote {out_dir / 'report.json'}")


if __name__ == "__main__":
    main()
