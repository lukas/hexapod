# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~09:1x (meta session read the landed verdict —
zero new compute): **cap=2.9 DECISIVE — CONFIRMED per item 1's own
pre-registered criteria.** `durctrl-canary` flat-only
`eval_done_gate_session` with `safety.max_current_a=2.9` (train-1,
`..._donegate_flatonly_cap29/session_verdict.json`): **32/32 episodes
seq_completed, ZERO terminations, BOTH dr0 (16/16) and own-DR (16/16)**
vs the un-capped control's 24/32 over-current. Femur still rides
~2.64-2.69 A (cap not lowered, just no longer tripped), no new failure
mode (height_err 1.9 mm, track_err 0.66°, gait_valid 1.0, zero falls).
Gate soft-flags that remain are the REAL remaining science:
`direction_err_med` **46.8°** (steering authority) and `slip_per_m_med`
**3.09** vs the <=~2.9 band (marginal). Prior context (sustained
femur-current localization, mass refuted at both body weights,
frame-blend refuted n=2): see archives. Note: every prior turn/session
arm TRAINED and EVALED under cap 2.5 with rife spurious over-current
terminations — closed turn-authority verdicts are suspect (item 2).

## Next (meta 09-02 ~09:1x)

1. **LAND the cap: launch the cap=2.9 acquisition arm + seed twin as
   ONE batch** — respec from the `gradclip0p15-acq1` lineage base (or
   turnpay-canary base, launcher's judgment) with
   `--cfg safety.max_current_a=2.9` (training-time too, so the policy
   stops learning under spurious mid-rise terminations; still under
   HARDWARE.md's real 2.97A/3A lab guard). Gate: flat-only
   `eval_done_gate_session` n>=12 det+sto dr0+own-dr, zero falls
   (bar now MET by the teacher control — regression = refute), plus
   direction_err/slip vs the cap29 read above (46.8°/3.09) as the
   baselines to beat. Register the eval via `ops.sh evalpending add`.
2. **Read-only re-probe of closed turn-authority champions under
   cap=2.9** (zero training compute, free pods): rerun
   `probe_turn_authority` + a short walk read on `klrolltight-acq1`
   and `gradclip0p15-acq1` checkpoints with
   `safety.max_current_a=2.9`. If wz authority reads materially better
   than the recorded 0.075-0.09 ceiling, the erosion-campaign closures
   were current-confounded and the cheapest reopened line wins;
   if unchanged, the ceiling is real and the steering gap needs its
   own mechanism arm.
3. **Steering gap (direction_err 46.8° med) is the largest remaining
   DONE-gate distance** — after 1-2 land, design the arm against the
   literal 60s session direction-following read, not the short probe
   (item 3's standing SUSPECT on probe_turn_authority stands).
4. **Closed (see archives):** update-size constraints, reward pricing,
   exploration magnitude, anchor dose, turn-skip, yaw-credit clip
   doses, mixedsession-audit + diet scoping (x2), duration-mismatch,
   switch-jump lead, ramp/height/mass as current driver, frame-blend
   (n=2), cap-diagnostic (POSITIVE, landed as item 1).

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

