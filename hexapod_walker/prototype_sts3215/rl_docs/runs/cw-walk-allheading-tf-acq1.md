# cw-walk-allheading-tf-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PARTIAL

**created**: 2026-08-29T15:35:25+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walk-allheading-tf-scratch1

**wandb_id**: 35mge3z0

**hypothesis**: Plain English: continue the healthy all-heading transformer walker (2M mechanism canary PASSED: bc-anchor loss falling, course-income mechanism live and recovering through the from-scratch 100Hz reward valley, no NaN/collapse, twin-matched reward) into a real 40M learning budget so it can actually acquire balanced-direction walking. Prediction-if-true: course-income share keeps climbing past the valley (already ticking up in the canary's last 100k steps) and by 40M the balanced 8-heading eval_cmd_suite panel shows every heading moving at >=half the teacher's own completion (>=0.19) with zero falls. Prediction-if-false: course-income share stays pinned near the canary's trough / support keeps falling -- BC-anchor imitation is dominating the objective over command-following and the walker never learns real course-following motion; audit anchor-vs-income coefficient balance before further budget. Strongest alternative: 40M still is not enough to fully exit the valley (08-24 FACT: the MLP reference sibling only crossed zero reward at 12-14M) -- judge interim checkpoints on trend (course-income share direction, bc-anchor loss), never absolute value.

**gate**: 40M acquisition. Cheap first gate (per the canary's own pre-registered gate text): eval_cmd_suite balanced-heading panel, 8 headings x 0.08 m/s + stop, det+sto -- EVERY heading must move (completion >=0.19, half the teacher's measured 0.373-0.385) with zero falls; lateral/reverse weakness = not passed. Full session/mixed-command hardening is a later rung, not this gate.

**verdict**: Real det-mode walking achieved (progress_ratio med 0.33, gait_valid 6/6, ZERO terminations, clean six-leg gait on video) but the registered det+sto gate is NOT met and reward CRASHED in the back half (quarters 150.7/139.7/-38.8/-310.1) -- root cause is a shared, cross-architecture PPO optimizer defect, not a dead lineage. Evidence: train/std (policy action std) grew UNBOUNDED across the whole 40M run, 0.40->1.91 (this run's own MLP twin cw-walk-allheading-mlp-acq1-rr1, read this cycle for comparison only, shows the identical shape even worse: 0.42->2.57), while rollout/ep_rew_mean peaks mid-run (~170/343) then collapses in the second half in BOTH arms -- an entropy/log_std runaway (ent_coef=0.01, no anneal) that torches stochastic-mode rollouts once the policy has learned enough that the entropy bonus starts dominating the advantage signal. DR-0 gate confirms the split cleanly: walk/det n=6 prog med 0.33, slip med 3.13, fwd med 0.37m, gait_valid 6/6, 0 terminations -- genuine partial forward progress at ~25-35% of the 0.08 m/s target, matching env/walk_speed's real 0.018-0.036 m/s over the run; walk/sto n=6 collapses to prog med -0.00, slip med 18.1 (cap intent ~3), gait_valid 5/6 with 1 over_current termination -- the huge sampled std (1.9) destroys the tuned gait entirely. This is NOT a reward-alignment problem (the det behavior shows the reward's optimum IS real forward walking) and going longer on the SAME recipe would only make it worse per the still-climbing std trend -- it needs the fix this exact codebase already proved twice: --log-std-final annealing (closed the identical sto-mode-collapse-from-runaway-std signature on the standwalk stance-hold/lower champions AND the joystick phasedir9 stotight ladder, both cited in SKILLS.md). Launching a continuation with that lever this cycle rather than closing the lineage.

