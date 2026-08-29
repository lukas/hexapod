# cw-walk-allheading-mlp-acq1-rr1-stdanneal

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-08-29T18:47:08+00:00

**pod**: hexapod-mjx-train-3

**steps**: 15000000

**parent**: cw-walk-allheading-mlp-acq1-rr1

**hypothesis**: Plain English: the MLP twin of cw-walk-allheading-tf-acq1 (this same cycle's cw-walk-allheading-mlp-acq1-rr1, verdict PARTIAL) learned the identical real, clean six-leg forward det gait (prog med 0.28, gait_valid 6/6, zero terminations) but its policy action std ran away UNBOUNDED the whole 40M run (0.42->2.57, no anneal), crashing training reward in the back half and collapsing the stochastic-mode gate (walk/sto: prog med -0.00, slip/m med 19.55, gait_valid 4/6, 1 over_current term). This exact signature has already been fixed twice on this codebase by --log-std-final (standwalk stance-hold/lower champions; joystick phasedir9 stotight ladder), and the exact same fix is already running for the transformer twin (cw-walk-allheading-tf-acq1-stdanneal). Single lever: continue from the finished 40M checkpoint with --log-std-final -3.0 (anneal starts from the checkpoint's own current mean log_std, not a fresh value) over 15M new steps, nothing else changed -- keeps the tf/mlp matched-lever comparison intact. Prediction-if-true: train/std falls back toward ~0.05-0.15, rollout/ep_rew_mean stops crashing and recovers toward/past its mid-run peak, and a fresh DR-0 gate shows walk/sto closing most of the gap to walk/det (progress rising off ~0.00, slip falling toward the det level, terminations dropping) with walk/det NOT regressed. Prediction-if-false: annealing this late also freezes det improvement or the sto gap does not close -- would indicate the defect needs a fresh-run fix (--log-std-final from step 0), and the mlp/tf comparison would need a matched from-scratch retry. Strongest alternative: 15M is not enough for the anneal to fully take hold this late -- judge on trend per 08-21, not absolute gate pass.

**gate**: Fresh DR-0 gate (walk/det+sto, walk_startjitter/det+sto, n=6 each) at the end of the 15M continuation: walk/sto progress_ratio med >=0.15 (up from -0.00), slip/m med <=6.0 (down from 19.55), zero-or-near-zero over_current terminations, walk/det NOT regressed (progress_ratio med still >=0.20, gait_valid still >=5/6, zero terminations). train/std should be visibly falling/bounded by the end, not still climbing. Full eval_cmd_suite balanced-heading panel remains the track's own cheap-first-gate text for a real PASS; this arm's own gate is the narrower std-anneal repair question, matched to the tf twin's own stdanneal gate.

