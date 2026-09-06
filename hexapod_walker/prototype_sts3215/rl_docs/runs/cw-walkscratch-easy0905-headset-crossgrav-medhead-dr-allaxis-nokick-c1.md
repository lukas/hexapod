# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T09:55:06+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis1x-c1

**wandb_id**: 1eh4y2ou

**hypothesis**: Plain English: allaxis1x-c1 (all ~30 nominal DR axes at once) FAILED with 5/24 real falls, but that arm bakes in the FULL-dose kick (walk_kick_prob=0.3), the one axis already known to fall in isolation (kick1x-c1). This control arm restores every OTHER axis identically but turns kick fully OFF (0.0, not even the safe half-dose) to test the cleanest possible read: do the other ~28 already-individually-clean axes compose without ANY kick confound at all? A companion allaxiskickhalf1x-c1 (kick=0.15) tests the same composite with kick still present at half dose; together the two arms bracket whether kick alone explains the composite failure or whether some OTHER pairwise interaction also contributes.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if the full 4-panel harness reaches 0 falls with aggregate gait_valid majority (>=18/24) and no new chronic single-leg sacrifice -- confirms kick was the SOLE broken ingredient in allaxis1x-c1's composite FAIL. FAIL/INFORMATIVE-NEGATIVE if a fall or gait_valid collapse still appears with kick fully off -- proves a DIFFERENT axis interaction is also broken, independent of kick.

**verdict**: CANARY PASS/INFORMATIVE-POSITIVE (mechanism-health) -- with kick fully OFF (0.0, not even the kickhalf1x-c1-r2 half-dose that itself still fell 7/24), the SAME ~30-axis composite as the FAILED allaxis1x-c1 (5/24 tilt_roll) and the FAILED allaxiskickhalf1x-c1-r2 (7/24 tilt_roll) now reads 0 falls/24, aggregate gait_valid 19/24 (walk/det 6/6, walk/sto 4/6, walk_startjitter/det 6/6, walk_startjitter/sto 3/6) -- majority-clean, no chronic single-leg pattern (scattered non-chronic flags on legs 0/1/5/0/5, no leg repeating enough to call chronic). Contact sheet confirms upright six-leg cycling with genuine forward translation across all 10 sampled frames. Evidence: kick WAS the sole broken ingredient for this composite -- at ANY nonzero dose tried (full 0.3 or half 0.15) the ~30-axis composite falls; at 0.0 it doesn't. This decisively closes QUEUE AIM item (1)'s kick-isolation question (the two prior composite FAILs left this ambiguous between 'kick is broken' and 'some other pairwise interaction is broken'): removing kick alone, with every other axis (mass/friction/stiffness/latency/gains/geom/etc.) still at full dose, is sufficient to restore composite tolerance. Why: the gate's own pre-registered PASS branch. What's next: a composite ACQ (40M) recipe should use this exact no-kick-any-dose composite as its base; kick recovery hardening (if wanted later) should be pursued as its OWN isolated dose-ladder line (kick0225x-c1, kickhalf1x-c1-acq1, both already in flight) rather than folded back into the full composite until it independently clears a higher dose. Found as an idle orphan (finished training+gate, no ledger owner) via a live-pod scan.

