# cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-acq8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-08-30T21:19:08+00:00

**pod**: hexapod-mjx-train-2

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary

**hypothesis**: Plain English: does the anchor14coef1 unified-policy RL fine-tune keep improving the dualbc4_walkteach (all-heading/turn-capable teacher-adoption) canary with an 8M-step acquisition budget, the same promote-on-PASS convention already validated twice on the dualbc3-dagger lineage (canary->acq8m PASS, progress_ratio 0.28->0.429, slip 3.39->2.55)? Canary cleared its mechanism-health gate (det walk gait_valid 6/6, prog_med 0.46, course_err_1s_med ~6deg inside walkteach-acq12m's 0.31-0.46 band, 0 sac/terms, wiring check PASS) -- straight continuation from the canary's own checkpoint, no cfg change.

**gate**: ACQUISITION (own-scope): det walk gait_valid stays >=5/6, sacrificed legs stay 0, progress_ratio improves or holds vs the canary's 0.43-0.46 (not regresses), slip/m stays inside teacher band (<=2.9), course_err_1s_med does not regress below walkteach-acq12m's own band, zero new walk terminations. Full DONE-gate mixedsession read follows per dualbc3 convention before any further unified-policy budget.

