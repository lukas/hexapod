# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6-w45

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T15:12:40+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6

**wandb_id**: a70gf0rb

**hypothesis**: Plain English: companion dose to the w15 arm (this cycle's other arm) on the same weight-reduction question. The recalibrated target=6.0 load-slip-ratio charge still missed the efficacy bar at weight=150 with a collapsing reward curve. This arm tries an intermediate weight (150->45, 1/3 instead of 1/10) so the two arms bracket the weight axis: if w15 works but w45 doesn't, the effective weight is narrowly below 45; if both work, weight just needs to be materially lower than 150 with room to spare; if neither works, weight was never the limiting factor and the mechanism needs a structural redesign, not dose tuning.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY: PASS if reward stays healthy (no order-of-magnitude late-training collapse vs the matched guardfix1 baseline's own quarter-over-quarter trend) AND >=3/4 of the 4 held-out groups (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto) jointly improve slip AND progress vs the matched 0.30-duty-dose guardfix1-s0 baseline with 0 new falls -- licenses a cont10m depth read and a matched n=3 seed batch at this weight. FAIL (still <3/4 groups, or reward still collapses) closes this dose point on the weight-reduction branch.

**verdict**: CANARY FAIL - MECHANISM (closes the weight-reduction branch on the other side, matching its w15 sibling): cutting walk_leg_loadslip_ratio_charge weight 150->45 (1/3) does NOT fix either half of the gate's own bar. (1) Reward health: quarters [29.8, 55.1, -1106.1, -4251.7] still collapse ~3 orders of magnitude in the back half -- same qualitative healthy-then-catastrophic-collapse shape as the weight=150 parent ([34.0,56.1,-1058.2,-6806.0]) and the weight=15 sibling ([34.6,50.5,-986.7,-4068.7]); w45's collapse magnitude sits between the two, not resolved. (2) Efficacy: vs the matched weight=150 parent (walk/det slip 9.55/fwd 0.61m, walk/sto slip 7.37/fwd 1.00m, walk_startjitter/det slip 9.17/fwd 0.66m, walk_startjitter/sto slip 12.37/fwd 0.59m gv4/6), w45 reads walk/det slip 9.73/fwd 0.58m (flat/slightly worse both), walk/sto slip 7.49/fwd 1.05m (flat/slightly better fwd), walk_startjitter/det slip 9.63/fwd 0.67m (flat), walk_startjitter/sto slip 12.41/fwd 0.44m gv4/6 (flat slip, worse fwd) -- 0/4 groups jointly and clearly improve both slip AND progress; every difference is noise-level, not the >=3/4-groups bar. 0 new falls (matches parent). Contact sheet confirms genuine forward translation across all 10 frames (mature/entrenched-exploiter lineage), so this reads real walking behavior, not a stationary artifact. Net: w15 and w45 bracket the weight axis and BOTH fail identically -- weight scale (10x down to 1/3x) changes only the reward-collapse magnitude, never the exported checkpoint's actual slip/progress behavior. CLOSES the weight-reduction branch on walk_leg_loadslip_ratio_charge entirely (both directions tested, both fail). Next licensed move: a genuinely new per-leg mechanism design, not further dose tuning of this charge.

