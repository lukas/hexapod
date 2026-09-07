# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenrear180

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-07T20:02:41+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-acq1

**wandb_id**: xz2k7jzj

**hypothesis**: Plain English: widen8 (adding all 3 new rear/diagonal-rear headings +-135/180deg at once to the base 5-way set) closed ACQ FAIL 3/3 seeds with a NEW chronic front-pair (legs 0/5) sacrifice, generalizing the L1/L4 middle-pair pathology to a heading-DEPENDENT redundant-pair rule. CURRENT_TRUTHS (09-07 ~09:5x) explicitly licenses a heading-bisected NARROWER widen (not the full 8-way jump) without waiting for the still-unbuilt heading-conditioned role-aware mechanism. This tests the narrowest possible step: add ONLY ONE new heading (180deg, straight-back, the single most extreme/pure rear direction and the most different from every already-trained heading) to the same seeds own already-ACQ-passed 40M crutch-off checkpoint, 2M canary, single axis (goal.walk_heading_set 5-way -> 6-way), matching widen8s own precedent tier/init exactly.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM/BEHAVIOR CANARY (2M, matches widen8 tier): PASS if gait_valid stays majority (>=4/6 walk/det) with 0 falls and NO chronic (repeated across episodes) leg-0 or leg-5 sacrifice -- if true, a single new rear heading does NOT reproduce widen8s fingerprint, supporting an incremental one-heading-at-a-time widening strategy that avoids needing the role-aware mechanism yet. FAIL if the SAME chronic front-pair (legs 0/5) sacrifice reproduces even from just this one heading -- if true, the pathology is triggered by rear-heading CONTENT itself (not by training multiple new headings at once), so incremental widening cannot dodge it and the role-aware mechanism becomes mandatory before any further heading-set expansion. Either outcome is informative and closes/advances the widen8 fork named in CURRENT_TRUTHS 09-07 ~09:5x.

**verdict**: CANARY FAIL - MECHANISM: completes the widenrear180 trio 3/3, matching s1/s2 exactly. Adding ONLY the 180deg (straight-back) heading to the ACQ-passed 5-way base reproduces widen8's chronic front-pair(legs 0/5) sacrifice at just 2M steps. Evidence: walk/det gait_valid 3/6 (below the required >=4/6 majority; fails ep0/1/5, sac=[0] on ep0+ep5), walk/sto 5/6 (sac=[3] ep1), walk_startjitter/det clean 6/6, walk_startjitter/sto 4/6 (sac=[5] ep2, sac=[0] ep3); 0 falls/24. s1/s2 (independent seeds) land on the IDENTICAL per-episode fingerprint at the SAME fixed-eval-RNG indices -- rules out seed noise, confirms the pathology is heading-content-driven. Consistent with the ~11:5x cycle's own single-seed 40M ACQ-depth widenbis180 FAIL on s0 (same fingerprint, deeper budget). Why: the redundant leg-pair for a rear-ish command is heading-dependent (front pair, not the forward-command L1/L4 middle pair); no per-tick price mechanism (11 already exhausted) can out-compete a genuinely cheaper stable 4-leg gait. What's next: CLOSES the widen8 fork's 'incremental one-heading-at-a-time' escape 3/3 seeds -- the heading-conditioned role-aware mechanism is now unambiguously mandatory before any further walk_heading_set expansion. Built+banked this cycle as a heading-UNIFORM per-leg minimum-duty TERMINATION (safety.walk_leg_duty_terminate_s, walk_task.py/sim_env.py, WALKCURR_LEGDUTY_TERM bank 4/4 green) instead of another per-tick price -- termination, not price, is the validated pattern from hold_min_load_terminate/walk_idle_terminate for this exact absorbing-state-beats-price class. 4 repair canaries launched this cycle (widen8-acq1 x3 seeds + widenbis180 x1, --init-from-source, safety.walk_leg_duty_terminate_s=4.0/floor=0.05/tau=1.0s/grace=3.0s, dedicated reward.walk_leg_duty_terminate_penalty=150) testing whether the termination repairs the already-entrenched sacrifice.

