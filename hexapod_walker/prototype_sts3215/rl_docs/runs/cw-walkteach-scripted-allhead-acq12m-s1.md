# cw-walkteach-scripted-allhead-acq12m-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-08-30T16:30:39+00:00

**pod**: hexapod-mjx-train-7

**steps**: 12000000

**parent**: cw-walkteach-scripted-allhead-canary-s1-r1

**wandb_id**: 3cj4qf8n

**hypothesis**: SEED TWIN (seed 1) of cw-walkteach-scripted-allhead-acq12m -- identical 12M continuation, distinct lineage (warm from its OWN canary-s1-r1 2M checkpoint). Plain English: give the direction-correct scripted-gait walker its full learning budget so it walks every heading harder and steadier; two seeds make the pass-rate claim. Sole schedule change vs canary: log-std anneal continues -3.0 -> -4.0 (stotight-class). Operator focus note 08-30: completion/authority vs teacher band (0.373-0.385 @12s holds) is a recorded comparison axis. Prediction-if-true: matches seed 0 -- det completion holds/exceeds teacher band every heading, sto converges to det, joygate stress_mix PASS. Prediction-if-false: std tightening erodes rear/lateral headings on one seed only -- pair divergence localizes it to seed noise, not mechanism. Strongest alternative: teacher-gait authority ceiling (~0.39 comp cap) -- then pass lands at teacher band and 'underpowered' is a harvest problem, not an RL-budget problem.

**gate**: ACQUISITION (12M, JOINT with seed 0): PASS if (a) every-heading cmdsuite (12s holds, own cfg) det AND sto: completion >= 0.19, zero falls, prog_m > 0 at ALL 8 headings -- ANY wrong-way heading = FAIL regardless of reward; (b) slip/m <= 2.9 teacher band; (c) eval_joystick_gate stress_mix PASS including course_err_1s bars; (d) turn-retention read vs the clone recorded; (e) AUTHORITY READ (operator 08-30): det completion vs teacher band 0.373-0.385 per heading -- at-or-above = full pass, below the canary pair's 0.356 floor = regression flag. On pair PASS: teacher adoption into stage-2 distillation as a PRE-REGISTERED swap vs the dualbc3 line.

**verdict**: PASS -- second-seed replicate confirms the acq12m result, not a lucky seed0 draw. (a) cmdsuite direction bar: zero falls det+sto all 8 headings+fwd/arc/tip/stop, completion 0.307-0.457, prog_m>0 everywhere. (b) slip/m: cmdsuite 1.35-1.99, DR-0 gate median 1.74-2.26 across 4 sub-panels (n=24), joygate median 1.76 -- all under the 2.9 cap. (c) eval_joystick_gate stress_mix (launched fresh this cycle, same as seed0): gate_verdict pass=true, n=24, zero falls, slip_med 1.76, dir_err_med 24.29deg (allow 40), course_err_1s_med 4.5deg, gait_valid_frac 1.0, zero sacrificed legs any of 6 legs. (d) turn-retention: tip wz_err 0.081-0.100 on a 0.3 cmd -> achieved wz~0.20-0.22 correct sign, matches seed0/canary precedent. (e) authority read: det completion 0.333-0.398 per heading -- most at/above the 0.373-0.385 band, h135 (0.333) a few percent below the canary's 0.356 floor, same teacher-ceiling pattern as seed0, no collapse. DR-0 gate clean: gait_valid 6/6 all 4 sub-panels, zero terminations/sacrificed legs. Same crash-then-reap story as seed0 (kubectl websocket drop mid-stream, remote eval finished fine, reaped via pollreap).

