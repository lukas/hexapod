# Review notice (2026-09-08)

The original measurement below is preserved as historical evidence.
Its command-path support bar remains unmet. Later-stage causal claims
(“fully accounted for”, friction as a “secondary sink”) are not established
by these descriptive fits and are superseded by
../twistfit_review_20260908/README.md. Original parity covers body
medians/count/fall summaries, not recorded trajectory parity. The repaired
probe is commit7ca821fb1; the source copy here is the original046c708a probe.

The proposed generic time-multiplexing experiment is withdrawn: existing
fixed-duty results and matched endpoint mixture estimates do not support
it. Original continuous joystick goals and gates remain unchanged.

--- Original owner record ---

# Stance-path twist-consistency measurement (turn steering, 2026-09-08)

Focus-note step after the root full-cone rerun: measure same-phase
COMMANDED vs ACTUAL stance XY foot paths in the body frame under a
single planar rigid-body twist, on the frozen steering plant
(fullmesh34, 4.80573 kg, 100 Hz, exact original `cfg_frozen_audit.json`,
seed 0, scripted TripodGait, cells (0.08, +/-0.15) + straight at
starts 0/pi, unchanged servo/qualification contract). Opposing yaw
moments alone are not proof of commanded-path inconsistency; this
measures it directly.

Probe: `rl_move/sim/probe_turn_twistfit.py` (snapshot 046c708a,
sha256 354ea1e592dc4dbc9b6813e833fc1ec3a651e647eb...486), executed in
the frozen worktree `/workspace/hexapod-turnphase-wt` (same assets as
root_fullcone_20260908; behavior parity vs the root scripted audit
medians asserted bit-for-bit per cell). Unit bank:
`rl_move/tests/test_probe_turn_twistfit.py` (9 tests, all pass).

## Pre-registered support bar (written BEFORE the measurement ran)

A command-side stance-sweep correction (re-projecting stance sweeps
onto the exact commanded twist; swing/touchdown retained) is
SUPPORTED only if on ALL FOUR arc cells the COMMANDED (des-stage,
plan-stance, edge-eroded) paths are themselves twist-inconsistent:

- S1: fitted wz / commanded wz outside [0.90, 1.10], or
- S2: normalized residual vs the exact commanded twist at current
  commanded positions > 0.10, or
- S3: per-foot implied-wz spread (max-min of per-foot medians)
  > 0.20 * |wz_cmd|.

Attenuation first appearing at safe/act/pads stages is EXECUTION, not
command inconsistency; it does not support a command re-projection and
is reported as the measured outcome with a concrete next mechanism.

## Result (measured 2026-09-08 ~03:57 UTC; 6 cells, zero falls, parity 6/6 bit-exact vs root_fullcone scripted medians, feasibility guard PASS: yaw margin 19.6 deg, hip 18.2, knee 45.3, zero IK failures)

**SUPPORT BAR NOT MET — command-side stance-sweep correction is CLOSED
without a preflight or canary.** On every arc cell the COMMANDED
(des-stage, plan-stance) paths are already consistent with the single
commanded rigid twist: fitted wz gain 0.9998 (S1 clear), exact-twist
residual norm 0.015-0.018 (S2 clear, this is the known anchor-frozen
chord linearization, ~1.5-1.8% of foot speed), per-foot implied-wz
spread 1.5e-4 rad/s ~= 0.1% of |wz_cmd| (S3 clear). Verdict computed
mechanically (`support_verdict`), breach false on 4/4 arc cells.

Where the twist actually collapses (same cells, arc +0.15 @0 shown;
all four arcs within noise of each other):

| stage/sel | vx fit | wz fit | resid_norm | per-foot wz spread |
|---|---|---|---|---|
| des/plan (commanded) | +0.0800 | +0.1500 | 0.005 | 0.0002 |
| safe/plan (post-slew-clip command) | +0.0607 | +0.0386 | 0.416 | 0.208 |
| act/contact (measured joints, loaded) | +0.0367 | +0.0566 | 0.545 | 0.064 |
| pads/contact (true mesh feet, loaded) | +0.0348 | +0.0584 | 0.378 | 0.064 |
| body (achieved) | +0.0372 | +0.0642 | — | — |

