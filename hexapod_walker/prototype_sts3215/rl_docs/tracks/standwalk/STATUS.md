# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~16:2x (DIG-IN RESOLVED, deep-model cycle): the
5/10 seed1 lever-cell reopening was **COMPARATOR NOISE**; the
sign-collapsed single-control `rescore_cell` PASS is INVALID on this
axis. Completed the n=4 spread: `cont-s1c`/`cont-s1d` finished
training (final checkpoints on pod), ran both probes on their own
pods (full 84-key cfg replay from each run's own ledger) ->
`logs/ckpt_eval/probe_turn_authority_cap29_stdwalklohi_cont_s1{c,d}_
combined_09-04.json`. Evidence, three independent lines: (1)
control-vs-control cells trigger the old criterion — `cont` vs
`cont-s1` scores +25.8%/+54.2% combined and PASSes; (2) all 5
reopened cells flip to FAIL when the denominator swaps `cont-s1` ->
`cont-s1b`; per-cell PASS counts across the 4 control draws are only
0/4–2/4; (3) measured n=4 zero-lever seed1-continuation spread is
enormous on the positive clauses — pt_pos 0.119–0.196 (50% rel),
cb_pos 0.064–0.136 (65% rel; `cont-s1d` is the worst positive draw
yet, not an OOD-cfg artifact — its pt_neg 0.195 tracks fine) — vs
tight negative clauses pt_neg 0.170–0.198, cb_neg 0.120–0.138.
**Adopted methodology (encoded as `rescore_turn_authority band`,
tests green):** score the FOUR clauses (pure/combined x +/-)
separately against the control-DISTRIBUTION band (n>=3 matched
zero-lever continuations); WIN only above band max, LOSS only below
band min, in-band = no-call; family claims need clause replication
across lever draws. **Real per-sign finding the collapsed score
hid:** cb_neg collapses in 4/4 zero-lever continuations (0.127
+/-0.008) vs frozen parent-s1 0.142 and seed0 `cont` 0.190, while
9/10 lever arms sit ABOVE the band (0.14–0.19; binomial p~4e-6) —
geometry levers do NOT improve steering (cb_pos: 0/10 wins), they
partially PROTECT it against continuation erosion. Frozen parents
hold the best pure-turn by far (0.223–0.226 vs ALL continuations
0.119–0.214): plain 2M continuation of this lineage is actively
steering-destructive; any future continuation needs the 4-clause
probe as a canary vs the band. FAIL wall on "levers improve combined
turn authority" stays CLOSED; NO acquisition run on the 5 cells.
`cont-s1b` verdicted PASS (canary); `cont-s1c`/`cont-s1d` verdicted
on W&B-finish this same cycle. Launched `cont-b`/`cont-c` (seed0
zero-lever continuations, seeds 21/31) so the seed0 half of the wall
(currently scored 9/10 FAIL vs the single `cont` draw) gets the same
n=3 band treatment — also tests whether cb_neg-protection replicates
where the control (0.190) did NOT collapse. n=4 manifest:
`logs/ckpt_eval/rescore_turn_authority_09-04/manifest_n4.json`.

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
2. **Steering branch — DIG-IN RESOLVED 09-04 ~16:2x (see Update):
   read `cont-b`/`cont-c` (seed0 zero-lever continuations, seeds
   21/31, launched this cycle, ~15-20 min class).** On finish: run
   `probe_turn_authority` on each pod (full cfg replay via
   `rescore_turn_authority cfg <run>`, `--vx-cmds 0.0,0.08`), add to
   the manifest, then `rescore_turn_authority band manifest_n4.json
   cont cont_b cont_c` over the 10 seed0 lever cells. Questions it
   answers: (a) does the seed0 half of the FAIL wall survive band
   scoring (it currently rests on the single `cont` draw); (b) does
   cb_neg-protection replicate in the lineage where the one control
   draw did NOT collapse (if seed0 controls spread down to ~0.12,
   `cont` was a lucky draw and continuation-erosion is lineage-
   independent; if they stay ~0.19, the collapse is seed1-specific).
   Binding rules from the resolution: sign-collapsed single-control
   scoring is DEAD on this axis; no lever acquisition runs (levers
   protect, they don't improve — cb_pos 0/10 wins); plain continuation
   of this lineage without a 4-clause probe canary is steering-
   destructive (frozen parents hold the best pure-turn 0.223-0.226).
   `selomegaboost4p0-s1`'s podeval DR-0 proxy (train-2) was lost —
   inconclusive, don't block on it. Rise-stall stays CLOSED (09-03o
   archive).
3. **Closed** (full list in archives 09-02{,b..h}, 09-03{a..u},
   09-04{aa,cc,dd}): architecture-split; lever/dose/seed sweeps up to
   09-04 (all FAIL/REFUTED pre-continuation-drift-finding, see item 2);
   cap29 acquisition (PARTIAL); log_std anneal grid; sto/det
   convergence; resamplematch; rise over_current dig-in; semantics-bank
   twins; IK-feasibility groundwork; mlcontprice2 (k=2.0, below dose
   threshold, 09-04 ~14:4x).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb,cc,dd,gg,hh,ii}.
> Current state = newest Update at the TOP; don't act on archived Next.

## Fleet capacity note (updated 09-04 ~16:2x)

7/12 GPU slots free after this cycle's launches (train-1/train-9
freed as cont-s1d/cont-s1c finished; cont-b/cont-c now occupy two
slots, ~15-20 min class, seed0 control band for Next item 2).
`mlcontprice16` finished and is owned by a concurrent cycle (Next
item 1). train-4 still Pending (OOMKilled 08:06, recreated from the
fixed 4Gi-dshm scaleout spec) — `bootstrap_train_pod.sh
hexapod-mjx-train-4` + `pod_torch_capability.py install` once
Running. Every OTHER track remains non-launchable by design
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

