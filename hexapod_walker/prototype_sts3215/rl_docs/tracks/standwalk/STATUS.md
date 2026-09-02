# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~04:0x (idle-kick DIG-IN, not verdicted):
`frameblend-canary`'s (non-s1) flat-only `eval_done_gate_session`
landed this cycle — DOES NOT confirm the blend fix, and roots the
campaign's real dominant defect. Numbers: 27/32 term (all
`over_current`) at t=7.01-11.59s (median 8.67s), vs the matched
no-blend control `durctrl-canary`'s 24/32 term at t=8.56-12.30s
(median 9.57s) — pulled the control's own raw dr0/owndr episode jsons
fresh this cycle (`/tmp/..._durctrl_canary_donegate_flatonly_{dr0,
owndr}.json`, never summarized into a `session_verdict.json` before)
to make this an apples-to-apples per-episode comparison, not a
re-quote. The prior "20 rise-term / 7 walk-term" split is an artifact
of the segment-label boundary at the switch's t=10.0s tick, not a
real behavior difference (control splits 14/10 at the same
boundary) — both arms' terminations form ONE tight cluster straddling
the switch, blend or no blend, count and spread slightly WORSE with
the blend on.

**Root cause, confirmed via new instrumentation this cycle:** ran
`debug_seq_switch_obs_jump.py --train-run <run>` (its existing
`--train-run` flag, previously unused live) on `frameblend-canary`,
then pulled the full per-tick `cur_trace`/`act_trace` it already
records. Episode 3 (terminated 8.52s, entirely BEFORE the 10.0s
switch — the blend literally cannot touch this episode): current
climbs smoothly from ~2.4A at t=5.5s to a hard plateau at **2.517A by
t=6.9s** (just over the 2.5A `safety.max_current_a` cap) and stays
pinned there for the full `over_current_trip_s=0.8s` window while
`|action|` keeps climbing 0.37->0.54 the whole time — a genuine
sustained whole-body current cost during the post-ramp RISE HOLD
itself (rise_ramp_s=6.0 completes ~t=6s, then the policy must hold
until the t=10.0 switch), not a switch-adjacent shock at all.
`cur_leg_imbalance` sits at 1.02-1.07 (near-perfectly balanced across
all 6 legs) on every terminated episode in the full n=32 report —
rules out one leg fighting alone; this is a uniform, whole-body
current cost. This is the SAME pattern flagged-but-unexplored as
"separate mid-rise sustained current fragility" in the prior Next
list (`durfix-canary-s1`: 3/4 terms at t=4.6-9.8s, current pinned
200ms+ pre-trip) — now confirmed as the DOMINANT term cause on the
frameblend/durctrl lineage too, and it explains why neither
`durfix-canary` (duration fix) nor `frameblend-canary` (blend fix)
move total termination count: both target the switch; the actual
majority defect predates it.

**Tooling gap found (not yet fixed):** `debug_seq_switch_obs_jump.py`'s
family-jump metric reads `env._q_nom` directly, which the blend
mechanism does NOT touch (only `_q_nom_for_obs()`, blended over the
following ticks, is obs-facing) — so its `worst_family_jump=219.9deg`
readout on this checkpoint does NOT mean the blend failed to engage;
it means the probe measures the wrong variable. Do not use that
metric to judge blend efficacy until it's patched to trace
`_q_nom_for_obs()` per-tick across the blend window instead.

Sibling `frameblend-canary-s1` flat-only read still in flight
(train-5, started 03:00 by a concurrent cycle after the donegate-bug
fix) at this cycle's end — not read, joint call deferred. No
verdict issued on either arm this cycle (DIG-IN, per the model-tiering
rule: this result is anomalous vs the pre-registered hypothesis and
decides whether item 1 below gets promoted/dose-swept or dropped).
No other launchable work found (all 5 other tracks re-confirmed
DONE/retired/delivered this cycle by re-reading each track's own
STATUS banner fresh); did not launch a blind fix — the sustained-hold
current defect needs its own root-cause pass (what commanded
height/pose is active during t=6-10s hold, is `current_hot_a=2.0`
pricing simply too weak, does the heavier mesh mass (3.50kg vs legacy
2.104kg) make a normal hold cost more torque than 2.5A allows) before
any reward/cfg change, per guardrails discipline.

