# cw-walk-allheading-mlp-singleframe-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PARTIAL

**created**: 2026-08-30T03:43:04+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walk-allheading-mlp-singleframe-canary

**wandb_id**: xkgk2em8

**hypothesis**: Plain English: continue the healthy single-frame all-heading MLP walker (2M mechanism canary PASSED: bc_anchor_loss_walk falling, course-income mechanism live and recovering through the from-scratch 100Hz reward valley in the same shape the hist64 twins showed, no NaN/collapse/termination-explosion, reward in-band of the hist64 mlp/tf scratch1 canaries' own quarters) into a real 40M learning budget -- this is the distill-compatibility probe: if this arm ALSO clears the same eval_cmd_suite balanced-heading first gate and the formal 60s eval_joystick_gate stress_mix script the hist64 twins cleared, it becomes a walk teacher immediately usable by distill_gru.py --dual with ZERO code changes (single-frame both sides), sidestepping the stacking-aware collect() rewrite this cycle root-caused as otherwise required. Prediction-if-true: course-income share keeps climbing past the valley, balanced 8-heading eval_cmd_suite panel shows every heading moving at >=half the teacher's own completion (>=0.19) with zero falls by 40M, and the eventual formal joygate reads clean (zero falls, slip<=2.9, windowed course_err<=12deg) same as cw-walk-allheading-mlp-stressmix-ft1. Prediction-if-false: single-frame obs turns out to be genuinely load-bearing for the hist64 twins' course-tracking win after all (something the 2M canary's mechanism-health checks cannot distinguish) -- direction_err stays pinned near chance/stress_mix fails the formal joygate, and the correct fix reverts to the stacking-aware distill_gru.py rewrite (fix path (a) in standwalk/STATUS.md 08-30 ~03:1x) instead.

**gate**: Cheap first gate (unchanged from the canary's own text): eval_cmd_suite balanced 8-heading panel, det+sto, every heading must move (completion >=0.19, half the teacher's 0.373-0.385), zero falls. If that clears: run the formal 60s randomized eval_joystick_gate stress_mix script (the real bar: zero falls, slip<=2.9, windowed course_err_1s_med<=12deg) -- if that ALSO passes, immediately re-attempt distill_gru.py --dual (walk teacher swapped to this checkpoint) as a smoke test (--transitions 4 --episodes 8 --epochs 2) before funding any acquisition-scale Stage-2 distillation run. FAIL on the eval_cmd_suite panel or the formal joygate hands the job back to fix (a): making distill_gru.py's teacher-obs extraction reshape/stacking-aware instead.

**verdict**: Real det-mode all-heading walk (prog med 0.47 walk / 0.45 walk_startjitter, slip med 2.03-2.30 -- inside teacher band, gait_valid 6/6 both, zero terminations, video-confirmed clean six-leg cycling, forward_dist med ~0.5m/20s) BUT reproduces the exact already-documented cross-architecture std-runaway bug (train/std 0.397->5.052 over 40M, no --log-std-final anywhere in this launch's args, same as the hist64 mlp/tf acq1 twins): rollout/ep_rew_mean peaks +405 near 10M then crashes monotonically to -836..-1112 by 40M as entropy-driven noise piles up excess_sway/park_duty/action_delta charges; sto-mode DR-0 gate collapses accordingly (walk/sto prog med 0.01, slip med 16.73 vs cap ~6, gait_valid 5/6 w/ 1 sacrificed-leg episode, 2/6 over_current terms; walk_startjitter/sto prog med -0.01, slip med 16.85, gait_valid 4/6, 2 terms). Deterministic periodic eval (wandb eval/walk/*) stayed flat-to-stable direction_err ~37-46deg and speed ~0.036-0.044 m/s from 6M through 40M -- the det policy plateaued early and did not improve further; the back-half budget was wasted feeding the runaway, not learning. This is NOT a fresh finding: it is the third instance of the identical bug (mlp/tf all-heading acq1, now this single-frame twin), for which the fix (--log-std-final anneal) is already proven twice on this exact codebase. Per the 08-21 ruling this is a MISALIGNED/undertrained-by-omission case, not a clean FAIL: launching the same repair now (cw-walk-allheading-mlp-singleframe-acq1-stdanneal, respec --init-from-source, +15M, --log-std-final -3.0 --log-std-anneal-frac 1.0, nothing else changed) rather than closing the distill-compatibility probe on a preventable artifact.

