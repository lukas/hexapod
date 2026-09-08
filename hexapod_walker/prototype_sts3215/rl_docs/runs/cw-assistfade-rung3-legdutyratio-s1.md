# cw-assistfade-rung3-legdutyratio-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T02:19:52+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-assistfade-rung3-residualfade-s1

**wandb_id**: d9bpmm0s

**hypothesis**: Seed 1 of the s0 pair (same question): does reward.walk_leg_duty_ratio_charge fix assistfade rung3's chronic leg-sacrifice-plus-high-slip-drift FAIL on real mesh/100Hz physics? Single lever vs the already-FAIL bare cw-assistfade-rung3-residualfade-s1 baseline (which showed a CLEANER signal than s0 -- no progress-via-sacrifice confound, straight ignition miss with leg [0,5] chronically sacrificed in the nostdanneal read): adds the charge (dose150, target0.30, grace3s, tau1s, the validated walkcurr dose), otherwise byte-identical (blend schedule t1_steps=1.4M, log-std anneal, random-weight init, seed1).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same MECHANISM-HEALTH canary gate as the s0 twin (read that entry for the full text): confirm the charge engages via wandb_history.csv telemetry first (CANARY FAIL - INFRASTRUCTURE if it never fires after grace), then compare held-out walk/det+sto against the bare-rung3-s1 baseline's own report.json. PASS-if per-leg duty on the previously-chronic legs measurably improves without new falls/regression; FAIL-MECHANISM if statistically indistinguishable from the undosed baseline (episode-by-episode diff, per the walkcurr retrofit arm's own self-correction lesson) or worse. No ignition-gate claim from 2M alone; a longer acquisition continuation is a follow-up decision, not this canary's own scope.

