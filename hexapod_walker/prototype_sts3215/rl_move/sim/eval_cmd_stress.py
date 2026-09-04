"""Mixed-command TRANSITION STRESS suite — the smooth-universal-policy
promotion gate (operator directive fb_20260904T074505_6a3ac9, 09-04).

WHY THIS EXISTS (vs eval_mixed_session / eval_done_gate_session): the
mixed-session harness repeats rise<->{hold|walk}<->lower cycles with
LONG (8-12 s) settled segments and the done-gate harness runs exactly
one polite rise->walk->lower cycle. Neither ever asks the product
question the operator registered: can ONE policy accept ARBITRARY
command changes at ANY time — rise interrupted into lower, rise->walk
before settling, walk->hold->walk stop/restart, rapid joystick
direction/turn flips — without falling and without violent actuator
motion. This suite is that instrument:

  - env-native `goal.mode_seq_stress=1` grammar (walk_task.
    SEQ_NEXT_STRESS): adds rise->lower and walk->hold transitions the
    legacy grammar never samples;
  - SHORT randomized segments (2.5-9 s, vs the >=7 s rise-ramp floor)
    so mode switches land MID-transition by construction;
  - walk segments ride the joystick stress_mix family resampled every
    ~3 s (direction changes, stops, reverses, laterals, turn-in-place,
    walk+turn) — faster switching than the 4 s mixed-session diet;
  - hold segments carry height up/down command scripts.

GATES (per the directive):
  - HARD (exit 1): zero MECHANICAL terminations — falls, tips,
    hold_min_load, any posture-loss reason. `over_current` is counted
    and reported SEPARATELY and does NOT veto: the sim current is an
    uncalibrated estimator whose 2.64 A pin is the actuator-forcerange
    rail image (see rl_move/sim/audit_over_current.py); corroborate
    rail hits with dynamics before treating them as unsafe.
  - REPORTED always, gated with --strict: session completion >= 0.9,
    walk gait validity >= 0.9, slip/dir-err/height caps (same bars as
    eval_mixed_session), PLUS the smoothness telemetry medians
    (cmd_rate_p95_deg_s, cmd_jerk_p95_deg_s2, slew_sat_frac,
    cur_rail_frac) — report them next to a named comparator; a
    smoothness claim without a baseline is noise.

    cd prototype_sts3215 && uv run python -m rl_move.sim.eval_cmd_stress \
        rl_move/sim/policies/<ckpt>.zip --own-dr-scale 0.5 \
        --extra-cfg-set env.model_source=mesh ... \
        [--episode-seconds 60] [--n 6] [--modes rise walk] [--video] \
        [--out-dir logs/ckpt_eval/X] [--strict]

Exit 0 = hard gate passed, 1 = failed. Seeds: SEED_BASE 93000 (held
out; 90000=joygate, 91000=mixedsession, 92000=donegate).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from .eval_mixed_session import (_run_eval_checkpoint, _episodes, _med,
                                 _safe_print, aggregate_session)

_PROTO = Path(__file__).resolve().parents[2]

# Canonical stress bundle. Versioned here so every candidate is measured
# against provably the SAME transition distribution.
CMD_STRESS_CFG = [
    "goal.mode_seq=1.0",                # every episode a sequence
    "goal.mode_seq_stress=1",           # SEQ_NEXT_STRESS grammar
    "goal.mode_seq_segment_s_min=2.5",  # BELOW the 7 s rise ramp:
    "goal.mode_seq_segment_s_max=9.0",  # switches land mid-transition
    "goal.mode_seq_max_segments=12",
    "goal.mode_seq_hold_height_cmd=1.0",
    "goal.hold_height_cmd_frac=1.0",
    "goal.walk_cmd_mode=stress_mix",    # joystick command family
    "goal.walk_cmd_resample_s=3.0",     # faster flips than mixedsession
    "goal.walk_cmd_resample_jitter=0.6",
]

SEED_BASE_DEFAULT = 93000

# Terminations that corroborate a MECHANICAL failure (posture/fall).
# over_current is deliberately NOT here (uncalibrated estimator rail —
# operator directive 09-04; report separately, never veto alone).
MECH_TERM_EXCLUDED = ("over_current",)


def aggregate_stress(reports: dict[str, dict], *, strict: bool = False,
                     smooth_caps: dict | None = None) -> dict:
    """Pure function: {pass_name: parsed report.json} -> scorecard.

    Wraps eval_mixed_session.aggregate_session, then (a) re-derives the
    hard gate over MECHANICAL terminations only, (b) adds smoothness /
    rail-dwell aggregates from the 09-04 per-episode telemetry fields.
    """
    base = aggregate_session(reports, strict=strict)
    mech = {r: c for r, c in base["term_reasons"].items()
            if r not in MECH_TERM_EXCLUDED}
    oc = sum(c for r, c in base["term_reasons"].items()
             if r in MECH_TERM_EXCLUDED)
    rates, jerks, sats, rails = [], [], [], []
    for _p, rep in reports.items():
        for _l, ep in _episodes(rep):
            if ep.get("cmd_rate_p95_deg_s") is not None:
                rates.append(float(ep["cmd_rate_p95_deg_s"]))
            if ep.get("cmd_jerk_p95_deg_s2") is not None:
                jerks.append(float(ep["cmd_jerk_p95_deg_s2"]))
            if ep.get("slew_sat_frac") is not None:
                sats.append(float(ep["slew_sat_frac"]))
            if ep.get("cur_rail_frac") is not None:
                rails.append(float(ep["cur_rail_frac"]))
    base["smoothness"] = {
        "cmd_rate_p95_deg_s_med": _med(rates),
        "cmd_jerk_p95_deg_s2_med": _med(jerks),
        "slew_sat_frac_med": _med(sats),
        "cur_rail_frac_med": _med(rails),
    }
    base["mech_term_reasons"] = mech
    base["over_current_terms"] = oc
    base["over_current_note"] = (
        "over_current is an UNCALIBRATED estimator trip (2.64 A = "
        "2.2 N*m forcerange * 1.2 A/N*m rail image); reported, not "
        "vetoing — corroborate with audit_over_current before judging")
    hard = sum(mech.values()) == 0
    soft_ok = all(base["gate"]["soft"].values())
    smooth_ok = True
    if smooth_caps:
        sm = base["smoothness"]
        checks = {}
        for k, cap in smooth_caps.items():
            v = sm.get(k + "_med")
            checks[k] = (v is not None and v <= cap)
        base["smoothness_gate"] = checks
        smooth_ok = all(checks.values())
    base["gate"] = {"zero_mech_terms": hard,
                    "soft": base["gate"]["soft"],
                    "strict": strict,
                    "pass": hard and ((soft_ok and smooth_ok)
                                      if strict else True)}
    return base


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Mixed-command transition stress gate")
    ap.add_argument("ckpt", type=Path)
    ap.add_argument("--task", default="joint_walk")
    ap.add_argument("--own-dr-scale", type=float, default=None)
    ap.add_argument("--episode-seconds", type=float, default=60.0)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--modes", nargs="+", default=["rise", "walk"])
    ap.add_argument("--seed-base", type=int, default=SEED_BASE_DEFAULT)
    ap.add_argument("--extra-cfg-set", nargs="*", default=[])
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    ckpt = args.ckpt if args.ckpt.is_absolute() else _PROTO / args.ckpt
    name = ckpt.stem.replace("ppo_goal_", "")
    out_root = args.out_dir or (_PROTO / "logs" / "ckpt_eval"
                                / f"{name}_cmdstress")
    out_root.mkdir(parents=True, exist_ok=True)

    passes = [("dr0", 0.0)]
    if args.own_dr_scale is not None:
        passes.append(("owndr", float(args.own_dr_scale)))

    reports: dict[str, dict] = {}
    t0 = time.time()
    for pname, dr in passes:
        pdir = out_root / pname
        rep = _run_eval_checkpoint(
            ckpt, task=args.task, dr_scale=dr,
            seed=args.seed_base + (0 if pname == "dr0" else 1),
            n=args.n, episode_seconds=args.episode_seconds,
            modes=list(args.modes),
            extra_cfg=list(args.extra_cfg_set),
            out_dir=pdir, log_path=out_root / f"{pname}.log",
            video=args.video, bundle=CMD_STRESS_CFG)
        reports[pname] = json.loads(rep.read_text())
        _safe_print(f"[cmd-stress] pass {pname} done "
                    f"({time.time() - t0:.0f}s)")

    verdict = aggregate_stress(reports, strict=args.strict)
    (out_root / "stress_verdict.json").write_text(
        json.dumps(verdict, indent=1))
    _safe_print(json.dumps(
        {k: verdict[k] for k in ("n_episodes", "mech_term_reasons",
                                 "over_current_terms",
                                 "session_complete_frac", "smoothness",
                                 "gate")}, indent=1))
    _safe_print(f"[cmd-stress] verdict -> {out_root/'stress_verdict.json'}")
    return 0 if verdict["gate"]["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
