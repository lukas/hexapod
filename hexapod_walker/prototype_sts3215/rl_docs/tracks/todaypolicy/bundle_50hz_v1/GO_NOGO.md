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

## Update, 2026-09-12 ~11:0x — turn-composition validated for the `walk_turn_capable` role (closes Next item 1 below)

One plain sentence: the `cap29` turn-capable role can now be run wrapped in a
non-RL turn-in-place composition (`any_means`: explicit controller
composition, built by amp/todaypolicy this same day) that is proven safe on
the actual bundle checkpoint's full gate panel and shows genuine turn
tracking on a 20 s joystick capture — RECOMMENDED whenever a session needs
turning, at zero measured cost to the non-turn modes.

Mechanism (`rl_move/sim/probe_turn_compose.py:_ComposedPolicy`, wired into
`eval_checkpoint.py`/`drive_video.py` via `--compose-turn-blend-s`, default
off/bit-exact): on ticks the env itself already classifies as live
turn-in-place, swap the action to the same scripted `TripodGait` teacher
this codebase's reward/BC-anchor machinery already treats as ground truth
elsewhere, blended over `blend_s` seconds; straight-walk ticks are
untouched. Validated at `blend_s=0.15`.

Evidence (corrected-mass-matched comparator, `..._gate_massfix` not the
stale pre-massfix `..._gate` amp's own STATUS entry diffed against): the
full `walk/rise/lower/hold` det+sto gate panel at `blend_s=0.15`
(`logs/ckpt_eval/cw_turn50hz_standwalk_cap29_stdwalklohi_warmadapt_canary2m_acq1_composed_gate/report.json`)
is panel-level IDENTICAL to the uncomposed corrected-mass gate
(`..._gate_massfix/report.json`) on every one of walk/rise/lower/hold
det+sto (same `gait_valid`, same terms); only `walk_startjitter` (the one
sub-panel whose natural goal draw occasionally contains a turn-in-place
tick) shows small per-episode deltas, consistent with the composition
engaging on a handful of ticks and being a true no-op elsewhere. A fresh 20 s
`human_turn` drivevideo at the same blend
(`logs/manual_drive/cap29_acq1_composed_humanturn/summary.json`):
`terminated=false`, `gait_valid=true`, `sacrificed_legs=[]`,
`turn_wz_err_med_rad_s=0.0747` (real tracking, not a freeze),
`cur_max_a=2.573A` (inside the 50 Hz motor contract). Frame strip shows
genuine per-frame leg reconfiguration through curved turn-in-place arcs.

**Honest gap — CLOSED 2026-09-12 ~11:5x/~12:0x (refill cycle), WITH the
known duration confound controlled for:** the matched RAW-vs-composed pair
is now on record for THIS checkpoint, in two batches. (A) Replayed the
training cfg-set verbatim on `probe_turn_compose.py`, forced
`goal.walk_turn_in_place_frac=1.0`, 4 seeds x 15 s @ 50 Hz (matched to the
official gate's episode length per this doc's own 06:0x root-cause entry):
RAW `gait_valid=False` 4/4 seeds (`sacrificed_legs` `[1,4]` on 3, `[1,4,5]`
on 1), `forward_dist_m` 0.010-0.017 (frozen), `mean|wz|_turn` 0.026-0.035
rad/s (noise floor). COMPOSED clears `gait_valid=True` 4/4, `sacrificed_
legs=[]` every seed, `mean|wz|_turn` 0.145-0.159 rad/s (5-6x the raw
reading). (B) Control at `goal.walk_turn_in_place_frac=0.0` (0 turn ticks,
confirmed), same construction, 3 seeds: RAW and COMPOSED are BYTE-IDENTICAL
and BOTH freeze the same way — this reproduces (does not newly discover)
this doc's own already-documented continuous-single-mode-duration artifact,
so (A)'s raw freeze is NOT by itself proof of a turn-specific defect. (B)
also shows the composed wrapper gives ZERO protection with no turn ticks to
substitute, so (A)'s fix is causally tied to the real turn-tick action
substitutions, not a wrapping/reset artifact. **Net verdict: the
composition is CONFIRMED to prevent this checkpoint's known
continuous-duration freeze specifically on sessions that hold sustained
turn-in-place** (a real, practically load-bearing property for real
joystick sessions with sustained turning).
Evidence: `logs/probe_turn_compose/cap29_acq1_tip1/{report.json,raw_*.png,
composed_*.png}` (batch A); `logs/probe_turn_compose/
cap29_acq1_purewalk_control/report.json` (batch B); full detail in
`composition.json`'s `walk_turn_capable.turn_composition_2026_09_12.
matched_raw_vs_composed_pair_2026_09_12` field.

**H1-vs-H2 mechanism question — CLOSED 2026-09-12 ~13:5x (refill cycle):**
whether the deeper mechanism is turn-specific (H2) or "any sustained
action substitution would also work" (H1) is now answered: **H1, generic
substitution.** Ran the exact control this doc's own gap named —
`probe_turn_compose.py --wrong-substitute-vx 0.05` injects a deliberately
WRONG action (straight walk, omega=0) on the same live turn ticks the real
composition substitutes on, natural `walk_turn_in_place_frac=0.30` mix, 10
seeds, matched 15s/50Hz. Of 5 episodes that drew turn ticks, the 4 with
substantial tick counts (263-699/750) ALL recover `gait_valid=True`,
`sacrificed_legs=[]` under the WRONG substitute — moving forward
(`forward_dist_m` 0.116-0.320) rather than turning, yet still unfreezing —
matching batch (A)'s correct-substitute recovery essentially 1:1. The one
episode with only 10/750 turn ticks shows partial-only recovery
(`sacrificed_legs` `[1,4]`->`[1]`), consistent with a dose/duration-
dependent unstick effect, not a contradiction. **Conclusion: the composed
action's turn-correctness is not what prevents the freeze — any sustained,
actively-commanded action for enough consecutive ticks is sufficient.**
The practical recommendation below is UNCHANGED (this composition remains
the right, already-built fix and is a true no-op elsewhere); what changes
is the causal story: "unstick a known continuous-single-mode-duration
freeze," not "supply a missing turn skill." Flagging, not building this
cycle: since batch (B) above already shows this composition gives ZERO
protection when there are no turn ticks to substitute, a genuinely new
general mechanism ("detect sustained single-mode duration, periodically
substitute/perturb the action regardless of mode") could plausibly extend
freeze protection to plain long straight-walk sessions too — a real Next
idea for whoever picks this track up, not a quick follow-up. Evidence:
`logs/probe_turn_compose/todaypolicy_cap29_acq1_wrongsub_tip1_frac30/
report.json`; `composition.json`'s `walk_turn_capable.
wrong_substitute_control_2026_09_12` field.

**Practical recommendation**: when a physical/sim session needs joystick
turning, load the `walk_turn_capable` export through
`--compose-turn-blend-s 0.15` rather than raw — it costs nothing on the
modes measured, and for any SUSTAINED turn-in-place command it is now the
only path confirmed not to freeze (raw freezes 4/4 seeds under the matched
pair above).

## Next

1. ~~A same-harness demo of the turn-capable composition...~~ DONE this
   update (see above). ~~Remaining sub-item: capture the matched raw-vs-
   composed `human_turn` pair on `cap29` itself~~ DONE 2026-09-12 ~11:5x —
   composition confirmed load-bearing, not merely precautionary.
2. If the structural torque-headroom mechanism for the stand/lower residual
   is ever built, re-run this exact demo command to confirm no regression
   before superseding this bundle.
3. Physical acceptance needs Robot Lab's bounded joystick trial per
   `RL_GOALS.md` — not scoped to this cloud cycle.
4. **NEW 2026-09-12 ~15:2x**: a generalized, mode-independent periodic
   teacher-substitution mechanism (`_ComposedPolicy`'s
   `stall_substitute_every_s`/`_dur_s`, default off) is now built and
   validated to prevent the SAME continuous-single-mode freeze on plain
   straight-line walking (5/5 raw fail -> 5/5 composed pass on
   `cap29-acq1`, turn_ticks=0), not just turn-in-place — see
   `todaypolicy/STATUS.md` 2026-09-12 ~15:2x. NOT yet wired into this
   bundle (the turn-composition above stays the only thing actually
   shipped) — a duty-cycle dose sweep (the tested 25% duty gave only
   modest net forward progress) and integration into
   `eval_checkpoint.py`/`drive_video.py` are the open next steps before
   this could supersede/extend the turn-only composition.
