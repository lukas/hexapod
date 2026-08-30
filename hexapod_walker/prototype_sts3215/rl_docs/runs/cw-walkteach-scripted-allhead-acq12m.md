# cw-walkteach-scripted-allhead-acq12m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T16:25:48+00:00

**pod**: hexapod-mjx-train-6

**steps**: 12000000

**parent**: cw-walkteach-scripted-allhead-canary-r1

**wandb_id**: bgza2h8k

**hypothesis**: Plain English: give the direction-correct scripted-gait walker its full learning budget so it walks every heading harder and steadier -- the canary already matches the scripted teacher's completion band, now we buy authority and a tight stochastic mode. Pre-registered continuation of the 2/2 CANARY PASS pair (cw-walkteach-scripted-allhead-canary-r1: 8/8 headings det comp 0.356-0.398 ON teacher band, 0 falls, slip/m 1.40-1.66, anchor+course-income healthy). 12M steps (inside the registered 8-15M window), warm from the canary's own 2M checkpoint, sole schedule change: log-std anneal continues -3.0 -> -4.0 (stotight-class tightening, same target as the rescue-acq8m precedent) to close the det/sto completion gap (sto comp 0.34-0.36 vs det 0.36-0.40 at sigma 0.05). Operator focus note 08-30: gate authority/completion, not just direction -- completion vs the teacher band (0.373-0.385 @12s holds) is a recorded comparison axis. Prediction-if-true: reward keeps rising, det completion holds or exceeds teacher band at every heading, sto completion converges toward det, joygate stress_mix passes incl course_err_1s. Prediction-if-false: over-tightened std erodes rear/lateral headings or gait validity (anisotropic course-income pressure) -- caught by the every-heading bar. Strongest alternative: authority ceiling is the scripted teacher's own gait (comp ~0.39 cap) -- then the pair passes the gate at teacher-band completion and the 'underpowered' fix belongs to a faster-teacher harvest, not more RL budget.

**gate**: ACQUISITION (12M): PASS if (a) every-heading cmdsuite (12s holds, run's own cfg) det AND sto: completion >= 0.19, zero falls, prog_m > 0 at ALL 8 headings -- ANY wrong-way heading = FAIL regardless of reward; (b) slip/m <= 2.9 teacher band; (c) eval_joystick_gate stress_mix PASS including course_err_1s bars; (d) turn-retention read vs the clone (tip wz sign correct, |wz| >= 0.1) recorded; (e) AUTHORITY READ (operator 08-30): report det completion vs teacher band 0.373-0.385 per heading -- at-or-above band = full pass, below canary's own 0.356 floor = regression flag. On pair PASS: teacher adoption into stage-2 distillation as a PRE-REGISTERED swap vs the dualbc3 line.

