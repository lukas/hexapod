# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-01 ~12:1x (2/3 of the grad-clip dose bracket READ +
verdicted; NEW CAMPAIGN BEST). Plain English: **the TIGHT clip (0.15)
doesn't just recover turn authority — it OVERSHOOTS the control on
both signs AND fixes a walk-quality collapse (2x slip, half progress)
neither the unclipped dose nor the LOOSE clip (2.0) escape; a 38M
acquisition + seed-1 twin are running off it now.**

1. **gradclip0p15-canary -> CANARY PASS (best turn result of the
   campaign).** Built own `probe_turn_authority` + own no-video
   `purewalk` det (gait_valid/progress_ratio/slip; standard video gate
   was still 1.5-2h out) on-pod for all 4 siblings — wz_med pos/neg,
   progress_ratio, slip/m: ctrl 0.083/-0.138, 0.38, 2.7-3.0;
   **gradclip0p15 0.198/-0.200, 0.38-0.40, 2.2-2.6** (clears/overshoots
   ctrl on ALL axes); rr1 (closed FAIL) 0.028/-0.097, 0.16-0.18,
   5.3-5.8; gradclip2p0 0.043/-0.132, 0.16-0.18, 5.6-5.7 (collapsed
   same as rr1 despite a tiny wz uptick) -> **gradclip2p0 CANARY FAIL**
   (within noise of rr1 on the decisive gait/progress clause). Sharp
   dose CLIFF, not a smooth curve: 0.15 fully recovers, 2.0 fully
   collapses — the concurrent cycle's own 0.5 arm places the middle.
   Evidence: `logs/ckpt_eval/turn_probe_yawcredit_gradclip{0p15,2p0}
   _canary.json`, `purewalk_{gradclip0p15,gradclip2p0,ctrl,rr1}.json`.
2. **Refill (same cycle):** launched `...-gradclip0p15-acq1` (38M,
   matches turnpay-acq1 precedent) AND a `-canary-s1` seed-1 twin (2M)
   off gradclip0p15 to check basin robustness before the 38M budget
   commits to one seed. Both VERIFIED RUNNING (train-7, train-5).

Prior entries (klrolltight2 close, yaw-critic build, canary pair,
grad-clip build+launch) VERBATIM in
`archive/standwalk_STATUS_journal_2026-09-01_trim.md`.

## Next (meta 09-01 ~12:1x)

1. **Read gradclip0p5-canary** (concurrent cycle's arm) to place the
   cliff boundary between 0.15 (recovers+overshoots) and 2.0
   (collapses) — do NOT re-verdict, just fold the number in.
2. **Read `gradclip0p15-acq1` (38M) + `-canary-s1` (seed1, 2M).** acq1
   PASS/PROMOTE (new campaign best, stage-2 teacher candidate) if
   final wz_med stays >=0.15 both signs AND gait/progress/slip hold
   the control band — every prior acquisition arm here eroded turn
   authority, so erosion is the default to beat. `-s1` PASS if it
   reproduces seed0's result (recipe, not basin luck).
3. **Standing bar:** new dual distillations need pre-RL
   probe_turn_authority >=0.10 both signs; RL arms here are RETENTION
   only. gradclip0p15 is the reference recipe until acq1/-s1 say
   otherwise.
4. **Closed:** update-size constraints (freeze/value-warmup/
   kl-rollback), reward pricing, exploration magnitude, anchor
   dose/isolate-update, turn-skip, yaw-credit with NO clip or
   clip=2.0. Evidence: archive + this update.

> Journal archives (VERBATIM): pre-08-30 in
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`; 08-30 through
> 09-01 ~10:5x in `archive/standwalk_STATUS_journal_2026-09-01_trim.md`.
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

