# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~14:4x (idle-kick): read `mlcontprice2` (k=2.0
canary, left unverdicted by its launching cycle) -> **CANARY
FAIL-MECHANISM**: 19/216 hold_min_load fires, session_complete 0.912,
sacrificed legs [0,2,3,5], dir_err +11.1% over cap. Also caught a
data-quality bug: this eval ran n=54/mode/pass (216 total), 3x its
k=8.0 twin's matched n=18 (72) — not an apples-to-apples pair. Rate-
normalized: k=2's 8.8% fire rate ~= the UNFIXED acq8m baseline's 8.3%
(zero net protection) vs k=8's 4.2% (halves it, cleans DR-0+gait-
validity) — real, monotonic dose-response; k=2 is below threshold.
Bracketed one step higher: `mlcontprice16` (k=16.0, same acq8m parent/
diet, matched n=18) VERIFIED RUNNING train-5. Also executed item 2's
named falsifier (seed1 re-score's 5 PASS cells ride entirely on
`cont-s1`, whose floor is weaker than `cont`'s): `cont-s1b`, an
INDEPENDENT 2nd seed1 plain-continuation (same recipe, trainer seed
1->21) VERIFIED RUNNING train-9. Both ~15-20 min class; next cycle
reads `mlcontprice16`'s stress_verdict.json vs `mlcontprice8`'s 3/72,
and runs `probe_turn_authority` on `cont-s1b` vs `cont-s1`'s
0.152/0.105 and `cont`'s 0.172/0.132 wz_med before touching the 5
provisionally-reopened lever cells.

Prior updates (09-04 ~13:2x, ~14:1x) archived verbatim in
`archive/standwalk_STATUS_journal_2026-09-04hh_trim.md`.

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
2. **Steering branch — re-score fork (09-04 ~14:1x) not yet resolved;
   falsifier now running.** 5/10 seed1 lever cells provisionally PASS
   only against `cont-s1`, whose own floor (pure-turn/combined wz_med
   0.152/0.105) is weaker than `cont`'s (0.172/0.132) — could be a
   real per-seed effect or a `cont-s1`-specific unlucky draw.
   `cont-s1b` (independent 2nd seed1 plain-continuation, same recipe,
   trainer seed 1->21) is VERIFIED RUNNING train-9, ~15-20 min class.
   Next cycle: run `probe_turn_authority` on its checkpoint, compare
   pure-turn/combined wz_med to `cont-s1`'s 0.152/0.105 and `cont`'s
   0.172/0.132. If it lands near `cont-s1`'s weak floor, the 5 PASS
   cells are legitimate reopen candidates for a confirmatory
   acquisition run; if it lands near `cont`'s strong floor, the
   floor-weakening was `cont-s1`-specific and the FAIL wall re-closes.
   `selomegaboost4p0-s1`'s podeval DR-0 proxy (train-2) is no longer
   running and left no report under its expected path — treat as lost/
   inconclusive, not a pending read; don't block on it. Rise-stall
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

## Fleet capacity note (updated 09-04 ~14:4x)

10/12 GPU pods free (train-5 busy: `mlcontprice16` dose-bracket canary;
train-9 busy: `cont-s1b` falsifier control — both launched this cycle,
~15-20 min class). train-4 still Pending (OOMKilled 08:06, recreated
from the fixed 4Gi-dshm scaleout spec; g142d86 at 98% CPU requests) —
`bootstrap_train_pod.sh hexapod-mjx-train-4` + `pod_torch_capability.py
install` once Running. No further launch this cycle: both open Next
items are now result-blocked on the two arms just started, not
launch-blocked. Every OTHER track remains non-launchable by design
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

