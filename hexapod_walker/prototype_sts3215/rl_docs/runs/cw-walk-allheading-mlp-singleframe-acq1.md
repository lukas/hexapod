# cw-walk-allheading-mlp-singleframe-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T03:43:04+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walk-allheading-mlp-singleframe-canary

**wandb_id**: xkgk2em8

**hypothesis**: Plain English: continue the healthy single-frame all-heading MLP walker (2M mechanism canary PASSED: bc_anchor_loss_walk falling, course-income mechanism live and recovering through the from-scratch 100Hz reward valley in the same shape the hist64 twins showed, no NaN/collapse/termination-explosion, reward in-band of the hist64 mlp/tf scratch1 canaries' own quarters) into a real 40M learning budget -- this is the distill-compatibility probe: if this arm ALSO clears the same eval_cmd_suite balanced-heading first gate and the formal 60s eval_joystick_gate stress_mix script the hist64 twins cleared, it becomes a walk teacher immediately usable by distill_gru.py --dual with ZERO code changes (single-frame both sides), sidestepping the stacking-aware collect() rewrite this cycle root-caused as otherwise required. Prediction-if-true: course-income share keeps climbing past the valley, balanced 8-heading eval_cmd_suite panel shows every heading moving at >=half the teacher's own completion (>=0.19) with zero falls by 40M, and the eventual formal joygate reads clean (zero falls, slip<=2.9, windowed course_err<=12deg) same as cw-walk-allheading-mlp-stressmix-ft1. Prediction-if-false: single-frame obs turns out to be genuinely load-bearing for the hist64 twins' course-tracking win after all (something the 2M canary's mechanism-health checks cannot distinguish) -- direction_err stays pinned near chance/stress_mix fails the formal joygate, and the correct fix reverts to the stacking-aware distill_gru.py rewrite (fix path (a) in standwalk/STATUS.md 08-30 ~03:1x) instead.

**gate**: Cheap first gate (unchanged from the canary's own text): eval_cmd_suite balanced 8-heading panel, det+sto, every heading must move (completion >=0.19, half the teacher's 0.373-0.385), zero falls. If that clears: run the formal 60s randomized eval_joystick_gate stress_mix script (the real bar: zero falls, slip<=2.9, windowed course_err_1s_med<=12deg) -- if that ALSO passes, immediately re-attempt distill_gru.py --dual (walk teacher swapped to this checkpoint) as a smoke test (--transitions 4 --episodes 8 --epochs 2) before funding any acquisition-scale Stage-2 distillation run. FAIL on the eval_cmd_suite panel or the formal joygate hands the job back to fix (a): making distill_gru.py's teacher-obs extraction reshape/stacking-aware instead.

