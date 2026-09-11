# speed-stride-ps-v1 — GO/NO-GO (2026-09-11)

**SUPERSEDED, 2026-09-11 ~23:5x (later same day):** the actuator-envelope
ladder (`env50dps`) plus a stacked `stride_scale=1.4` dose
(`cw-speed50hz-env50dps-ps200-ss14-sr105-disc2m`/`-acq10m`) clears the
track's own 0.08 m/s milestone this bundle's pair (0.045-0.052 m/s)
never reached, and is now the track's frontier pick — see
`../bundle_speed_envelope_v1/GO_NOGO.md`. This bundle's own evidence
stays valid and it remains the right choice if Robot Lab rejects the
wider (50 deg/s) actuator envelope for hardware reasons (this bundle
needs no slew-contract change from the legacy 37.5 deg/s default).

## Verdict: GO for sim-demo readiness (both candidates). NOT a physical-acceptance verdict; no actuator envelope change proposed.

One plain sentence: the speed track's own PASSing +20%-speed acquisition pair
(`ps175-lift14-acq20m`, `ps200-lift14-acq20m`) now each has a same-harness
interactive `--script human` sim demo on video, closing the "visible sim demo
per candidate" gap `STATUS.md` Next item 2 had left open, and this doc names
the Pareto tradeoff between them so a future reader doesn't have to re-derive
it from the eval JSON.

## Candidates (Pareto frontier pair, `TripodGait.stride_scale`/`stance_lift_scale` geometry lever)

Both: mesh model, 50 Hz control, `train.bc_anchor_teacher_period_scale`/
`_lift_scale` gait-geometry mechanism (`exp/speed-step0-teacherscales`),
20M-step acquisition, warm-started from their own 2M discovery checkpoint,
zero falls / zero sacrificed legs across the full acquisition gate panel
(det+sto, 4 pins x 2 modes, 80 held-out episodes total — see
`STATUS.md` 08:0x entry).

| | `ps175-lift14-acq20m` (smoother) | `ps200-lift14-acq20m` (frontier) |
|---|---|---|
| `period_scale` / `lift_scale` | 1.75 / 1.4 | 2.00 (`SCALE_PERIOD_MAX`) / 1.4 |
| Pinned-0.10 det speed | 0.045-0.047 m/s | 0.048-0.052 m/s |
| Pinned-0.10 sto speed | ~0.044 m/s | 0.045 m/s |
| Human-drive `progress_ratio` | 0.498 | 0.503 |
| Human-drive `slip_per_m` | 1.58 | 1.608 |
| Human-drive `course_err_1s_med_deg` | 5.55 | 5.1 |
| Human-drive `wrong_course_frac_1s` | 0.0 | 0.006 |
| `cur_max_a` / `cur_p95_a` | 2.624 / 1.34 | 2.609 / 1.319 |
| `sacrificed_legs` | [] | [] |
| `gait_valid` | true | true |

Both stay inside the conservative 0.75 deg/tick (37.5 deg/s) transfer slew
contract (`motor_contract.slew_limit_deg_s=37.5` in both drivevideo runs) —
no actuator-envelope change proposed for either.

**Tradeoff**: `ps200` is marginally faster and has a tighter det slip/course
error edge; `ps175` has marginally lower human-drive slip and zero
wrong-course frames. The two are within noise of each other on every axis —
neither dominates. `ps200` is named as the **frontier candidate** (closer to
the class's own `SCALE_PERIOD_MAX` geometric ceiling, useful if a future
mechanism raises that ceiling) and `ps175` as the **smoother alternate**
(same speed class, slightly quieter joystick feel). Either is promotable;
this doc does not force a single default the way `todaypolicy` does for its
composed bundle.

## Evidence (reproducible launch path)

- `ops.sh drivevideo cw-speed50hz-stride-ps200-lift14-acq20m --script human`
  → `logs/manual_drive/cw_speed50hz_stride_ps200_lift14_acq20m_drivevideo_20260911_080142/`
  (contact_sheet.png, drive.mp4, summary.json)
- `ops.sh drivevideo cw-speed50hz-stride-ps175-lift14-acq20m --script human`
  → `logs/manual_drive/cw_speed50hz_stride_ps175_lift14_acq20m_drivevideo_20260911_114522/`
  (contact_sheet.png, drive.mp4, summary.json)
- Full acquisition gate panels: `ops.sh entry cw-speed50hz-stride-ps{175,200}-lift14-acq20m`;
  `STATUS.md` 08:0x Update.

## What's still open (per `STATUS.md` Next)

- No sustained candidate yet reaches the named 0.08 m/s stretch milestone —
  both PASSing checkpoints plateau at 0.045-0.052 m/s across the whole
  0.06-0.12 command range (a geometric ceiling of this mechanism, not a
  training-budget gap; do not fund a 3rd acquisition continuation of the
  same recipe expecting more speed).
- Command-invariance (achieved speed not tracking commanded speed between
  0.03-0.05 m/s) is a named, unaddressed gap — a useful physical-delivery
  improvement even without a higher ceiling; no design yet.
- Physical trials remain Robot Lab-owned; this doc proposes no actuator
  envelope change and makes no physical-acceptance claim.
