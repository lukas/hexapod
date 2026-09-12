# State of the robot, 2026-09-11 (hexapod 1, with hexapod 2 for comparison)

One page from everything the two labs and the hand runners recorded between 2026-09-03 and 2026-09-11, read back from the CSVs, logs and frames rather than from memory. Regenerate the tables, sheets and plots with:

    /Users/lukas/hexapod/.venv/bin/python -m sysid.archive_review \
        --lab-dir "$HOME/Library/Application Support/Hexapod Lab/v2" \
        --out "$HOME/Library/Application Support/Hexapod Lab/v2/review-20260911"

Artifacts: `review-20260911/{REVIEW.md,index.csv,events.csv,sheets/,plots/}` under `~/Library/Application Support/Hexapod Lab/v2/`. Also filed on Robot Lab run `199460d899f6`.

## What the archive actually is

| source | runs | with joint CSVs | with frames |
|---|---:|---:|---:|
| Robot Lab v2, hexapod 1 protocol runs | 115 (107 with a run dir) | 95 | 40 wide (1 Hz) + tracker frames (~5 Hz) per dataset |
| old lab (2026-09-03..10), hexapod 1 | 76 (2 simulated) | 22 | preflight/recovery stills only |
| hexapod 2 imports | 52 | 37 RL drive CSVs | 11 camera-measured walks with mkv |

4,073 wide frames total, not the 55,000 I quoted earlier; the rest are per-dataset tracker frames. 72 events indexed, 32 contact sheets cut.

## Ten measured facts

1. **Only 15 of 107 v2 runs (14%) are the robot physically failing to do what was asked.** 76 ran clean. Of the 31 failures, 10 never ran a tick (no trace CSV, robot not ready, state stream incomplete, empty error), 4 were bus comms (missed reads, write timeout, joint not answering) and 2 were overcurrent trips on a 124.8 A / 126.5 A reading, which is telemetry garbage, not a servo. Harness and telemetry account for 16 of the 31 failures; the robot for 15 (7 overcurrent, 5 start-pose, 3 tracking).
2. **Unloaded, the servos track to a third of a degree.** Median mean tracking error over the 74 clean v2 runs with CSVs is 0.3 deg (single-leg ladders 0.2, stand holds 1.0, whole-body 0.9). The gait problem is not open-loop tracking on an unloaded leg.
3. **Standing, the knees sag 2 to 6 deg below command, and the sag builds over the hold.** In all five 120 to 131 s champion stand holds the end-of-segment signed error is negative on every knee: L2 knee 3.6 to 6.4 deg, L4 knee 3.3 to 6.1 deg, the others 1.5 to 3.8. Hips stay within 2.3 deg. In the two 15 s stands every knee is still within 1.6 deg, and on the belly (droop map, 5 runs) every joint is within 1 deg. Droop is a loaded-knee phenomenon of about 5 deg that takes longer than 15 s to develop, worst on L2 and L4.
4. **The same knee twice could not reach the commanded stand at all.** Both champion stand tracking trips are L2 knee: commanded 89, present 57 and 56 deg (30 deg error, the trip threshold) within the first 6 s, as the robot rose. Either the geometry cannot get there under load or the logical zero on that knee is off.
5. **Trips cluster on four joints.** L0 hip 5 (4 start-pose verify failures at 3.4 to 4.4 deg after glide, tolerance 3, plus one tracking trip where it fell from +18.7 commanded to -12.7 present under the static tripod weight shift), L4 knee 4 overcurrent (0.39 to 2.34 A, all between 20:58 and 23:09 on 09-10), L2 hip 3 overcurrent (1.07 to 2.27 A under tripod weight shift and step amplitude), L2 knee 2 tracking. Over all 95 CSVs the worst-tracking joint in a run is L0 hip 21 times, L5 hip 20, L2 knee 15, L1 hip 14. Yaw joints never exceed 0.3 deg mean.
6. **Current is low except at the trips.** Per-joint mean current is at or below 0.06 A everywhere; the highest non-garbage peaks in the archive are 2.94 A (L4 knee) and 2.35 A (L2 hip). Bus voltage sits at 11.2 V median and dipped below 9.5 V in five clean runs (minimum 7.2 V). The trace's single temperature column reached 95 C once and 83 C at the 90th percentile of runs.
7. **Camera-measured walking delivers 10 to 45% of the commanded speed on the RL policies.** hexapod 2, 80 mm/s commanded: walkteach forward 15.4, 28.5, 37.7 mm/s; walkteach reverse 7.1, 7.4; allheading MLP 6.5 to 11.4; the ps200 speed policy 1.5. Scripted gait 1 on hexapod 2 at 30 mm/s gave 21.1 mm/s (70%) but yawed 60 deg over the walk. Hexapod 1, scripted gait 1 at 30 mm/s by hand today: 8.7 mm/s (29%), 10 deg heading change, floor tag lost after 2.2 s.
8. **Tilt while walking is a few degrees RMS on hexapod 2.** 1.4 to 6.1 deg RMS, peaks 3.5 to 15.9 deg, worst on the ps200 policy and the stotight45 seed. Hexapod 1 has no comparable walking IMU trace yet; its stand and ladder runs read 4.7 deg RMS from the tracker's IMU field, which is mostly the 3.3 deg belly-rest pitch, not motion.
9. **The runner's logs mislead in two places.** The cmd column lags the measured position at segment boundaries, so the 52 and 60 deg "hip errors" in `steps_loaded_v1` are the log, not the servo (q reaches -39 a second before cmd shows -39). And 310 tick overruns are spread across the 95 runs at 10 Hz. Neither is physics.
10. **Most of the failure video barely shows the robot.** In the tracker frames saved with the datasets, camera 2 has the robot at the top edge of the frame in the early-evening 09-10 runs (the four sheets checked from 20:13 to 21:20 show it rising or standing there) and outside the frame in the late ones (23:09 onward show only floor tags); only 4 of the 15 robot trips have wide-camera frames, and there the robot is a small cluster in a corner. The hexapod 2 walks are fully on camera. The old lab's hysteresis numbers (L0 -0.97 deg, L3 -0.67/-0.70, L4 -0.70 deg = 8 counts, L2 about half of L5) remain the only per-joint mechanical measurements we have.

