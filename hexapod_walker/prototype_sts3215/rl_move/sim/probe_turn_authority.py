"""probe_turn_authority.py — turn-in-place wz-tracking probe.

WHY (standwalk wave-2 turn-diet canary gate, 08-30): the gate text for
any turn-ticks arm on the walkteach/dualbc lineage names a specific
required instrument — "a turn-in-place probe (tip_ccw/tip_cw rollout
or held wz command) shows real wz tracking (wz_err well below the
frozen-body wz_err~wz_ref prediction)" — that did not exist as a
runnable tool before this: `eval_checkpoint.py` never computes a body
yaw-rate error (its own `info["walk_wz"]`/`reward_walk_yaw` fields are
only populated when `reward.k_walk_yaw > 0`, which the walkteach/dualbc
reward stack never sets as of 08-30 — it relies on BC-anchor imitation
for turning, not the OMNI yaw kernel; STALE as of the yawcredit/turncap
wave, cw-standwalk-stage2-dualbc6-...-cap29-stdwalklo-hi's own ledger
cfg sets `reward.k_walk_yaw=1.0` (plus walk_yaw_kernel_gate/k_yaw_prog/
k_yaw_still/etc) applied to every walk tick — this tool's own combined-
tick reads still hold, this note just no longer describes why the tool
was needed), and the single-mode `eval_cmd_suite`/
`hybrid_demo` session tools do not support this dual-core 4-submode
`joint_walk` checkpoint family at all (documented INCOMPATIBLE-obs-
contract class, standwalk STATUS 08-30).

WHAT IT DOES: holds a fixed body-frame wz command (vx_ref=vy_ref=0,
i.e. a pure turn-in-place segment, matching `test_task_semantics.py`'s
`_turn_rollout` pinned-command convention) for a full episode, steps
either a loaded checkpoint (GRU dual-core auto-detected + threaded
hidden state via `gru_policy.RecurrentPredictor`, exactly like
`eval_checkpoint`) or the scripted `TripodGait` reference (the
`--policy scripted` sanity control — this is what proves the
methodology can measure a REAL nonzero wz at all: the checkpoint-only
read has no independent way to tell "policy achieves ~0 wz" apart from
"probe never captures real wz"), and reads the ALWAYS-computed
`env._body_wz()` every tick (never `info["walk_wz"]`, which is reward-
gated off in this recipe family — see WHY above; a first version of
this tool used the info field and produced a false "frozen body"
result on the scripted control, caught by mismatching the fix's own
env-mechanics sanity check).

Ticks are filtered to `info["goal_mode"] == "walk"` before scoring:
`goal.mode_seq` composes rise/walk/lower/hold SEQUENCES within one
episode even when the goal generator's own per-mode probabilities are
forced to walk-only (verified 08-30: a forced-p_walk=1.0 episode still
transitioned walk -> lower mid-episode) — scoring un-filtered ticks
silently mixes in submodes where zero wz is the CORRECT behavior, not
evidence of a turn-tracking failure.

Usage:
  uv run python -m rl_move.sim.probe_turn_authority CKPT.zip \
      --cfg-set goal.walk_yaw_cmd=1 --cfg-set goal.walk_phase_run_on_yaw=1 \
      --cfg-set env.model_source=mesh --cfg-set control.hz=100 \
      --wz-cmds 0.25,-0.25 --seeds 0,1 --out logs/ckpt_eval/turn_probe.json

  # sanity control (proves the tool can see a real turn at all):
  uv run python -m rl_move.sim.probe_turn_authority --policy scripted \
      --cfg-set env.model_source=mesh --cfg-set control.hz=100 \
      --wz-cmds 0.25,-0.25 --out logs/ckpt_eval/turn_probe_scripted.json

  # COMBINED walk+turn probe (09-03, standwalk redesign-spec item 2
  # sub-step: every prior anchor-coef/turn-authority read here held
  # vx_ref=0 — this crosses a nonzero forward command with wz so the
  # SAME tool answers "does wz/vx tracking hold when both are
  # commanded at once", zero training required either against the
  # scripted teacher (the BC anchor's own target) or a live checkpoint:
  uv run python -m rl_move.sim.probe_turn_authority --policy scripted \
      --cfg-set env.model_source=mesh --cfg-set control.hz=100 \
      --wz-cmds 0.25,-0.25,0.0 --vx-cmds 0.0,0.08 \
      --out logs/ckpt_eval/turn_probe_combined_scripted.json

Output JSON: per (wz_cmd, vx_cmd, seed) wz_med/wz_p90_abs/wz_err_med
and vx_med/vx_err_med (body-frame forward speed, robust to a rotating
heading) over walk-mode ticks only, plus the frozen-body wz
prediction (|wz_cmd|) for direct comparison, and an aggregate
PASS/FAIL-style summary line printed to stdout (median |wz_err| vs a
configurable `--frozen-margin` fraction of |wz_cmd|) — the summary
verdict is wz-only and unaffected by `--vx-cmds`; read vx_err_med
per-row for the combined-tick course question.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent
for _p in (_PROTO, _PROTO / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.config import load_config  # noqa: E402
from rl_move.robot_state import DEG2RAD  # noqa: E402
from .servo_model import SimServoParams  # noqa: E402
from .walk_task import SimHexapodJointWalkEnv  # noqa: E402
from .joint_task import q_rad_to_action  # noqa: E402

# Preserve the probe's original physical pose after the repository-wide
# robot-absolute coordinate migration.  Its former compatibility wrapper took
# (hip=20, relative-knee=80) and commanded absolute tibia 20+80=100 degrees.
WALK_PLANT = (20.0, 100.0)


def _build_cfg(cfg_set: list[str] | None, mode_onehot: bool = False) -> dict:
    from .train_ppo_sim import _parse_cfg_set
    cfg = load_config()
    for key, parsed in _parse_cfg_set(cfg_set or []).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    if mode_onehot:
        cfg.setdefault("obs", {})["mode_onehot"] = 1.0
    return cfg


def make_env(cfg_set: list[str] | None, seed: int,
             episode_seconds: float, mode_onehot: bool = False):
    cfg = _build_cfg(cfg_set, mode_onehot=mode_onehot)
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg), randomize=False,
        dr_scale=0.0, episode_seconds=episode_seconds, seed=seed, cfg=cfg,
        render_mode=None)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env


def _load_model(checkpoint: Path):
    from .gru_policy import load_checkpoint_auto, RecurrentPredictor
    model = load_checkpoint_auto(checkpoint, device="cpu")
    obs_width = int(model.observation_space.shape[0])
    if getattr(model.policy, "lstm_actor", None) is not None:
        model = RecurrentPredictor(model)
    return model, obs_width


def rollout(*, model, env_cls_kwargs: dict, wz_cmd: float, seed: int,
            episode_seconds: float, policy: str = "checkpoint",
            model_obs_width: int | None = None,
            vx_cmd: float = 0.0,
            scripted_omega_boost: float = 1.0,
            scripted_yaw_arm_scale: float = 1.0) -> dict:
    """``vx_cmd`` (09-03, standwalk redesign-spec item 2 sub-step,
    "COMBINED walk+turn ticks specifically" branch — every prior
    anchor-coef/turn-authority probe in this lineage held vx_ref=0,
    i.e. PURE turn-in-place; nobody had measured wz/vx tracking with a
    simultaneous nonzero linear command). Default 0.0 reproduces the
    exact prior behavior bit-for-bit (``traj.vx[:] = 0.0`` either way,
    same ramp-from-zero shape since ramping 0->0 is a no-op) — this is
    an additive probe capability, not a semantics change. When nonzero,
    vx is ramped over the SAME 1s hold + ramp window as wz so both
    axes reach their commanded value together, and per-tick BODY-FRAME
    forward speed (``env._body_vel_xy()[0]``, robust to the heading
    rotating under a live wz command — unlike a world-frame track)
    is recorded over the identical walk-mode-filtered tick set as wz.

    ``scripted_omega_boost`` (09-03, standwalk branch-(a) combined-tick
    fix candidate, ``--policy scripted`` only): multiplies the omega
    handed to ``TripodGait.set_velocity`` ONLY on a combined tick
    (vx_cmd!=0 AND wz_cmd!=0) — mirrors the sim_env.py BC-anchor
    ``train.bc_anchor_teacher_omega_boost`` knob exactly (same gate,
    same multiply site: `self.omega` is used nowhere else in
    TripodGait). Default 1.0 is bit-exact (identity multiply, and a
    no-op on pure-turn/pure-walk ticks regardless since the gate
    requires BOTH nonzero).

    ``scripted_yaw_arm_scale`` (09-03, standwalk candidate (i)-v2,
    ``--policy scripted`` only): forwarded straight to
    ``TripodGait(combined_yaw_arm_scale=...)`` -- the combined-tick
    gate lives INSIDE TripodGait itself (see its docstring), so this
    probe just passes the dose through at construction. Default 1.0
    is bit-exact.
    """
    mode_onehot = False
    env = make_env(env_cls_kwargs["cfg_set"], seed, episode_seconds,
                   mode_onehot=env_cls_kwargs.get("mode_onehot", False))
    if model_obs_width is not None:
        n_env = int(env.observation_space.shape[0])
        if model_obs_width != n_env:
            from .walk_task import N_MODE_OBS
            if model_obs_width == n_env + N_MODE_OBS:
                env.close()
                env = make_env(env_cls_kwargs["cfg_set"], seed,
                               episode_seconds, mode_onehot=True)
            else:
                raise SystemExit(
                    f"checkpoint obs width {model_obs_width} does not "
                    f"fit env ({n_env}); wrong --cfg-set?")
    obs, info = env.reset()
    if policy == "checkpoint" and hasattr(model, "reset"):
        model.reset()
    traj = env._goal_traj
    n = len(traj.vx)
    hold_n = ramp_n = int(round(1.0 / env.dt))
    traj.vx[:] = vx_cmd
    traj.vy[:] = 0.0
    traj.wz[:] = wz_cmd
    traj.vx[:hold_n] = 0.0
    traj.wz[:hold_n] = 0.0
    traj.vx[hold_n:hold_n + ramp_n] = np.linspace(0.0, vx_cmd, ramp_n)
    traj.wz[hold_n:hold_n + ramp_n] = np.linspace(0.0, wz_cmd, ramp_n)
    if policy == "scripted":
        from hexapod_core.tripod_gait import TripodGait
        gait = TripodGait(vx=0.0,
                           combined_yaw_arm_scale=scripted_yaw_arm_scale)
        gait.sync_plant_stance(*WALK_PLANT)
        gait.reset_phase()
    step = 0
    wz_list: list[float] = []
    vx_list: list[float] = []
    modes_seen: list[str] = []
    fell = False
    while True:
        cmd_wz = float(traj.wz[min(step, n - 1)])
        cmd_vx = float(traj.vx[min(step, n - 1)])
        if policy == "scripted":
            t = step * env.dt
            _combined = abs(cmd_vx) > 1e-3 and abs(cmd_wz) > 1e-3
            _omega = (cmd_wz * scripted_omega_boost
                      if (_combined and scripted_omega_boost != 1.0)
                      else cmd_wz)
            gait.set_velocity(vx=cmd_vx, omega=_omega)
            act = q_rad_to_action(np.asarray(gait.desired_deg(t)) * DEG2RAD)
        else:
            act, _ = model.predict(obs, deterministic=True)
        obs, r, term, trunc, info = env.step(act)
        gm = info.get("goal_mode")
        modes_seen.append(gm)
        if step >= hold_n + ramp_n and gm == "walk":
            wz_list.append(float(env._body_wz()))
            vx_list.append(float(env._body_vel_xy()[0]))
        step += 1
        if term:
            fell = True
        if term or trunc:
            break
    env.close()
    wz_arr = np.array(wz_list)
    wz_err = np.abs(wz_arr - wz_cmd)
    vx_arr = np.array(vx_list)
    vx_err = np.abs(vx_arr - vx_cmd)
    return {
        "wz_cmd": wz_cmd,
        "vx_cmd": vx_cmd,
        "seed": seed,
        "n_walk_ticks": len(wz_arr),
        "n_total_ticks": step,
        "modes": dict(Counter(modes_seen)),
        "wz_med": float(np.median(wz_arr)) if len(wz_arr) else None,
        "wz_p90_abs": (float(np.percentile(np.abs(wz_arr), 90))
                       if len(wz_arr) else None),
        "wz_err_med": float(np.median(wz_err)) if len(wz_arr) else None,
        "frozen_body_wz_err_pred": abs(wz_cmd),
        "vx_med": float(np.median(vx_arr)) if len(vx_arr) else None,
        "vx_err_med": (float(np.median(vx_err)) if len(vx_arr) else None),
        "fell": fell,
    }


def summarize(results: list[dict], frozen_margin: float = 0.5) -> dict:
    """Pure aggregation: median |wz_err| vs the frozen-body prediction.

    FAIL (frozen) when the achieved median error stays ABOVE
    ``frozen_margin`` of the frozen-body prediction (|wz_cmd|) — i.e.
    the policy tracks meaningfully less than half the commanded rate.
    Split out from ``main()`` so the threshold logic is unit-testable
    without spinning up MuJoCo.
    """
    errs = [r["wz_err_med"] for r in results if r.get("wz_err_med") is not None]
    preds = [r["frozen_body_wz_err_pred"] for r in results]
    med_err = float(np.median(errs)) if errs else None
    med_pred = float(np.median(preds)) if preds else None
    frozen = (med_err is not None and med_pred is not None
              and med_err > frozen_margin * med_pred)
    verdict = ("FROZEN-BODY (no real turn tracking)" if frozen else
               "TRACKS (wz_err well below frozen-body prediction)")
    return {"med_wz_err": med_err, "frozen_body_pred": med_pred,
            "frozen": frozen, "verdict": verdict}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("checkpoint", nargs="?", type=Path, default=None)
    ap.add_argument("--policy", choices=("checkpoint", "scripted"),
                    default="checkpoint")
    ap.add_argument("--cfg-set", action="append", default=None)
    ap.add_argument("--wz-cmds", default="0.25,-0.25",
                    help="comma-separated commanded wz values (rad/s)")
    ap.add_argument("--vx-cmds", default="0.0",
                    help="comma-separated commanded body-frame forward "
                         "speeds (m/s), crossed with every --wz-cmds "
                         "value (09-03 COMBINED walk+turn probe "
                         "extension) — default '0.0' reproduces the "
                         "original pure-turn-in-place behavior exactly")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--frozen-margin", type=float, default=0.5,
                    help="PASS if median wz_err <= this fraction of "
                         "the frozen-body prediction |wz_cmd|")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--scripted-omega-boost", type=float, default=1.0,
                    help="--policy scripted only: multiply omega by "
                         "this factor on combined ticks only (mirrors "
                         "sim_env.py's train.bc_anchor_teacher_omega_"
                         "boost); default 1.0 is bit-exact")
    ap.add_argument("--scripted-yaw-arm-scale", type=float, default=1.0,
                    help="--policy scripted only: TripodGait's "
                         "combined_yaw_arm_scale (standwalk candidate "
                         "(i)-v2) on combined ticks only; default 1.0 "
                         "is bit-exact")
    args = ap.parse_args()

    if args.policy == "checkpoint" and args.checkpoint is None:
        raise SystemExit("--policy checkpoint requires a CKPT.zip path")

    model = None
    model_obs_width = None
    if args.policy == "checkpoint":
        model, model_obs_width = _load_model(args.checkpoint)

    wz_cmds = [float(x) for x in args.wz_cmds.split(",") if x.strip()]
    vx_cmds = [float(x) for x in args.vx_cmds.split(",") if x.strip()]
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    env_kwargs = {"cfg_set": args.cfg_set}
    results = []
    for wz_cmd in wz_cmds:
        for vx_cmd in vx_cmds:
            for seed in seeds:
                res = rollout(model=model, env_cls_kwargs=env_kwargs,
                              wz_cmd=wz_cmd, vx_cmd=vx_cmd, seed=seed,
                              episode_seconds=args.episode_seconds,
                              policy=args.policy,
                              model_obs_width=model_obs_width,
                              scripted_omega_boost=(
                                  args.scripted_omega_boost),
                              scripted_yaw_arm_scale=(
                                  args.scripted_yaw_arm_scale))
                results.append(res)

    summary = summarize(results, frozen_margin=args.frozen_margin)
    print(f"[probe_turn_authority] policy={args.policy} "
          f"med|wz_err|={summary['med_wz_err']} "
          f"frozen_body_pred={summary['frozen_body_pred']} -> "
          f"{summary['verdict']}")

    out = {"policy": args.policy,
           "checkpoint": str(args.checkpoint) if args.checkpoint else None,
           **summary, "results": results}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, indent=2))
        print(f"[probe_turn_authority] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
