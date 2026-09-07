# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyfresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T21:57:14+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1

**wandb_id**: 2oy8dcf9

**hypothesis**: Plain English: 2nd seed of the from-scratch legdutyterm dose disambiguation (see s0-widen8-acq1-legdutyfresh's own hypothesis) -- does having the per-leg minimum-duty TERMINATION present from the START of the 8-way heading-widening training prevent the chronic front-pair (legs 0/5) sacrifice from ever forming, instead of failing to repair it after 40M steps of habit like the just-closed 4/4 FAIL legdutyterm1 retrofit batch? Byte-identical to the original widen8-acq1 40M run (same seed 3, same --init-from the pre-widen8 medhead champion) with only the 5 walk_leg_duty_terminate/_penalty cfg-sets added from step 0.

**gate**: PASS if gait_valid across the 24-episode panel is majority-clean (>=18/24, matching the original pre-widen8/medhead baseline band) with NO chronic single-leg sacrifice recurring across most eval draws, 0 new falls vs the undosed widen8-acq1 baseline, and walk_leg_duty_terminate firing rarely/not-at-all by the end of the 40M. FAIL if the same front-pair (legs 0/5) chronic sacrifice still forms by 40M regardless of whether the termination is firing frequently or has gone quiet.

