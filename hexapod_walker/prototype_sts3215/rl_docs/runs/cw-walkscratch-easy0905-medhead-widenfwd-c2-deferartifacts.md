# cw-walkscratch-easy0905-medhead-widenfwd-c2-deferartifacts

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T04:13:07+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1

**wandb_id**: o81ovjq7

**hypothesis**: Two questions in one bounded run. INFRA (primary, operator fb_20260906T035950_cd260e): with the new --defer-final-artifacts handoff, the GPU-owning trainer process exits within ~1 min of optimization finishing (GPU memory actually freed, verified by process census on the pod) while a detached CPU-only finalizer completes and logs the outstanding eval/video jobs to the same W&B run (registry phase training->artifacts_pending->evaluated, ops.sh handoff). Prediction-if-true: trainer process gone + ~0GB GPU used while finalizer.log shows jobs completing; final video + evals present in W&B; state.json phase=evaluated. Prediction-if-false: trainer still resident after budget (ordering bug), or missing/duplicate W&B artifacts (handoff bug). Strongest alternative: wandb resume rejected after run.finish -> finalizer logs nothing (visible in finalizer.log). SCIENCE (secondary): seed-2 replication of the medhead-widenfwd 1g forward-composition discovery canary (seed-1 PASSed 23/24 gv, 0 falls) -- mechanism-health read only.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. INFRA gate: after training completes, pod census shows no trainer process holding GPU memory while state.json advances to evaluated with all jobs done and the final video visible in W&B; an operator-forced finalizer interruption + rerun resumes without duplicate delivery. SCIENCE gate (canary-scope): mechanism health -- six-leg participation, 0 falls, gait_valid majority in walk/det, consistent with seed-1's 23/24.

**verdict**: CANARY PASS (unchanged from prior verdict; adding the science read that was advisory-only at last write-up). The new deferred-artifacts handoff works end to end: the GPU is freed the moment training ends while a CPU-only finalizer completes and uploads every eval/video artifact, with no duplicates, surviving two forced interruptions. Evidence (INFRA gate, primary): trainer exited ~30s after model.learn returned; nvidia-smi on train-2 read 0 MiB used from handoff through finalization (vs ~46GB retained for 6-10 min on every pre-change run); registry advanced training -> artifacts_pending -> evaluated (3/3 done, 0 failed); W&B run o81ovjq7 holds exactly 2 video rows + 1 eval row (no dup deliveries). Two real defects found+fixed: inherited WANDB_SERVICE env leaking into the detached finalizer (tag exp/gpu-artifact-handoff-wandbservice-fix); pid-1-no-reap zombie-lock false-liveness on a SIGKILLed finalizer (tag exp/gpu-artifact-handoff-zombielock-fix). SCIENCE (secondary, now CONFIRMED not advisory): the standard prestage gate has landed -- aggregate gait_valid 23/24, IDENTICAL to seed-1's own 23/24 (walk/det 5/6 one non-chronic sac=[0], walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6). 0 falls/24. Confirms seed-2 of the medhead-widenfwd 1g forward-composition is mechanism-healthy, matching seed-1 -- a 2nd independent seed for this specific axis/base pairing. Still not a robot-skill PASS on its own (no SKILLS.md row; deliverable is fleet infra) but the science read no longer needs the advisory caveat. Next: flag stays default-OFF pending an adoption decision; launched a matched 40M ACQ continuation for the widenfwd-c2 seed itself (2nd-seed replication discipline, matching medhead-widenfwd-c1's own ACQ PASS precedent) now that mechanism health is confirmed.

