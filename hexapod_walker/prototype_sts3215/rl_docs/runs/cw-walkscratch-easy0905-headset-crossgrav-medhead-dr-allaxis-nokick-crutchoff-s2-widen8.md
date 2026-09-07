# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widen8

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-07T07:19:19+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-acq1

**wandb_id**: taixfj43

**hypothesis**: Plain English: two-seed confirmation twin of crutchoff-s1-widen8 -- can the crutch-off full-realism composite absorb the full 8-way heading set (adds +-135deg and 180deg) as a single-axis extension on a second independent seed, or is heading-breadth-under-composite-DR seed-fragile the way the crutch-ON composite was? Same single change (goal.walk_heading_set 5->8), init from THIS seed's own ACQ-passed 40M checkpoint. Prediction-if-true: 0 falls, gait_valid majority at 2M, matching s1-widen8. Prediction-if-false: tilt falls or chronic single-leg sacrifice on rear headings on this seed only (seed fragility) or both seeds (mechanism limit). Strongest alternative: low dir-valid on the new headings without falls = budget, reads as continue per the 08-21 ruling.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (mechanism health, 2M): held-out gate on own cfg (8-way heading set, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid >=18/24. FAIL if any fall or chronic (<0.10-duty every episode) single-leg sacrifice. Low dir-valid confined to the 4 new headings without falls = inconclusive-continue (budget, not mechanism).

**verdict**: CANARY PASS. Same single-axis 8-way heading widen as the s1 twin, init from this seed's own ACQ-passed 40M checkpoint. 0 falls/terminations across all 24 held-out episodes; gait_valid 22/24 (walk/det 6/6, walk/sto 6/6, startjitter/det 6/6, startjitter/sto 4/6) -- numbers essentially identical to the s1 twin (21/24). Non-chronic single-leg flags confined to the hardest startjitter/sto cell only. 2/2 crutch-off seeds now clean on the 8-way widen at canary depth (3rd seed s0-widen8 still computing). Next: ACQ continuation at 40M to test scale durability, same as s1.

