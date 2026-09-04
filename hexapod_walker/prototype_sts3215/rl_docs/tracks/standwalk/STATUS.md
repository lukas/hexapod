# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~04:3x (**Seed1 twin `cap29-stdwalklohi-triplecore-
s1-r2` also CANARY FAIL - MECHANISM — the 2-seed `TripleGruActor
CriticPolicy` canary now CLOSES 2/2 FAIL, confirming seed0's read was
not a fluke.**)

`probe_turn_authority.py --vx-cmds` (full 85-key non-train cfg-set
replay; `logs/ckpt_eval/probe_turn_authority_triplecore_s1_r2_
combined_09-04.json` vs control `cap29-stdwalklo-hi-s1`'s cached
combined read): combined-tick (vx=0.08) `wz_med` +0.086/-0.103 vs
control +0.087/-0.137(-.142) — FLAT on the positive sign (-0.7%, the
gate's own explicit "flat" FAIL trigger) and ~25-28% WEAKER on the
negative sign; no combined-tick win on either sign, let alone both.
Pure-turn (vx=0) also regressed past the 10% cap on both signs
(+0.182 vs control +0.228 = -20.2%; -0.201 vs control -0.246 = -18.5%),
matching seed0's shape closely (13-26% seed0 vs 18-20% seed1 — same
double-fail signature, not seed noise). No falls in any of the 8
probe rows; training reward quarters [29.6, 49.5, -105.1, 27.8], final
177/126.6 (s0/s1) — same family Q3-dip shape. Full verdict: ledger /
W&B notes for `...-triplecore-s1-r2`.

**Reading, both seeds together:** a fully architecturally isolated
pure-turn core (`core_t` starts as a byte-exact copy of `core_a`, so
it begins at exact parity with the shared-core control) still lost
10-26% of its pure-turn authority AND gained ZERO combined-tick
benefit in both seeds — worse on every axis than the shared-core Dual
control it was meant to beat. This is real evidence against the
representational-interference hypothesis itself, not just this one
lever: if two skills fighting over one representation were the cause,
isolating them should have protected pure-turn at minimum. It didn't.
The better-supported explanation is now upstream of the policy
entirely: the 09-03 16:1x zero-training finding that the SCRIPTED
teacher itself (the BC-anchor's own imitation target) retains only
~33% of its pure-turn `wz` once walking forward — the RL-trained Dual
control already exceeds that (38-49% combined/pure retention), so the
ceiling any policy-capacity mechanism can buy is bounded by how good
the TEACHER's combined-motion turn command is, not by how the policy
represents it. **Architecture-split lever CLOSED 2/2 FAIL. Do not
build the `yaw_critic.py`-on-Triple follow-up** (prior Next item) —
it inherits this now-doubted premise. Next step is teacher-side: build
a zero-training instrument that measures/repairs the scripted
`TripodGait`'s own combined-motion turn-command shortfall (candidate
fix direction: the foot-contact/thrust-budget mechanism named in the
09-03 16:1x note) BEFORE trying another policy-side mechanism.

Build details for `TripleGruActorCriticPolicy` (architecture, CLI,
tests, the self-inflicted net_arch-derivation bug + same-cycle fix)
moved VERBATIM to `archive/standwalk_STATUS_journal_2026-09-04w_trim.md`;
seed0's own verdict banner moved VERBATIM to `archive/standwalk_
STATUS_journal_2026-09-04x_trim.md`.

## Next (updated 09-04 ~04:3x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md` for the full write-
   up. No reward code changed; a future fix should price sustained
   near-ceiling current directly (`over2A_s`-style), not a
   stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM, now teacher-side.
   `TripleGruActorCriticPolicy` CLOSED 2/2 FAIL this cycle (see
   banner) — the whole policy-capacity/architecture-split family
   (open-loop geometry/dose levers 8/8 FAIL + this 2/2 FAIL) is now
   exhausted. NEXT: build a zero-training instrument on the SCRIPTED
   `TripodGait` teacher itself to measure/repair its own combined-
   motion turn-command shortfall (09-03 16:1x finding: only ~33% of
   pure-turn `wz` survives at vx=0.08) — candidate mechanism named in
   that finding is a shared foot-contact/thrust budget under the
   tripod gait; a fix there raises the BC-anchor's own imitation
   TARGET, which every downstream policy mechanism has been bounded
   by. Do NOT queue the `yaw_critic.py`-on-Triple follow-up (inherits
   the now-doubted interference premise) or another policy-side dose/
   architecture lever before this teacher-side measurement pass.
3. **Closed (archives 09-02{,b..h}, 09-03{a..u}):** yaw-arm-scale
   candidate (i)-v2 dose x seed grid (4/4 FAIL, 09-04); update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound/combined-tick-anchor-skip/
   omega-boost (both directions)/combined-yaw-boost sweeps; cap29
   acquisition (PARTIAL); log_std anneal dose grid (`hi` PASS, `mild`
   FAIL); item 0 sto/det convergence-at-scale (PASS); resamplematch
   diet-match-rate hypothesis (refuted both doses/seeds); rise
   over_current dig-in
   (genuine lineage fragility, not an instrument defect); rise-stall
   faithful replay (CLOSED, see item 1); steering/rise-stall
   semantics-bank twins (both PASS); candidate (i) IK-feasibility +
   naive slew-saturation groundwork (superseded by the per-axis
   split above, see archive 09-03q for the superseded framing).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x}. Current state = newest
> Update at the TOP; don't act on archived Next.

## Fleet capacity note (updated 09-04 ~04:3x)

Both `triplecore-{r2,s1-r2}` seeds verdicted FAIL this cycle — 2 GPU
slots freed, both idle. Every OTHER track remains non-launchable by
design (`joystick`/`amp`/`cpg` DONE or maintenance-only; `walkcurr`
RETIRED; `todaypolicy` DELIVERED). The next standwalk step (Next
item 2, teacher-side scripted-gait measurement) is ZERO-TRAINING
instrument/tool-building work (extend `probe_turn_authority.py` or a
sibling tool against `--policy scripted`, no GPU needed) before any
new training arm is launchable — do not launch a 3rd architecture-
split seed or a new policy-side lever on the now-closed hypothesis.

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

