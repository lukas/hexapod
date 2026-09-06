# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T10:12:45+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1

**wandb_id**: jeigs5gn

**hypothesis**: Plain English: does the gradual-ramp gravity-transfer champion (medhead-ramp-c1-acq1, clean ACQ PASS at 40M, 0 falls) hold up under a 2nd 40M endurance helping (80M cumulative)? The ABRUPT gravity-transfer sibling (medhead-abrupt-c1-acq1-cont40m) already confirmed clean at 80M -- this is the matching root-line cont40m for the RAMP transfer mechanism (its own irrfwd/widenfwd children already got cont40m continuations, but the plain ramp root itself has not).

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 80M cumulative with no NEW chronic single-leg pattern and 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall).

**verdict**: HARDENING PASS/HOLDS — the gradual cross-gravity-ramp root holds PERFECT at 80M cumulative. gait_valid 24/24 across all 4 panels (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto all 6/6), 0 falls/terms, sac=[] on every single episode, slip in-band (3.0-4.9/m), progress/forward_dist consistent with the 40M parent. ep_rew_mean rises every quarter (532->992->1082->1142). This is the ramp-family root's FIRST cont40m read (its abrupt sibling already confirmed clean at 80M, and its irrfwd/widenfwd children already passed cont40m) — closes the plain-ramp-root endurance question with the cleanest possible result, no new chronic pattern of any kind at double budget. Champion-grade: safe to treat as a stable full-realism composite source for the contextual DONE-gate rungs once QUEUE AIM item (4) opens.

