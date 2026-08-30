# cw-standwalk-unified1-joyfix-coursedisp-w015-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-08-29T07:58:55+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-unified1-mix-long-s0

**wandb_id**: rooax70o

**hypothesis**: Plain English: the short-window dose point of the sub-stride course-displacement sweep (1.5s -> 0.15s; sibling w035-c1 is 0.35s) -- prices where the body drifted over the last 15 ticks, well below the ~0.375s half-stride sway timescale, the closest displacement-based analogue to per-tick heading pricing without the raw velocity tax that blew slip 2.5x in cmdtrack-c1. Motivation and measurements identical to w035-c1 (probe_dir_floor 08-29: matched-condition reference floor 13.5/5.4 deg per-tick vs this policy's 60.3/32.4; windows >=0.75s provably blind to the excess). Bank: test_course_disp_window_semantics.py 22/22 green at 0.35/0.15. Predict-if-true: dir_err_mean drops >=15deg at 2M, slip in band; if w015 moves dir_err but w035 does not, the sway timescale is even shorter than half-stride; if both flat, sub-stride displacement pricing is closed. Predict-if-false: flat dir_err or slip blowup -> route sway to stage-2 distillation. Strongest alternative: at 0.15s the displacement estimate degenerates toward noisy velocity and re-taxes honest motion (the cmdtrack failure mode) -- watch slip.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY at 2M. PASS-with-delta: reward_walk_course_disp telemetry on >=50% of commanded walk ticks AND DR-0 det walk direction_err_mean_deg drops >=15deg vs long-s0's ~55-65deg band AND slip/m within 1.5x parent band AND gait_valid>=5/6, no new sacrificed leg, session terminations<=6/90 -> escalate winner of w035/w015 to 2-seed acquisition. PASS-no-delta (fires >=50% but dir_err flat): sub-stride window lever closed -- do NOT fund further coursedisp window/dose arms; route the sway problem to stage-2 distillation. FAIL: reward collapse (vs long-s0 matched-step trend), terminations>6/90, or slip/m >1.5x parent band -> mechanism reverts to window=1.5 default.

**verdict**: CANARY PASS (mechanism live, no delta on the gate metric -- PASS-no-delta per the run's own pre-registered branch). The sub-stride window=0.15s dose of k_walk_course_disp fires on the majority of commanded walk ticks but does NOT move direction error off the flat band. Mechanism-fires check: fresh --course-trace re-measurement this cycle (n=6 det walk episodes, 35912/36000 ticks, run on-pod train-2) shows walk_course_disp_speed_m_s populated on 55.4% of COMMANDED ticks (4354/7856) -- clears the >=50% bar (corrects an earlier n=1 probe on record that used the wrong denominator, all-ticks not commanded-ticks, and read 14.3%; the all-tick denominator here is 12.1%, matching that earlier probe's ballpark and explaining the discrepancy -- it was measuring episode-wide dilution by non-walk-commanded ticks, not mechanism inactivity). Direction error: DR-0 gate n=12 det (walk+walk_startjitter) direction_err_mean_deg medians 56.5/64.1deg -- squarely inside long-s0's pre-existing 55-65deg band, matching the run's own mixedsession official read (direction_err_med_deg 67.925, n=88 pooled dr0+owndr+dr0_long) -- no >=15deg drop by any measurement, so PASS-with-delta is ruled out. Not a FAIL either: mixedsession terminations 3/90 (cap 6/90), slip_per_m_med 13.15 pooled / walk-sto-mode-only 18.31 vs long-s0's own ~18.1 sto baseline (flat, nowhere near the 1.5x=27.15 FAIL bar), gait_valid stays true/6-6 throughout, zero new sacrificed legs, reward did not collapse (train quarters 36.0/-15.1/-468.0/-146.1 -- noisy but this is the expected repricing-dip-then-recovery shape already seen on c1, not a collapse). CLOSES the sub-stride window lever per the gate's own text: do not fund further coursedisp window/dose arms; route the sway/direction problem to a structural fix. Joins coursedisp-c1 (window=1.5s, CANARY PASS/no-delta) -- see w035-c1's own verdict this cycle for the 3rd window value, completing the trio.

