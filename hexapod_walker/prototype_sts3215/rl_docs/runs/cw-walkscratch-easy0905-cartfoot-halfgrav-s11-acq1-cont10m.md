# cw-walkscratch-easy0905-cartfoot-halfgrav-s11-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RETENTION FAIL

**created**: 2026-09-08T11:52:07+00:00

**pod**: hexapod-mjx-train-4

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s11-acq1

**wandb_id**: qnxlwcxv

**hypothesis**: Does the halfgrav cart_foot (ON) seed11 arm's 40M ACQ PASS (0 falls/24, speed 0.20-0.24 m/s, gait_valid 11/24, forward-only, systematic leg1 dropout in both det panels) hold, degrade, or recover at 10M more training, extending the cont10m depth check (seed7 held its band, this is a 3rd seed and the one whose ON advantage did NOT clearly beat its own OFF sibling at 40M).

**gate**: RETENTION at 50M cumulative: PASS/HOLDS = 0 new falls/terminations vs this run's own 40M read, gait_valid staying in-or-above its established 11/24 band, slip/m staying within +/-20% of the 40M read (1.61/1.58/1.50/1.69). Report whether the chronic leg1 det-mode dropout (12/12 episodes) persists, clears, or worsens -- this is the seed where ON did not show seed7/10's clear gait_valid advantage over OFF.

**verdict**: Seed11 halfgrav cart_foot (ON) +10M continuation (50M cumulative) fails its own pre-registered RETENTION bar: gait_valid drops 11/24 -> 8/24 (walk/det 0/6->0/6 unchanged, walk/sto 6/6->4/6, walk_startjitter/det 0/6->0/6 unchanged, walk_startjitter/sto 5/6->4/6), below the required in-or-above-11/24 floor, even though the other two clauses clear (0 new falls/terminations in all 24 episodes; slip/m 1.63/1.79/1.74/1.85 vs the 40M read's 1.61/1.58/1.50/1.69, all within +/-20%). The chronic leg1 det-mode dropout (12/12 det episodes, unchanged from 40M) does not clear -- it SPREADS: leg1 is now also sacrificed in 2/6 walk/sto and 1/6 walk_startjitter/sto episodes that were clean at 40M, the exact 'spreads into a previously-clean mode' shape this file's other halfgrav cont10m entries treat as a real degradation, not noise. ep_rew_mean keeps rising every quarter (257.6/696.3/1156.2/1419.0, final 1425.76) with no plateau -- per the 08-21 ruling this is reward/gait misalignment to note, not grounds to kill the seed11 lineage (its 40M ACQ-PASS checkpoint stands as champion); do not warm-start or evaluate this cont10m checkpoint as a gait-health improvement over its own parent. Seed7's matched cont10m HOLDS its band exactly and seed10's OFF/ON cont10m pair is under a concurrent cycle -- do not pool seed11's degrade with seed7's hold; report per-seed as this file has repeatedly required. Next: no further budget on this exact seed11 cont10m lineage; the open cohort question (does seed10's cont10m pair confirm hold-vs-degrade splits 1-of-3 or 2-of-3) belongs to whichever cycle reads seed10's matched pair.

