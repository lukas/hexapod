# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s11-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-08T07:12:00+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s11

**wandb_id**: ilmolyis

**hypothesis**: Plain English: matched control for cartfoot-freshinit-c1-s11-acq1 -- the same exact 40M own-checkpoint continuation of the joint-decode (no Cartesian keys) seed-11 arm, so the fresh-init seed cohort's ON-vs-OFF slip/gait_valid read at full budget is causal to the 3 cart keys, not a seed or training-depth artifact. Completes the n>=3 fresh-init pair set (s7 done, s10 in flight, s11 now paired).

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with cartfoot-freshinit-c1-s11-acq1 at the SAME budget. This is the matched control -- if it itself drifts/fails the acquisition bar, read the ON/OFF pair as inconclusive rather than crediting/blaming the Cartesian mechanism.

**verdict**: Matched joint-space control, seed11, 40M: 0/24 falls, gait_valid 6/6 sto, 6/6 startjitter/sto, but 0/6 walk/det and 0/6 startjitter/det (legs [1,4] sacrificed identically every det episode, vanishing under stochastic action noise) -- the same benign det-only leg-underuse fingerprint already precedented family-wide (halfgrav-s0-c1, base-cartfoot-fresh-s10-c1b), not a new pathology. Speed clears the 0.03 m/s floor in all groups (0.14-0.18 m/s). Reward rises every quarter (-363.8->1907.2), no plateau. This is the matched control read together with the ON arm this cycle: ON lands at-or-under this control's slip in all 4 groups (0.94-1.00x), confirming the pair reads as a valid PARITY comparison, not confounded by control drift.

