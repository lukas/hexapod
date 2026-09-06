# cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T03:09:47+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1

**hypothesis**: Plain English: this cycle found that a DIFFERENT crossgrav champion (irr-timing recipe) which cleanly PASSED its own 2M canary (23/24) and then held reward-rising all the way through 40M nonetheless ACQ-FAILED via the same known base(1g) leg-1/4 structural-entrenchment fingerprint (CURRENT_TRUTHS 09-05 ~22:3x: the two structurally-redundant middle legs are a genuinely cheaper stable 1g gait, not a random exploit) -- a failure mode invisible at 2M canary scale and only visible at full 40M ACQ. medhead-abrupt-c1-acq1 is the campaign's cleanest, most-tested ACQ-PASS champion (23/24, 0 falls) off a materially different recipe (plain heading, no timing-jitter/widen composition). Does the SAME late-entrenchment risk apply to it too given yet more 1g steps, or was irracq1's regression specific to the irr-timing recipe / that seed? A genuinely informative endurance check either way, using free fleet capacity rather than leaving the question open.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no NEW chronic leg (<0.10 duty every episode) beyond this checkpoint's own established 40M read (23/24, sac=[] in all clean modes) -- would show medhead's crossgrav transfer is durable past 40M and irracq1's entrenchment is recipe/seed-specific, not universal. FAIL/ENTRENCHES if walk/det or walk/sto regresses to majority failure or a leg[1,4]-pattern chronic sacrifice newly emerges -- would show ANY crossgrav-transferred champion is on a slow clock toward the same base(1g) structural attractor regardless of source recipe, reframing every prior crossgrav ACQ PASS in this campaign as provisional (budget-limited, not durable) and escalating the STRUCTURAL DIAGNOSTIC role-aware-mechanism design (CURRENT_TRUTHS 09-05 ~22:3x, not yet built) from 'flagged for later' to urgent.

