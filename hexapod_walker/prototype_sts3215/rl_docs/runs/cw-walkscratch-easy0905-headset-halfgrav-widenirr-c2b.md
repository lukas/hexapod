# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c2b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-05T22:54:56+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2b

**wandb_id**: lldm22oo

**hypothesis**: Plain English: 2nd-seed twin of widenirr-c1 (same cycle), using the OTHER matched-budget widen2 seed (widen2-c2b, warm-started from medhead2-acq1, CANARY PASS 16/24 gait_valid, 0 falls, direrr/courserr/slip close to widen2-c1's own numbers). Adds ONLY goal.walk_cmd_resample_jitter=0.5 on top, no new reward keys. Gives the heading-widen-then-add-timing-jitter composition order n=2 independent seeds in one batch (operator 08-22 batching discipline) instead of drawing a recipe-level conclusion off a single arm.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M). PASS/INFORMATIVE if gait_valid stays majority-valid (>=4/6 det) with 0 falls, matching or beating widen2-c2b's own clean numbers (16/24 gait_valid, 0 falls), and wrong_course_frac/direction tracking doesn't blow up under the added timing jitter. FAIL if gait_valid collapses (new leg sacrifice vs widen2-c2b's own baseline) or falls appear. Read together with widenirr-c1 before concluding the composition order is recipe-general vs seed-specific.

**verdict**: CANARY FAIL - MECHANISM: widen-first composition (widen2-c2b heading-widen + irr timing-jitter on top) does NOT hold on seed 2 -- gait_valid TOTAL happens to tie the parent (16/24 both) but the composition shifts WHICH mode fails, tripping the gate's own explicit FAIL trigger. Evidence: walk/det drops from parent's 4/6 (sacrificed legs [1] or [1,3], always leg-1-led) to 3/6 in the child with a NEW leg-sacrifice pattern (failures now show legs [4], [1], [2,4] -- leg 2 and 4 newly implicated, not just leg 1), breaching the gate's own >=4/6 det majority-valid bar on that mode; walk/sto also slips 6/6->5/6 (new leg-1 failure). walk_startjitter/sto improves 4/6->6/6 which is what keeps the raw total flat, but that's a different mode than the one the gate is watching for collapse. 0 falls in all 24 episodes (both), so this is not a safety failure, purely a per-leg-utilization regression. Why: the gate text is explicit -- 'FAIL if gait_valid collapses (new leg sacrifice vs widen2-c2b's own baseline)' -- that is exactly what walk/det shows, so a flat aggregate total does not override it. This reads as fully consistent with (not surprising given) the SAME seed's pure widen2-c2b-acq1 lineage already independently ACQ-FAILing at 40M this cycle with chronic leg-1 entrenchment (14/24 gait_valid, leg-1 duty 0.01-0.21 in all 24 episodes) -- seed 2 of this heading-widen lineage is simply a weaker/leg-1-prone champion, and adding timing jitter doesn't repair it, it just redistributes which episodes fail. Read together with sibling widenirr-c1 (CANARY PASS, clean beat of its own parent): the widen-first composition benefit is SEED-SPECIFIC, not yet recipe-general -- 1/2 seeds pass. What's next: do NOT spend a 40M ACQ budget continuing this checkpoint (same 'do not respec this exact checkpoint further' conclusion the concurrent cycle already reached for the pure widen2-c2b-acq1 lineage); if the widen-first composition needs an n=2 acquisition-scale confirmation, it needs a FRESH 3rd seed of the widen2 rung first (not yet funded), not another jitter retrofit onto a known-bad seed 2.

