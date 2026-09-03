# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~05:0x (idle-kick, item 0 STILL mid-flight on
train-6/7, pace unchanged): closed the last open semantics-bank item,
`test_getup_honest_ordering` (genuine reward-design gap, not papered
over). Root cause: the same-day q0-frame fix made "freeze"'s held
pose correct (ret -40.4 buggy -> -30.3 accurate, cheaper to hold),
eating the 08-22 margin over "partial" (-35.1, untouched) since that
margin was only ever sized against freeze's old buggier cost. Fix:
`getup_k_progress` 200->350 (partial's ratchet income scales
~0.18/unit-k, freeze's ~flat 0.006) restores partial -8.2 > freeze
-29.3 (~20+ margin); swept 250->350, every other GETUP ordering stays
intact/widens. `-k getup`: 9/9 pass. Global default, but `p_getup`
isn't wired into any training recipe (0 ledger matches) so this is
SPECIFICATION work, no behavior change to anything running today.
Snapshotted+pushed (`exp/getup-honest-ordering-krecal-fix-0903`).
Closes the semantics-bank dig-in queue from the 09-02/09-03 window --
only RETIRED-track `walkcurr_pf` reds (~16-18) and whatever
`/tmp/full_after_tanglefix_0903.log` surfaces fresh remain. Full
derivation: OPERATOR_QUESTIONS.md.

Earlier updates (q0-frame fixes, hold-bank recalibrations,
joint-frame-v2 bug #3, tangle-spread probe-bug close, the 09-02
merge-recovery/plant-stance/stdwalklohi-acq1 window) moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-03{a,b,c,d}_trim.md` and
`2026-09-02{f,h}_trim.md`.

## Next (updated 09-02 ~18:3x)

0. **READ `logs/ckpt_eval/cw_..._stdwalklohi_acq1{,_s1}_donegate_
   flatonly/session_verdict.json`** once both land (in flight on
   train-6/7, n=32 det+sto DR-0+own-DR each): does sto/det walk-
   progress convergence survive to full budget, and does
   direction_err_med/slip_per_m_med improve on cap29-acq1's baseline
   (46.8 deg/3.09)? Gate text in the ledger. PASS -> new steering/slip
   reference; PARTIAL (falls+convergence hold, steering doesn't) ->
   item 1 is next; FAIL (sto regresses at scale) -> credit-assignment
   (08-31 yaw-credit probe) is next.
1. Steering gap (windowed course_err ~22-23 deg, cap 2.9) — was
   secondary to the sto/det asymmetry; worst course_speed_ratio dips
   land at the ~4s `walk_cmd_resample_s` boundaries, consistent with
   the closed turn-authority ceiling (wz_med 0.075-0.21). Revisit once
   item 0 reads back.
2. **Closed (full list in archives 09-02{,b..h}):** update-size/reward/
   exploration/anchor/turn-skip/yaw-credit/diet/duration/switch-jump/
   frame-blend/current-confound sweeps; cap29 acquisition (PARTIAL);
   walk-core log_std anneal dose grid (`hi` PASS, `mild` FAIL).

> Journal archives (VERBATIM, oldest->newest):
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`,
> `2026-09-01_trim.md`, `2026-09-02_trim.md`, `2026-09-02b_trim.md`,
> `2026-09-02c_trim.md`, `2026-09-02d_trim.md`, `2026-09-02e_trim.md`,
> `2026-09-02f_trim.md`, `2026-09-02g_trim.md`, `2026-09-02h_trim.md`,
> `2026-09-03a_trim.md`, `2026-09-03b_trim.md`, `2026-09-03c_trim.md`.
> Current state = newest Update at the TOP; don't act on archived Next.

## Goal (operator, 08-24 evening)

Retrain the best rising-and-lowering (stance) model on the NEW mesh
MuJoCo model at 100 Hz, then use it as a teacher to distill rise/lower
plus the best walking behavior into one policy. Product: a single
mesh-family 100 Hz policy that, starting from sit, rises, follows a
randomized 60 s joystick session with zero falls, and lowers back.

## Binding constraints (why this is a retrain, not a resume)

- Families do NOT transfer (CURRENT_TRUTHS "SIM MODEL FAMILIES"): the
  legacy stance champion `ppo_goal_cw_stance_dr10` and walk champion
  `ppo_goal_cw_dep_bcgait4_phasedir9_stotight45_seed13` are
  primitive-family 25 Hz policies. NO `respec --from` / warm-start of
  them onto mesh — stage 1 is a recipe rerun on the new model.
- New launches already get `control.hz=100` (launcher-injected) and
  `env.model_source=mesh` (the default) — do not pin legacy values
  here, and never pin `model_source=primitive` in this track.
- Legacy champions MAY be queried as teachers (same obs layout), but
  they carry 25 Hz action scale and primitive dynamics: any
  distillation mechanism must handle the 25->100 Hz gap (query at
  25 Hz + interpolate, distill trajectories, DAgger with rate
  conversion, ...) and must MEASURE whether primitive-trained advice
  is good on mesh dynamics before trusting it.

## Stage 1 — mesh/100 Hz stance retrain (rise + lower)

Recipe basis: `stance_dr10` (exact cfg in ledger/W&B); rise-reference
machinery green since 08-24.
GATE (pre-registered): stance panel rise/hold/lower (pod_eval stance
modes), n>=12, det+sto, DR-0 + own-DR: zero falls/tips, quiet hold
(no creep), rise/lower height tracking comparable to the legacy
champion's band. Absolute numbers shift with the +66% mass — the
first passing run's numbers become the recorded mesh reference band.

## Stage 2 — teacher distillation into the best walking model

Use the stage-1 policy as the rise/lower TEACHER. Walking source: the
joystick champion lineage (`stotight45-seed13`) or its mesh-era
successor if the joystick track's in-flight mesh arms produce one
first — either adoption is PRE-REGISTERED here, never a silent
teacher swap (cpg containment rule applies). Mechanism is
cycle-designed (BC clone + RL fine-tune a la bcgait, KL-to-teacher,
phase-scheduled multi-teacher, ...); every mechanism arm pre-registers
its gate and a matched control.

DONE GATE (the track's): ONE mesh-family 100 Hz policy, from sit:
rise -> randomized 60 s joystick command script -> lower to sit.
Zero falls, directions followed, slip/m within the joystick band
(<=~2.9), held-out panel n>=12, det+sto, DR-0 + own-DR.
`eval_joystick_gate` covers the walk segment; the sit->rise->walk->
lower session harness is stage-2 tooling to build.

## Landmines

- Sim only — hardware stand/plant transfer stays operator-owned.
- No stage-2 arm may warm-start from a primitive checkpoint.
- The joystick track owns generic mesh walking; this track owns
  rise/lower + the unification. Coordinate via STATUS, don't duplicate
  its mesh conversion arms.
- `_mixedsession` (REPEATING rise<->walk<->lower) is a stress test, NOT
  the DONE-gate instrument; the gate read is `eval_done_gate_session`
  (`ops.sh donegatecmd`, flat=1).

