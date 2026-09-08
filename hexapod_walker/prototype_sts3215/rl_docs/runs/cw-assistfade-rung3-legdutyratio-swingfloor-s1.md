# cw-assistfade-rung3-legdutyratio-swingfloor-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-08T12:25:54+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-assistfade-rung3-legdutyratio-s1

**wandb_id**: e02k5rqc

**hypothesis**: Seed-1 replicate of the swingfloor-s0 canary launched this cycle: does pairing the assistfade rung3 duty-ratio charge with the walkcurr-proven swing-count floor fix the bare charge's inability to target a fully-planted no-swing leg? Single lever vs the matched bare-charge cw-assistfade-rung3-legdutyratio-s1 sibling (CANARY FAIL - MECHANISM, leg [0,5] sacrificed): only reward.walk_leg_duty_ratio_swing_min_count=2.0 / _swing_window_s=4.0 added, otherwise byte-identical. Batched with -swingfloor-s0 for an n=2 read per the operator's batch-launch guidance rather than serializing one seed per cycle.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as -swingfloor-s0's own gate, matched to this seed's own bare-charge sibling report.json: telemetry activation check, zero new falls vs the s1 bare-charge sibling, and per-leg duty narrowing for legs [0,5] without new slip/current regression to CONTINUE; statistically-indistinguishable duty or any new regression is FAIL-MECHANISM.

**verdict**: CANARY FAIL - MECHANISM: swing-count-floor lever (>=2 qualifying swings/4s window ratio credit) added to the matched bare-charge cw-assistfade-rung3-legdutyratio-s1 sibling (same seed1/budget/blend-schedule, only swing-floor keys added). Telemetry engages post-grace (walk_leg_duty_ratio_shortfall/reward_walk_leg_duty_ratio finite from step~396), so not an infrastructure miss. But per-leg duty shows NO narrowing on the gate's own target legs [0,5]: leg5 stays fully planted (duty_cycle=1.0, swing_count=0) in every walk/det AND walk/sto episode (6/6 each), identical to the bare sibling; leg0's duty actually falls slightly (walk/det 0.32 vs sibling 0.45; walk/sto 0.40 vs sibling 0.48) instead of narrowing toward the peer band. gait_valid totals move only 2/24 (sibling) -> 3/24 (this run), noise not repair, while walk/sto picks up a NEW over_current termination (0->1) and walk/det slip worsens (17.02->18.31 med). ep_rew_mean matches the bare sibling through 3 quarters (101.6/160.3/184.7 vs 101.4/161.0/196.9) then collapses far harder in the settling window (final quarter -943.8 vs sibling's 95.4), the same genuine-regression fingerprint s0's twin already showed, not an 08-21 rising-reward case. Matches s0's verdict on this lineage: swing-floor does not repair rung3's chronic leg5 sacrifice and makes leg0 worse, not better. No further rung3+swing-floor budget on this seed; both s0 and s1 of this lever are now closed FAIL. Evidence: logs/ckpt_eval/cw_assistfade_rung3_legdutyratio_swingfloor_s1_gate/report.json vs cw_assistfade_rung3_legdutyratio_s1_gate/report.json; W&B e02k5rqc.

