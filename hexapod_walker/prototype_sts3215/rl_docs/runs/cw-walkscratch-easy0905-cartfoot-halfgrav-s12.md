# cw-walkscratch-easy0905-cartfoot-halfgrav-s12

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T11:26:13+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s7

**wandb_id**: g8d825dk

**hypothesis**: Plain English: 4th-seed replicate of the halfgrav cart_foot ON canary, breaking the tie in the closed n=3 (seed7/10/11) cohort where cart_foot's gait_valid advantage over joint-space held for 2/3 seeds (s7 22/24 vs 10/24, s10 17/24 vs 7/24) but vanished for s11 (11/24 vs 10/24, near-parity). Byte-identical to cartfoot-halfgrav-s7 with only seed changed to 12.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: finite losses, weights changing, real joint/foot excursion, no hidden limiter, reward/tick agreeing with the bank (park~0, moving>0). NO WALKING AT 2M IS NOT A FAILURE. On PASS, extend to 40M acquisition (respec pattern) and read together with its matched offctrl-s12 OFF sibling: gait_valid gap vs slip-only difference determines whether the seed7/10 pattern (2/3) or the seed11 pattern (1/3) is the majority case for this recipe family.

