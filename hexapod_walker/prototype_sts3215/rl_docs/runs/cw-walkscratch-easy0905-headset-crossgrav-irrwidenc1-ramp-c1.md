# cw-walkscratch-easy0905-headset-crossgrav-irrwidenc1-ramp-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_FAIL

**created**: 2026-09-06T02:06:16+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c1-acq1

**wandb_id**: mkjeg5et

**hypothesis**: Plain English: this cycle's own irrwidenc1-abrupt-c1 CANARY FAIL (jitter-first widen+irr composite champion, abrupt 1g jump: walk/det collapses from the parent's majority 5/6 to minority 3/6, walk_startjitter/det 6/6->4/6, 0 falls) is the first clean negative in the cross-gravity-transfer generality sweep, after 2/2 clean PASS on the medhead recipe at BOTH abrupt and gradual-ramp transition speeds. Does a GRADUAL gravity ramp (0.5g->1.0g linearly over the first 1M of a matched 2M budget, identical sched.key=ease.gravity_scale engine used for medhead-ramp-c1) rescue this specific composite the same way it was equally clean as abrupt for the simpler medhead recipe, or does the composite's det-mode degradation persist regardless of transition speed (implicating something about the composite itself -- e.g. reversal-heading commands plus 1g torque limits -- rather than shock speed)?

**gate**: DISCOVERY (2M), ramped-gravity arm on the jitter-first widen+irr composite. PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det AND walk_startjitter/det with no chronic single-leg (<0.10 duty every episode) sacrifice -- would show the composite's abrupt-transfer degradation was a transition-shock artifact, not intrinsic, reopening the composite recipe for a 40M acquisition continuation the same way medhead's ramp variant did. FAIL/INFORMATIVE-NEGATIVE if walk/det or walk_startjitter/det stays minority or the same leg[1,3,4] pattern recurs -- would show transition speed does NOT explain the composite's weaker transfer (unlike medhead, where abrupt and ramp read equivalently well), narrowing the causal question toward the composite's reversal-heading commands or composition order itself rather than shock speed, and closing gravity-ramp as a repair lever for THIS recipe specifically. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: FAIL - INFORMATIVE-NEGATIVE, closes gravity-ramp as a repair lever for the jitter-first widen+irr composite. Result: gradual 0.5g->1.0g ramp (over first 1M of 2M) reproduces the abrupt sibling's own failure almost exactly -- aggregate gait_valid 19/24 (walk/det 3/6 minority, sac=[4],[4],[3]; walk/sto 6/6 clean; walk_startjitter/det 4/6, sac=[1],[1]; walk_startjitter/sto 6/6 clean), 0 falls/terminations in all 24 episodes. This lands squarely in the gate's own pre-registered FAIL branch text verbatim ("walk/det or walk_startjitter/det stays minority or the same leg[1,3,4] pattern recurs") -- irrwidenc1-abrupt-c1 (this same cycle's sibling read) showed walk/det 3/6 with leg[3,4] flags and walk_startjitter/det 4/6, i.e. the SAME minority result at the SAME magnitude regardless of transition speed. Video (walk_det_0, sac=[4]) confirms genuine six-leg-ish body translation, not a paddle/freeze -- a gait-quality mechanism issue, not a safety collapse. Several episodes show slip_per_m 10-200x the teacher band (walk/sto/3 slip=201, walk_startjitter/det/2 slip=156) but duty_cycle for the flagged episode is balanced (0.38-0.41 all six legs) -- confirmed as the already-documented reversal-heading low-progress-denominator artifact, not a new defect. Why: transition speed is now ruled out as the causal variable (2/2 abrupt+ramp read equivalently poorly, mirroring how 2/2 abrupt+ramp read equivalently WELL for the simpler medhead recipe) -- the differentiator is the composite itself (reversal-heading commands and/or widen+irr composition order), not shock speed. What's next: the natural n=2-seed check for this exact composite (crossgrav-irrwidenc2-abrupt-c1, off the independently-seeded healthy ACQ-PASS headset-halfgrav-irrwiden-c2-acq1 champion) is ALREADY RUNNING (launched by a concurrent cycle, verified train-10) -- if it also fails with the same leg pattern, this closes the composite-recipe-fragile hypothesis at n=2; if it passes, irrwidenc1's own FAIL was seed-specific. No further ramp-vs-abrupt spend warranted on this recipe.

