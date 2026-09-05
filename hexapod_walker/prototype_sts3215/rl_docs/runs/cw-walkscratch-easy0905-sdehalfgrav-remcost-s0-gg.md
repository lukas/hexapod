# cw-walkscratch-easy0905-sdehalfgrav-remcost-s0-gg

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: KILLED

**created**: 2026-09-05T13:14:01+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-remcost-s0

**wandb_id**: etdztfsy

**hypothesis**: Plain English: sdehalfgrav-remcost-s0 fixed the survival-duration exploit (falls 800->190, ep_len->1033) but still shows the LEGPARK-SKATE fingerprint (legs 1,4 permanently parked, gait_valid 0/6 every det+sto episode, contact-sheet confirms two retracted legs) -- this continuation keeps its 40M of survival+speed skill but multiplies transport income by the MIN over support legs of a recently-completed-real-swing score (reward.walk_gait_gate=1.0, gait_gate_stride_mm=5, the same bank-proven structural fix already funded on the bare-sde recipe as sde-s1-c3gg/sde-s2-c3gg), so the parked legs zero income until all six cycle. Tests this fix generalizes across the sde+halfgrav+remcost recipe family, not just bare sde.

**gate**: Acquisition milestone at OWN physics (0.5g) WITH gait validity: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, gait_valid true (no sacrificed legs, all six legs' swing_count>5) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Watch env/walk_gait_gate_factor (must rise from ~0 toward 1) and env/walk_speed (must not collapse to ~0). Per 08-21: factor rising + speed alive but gate unmet at 40M = continue; reward flat AND factor flat at 0 = FAIL.

**verdict**: KILLED_SELF_CORRECTED: launched fresh-scratch (--use-sde retained, no --init-from) instead of the intended own-checkpoint continuation -- the plain respec --from clone carried over --use-sde+elu from the source and respec has no flag-removal primitive, so this silently trained from scratch rather than continuing remcost-s0. Superseded by the hand-built-arg-vector correct launch cw-walkscratch-easy0905-sdehalfgrav-remcost-s0-gg2 (verified --init-from present, --use-sde stripped).

