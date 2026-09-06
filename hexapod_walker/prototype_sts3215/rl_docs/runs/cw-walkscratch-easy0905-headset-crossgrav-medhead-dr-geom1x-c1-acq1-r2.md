# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-geom1x-c1-acq1-r2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T08:39:54+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-geom1x-c1

**wandb_id**: 442acsdz

**hypothesis**: Plain English: does the nominal print/assembly GEOMETRY spread (link_len_scale_pct/link_len_leg_pct/com_offset_m) stay a clean walk with a REAL 40M training budget, not just a 2M canary glance? Re-run of geom1x-c1-acq1, which landed with an accidental 2M-step budget (the --steps-not-overridden respec bug, RL_LOG 09-06 07:3x/08:2x) -- this -r2 explicitly pins --steps 40000000 to give the axis its intended first ACQ-scale confirmation.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show the geometry-spread axis needs more/different training exposure before being called safe.

**verdict**: ACQ PASS/HOLDS -- the corrected (real 40M, not the r1 2M-step-bug budget) print/assembly GEOMETRY-spread axis (link_len_scale_pct/link_len_leg_pct/com_offset_m) is durable at ACQ scale. Evidence: aggregate gait_valid 22/24 (6/6 det, 5/6 sto, 5/6 startjitter-det, 6/6 startjitter-sto), 0 falls/terms across all 24 episodes, only 2 non-chronic single-episode sac flags (walk/sto ep2 leg0, startjitter/det ep5 leg1) that do not repeat across modes -- no new chronic single-leg sacrifice vs the 2M canary. slip/m flat (3.1-4.5, in-band), reward still rising every quarter (507->953->1016->1083). Contact sheet confirms clean six-leg cycling gait, no dragging/skating. Matches the 2M canary's own clean read (21/24) and closes geometry as another confirmed-durable single-axis DR-restore source -- per this doc's own QUEUE AIM this is a recorded confirmation of already-funded work, not a new axis to chase; no further per-axis spend justified by this result.

