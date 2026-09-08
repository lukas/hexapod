# cw-assistfade-rung3-legdutyratio-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-08T02:19:52+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-assistfade-rung3-residualfade-s1

**wandb_id**: d9bpmm0s

**hypothesis**: Seed 1 of the s0 pair (same question): does reward.walk_leg_duty_ratio_charge fix assistfade rung3's chronic leg-sacrifice-plus-high-slip-drift FAIL on real mesh/100Hz physics? Single lever vs the already-FAIL bare cw-assistfade-rung3-residualfade-s1 baseline (which showed a CLEANER signal than s0 -- no progress-via-sacrifice confound, straight ignition miss with leg [0,5] chronically sacrificed in the nostdanneal read): adds the charge (dose150, target0.30, grace3s, tau1s, the validated walkcurr dose), otherwise byte-identical (blend schedule t1_steps=1.4M, log-std anneal, random-weight init, seed1).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same MECHANISM-HEALTH canary gate as the s0 twin (read that entry for the full text): confirm the charge engages via wandb_history.csv telemetry first (CANARY FAIL - INFRASTRUCTURE if it never fires after grace), then compare held-out walk/det+sto against the bare-rung3-s1 baseline's own report.json. PASS-if per-leg duty on the previously-chronic legs measurably improves without new falls/regression; FAIL-MECHANISM if statistically indistinguishable from the undosed baseline (episode-by-episode diff, per the walkcurr retrofit arm's own self-correction lesson) or worse. No ignition-gate claim from 2M alone; a longer acquisition continuation is a follow-up decision, not this canary's own scope.

**verdict**: CANARY FAIL - MECHANISM (per its own pre-registered gate). Charge telemetrically engages after the 3s grace (env/walk_leg_duty_ratio_shortfall/reward_walk_leg_duty_ratio genuinely nonzero from step ~396, rising to shortfall ~0.009 by end of the 2M buds -- not the earlier activation-guard bug), so this is not FAIL-INFRASTRUCTURE. But held-out 24-episode det+sto walk/startjitter panel is WORSE than the undosed bare-rung3-s1-nostdanneal baseline, not improved: gait_valid totals 2/24 (walk/det 0/6, walk/sto 0/6, sj/det 0/6, sj/sto 2/6) vs baseline 5/24 (0/6, 1/6, 0/6, 4/6) -- a net REGRESSION, losing passes in walk/sto (1->0) and sj/sto (4->2). Per-leg diagnosis: leg5, the dominant chronic-sacrifice leg in the baseline, is UNCHANGED -- duty_cycle=1.0, swing_count=0 in every single walk/det and walk/sto episode (6/6 each), i.e. still fully planted/never lifts, identical pathology to baseline. Leg0 partially recovers (duty 0.1->0.45-0.6, some swings) but that is not enough to fix six-leg validity since leg5 alone still fails gait_valid every episode. Slip also gets worse where episodes now survive to completion: walk/det slip_per_m 17.02 (charge) vs 10.68 (baseline) -- the charge trades over_current TERMINATION (baseline: all 24/24 episodes terminate) for a static-stall/high-slip failure mode instead (charge: 9/24 terminate, but the 15 that survive do so by chronically planting leg5 and barely creeping, prog med 0.05, not by walking). Reward quarters [101.4,161.0,196.9,95.4] peak then decline late, matching this tracks own already-diagnosed drift-into-high-slip/reward-misalignment fingerprint, not a genuine skill gain. This is the SAME mechanism that CANARY PASSED on walkcurr (a different task diet, no residual-fade schedule/BC-anchor interaction) -- result does NOT generalize to assistfade rung3 as tested: it does not resolve the chronic single-leg-sacrifice pathology this composition was designed to fix, and net gait validity regresses. No further rung3+legdutyratio budget from this arm; s0 twin still evaluating (own pod, unclaimed). Track-level design lead (per-leg-utilization pricing) stays open but this specific composition (charge onto the byte-identical closed bare-rung3 recipe) is now closed 1/2 seeds FAIL, pending s0. Evidence: logs/ckpt_eval/cw_assistfade_rung3_legdutyratio_s1_gate/report.json vs .../cw_assistfade_rung3_residualfade_s1_nostdanneal_gate/report.json; logs/experiments/cw-assistfade-rung3-legdutyratio-s1/wandb_history.csv. W&B d9bpmm0s.

