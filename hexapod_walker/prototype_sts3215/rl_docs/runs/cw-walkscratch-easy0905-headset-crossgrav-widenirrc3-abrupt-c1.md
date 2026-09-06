# cw-walkscratch-easy0905-headset-crossgrav-widenirrc3-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T03:35:33+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3

**wandb_id**: ou65x19c

**hypothesis**: widen2-crossgrav just split 1PASS/1FAIL across seeds (widen2c1 PASS, widen2c3 FAIL-MECHANISM this cycle), showing crossgrav-transfer robustness CAN be seed-sensitive for a composite recipe. Does the SAME seed-sensitivity risk apply to the sibling widen+irr composite (widenirr), whose 1st seed (widenirrc1-abrupt-c1) already PASSed crossgrav transfer? Testing widenirr's 3rd seed (widenirr-c3, this cycle's clean 23/24 CANARY PASS) under the identical abrupt 0.5g->1.0g jump gives the widenirr-crossgrav axis its own n=2 seed check.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice, matching widenirrc1-abrupt-c1's own clean transfer -- closes widenirr-crossgrav n=2 seeds clean, unlike widen2. FAIL/INFORMATIVE-NEGATIVE if it collapses into the leg[1,4] chronic-sacrifice fingerprint (matching this cycle's widen2c3 FAIL) -- would show composite-crossgrav transfer is seed-sensitive more broadly, not just a widen2 quirk. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: CANARY PASS/INFORMATIVE-POSITIVE, matching this gate's own pre-registered PASS branch: closes the widenirr-crossgrav axis at n=2 seeds clean (unlike widen2, which split 1 PASS/1 FAIL). Warm-started the widenirr-c3 halfgrav champion (own 23/24 CANARY PASS) into an abrupt 0.5g->1.0g jump. Result: harness gait_valid majority-clean in all 4 modes -- walk/det 5/6 (only 1 flagged episode, sac=[2,5], not the closed leg[1,4] fingerprint), walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6 -- 0 falls/terminations across all 24 episodes. Frame strip (walk_det_3, the one flagged episode) still shows genuine body translation across the floor tiles with legs cycling, not a frozen/dragging pose. slip_per_m is elevated/noisy (5-20, some reversal-heading sto episodes spiking to 130-207) but that's the already-documented low-net-progress-denominator artifact on this widen/reversal family at 2M scale, not a new pathology, and this canary's own gate text explicitly does not require a mature 40M-grade gait/slip read at 2M. Why: this is the SECOND widenirr seed to independently clear the abrupt full-gravity jump (n=2), reinforcing that cross-gravity-transfer generalizes across simple + widen+irr composite recipes, in contrast to widen2's seed-split. Next: matches the medhead/widen2c1/irracq1 precedent -- eligible for a matched 40M ACQ continuation if a GPU slot opens and no higher-priority refill exists; not launched this cycle (see refill notes).

