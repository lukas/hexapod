# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-01 ~15:0x (MIXEDSESSION AUDIT CLOSED, root cause NOT
a cfg bug; new single-cycle DONE-gate session tool built + running).
Plain English: the 09-01 landmine ("`_mixedsession` shows 100%
over_current on EVERY submode incl. plain rise/det, but cfg-matched
probe/purewalk reads are clean -- audit before trusting it") is
CLOSED: it is NOT a `--cfg-set`/`--extra-cfg-set` propagation bug (all
of gradclip0p15-canary's own cfg-set overrides, incl. the low
`actions.max_height_mm=88`/`goal.rise_height_mm=[79,87]` envelope,
were already reaching `eval_mixed_session`'s inner `eval_checkpoint`
call correctly -- traced by hand through `pod_eval.py`'s `all_cfgs`
plumbing and `eval_mixed_session._run_eval_checkpoint`, both correct).
The real mechanism, found by reading one terminated episode's
`seq_plan`/`seq_end_seg_mode`/`seq_end_t_s` directly: mixedsession's
canonical grammar REPEATS rise<->{hold|walk}<->lower cycles for the
WHOLE episode (4-7 segments per 60s episode), so ANY single-rise-
after-self-lower fragility compounds across those forced repeats --
a checkpoint that fails only ~15-25% of individual rise attempts
still reads as a ~100% SESSION failure once forced through 4-7 of
them back to back. The standwalk DONE gate itself only ever asks for
ONE cycle ("sit -> rise -> randomized 60s walk -> lower"), which
mixedsession was never built to isolate.

**Built (CODE, tested, snapshotted `b9ea6d2e`): the actual missing
DONE-gate instrument.** (1) `walk_task._sample_mode_seq` gets a new
`goal.mode_seq_forced_plan` key (default `""` = bit-exact legacy
random plan; 16 tests incl. off-by-default equivalence) -- a
deterministic `"mode:seconds,..."` override, e.g.
`"rise:10,walk:60,lower:15"`, replacing the random SEQ_NEXT walk for
exactly this one-cycle session shape. (2) Found + fixed a SEPARATE
real `eval_checkpoint.py` bug while building this: `run_episode`
captured the episode's goal-mode ONCE at reset and every
`progress_ratio`/`slip_per_m`/`gait_valid`/course-window gate kept
reading that STALE label all episode -- a rise-first sequence that
switches to a real walk segment never accumulated `cmd_dist_m`/
`along_dist_m` at all (mode stayed "rise"), so those metrics silently
came back `None` for a session that plainly walked. Fixed to track the
LIVE per-tick `info["goal_mode"]`, windowing the gait/slip computation
to the walk-only tick run(s) (summed per disjoint run, no cross-run
diff/slip contamination at a segment seam); bit-identical for every
pre-09-01 single-mode episode (single run spanning the whole array) --
4 new regression tests incl. a direct formula-equivalence check
against the untouched `slip_m_total` field. (3) New
`rl_move.sim.eval_done_gate_session` (reuses `eval_mixed_session`'s
`aggregate_session`/`_run_eval_checkpoint`/resume-safety verbatim) +
`ops.sh donegatecmd <run> [rise_s] [walk_s] [lower_s]` -- the literal
DONE-gate session harness this track's own Goal section named as
unbuilt stage-2 tooling. All new tests green
(`test_mode_seq.py`+`test_eval_checkpoint_seq_walk_metrics.py`, 19
new + 67 adjacent regression tests re-run clean).

**Launched same-cycle (informational, on-pod, no training spend):**
`eval_done_gate_session` against `gradclip0p15-canary` (train-3) and
`-canary-s1` (train-5), n=8 det+sto, DR-0 + own-DR (0.5), rise:10s
-> walk:60s (own stress_mix joystick diet) -> lower:15s, WITH video --
both still running (long: 32 episodes x ~95s sim + video render each).
A quick n=2 hand-smoke on the controller (no video, `--own-dr-scale`
omitted) on `canary` alone already surfaced a REAL signal worth
flagging before the full read lands: 2/4 episodes terminated (both
det+sto) on the actual randomized-diet single cycle -- softer than
mixedsession's 100% (confirming the repeat-cycle theory) but NOT the
clean zero-fall result the isolated `probe_turn_authority`/`purewalk`
reads showed either. Too small an n to verdict (need the n=8 x
det+sto+DR0+ownDR panel now running); do not treat this as a gate
read. Evidence so far: `/tmp/forced_plan_smoke2` (controller
hand-smoke, no diet), `/tmp/donegate_smoke` (controller hand-smoke,
own diet, n=2) -- both superseded by the on-pod n=8 runs once they
land.

Prior entries (`gradclip0p15-acq1` 38M PARTIAL read + intermediate-
checkpoint probe, grad-clip bracket close, `-canary-s1` seed split,
klrolltight2 close, yaw-critic build) VERBATIM in
`archive/standwalk_STATUS_journal_2026-09-01_trim.md`.

## Next (meta 09-01 ~15:0x)

1. **DIG-IN queued (not yet read).** Read the two on-pod
   `eval_done_gate_session` panels once they finish (n=8 det+sto,
   DR-0+own-DR, video): `logs/ckpt_eval/
   cw_standwalk_stage2_dualbc6_turncap_mirroraug_yawcredit_
   gradclip0p15_{canary,canary_s1}_donegate/{dr0,owndr}/report.json`
   + `session_verdict.json` (train-3 / train-5). This is the FIRST
   real single-cycle sit->rise->walk(60s,own diet)->lower read on
   this lineage — it decides whether `gradclip0p15-canary` is close
   to the literal DONE gate or still has a real fall-rate problem
   under the randomized diet (the n=2 hand-smoke split the difference:
   not mixedsession's 100%, not probe/purewalk's 0% either — see
   Update). Watch video for pathology, not just the scalar gate.
2. **Campaign reference artifact:** the 2M `...-gradclip0p15-canary`
   checkpoint (NOT `-acq1`) is still the best turn-authority +
   walk-quality SINGLE-MODE combination found in this campaign;
   whether it also clears the single-CYCLE session is item 1's open
   question. Any stage-2 distillation needing a turn-capable walk
   teacher starts from that checkpoint pending item 1's answer.
3. **Standing bar:** new dual distillations need pre-RL
   probe_turn_authority >=0.10 both signs; RL arms here are RETENTION
   only.
4. **Closed:** update-size constraints (freeze/value-warmup/
   kl-rollback), reward pricing, exploration magnitude, anchor
   dose/isolate-update, turn-skip, yaw-credit with NO clip, clip=0.5,
   clip=2.0, acquisition-scale retention of clip=0.15 (`-acq1` 38M
   PARTIAL: turn authority+stability hold, walk quality regresses vs
   the 2M canary), and the mixedsession-audit landmine (root cause =
   repeating-cycle statistics, not a cfg bug; see Update + archive).

> Journal archives (VERBATIM): pre-08-30 in
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`; 08-30 through
> 09-01 ~15:0x in `archive/standwalk_STATUS_journal_2026-09-01_trim.md`.
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
ledger/W&B). The rise-reference machinery (`extract_rise_ref.py`,
rise bank) is green as of 08-24. Bank/semantics-check the stance
reward ON MESH before the first launch (mass went 2.104 -> 3.50 kg;
thresholds calibrated on primitive may rank behaviors differently).

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
- **Tooling flag (09-01) CLOSED:** the standing `_mixedsession`
  harness's REPEATING rise<->walk<->lower grammar compounds any
  single-rise fragility into a misleadingly total session failure
  (see Update) — treat it as a mechanism-robustness stress test, NOT
  the DONE-gate instrument; use `eval_done_gate_session`
  (`ops.sh donegatecmd`) for the actual one-cycle DONE-gate read.

