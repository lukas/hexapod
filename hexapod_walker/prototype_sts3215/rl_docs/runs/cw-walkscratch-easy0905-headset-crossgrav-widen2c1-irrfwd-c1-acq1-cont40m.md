# cw-walkscratch-easy0905-headset-crossgrav-widen2c1-irrfwd-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T07:28:51+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c1-irrfwd-c1-acq1

**wandb_id**: p26jofub

**hypothesis**: Plain English: this composition arm just ACQ PASSed at 40M (21/24 held, falls 1->0, slip down/progress up across all 4 modes, same non-chronic leg signature as canary) but has never had a +40M endurance helping. This campaign's standing rule (widen2/widenirr/s1acq/medhead precedent) is that clean ACQ PASSes without an endurance read are the refill priority: does this 3rd, harder/slower base-champion composition also tolerate a 2nd 40M dose (80M cumulative) without the pre-existing leg[1,4]-style pattern entrenching or a new one emerging?

**gate**: cont40m PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto at 80M cumulative with no NEW chronic single-leg sacrifice and no MORE falls than the 40M ACQ read's 0. cont40m WATCH if gait_valid holds but the non-chronic leg pattern spreads to more episodes/legs without hardening to chronic. cont40m FAIL if walk/det or walk/sto regresses to majority failure or falls appear.

