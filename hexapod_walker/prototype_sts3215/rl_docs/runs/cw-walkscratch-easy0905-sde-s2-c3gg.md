# cw-walkscratch-easy0905-sde-s2-c3gg

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T12:39:40+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s2-c2

**wandb_id**: vb2m7gr2

**hypothesis**: Second independent seed of the LEGPARK-SKATE structural repair (see sde-s1-c3gg): sde-s2-c2 shows the identical exploit (sacrificed legs [1]/[3,4], reward up while walk_speed declines to the freeprog cap) — same walk_gait_gate=1.0 + gait_gate_stride_mm=5 + k_step_event=1.0 continuation from its own checkpoint. Two seeds decide whether the structural gate reliably recovers six-leg cycling from inside the legpark basin, or whether the sde cell should be closed (Gaussian families are already 8/8 valid-gait PASS at this rung).

**gate**: Acquisition milestone at easy physics WITH gait validity: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, gait_valid true (no sacrificed_legs, all six legs' swing_count > 5) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Watch env/walk_gait_gate_factor (must rise from ~0 toward 1) and env/walk_speed (must NOT collapse to ~0 — full-park recapture = FAIL regardless of reward). Per 08-21: factor rising + speed alive but gate unmet at 40M = continue; reward flat AND factor flat at 0 = FAIL (income blackout, retry at lower gate dose e.g. 0.7).

