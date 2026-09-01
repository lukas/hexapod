# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-01 ~18:5x (idle-kick: DONE-gate session READ +
RISE-DIET SCOPING BUG found in the harness built this same day).
Plain English: the two `eval_done_gate_session` panels queued by the
prior update (item 1 below, `gradclip0p15-canary`/`-canary-s1`,
n=32 each det+sto/DR-0+own-DR, video) finished on-pod and were read.
Headline: **gate FAILS both seeds** (`zero_falls=false`; canary 9/32
terminations, `-s1` 4/32) with poor aggregate walk tracking
(`direction_err_med_deg` 45.5/47.8, `slip_per_m_med` 3.27/3.29 — over
the 2.9 joystick band; `progress_ratio_med` 0.27/0.34). BUT reading
`terms_by_start_kind` + `terms_by_segment_mode` in the raw episode
JSON surfaced a real SCOPING bug in the harness itself, built and
missed same-day: `eval_done_gate_session` runs each checkpoint's OWN
training `--extra-cfg-set` stack verbatim, which for this lineage
carries `goal.rise_rsi_frac=0.5` (the DeepMimic-style mid-rise
reference-state-init used to bootstrap rise training — spawns the
robot ALREADY partway up the rise ramp) plus the default 40%/25%
partial-curl/crouch mix — so the "rise" segment of this "sit -> rise"
DONE-gate session sampled the FULL training-curriculum start
distribution, not a literal cold sit/flat start: only 3/32 (canary)
and 1/32 (`-s1`) episodes were actually `start_kind=flat`. 8/9 and
4/4 of the terminations landed in the rise segment, concentrated in
`rsi`/`bridge` starts (4+4 of canary's 9; 3+1 of `-s1`'s 4) — the one
flat-start termination (canary, n=3) is too small to read either way.
**This is not the literal DONE-gate question** ("from sit: rise ->
... -> lower" describes ONE fixed cold start, not a recovery-curriculum
mix). Fix (no code change — existing `--extra-cfg-set` override
mechanism, confirmed last-key-wins in `_parse_cfg_set`): layered
`goal.rise_flat_frac=1.0 rise_partial_frac=0 rise_start_bank_frac=0
rise_rsi_frac=0` on top of each run's own cfg stack and relaunched
both sessions (train-3/train-5, n=8 det+sto x DR0+ownDR = 32 literal
flat-start episodes each, video on, `..._donegate_flatonly` out-dirs)
— the actual literal-gate instrument going forward. Not yet read (in
flight, ETA ~1.5-2h). The walk-segment quality flags (slip/direction)
stand regardless of the rise question and need their own follow-up
once the flat-only rise read narrows the picture. wandb notes added
to both runs recording this (informational — does NOT reopen either
run's already-closed CANARY PASS/FAIL verdicts, which were narrowly
scoped to mechanism-health turn-authority, not this session shape).

Prior entries (mixedsession audit close + `eval_done_gate_session`
build, `gradclip0p15-acq1` 38M PARTIAL read + intermediate-checkpoint
probe, grad-clip bracket close, `-canary-s1` seed split, klrolltight2
close, yaw-critic build) VERBATIM in
`archive/standwalk_STATUS_journal_2026-09-01_trim.md`.

## Next (meta 09-01 ~18:5x)

1. **Read the flat-only DONE-gate sessions once they land** (train-3
   / train-5, ETA ~1.5-2h): `logs/ckpt_eval/
   cw_standwalk_stage2_dualbc6_turncap_mirroraug_yawcredit_
   gradclip0p15_{canary,canary_s1}_donegate_flatonly/
   {dr0,owndr}/report.json` + `session_verdict.json`. This IS the
   literal "from sit" DONE-gate read (32 pure flat-start episodes per
   seed). Zero falls here + slip/direction still bad -> the checkpoint
   has a real walk-segment quality gap, not a rise gap, under a fair
   single-cycle read. Any falls here -> a genuine cold-start rise
   problem survives independent of the RSI/bridge curriculum dilution
   found this cycle. Either way, also address the direction_err
   (~46deg) / slip (~3.3) numbers from the mixed-diet read — worse
   than `probe_turn_authority`'s narrower wz-only diet, so the fuller
   stress_mix walk diet may be exposing a real steering gap the
   turn-authority probe doesn't see.
2. **Campaign reference artifact:** the 2M `...-gradclip0p15-canary`
   checkpoint (NOT `-acq1`) is still the best turn-authority +
   walk-quality SINGLE-MODE combination found in this campaign; item
   1's flat-only read is now the decisive DONE-gate evidence (the
   mixed-diet read is confounded, see Update). Any stage-2
   distillation needing a turn-capable walk teacher starts from that
   checkpoint pending item 1's answer.
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
   Also closed: the mixed-diet `eval_done_gate_session` read (own-cfg
   RSI/bridge/crouch rise-start mix) as THE literal DONE-gate
   instrument — it answers a curriculum-robustness question, not the
   gate's fixed "from sit" one; the flat-only variant (`goal.
   rise_flat_frac=1.0`, etc., see Update) is the corrected instrument.

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

