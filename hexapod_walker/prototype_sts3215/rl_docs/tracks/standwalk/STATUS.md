# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~05:3x (idle-kick, drained Next item 1's "one more
comparison" — zero training, all read-only pod evals): ran the SAME
per-joint current probe against the LEGACY primitive-family (2.104kg)
`ppo_goal_cw_stance_dr10` — decisive, mass-REFUTING result.

1. **Tooling fix:** `debug_seq_switch_obs_jump.py` was hardcoded to
   `joint_walk`; this legacy checkpoint trains on `joint_goal`, 4 obs
   dims narrower (walk_task's command+measured-velocity channels are
   UNCONDITIONAL, no cfg flag shrinks them). Added `--task` (default
   `joint_walk`, bit-exact for existing callers), 7/7 tests,
   snapshotted (`exp/standwalk-perjoint-legacy-task-flag`).
2. **Femur pins at cap in BOTH mass regimes, ~identically.** n=8 DR-0
   flat-start pure rise (primitive, this checkpoint's native recipe):
   femur peaks 2.638-2.640A in **8/8** episodes (mean-of-max 2.6396A)
   — matches the mesh finding (2.63-2.64A) almost exactly; coxa/tibia
   stay under cap, same pattern as mesh. **5/8 episodes TERMINATE
   over_current**, sustained 0.6-3.9s (not a brief spike) — matches
   HARDWARE.md's standing flag ("belly RISE is the risky part...
   incident class"), i.e. this was never mesh-specific.
   `logs/ckpt_eval/ppo_goal_cw_stance_dr10_seqswitch_dr0_perjoint_n8.json`.
   **Mass is NOT the primary driver** — the cap-hit is intrinsic to
   the curl-up-from-flat motion, present at both masses under two
   different rise references.
3. **Cheap follow-up: is the cap itself just too low?** Same primitive
   probe, only `safety.max_current_a` raised 2.5->2.9A (HARDWARE.md
   already recorded a real servo at 2.97A, "a hair under the 3A lab
   guard", 08-10) — **0/8 terminations** (was 5/8), current settles to
   1.3-1.9A by episode end (not runaway). Reran `durctrl-canary`'s own
   flat-only `eval_done_gate_session` (n=32, the real DONE-gate
   harness) with the same override — **launched, in flight on
   train-1**, ETA ~1-2h, not read this cycle: does it resolve the
   control's 24/32 session-level over_current rate cleanly?

No reward/cfg DEFAULT changed (both cap tests were read-only
`--extra-cfg-set` overrides on already-trained checkpoints, zero new
training compute). Front-running lever is now **raise
`safety.max_current_a`** (sim's cap sits below the recorded real "3A
lab guard"; reprice/re-author were both already implicitly active and
neither escaped the cap alone) — recorded in `OPERATOR_QUESTIONS.md`,
still gated on the in-flight session read before any training launch
bakes it in. Other 5 tracks reconfirmed DONE/retired/delivered. Full
prior journal archived verbatim in
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
2. **Frame-blend fix: NOT CONFIRMED, orthogonal to item 1** (see
   archive). Do not dose-sweep `mode_seq_frame_blend_s`.
   `frameblend-canary-s1` flat-only read may still be in flight
   (another cycle's remit) — join once done. **Tooling gap:**
   `debug_seq_switch_obs_jump.py`'s family-jump metric reads
   `env._q_nom` (unblended by design); patch to trace
   `_q_nom_for_obs()` before using it to judge blend efficacy.
3. **Standing bar, still SUSPECT:** `probe_turn_authority >=0.10 both
   signs` predicts the isolated short-window probe, not the literal
   60s DONE gate — do not fund a short-probe-scored turn-authority arm
   until item 1 is closed (the sustained-current fragility may have
   hidden/inflated some closed verdicts).
4. **Closed (pre-09-02, see archives):** update-size constraints,
   reward pricing (original pass), exploration magnitude, anchor
   dose/isolate-update, turn-skip, yaw-credit at every clip dose, the
   mixedsession-audit landmine, the mixed-diet `eval_done_gate_session`
   scoping bug (x2), duration-mismatch, the switch-jump causal lead
   (partial only), ramp-rate/target-height/mass as the sustained-
   current driver (all three A/B-refuted 09-02).

> Journal archives (VERBATIM): pre-08-30 in
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`; 08-30 through
> 09-01 ~15:0x in `archive/standwalk_STATUS_journal_2026-09-01_trim.md`;
> 09-01 ~15:0x through 09-02 ~00:4x in
> `archive/standwalk_STATUS_journal_2026-09-02_trim.md`; 09-02 ~01:4x
> through ~05:0x in `archive/standwalk_STATUS_journal_2026-09-02b_
> trim.md` and `archive/standwalk_STATUS_journal_2026-09-02c_trim.md`.
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

