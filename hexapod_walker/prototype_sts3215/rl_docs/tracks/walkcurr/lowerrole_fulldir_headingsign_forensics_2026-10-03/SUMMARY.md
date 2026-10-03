# rl_only lower-role full-direction collapse: HEADING-SIGN forensics (2026-10-03)

Scoped item: walkcurr/STATUS.md Next(1) — the `lifecycle_fulldir_
holdonly100s3_panel` finding that composed (rise->walk->lower) `lower_ok`
collapses off-axis even though the walk role itself generalizes cleanly
full-circle. That panel read n=4 episodes/heading/arm at a single eval
seed. This item reruns the SAME 3-checkpoint composition (stance
`currentcap29-s5-klrollback05-acq15m`, walk `slew_smooth_s0` + `--rot60`,
lower `holdonly100-s3`) at n=4 episodes x 2 eval seeds {0,100} = n=8 per
heading, all 8 headings, zero `--lower-cfg` override (matching the
official matched-seed-retest protocol exactly — passing
`goal.lower_hold_only_frac=1.0` at eval time is a no-op for the training-
curriculum-only reset path but WAS present in this item's own first,
discarded probe; dropping it to match protocol changed the per-episode
draws materially, a good reminder that `--lower-cfg` presence/absence is
not actually inert here the way a first reading suggested). Zero GPU
spend (CPU MuJoCo eval only, pre-existing `eval_lifecycle_handoff_rlonly.
py --current-trace-dir`). Raw JSON in `/tmp/fulldir_trip_diag/` on the
controller pod (ephemeral, rerunnable from the commands below in ~1-2 min
each).

## Finding 1: the collapse is HEADING-SIGN asymmetric, not a uniform
off-axis gradient — CORRECTS the panel's framing
| heading (deg) | direct lower_ok | plant lower_ok |
|---|---|---|
| -135 | 1/8 (12%) | 0/8 (0%) |
| -90  | 1/8 (12%) | 2/8 (25%) |
| -45  | 2/8 (25%) | 5/8 (62%) |
| 0    | 7/8 (88%) | 3/8 (38%) |
| +45  | 3/8 (38%) | 5/8 (62%) |
| +90  | 6/8 (75%) | 7/8 (88%) |
| +135 | 7/8 (88%) | 5/8 (62%) |
| 180  | 8/8 (100%)| 8/8 (100%) |
| **TOTAL** | **35/64 (55%)** | **35/64 (55%)** |

(n=8/cell: episodes {0,1,2,3} at eval-seed 0 + eval-seed 100, det, zero
`--lower-cfg`.) The original panel's n=4-single-seed "8/32=25% aggregate,
forward-ish ~50% vs lateral/behind 0-25%" read is corrected/superseded by
this larger-n table for the DIRECT arm specifically — it is NOT a
"forward good, everything else bad" shape. It is a clean LEFT/RIGHT
split: every NEGATIVE heading (-45/-90/-135) is bad (12-25%) regardless
of how far off-axis, while every POSITIVE heading (+45/+90/+135) AND
180 (straight behind) are good-to-perfect (38-100%, improving the
further from 0). 0 itself (88%) is NOT the best cell — 180 and +135 are
as good or better. This is a materially different shape than "forward
generalizes, off-axis doesn't": it is "one turn direction generalizes,
the other doesn't, independent of magnitude."

## Finding 2: the trip SIGNATURE differs by sign too — negative headings
are PURELY the chronic L2+L5 habit; positive-heading failures are
joint-diverse
Current-traced over_current fails, `trip_summary.final_joint`
(`hexapod_core.joint_frame.SIM_JOINT_NAMES`):
- Negative headings (-45, -90, -135), 5 traced over_current fails: ALL 5
  are joint 7 (**L2_pitch**, hip) or joint 16 (**L5_pitch**, hip) — the
  exact same universal pair every forensics doc this week has already
  named as this lineage's one discovered stable (if expensive) terminal
  stance. Zero exceptions.
- Positive heading (+45), 5 traced fails (2 direct over_current, 1 direct
  tilt_pitch, 2 plant over_current): joint 5 (**L1_knee**), joint 16
  (L5_pitch), joint 14 (**L4_knee**), joint 7 (L2_pitch), joint 5 again —
  a mix including TWO joints (L1/L4 knee) that never appear in the
  negative-heading failure set at all.

