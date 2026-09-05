# cw-walkscratch-easy0905-headset-base-medhead2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-05T19:15:54+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-medhead2-c1

**wandb_id**: 47j1zemx

**hypothesis**: Second-seed medium-heading (5-way, 0/+-45/+-90deg) acquisition on the base(1g) family: headset-base-medhead2-c1's own 2M canary already CANARY PASSED (v_along clears noise floor, 18/24 harness gait_valid, no chronic single-leg sacrifice), warm-started from a DIFFERENT base champion (headset-base-acq1) than the first-seed acq1 continuation (which used medhead-c1, warm-started from s1c1-acq1). This gives it the full 40M budget to confirm the medium-heading rung acquires cleanly from a second independent seed, mirroring headset-base-medhead-acq1's template exactly.

**gate**: Acquisition milestone at own physics + medium heading set: 20s held-out episodes across all 5 headings (0,+-45,+-90deg), >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than reflex-stop. PASS (2nd seed) closes the medium-heading rung's acquisition-scale seed-robustness confirmation at n=2 and licenses re-attempting a wider set as the next widening rung; FAIL means the rung is champion-specific even at 40M budget and the acq1 (first-seed) result must be weighted more heavily before widening further.

**verdict**: 5-way medium-heading 40M continuation FAILs on the base(1g) family, a 4th independent confirmation of the same leg-1/4 favoritism entrenching under any added heading axis. Evidence: DR-0 gate harness gait_valid 0/6 walk/det (leg 1 or 4 sacrificed EVERY episode), 6/6 walk/sto, 0/6 walk_startjitter/det (legs [1,4] or [1] every episode), 2/6 walk_startjitter/sto -- 8/24 total, well under the campaign's adopted >=12/24 majority bar (same bar used for s0c1-acq1/medhead-acq1/irr-acq1 FAILs). Frame strip (walk_det_1_sheet.png) confirms one leg held rigid/planted the whole clip while the other five cycle. 0/24 falls, slip 3.5-4.5 (above 2.9 teacher band), fwd speed fine (2.15m/20s median). Reward is still climbing (quarters -238,-79,133,366) but per the base family's own established precedent (medhead-acq1, s0c1-acq1, irr-acq1 all FAILed with reward also still climbing) this is treated as adequate-budget-doesn't-move-the-gate, not a license to continue -- the base(1g) leg-1/4 habit is now confirmed structural across 4 independent 40M seeds/champions at this rung. Why: same root cause already diagnosed for this family (marginal-leg pricing absent; duty_gate/noise levers already closed 09-05). Next: no further base-family medium-heading seed at this recipe; the open thread is the halfgrav sibling (own verdict) and the still-unbuilt per-leg-utilization mechanism design.

