# cw-walkscratch-easy0905-medhead-widenfwd-c2-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: HARDENING PASS

**created**: 2026-09-06T07:40:40+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-medhead-widenfwd-c2-acq1

**wandb_id**: bfwfmdmo

**hypothesis**: Plain English: does the 2nd-seed medhead-widenfwd composition (just ACQ PASS at 40M, 21/24 gv, 0 falls) keep holding with another 40M of training (warm-started from the ACQ checkpoint, matching the endurance recipe already funded for seed-1's medhead-widenfwd-c1-acq1-cont40m and the other cont40m siblings)?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) after the extra 40M with no NEW chronic single-leg pattern and 0 falls beyond the ACQ read's baseline. FAIL/ENTRENCHES if gait_valid drops toward minority or a chronic leg[1,4]-style pattern emerges.

**verdict**: Endurance hold confirmed: this composition's 2nd-seed 40M ACQ checkpoint (widenfwd-c2-acq1, 21/24 gv) stays stable for another 40M (80M total). Fresh held-out gate (walk+walk_startjitter, det+sto, DR-0, n=24) reads 21/24 gait_valid -- flat vs the parent's own 21/24 -- with 0 falls/terminations in all 24 episodes both before and after. The flagged sacrifice pattern reproduces rather than consolidates: walk/det ep4 leg0 is the SAME episode+leg flagged at the parent; walk_startjitter/sto ep5 leg0 is also the identical episode+leg carried over; only walk_startjitter/sto ep4 leg5 is a new scattered flag (parent had a different scattered flag at walk/sto ep2 leg5 -- same leg, different episode, still not chronic). Slip/m stays in the same 3.7-6.4 band both budgets (above the 2.9 teacher cap, matching every sibling in this composite family). Matches this run's own pre-registered PASS/HOLDS branch (majority gv sustained, 0 new falls, no new chronic single-leg pattern) and the same-shape HARDENING PASS already recorded for its seed-1 sibling widenfwd-c1-acq1-cont40m. Video: contact sheet shows continuous six-leg cycling, no static pose. Next: no further budget on this lineage; joins the composition-cont40m endurance series (now consistently PASS across every tested composition seed).

