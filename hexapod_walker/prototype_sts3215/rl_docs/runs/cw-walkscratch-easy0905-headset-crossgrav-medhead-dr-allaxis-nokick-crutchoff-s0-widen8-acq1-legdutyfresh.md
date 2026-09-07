# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyfresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T21:53:47+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1

**wandb_id**: cz6v360t

**hypothesis**: Plain English: does having the per-leg minimum-duty TERMINATION present from the START of the 8-way heading-widening training (not retrofitted after 40M steps of habit, as the just-closed 4/4 FAIL legdutyterm1 batch tried) prevent the chronic front-pair (legs 0/5) sacrifice from ever forming, instead of failing to repair it after the fact? Byte-identical to the original widen8-acq1 40M run (same seed, same --init-from the pre-widen8 medhead champion) with only the 5 walk_leg_duty_terminate/_penalty cfg-sets added from step 0 -- the from-scratch disambiguation the 09-07 ~21:5x widenbis180-legdutyterm1 verdict named as the next cheap test before either abandoning the termination approach or funding the heavier heading-conditioned role-aware mechanism.

**gate**: PASS if gait_valid across the 24-episode panel is majority-clean (>=18/24, matching the original pre-widen8/medhead baseline band) with NO chronic single-leg sacrifice recurring across most eval draws (transient/non-repeating drops OK), 0 new falls vs the undosed widen8-acq1 baseline, and walk_leg_duty_terminate firing rarely/not-at-all by the end of the 40M (policy never needed to lean on it). FAIL if the same front-pair (legs 0/5) chronic sacrifice still forms by 40M regardless of whether the termination is firing frequently or has gone quiet (a quiet termination with the leg still parked means it found a dodge, exactly like every closed per-tick-price mechanism).

