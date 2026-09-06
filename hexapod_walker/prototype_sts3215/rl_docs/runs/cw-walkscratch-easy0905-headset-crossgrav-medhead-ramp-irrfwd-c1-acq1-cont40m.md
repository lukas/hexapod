# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-irrfwd-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T06:57:41+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-irrfwd-c1-acq1

**wandb_id**: yp7q6t8m

**hypothesis**: Plain English: same endurance question as the medhead/widen2c1/widenirrc1 cont40m siblings, run on the ramp-transfer + irr-forward-composed champion (medhead-ramp-irrfwd-c1-acq1: 22/24 gait_valid, EXACT match to its own 2M canary's structure, 0 falls) -- first endurance read on a RAMP-transfer (not abrupt) source, and separately tests whether ramp-transfer itself carries elevated entrenchment risk under a 2nd 40M helping (open question raised by sibling medhead-ramp-widenfwd-c1-acq1 ACQ FAIL).

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with slip_per_m staying tightly banded and no NEW chronic leg beyond this checkpoint's own established 40M read (22/24, non-chronic leg-5 flag only). FAIL/ENTRENCHES if a leg[1,4]-or-other chronic single-leg sacrifice newly spreads across multiple modes.

**verdict**: HARDENING/endurance continuation HOLDS at +40M (80M total). Aggregate gait_valid 22/24 -- an EXACT reproduction of this checkpoint's own established 40M read: walk/det 4/6 (same 2 flagged episodes, ep1+ep5, SAME leg-5, duty 0.06/0.08 vs the parent's 0.04/0.05 -- unchanged borderline pattern, not a new or spreading pathology), walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6, 0 falls/terminations across all 24 episodes. slip/m tightly banded (3.25-4.96), matching the parent. Frame strips (walk_det_1, the flagged episode) confirm clean six-leg tripod cycling with body translation, no drag/skate/collapse -- the low-duty leg5 in these 2 episodes is a mild asymmetry, not a parked/sacrificed leg (duty>0, swing_count 54-60 over 20s, still cycling). Why: the extra 40M of ramp-transfer training changed nothing structurally -- same non-chronic single-leg-5 blip, confined to walk/det only, never spreading to sto or startjitter modes. Next: this closes the endurance question for the ramp-transfer-sourced composition family (joining medhead-abrupt/widen2c1/widenirrc3 cont40m holds); no further budget needed on this specific line.

