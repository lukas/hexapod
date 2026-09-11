# Gaits on hexapod 1 and hexapod 2 vs their MuJoCo versions (2026-09-11)

Every gait run both robots have made through Robot Lab v2, compared with the
simulation each one came from. Hardware numbers are computed from the per-tick
CSVs the runners already save, with `sysid/gait_metrics.py` (new; run it on any
run's CSV). Sim numbers are read from the eval files named in each row. Builds
on `WALKING_REVIEW_2026-09-05.md` and `artifacts/gait14_acceptance/` (the
laptop session's committed output; nothing else from it is in the repo).
Each finding is also filed against its run in the lab (`hexapod-lab2 note`),
with the contact sheets attached.

## Three sim populations, not one

| family | model | mass | used for |
| --- | --- | --- | --- |
| full mesh (Mac only) | `mesh_mujoco/hexapod_mesh.xml` | 3.49 kg | acq1_stdanneal rollout, walkteach sim screen |
| checked-in twin | `mesh_mujoco/hexapod_mesh_mjx.xml` | **4.81 kg from 09-03 to 09-11** (bug, fixed 09-11) | every pod gate in that window, incl. cap29 50/100 Hz, gait-14 sim screen |
| legacy primitive | `mujoco_prototype.py` | old geometry, leg chain ~46 mm high | dep_tip1, stotight45, amp_phasehz11_s29 |

Only acq1_stdanneal has a directly recorded sim speed (vx median 0.031 m/s).
Every other sim speed below is `progress_ratio x commanded speed`.

## Hexapod 2 (RL policies and scripted gaits, 2026-09-10)

| gait | sim speed (family) | hardware speed | stride Hz cfg / hw | hw cmd amp yaw/hip/knee deg | hw tracking err mean/max deg | hw roll, pitch range deg | run |
| --- | --- | --- | --- | --- | --- | --- | --- |
| walk_allheading_mlp_singleframe_acq1_stdanneal, 100 Hz, cmd 0.08 | 0.031 med (full mesh); progress 0.42 | ~1 m in 31 s on camera ≈ 0.032 fwd; 35 s rev | 1.333 / 1.32–1.35 | 7.5 / 12.5 / 10.8 | 3.3 / 11.7 | ±3, ±3 | c728d29657ef, 37d4c5856748 |
| walkteach_scripted_allhead_acq12m, 100 Hz, cmd 0.08 | ≈0.025 (0.318 x 0.08, full mesh screen) | not tag-measured; visually "~2x allheading" (learning) | 1.333 / 1.33 | 13.8 / 12.6 / 13.0 | 4.6 / 11.5 | −2.7..2.9, −2.0..0.3 | e9ab4b1873c7 |
| amp_phasehz11_s29, 25 Hz, cmd 0.06 | ≈0.085 (prog 1.06 x 0.08, primitive) | not measured (heading drift; turn attempt guard-aborted) | 1.1 / 1.08 | 17.5 / 32.4 / 21.0 | 8.7 / 32.1 | 1.0..6.5, −1.6..6.9 | e9ab4b1873c7, 8c28b0dbd205 |
| dep_tip1, 25 Hz, cmd −0.05 | ≈0.05 (prog 1.01, primitive) | "one body width" in 6 s, yawed; ≈0.03 | — / 0.33 knee, 0.5 hip | 46 / 60 / 48 | 7.2 / 15.8 | −10.5..0.8, −0.9..8.9 | c728d29657ef |
| cap29 recurrent turn/standwalk, 100 Hz | ≈0.022 (prog 0.27, **4.81 kg twin**) | not measured: 12.8 ms/tick, guard abort at 3 s | 1.333 / — | — | — | — | 7ac4e81da79b, 8c28b0dbd205 |
| stotight45 joystick, 25 Hz | ≈0.046 (det prog 0.58, primitive) | not measured: guard abort at 2.1 s | — | — | — | — | 8c28b0dbd205 |
| scripted no-slip tripod GAIT 1, cmd 30 mm/s | sim harness default is 20 mm/s cmd; CLAMP_FIT travel ratio 0.96 at 13 mm/s (Aug) | 9–12.5 mm/s (suite px scale 0.1 m/223 px vs notes "10 cm per 8 s"): travel ratio 0.3–0.4 | 0.31 / — | — | — | level on camera | 8c28b0dbd205 |

Per-leg knee swing, AMP walk: 30.7, 18.2, 21.6, **8.8**, 26.6, 20.3 deg. Leg 3
swings a third as far as its neighbours. Walkteach: 15.4, 11.1, 12.9, 15.2,
12.7, 10.6 (even). Allheading fwd: 12.2, 7.9, 11.9, 10.0, 9.7, 11.0.

The repo's tracking docs say amp, cap29 and stotight45 have never run on
hardware. They have (rows above, 2026-09-10 on hexapod2); the lab database is
now the record, the docs are stale.

## Hexapod 1 (sysid whole-body protocols, 2026-09-10/11)

No sim counterpart exists: `sysid/replay.py` is fixed-base with contacts off,
so the loaded whole-body protocols cannot be replayed. The comparison is
commanded vs measured, against a sim that delivers the command exactly.

| protocol | cmd hip amp deg | measured hip amp | tracking err mean/max | cycle Hz | current max A | run |
| --- | --- | --- | --- | --- | --- | --- |
| tripod step in place, 15 mm lift, 25 Hz | 10.5 | 8.8 (−16%) | 0.7 / 6.2 | 0.112 | 0.55 | ec02c879c8f2 |
| same, second run | 10.5 | 8.6 | 0.8 / 6.7 | 0.112 | 0.75 | 35d88e1cb7c3 |
| lift ladder 15/25/35/45 mm, 10 Hz | 29.6 | 27.4 | 0.9 / 13.8 | 0.074 | 0.53 | cb3b0231e0e9 |
| static weight shift v2, 6 mm, 10 Hz | — | — | (clean, 0 overruns) | 3 cycles / 126 s | — | 5f79e4b7dd71 |

At 15 mm commanded lift the wide camera saw no clearance; the 2 deg of hip
the loaded joints give up is the whole 15 mm. The ladder to 45 mm is what
produced visible lift. Stride cycle here is 0.07–0.11 Hz, ten times slower
than the RL policies' 1.33 Hz, by design (isolating load transfer).

Scripted gaits 9 and 14 on hexapod 1 (Sep 3, tag-tracked, 16 trials): 20.9
and 17.6 mm/s forward at 30 mm/s command vs 25 mm/s in sim (ratio 0.84 sim,
~0.6–0.7 hardware). Different gait from hexapod2's GAIT 1 (period 2.65 s vs
3.2 s, lift 16 vs 28 mm), so not directly comparable; both are below sim.

## What is the same

- Stride frequency. Both 100 Hz policies run on hardware at exactly their
  configured phase clock (1.333 Hz), measured from the knee commands. The
  AMP policy likewise: 1.1 configured, 1.08 measured.
- Allheading speed and look. ~0.032 m/s on camera vs 0.031 sim median; the
  tucked, low, legs-pulled-in stance in the sim rollout frames is what the
  floor camera shows. The "speed-softness" is the policy, not the robot.
- The shuffle. Both robots' RL gaits drag feet in swing; sim charges nothing
  for it (HARDWARE.md), and the hardware knees swing 8–13 deg.

## What is different

- Tracking error. Hardware command-to-position error is 3–9 deg mean and
  12–32 deg max on every RL gait; the sim servo fits are sub-degree. The
  legacy 25 Hz policies with big swings (dep_tip1 60 deg hip, AMP 32 deg) are
  worst.
- Tilt. Scripted gait sim tilt is 0.2–0.5 deg; hardware RL gaits roll/pitch
  3 deg (100 Hz policies) to 7–10 deg (AMP, dep_tip1). Hexapod1 gait-14 IMU
  peaked at 10.3 deg on Sep 3 against 0.27 deg in sim.
- Progress ratio of the open-loop gaits. Sim is optimistic for no-slip gaits
  (0.84 vs 0.6–0.7 on hexapod1, 0.3–0.4 for GAIT 1 on hexapod2) and
  pessimistic for the drag gait (GAIT.md: 0.35–0.41 sim vs 0.50 real). Same
  floor, opposite sign: the contact model, not friction, is the gap.
- AMP. A sim progress ratio of 1.06 arrived on hardware as 32 deg hip swings,
  7 deg tilt, heading drift and one leg barely lifting, not as speed.
- Loaded droop on hexapod1. Every weight-bearing hip settles 2–4 deg short
  of command; the sim has no such compliance, so any sim lift under ~20 mm is
  fiction on this robot.
- Mass. Anything gated on the pod twin between 09-03 and 09-11 was scored on
  a robot 38% too heavy; cap29's numbers need re-running before comparison.

## Still missing

Camera speed for walkteach and AMP (the tag tracker only ran for the scripted
suite), any sim replay of the whole-body protocols on the ground, and a
smoothness metric in the loop itself. `gait_metrics.py` is the start of the
last one: run it after every run and file the numbers with `hexapod-lab2 note`.
