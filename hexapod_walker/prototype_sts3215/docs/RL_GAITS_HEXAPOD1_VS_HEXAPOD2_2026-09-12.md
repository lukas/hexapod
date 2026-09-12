# RL gaits: hexapod 1 vs hexapod 2 (2026-09-12)

Same policy files, same commanded speeds. hexapod 2's numbers are its 2026-09-11 tag-grid session (floor camera, 2 fps fixes, straight-line speed). hexapod 1's are Robot Lab v2 walk runs on 2026-09-12 (camera 1, net start-to-end speed over the leg, out and back). Speed is the camera's, not the command.

| gait | robot | cmd mm/s | measured mm/s | heading change deg | tilt max / rms deg | stop | runs |
|---|---|---:|---:|---:|---|---|---|
| allheading 100 Hz | hexapod1 | 80 | 0.1-0.1 | +0..+0 | - / - | frame_edge | 2 |
| allheading 100 Hz | hexapod2 | 80 | 6.5-11.4 | -8..+9 | 7.8 / 4.0 | done | 3 |
| scripted gait 1 | hexapod1 | 30 | 4.7-22.6 | -2..+8 | 20.5 / 9.3 | duration; servo at 56 C | 3 |
| scripted gait 1 | hexapod2 | 30 | 21.1 | 60.1 | - / - | done | 1 |
| speed ps200 50 Hz | hexapod1 | - | not run | - | - | - | 0 |
| speed ps200 50 Hz | hexapod2 | 100 | 1.5 | 2.0 | 15.9 / 6.0 | done | 1 |
| stotight45 25 Hz | hexapod1 | - | not run | - | - | - | 0 |
| stotight45 25 Hz | hexapod2 | 60 | 2.3 | -0.6 | 8.2 / 4.0 | robot tag lost for 6 s | 1 |
| walkteach 100 Hz | hexapod1 | 80 | 1.2-3.3 | -0..+0 | 4.3 / 4.3 | drive session ended: no drive ; frame_edge | 3 |
| walkteach 100 Hz | hexapod2 | 80 | 7.1-37.7 | +2..+13 | 5.6 / 2.0 | done | 5 |

## What hexapod 1 could and could not do on 2026-09-12

- **Scripted gait 1, 30 mm/s, 10 s legs (run dbe7def67e34):** forward 4.7 mm/s net, back 22.6 mm/s net; heading change +7.5 / -2.4 deg; tilt RMS 8.5 deg, max 20; total current 0.33 A. hexapod 2 on the same command: 21.1 mm/s with a 60 deg yaw. hexapod 1's gait is asymmetric (back is five times faster than forward) and rolls twice as much.
- **RL walks did not produce a number.** Every policy file hexapod 2 ran is now on hexapod 1 and reported runnable. The drive session opens and streams (the first attempt failed only because the runner sent its first command before the asynchronous session was live; fixed). What stopped them was position: the robot stood at the bottom edge of camera 1's frame and the frame-edge guard ended each leg within a second. The eight RL protocols are queued on the lab for when the robot is placed mid-frame.
- **The gait's stop pose blocks the next command.** After each 8 s of scripted gait the swing tripod (legs 0, 2, 4) is left mid-stride, 20-32 deg from walk-ready, and the drive refuses the next J command until the robot is re-stood. hexapod 2 recorded the same on 2026-09-11 (run e3d29d962f0d). It is not a joint fault: the encoders read what the gait commanded and the 120 s hold sags under 0.8 deg. The walk runner now re-stands once and retries. (The earlier reading of this as an L0 knee horn slip was wrong and is retracted.)
- **Camera 1's fixes are noisy.** The chassis tag jitters by tens of millimetres per fix (path speed 120-175 mm/s against a net 5-23 mm/s), so net start-to-end speed is the number to compare, as hexapod 2 did. Camera 1 is calibrated from four floor tags in one part of its view; hexapod 2's extra surveyed tags did not fit it (20 px rms) and were not kept.

## Every leg

