# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T13:07:33+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: ruhn1ha3

**hypothesis**: Does directly pricing per-leg relative load-slip (the physical symptom -- how fast a foot slides while loaded, peer-excluded MEDIAN ratio, target 1.5, charge 150) alongside the existing duty-ratio charge fix the 'gait_valid recovers via worse slip' trade that dose escalation (0.30->0.45) and the swing-count-floor both failed to fix (3/3 walkcurr + 2/2 assistfade reproductions closed null/regressive)? This is a genuinely different mechanism from both prior attempts: a continuous physically-direct measurement of the actual bad symptom (slip), not a proxy (duty magnitude or swing count). Bank-tested this cycle (9 new unit tests + activation-matches-plain-when-off rollout guard, all green; 42/42 duty+gait+slip family tests green, only 2 unrelated pre-existing loadslip-bootstrap failures confirmed pre-existing via git-stash isolation). Same seed0/init-from/heading-set/DR/motor cfg as the matched 0.30-dose guardfix1 sibling, only the new load-slip charge added.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. (a) post-grace env/walk_leg_loadslip_ratio_excess and env/reward_walk_leg_loadslip_ratio must appear, finite, in real GPU telemetry. (b) zero new falls/terminations vs the matched 0.30-dose s0 guardfix1 sibling at the same seed/budget. (c) same joint gait_valid-AND-slip/progress comparison the swing-floor arms used: >=3/4 groups must jointly improve (not gait_valid alone) vs the matched 0.30-dose sibling for a CONTINUE signal; report whether the same episode indices that showed the gait_valid-recovers/slip-worsens trade at 0.30/0.45 dose and under the swing-floor still show it here. Read together with s1/s2 siblings (same launch batch): majority (>=2/3 seeds hitting >=3/4) funds a cont10m depth read; minority does not -- do not pool a single seed's read into a lever verdict.

