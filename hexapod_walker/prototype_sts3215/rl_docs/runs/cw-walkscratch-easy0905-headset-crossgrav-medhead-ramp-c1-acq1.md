# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ_PASS

**created**: 2026-09-06T00:45:50+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1

**wandb_id**: y8jypeph

**hypothesis**: Plain English: the ramped-1g crossgrav discovery canary (CANARY PASS, gait_valid 21/24, walk/det+sto+startjitter/sto 18/18 clean, 0 falls) already showed six-leg walking survives a gradual gravity ramp to full gravity from the leg-healthy halfgrav-medhead-acq1 champion, marginally cleaner than the abrupt sibling. This is the acquisition-scale (40M) confirmation, run at flat 1.0g throughout (the sched ramp already completed by 1M steps of the 2M canary and the per-process sched tick resets to 0 on resume, so the schedule is disabled here and gravity is pinned at 1.0 directly instead of re-ramping): does the six-leg gait hold up (or fully resolve the mild start-jitter leg-4 softening) with a full training budget, giving cross-gravity transfer an n=2 (abrupt+ramp) acquisition-scale confirmation as a real repair path for the base(1g) family?

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with sac=[] (no chronic <0.10-duty single-leg sacrifice) at 40M, matching or improving the 2M canary's clean 18/18 read, 0 falls, and slip/m at/near the 2.9 teacher band. ACQ FAIL if walk/det or walk/sto regresses to majority failure or the leg[1,4] chronic-park fingerprint emerges under longer 1g exposure. ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling. Read together with the abrupt sibling's own acq1 read: 2/2 ACQ PASS would fully validate cross-gravity-transfer as a base(1g) recipe regardless of transition speed.

**verdict**: ACQ PASS. 40M own-checkpoint continuation of the gradual-ramp 1g cross-gravity-transfer canary, gravity pinned flat at 1.0 (sched already completed by 1M of the 2M canary, resets on resume). Harness gait_valid 21/24: walk/det 6/6 clean (sac=[]), walk/sto 6/6 clean, walk_startjitter/sto 6/6 clean, walk_startjitter/det 3/6 with the SAME mild leg-4-only softening (sac=[4], never chronic <0.10 duty, other legs healthy) already seen at this run's own 2M canary -- exact structural match (18/18 clean modes + the one known-soft mode), not a regression at 4x the budget. 0 falls/terminations in all 24 episodes. fwd_dist_m 1.4-2.8m/20s (0.07-0.14 m/s), slip_per_m tightly banded 3.0-4.9, at/near the 2.9 teacher band and matching the abrupt sibling's own 3.2-4.6. Video (walk_det_0) shows genuine six-leg cycling with clear lift/place and body translation, not dragging. Together with the concurrent cycle's headset-crossgrav-medhead-abrupt-c1-acq1 ACQ PASS (23/24, logged 01:59), this is 2/2 ACQ PASS -- fully validates cross-gravity-transfer (1g reachable via curriculum transfer from an already leg-healthy 0.5g gait) as a real base(1g) recipe regardless of transition speed (abrupt vs gradual read equivalently well). Next: this closes the medhead-recipe abrupt-vs-ramp question; remaining budget goes to confirming generality across OTHER halfgrav champions/recipes (widen2c1, irr-timing, s1acq/s3acq already in flight) and to the composite widen+irr recipe, which is reading weaker (see irrwidenc1-abrupt-c1 sibling verdict).

**refused_reason**: hexapod-mjx-train-0 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1 — GPU pods host exactly one run; pick a free GPU pod.

