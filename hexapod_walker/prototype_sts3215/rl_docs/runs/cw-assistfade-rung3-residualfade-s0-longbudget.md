# cw-assistfade-rung3-residualfade-s0-longbudget

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_FAIL

**created**: 2026-09-06T19:36:26+00:00

**pod**: hexapod-mjx-train-1

**steps**: 6000000

**parent**: cw-assistfade-rung3-residualfade-s0

**wandb_id**: 1nt19pgb

**hypothesis**: Rung-3's 2/2 CANARY FAIL-MECHANISM (both the original pair AND the std-anneal-frac retry, 2/2 seeds each) shows a schedule collision: the residual-blend anneal completes at 1.4M/2M steps and leaves only a 0.6M-step settling window before eval, and the std-anneal-frac=3.0 single-lever fix REFUTED (worse or equal on both seeds, RL_LOG 09-06 19:2x-19:3x). Per the pre-registered fallback (do not repeat std-anneal-frac), this is the OTHER named lever: a longer total step budget with EVERY other lever (blend schedule sched.t1_steps=1.4M, log-std-anneal-frac reverted to the original default 1.0/-3.0, reward stack, random-weight init) byte-identical to the originally-failed parent -- steps 2M->6M (3x) gives a 4.6M-step settling window post-blend instead of 0.6M, AND (since log-std-anneal-frac=1.0 anneals relative to --steps) slows the std anneal's absolute-time rate 3x so std stays much higher through the blend fade-out too, attacking the same schedule-collision root cause via budget rather than the already-refuted frac lever. Seed 0 of the pair.

**gate**: MECHANISM-HEALTH CANARY ONLY (same ignition text as the parent, budget-extended not skill-graded): do not judge skill acquisition, close a behavior/reward class, or require mature gait. Ignition gate (curriculum doc, det+sto held-out, DR-0): sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes. MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set). FAIL if progress stays <0.35, any leg is chronically parked/unloaded, or over_current terminations reappear in the startjitter panel. If this ALSO fails the same way (3rd lever refuted for this rung), the compounding is not a schedule-hyperparameter issue at all and the mechanism itself needs re-examination, not another schedule tweak.

**verdict**: Longer-budget rung-3 lever FAILS like its s1 twin -- closes rung 3's budget fork 2/2, not a partial pass. Held-out gate: walk/det progress_ratio 0.274 (below the 0.35 bar, contra the earlier 'closer than any prior lever' read once the actual gated-mode number is checked against the bar itself, not just relative to worse siblings), gait_valid FALSE with leg-5 chronically sacrificed in every episode (duty_cycle e.g. [0.24,0.92,0.76,0.88,0.25,1.0], swing_count leg5=0), and EVERY walk/det episode terminates identically via over_current at forward_dist_m=0.024 (near zero net translation) with roll_class=fell. Frame strip (walk_det_0_sheet.png) confirms: body stays essentially planted across all 6 sampled frames, legs shuffling in place, until the over_current cutoff at the last frame -- a stall, not real walking, despite this being the 'best of the grid' by relative comparison. startjitter/det crossing 0.48 progress on its own submode does not override the gated primary mode's clean fail. Root cause: this is the same schedule-collision-driven residual-blend handover failure as every other rung-3 lever (stdslow x2, latehandover x2, now longbudget x2) -- 3x the budget bought a marginally less-bad stall, not a working gait. Rung 3 (bounded residual fade from a fading scripted reference) is now CLOSED at the behavior level across all 3 named schedule/budget levers (6 arms, 2 seeds each) with zero clean passes. Per the track's own ladder rule, next licensed step is either (a) a genuinely new reward mechanism for rung 2/3's flat-speed-vs-command and stall pathologies (not another schedule/budget tweak) or (b) retreat one further rung -- both are unscoped design work, not a same-cycle relaunch.