| robot | run | gait | leg | cmd | s | mm/s | heading | drift | tilt max/rms | current A | hottest C | service ms | overruns | stop |
|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| hexapod1 | 8ba2de3333c1 | allheading 100 Hz | allheading_fwd | 80 | 0.1 | 0.1 | 0.1 | - | -/- | - | - | - | - | frame_edge |
| hexapod1 | 8ba2de3333c1 | allheading 100 Hz | allheading_fwd_back | -80 | 0.5 | 0.1 | 0.1 | - | -/- | - | - | - | - | frame_edge |
| hexapod2 | 7c968b7792ca | allheading 100 Hz | allheading fwd | 80 | 11.0 | 11.4 | 9.0 | - | 6.9/4.0 | - | - | 9.6 | 389 | done |
| hexapod2 | ca3e7039d1d6 | allheading 100 Hz | allheading fwd | 80 | 13.5 | 9.5 | 2.0 | - | 7.8/4.0 | - | - | 9.6 | 374 | done |
| hexapod2 | a8422106c7b0 | allheading 100 Hz | allheading fwd | 80 | 6.9 | 6.5 | -8.3 | - | 3.8/1.4 | - | - | 10.1 | 437 | done |
| hexapod1 | 4109077fd1a7 | scripted gait 1 | fwd30 | 30 | 2.6 | 21.4 | 3.7 | -10.5 | 16.7/9.3 | 0.47 | 56 | - | - | servo at 56 C |
| hexapod1 | dbe7def67e34 | scripted gait 1 | fwd30 | 30 | 10.1 | 4.7 | 7.5 | -31.2 | 13.2/8.5 | 0.33 | 51 | - | - | duration |
| hexapod1 | dbe7def67e34 | scripted gait 1 | fwd30_back | -30 | 10.0 | 22.6 | -2.4 | -23.6 | 20.5/8.6 | 0.34 | 46 | - | - | duration |
| hexapod2 | 8b33c3a239e3 | scripted gait 1 | scripted gait1 noslip tripod | 30 | 11.2 | 21.1 | 60.1 | - | -/- | - | - | - | - | done |
| hexapod2 | cc274e771141 | speed ps200 50 Hz | speed ps200 fwd 0.10 | 100 | 2.7 | 1.5 | 2.0 | - | 15.9/6.0 | - | - | 19.2 | 48 | done |
| hexapod2 | 867eb750b497 | stotight45 25 Hz | stotight45 fwd 0.06 | 60 | 1.4 | 2.3 | -0.6 | - | 8.2/4.0 | - | - | 38.9 | 0 | robot tag lost for 6 s |
| hexapod1 | 943b8bc89f8a | walkteach 100 Hz | walkteach_fwd | 80 | 0.3 | 3.0 | -0.2 | - | 4.3/4.3 | 1.37 | 36 | - | - | drive session ended: no drive session |
| hexapod1 | 5f64a8893a54 | walkteach 100 Hz | walkteach_fwd | 80 | 0.1 | 3.3 | -0.1 | - | -/- | - | - | - | - | frame_edge |
| hexapod1 | 5f64a8893a54 | walkteach 100 Hz | walkteach_fwd_back | -80 | 0.4 | 1.2 | 0.0 | - | -/- | - | - | - | - | frame_edge |
| hexapod2 | 59b526d18bb3 | walkteach 100 Hz | walkteach fwd | 80 | 14.4 | 28.5 | 5.3 | - | 5.6/2.0 | - | - | 9.6 | 363 | done |
| hexapod2 | 9aa024c6935a | walkteach 100 Hz | walkteach fwd | 80 | 14.7 | 15.4 | 2.2 | - | 4.6/1.8 | - | - | 9.5 | 384 | done |
| hexapod2 | 10f90c2597f3 | walkteach 100 Hz | walkteach fwd | 80 | 14.4 | 37.7 | 11.7 | - | 3.2/1.8 | - | - | 10.0 | 439 | done |
| hexapod2 | e6e216c01d62 | walkteach 100 Hz | walkteach reverse | -80 | 8.2 | 7.4 | 13.0 | - | 3.7/1.4 | - | - | 9.5 | 378 | done |
| hexapod2 | 65688bc6207c | walkteach 100 Hz | walkteach reverse | -80 | 13.7 | 7.1 | 2.0 | - | 2.8/1.5 | - | - | 10.0 | 423 | done |
