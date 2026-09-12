# GPU vision lab: what bigger video models can do with Robot Lab footage

Date: 2026-09-12. One H200 on the CoreWeave cluster (pod `hexapod-vision-lab`,
node g13e3e6, PVC `hexapod-vision-data`), vLLM 0.29, Qwen3-VL-32B-Instruct-FP8
and Qwen3-VL-8B-Instruct served side by side, DINOv2-giant for the pose probe.
Data: every mp4/mkv in the Robot Lab v2 store (252 clips, 4.1 h, 2.4 GB) plus
the 50,675 floor-camera frames that carry frame-synced IMU roll/pitch and 18
encoder joint angles (`vision.jsonl`). Scripts: this directory; results on the
pod under `/data/results/`; a local mirror under `~/hexapod-vision-data/report/`.

## TL;DR

E1_PLACEHOLDER

## E1: pose estimation from the floor camera (50k labelled frames)

Question: can a frozen foundation backbone (DINOv2-giant, 1.1B) read body
roll/pitch and the 18 joint angles from a single lab-camera frame better than
the repo's 0.55M-param `video_state/train_state.py` CNN?

Setup: ridge regression on frozen DINOv2 features (CLS + mean patch, 518 px)
vs the StateCNN architecture trained from scratch on 160 px frames (no
detector bbox), same splits, MAE in degrees. Two splits: 5-fold grouped by
run (102 runs) and leave-one-protocol-family-out (4 families).

| split | model | roll | pitch | coxa/yaw | femur/hip | knee | all 20 |
|---|---|---|---|---|---|---|---|
| by run | predict train mean | 1.18 | 2.23 | 1.95 | 6.42 | 28.85 | 11.34 |
| by run | DINOv2-g + ridge | 0.94 | 0.99 | 1.18 | 4.13 | 7.95 | 4.07 |
| by run | StateCNN from scratch | 0.83 | 1.06 | 0.74 | 3.39 | 8.05 | 3.75 |
| by family | predict train mean | 1.36 | 3.05 | 1.75 | 12.09 | 41.66 | 16.87 |
| by family | DINOv2-g + ridge | 1.66 | 1.71 | 1.93 | 4.64 | 12.93 | 6.02 |
| by family | StateCNN from scratch | 1.41 | 1.68 | 1.49 | 4.15 | 10.42 | 4.97 |

Per-family probe error (DINOv2 ridge, held-out family): single_leg 6.7,
stand 4.5, tripod 4.2, soak 2.8 (all-20 MAE, deg).

Reading:
- Knee angle is the only target with real variance in this set (train-mean
  MAE 29-42 deg) and both vision models cut it to 8-13 deg from one frame.
- Roll/pitch are essentially constant in these recordings (|roll| p90 = 3.2
  deg, max 21 deg, no tips anywhere), so a 1 deg MAE there is not evidence of
  tip detection; it is evidence the set has no tips. The old bench numbers in
  the video_state README (6.7 deg roll) are not comparable (different camera).
- The big frozen backbone did NOT beat the small CNN trained on the same
  frames; the CNN is 20% better overall and far cheaper. Data (one camera,
  static sysid protocols) is the limit, not model capacity.
- Cost: DINOv2-g runs ~95 frames/s batched and 21 ms per frame at batch 1 on
  the H200, i.e. live-rate. The CNN trains in ~6 min for 5 folds.

## E2: behaviour classification of every clip (VLM, native video input)

E2_PLACEHOLDER

## E3: dense safety timeline on the event-rich clips

E3_PLACEHOLDER

## E4: how close to live

E4_PLACEHOLDER

## Zero-shot keypoints / grounding

Qwen3-VL-32B returns coordinates on a 0-1000 grid. Bounding boxes around the
subject robot are tight and correct for both robots (see
`report/ground_hexapod{1,2}_qwen32b.jpg`); the six foot-tip points are only
roughly right (about half land on a foot, the rest on the body or a wrong
leg), and the on-ground flags are guesses. Usable for "where is the robot /
is it in frame", not for joint-level pose. ~14 s per frame under load.

## Things that went wrong and matter for any follow-up

- Two robots share the lab. hexapod1 is the tag-covered red/blue robot;
  hexapod2 has the flat purple top plate. In most 30 fps clips both are in
  frame. Until the prompt named the subject and showed a reference crop of
  each robot, the VLM described the idle one.
- The wide overview camera is grayscale IR and the robot is ~5% of the
  frame; without the same 0.02/0/0.62/0.75 crop the lab's own eyes.py uses,
  Qwen3-VL-32B said "no robot visible" on every wide clip.
- Title-derived labels are a weak ground truth: several "walk" grid runs
  measured 3-4 mm of travel in their own camera sidecar. Where the sidecar
  exists (22 clips) it is used instead.
- Qwen3-VL-8B in native video mode answered "stand_hold" for 92% of clips;
  it is not a usable substitute for the 32B here.
