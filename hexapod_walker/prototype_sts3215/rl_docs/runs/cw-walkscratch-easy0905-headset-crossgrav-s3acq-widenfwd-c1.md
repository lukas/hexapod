# cw-walkscratch-easy0905-headset-crossgrav-s3acq-widenfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T04:24:14+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1-acq1

**wandb_id**: zvxecftd

**hypothesis**: Plain English: s3acq-abrupt-c1-acq1 is the 2nd-cleanest crossgrav champion in the sweep (gait_valid 21/24 at 40M, only a mild non-chronic leg-1 jitter-sensitivity). Mirroring the s1acq pair launched this cycle, can the SAME widen2 full-8-way-heading-set composition be added FORWARD, directly at 1g, on this 2nd champion too -- giving n=2 champions x n=2 axes for the forward-compose-on-a-clean-crossgrav-source question?

**gate**: CANARY PASS - INFORMATIVE-POSITIVE if gait_valid stays majority-or-better (>=18/24) with no chronic single-leg sacrifice, matching medhead-widenfwd-c1 (23/24) and the s1acq sibling. FAIL/INFORMATIVE-NEGATIVE if it collapses toward chronic single-leg sacrifice.

**verdict**: CANARY FAIL - INFORMATIVE-NEGATIVE: forward-composing the full 8-way heading-widen set onto the already-known-compromised s3acq-abrupt-c1-acq1 source (itself ACQ FAIL at 40M with chronic leg-1 startjitter entrenchment, WORSENING further on its own -cont40m) reproduces the SAME chronic leg-1 pattern immediately at just 2M. Aggregate gait_valid 14/24 (walk/det 4/6, walk/sto 6/6, walk_startjitter/det 1/6, walk_startjitter/sto 3/6) -- clearly below the run's own >=18/24 bar. ALL 10 invalid episodes across all 4 modes name leg-1 as the sole sacrificed leg, exactly matching/exceeding the source's own closed fingerprint (contrast medhead-widenfwd-c1's 21/24 with a DIFFERENT non-repeating leg per episode). 0 falls/terminations. Several episodes show extreme skating (slip/m 24-208) on hard heading cells with near-zero net progress -- worse than the already-documented reversal-heading artifact alone. Reward NET-DECLINING every quarter (-80.7/-214.0/-254.3/-606.3, not the 08-21 rising-reward/continue case) -- a genuine, unambiguous FAIL by both reward and eval, not misalignment. Video (walk_startjitter_det_3) confirms body translation with one leg visibly parked. Closes the question for this source: forward-composing ANY axis onto an already-compromised champion re-surfaces its structural weakness immediately, it does not heal or hide it. No further budget/continuation warranted on this arm; the s3acq lineage's own leg-1 entrenchment is now confirmed at 3 scales (40M, 80M-cont40m, and this 2M forward-compose) -- source health, not recipe or budget, is the predictor. Next: matches the already-flagged role-aware per-leg-utilization repair mechanism (CURRENT_TRUTHS), not a same-recipe relaunch.

