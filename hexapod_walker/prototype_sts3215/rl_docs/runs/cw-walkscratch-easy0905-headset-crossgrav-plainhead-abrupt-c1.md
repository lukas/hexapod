# cw-walkscratch-easy0905-headset-crossgrav-plainhead-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: KILLED_LAUNCH_BUG

**created**: 2026-09-06T02:14:44+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-acq1

**hypothesis**: Plain English: headset-halfgrav-acq1 (the plain 3-way 0/+-45deg heading champion, the base lineage every medhead/widen2/irr/composite champion descends from) is the CLEANEST champion in the whole halfgrav roster (gait_valid 24/24 -- 6/6 in all 4 modes, no sacrificed leg ever) but has never itself been tested for cross-gravity-transfer -- only its descendants (medhead, widen2c1, irr, irrwiden, widenirr) were. Since the composite irrwiden-c1-acq1 (this cycle's own CANARY FAIL) just showed transfer degradation CAN happen even from a clean 0.5g parent, does the campaign's cleanest, simplest reference champion transfer cleanly to abrupt 1g, or does it also degrade -- giving the sweep its missing baseline/simplest-case data point?

**gate**: DISCOVERY (2M), abrupt 1g jump from the cleanest (24/24) halfgrav champion. PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic single-leg sacrifice -- extends cross-gravity-transfer confirmation to the simplest possible recipe, the natural baseline the rest of the sweep has been implicitly assuming. FAIL/INFORMATIVE-NEGATIVE if walk/det collapses to minority -- would mean even the cleanest, simplest champion isn't immune, undermining the working theory that transfer difficulty tracks recipe complexity (composite vs simple) rather than being uniformly fragile.

**verdict**: KILLED before any training signal (0 GPU-seconds lost beyond ~2 min wall clock): my own respec --from used headset-crossgrav-medhead-abrupt-c1 as the template, and --parent only sets ledger lineage bookkeeping, not the actual --init-from checkpoint path -- the cloned extra_args silently kept the TEMPLATE run's own --init-from (ppo_goal_..._headset_halfgrav_medhead_acq1.zip) instead of the intended untested headset_halfgrav_acq1.zip champion. Caught via kubectl exec ps aux inspection of the actual launched command line before assuming success. Relaunched correctly this cycle as cw-walkscratch-easy0905-headset-crossgrav-plainhead-abrupt-c1b with an explicit --arg=--init-from=... override. Gotcha for next time: respec --from + --parent does NOT repoint --init-from; use --arg="--init-from=<path>" explicitly whenever the intended source checkpoint differs from the templates own.

