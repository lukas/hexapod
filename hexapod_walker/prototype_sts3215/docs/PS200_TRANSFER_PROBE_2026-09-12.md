# PS200 recurrent-roll transfer probe — 2026-09-12

## Question

Hexapod-2's PS200 hardware run peaked at 16.78° roll while replaying the
identical command tape in the full-mesh MuJoCo model peaked at 3.32°. Test the
frozen PS200 actor before funding more training:

1. physically correct frame-coupled logical-zero offsets of 0°, ±1°, ±3° and
   ±5° per joint;
2. loss of L4 foot contact for 0.2–0.4 s once per 1.5 s PS200 gait cycle,
   across four phases; and
3. a smooth recurrent body-roll torque over the same gait-cycle/phase grid.

The two lower-roll deployable 50 Hz actors (`walkteach` and `allheading`) are
negative controls. A perturbation only licenses training if it reproduces the
PS200 roll scale and recurrence without producing the same response in both
controls.

Reproduce from `prototype_sts3215`:

```sh
uv run python -m rl_move.sim.probe_ps200_transfer
```

The probe uses exported deterministic actor weights, the full mesh model, the
trained 50 Hz servo/control contract, four seeds, and a 0.10 m/s command after
the standard 1 s hold + 1 s ramp. Per-seed signed roll, contact duty, longest
air interval, speed and termination results are written to the printed
`logs/ckpt_eval/ps200_transfer_probe_<UTC>/results.json` path.

## Results

### Logical-zero hypothesis

| uniform frame-coupled range | PS200 median peak roll | seed range | falls |
|---:|---:|---:|---:|
| 0° | 1.32° | 1.01–2.21° | 0/4 |
| ±1° | 1.80° | 1.48–2.32° | 0/4 |
| ±3° | 1.98° | 1.65–2.86° | 0/4 |
| ±5° | 2.28° | 1.88–2.70° | 0/4 |

The zero range has a real dose response, but even the deliberately large ±5°
range closes only about 1° of the roughly 15° closed-loop hardware gap. It is
not the primary PS200 roll mechanism.

### Airborne/support-loss hypothesis

Nominal PS200 MuJoCo rollouts already reach only 2–3 contacting feet and show
per-leg air intervals up to 0.84 s. Therefore "feet are never in the air in
sim" is false in the literal sense; the relevant missing behavior would be an
*unexpected loss of a commanded support foot*, not ordinary tripod swing.

Removing L4's collision contact for 0.2–0.4 s once per cycle had a best
four-seed median of only 2.82° (the best phase was +1.125 s, duration 0.3 s).
An isolated missing L4 contact is insufficient to explain the hardware roll.

### Recurrent support-asymmetry proxy

A positive 5 N·m half-sine body-roll torque for 0.3 s, beginning at PS200 gait
phase +0.375 s and repeating every 1.5 s, was the smallest screened dose that
matched the hardware signature without a fall. This torque is a causal proxy
for a load-dependent support asymmetry, not a claim that an external force is
the physical root cause.

| frozen policy | baseline peak | recurrent-torque peak | speed after 2 s | falls |
|---|---:|---:|---:|---:|
| PS200 | 1.32° | **14.73°** | 0.038 m/s (baseline 0.049) | 0/4 |
| walkteach | 1.48° | 6.30° | 0.031 m/s | 0/4 |
| allheading | 1.52° | 6.42° | 0.028 m/s | 0/4 |

PS200 produced five separated positive peaks above 5° in each 10 s seed,
matching the hardware's repeated same-direction character. The same
intervention was 2.3× smaller on the controls. One PS200 seed momentarily had
zero contacting feet after the induced roll, so the observed airborne state
is plausibly downstream of the support-asymmetry cascade rather than caused by
a static zero error alone.

## Decision

The recurrent-roll mechanism passes the pre-registered frozen-policy gate. A
small warm-start hardening canary is justified on the PS200 checkpoint with
the perturbation present in 30% of episodes, fixed to the diagnosed phase and
randomized in sign. Do **not** combine zero-offset widening into that first
canary: the zero-only mechanism failed its causal gate, and stacking it now
would confound the result.

Success for the canary means retaining nominal pinned-0.10 speed within 5% of
the 0.0545 m/s parent while reducing the forced recurrent-pulse roll by at
least 30% (14.73° → ≤10.31°), with zero falls and all six legs cycling. The
paired nominal and forced panels must use the parent and child under identical
seeds; training reward alone is not a verdict.

## Canary outcome

`cw-speed50hz-ps200-recurroll5-d03-p0375-canary2m` warm-started from the
mass-corrected PS200 parent and trained for 2,015,232 actual steps (2M target)
in 174 s. The recurrent perturbation was active in 30% of training episodes
and randomized in sign. The checkpoint completed and published normally.

