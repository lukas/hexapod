# Scratch action-clip probe: reviewed interpretation, 2026-09-08

The six deterministic cells show broad **safe-target sensitivity** to small
applied-action changes. They do not establish actual dynamic foot authority or
refute the whole reachable-target residual mechanism class. The conditional
2M on/off pair has not earned its prerequisite positive evidence.

## Provenance and parity

Cycle `20260908T040325_operator-kick` completed at 04:20:59 UTC. It used
`f07e14d745253c6c153bb2c31261bb005d771313` and the original
`cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m`
checkpoint, six deterministic 20-second walk cells, eval seed 0, std 0.135,
mesh_mjx_twin 4.80573 kg, 100 Hz and 3.6 degrees/tick safety cap.
All 78 ledger cfg overrides match `/tmp/clipprobe_cfgs.txt` exactly. All 55
common per-episode report fields, including randomization, match the original
`_gate` report; newer yaw-reference metrics are additional. This is
**report-summary parity**, not a bitwise comparison of original trajectories.
The checkpoint path differs only by its absolute/relative prefix; reports do
not provide a checkpoint-content hash.

The trace hooks copy post-noise actions, decoder targets and pre-filter
last-safe targets without consuming RNG. The offline slew/limit replica has
zero decoder, safe-target and last-safe-chain error over all 12,000 recorded
ticks. It copies only the relevant target state; it does not clone the complete
SafetyLayer, motor profile, environment, contacts or RNG. Nominal parity
supports this healthy fixed recipe, not arbitrary safety modes.

## Retained measurements and corrections

The saved `probe_summary.json` is the original, uncorrected output. Its
logical target-space metrics remain usable: per-joint saturation is yaw
0.576%, hip 6.351%, knee 11.256%; mean 1.091/18 joints per tick. At an
applied-action budget of 0.05, a safe target moves in 95.67%/95.70% of sampled
channels for positive/negative perturbations and 97.58% for either sign.
This panel's raw any-joint saturation is 57.13%; the earlier 86.65% median
comes from the full 24-cell panel and is not the six-cell measurement.

The saturated-channel median action margin is 0.03586. The old prose used the
wrong denominator: 2.293% of **all** joint/tick samples need more than 0.05;
that is **37.82% of saturated samples**. At 0.25 the corresponding fractions
are 0.0958% of all samples and 1.58% of saturated samples.

The old foot-direction and tracking-error numbers are superseded. Commands
use `robot_abs_tibia_v2`, while MuJoCo stores `knee_rel = knee_abs - hip_abs`.
The probe previously applied relative-hinge Jacobian columns to absolute
increments and directly subtracted those incompatible knee coordinates.
The corrected probe differentiates in absolute target coordinates and converts
measured positions before computing target error. Its output carries
`analysis_contract.version = 2`; the retained JSON has not been recomputed.

Even corrected foot output is a nominal kinematic projection-support proxy,
not loaded dynamic response or independently reachable displacement vectors.
It ignores episode geometry variation and uses post-step qpos/contact with
pre-filter targets. Sampling every 50/100 ms and pooling stance/swing does not
isolate touchdown/liftoff windows.

## Next executable step

Reuse the existing six `trace_ep{0..5}.npz` files on controller/train-5. Recompute
with the corrected frames, align pre-step state where available, and evaluate
all touchdown/liftoff ticks per affected leg before considering another gate.
Only a meaningful transition-specific loss warrants a bounded cloned-state
motor/contact response check. A learned residual requires positive evidence,
zero-residual parity and its original bank/preflight; this review authorizes no
training and changes no plant or limits.

The frame repair is checked against MuJoCo's independent analytic site
Jacobian at three poses and a mixed-frame target-error regression:
`test_probe_action_clip.py`: **4 passed**. No simulation gate was rerun.

Original cloud records `0b86eece` contain STATUS/RL_LOG only; they did not
commit the advertised artifact directory. This reviewed README accompanies the
recovered original summary and preserves that provenance distinction.
