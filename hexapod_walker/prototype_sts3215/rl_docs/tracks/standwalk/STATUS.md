# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~15:0x: **cap29-acq1 pair's flat-only
`eval_done_gate_session` READ (n=32 each), both verdicted PARTIAL.**
Zero falls held (0/32 term each, matches the `durctrl-canary` bar —
the training-time cap-raise does NOT regress fall-safety) but
direction_err_med/slip_per_m_med came in WORSE than the cap29
zero-training baseline (acq1 55.5°/3.46, s1 61.1°/3.45, vs baseline
46.8°/3.09) — two seeds agree, not noise. Evidence:
`logs/ckpt_eval/cw_standwalk_stage2_dualbc6_turncap_mirroraug_
yawcredit_gradclip0p15_cap29_acq1{,_s1}_donegate_flatonly/{dr0,owndr}/
report.json` (+ pulled to `/tmp/pull_acq1{,s1}` for the windowed
re-analysis below).

**Deeper zero-compute read of the SAME artifacts** (built the tool
first): `eval_mixed_session.aggregate_session` did not surface the
already-computed windowed course metrics (`eval_checkpoint.
windowed_course_stats`, the operator's 08-29 PRIMARY command-following
read, fb_20260829T141858_9421cd) at the session level — every prior
standwalk session triage had to hand-dig report.json for it. Fixed:
`walk.course_err_{1s,2s}_med_deg` / `course_speed_ratio_1s_med` now
ride along in every `aggregate_session` output, INFORMATIONAL ONLY
(gate.soft unchanged, bit-exact when the source report predates the
field — `test_eval_mixed_session.py` 11/11 green). Reading it back on
this pair:
- windowed course_err (acq1 22.0°, s1 23.2°) is BELOW the tick number
  but still ~2x the joystick-track's calibrated windowed allow
  (2.0+10=12°) — the steering gap is real by either metric, this is
  NOT the "false fail" shape 08-29 found elsewhere (tick 45-55°/
  windowed 2-9°); here windowed stays elevated too.
- **Bigger finding: det vs sto asymmetry dominates the gap more than
  steering does.** Per-episode: DET walk segments with a real command
  (`cmd_dist_m` 4-4.7m) reach `progress_ratio` ~0.32-0.38 (real, if
  ~65% underspeed) with slip 2.8-3.6 — plausible. STO walk segments
  with the SAME command scale reach `progress_ratio` only 0.045-0.085
  (5-8% of commanded distance!) with slip 10.6-28.5 — action-sampling
  noise during walk is closer to non-functional than "degraded."
  Per-window course_speed_ratio_1s on the worst DET windows goes
  slightly negative (-0.05) at exactly the ~4s `walk_cmd_resample_s`
  boundaries — consistent with (not a new refutation of) the closed
  turn-authority-ceiling finding: command changes outrun the policy's
  turn rate, and the DONE-gate's stress_mix diet resamples direction
  every ~4s by design.
- 14/32 session episodes had `cmd_dist_m=0.0` (a stress_mix command
  that sampled near-zero net displacement that segment) and correctly
  contribute no walk metrics — not a bug, not silently inflating the
  medians either way.

Prior update, 2026-09-02 ~10:4x: cap29-acq1 pair TRAINING FINISHED (38M
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

## Next (idle-kick 09-02 ~15:0x)

1. **DIG-IN flagged (this cycle): design the next mechanism against
   the det/sto walk-progress ASYMMETRY, not steering alone.** STO-mode
   walk segments reach only 5-8% of commanded progress (slip
   10.6-28.5) vs DET's 32-38% (slip 2.8-3.6) on the exact same
   cap29-acq1{,+s1} DONE-gate session read — this gap is bigger than
   the ~2x windowed-course-err overshoot (22-23° vs the joystick
   track's calibrated 12° allow). Needs the full toolkit (per-leg
   gait metrics under sto sampling specifically, root-cause chain
   behavior<-incentive<-pricing) before any reward patch — root
   candidate hypotheses to test, not yet run: (a) action-noise
   (SDE/Gaussian std) is large enough relative to the turn/velocity
   command scale that sto sampling knocks the gait off the DET
   trajectory near every ~4s command resample and it never recovers
   within the segment; (b) the value/advantage estimate used at
   training time is itself computed under stochastic rollouts, so a
   policy this fragile to its OWN sampling noise should show up in
   training-time eval curves too (check `eval/sto/*` vs `eval/dr0/*`
   W&B history on this lineage before hypothesizing further). Any
   reward-mechanism arm from this needs `test_task_semantics.py`
   green first (bank status not re-checked this cycle — long-running,
   verify before launch).
2. Steering gap (windowed course_err ~22-23°, cap 2.9) is real but
   secondary to item 1 — the worst per-window course_speed_ratio dips
   (~0 or slightly negative) land at the ~4s `walk_cmd_resample_s`
   boundaries, consistent with the already-closed turn-authority
   ceiling (wz_med 0.075-0.19 rad/s) rather than a new defect.
3. **Closed (see archives):** update-size constraints, reward pricing,
   exploration magnitude, anchor dose, turn-skip, yaw-credit clip
   doses, mixedsession-audit + diet scoping (x2), duration-mismatch,
   switch-jump lead, ramp/height/mass as current driver, frame-blend
   (n=2), cap-diagnostic (POSITIVE), current-confound re-probe
   (NEGATIVE — ceiling real), cap29 training-time acquisition (item 1
   of the 09-02 09:3x Next, PARTIAL both seeds — zero-falls transfers,
   steering/slip does not).

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

