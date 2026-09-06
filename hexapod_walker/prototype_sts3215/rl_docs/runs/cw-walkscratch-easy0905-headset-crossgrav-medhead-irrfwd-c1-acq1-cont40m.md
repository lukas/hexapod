# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T06:56:20+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1-acq1

**wandb_id**: flkoqbnm

**hypothesis**: Plain English: medhead-irrfwd-c1-acq1 (irregular direction-change timing composed onto the campaign's cleanest crossgrav champion) held ACQ PASS at 40M (21/24, flat vs its own 22/24 canary). Same endurance-panel predictor test as the widenfwd-cont40m sibling launched this cycle: does a 2nd +40M helping hold/improve a source whose first 40M read was already clean (per the established rule), giving a 2nd concurrent confirmation from an independent composition (irr-first, not widen-first)?

**gate**: PASS/HOLDS if aggregate gait_valid stays >=18/24 at/above the 40M read's own 21/24, no NEW chronic single-leg pattern, 0 falls. WORSENS if gait_valid drops materially (e.g. <16/24) or a chronic leg[1,4]-style pattern spreads to a previously-clean mode — a counter-example to the cleanliness-margin-at-40M rule.

**verdict**: HARDENING/endurance continuation HOLDS (improves) at +40M (80M total): aggregate gait_valid 22/24 (walk/det 4/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), UP from the parent 40M read's own 21/24 (walk/det 4/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 5/6). 0 falls/terminations across all 24 episodes both reads. Evidence: the walk/det leg-flag pattern is the SAME confined single-mode signature (leg 5 only, episodes 1+5) as the parent's own leg-2/5-on-ep1 + leg-5-on-ep5 -- actually NARROWED (ep1 dropped from sac=[2,5] to sac=[5]) -- and the parent's one flagged walk_startjitter/sto episode (ep2, leg 0) is now clean. No new leg or mode picked up the pattern; frame strips (walk_det_1, the flagged episode) show clean six-leg body translation, softened not parked duty on leg 5, matching the established non-chronic signature. Why: this is the cleanliness-margin-at-40M rule holding as designed -- a confined, already-known single-leg softening does not spread or harden with more budget on this composition. course_err_1s/success stay poor (not this gate's bar; walkcurr ACQ-durability reads gait_valid/falls only, course-tracking is a separate later rung). Next: no further budget needed on this line; this composition (medhead-irrfwd) now has 2 independent clean data points (40M + 80M) and joins the campaign's cleanliness-margin precedent set alongside ramp-irrfwd-cont40m.

