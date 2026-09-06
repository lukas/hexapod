# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-groundtilt1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T09:08:33+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-groundtilt1x-c1

**wandb_id**: z6vush6h

**hypothesis**: Does the PERFECT floor-slope (tilted-ground) mechanism-health canary (medhead-dr-groundtilt1x-c1: 24/24 gait_valid at 2M, 0 falls, sac=[] every episode) hold up at a real 40M ACQ budget -- moving this axis beyond its mechanism-health-only scope into a genuine skill-acquisition durability read, matching the friction1x/mass1x/cmddrop1x/imubias1x precedent?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg pattern and 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall).

**verdict**: ACQ PASS/HOLDS -- found as an orphan (training + gate finished, ledger stuck at stale RUNNING, no verdict) -- the floor-slope (ground-tilt DR) axis is durable at real 40M ACQ scale (steps=40370176). Aggregate gait_valid 22/24 (6/6 det, 6/6 sto, 5/6 startjitter/det, 5/6 startjitter/sto), 0 falls/terms across all 24 episodes, only 2 non-chronic singleton sac flags (leg5 in one startjitter/det episode, leg0 in one startjitter/sto episode) -- no repeat, no new chronic leg. slip/m in-band (3.5-5.7). Reward rising every quarter (786->1384->1451->1546). Contact sheet confirms clean six-leg cycling. Matches its own 2M canary's PERFECT 24/24 class closely enough (majority-hold, no new pathology) -- ground-tilt joins the durable-single-axis set.

