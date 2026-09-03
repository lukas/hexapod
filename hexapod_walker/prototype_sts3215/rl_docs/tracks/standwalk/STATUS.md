# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~19:1x (**Next item 2, branch (a) 4-ARM CANARY
BATCH COMPLETE — ALL 4 FAIL; branch (a) REFUTED. Next item 1
(rise-stall faithful replay) CLOSED same cycle, with a mesh/primitive
model-family test-harness bug fixed along the way.**)

**Item 2 (steering, top item):** all 4 omega-boost canary cells now
read (`cap29-stdwalklohi-omegaboost{1p5,2p0}{,-s1}`, 2 doses x 2
seeds, concurrent cycles): FAIL/FAIL/FAIL/FAIL. Every cell reproduces
the SAME sign-asymmetric signature already seen in `combskip`: the
negative-wz combined-tick side clearly beats the pre-registered
comparator (+57-61% magnitude) but the positive side falls short
(does not beat +0.145 rad/s), AND pure-turn wz_med regresses >10% vs
the matched control on BOTH signs in every cell (10-25%, not dose-
monotonic — 1.5-s1 regressed worse than 2.0-s0). Conclusion: the
scripted-teacher-level authority gain from `train.bc_anchor_
teacher_omega_boost` (proven zero-training on the SCRIPTED teacher
itself) does NOT survive PPO fine-tuning into a real, symmetric
combined-tick wz gain on the RL checkpoint — it trades pure-turn
authority for a lopsided partial gain, 4/4 cells, 2 independent
mechanisms now (`combskip`, `omegaboost`). **Branch (a) is REFUTED.**
Per the pre-registered fallback, the remaining candidates are (i) the
`tripod_gait.py` class-level combined vx+omega foot-target geometry
edit (shared hardware-adjacent code — needs its own before/after
validation harness before any launch) or (ii) a combined-tick-
targeted course/yaw reward term (needs a `test_task_semantics.py`
bank entry pinning the exploit before any launch, per RESEARCH_RULES).
Neither is launch-ready yet — this is the track's next NEW-CODE item.
Evidence: `logs/ckpt_eval/probe_turn_authority_omegaboost{1p5,2p0}_
{s0,s1}_combined_09-03.json`, `..._cap29_stdwalklo_hi{,_s1}_combined_
09-03.json`; ledger verdicts on all 4 run names.

