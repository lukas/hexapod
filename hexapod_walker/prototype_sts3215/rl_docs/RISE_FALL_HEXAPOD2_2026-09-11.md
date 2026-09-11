# hexapod2 2026-09-11 — every rise and fall, with what to change

Source: robot event log (stand_route, standup, safe_zero, servo_fb sweeps), floor camera (cam2, 2 ft) and
overhead camera (cam1, 3 ft, from 14:23 PDT). 54 event windows, 78 clips (`clips/`, names are UTC
`HHMMSSZ_<kinds>_<camera>.mkv`, each starts 8 s before the event). PDT = UTC − 7 h.

## 1. STEP stand-up from belly (16 today; clips `*_stepup_*`)

What happens: `standup_modes.json` step mode = 18 keyframes, 8.96 s at 1x: tuck tripod A through the air
(keyframes 1–5), tuck tripod B (6–10), then PUSH all six legs straight up from hips −65 / knees 146 to
hips 21 / knees 82 (keyframes 10–17). `_acquire_start` plays it at **speed 10** ("step stand-up x10"):
the whole rise streams in 2.8–5.0 s and the push phase in well under a second. Telemetry on all 16 rises:
peak 1.30–1.77 A, knee load at the 70 % cap every time, settle error 0.8–2.9°. On video the body pops up
and rocks; this is the "rise up" the operator dislikes.

Change:
- Play the tuck phases fast (they are unloaded air moves) but the push phase (keyframes 10–17) at 2–3x,
  not 10x: ~1.5–2 s for the rise. One-line change in `api/zero.py::_acquire_start`
  (`speed=(6.0 if tuck_stand else 10.0)`) plus a per-keyframe speed field in `standup_modes.json`.
- Ramp the servo write profile for the push (`api/standup.py` lines ~332/335 use speed 400/acc 50 and
  300/40): acc 20 for the loaded frames.
- Stand up on tripods, not six legs: raise tripod A to half height, then B, then both to full height. The
  keyframe list already knows the tripods; a "push" split into two half-pushes removes the bounce.

## 2. Lower / drop through safe_zero, then rise again (5 today; clips `*_safezero_*`, `*_route_safezero+stepup_*`)

What happens: after a walk the pose is not walk-ready and the median foot is only 50–60 mm below the hip
pivot (a low crouch). `_stand_route_decision` only treats a robot as standing when the median foot is
> 65 mm below the pivot (STAND_DETECT 25 mm below the −40 mm belly plane), so this crouch is routed to
safe_zero: all six legs straighten (loaded blend at full torque or the low-drag descent), the chassis drops
to the belly, then a full x10 STEP stand-up follows. That is the "sit down then crash up" cycle
(13:18:50 PDT right before the leg 3 clamp broke; 14:38, 14:59). The 12:01 and 12:06 drops were the older
version of the same path (fold + loaded straighten) and are already fixed.

Change:
- Route any LEVEL robot whose median foot is below the belly plane at all (z < −45 mm) to the tripod
  glide, not safe_zero. It is standing, just low; the glide re-plants tripods and rises. Change the
  threshold in `_stand_route_decision` (`modelled_stand = mz < gz - STAND_DETECT_MM` → `mz < gz - 5`) and
  add a test with the 13:18:50 pose (median foot 53 mm).
- Where a real lower is wanted (`/api/rl/lower`), use STEP-down at 1–2x with the push phase reversed
  slowly, never the six-leg straighten. safe_zero stays for belly-down / tangled recovery only.

## 3. Tripod glide re-steps between runs (40+ today; clips `*_glide_*`, overhead view from 14:23)

What happens: each scripted orient turn and most RL runs end with one hip 25–66° from walk-ready, the
walk preflight fails, and `/api/rl/stand` re-steps the robot via `build_tripod_plant_transition`. It is the
right route (no drop) but it fires before every run, and the pre-glide tilt was 8–11° on nine of them.
One glide failed verification (L2 hip 27° off, 13:14:39) and the fallback is to hold, which is correct.

Change:
- Make the scripted gait stop (`J 0 0 0`) and the RL drive stop return to walk-ready themselves (one
  settle frame), so the preflight passes and the re-step is not needed.
- Widen the walk preflight tolerance for the RL start (25° → 35°) for hips only; the runner's own arming
  check already refuses > ~10° drift, so the glide only needs to fix large offsets.
- Log IMU roll/pitch per glide frame (servo_fb already carries joints; add tilt) so the 10° cases can be
  compared to the 1° ones.

## 4. Tilt trips and the fall (clips `*_trip_*`, 11:51, 12:53, 15:23 PDT)

What happens: preflight refused three times for tilt (roll 14.5/pitch 13.4; pitch −12.9; pitch −18.2) and
at 15:23 a goto tripped the runner's `tilt_pitch` safety at 25.1°. The robot had walked to the far end of
the grid next to hexapod-1 (its plate tag is unreadable there for both cameras) and the walkteach / allheading
hold poses leave the body pitched 8–16° (tilt_rel_max 16.1° on the allheading reverse just before). The
camera did not capture the fall itself: the robot was out of both views and a person then lifted it.

Change:
- Treat pitch/roll > 12° at the end of a run as "not walk-ready" and glide immediately, before the next
  command (the runner has the IMU; today the tracker only saw it via preflight refusals).
- Keep the arena guard's far-end limit at x ≤ 500 mm for hexapod2 while hexapod-1 sits at x ≈ 600.
- A hold policy should not leave the body pitched: after `drive/stop`, blend to walk-ready over 1 s instead
  of freezing the last policy pose.

## Bottom line

Today's hard landings are not one bug but one design choice used three times: all six legs move together
under load (STEP push at 10x, safe_zero straighten, STEP-down). Every gentle transition the robot already
does is a tripod move (the glide, the STEP tuck phases). Make every loaded height change a tripod move at
1–3x and route low-but-level poses to the glide, and the sit/rise cycle disappears.
