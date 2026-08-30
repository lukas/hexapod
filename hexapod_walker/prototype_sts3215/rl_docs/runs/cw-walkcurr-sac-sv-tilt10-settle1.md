# cw-walkcurr-sac-sv-tilt10-settle1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-29T23:41:34+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkcurr-sac-sv-tilt10-s1-r2

**wandb_id**: utmpvz1i

**hypothesis**: Plain English: cw-walkcurr-sac-sv-tilt10-s1-r2 (this cycle, FAIL) showed the codebase's full-default anti-tilt dose (10.0) REVERSES the tilt5 sibling's real dose-response -- deterministic instant tilt_pitch collapse (fwd 0.026m all 6 seeds, gait_valid 0/6), consistent with the charge over-taxing the vulnerable post-spawn recovery window rather than the robot being genuinely worse-balanced (roll_peak actually LOWER than tilt5/tilt2, 5.3 vs ~10deg). This arm tests that root cause directly: IDENTICAL SV diet/seed(1)/algo(SAC)/budget(2M)/dose(10.0) as tilt10-s1-r2, only lever added: reward.tilt_settle_grace_s=0.5 + tilt_settle_ramp_s=0.5 (the charge is free for 0.5s post-spawn, ramps to full over the next 0.5s -- WALKCURR_SV_TILT_SETTLE bank green, 4/4, default-off bit-exact + ranking intact at dose 10.0 with the window on). Fresh 2M run (SAC has no --init-from support, so this cannot be a warm-started continuation of tilt10-s1-r2 -- the only valid way to add a reward lever to this lineage). Prediction-if-true: the settle window RESCUES dose 10.0 back to at least tilt5's level (fwd med >=0.05m, gait_valid >=4/6) or better (dose 10.0's stronger steady-state charge should, once past the window, hold the robot more upright than dose 5.0 for the rest of the episode) -- confirms the over-pricing-the-recovery-window diagnosis and argues for making the settle window a standard companion to any tilt dose >=5.0. Prediction-if-false: still deterministic/near-instant fall despite the free window -- the dose-10 basin is not a settle-window problem (e.g. the policy's own network/exploration already collapsed to a bad local optimum this dose pushed it into, independent of when the charge bites) -- abandon dose 10.0 outright, standardize future work on dose 5.0 (+/- the settle window, per the sibling arm's own read) instead.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 2M, same harness. PASS/continue-worthy: fall rate below 24/24 OR forward_dist_m median clearing ~0.06m. Read against BOTH siblings: recovers to >= tilt5's own no-window level (fwd med ~0.05-0.06m, gait_valid >=4/6) = the settle-window diagnosis is confirmed and dose 10.0 is viable again with it; stays at/below tilt10-s1-r2's own deterministic-collapse level (fwd ~0.03m, gait_valid 0/6) = dose 10.0's basin is not fixed by timing alone, drop it and keep dose 5.0+window as the frontier.

**verdict**: FAIL -- the settle window does NOT rescue dose 10.0 on its primary (walk/det) mode: fwd_dist stays at 0.028m median, gait_valid 0/6, identical to tilt10-s1-r2's own deterministic-collapse floor (0.026m, 0/6) -- the timing-of-charge diagnosis is falsified for the deterministic evaluation surface. Other sub-modes (walk/sto gait_valid 6/6, walk_startjitter/sto 4/6) show partial stepping recovery, but this tracks with SAC's inherent stochastic-rollout exploration noise (present in every sto pass regardless of the settle mechanism) rather than a settle-window effect specifically -- walk/det, the deterministic read with no exploration noise to confound it, is the clean test and it shows no rescue. Pooled 24-episode fwd_med 0.029m/gait_valid 12/24 (up from tilt10-s1-r2's 1/24) is driven entirely by those noisy sto passes. ep_rew_mean quarters [157.3,123.9,143.7,135.6] -- noisy/declining, not rising: aligned FAIL per 08-21. Evidence: logs/ckpt_eval/cw_walkcurr_sac_sv_tilt10_settle1_gate/report.json. Combined with the tilt5-settle1 sibling, this CLOSES the settle-window mechanism at both doses tested -- SAC-SV branch (7 arms total: s0/s1/budget10m/tilt2/tilt5/tilt10/tilt10-r2/tilt5-settle1/tilt10-settle1) exhausts fallback (a) of the operator's ladder.

