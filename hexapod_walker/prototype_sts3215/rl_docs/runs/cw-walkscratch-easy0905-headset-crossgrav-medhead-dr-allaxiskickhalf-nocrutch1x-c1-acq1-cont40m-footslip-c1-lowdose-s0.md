# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-footslip-c1-lowdose-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T20:15:51+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-footslip-c1

**wandb_id**: gyq6xv2x

**hypothesis**: Plain English: does the same per-tick contact-conditioned slip charge actually reduce sliding once its dose is scaled to match the rest of the reward, instead of dominating/swamping it 5x over? footslip-c1 (k=35) FAILED with env/walk_tangent_contact_vel_mean_m_s completely flat (0.159-0.161 m/s) across its whole 2M run -- but per-channel wandb_history decomposition (this cycle) shows env/reward_foot_slip_tangent averages -4.2 to -4.3/tick while EVERY OTHER walk reward channel combined (reward_walk + freeprog_pen + prog) sums to only +0.23/tick net: the charge outweighs the rest of the reward ~5x, a scale fact the bank's synthetic k=20-100 sweep (gait-vs-skate margin only) never checked. Single lever vs footslip-c1: reward.k_foot_slip_tangent 35.0->3.0 (excess~0.145 m/s * k=3 ~= -0.4/tick, same order as the other walk channels), everything else byte-identical (foot_slip_contact_n=2.0, deadband_m_s=0.015, max_m_s=0.25, walk_loadslip_gate off, same warm-start champion checkpoint via the cloned --init-from, no --init-from-source). Seed 0 of a 2-seed pair (s1 companion).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (dose-scale probe, not a skill/behavior-class verdict). PASS-partial (worth a dose-SCHEDULE follow-up, not yet a lineage pass): env/walk_tangent_contact_vel_mean_m_s trends measurably down from its ~0.16 m/s start (even partially, e.g. -10%+) while reward_walk/reward_walk_prog stay flat-to-rising and 0 falls / no new leg-sacrifice on a fresh own-pod gate re-eval (DR-0, walk+walk_startjitter, det+sto, n>=24) -- this would mean the mechanism itself is NOT stuck, only the k=35 dose was structurally too large relative to the rest of the reward, and the right next recipe is a small-to-larger dose SCHEDULE, not a bigger single k. FAIL-STILL-STUCK if the metric is AGAIN flat even at 1/12th the dose -- this would rule out scale-mismatch and confirm the earlier closure's read (needs a genuinely different, contact-independent sensing mechanism, or accept the slip gap as this rung's hardening boundary). FAIL-EXPLOIT if walk_contact_meaningful_feet collapses toward 0 (crouch/reduced-contact evasion) or height/pitch/roll leave the champion's normal band.

