# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widen8-acq1-legdutyfresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-07T22:00:59+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widen8-acq1

**wandb_id**: sdy8u73j

**hypothesis**: Plain English: 3rd seed of the from-scratch legdutyterm dose disambiguation (see s0-widen8-acq1-legdutyfresh's own hypothesis) -- does having the per-leg minimum-duty TERMINATION present from the START of the 8-way heading-widening training prevent the chronic front-pair (legs 0/5) sacrifice from ever forming, instead of failing to repair it after 40M steps of habit like the just-closed 4/4 FAIL legdutyterm1 retrofit batch? Byte-identical to the original widen8-acq1 40M run (same seed 4, same --init-from the pre-widen8 medhead champion) with only the 5 walk_leg_duty_terminate/_penalty cfg-sets added from step 0. Queued to backlog (this cycle's 80M/2-launch cap already used by s0/s1); drain onto the next free slot.

**gate**: PASS if gait_valid across the 24-episode panel is majority-clean (>=18/24, matching the original pre-widen8/medhead baseline band) with NO chronic single-leg sacrifice recurring across most eval draws, 0 new falls vs the undosed widen8-acq1 baseline, and walk_leg_duty_terminate firing rarely/not-at-all by the end of the 40M. FAIL if the same front-pair (legs 0/5) chronic sacrifice still forms by 40M regardless of whether the termination is firing frequently or has gone quiet.

**verdict**: FAIL per own gate: gait_valid 13/24 (det2/6, sto4/6, sjdet5/6, sjsto2/6), chronic front-pair legs0/5 sacrificed in 11/24 episodes -- exact fingerprint the gate pre-registered as automatic FAIL. walk_leg_duty_terminate still firing at run end despite reward still rising (quarters 196.5->421.3->572.4->605.8); gate explicitly pre-registered chronic-sacrifice+reward-rising as FAIL. This CLOSES the widen8-acq1-legdutyfresh trio 3/3 FAIL (s0 12/24, s1 13/24, s2 13/24, identical legs0/5 fingerprint) -- combined with the 4/4 legdutyterm1 retrofit FAILs, safety.walk_leg_duty_terminate_s is now 7/7 FAIL (later confirmed 8/8 by the s0-widenbis180-legdutyfresh dig-in, RL_LOG 09-07 23:2x); termination-as-price is closed as a mechanism SHAPE for this pathology. Ledger-only closeout: already narratively triaged+FAIL-verdicted in RL_LOG 09-07 22:55/STATUS.md but ledger status/verdict/W&B note were never written -- recording now to match the published narrative, no new evidence.

