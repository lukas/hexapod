# cw-standwalk-stage2-dualbc5-turncap-stdwalk-mild-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T07:40:26+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: 0tcfig0w

**hypothesis**: Plain English: the last 5 turn-authority mechanism classes (anchor dose 3.0/1.0/0.3, anchor turn-tick-targeted skip, BC-anchor isolate-update, PPO ent-coef 4x) all left wz_med under the 0.03 FAIL floor -- the STATUS dig-in found the entropy-boost arm was a weaker test than it looked (train/std never left ~0.223 the whole 2M run despite entropy_loss rising 20x), so PPO's own gradient may simply never widen the walk core's action noise enough on its own to discover the turning behavior even with more exploration REWARD pressure. This tests a guaranteed-to-move DIRECT lever instead: using the new multi-core log-std-anneal support (this cycle's own code, plus an argv-parsing fix after the first launch attempt of this exact arm crashed pre-boot on a comma-list-vs-argparse-negative-number gotcha -- see _fixup_log_std_final_argv), forcibly raise the walk core's log_std from its current ~-1.5 (std 0.22) to -0.8 (std ~0.45) over the first 10pct of steps and PIN it there for the rest of the run (PPO cannot fight it back down), while leaving the already-proven stance-core cooling (-4.0 over 50pct) untouched. Prediction-if-true: probe_turn_authority wz_med clears 0.03 both signs without gait collapse. Prediction-if-false: identical frozen-body read despite genuinely wider action noise (env/train/std should confirm >=0.4 for real, unlike the entboost arm) -- exploration MAGNITUDE is refuted too, next suspect is a structural credit-assignment defect in the shared value function / GAE over the minority turn-tick states, requiring the raw per-tick reward-vs-value trace tool named in the prior STATUS update.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. probe_turn_authority (own cfg, wz_cmd=+-0.25, walk-mode-filtered): PASS if wz_med clears 0.03 in the commanded direction both signs; joint with the -hi sibling. Also check env/train/std actually reached >=0.35 by 200k steps (confirms the lever moved, distinguishing 'exploration didn't help' from 'exploration didn't happen' the way the entboost arm's flat std did) and walk_det frame-strip for gait collapse (6-leg cycling preserved is required for any PASS read, a collapsed gait 'turning' via falling over does not count).

