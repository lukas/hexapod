# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-05 ~02:4x: **Infra recovery — DONE-gate eval RELAUNCHED
on train-9.** train-6 (running the 09-04 ~18:1x DONE-gate flat-only
read) was found OOMKilled (host-level, exit 137, container 96Gi limit
hit ~22:48Z 09-04 — the eval's own `--shards 8`, 8 concurrent
`eval_checkpoint` subprocesses each with `--video` against the mesh/
100Hz model, plus this pod's usual accumulated stale-process load, is
the likely cause; matches the recurring "idle pod accumulates memory"
pattern from train-0/4/10 incidents). `pending_evals.json`'s entry had
already silently expired (8h TTL) with no verdict ever landing — the
read was fully lost, not just delayed. Recovery: deleted+recreated
train-6 from the manifest (now Pending on host CPU, normal, will
schedule when capacity frees — do NOT force it); pushed the
`mlcontprice8` checkpoint + synced code to train-9 (clean pod, no
stale processes, confirmed via `ps`) and relaunched the identical
`donegatecmd` flat=1 command with **`--jobs 4`** added (caps concurrent
shard subprocesses at 4 instead of 8, same `--shards 8` statistical
layout/seed streams) to keep memory headroom — confirmed at ~40GB/96GB
cgroup usage with 4 shard workers running, well clear of the limit.
Re-registered via `evalpending` (train-9). Still the track's first read
of this lineage against the real gate, not the stress diet.

Prior updates (09-04 ~13:2x..~18:1x) archived verbatim in `archive/
standwalk_STATUS_journal_2026-09-04{hh,jj,kk,ll}_trim.md`.

## Next (updated 09-05 ~02:4x)

1. **Literal DONE-gate flat-only read on mlcontprice8 — IN FLIGHT on
   train-9** (relaunched after train-6 OOMKilled lost the first
   attempt; see Update). `evalpending` entry
   `..._mlcontprice8_donegate_flatonly` auto-kicks a cycle on
   `session_verdict.json`. Read zero-falls first, then
   dir_err_med/slip_per_m_med vs the existing best flat-only band
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

## Fleet capacity note (updated 09-05 ~02:4x)

10/12 GPU slots free (train-9 running the literal DONE-gate eval,
eval-only, `--jobs 4`). train-6 OOMKilled (see Update) — recreated,
Pending on host CPU, will schedule + need `bootstrap_train_pod.sh
hexapod-mjx-train-6` once Running (do not force). train-4 previously
recovered the same way, now Running. Pods 1/2/3/5/8/10/11 still run
stale mixedsession/eval_checkpoint jobs from already-verdicted runs —
harmless CPU load, not launch-blocking, but a slow-accumulating OOM
risk on long-lived pods (3rd such incident after train-0, train-4/10)
— a standing cleanup lever if this recurs: `ops.sh procs <pod>` +
kill stale multiprocessing-fork children before a memory-heavy
`--shards`+`--video` job, or route such jobs to the freshest pod.
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

- Sim only — hardware stand/plant transfer stays operator-owned.
- No stage-2 arm may warm-start from a primitive checkpoint.
- The joystick track owns generic mesh walking; this track owns
  rise/lower + the unification. Coordinate via STATUS, don't duplicate.
- `_mixedsession` (REPEATING rise<->walk<->lower) is a stress test,
  NOT the DONE-gate instrument (that's `eval_done_gate_session`,
  `ops.sh donegatecmd`, flat=1).

