# GPU vision lab: what bigger video models can do with Robot Lab footage

Date: 2026-09-12. One H200 on the CoreWeave cluster (pod `hexapod-vision-lab`,
node g13e3e6, PVC `hexapod-vision-data`), vLLM 0.29, Qwen3-VL-32B-Instruct-FP8
and Qwen3-VL-8B-Instruct served side by side, DINOv2-giant for the pose probe.
Data: every mp4/mkv in the Robot Lab v2 store (252 clips, 4.1 h, 2.4 GB) plus
the 50,675 floor-camera frames that carry frame-synced IMU roll/pitch and 18
encoder joint angles (`vision.jsonl`). Scripts: this directory; results on the
pod under `/data/results/`; a local mirror under `~/hexapod-vision-data/report/`.

## TL;DR

- **Pose from one frame (E1)**: a frozen DINOv2-giant probe reads the 18 joint
  angles to 4-6 deg MAE (knee 8-13 deg vs 29-42 deg for guessing the mean) but
  does NOT beat the repo's 0.55M CNN retrained on the same 50k frames (3.8 /
  5.0 deg). Data, not model size, is the bottleneck; and the labelled set has
  no tips at all (|roll| max 21 deg), so nothing here validates tip detection.
- **Behaviour classification (E2)**: Qwen3-VL-32B given the whole clip as video
  is a decent narrator: it names the right robot, times stand-ups and lowers
  to within a second (checked against frame-difference motion bursts), sees
  operator handling, robot-leaves-frame and in-place stepping. It is weak on
  slow locomotion: of 14 clips where the lab camera measured >= 90 mm of
  travel it called only 3 "walking" (the ones faster than ~28 mm/s, side
  camera only). Qwen3-VL-8B answered "stand_hold" for 92% of clips in both
  video and stills mode; it is not usable here.
- **Safety timeline (E3)**: 8 s windows over 31 min of the event-rich clips
  ran at 0.39x realtime sequentially. It reliably reports human contact and
  robot-at-frame-edge, but produced 46 low-severity "leg folded under body"
  events (mostly normal stance changes) and rated every clip risk=none,
  including the drop-through-safe_zero clips. No evidence it would catch a
  tip in time; the incumbent IMU trip is still the safety path.
- **Latency (E4)**: with the GPU idle, an 8-frame safety question answers in
  0.61 s on the 32B and 0.18 s on the 8B; DINOv2-g is 21 ms/frame. A 32B
  windowed spotter at ~1.5 Hz on one H200 is feasible; whether it is worth it
  depends on fixing the recall problems above first.
- **Versus the incumbent** (Claude Sonnet 5 on 12 timelapse frames, eyes.py):
  on the 53 wide-camera runs the two narrations agree on the gist in nearly
  every case; the local model is not better, just free per call (~8 s/clip).

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

Setup: 252 clips, subject robot named per clip (runs.robot) with two reference
crops, strict JSON schema (activity enum, visibility, person in frame, timed
safety events, outcome, <=100-word timeline). Qwen3-VL-32B-FP8 and
Qwen3-VL-8B with the clip as native video (vLLM samples ~2 fps; 13k prompt
tokens per clip median); 8B also with 24 timestamped stills as a control.
Clips over 200 s go through stills (a 41-min clip decoded whole OOM-killed the
pod). Labels: title-derived activity (238 clips; weak), the lab camera's own
travel measurement (22 clips; strong), and spot checks by eye on ~15 clips.

| model | mode | exact vs title | coarse vs title | events/clip | infer s p50/p90 (shared GPU) |
|---|---|---|---|---|---|
| Qwen3-VL-32B-FP8 | video | 20/238 | 34/238 | 0.28 | 7.6 / 12.3 |
| Qwen3-VL-8B | video | 14/238 | 15/238 | 0.03 | 5.2 / 8.8 |
| Qwen3-VL-8B | 24 stills | 12/238 | 13/238 | 0.06 | 4.3 / 5.4 |

Those title-accuracy numbers are low for both good and bad reasons. Bad: the
32B calls the 58 "glide re-step" clips in-place stepping (41) or standing (16),
and "walk" clips mostly stand_hold/in-place. Good: many of those titles are
wrong about the video. Where the lab camera measured travel (22 clips):

