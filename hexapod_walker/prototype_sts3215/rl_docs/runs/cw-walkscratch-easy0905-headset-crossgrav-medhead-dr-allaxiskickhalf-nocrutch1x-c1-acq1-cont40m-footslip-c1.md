# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-footslip-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T17:00:26+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-loadslip-c1

**wandb_id**: itmvzmdh

**hypothesis**: Plain English: can pricing loaded-foot sideways slip PER-TICK (not the failed episode-cumulative loadslip ratio, closed this cycle for barely moving the metric) make this already-clean champion (0 falls, six-leg gait_valid, only gap = slip/m 4.3-6.5x the 2.9 cap) actually slip less? Single-lever swap vs the byte-identical bare recipe: turn the FAILED loadslip-gate mechanism fully off (reward.walk_loadslip_gate=0.0, reward.k_loadslip_excess=0.0) and arm reward.k_foot_slip_tangent=35.0 (+foot_slip_contact_n=2.0/deadband_m_s=0.015/max_m_s=0.25, goal.walk_contact_diagnostics=1.0 for W&B visibility) -- a contact-conditioned per-tick charge on foot XY velocity while planted, structurally immune to the cumulative ratio's floor-clamped-denominator defect. Bank-checked (WALKCURR_ITEM4_FOOTSLIP_OVERRIDES, test_task_semantics.py, 4/4 new tests green): skate reads clearly worse than park/gait/stall, honest gait stays clearly positive (759.6 vs bare 1005.7, -24.5%), and the gait-vs-skate margin WIDENS vs the bare recipe (not just preserved). Warm-starts from the SAME clean champion checkpoint the loadslip-c1 canary used (not from loadslip-c1's own degraded/unmoved end) -- respec clones its baked --init-from literal path, --init-from-source intentionally NOT passed.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, not a skill-acquisition or behavior-class verdict. PASS if: wandb_history shows env/walk_tangent_contact_vel_mean_m_s (or the per-tick charge magnitude) trending down while reward_walk/reward_walk_prog stay flat-to-rising (08-21-aligned), AND a fresh own-pod gate re-eval (DR-0, walk+walk_startjitter, det+sto, n>=24) reads 0 falls / gait_valid all-clear (no new leg-sacrifice vs the 22/24 baseline) with slip/m median MEASURABLY lower than the 5.065 training-diet baseline (not another ~4% wiggle) AND no sign of the known stagea-slip1 belly-flop/crouch exploit (height/pitch/roll stay in the champion's normal band, env/walk_contact_meaningful_feet stays high -- not evading the charge via reduced ground contact). FAIL-STILL-STUCK if slip barely moves again -> escalate past reward-shaping to a structural fix (contact-independent floor-height charge, or accept the champion's slip gap as a hardening-target boundary). FAIL-EXPLOIT if the crouch/reduced-contact pattern reappears at this scale -> needs a contact-independent redesign before a third attempt, not another dose.

