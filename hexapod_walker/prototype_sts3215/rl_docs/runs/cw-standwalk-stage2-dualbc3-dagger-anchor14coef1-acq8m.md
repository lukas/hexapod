# cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-acq8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-08-30T12:18:26+00:00

**pod**: hexapod-mjx-train-0

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary

**hypothesis**: Plain English: the dualbc3_dagger-based anchor14coef1 2M canary just PASSED cleanly on a genuinely-walking base (both seeds: det walk gait_valid 8/8, zero sacrificed legs, zero falls, progress_ratio 0.28/0.39 -- well above the 0.10-0.18 band the same recipe showed on the OLD stotight45 teacher). Per this track's own repeated 2M-canary-PASS -> 8M-acquisition convention (bcanchor1/3, anchor14-walkretaincoef1-rescue-acq8m, meshref-8m), does the walk quality keep compounding with 4x the budget the way it did for every prior instance of this exact convention, now for the first time on a genuinely-repaired (DAgger, not raw BC) Stage-2 walk base?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. ACQUISITION READ (paired 2-seed call, same convention as anchor14-walkretaincoef1-rescue-acq8m): compare 8M det walk DR-0 gate + own-DR against this run's own 2M canary snapshot (prog_ratio med 0.28 DR-0, slip/m med 3.39, gait_valid 8/8 sac=[]). PASS if BOTH seeds show gait_valid stays >=5/6 with zero/near-zero sacrificed legs AND progress_ratio improves (not just noise) over the 2M snapshot with slip/m flat-or-improving. PARTIAL if gait_valid holds but progress_ratio is flat. FAIL only if gait_valid regresses below 5/6 or sacrificed legs reappear on either seed (the anchor4-class catastrophe returns under more training).

**refused_reason**: canary runs cap at 2000000 steps (asked 8000000): the question is 'is the training mechanism healthy?' - continue as --phase acquisition with --evidence.

