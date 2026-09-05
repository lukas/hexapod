# cw-walkscratch-easy0905-sdehalfgrav-remcost-s1-gg-rr1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: KILLED

**created**: 2026-09-05T13:15:18+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-remcost-s1

**wandb_id**: d3hzx7fe

**hypothesis**: Plain English: sdehalfgrav-remcost-s1 (2nd seed) matches remcost-s0's LEGPARK-SKATE fingerprint exactly (0/12 det falls, gait_valid 0/12, 2-leg sacrifice) -- same fix as remcost-s0-gg, this continuation adds reward.walk_gait_gate=1.0 + gait_gate_stride_mm=5 (bank-proven on sde-s1-c3gg/sde-s2-c3gg) to price parked legs to zero income until all six cycle. Second seed of the remcost+gait-gate generalization test.

**gate**: Acquisition milestone at OWN physics (0.5g) WITH gait validity: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, gait_valid true (no sacrificed legs, all six legs' swing_count>5) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Watch env/walk_gait_gate_factor (must rise from ~0 toward 1) and env/walk_speed (must not collapse to ~0). Per 08-21: factor rising + speed alive but gate unmet at 40M = continue; reward flat AND factor flat at 0 = FAIL.

**verdict**: KILLED_SELF_CORRECTED: same launch-mechanics bug as the -gg name it retried (fresh-scratch --use-sde retained, no --init-from -- respec cannot strip a bare flag from a cloned gSDE source). Superseded by the hand-built-arg-vector correct launch cw-walkscratch-easy0905-sdehalfgrav-remcost-s1-gg2 (verified --init-from present, --use-sde stripped).

