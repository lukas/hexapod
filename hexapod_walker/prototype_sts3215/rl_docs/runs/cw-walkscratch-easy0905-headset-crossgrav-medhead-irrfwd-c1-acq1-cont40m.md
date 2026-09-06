# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T06:56:20+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1-acq1

**hypothesis**: Plain English: medhead-irrfwd-c1-acq1 (irregular direction-change timing composed onto the campaign's cleanest crossgrav champion) held ACQ PASS at 40M (21/24, flat vs its own 22/24 canary). Same endurance-panel predictor test as the widenfwd-cont40m sibling launched this cycle: does a 2nd +40M helping hold/improve a source whose first 40M read was already clean (per the established rule), giving a 2nd concurrent confirmation from an independent composition (irr-first, not widen-first)?

**gate**: PASS/HOLDS if aggregate gait_valid stays >=18/24 at/above the 40M read's own 21/24, no NEW chronic single-leg pattern, 0 falls. WORSENS if gait_valid drops materially (e.g. <16/24) or a chronic leg[1,4]-style pattern spreads to a previously-clean mode — a counter-example to the cleanliness-margin-at-40M rule.

