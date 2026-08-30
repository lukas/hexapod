# cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-08-30T11:25:28+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc2-allheadwalk-anchor14coef1-canary-s1

**wandb_id**: uwy454jo

**hypothesis**: Seed1 companion of cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary (same recipe/base question, same paired-seed convention as the dualbc2 pair) -- checks whether the anchor14coef1 recipe's seed-dependence (seed1 was historically the catastrophe-prone seed on the OLD teacher lineage) reproduces on the DAgger-repaired dualbc3_dagger base, which this cycle's quick_probe re-run confirmed actually walks net-forward (0.463/0.493m/15s fixed-heading, vs dualbc2's 0.004-0.026m in-place quiver).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same MECHANISM-HEALTH CANARY gate as the seed0 twin, read jointly: WIRING CHECK bc_anchor_loss_walk/fill_walk nonzero; PASS/promote if gait_valid>=5/6 zero-sac and progress_ratio clears 0.10-0.18; PARTIAL if gait_valid holds but progress flat (still fund 8M); FAIL if anchor4-class catastrophe or probe pathologies worsen under RL -- note base is now pre-verified walking, so FAIL implicates the recipe not the base.

**verdict**: CANARY PASS, joint close with the seed0 twin. Same fast-eval-on-spare-pod protocol (train-3, weights unchanged, since ledger gate/owncfg still mid-flight): det walk gait_valid 8/8, sacrificed_legs=[] every episode, 0/8 terminations, progress_ratio 0.39 (forward_dist_m 0.87-0.90m/30s at speed 0.044 m/s) -- clears the 0.10-0.18 old-teacher band by an even wider margin than seed0, slip/m 2.71, dir_err_mean 58.7deg (course_err_1s 2.1deg -- clean short-window tracking, same low-speed-episode-start artifact as seed0). Sto weaker (prog_ratio 0.06, slip/m 12.9) but net-forward (fwd 0.12-0.15m/30s), zero falls/sac. WIRING CHECK clean (bc_anchor_loss_walk 0.0005-0.005 falling, fill_walk 12k->39.6k monotonic). This is seed1 -- historically the catastrophe-prone seed on the OLD teacher lineage -- now the STRONGER of the two on the repaired base, confirming this is a genuinely fixed base, not a lucky seed0 draw. Next: promoted -- launched cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-acq8m-s1 (8M, train-1, same std-anneal bundle as the seed0 twin).

