# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-friction1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T05:11:26+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: 2lblab0c

**hypothesis**: Restore nominal (1x) ground-friction randomization -- the easy0905 recipe has trained with foot/ground friction pinned at an exact fixed 1.0x scale (dr-scale=0.0 collapses the RandRanges friction_scale pair(0.6,1.4) to a single fixed point when not explicitly overridden) throughout the whole crossgrav campaign. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR friction range (0.6-1.4x, i.e. from noticeably slippery to noticeably grippy) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass DR-restoration arms.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the fixed-friction idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows friction realism is a binding constraint the DR-rung must budget real training time against.

**verdict**: CANARY PASS -- restoring nominal (0.6-1.4x) ground-friction randomization (previously pinned at exactly 1.0x every episode, arguably the axis most directly tied to this campaign's own tracked slip/m metric) on the champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24) costs NOTHING: a PERFECT 24/24, sac=[] every episode, 0 falls/terms. slip/m banded 3.2-5.8 (consistent with sibling DR-restore canaries, no blowout into a skate/paddle regime despite the wider friction range). Video (walk_det_0) clean six-leg cycling. Joins deadband1x/latency1x/tiltnoise1x/noise1x/torquefade2x/encnoise1x/contactstiff1x as a clean axis-restore PASS.

