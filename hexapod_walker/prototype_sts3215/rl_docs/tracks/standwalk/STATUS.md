# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-01 ~10:5x (this cycle — yaw-credit canary pair READ +
verdicted, follow-up grad-clip lever built + a 3-arm dose bracket
launched). Plain English: **the reward-decomposed yaw critic's FIRST
dose (coef=1.0/vf=0.5, no trust region) made turn authority WORSE than
doing nothing — root cause looks like an oversized, unclipped actor
step, so I built a gradient-norm clip for just that step and launched
3 doses to find out if capping the step size recovers it.**

1. **yaw-credit canary pair verdicted** (own `probe_turn_authority`,
   TURNCAP_CFG_SET, run myself on-pod): `...-ctrl-canary` -> CANARY
   PASS (baseline, coef=0) wz_med pos avg **+0.083**/neg avg
   **-0.138**. `...-canary-rr1` (coef=1.0/vf=0.5) -> **CANARY FAIL -
   MECHANISM**: pos avg **+0.028**/neg avg **-0.097** — WORSE than
   control BOTH signs by 0.04-0.055 (2-3x the 0.02 gate threshold,
   wrong direction); reward-quarters crash deeper too (Q3/Q4
   -337/-62 vs -208/-22). Evidence:
   `logs/ckpt_eval/turn_probe_yawcredit_{ctrl_canary,canary_rr1}.json`.
2. **Root cause + fix:** the extra actor pg step
   (`yaw_critic.py::_yaw_credit_step`) shares the main optimizer with
   NO trust region — the same update-SIZE failure shape the closed
   freeze/kl-rollback family guards against, newly uncapped. Added
   `train.yaw_credit_grad_clip` (default 0/off, bit-exact when unset)
   = a plain `clip_grad_norm_` on just that step. 18/18
   `test_yaw_critic.py` green (3 new). Snapshot:
   `exp/yaw-credit-grad-clip-followup`.
3. **3-arm dose bracket launched** (respec of `-rr1`, clip-only
   lever): `grad_clip={0.15 (concurrent cycle's sibling, train-3), 0.5
   (train-4), 2.0 (train-5)}`, all VERIFIED RUNNING.

Prior entries (klrolltight2 close, yaw-critic build, canary launch)
VERBATIM in `archive/standwalk_STATUS_journal_2026-09-01_trim.md`.

## Next (meta 09-01 ~10:5x)

1. **Read the 3-arm grad-clip bracket**
   (`gradclip{0p15,0p5,2p0}-canary`). PASS/PROMOTE the best dose if
   wz_med clears the ctrl-canary baseline (0.083/-0.138) within 0.01
   both signs + gait/progress held -> acquisition continuation.
   INFORMATIVE if it beats rr1 (0.028/-0.097) by >=0.02 both signs but
   short of parity -> intermediate dose. FAIL all 3 -> retire the
   reward-decomposed-critic lever, accept the mirror-augment ceiling
   (~0.075-0.09 pos/-0.10 to -0.12 neg) as durable; last untried axes
   are a shared (non-detached) trunk or a smaller coef.
2. **Standing bar:** new dual distillations need pre-RL
   probe_turn_authority >=0.10 both signs; RL arms here are turn
   RETENTION only, never discovery.
3. **Closed — do not refund:** update-size constraints (all freeze/
   value-warmup/kl-rollback doses), reward pricing, exploration
   magnitude, anchor dose/isolate-update, turn-skip, yaw-credit
   coef=1.0/vf=0.5 with NO grad clip. Evidence: the archive above.

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

