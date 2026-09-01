# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-durctrl-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS (own scope) - joint pending flatonly-read

**created**: 2026-09-01T21:18:21+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**wandb_id**: ovccwihp

**hypothesis**: Seed-pass-rate twin of durctrl-canary (this cycle, same base checkpoint/steps, no cfg change, --seed 1 only) -- matched control for durfix-canary-s1.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Comparison-only, read jointly with durctrl-canary and both durfix arms.

**verdict**: CANARY PASS (own scope) - joint pending flatonly-read. Training-only triage: seed1 twin of durctrl-canary (matched no-cfg-change CONTROL, 2M steps, same warm-start as gradclip0p15-canary-s1 -- only more training, no widened mode_seq_segment/episode-seconds). No independent PASS/FAIL bar at this mechanism-health canary scope; the decisive read is the flat-only eval_done_gate_session (n=8, video, goal.rise_flat_frac=1.0 override) read jointly against durfix-canary-s1's at the same step count (that twin is still training, train-4, not yet at 2M) per STATUS Next item 1. Reward curve is healthy (no blowup, no flatline): dipped hard mid-run (~900k-1.5M steps, ep_rew_mean 108->-387) then partially recovered to only 4.15 by 2M (weaker recovery than the durctrl-canary seed0 twin's 140.6, but rolling ep_rew_mean is noisy and this is not the gate metric) -- self-correcting, not stuck. Launched the flat-only DONE-gate session on this checkpoint (train-2) alongside durctrl-canary (train-1) and durfix-canary (train-3) so all three land together for the joint verdict; durfix-canary-s1 will need its own flat-only read once it finishes training.