The decisive local full-mesh panel used the frozen parent and child under the
same four seeds, 10 s episodes and pinned 0.10 m/s command. Raw rows are in
`logs/ckpt_eval/ps200_recurroll_child_gate_20260913T030725Z/results.json` on
the operator Mac.

| policy | case | median peak roll | median speed | recurrent >5° peaks | falls |
|---|---|---:|---:|---:|---:|
| parent | nominal | 1.32° | 0.0488 m/s | 0 | 0/4 |
| child | nominal | 1.38° | 0.0512 m/s | 0 | 0/4 |
| parent | +5 N·m recurrent | 14.73° | 0.0382 m/s | 5 | 0/4 |
| child | +5 N·m recurrent | **14.79°** | 0.0407 m/s | 5 | 0/4 |
| parent | −5 N·m recurrent | 1.50° | 0.0465 m/s | 0 | 0/4 |
| child | −5 N·m recurrent | 3.00° | 0.0508 m/s | 0 | 0/4 |

The child retained nominal behavior, but it reduced the diagnosed positive
roll by **−0.4%** rather than the required ≥30%, and forced speed improved
only 6.5% rather than ≥20%. Every leg still cycled (worst positive-pulse child
contact duty 0.293), so this is not a false failure caused by freezing, but L1
air time worsened to 1.22 s in one child seed. The opposite torque direction
was never the frozen parent's vulnerability and training did not generalize
into positive-direction rejection.

**Verdict: FAIL.** Recurrent external roll torque is useful as a diagnostic
stress test, but this 30%-episode, 2M-step curriculum did not teach the missing
response. Do not continue it or increase the dose. The next sim-to-real work
should model the upstream load-dependent mechanism (post-encoder compliance,
backlash/contact loss, or a load-triggered L4 stance-onset error) and validate
that component against the recorded joint/current/contact timing before
funding another PS200 descendant.

## Addendum, 2026-09-13: static global deadband/backlash dose — RULED OUT

The FAIL verdict above named three candidates for the next sim-to-real
mechanism: post-encoder compliance, backlash/contact loss, or a
load-triggered L4 stance-onset error. This addendum screens the first
candidate the same way the zero-offset hypothesis was screened above: a
static, per-episode, uniform per-joint dose — here a pinned multiplier on
the SAME calibrated real-hardware `deadband_deg` (`motor_model.json`) that
ordinary training DR already samples up to 1.8x nominal. `probe_ps200_transfer.py`
gained a `deadband` mechanism/case family (`cb70c89b`'s sibling change,
`--cfg-set`-equivalent `dr.deadband_scale="<d>,<d>"` absolute override,
same pattern as `joint_zero_bias_deg`); no new mechanics code was needed.

Doses 2x–12x nominal (well past the training ceiling) on the frozen PS200
actor, full 4-seed panel, identical command/seeds/episode as every other
case in this doc:

| deadband multiplier | PS200 median peak roll (°) | median fwd speed (m/s) |
|---:|---:|---:|
| 1x (baseline) | 1.35 | 0.048 |
| 2x | 1.02 | 0.046 |
| 3x | 1.10 | 0.042 |
| 4x | 1.21 | 0.037 |
| 6x | 1.36 | 0.028 |
| 8x | 1.62 | 0.017 |
| 12x | 1.53 | 0.007 |

Peak roll stays flat at 1.0–1.6° across the entire dose range — far short
of the 16.78° hardware target and even short of the already-insufficient
±5° zero-offset case (2.25°) — while forward speed collapses toward a
near-stall crawl at the top doses (0.048 → 0.007 m/s, a 6.9x slowdown).
A crippling global backlash dose that nearly halts the gait still does not
reproduce the hardware roll signature. **Static, uniform (non-load-coupled)
deadband/backlash is RULED OUT** as the PS200 roll mechanism; do not
re-screen it at a higher dose or apply it as a training DR widening.

This narrows the remaining named candidates to a **load-triggered** effect
(only the third candidate, a load-dependent stance-onset error, or a
load-coupled — not globally-static — version of backlash/compliance):
whatever is happening is coupled to which leg is bearing weight, not to a
context-free joint property. Building and validating that mechanism (using
sensed per-leg ground-reaction force as the trigger, not a fixed phase
schedule) is unbuilt design/code work for a future cycle — this addendum
only closes the static/global half of the "post-encoder compliance /
backlash" candidate.

Reproduce: `uv run python -m rl_move.sim.probe_ps200_transfer` (now runs
4 stages: zero panel, deadband dose panel, phase screens, control panel).
Full results: `logs/ckpt_eval/ps200_transfer_probe_deadband_20260913/`.
The recurrent-torque re-selection in that run reproduces the original
14.7° finding almost exactly (byte-close to the FAIL verdict above),
confirming the harness is stable; it is not a new training recommendation
— that mechanism already FAILED its hardening canary (see FAIL verdict
above) and is not being re-funded here.
