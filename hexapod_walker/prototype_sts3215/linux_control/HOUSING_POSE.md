# Housing-marker pose estimation

`apriltag_vision.py` detects tags in pixels and estimates their calibrated 6-D
camera/world poses. `housing_pose.py` then converts those rigid poses into the
chassis pose, observable joint angles, and (when all links are observed) foot
positions. Both are offline/read-only: they do not connect to or move the
robot, and they never write servo zeros.

## What each marker observes

| Physical marker location | Kinematic frame | Observable quantity |
| --- | --- | --- |
| Chassis-center/body-fixed marker | `body` | Chassis 6-DoF pose |
| Hip-servo housing | `L*_coxa` | Yaw angle |
| Knee-servo housing | `L*_femur` | Yaw + hip angles |
| Tibia | `L*_tibia` | Yaw + absolute tibia/knee angle |

The knee servo is bolted to the femur. Its housing does **not** rotate when its
own output shaft moves, so motor-housing markers alone provide 12 joint angles,
not 18. Add one small marker to each tibia to recover the six knees.

## As-photographed map (2026-08-31)

The physical handwritten `0` is beside tag 1, so tag 1 is authoritative L0.
The other legs follow the repository sequence around the chassis. “Orientation”
below means the decoded tag **+Y/top direction**, in degrees clockwise from the
top edge of `apriltags.jpeg`; it is not a robot joint angle.

| Location in photo | Tag | Kinematic frame | Tag +Y orientation |
| --- | ---: | --- | ---: |
| Chassis center | 0 | `body` | +68.3° |
| L0 hip lid (handwritten 0), upper-left | 1 | `L0_coxa` | +108.3° |
| L0 knee lid, outer upper-left | 7 | `L0_femur` | +109.7° |
| L1 hip lid, lower-left | 4 | `L1_coxa` | −138.1° |
| L1 knee lid, outer lower-left | 14 | `L1_femur` | +39.2° |
| L2 hip lid, bottom | 6 | `L2_coxa` | +76.5° |
| L2 knee lid, outer bottom | 11 | `L2_femur` | +76.3° |
| L3 hip lid, lower-right | 5 | `L3_coxa` | −71.7° |
| L3 knee lid, outer lower-right | 9 | `L3_femur` | −161.2° |
| L4 hip lid, upper-right | 3 | `L4_coxa` | −131.1° |
| L4 knee lid, outer upper-right | 10 | `L4_femur` | +137.0° |
| L5 hip lid, top | 2 | `L5_coxa` | +166.7° |
| L5 knee lid, outer top | 8 | `L5_femur` | −11.8° |
| Floor, left/origin | 12 | world reference | −175.1° |
| Floor, upper-right | 15 | world reference | −1.1° |
| Floor, lower-right | 13 | world reference | +176.6° |

The machine-readable version is `apriltag_pose_config_20260831.json`. Its floor
map chooses tag 12 as `(0, 0, 0)` and records tags 13/15 relative to it. Do not
move those three floor tags after establishing the map.

## Photo, video, and live-camera use

Run from `prototype_sts3215`. A still image produces one JSON record:

```sh
uv run python linux_control/track_apriltags.py \
  linux_control/apriltag_pose_config_20260831.json \
  --input /path/to/photo.jpg \
  --pose-output pose.json \
  --annotated-output annotated.jpg
```

An existing video produces JSONL (one JSON object per frame) and an annotated
MP4:

```sh
uv run python linux_control/track_apriltags.py \
  linux_control/apriltag_pose_config_20260831.json \
  --input /path/to/video.mov \
  --pose-output poses.jsonl \
  --annotated-output annotated.mp4
```

Capture one raw + annotated photo from camera 0:

```sh
uv run python linux_control/track_apriltags.py \
  linux_control/apriltag_pose_config_20260831.json \
  --camera 0 \
  --raw-output capture.jpg \
  --annotated-output capture_annotated.jpg \
  --pose-output capture_pose.json
```

Or record 10 seconds:

```sh
uv run python linux_control/track_apriltags.py \
  linux_control/apriltag_pose_config_20260831.json \
  --camera 0 --duration 10 \
  --raw-output capture.mp4 \
  --annotated-output capture_annotated.mp4 \
  --pose-output capture_poses.jsonl
```

The supplied configuration's iPhone intrinsics are an EXIF-derived first
estimate. They scale safely to another resolution only at the same aspect
ratio. Replace `camera_matrix` and `distortion_coefficients` with a checkerboard
calibration for accurate metric height and tilt. The three mapped floor tags
then solve the camera extrinsics in every frame; if none is visible, output is
explicitly camera-relative instead of pretending it is in floor/world axes.

## Input contract

Every transform is named `A_from_B`: it maps B-frame coordinates into A.
Quaternions are `[x, y, z, w]`. The generic example configuration is
`housing_pose_config.example.json`; its identity tag mounts are placeholders,
not measured values.

Detector output looks like:

```json
{
  "detections": [
    {
      "camera": "overhead",
      "tag_id": 0,
      "camera_from_tag": {
        "translation_m": [0.12, -0.04, 0.88],
        "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0]
      },
      "decision_margin": 80.0
    }
  ],
  "encoder_joint_deg": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
}
```

Run it from `prototype_sts3215`:

```sh
uv run python linux_control/estimate_housing_pose.py \
  linux_control/housing_pose_config.example.json detections.json \
  --output pose.json
```

For a tracker that already produces rigid-link poses, replace `detections`
with `frame_transforms`, keyed by `body`, `L0_coxa`, `L0_femur`, and so on.

## Mount calibration and identifiability

`frame_from_tag` is the fixed pose of the printed tag in its rigid robot frame.
Use the CAD mount transform or a mechanically indexed tag plate. Translation
errors mainly affect the reported body/foot positions; orientation errors bias
joint angles directly.

A tag's unknown rotation about a joint axis and that joint's unknown encoder
zero are mathematically indistinguishable. Video alone cannot solve both. Each
tag therefore needs either an indexed mounting orientation or one mechanically
known reference pose. After that one reference, many stationary video frames
can estimate `visual_minus_encoder_deg` automatically and consistently.

Treat those values as suggestions. Average repeated stationary captures,
reject poor/mount-residual frames, and inspect the result before changing the
robot calibration.