## Three failure modes, with the best frames we have

**A. Loaded knees fold or stall (L2, L4).** Facts 3, 4, 5. Sheets: `sheets/trip_2976cb149f77_tracking_j8_tracker.jpg` (the L2 knee stall: the robot is at the top edge of camera 2, flat until -1.5 s, then rises and trips at tick 61), `sheets/trip_7a3e8b8b4cc5_overcurrent_j7_wide.jpg` (L2 hip 2.27 A during the tripod step amplitude ladder, robot standing top-left of the wide frame). The hold-90 knee sag is the same phenomenon at a lower level and is the cheapest thing to measure before and after any mechanical change.

**B. L0 hip drifts under load.** Fact 5. It fails the 3 deg start-pose check four times, is the worst joint in 21 runs, and collapsed 31 deg under the static weight shift. Sheet: `sheets/trip_e39c9594ff9d_tracking_j1_wide.jpg` (robot top-left of the wide frame, 6 s before to 2 s after). The two L0 hip mounts are also the two with no tag, so the camera cannot yet see this joint move.

**C. Harness and telemetry, not the robot.** Fact 1 and 9: 10 plumbing, 4 comms, 2 garbage-current trips, plus the lagging cmd column and the tracker camera framed on the wrong patch of floor. Sheet: `sheets/trip_2e256f3a0386_overcurrent_j0_wide.jpg` (the 126 A "trip": nothing happens in the frames). Half the failed runs and most of the lost video are here.

## Hypotheses and the cheapest test that kills each

| # | hypothesis | archive evidence | cheapest test |
|---|---|---|---|
| 1 | Horn screws are loose, so the horn moves and the output shaft does not: the wiggle is slop after the encoder | None either way. Every CSV reads the output-shaft encoder, so slop is invisible to all 95 traces. Only the operator's eyes and this morning's two-lid disagreement on legs 2 and 3 point at it | One leg, one minute: command each joint of L2 to +20 then -20 with the lids in camera 2, compare lid rotation to the encoder delta. Then tighten L2's horn screws and repeat `champion_stand_ground_hold90_v1`; if L2 knee sag drops from 4 to 6 deg toward L3's 2.5, the slop was the sag |
| 2 | Knee sag is the servo running out of torque at this stance height, not slop | Sag is knee-only, largest on L2 and L4, absent on the belly | Swap the L2 and L3 knee servos; if the 6 deg follows the servo it is the servo. Or hold the stand at two heights and see whether sag scales with knee load |
| 3 | L0 hip has a wrong logical zero or a loose horn | 4 start-pose misses at 3 to 4.4 deg, the 31 deg collapse, 21 worst-joint runs | Re-run `set_zero` on joint 1, glide to start three times and log the resting offset; then a 20 s hold with the wide camera on leg 0 |
| 4 | The 124 A overcurrent trips are bus garbage | 124.8 and 126.5 A are impossible on this bus; the hard limit trips on 2 consecutive polls | In the on-robot runner, treat any single read above 10 A as a bad read and drop it, then require 3 good consecutive polls, as the soft limit already does |
| 5 | The RL policies are slow because they shuffle, not because the servos lag | Speed 10 to 45% of command; knee swing 8 to 13 deg; the gait clock transfers exactly (sim audit) | The seven `walk_*` protocols already queued, run with camera 2 on the robot: speed, drift and tilt per commanded speed for scripted gait 1 first, then the policies |
| 6 | Half the lab's failures are the harness | 16 of 31 | Before the next batch: a look that confirms the robot is inside camera 2's frame, the wild-read guard above, and a cmd/q timestamp fix in the trace |

## What I would do next, in order

1. Fix the harness (hypotheses 4 and 6) before running more physics; otherwise a third of the new runs will fail for reasons that teach nothing.
2. Spend one afternoon on hypothesis 1: camera sweep of L2's three joints, tighten horns, repeat the hold-90 stand. This is the only test that speaks to what the operator sees, and the stand-sag number is already a repeatable before/after metric.
3. Then the walk queue with the robot in camera 2's view, scripted gait 1 first, so hexapod 1 gets the same speed-versus-command curve hexapod 2 already has.
