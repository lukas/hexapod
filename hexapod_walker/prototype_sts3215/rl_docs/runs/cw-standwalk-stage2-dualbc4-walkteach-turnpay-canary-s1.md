# cw-standwalk-stage2-dualbc4-walkteach-turnpay-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-08-30T23:43:28+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-turnpay-canary

**wandb_id**: 10dtf01e

**hypothesis**: Seed-1 twin of cw-standwalk-stage2-dualbc4-walkteach-turnpay-canary (see its ledger hypothesis for full rationale): paired seed for mechanism-health replication of the direct-yaw-income + denser-exposure turn canary before any acquisition spend.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, joint with seed0: PASS/promote if BOTH seeds show probe_turn_authority (checkpoint own cfg, wz_cmd=+-0.25, walk-mode-filtered) wz_med >= 0.08 both signs, det walk gait_valid >= 5/6, sacrificed legs ~0, and pure-walk (mode_seq OFF) det progress_ratio not hard-regressed vs the wave-1 band 0.43-0.48. FAIL if wz_med < 0.03 (still frozen), gait collapses, or straight-walk progress craters. Do not judge mature turn quality or close the reward class at 2M.

**verdict**: CANARY FAIL - MECHANISM (joint with seed0 twin cw-standwalk-stage2-dualbc4-walkteach-turnpay-canary; identical finding, see its verdict for full text): probe_turn_authority (checkpoint own cfg, wz_cmd=+-0.25, walk-mode-filtered, seeds 0/1) gives wz_med in [-0.0013,+0.0004] both signs vs the >=0.08 PASS bar and <0.03 FAIL threshold; wz_err_med 0.2496-0.2513, matching the frozen-body prediction |wz_cmd|=0.25. Training telemetry: env/walk_yaw_kernel_factor 0.16-0.26->0.05-0.08 over 2M, env/reward_walk_yaw declining, env/yaw_prog_wz_avg ~0 the whole run. No falls in probe (fell=false 8/8). Direct yaw income + denser exposure jointly refuted at canary scale on both seeds; not a single-seed fluke. NOT HARDWARE-READY. Evidence: /tmp/turnpay_probe_s1.json.

