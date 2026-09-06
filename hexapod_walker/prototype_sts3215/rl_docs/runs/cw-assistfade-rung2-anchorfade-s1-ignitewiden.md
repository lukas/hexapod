# cw-assistfade-rung2-anchorfade-s1-ignitewiden

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL - STILL-IGNORES

**created**: 2026-09-06T17:08:01+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s1-reseed8m-gatefix

**wandb_id**: sk43wm2m

**hypothesis**: Twin of s0-ignitewiden (same one-cycle batch, seed 1): does the speed-band-ignoring pathology trace to single-fixed-speed habituation baked in during ignition itself, not insufficient hardening-stage exploration (exploration magnitude closed 3/3 this cycle)? Same single lever: widen goal.walk_speed_min_m_s/max_m_s to 0.04-0.08 m/s from step 0 of the full anchor-fade ignition anneal (unchanged reward stack, unchanged original 2M seed checkpoint via the untouched --init-from), vs the pinned-0.06 reseed8m-gatefix ignition this seed already passed cleanly.

**gate**: Same as s0-ignitewiden: PASS needs both the standard ignition bar (anneal latches, gait_valid/falls/progress_ratio clean) AND achieved speed covarying with the per-episode commanded value across the widened band. FAIL-NO-IGNITION if the widened band itself blocks ignition; FAIL-STILL-IGNORES if ignition passes but speed still clusters flat -- closes ignition-habituation too, escalate to an explicit speed-tracking/stride-amplitude reward mechanism next.

**verdict**: Result: ignition mechanism healthy (bc_anchor_anneal/gate_pass latches at 1.03M, bc_coef ramps 3->0 by ~5.06M, holds 0 through the 8M budget) and the held-out gate is clean (gait_valid 6/6 all 4 modes, 0 falls/terms, sacrificed_legs=[] every episode, video confirms six legs cycling not static) -- but per-episode speed_mean_m_s clusters 0.036-0.043 m/s across a commanded 0.035-0.066 m/s spread in both walk/det and walk/sto (e.g. cmd=0.0352->speed=0.041, cmd=0.0659->speed=0.043), zero visible covariance, the identical fingerprint as -v2/-lsd2/-explore2/-s0-freshband. progress_ratio also runs below the 0.35 ignition bar in most episodes (walk/det med 0.42, walk/sto med 0.28) and slip_per_m 3.6-5.8 sits above the 2.9 teacher band -- worse on both counts than sibling s0-freshband. Why: this is the 4th and final habituation-dose arm (widened band from step 0 + baked prior single-speed init-from, the opposite corner from s0-freshband's true-random-init) testing whether SOME form of habituation (init or reward-shape) explains the flat-speed pathology; it reproduces anyway. Combined with s0-freshband (FAIL-HABITUATION-NOT-THE-CAUSE, closed 09-06), this closes the ignition-habituation hypothesis family 2/2 on the widened-band structural test (on top of exploration-magnitude closed 3/3 at -v2/-lsd2/-explore2) -- 6 total arms now show the same fingerprint under every combination of init/habituation/exploration tried. Next: per the pre-registered gate text and STATUS Next#0, escalate to an explicit stride-amplitude/speed-tracking reward term (semantics-bank first) since no per-step lever currently prices achieved speed against the commanded value beyond the saturating course-income kernel; do not fund a 5th same-mechanism speed-band arm on this recipe.

