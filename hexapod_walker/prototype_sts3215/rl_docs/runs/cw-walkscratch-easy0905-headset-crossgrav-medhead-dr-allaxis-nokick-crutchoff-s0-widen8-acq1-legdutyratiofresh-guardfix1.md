# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratiofresh-guardfix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T00:30:24+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratiofresh

**wandb_id**: iwhaciad

**hypothesis**: Activation recovery after INVALID_MECHANISM_NOT_ACTIVATED in cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratiofresh. Fix ebad6d0df adds the missing ratio reward to contact bookkeeping; two sparse-config regressions fail before and pass after, 9 focused tests pass. This bounded 2M rerun preserves the source attempt's ORIGINAL --init-from checkpoint, RNG seed2, reward150/target0.30/grace3s, heading and motor settings. It does not initialize from the undosed failed-attempt output. First test is runtime activation: ratio ticks and scalar shortfall/charge must appear after grace in the actual sharded GPU training path. Only then does held-out leg usage assess the intended mechanism; no new seed and no class-wide conclusion from a short null.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY. First require post-grace env/walk_leg_duty_ratio_shortfall and env/reward_walk_leg_duty_ratio in actual GPU training telemetry, with finite nonpositive charge and consistent -150*shortfall; missing telemetry is infrastructure/mechanism invalidity, not efficacy FAIL. Preserve exact original held-out 24-episode deterministic/stochastic walk/start-jitter evaluation and existing safety limits. Record duty ratios and gait_valid against the original undosed parent; zero new falls required for healthy continuation. Behavioral improvements justify a recorded longer continuation; short nulls do not close an entire reward class.