**Item 1 (rise-stall, CLOSED):** finished the faithful-replay twin
(`test_task_semantics.py::test_rise_stall_replay_*`, built off the
real `yawdensity_s1_riseAB_cap29cf` silent-stall trace). Two findings:
(1) **A REAL BUG, now FIXED**: the replay ran on `conftest.py`'s
session-pinned `HEXAPOD_MODEL_SOURCE=primitive` the whole time,
silently ignoring its own `env.model_source: mesh` cfg override
(`resolve_model_source()` checks the env var first, unconditionally)
— the hand-built bank above it had the SAME latent bug but happened
to still pass qualitatively either way since it's purely comparative;
the faithful replay diverged wildly (wrong mass family) until wrapped
in a new `_mesh_family_env()` context manager (now applied to both
banks). (2) Once genuinely mesh-family, the replay **does not fully
confirm the hand-built twin's story**: the real recorded "stall" ends
up HIGHER (h_end 29.3mm) than an early-frozen "partial" hold
(19.4mm) — the opposite of the synthetic +40deg-offset twin's height
ranking — because the real fight keeps inching upward the whole
episode while a frozen hold sags. The TRUE distinguishing signature
is duration at dangerous current, not final height: real stall
sustains >2A for ~25/30s vs partial's ~1s (`over2A_s`), and the
pricing gap survives but shrinks (partial beats stall by ~82pts/30s,
not the hand-built twin's larger margin). Tests recalibrated to match
measured reality (not re-inflated to match the synthetic version), per
the twin's own pre-written instruction to trust the faithful replay
over the hand-built one on disagreement. Net effect: the height-
ranking half of the rise-stall reward-fix motivation is retracted;
the current-duration half still stands. No reward change made yet —
a future rise-stall fix should price sustained near-ceiling current
directly (matching `over2A_s`), not a stall-vs-partial-height
framing. 4/4 replay tests green; full `-k rise`/`-k steer` reruns
green (18 tests). Snapshot `54cb4765`
(`exp/standwalk-risestall-replay-mesh-family-fix-09-03`).

Earlier update, 2026-09-03 ~17:5x (root cause found + omega-boost
lever built + the 4-arm canary batch launched — now fully read and
REFUTED, see the top Update) moved VERBATIM to `archive/standwalk_
STATUS_journal_2026-09-03n_trim.md`.

Earlier updates (17:2x combskip verdicts/branch-b REFUTED, 16:4x
branch-(b) lever build+launch, 16:0x combined-probe mechanism
discovery, 15:2x rollout-trace tool, 15:0x semantics-bank twins, and
everything before) moved VERBATIM to `archive/standwalk_STATUS_
journal_2026-09-03m_trim.md` (which points on to `...-03l_trim.md` —
noted gap: that file and the `09-03{a..k}`/`09-02{f,h}` files it in
turn points to do not exist on disk, unrepaired here).

## Next (updated 09-03 ~19:1x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** Faithful-replay twin
   built, a model-family test-harness bug fixed
   (`_mesh_family_env()`), tests recalibrated to the real (not
   hand-built) signature. See Update. No reward code changed; a
   future fix should price sustained near-ceiling current directly
   (`over2A_s`-style), not a stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM. Branch (a) (omega-boost) now ALSO
   REFUTED 09-03 ~19:1x — 4/4 canary cells FAIL** (same sign-
   asymmetric + pure-turn-regression pattern as branch (b)'s
   `combskip`). Two candidates remain, NEITHER launch-ready:
   (i) `tripod_gait.py` class-level combined vx+omega foot-target
   geometry edit (shared hardware-adjacent code — build its own
   before/after validation harness first, e.g. extend
   `probe_turn_authority.py`/`test_probe_turn_authority.py` to cover
   the edited function directly); (ii) a combined-tick-targeted
   course/yaw reward term (needs a `test_task_semantics.py` bank
   entry pinning the current combined-tick exploit BEFORE any reward
   change, per RESEARCH_RULES — nothing built yet). NEXT CYCLE: pick
   one, build its validation/bank harness, THEN launch a matched
   canary — don't launch either without that harness. Prior findings
   still hold: turn-in-place authority alone is strong everywhere (wz
   ~0.18-0.23 on 0.25 cmd); diet-rate, structural co-occurrence
   (`walk_yaw_zero_frac`), combined-tick BC-anchor-skip, and now
   teacher-omega-boost are ALL refuted, 2+ seeds each — 3 independent
   mechanisms down. Must-fix riders for whatever arm eventually
   launches: (a) current-cap trip threshold must sit BELOW the 2.64 A
   model ceiling (cap 2.9 silently disables over_current); (b) verify
   `safety.max_current_a`/speed keys in the ledger `extra_args`
   explicitly, names lie; (c) investigate the family-wide Q3
   training-reward collapse (all lineage members incl. both combskip
   seeds) before trusting any 2M canary endpoint again.
3. **Closed (archives 09-02{,b..h}, 09-03{a..m}):** update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound/combined-tick-anchor-skip
   sweeps; cap29 acquisition (PARTIAL); log_std anneal dose grid (`hi`
   PASS, `mild` FAIL); item 0 sto/det convergence-at-scale (PASS);
   resamplematch diet-match-rate hypothesis (refuted both doses/seeds);
   rise over_current dig-in (genuine lineage fragility, not an
   instrument defect); steering/rise-stall semantics-bank twins (both
   PASS).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n}. Current state = newest Update at the TOP; don't act
> on archived Next.

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

