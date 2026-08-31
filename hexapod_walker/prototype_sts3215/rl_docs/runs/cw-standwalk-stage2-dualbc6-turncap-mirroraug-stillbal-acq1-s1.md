# cw-standwalk-stage2-dualbc6-turncap-mirroraug-stillbal-acq1-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T19:58:57+00:00

**pod**: hexapod-mjx-train-1

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yaw5x-acq1

**wandb_id**: qdhjgs0j

**hypothesis**: Plain English: seed-1 twin of stillbal-acq1 — does symmetric rotation pricing (k_yaw_still 50->5, the only change vs the refuted yaw5x-acq1 recipe) stop PPO from trading turn authority away? Campaign convention: every retention arm runs as a 2-seed pair; yaw5x showed real seed variance in erosion DEPTH (seed0 froze at 0.024-0.039, seed1 held a 0.045-0.116 mid-band), so a single seed cannot separate 'slowed erosion' from seed luck. Same trace evidence as the seed0 twin (probe_yaw_credit income accounting: turning is net-profitable +1.0-1.3/tick yet erodes; critic value degenerate-constant; the 10x still-vs-turn pricing asymmetry on 50% of commands is the last unpriced suspect). Prediction-if-true: snapshot curve holds materially above yaw5x-acq1-s1's measured mid-band (0.045-0.116) and final reads >=0.10 both signs. Prediction-if-false: same erosion band as its 1x/5x predecessors.

**gate**: ACQUISITION retention test, seed-1 twin — SAME gate as cw-standwalk-stage2-dualbc6-turncap-mirroraug-stillbal-acq1: PASS if final probe_turn_authority wz_med >= 0.10 both signs AND gait_valid >= 5/6 zero falls AND pure-walk det progress_ratio in/above 0.40-0.48. FAIL if snapshot curve matches the yaw5x pair's measured erosion. DRIFT-BREAK FAIL if zero-cmd heading drift returns beyond noise. PARTIAL otherwise — joint read with seed0.

