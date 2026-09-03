# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~05:0x (idle-kick): item 0's flat-only donegate
session still mid-flight on train-6/7 (~91/90 mp4s, ETA unchanged
~08:3x UTC) -- while it runs, dispatched an EARLY INFORMAL READ on
spare pods (train-2/3, dualbc3-dagger 08-30 fast-read precedent):
walk-mode-only, no video, n=16 det+sto x DR-0+own-DR, SAME train cfg.
**direction_err clearly improved** vs the cap29-acq1 baseline
(46.8deg) on all 8 subgroups/2 seeds: 24.8-35.6deg. **sto/det
convergence holds at acquisition scale**: sto progress_ratio 84-92%
of det (was the old 5-8% collapse) -- canary finding replicates both
seeds. **slip/m MIXED**: dr0-det ties/beats 3.09 (2.83/3.12) but
dr0-sto/owndr-det/owndr-sto read worse (3.39-4.63). Zero falls in all
128 episodes. Reads gate-PARTIAL-shaped (steering fixed, slip not
uniform) not full PASS -- informal proxy only, real verdict still
awaits the video-bearing session. Evidence:
`logs/ckpt_eval/standwalk_stdwalklohi_acq1_{s0,s1}_fastwalkcheck/`.
Also: prior cycle's full-suite regression finished, 39F/256P (was
40F) -- all 5 banks pricing standwalk's LIVE levers (hold/getup/
rise_rock/stopcurrent/trans_drag) now green; remaining reds are 24
RETIRED walkcurr_pf/sv + 1 stale-log getup + 14 non-live-lever banks,
not blocking any funded arm, not chased.

Earlier updates (getup-ordering fix, q0-frame fixes, hold-bank
recalibrations, joint-frame-v2 bugs, tangle-spread close, the 09-02
merge-recovery/plant-stance/stdwalklohi-acq1 window) moved VERBATIM
to `archive/standwalk_STATUS_journal_2026-09-03{a,b,c,d,e}_trim.md`
and `2026-09-02{f,h}_trim.md`.

## Next (updated 09-02 ~18:3x)

0. **READ `logs/ckpt_eval/cw_..._stdwalklohi_acq1{,_s1}_donegate_
   flatonly/session_verdict.json`** once both land (n=32 det+sto
   DR-0+own-DR each; the 09-03 fast-check above already leans
   PARTIAL-shaped, see Update). Gate text in the ledger. PASS -> new
   steering/slip reference; PARTIAL -> item 1 next; FAIL -> credit-
   assignment (08-31 yaw-credit probe) next.
1. Steering gap (windowed course_err ~22-23 deg, cap 2.9) — was
   secondary to the sto/det asymmetry; worst course_speed_ratio dips
   land at the ~4s `walk_cmd_resample_s` boundaries, consistent with
   the closed turn-authority ceiling (wz_med 0.075-0.21). Revisit once
   item 0 reads back.
2. **Closed (full list in archives 09-02{,b..h}):** update-size/reward/
   exploration/anchor/turn-skip/yaw-credit/diet/duration/switch-jump/
   frame-blend/current-confound sweeps; cap29 acquisition (PARTIAL);
   walk-core log_std anneal dose grid (`hi` PASS, `mild` FAIL).

> Journal archives (VERBATIM, oldest->newest):
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`,
> `2026-09-01_trim.md`, `2026-09-02_trim.md`, `2026-09-02b_trim.md`,
> `2026-09-02c_trim.md`, `2026-09-02d_trim.md`, `2026-09-02e_trim.md`,
> `2026-09-02f_trim.md`, `2026-09-02g_trim.md`, `2026-09-02h_trim.md`,
> `2026-09-03a_trim.md`, `2026-09-03b_trim.md`, `2026-09-03c_trim.md`.
> Current state = newest Update at the TOP; don't act on archived Next.

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
- New launches already get `control.hz=100` (launcher-injected) and
  `env.model_source=mesh` (the default) — do not pin legacy values
  here, and never pin `model_source=primitive` in this track.
- Legacy champions MAY be queried as teachers (same obs layout), but
  they carry 25 Hz action scale and primitive dynamics: any
  distillation mechanism must handle the 25->100 Hz gap (query at
  25 Hz + interpolate, distill trajectories, DAgger with rate
  conversion, ...) and must MEASURE whether primitive-trained advice
  is good on mesh dynamics before trusting it.

## Stage 1 — mesh/100 Hz stance retrain (rise + lower)

Recipe basis: `stance_dr10` (exact cfg in ledger/W&B); rise-reference
machinery green since 08-24.
GATE (pre-registered): stance panel rise/hold/lower (pod_eval stance
modes), n>=12, det+sto, DR-0 + own-DR: zero falls/tips, quiet hold
(no creep), rise/lower height tracking comparable to the legacy
champion's band. Absolute numbers shift with the +66% mass — the
first passing run's numbers become the recorded mesh reference band.

## Stage 2 — teacher distillation into the best walking model

Use the stage-1 policy as the rise/lower TEACHER. Walking source: the
joystick champion lineage (`stotight45-seed13`) or its mesh-era
successor if the joystick track's in-flight mesh arms produce one
first — either adoption is PRE-REGISTERED here, never a silent
teacher swap (cpg containment rule applies). Mechanism is
cycle-designed (BC clone + RL fine-tune a la bcgait, KL-to-teacher,
phase-scheduled multi-teacher, ...); every mechanism arm pre-registers
its gate and a matched control.

DONE GATE (the track's): ONE mesh-family 100 Hz policy, from sit:
rise -> randomized 60 s joystick command script -> lower to sit.
Zero falls, directions followed, slip/m within the joystick band
(<=~2.9), held-out panel n>=12, det+sto, DR-0 + own-DR.
`eval_joystick_gate` covers the walk segment; the sit->rise->walk->
lower session harness is stage-2 tooling to build.

## Landmines

- Sim only — hardware stand/plant transfer stays operator-owned.
- No stage-2 arm may warm-start from a primitive checkpoint.
- The joystick track owns generic mesh walking; this track owns
  rise/lower + the unification. Coordinate via STATUS, don't duplicate
  its mesh conversion arms.
- `_mixedsession` (REPEATING rise<->walk<->lower) is a stress test, NOT
  the DONE-gate instrument; the gate read is `eval_done_gate_session`
  (`ops.sh donegatecmd`, flat=1).

