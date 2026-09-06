# cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T06:42:06+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1-acq1

**hypothesis**: Plain English: medhead-widenfwd-c1-acq1 (forward-composing the full 8-way heading set onto the campaign's cleanest crossgrav champion) held ACQ PASS at 40M (21/24, mild non-chronic dip). The campaign's own endurance-panel rule (established across s1acq/s3acq/medhead/widenirrc1, 09-06 ~05:3x) says a 2nd +40M helping should HOLD/IMPROVE any source whose first 40M read was already clean, and WORSEN one that was already chronically entrenching. This is the 4th test of that predictor (5th endurance data point overall) on a clean-at-40M source: does it hold per the rule, extending n from 3 to 4 clean confirmations?

**gate**: PASS/HOLDS if aggregate gait_valid stays >=18/24 at/above the 40M read's own 21/24, no NEW chronic single-leg pattern, 0 falls. WORSENS if gait_valid drops materially (e.g. <16/24) or a chronic leg[1,4]-style pattern spreads to a mode that was previously clean — would be the first counter-example to the cleanliness-margin-at-40M rule.

