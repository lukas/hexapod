# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-encnoise1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RECONSTRUCTED_LEDGER_ENTRY

**created**: 2026-09-06T07:53:05+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-encnoise1x-c1

**wandb_id**: dwznelgb

**hypothesis**: Sensing-side twin of the friction1x-c1-acq1 question: does the campaign's PERFECT single-axis DR-restore canary (medhead-dr-encnoise1x-c1: nominal ~1 LSB encoder read noise restored, 24/24 gait_valid, sac=[] every episode, 0 falls at 2M) hold up at acquisition-scale (40M) on top of the 80M champion?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice and 0 falls. FAIL/ENTRENCHES if it drops below half, a chronic single-leg pattern emerges, or a fall appears.

**note**: ledger entry for this run was lost (non-atomic experiments.json write race during the 09-06 ~06:59-07:03 concurrent-cycle incident already documented in walkcurr STATUS.md); reconstructed 09-06 ~07:5x from the cached W&B summary (wandb_id dwznelgb, config/cfg_set/notes match exactly) plus the checkpoint recovered by hand via kubectl cp from hexapod-mjx-train-8 (md5 829251d87fde76db30e16548217b4a92, 4469270 bytes, matches on-pod size exactly) -- training itself was never lost, only the ledger row.

