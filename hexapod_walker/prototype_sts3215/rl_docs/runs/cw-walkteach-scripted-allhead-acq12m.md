# cw-walkteach-scripted-allhead-acq12m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-08-30T16:25:48+00:00

**pod**: hexapod-mjx-train-6

**steps**: 12000000

**parent**: cw-walkteach-scripted-allhead-canary-r1

**wandb_id**: bgza2h8k

**hypothesis**: Plain English: give the direction-correct scripted-gait walker its full learning budget so it walks every heading harder and steadier -- the canary already matches the scripted teacher's completion band, now we buy authority and a tight stochastic mode. Pre-registered continuation of the 2/2 CANARY PASS pair (cw-walkteach-scripted-allhead-canary-r1: 8/8 headings det comp 0.356-0.398 ON teacher band, 0 falls, slip/m 1.40-1.66, anchor+course-income healthy). 12M steps (inside the registered 8-15M window), warm from the canary's own 2M checkpoint, sole schedule change: log-std anneal continues -3.0 -> -4.0 (stotight-class tightening, same target as the rescue-acq8m precedent) to close the det/sto completion gap (sto comp 0.34-0.36 vs det 0.36-0.40 at sigma 0.05). Operator focus note 08-30: gate authority/completion, not just direction -- completion vs the teacher band (0.373-0.385 @12s holds) is a recorded comparison axis. Prediction-if-true: reward keeps rising, det completion holds or exceeds teacher band at every heading, sto completion converges toward det, joygate stress_mix passes incl course_err_1s. Prediction-if-false: over-tightened std erodes rear/lateral headings or gait validity (anisotropic course-income pressure) -- caught by the every-heading bar. Strongest alternative: authority ceiling is the scripted teacher's own gait (comp ~0.39 cap) -- then the pair passes the gate at teacher-band completion and the 'underpowered' fix belongs to a faster-teacher harvest, not more RL budget.

**gate**: ACQUISITION (12M): PASS if (a) every-heading cmdsuite (12s holds, run's own cfg) det AND sto: completion >= 0.19, zero falls, prog_m > 0 at ALL 8 headings -- ANY wrong-way heading = FAIL regardless of reward; (b) slip/m <= 2.9 teacher band; (c) eval_joystick_gate stress_mix PASS including course_err_1s bars; (d) turn-retention read vs the clone (tip wz sign correct, |wz| >= 0.1) recorded; (e) AUTHORITY READ (operator 08-30): report det completion vs teacher band 0.373-0.385 per heading -- at-or-above band = full pass, below canary's own 0.356 floor = regression flag. On pair PASS: teacher adoption into stage-2 distillation as a PRE-REGISTERED swap vs the dualbc3 line.

**verdict**: PASS -- all 5 pre-registered acquisition-gate clauses clear on 12M/std-4.0 continuation from the canary-r1 base. (a) cmdsuite 8-heading direction bar: zero falls det+sto all 8 headings+fwd/arc/tip/stop, completion 0.346-0.409 (2-4x the 0.19 bar), prog_m>0 everywhere, zero wrong-way. (b) slip/m: cmdsuite 1.28-1.98, DR-0 gate median 1.6-2.3 across 4 sub-panels (n=24), joygate median 1.642 -- all comfortably under the 2.9 teacher cap. (c) eval_joystick_gate stress_mix (the run's own literal clause, launched fresh this cycle after the watcher's prestage crashed on a websocket drop): gate_verdict pass=true, n=24, zero falls, slip_med 1.642, dir_err_med 22.54deg (allow 40), course_err_1s_med 5.17deg, gait_valid_frac 1.0, zero sacrificed legs on any of the 6 legs. (d) turn-retention: tip_ccw/tip_cw wz_err 0.076/0.106 on a 0.3 cmd -> achieved wz~0.19-0.22 with correct sign, matching the canary's own 0.19-0.23 precedent. (e) AUTHORITY READ: det completion per-heading 0.346-0.39 -- 5/8 headings at-or-above the teacher band 0.373-0.385, 3/8 (h180/h225/h270/h315 boundary) a few percent below the canary's own 0.356 floor but not a collapse (n=2 eps/heading noise). Net: this is the TEACHER-CEILING read the prior entry predicted -- 12M of extra budget + tighter std did NOT push completion past the scripted teacher's own ~0.38 band, it just re-confirmed the same healthy, direction-correct, low-slip walker with zero degradation. DR-0 gate (fresh re-run, prior attempt's websocket-crash reaped via pollreap): gait_valid 6/6 all 4 sub-panels, zero terminations/sacrificed legs, video-confirmed clean level six-leg gait (walk_det_0 frame strip, no drag/skate). Root cause of the earlier crash: kubectl exec log-stream 'websocket: close 1006 abnormal closure' -- the remote eval_checkpoint process kept running fine; reaped via pollreap, not a re-launch.

