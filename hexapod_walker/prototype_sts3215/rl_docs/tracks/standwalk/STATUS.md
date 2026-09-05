# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~18:1x: **Next#1 CLOSED at n=20 — genuine own-DR
variance, no dominant DR field.** Pulled the in-flight `--n 20`
cmdstress read (train-5, 240 seq eps: 14 `hold_min_load` fires) and
re-ran `audit_dr_hold_correlate` on dr0+owndr. Top field `latency_scale`
d=0.517 (fired median 1.073 vs clean 1.0) — real but not dominant
(every other field d<=0.39); fire timing/start_kind still spread
across buckets. The k=8 mechanism's residual ~4-6% own-DR fire rate is
genuine DR variance, not a missing field or code defect — matches the
pre-registered fallback; no further dose/field lever on this axis.
Manifest `/tmp/dr_correlate_n20.json`, reports in `logs/ckpt_eval/
..._mlcontprice8_cmdstress_n20/{dr0,owndr}/`.

Both Next items now CLOSED — the transition-stress mechanism sub-effort
is done at its k=8 ceiling. Refill: launched the track's actual
literal DONE-gate read (`eval_done_gate_session`, flat=1, n=8x8
shards) on mlcontprice8 (best fall-safety in the lineage) on train-6
(pushckpt+snapshot --sync done, code confirmed fresh) — never run on
this lineage before; eval-only. Registered via `evalpending` — new
Next item 1.

Prior updates (09-04 ~13:2x..~17:2x) archived verbatim in `archive/
standwalk_STATUS_journal_2026-09-04{hh,jj,kk,ll}_trim.md`.

## Next (updated 09-04 ~18:1x)

1. **Literal DONE-gate flat-only read on mlcontprice8 — IN FLIGHT on
   train-6.** `evalpending` entry `..._mlcontprice8_donegate_flatonly`
   auto-kicks a cycle on `session_verdict.json`. Read zero-falls first,
   then dir_err_med/slip_per_m_med vs the existing best flat-only band
   (44-45deg / 2.8-2.9, `cap29-stdwalklohi-acq1{,-s1}`, PARTIAL —
   steering gap). First time this stress-hardened lineage is read
   against the real gate, not the stress diet; pass = new best DONE
   candidate, fall = stress-diet training regressed base walk quality.
2. **DR-draw correlation — CLOSED (see Update).** No dominant DR field
   at n=20; own-DR variance stands, k=8 is the standing ceiling dose.
3. **Steering branch — CLOSED both seeds** (09-04 ~17:0x). No further
   lever acquisition; frozen parents (`cap29-stdwalklo-hi{,-s1}`)
   remain the reference steering checkpoints. Rise-stall stays CLOSED.
4. **Closed** (archives 09-02{,b..h}, 09-03{a..u}, 09-04{aa,cc,dd,jj,
   kk,ll}): architecture-split; lever/dose/seed sweeps; cap29
   acquisition (PARTIAL); log_std anneal grid; sto/det convergence;
   resamplematch; rise over_current dig-in; semantics-bank twins;
   IK-feasibility groundwork; mlcontprice2/8/16 dose bracket (k=8
   ceiling); steering FAIL-wall dig-in; DR-draw correlation (n=20).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z,aa,bb,cc,dd,gg,hh,ii,jj,
> kk,ll}. Current state = newest Update at the TOP; don't act on
> archived Next.

## Fleet capacity note (updated 09-04 ~18:1x)

10/12 GPU slots free (train-6 running the literal DONE-gate eval,
eval-only). train-4 still Pending (OOMKilled 08:06, recreated 4Gi-dshm
spec) — `bootstrap_train_pod.sh hexapod-mjx-train-4` once Running.
Pods 1/2/3/5/8/10 still run stale mixedsession/eval_checkpoint jobs
from already-verdicted runs — harmless CPU load, not launch-blocking.
Every OTHER track non-launchable by design (`joystick`/`amp`/`cpg`
DONE/maintenance; `walkcurr` RETIRED; `todaypolicy` DELIVERED).

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

- Sim-only evidence here; hardware stand/plant transfer goes through Robot
  Lab's serialized guarded runner.
- No stage-2 arm may warm-start from a primitive checkpoint.
- The joystick track owns generic mesh walking; this track owns
  rise/lower + the unification. Coordinate via STATUS, don't duplicate.
- `_mixedsession` (REPEATING rise<->walk<->lower) is a stress test,
  NOT the DONE-gate instrument (that's `eval_done_gate_session`,
  `ops.sh donegatecmd`, flat=1).
