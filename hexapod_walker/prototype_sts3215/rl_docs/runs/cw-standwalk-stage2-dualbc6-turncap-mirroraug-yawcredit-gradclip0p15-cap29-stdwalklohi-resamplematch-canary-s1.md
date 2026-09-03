# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-resamplematch-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-03T09:27:26+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-acq1-s1

**hypothesis**: Plain English: seed-1 companion to resamplematch-canary -- same question, does matching training's command-resample rate to the eval's faster stress_mix diet close the steering gap, replicated on the seed-1 twin.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same gate as resamplematch-canary (seed0): probe_turn_authority wz_med >=0.07 rad/s; det+sto walk-mode read under stress_mix/resample_s=4.0/jitter=0.5 vs stdwalklohi-acq1-s1 session baseline (43.6deg/27.26-28.2deg windowed, slip 2.939); PASS if direction_err_med or course_err_1s_med drops >=20% without slip>~3.0 or falls; PARTIAL if authority+zero-fall hold but steering doesn't move; FAIL if authority regresses or terminations appear.

**refused_reason**: hexapod-mjx-train-2 already runs cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-turndiet-canary-s1 — GPU pods host exactly one run; pick a free GPU pod.

