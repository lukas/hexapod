# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~23:1x (idle-kick, item 0's read still mid-flight):
**ROOT-CAUSED + FIXED the `k_walk_course_income` regression the ~22:2x
entry below flagged for a dedicated dig-in.** Not the reward mechanism
-- a stale plant-stance literal. The b7e7ea05 merge switched
`sim_env.py`'s internal TripodGait use from the `sim_gait_compat`
wrapper (mujoco-relative knees) to the raw absolute-tibia gait (the
whole env now speaks `robot_abs` at the physics boundary, a real and
mostly-correct refactor) but left `_default_plant_deg()`'s stance
literal and `_make_walk_bc_gait`'s `sync_plant_stance(20.0, 80.0)`
un-converted: 80 was always the MUJOCO-RELATIVE knee value; relabeling
it as robot_abs without converting makes the physical knee 20 deg
LESS bent (`mujoco_rel = robot_abs_knee - hip = 80-20=60`, not the
intended 80). Measured (static-hold "park" episode, 8s): chassis rode
+82mm above the reset-settled height, `reward_height` -436,
`reward_loadslip_excess` -160, total park reward -1168 (historical
~+90). Fix: literal 80 -> **100** (its robot_abs equivalent, 80+hip 20)
in both call sites -- post-fix the same probe holds height_err_mm
~13mm all episode, loadslip/drag -> 0, total park reward **+89**,
matching history. Bank effect: `test_course_income_semantics.py`
7fail/5pass -> 4fail/8pass; `test_course_disp_semantics.py` +
`_window` -> 1fail/37pass (a margin edge, not a mechanism break);
`test_phasedir_semantics.py` + `test_quad_body_frame_trim.py`
(disposable-worktree pre/post cross-check) 17fail/19pass ->
10fail/26pass, ZERO new failures anywhere (the one remaining
quad_body_frame_trim failure is identical pre- and post-fix,
pre-existing, unrelated). Full derivation + numbers:
`OPERATOR_QUESTIONS.md` 2026-09-02 ~23:1x entry. Remaining follow-up
for whoever next touches this: retune the 4 still-failing
course_income margin constants against the now-correct physics (they
read as genuine recalibration, not further bugs -- the module's own
docstring already flags `backward`-vs-`park` as a historically tight
tradeoff), and triage the 10 still-failing phasedir cases (untouched
this cycle, different reward stack). Two full-bank pytest runs
(the ~22:2x entry's 398-test regression, PID 186875 from 22:19; this
entry's own `test_task_semantics`+`joint_action_{bias,box}` recheck
from 22:55) are BOTH still running past this cycle's exit -- read
them first. Snapshotted+pushed. This is CODE work (a real sim-physics
bug affecting every walk-mode reward term that reads chassis height/
drag/slip while near the plant stance, i.e. every live standwalk arm)
rather than a training result, so item 0 below (the in-flight
stdwalklohi-acq1 session read) is UNCHANGED/still the track's primary
open item; this fix does not itself require re-running that read.

Update, 2026-09-02 ~22:2x: idle-kick (item 0's read still mid-flight
on train-6/7) found a shared-repo infra emergency mid-cycle and fixed
it before anything else: a concurrent cycle's routine `snapshot.sh`
pull fast-forwarded main onto the operator's `66c4af30` merge, which
DELETED `test_task_semantics.py` + 7 sibling spec files, several
motion-library assets, a BC checkpoint, AND a real `joint_task.py`
mechanism (`goal.joint_action_bias/box_*`) with no replacement code —
collateral damage from an otherwise-legitimate joint-frame-v2 /
"remove pre-v2 compat" cleanup upstream. Restored everything verbatim
from `631d7f4c` (commit `07d0a475`) + fixed one downstream break
(`sim_gait_compat.py`'s `joint_frame` import got renamed out from
under it) + landed the previously-flagged `trans_drag_mm`/
`k_drag_loaded` dt-scaled deadband fix (bit-exact at legacy
`control.hz=25`, correctly tightens at the 100Hz default — the
`test_trans_drag_*` bank now passes 4/4). Full writeup, including one
STILL-OPEN unrelated regression this same merge introduced in
`k_walk_course_income` walk-mode physics (confirmed via a disposable
`631d7f4c` worktree, confirmed NOT caused by the drag fix, not yet
root-caused — flagged for a dedicated dig-in), in
`OPERATOR_QUESTIONS.md` 2026-09-02 ~22:0x entry. Full-bank regression
re-run in flight at cycle end (not read this cycle). Snapshotted+
pushed. Prior 09-02 ~21:3x update (the semantics-bank dig-in that
found this bug) moved verbatim to
`archive/standwalk_STATUS_journal_2026-09-02g_trim.md`.

Update, 2026-09-02 ~18:3x (`stdwalklohi-acq1{,-s1}` 38M pair FINISHED
training clean; auto SESSION/MIXEDSESSION harness errored rc=1 with
the SAME expected-broken "obs contract mismatch" every arm in this
exotic dual-core-obs lineage has hit since 09-01 — not a new defect):
verdicted both CANARY PASS (own scope) - joint pending flatonly-read.
Per Next item 0, dispatched the track's own flat-only
`eval_done_gate_session` (n=32, matching the cap29-acq1 baseline
read's own n) directly on-pod (train-6/7, code synced c70333b),
backgrounded + registered via `evalpending` — this is the acq-scale
read of whether the `hi`-dose walk-core log_std anneal's canary-scale
sto/det convergence (0.28-0.32 vs 0.32-0.36 progress_ratio) survives
to full budget, and whether direction_err_med/slip_per_m_med drop
to/below the cap29-acq1 baseline (46.8 deg/3.09). Not yet landed —
the reading cycle gets a fresh `session_verdict.json` on each pod.

Earlier 09-02 updates (config archaeology, the stdwalklo grid launch
+ read, cap29 zero-training session read + windowed course-metrics
tooling) moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-02f_trim.md`.

## Next (updated 09-02 ~18:3x)

0. **READ `logs/ckpt_eval/cw_..._stdwalklohi_acq1{,_s1}_donegate_
   flatonly/session_verdict.json`** once both land (in flight on
   train-6/7, n=32 det+sto DR-0+own-DR each): does the sto/det
   walk-progress convergence survive to full budget, and does
   direction_err_med/slip_per_m_med improve on the cap29-acq1
   baseline (46.8 deg/3.09)? Gate text in the ledger. PASS -> new
   steering/slip reference; PARTIAL (falls+convergence hold, steering
   doesn't) -> item 1 is the next target; FAIL (sto regresses at
   scale) -> credit-assignment angle (08-31 yaw-credit probe) is next.
1. Steering gap (windowed course_err ~22-23 deg, cap 2.9) — was
   secondary to the sto/det asymmetry; worst course_speed_ratio dips
   land at the ~4s `walk_cmd_resample_s` boundaries, consistent with
   the closed turn-authority ceiling (wz_med 0.075-0.21). Revisit once
   item 0 reads back.
2. **Closed (full list in archives):** update-size constraints, reward
   pricing, exploration magnitude, anchor dose, turn-skip, yaw-credit
   clip doses, mixedsession/diet scoping, duration-mismatch,
   switch-jump/ramp/height/mass/frame-blend/cap-diagnostic/current-
   confound (see 09-02{,b..f} archives), cap29 training-time
   acquisition (PARTIAL, steering/slip didn't transfer), walk-core
   log_std anneal dose grid (`hi` PASS 2/2, `mild` FAIL - dose too
   low, both closed this cycle-window).

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

