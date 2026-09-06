# cw-walkscratch-easy0905-headset-halfgrav-irr2-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL (HARDENING FAIL) — the halfgrav irr-timing composite's leg4 weakness, already visible as a minor 5/24 flag at its own 40M ACQ PASS, consolidates into a real chronic sacrifice by 80M. gait_valid drops materially 19/24 -> 16/24 (parent -> this cont40m); the collapse concentrates in walk_startjitter/sto (5/6 -> 2/6), and leg4 is now the flagged leg in 7 of the 8 sacrificed episodes (was 5/5 at the parent, just fewer of them) with duty_cycle[4] falling to 0.01-0.10 in every flagged episode vs a healthy 0.10-0.27 elsewhere -- a genuine consolidation, not scattered noise on different legs. 0 falls/terminations in all 24 episodes both before and after, slip/m stays in-band (2.1-3.6), and ep_rew_mean keeps rising every quarter (569.5/1055.8/1186.3/1291.7) -- per the 08-21 ruling this would normally license a continue/realign read, but this run's OWN pre-registered gate text names exactly this shape as FAIL ('a leg consolidates into a chronic sacrifice across most episodes') and the campaign has already established this same reward-rises-while-one-leg-entrenches pattern as a genuine duration effect on multiple siblings this cycle-window (headset-base-acq1-cont40m, headset-base-s1c1-acq1-cont40m, headset-halfgrav-medhead-acq1-cont40m) -- this is a 4th corroboration, not a new finding needing dig-in. Video (walk_det_0/3, walk_startjitter_sto_0/1/2) shows clean overall forward translation, no static/frozen pose, no tipping -- hardware-ready: no, not on this consolidating-leg checkpoint past 40M. Treat the 40M headset-halfgrav-irr2-acq1 checkpoint (ACQ PASS, 19/24, leg4 only a minor scattered flag) as the champion for this lineage, not this cont40m. No further irr2 cont40m spend; read the sibling headset-halfgrav-irr-acq1-cont40m (c1 seed, same recipe family) next for a 2-seed read on whether this is composition-wide or seed-specific. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_irr2_acq1_cont40m_gate/report.json vs logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_irr2_acq1_gate/report.json, W&B pf38aqrx.

**created**: 2026-09-06T12:08:56+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr2-acq1

**wandb_id**: pf38aqrx

**hypothesis**: Plain English: does the halfgrav (0.5g) irr-timing composite's SECOND seed (headset-halfgrav-irr, canary c2, testing seed generalization of the same irr-timing mechanism as the irr-acq1-cont40m sibling) stay clean over a SECOND 40M block (80M cumulative, true continuation via --init-from-source)? Its own 40M ACQ read is ACQ PASS with 19/24 gait_valid (4/6 det, 6/6 sto, 4/6 startjitter/det, 5/6 startjitter/sto, 0 falls, scattered leg1/4 flags) -- queued (not launched immediately -- this cycle's 80M-step cap was already spent on the cleaner crossgrav-medhead irrwiden/widenirr pair).

**gate**: PASS/HOLDS if gait_valid stays majority (>=18/24) with 0 falls and no NEW chronic single-leg pattern. FAIL/entrenches if gait_valid drops materially, a fall appears, or a leg consolidates into a chronic sacrifice across most episodes. Read alongside the irr-acq1-cont40m (c1 seed) sibling for a 2-seed endurance generalization read.

**verdict**: 09-06 ~13:1x irr2-acq1-cont40m HARDENING FAIL: leg4 consolidates 5/24->8/24 flagged episodes (gait_valid 19/24->16/24), reward still rising -- 4th corroboration of the base/halfgrav cont40m chronic-leg-entrenchment duration effect this cycle-window; champion stays the 40M acq1 checkpoint.

