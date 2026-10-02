# s0 jointlimitlower-acq1-cont1-r2 composed gate result (2026-10-02)

Ran this ledger entry's own registered gate (`eval_lifecycle_handoff_rlonly.py`,
det, n=18 episodes x seeds {0,100}, stance `currentcap29-s5-klrollback05-acq15m`
/ walk `slew_smooth_s0` / lower `...jointlimitlower_acq1_cont1_r2.zip`) --
the pasted triage only carried the isolated DR-0/owncfg gate (own-reset lower,
n=6), not the composed protocol this entry's gate text names.

## Result
Composed direct-arm `lower_ok`: seed0 5/18, seed100 9/18 = **14/36**, vs s0's
own matched-parent baseline (`...drramp-acq1`) of **24/36** -- a sharp
regression, not an improvement. Plant arm also regressed (13/18, 2/18 = 15/36
vs parent band). New fall modes appear that were absent/rare in the parent's
direct arm: tilt_pitch 6/36, tilt_roll 2/36 (parent: tilt_roll 3/36, tilt_pitch
0/36); over_current direct-arm count itself also rose (14/36 vs 8/36).

`trip_summary.stall_classification` on all 26 over_current traces: **0
CORROBORATED_STALL, 26 RAIL_MOVING (100%)**. lower_joint_limit itself never
appears as a trip cause in any of the 72 composed episodes (0 occurrences) --
the termination behaved exactly as designed (rare, never itself the failure)
but did not rescue the composed outcome, which regressed via a different
channel (sustained near-rail current while still turning / tilt falls).

This exactly reproduces the pattern the sibling `s1-drramp-jointlimitlower-
acq1-cont1` run already found and used to defer cfg-key closure to this
result (s1: composed lower_ok 16/36 -> 0/36, 100% RAIL_MOVING, 0 corroborated
stalls). Both seeds now agree: removing the stall-vs-load false-positive gap
did not fix control quality under composed walk-exit entry diversity; the
policy substitutes a different cheap failure mode the isolated/own-DR reset
training distribution never surfaces.

## Verdict feeding into ledger
FAIL (this entry's own gate: "FAIL if lower_ok does not improve over 24/36").
Closes `safety.lower_joint_limit_terminate_s`/`_grace_s`/`_margin_rad`/
`_stall_qvel`: deleted (not adopted) per RESEARCH_RULES "Code changes" --
no live ledger entry sets these keys going forward, and across both seeds the
mechanism never improved the composed metric it was built to move.

## Next (corrected)
NOT entry-state exposure during training -- the entrybank020 bank-
curriculum family (ramp/delay/downweight x2 doses x2 seeds, 8
acquisition arms) already tried exactly this (harvested walk-exit entry
states, with/without qvel restore) and was CLOSED 2026-10-01 for
failing to reach the drramp composed baseline on either seed (best
mitigant 7/12 direct but 3/12 plant). Genuinely open per that closure:
(a) a structurally different off-policy scheme, or (b) accept the
plain drramp lower role (91.7% isolated, ~68% composed) as the working
candidate without further composed-robustness hardening.
