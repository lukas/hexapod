# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:20:21+00:00

**pod**: hexapod-mjx-train-11

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1

**wandb_id**: mhn5rvg4

**hypothesis**: Plain English: widenirr-c1 (irr-timing-jitter added on top of the healthy widen2-c1 champion, widen-first order) CANARY PASSed cleanly (23/24), but the ONLY other widen-first composite arm tried, widenirr-c2b (jitter on top of the weak widen2-c2b seed), CANARY FAILed with a NEW leg-2 sacrifice pattern -- that verdict explicitly named 'a 3rd seed of the widen2 rung (not a jitter retrofit onto seed 2)' as the right tie-breaker, not yet launched because widen2-c3 (the 3rd, cleanly-PASSing widen2 seed) only just finished its own 40M ACQ PASS this cycle. This arm applies the SAME bank-proved jitter mechanism (goal.walk_cmd_resample_jitter=0.5) on top of widen2-c3's 2M checkpoint (clean-parent widen2 seed 3, matching widen2-c1's own health rather than widen2-c2b's) to test whether the widen-first composite edge is general across healthy widen2 seeds (matching widenirr-c1's clean read) or was itself specific to the widen2-c1 checkpoint.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M) -- do not judge mature course-tracking. PASS/INFORMATIVE if gait_valid stays majority-valid (>=4/6 det) with 0 falls, matching or beating widen2-c3's own clean 2M numbers (20/24 gait_valid, 0 falls) with no NEW leg sacrificed vs widen2-c3's own baseline pattern (legs 0/3/4 only, transient). FAIL if gait_valid collapses or a NEW leg (not 0/3/4) becomes chronically sacrificed, mirroring the widenirr-c2b FAIL trigger.

