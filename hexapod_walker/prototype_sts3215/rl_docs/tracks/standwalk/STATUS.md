# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~02:4x: `frameblend-canary-s1` (train-5) finished
training (2M, healthy dip-recover). No prestaged eval existed for this
custom canary harness (expected — track-built tooling, not the
standard gate), so this cycle launched its flat-only
`eval_done_gate_session` read on-pod (n=8, video, matching
`durctrl-canary-s1`'s exact flat cfg). Confirmed genuinely progressing
via kubectl exec (not just assumed) but SLOW: train-5 is heavily
CPU-contended (3-4 other eval_checkpoint/eval_mixed_session procs at
600-780% CPU sharing 26 cores, leftovers from other cycles' work) —
still mid-flight at cycle end, not read. Comparison baseline already
in hand (`durctrl_canary_s1_flatonly_{dr0,owndr}_report.json`): 5/32
total term, all `over_current`, all at post-switch offset 3.16-3.24s
— this is the number the blend fix must beat. `frameblend-canary`
(non-s1, train-1) is a separate concurrent cycle's remit (pid 3753212)
— not touched here. wandbnote added to h58vj6eg with full detail.

Prior update, 2026-09-02 ~01:4x (idle-kick DRAINED the DIG-IN: instrumented +
CONFIRMED the switch-frame-teleport root-cause lead, built a matched
fix, launched a canary pair). Full journal of the duration-mismatch
quartet read + this dig-in in `archive/standwalk_STATUS_journal_
2026-09-02_trim.md`; summary below.

**CONFIRMED (not just a lead anymore): the un-blended rise->walk
`q_nom` teleport in `sim_env._seq_maybe_switch` is a real, near-
universal shock, and it is a genuine (partial) cause of the
duration-mismatch quartet's near-switch `over_current` terminations.**
Built `rl_move/sim/debug_seq_switch_obs_jump.py` (monkey-patches
`_seq_maybe_switch` to snapshot q_nom/z0 immediately before/after the
frame install; 3/3 tests green) and ran it on-pod against all 4
quartet checkpoints (own-DR, stochastic, n=8-24, same seeds/cfg as the
flat-only `eval_done_gate_session`):
- Every family-changing switch (rise="belly"->walk="plant") produces
  an EXACT, ~constant q_rel jump of ~215-220° L2 / up to ~89° on one
  joint, and a ~-70mm height-frame jump — independent of checkpoint or
  seed (a fixed geometric fact: belly=all-zero pose, plant=standing
  pose). A same-family switch (walk->lower, both "plant") shows an
  EXACT 0.0° jump every time (test-locked) — cleanly isolating the
  cause to the family change, not switching per se.
- Per-tick action/current tracing at the switch (durctrl-canary,
  n=24 owndr-sto): **action output saturates (clipped near max
  magnitude, ~0.7-1.0) on the EXACT switch tick in EVERY surveyed
  episode** (both the 2 that later terminate AND the 22 that survive)
  and stays saturated for seconds, driving current from its pre-switch
  baseline (~2.0-2.5A) up toward the 2.64A safety cap over the
  following 0.2-2.3s. Episodes already running hot pre-switch tip into
  `over_current`; others merely lose margin. This is a direct,
  tick-exact causal chain (jump -> saturated action -> rising current
  -> some episodes trip), not a coincidence-timed correlation.
- **This is only a PARTIAL cause, not the whole story**: in the same
  n=24 durfix-canary-s1 sample, 3/4 terminations happened WELL BEFORE
  the switch even fires (t=4.6-9.8s, mid-rise, current PINNED near-cap
  for 200ms+ beforehand — a sustained-load pattern, not a sudden
  shock) — a separate, switch-unrelated rise-segment fragility exists
  too and is NOT explained or fixed by anything below. Re-reading the
  4th quartet arm (`durctrl-canary-s1`, flat-only session landed this
  cycle, train-2): 5/5 walk-segment terms clustered at an almost
  IDENTICAL 13.16-13.24s (3.16-3.24s post-switch) — outside the crude
  "<=2s near-instant" bucket but still switch-locked (a fixed post-
  switch delay is itself strong evidence for a switch-triggered decay,
  not random bad luck).
- **Full 4-arm quartet flat-only DONE-gate read is now complete**
  (durctrl-canary 24 term, durctrl-canary-s1 5 term/0.298 prog, durfix-
  canary 21 term, durfix-canary-s1 24 term) — all 4 still `gate.pass=
  false` as expected (mechanism-health canaries only); the quartet's
  own PASS/PARTIAL/FAIL branching from 09-01 is superseded by this
  richer causal read, not worth re-scoring further.

**FIX BUILT + LAUNCHED (not yet read).** `goal.mode_seq_frame_blend_s`
(default 0.0 = off = bit-exact; `sim_env.py`, `mjx_host.SNAP_ATTRS`,
5 tests in `test_mode_seq_frame_blend.py`, all green): linearly blends
ONLY the q_nom `build_obs` reads (`_q_nom_for_obs()`) from the
pre-switch to the post-switch canonical frame over N seconds after a
family-changing switch — deliberately leaves `self._q_nom` itself
(the reward/anchor/IK-facing value) teleporting exactly as before, so
only the policy's raw NETWORK INPUT changes, nothing about reward
pricing or the anchor mechanism. Runs through the SAME per-env step
path both the CPU eval harness and the batched Warp/MJX training
vec-env share (`MjxVecEnv` calls each host env's `_step_finish`
directly — confirmed by code read, no separate MJX-kernel reimplement
needed), so a training canary genuinely exposes the policy to blended
inputs during learning, not just an eval-time patch on a frozen net.
Launched a matched pair off the SAME `gradclip0p15-canary` parent,
SAME steps/duration diet as `durctrl-canary` (isolates the blend fix
from the duration question; `durctrl-canary{,-s1}` are the existing
matched no-blend controls, already trained+read):
`...-frameblend-canary` (train-1) + `...-frameblend-canary-s1`
(train-5), `goal.mode_seq_frame_blend_s=0.5`, 2M steps each, VERIFIED
RUNNING. Gate: same flat-only `eval_done_gate_session` vs the
`durctrl-canary{,-s1}` numbers above — does near-switch/near-instant
`over_current` drop without progress/slip regressing. Not yet read.

No further mechanism arm queued pending this read (one dose, seed-
paired, per the "boring informative experiment" discipline — a dose
sweep is the natural follow-up once this pair lands, not before). The
separate mid-rise sustained-current fragility found above is flagged
but NOT investigated this cycle (orthogonal to the switch fix; next
dig-in candidate once frameblend lands). Other 5 tracks reconfirmed
DONE/retired/delivered (joystick DONE-gate 08-23, amp DONE at M5
sim-scope, cpg DONE pending `[operator]` hardware-adoption, walkcurr
RETIRED 08-31, todaypolicy DELIVERED 08-30) — standwalk remains the
only track with agent-launchable open work.

## Next (meta 09-02 ~01:4x)

1. **Read `frameblend-canary{,-s1}` once they finish 2M steps** (same
   pod flat-only `eval_done_gate_session` as the quartet). PASS
   signal: near-switch/near-instant `over_current` fraction drops
   meaningfully below `durctrl-canary{,-s1}` (24 term / 5 term
   respectively) without `progress_ratio`/`slip_per_m` regressing
   outside noise. If it clears: (a) promote as the new default lever
   for every future mode_seq mechanism arm in this campaign (re-run
   the closed turn-authority verdicts through it only if a later
   result depends on walk-segment survivability, not reflexively);
   (b) dose-sweep `mode_seq_frame_blend_s` (0.25/0.5/1.0/2.0) to find
   the ceiling; (c) consider whether `z0`/`pad_z_ref` also need the
   same treatment (height reward, not touched this round). If it does
   NOT clear: the action-saturation shock may be necessary-but-not-
   sufficient (something else about the walk segment's own dynamics
   is also hostile right after a rise) — pull the SAME per-tick
   current/action trace on the blended checkpoint to see whether the
   shock itself is gone (blend working as designed) even if
   termination doesn't improve (a different defect dominates).
2. **Separate, NOT YET INVESTIGATED: mid-rise sustained-current
   fragility.** `durfix-canary-s1` n=24 probe: 3/4 terminations at
   t=4.6-9.8s (well before any switch), current PINNED near the 2.64A
   cap for 200ms+ before tripping (a sustained-load pattern, not a
   spike) — orthogonal to the frame-blend fix, unexplained. Next dig-in
   candidate once item 1 lands: pull the same per-tick trace on a bank
   of these specific episodes, check foot-contact/leg-imbalance at the
   moment current pins (one leg fighting load asymmetrically?) before
   proposing a reward/DR change.
3. **Standing bar, still SUSPECT:** `probe_turn_authority >=0.10 both
   signs` predicts the isolated short-window probe, not the literal
   60s DONE gate — do not fund a short-probe-scored turn-authority arm
   until item 1's read says whether the switch-shock (which this bar's
   own probes never traverse, being single-mode) was hiding/inflating
   any of the closed verdicts.
4. **Closed (pre-09-02, see prior archives):** update-size constraints
   (freeze/value-warmup/kl-rollback), reward pricing, exploration
   magnitude, anchor dose/isolate-update, turn-skip, yaw-credit at
   every clip dose, the mixedsession-audit landmine, the mixed-diet
   `eval_done_gate_session` scoping bug, and the original 4-arm
   duration-mismatch PASS/PARTIAL/FAIL branching (superseded by the
   causal read above).

> Journal archives (VERBATIM): pre-08-30 in
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`; 08-30 through
> 09-01 ~15:0x in `archive/standwalk_STATUS_journal_2026-09-01_trim.md`;
> 09-01 ~15:0x through 09-02 ~00:4x (duration-mismatch quartet find +
> dig-in flag) in `archive/standwalk_STATUS_journal_2026-09-02_trim.md`.
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

