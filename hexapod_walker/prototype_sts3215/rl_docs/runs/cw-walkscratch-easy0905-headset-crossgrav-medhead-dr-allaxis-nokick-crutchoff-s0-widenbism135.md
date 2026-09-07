# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbism135

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-07T10:37:00+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8

**wandb_id**: c3hqpdus

**hypothesis**: Plain English: same bisection as arm 1 (see widenbis135), arm 2/3: add ONLY -135deg (the mirror rear-diagonal heading) to the ACQ-passed 5-way base, same s0 checkpoint/seed/budget/recipe. Isolates whether the LEFT rear-diagonal alone (vs. the right one or straight-back) drives the front-pair[0,5] chronic-sacrifice shortcut widen8-acq1 showed 3/3. Prediction-if-true: chronic front-pair (or similar) sacrifice reappears by 40M. Prediction-if-false: panel stays clean near s0-acq1's 21/24 baseline -- -135deg alone is not sufficient.

**gate**: PASS (heading exonerated) if 0 falls/24 AND gait_valid>=19/24 AND no chronic single-leg/pair sacrifice absent from s0-acq1's own clean panel. FAIL (heading implicated) if a chronic front-pair[0,5]-style (or any new persistent single-leg) sacrifice reappears, matching widen8-acq1's fingerprint.

**verdict**: Adding ONLY -135deg (one new rear-diagonal heading, mirror of the PASSing +135 sibling) to the ACQ-passed 5-way base breaks badly at full 40M ACQ depth -- this heading is IMPLICATED alone, no interaction with the other two needed. Evidence: 2 real falls (TERM tilt_roll, walk_startjitter/det ep3 and walk_startjitter/sto ep5) plus gait_valid drops to 18/24 (vs this seed's own clean acq1 baseline 21/24) via a NEW chronic leg-0 sacrifice that spreads into walk/det (3/6, sac[0] or sac[0,3] in 3 of 6 episodes -- baseline was clean 6/6 here) and walk_startjitter/det (baseline clean 6/6, now 4/6). Video (walk_det/0 contact sheet) shows the robot barely translating across frame while the commanded-direction arrow rotates through different headings each frame -- a spin/skate-in-place pattern, not directed walking, consistent with the chronic leg-0 sacrifice. Why: this is the FAIL half of the widen8 heading bisection -- confirms the front-pair-style sacrifice is HEADING-dependent and does NOT require combining multiple new headings; -135deg alone is sufficient to trigger it (unlike its mirror +135, which passed clean). This resolves the bisection's open question decisively: it is NOT a >=2-heading interaction effect, it is a per-heading vulnerability that only the +135 arm avoided. Note: this run initially received a stale mechanical SEED-PRUNED auto-verdict written before its gate eval had landed (the run had actually already FINISHED naturally at 40,370,176 steps) -- this verdict supersedes that placeholder with the real post-eval science read. What's next: do not relaunch -135 alone or in any wider set without the still-unbuilt role-aware/support-margin reward mechanism (CURRENT_TRUTHS 'Walkcurr Reward Mechanisms' -- 4 independently-designed price-based mechanisms already exhausted on the sibling middle-pair pathology).

