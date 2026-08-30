# cw-walkteach-scripted-allhead-acq12m-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T16:30:39+00:00

**pod**: hexapod-mjx-train-7

**steps**: 12000000

**parent**: cw-walkteach-scripted-allhead-canary-s1-r1

**wandb_id**: 3cj4qf8n

**hypothesis**: SEED TWIN (seed 1) of cw-walkteach-scripted-allhead-acq12m -- identical 12M continuation, distinct lineage (warm from its OWN canary-s1-r1 2M checkpoint). Plain English: give the direction-correct scripted-gait walker its full learning budget so it walks every heading harder and steadier; two seeds make the pass-rate claim. Sole schedule change vs canary: log-std anneal continues -3.0 -> -4.0 (stotight-class). Operator focus note 08-30: completion/authority vs teacher band (0.373-0.385 @12s holds) is a recorded comparison axis. Prediction-if-true: matches seed 0 -- det completion holds/exceeds teacher band every heading, sto converges to det, joygate stress_mix PASS. Prediction-if-false: std tightening erodes rear/lateral headings on one seed only -- pair divergence localizes it to seed noise, not mechanism. Strongest alternative: teacher-gait authority ceiling (~0.39 comp cap) -- then pass lands at teacher band and 'underpowered' is a harvest problem, not an RL-budget problem.

**gate**: ACQUISITION (12M, JOINT with seed 0): PASS if (a) every-heading cmdsuite (12s holds, own cfg) det AND sto: completion >= 0.19, zero falls, prog_m > 0 at ALL 8 headings -- ANY wrong-way heading = FAIL regardless of reward; (b) slip/m <= 2.9 teacher band; (c) eval_joystick_gate stress_mix PASS including course_err_1s bars; (d) turn-retention read vs the clone recorded; (e) AUTHORITY READ (operator 08-30): det completion vs teacher band 0.373-0.385 per heading -- at-or-above = full pass, below the canary pair's 0.356 floor = regression flag. On pair PASS: teacher adoption into stage-2 distillation as a PRE-REGISTERED swap vs the dualbc3 line.

