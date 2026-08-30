# cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T11:25:28+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc2-allheadwalk-anchor14coef1-canary-s1

**wandb_id**: uwy454jo

**hypothesis**: Seed1 companion of cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary (same recipe/base question, same paired-seed convention as the dualbc2 pair) -- checks whether the anchor14coef1 recipe's seed-dependence (seed1 was historically the catastrophe-prone seed on the OLD teacher lineage) reproduces on the DAgger-repaired dualbc3_dagger base, which this cycle's quick_probe re-run confirmed actually walks net-forward (0.463/0.493m/15s fixed-heading, vs dualbc2's 0.004-0.026m in-place quiver).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same MECHANISM-HEALTH CANARY gate as the seed0 twin, read jointly: WIRING CHECK bc_anchor_loss_walk/fill_walk nonzero; PASS/promote if gait_valid>=5/6 zero-sac and progress_ratio clears 0.10-0.18; PARTIAL if gait_valid holds but progress flat (still fund 8M); FAIL if anchor4-class catastrophe or probe pathologies worsen under RL -- note base is now pre-verified walking, so FAIL implicates the recipe not the base.

