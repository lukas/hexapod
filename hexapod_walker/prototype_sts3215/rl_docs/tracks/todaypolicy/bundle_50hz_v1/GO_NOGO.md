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

**Packaged 2026-09-12 ~19:4x**: the structured transfer-manifest + demo
video hand-off artifact for this composed role lives at
`composed_turn_role/{transfer_manifest.json,GO_NOGO.md,drive.mp4,
drive_sheet.png,summary.json}` (schema-matched to `walkcurr`'s
`bundle_rlonly_v2` pattern) — this is the artifact `amp/STATUS.md`
2026-09-12 ~10:5x asked for.

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

## Update, 2026-09-22 — two new full-envelope walk-role candidates, WITH a physical-trial priority ranking (refill cycle, doc-only, no code/GPU spend)

One plain sentence: since 09-21/09-22 the `standwalk` widedr saga produced
two architecturally-distinct, independently-DR-hardened walk-role
candidates that generalize to the FULL continuous-heading/variable-speed
joystick envelope (not the 8-fixed-heading/fixed-speed grid every earlier
candidate in this doc trains on) — both are real upgrades over every
candidate named above, but a same-day composed-session diagnostic found
they are NOT equally safe to hand to Robot Lab, so this update names a
priority order rather than just adding two more rows nobody would notice.

**Candidates** (registered in `composition.json` under
`roles.walk_straight`, not yet promoted to this doc's own default/alternate
table above — both are still `alternate_dr_hardened_fullenvelope*`
entries):
- `alternate_dr_hardened_fullenvelope_2026_09_22` (GRU, uniform
  `dr_scale=1.0`) → `linux_control/policies/walk50hz_gru_dr10_envwide_s0.json`.
  Seed-confirmed 3/3 GO. Composed own-DR(1.0) roll-peak band 3.4-7.2°,
  **0/4 seed terminations**.
- `alternate_dr_hardened_fullenvelope_mlp_2026_09_22` (MLP, per-axis-
  widened DR: torque/mass/foot_friction/friction/vel/contact/backlash
  each individually widened) →
  `linux_control/policies/walk50hz_mlp_widedr_quad5_torque_envwide_s0.json`.
  Seed-confirmed 3/3 GO. Composed own-DR(1.0) roll-peak band 3.7-26.3°,
  **1/4 seeds TERMINATED (`tilt_roll`)**.

**Root cause of the fall (not the MLP walk gait itself)**: the walk phase
proper is calm and comparable between architectures in 3/4 MLP seeds
(max 3.7-4.3° vs GRU's 3.4-4.0°). The fatal/near-fatal roll peaks occur in
the shared frozen **lower** phase (`stand50hz_stance_tuckclock_scratch6m_
curhot_b23k12`, same checkpoint both candidates use), whose own adoption
gate only ever verified robustness up to `dr_scale=0.2` (see that
checkpoint's own `known_limit` in `composition.json`'s `stand_lower` role
and its `-drwiden35` child FAIL, 2026-09-11 — widening this exact
checkpoint's own training DR was already tried and refuted, so this is
NOT a queued retrain lever). Composing it after the MLP recipe's wider
per-axis DR draw exposes that comparatively-narrow-DR lower controller to
physics variety well outside its own verified band; the GRU recipe's
uniform (not per-axis-widened) DR draw happens not to stress the same
weak point as hard.

**Practical recommendation for whoever runs the next physical joystick
trial**: prefer the **GRU-composed bundle**
(`alternate_dr_hardened_fullenvelope_2026_09_22`) over the MLP one for the
first full-envelope physical trial — same envelope coverage and identical
walk-mode gate bars, but a materially tighter/zero-termination composed
own-DR safety margin. The MLP candidate remains a valid second
architecturally-independent full-envelope option (useful if the GRU
bundle needs a fallback or for a future architecture-robustness
comparison) but should not be the first one tried hands-on.

Full evidence chain: `rl_docs/tracks/todaypolicy/STATUS.md` and
`rl_docs/tracks/standwalk/STATUS.md`, both 2026-09-22 ~12:0x through
~13:3x; `composition.json`'s `seed_sweep_roll_diagnostic_2026_09_22b`
field. No config default changed, no code change, no GPU spend (this
update only republishes an already-recorded finding into the doc Robot
Lab actually reads before a trial).

## Update, 2026-09-22 (refill cycle, no run completion required) — a THIRD GRU full-envelope candidate, strictly more DR-hardened than the one above, now exported with the tightest composed-session safety margin of any candidate in this bundle: **this is the new top physical-trial pick**

One plain sentence: `standwalk`'s frictionasym+stickslip grid (registered
in its own STATUS.md the same day) warm-started the exact same dr-1.0
full-envelope GRU (`envwide-s2`) that produced
`alternate_dr_hardened_fullenvelope_2026_09_22` above and added two foot
axes that recipe never had (per-foot friction asymmetry, 2x-dosed
stick-slip), closed 3/3 seeds GO with the dose ladder still not finding a
break — this cycle exported the strongest rung of that grid
(`dose08`) and ran it through the same composed stand→walk→lower
DR-0/own-DR demo every other candidate in this doc got, and it comes out
ahead on every composed-session number that matters for a physical
handoff, not just tied.

