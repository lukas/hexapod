# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-durfix-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-01T21:20:30+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**hypothesis**: Seed-pass-rate twin of durfix-canary (this cycle, same base checkpoint/steps/cfg, --seed 1 only) so the duration-mismatch-fix verdict rests on n=2 seeds, not one -- otherwise identical hypothesis/gate to durfix-canary.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as durfix-canary, read jointly: n=2 seeds both improving over their durctrl controls = duration-mismatch confirmed generally, not a seed fluke; a seed split = re-open with more seeds before trusting either direction.

