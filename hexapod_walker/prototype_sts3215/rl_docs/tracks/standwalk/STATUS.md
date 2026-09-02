# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~05:4x (idle-kick, drained Next item 2 — frame-blend
joint verdict, zero new training compute, pulled+read both pending
on-pod session files): **frame-blend is REFUTED, not just
"unconfirmed."** `frameblend-canary` (seed0) and `-s1` (seed1)
flat-only `eval_done_gate_session` (n=32 each) both landed: seed0
27/32 term vs its no-blend control's 24/32 (worse); seed1 21/32 term
vs its control's 5/32 (4x worse). Both directions agree: blending only
the obs-facing switch handoff does not touch the dominant mid-rise
sustained-femur-current fragility (see item 2 below), so total
terminations don't drop and in seed1's case explode. Verdicted
`CANARY FAIL - MECHANISM` on both runs; no further frame-blend dose
sweeping. Item 1 (cap=2.9 decisive session read) is still mid-flight
on train-1 (started 05:18, ETA ~1-2h, not yet read this cycle).

Interim check 09-02 ~07:3x (idle-kick, zero new compute, no verdict —
job still running): the flat-only dr0 HALF of the cap=2.9
`eval_done_gate_session` for `durctrl-canary` finished at 06:52 and is
already decisive on its own axis — **16/16 det+sto episodes
`seq_completed=true`, ZERO terminations**, femur `cur_max_a` still
2.64 (still riding the cap, not lowered) but no longer tripping it,
vs. the un-capped control's 24/32 session-level over_current rate.
own-DR half started 06:52, ~7/8 det episodes rendered by 07:35 (own-DR
sto not started yet) — ETA ~45-60 more min. Matches the cap-raise
prediction so far; still waiting on own-DR before landing the cfg
default per item 1's own criteria (do not act on the dr0-only half).

Prior update, 2026-09-02 ~05:3x (idle-kick): the SAME per-joint current
probe run against the LEGACY primitive-family (2.104kg)
`ppo_goal_cw_stance_dr10` found femur pins at the IDENTICAL ~2.64A cap
(8/8 episodes, 5/8 terminate) — **mass REFUTED** as the sustained-
current driver, it's intrinsic to the curl-up-from-flat rise motion at
both body weights. Cheap zero-training follow-up: raising
`safety.max_current_a` 2.5->2.9A (grounded in HARDWARE.md's recorded
real 2.97A/"3A lab guard") eliminated all terminations (0/8) on the
same read-only probe. Front-running lever is now **raise
`safety.max_current_a`**, gated on the in-flight `durctrl-canary`
`eval_done_gate_session` cap=2.9 read (item 1, train-1, still mid-
flight). Full detail archived verbatim in
`archive/standwalk_STATUS_journal_2026-09-02c_trim.md`.

## Next (meta 09-02 ~05:3x)

1. **TOP ITEM: read the in-flight cap=2.9 `eval_done_gate_session`
   flat-only session** (train-1, launched this cycle, ETA ~1-2h from
   ~05:3x) for `durctrl-canary`. If the session-level over_current
   rate drops sharply (from the un-capped control's 24/32) with no new
   failure mode (falls, tips, slip blowup) and femur current settles
   rather than staying pinned, that CONFIRMS raising
   `safety.max_current_a` (propose 2.5->2.8 or 2.9, still under the
   documented 3A real guard) as the lever: land it as a training cfg
   default for the standwalk stance/rise recipe (new launches only,
   `require_root_cause_chain` satisfied by this Update's 3-part
   comparison) and re-verify against the DONE gate's zero-falls/
   joystick-band-slip bars. If it does NOT resolve session-level
   terminations (e.g. current now sustains even higher, or a NEW
   failure mode appears), the cap-raise lever is refuted at this dose
   and the remaining options (reprice `k_current_hot`/`current_hot_a`
   harder, or re-author `rise_ref_mesh_scripted.npz`) need their own
   dose test — still one lever at a time.
2. **CLOSED 09-02 ~05:4x: frame-blend REFUTED** (n=2 seeds, see
   Update). `goal.mode_seq_frame_blend_s` does not reduce total
   over_current terminations — it increases them on both seeds. No
   further dose-sweeping; the family-jump-metric tooling gap
   (`debug_seq_switch_obs_jump.py` reading unblended `env._q_nom`) is
   now moot, not worth fixing.
3. **Standing bar, still SUSPECT:** `probe_turn_authority >=0.10 both
   signs` predicts the isolated short-window probe, not the literal
   60s DONE gate — do not fund a short-probe-scored turn-authority arm
   until item 1 is closed (the sustained-current fragility may have
   hidden/inflated some closed verdicts).
4. **Closed (pre-09-02, see archives):** update-size constraints,
   reward pricing, exploration magnitude, anchor dose/isolate-update,
   turn-skip, yaw-credit at every clip dose, mixedsession-audit,
   mixed-diet `eval_done_gate_session` scoping (x2), duration-
   mismatch, switch-jump causal lead (partial), ramp-rate/target-
   height/mass as the sustained-current driver (all A/B-refuted),
   frame-blend (09-02, this cycle).

> Journal archives (VERBATIM, oldest->newest):
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`,
> `2026-09-01_trim.md`, `2026-09-02_trim.md`, `2026-09-02b_trim.md`,
> `2026-09-02c_trim.md`. Current state = newest Update at the TOP;
> don't act on archived Next.

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

