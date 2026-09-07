# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180-legdutyfresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T22:03:01+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180

**wandb_id**: d3qlhag1

**hypothesis**: Plain English: 4th arm of the from-scratch legdutyterm dose disambiguation (see s0-widen8-acq1-legdutyfresh's hypothesis), on the OTHER already-entrenched lineage (widenbis180, base5+ONLY the 180deg heading) -- does having the per-leg minimum-duty TERMINATION present from the START of training prevent the chronic leg-0 sacrifice from ever forming, instead of failing to repair it after 40M steps of habit like the just-closed s0-widenbis180-legdutyterm1 retrofit FAIL? Byte-identical to the original widenbis180 40M run (same seed, same --init-from the pre-widen medhead champion) with only the 5 walk_leg_duty_terminate/_penalty cfg-sets added from step 0. Queued to backlog (no launch cap left this cycle); drain onto the next free slot.

**gate**: PASS if gait_valid across the 24-episode panel is majority-clean (>=18/24, matching the pre-widen/medhead baseline band), no chronic leg-0 sacrifice recurring across most eval draws, 0 new falls vs the undosed widenbis180 baseline, and walk_leg_duty_terminate firing rarely/not-at-all by the end of the 40M. FAIL if the same leg-0 chronic sacrifice still forms by 40M regardless of whether the termination is firing frequently or has gone quiet.

