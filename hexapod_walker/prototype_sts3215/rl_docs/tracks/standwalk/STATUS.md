# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-05 ~05:4x: **phase-scheduled multi-teacher canary,
SEED0 HALF (2/4 arms) IN — both FAIL, matching the ~20-arm pattern.**
`multiteach-b05` (blend=0.5) and `-b10` (blend=1.0), both seed0, read
via `probe_turn_authority.py` (full 84-key cfg replayed, wz-cmds
0.25/-0.25 x vx-cmds 0/0.08, seeds 0+1, on-pod): b05 pure-turn wz_med
+0.176/-0.167 vs the seed0 control's +0.223/-0.250 (-21%/-33%,
past the gate's 10% cap); b10 pure-turn +0.117/-0.153 (-48%/-39%,
worse at full dose than half dose). Combined-tick (vx=0.08): b05
+0.095/-0.116 vs control +0.110/-0.170 (fails to beat on either
sign); b10 +0.084/-0.191 (beats on neg only, still fails the
both-signs PASS clause). No falls in either probe. **Phasing the
aggressive pure-turn target in late does NOT protect the safe
demo's own pure-turn magnitude — if anything higher blend dose makes
it worse**, refuting this run's own hypothesis at both tested doses.
`multiteach-b05-s1`/`-b10-s1` (seed1 half) still training on another
cycle's watch — not yet folded into a joint verdict; the seed0 read
alone already matches the pre-registered 4/4-closes-it pattern from
every prior static-dose arm (~20 total). Full JSON:
`logs/ckpt_eval/probe_turn_authority_cap29_stdwalklohi_multiteach_
b{05,10}_combined_09-05.json`.

Prior updates (09-04 ~13:2x..09-05 ~04:5x) archived verbatim in
`archive/standwalk_STATUS_journal_2026-09-0{4hh,4jj,4kk,4ll,5a,5b,5c}_
trim.md`.

## Next (updated 09-05 ~05:4x)

1. **Close the phase-scheduled multi-teacher canary joint verdict**
   once `-b05-s1`/`-b10-s1` (seed1) report (owned by a concurrent
   cycle at time of this write). Given both seed0 arms already FAIL
   decisively (past the 10% cap by 2-5x on pure-turn, and fail the
   both-signs beat-comparator clause on combined-tick), a matching
   seed1 result closes the WHOLE reward/supervision-side lever family
   (now ~22 arms) for good. Do not re-attempt a static-or-scheduled
   reweight/rescale of the combined-tick BC-anchor target after that
   — the axis is exhausted.
2. **If/when item 1 closes 4/4 (or 3/4+1 pending-consistent): the two
   remaining moves are (a) a genuine gait-STRUCTURE change (e.g.
   turn-dependent per-leg stance/swing duty skew, not another
   velocity-magnitude/atan2-denominator rescale — every rescale/boost/
   amplify/detangle variant of "change the commanded magnitude" is
   now refuted) or (b) renegotiate the DONE gate's turn-authority bar
   given the scripted teacher's OWN combined-tick ceiling (33% pure-
   turn retention, `probe_turn_authority` 09-03 finding) may make the
   current bar structurally unreachable via BC-anchored RL at all.
   (a) needs a dedicated design pass (duty-cycle/support-polygon
   changes are riskier than an amplitude rescale and deserve their own
   cycle, not a rushed same-cycle bolt-on) — do not half-build it.
2b. **DR-draw correlation — CLOSED.** No dominant DR field at n=20;
   k=8 is the standing ceiling dose (now also known to cost slip on
   the literal gate — do not re-promote mlcontprice8 or raise dose).
3. **Steering branch — CLOSED, both seeds, all axes** (09-04 ~17:0x
   sweep + architecture-swap/turn-skip/cap-recalibration closures).
   No further lever acquisition; frozen parents
   (`cap29-stdwalklo-hi{,-s1}`) remain the reference. Rise-stall
   stays CLOSED.
4. **Closed** (archives 09-02{,b..h}..09-05c): architecture-split;
   lever/dose/seed sweeps incl. `TripleGruActorCriticPolicy` turn-core
   swap; `combskip`/dose-bracket ablations; cap29 acquisition
   (PARTIAL); log_std anneal grid; sto/det convergence; resamplematch;
   rise over_current dig-in; semantics-bank twins; IK-feasibility;
   mlcontprice2/8/16 (k=8 ceiling, costs slip); steering FAIL-wall
   dig-in; DR-draw n=20; mlcontprice8 literal DONE-gate (FALL);
   dir_err_cap miscalibration (REFUTED); multiteacher blend
   {0.5,1.0}-seed0 (this update, FAIL both).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb,cc,dd,gg,hh,ii,jj,
> kk,ll}, 09-05{a,b,c}. Current state = newest Update at the TOP;
> don't act on archived Next.

## Fleet capacity note (updated 09-05 ~05:4x)

2 GPU slots still BUSY with the seed1 half of the multiteacher canary
(owned by a concurrent cycle), ~9-10 free. Every OTHER track
non-launchable by design (`joystick`/`amp`/`cpg` DONE/maintenance;
`walkcurr` RETIRED; `todaypolicy` DELIVERED). No new standwalk GPU
launch this update — item 1 needs the seed1 read first (avoid
duplicating/pre-empting the concurrent cycle's runs), and item 2's
gait-structure candidate is explicitly deferred to its own dedicated
design pass rather than a rushed same-cycle build.

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

