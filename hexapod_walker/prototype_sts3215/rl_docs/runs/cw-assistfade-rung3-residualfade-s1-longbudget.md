# cw-assistfade-rung3-residualfade-s1-longbudget

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T19:40:02+00:00

**pod**: hexapod-mjx-train-0

**steps**: 6000000

**parent**: cw-assistfade-rung3-residualfade-s1

**wandb_id**: j8l8va6k

**hypothesis**: Rung-3's 2/2 CANARY FAIL-MECHANISM (both the original pair AND the std-anneal-frac retry, 2/2 seeds each) shows a schedule collision: the residual-blend anneal completes at 1.4M/2M steps and leaves only a 0.6M-step settling window before eval, and the std-anneal-frac=3.0 single-lever fix REFUTED (worse or equal on both seeds, RL_LOG 09-06 19:2x-19:3x). Per the pre-registered fallback (do not repeat std-anneal-frac), this is the OTHER named lever: a longer total step budget with EVERY other lever (blend schedule sched.t1_steps=1.4M, log-std-anneal-frac reverted to the original default 1.0/-3.0, reward stack, random-weight init) byte-identical to the originally-failed parent -- steps 2M->6M (3x) gives a 4.6M-step settling window post-blend instead of 0.6M, AND (since log-std-anneal-frac=1.0 anneals relative to --steps) slows the std anneal's absolute-time rate 3x so std stays much higher through the blend fade-out too, attacking the same schedule-collision root cause via budget rather than the already-refuted frac lever. Seed 1 of the pair.

**gate**: MECHANISM-HEALTH CANARY ONLY (same ignition text as the parent, budget-extended not skill-graded): do not judge skill acquisition, close a behavior/reward class, or require mature gait. Ignition gate (curriculum doc, det+sto held-out, DR-0): sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes. MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set). FAIL if progress stays <0.35, any leg is chronically parked/unloaded, or over_current terminations reappear in the startjitter panel. If this ALSO fails the same way (3rd lever refuted for this rung), the compounding is not a schedule-hyperparameter issue at all and the mechanism itself needs re-examination, not another schedule tweak.

**verdict**: CANARY FAIL - MECHANISM (longer-budget lever, 2M->6M, refuted on seed 1). Held-out ignition gate (logs/ckpt_eval/cw_assistfade_rung3_residualfade_s1_longbudget_gate/report.json, dr=0.0, n=24): progress_ratio med 0.10 (walk/det), 0.09 (walk/sto), 0.10 (startjitter/det), 0.14 (startjitter/sto) -- every mode 2.5-3.5x short of the 0.35 bar, no submode median comes close (unlike the s0 twin, where startjitter/det crossed 0.48 -- this seed shows no such partial pass). walk/det+sto gait_valid mostly True but paddle-creep (slip/m 17-18, fwd only ~0.05-0.06m/10s, contact-sheet-consistent with the sibling latehandover arms' in-place shuffle). walk_startjitter reintroduces chronic single-leg sacrifice + over_current in 2/6 det and 2/6 sto (one episode, sto/1, spikes to prog 0.73 but that is the SAME episode that sacrifices legs [2,5] and terminates over_current -- a transient burst before failure, not sustained translation, so not read as a partial pass). Reward quarters [146.5,76.3,32.7,31.3] are a clean Q1->Q4 DECLINE (same collapse-with-more-budget shape as the s0 twin's own quarters), so the 08-21 continue-reading does not apply here either. Net: this seed cleanly closes the budget lever the way stdslow/latehandover already closed theirs -- but its s0 twin (cw-assistfade-rung3-residualfade-s0-longbudget) shows a genuinely different, ambiguous partial-improvement shape (prog up to 0.48 on one submode, DIG-IN flagged, left unverdicted) that this result does NOT resolve on its own -- the pair reads 1 clean FAIL + 1 ambiguous, not 2/2 clean FAIL, so do NOT treat 'longbudget' as fully closed until s0's DIG-IN lands. All 4 of this rung's named single-lever fallbacks (stdslow x2, latehandover x2, longbudget-s1) are now FAIL; only s0-longbudget remains open.

