# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-01 ~14:0x (`gradclip0p15-acq1` READ, 38M — TURN
AUTHORITY + STABILITY HOLD, WALK QUALITY REGRESSES). Plain English: at
acquisition scale, turn authority and zero-fall stability from the 2M
canary checkpoint both HOLD — but forward walk quality (progress/slip)
gets WORSE with the extra 36M steps, not better. Own
`probe_turn_authority`: wz_med pos 0.189/0.171 (avg 0.180), neg
-0.214/-0.218 (avg -0.216) — clears the >=0.15 bar both signs, close
to the 2M canary's own 0.198/-0.200 (essentially held, unlike every
prior acquisition arm in this campaign that eroded turn authority).
Own no-video `purewalk` det (`--modes walk --per-mode 8
--start-jitter-panel`): gait_valid 16/16, terminated 0/16 — zero
falls, matching the 2M canary's clean record and NOT reproducing
seed1's 44% over-current fall rate. But progress_ratio 0.313/0.324
(mean, both submodes) is BELOW the 0.40-0.48 wave-1 band and below
the 2M canary's own 0.38-0.40; slip/m 5.76/10.18 (mean) is well above
the 2.9 cap and above the canary's own 2.2-2.6. Not a full collapse
(FAIL needs prog<0.25 AND slip>4 together; progress stays >0.25
throughout) so this is **PARTIAL** by the gate's letter. Training
curve corroborates: reward flat after ~25% of the run (quarters
459/1995/2215/2191), periodic eval/walk/survived_frac=1.0 from 50%
onward (falls-free held throughout, not just at the final checkpoint),
eval/walk/speed_m_s stayed low/flat (~0.02-0.035 m/s) the whole back
half — a plateaued optimum, not an under-trained one; per the 08-21
ruling this is erosion to fix, not a "just run longer" case. Video
frame strip (walk_det_0) confirms visually: legs cycle, robot stays
upright, but progress is slow/slippy, not pathological. **Verdict:
do NOT promote acq1 (38M) over the 2M canary checkpoint as the
walk-quality reference — the 2M checkpoint remains the cleanest
turn-authority+walk-quality artifact in this lineage; acquisition
budget past ~2M buys nothing on turn authority (already at ceiling)
and costs walk quality.** Evidence:
`logs/ckpt_eval/turn_probe_yawcredit_gradclip0p15_acq1.json`,
`logs/ckpt_eval/purewalk_gradclip0p15_acq1_det.json/report.json`.

**Same-cycle follow-up (no new GPU launch, on-pod checkpoints):** probed
3 of acq1's own intermediate checkpoints (`purewalk` det, same
instrument) to see where the regression happens. s2097152 (~2M into
this run's OWN trajectory, not the same file as the verdicted
`-canary` checkpoint): prog 0.386/0.394 (good) but walk/det
TERMINATED 8/8 (100% fall rate!) and walk_startjitter/det 5/8, slip
6.1/5.0. s10485760 (~10M): 0 terminations either submode, prog
dropped to 0.286/0.294, slip 6.8/11.7. s20447232 (~20M): 0
terminations, prog 0.296/0.295, slip 6.8/12.5 — essentially unchanged
from 10M through the 38M final read. **Revised picture:** this run's
own early trajectory was UNSTABLE (not clean like the officially-read
canary checkpoint's 2M numbers) and stabilizes (zero falls) by ~10M;
progress/slip regress once between ~2M and ~10M and then hold flat
through 38M, rather than eroding continuously. **Methodology caveat:**
`acq1` is a FRESH 38M launch sharing recipe+seed=0 with the `-canary`
run and the same `turnpay_canary` ancestor — it is NOT a continuation
of the specific passing 2M canary checkpoint file, so "same seed"
does not reproduce that run's exact trajectory (4096-env PPO isn't
bit-deterministic in practice here). Treat any acq-vs-canary
comparison in this campaign as basin-comparison, not a strict
extension, unless the acquisition arm is launched via `--init-from`
the exact prior checkpoint. Evidence:
`logs/ckpt_eval/purewalk_gradclip0p15_acq1_{s2097152,s10485760,
s20447232}_det.json/report.json`.

