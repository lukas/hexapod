# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~16:3x: **`mlcontprice16` (k=16.0, top of the
3-point dose bracket) is CANARY FAIL-MECHANISM — dose bracket CLOSED,
k=8 stands as the ceiling.** `eval_cmd_stress` (seed 93000, --strict):
26 hold_min_load fires, session_complete_frac 0.88 (<0.95),
gait_valid_frac 0.991 with sacrificed_legs_seen=[1,2,3,4] (the
companion pathology k=8 fully closed REAPPEARS), direction_err_med
48.72deg vs acq8m's 43.1deg (+13.0%, breaches the 10% cap). DATA-
QUALITY NOTE (repeat of the mlcontprice2 bug, now fixed in tooling):
ran at `--n 18` -> n_episodes=216 (12*N per the harness's actual
6-bucket-x-2-pass structure), NOT the matched `--n 6`->72-total read
k=8 used — this run's own pre-registered "n=18/mode/pass (72 total)"
text was internally inconsistent. Rate-normalized: combined dr0+ownDR
fire rate 12.0% (dr0 15.7%, ownDR 8.3%) is WORSE than k=8's matched
4.2%, worse than k=2's rate-normalized 8.8%, and worse than the
unfixed acq8m baseline's own 8.3% — dose-response is NON-monotonic
(0->8.3%, 2->8.8%, 8->4.2% best, 16->12.0% worst). The sacrificed-leg/
direction-err/session-complete breaches are median/fraction stats,
not raw counts, so they corroborate the FAIL independent of the n
mismatch. Dose search on `reward.k_hold_min_load_short` is CLOSED
(both directions bracketed: k=2 below threshold, k=16 past the
ceiling and actively corrupting walk quality); k=8 is the adopted
standing recipe. TOOLING FIX landed: `ops.sh evalcmdstress` doc now
states the matched-72 read needs the DEFAULT `--n 6` (12*N formula),
not 18 or 54, to stop a third mis-derivation. Full report:
`logs/ckpt_eval/cw_standwalk_stage2_dualbc6_turncap_mirroraug_
yawcredit_gradclip0p15_cap29_stdwalklohi_transtress_s1_acq8m_
mlcontprice16_cmdstress/stress_verdict.json`.

Prior update (09-04 ~16:2x — steering-branch dig-in resolution,
`cont-b`/`cont-c` launch) archived verbatim in `archive/standwalk_
STATUS_journal_2026-09-04jj_trim.md`; that item (Next #2) is
untouched by this update and remains owned by its own cycle.

Older updates (09-04 ~13:2x, ~14:1x, ~14:4x, ~16:2x — mlcontprice2
FAIL-MECHANISM/dose-bracket-to-k16 read, cont-s1b launch, steering
dig-in resolution) archived verbatim in `archive/standwalk_
STATUS_journal_2026-09-04{hh,jj}_trim.md`.

## Next (updated 09-04 ~16:3x)

1. **Universal-command branch — dose bracket CLOSED (see Update):
   k=0 (8.3%) -> k=2 (FAIL, below threshold, ~8.8%) -> k=8
   (FAIL-MECHANISM but the real partial fix, 4.2%, best) -> k=16
   (FAIL-MECHANISM, worse than baseline, 12.0%, dose ceiling
   confirmed both directions). Adopt k=8's recipe
   (`safety.hold_min_load_ema_continuous=1`,
   `reward.k_hold_min_load_short=8.0`) as standing; do NOT raise the
   dose further. NEXT LEVER (own-DR-specific, not dose): add
   per-episode DR-draw logging to `eval_cmd_stress`/`eval_checkpoint`
   own-DR pass (record the sampled friction/mass/gain/etc multipliers
   per episode) and correlate against which episodes still fire
   `hold_min_load` at k=8, to find the specific randomized axis the
   price under-covers. This is new harness code (SPECIFICATION work,
   not a reason to wait) — write it, smoke-test against a k=8 rerun,
   snapshot, before the next acquisition spend on this axis.
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
   twins; IK-feasibility groundwork; mlcontprice2/mlcontprice16 dose
   bracket (k=2 below threshold, k=8 the adopted ceiling, k=16 past it
   and regressing — 09-04 ~14:4x/~16:3x).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb,cc,dd,gg,hh,ii,jj}.
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

