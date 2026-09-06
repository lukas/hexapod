# cw-walkscratch-easy0905-headset-crossgrav-widen2c1-irrfwd-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T07:28:51+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c1-irrfwd-c1-acq1

**wandb_id**: p26jofub

**hypothesis**: Plain English: this composition arm just ACQ PASSed at 40M (21/24 held, falls 1->0, slip down/progress up across all 4 modes, same non-chronic leg signature as canary) but has never had a +40M endurance helping. This campaign's standing rule (widen2/widenirr/s1acq/medhead precedent) is that clean ACQ PASSes without an endurance read are the refill priority: does this 3rd, harder/slower base-champion composition also tolerate a 2nd 40M dose (80M cumulative) without the pre-existing leg[1,4]-style pattern entrenching or a new one emerging?

**gate**: cont40m PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto at 80M cumulative with no NEW chronic single-leg sacrifice and no MORE falls than the 40M ACQ read's 0. cont40m WATCH if gait_valid holds but the non-chronic leg pattern spreads to more episodes/legs without hardening to chronic. cont40m FAIL if walk/det or walk/sto regresses to majority failure or falls appear.

**verdict**: HARDENING PASS (exact hold) — the 8-way-heading widen2c1-irrfwd composition holds gait_valid EXACTLY at 21/24 through +40M more steps (80M cumulative), reproducing the IDENTICAL flagged episodes/legs as its own 40M ACQ parent: walk/det ep3 leg5, walk_startjitter/det ep4 leg1, walk_startjitter/sto ep5 leg1 -- same 3 episode indices, same 3 legs, no new/spreading pattern. 0 falls/terminations across all 24 episodes both reads. slip/m and progress medians both stay in the same range as the 40M parent (walk/det slip 3.33 vs 4.02, walk/sto 4.15 vs 4.86, startjitter modes 4.05-4.15 vs 4.58-4.61 -- if anything slightly improved). Why: this is the cleanest possible cont40m outcome -- zero drift, joining ramp-irrfwd-cont40m (exact hold) and medhead-irrfwd-cont40m (improves) as the 3rd/4th confirmation that cleanliness-margin-at-40M reliably predicts cont40m endurance. Closes this composition line; no further budget needed on it.

