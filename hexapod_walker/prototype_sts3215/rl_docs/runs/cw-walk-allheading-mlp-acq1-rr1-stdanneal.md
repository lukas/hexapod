# cw-walk-allheading-mlp-acq1-rr1-stdanneal

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-08-29T18:47:08+00:00

**pod**: hexapod-mjx-train-3

**steps**: 15000000

**parent**: cw-walk-allheading-mlp-acq1-rr1

**wandb_id**: 8vkl1aci

**hypothesis**: Plain English: the MLP twin of cw-walk-allheading-tf-acq1 (this same cycle's cw-walk-allheading-mlp-acq1-rr1, verdict PARTIAL) learned the identical real, clean six-leg forward det gait (prog med 0.28, gait_valid 6/6, zero terminations) but its policy action std ran away UNBOUNDED the whole 40M run (0.42->2.57, no anneal), crashing training reward in the back half and collapsing the stochastic-mode gate (walk/sto: prog med -0.00, slip/m med 19.55, gait_valid 4/6, 1 over_current term). This exact signature has already been fixed twice on this codebase by --log-std-final (standwalk stance-hold/lower champions; joystick phasedir9 stotight ladder), and the exact same fix is already running for the transformer twin (cw-walk-allheading-tf-acq1-stdanneal). Single lever: continue from the finished 40M checkpoint with --log-std-final -3.0 (anneal starts from the checkpoint's own current mean log_std, not a fresh value) over 15M new steps, nothing else changed -- keeps the tf/mlp matched-lever comparison intact. Prediction-if-true: train/std falls back toward ~0.05-0.15, rollout/ep_rew_mean stops crashing and recovers toward/past its mid-run peak, and a fresh DR-0 gate shows walk/sto closing most of the gap to walk/det (progress rising off ~0.00, slip falling toward the det level, terminations dropping) with walk/det NOT regressed. Prediction-if-false: annealing this late also freezes det improvement or the sto gap does not close -- would indicate the defect needs a fresh-run fix (--log-std-final from step 0), and the mlp/tf comparison would need a matched from-scratch retry. Strongest alternative: 15M is not enough for the anneal to fully take hold this late -- judge on trend per 08-21, not absolute gate pass.

**gate**: Fresh DR-0 gate (walk/det+sto, walk_startjitter/det+sto, n=6 each) at the end of the 15M continuation: walk/sto progress_ratio med >=0.15 (up from -0.00), slip/m med <=6.0 (down from 19.55), zero-or-near-zero over_current terminations, walk/det NOT regressed (progress_ratio med still >=0.20, gait_valid still >=5/6, zero terminations). train/std should be visibly falling/bounded by the end, not still climbing. Full eval_cmd_suite balanced-heading panel remains the track's own cheap-first-gate text for a real PASS; this arm's own gate is the narrower std-anneal repair question, matched to the tf twin's own stdanneal gate.

**verdict**: Result: the std-anneal repair works cleanly on the MLP twin -- PASSES its own pre-registered gate outright. Evidence: fresh DR-0 gate (n=6 each) walk/det prog med 0.41 (up from 0.28, gate wanted >=0.20, NOT regressed), walk/sto prog med 0.36 (up from -0.00, gate wanted >=0.15), slip/m med 2.14 sto / 2.46 det (down from 19.55, gate cap 6.0, now inside the joystick teacher band <=2.9), gait_valid 6/6 in all four sub-panels (det/sto x walk/walk_startjitter), zero terminations anywhere. train/std fell 2.15->0.05 over the anneal exactly as predicted; rollout/ep_rew_mean recovered from the crash (quarters 8.6/-33.1/477.1/1100.3, ending well past its old mid-run peak). Video (frame strips, all 4 sub-panels) shows upright six-leg cycling gait, no pathology. Why: this is the 3rd confirmed instance of the same --log-std-final fix on this codebase (standwalk hold/lower champions, joystick stotight ladder) -- a fully general repair for unannealed-std sto-mode collapse, not a fluke. What's next: matched tf twin (cw-walk-allheading-tf-acq1-stdanneal) verdicted separately this cycle with near-identical numbers -- architecture doesn't matter here. Kicked off the track's own still-missing 'cheap first gate' (eval_cmd_suite 8-heading panel, new suite file rl_move/sim/cmd_suites/allheading8_v08.json) on both champions to check the balanced-heading claim directly rather than inferring it from the mixed-heading DR-0 sample.

