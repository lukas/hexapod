# cw-walkscratch-easy0905-sde-s1-c3gg

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-05T12:40:56+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s1-c2

**hypothesis**: Plain English: sde-s1-c2 learned to survive by parking 1-2 legs and skating the rest (LEGPARK-SKATE, ACQ FAIL misaligned) — this continuation keeps its 40M of survival skill but multiplies ALL transport income by the MIN over support legs of a recently-completed-real-swing score (reward.walk_gait_gate=1.0, the structural 08-13 close of the leg-sacrifice loophole that additive k_park_duty pricing cannot close), so the parked legs zero the income until all six cycle; gait_gate_stride_mm=5 lets the current ~6mm active-leg swings qualify (the MIN is held at 0 by the PARKED legs regardless of bar, so this only speeds income recovery once all six move), and k_step_event=1.0 pays each completed forward swing per-leg = the direct gradient for waking legs 1/4. Semantics-bank gait-gate trio repaired and 4/4 green this cycle (snapshot exp/walkcurr-legpark-skate-digin-gaitgate-bank-repair) before this launch.

**gate**: Acquisition milestone at easy physics WITH gait validity: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, gait_valid true (no sacrificed_legs, all six legs' swing_count > 5) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Watch env/walk_gait_gate_factor (must rise from ~0 toward 1) and env/walk_speed (must NOT collapse to ~0 — full-park recapture = FAIL regardless of reward). Per 08-21: factor rising + speed alive but gate unmet at 40M = continue; reward flat AND factor flat at 0 = FAIL (income blackout, retry at lower gate dose e.g. 0.7).

