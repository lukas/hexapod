# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~05:0x (idle-kick, drained Next item 1 with THREE
new A/B diagnostics — zero training, all read-only pod evals):
completed the promoted sustained-current root-cause item. Extended
`debug_seq_switch_obs_jump.py` (new `h_trace_mm`/`href_trace_mm`/
`mode_trace` fields + `--extra-cfg-set` passthrough, 5/5 tests green,
snapshotted) so per-tick current can be read alongside commanded vs
actual height, then ran it on `durctrl-canary` (already trained,
zero new training compute) three ways, all on-pod (train-2):

1. **(a) Not frameblend-specific.** n=24 own-DR stochastic read: only
   2/24 terminated (both walk-segment, switch-adjacent) — MUCH lower
   than the full 32-episode donegate session's 24/32, because this
   seed range happened to sample fewer bad draws — but critically,
   **21/22 SURVIVING episodes also peak at/above the 2.5A cap
   (2.40-2.69A) during the t=5.5-10s rise window**, they just don't
   sustain it a full 0.8s. Confirms the near-cap rise-hold current is
   a general durctrl-canary property, not a frameblend artifact.
2. **(b) Height/pose trace, DR-0 (n=8):** actual height tracks
   commanded height (`href`) closely while current stays near-cap
   (2.3-2.6A); episodes that keep tracking closely all the way to the
   87mm target stay pinned at/near cap continuously, while one episode
   that fell ~15mm short of target saw current DROP to 1.3-1.9A once
   it stopped climbing — current cost tracks HEIGHT-CHASING effort,
   not height-holding per se. Confirmed present at DR-0 (no
   randomization needed) — this is a NOMINAL-dynamics margin issue,
   not an own-DR robustness gap.
3. **(c) Named the mechanism by elimination, two clean A/B tests,
   both REFUTED the obvious candidates:**
   - **Ramp rate is NOT it.** Doubling `goal.rise_ramp_s` (6.0->12.0,
     half the commanded climb rate) left peak current in the
     t=3-9s window UNCHANGED (2.60-2.64A both ways, per episode,
     matched seeds, DR-0). Slowing the schedule doesn't cheapen it.
   - **Target height is NOT it either.** Commanding half the height
     (`rise_height_mm=[45,45]` vs the trained `[79,87]`) ALSO left
     peak current unchanged (2.62-2.64A) — despite the actual height
     tracking the lower target much more tightly (2-4mm lag vs
     ~15mm lag at the higher target).
   - **Conclusion:** the near-cap current is tied to the RISE MOTION
     ITSELF (curling up from the flat/belly start under the heavier
     3.50kg mesh body) at a roughly fixed cost, largely independent of
     how far or how fast the commanded height moves. Combined with the
     already-known `cur_leg_imbalance`~1.0 (uniform across all 6 legs,
     not one leg), this points at the curl-up/liftoff transient's
     joint-torque demand under the new mass+kinematics (not a reward-
     pricing dial, not a switch/blend artifact, not a duration-mismatch
     effect) as the dominant term driver. `reward.current_hot_a=2.0
     k_current_hot=1.0` prices current above 2.0A but apparently not
     hard enough to push the policy toward a cheaper curl-up posture.
4. **(d) LOCALIZED to the FEMUR joint, cleanly, all 8/8 episodes.**
   Extended the probe again with a per-tick `[coxa,femur,tibia]`
   max-over-legs current trace (`cur_joint_trace`, 6/6 tests green,
   snapshotted) and reran the same DR-0 window (t=3-9.5s): **femur
   (hip-pitch/thigh) pins at 2.63-2.64A (p95 2.57-2.64A) in EVERY
   episode** — essentially always at the safety cap; tibia (knee) runs
   hot but clearly below cap (peak 2.37-2.55A, p95 2.07-2.39A); coxa
   (hip yaw) is comfortable (peak 0.56-0.86A, p95 0.4-0.8A). This
   matches the physics exactly: the femur/thigh joint carries the
   primary body-weight-lifting torque during a stand-up curl, so it's
   the joint the +66% mesh mass loads hardest — CONFIRMS "the heavier
   mesh body's stand-up lifting torque, borne mainly by the femur
   joint, is right at the actuator's modeled current limit" as the
   root mechanism, not a diffuse/uniform posture cost.
   `logs/ckpt_eval/durctrl_canary_seqswitch_dr0_perjoint_n8.json`
   (`git tag exp/standwalk-perjoint-current-trace`).

