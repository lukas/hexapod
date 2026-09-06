# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-encnoise1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T06:48:53+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-encnoise1x-c1

**hypothesis**: Sensing-side twin of this cycle's friction1x-c1-acq1 question: does the campaign's PERFECT single-axis DR-restore canary (medhead-dr-encnoise1x-c1: nominal ~1 LSB encoder read noise restored, 24/24 gait_valid, sac=[] every episode, 0 falls at 2M) hold up at acquisition-scale (40M) on top of the 80M champion? Physics-axis (friction) and sensing-axis (encoder noise) are the two broad DR categories this campaign's single-axis sweep covers -- testing one of each for whether canary-clean single axes entrench at ACQ scale the way composition axes have (roughly half of healthy-source crossgrav/widen/irr compositions did).

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice vs the 2M canary and 0 falls -- shows encoder-noise realism is durable, not just canary-clean. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows sensing-axis DR canaries are also at ACQ-entrenchment risk, not just physics/composition axes.

