# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-durctrl-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS (own scope) - joint flatonly-read COMPLETE

**created**: 2026-09-01T21:18:21+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**wandb_id**: ovccwihp

**hypothesis**: Seed-pass-rate twin of durctrl-canary (this cycle, same base checkpoint/steps, no cfg change, --seed 1 only) -- matched control for durfix-canary-s1.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Comparison-only, read jointly with durctrl-canary and both durfix arms.

**verdict**: CANARY PASS (own scope) - joint flatonly-read COMPLETE. Flat-only eval_done_gate_session (n=32, dr0+owndr) landed: gate.pass=false (expected, mechanism-health canary), 5/32 terminated, ALL 5 walk-segment over_current, clustered at an almost identical 13.16-13.24s (3.16-3.24s post rise->walk switch) across every failing episode -- a fixed post-switch delay, not scattered bad luck, consistent with the switch-shock mechanism this cycle's instrumentation (debug_seq_switch_obs_jump.py) confirmed on the sibling durctrl-canary (action output saturates on the exact switch tick, driving current toward the 2.64A cap over the following ~0.2-3.2s). progress_ratio_med=0.298, gait_valid=1.0, direction_err_med=45.4deg -- best directional accuracy of the quartet's 4 arms despite the term rate. This completes the duration-mismatch quartet's flat-only reads (durctrl-canary, durctrl-canary-s1, durfix-canary, durfix-canary-s1 all landed); full causal writeup in rl_docs/tracks/standwalk/STATUS.md.

