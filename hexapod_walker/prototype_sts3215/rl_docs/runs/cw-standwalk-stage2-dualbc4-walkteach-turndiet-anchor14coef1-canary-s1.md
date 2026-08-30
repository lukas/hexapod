# cw-standwalk-stage2-dualbc4-walkteach-turndiet-anchor14coef1-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-08-30T21:30:46+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary-s1

**wandb_id**: 0bfbrd22

**hypothesis**: Seed-1 twin of the wave-2 turn-diet canary (see seed0's ledger hypothesis for full rationale) -- same turn-exposure + yaw-gate cfg, same init-from, paired seed for mechanism-health replication before any acquisition spend.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, joint with seed0: PASS/promote-to-8M if BOTH seeds show det walk gait_valid>=5/6, sacrificed legs ~0, progress_ratio not worse than wave-1's 0.43-0.46, AND a turn-in-place probe shows real wz tracking (wz_err well below the frozen-body wz_err~wz_ref prediction). FAIL if gait_valid collapses, sac legs reappear, straight-walk progress_ratio regresses hard, or turn probes still show frozen-body behavior.

**verdict**: CANARY FAIL - MECHANISM: turn-in-place training exposure did NOT produce any turn authority at mechanism level - the policy still never rotates its body on command, the canary gate's own pre-registered FAIL clause. Evidence: probe_turn_authority (new instrument, walk-mode-filtered, with a scripted-gait control achieving wz~0.21 on the identical cfg) measured wz_med 0.0004-0.0011 rad/s vs commanded +/-0.25 on both signs and both probe seeds (wz_err_med 0.249-0.250 = exactly the frozen-body prediction); training telemetry shows env/walk_yaw_kernel_factor DECLINING 0.22->0.07 across the 2M run - the policy moved AWAY from turn tracking, not slowly toward it. Straight-walk health is fine within canary scope: det walk gait_valid 8/8, sacrificed legs 0, zero terminations, prog med 0.42-0.425 (NOTE: controller fastcheck ran with the run's own goal.mode_seq=0.75 so episodes compose walk->lower->rise segments; the parent band 0.43-0.46 is pure-walk - the straight-walk clause is not the failure, the turn clause is). Root cause chain: incentive existed (walk_kernel_yaw_gate=1.0 zeroes frozen-body kernel income on tip ticks, linear gradient in wz) and supervision existed (BC walk anchor IS omega-conditioned TripodGait with the run_on_yaw phase-clock fix), but the dose is homeopathic: wz!=0 appears ONLY in tip episodes (walk_yaw_zero_frac=1.0) = 15% of walk episodes = ~4.5% of experience, and the warm-start lineage trained its whole life with the wz obs channel constant zero, so the policy has learned to ignore the channel it now must read. 2M at this exposure produced literally zero wz response - no partial credit to continue. Do NOT promote to 8M. Next: turn-authority canary pair with denser yaw exposure (zero_frac 0.5, tip_frac 0.30) plus direct yaw income (the proven OMNI k_walk_yaw stack with kernel/hold gates + EMA), gated on the same probe instrument.

