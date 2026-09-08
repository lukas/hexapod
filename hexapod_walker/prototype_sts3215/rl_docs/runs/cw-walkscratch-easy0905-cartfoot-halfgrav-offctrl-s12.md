# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s12

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T11:28:40+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7

**hypothesis**: Plain English: matched joint-space control for the halfgrav cart_foot seed12 canary (ON launched same cycle) -- 4th-seed replicate breaking the tie in the closed n=3 cohort (2/3 seeds showed a cart_foot gait_valid advantage, 1/3 near-parity). Byte-identical to cartfoot-halfgrav-offctrl-s7 with only seed changed to 12.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: finite losses, weights changing, real joint/foot excursion, no hidden limiter, reward/tick agreeing with the bank. NO WALKING AT 2M IS NOT A FAILURE. On PASS, extend to 40M acquisition and read together with the ON s12 sibling: same joint reading protocol as s7/s10/s11 (>=0.03 m/s median net forward in >=1 of walk/det,sto, 0 falls in det; slip/m and gait_valid vs ON sibling are the headline comparisons).

