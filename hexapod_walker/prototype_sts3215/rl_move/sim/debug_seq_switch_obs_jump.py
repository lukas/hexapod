"""DIG-IN instrument (2026-09-02, standwalk duration-mismatch fork):
does `sim_env._seq_maybe_switch`'s unblended q_nom/z0 canonical-frame
teleport create an observation discontinuity at mode-sequence switch
ticks, and does that discontinuity line up with the near-instant
`over_current` terminations found in the flat-only
`eval_done_gate_session` reads (STATUS.md 2026-09-02 00:4x)?

`_seq_maybe_switch` blends the GOAL trajectory (height/roll/pitch)
across a switch but installs the new segment family's canonical
`q_nom`/`z0`/`pad_z_ref` in one tick (see its docstring + the
SEQ_FRAME_FAMILY belly/plant split). Since `build_obs` reads
`q_rel = (joint_position - q_nom) / q_scale` and height error is
`chassis_z - z0`, a family change (rise="belly" -> walk="plant") can
make the observed joint-delta and height-error jump discontinuously
even though the robot's ACTUAL pose/physics carried over untouched.
A same-family switch (walk="plant" -> lower="plant") should show ~0
jump (control case, same script, same episodes).

This script does NOT change any training/eval default (no cfg
touched, no sim_env edit) -- it is a read-only measurement built by
monkey-patching one instance method to snapshot state immediately
before/after the frame swap that method already performs, on ordinary
`env.step()` episodes run exactly like `eval_done_gate_session`'s
flat-only rise->walk->lower panel (same forced plan, same cfg stack,
same seeds-in-family). Output: one JSON per checkpoint with, per
episode: every switch event (tick, old/new family, q_rel-jump L2 norm
in degrees, height-frame jump in mm) and the termination tick/reason,
so a human/next-cycle can eyeball whether terminations cluster at the
jump tick (confirms the lead) or not (refutes it -- a duration/reward
defect elsewhere would be next).

Usage (run ON A POD, not the controller -- MuJoCo-stepping bound):
    uv run python -m rl_move.sim.debug_seq_switch_obs_jump \
        rl_move/sim/policies/<ckpt>.zip --dr-scale 0.5 --n 8 \
        --seed-base 92000 --out logs/ckpt_eval/<ckpt>_seqswitch_probe.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_PROTO = Path(__file__).resolve().parents[2]
for p in (_PROTO, _PROTO / "linux_control"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from rl_move.config import load_config  # noqa: E402
from rl_move.sim.eval_checkpoint import ENV_CLASSES  # noqa: E402
from rl_move.sim.gru_policy import load_checkpoint_auto  # noqa: E402
from rl_move.sim.servo_model import SimServoParams  # noqa: E402
from rl_move.sim.train_ppo_sim import _parse_cfg_set  # noqa: E402

RAD2DEG = 180.0 / np.pi

# The exact flat-only + forced-plan cfg tail `eval_done_gate_session`
# adds on top of a run's own training cfg-set (rise_flat_frac=1.0 etc
# force a literal cold sit start; mode_seq_forced_plan pins the ONE
# rise->walk->lower cycle the DONE gate itself asks for; the
# mode_seq_segment_s_* keys are moot under a forced plan -- kept for
# fidelity with the actual quartet reads, not because they do anything
# here). Shared verbatim by durctrl/durfix probes (both quartet reads
# used episode-seconds derived from the SAME rise/walk/lower/buffer
# split; the only per-arm difference, mode_seq_segment_s_min/max, is
# inert under forced_plan -- see eval_done_gate_session.py comment).
FLATONLY_FORCED_PLAN_CFG = [
    "goal.rise_flat_frac=1.0",
    "goal.rise_partial_frac=0",
    "goal.rise_start_bank_frac=0",
    "goal.rise_rsi_frac=0",
    "goal.mode_seq_forced_plan=rise:10.0,walk:60.0,lower:15.0",
    "goal.mode_seq=1.0",
    "goal.mode_seq_hold_height_cmd=1.0",
    "goal.hold_height_cmd_frac=1.0",
    "goal.walk_cmd_mode=stress_mix",
    "goal.walk_cmd_resample_s=4.0",
    "goal.walk_cmd_resample_jitter=0.5",
    "goal.mode_seq_max_segments=13",
]


def _install_switch_probe(env) -> list:
    """Monkey-patch env._seq_maybe_switch to record a before/after
    snapshot of the canonical-frame variables it installs. Returns the
    (mutable) list the callback appends to -- one dict per switch this
    episode. Reinstalled fresh per episode by the caller (list swap)."""
    events: list = []
    orig = env._seq_maybe_switch

    def wrapped():
        nxt = env._seq_idx + 1
        pre_seg = None
        if env._seq_plan is not None and nxt < len(env._seq_plan):
            seg = env._seq_plan[nxt]
            if env._step_i >= int(seg["tick"]):
                pre_seg = seg
        if pre_seg is None:
            return orig()
        old_mode = str(env._seq_plan[env._seq_idx]["mode"])
        new_mode = str(pre_seg["mode"])
        old_fam = env.SEQ_FRAME_FAMILY[old_mode]
        new_fam = env.SEQ_FRAME_FAMILY[new_mode]
        q_nom_pre = env._q_nom.copy()
        z0_pre = float(env._z0)
        actual_q = env.data.qpos[env._qadr].copy()
        actual_z = float(env.data.xpos[env._chassis_bid, 2])
        q_rel_pre = actual_q - q_nom_pre
        h_rel_pre = actual_z - z0_pre
        ret = orig()
        q_nom_post = env._q_nom.copy()
        z0_post = float(env._z0)
        q_rel_post = actual_q - q_nom_post   # physics untouched by switch
        h_rel_post = actual_z - z0_post
        jump_deg = (q_rel_post - q_rel_pre) * RAD2DEG
        events.append({
            "tick": env._step_i,
            "t_s": env._step_i * env.dt,
            "old_mode": old_mode, "new_mode": new_mode,
            "old_family": old_fam, "new_family": new_fam,
            "family_changed": old_fam != new_fam,
            "q_jump_l2_deg": float(np.linalg.norm(jump_deg)),
            "q_jump_max_abs_deg": float(np.max(np.abs(jump_deg))),
            "h_jump_mm": (h_rel_post - h_rel_pre) * 1000.0,
        })
        return ret

    env._seq_maybe_switch = wrapped
    return events


def _ledger_cfg_set(run: str) -> list[str]:
    """The run's own training --cfg-set list, straight from the
    ledger's extra_args (same lookup `ops.sh evalcmd`/`sessioncmd` use:
    prefer an entry that actually ran over a later REFUSED stub)."""
    import os
    ledger = Path(os.environ.get(
        "LEDGER", _PROTO / "rl_move/orchestrator/experiments.json"))
    entry, fallback = None, None
    for e in json.loads(ledger.read_text()):
        if isinstance(e, dict) and e.get("run") == run and e.get(
                "extra_args"):
            fallback = e
            if e.get("wandb_id") or e.get("checks", {}).get("pid"):
                entry = e
    entry = entry or fallback
    if entry is None:
        raise SystemExit(f"no ledger entry with extra_args for run {run!r}")
    args = entry["extra_args"]
    return [args[i + 1] for i, a in enumerate(args) if a == "--cfg-set"]


def run_probe(ckpt: Path, *, dr_scale: float, n: int, seed_base: int,
             episode_seconds: float, stochastic: bool,
             train_run: str | None = None) -> dict:
    cfg = load_config()
    overrides = list(FLATONLY_FORCED_PLAN_CFG)
    if train_run:
        # Training cfg first, flat-only+forced-plan overrides last (same
        # precedence eval_done_gate_session gets via cfg-set append
        # order) so e.g. rise_rsi_frac=0 wins over the training
        # default 0.5.
        overrides = _ledger_cfg_set(train_run) + overrides
    for key, parsed in _parse_cfg_set(overrides).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    env = ENV_CLASSES["joint_walk"](
        params=SimServoParams.from_cfg(cfg), cfg=cfg,
        randomize=(dr_scale > 0), dr_scale=dr_scale,
        episode_seconds=episode_seconds, seed=seed_base,
        render_mode=None)
    model = load_checkpoint_auto(ckpt, device="cpu")
    n_model = int(model.observation_space.shape[0])
    n_env = int(env.observation_space.shape[0])
    if n_model != n_env:
        raise SystemExit(
            f"obs width mismatch: ckpt={n_model} env={n_env} -- "
            f"add the missing --cfg-set override(s) to "
            f"FLATONLY_FORCED_PLAN_CFG (probably obs.mode_onehot=1 or "
            f"goal.walk_phase_obs=1; check the run's own training cfg "
            f"via `ops.sh evalcmd <run>`).")
    episodes = []
    for i in range(n):
        obs, info0 = env.reset(seed=seed_base + i)
        if hasattr(model, "reset"):
            model.reset()
        events = _install_switch_probe(env)
        term_tick = None
        term_reason = None
        term_mode = None
        # Per-tick trace (2026-09-02 extension): the family-change jump
        # SIZE is ~constant every episode (belly vs plant are fixed
        # canonical poses, ~weakly dependent on the trained policy) --
        # it cannot by itself explain why only SOME episodes die right
        # after it. What can differ per-episode is the SHOCK RESPONSE:
        # does the policy's action/current spike right at the jump
        # tick (a real disturbance response) or does current climb
        # gradually (a different, switch-unrelated cause)? Track a
        # cheap per-tick (cur_max, |action|_max) trace so a human/
        # next-cycle can eyeball the window around each switch/term.
        cur_trace: list[float] = []
        act_trace: list[float] = []
        # Height trace (2026-09-02 sustained-current dig-in, STATUS.md
        # Next item 1b): is the mid/late-rise current climb driven by a
        # commanded-height/pose demand the heavier mesh mass can't hold
        # cheaply, or is it drift unrelated to the height goal? `info`
        # already exposes the actual vs commanded height every tick
        # (sim_env.py height_mm/height_ref_mm) -- no new env plumbing
        # needed, just record what's already computed.
        h_trace: list[float] = []
        href_trace: list[float] = []
        mode_trace: list[str] = []
        done = False
        while not done:
            a, _ = model.predict(obs, deterministic=not stochastic)
            obs, r, term, trunc, info = env.step(a)
            done = term or trunc
            st = env._state
            cur_trace.append(
                float(np.max(np.abs(st.servo_current)))
                if st.servo_current is not None else float("nan"))
            act_trace.append(float(np.max(np.abs(np.asarray(a)))))
            h_trace.append(float(info.get("height_mm", float("nan"))))
            href_trace.append(
                float(info.get("height_ref_mm", float("nan"))))
            mode_trace.append(str(info.get("goal_mode", "")))
            if term:
                term_tick = env._step_i
                term_reason = info.get("termination_reason")
                term_mode = info.get("goal_mode")
        episodes.append({
            "ep": i, "switches": events,
            "term_tick": term_tick, "term_t_s":
                (term_tick * env.dt) if term_tick is not None else None,
            "term_reason": term_reason, "term_mode": term_mode,
            "cur_trace": cur_trace, "act_trace": act_trace,
            "h_trace_mm": h_trace, "href_trace_mm": href_trace,
            "mode_trace": mode_trace, "dt": env.dt,
        })
    return {"checkpoint": str(ckpt), "dr_scale": dr_scale, "n": n,
            "stochastic": stochastic, "episodes": episodes}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("--dr-scale", type=float, default=0.5)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--seed-base", type=int, default=92000)
    ap.add_argument("--episode-seconds", type=float, default=90.0)
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--train-run", type=str, default=None,
                    help="ledger run name to source the training "
                         "--cfg-set stack from (required unless the "
                         "checkpoint's obs width happens to match the "
                         "bare flat-only overrides)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    result = run_probe(
        args.checkpoint, dr_scale=args.dr_scale, n=args.n,
        seed_base=args.seed_base, episode_seconds=args.episode_seconds,
        stochastic=args.stochastic, train_run=args.train_run)
    out = args.out or Path(
        f"logs/ckpt_eval/{args.checkpoint.stem}_seqswitch_probe.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1))
    # Compact summary to stdout.
    for ep in result["episodes"]:
        fam_jumps = [e for e in ep["switches"] if e["family_changed"]]
        worst = max(fam_jumps, key=lambda e: e["q_jump_l2_deg"],
                    default=None)
        near = ("NEAR" if (worst and ep["term_tick"] is not None
                           and 0 <= ep["term_tick"] - worst["tick"] <= 300)
               else "")
        print(f"ep{ep['ep']}: term={ep['term_reason']}@"
              f"{ep['term_t_s']}s mode={ep['term_mode']}  "
              f"worst_family_jump={worst['q_jump_l2_deg']:.1f}deg@"
              f"{worst['t_s']:.2f}s" if worst else
              f"ep{ep['ep']}: term={ep['term_reason']}@"
              f"{ep['term_t_s']}s mode={ep['term_mode']}  no switch",
              near)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
