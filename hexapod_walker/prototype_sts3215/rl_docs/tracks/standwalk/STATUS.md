# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~16:4x (canary grid READ -- `hi`/`hi-s1` CANARY
PASS, acq-scale pair funded): stdwalklo-{mild,hi}{,-s1} 2M grid
(archived below) finished. This cycle's assignment was `hi`/`hi-s1`;
`mild`/`mild-s1` are a concurrent cycle's (own RL_LOG lines, not
duplicated here). Both `hi`/`hi-s1` **CANARY PASS-for-acquisition**,
strongest of the grid: `probe_turn_authority` wz_med 0.19-0.21 rad/s
(both seeds/signs, floor 0.07) -- untouched. `purewalk` det-vs-sto
walk `progress_ratio_med`: hi 0.32/0.32, hi-s1 0.32/0.28 -- STO
essentially MATCHES det on both seeds, closing the cap29-acq1 session
baseline's sto/det gap (0.045-0.085 sto vs 0.32-0.38 det) almost
completely (well past the ~0.15 PASS bar); slip flat-to-better in sto.
Zero falls, 32/32 episodes. (`mild`'s -2.0 dose was weaker: sto
0.14-0.16, right at the PASS floor, worse slip -- `hi`'s -3.5 is the
clear winner.) Confirms the WALK core's un-annealed log_std was the
sto/det-gap driver, not credit assignment/command-resample dynamics.

**Funded the acq-scale follow-up**: respec'd both `hi` canaries to
the full 38M-step budget on the SAME recipe as `cap29-acq1` itself
(one lever changed) -- `...cap29-stdwalklohi-acq1{,-s1}`, VERIFIED
RUNNING train-6/7. Gate: flat-only `eval_done_gate_session` n>=12
det+sto DR-0+own-DR vs the cap29-acq1 baseline (46.8 deg/3.09; acq1
itself came in worse at 55.5-61.1/3.45-3.46) -- PASS if steering+slip
drop to/below baseline AND sto/det convergence survives at session
scale; PARTIAL if falls+convergence hold but steering doesn't
(separate defect, Next item 1); FAIL if sto regresses at scale.
Evidence: `logs/ckpt_eval/{turn_probe,purewalk}_..._stdwalklo_
{hi,hi_s1}*`.

Earlier 09-02 updates (config archaeology + grid launch, cap29
zero-training session read + windowed course-metrics tooling) moved
VERBATIM to `archive/standwalk_STATUS_journal_2026-09-02f_trim.md`.

## Next (updated 09-02 ~16:4x)

0. **READ the stdwalklohi-acq1{,-s1} full-budget pair** (train-6/7,
   38M steps, acq-scale continuation of the CANARY-PASS `hi` dose):
   does the sto/det walk-progress convergence survive to full budget,
   and does `eval_done_gate_session` direction_err_med/slip_per_m_med
   improve on the cap29-acq1 baseline (46.8 deg/3.09)? Gate text in
   the ledger. PASS -> new steering/slip reference; PARTIAL (falls+
   convergence hold, steering doesn't) -> item 1 is the next target;
   FAIL (sto regresses at scale) -> credit-assignment angle (08-31
   yaw-credit probe) is next.
1. Steering gap (windowed course_err ~22-23 deg, cap 2.9) — was
   secondary to the sto/det asymmetry; worst course_speed_ratio dips
   land at the ~4s `walk_cmd_resample_s` boundaries, consistent with
   the closed turn-authority ceiling (wz_med 0.075-0.21). Revisit once
   item 0 reads back.
2. **Closed (see archives):** update-size constraints, reward pricing,
   exploration magnitude, anchor dose, turn-skip, yaw-credit clip
   doses, mixedsession-audit + diet scoping (x2), duration-mismatch,
   switch-jump lead, ramp/height/mass as current driver, frame-blend
   (n=2), cap-diagnostic (POSITIVE), current-confound re-probe
   (NEGATIVE — ceiling real), cap29 training-time acquisition (PARTIAL
   both seeds — zero-falls transfers, steering/slip did not), walk-core
   log_std anneal canary grid (`hi` CANARY PASS 2/2 seeds — this
   cycle; `mild` weaker — concurrent cycle's own verdict).

> Journal archives (VERBATIM, oldest->newest):
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`,
> `2026-09-01_trim.md`, `2026-09-02_trim.md`, `2026-09-02b_trim.md`,
> `2026-09-02c_trim.md`, `2026-09-02d_trim.md`, `2026-09-02e_trim.md`.
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

Recipe basis: the `stance_dr10` lineage recipe (exact cfg in the
ledger/W&B); rise-reference machinery green since 08-24.
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
  rise/lower + the unification. Coordinate via STATUS, don't
  duplicate its mesh conversion arms.
- `_mixedsession` (REPEATING rise<->walk<->lower) is a stress test,
  NOT the DONE-gate instrument; the gate read is
  `eval_done_gate_session` (`ops.sh donegatecmd`, flat=1).

