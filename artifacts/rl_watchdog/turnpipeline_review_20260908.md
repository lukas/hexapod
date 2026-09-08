# Review of the turn-pipeline interpretation

Reviewed 2026-09-08 00:50 UTC. The 43 rollouts from cycle
`20260908T000347` measure undertracking for the tested frozen controllers
and settings. They do not prove the original command targets impossible
for every controller. Original qualification criteria remain unchanged.

- Every pipeline row reports mass 3.494226 kg; the corrected frozen
  audit reports 4.80573 kg. Both have 34 meshes, which does not establish
  identical plants. The new comparisons are internally matched; comparisons
  across audits must identify the differing models and pin their hashes.
- The 0.071 m yaw arm is measured at a nominal stance, not bounded over
  the permitted workspace. A finite controller/profile matrix is not an
  impossibility proof. The report's own arc example gives
  `0.038 + 0.171 * 0.064 = 0.048944`, not the claimed common 0.040 m/s
  line. A per-leg directional projection is needed for a kinematic bound.
- The scripted desired twist is approximately (+0.08,+0.15) using
  planned stance feet, but (-0.08,-0.15) using actual contacts. The
  narrative changes selectors between stages. Motion loss cannot be
  allocated causally by subtracting these different foot populations.
- `probe_turn_pipeline.py:fit_twist` discards least-squares residuals;
  later medians also discard per-foot disagreement. Similar fitted pad
  and body twists do not establish negligible material-contact slip.
  Reported 65–69% contact during planned swing warrants investigation.

The observations support a contact/actuator timing hypothesis. Next is
one simulation-only lift-phase comparison: freeze the corrected XML/STL,
mass, full configuration and motor model; estimate one vertical phase
lead from measured per-foot actuator/contact lag; compare baseline and
that lead at the original 0.08 m/s, +/-0.15 rad/s arcs, starts 0/pi.
These eight short rollouts preserve XY trajectory, cadence, swing duration,
neutral stance, motor limits, write_speed 400, write_acc 20 and the
0.375-degree/tick slew. Include a straight-walking guard when needed.
Measure per-foot phase-aligned motion, fit residuals and material-contact
slip alongside the original yaw/progress/gait/fall criteria.

This differs from the closed yaw/omega scaling, tripod-duty redistribution,
BC reweighting and command time-slicing experiments. Only a measured gain
in both turn directions with retained gait/progress/slip justifies the next
bounded canary on an existing seed. No physical action, raised limit,
new seed or relaxed qualification is authorized by this review.

Question q_20260908T0050Z's assumed derating and universal training stop
are superseded for this task. Lukas already authorized bounded simulation,
training and routine recovery; this review needs no new permission gate.
The 00:50 operator kick owns the experiment; root owns this correction.

## Frozen assets supplied at 00:58 UTC

The controller now has `/workspace/turnphase_frozen_20260908/assets.tar.gz`
(211,672 bytes). Root verified all 38 archived XML/STL/motor files against
the corrected audit's manifest, both locally and after upload: zero
mismatches. The full-mesh XML SHA256 is
`7efb8e8a0cb014c0b4bac27c41e7a85e683553168b87d85aac0d52d6a8e5a837`.
Extract these into the isolated experiment workspace. There is no missing
full-mesh dependency requiring a reply or a substitute MJX-twin result.
Any exploratory twin runs must remain separately labelled and cannot
replace the requested full-mesh comparison. Feedback receipt:
`fb_20260908T005811_d3e2a7`.
