# Zero-GPU scoping probe: does the lower-role champion's action
# distribution collapse during the terminal HOLD phase? NO -- decisive
# null, closes the "exploration-starvation" mechanism class before any
# GPU spend. (2026-10-04, idle-kick refill cycle)

## Plain-English summary
`lowerrole_terminal_support_forensics_2026-10-02/SUMMARY.md` left two
UNSCOPED candidate ideas for closing the lower role's residual
~24-28% composed over_current rate (walkcurr/STATUS.md Next 1): a
hold-phase-isolated curriculum (built+tried as `goal.lower_hold_only_
frac`, now CLOSED -- catastrophic regression, 0/36 at the extreme
dose) and a floor/count-style stance-width reward (built+tried as
`reward.k_stance_count`, now CLOSED -- same tilt-destabilization
family as `k_load_even`/`k_load_rotate`). Both of that forensics doc's
own named candidates are now closed. Before inventing a THIRD, bigger,
unbuilt idea -- boosting the SAC policy's exploration specifically
during the ~9 s terminal hold window, on the theory that the policy's
entropy collapses once it finds the 2-leg (L2+L5) support config and
never samples an alternative again -- this cycle checked the premise
cheaply first, the same discipline the standwalk per-leg-unload item
used (CPU-only preflight before any canary spend).

## Method
New read-only diagnostic, `rl_move/sim/probe_lower_hold_action_std.py`
(+ mechanics-only test, no checkpoint dependency per RESEARCH_RULES
"Tests" rule 4). Loads the standing lower-role champion (`drramp-acq1
s0`, unchanged, no retrain), rolls out 18 `lower`-only episodes from a
clean plant reset (randomize=False, matching the registered composed
gate's own env construction), deterministic actions (matching the
gate's "direct" det arm) -- but at every tick also queries the SAC
actor's OWN `get_action_dist_params` for the pre-squash Gaussian std
(the policy's modeled uncertainty, not the realized action noise).
Reports mean std over the DESCENT window (ticks 50-300, i.e. the 5 s
ramp after the 1 s initial hold) vs the TERMINAL-HOLD window (last 2 s
of the 15 s episode), split by pass/fail. ~35 s wall-clock, CPU only,
zero GPU, zero retrain.

## Result: NO collapse -- std stays within ~3% of itself throughout
(n=18, seed=0, 13/18 passed -- consistent with the known ~72% direct
baseline from a clean-plant reset rather than the composed-handoff
start state the registered gate uses)

| window | passed episodes | failed episodes |
|---|---|---|
| descent (ramp) | 0.456 | 0.466 |
| terminal hold (last 2s) | 0.445 | 0.445 |

The policy's own stochastic head reports essentially the SAME action
std during the converged terminal hold as during the active descent
ramp -- no collapse toward determinism, and no detectable difference
between episodes that ultimately pass vs fail. (Raw per-episode JSON:
`/tmp/lower_hold_std_champ.json`, rerunnable any time, zero GPU --
`uv run python -m rl_move.sim.probe_lower_hold_action_std --episodes 18
--seed 0`.)

## What this closes
The "SAC entropy-collapse starves hold-phase exploration of
alternative support patterns" story is FALSE on this checkpoint: the
policy is not frozen into a low-noise, locked-in output during hold --
it keeps sampling roughly the same width of nearby actions throughout,
and still converges to (and stays at) the identical 2-leg support
habit in both passing and failing episodes regardless. This means a
targeted "boost exploration/entropy specifically during the hold
segment" mechanism -- the natural next escalation after the
terminal-support forensics doc's two now-closed candidates -- has no
premise to act on and should NOT be built: there is no entropy deficit
to relieve. Combined with the terminal-support forensics' own finding
(near-identical force magnitudes in passing vs failing episodes), the
residual gap looks less like an exploration/discovery problem and more
like a narrow, converged VALUE-LANDSCAPE optimum that per-step
Gaussian noise of this magnitude already explores around without ever
finding (or being rewarded toward) a cheaper multi-leg alternative --
consistent with why every reward-pricing attempt to redirect it
(`k_load_even`/`k_stance_count`/`k_load_rotate`) destabilized instead
of redirecting: there may be no nearby stable alternative in this
policy's reachable action manifold at all, only the one it already
found.

## Next
No new cheap lever identified by this probe either -- it is a
closure, not a fix. The standing "needs a genuinely new structural
design" framing in walkcurr/STATUS.md Next 1 is unchanged; this
narrows what that design should NOT assume (exploration/entropy
starvation) on top of the already-narrowed "not reward-pricing, not
episode-sampling curriculum, not sector/heading-indexed" list. A
mechanism that would still be worth building given this evidence: one
that changes what configurations are REACHABLE at all from the
converged state (e.g. a brief, bounded physical perturbation injected
during the hold phase itself, which is a genuinely different
intervention class than per-step action noise -- it changes the
STATE the policy is reacting to, not the policy's own output
distribution) -- unscoped, not built, needs its own design pass before
any GPU spend, same as the terminal-support doc's own standard.
