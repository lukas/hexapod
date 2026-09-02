# Foot-contact predictor: first offline evaluation

Date: 2026-09-01

This is an observer-only experiment. It did not command or connect to the
physical robot, and the fitted model is explicitly not approved for gait
gating.

## Question

Can commanded joint state plus onboard proprioception estimate whether a foot
is actually planted more accurately than the gait clock alone?

## Method

The scripted MuJoCo replay now records its six foot touch sensors as independent
labels. A small class-balanced linear logistic model uses some or all of:

- commanded foot clearance derived from joint commands;
- measured foot clearance derived from encoders;
- encoder-derived vertical foot speed;
- command-to-encoder tracking error; and
- simulated servo current (in the current ablation only).

The evaluation used 17,280 per-foot samples from gaits 1, 2, 3, and 9 at
30 mm/s, with each gait held out in turn. A touch force above 0.5 N is contact.
The transition metric includes samples within 150 ms of a real touch-sensor
state change. This prevents long, easy stance intervals from hiding poor
touchdown timing.

## Result

| Observer | All-sample accuracy | All-sample balanced accuracy | Transition balanced accuracy |
|---|---:|---:|---:|
| Commanded-height baseline | 93.56% | 88.88% | 72.75% |
| Proprioceptive kinematics | 94.69% | 91.28% | 76.27% |
| Command + proprioception | **95.03%** | **91.76%** | **77.24%** |
| Command + proprioception + current | 94.74% | 91.53% | 75.82% |

The selected command-plus-proprioception model improves balanced accuracy by
2.87 percentage points overall and 4.49 points near contact transitions.
Simulated current did not add accuracy; its overall contribution was -0.23
points. Results were mixed by gait: the largest improvement was on fluid gait
9, while near-transition accuracy was slightly worse than the baseline on
ripple and wave gaits 2 and 3.

## Decision

This is enough evidence to continue with proprioception, but not enough to let
the model declare a supporting foot planted. The ordinary 95% accuracy is
inflated by easy, long stance periods. The safety-relevant transition result is
only 77%, and no independently labeled physical contacts have been used.

The next validation should archive encoder state at the controller cadence and
pair it with temporary, independently sampled physical contact truth (for
example a toe switch or instrumented floor). Current/load can be included at
their available lower rate. That reference sensor is only for calibration and
evaluation; walking would still use no camera. Until that test, the model should
remain a logged confidence channel and must not delay or trigger support
transfer.

### Recent hardware-trace audit

The 2026-09-01 13:32 gait 1/9 run cannot supply that validation after the
fact. Its archived gait telemetry has a median interval of 427 ms (2.34 Hz),
which is slower than the whole transition window. The AprilTag/foot-color
analysis is about 10 Hz, but its floor projection explicitly cannot prove
contact or load. It remains useful for finding candidate drag episodes, not for
grading a touchdown detector.

## Reproduce

From `hexapod_walker/prototype_sts3215`:

```sh
eval_parent=$(mktemp -d /tmp/hexapod-contact-eval.XXXXXX)
uv run python -m rl_move.scripts.replay_scripted_gait_suite_sim \
  --output-dir "$eval_parent/replay" --gaits 1 2 3 9 \
  --speed-mm-s 30 --direction-s 3.2 --settle-s 0.4
uv run python -m rl_move.scripts.evaluate_foot_contact_predictor \
  --sim-telemetry "$eval_parent/replay/sim_telemetry.csv" \
  --output-json "$eval_parent/evaluation.json" \
  --model-json "$eval_parent/model.json"
```