No reward/cfg change proposed or launched this cycle. The mechanism
is now named AND localized (femur-joint stand-up lifting torque vs.
the heavier mesh mass, right at the modeled current cap) but a fix
still needs one more comparison before choosing a lever: is 2.5A
`safety.max_current_a` simply the wrong number for this femur servo
at 3.50kg (an actuator-model calibration question), or is
`reward.k_current_hot`/`current_hot_a` supposed to be steering the
policy toward a lower-torque stand-up strategy (e.g. wider stance,
different curl trajectory) and isn't strong enough to do so — those
call for different fixes (raise the cap vs. reprice vs. re-author
`rise_ref_mesh_scripted.npz`) and picking wrong risks masking a real
hardware-safety signal. Per guardrails ("name a mechanism before any
reward/cfg change" — done twice over; "no blind dose arm" — still
true one level down: WHICH of cap/pricing/reference to touch).
`frameblend-canary-s1`'s flat-only read (train-5, a concurrent
cycle's remit) is still mid-flight (dr0 done, owndr partial) — not
joined this cycle. Full prior journal (duration-mismatch quartet,
switch-jump lead, frame-blend build+read, the two donegate-bug fixes)
archived verbatim in `archive/standwalk_STATUS_journal_2026-09-02b_
trim.md`. Other 5 tracks reconfirmed DONE/retired/delivered.

## Next (meta 09-02 ~05:0x)

1. **TOP ITEM: pick the fix lever for the now-localized femur-torque
   cap-hit.** Mechanism named AND localized (see Update): the FEMUR
   joint alone pins at 2.63-2.64A (the safety cap) in every surveyed
   episode during the curl-up-from-flat rise motion, independent of
   ramp rate and target height (both A/B-refuted), under the heavier
   3.50kg mesh body — tibia runs hot but under-cap, coxa is
   comfortable. One more comparison before choosing: (a) run the SAME
   per-joint probe against the legacy primitive-family (2.104kg)
   stance champion (needs a `model_source=primitive` env — legacy-
   family checkpoint only, per the CONTINUITY RULE) to quantify how
   much of the femur cost is the +66% mass vs. the corrected mesh
   kinematics (hip-pitch axis shift) vs. this always having run this
   hot; (b) only after (a), choose ONE lever — raise
   `safety.max_current_a` for this joint if the real servo's
   continuous rating actually supports it (an actuator-spec question,
   not a training one), increase `reward.k_current_hot`/lower
   `current_hot_a` to price the policy toward a cheaper stand-up
   trajectory, or re-author `rise_ref_mesh_scripted.npz` with a
   femur-lighter curl-up reference — no blind dose arm across all
   three at once.
2. **Frame-blend fix: NOT CONFIRMED, orthogonal to the dominant
   defect (item 1).** `frameblend-canary` read WORSE than
   `durctrl-canary` on term count/spread; most terminations predate or
   straddle the switch for reasons item 1 now explains. Do not
   dose-sweep `mode_seq_frame_blend_s`. `frameblend-canary-s1`
   flat-only read still in flight (train-5, another cycle's remit) —
   join once done, expect the same story. **Tooling gap:**
   `debug_seq_switch_obs_jump.py`'s family-jump metric reads
   `env._q_nom` (unblended by design); patch to trace
   `_q_nom_for_obs()` before using it to judge blend efficacy.
3. **Standing bar, still SUSPECT:** `probe_turn_authority >=0.10 both
   signs` predicts the isolated short-window probe, not the literal
   60s DONE gate — do not fund a short-probe-scored turn-authority arm
   until item 1 is closed (the sustained-current fragility may have
   hidden/inflated some closed verdicts).
4. **Closed (pre-09-02, see archives):** update-size constraints
   (freeze/value-warmup/kl-rollback), reward pricing (original pass),
   exploration magnitude, anchor dose/isolate-update, turn-skip,
   yaw-credit at every clip dose, the mixedsession-audit landmine, the
   mixed-diet `eval_done_gate_session` scoping bug (x2), the 4-arm
   duration-mismatch PASS/PARTIAL/FAIL branching, the switch-jump
   causal lead (partial cause only), ramp-rate and target-height as
   the sustained-current driver (both A/B-refuted 09-02 ~05:0x).

> Journal archives (VERBATIM): pre-08-30 in
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`; 08-30 through
> 09-01 ~15:0x in `archive/standwalk_STATUS_journal_2026-09-01_trim.md`;
> 09-01 ~15:0x through 09-02 ~00:4x in
> `archive/standwalk_STATUS_journal_2026-09-02_trim.md`; 09-02 ~01:4x
> through ~04:0x in `archive/standwalk_STATUS_journal_2026-09-02b_
> trim.md`. Current state = newest Update at the TOP; don't act on
> archived Next.

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

