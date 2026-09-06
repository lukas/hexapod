# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T12:20:32+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1

**hypothesis**: The full ~30-axis DR composite without the torque crutch (dr.torque_scale=1, true unassisted servo spec) just ACQ PASSED at 40M (22/24 gait_valid, 0 falls, matching/improving its own 21/24 canary). Per this campaign's own endurance-testing convention (every clean ACQ PASS in this campaign gets a cont40m hold-check before champion consideration), continue +40M (80M cumulative) to confirm it is durable past acquisition budget, not just at it -- closes the remaining half of QUEUE AIM items (3)/(4)'s precondition (the crutch-ON sibling allaxis-nokick-c1-acq1 landed the same cycle with 2 falls and is separately DIG-IN flagged; this continuation is independent of that finding).

**gate**: cont40m gate (80M cumulative): PASS/HOLDS if gait_valid stays majority (>=18/24), 0 falls/terminations, no NEW chronic single-leg pattern beyond the 2 scattered non-chronic flags already seen at 40M. FAIL/ENTRENCHES if gait_valid drops below majority, a chronic single-leg pattern emerges, or any fall appears where the 40M parent had none.

**refused_reason**: --steps belongs to the launcher, not the passthrough args

