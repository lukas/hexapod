# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~15:3x (idle-kick, zero-compute root-cause dig +
4-way canary launch on the det/sto walk-progress asymmetry flagged
last cycle): **config archaeology on the cap29-acq1{,+s1} launch args
+ cached W&B history found a concrete, untested cause candidate.**
Only the STANCE core's log_std is annealed down this whole lineage
(`--log-std-anneal-core stance --log-std-final -4.0`, confirmed live
in `log_std_anneal/stance/std` dropping to 0.0183 by 10% of training);
the WALK core's log_std is never touched by the anneal and its
`train/std` metric sits flat at 0.222-0.223 (log_std≈-1.5) for the
*entire* 38M-step run — i.e. walk-mode action noise never shrinks
while stance's does, a structural asymmetry that lines up with the
det/sto walk-progress gap being far worse than any stance-mode
degradation. This is NOT the same question the already-closed
`stdwalk-mild/hi` canary answered (08-31, dualbc5 lineage): that pair
RAISED walk log_std (-1.5→-0.8/-0.2) chasing turn authority and found
achieved body-yaw noise completely insensitive to input std — refuted
in that direction only. Lowering walk's log_std (this cycle's lever)
is the untested opposite move, and per that same 08-31 finding should
be safe for turn authority (already shown std-insensitive) while
plausibly tightening the walk policy's own sto-vs-det consistency.
**Launched a 2-dose x 2-seed canary grid (2M steps each, cap=2.9,
warm-started from the SAME `gradclip0p15-canary` 2M ancestor cap29-
acq1 itself used, not the degraded 38M checkpoint)**:
`cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-
cap29-stdwalklo-{mild,hi}{,-s1}` — mild anneals walk log_std to -2.0,
hi to -3.5, both paired with stance's existing -4.0
(`--log-std-anneal-core walk,stance --log-std-final <X>,-4.0`, the
multi-core anneal tool built 08-31 for exactly this kind of per-core
schedule, `test_log_std_anneal_multi.py` reconfirmed green pre-
launch). All 4 VERIFIED RUNNING (train-2/3/4/5). Not a reward/task-
mechanism change (pure PPO exploration schedule, no reward-pricing
touched) so `test_task_semantics.py` was not required as a
precondition. Gate (pre-registered, full text in the ledger): (1)
`probe_turn_authority` wz_med stays >=0.07 rad/s (no turn-authority
regression); (2) det+sto `eval_checkpoint.py` walk-mode read shows
sto `progress_ratio_med` rise materially off the cap29-acq1 baseline
(0.045-0.085) toward det (0.32-0.38) without det itself dropping
outside 0.28-0.40 or slip rising. Not yet read (still training this
cycle). Evidence once read: `logs/ckpt_eval/turn_probe_stdwalklo_
{mild,hi}.json`, `logs/ckpt_eval/purewalk_stdwalklo_{mild,hi}_{det,
sto}.json` (paths to be created by the reading cycle).

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

Earlier 09-02 updates (~10:4x cap29-acq1 training-finish note, ~09:3x
cap29 acquisition launch + current-confound re-probe CLOSED) moved
VERBATIM to `archive/standwalk_STATUS_journal_2026-09-02e_trim.md`
(purewalk cap29 det baselines: gradclip0p15-acq1 prog 0.35/slip 2.81,
klrolltight-acq1 prog 0.36-0.39/slip 2.74-3.16 — referenced above).

## Next (idle-kick 09-02 ~15:3x)

0. **READ the stdwalklo-{mild,hi}{,-s1} canary grid** (launched this
   cycle, train-2/3/4/5, 2M steps each — should finish fast): does
   annealing walk-core log_std down (mild -2.0 / hi -3.5, paired with
   stance's -4.0) close the sto-vs-det walk-progress gap
   (baseline sto 0.045-0.085 vs det 0.32-0.38) without regressing det
   or the turn-authority floor (wz_med >=0.07)? Full gate text in the
   ledger entry / STATUS update above. If PASS-for-acquisition, fund
   an acq-scale pair on the winning dose; if FAIL (gap persists
   despite the std cut), the asymmetry is NOT std-driven and the next
   suspect is the credit-assignment angle the 08-31 yaw-credit probe
   already found weak (critic barely reacts to per-tick noise
   direction) — extend `probe_yaw_credit`-style analysis to whole-
   episode sto-vs-det progress instead of just yaw.

1. Original DIG-IN framing (superseded by item 0's concrete launch,
   kept for the record): design the next mechanism against
   the det/sto walk-progress ASYMMETRY, not steering alone. STO-mode
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

