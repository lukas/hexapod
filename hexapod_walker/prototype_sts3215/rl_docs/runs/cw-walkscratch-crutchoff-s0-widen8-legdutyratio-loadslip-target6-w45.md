# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6-w45

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-08T15:12:40+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6

**wandb_id**: a70gf0rb

**hypothesis**: Plain English: companion dose to the w15 arm (this cycle's other arm) on the same weight-reduction question. The recalibrated target=6.0 load-slip-ratio charge still missed the efficacy bar at weight=150 with a collapsing reward curve. This arm tries an intermediate weight (150->45, 1/3 instead of 1/10) so the two arms bracket the weight axis: if w15 works but w45 doesn't, the effective weight is narrowly below 45; if both work, weight just needs to be materially lower than 150 with room to spare; if neither works, weight was never the limiting factor and the mechanism needs a structural redesign, not dose tuning.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY: PASS if reward stays healthy (no order-of-magnitude late-training collapse vs the matched guardfix1 baseline's own quarter-over-quarter trend) AND >=3/4 of the 4 held-out groups (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto) jointly improve slip AND progress vs the matched 0.30-duty-dose guardfix1-s0 baseline with 0 new falls -- licenses a cont10m depth read and a matched n=3 seed batch at this weight. FAIL (still <3/4 groups, or reward still collapses) closes this dose point on the weight-reduction branch.

