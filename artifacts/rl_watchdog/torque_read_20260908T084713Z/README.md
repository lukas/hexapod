# Seed7 torque closeout: corrected zero-shot comparison

The Cartesian ON policy already retains gait at normal torque before retraining. The joint-space OFF policy already has the same chronic-leg deficit subsequently seen in its trained child. The 2M continuations changed weights and some slip/speed metrics, but produced **no acquired gait recovery**.

Six exact reports are complete: each arm's frozen 40M parent at 3x torque, the corrected frozen parent at 1x (`_torque1x_zeroshot_evalfix1`), and its trained 1x child (`_torque1x_c1_gate`). Every report has four groups of six episodes and zero terminations. Corrected reports are canonical and available through native `eval_report` using their exact directory names. Original invalid zero-shot reports are excluded from all calculations.

| Arm | Group | Gait source 3x / zero-shot 1x / child 1x | Mean slip/m source 3x / zero-shot 1x / child 1x | Median net forward m/s zero-shot / child |
|---|---|---|---|---|
| ON | walk/det | 6/6 / 6/6 / 6/6 | 2.791 / 3.650 / 3.727 | 0.1425 / 0.1267 |
| ON | walk/sto | 6/6 / 6/6 / 6/6 | 3.220 / 5.652 / 5.231 | 0.0940 / 0.0973 |
| ON | jitter/det | 5/6 / 5/6 / 5/6 | 2.789 / 3.729 / 3.679 | 0.1307 / 0.1367 |
| ON | jitter/sto | 6/6 / 6/6 / 6/6 | 3.095 / 5.489 / 5.184 | 0.0928 / 0.1005 |
| OFF | walk/det | 6/6 / 0/6 / 0/6 | 2.826 / 4.403 / 4.439 | 0.1178 / 0.1217 |
| OFF | walk/sto | 6/6 / 6/6 / 6/6 | 3.412 / 5.974 / 5.750 | 0.0902 / 0.0957 |
| OFF | jitter/det | 1/6 / 0/6 / 0/6 | 2.850 / 4.434 / 4.224 | 0.1158 / 0.1255 |
| OFF | jitter/sto | 6/6 / 6/6 / 6/6 | 3.257 / 5.773 / 5.815 | 0.0934 / 0.0945 |

Under the original [frozen plan](PLAN.md), ON zero-shot and child are HEALTH RETAINED at 23/24 gait. OFF zero-shot and child are PARTIAL at 12/24 versus their own 19/24 source: ordinary walk/det newly sacrifices leg4 in all six episodes, while the existing jitter/det leg4 deficit grows from five to six. ON retains its single jitter/det leg4 episode, index1. All leg/panel counts and affected episodes are in [summary.json](summary.json).

The separate trained ON/OFF mean-slip ratios are **0.8396 / 0.9098 / 0.8709 / 0.8915**, meeting <=1.2 in all four panels (three required). ON improves three of four slip means against its corrected zero-shot parent, but ordinary deterministic slip worsens 2.1% and net-forward speed drops 11.1%. OFF improves two of four slip means. These are small, mixed checkpoint differences, not gait recovery.

Both checkpoints contain 2,097,152 new steps. Normalized reward per tick rises from 0.986866 to 1.125428 ON and 1.033928 to 1.185338 OFF over 524,288 to 2,097,152 steps. Actual non-log-std weights change in all16 tensors, including policy network and action head: L2 deltas 0.476046 ON and 0.525812 OFF. This rules out an unchanged-policy/std-only account without establishing a behavioral training gain. Raw episode reward also rises with growing episode length, so it is not used alone as adaptation evidence.

Frozen checkpoint hashes match the preregistration. Corrected zero-shot and child cfg overrides match exactly; source3x differs only in torque3→1. Published recovery receipts establish evaluator/source, model, motor and package alignment. All reported reset/randomization summaries match within source→zero-shot comparisons after excluding the intentional torque difference, and exactly within zero-shot→child comparisons. Summaries do not expose full reset vectors or every hidden RNG/state; rounded report std is0.135, while exact log_std tensors differ slightly with training. See [weights.json](weights.json), [recovery.json](recovery.json) and [recovery_recipes.json](recovery_recipes.json).

The completed cycle082731's claim that a catastrophic zero-shot ON baseline proved genuine 2M recovery is withdrawn: that old train5 evaluator lacked Cartesian decode. The raw cycle narrative remains here as historical evidence. Current STATUS/SKILLS had deferred adaptation claims; their pending-baseline caveat is now resolved by this corrected read. Existing child verdict statuses are unchanged.

This closes the finite 2M comparison. It grants no automatic extension, new seed, dose grid or hardware qualification. The EASY configuration still uses a fast idealized motor contract, no sensor noise, DR0 and the 0-mesh/91-geom/4.80573kg MJX twin. One training seed and repeated deterministic conditions do not establish a general advantage.

[publication.json](publication.json) records original and published hashes and URL sanitization. All six raw report captures and the cycle narrative are unchanged. [analyze.py](analyze.py) recomputes the metrics locally; [audit_weights.py](audit_weights.py) documents the read-only controller checkpoint comparison. No rollout, render, PPO, verdict mutation, or controller deployment was performed for this closeout.
