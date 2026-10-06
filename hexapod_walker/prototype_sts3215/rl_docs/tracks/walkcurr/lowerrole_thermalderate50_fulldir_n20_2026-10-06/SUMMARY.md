# thermalderate50-s2 full-direction composed readiness check (2026-10-06, idle-kick refill cycle, zero GPU spend)

## Why this item exists
The 3-seed `thermalderate50` population (s0=31/36, s1=32/36, s2=33/36,
all three individually clearing the >=30/36 PASS-MECHANISM bar, mean
88.9%, zero `over_current`) just closed walkcurr's 16-lever L2+L5
lower-role investigation and was ADOPTED as the new standard lower-role
training recipe (`walkcurr/STATUS.md`, `ops.sh index story
cw-stance50hz-rlonly-lowerrole-scratch-sac-s2-drramp-thermalderate50-acq1`).
That population number is FORWARD-ONLY (`heading_deg=0.0`, no `--rot60`).
Before promoting this checkpoint into `bundle_rlonly_lifecycle_v2`
(todaypolicy), the same off-axis precondition the old `drramp-acq1 s0`
champion needed (`lowerrole_truechamp_fulldir_n20_2026-10-03`) applies
here too: does the forward number hold up at all 8 commanded headings,
or does it collapse off-axis?

## Method
Same tooling, zero code changes: `eval_lifecycle_handoff_rlonly.py
--walk slew_smooth_s0 --rot60 --lower <thermalderate50-s2 ckpt>
--lower-recipe lowerrole_sac_drramp --lower-cfg
motor.thermal_derate_enable=1 --lower-cfg motor.thermal_derate_max_frac=0.5
--episodes 20 --heading-deg <H> --seed 0`, all 8
`PINNED_HEADING_DEFAULTS` headings, n=20/heading/arm (n=160/arm total),
CPU MuJoCo only, launched in parallel via `ops.sh localbg` (registered,
not babysat). The `--lower-cfg` flags replay the candidate's own training
delta (`motor.thermal_derate_enable=1/max_frac=0.5`), matching the
convention `pod_eval.lifecycle_lower_cfg_delta` already uses for the
registered composed gate (a physics key, correctly replayed, not a
curriculum-only key per the holdonly100 confound fix).

## Finding: NO off-axis collapse -- the champion generalizes full-direction, at a HIGHER rate than the forward-only official gate number

| heading | direct lower_ok | direct falls | plant lower_ok |
|---|---|---|---|
| -135 | 20/20 (100%) | 0 | 20/20 (100%) |
| -90  | 19/20 (95%)  | 1 | 20/20 (100%) |
| -45  | 19/20 (95%)  | 1 | 20/20 (100%) |
| 0    | 20/20 (100%) | 0 | 20/20 (100%) |
| +45  | 18/20 (90%)  | 1 | 20/20 (100%) |
| +90  | 19/20 (95%)  | 1 | 20/20 (100%) |
| +135 | 19/20 (95%)  | 0 | 14/20 (70%)  |
| 180  | 19/20 (95%)  | 0 | 20/20 (100%) |
| **TOTAL** | **153/160 (95.6%)** | **4/160** | **154/160 (96.2%)** |

Flat across all 8 headings (90-100% range, within binomial noise at
n=20/cell around a true ~95% rate) -- no heading-sign split, no
forward-good/off-axis-bad shape. The one weak cell (plant@+135, 70%) is
the PLANT arm (walk-role's own clean reset -> lower, isolating momentum),
not the DIRECT arm that matters for the real composed lifecycle, and is
a single cell at n=20 (binomial noise plausible, not investigated
further here). This 95.6% direct rate is noticeably HIGHER than the
official registered composed gate's own forward-only number for this
same checkpoint (33/36=91.7%, no `--rot60` wrapper) -- consistent with
the already-established finding (bundle_rlonly_curvewalk_v1 forensics)
that `--rot60` sector-canonicalization does not hurt and sometimes
modestly helps this family, not a contradiction.

## What this does and does not change
**Clears the precondition** `todaypolicy/STATUS.md` Next item 0 named:
promotion of `thermalderate50-s2` into `bundle_rlonly_lifecycle_v2` as
the new `lower` component is now evidenced full-direction, not just
forward. **Does not** itself edit the manifest (done in the same cycle,
separately, citing this file). **Does not** claim a physical/hardware
read -- sim-only, CPU MuJoCo, no GPU spend, no robot motion.