**Candidate**: `alternate_dr_hardened_fullenvelope_frictionasym_stickslip_2026_09_22`
(GRU, same continuous full-envelope contract as `envwide-s0`, PLUS
per-foot friction asymmetry `dr.foot_friction_scale=0.7,1.3` and
stick-slip `dr.foot_stickslip_gain=0.0,0.8`) →
`linux_control/policies/walk50hz_gru_dr10_frictionasym_stickslip_dose08.json`
(export parity 1.79e-07 action / 2.38e-07 hidden, bar 1e-5).
Seed-robust 3/3 at the source grid's own base dose (`s0`/`seed0`/`seed1`,
standwalk's own verdicts); this exported checkpoint is the highest,
still-undegraded dose rung of that same grid, not a separate seed
question of its own.

**Composed DR-0 / own-DR(1.0) session** (`ops.sh hybriddemo`, identical
command shape to every sibling above — full detail in
`composition.json`'s new field):

| metric | `envwide_s0` (current top pick) | `quad5_torque_envwide_s0` (MLP) | **`frictionasym_stickslip_dose08` (this update)** |
|---|---:|---:|---:|
| roll_peak_abs_deg, DR-0 → own-DR(1.0) | 3.554 → 5.678 | 4.19 → **17.836 (1/4 seeds fell)** | 3.889 → **3.535 (flat, not degrading)** |
| course_err_1s_settled_p90_deg, DR-0 → own-DR(1.0) | 11.63 → 30.64 | 15.75 → 31.84 | **9.34 → 8.26 (flat, best of the three)** |
| walk_progress_ratio, DR-0 → own-DR(1.0) | 0.439 → 0.335 | 0.395 → 0.243 | 0.441 → 0.361 |
| falls / sacrificed legs, either dose | 0 / none | 0 / none (own-DR seed-sweep found 1/4 seeds fall, see below) | 0 / none |

This is the tightest own-DR roll band and the best settled-course number
of any full-envelope candidate registered in this bundle to date — and
unlike the other two, own-DR(1.0) roll/course barely move from DR-0
rather than softening, despite carrying MORE randomized axes (friction
asymmetry + 2x-dosed stick-slip on top of everything `envwide-s0`
already had).

**Practical recommendation, superseding the update above**: for the next
physical joystick trial, prefer
**`alternate_dr_hardened_fullenvelope_frictionasym_stickslip_2026_09_22`**
over both `alternate_dr_hardened_fullenvelope_2026_09_22` (plain GRU
envwide-s0) and the MLP candidate — same envelope coverage, strictly more
randomized-axis coverage (adds the two foot-contact axes closest to the
real robot's actual friction/slip physics), and the best-measured
composed-session safety margin of the three. `envwide-s0` remains a valid
fallback (still zero-termination, slightly wider roll swing); the MLP
candidate stays third given its 1/4-seed composed-session fall rate
documented above.

No config default changed, no code change, no GPU spend (export +
composed-demo only, reusing `export_policy_np.py`/`ops.sh hybriddemo`
verbatim). `hardware_ready=true` set on
`cw-walk50hz-gru-dr10-frictionasym-stickslip-dose08`.

Evidence: `rl_docs/tracks/standwalk/STATUS.md` 2026-09-22 ~19:1x (grid
closure); `composition.json`'s new
`alternate_dr_hardened_fullenvelope_frictionasym_stickslip_2026_09_22`
field; `logs/manual_drive/todaypolicy_bundle50hz_v1_stand_b23k12_walk_
frictionasym_stickslip_dose08_{dr0,dr1}/{summary.json,drive.mp4,
contact_sheet.png}`.
