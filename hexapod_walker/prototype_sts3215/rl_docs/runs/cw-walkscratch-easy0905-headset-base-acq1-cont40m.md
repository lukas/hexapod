# cw-walkscratch-easy0905-headset-base-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T10:09:12+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-acq1

**wandb_id**: kevdolja

**hypothesis**: Plain English: does the base(1g)/heading-generalization flagship champion (headset-base-acq1, clean ACQ PASS at 40M) hold up under a 2nd 40M endurance helping (80M cumulative), following the campaign's cleanliness-margin-predicts-endurance precedent (9 prior cont40m confirmations)? This is the 1g base family's FIRST cont40m -- all prior cont40m reads have been crossgrav/halfgrav sources.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 80M cumulative with no NEW chronic single-leg pattern and 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show base(1g)'s own known leg-1/4 structural attractor (already documented in CURRENT_TRUTHS) resurfaces under more budget even on an already-clean champion.

**verdict**: HARDENING FAIL — confirms (3rd/3rd seed) the base(1g) family's leg1/4 sacrifice is a training-DURATION effect, not seed-specific. Parent acq1 (40M) was already at its documented fingerprint: 18/24 gait_valid, clean walk/det+walk/sto (6/6 each), sacrifice confined entirely to walk_startjitter/det (0/6, legs 1/4). This cont40m (+40M, 80M cumulative) drops to 14/24: the chronic leg NOW ALSO invades the previously-perfect walk/det (6/6->3/6, sac legs [1]/[4]) and walk_startjitter/sto degrades (6/6->4/6); walk_startjitter/det only partially recovers (0/6->1/6), net redistribution not net gain. ep_rew_mean still rises every quarter (519->943->1066->1239) but the pre-registered HARDENING gate's own chronic-leg-entrenchment FAIL clause is squarely met regardless of reward trend (08-21 ruling: this is corroboration of an already-closed pathology, not reward/eval misalignment needing more budget or a reward fix). Together with headset-base-s1c1-acq1-cont40m (11:3x, same fate at 80M) and headset-base-acq1 itself hardening solo per CURRENT_TRUTHS, this closes the base(1g) 40M+ HARDENING question 3/3: every base-gravity seed given enough budget converges on the leg1/4 attractor. No new repair mechanism warranted (6 reward-shaping levers already closed on the sibling crossgrav-medhead-dr sde/gSDE line for the same class of pathology). Downweight base(1g) 40M+ checkpoints from champion contention; standardize on the halfgrav(0.5g) sibling family (independently clean through irr-timing/medhead/widen/cont40m axes) for any downstream full-realism composite or champion pick.