## Mechanistic hypothesis (not yet verified by a dedicated check, but
the only explanation that fits both findings without positing a bug or
new hardware asymmetry)
The WALK role is rotation-EQUIVARIANT by construction (`rot60.py`,
physics-level proof in `test_rot60.py`) — walking at heading theta is
exactly walking at theta-60*k with legs relabeled by `leg_perm(k)`. The
LOWER role is NOT wrapped in any such transform and was never trained
with heading/sector context at all (`lower_hold_only_frac=1.0` training
starts near final height, no walk precursor) — it independently
converged, via ordinary SAC symmetry-breaking, on a FIXED REAL-leg-space
preference (rest on real L2+L5, the diametrically-opposite pair) that
has no reason to be the canonical-frame-identical choice for every
sector. A rotation by +k sectors and -k sectors are NOT mirror images
of each other (`rot60` is a rotation group, not a reflection group;
`leg_perm` for k and -k are different, non-conjugate-by-anything-simple
permutations of the hexagon) — so there is no a priori reason the
lower role's fixed L2/L5 realspace habit should line up equally well
with the walk-exit state the rot60 wrapper leaves behind at every
sector. This composition-alignment story predicts exactly what was
found: a sign-dependent (not magnitude-dependent) split, with the SAME
universal pair dominating failures wherever the alignment is bad
(negative sectors) and a more generic, lower-rate, momentum/tilt-driven
failure mode when the alignment is merely suboptimal rather than badly
mismatched (positive sectors). It does NOT require a `rot60.py` bug
(the sector-pick itself is unambiguous at +-45, not a boundary tie —
`round(-0.75)=-1`/`round(0.75)=1`, clean) or a real per-leg hardware
asymmetry the mesh-mass audit hasn't already modeled.

## What this does and does not change
Does NOT reopen any CLOSED single-factor lever (entrybank, reward
dosing, action-smoothing, ext_push) — none of those touched the
walk<->lower FRAME-ALIGNMENT question at all; this is a structurally
new axis. Does NOT contradict the forward matched-seed PASS-MECHANISM
verdict for holdonly100 (that retest used heading 0 only, which this
table confirms is a genuinely good cell, 88%).

## Concretely scoped next step (NOT built this cycle — needs real
design, flagged here rather than rushed, per this track's own
discipline)
A sector-AWARE composition wrapper for the lower role specifically: at
the walk->lower handoff, read the walk role's own final `Rot60Policy.k`
(already computed, already available at the exact handoff tick — zero
new observation/training needed) and apply the SAME `leg_perm(k)`-style
relabeling to the lower role's own per-leg observation (and inverse-
permute its action) so the lower role's single learned canonical-leg
preference (whatever real legs it happens to prefer in ITS OWN training
frame) gets consistently re-mapped onto whichever real legs are
sector-appropriate, instead of being applied blindly in fixed real-leg
space regardless of heading. This is a ZERO-RETRAIN, composition/eval-
code-only change (reuses the existing `holdonly100-s3` checkpoint as
is) — cheap to build and test (no GPU) relative to every reward/
curriculum lever already closed this week, and the first candidate
that targets the ACTUAL newly-identified mechanism (frame misalignment)
rather than another dose on the stance/reward side. Not built this
cycle: the stance/lower env's own observation layout (`sim_env.py`'s
goal-conditioned balance obs, NOT the 72-wide stacked walk frame
`rot60.py` already transforms) needs its own from-scratch per-leg
slice map before a transform can be written and tested — real design
work, scoped here for the next cycle rather than rushed against this
cycle's remaining budget.

## Repro commands (zero GPU, ~1-2 min each on CPU MuJoCo)
```
uv run python -m rl_move.sim.eval_lifecycle_handoff_rlonly \
  --stance rl_move/sim/policies/ppo_goal_cw_stance50hz_rlonly_currentcap29_s5_klrollback05_acq15m.zip \
  --walk rl_move/sim/policies/ppo_goal_cw_walk50hz_slew_smooth_s0.zip --walk-recipe slew_smooth_s0 --rot60 \
  --lower rl_move/sim/policies/ppo_goal_cw_stance50hz_rlonly_lowerrole_scratch_sac_s3_drramp_holdonly100_acq1.zip \
  --lower-recipe lowerrole_sac_drramp \
  --episodes 4 --heading-deg <H> --seed <0|100> \
  --current-trace-dir /tmp/<dir> --out /tmp/<out>.json
```