Prior entries (grad-clip bracket close, `-canary-s1` seed split,
klrolltight2 close, yaw-critic build) VERBATIM in
`archive/standwalk_STATUS_journal_2026-09-01_trim.md`.

## Next (meta 09-01 ~14:0x)

1. **DONE this cycle.** `gradclip0p15-acq1` (seed0, 38M) read+verdicted
   PARTIAL: turn authority + stability retained at scale, walk quality
   (progress/slip) regressed vs the 2M canary checkpoint. See the
   Update above; do not re-verdict.
2. **Campaign reference artifact:** the 2M
   `cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary`
   checkpoint (NOT `-acq1`) is now the best turn-authority +
   walk-quality combination found in this campaign. Any stage-2
   distillation attempt that needs a turn-capable walk teacher should
   start from that checkpoint, not a longer-trained descendant, unless
   a future arm demonstrates it can hold walk quality at acquisition
   scale (e.g. an early-stop variant, or a reward fix that keeps
   pricing progress/slip past ~2M steps).
3. **DONE this cycle.** Probed 3 intermediate `-acq1` checkpoints
   (~2M/10M/20M) — regression is NOT monotonic-with-budget: this run's
   own early (~2M) trajectory was actually UNSTABLE (100% fall rate on
   walk/det, unlike the clean officially-read `-canary` 2M checkpoint —
   different basin despite matching seed/recipe), stabilizes to zero
   falls by ~10M, and progress/slip regress once by ~10M then hold
   flat to 38M. See the methodology-caveat paragraph above: acq-vs-
   canary numbers are basin comparisons, not strict extensions, since
   acq1 was not `--init-from`'d off the exact canary checkpoint file.
4. **Standing bar:** new dual distillations need pre-RL
   probe_turn_authority >=0.10 both signs; RL arms here are RETENTION
   only. gradclip0p15 (2M canary checkpoint specifically) is the
   reference recipe/artifact until a walk-quality-clean acquisition-
   scale replicate exists.
5. **Closed:** update-size constraints (freeze/value-warmup/
   kl-rollback), reward pricing, exploration magnitude, anchor
   dose/isolate-update, turn-skip, yaw-credit with NO clip, clip=0.5,
   clip=2.0, and now acquisition-scale retention of clip=0.15 (turn
   authority holds, walk quality doesn't). Evidence: archive + this
   update.

> Journal archives (VERBATIM): pre-08-30 in
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`; 08-30 through
> 09-01 ~14:0x in `archive/standwalk_STATUS_journal_2026-09-01_trim.md`.
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

Recipe basis: the `stance_dr10` lineage recipe (exact cfg in the
ledger/W&B). The rise-reference machinery (`extract_rise_ref.py`,
rise bank) is green as of 08-24. Bank/semantics-check the stance
reward ON MESH before the first launch (mass went 2.104 -> 3.50 kg;
thresholds calibrated on primitive may rank behaviors differently).

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
  rise/lower + the unification. Coordinate via STATUS, don't
  duplicate its mesh conversion arms.
- **Tooling flag (09-01):** the standard prestage `_mixedsession`
  harness's `rise->walk` mode-seq read for `gradclip0p15-canary`
  showed 100% `over_current` termination on EVERY submode, including
  plain `rise/det` — but that checkpoint's own cfg-matched
  `probe_turn_authority`/`purewalk` reads (this run's actual verdict
  evidence) show zero falls. Suspect `_mixedsession` isn't inheriting
  the run's `--cfg-set` overrides (goal/actions/safety height+height-
  gate params this recipe depends on) the way `_gate`/`_owncfg` do —
  consistent with the campaign's existing practice of treating
  `_mixedsession` as informational-only and never letting it flip a
  cfg-matched read. Someone should audit `ops.sh podeval`'s
  mixedsession invocation before trusting it for a real DONE-gate
  session read.

