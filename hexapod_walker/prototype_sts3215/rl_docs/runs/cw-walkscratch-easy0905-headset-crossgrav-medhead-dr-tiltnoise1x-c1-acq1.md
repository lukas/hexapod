# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-tiltnoise1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-06T08:03:51+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-tiltnoise1x-c1

**wandb_id**: 7ejprgld

**hypothesis**: Plain English: does the nominal (0.3deg) IMU tilt-sensor noise axis stay a clean walk with a real 40M training budget, not just a 2M canary glance? tiltnoise1x-c1's own 2M canary was a PERFECT 24/24 (0 falls, sac=[] every episode) -- this is its first ACQ-scale confirmation, joining the sibling latency1x/torquefade/mass/friction/gains/geom/fault/extpush/actionnoise/contactstiff/deadband individual-axis durability batch.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show tilt-noise realism needs real training exposure before being called safe.

**verdict**: CANARY PASS: 40M ACQ read of the tilt-noise DR-restore axis (2M canary source, 09-06) on the medhead-crossgrav champion. gait_valid 24/24 across all 4 groups (6/6 each), 0 falls/terminations in every mode, slip/m med 3.88-4.80 (in-band, matches the sibling DR-restore axes' 3.4-5.6 range), progress_ratio med 1.66-1.93 (>>1.0). Reward quarters rise monotonically [789.2, 1392.9, 1464.3, 1560.1], still climbing at 40M. Contact-sheet + walk_det frame strip: body clearly translating across frames, legs visibly cycling stance/swing, no flag-leg/skate. This eval was orphaned since 09-06 (checkpoint pulled repeatedly but the gate harness's report.json was never generated/copied back -- prestage gap, not a training problem); reaped via ops.sh podeval this cycle, no relaunch needed. Confirms the tilt-noise axis as durable at ACQ depth, joining the already-closed single-axis DR-restore sweep (09-06 ~10:1x-10:24: 'per-axis funding now closed, every RandRanges field covered') -- no new frontier implication, this is mop-up of a pending read, not new information.

