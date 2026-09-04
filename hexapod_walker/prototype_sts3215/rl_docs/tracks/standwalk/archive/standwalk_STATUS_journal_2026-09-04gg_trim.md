# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~13:2x: `mlcontprice8` (k=8.0 continuity+price canary,
2M off the acq8m checkpoint) TRIAGED — CANARY FAIL-MECHANISM vs its own
zero-mech-term gate, but the fix is real and dose-responsive, not dead.
`eval_cmd_stress` at 2M: hold_min_load HALVED (3/72, was acq8m's 6/72);
DR-0 pass is now fully CLEAN (0/36, was 2/36) and the companion
gait-validity/sacrificed-leg pathology is FULLY CLOSED
(gait_valid_frac=1.0, sacrificed_legs_seen=[], was 0.986/[1,2,3]); the
3 residual fires are ALL under own-DR (was 4/36). Walk quality held
(progress_ratio -4.9%, dir_err +3.2%, slip/m -7.5%, all inside the 10%
cap) — the price did not corrupt the walk optimum, so this is not the
dose-ceiling FAIL shape. DIG-IN this cycle on the 3 residual fires'
timing (per-episode `seq_plan`/`seq_end_t_s` in the cmdstress
report.json) REFUTES the "entry-window artifact" reading: fires land
2.2-5.1 s into the hold segment (well past grace 1.0 s + term_s 1.0 s
= 2.0 s minimum), and the pre-fix acq8m baseline's own 6 fires show
the IDENTICAL 2.4-5.3 s timing signature — the mechanism reduced the
RATE (via training pressure from the price) but did not change the
qualitative failure shape. Also: `_hold_minload_low_s` never
accumulates outside `hold` mode (checked `sim_env.py`), so there is no
pre-switch counter to "carry over" — the residual failures read as a
genuine hold-under-own-DR robustness gap, not a segment-entry code
defect. Verdict: `mlcontprice8`. Sibling `mlcontprice2` (k=2.0) is a
concurrent cycle's run — compound "both doses" call and any next-lever
design wait for its read. Prior banner archived:
`archive/standwalk_STATUS_journal_2026-09-04ff_trim.md`.

## Next (updated 09-04 ~13:2x)

1. **Universal-command branch — mechanism CONFIRMED real + dose-
   responsive at k=8 (halves fires, fully closes DR-0 + gait-validity),
   but residual own-DR fires are NOT an entry-window code artifact —
   read `mlcontprice8`'s verdict before designing any further lever.**
   Wait for `mlcontprice2` (k=2.0 twin, concurrent cycle) to complete
   the dose-response read: if it fails WORSE (more fires) the price is
   working as intended and a higher dose or more steps is the next
   experiment; if it fails SIMILARLY the price has saturated and the
   next question is what makes own-DR specifically harder to sustain
   hold-load on (candidate: log per-episode DR draws in eval_cmd_stress
   to correlate residual fires with specific randomized params — mass/
   friction/gain extremes — before writing any new mechanism). Do NOT
   build an "entry-window termination carry-over" fix on the untested
   theory named in the original gate text — this cycle's per-episode
   timing evidence refutes it (see Update banner). Numbers:
   `mlcontprice8` verdict + `logs/ckpt_eval/cw_standwalk_stage2_
   dualbc6_turncap_mirroraug_yawcredit_gradclip0p15_cap29_stdwalklohi_
   transtress_s1_acq8m_mlcontprice8_cmdstress/` (per-episode detail in
   `dr0/report.json` + `owndr/report.json`).
2. **Steering branch — CONFIRMED continuation-drift confound; axis
   needs re-scoring, not more lever canaries.** `cont`/`cont-s1`
   `probe_turn_authority` pure-turn wz_med sits 22-35% below the FROZEN
   cap29-stdwalklo-hi{,-s1} baselines gating all ~26 steering-lever
   canaries (6 families) — from PLAIN continuation, zero lever.
   Re-scored vs this matched control, `selomegaboost4p0-s1` (verdict
   pending its podeval DR-0 proxy, running on train-2) looks BETTER on
   pure-turn (+30-46% vs `cont-s1`) and mixed on combined-tick (neg-wz
   better, pos-wz ~8-17% worse) — opposite of scoring vs the frozen
   baseline (flat/failing like every prior lever). DIG-IN owed:
   re-score the 6-lever-family FAIL wall vs matched continuations
   before declaring the axis closed, or at minimum re-open
   `selomegaboost4p0-s1` once its DR-0 proxy lands. Numbers: `cont`/
   `cont-s1` verdicts + `logs/ckpt_eval/probe_turn_authority_
   cap29_stdwalklohi_{cont,cont_s1,selomegaboost4p0_s1}_combined_
   09-04.json`. Rise-stall stays CLOSED (09-03o archive).
3. **Closed** (full list in archives 09-02{,b..h}, 09-03{a..u},
   09-04{aa,cc,dd}): architecture-split; lever/dose/seed sweeps up to
   09-04 (all FAIL/REFUTED pre-continuation-drift-finding, see item 2);
   cap29 acquisition (PARTIAL); log_std anneal grid; sto/det
   convergence; resamplematch; rise over_current dig-in; semantics-bank
   twins; IK-feasibility groundwork.

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb,cc,dd,ee,ff}.
> Current state = newest Update at the TOP; don't act on archived Next.

## Fleet capacity note (updated 09-04 ~13:2x)

11/12 GPU pods free (train-2 busy running selomegaboost4p0-s1's podeval
walk-only DR-0 proxy — long-running since 11:51, still progressing,
not stuck; leave it, its owner reads it). No acquisition/lever launch
this cycle — item 1's compound dose call needs the concurrent
`mlcontprice2` cycle's read first, and this cycle's per-episode dig-in
refuted the only named next-lever theory (see Update banner), so there
is no evidence-backed code fix to land yet either. train-4 still
Pending (OOMKilled 08:06, recreated from the fixed 4Gi-dshm scaleout
spec; g142d86 at 98% CPU requests) — `bootstrap_train_pod.sh
hexapod-mjx-train-4` + `pod_torch_capability.py install` once Running.
Every OTHER track remains non-launchable by design (`joystick`/`amp`/
`cpg` DONE or maintenance-only; `walkcurr` RETIRED; `todaypolicy`
DELIVERED).

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

