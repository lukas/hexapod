# cw-walkscratch-easy0905-headset-halfgrav-medhead-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T09:56:53+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead-acq1

**wandb_id**: frmzojxo

**hypothesis**: Plain English: the halfgrav 0.5g medium-heading-set (5-way) champion, the foundation source several downstream widen/irr composites are built on, cleared its own 40M ACQ PASS (6/6 det+sto gait_valid, 4/6 startjitter/det just at the majority bar, 0 falls); a +40M own-checkpoint cont40m endurance continuation (80M cumulative) tests whether this foundational source holds at endurance scale, matching the campaign's standard cleanliness-margin-predicts-endurance refill pattern already confirmed on base/widenfwd/irrfwd/abrupt siblings.

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority (>=4/6 walk/det and walk/sto, startjitter panels not worse than the 40M read) with 0 NEW chronic single-leg pattern and 0 falls; HARDENING FAIL if a chronic leg entrenches, falls appear, or gait_valid drops below majority.

**verdict**: HARDENING FAIL, MILD/MARGINAL — a genuine but narrow regression, not a collapse. Parent acq1 (40M) was clean: 22/24 gait_valid, 0 falls/24 across all 4 panels. This cont40m (+40M, 80M cumulative) trips the gate's own pre-registered bright line: walk/sto/0 TERMINATES tilt_roll (roll_peak 31.9deg > the 25deg safety limit, roll_class=fell) — 0 falls -> 1 fall, disqualifying under the gate's explicit '0 falls' HARDENING PASS condition regardless of aggregate count. Aggregate gait_valid stays majority (21/24) with NO new chronic single-leg pattern (sac legs scattered: [4] in det, [2,5]/[4] in startjitter/sto, different legs each time, none repeating) — this is NOT the base-family systemic leg1/4 entrenchment seen on the sibling verdict this cycle. walk_startjitter/sto also regresses vs the 40M read (6/6->4/6), the gate's other explicit 'not worse than 40M' condition. ep_rew_mean still rises every quarter (158->391->455->559) but the pre-registered gate exists precisely to catch a stochastic-mode stability regression reward curves alone would miss (08-21 ruling: this corroborates rather than contradicts — the eval genuinely got measurably worse on a named axis, not just 'looks bad while reward rises'). Net: treat the 40M acq1 checkpoint, not this cont40m, as the champion-grade artifact for the halfgrav-medhead line; do not spend further budget hardening this exact checkpoint. No new repair mechanism warranted for a single non-chronic fall — flag as informative variance (harder combined halfgrav+medhead+extra budget nudges stochastic-mode roll margin) for whoever next tunes roll-margin/DR interactions on this family.

