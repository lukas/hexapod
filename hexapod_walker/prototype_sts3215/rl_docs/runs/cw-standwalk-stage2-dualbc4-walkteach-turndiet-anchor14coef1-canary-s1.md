# cw-standwalk-stage2-dualbc4-walkteach-turndiet-anchor14coef1-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T21:30:46+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary-s1

**wandb_id**: 0bfbrd22

**hypothesis**: Seed-1 twin of the wave-2 turn-diet canary (see seed0's ledger hypothesis for full rationale) -- same turn-exposure + yaw-gate cfg, same init-from, paired seed for mechanism-health replication before any acquisition spend.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, joint with seed0: PASS/promote-to-8M if BOTH seeds show det walk gait_valid>=5/6, sacrificed legs ~0, progress_ratio not worse than wave-1's 0.43-0.46, AND a turn-in-place probe shows real wz tracking (wz_err well below the frozen-body wz_err~wz_ref prediction). FAIL if gait_valid collapses, sac legs reappear, straight-walk progress_ratio regresses hard, or turn probes still show frozen-body behavior.

