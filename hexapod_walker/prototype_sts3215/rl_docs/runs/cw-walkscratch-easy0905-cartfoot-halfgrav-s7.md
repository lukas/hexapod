# cw-walkscratch-easy0905-cartfoot-halfgrav-s7

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T08:35:49+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**wandb_id**: 4fubbj7g

**hypothesis**: Plain English: does the Cartesian foot-target action decode, already proven to reach fresh-init slip PARITY with joint-space at 1g (n=3 seeds, both 40M and 50M durability), ALSO bootstrap cleanly at 0.5g -- the other gravity cell this campaign has validated for joint-space (base+halfgrav 2x2)? Byte-identical to the proven cw-walkscratch-easy0905-halfgrav-s0 recipe (fresh random init, easy-DR-0, gamma .995/lam .97, 256,256,128 ELU, ease.gravity_scale=0.5) plus seed 7 (reusing the cart_foot family's own proven seed) and the 3 cart_foot box keys (0.06/0.035/0.04 m, same bank-proven leg-root-frame IK already used in the 1g fork(b) cohort). No teacher/BC/phase/clock/motion prior. Matched against the joint-space control offctrl-s7 launched the same cycle.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M MECHANISM-HEALTH CANARY ONLY (same bar as halfgrav-s0/cartfoot-freshinit-c1-s7 themselves used): finite losses, weights changing, real joint/foot excursion beyond settled stance, reward agrees with WALKSCRATCH_EASY semantics bank. No-walk-at-2M is NOT a failure (halfgrav-s0 and cartfoot-freshinit-c1-s7 both needed the long continuation chain to walk). Read together with the matched offctrl-cartfoot-halfgrav-s7 control; healthy canaries get the normal 40M acquisition continuation next cycle.

**verdict**: CANARY PASS: Cartesian-foot-target (ON) control ignites cleanly at 0.5g+seed7, matching the joint-space (OFF) sibling offctrl-s7 (verdicted this cycle). Finite losses, std anneals 0.37->0.22 on schedule. ep_rew_mean falls (-132->-619) but per-tick env/reward_walk RISES 0.164->0.188->0.217->0.229 and env/v_along_cmd_m_s turns positive (-0.003->+0.010) as ep_len_mean grows 103->224->353->488 -- the same healthy ep_len-growth artifact as the OFF control and the 1g fork(b) precedent, not real regression. 0 falls/terminations across all 24 episodes, gait_valid 6/6, 6/6, 5/6, 6/6 across the four modes. Slip is near-parity with the matched joint-space control at this early stage: det 1.03 (ON) vs 0.83 (OFF), sto 21.79 med (ON) vs 28.16 med (OFF) -- ON is not worse here, unlike the mature 1g comparison where cart_foot eventually showed a 3-10x slip gap only after a long continuation chain (cartfoot-c1-cont10m). This 2M canary cannot yet see that divergence either way; it answers ignition only. Both halfgrav-s7 (ON) and offctrl-s7 (OFF) clear the CANARY PASS bar (finite/changing weights, real excursion beyond settled stance, reward agrees with the WALKSCRATCH_EASY bank, 0 falls) -- the 0.5g cell of the base/halfgrav x joint/cartfoot 2x2 matrix is now proven to ignite for BOTH action spaces, same as the 1g cell.

