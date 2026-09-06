# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T00:44:34+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1

**wandb_id**: y8jypeph

**hypothesis**: Plain English: the ramped-1g crossgrav discovery canary (CANARY PASS, gait_valid 21/24, walk/det+sto+startjitter/sto 18/18 clean, 0 falls) already showed six-leg walking survives a gradual gravity ramp to full gravity from the leg-healthy halfgrav-medhead-acq1 champion, marginally cleaner than the abrupt sibling. This is the acquisition-scale (40M) confirmation, run at flat 1.0g throughout (the sched ramp already completed by 1M steps of the 2M canary and the per-process sched tick resets to 0 on resume, so the schedule is disabled here and gravity is pinned at 1.0 directly instead of re-ramping): does the six-leg gait hold up (or fully resolve the mild start-jitter leg-4 softening) with a full training budget, giving cross-gravity transfer an n=2 (abrupt+ramp) acquisition-scale confirmation as a real repair path for the base(1g) family?

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with sac=[] (no chronic <0.10-duty single-leg sacrifice) at 40M, matching or improving the 2M canary's clean 18/18 read, 0 falls, and slip/m at/near the 2.9 teacher band. ACQ FAIL if walk/det or walk/sto regresses to majority failure or the leg[1,4] chronic-park fingerprint emerges under longer 1g exposure. ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling. Read together with the abrupt sibling's own acq1 read: 2/2 ACQ PASS would fully validate cross-gravity-transfer as a base(1g) recipe regardless of transition speed.

