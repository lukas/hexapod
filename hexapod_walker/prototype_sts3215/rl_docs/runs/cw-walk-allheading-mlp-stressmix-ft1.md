# cw-walk-allheading-mlp-stressmix-ft1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-29T22:28:39+00:00

**pod**: hexapod-mjx-train-3

**steps**: 15000000

**parent**: cw-walk-allheading-mlp-acq1-rr1-stdanneal

**wandb_id**: 96rcbagu

**hypothesis**: Plain English: the all-heading MLP walker (clean six-leg det/sto gait, DR-0 gate PASS) was trained on discrete heading jumps only and its own held-out 60s randomized-script joygate FAILS on direction (dir_err_med 51.9 deg, allow 40; slip 2.992, cap 2.9) while zero falls -- the eval script's own command families (random_hold/flip_180/sweep_circle/square/stop_go/jitter, goal.walk_cmd_mode=stress_mix) were NEVER part of training, so this reads as an out-of-distribution command-following gap, not a gait defect. WALKCURR... no, standwalk track: per OPERATOR_QUESTIONS q_20260829T16xx's own stage gate ('arcs/sweeps enter at stage (c) only after a wz case is added to test_course_income_semantics'), this cycle added that case (3 new tests, 12/12 green, rl_move/tests/test_course_income_semantics.py): a moderate turn (period 6s) rides at 0.946x straight-line income with only a small sway charge -- the existing windowed course-income/excess-sway mechanism needs NO reward-formula change to admit arcs; a tight/physically-extreme turn (period 3s) is gracefully discounted (0.638x), not exploited. Single lever: continue the finished stdanneal checkpoint with goal.walk_cmd_mode=stress_mix added (nothing else changed, --log-std-final/-anneal-frac carried over from the source to avoid re-triggering the std runaway), so training now samples the SAME command family mix the joygate evaluates against. Prediction-if-true: a fresh joygate on the new checkpoint shows direction_err_med dropping toward/under the 40 deg allowance with slip staying near/under 2.9 and zero falls preserved; DR-0 fixed-forward gate (walk/det+sto) should not regress off its current progress_ratio/gait_valid/zero-terminations baseline. Prediction-if-false: dir_err stays pinned above 40 or slip/falls regress -- would indicate the command families need curriculum staging (walk_cmd_stage ramp) rather than a flat mix, or a from-scratch stress_mix run is needed instead of a fine-tune off a heading-only optimum.

**gate**: Fresh eval_joystick_gate (60s randomized stress_mix script, n=24, DR-0) on the new checkpoint: PASS/continue-worthy needs direction_err_med improving materially toward/under 40 deg (from 51.9) with slip_per_m_med staying <=2.9-3.0ish and zero-or-near-zero falls (from 0/24). Also re-run eval_cmd_suite (8-heading balanced panel) and the plain DR-0 fixed-forward gate to confirm no regression off progress_ratio~0.41/gait_valid 6/6/zero terminations. FAIL: direction_err unchanged/worse or slip/falls regress with flat reward -- forks to walk_cmd_stage curriculum ramp or a from-scratch stress_mix run.

