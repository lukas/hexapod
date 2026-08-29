# cw-walk-allheading-mlp-acq1-rr1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PARTIAL

**created**: 2026-08-29T16:43:37+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walk-allheading-mlp-scratch1

**wandb_id**: 0b8y4nko

**hypothesis**: Plain English: retry of cw-walk-allheading-mlp-acq1 (CRASHED by an infra OOM at 17.5M/40M with no science signal -- training was healthy/unremarkable up to the crash, no checkpoint survived the pod's death) -- re-continue the healthy matched-step MLP control twin from its last recoverable checkpoint (the scratch1 canary) into the same real 40M learning budget alongside its transformer sibling cw-walk-allheading-tf-acq1 (now past 21M, unaffected), so the pair stays comparable through acquisition and this arm keeps serving as the reference trajectory the gate text names it as. Prediction-if-true: course-income share keeps climbing past the valley and by 40M the balanced 8-heading eval_cmd_suite panel shows every heading moving at >=half the teacher's own completion (>=0.19) with zero falls -- and the MLP either matches or falls behind the transformer, telling us whether the extra architecture capacity actually helps this task. Prediction-if-false: course-income share stays pinned near the canary's trough -- BC-anchor imitation dominates over command-following at this budget too, confirming the problem is reward composition, not architecture. Strongest alternative: 40M still is not enough to fully exit the valley (08-24 FACT: this exact sibling crossed zero reward only at 12-14M in the prior architecture-canary precedent) -- judge interim checkpoints on trend, never absolute value. Secondary purpose: if THIS pod also OOMs, that is evidence of a real memory-leak defect in this recipe/trainer combination rather than pod-accumulated infra cruft, and should be escalated.

**gate**: 40M acquisition, same gate as the transformer twin: eval_cmd_suite balanced-heading panel, 8 headings x 0.08 m/s + stop, det+sto -- EVERY heading must move (completion >=0.19, half the teacher's measured 0.373-0.385) with zero falls; lateral/reverse weakness = not passed.

**verdict**: Same std-runaway pathology as its transformer twin (cw-walk-allheading-tf-acq1), confirmed on this arm's own DR-0 gate + video. Evidence: train/std climbed unbounded the whole 40M run (0.42->2.57, wandb_history.csv, no anneal set); walk/det is a real, clean six-leg forward gait (report.json: prog med 0.28, slip med 3.32, fwd med 0.33m, gait_valid 6/6, zero terminations, video confirms upright cycling all six legs) but walk/sto collapses completely (prog med -0.00, slip med 19.55, gait_valid 4/6, 1 over_current term) -- the runaway std destroys the tuned gait once sampled. reward quarters [199.6, 228.0, 108.4, -93.9] crash in the back half exactly like the tf twin, same mechanism (entropy/log_std growth dominating the advantage once the gait is learned), not a dead lineage. This is the SAME diagnosis already fixed twice on this codebase (standwalk stance-hold/lower champions; joystick phasedir9 stotight ladder) via --log-std-final annealing, and the tf twin's own continuation (cw-walk-allheading-tf-acq1-stdanneal) is already running with that exact lever. Launching this run's own matched-recipe continuation (mlp-acq1-rr1-stdanneal) rather than closing the lineage, per the 08-21 ruling (rising-then-crashing reward + a known, previously-fixed mechanism = continue/realign, not FAIL).

