# cw-walk-allheading-tf-acq1-stdanneal

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-08-29T18:31:05+00:00

**pod**: hexapod-mjx-train-0

**steps**: 15000000

**parent**: cw-walk-allheading-tf-acq1

**wandb_id**: lb1nx8m1

**hypothesis**: Plain English: the just-finished 40M all-heading transformer walker learned a real, clean, six-leg forward det gait (prog_ratio med 0.33, gait_valid 6/6, zero falls) but its policy action std ran away UNBOUNDED the whole run (0.40->1.91, no anneal), which crashed training reward in the back half and makes the stochastic-mode gate collapse completely (walk/sto: prog med -0.00, slip/m med 18.1, gait_valid 5/6, 1 over_current term). This exact signature (sto-mode collapse from an unannealed std) has already been fixed twice on this codebase by --log-std-final (standwalk stance-hold/lower champions; joystick phasedir9 stotight ladder), always without eroding det behavior. Single lever: continue from the JUST-FINISHED 40M checkpoint (--init-from-source, not the 2M canary) with --log-std-final -3.0 (anneal starts from the checkpoint's OWN current mean log_std ~0.65 in log-space, not a fresh value) over 15M new steps, nothing else changed. Prediction-if-true: train/std falls back toward ~0.05-0.15 over the anneal, rollout/ep_rew_mean stops crashing and recovers toward/past its mid-run peak (~170), and a fresh DR-0 gate shows walk/sto closing most of the gap to walk/det (progress_ratio rising off ~0.00, slip/m falling toward the walk/det level, terminations dropping) with walk/det NOT regressing. Prediction-if-false: annealing std this late (after 40M of runaway) also freezes the det gait's own further improvement or the sto gap does not close -- would indicate the defect needs a fresh-run fix (--log-std-final from step 0) rather than a late repair. Strongest alternative: 15M is not enough for a full anneal to take hold this late -- judge on trend (std falling, reward recovering), not absolute gate pass, per 08-21.

**gate**: Fresh DR-0 gate (walk/det+sto, walk_startjitter/det+sto, n=6 each) at the end of the 15M continuation: walk/sto progress_ratio med >=0.15 (up from -0.00), slip/m med <=6.0 (down from 18.1), zero-or-near-zero over_current terminations, walk/det NOT regressed (progress_ratio med still >=0.25, gait_valid still >=5/6, zero terminations). train/std should be visibly falling/bounded by the end, not still climbing. Full eval_cmd_suite balanced-heading panel remains the track's own cheap-first-gate text for a real PASS; this arm's own gate is the narrower std-anneal repair question.

**verdict**: Result: the std-anneal repair works cleanly on the transformer twin too -- PASSES its own pre-registered gate outright, matching the MLP twin near-exactly. Evidence: fresh DR-0 gate (n=6 each) walk/det prog med 0.41 (up from 0.33, gate wanted >=0.25, NOT regressed), walk/sto prog med 0.36 (up from -0.00, gate wanted >=0.15), slip/m med 2.10 sto / 2.42 det (down from 18.1, gate cap 6.0, now inside the joystick teacher band <=2.9), gait_valid 6/6 in all four sub-panels, zero terminations anywhere. train/std fell 1.92->0.05 exactly as predicted; rollout/ep_rew_mean recovered (quarters 7.4/-160.9(early noise)/.../1328.8 ending well past its old ~170 mid-run peak). Video (frame strips, all 4 sub-panels) shows the same clean upright six-leg cycling gait as the MLP twin -- no pathology, no architecture-specific difference. Why: 3rd confirmed instance of the --log-std-final fix on this codebase (standwalk hold/lower champions, joystick stotight ladder); the tf/mlp matched-lever design confirms the fix and the underlying walk skill are architecture-independent, so the simpler/cheaper MLP is the practical champion going forward. What's next: kicked off the track's still-missing 'cheap first gate' (eval_cmd_suite balanced 8-heading panel, new suite rl_move/sim/cmd_suites/allheading8_v08.json) on both checkpoints to verify the balanced-heading claim directly (per-heading completion/falls) rather than inferring it from the mixed-heading DR-0 sample.

