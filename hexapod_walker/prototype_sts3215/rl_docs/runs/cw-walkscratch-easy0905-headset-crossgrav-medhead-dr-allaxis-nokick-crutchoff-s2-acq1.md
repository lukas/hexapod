# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-07T05:33:14+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2

**hypothesis**: Plain English: crutchoff-s2's 2M canary CANARY PASSED (0 falls/24 eps, gait_valid 20/24), matching its s1 twin, on a seed that fell repeatedly with the 3x torque crutch ON. Second seed of the same acquisition-scale durability question: does crutch-off push-recovery robustness survive 40M of further training, not just a 2M canary?

**gate**: ACQUISITION: held-out gate (DR-0, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid stays >=18/24 (flat-or-better vs the 2M canary's 20/24) -- entrenchment/regression if falls reappear or gait_valid drops materially.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

