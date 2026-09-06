# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-actionnoise1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T05:48:01+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: 5hdibkd4

**hypothesis**: Restore nominal (1x) ACTION-NOISE spread (dr.action_noise: gaussian noise injected on the policy's own commanded action before it reaches the servo model, distinct from the already-tested sensor-side encoder/tilt/gyro noise axes) -- the easy0905 recipe has trained with a perfectly noiseless action pathway every episode (dr-scale=0.0 collapses this to 0 when not explicitly overridden). Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR action-noise spread (0.02) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/mass/friction/gain/geometry/sensor-noise DR-restoration arms -- closes out the actuation-noise axis distinct from sensing-noise (already split into encnoise1x/tiltnoise1x/gyronoise1x).

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the noiseless-action-pathway idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows action-noise realism is a binding constraint the DR-rung must budget real training time against.

**verdict**: CANARY PASS — actuation-side action-noise (dr.action_noise=0.02) restores clean on the campaign's cleanest champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24). Evidence: aggregate gait_valid 22/24 (walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6 all PERFECT; walk/det 4/6 with leg-5 flagged in 2 of 6 episodes, confined to that single mode, not chronic across modes -- matches the precedent set by contactstiff1x/deadband1x's own non-chronic single-mode flags, both called PASS). 0 falls in all 24 episodes. slip/m median 3.95 (band 3.13-5.27), consistent with every sibling DR-restore axis this sweep has tested. Video (walk_det/walk_sto/startjitter contact sheets) confirms six-leg cycling gait, no skating/paddle-creep beyond the established band. Shows the gait does not depend on a noiseless-action-pathway idealization -- joins latency/deadband/torquefade/mass/friction/contactstiff/encnoise/gyronoise/gyrobias/push/tiltnoise/velscale/cmddrop/imubias/groundtilt/imupos as a clean single-axis DR-restore PASS. No ACQ continuation queued this cycle (fleet already saturated with 2 fresh ACQ continuations -- torquefade2x-c1-acq1, mass1x-c1-acq1 -- launched this same cycle for the two highest-value untested-at-scale axes).

