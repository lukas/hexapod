# cw-walk-allheading-tf-stressmix-ft1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-08-29T22:30:51+00:00

**pod**: hexapod-mjx-train-0

**steps**: 15000000

**parent**: cw-walk-allheading-tf-acq1-stdanneal

**hypothesis**: Plain English: matched transformer twin of cw-walk-allheading-mlp-stressmix-ft1 (same cycle) -- same hypothesis: the all-heading TF walker (clean det/sto gait, DR-0 PASS) FAILS its own held-out 60s randomized joygate on direction (dir_err_med 45.5 deg, allow 40; slip 2.799, cap 2.9 -- passes slip) because training never saw the eval's own command families (stress_mix: random_hold/flip_180/sweep_circle/square/stop_go/jitter). Per OPERATOR_QUESTIONS q_20260829T16xx's stage gate, this cycle added the required wz/arc bank case (test_course_income_semantics.py, 3 new tests, 12/12 green): moderate turns ride at 0.946x straight income, tight/extreme turns are gracefully discounted not exploited -- no reward-formula change needed to admit arcs. Single lever: continue the finished stdanneal checkpoint with goal.walk_cmd_mode=stress_mix added, nothing else changed (log-std-final/anneal-frac carried over from source). Prediction-if-true: fresh joygate shows dir_err_med dropping toward/under 40 deg, slip staying near/under 2.9-3.0, zero falls preserved, DR-0 fixed-forward gate not regressed. Prediction-if-false: dir_err unchanged/worse or slip/falls regress -- forks to a walk_cmd_stage curriculum ramp or a from-scratch stress_mix run; the tf/mlp matched-pair comparison stays intact either way.

**gate**: Fresh eval_joystick_gate (60s stress_mix, n=24, DR-0): PASS/continue-worthy needs direction_err_med improving materially toward/under 40 deg (from 45.5) with slip_per_m_med staying <=2.9-3.0ish and zero-or-near-zero falls. Re-run eval_cmd_suite + plain DR-0 fixed-forward gate to confirm no regression off the current baseline (prog_ratio med 0.41, gait_valid 6/6, zero terminations). FAIL: unchanged/worse direction or regressed slip/falls with flat reward -- forks to curriculum staging or from-scratch.

