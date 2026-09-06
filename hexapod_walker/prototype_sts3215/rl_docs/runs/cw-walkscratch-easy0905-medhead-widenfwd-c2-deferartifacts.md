# cw-walkscratch-easy0905-medhead-widenfwd-c2-deferartifacts

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T04:13:07+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1

**hypothesis**: Two questions in one bounded run. INFRA (primary, operator fb_20260906T035950_cd260e): with the new --defer-final-artifacts handoff, the GPU-owning trainer process exits within ~1 min of optimization finishing (GPU memory actually freed, verified by process census on the pod) while a detached CPU-only finalizer completes and logs the outstanding eval/video jobs to the same W&B run (registry phase training->artifacts_pending->evaluated, ops.sh handoff). Prediction-if-true: trainer process gone + ~0GB GPU used while finalizer.log shows jobs completing; final video + evals present in W&B; state.json phase=evaluated. Prediction-if-false: trainer still resident after budget (ordering bug), or missing/duplicate W&B artifacts (handoff bug). Strongest alternative: wandb resume rejected after run.finish -> finalizer logs nothing (visible in finalizer.log). SCIENCE (secondary): seed-2 replication of the medhead-widenfwd 1g forward-composition discovery canary (seed-1 PASSed 23/24 gv, 0 falls) -- mechanism-health read only.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. INFRA gate: after training completes, pod census shows no trainer process holding GPU memory while state.json advances to evaluated with all jobs done and the final video visible in W&B; an operator-forced finalizer interruption + rerun resumes without duplicate delivery. SCIENCE gate (canary-scope): mechanism health -- six-leg participation, 0 falls, gait_valid majority in walk/det, consistent with seed-1's 23/24.