| camera-measured travel | 32B said walking | 8B said walking |
|---|---|---|
| >= 90 mm (14 clips, 7-38 mm/s) | 3 | 1 |
| < 90 mm (8 clips, 1.5-7 mm/s) | 1 (false alarm) | 0 |

The three hits are the 28-38 mm/s walks seen from the 30 fps side camera; the
same walks from the 1 fps overhead camera were called in-place stepping.
Anything at <= 21 mm/s reads as standing or weight-shifting to the model.

What the 32B gets right (spot-checked against contact sheets / motion energy):
- Stand-up timing: "rises 10.4-13.5 s" on d0166033c807/183420Z matches the
  frame-difference burst at 10-16 s; the second burst (18-27 s) was described
  as a lower in free-text mode and missed in JSON mode.
- Operator interaction: 49 of 71 reported events are hands/feet near or on
  the robot, and every one I checked was real (e.g. rise_lower_v2_cam1: hand
  adjusting cable at 0 s, repositioning a floor tag at 0.9 s).
- Robot leaving the frame: 82461d6ac452/214939Z_glide_cam1 "exits left edge by
  56.5 s" is correct.
- The one fall_or_collapse (a678e61ddb8a at 36 s) is a real, fast, controlled
  lower at the end of a walk canary: right event, wrong severity.

What it gets wrong: the drop-through-safe_zero "sit/crash" clips
(0a8762fc978f) are all called stand_hold; slow walks are not walks; the 8B
model is blind to motion at this scale in either input mode.

Incumbent comparison: for the 53 `wide.mp4` runs the manifest carries the lab's
own Claude 'seen' text. Both narrations agree the sysid robot is essentially
static; Claude's text is more specific about which legs twitched (it gets the
protocol description in its prompt); Qwen's is generic. Full side-by-side in
`~/hexapod-vision-data/report/e2_report.txt`.

## E3: dense safety timeline on the event-rich clips

Setup: 46 real-time clips from the trip / sit-crash / failed-RL-walk /
stand-up / walk-acceptance runs (31 min), 8 s windows with 4 s stride, 16
frames per window, Qwen3-VL-32B, JSON with end-state, risk (none / watch /
intervene_now) and timed events. 396 windows in 12.2 min wall time (0.39x
realtime sequential; p50 1.5 s, p90 2.7 s per window on a shared GPU).

- Risk was "none" in every clip. End states: 344 standing_stable, 46
  lowering_or_sitting, 3 being_handled, 2 not_visible, 1 tilted_or_propped.
- Events: 46 leg_folded_under_body (low), 12 operator, 3 cable_snag, 1 stall.
  The leg-fold events cluster at stand-up onsets (legs tuck as the body rises)
  and at the hexapod1 splayed pose; they are stance changes, not faults.
- The operator events are accurate narrations (e.g. 0ea04f611690/222336Z:
  operator places a box at 31 s, sets the robot on it at 32 s).
- It did not flag the safe_zero drops, the IMU-limp walk or the tilt-refusal
  runs as anything but standing_stable. Windowed stills lose the slow drop
  that whole-clip video mode sometimes catches.

Verdict: usable today as an "is a person touching / is the robot still in
frame / is it upright or on its belly" annotator; not as a tip detector.

## E4: how close to live

Sequential requests, GPU otherwise idle, 960 px frames, short JSON answer:

| model | 1 frame | 8 frames (4 s window) |
|---|---|---|
| Qwen3-VL-8B | 0.14 s | 0.18 s |
| Qwen3-VL-32B-FP8 | 0.53 s | 0.61 s |
| DINOv2-giant features (probe is free) | 0.021 s | - |

So a 32B spotter can look at a 4 s window every ~0.7 s on one H200, and the
whole-clip narration costs ~8 s per 40 s clip. The blocker for a live safety
use is recall on subtle events (E2/E3), not speed. The pose probe (E1) is the
only thing here that is both live-rate and quantitatively validated, and it
is validated only on static poses.

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
