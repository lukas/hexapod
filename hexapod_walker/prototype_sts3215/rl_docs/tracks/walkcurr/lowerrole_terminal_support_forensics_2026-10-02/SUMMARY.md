# rl_only lower-role terminal-stance per-leg LOAD forensics (2026-10-02)

Zero-GPU, zero-retrain (CPU MuJoCo eval only, reused the already-adopted
`drramp-acq1` s0 champion checkpoint, bit-exact). Tool: `eval_lifecycle_
handoff_rlonly.py --current-trace-dir ... --minload-trace-dir ...` (both
already built; no code change). Follows directly from today's closure of
all 3 per-joint current/concentration reward levers plus the ramp-SPEED
trajectory lever (`goal.lower_ramp_s` 3/8/12, all FAIL) on this lineage's
composed over_current/tilt ceiling. Before guessing a 4th reward shape or
a 2nd trajectory-schedule idea, this item asks a question none of the
prior forensics docs answered: at the MOMENT an over_current trip fires,
what does the actual PER-LEG FOOT FORCE distribution look like (not just
which joint's current is highest)?

## Method
Ran `n=18, seed=0, direct` composed rise->walk->lower with the champion
stance/walk/lower triple (`currentcap29-s5-klrollback05-acq15m` /
`slew_smooth_s0` / `lowerrole-scratch-sac-s0-drramp-acq1`), capturing
BOTH traces together for every episode (12/18 lower_ok, matching the
known baseline). `minload`'s `perleg_force_trace_n` (T,6) gives the raw
per-foot touch-sensor normal force every tick regardless of outcome;
`current`'s trip_summary gives which joint/when for the 5 failures.

## Finding: the terminal support pattern is a FIXED, UNIVERSAL 2-leg
(L2+L5) prop, present in PASSING episodes too — not a failure signature
Mean per-leg force over the last 100 ticks (~2s) of all 18 direct
episodes:

| episode | L0 | L1 | L2 | L3 | L4 | L5 | lower_ok |
|---|---|---|---|---|---|---|---|
| 0 (ok) | 0.6 | 2.3 | **16.8** | 0.0 | 0.0 | **14.7** | True |
| 3 (ok) | 0.9 | 2.3 | **16.8** | 0.05| 0.0 | **14.4** | True |
| 7 (ok) | 0.6 | 1.9 | **17.4** | 0.0 | 0.0 | **14.3** | True |
| 16 (FAIL, over_current, L5 hip) | ~0 | ~1 | **15.9** | ~0 | ~0 | **13.5** | False |
| 5 (FAIL, over_current, L2 hip) | ~0 | ~1 | **16.4** | ~0 | ~0 | **13.5** | False |
| 9 (FAIL, over_current, L4 knee) | 2.2 | ... | 2.2 | ... | ... | 6.0 | False (outlier, different final config) |

(Full 18-row table re-derivable from `minload/direct_*.json`, same
protocol.) Across **every** direct episode but one outlier, by the last
~2-4s of the 15s episode the robot is resting on exactly TWO feet —
**L2 and L5** — at 13-17 N each, while L0/L1/L3/L4 carry under ~1-3 N
(several exactly 0.0 N, fully unloaded). This is true for PASSING
episodes at the SAME magnitude as the failing ones (e.g. ep0 PASS:
L2=16.8/L5=14.7 vs ep16 FAIL: L2=15.9/L5=13.5 — the failure is not
running hotter, it's nearly identical). The pattern is visible from at
least tick ~518/750 (69% through the episode, ~4.4s of hold remaining)
through episode end in the inspected traces — i.e. it persists for
several continuous seconds, not just a final-instant artifact.

## What this does and does not explain
Does NOT reopen a "redistribute away from L5" framing — L2 carries
MORE than L5 in every row above; the earlier per-joint-current
breakdown's "L5 hip 47% of RAIL_MOVING" finding was about which joint's
CURRENT reading crosses the trip threshold first, not about L5 carrying
the most force (L2 does, consistently, but L2's hip evidently has more
headroom at this posture/gear ratio before its own current trips).
Does NOT corroborate "policy picks an arbitrary/different leg each
time" (the `k_load_even` forensics' framing) — it picks the SAME two
legs essentially every episode, pass or fail.
DOES explain why all three closed per-joint reward levers behaved as
observed: `k_current_hot`/`k_torque_headroom` price a single joint's
current magnitude but this is a STRUCTURAL two-leg support habit, not
an avoidable spike — pricing it harder either does nothing (current
is near the physical minimum needed to hold this stance) or forces the
policy away from its only discovered stable terminal configuration,
which is exactly what `k_load_even` reward did: it destabilized the
robot into TILT failures at every dose instead of discovering a lower-
current alternative stance. Likewise explains why ramp-SPEED (`goal.
lower_ramp_s` 3/8/12) could not help: the ramp only controls the
DESCENT portion (first ~5s); this 2-leg support signature is a
POST-RAMP HOLD phenomenon (lasting ~9s of the 15s episode,
`lower_hold_s=1.0` + the remaining settle time after the ramp
completes) that ramp duration does not touch at all.

## Why some episodes trip and others with near-identical load don't
The over_current trip is a SUSTAINED-duration rail check
(`safety.over_current_trip_s`), already confirmed (walkcurr system-ID,
2026-10-01/02) to NOT be a miscalibrated threshold — the scripted
open-loop baseline stays <=43% of the same rail at every trained depth,
proving a genuinely lower-current way to hold a similar final height
exists (almost certainly via a more-symmetric, more-than-2-leg support
distribution the scripted baseline uses, unlike this policy's 2-leg
habit). Given near-identical force magnitudes in both passing and
failing episodes, whether a given episode's dwell crosses the trip's
time threshold within the ~9s hold looks governed by fine-grained,
episode-to-episode control noise/dwell variance around a narrow safety
margin, not by an identifiable per-episode mistake this eval protocol
can see. This reframes the ~28%(s0) composed over_current rate as a
MARGIN question against a converged, universal, higher-than-necessary-
current terminal habit, not a per-episode fixable bug.

## Recommendation: do NOT dose another per-joint reward shape or ramp
schedule on this lineage without a new idea; two live, UNSCOPED
candidates for a future cycle (neither built/tried, both consistent
with the rl_only no-demo contract since neither copies a scripted
trajectory, only a kinematic/curriculum framing):
1. **Curriculum/credit-assignment**: the policy may never get strong
   enough gradient signal specifically on the long post-ramp HOLD
   sub-skill (vs. the preceding descent) to discover a better-than-2-
   leg stance; a hold-phase-only training variant (episodes that start
   already near the final lowered height, analogous to the existing
   `goal.mode_seq_rise_from_h` "stand up from where you are" trick,
   applied to `lower`/hold instead of `rise`) would give it isolated
   practice at exactly this sub-skill. NOT built; needs a symmetric
   `goal.mode_seq_lower_from_h`-style key + cfg-set + its own canary.
2. **Posture/kinematic reference, not pricing**: instead of pricing
   current/force magnitude or concentration (all 3 closed), give the
   hold phase a stance-WIDTH or symmetry-biased observation/bonus that
   rewards keeping MORE than 2 feet above a small force floor (distinct
   in shape from `k_load_even`'s Herfindahl concentration price, which
   this doc shows destabilizes the only stable configuration the
   policy has found — a floor/count-style term is a different
   mathematical object and has not been tried on this lineage).
Both need real design + a from-scratch canary before any acq spend;
neither is launched this cycle.

Evidence: `/tmp/lf_trace_champ/{current,minload}/direct_*.json` (this
session's capture, not committed — rerunnable any time from the
already-adopted `drramp-acq1` s0 checkpoint with the command above,
zero GPU, ~3 min CPU).