Prior update, 2026-09-02 ~03:0x (idle-kick, drained a real bug): found the
in-flight `frameblend-canary-s1` `eval_done_gate_session` read (on
train-5, started ~02:28 by a concurrent cycle) had REGRESSED the
09-01 mixedsession-diet scoping bug — it was running plain
`ops.sh donegatecmd` output (`goal.rise_rsi_frac=0.5`, the
checkpoint's own training-curriculum rise-start mix, out-dir
`..._s1_donegate` with NO `_flatonly` suffix), not the flat/sit-start
overrides its own STATUS text claimed and that the matched non-s1 run
(train-1) actually used. Root cause: `ops.sh donegatecmd` has no
flat-start mode, so anyone invoking it directly (instead of
hand-adding the override args the way the quartet + non-s1 frameblend
runs did) silently reproduces the exact bug closed on 09-01. Killed
it early (3/8 `rise_det` episodes in, minimal waste) and fixed at the
source: `donegatecmd` now takes an optional `flat=0/1` 6th arg — `1`
appends `goal.rise_flat_frac=1.0/rise_partial_frac=0/
rise_start_bank_frac=0/rise_rsi_frac=0` and suffixes the out-dir
`_donegate_flatonly` so a flat and a mixed-diet read of the same
checkpoint can never collide; default stays `0` (existing
call-sites/behavior unaffected). Verified the generated command
matches the non-s1 sibling's actual flat cfg byte-for-byte apart from
the checkpoint name, then relaunched the corrected
`frameblend-canary-s1` flat-only read on train-5 (n=8, video,
`..._s1_donegate_flatonly`), confirmed running with the right
`--extra-cfg-set goal.rise_flat_frac=1.0 ... rise_rsi_frac=0` args.
Non-s1 `frameblend-canary` read (train-1) untouched, still mid-flight
(dr0 phase done, owndr partial per its own prior update below). No
other launchable work found this cycle (all 5 other tracks
DONE/retired/delivered, backlog empty, single-dose discipline holds
pending both reads landing).

