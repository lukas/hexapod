# drramp-acq1 (original champion) composed gate under the NEW adopted
# hip-pitch envelope (2026-10-02, zero GPU spend -- pure re-eval of
# EXISTING checkpoints, no training)

## Why
Verdicting `hippitchmax-acq1-r2-cont1` (s0/s1, same cycle) found the
retrained hip-pitch-constrained lower role regresses hard on the
composed direct-arm `lower_ok` gate (s0 7/36, s1 2/36) vs each seed's
own quoted `drramp-acq1` baseline (24/36, 16/36) -- even though the
L1-hip CORROBORATED_STALL exploit the fix targets is confirmed gone
(0/119 traces). That baseline number was measured under the OLD
(buggy, too-loose) hip-pitch clip, so the comparison wasn't apples to
apples, and it was an open question whether the corrected (tighter)
envelope itself is what costs composed robustness, or whether the
hippitchmax RETRAIN just landed a worse policy for unrelated reasons.

`safety.hip_pitch_max_deg` was ADOPTED as a model-source-derived
`SafetyLayer` default this same cycle (mesh/mesh_mjx -> 29.8 deg,
no cfg-set required) -- a pure runtime inference-time filter, so the
ALREADY-TRAINED, ALREADY-ACCEPTED `drramp-acq1` champion checkpoints
(s0/s1, PASS 2026-09-24, the current `todaypolicy`-promoted lower-role
candidate) now automatically run under the corrected envelope too,
with no retraining. Re-ran THIS entry's own composed gate protocol
against them, unmodified code, zero GPU spend -- pure eval.

## Result
Composed direct-arm `lower_ok`, drramp-acq1 (original champion) under
the NEW envelope:
- s0: seed0 12/18, seed100 14/18 = **26/36** (72%) -- vs the OLD-clip
  quoted baseline of 24/36 (67%): UNCHANGED/slightly BETTER, not worse.
- s1: seed0 9/18, seed100 9/18 = **18/36** (50%) -- vs the OLD-clip
  quoted baseline of 16/36 (44%): same pattern, UNCHANGED/slightly
  better.

`trip_summary.stall_classification` on all 54 over_current traces
(both seeds): **0 CORROBORATED_STALL, 100% RAIL_MOVING** -- the L1-hip
dead-zone exploit is gone for the EXISTING champion too, for free.

## Conclusion (resolves the open question from hippitchmax-acq1-r2-cont1's verdict)
The corrected hip-pitch safety envelope does NOT itself cost composed
robustness -- the original champion is unaffected (if anything,
marginally better) by the tighter, correct clip. The hippitchmax
RETRAIN's sharp regression (7/36, 2/36) is therefore better explained
by ordinary training-quality/seed variance in that specific from-
scratch SAC run (which also went through a seed-prune-then-continue
path) than by any structural cost of the safety fix. **No retrain is
needed to get an exploit-free, composed-reliable lower role**: the
EXISTING drramp-acq1 s0/s1 checkpoints, under current (post-adoption)
code, already are one -- same composed pass rate as before, now with
the real-hardware-relevant dead-zone stall mechanism closed.

## Recommendation
Promote plain `drramp-acq1` (s0 AND s1, unchanged checkpoints) as the
confirmed exploit-free rl_only lower-role candidate; no further
training needed for THIS question. The hippitchmax-acq1-r2-cont1
lineage is superseded for the composed-robustness purpose it was
retrained for (the safety fix it validated is adopted into the shared
code path regardless, independent of that specific checkpoint).