New quantitative localization:

1. **The twist coherence is destroyed at the SafetyLayer slew-clip
   stage, before the servos and before ground contact**: within
   commanded stance windows the clipped command's fitted wz drops
   0.150 -> 0.039 (-74%) while vx drops only 0.080 -> 0.061 (-24%),
   and the clipped command is itself twist-INCOHERENT across legs
   (per-foot implied-wz spread 0.208 rad/s, ~139% of the surviving
   wz). The gait demands ~82 deg/s mean yaw-servo rate (15.39 deg
   amplitude per 0.375 s half-period), 2.2x the pinned 37.5 deg/s.
2. **Executed contact is nearly anti-phased with the commanded
   windows**: P(contact | commanded stance) ~= 0.44 vs
   P(contact | commanded swing) ~= 0.70 (scuff_frac 0.695-0.701,
   contact duty 0.53-0.60). This is why plan-window act/pads fits
   show sign-flipped twists (act/plan wz -0.068 under a +0.15
   command) and why per-segment des-vs-pads sweeps show amp_ratio_med
   ~0.21 with ~120 deg heading error: the executed stroke happens
   mostly outside its commanded window. Consistent with (not
   contradicting) the lift-lead closure: the executed stroke and
   executed contact are SELF-aligned; both lag the command clock.
3. **The achieved gains match the analytic slew-cap ratio**: a
   zero-mean stroke through a 37.5 deg/s rate limit at period 0.75 s
   caps executed amplitude at 37.5*T/4 = 7.03 deg vs commanded
   15.39 deg = 0.457. Measured: wz gain 0.428 (0.0642/0.15), vx gain
   0.465 (0.0372/0.08). Both axes are ~fully accounted for by the
   pinned rate contract at this cadence/amplitude; traction
   saturation (root_fullcone: usage_max_med 0.66-1.00, ~50-80% of
   loaded substeps near the cone) is the secondary sink, worth only
   a few % relative here.
4. **The achieved arc CURVATURE is nearly correct**: wz/vx = 1.73
   vs commanded 1.875 (-8%). The combined-arc deficit is arc SPEED
   (both axes ~0.43-0.47), not steering direction. During real
   contact the loaded feet fit the achieved body twist (pads/contact
   wz +0.058 vs body +0.064).

## Saved next mechanism (designed, NOT launched; per focus note)

Command-level TURN/WALK TIME-MULTIPLEXING: alternate short pure-turn
and pure-walk bouts (1-2 s) at the session/command layer instead of
commanding vx and wz simultaneously. Motivation measured here + prior
dial evidence: pure-turn tracks ~0.88 gain (wz_med 0.2198 at 0.25
cmd, bit-exact across yaw-arm doses) because the tangential yaw-servo
budget is not shared with vx, while simultaneous combined collapses
both axes to ~0.43-0.47; multiplexing changes WHAT is commanded per
tick (scheduling), not any closed gait dial (phase/posture/cadence/
omega/arm all closed), no contract or plant change. Gate for a future
cycle: averaged-course tracking (curvature + progress) on the same
frozen cells, both signs beyond start scatter, straight health, slip,
zero IK/limit failures — with the honest caveat that per-tick wz
tracking is definitionally worse during walk bouts, so the gate must
score the 60 s averaged course, and A/B against the simultaneous
baseline at equal average vx.

Explicitly recorded negative prediction: a per-tick slew-feasibility
twist governor (uniformly down-scaling the commanded twist until all
joint rates fit the clip) is ALREADY argued against by two closures —
scripted omega-discount (dose 1.0->0.3 made wz monotonically WORSE,
0.0723->0.0620: the overdriven command extracts more rotation than a
feasible-amplitude one) and period_scale 1.5 (executed-stroke
completion improved massively, body wz regressed -14/-16% both
signs). Do not spend a canary on governor-style uniform rescaling
without new contrary evidence.
