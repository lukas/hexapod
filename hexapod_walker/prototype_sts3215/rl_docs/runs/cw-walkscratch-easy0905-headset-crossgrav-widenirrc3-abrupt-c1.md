# cw-walkscratch-easy0905-headset-crossgrav-widenirrc3-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T03:34:11+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3

**hypothesis**: widen2-crossgrav just split 1PASS/1FAIL across seeds (widen2c1 PASS, widen2c3 FAIL-MECHANISM this cycle), showing crossgrav-transfer robustness CAN be seed-sensitive for a composite recipe. Does the SAME seed-sensitivity risk apply to the sibling widen+irr composite (widenirr), whose 1st seed (widenirrc1-abrupt-c1) already PASSed crossgrav transfer? Testing widenirr's 3rd seed (widenirr-c3, this cycle's clean 23/24 CANARY PASS) under the identical abrupt 0.5g->1.0g jump gives the widenirr-crossgrav axis its own n=2 seed check.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice, matching widenirrc1-abrupt-c1's own clean transfer -- closes widenirr-crossgrav n=2 seeds clean, unlike widen2. FAIL/INFORMATIVE-NEGATIVE if it collapses into the leg[1,4] chronic-sacrifice fingerprint (matching this cycle's widen2c3 FAIL) -- would show composite-crossgrav transfer is seed-sensitive more broadly, not just a widen2 quirk. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**refused_reason**: hexapod-mjx-train-9 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-irrfwd-c1-acq1 — GPU pods host exactly one run; pick a free GPU pod.

