# cw-walk-allheading-mlp-acq1-rr1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-29T16:43:37+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walk-allheading-mlp-scratch1

**wandb_id**: 0b8y4nko

**hypothesis**: Plain English: retry of cw-walk-allheading-mlp-acq1 (CRASHED by an infra OOM at 17.5M/40M with no science signal -- training was healthy/unremarkable up to the crash, no checkpoint survived the pod's death) -- re-continue the healthy matched-step MLP control twin from its last recoverable checkpoint (the scratch1 canary) into the same real 40M learning budget alongside its transformer sibling cw-walk-allheading-tf-acq1 (now past 21M, unaffected), so the pair stays comparable through acquisition and this arm keeps serving as the reference trajectory the gate text names it as. Prediction-if-true: course-income share keeps climbing past the valley and by 40M the balanced 8-heading eval_cmd_suite panel shows every heading moving at >=half the teacher's own completion (>=0.19) with zero falls -- and the MLP either matches or falls behind the transformer, telling us whether the extra architecture capacity actually helps this task. Prediction-if-false: course-income share stays pinned near the canary's trough -- BC-anchor imitation dominates over command-following at this budget too, confirming the problem is reward composition, not architecture. Strongest alternative: 40M still is not enough to fully exit the valley (08-24 FACT: this exact sibling crossed zero reward only at 12-14M in the prior architecture-canary precedent) -- judge interim checkpoints on trend, never absolute value. Secondary purpose: if THIS pod also OOMs, that is evidence of a real memory-leak defect in this recipe/trainer combination rather than pod-accumulated infra cruft, and should be escalated.

**gate**: 40M acquisition, same gate as the transformer twin: eval_cmd_suite balanced-heading panel, 8 headings x 0.08 m/s + stop, det+sto -- EVERY heading must move (completion >=0.19, half the teacher's measured 0.373-0.385) with zero falls; lateral/reverse weakness = not passed.

