# cw-walkscratch-easy0905-headset-crossgrav-irrwidenc1-ramp-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:06:16+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c1-acq1

**wandb_id**: mkjeg5et

**hypothesis**: Plain English: this cycle's own irrwidenc1-abrupt-c1 CANARY FAIL (jitter-first widen+irr composite champion, abrupt 1g jump: walk/det collapses from the parent's majority 5/6 to minority 3/6, walk_startjitter/det 6/6->4/6, 0 falls) is the first clean negative in the cross-gravity-transfer generality sweep, after 2/2 clean PASS on the medhead recipe at BOTH abrupt and gradual-ramp transition speeds. Does a GRADUAL gravity ramp (0.5g->1.0g linearly over the first 1M of a matched 2M budget, identical sched.key=ease.gravity_scale engine used for medhead-ramp-c1) rescue this specific composite the same way it was equally clean as abrupt for the simpler medhead recipe, or does the composite's det-mode degradation persist regardless of transition speed (implicating something about the composite itself -- e.g. reversal-heading commands plus 1g torque limits -- rather than shock speed)?

**gate**: DISCOVERY (2M), ramped-gravity arm on the jitter-first widen+irr composite. PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det AND walk_startjitter/det with no chronic single-leg (<0.10 duty every episode) sacrifice -- would show the composite's abrupt-transfer degradation was a transition-shock artifact, not intrinsic, reopening the composite recipe for a 40M acquisition continuation the same way medhead's ramp variant did. FAIL/INFORMATIVE-NEGATIVE if walk/det or walk_startjitter/det stays minority or the same leg[1,3,4] pattern recurs -- would show transition speed does NOT explain the composite's weaker transfer (unlike medhead, where abrupt and ramp read equivalently well), narrowing the causal question toward the composite's reversal-heading commands or composition order itself rather than shock speed, and closing gravity-ramp as a repair lever for THIS recipe specifically. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

