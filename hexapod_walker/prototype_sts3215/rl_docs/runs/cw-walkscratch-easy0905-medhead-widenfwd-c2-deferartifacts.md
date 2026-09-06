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

**verdict**: CANARY PASS. The new deferred-artifacts handoff works end to end: the GPU is freed the moment training ends while a CPU-only finalizer completes and uploads every eval/video artifact, with no duplicates, surviving two forced interruptions. Evidence (INFRA gate, primary): trainer exited ~30s after model.learn returned; nvidia-smi on train-2 read 0 MiB used from handoff through finalization (vs ~46GB retained for 6-10 min on every pre-change run); registry advanced training -> artifacts_pending (3 jobs, durable snapshots) -> evaluated (3/3 done, 0 failed); W&B run o81ovjq7 holds exactly 2 video rows + 1 eval row (no dup deliveries) with the final walking reel logged post-hoc by the resumed finalizer; a SIGKILL mid-eval-job left in_flight/attempts=1 and the rerun skipped the done job, retried the killed one exactly once (attempts=2), and completed. Two real defects were found and fixed by this canary: (1) inherited WANDB_SERVICE made the detached finalizer attach to the trainer's dead wandb-core service (HandleAbandonedError) -- spawn env + finalizer startup now scrub WANDB*SERVICE* vars (tag exp/gpu-artifact-handoff-wandbservice-fix); (2) train-pod pid-1 does not reap orphans, so a SIGKILLed finalizer zombie made os.kill(pid,0) report the lock owner live and refused a legitimate resume -- liveness now requires a running artifact_finalizer cmdline (tag exp/gpu-artifact-handoff-zombielock-fix). SCIENCE (secondary, mechanism-health only): seed-2 of the medhead-widenfwd 1g forward-composition looks mechanism-healthy on the final reel (upright six-leg walking, 0 falls, 4/4 walk:ok, walk_fwd canaries 2/2 at the 1M eval); formal gait_valid count awaits the watcher's standard prestage eval -- treat the seed-2 replication read as advisory until that lands. Not a robot-skill PASS (no SKILLS.md row): this run's deliverable is fleet infrastructure. Next: flag stays default-OFF; adoption decision (e.g. flipping it on for long ACQ runs where the 6-10 min GPU retention actually bites) belongs to a future cycle with this canary as evidence.

