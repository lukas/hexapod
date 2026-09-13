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
