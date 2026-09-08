# cw-walkscratch-easy0905-widen8-jointspace-freshinit-quarterdr2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T15:01:14+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**hypothesis**: Plain English: companion dose-ladder rung to this cycle's halfdr2m arm -- if halving every DR axis together (not removing any single one) still fails to ignite fresh-init walking on the widen8 composite, does quartering it (x0.25 magnitude/probability on every axis simultaneously, same structure as halfdr2m) ignite instead? Single-lever dose vs the SAME offctrl baseline halfdr2m used, not vs halfdr2m itself (independent rung, same ladder).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: PASS if majority gait_valid (>=13/24 pooled or >=3/4 modes) AND net forward speed >=0.03 m/s median AND 0 new falls vs the offctrl baseline -- licenses a 40M follow-up on this rung and pins the minimum DR magnitude that still ignites (compare against halfdr2m's own read). FAIL (still flat/thrashing, slip 8-142/m, near-zero net speed matching the closed fingerprint) means even a quarter-strength full composite is still too much, and DR must be curriculum-staged UP from near-zero rather than launched at any fixed fraction from step 0.

