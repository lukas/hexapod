# cw-walkscratch-easy0905-sdehalfgrav-remcost-s1-gg

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-05T13:12:44+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-remcost-s1

**hypothesis**: Plain English: sdehalfgrav-remcost-s1 (2nd seed) matches remcost-s0's LEGPARK-SKATE fingerprint exactly (0/12 det falls, gait_valid 0/12, 2-leg sacrifice) -- same fix as remcost-s0-gg, this continuation adds reward.walk_gait_gate=1.0 + gait_gate_stride_mm=5 (bank-proven on sde-s1-c3gg/sde-s2-c3gg) to price parked legs to zero income until all six cycle. Second seed of the remcost+gait-gate generalization test.

**gate**: Acquisition milestone at OWN physics (0.5g) WITH gait validity: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, gait_valid true (no sacrificed legs, all six legs' swing_count>5) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Watch env/walk_gait_gate_factor (must rise from ~0 toward 1) and env/walk_speed (must not collapse to ~0). Per 08-21: factor rising + speed alive but gate unmet at 40M = continue; reward flat AND factor flat at 0 = FAIL.

**failed_reason**: process died; log tail:
_cholesky__locals__kernel_25359851 955f36a load on device 'cuda:0' took 34.09 ms  (cached)
Module _linesearch_iterative_kernel__locals__kernel_3bda5534 1d4d749 load on device 'cuda:0' took 0.78 ms  (cached)
Module _solve_zero_search_dot__locals__kernel_9447c2fc 9447c2f load on device 'cuda:0' took 0.65 ms  (cached)
Module _solve_search_update__locals__kernel_427332be 427332b load on device 'cuda:0' took 0.41 ms  (cached)
Module _next_time_builder__locals___next_time_a67f49d6 a67f49d load on device 'cuda:0' took 0.60 ms  (cached)
Logging to /workspace/prototype_sts3215/rl_move/sim/policies/tb/PPO_12
[servo_model] full STL mesh assets not available (run mesh_mujoco/build_mesh_model.py for CPU full-mesh eval); using the checked-in mesh-family MJX primitive-collision twin hexapod_mesh_mjx.xml


