"""Single-cycle sit->rise->walk->lower DONE-gate session (09-01,
standwalk track — the literal `standwalk` DONE-gate shape: "ONE
mesh-family 100 Hz policy, from sit: rise -> randomized 60 s joystick
command script -> lower to sit").

WHY THIS EXISTS (not a duplicate of `eval_mixed_session`): that
harness's canonical grammar REPEATS rise<->{hold|walk}<->lower cycles
for the whole episode (built for the harder "does one policy survive
an indefinitely long mixed session" question). Any single rise-after-
self-lower fragility compounds across those repeats — a checkpoint
with, say, an 80% single-rise success rate reads as a near-100%
SESSION failure once you force it through 4-7 rise attempts back to
back (found 09-01 on `gradclip0p15-canary`: mixedsession showed 100%
over_current on every submode incl. plain rise/det, but the SAME
checkpoint's own probe/purewalk single-mode reads were clean — the
gap traced to exactly this repeating-cycle statistics, not a tooling
bug in cfg propagation as first suspected). The DONE gate itself only
ever asks for ONE cycle. This harness gives that exact, and only that,
shape: a DETERMINISTIC `goal.mode_seq_forced_plan=rise:R,walk:W,
lower:L` (see `walk_task._sample_mode_seq`) instead of the random
repeating grammar, riding the SAME joystick stress_mix walk diet
(`eval_mixed_session.MIXED_SESSION_CFG`) the DONE gate text calls a
"randomized ... command script", and the same `eval_checkpoint.py`
walk-metric fix (09-01, live goal_mode tracking) that makes
progress_ratio/slip_per_m/gait_valid populate for a walk segment
buried inside a rise-first sequence.

Reuses `eval_mixed_session`'s `_run_eval_checkpoint`/`aggregate_session`
machinery verbatim (same resume-safety, same report.json passes, same
hard/soft gate structure) — only the plan-shaping cfg differs.

    cd prototype_sts3215 && uv run python -m rl_move.sim.eval_done_gate_session \
        rl_move/sim/policies/<ckpt>.zip --own-dr-scale 0.5 \
        --extra-cfg-set env.model_source=mesh ... \
        [--rise-s 10] [--walk-s 60] [--lower-s 15] [--n 6] [--video] \
        [--out-dir logs/ckpt_eval/X]

Exit 0 = hard gate (zero falls) passed, 1 = failed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .eval_mixed_session import (
    DIR_ERR_CAP_DEFAULT, HEIGHT_ERR_CAP_MM, SLIP_CAP_DEFAULT, _PROTO,
    _run_eval_checkpoint, _safe_print, aggregate_session,
)

SEED_BASE_DEFAULT = 92000   # held out (90000=joygate, 91000=mixedsession,
                            # 900000/910000=bulk_session_eval)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Single-cycle sit->rise->walk->lower DONE-gate "
                    "session (one policy, one cycle, no repeats)")
    ap.add_argument("ckpt", type=Path)
    ap.add_argument("--task", default="joint_walk")
    ap.add_argument("--own-dr-scale", type=float, default=None,
                    help="the checkpoint's own training DR scale; "
                         "omit to run DR-0 only")
    ap.add_argument("--n", type=int, default=6,
                    help="episodes per pass")
    ap.add_argument("--rise-s", type=float, default=10.0)
    ap.add_argument("--walk-s", type=float, default=60.0,
                    help="the DONE gate's '60 s joystick command "
                         "script' segment")
    ap.add_argument("--lower-s", type=float, default=15.0)
    ap.add_argument("--episode-buffer-s", type=float, default=5.0,
                    help="slack past rise+walk+lower so the lower "
                         "segment's own settle isn't clipped")
    ap.add_argument("--seed-base", type=int, default=SEED_BASE_DEFAULT)
    ap.add_argument("--extra-cfg-set", action="append", default=[],
                    help="the run's own cfg stack (ops.sh evalcmd "
                         "prints it)")
    ap.add_argument("--slip-cap", type=float, default=SLIP_CAP_DEFAULT)
    ap.add_argument("--dir-err-cap", type=float,
                    default=DIR_ERR_CAP_DEFAULT)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    ep_s = args.rise_s + args.walk_s + args.lower_s + args.episode_buffer_s
    plan = f"rise:{args.rise_s},walk:{args.walk_s},lower:{args.lower_s}"
    # goal.mode_seq=1.0 + the stress_mix walk diet already ride in
    # eval_mixed_session.MIXED_SESSION_CFG (appended inside
    # _run_eval_checkpoint) — the ONE thing this harness adds on top
    # is the forced deterministic plan, which makes those random-
    # segment-length keys moot (the forced branch never reads them).
    cfg = list(args.extra_cfg_set) + [f"goal.mode_seq_forced_plan={plan}"]

    stem = args.ckpt.stem.replace("ppo_goal_", "")
    out_root = args.out_dir or (_PROTO / "logs" / "ckpt_eval"
                                / f"{stem}_donegate")
    out_root.mkdir(parents=True, exist_ok=True)

    passes: list[tuple[str, float]] = [("dr0", 0.0)]
    if args.own_dr_scale is not None:
        passes.append(("owndr", args.own_dr_scale))

    reports: dict[str, dict] = {}
    for pname, dr in passes:
        rp = _run_eval_checkpoint(
            args.ckpt, task=args.task, dr_scale=dr,
            seed=args.seed_base, n=args.n, episode_seconds=ep_s,
            modes=["rise"], extra_cfg=cfg, out_dir=out_root / pname,
            log_path=out_root / f"{pname}.log", video=args.video)
        reports[pname] = json.loads(rp.read_text())
        _safe_print(f"[done-gate-session] pass {pname} done")

    verdict = aggregate_session(
        reports, slip_cap=args.slip_cap, dir_err_cap=args.dir_err_cap,
        height_err_cap=HEIGHT_ERR_CAP_MM, strict=args.strict)
    verdict["checkpoint"] = str(args.ckpt)
    verdict["passes"] = [p[0] for p in passes]
    verdict["rise_s"] = args.rise_s
    verdict["walk_s"] = args.walk_s
    verdict["lower_s"] = args.lower_s
    (out_root / "session_verdict.json").write_text(
        json.dumps(verdict, indent=1))
    _safe_print(json.dumps(verdict, indent=1))
    _safe_print(f"[done-gate-session] verdict written to "
                f"{out_root / 'session_verdict.json'}")
    return 0 if verdict["gate"]["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
