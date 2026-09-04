# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~15:3x (this cycle): closed the `cont-s1b` falsifier
(training finished clean, W&B state=finished @2.03M steps) — ran
`probe_turn_authority` on the pod (train-9), full 84-key non-`train.*`
cfg-set replayed from its own ledger `extra_args`. Then re-ran it
through `rescore_turn_authority.rescore_cell` (the SAME both-signs
tool that produced the 5/10 seed1 flip) against both `cont` and
`cont-s1` as controls, not just the shorthand positive-only numbers
quoted in the falsifier's gate text. **Result is neither branch the
falsifier pre-registered — a third, SIGN-ASYMMETRIC pattern:**
pure-turn/combined vs `cont` = +14.1%/+0.7% (positive dir, "strong,
matches cont") but -15.1%/-36.9% (negative dir, "weak, WORSE than
cont-s1"); vs `cont-s1` = +28.5%/+26.6% (positive) but -10.8%/-2.6%
(negative). Raw wz_med: pos pure-turn 0.196 (beats `cont`'s 0.172),
neg pure-turn -0.170 (below even `cont-s1`'s -0.190). The shorthand
positive-only read ("0.196/0.132, lands at/above `cont`'s 0.172/0.132,
FAIL wall re-closes") would have been a false-clean answer — the
negative-command floor independently reproduces-or-worsens the
`cont-s1` weak read. **This means a single matched-continuation
control (n=1 per seed) is not a stable comparator** for this axis:
three independent seed1-family continuations (`cont-s1`, `cont-s1b`,
and by extension every lever-arm's own continuation) now show
run-to-run turn-authority variance large enough, and asymmetric
enough between +/- command, to plausibly explain the whole 5/10 flip
as control noise rather than a real per-seed dynamics effect — but it
could equally mean genuine per-run bimodality. Left `cont-s1b`
UNVERDICTED (mechanism-health canary, no fixed pass/fail; the decisive
question is the fork, not this run's own pass/fail). Evidence:
`logs/ckpt_eval/probe_turn_authority_cap29_stdwalklohi_cont_s1b_
combined_09-04.json`. **DIG-IN owed** (flagged this cycle) — do not
spend on the 5 reopened lever cells nor re-close the FAIL wall until
a deep-model pass decides: (a) treat +/- signs as two independently-
scored sub-questions instead of collapsing to one number, or (b) some
other resolution. Started building resolution path (a)'s prerequisite
same cycle: launched `cont-s1c` (seed=31, train-9) and `cont-s1d`
(seed=41, train-1), both VERIFIED RUNNING, 2M steps, exact same
recipe as `cont-s1`/`cont-s1b` (init-from the frozen `cap29-stdwalklo-
hi-s1` checkpoint, zero lever, only trainer seed differs) — by next
read there will be n=4 independent seed1-family continuations to
compute a real per-sign spread instead of trusting any single draw.

Prior updates (09-04 ~13:2x, ~14:1x, ~14:4x — mlcontprice2 FAIL-
MECHANISM/dose-bracket-to-k16 read, cont-s1b launch) archived verbatim
in `archive/standwalk_STATUS_journal_2026-09-04hh_trim.md`. `mlcontprice16`
(k=16.0 dose-bracket canary) is still VERIFIED RUNNING train-5, owned
by a concurrent cycle — see Next item 1.

## Next (updated 09-04 ~14:4x)

1. **Universal-command branch — 3-point dose bracket now running:
   k=0 (acq8m baseline, 8.3%) -> k=2 (FAIL, ~8.8%, below threshold,
   verdicted this cycle) -> k=8 (FAIL-MECHANISM but real partial fix,
   halves fires to 4.2%, cleans DR-0+gait-validity) -> k=16
   (`mlcontprice16`, VERIFIED RUNNING train-5, ~15-20 min class).**
   Read `mlcontprice16`'s `stress_verdict.json` next cycle
   (`logs/ckpt_eval/cw_standwalk_stage2_dualbc6_turncap_mirroraug_
   yawcredit_gradclip0p15_cap29_stdwalklohi_transtress_s1_acq8m_
   mlcontprice16_cmdstress/`, matched n=18/mode/pass so it's a clean
   comparator to `mlcontprice8`'s 3/72). If fires keep dropping without
   breaching the walk/smoothness caps, dose is still climbing — raise
   again or add steps; if it plateaus near k=8 or corrupts walk
   quality, k=8 is near the mechanism's usable ceiling and the next
   lever is genuinely own-DR-specific (log per-episode DR draws in
   eval_cmd_stress to correlate residual fires with specific
   randomized params). Do NOT build an "entry-window termination
   carry-over" fix — already refuted (09-04 12:15 dig-in).
2. **Steering branch — re-score fork DIG-IN OWED (falsifier read
   09-04 ~15:3x, result ambiguous, not resolved).** `cont-s1b`
   (independent 2nd seed1 plain-continuation) neither reproduces
   `cont-s1`'s weak floor nor `cont`'s strong floor cleanly — it's a
   THIRD, sign-asymmetric pattern (positive-command turn authority
   beats even `cont`; negative-command turn authority is at/below
   `cont-s1`'s weak floor). Full both-signs numbers + `rescore_cell`
   output in the Update above. This means the single matched-
   continuation control (n=1/seed) may itself be too noisy to trust
   as the yardstick for the 5/10 seed1 lever-cell flip. DO NOT launch
   a confirmatory acquisition run off the 5 reopened cells, and do NOT
   re-close the FAIL wall, until a deep-model dig-in decides how to
   score it (score +/- signs as separate sub-questions rather than one
   collapsed number is the leading candidate). `cont-s1c`/`cont-s1d`
   (seed=31/41, VERIFIED RUNNING train-9/train-1, ~15-20 min class,
   same recipe as `cont-s1`/`cont-s1b`) are in flight to hand the
   dig-in a real n=4 seed1-continuation spread instead of n=1/2 —
   read both (`probe_turn_authority` + `rescore_cell` vs cont/cont-s1/
   cont-s1b) before the dig-in decision. `selomegaboost4p0-s1`'s podeval
   DR-0 proxy (train-2) is no longer running and left no report under
   its expected path — treat as lost/inconclusive, not a pending
   read; don't block on it. Rise-stall
   stays CLOSED (09-03o archive).
3. **Closed** (full list in archives 09-02{,b..h}, 09-03{a..u},
   09-04{aa,cc,dd}): architecture-split; lever/dose/seed sweeps up to
   09-04 (all FAIL/REFUTED pre-continuation-drift-finding, see item 2);
   cap29 acquisition (PARTIAL); log_std anneal grid; sto/det
   convergence; resamplematch; rise over_current dig-in; semantics-bank
   twins; IK-feasibility groundwork; mlcontprice2 (k=2.0, below dose
   threshold, 09-04 ~14:4x).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb,cc,dd,gg,hh}.
> Current state = newest Update at the TOP; don't act on archived Next.

## Fleet capacity note (updated 09-04 ~15:5x)

9/12 GPU pods free (train-1 busy: `cont-s1d` seed=41 control; train-9
busy: `cont-s1c` seed=31 control — both launched this cycle, ~15-20
min class, building the seed1-continuation spread for the dig-in).
`mlcontprice16` finished and is owned by a concurrent cycle. train-4
still Pending (OOMKilled 08:06, recreated from the fixed 4Gi-dshm
scaleout spec; g142d86 at 98% CPU requests) — `bootstrap_train_pod.sh
hexapod-mjx-train-4` + `pod_torch_capability.py install` once Running.
No further launch this cycle: item 2 is now result-blocked on the
4-continuation spread, not launch-blocked; item 1 belongs to the
concurrent cycle. Every OTHER track remains non-launchable by design
(`joystick`/`amp`/`cpg` DONE or maintenance-only; `walkcurr` RETIRED;
`todaypolicy` DELIVERED).

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
- New launches already get `control.hz=100`/`env.model_source=mesh`
  (launcher-injected defaults) — never pin `model_source=primitive`.
- Legacy champions MAY be queried as teachers (same obs layout) but
  carry 25 Hz action scale/primitive dynamics: any distillation must
  handle the 25->100 Hz gap and MEASURE whether primitive-trained
  advice is good on mesh dynamics before trusting it.

## Stage 1 — mesh/100 Hz stance retrain (rise + lower)

Recipe basis: `stance_dr10` (exact cfg in ledger/W&B); rise-reference
machinery green since 08-24. GATE (pre-registered): stance panel
rise/hold/lower (pod_eval stance modes), n>=12, det+sto, DR-0+own-DR:
zero falls/tips, quiet hold, rise/lower height tracking comparable to
the legacy champion's band (absolute numbers shift with +66% mass).

## Stage 2 — teacher distillation into the best walking model

Use the stage-1 policy as the rise/lower TEACHER. Walking source: the
joystick champion lineage (`stotight45-seed13`) or its mesh-era
successor if the joystick track's in-flight mesh arms produce one
first — either adoption is PRE-REGISTERED, never a silent teacher
swap (cpg containment rule applies). Mechanism is cycle-designed (BC
clone + RL fine-tune, KL-to-teacher, phase-scheduled multi-teacher);
every mechanism arm pre-registers its gate and a matched control.

DONE GATE (the track's): ONE mesh-family 100 Hz policy, from sit:
rise -> randomized 60 s joystick command script -> lower to sit. Zero
falls, directions followed, slip/m within the joystick band (<=~2.9),
held-out panel n>=12, det+sto, DR-0+own-DR. `eval_done_gate_session`
is the session harness (flat=1 is the literal gate shape).

## Landmines

- Sim only — hardware stand/plant transfer stays operator-owned.
- No stage-2 arm may warm-start from a primitive checkpoint.
- The joystick track owns generic mesh walking; this track owns
  rise/lower + the unification. Coordinate via STATUS, don't duplicate.
- `_mixedsession` (REPEATING rise<->walk<->lower) is a stress test,
  NOT the DONE-gate instrument (that's `eval_done_gate_session`,
  `ops.sh donegatecmd`, flat=1).

