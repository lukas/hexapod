# curvewalk_v1 turn-hold composed gate: silent regression from the
# 2026-10-02 `safety.hip_pitch_max_deg` adoption (found 2026-10-06,
# refill cycle, zero GPU spend, CPU-only re-verification)

## Why this check ran
Goal 2's (`rl_only`) own STATUS.md readiness note names an open gap:
no single candidate yet stitches rise+walk+turn+lower in one session
(`bundle_rlonly_lifecycle_v2` has rise+walk+lower but no turn;
`bundle_rlonly_curvewalk_v1` has walk+turn but no rise/lower; both
share the "walk" role designation but actually use DIFFERENT specific
walk checkpoints -- `slew_smooth_s0` vs `crutchoff_s0_warmadapt_acq1`,
the former a warm-started child of the latter). Before building a
unified 4-role candidate, the natural first question is whether the
turn-and-hold specialist (`acq5-seedsweep-s5`, frozen) composes
cleanly with the NEWER `slew_smooth_s0` walk checkpoint instead of its
original `crutchoff` partner -- a cheap, zero-GPU, CPU-only
`eval_walk_turn_compose.py` re-run (same harness `bundle_rlonly_
curvewalk_v1`'s own registered gate used).

## Tool change (additive, bit-exact when unset, tests green)
`eval_walk_turn_compose.py`: added `--walk-recipe slew_smooth_s0`
(reuses the existing, already-versioned `cfg_recipe_walk50hz_
slew_smooth_s0.CFG_ARGS` module -- no new cfg plumbing) and
`--walk-cfg`/`--turn-cfg` override flags (same `_compose_lower_cfg_args`
append convention `eval_lifecycle_handoff_rlonly.py`'s `--lower-cfg`
already established). `rl_move/tests/test_walk_turn_compose.py` 5/5
green before and after.

## Finding 1 (the one that matters): the already-PASSED curvewalk_v1
## gate no longer reproduces on HEAD -- NOT because of the walk-
## checkpoint swap, but because of an intervening shared-default change
Re-running the ORIGINAL registered pairing (`crutchoff_s0_warmadapt_
acq1` walk + `acq5-seedsweep-s5` turn, no `--rot60`, no `--settle-
grounded-s`, `--episodes 12 --cycles 2`, det -- i.e. the exact
invocation behind the archived `walk_turn_compose_v1_det.json`, which
reads `turn_success 23/24`) on the CURRENT tree reproduces only
**7/24** turn_success (same `trk_err`/convergence -- `turn_converged`
stays 24/24, `err_q4_mean_rad` ~0.02 in both reads -- so yaw TRACKING
is unaffected; the drop is entirely `gait_valid` going False via a
leg-3 duty/swing-count sacrifice during the hold). Zero falls either
way (12/12 episodes). Deterministic and reproducible (reran twice,
byte-identical summary).

Root cause, confirmed by a clean A/B: `safety.py`'s 2026-10-02
`safety.hip_pitch_max_deg` adoption (`ops.sh index story
cw-stance50hz-rlonly-lowerrole-scratch-sac-s0-drramp-hippitchmax-acq1-
r2-cont1`, PARTIAL) made the hip-pitch upper safety clip
MODEL-SOURCE-DERIVED (mesh/mesh_mjx auto -> 29.8deg, tighter than the
old unconditional 40deg servo ceiling every mesh_mjx env used before
that date) -- applied retroactively to EVERY mesh_mjx eval env,
including frozen pre-10-02 checkpoints that were never trained under
it. Overriding both envs back to the legacy bound
(`--walk-cfg safety.hip_pitch_max_deg=40.0 --turn-cfg
safety.hip_pitch_max_deg=40.0`) reproduces the archived number almost
exactly: **23/24** turn_success -- a clean causal match, not a
coincidence. This is the SAME mechanism class the hippitchmax-acq1-
r2-cont1 verdict already named for the LOWER role's own composed gate
("a DIFFERENT composed-robustness metric regressed... the tighter
hip-pitch envelope plausibly removes actuation headroom the policy
was illegitimately using") -- this entry shows it is not scoped to the
lower role: it also silently regresses the already-PASSED
**curvewalk_v1 turn-hold composition**, a standing Goal-2 sim-demo
candidate, from 96% to 29% gait_valid on its own registered read.

## Finding 2 (the original question, now answerable only net of Finding 1)
Under the MATCHED legacy-hip condition (so Finding 1's confound is
controlled out), swapping the walk role from `crutchoff_s0_warmadapt_
acq1` to `slew_smooth_s0` (`--rot60`, `--settle-grounded-s 1.0`, same
turn checkpoint) gives **20/24** turn_success -- down from crutchoff's
23/24 under the same override, but far closer to it than the raw
(un-ablated) 7/24 vs 6/24 numbers suggested before Finding 1 was
isolated. A real, smaller, secondary degradation exists from the
walk-checkpoint swap alone (different `safety.max_delta_q_deg`
3.5-vs-7.2deg / reward-shaping contract the two recipes carry), but it
is NOT the dominant effect naive numbers implied.

## What this does and does not change
**Does not** touch `bundle_rlonly_curvewalk_v1`'s historical artifacts
or its PASS verdict as a record of what was true on 2026-09-30 --
those files/numbers stand. **Does** mean that candidate's live
HEAD-tree behavior needs re-verification (or the turn role needs a
short fine-tune under the corrected hip-pitch envelope, same as the
lower role's own open item) before it is cited again as current
evidence, and before ANY unified rise+walk+turn+lower candidate is
built on top of it -- building one now would inherit an already-known,
unaddressed regression rather than test anything new. No code default
changed here (the override flags are additive/opt-in, off by default);
no training run launched (zero GPU spend, CPU-only, all four reads
above are archived under `logs/ckpt_eval/walk_turn_compose_{crutchoff,
slewsmooth}_{baseline_recheck,legacyhip_ablation}*.json`).

## Next
1. Decide + execute ONE of: (a) short fine-tune/continuation of the
   `acq5-seedsweep-s5` turn checkpoint under the now-default 29.8deg
   hip-pitch envelope (mirrors the lower role's own still-open
   "separate problem"), or (b) accept the composed-gate regression as
   a known, bounded, non-fall (gait_valid only, 0 falls) cost and
   re-register `bundle_rlonly_curvewalk_v1`'s gate numbers under the
   current tree before any further reliance on it. Either needs a
   deliberate choice, not a silent re-use of the stale 09-30 numbers.
   Unscoped -- no GPU spend justified until one is picked.
2. A unified rise+walk+turn+lower `rl_only` candidate (closing the gap
   STATUS.md names) should wait on item 1 -- composing on top of an
   already-regressed turn role would not produce trustworthy new
   evidence. Once item 1 lands, retest turn-vs-`slew_smooth_s0` (this
   entry's Finding 2) to pick the unifying walk checkpoint.
3. Same re-verification question likely applies to any OTHER mesh_mjx
   composed-gate evidence collected before 2026-10-02 that has not
   been re-read since (e.g. `amp` track's push/fault-hardened M3/M4
   exports, trained/gated pre-10-02) -- flagged here, not chased
   further this cycle (out of scope: those are a different track's
   own evidence to re-verify on their own schedule).