Prior update, 2026-09-02 ~02:4x (this cycle, non-s1 remit): `frameblend-canary`
(train-1, seed0) finished training (2M steps, `ep_rew_mean=166.4`,
reward quarters `[55.7, 79.6, -208.5, -22.6]` — dipped then partially
recovered, same healthy pattern as its siblings). No prestaged eval
covers this custom canary harness, so launched its flat-only
`eval_done_gate_session` on-pod (train-1, own pod — synced code
first), n=8, video, same flat-start overrides as the rest of the
quartet (`goal.rise_flat_frac=1.0 rise_partial_frac=0
rise_start_bank_frac=0`, plus `rise_rsi_frac=0` implied by
`rise_flat_frac=1.0`'s draw order) and the checkpoint's own
`goal.mode_seq_frame_blend_s=0.5`. Confirmed genuinely progressing via
repeated kubectl exec artifact counts (8/8 `rise_det` done, into
`rise_sto` by cycle end) but SLOW — 2 other prestage `eval_checkpoint`
procs (gate dr0 + owncfg dr0.5) are running concurrently on the same
pod sharing 26 cores, plus whatever contention `frameblend-canary-s1`'s
own reader (a different concurrent cycle, train-5) adds cluster-wide;
not read this cycle. **The matched control this run must beat**
(seed0, already read, see the archived table above):
`durctrl-canary` — 24/32 term, 10 walk-segment term, 6/24=25%
near-instant-onset, `progress_ratio` med 0.051, `slip_per_m` med
12.465, `dir_err` med 75.1°, `gait_valid` frac 0.444. Out-dir:
`logs/ckpt_eval/..._frameblend_canary_donegate_flatonly/{dr0,owndr}/`.
Next cycle: read both `frameblend-canary` (here) and `-s1` (other
cycle's remit) jointly once both `session_verdict.json`s exist —
neither alone should be over-interpreted per this campaign's own
seed-inconsistency lesson (durfix seed0 vs seed1 disagreed). No other
launchable work found (all 5 other tracks DONE/retired/delivered;
single-dose discipline blocks a second frame-blend dose pending this
read) — no filler launched.

Prior update, 2026-09-02 ~02:4x: `frameblend-canary-s1` (train-5) finished
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

## Next (meta 09-02 ~04:0x)

1. **PROMOTED TOP ITEM: root-cause the mid/late-rise sustained-current
   fragility.** Confirmed this cycle as the DOMINANT term cause on
   `frameblend-canary`/`durctrl-canary` alike (27/32, 24/32 term, both
   clustered t=7-12s regardless of blend) — not the switch shock item
   2 (below) was built to fix. Per-tick trace (ep3, `frameblend-canary`):
   current climbs smoothly from ~2.4A (t=5.5s) to a pinned 2.517A
   plateau by t=6.9s (just over the 2.5A cap), held through the
   0.8s trip window, while `|action|` keeps climbing the whole time;
   `cur_leg_imbalance` ~1.02-1.07 (balanced, rules out one leg alone).
   Next actions, in order: (a) pull the same per-tick trace on a bank
   of `durctrl-canary`'s own 14 rise-segment terminations (already
   trained+read, zero new compute) to confirm this isn't
   frameblend-specific; (b) inspect the commanded height/pose/goal
   trajectory during the t=6-10s hold window on a surviving vs a
   terminating episode — is the ramp target itself demanding (e.g.
   `rise_height_mm=[79,87]` at the heavier 3.50kg mesh mass) or is
   this idle-hold drift; (c) only after (a)+(b) name a mechanism
   (reward pricing `current_hot_a`/`k_current_hot` too weak, torque/
   gear-ratio mismatch for the +66% mass, or a genuine posture defect)
   before proposing any reward/cfg change — no blind dose arm.
2. **Frame-blend fix: NOT CONFIRMED, likely orthogonal to the
   dominant defect.** `frameblend-canary` (blend=0.5s) read WORSE
   than `durctrl-canary` (no blend) on total term count and timing
   spread — but per item 1, most terminations (both arms) happen
   before or straddling the switch for a reason unrelated to the
   q_nom teleport. Do not dose-sweep `mode_seq_frame_blend_s` or
   promote it as a default lever yet. `frameblend-canary-s1` flat-only
   read still in flight (train-5) — read it for the n=2 seed
   confirmation once done, but expect it to tell the same story.
   **Tooling gap:** `debug_seq_switch_obs_jump.py`'s family-jump
   metric reads `env._q_nom` (unblended by design) — it cannot judge
   blend efficacy; patch it to trace `_q_nom_for_obs()` per-tick
   across the blend window before using it for that question again.
3. **Standing bar, still SUSPECT:** `probe_turn_authority >=0.10 both
   signs` predicts the isolated short-window probe, not the literal
   60s DONE gate — do not fund a short-probe-scored turn-authority arm
   until item 1 says whether the sustained-current fragility (which
   this bar's own probes may or may not traverse) was hiding/inflating
   any of the closed verdicts.
4. **Closed (pre-09-02, see prior archives):** update-size constraints
   (freeze/value-warmup/kl-rollback), reward pricing, exploration
   magnitude, anchor dose/isolate-update, turn-skip, yaw-credit at
   every clip dose, the mixedsession-audit landmine, the mixed-diet
   `eval_done_gate_session` scoping bug, the original 4-arm
   duration-mismatch PASS/PARTIAL/FAIL branching, and the switch-jump
   causal lead itself (superseded by item 1's finding that it's not
   the dominant term cause).

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

