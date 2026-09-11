# todaypolicy-50hz-v1 — GO/NO-GO (2026-09-11)

## Verdict: GO for controller handoff (sim), NOT physical acceptance — first ALL-LEARNED stand+walk+lower composition at 50 Hz

One plain sentence: this is the operator's `op_20260910_50hz` bundle (stand/sit +
walk + turn, all retrained at the deployable 50 Hz control rate) assembled and
demoed end-to-end for the first time, with a genuinely learned stand-up and
lower (not the scripted `tuck` fallback the 100 Hz bundle used) plus a choice
of two straight-walk candidates and two turn-capable candidates — every 50 Hz
role landed by 09-11 ~09:2x now has a home in one composed, reproducible demo.

## Why now

`op_20260910_50hz` (hexapod2's MCU bridge trips the 100 Hz timing fault; 50 Hz
fits the 20 ms budget) named 5 retrain arms — walk x2, turn x2, stand/sit x1 —
to rebuild the `todaypolicy-mlpsf-tuck-v1` bundle at 50 Hz. By 09-11 ~09:2x all
5 arms had PASSED and exported (`RL_LOG.md` 09-10 21:05..09-11 08:20); nobody
had yet assembled them into one composition + demo + GO/NO-GO. This closes
that gap and, incidentally, closes `todaypolicy/STATUS.md` Next item 4
("Arc/turn remains open") for the first time — a validated turn-capable
candidate now exists and is named below, even though it is not the default
(see the tradeoff).

## Composition (roles + candidates)

| Role | Default candidate | Export | Alternate(s) |
|---|---|---|---|
| Stand (belly→walk_ready) + Lower (walk_ready→grounded) | `cw-stand50hz-...-curhot-b23k12` (learned, single policy handles hold+rise+lower) | `linux_control/policies/stand50hz_stance_tuckclock_scratch6m_curhot_b23k12.json` (obs 68, 50 Hz) | scripted `tuck` (`standup_modes.json`) remains the zero-risk fallback, same as the 100 Hz bundle |
| Walk (straight, joystick vx/vy) | `cw-walk50hz-allheading-mlp-singleframe-scratch-acq20m` | `linux_control/policies/walk_allheading_mlp_singleframe_scratch_50hz.json` (obs 74) | `cw-walk50hz-teach-scripted-allhead-scratch-acq10m-cont15m` -> `walkteach_scripted_allhead_scratch_50hz.json` (near-identical quality, alternate lineage) |
| Walk+turn (joystick vx/vy/wz, real turn authority) | `cw-turn50hz-standwalk-cap29-stdwalklohi-warmadapt-canary2m-acq1` (s0) | `turn50hz_standwalk_cap29_stdwalklohi_warmadapt_canary2m_acq1.json` (dual-GRU, obs incl. wz) | s1 twin `..._s1_acq1.json`, same band |

Both walk-role and turn-role files load into the SAME robot runtime slot
(`rl_walk_weights.json`, obs-width routed — see `linux_control/rl_policy.py`);
there is no separate hardware "turn slot". The operator/pilot picks
straight-quality (default) or turn-capable via the same picker, same as any
other walk-role swap.

## Why straight-only stays the DEFAULT walk role (not the turn-capable one)

Matched DR-0 gate numbers, same harness, same day:

| candidate | det progress_ratio med | det slip med | falls (24 walk-mode eps) | hold-mode falls |
|---|---|---|---|---|
| singleframe (default) | 0.41 | 2.19 | 0 | 0 |
| teach (alternate) | 0.38 | 2.57 | 0 | 0 |
| **cap29 turn-capable (s0)** | 0.27 | 3.87 | 0 | **2/6 det, 1/6 sto (`hold_min_load`)** |

The turn-capable policy is a real, validated capability (`probe_turn_authority`
wz_med +0.19/-0.19 rad/s, clears the >=0.14 bar with room, matches the 100 Hz
parent band) but is measurably softer on straight-line quality and shows new
hold-mode falls the straight-only candidates don't have. Per the same
tradeoff the 100 Hz bundle already made (deferred turn, shipped quality), the
default stays straight-only; the turn-capable export is registered here as
the first NAMED, PASSING answer to "how do we add joystick turning" rather
than left unbuilt.

## Demo (this cycle, full mesh, sim only — no physical robot contact)

`ops.sh hybriddemo cw-walk50hz-allheading-mlp-singleframe-scratch-acq20m \
  --stand-controller learned --lower-controller learned \
  --stance-policy linux_control/policies/stand50hz_stance_tuckclock_scratch6m_curhot_b23k12.json \
  --script human --policy-mode deterministic`

Artifacts: `logs/manual_drive/todaypolicy_bundle50hz_v1_stand_b23k12_walk_singleframe/`
(`drive.mp4`, `contact_sheet.png`, `summary.json`, `composition.json`,
`transfer_manifest.json`).

Result: **first successful full learned stand -> walk -> lower composition at
50 Hz.** `terminated=false`, `truncated=false`, 40 s total (10 s learned
stand-up incl. early stable handoff at 9.25 s, 20 s `human`-script joystick
walk, ~7.5 s learned lower + limp settle). `roll_peak_abs_deg=3.62`,
`pitch_peak_abs_deg=0.0`, `sacrificed_legs=[]`, `walk_gait_valid=true`,
`walk_progress_ratio=0.402`, `cur_max_a=2.64A` (inside the resolved 50 Hz
motor contract, `slew_limit_deg_s=37.5` preserved), `course_err_1s_med_deg
=3.68` / `p90=12.27`, `wrong_course_frac_1s=0.0`. Model: `mesh`/`full_mesh`,
3.494 kg. Video shows a clean rise into a stable stance, genuine six-leg
tripod-cycling forward+diagonal joystick translation, and a controlled
lower with no drag/tip.

## Known limitations (carried forward honestly, not hidden)

- **Stand/lower residual** (from `cw-stand50hz-...-curhot-b23k12`'s own
  adoption verdict): 1/12 rise `over_current` under mixed-start DR-0 (a
  bridge-start episode) and, under own-DR 0.2, one `hold/sto` + one
  `lower/sto` `tilt_roll` fall — a real but small residual the track's own
  pricing/pacing/budget levers (all closed, see `CURRENT_TRUTHS.md` 09-11)
  could not fully clear. The named next lever (structural per-leg
  torque-headroom / DR-robustness mechanism) is unbuilt; this bundle ships
  the best-available checkpoint with the limitation documented, not a
  perfect one.
- **Zero turn authority** on the DEFAULT walk role (by design, see tradeoff
  above); the turn-capable alternate trades some straight-line quality and
  robustness for it.
- Speed-soft: `walk_progress_ratio` ~0.40, consistent with every other
  champion at this recipe family (not a new regression).
- No physical-robot motion was performed to produce this bundle or its demo;
  hardware handoff is Robot Lab's guarded-runner lane per `RL_GOALS.md`.

## Next

1. A same-harness demo of the turn-capable composition (`--stance-policy`
   unchanged, walk checkpoint swapped to the cap29 export) for a fair
   side-by-side, if/when a joystick session actually needs turning.
2. If the structural torque-headroom mechanism for the stand/lower residual
   is ever built, re-run this exact demo command to confirm no regression
   before superseding this bundle.
3. Physical acceptance needs Robot Lab's bounded joystick trial per
   `RL_GOALS.md` — not scoped to this cloud cycle.
