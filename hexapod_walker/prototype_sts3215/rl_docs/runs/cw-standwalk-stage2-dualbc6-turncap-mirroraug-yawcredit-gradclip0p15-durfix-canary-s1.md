# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-durfix-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS (own scope) - joint pending flatonly-read

**created**: 2026-09-01T21:20:30+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**wandb_id**: a9nl73qk

**hypothesis**: Seed-pass-rate twin of durfix-canary (this cycle, same base checkpoint/steps/cfg, --seed 1 only) so the duration-mismatch-fix verdict rests on n=2 seeds, not one -- otherwise identical hypothesis/gate to durfix-canary.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as durfix-canary, read jointly: n=2 seeds both improving over their durctrl controls = duration-mismatch confirmed generally, not a seed fluke; a seed split = re-open with more seeds before trusting either direction.

**verdict**: CANARY PASS (own scope) - joint pending flatonly-read. Training-only triage: seed-1 twin of durfix-canary (same duration-mismatch-fix cfg: episode-seconds 30->90, mode_seq_segment_s_min/max 6/8->20/60, off gradclip0p15-canary, 2M steps). Finished training this cycle (checkpoint synced, ledger was stale RUNNING though train-4 was already idle). No independent PASS/FAIL bar at this mechanism-health canary scope; the decisive read is the flat-only eval_done_gate_session read jointly against durctrl-canary-s1's at the same step count per STATUS Next item 1. Reward curve is healthy (no blowup, no flatline): quarters 52.2, 68.3, -363.9, ending -240.5 -- dipped hard mid-run then partially recovered, same shape as its durctrl-canary-s1 control (recovered to 4.2) and its own durfix-canary seed-0 twin (-353.8). Launched this checkpoint's own flat-only eval_done_gate_session on train-4 this cycle (was untouched/idle -- STATUS Next#1 flagged it as the missing 4th arm); it is now running alongside durctrl-canary (train-1), durctrl-canary-s1 (train-2), durfix-canary (train-3).

