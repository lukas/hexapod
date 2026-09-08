# cw-walkscratch-easy0905-widen8-jointspace-freshinit-quarterdr2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T15:01:14+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: x3lq37jw

**hypothesis**: Plain English: companion dose-ladder rung to this cycle's halfdr2m arm -- if halving every DR axis together (not removing any single one) still fails to ignite fresh-init walking on the widen8 composite, does quartering it (x0.25 magnitude/probability on every axis simultaneously, same structure as halfdr2m) ignite instead? Single-lever dose vs the SAME offctrl baseline halfdr2m used, not vs halfdr2m itself (independent rung, same ladder).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: PASS if majority gait_valid (>=13/24 pooled or >=3/4 modes) AND net forward speed >=0.03 m/s median AND 0 new falls vs the offctrl baseline -- licenses a 40M follow-up on this rung and pins the minimum DR magnitude that still ignites (compare against halfdr2m's own read). FAIL (still flat/thrashing, slip 8-142/m, near-zero net speed matching the closed fingerprint) means even a quarter-strength full composite is still too much, and DR must be curriculum-staged UP from near-zero rather than launched at any fixed fraction from step 0.

**verdict**: CANARY FAIL - MECHANISM: Quarter-strength DR dose (0.25x every dr.* axis) STILL fails to ignite on the widen8 jointspace fresh-init composite -- closes the fixed-fraction dose-ladder at all three rungs tested (1.0x, 0.5x halfdr2m, 0.25x here). Evidence: walk/det (primary gated mode) gait_valid 0/6, fwd med 0.00m over the full 20s episode in every one of 6 det episodes (contact sheet: robot visibly stationary, legs not translating body across all 10 sampled frames); walk_startjitter/det similarly collapses to 1/6. The sto-mode groups (5/6, 5/6 gait_valid) are the same skating artifact flagged in halfdr2m's verdict: slip/m 65-217 (40-70x the healthy <=2.9 band), i.e. noise-driven drag, not gaited locomotion -- do not read pooled gait_valid/naive-PASS off these. Training reward quarters [-90.9,-228.3,-346.9,-466.4] DECLINE monotonically (not the 08-21 rising-reward-continue shape) -- this is a genuine flat/regressing-reward result, not a case for more steps at this same fixed dose. Net: DR magnitude alone (any fixed nonzero fraction applied from step 0) is not the lever on this composite/init; the gate's own pre-registered FAIL branch licenses DR curriculum-staging UP from near-zero rather than more fixed-fraction rungs. No further fixed-dose rung is funded on this exact composite.

