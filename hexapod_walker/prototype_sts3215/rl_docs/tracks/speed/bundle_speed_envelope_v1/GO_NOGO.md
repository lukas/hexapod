# speed-envelope-v1 — GO/NO-GO (2026-09-11, refill cycle)

## Verdict: GO for sim-demo readiness (new track frontier). NOT a physical-acceptance verdict; widening the actuator envelope from 37.5 to 50 deg/s is a real change Robot Lab must independently verify (bus/slew/current contract) before any hardware trial — this doc proposes the sim recipe, not the hardware change.

One plain sentence: opening the actuator envelope (37.5->50 deg/s) plus
stacking a teacher `stride_scale=1.4` dose breaks the stride-geometry
ceiling `bundle_stride_ps_v1` plateaued at, clears the track's own named
0.08 m/s initial-simulation-milestone for the first time, and now
supersedes that older bundle as the track's frontier pick — this doc
names the new candidate, records its own interactive sim demo, and
retires the superseded bundle without deleting its (still-valid, safer,
narrower-envelope) evidence.

## Candidate (new track frontier)

`cw-speed50hz-env50dps-ps200-ss14-sr105-disc2m` (2M discovery) and its
`-acq10m` (10M) sibling — same-tier alternates, per `STATUS.md` 2026-09-11
~17:3x/~18:2x entries. Mechanism: `env.motor.write_speed=570`
(50.1 deg/s slew, up from the legacy 37.5 deg/s contract) stacked with
`train.bc_anchor_teacher_stride_scale=1.4` (teacher stride-length dose,
first tested in combination with the wider envelope this cycle) and the
already-adopted `period_scale=2.0`/`lift_scale=1.4`/`stance_radius_scale=1.05`
geometry doses. Mesh model, 50 Hz control, `model_mass_kg=3.490038`
(post mass-audit-bug fix).

| pin (m/s cmd) | det (disc2m) | det (acq10m) | sto (disc2m) | sto (acq10m) |
|---|---|---|---|---|
| 0.06 | 0.063 | 0.062 | 0.0665 | 0.061 |
| 0.08 | 0.075 | 0.074 | 0.072 | 0.073 |
| 0.10 | 0.078 | 0.081 | 0.0775 | 0.078 |
| 0.12 | 0.082 | 0.084 | 0.0775 | 0.0815 |

Both checkpoints: zero falls across the full acquisition gate + speedpanel
+ retention reads (88-104 held-out episodes each, see `STATUS.md`
~17:3x/~18:2x), `gait_valid` clean on every row, zero sacrificed legs, det
slip/m 1.08-1.68 (cap 1.8), roll/pitch peaks <=4.8deg det / <=6.0deg sto.
RETENTION at the legacy 37.5 deg/s contract: 0 falls, `gait_valid` clean —
either checkpoint has a safe legacy fallback if the envelope change is
rejected for hardware.

**Track milestone: the named 0.08 m/s initial-simulation-milestone target
is now MET** (0.081-0.084 m/s det at the 0.10-0.12 pins) — the first
recipe on this track to clear it (`bundle_stride_ps_v1`'s ps175/ps200
pair plateaued at 0.045-0.052 m/s across the same command range).
Command-sensitivity is also restored for the first time: speed now
tracks the command (0.062-0.084 m/s det across 0.06-0.12) instead of the
flat command-invariant ceiling every pre-envelope stride/period/lift
lever showed — this is the track's OTHER standing open question
(named in both bundles' "still open" section) substantially addressed
as a side effect of the same lever.

## Interactive sim demo (captured this cycle, closing the "visible demo"
gap for this candidate — none existed before this entry)

`ops.sh drivevideo cw-speed50hz-env50dps-ps200-ss14-sr105-disc2m --script human --seconds 20`
→ `logs/manual_drive/cw_speed50hz_env50dps_ps200_ss14_sr105_disc2m_drivevideo_20260911_233652/`
(contact_sheet.png, drive.mp4, summary.json). Full-mesh model, controller
CPU, stochastic policy, 20 s, `--script human` (direction changes mid-run
— contact sheet shows the commanded-direction arrow rotating with real
six-leg tripod cycling, body level, no drag/paddle-creep/skate). Numbers:
`gait_valid=true`, `sacrificed_legs=[]`, `progress_ratio=0.73`,
`slip_per_m=1.458`, `cur_max_a=2.639`/`cur_p95_a=1.726` (inside the
motor_contract's own resolved 50.1 deg/s slew rail), `course_err_1s_med_deg=8.96`,
`wrong_course_frac_1s=0.019`. Duty cycle balanced across all six legs
(0.43-0.60), `swing_count` 12-16 per leg over 20 s — genuine six-leg
participation, not a partial-leg gait.

## Relationship to `bundle_stride_ps_v1` (previous frontier, 09-11 morning)

`bundle_stride_ps_v1` (`ps175-lift14-acq20m`/`ps200-lift14-acq20m`,
0.045-0.052 m/s, 37.5 deg/s legacy envelope) is SUPERSEDED as the track's
speed frontier by this bundle but remains a valid, safer (narrower
actuator envelope, no hardware-contract change needed) alternate — its
own GO/NO-GO doc is stamped with a pointer to this one. Do not discard
its evidence; it is the right choice if Robot Lab rejects the wider
slew envelope for hardware reasons.

## What's still open (per `STATUS.md` Next)

- No further acquisition continuation of this exact `ss14`/`env50dps`
  recipe is funded — `acq10m` already tested the "more budget" question
  and plateaued within noise of `disc2m` (same ceiling-plateau shape as
  every prior acquisition-depth question on this track).
- Raising `TripodGait.SCALE_PERIOD_MAX` past 2.0 is CLOSED (zero-training
  sweep shows a decline past 2.5, no code change needed to test it).
- Envelope rungs above 65 deg/s are not funded (dose-response already
  flattens 50->65 while quality degrades monotonically).
- Physical trials remain Robot Lab-owned. This doc proposes the sim
  recipe only; the 50 deg/s (570 counts/s) slew envelope is a REAL
  actuator-contract change from the legacy 37.5 deg/s hardware default
  and needs Robot Lab's own bus/slew/current verification before any
  physical trial — this doc makes no claim that hexapod2's real servos
  tolerate 50 deg/s continuous slew, only that the sim model does.

## Evidence

- `rl_docs/tracks/speed/STATUS.md` 2026-09-11 ~14:0x, ~14:4x, ~15:3x,
  ~16:4x, ~17:3x, ~18:2x entries (full derivation, panels, verdicts).
- `logs/ckpt_eval/cw_speed50hz_env50dps_ps200_ss14_sr105_{disc2m,acq10m}_{gate,speedpanel,retention}/report.json`
- `logs/manual_drive/cw_speed50hz_env50dps_ps200_ss14_sr105_disc2m_drivevideo_20260911_233652/`
- `ops.sh entry cw-speed50hz-env50dps-ps200-ss14-sr105-{disc2m,acq10m}`
