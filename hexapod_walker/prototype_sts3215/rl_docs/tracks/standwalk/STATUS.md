# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~17:0x: **Steering branch (Next#2) FULLY RESOLVED,
both seeds — comparator noise, not a real lever effect.** `cont-b`/
`cont-c` (2nd/3rd zero-lever seed0 continuations) verdicted PASS; n=3
seed0 band: pt 0.157-0.200, cb_pos 0.121-0.132, cb_neg 0.152-0.190.
(a) the seed0 "9/10 lever FAIL" figure doesn't survive: `cont-b`/
`cont-c` (themselves zero-lever) also FAIL vs `cont` single-control,
proving that comparator invalid; band-scored, only 1/10 cells
(`yawarm1p5`) wins both cb signs, matching seed1. (b) seed0 cb_neg
does NOT collapse (0.152-0.190, tracks frozen-parent-s0 0.170) unlike
seed1's collapsed 0.120-0.138 — that erosion is SEED1-SPECIFIC.
Binding: frozen parents stay the best steering checkpoints on both
seeds; NO lever acquisition. Manifest: `logs/ckpt_eval/
rescore_turn_authority_09-04/manifest_n4.json`.

Also this cycle: **Next#1 tooling landed** — `run_episode` persists
the per-episode DR draw (`ep["randomization"]`, additive/bit-exact-off
when DR is off) + new `audit_dr_hold_correlate.py` (fired-vs-clean
median + standardized-mean-diff per DR field, ranked). Tests green;
snapshotted `exp/standwalk-dr-draw-logging-09-04`. Smoke-test vs the
k=8 checkpoint launched on its own pod (train-5) — correlation read
is new Next item 1.

Prior updates (09-04 ~13:2x..~16:3x) archived verbatim in `archive/
standwalk_STATUS_journal_2026-09-04{hh,jj,kk}_trim.md`.

## Next (updated 09-04 ~17:0x)

1. **DR-draw / hold_min_load correlation (tooling landed this cycle) —
   read the smoke-test output.** Once `logs/ckpt_eval/
   ..._acq8m_mlcontprice8_cmdstress/{dr0,owndr}/report.json` carry the
   new `randomization` field (pre-existing report predates it, moved
   to `..._prerandfield_bak/` so resume didn't skip the rerun), run
   `audit_dr_hold_correlate logs/.../owndr/report.json --reason
   hold_min_load`, read `ranked_fields`/`std_mean_diff`. n is small
   (~3 fired of 72) — a single-axis read is a LEAD, not a closed
   finding; `low_n_warning` gates trust.
2. **Steering branch — CLOSED both seeds (see Update).** No further
   lever acquisition; frozen parents (`cap29-stdwalklo-hi{,-s1}`)
   remain the reference steering checkpoints. Rise-stall stays CLOSED
   (09-03o archive).
3. **Closed** (archives 09-02{,b..h}, 09-03{a..u}, 09-04{aa,cc,dd,jj,
   kk}): architecture-split; lever/dose/seed sweeps (comparator-noise-
   resolved); cap29 acquisition (PARTIAL); log_std anneal grid; sto/
   det convergence; resamplematch; rise over_current dig-in;
   semantics-bank twins; IK-feasibility groundwork; mlcontprice2/8/16
   dose bracket (k=8 ceiling); steering FAIL-wall dig-in (both seeds).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb,cc,dd,gg,hh,ii,jj,kk}.
> Current state = newest Update at the TOP; don't act on archived Next.

## Fleet capacity note (updated 09-04 ~17:0x)

11/12 GPU slots free (cont-b/cont-c/cont-s1c finished+verdicted this
cycle; train-5 running the item-1 DR-draw smoke, eval-only, no train
slot consumed). train-4 still Pending (OOMKilled 08:06, recreated
from the fixed 4Gi-dshm spec) — `bootstrap_train_pod.sh
hexapod-mjx-train-4` once Running. Both lever/dose axes CLOSED this
cycle; only standwalk work left is the item-1 correlation read
(eval-only) until it names a concrete new axis to dose. Every OTHER
track remains non-launchable by design (`joystick`/`amp`/`cpg` DONE or
maintenance-only; `walkcurr` RETIRED; `todaypolicy` DELIVERED).

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

