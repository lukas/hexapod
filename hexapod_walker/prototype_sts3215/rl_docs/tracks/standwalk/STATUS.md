# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~10:4x: **cap29-acq1 pair TRAINING FINISHED** (38M
steps each, healthy reward curves, fps>11k) — Next item #1's read is
now IN FLIGHT: flat-only `eval_done_gate_session` (n=8/pass x4 passes
= 32 total, matching the durctrl-canary decisive-read precedent),
launched on-pod (acq1 on train-3, `-s1` on train-1), both registered
via `ops.sh evalpending`. Not yet read.

Prior update, 2026-09-02 ~09:3x (idle-kick executed item 1+2, zero
backlog left): **cap=2.9 LANDED as a training-time acquisition** —
`cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-acq1`
(seed0, train-3) + `-s1` (seed1, train-1), warm-started from the
lineage's own best walk-quality+turn-authority checkpoint (the 2M
`gradclip0p15-canary`, NOT the degraded 38M `-acq1` — that acq1 run
itself REGRESSED walk quality under the OLD 2.5A cap, see its own
PARTIAL verdict), `safety.max_current_a=2.9` set both training- and
eval-time.

Item 2 (read-only re-probe, zero training compute) **CLOSED this
cycle**: reran `probe_turn_authority` + a purewalk det harness on
`klrolltight-acq1` and `gradclip0p15-acq1` with
`safety.max_current_a=2.9`. **Turn ceiling is REAL, NOT
current-confounded**: both checkpoints' wz_med (klrolltight 0.081/
-0.110, gradclip0p15 0.188/-0.224) are unchanged from their archived
cap-2.5 reads within noise. **But walk QUALITY improves under the
raised cap** (side-finding): gradclip0p15-acq1 purewalk det prog 0.35/
slip 2.81/dir_err 46.4°/cur_max 2.58A/zero term vs its cap-2.5 PARTIAL
(prog 0.31-0.32/slip 4.9-5.8) — corroborates item 1's hypothesis that
the old cap's spurious terminations, not steering, capped walk
quality. klrolltight-acq1 purewalk det: gait_valid 8/8, zero term,
prog 0.36-0.39, slip 2.74-3.16, dir_err 43.4°. Evidence:
`logs/ckpt_eval/turn_probe_{klrolltight_acq1,
yawcredit_gradclip0p15_acq1}_cap29.json`,
`logs/ckpt_eval/purewalk_{klrolltight_acq1,gradclip0p15_acq1}_cap29_det.json/`.

## Next (idle-kick 09-02 ~09:3x)

1. **Read the cap29-acq1 pair's flat-only `eval_done_gate_session`**
   (launched 10:4x, IN FLIGHT on train-3/train-1, registered via
   `ops.sh evalpending`, ETA hours). Gate: zero falls (bar MET by the
   teacher control `durctrl-canary` at 32/32 — regression here
   refutes); direction_err_med/slip_per_m_med at/below the cap29
   zero-training baselines (46.8°/3.09) — the purewalk side-read above
   (dir 43-46°, slip 2.7-3.2) suggests this is plausible, not yet
   confirmed at full acquisition scale or on the session harness.
2. **Steering gap (direction_err ~44-47°, cap 2.5 or 2.9) is the
   largest remaining DONE-gate distance, CONFIRMED not a current
   artifact** (item 2, closed) — design the next arm against the
   literal 60s session direction-following read, not the short probe.
3. **Closed (see archives):** update-size constraints, reward pricing,
   exploration magnitude, anchor dose, turn-skip, yaw-credit clip
   doses, mixedsession-audit + diet scoping (x2), duration-mismatch,
   switch-jump lead, ramp/height/mass as current driver, frame-blend
   (n=2), cap-diagnostic (POSITIVE), current-confound re-probe
   (NEGATIVE — ceiling real).

> Journal archives (VERBATIM, oldest->newest):
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`,
> `2026-09-01_trim.md`, `2026-09-02_trim.md`, `2026-09-02b_trim.md`,
> `2026-09-02c_trim.md`, `2026-09-02d_trim.md`. Current state = newest
> Update at the TOP; don't act on archived Next.

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

