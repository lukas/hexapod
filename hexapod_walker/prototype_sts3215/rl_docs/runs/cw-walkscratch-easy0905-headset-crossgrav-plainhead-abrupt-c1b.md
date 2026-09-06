# cw-walkscratch-easy0905-headset-crossgrav-plainhead-abrupt-c1b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:18:04+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-acq1

**wandb_id**: 59h70mm0

**hypothesis**: Plain English: headset-halfgrav-acq1 (the plain 3-way 0/+-45deg heading champion, the base lineage every medhead/widen2/irr/composite champion descends from) is the CLEANEST champion in the whole halfgrav roster (gait_valid 24/24 -- 6/6 in all 4 modes, no sacrificed leg ever) but has never itself been tested for cross-gravity-transfer -- only its descendants (medhead, widen2c1, irr, irrwiden, widenirr) were. Since the composite irrwiden-c1-acq1 (this cycle's own CANARY FAIL) just showed transfer degradation CAN happen even from a clean 0.5g parent, does the campaign's cleanest, simplest reference champion transfer cleanly to abrupt 1g, or does it also degrade -- giving the sweep its missing baseline/simplest-case data point?

**gate**: DISCOVERY (2M), abrupt 1g jump from the cleanest (24/24) halfgrav champion. PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic single-leg sacrifice -- extends cross-gravity-transfer confirmation to the simplest possible recipe, the natural baseline the rest of the sweep has been implicitly assuming. FAIL/INFORMATIVE-NEGATIVE if walk/det collapses to minority -- would mean even the cleanest, simplest champion isn't immune, undermining the working theory that transfer difficulty tracks recipe complexity (composite vs simple) rather than being uniformly fragile.

