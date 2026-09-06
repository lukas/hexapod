# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-contactstiff1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T05:19:29+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: 4i5jjieu

**hypothesis**: Restore nominal (1x) ground-contact stiffness/compliance spread (contact_stiff_scale) -- the easy0905 recipe has trained with foot/ground contact solref timeconst pinned at the exact same fixed point every episode (dr-scale=0.0 collapses the RandRanges contact_stiff_scale pair (0.7,2.0) to a single fixed point when not explicitly overridden), i.e. every episode sees IDENTICAL ground compliance regardless of real surface hardness spread (concrete/mat/carpet). Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR contact-stiffness range (0.7-2.0x) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction DR-restoration arms.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls, slip/m not blown out past the champion band -- shows the gait tolerates ground-compliance spread. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, falls, or slip/m spikes) -- shows fixed-contact idealization is load-bearing.

**verdict**: CANARY PASS -- restoring nominal (0.7-2.0x) ground-contact stiffness/compliance spread (previously pinned identical every episode) on the champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24) costs almost nothing: aggregate gait_valid 23/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 5/6 with one non-chronic leg-4 flag, walk_startjitter/sto 6/6), 0 falls/terms. slip/m banded 3.0-5.2 (consistent with sibling DR-restore canaries). Video (walk_det_0) clean six-leg cycling. Joins deadband1x/latency1x/tiltnoise1x/noise1x/torquefade2x/encnoise1x as a clean axis-restore PASS.

