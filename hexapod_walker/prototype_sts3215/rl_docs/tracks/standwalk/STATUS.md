# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-08-30 ~13:3x (**`dualbc3-dagger-anchor14coef1-acq8m`
ACQUISITION PASS (own-scope) — the 8M continuation compounds cleanly
past its own 2M canary snapshot.**) Plain English: fast spare-pod
det+sto walk-only read (`/tmp/fastcheck_acq8m_s{0,1}_{det,sto}`,
train-4/train-5, weights unchanged) while the ledger's own
gate/owncfg/mixedsession harness ran on train-0/train-1 (both
watcher-auto-launched at 13:02/13:07, historically ~1.5-3h). seed0
det: `gait_valid` 8/8, `sacrificed_legs=[]`, 0/8 terms, `progress_ratio`
med 0.429 (up from the 2M canary's 0.28), `slip/m` med 2.55 (down from
3.39). seed1 det (informal cross-check, own verdict belongs to a
concurrent cycle claiming that run): `progress_ratio` med 0.423 (up
from 0.39), `slip/m` med 2.45 (down from 2.71) — same improving shape.
Sto weaker but net-forward, zero falls/sac both seeds (prog med
~0.077-0.078, slip/m med ~11 — actually better than the canary's own
sto numbers). Reward quarters rose every quarter both seeds
(`[-62.5,-57.0,239.2,590.2]` / `[-83.7,-9.5,253.5,587.1]`). Clears the
run's own pre-registered PASS clause (gait_valid stays >=5/6 zero-sac
AND progress_ratio improves with slip/m flat-or-better) on both
seeds. Verdicted `cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-acq8m`
PASS; `-acq8m-s1`'s own formal verdict is a concurrent cycle's (same
evidence pattern independently confirmed here as a cross-check).
**Next, per the identical anchor14-walkretaincoef1-rescue-acq8m
precedent: the real decision point is the `eval_mixed_session`
sit→rise→walk→lower DONE-gate read**, already running per-seed
(watcher auto-launch, `logs/ckpt_eval/..._acq8m{,_s1}_mixedsession/`)
— do not commit further RL budget to this lineage until that lands.
Cleaned up the controller-diagnostic `/tmp/fastcheck_*` artifacts on
train-4/train-5 after reading them. Re-swept other tracks: nothing
else legal (joystick/amp/cpg DONE-or-`[operator]`-maintenance,
walkcurr `[operator]`-blocked, backlog empty, all 12 pods either
free or running the in-flight mixedsession/gate harness reads).

Update, 2026-08-30 ~12:2x (**`dualbc3-dagger-anchor14coef1-canary{,-s1}`
BOTH CANARY PASS — first anchor14coef1 canary pair run on a base
checkpoint independently pre-verified to walk net-forward; PROMOTED,
both seeds now training an 8M acquisition continuation.**) Plain
English: the prior entry's canary pair finished training (2.03M steps
each) but the ledger's own video-bearing gate/owncfg/mixedsession
harness was still genuinely mid-flight on-pod (~1-1.5h ETA, video-
every=1 4-mode panel) — rather than wait, ran a fast `--no-video`
det+sto walk-only read on two spare pods (train-2/train-3, weights
unchanged, controller-local diagnostic only). Both seeds clean: det
walk `gait_valid` 8/8, `sacrificed_legs=[]` every episode, 0/8
terminations, `progress_ratio` **0.28 (seed0) / 0.39 (seed1)** —
comfortably clears the 0.10-0.18 band the same anchor14coef1 recipe
showed on the OLD `stotight45` teacher, `slip/m` 3.39/2.71,
`forward_dist_m` 0.63-0.90m/30s at 0.037-0.044 m/s (real net motion,
not quiver). Full-episode `direction_err_mean_deg` reads high
(58-62deg) but the windowed `course_err_1s_med_deg` is clean (2-6deg)
— a low-speed-early-in-episode artifact (same shape CURRENT_TRUTHS
already names for this campaign), not a wrong-way walk. Sto mode is
weaker (prog_ratio 0.04-0.06, slip/m 13-17) but still net-forward with
zero falls/sac — expected 2M-canary softness, not the gate's own PASS
criterion (det walk). WIRING CHECK clean both seeds
(`bc_anchor_loss_walk` falling to 0.0005-0.006, `bc_anchor_fill_walk`
monotonic 12k->~39k, straight from cached `wandb_history.csv`).
**Notably, seed1 — historically the catastrophe-prone seed on the OLD
teacher lineage — is now the STRONGER of the two**, confirming this is
a genuinely repaired base, not a lucky seed0 draw. This is the
gate's own pre-registered PASS branch ("the upstream base is now
pre-verified walking net-forward" — see the prior entry): the
dualbc2 pair's FAILs traced entirely to a broken BASE (BC compounding
error), and this result shows the identical RL recipe genuinely
ACQUIRES skill (not just avoids catastrophe) once given a real walking
base. **Action per the gate's own PASS clause: promoted both seeds to
an 8M acquisition continuation**, same convention +
std-anneal bundle as the `anchor14-walkretaincoef1-rescue-acq8m`
precedent (`--log-std-final -4.0 --log-std-anneal-frac 0.5
--gru-dual-log-std-split --log-std-anneal-core stance`) —
`cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-acq8m{,-s1}`, both
VERIFIED RUNNING (train-0/train-1, warm-started correctly, ps-
confirmed genuine GPU training). Gate for the 8M read: BOTH seeds keep
`gait_valid>=5/6` zero-sac AND `progress_ratio` improves over this
canary's own 0.28/0.39 snapshot with slip/m flat-or-better; FAIL only
if the anchor4-class catastrophe (sacrificed legs) reappears under
more budget. Evidence: `/tmp/fastcheck_dualbc3_s{0,1}_{det,sto}/
report.json` (controller-local diagnostic, not ledger-tracked — the
ledger's own gate/owncfg/mixedsession passes are still computing on
train-0/train-1's prior occupants and will sync when done, informational
only per the fast-read precedent this exact track has used repeatedly
this campaign). 8 GPU pods free after the two launches (10 -> 8);
other tracks re-swept, nothing else legal (joystick/amp/cpg DONE-or-
`[operator]`-maintenance, walkcurr `[operator]`-blocked). CYCLE_WORKED.

Update, 2026-08-30 ~11:2x (**`dualbc3_dagger` finished (background CPU,
picked up from the prior entry's launch) — `quick_probe` output was
SILENT on the exact number that matters because of a print-precedence
bug; fixed the bug, re-ran the check standalone against the saved
checkpoint (no retraining), confirmed it CLEARS the 0.05m bar, and
launched the paired RL canary the "Next" item called for.**) Plain
English: `distill_gru.quick_probe`'s own net-displacement WARNING
(added 08-30 ~10:2x after the dualbc2 lesson) only printed the
`net_disp_m` numbers INSIDE the `if max(disps) < 0.05` ternary — i.e.
adjacent string-literal concatenation happened before the ternary was
applied, so the whole `net_disp_m [...]` substring (values AND the
WARNING suffix) only ever appeared when the checkpoint was BAD. When
displacement was fine, the line printed nothing extra at all — exactly
backwards from the intent, and exactly why `dualbc3_dagger.log`'s own
`probe walk: ep returns ['3660','3918']` line showed strong returns
with zero displacement readout: the check had silently passed but
hid the evidence. Fixed (`net_disp_m` always prints, WARNING appended
only when bad; unit-verified with a 3-case string-building smoke,
snapshot `quick-probe-fixed-heading-fix`→now `0f55c8c1`). Reran the
check standalone: loaded the SAVED `dualbc3_dagger.zip` weights into a
freshly-built matching env (same exact `--cfg-set` command replayed,
BC/DAgger training monkeypatched out — no retraining, no wasted
compute) and called `quick_probe` directly: **walk-mode
`net_disp_m` 0.463m / 0.493m over a 15s fixed-heading episode** — an
order of magnitude above the 0.05m in-place-quiver threshold and
~20-100x `dualbc2`'s 0.004-0.026m. The DAgger fix worked: this base
checkpoint genuinely walks net-forward. **Action per the prior
entry's own pre-registered "Next": launched the anchor14coef1 RL
canary pair** (`cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-
canary{,-s1}`, respec'd from the dualbc2 pair with only `--init-from`
swapped to `dualbc3_dagger.zip`, same 2M mechanism-health gate/
convention, both VERIFIED RUNNING train-0/train-1). If either seed
now shows the anchor4-class catastrophe or a worsening probe
pathology, that would implicate the anchor14coef1 recipe itself (the
base is pre-verified walking this time, unlike the dualbc2 pair where
the base was the confound). 10 GPU pods free after this launch; other
tracks re-swept, nothing else legal (joystick/amp/cpg DONE-or-
`[operator]`-maintenance-only, walkcurr `[operator]`-blocked). Prior
banner below.

Update, 2026-08-30 ~10:3x (**Root cause of the `dualbc2_allheadwalk`
never-walks defect ISOLATED to plain-BC compounding error, not
context/mix/architecture — DAgger fix built and the full-scale rerun
LAUNCHED (`dualbc3_dagger`, background CPU, single lever vs the
FAILED recipe).**) Plain English: picked up the 09:1x entry's own
"Next" item (diagnose before re-funding). Ran 4 small scoped probes
(24-episode toy-scale `distill_gru` reruns, CPU, ~1-2min each) to
narrow the cause instead of guessing at a fix:
1. **Context/leftover-cfg hypothesis REFUTED.** `distill_gru._build_cfg`
   layers a `R3_CFG` baseline (an older recipe's defaults, e.g.
   `walk_cmd_blend_s_min=0.1`) UNDER the real launch's `--cfg-set`
   overrides — a plausible context mismatch vs the teacher's own
   training cfg (which never goes through `_build_cfg`/`R3_CFG` at
   all). Directly probed the RAW walk teacher
   (`..._singleframe_acq1_stdanneal.zip`, itself gate-PASSED 06:3x)
   inside (A) the exact merged dualbc2 context and (B) a plain
   `load_config()`+overrides-only context with no `R3_CFG` residue:
   identical per-episode returns/displacement in both (e.g. one
   episode's return/net_disp_m matched to 4 decimal places across A
   and B) — the leftover keys have zero effect here, ruling this out.
   The raw teacher-in-context shows real net displacement on most
   draws (0.3-0.47m/15s) and near-zero on some (an expected
   `walk_stop_frac=0.15` stop-commanded segment, not a defect).
2. **Mode-mixing/dilution hypothesis REFUTED.** A `--dual --mix
   walk=1.0` toy rerun (rise/lower/hold dropped entirely, 100% walk
   data, same env/cfg) still collapsed to near-zero net displacement
   (0.004-0.006m over 15s) despite a plausible-looking BC actor MSE
   (~0.008) and decent single-episode returns (1219) — walking fails
   even with ZERO other-mode data to dilute it.
3. **Dual-core-architecture-bug hypothesis REFUTED.** The identical
   toy rerun WITHOUT `--dual` (plain `GruActorCriticPolicy`, no mode
   one-hot/routing at all) reproduced the exact same near-zero
   displacement (0.004-0.006m) — the `DualGruActorCriticPolicy`
   mode-gating code is not the culprit either.
4. **Classic BC compounding-error IS supported.** `train_student`
   trains the GRU actor by supervised BPTT on the teacher's
   open-loop-labeled trajectories only; the saved dualbc2 launch used
   `--dagger-rounds 0` (never invoked, despite the tool's own
   docstring precedent recipe using `--dagger-rounds 2` and
   `collect_dagger`'s own comment: "Fixes BC compounding error — the
   student learns recoveries on its own trajectory distribution").
   Adding a tiny 3-round/16-episode DAgger pass on top of the SAME
   walk-only toy setup measurably improved held-out closed-loop
   displacement on 2/4 replay episodes (0.038m, 0.088m vs 0.0005-
   0.004m for plain BC on all 4) — an order-of-magnitude direction
   change on a probe this small, consistent with compounding error
   being the dominant defect (the small budget is why it's not yet a
   full fix on all episodes).
**Action taken (not left as a placeholder): launched the real-scale
fix.** `ppo_goal_cw_standwalk_stage2_dualbc3_dagger.zip` — BYTE-
IDENTICAL to the failed `dualbc2_allheadwalk` command (same teachers,
mix, episodes/epochs, full 80-key merged cfg) with exactly ONE lever
added: `--dagger-rounds 2 --dagger-episodes 100` (the module's own
documented precedent dose). Running now, background CPU nohup,
`logs/distill_gru/dualbc3_dagger.log` (no ledger entry, same
convention as every prior `distill_gru` build — check the log/output
zip directly). **Next** once it lands: run the new `quick_probe`
net-displacement check first (already prints a WARNING under 0.05m —
this is exactly the guard that would have caught dualbc2 pre-launch);
only if it clears that bar, fund a fresh RL canary (the
`anchor14coef1` recipe already used is fine to reuse) — do NOT repeat
the 09:1x lesson of funding a GPU RL run on an undiagnosed walk clone.
If DAgger alone doesn't fully clear the 0.05m bar at full budget,
next levers in order: more dagger rounds/episodes (cheap, CPU-only,
try before anything else), then `--dagger-extra-mix walk=1.0
--dagger-extra-episodes N` to concentrate correction density on the
one broken mode. Toy probe checkpoints
(`/tmp/probe_walkonly_{dualbc,plaingru,dagger}.zip`, not committed —
throwaway diagnostics) can be deleted once dualbc3 lands. No code
changes this cycle (pure diagnostic reruns of existing `distill_gru`
flags); no bank/snapshot owed.

Update, 2026-08-30 ~09:1x (**`anchor14coef1-canary-s1` VERDICTED CANARY
FAIL - MECHANISM — but the real finding is upstream: the Stage-2
`dualbc2_allheadwalk` BASE checkpoint itself never demonstrated real
forward walking before being used to fund 2 GPU RL canaries.**) Plain
English: while the prior 08:5x entry (below, a concurrent cycle's own
read) was still waiting on the long video-bearing harness passes, ran
a cheap parallel **fast (`--no-video`) det-mode harness pass** for
`-s1` on a spare pod (train-2) instead of waiting ~1-2h: det walk
`progress_ratio` median **-0.05 (NEGATIVE — net motion runs backward
relative to command)**, `slip_per_m` 34.9-55.9, `direction_err_mean_deg`
128.8-132.9 (near-exact OPPOSITE of the single commanded heading),
`gait_valid` True / `sacrificed_legs=[]` on all 6 — a real pathology,
but NOT the literal old anchor4 leg-freeze signature the gate names,
so it needed a second look before the verdict wrote itself. **Root
cause, confirmed by directly probing the BASE checkpoint
(`ppo_goal_cw_standwalk_stage2_dualbc2_allheadwalk.zip`, this run's
`--init-from`, BEFORE any RL) the same way**: det walk `progress_ratio`
~0.000, `forward_dist_m` 0.018-0.026m over a full 30s episode (in-place
quiver, not walking), `slip/m` 27-38, `direction_err` 27-47deg det /
~90deg sto. **The walk clone never walked forward, full stop** — the
distillation's own `quick_probe` smoke test only ever checked episode
RETURN (`probe walk: ep returns ['260','-1111']`, logged
07:0x/`logs/distill_gru/dualbc2_allheadwalk.log`), which looked
unremarkable enough that nobody caught this before funding
`anchor14coef1-canary{,-s1}` on top of it. 2M of RL under the
anchor14coef1 walk-retain recipe made the pathology WORSE, not better
— near-zero/incoherent direction became a confident ~130deg-off-command
walk (more distance covered, the wrong way, slip up) — which is the
gate's own explicit disjunct ("probe pathologies worsen under RL"),
independent of the literal gait_valid/sacrificed-legs clause. WIRING
CHECK stays clean throughout (`train/bc_anchor_loss_walk` falls to a
0.004 plateau, `fill_walk` nonzero every rollout) — this is a
**distillation-quality defect, not an anchor14coef1 dose/mechanism
finding**; the anchor mechanism itself is not implicated.
**CONSEQUENCE for the lineage**: do not fund further RL fine-tunes on
`ppo_goal_cw_standwalk_stage2_dualbc2_allheadwalk.zip` as-is — its
seed0 twin (`cw-standwalk-stage2-dualbc2-allheadwalk-anchor14coef1-
canary`, the concurrent cycle's own run, verdict pending below) almost
certainly shares this same broken base and should be read with this
context, not as an independent anchor14coef1-dose data point. The real
fix is upstream in the Stage-2 distillation recipe (mix/epochs/teacher
quality) — most likely candidate given the composed-sequence residual
already on record (07:0x entry): whatever produced the flat-rise
composed-sequence failures may share a cause with a walk clone that
also never left the spot; worth checking together, not as two
unrelated bugs. **TOOLING FIX landed this cycle** (closes the gap that
let this ship unnoticed, default-off/no behavior change for existing
callers): `distill_gru.py quick_probe` now also tracks net planar
body displacement for `walk`-mode probe episodes and prints a
`WARNING` when it stays under 0.05m over a full episode — the exact
signature this checkpoint would have tripped before ever reaching an
RL launch. 2 new tests (`test_distill_transitions.py`:
`test_com_xy_helper`, `test_quick_probe_flags_near_zero_walk_
displacement`, `test_quick_probe_non_walk_mode_has_no_displacement_
field`), full module green (11/11), snapshot
`exp/quick-probe-net-displacement-check`. **Next**: (1) re-run the
Stage-2 distillation with a mix/epoch change once diagnosed (or swap
walk-teacher/mode-collection strategy) and confirm via the new
`net_disp_m` check BEFORE funding any RL canary on the new zip; (2)
whoever reads the seed0 twin's own harness numbers should cross-check
against this same base-checkpoint defect rather than treating its
result as clean anchor-dose evidence. Evidence: `logs/ckpt_eval/
cw_standwalk_stage2_dualbc2_allheadwalk_anchor14coef1_canary_s1_
gate_fast/report.json` (this run's fast probe) and
`logs/ckpt_eval/cw_standwalk_stage2_dualbc2_allheadwalk_baseprobe_
gate_fast/report.json` (the base-checkpoint root-cause probe); full
video-bearing gate/owncfg/mixedsession passes for `-s1` are still
computing on train-1 (pollreap running detached,
`/tmp/pollreap_anchor14coef1_canary_s1.log`) — informational only,
the fast numeric read + base-checkpoint diagnostic already decide
the verdict per the 08-21/dig-in discipline (root-cause chain over
another scalar wait). Checked the rest of the fleet: walkcurr stays
`[operator]`-blocked pending the in-flight SAC tilt5 x4 read (not
mine this cycle), joystick/amp/cpg stay DONE-or-maintenance-only,
backlog empty — no other standwalk arm is fundable before the
distillation defect above is diagnosed/fixed. 8 GPU pods stayed free
(one genuine finding this cycle, not filler). CYCLE_WORKED.

Update, 2026-08-30 ~08:5x (**anchor14coef1-canary{,-s1} triage: WIRING
CHECK PASS + reward shape matches the old-teacher precedent almost
exactly, but the harness gate/owncfg/mixedsession evals are still
genuinely mid-run on-pod — no verdict yet, same class of wait the
08-27 anchor14-rescue{,-s1} pair went through.**) Plain English: both
canary seeds finished training (2.03M steps each, W&B state=finished).
`train/bc_anchor_loss_walk` (0.002-0.006) and `train/bc_anchor_fill_
walk` (12k->40k, monotonic) are nonzero on every logged update for
BOTH seeds — the pre-registered WIRING CHECK clause of the gate PASSES
directly from cached W&B history, no harness needed for that part.
Reward-quarter trajectory: canary `[38.2, 2.9, -313.9, -101.0]`,
`-s1` `[40.0, -2.5, -268.2, -154.7]` — superficially alarming (big mid-
run dive) but this is the SAME shape the OLD-teacher anchor14-
walkretaincoef1-rescue pair showed at 2M (`[38.6, 16.0, -108.7,
-30.9]` / `[40.0, -6.3, -70.8, -66.6]`), which went on to a funded 8M
acquisition — reading this as a red flag would contradict the track's
own precedent; it looks like recipe-normal anchor-coefficient dynamics,
not a new pathology. **What's actually blocking a verdict:** the
on-pod `_gate`/`_owncfg`/`_mixedsession` eval_checkpoint/eval_mixed_
session passes (the ones that produce `gait_valid`/`progress_ratio`,
the gate's real PASS/FAIL clauses) started at 08:11 and were still
progressing at ~08:50 (confirmed live via `ps`+growing per-episode
video timestamps on hexapod-mjx-train-0, not stalled — 3 parallel
eval_checkpoint processes each pegged near 800% CPU, currently mid
`lower_det`, 3/4 modes through the det pass alone). This exact
recipe/harness combo historically takes ~1.5-2h wall time (matches
the 08-27 anchor14-rescue prestage timeout precedent) — expect this
to finish and sync well after this cycle ends; the finish-triage
belongs to whichever cycle sees the SYNCED marker. Separately: the
`_session` (single-mode partner-handoff) pass crashed immediately
with `walk policy obs (80,) != env (72,)` on BOTH seeds — this is
`pod_eval.py`'s own DOCUMENTED expected behavior for a joint dual-
mode policy (`session_side`'s docstring: "a joint-mode dual-core
policy is EXPECTED to fail eval_session's single-mode partner-based
composition"), informational-only, not a new incompatibility to
chase. **Refill check (same as the 08:32 cycle, re-confirmed):** 8
GPU pods free, backlog empty, but zero legal arms exist anywhere —
joystick/amp/cpg are DONE-or-operator-maintenance-only; walkcurr's
sole in-flight lever (SAC tilt5 x4) is training and no further
rung-1 arm may launch until the operator answers the BC-kickstart
question (08-25 ruling); standwalk's only queued Next item (the 8M
acquisition continuation) is explicitly gated on THIS canary pair's
verdict. Nothing runnable this cycle; next actionable step is reading
the completed harness eval once SYNCED.

Update, 2026-08-30 ~07:0x (**Real-scale Stage-2 BC distillation LAUNCHED
with the new mesh/100Hz all-heading walk teacher — the concrete
next-cycle item the 06:3x entry flagged; found + fixed one real
--transitions incompatibility on the way in, not a rushed retry.**)
Plain English: acting on this file's own "next-cycle item" (real-scale
Stage-2 distillation using `cw-walk-allheading-mlp-singleframe-acq1-
stdanneal` in place of `stotight45-seed13`), built the merged env cfg
programmatically from both teachers' own ledger `extra_args` (walk 48
keys + stance 34 keys, exactly 2 overlaps — `control.hz`,
`train.bc_anchor_coef` — both identical values, matching the smoke
test's own count) and launched the real-scale `distill_gru.py --dual`
collection (background CPU nohup, same class as every prior
`distill_gru` arm, not GPU/ledger-tracked): `--stance-teacher
ppo_goal_cw_standwalk_stance_mesh2_stancemix_bcchain3_stdanneal.zip`
(same stance teacher the 06:3x smoke test used), `--mix walk=0.30,
rise=0.40,lower=0.15,hold=0.15 --episodes 100 --epochs 25` (the
established real-scale recipe from the original dualbc1 build).
**FIRST ATTEMPT included `--transitions 20` (matching the original
recipe) and ABORTED immediately, informatively**: `distill_gru.py`'s
own `--seq-verify` safety check found 10/12 deterministic composed
sequences falling (9 rise, 1 hold) and refused to collect
("TEACHER NOT SEQUENCE-COMPETENT... fix the teacher/context, do not
collect more demos"). **This means the 06:3x smoke test's "zero
crashes" read was a false reassurance for the SEQUENCE path
specifically**: that smoke run used `--transitions 4`, too few draws
for the 12-sample verify window to ever engage the same statistic —
it validated obs-width/pipeline plumbing, not sequence competence.
Root cause matches an already-open track finding, not a new bug: the
`stancemix_bcchain3_stdanneal` stance teacher still carries the
tracked flat-start-rise-in-composition residual (segfix/tuckclock
dig-in lineage) — composed mode_seq segments (6-8s) sometimes cut
off its ~7s rise ramp, exactly the failure this checkpoint is already
known for outside distillation too. **Fix applied (one lever,
directly following the tool's own advice): dropped `--transitions`
entirely** — plain multi-mode (non-composed) BC collection, which
does not exercise the fragile composed-sequence timing edge case
(isolated rise episodes get the full stance episode length, not a
truncated segment draw). Relaunched, now running past the point of
the original abort with no error. **Composed-sequence competence
(`--transitions`) stays a named gap for whichever mechanism finally
solves flat-rise-in-composition** — not silently dropped, tracked
here. Log: `logs/distill_gru/dualbc2_allheadwalk.log` (controller,
pid visible via `ps`); output `rl_move/sim/policies/
ppo_goal_cw_standwalk_stage2_dualbc2_allheadwalk.zip` when it
finishes (likely runs well past this cycle's own end — no ledger
entry to poll; a future cycle's triage should check the log/output
file directly, same convention as every prior `distill_gru` build).
**Next** once it lands: smoke-probe the saved zip (`quick_probe`/
`probe_seq`, matching the anchor1 precedent) before funding any GPU
RL fine-tune, then design the Phase-2 acquisition launch reading the
anchor2-14 lessons (in-loss `train.bc_anchor_walk`/`_phase_lock`/
`_knee_abs`, `--log-std-anneal-core stance`, coef=1.0 per-mode-
decoupled walk-anchor — the anchor14 recipe already proved this dose
compounds cleanly with budget on the OLD teacher; same recipe is the
right first thing to try on the new one, not a fresh lever search).

Update, 2026-08-30 ~06:3x (**`cw-walk-allheading-mlp-singleframe-acq1-stdanneal`
VERDICTED PASS — 3rd confirmed instance of the std-anneal repair,
matching both prior siblings; walk-alone skill confirmed, distill-
compatibility is the next open question.**) Plain English: the
`--log-std-final -3.0` repair (see the 05:1x entry below) worked
again, cleanly. Fresh DR-0 gate: det walk prog_med 0.429/slip_med
2.429, walk_startjitter prog_med 0.433/slip_med 2.453 (both clear
prog>=0.35/slip<=3.0, gait_valid 6/6, zero terms); sto walk prog_med
0.363/slip_med 2.182, walk_startjitter prog_med 0.365/slip_med 2.498
(clear prog>=0.15/slip<=6.0 with real margin — sto slip is actually
BETTER than det in 3/4 sub-panels); zero sacrificed legs, per-leg
duty_cycle balanced 0.45-0.70 on all six legs every episode;
`policy_std=0.05` confirms the anneal landed at target. Video (contact
sheet + walk_det_0.mp4 frame strip) confirms real six-leg cycling,
level body (roll_peak 1.0-2.9deg), no dragging/skating. `eval_cmd_suite`
balanced 8-heading panel: zero falls in all 16 rows, completion
0.27-0.34 on every heading (isotropic, clears the track's 0.19 cheap-
gate bar by >=1.4x). SKILLS.md row added.
**Code landed this cycle (both tested + snapshotted, default-off/
bit-exact where applicable):** (1) `launch_run.py` now defaults
`--log-std-final -3.0 --log-std-anneal-frac 1.0` onto new
acquisition-phase PPO launches that don't set it explicitly (narrow:
skips `--algo sac`, `--gru-dual`/`--gru-experts`, any explicit
`--log-std-final`/`--log-std-anneal-core`; escape hatch
`--allow-no-log-std-final`) — this is the 3rd independent from-scratch
rediscovery of the exact same bug (mlp-acq1-rr1, tf-acq1, this run),
so a 4th recipe family should no longer be able to hit it by omission;
9 new tests (`test_launch_run_log_std_final.py`). (2) `eval_cmd_suite.py`
reimplemented its own float-or-string-only `--cfg-set` parser instead
of sharing `train_ppo_sim._parse_cfg_set`, silently keeping a `[..]`
JSON-list value (`goal.walk_heading_set`) as a literal bracketed
STRING and crashing `float('[0')` deep in `walk_task.py` — the exact
bug class `eval_checkpoint.py`'s own docstring already named and
fixed once (08-10, cw-stand-b2p1); now shares the parser, 4 new tests
(`test_eval_cmd_suite_cfg_parse.py`). Tags `exp/log-std-final-default-
injection`, `exp/eval-cmd-suite-cfg-set-bracket-fix`.
**Full chain now closed out THIS cycle, all three follow-up reads
PASS:** (a) held-out 60s `eval_joystick_gate` stress_mix (train-0,
n=24, seed_base=90000): **PASS on every axis, including the stricter
default TICK metric** — zero_falls, slip_ok (slip/m med 2.222, cap
2.9), dir_ok (dir_err med **39.94deg**, allow 40.0 — a genuine but
thin margin; the windowed course metric is comfortably clean too,
`course_err_1s_med=5.52deg` vs the 12deg allow), gait_valid_frac 1.0,
zero sacrificed legs. This is a STRONGER result than both stdanneal
siblings (`mlp-acq1-rr1`/`tf-acq1`, both FAILed dir_ok at 51.9/45.5deg
tick) — the first all-heading walker on this track to clear the
formal stress_mix gate outright, not just on the windowed-metric
reread. `logs/ckpt_eval/cw_walk_allheading_mlp_singleframe_acq1_
stdanneal_joygate/gate_verdict.json`. (b) `distill_gru.py --dual`
zero-code-change smoke test (this is the actual point of the whole
"singleframe" lineage — sidestep path (b) from the 03:1x mode_onehot-
stacking-bug entry below by using a walk teacher with plain
`obs.history_frames=1`, avoiding the tool's per-tick-vs-post-stack
mismatch entirely): ran `--dual --walk-teacher
ppo_goal_cw_walk_allheading_mlp_singleframe_acq1_stdanneal.zip
--stance-teacher ppo_goal_cw_standwalk_stance_mesh2_stancemix_
bcchain3_stdanneal.zip --episodes 8 --epochs 2 --transitions 4`
(smoke scale, matching the earlier probe's own scale) with the full
merged cfg-set union (48 walk keys + 34 stance keys, only 2
overlapping keys and both identical values — `control.hz=100`,
`train.bc_anchor_coef=3.0` — no collision). **Completed the ENTIRE
pipeline with ZERO code changes and zero crashes**: `walk obs 74,
stance obs 68` (no width mismatch — confirms the fix-free path (b)
works), collected transitions + per-mode demos + 2 BC epochs +
walk/rise/hold probes + 2 composed sequence probes, saved a loadable
student zip. The smoke checkpoint itself is expectedly poor (2
epochs, actor RMS 0.35 ~30deg, one seq probe fell) — this run answers
COMPATIBILITY, not quality, and was deleted after confirming it
loaded (throwaway, not a champion).
**CONSEQUENCE — this is the biggest capability finding of the
cycle:** the standwalk track now has, for the first time, a
mesh/100 Hz all-heading walk teacher that (1) clears its own DR-0
gate, (2) clears the balanced 8-heading `eval_cmd_suite` panel, (3)
clears the held-out 60s stress_mix `eval_joystick_gate` DONE-gate
outright, and (4) is confirmed plug-compatible with the existing
`distill_gru.py --dual` tool with ZERO code changes. Every prior
Stage-2 `stance-mesh2-stage2-dualbc1`/`anchor2..14` iteration used
`stotight45-seed13` — a PRIMITIVE-family, 25 Hz scripted-teacher BC
clone — as its walk-teacher; this checkpoint is the first genuinely
learned, mesh/100 Hz, joygate-passing candidate to replace it.
**NOT launched this cycle (properly scoped, not rushed onto this
one's tail — same discipline this file already applies to the
graduated-step-shaping walkcurr candidate and the per-mode-objective-
normalization fork):** a REAL-scale Stage-2 distillation run with
this walk teacher needs its own hypothesis/gate registration and a
deliberate read of the anchor2-14 lessons already banked here (walk-
retention needs an in-loss BC-anchor term per the operator's
"evals become audit only" ruling — `train.bc_anchor_walk`/
`_phase_lock`/`_knee_abs` on the STUDENT side, not just present in
this teacher's own training recipe; per-core log-std annealing via
`--log-std-anneal-core` to avoid the anchor4/6b shared-log_std walk
tax; mix ratio and stance-teacher choice, e.g. `stancemix_bcchain3_
stdanneal` for full hold+rise+lower coverage vs the cleaner isolated
`holdminload40`/`loweronly` champions) before committing real
episodes/epochs budget. Flagging this as the concrete next-cycle
item rather than a bare placeholder.

Previous entry, 2026-08-30 ~05:1x (**`cw-walk-allheading-mlp-singleframe-acq1`
verdicted PARTIAL — 3rd confirmed instance of the already-fixed
cross-architecture std-runaway bug; repair launched, not a new
finding.**) Plain English: the single-frame distill-compatibility
probe's 40M acquisition run DID learn a real, clean det-mode
all-heading walk (DR-0 gate: walk/det prog med 0.47, slip med 2.03,
walk_startjitter/det prog med 0.45, slip med 2.30 — both inside the
joystick teacher band, gait_valid 6/6 both, zero terminations,
video-confirmed six-leg cycling, forward_dist med ~0.5m/20s) — but
`train/std` climbed UNBOUNDED the entire run (0.397->5.052, no
`--log-std-final` anywhere in the launch args), the exact same bug
already documented+fixed twice for the sibling hist64 mlp/tf
all-heading acq1 checkpoints (08-29 entries below). Consequence:
`rollout/ep_rew_mean` peaks +405 near 10M then crashes monotonically
to -836..-1112 by 40M (excess_sway/park_duty/action_delta charges
compounding on top of increasingly-noisy stochastic actions), and the
sto-mode DR-0 gate collapses (walk/sto prog med 0.01, slip med 16.73,
gait_valid 5/6, 1 sacrificed leg, 2/6 over_current terms;
walk_startjitter/sto prog med -0.01, slip med 16.85, gait_valid 4/6, 2
terms). The periodic deterministic eval logged during training
(`eval/walk/*`) stayed flat 37-46deg dir_err / 0.036-0.044 m/s from 6M
through 40M — the det policy plateaued early; the back half of the
40M budget was spent feeding the runaway, not learning. Per the 08-21
ruling this is misaligned/undertrained-by-omission, not a clean FAIL:
launched the proven fix immediately, same lever as the twins
(`cw-walk-allheading-mlp-singleframe-acq1-stdanneal`, respec
`--init-from-source`, +15M, `--log-std-final -3.0
--log-std-anneal-frac 1.0`, nothing else changed), VERIFIED RUNNING
hexapod-mjx-train-0. **Any future long-budget all-heading (or other
PPO) acquisition launch on this recipe family should set
`--log-std-final` from the start** — this is now the 3rd from-scratch
rediscovery of the same collapse; CURRENT_TRUTHS/launch defaults
should stop letting new acquisition-phase launches omit it. Gate for
the continuation: fresh DR-0 (sto recovers to prog med >=0.15, slip
med <=6.0, gait_valid>=5/6, no new sacrificed leg, without eroding
det) AND `train/std` actually lands near -3.0; if PASS, run
`eval_cmd_suite` balanced 8-heading then the formal 60s
`eval_joystick_gate` stress_mix, then retry `distill_gru.py --dual`
(single-frame both sides, zero code changes) as the smoke test this
whole probe exists to run. Evidence:
`logs/ckpt_eval/cw_walk_allheading_mlp_singleframe_acq1_gate/`,
`logs/experiments/cw-walk-allheading-mlp-singleframe-acq1/
wandb_history.csv`. Checked the rest of the fleet before exiting: 3-4
walkcurr overnight-wave pods freed mid-cycle (some arms finished) but
those runs are a concurrent cycle's own read (off-limits per this
cycle's containment); backlog is empty and no other standwalk/
walkcurr/joystick/amp/cpg item is pre-registered-and-ready without
either that read landing or a from-scratch mechanism build the
walkcurr STATUS explicitly defers until its full wave reads in — no
filler launched.

Update, 2026-08-30 ~04:5x (**`cw-standwalk-unified1-joyfix-courseincome1`
DIG-IN RESOLVED -> CANARY PASS, PASS-no-delta branch; income/sway
lever CLOSED; reward-shaping on unified1-mix is now EXHAUSTED.**)
Plain English: the ambiguous sub-mode signal the 04:3x triage flagged
is an artifact, not partial command tracking. The walk/det-only
43.2deg median comes with a wholesale gait-regime switch — per-leg
duty_cycle 0.79–0.85 vs the parent w015-c1's ~0.55–0.61 — and slip/m
med 6.29 = 2x parent's 3.29 (over the gate's own 1.5x cap of 4.8);
the SAME checkpoint under start jitter reverts to normal duty
(~0.53–0.62) and flat dir_err 68.3deg. I.e., from the fixed start the
policy buys measured direction error with a planted-feet dragging
shuffle — the excess-sway term's perverse optimum (minimize path
deviation by not really stepping) — and it does not transfer.
Video (train-11 full gate pass, walk_det_0 pulled to controller)
confirms a low-stance near-in-place shuffle. Income telemetry fires
but pays ~0.075/tick (angle_f 0.78, support 0.31, speed_f 0.13 —
speed-completion is the binding factor). FAIL branch ruled out
(quarters track w015-c1's own shape, Q3/Q4 less negative; 0/24 walk
terminations). CONSEQUENCE (pre-registered): 4th and final
reward-shaping lever on unified1-mix reads flat (disp windows
1.5s/0.35s/0.15s + income/sway) — no more reward-shaping arms on this
lineage; course tracking needs the structural fix: stage-2
composition/distillation with a GENUINELY BETTER WALK SOURCE. That
source does not exist yet — it is precisely what the running walkcurr
overnight wave (6x100M PPO decleg/central-sv + 4x20M SAC tilt5) and
the joystick track are hunting; the stage-2 arm should be specced
against whichever candidate first clears its own walk gate.
SEMANTICS-BANK obligation before any sway-term reuse: add a bank case
asserting clean stepping outranks planted dragging (the observed
duty-0.8/slip-2x exploit) — k_walk_excess_sway is not re-armable
until that case PASSES. The full video gate/owncfg passes were still
running detached on train-11 at verdict time (informational only; the
numeric fast pass + pulled video already decided the branch).

Update, 2026-08-30 ~04:3x (**`cw-standwalk-unified1-joyfix-courseincome1`
triaged — MIXED/AMBIGUOUS read, does NOT clean-verdict against its own
pre-registered branches; DIG-IN flagged, left UNVERDICTED.**) Plain
English: this run (a concurrent cycle's own launch, finished mid-cycle
per the containment rule) had no prestaged gate/owncfg — the watcher's
prestage only did wandbdump+pullckpt for this one, no `ckpt_eval`
artifacts existed. Ran the gate eval myself: pushed the checkpoint +
synced code to a free pod (train-5), then train-5 got claimed mid-eval
by the self-repairing launcher's own decleg-sv-s3-b100m relaunch (not
mine, left untouched) — killed my own video-bearing gate/owncfg passes
to avoid contending CPU with that training run and kept only a fast
`--no-video` numeric pass alive (same n=6 det+sto per walk-family mode
the coursedisp trio used). Result does NOT cleanly match either
pre-registered branch: **PASS-with-delta is ruled OUT on slip alone**
(det slip/m pooled walk+startjitter median 6.29, vs the gate's own
cap of 1.5x long-s0's ~3.2 = 4.8 — genuinely over, not noise) even
though `direction_err_mean_deg` shows a real, uneven partial move:
walk/det median 43.2deg (a genuine ~15-20deg drop off the 55-65deg
band, on its own clearing the "med<=40-50" bar) but
walk_startjitter/det median 68.3deg (flat-to-slightly-worse, no
improvement) — pooled (the gate's literal instruction) medians 52.05,
short of the pooled <=40-50 bar by a couple of degrees. Reward does
NOT collapse vs its own parent (`w015-c1`)'s quarters trend — recomputed
both from `wandb_history.csv` `rollout/ep_rew_mean`: w015-c1's own
quarters [36.0,-15.1,-468.0,-134.3] vs courseincome1's [36.5,-15.3,
-347.6,-86.6] — Q3/Q4 are LESS negative (better), ruling out the FAIL
branch (reward collapse). Zero terminations in this DR-0 panel (0/24
across all 4 walk-family sub-panels), so no termination-spike FAIL
signature either. Net: the walk-only sub-mode's dir_err improvement
is real and non-trivial (not matched by any of the 3 disp-window
canaries, all of which read flat with NO daylight from the 55-65 band)
but (a) doesn't survive pooling with startjitter, (b) comes with worse
slip than the parent band, and (c) the PASS-no-delta branch's own
"do not fund a 3rd reward-shaping lever" advice would be premature to
apply given the partial signal — this is exactly the "decides a fork"
trigger (escalate income/sway to acquisition+seed-replicate vs close
as no-delta), not a call to force through triage. Report at
`logs/ckpt_eval/cw_standwalk_unified1_joyfix_courseincome1_gate_fast/
report.json` (fast, no video). Also launched the FULL official
video-bearing gate+owncfg pair (same command, `--video-every 1`,
n=6 det+sto x4 modes x2 dr-scales) detached on the one genuinely free
pod (train-11, checkpoint+code pushed/synced) for whoever picks up the
dig-in — check `/tmp/eval_ci1_gate.log` / `/tmp/eval_ci1_owncfg.log`
on train-11 for completion (these passes run 1.5-2h+ per this
lineage's own precedent) before spending more compute re-deriving
numbers already in flight. **DIG-IN: cw-standwalk-unified1-joyfix-
courseincome1 — mixed pooled-vs-submode dir_err signal (43.2 vs
68.3deg) plus worse-than-parent slip decides whether income/sway
escalates to acquisition or closes no-delta; needs the video strip +
per-leg gait read, not another scalar pass.**

Separately, launched the operator-authorized overnight SAC
population-sweep tail: `cw-walkcurr-sac-sv-tilt5-s1-b20m` (train-7,
same seed/diet as `tilt5-s1`, budget 2M->20M, SAC refuses
`--init-from` so this is the same fixed-seed-replay continuation
workaround as `sac-sv-s1-budget10m`) and `-tilt5-s3` (train-9, fresh
seed 3, same dose/budget) — the wave's other two arms
(`-tilt5-s2`/`-tilt5-s4`) were already claimed by concurrent cycles by
the time I went to launch them (found via `REFUSED: ... already runs`).
All 10 arms of the operator's named 08-30 overnight wave (6x100M PPO
decleg-sv-{s2..s6}/central-sv-s0 + 4x20M SAC tilt5-{s1-b20m,s2,s3,s4})
are now RUNNING-verified on distinct pods (`capacity.py`). Per the
guardrails file's own restore condition, RESTORED `max_steps_per_run`
100M->40M this cycle (all 10 arms launched) and pushed the change
(`snapshot.sh restore-cap-post-overnight-wave`, tag
`exp/restore-cap-post-overnight-wave`).

Update, 2026-08-30 ~03:4x (**`cw-walk-allheading-mlp-singleframe-canary`
CANARY PASS — matches the hist64 mlp/tf scratch1 canaries' own
mechanism-health signature; promoted to a 40M acquisition.**) Plain
English: triaged the distill-compatibility probe from the prior
cycle's entry (single-frame retrain of the all-heading recipe, testing
whether dropping `obs.history_frames=64` sidesteps the `--dual`
stacking bug cheaply). All 4 pre-registered criteria clear, each one a
close match to the precedent canaries' own recorded shape, not just a
loose pass: (1) no NaN/blowup, `train/std` rises mildly (healthy, no
collapse), `terminations/over_current` shows one transient bump
(1.33M-1.72M, peak 42) fully resolving to single digits by 1.8M — same
shape as the precedent's shared 86-108-peak bump, not a divergent
explosion; (2) `train/bc_anchor_loss_walk` bumps during anchor warmup
then falls steadily to a 0.006 plateau; (3) course-income
(`reward_walk_course_income`/`walk_course_income_support`) nonzero on
29/31 logged ticks, dips through the mid-run 100Hz valley then ticks
back UP in the final ~250k steps (support 0.0->0.35) — textbook match
to the precedent's own "dips then recovers in the final ~100k steps"
language; (4) reward quarters [69.8, 151.9, 166.0, 113.2] sit inside/
near the twins' 73-172 band (Q4 softer than the twins' 162-172 but
still a rising trajectory overall, no divergence-down signature).
Auto-caption on the final training video reads "walk:ok raise:ok
hold:ok" (no formal DR-0/joygate needed at canary phase, non-blocking,
same convention as the precedent pair). **Promoted per the gate's own
text: launched `cw-walk-allheading-mlp-singleframe-acq1`** (respec
`--init-from-source`, 40M budget, `--phase acquisition`, VERIFIED
RUNNING train-0, W&B `xkgk2em8`). Cheap first gate: the same
`eval_cmd_suite` balanced 8-heading panel the hist64 twins used; if
that clears, the formal 60s `eval_joystick_gate` stress_mix script; if
THAT also clears, immediately re-attempt the `distill_gru.py --dual`
smoke test with this checkpoint as walk-teacher (should now match
cleanly, single-frame both sides, zero new code) before funding any
acquisition-scale Stage-2 distillation. FAIL on either eval hands the
job back to fix (a) from the 08-30 ~03:1x entry (stacking-aware
`distill_gru.py` `collect()` rewrite). Checked the rest of the fleet
before refilling further: joystick/amp/cpg stay DONE-or-operator-wait
(joystick's 100Hz hardening thread explicitly deferred to this track;
amp M6 is hardware-only; cpg's only open item is a non-blocking A/B
adoption read), and walkcurr's two most-recent arms
(`central-sv-idle2-s0`/`decleg-sv-idle2-s0`) are already
FAIL-verdicted with the track's own STATUS recording itself blocked
pending a genuinely new mechanism — no other track had a justified,
non-filler launch this cycle. 10 GPU pods stayed free (one honest arm
existed; batching would have meant inventing untested siblings).
`cw-standwalk-unified1-joyfix-courseincome1` (a concurrent cycle's
run) finished mid-cycle (W&B synced) — left untouched/unverdicted per
the standing containment rule; it belongs to whichever cycle owns it.

Update, 2026-08-30 ~03:2x (**COURSEDISP TRIO CLOSED, 3/3 CANARY PASS/
no-delta — the sub-stride window lever does not exist; UNBLOCKED and
LAUNCHED the pre-registered course-INCOME arm.**) Plain English: found
`coursedisp-w015-c1`/`-w035-c1` (ledger stale-RUNNING, actually
finished+eval-ready for hours — the two GPU pods sitting idle,
`capacity.py` reads all-12-free, are exactly this) and closed both.
`w015-c1` (window=0.15s): direction_err_mean_deg medians 56.5/64.1deg
(walk/walk_startjitter det, n=12) stay squarely inside long-s0's
55-65deg band — no >=15deg drop, so PASS-with-delta is out. Ran a
fresh `--course-trace` diagnostic on-pod (n=6 det, 35912/36000 ticks)
to settle the open activation question properly: `walk_course_disp_
speed_m_s` fires on **55.4% of COMMANDED walk ticks** (4354/7856) —
clears the gate's own >=50% bar. **This corrects a standing metric
error on record**: earlier n=1 probes (08-29) read 14.3%/17.9% and
were logged as "well under the bar" — they used an ALL-TICK
denominator (this remeasurement's all-tick number is 12.1%, matching
those probes almost exactly), diluted by non-walk-commanded ticks
(park/rise/hold segments the session interleaves); the gate text says
"of commanded walk ticks", and against that correct denominator the
mechanism was firing fine all along. Net read: **CANARY PASS/
no-delta** — mechanism live, dir_err flat. Slip/terms/gait_valid all
in-band (mixedsession terms 3/90, slip pooled 13.15 vs cap; walk/sto
slip 18.31 flat vs long-s0's own ~18.1). `w035-c1` (window=0.35s):
same DR-0 instrument, dir_err medians 57.4/62.7deg — also flat,
gait_valid 6/6, zero terminations in-panel. Its own mixedsession
reopen-check is genuinely unrecoverable (`hexapod-mjx-train-1`'s k8s
`startTime` shows a recreation at 2026-08-29T16:45:30Z, mid-session —
real data loss, not the websocket-drop-survives-remotely pattern this
file documents elsewhere) but the gate's PASS-no-delta branch only
needs "(fires >=50% but dir_err flat)", not the termination count
(that clause is scoped to PASS-with-delta only), and dir_err alone
already rules PASS-with-delta out — closes on the DR-0 evidence
without needing the lost pass. **TRACK SYNTHESIS: all 3 tested
windows (1.5s=c1, 0.35s=w035-c1, 0.15s=w015-c1) read flat** —
shrinking the course-disp integration window is not the fix,
independent of activation rate. Per the pre-registered Next item
(a)->(c) (top of "Now" below), this unblocks the course-INCOME arm:
**launched `cw-standwalk-unified1-joyfix-courseincome1`** (respec
`--init-from-source` off `w015-c1`, single new lever `reward.
k_walk_course_income=2.0` + `reward.k_walk_excess_sway=2.0` added on
top of the already-trained disp-0.15 recipe, bank `test_course_
income_semantics.py` 12/12 green, 2M mechanism-health canary,
VERIFIED RUNNING train-2) — tests the operator's registered windowed
net-command-following INCOME objective (support-gated angle x
speed-completion factor, optimum AT the command) plus a teacher-
enveloped excess-sway charge, the primary moving-command mechanism
this reward-design directive was actually FOR, distinct from the
disp term's raw instantaneous-cosine pricing that 3/3 window doses
just closed. Left the concurrent cycle's own composition-wiring
scoping work (entry below) untouched — different question, same
track, no collision. Evidence: `logs/ckpt_eval/cw_standwalk_
unified1_joyfix_coursedisp_{w015,w035}_c1_{gate,owncfg}/`,
`/tmp/coursetrace_w015_det_final.csv` (course-trace remeasurement,
not synced to W&B — raw diagnostic only).

Update, 2026-08-30 ~03:1x (**Scoped the "needs new dual-core/session-
composition wiring" item from the entry below with a real smoke test
— found and root-caused a SPECIFIC, previously-latent bug: `--dual`
BC distillation is incompatible with a `obs.history_frames>1` teacher
because `obs.mode_onehot` is a PER-TICK field, not a post-stack one.
No training launched — this is a code-scoping finding, not a science
result.**) Plain English: before spending GPU budget on a guess, ran
`distill_gru.py --dual` (the existing acq8m+stotight45 dual-BC tool)
with the walk teacher swapped to the new, much better all-heading
source (`cw-walk-allheading-mlp-stressmix-ft1`, windowed course err
<12deg, clean six-leg gait) at smoke scale (`--transitions 4
--episodes 8 --epochs 2`, merged cfg = the full union of the walk
teacher's own 50 `--cfg-set` flags + the stance teacher's own 41,
zero key collisions). It failed immediately and informatively: `env
obs 5120 != expected 4742 (walk teacher 4736 + 6 one-hot)`.
**Root cause, code-read confirmed:** the walk teacher's own
`obs.history_frames=64` stacks 64 single-tick frames (`sim_env.py`
`_hist_n`, "newest-first"); `--dual` turns on `obs.mode_onehot=1`,
which `walk_task.py` (`_mode_obs`, comment: "+6 obs at the frame
TAIL... recomputed every tick like mode_onehot/wz_ref so it survives
obs-history stacking") appends to EVERY tick's base frame BEFORE
stacking — by design, so the mode signal isn't lost to a stale first
frame. So the composed env's real per-frame width is 74+6=80, stacked
64x = 5120 — exactly the observed number. `distill_gru.py`'s own
width check (and the `collect()` function's core mechanism, `t_obs =
obs[:n_t_obs]`, a flat prefix slice) both assume the onehot is
appended ONCE, after stacking (`n_walk + 6`) — true and harmless for
every teacher pairing tried before this (all single-frame,
`history_frames=1`, where "per-tick" and "once" are the same thing),
but wrong here: a flat prefix slice of an 80-wide-per-frame stacked
vector does not reconstruct a clean 74-wide-per-frame view at all
(it isn't even a per-frame-respecting operation once the frame width
changes) — this is not just an off-by-384 constant, the whole
prefix-slice trick breaks structurally the first time a `--dual`
teacher pairing includes an `obs.history_frames>1` member, which
never happened before this cycle (dual-core distillation predates the
all-heading/hist64 lineage entirely).
**Two concrete fix paths for whichever cycle picks this up (not
attempted this cycle — a rushed fix to core obs-stacking/distillation
code is exactly the kind of change that should be tested carefully,
not squeezed in after this much investigation already):**
(a) make `collect()`'s teacher-obs extraction stacking-aware: reshape
    the composed obs to `(history_frames, per_frame_width)`, slice the
    first `teacher_per_frame_width` columns of every row, reshape back
    to flat — this is the general, reusable fix (works for ANY future
    stacked-teacher pairing, not just this one) but touches the
    hot path of every existing dual-core/experts BC run, so it needs
    the full `test_distill_gru`-class regression bank re-run green
    (byte-identical output for every existing single-frame pairing)
    before it can be trusted on a real collection run.
(b) sidestep it for THIS pairing specifically: distill against a
    walk teacher trained WITHOUT `obs.history_frames` (a single-frame
    all-heading walker) instead of the hist64 twin — cheaper to try
    first (no distill_gru.py changes at all) but empirically unproven:
    the operator specifically ordered hist64/transformer for the
    all-heading line (fb_20260829T144550_c921fa) after single-frame
    obs was the norm for every prior walk-quality lineage on this
    track (stotight45, unified1-mix) — if hist64 was load-bearing for
    the all-heading twin's own course-tracking win (not yet isolated
    as a controlled ablation anywhere in this file), a single-frame
    retrain might not clear the same joygate the twin did, and a
    lesser walk source would just reproduce the unified1-mix
    dir_err-can't-close-the-gate story instead of really fixing it.
Also flagged, orthogonal to the obs bug: even a fixed pairing still
needs the stance TEACHER side re-checked — `standheight-rung5-acq8m`
(chosen for its rise->hold(height-cmd)->lower composition win) reports
its OWN obs at 68 (single-frame, unaffected by this bug), so it is not
implicated, but has not itself been smoke-verified end-to-end past
the walk-side crash this cycle; re-verify once (a) or (b) lands.
Snapshot not needed (no code changed, no checkpoint produced —
`_smoke_dualbc2.zip` deleted, cfg-set union was scratch-only, not
committed). 12 GPU slots stayed free the whole cycle; walkcurr
[operator]-free-but-genuinely-blocked-pending-a-new-mechanism (see its
own STATUS), joystick/amp/cpg DONE-or-maintenance — this smoke test
was the one legitimately fundable next step across all 5 tracks this
cycle, and it is now scoped concretely rather than a bare "needs
wiring" placeholder.

Previous entry, 2026-08-30 ~00:3x (**`cw-walk-allheading-mlp-stressmix-ft1`
VERDICTED PASS too — MATCHED PAIR COMPLETE, both architecture twins
clean.**) Plain English: the mlp twin's own formal 60s joygate (already
finished, W&B `state=finished`, sitting untriaged) reads exactly like
the tf twin: zero falls (24/24), slip_ok (2.394 med, cap 2.9),
gait_valid_all (6/6 legs cycling, duty 0.56-0.61, zero sacrificed) —
the tool's tick-default `dir_ok` reads false (47.73deg vs allow 40)
but re-aggregating the SAME saved report.json (no re-simulation) with
`--dir-err-metric windowed_1s` flips it true: `course_err_1s_med`
3.96deg (allow 12deg) — full PASS. Fresh DR-0 fixed-forward gate (n=24)
also confirms no regression: prog med 0.36-0.41 (matches the
pre-finetune ~0.41 baseline), slip med 2.10-2.71, gait_valid 6/6, zero
terminations, contact sheet clean (upright, level, six legs cycling).
This CLOSES Next item (b) — both twins now agree under the binding
windowed metric, a genuinely matched pair, not a one-off reading.
Evidence: `logs/ckpt_eval/cw_walk_allheading_mlp_stressmix_ft1_
{gate,joygate}/`.
**Next item (a) is now live and unblocked**: mlp+tf
(`cw-walk-allheading-{mlp,tf}-stressmix-ft1`) are the leading candidate
walking SOURCE pair for Stage-2 sit→rise→walk→lower distillation —
composing either/both with the mesh stance champion
(`cw-standwalk-stance-mesh2-*-acq8m`) needs new dual-core/session-
composition wiring (a design task), not funded/started this cycle
(flagging for the next cycle with bandwidth to design it, per the
"do not park on operator input" rule — this is agent design work, not
an operator wait).

Previous entry, 2026-08-29 ~23:5x-00:0x (**`cw-walk-allheading-tf-stressmix-ft1`
VERDICTED PASS — the stress_mix fix genuinely works; the prior "FAILS
direction" read was a metric artifact, and this is now CONFIRMED on
the real formal 60s joygate script, not just a 20s proxy panel.**)
Plain English: this run's own held-out DR-0 stress_mix panel (24 eps,
4 subgroups) showed gait_valid 6/6 everywhere, zero terminations,
slip/m 2.06-2.6 (cap 2.9), and windowed `course_err_1s_med_deg`
1.7-9.5deg — clean by the CURRENT_TRUTHS-binding windowed metric even
though the demoted tick `direction_err_mean_deg` reads WORSE than the
stdanneal parent's own FAIL (53.0/38.6 vs 45.5) — exactly the
stride-oscillation false-fail shape the 08-29 windowed-metric ruling
predicted. **Went further and ran the actual formal 60s randomized
`eval_joystick_gate` script** (n=24, `resample_s=4.0/jitter=0.5` —
MORE adversarial than training's own 6.0s/0.2, launched detached on
the run's own pod as an extra eval): zero_falls, gait_valid_all
(24/24, all six legs cycling ~duty 0.56-0.59, zero sacrificed),
slip_ok (2.351 med) all true; the tool's own tick-default `dir_ok`
reads false (46.3deg vs allow 40) but re-aggregating the SAME real
report against a new `--dir-err-metric windowed_1s` option (built
this cycle, see below) flips it true: course_err med 3.77deg (allow
12deg) — full PASS. Matches the mlp twin's independently-read pattern
(gait_valid 6/6, slip 2.1-2.7, course_err 1.7-9.5deg) — three separate
readings (20s panel, 60s formal script, mlp architecture twin) now
agree. Evidence: `logs/ckpt_eval/cw_walk_allheading_tf_stressmix_ft1_
{gate,joygate}/`.

**Tool fix landed this cycle** (`rl_move/sim/eval_joystick_gate.py`):
`aggregate_gate` gained an opt-in `--dir-err-metric {tick,windowed_1s,
windowed_2s}` (default `tick`, bit-exact prior behavior — no existing
caller's judgment changes) so the formal joygate's own PASS/FAIL can
be read against the CURRENT_TRUTHS-binding windowed course metric
instead of the stale per-tick one its original design predates.
`test_eval_joystick_gate.py` 16/16 green (5 new tests incl. the exact
false-fail-flips-to-pass shape found this cycle, a genuinely-bad-course
still fails, and a pre-08-29 report with no windowed keys fails closed
rather than silently passing). Snapshot pending this cycle's push.

**Next** (not pre-empted this cycle, to avoid duplicating the
concurrent cycle's own mlp-side synthesis): (a) once the mlp twin's
own verdict lands, if both are clean this pair becomes the leading
candidate walking SOURCE for Stage-2 distillation (composing with the
mesh stance champion into one sit→rise→walk→lower policy) — that
needs new dual-core/session-composition wiring, a design task, not a
quick launch; (b) re-read the mlp twin's own formal joygate (if/when
run) with `--dir-err-metric windowed_1s` too, for a fully matched
pair; (c) a true seed replicate of this recipe would require a whole
new from-scratch multi-stage lineage (canary→acquisition→stdanneal→
stressmix, ~70M+ steps) — not funded blind; pre-register explicitly
if the Stage-2 candidacy decision wants it. 10 GPU slots free at this
cycle's end, backlog empty — no new arm uniquely justified beyond
what's already running/decided above without stepping on (a).

Previous entry, 2026-08-29 ~22:2x (**Both stdanneal checkpoints' held-out
60s joygate read: FAIL on direction (as anticipated), zero falls
(better than anticipated) — wz/arc bank case added (closes
q_20260829T16xx's stage gate) and a stress_mix continuation pair
LAUNCHED.**) Plain English: the joygate riders the prior update left
running (`eval_joystick_gate`, stress_mix, n=24, DR-0) had actually
finished on-pod but not synced; pulled directly via `kubectl cp`.
Both checkpoints: **zero falls (0/24 each)**, gait_valid 1.0, no
sacrificed legs — but `direction_err_med` fails the 40 deg allowance
(mlp 51.9 deg, tf 45.5 deg) and mlp's slip/m also just misses (2.992
vs cap 2.9; tf passes slip at 2.799). Root cause: training used
ONLY discrete 8-heading resamples (`goal.walk_cmd_mode` default
"legacy", `walk_heading_set` + `walk_cmd_resample_s=6.0`) — the
eval's own `stress_mix` command families (random_hold/flip_180/
sweep_circle/square/stop_go/jitter) were never part of the training
distribution. This is exactly the scope gap `OPERATOR_QUESTIONS
q_20260829T16xx` flagged in advance ("arcs/sweeps enter at stage (c)
only after a wz case is added to test_course_income_semantics").
Artifacts synced to
`logs/ckpt_eval/cw_walk_allheading_{mlp_acq1_rr1,tf_acq1}_stdanneal_joygate/`.

**Built the wz/arc bank case this cycle** (`rl_move/tests/
test_course_income_semantics.py`, +3 tests, 12/12 green,
`exp/walkcurr-tilt2-fail-standwalk-wz-arc-bank`): measured the
windowed course-income mechanism against a teacher faithfully
tracking a continuously-rotating world-frame command
(`goal.walk_cmd_mode=sweep_circle`; found + documented a real gotcha
— the whole cmd_mode dispatch is dead unless `walk_cmd_resample_s>0`,
so a naive sweep_circle cfg silently never turns). Result: a
moderate turn (period 6 s, ~7.6 cm radius at the 0.08 m/s command)
rides at 0.946x straight-line income with only a small excess-sway
charge (-9.5 vs a clean teacher's ~0) — no reward-formula change
needed to admit arcs. A physically-extreme tight turn (period 3 s,
~3.8 cm radius) is gracefully discounted (0.638x the moderate arc's
income), not exploited or double-charged. **Conclusion: stage (c) is
SAFE to fund on the existing reward stack** — the gap is training
DISTRIBUTION (never saw these command families), not reward
mechanism.

**Launched the fix as a stress_mix continuation pair** (respec
`--init-from-source`, +15M steps each, single lever
`--cfg goal.walk_cmd_mode=stress_mix` added, `--log-std-final -3.0
--log-std-anneal-frac 1.0` carried over from the source to avoid
re-triggering the std runaway): `cw-walk-allheading-mlp-stressmix-ft1`
(VERIFIED RUNNING hexapod-mjx-train-3) and
`cw-walk-allheading-tf-stressmix-ft1` (VERIFIED RUNNING
hexapod-mjx-train-0). Gate (both arms): fresh `eval_joystick_gate`
must show `direction_err_med` improving materially toward/under 40
deg with slip staying near/under 2.9-3.0 and zero-or-near-zero falls
preserved; DR-0 fixed-forward gate and `eval_cmd_suite` must not
regress off the current baseline (prog_ratio med 0.41, gait_valid
6/6, zero terminations). FAIL (dir_err unchanged/worse, or slip/falls
regress with flat reward) forks to a `walk_cmd_stage` curriculum ramp
(the codebase already has this — stage 0 flip_180/stop_go only,
stage 1 adds random_hold/sweep_circle/square, stage 2 adds jitter)
instead of a flat full-family fine-tune, or a from-scratch stress_mix
run if the fine-tune-off-a-heading-only-optimum approach itself is
the problem. **Next cycle: read these two joygates before anything
else on this line.**

Previous entry (2026-08-29 ~21:5x (**BOTH std-anneal repairs PASS outright —
the all-heading walker is now a genuinely clean mesh/100 Hz walk
source, and it clears the track's own long-named "cheap first gate"
too**): `cw-walk-allheading-mlp-acq1-rr1-stdanneal` and
`cw-walk-allheading-tf-acq1-stdanneal` both verdicted **PASS** (full
detail in each run's ledger/W&B OUTCOME note). Fresh DR-0 gate (n=6
each, both twins near-identical): walk/det prog med 0.41 (up from
0.28/0.33, gate wanted "not regressed" >=0.20/0.25), walk/sto prog med
0.36 (up from -0.00, gate wanted >=0.15), slip/m med 2.1-2.6 everywhere
(down from 18-19.6, gate cap 6.0 — **now inside the joystick teacher
band <=2.9**), gait_valid 6/6 in all 4 sub-panels (det/sto x
walk/walk_startjitter) on both checkpoints, ZERO terminations anywhere.
`train/std` fell 2.15/1.92 -> 0.05 exactly on schedule; reward recovered
past its old mid-run peak on both (mlp quarters 8.6/-33.1/477.1/1100.3,
tf 7.4/-160.9/.../1328.8). Video (all sub-panel strips, both
checkpoints) shows upright six-leg cycling, no pathology. 3rd confirmed
instance of the `--log-std-final` fix on this codebase (standwalk
hold/lower champions, joystick stotight ladder) — architecture-
independent, MLP is the practical champion going forward (same skill,
cheaper).

**Went further this cycle and actually measured the balanced-heading
"cheap first gate" the acquisition launch's own text has named since
08-29 ~15:2x but nobody had run yet** (`eval_cmd_suite`, new suite file
`rl_move/sim/cmd_suites/allheading8_v08.json` — the exact 8 headings
[0,±45,±90,±135,180]deg @ 0.08 m/s the training diet uses, generated
via vx=s·cos h / vy=s·sin h same as `probe_teacher_headings`), det+sto,
3 episodes/heading/pass, both checkpoints: **CLEARS the gate outright
on EVERY heading** — zero falls in all 32 rows (8 headings x det/sto x
2 checkpoints), completion (from v_err_med) 0.37-0.44 on every heading
for both checkpoints (gate wanted >=half the teacher's 0.373-0.385,
i.e. >=~0.19 — we're at 2x that bar, not just clearing it), slip/m
1.75-2.35 (inside the joystick teacher band). Isotropic: no
forward-bias, no weak axis. Artifacts:
`logs/ckpt_eval/cw_walk_allheading_{mlp_acq1_rr1,tf_acq1}_stdanneal_cmdsuite8.json`.

**Also launched the track's own actual walk-segment DONE-gate
instrument** (`eval_joystick_gate` — Stage 2's DONE GATE text literally
names this tool as the walk-segment evaluator) on both checkpoints, to
see whether translation-only balanced-heading training generalizes to
the REAL held-out stress_mix script (random_hold/flip_180/
sweep_circle,square/stop_go/jitter — includes turns this diet never
trained on, same emergent-generalization question the joystick track's
own champion answered YES to on a fixed-forward-only diet). Own-dr=0.0
(DR-0 checkpoint, own-DR pass skipped as redundant per the tool's own
rule), n=12 det+sto, 60s episodes. Running IN-FLIGHT as of this note:
`hexapod-mjx-train-3` (mlp, log `/tmp/eval_mlp_joygate.log`) and
`hexapod-mjx-train-1` (tf, checkpoint pushed + code synced this cycle,
log `/tmp/eval_tf_joygate.log`), both writing to
`logs/ckpt_eval/cw_walk_allheading_{mlp_acq1_rr1,tf_acq1}_stdanneal_joygate/`.
**Next cycle: read `gate_verdict.json` in those two dirs before doing
anything else on this line** — do not relaunch, do not re-derive the
suite, just wait/read. If PASS: this all-heading lineage is a strong
candidate for Stage 2's walking-source role (STATUS Stage 2 text) even
though it has never seen wz/turns in training — pre-register the
adoption fork against the joystick champion per Stage 2's own
never-silent-swap rule. If FAIL (turns are the likely failure axis,
since stress_mix's sweep_circle/square are genuinely off-distribution
for a heading-only diet): that's exactly what stage-a's own recorded
scope note anticipated ("arcs/sweeps enter at stage (c) only after a
wz case is added to test_course_income_semantics",
OPERATOR_QUESTIONS q_20260829T16xx) — the next funded arm is the wz
bank case, not more heading-only budget.

Update, 2026-08-29 ~18:4x (**MLP twin's own triage now recorded —
`cw-walk-allheading-mlp-acq1-rr1` verdicted PARTIAL, matching the tf
twin exactly**): confirms the previous update's "not architecture-
specific" claim was correct rather than a fluke read from a borrowed
comparison. This arm's own DR-0 gate: walk/det prog med 0.28, slip med
3.32, gait_valid 6/6, zero terminations (real clean six-leg gait,
video-checked); walk/sto collapsed (prog med -0.00, slip med 19.55,
gait_valid 4/6, 1 over_current term) from the identical unbounded
`train/std` runaway (0.42->2.57, no anneal). Continuation launched
with the SAME lever as the tf twin: `cw-walk-allheading-mlp-acq1-rr1-
stdanneal` (`--log-std-final -3.0 --log-std-anneal-frac 1.0`,
`--init-from-source` off the finished 40M checkpoint, +15M steps),
VERIFIED RUNNING hexapod-mjx-train-3, alongside `cw-walk-allheading-
tf-acq1-stdanneal` (train-0) — the tf/mlp matched-lever comparison
stays intact through this repair. No other standwalk work is
runnable this cycle; next triage is whichever cycle reads these two
stdanneal continuations out.

Update, 2026-08-29 ~18:2x (**`cw-walk-allheading-tf-acq1` verdict
PARTIAL — real det-mode walking, but an UNBOUNDED std/entropy runaway
(no anneal) crashes reward and torches sto-mode late in every 40M
all-heading acquisition arm; cross-architecture, not tf-specific;
fix is already proven elsewhere in this codebase.**) Plain English:
the 40M all-heading acquisition arm DID learn a real, clean, six-leg
forward gait (DR-0 det gate: progress_ratio med 0.33, gait_valid 6/6,
ZERO terminations, ~25-35% of the 0.08 m/s target speed) — but
`train/std` (policy action std) climbed UNBOUNDED the entire run,
0.40->1.91, with no ceiling and no anneal (`--ent-coef 0.01`, no
`--log-std-final`). That runaway (1) destroys stochastic-mode
rollouts (walk/sto DR-0: progress_ratio med -0.00, slip/m med 18.1,
gait_valid 5/6, 1 over_current termination — the tuned gait cannot
survive its own sampled noise) and (2) crashes `rollout/ep_rew_mean`
in the back half of training (quarters 150.7/139.7/-38.8/-310.1,
peaking mid-run then collapsing). **This is NOT architecture-specific
or a fluke:** the matched MLP twin (`cw-walk-allheading-mlp-acq1-rr1`,
a concurrent cycle's own run, read here for comparison only) shows the
identical shape, even more extreme — std 0.42->2.57, reward peaks
~343 mid-run then crashes to -228/-242. Every 40M-budget all-heading
acquisition arm launched without a std-anneal lever should be expected
to reproduce this. **The fix already exists and is already proven on
this exact codebase**: `--log-std-final` (linear anneal of the
policy's log_std down to a target, holding after) closed the
IDENTICAL sto-mode-collapse-from-runaway-std signature twice before —
the standwalk stance-hold (`bcanchor3_stdanneal`) and stance-lower
(`loweronly_bcchain3_stdanneal`) champions, AND the joystick track's
`phasedir9` stotight ladder (`log-std-final` -3.2->-4.5->-5.0->-5.5,
each rung widening the sto-mode margin with no det trade). Continuing
from a checkpoint mid-runaway is exactly the tool's supported case
(anneal start value = the policy's own current mean log_std, not a
fresh-init value). **Refill this cycle:** `cw-walk-allheading-tf-acq1-
stdanneal` (`respec --from` the finished 40M checkpoint, +15M,
`--log-std-final -3.0 --log-std-anneal-frac 1.0`, nothing else
changed) — tests whether annealing the runaway down while continuing
training both stops the reward crash and closes the sto-mode gap
without eroding the det gait. **Any future all-heading (or other
long-budget PPO) acquisition arm launched on this recipe family should
set `--log-std-final` from the start** rather than rediscover this
same collapse at 40M; the MLP twin's own eventual triage should apply
the same lever if its owning cycle hasn't already.

Update, 2026-08-29 ~16:4x (**`cw-walk-allheading-mlp-acq1` CRASHED —
infra OOM, not a science verdict, retried**): the MLP acquisition twin
died at 17.5M/40M steps when its pod (`hexapod-mjx-train-1`) was
OOMKilled (container mem limit 96Gi, exit 137) — training itself was
unremarkable up to the crash (bc_anchor_loss_walk flat/low, no NaN,
ep_rew_mean noisy-but-not-degenerating, over_current terminations
single-digit after the shared canary-era transient), and the sibling
`cw-walk-allheading-tf-acq1` on the SAME node kept running past 21M
unaffected, so this reads as localized (possibly this 13-day-old
pod's own accumulated state from many prior sequential jobs — these
pods have no PVC and are never restarted between launches), not a
node-wide or recipe-wide memory problem. No checkpoint survived (no
PVC backs these pods; a pod OOM kill leaves nothing kubectl can
exec/cp out of once it's Failed) — the 17.5M steps of acquisition
progress are unrecoverable. Retried as `cw-walk-allheading-mlp-acq1-rr1`
(same hypothesis/gate/40M budget, `--init-from-source` off the last
recoverable checkpoint — the scratch1 canary — since acq1's own
checkpoint never synced), VERIFIED RUNNING on a fresh pod
(`hexapod-mjx-train-3`). Also recreated+rebootstrapped
`hexapod-mjx-train-1` itself (delete/apply/bootstrap; it was
Failed/un-execable and could not host any run) — back in the free
pool. If `-rr1` ALSO OOMs on its fresh pod, treat that as a real
memory-leak defect in this recipe (obs.history_frames=64 / mesh /
100Hz / 3072 envs) worth a root-cause dig-in, not another blind retry.

Update, 2026-08-29 ~15:4x triage (all-heading canary pair VERDICTED PASS,
**40M acquisition pair LAUNCHED**): both `cw-walk-allheading-tf-scratch1`
(transformer) and `cw-walk-allheading-mlp-scratch1` (matched MLP twin)
cleared the 2M mechanism-health canary from the prior cycle's launch.
Evidence (W&B history, both arms): bc_anchor_loss_walk falls
monotonically for both (tf 0.0041->0.00019, mlp 0.0030->0.00047);
course-income mechanism (reward_walk_course_income /
walk_course_income_support) never hits zero on either arm, dips through
the mid-run 100Hz reward valley (08-24 FACT) then ticks back up in the
final ~100k steps of both (tf support 0.22->0.35, mlp 0.30->0.33); no
NaN/entropy collapse (train/std rises on both); terminations/over_current
shows a transient bump ~800k-1.05M steps shared almost step-for-step by
both arms (tf peak 108, mlp peak 86) that fully resolves to single digits
by 1.1M — a shared training-dynamics wobble, not a divergent explosion;
reward trajectories track each other closely at every matched step (tf
quarters 74.4/84.8/127.7/162.3 vs mlp 73.1/87.0/122.4/172.1) — no
divergence-down signature, the only thing that would fail this gate.
Frame strips (walk_det_0-5 on-pod for both) show the robot upright, six
legs planted/spread, no topple. Per the canary's own pre-registered gate
text, launched the 40M acquisition continuations same cycle:
`cw-walk-allheading-tf-acq1` (train-0, VERIFIED RUNNING) and
`cw-walk-allheading-mlp-acq1` (train-1, VERIFIED RUNNING), both
`--init-from-source` off their own canary checkpoint, identical
env/reward/BC-anchor stack, no cfg changes (budget-only continuation).
Cheap first gate for both (unchanged from the canary's own text):
`eval_cmd_suite` balanced 8-heading panel, det+sto, every heading must
move (completion >=0.19, half the teacher's 0.373-0.385), zero falls.
The full n=16 DR-0 gate report (walk det/sto + startjitter sub-checks)
was still finishing on-pod for both scratch1 canaries at verdict time
(non-blocking — canary criteria (1)-(4) are training-curve-based, not
eval-based, per the gate's own text); partial frame strips already
reviewed showed nothing anomalous.

Update, 2026-08-29 ~15:2x operator-kick (executing fb_20260829T144550_c921fa —
**NEW LINE: from-scratch ALL-HEADING walker on the mesh/100 Hz
contract, transformer-preferred, teacher-anchored; canary pair
LAUNCHED**). Operator wants a walker whose FIRST job is balanced
walking in every direction (the unified1-mix champion is forward-
biased: crab-right ~5% commanded speed / ~69 deg dir err on manual
drive). Done this cycle: (1) teacher sanity check (the order's item 2)
PASSED — new probe `probe_teacher_headings.py`, scripted TripodGait on
mesh/100 Hz at all 8 balanced headings: ZERO falls, net course err
<=2.26 deg, completion 0.373-0.385 at EVERY heading (isotropic),
slip/m 1.24-1.36, all six legs cycling (artifact:
logs/probe_teacher_headings_mesh100.json) — the teacher is a valid
all-heading BC anchor source and the champion's forward bias is a
training artifact, not a robot limit. (2) Launched the 2M mechanism
canary pair (phase=canary, DR-0, walk-only `--goal-mix walk=1.0`,
episode 20 s, `goal.walk_heading_set=[0,±45,±90,±135,180 deg]`
balanced draw + 6 s resamples + stop_frac 0.15, fixed 0.08 m/s, the
sibling cycle's bank-proven course-income reward stack VERBATIM
(income 2.0 / sway 2.0 / disp 0.15 / overspeed 4.0 + support gates,
test_course_income_semantics 9/9 green re-verified pre-launch), walk
BC anchor at the proven dose (coef 3.0, walk_coef 1.0, phase_lock,
knee_abs, isolate_update)):
  - `cw-walk-allheading-tf-scratch1` — transformer (2L/128d/8h/ff256,
    64-frame context), the operator-preferred arm;
  - `cw-walk-allheading-mlp-scratch1` — matched-step MLP twin
    (identical everything, default 128,128 MLP on the same 64-frame
    stack): the 08-24 valley FACT requires a matched-step control for
    from-scratch 100 Hz canaries and this reward stack has no prior
    reference trajectory; also the operator's named fallback if the
    transformer shows its collapse signature.
Canary gate is mechanism health ONLY (bc-walk-anchor loss falling,
course-income share nonzero/rising, no NaN/entropy/termination
explosion, reward within band of the twin at matched steps — NEVER
absolute-value judged, 08-24 valley FACT). Healthy canary -> 40M
acquisition whose cheap first gate is the balanced-heading panel
(eval_cmd_suite, 8 headings x 0.08 m/s + stop, det+sto: EVERY heading
must move, completion >= half the teacher's 0.373-0.385, no falls) —
NOT hours of session eval, per the order. Stage-a scope decisions
(wz/arcs deferred until the income bank grows a wz case; D6
regularizer deferred, symmetry pressure via balanced diet +
command-conditioned anchor + per-heading eval; track routing here) in
OPERATOR_QUESTIONS q_20260829T16xx. Next after a healthy canary:
(a) 40M acquisition continuation of the healthy arm(s); (b) graduate
per the order — heading buckets -> joystick changes/holds/stops/
sweeps -> longer mixed sessions; (c) add the wz bank case before any
arc/sweep rung.

Update, 2026-08-29 ~15:3x operator-directed reward/eval design cycle
(**implemented the fb_20260829T142239_63c818 reward directive + the
fb_20260829T141858_9421cd windowed eval metric — no launches, per the
focus note's own "don't fund another arm until the objective is
proven" order; the objective is now built AND bank-proven**):

1. **Eval**: `eval_checkpoint.windowed_course_stats` — rolling 1 s/2 s
   net-course windows vs the INTEGRATED command; new ep keys
   `course_err_{1s,2s}_{mean,med,p90}_deg`, `wrong_course_frac_*`,
   `course_speed_ratio_*_med`, `course_motion_valid_frac_*`, pushed to
   W&B medians + both console summary lines. Tick `direction_err_deg`
   demoted to diagnostic (EVALS.md updated). Unit bank
   `test_windowed_course_metrics.py` 6/6 (incl. park-can't-hide,
   stop-straddle exclusion, reversal grace).
2. **Teacher calibration**: `probe_dir_floor --envelope-windows`
   (mesh/100 Hz/0.08): windowed course err med 1.2–2.2°, p95 ≤5.2°;
   sway RMS p95 ≤1.7 mm; completion ~0.39 (teacher can't reach 0.08
   under the slew contract — killed the raw |disp−cmd| vector-kernel
   design on measurement: it would pay a PARK 0.33 of max).
3. **Reward**: `reward.k_walk_course_income` (windowed net
   command-following INCOME: support-gate product of the run's own
   anchor/loadslip/height/gait gates × teacher-deadbanded angle factor
   (6°/σ20°) × command-completion speed factor with falloff past the
   band — optimum AT the command) and `reward.k_walk_excess_sway`
   (RMS perpendicular path deviation minus 5 mm teacher allowance,
   charged only around a followed course, cap 60°). Both default OFF,
   bit-exact legacy (smoke-verified), state rides MJX_SNAPSHOT_EXTRA.
4. **Bank** `test_course_income_semantics.py` 9/9 green (mesh/100 Hz):
   obey 1869 > fastcadence 1520 > zigzag 1187 (income discounted AND
   −288 sway charge) > stall 693 > sideways 593 > backward 254 > park
   90; teacher angle-factor 1.0 and sway charge exactly 0 (the
   directive's central invariant). One documented ordering deviation
   (stall vs wrong-way; OPERATOR_QUESTIONS q_20260829T15xx). Doses
   that made the chain work: k_walk_course_disp 0.15 (2.0 buries
   wrong-way below park), idle floor 0.02/k=20, park_duty 2.0.
5. q_20260829T0805Z (per-tick gate metric) CLOSED-OVERRIDDEN by the
   operator notes; CURRENT_TRUTHS + REWARD.md + EVALS.md carry the
   ruling.

NEXT (this track, in order): ~~(a) coursedisp trio mixedsession
verdicts land~~ **DONE 08-30 ~03:2x: all 3 CANARY PASS/no-delta, see
banner at top of file — window lever closed, does not reopen.**
(b) calibrate windowed-gate pass thresholds by re-evaluing the
joystick champion (`cw-dep-bcgait4-phasedir9-stotight45-seed13`,
primitive/25 Hz pins) and the unified longrun checkpoints with the
updated harness (pod eval, no training) — champion half LAUNCHED
08-30 ~00:xx (`podeval ... wincal`, check `/tmp/podeval_champion_
wincal.log` / `logs/ckpt_eval/*wincal*` for a landed read); the
unified-longrun half is unblocked now that the coursedisp trio no
longer needs train-1/-2's CPU. ~~(c) pre-register the first
course-INCOME arm~~ **DONE 08-30 ~03:2x: `cw-standwalk-unified1-
joyfix-courseincome1` LAUNCHED (VERIFIED RUNNING train-2, see banner
at top) — read its 2M canary next cycle per its own gate text.**
(d) NEW, opened by this cycle's dual-core/session-composition
scoping (see banner below): pick one of the two fix paths for the
`--dual` distillation obs-stacking bug (general stacking-aware
`collect()` fix vs a single-frame all-heading walk-teacher retrain)
before Stage-2 composition with the new mlp/tf-stressmix-ft1 walk
source can proceed at all.

Prior update, 2026-08-29 ~13:4x idle-kick (real infra fix + partial evidence,
no final verdict — **found the coursedisp-c1/w015-c1 gate+owncfg
report.json pairs FINISHED-BUT-UNCOLLECTED with no local supervisor
watching them (their controller-side driver had died to the same
kubectl-exec websocket drop already tracked elsewhere in this file;
remote processes survived), and fixed the same gap for all 3 open
coursedisp items at once**: launched `ops.sh pollreap` (300s poll,
5h budget, detached+disowned) for `coursedisp-c1`, `-w035-c1`, and
`-w015-c1` — the first invocation of each immediately reaped
gate+owncfg for `-c1` (record-only, already CANARY PASS) and for
`-w015-c1` (NEW), confirmed `-w035-c1`'s gate/owncfg/mixedsession
still genuinely computing (not a duplicate, left alone), and started
all 3 mixedsession passes' own poll cycle so their still-pending
`session_verdict.json` (dr0->owndr->dr0_long, each pass ~2.5-4h per
the established convention) will sync back automatically without
requiring another cycle to notice. **New official evidence,
`w015-c1` (0.15s window) gate+owncfg (n=6 det walk each, dr=0.0/0.5)**:
`direction_err_mean_deg` averages 59.8/59.3 deg — squarely inside
long-s0's ~55-65deg band, confirming (not just an n=1 probe anymore)
that dir_err is FLAT, not the >=15deg drop PASS-with-delta needs;
slip/m 2.47-6.62 (well under 1.5x the 9.17 parent band); gait_valid
6/6, zero new sacrificed legs, zero terminations in this panel. This
is consistent with (and now backed by n=6, not n=1) both prior course-
trace probes (w015 14.3% / w035 17.9% mechanism activation, both well
under the gate's >=50% bar) — trending toward PASS-no-delta on w015
specifically, but the gate's own text requires mixedsession's session
termination count (<=6/90) before any of the three can be closed, and
that has not landed for any of them yet. Left all remote eval
processes untouched (no relaunch, no duplicate — pod_eval.py's own
idempotent reap-vs-relaunch logic confirmed this, matching its
docstring). All 12 GPU training slots free (`capacity.py`), backlog
empty; no other standwalk arm has independent preconditions met.
joystick/amp/cpg STATUS.md byte-unchanged for 4+ days (git log
confirms, DONE-or-maintenance), walkcurr still `[operator]`-blocked
(`q_20260824T0233Z` unanswered). CYCLE_WORKED (real orphan-reap +
pollreap-loop infra fix + new n=6 evidence, not a re-verify no-op).

Prior update, 2026-08-29 ~10:3x idle-kick (housekeeping + contention audit,
no verdict — **committed+pushed the prior cycle's 5-file uncommitted
diff (hdgset1/long-s0-cont1 FAIL verdicts) that had accumulated in the
working tree** (44c8e116). Investigated train-1 CPU contention between
coursedisp-c1's own still-open `mixedsession` `owndr` pass and
w035-c1's gate/owncfg: confirmed this is NOT an orphan to kill —
coursedisp-c1's own recorded verdict text explicitly flags "the
mixedsession termination count (<=6/90) was still computing at
verdict time... if the landed report shows terminations>6/90, reopen
as FAIL", so that pass is a live reopen-check, not redundant load (its
dr0 pass already landed clean at 09:15; owndr in progress since
10:28). Left both runs' processes untouched. w015-c1 (train-2,
uncontended) has progressed further (into `walk_sto_0`) than w035-c1
(train-1, contended, still on `walk_det_5` since ~09:44) — expected
given the shared pod, not a stall. No session_verdict.json/report.json
landed for either sub-stride sibling or for coursedisp-c1's own
reopen-check this cycle. Backlog empty; no other standwalk arm has
independent preconditions met (re-confirmed). joystick/amp/cpg
DONE-or-maintenance (banners unchanged), walkcurr
[operator]-blocked (q_20260824T0233Z still open). IDLE: nothing
runnable beyond the housekeeping commit — CYCLE_WORKED not touched
(git-hygiene + verification only, no new triage/launch/code this
cycle).

Prior update, 2026-08-29 ~09:3x idle-kick (agent-doable-queue drain — **TWO
long-pending mixedsession reads finally landed and both VERDICTED
FAIL, closing two open threads at once; coursedisp-w015/w035 still
genuinely computing, untouched.**

1. **`hdgset1` (staged heading-SET canary) — CANARY FAIL** (marginal,
   one AND-clause only). 3/4 pre-registered criteria PASS (reward
   recovery, DR-0 gait_valid 6/6, probe_cmd_sensitivity diagonal
   response), but the mixedsession session-termination read — found
   this cycle already finished-but-uncollected on train-4 (`ops.sh
   podeval` idempotent reap, no relaunch) — is 7/90, one over the
   canary's own <=6/90 cap. All 7 are `hold_low_height`/`over_current`
   in hold/rise segments (the track's pre-existing stance-hold
   weakness, not a new walk fall; contact sheet clean six-leg gait).
   **This closes the joyfix grid at 5/5 FAIL** (bundle-c1, hdg-c1,
   cmdtrack-c1, velobs3-c1, hdgset1): no heading-width, bundle,
   raw-tick command-track, velocity-observability, or staged-heading-
   set lever moves off-axis (lateral/diagonal) command following at
   this 2M budget without tripping the stance-termination bar.
2. **`long-s0-cont1` (16M->32M budget continuation) — FAIL, joint
   with the already-recorded `long-s1-cont1` FAIL.** Same
   session_verdict.json instrument found finished-but-uncollected on
   the same pod/reap: dir_err_med 64.6->62.65deg (+3.0%, a plateau),
   slip/m_med 9.17->8.283 (+9.7%, real but under the 15% material bar
   both siblings needed for PASS), AND terminations/completion/
   gait_valid/sac all REGRESSED (2->5 terms, 0.978->0.944 complete,
   0.967->0.95 gait_valid, sac [2]->[0,2] new leg). Reward itself rose
   healthily the whole run (quarters -11.5/631.7/1412.5/2210.8) — not
   an optimizer failure, exactly the gate's own predicted
   mechanism/reward-shape ceiling: more budget on the identical
   recipe does not move command-tracking and mildly costs stance
   robustness doing it. **Confirms (does not just repeat) the
   long-s1-cont1 finding cross-seed**: budget-continuation on
   unified1-mix is closed; the course-tracking fix has to be a
   reward-shape change, which is exactly what the already-in-flight
   `k_walk_course_disp` / sub-stride-window lever (coursedisp-c1 /
   w015-c1 / w035-c1) is testing.

Both verdicts + SKILLS.md untouched (no PASS this cycle). Full sweep:
`coursedisp-w015-c1`/`-w035-c1` still genuinely computing on-pod
(train-2/train-1, no report.json yet, ps-alive) — the only in-flight
standwalk work, left untouched. All 12 GPU training slots free
(`capacity.py`), backlog+backlog_failed empty of in-scope work; with
the joyfix grid and the cont1 budget-continuation question both now
fully closed, there is no other pre-registered standwalk arm with met
preconditions until the coursedisp pair's official reads land. Other
tracks re-swept fresh: joystick/amp/cpg DONE-or-`[operator]`-
maintenance-only (banners byte-unchanged), walkcurr still
`[operator]`-blocked (`q_20260824T0233Z` unanswered). CYCLE_WORKED (2
real verdicts off genuinely-finished-but-uncollected artifacts, not a
re-verify no-op).

Prior update, 2026-08-29 ~09:1x triage cycle (no verdict yet — **w035-c1's own
n=1 course-trace probe lands, and it CONFIRMS the sibling's activation-
floor hypothesis rather than refuting it.** w035-c1 (0.35s window, MY
run this cycle per the prompt's own routing) finished training; its
official gate/owncfg/mixedsession prestage is genuinely computing on
train-1 (2/48 gate episodes in ~19min, matching this recipe's
established multi-hour ETA — confirmed via remote `ls`, not stalled).
Rather than block on that, ran the same fast preliminary read the
prior cycle used for w015-c1: pushed the checkpoint (md5-verified) +
synced fresh code (`1dce256e`) to genuinely-idle `train-3` (zero
contention with the official passes) and ran a single
`eval_checkpoint.py --course-trace` det walk episode (seed 91000, the
run's own full 95-key cfg-set verbatim, no video, ~9min wall on an
idle pod). Result, informative but n=1 (official n=12 det+sto read
still the one that counts): harness-printed per-tick `dir_err`
**52.9deg** (vs long-s0's ~55-65 band and coursedisp-c1's 60.3 mean —
same small/noisy improvement magnitude as w015's 52.6, nowhere near
the >=15deg PASS-with-delta bar) and independently re-derived from the
raw course-trace CSV: disp-mechanism telemetry active on only **17.9%**
of ticks (1072/6000) — comfortably below the gate's own >=50%
activation bar (worse than coursedisp-c1's 71% at window=1.5s, and
only marginally better than w015's 14.3% at window=0.15s despite a
2.3x longer window). When the mechanism DOES fire, its own windowed
metric reads clean (mean 11.6/median 6.9deg — genuinely on-course,
consistent with every prior reading of this mechanism). **Reading the
pair together**: both sub-stride windows (0.15s AND 0.35s) undershoot
the >=50% activation bar by a wide margin, and 0.35s barely helps vs
0.15s (17.9% vs 14.3%) — this looks less like "window size tunes
activation smoothly" and more like a step-function floor somewhere
between 0.35s and the parent's 1.5s (which cleared 71%). That is a
sharper, more useful conclusion than "both closed": if the official
n=12 reports confirm <50% activation on both, the productive next
question (should this lever ever be revisited) is where between 0.35s
and 1.5s activation actually crosses 50%, not whether sub-stride
windows help dir_err once active (they clearly do, when they fire).
Per the arm's own pre-registered branches this is consistent with
"sub-stride displacement pricing closed, route sway to stage-2
distillation" — but the OFFICIAL verdict stays deferred for both
siblings until their real n=12 det+sto reports land (gait_valid,
terminations, slip/m not yet in hand for either). Full sweep: all 12
GPU training slots free, backlog+backlog_failed empty of in-scope
work, no legal new standwalk arm exists before this joint pair's
official reads land. Other tracks re-swept (byte-identical banners):
joystick/amp/cpg DONE-or-maintenance-only, walkcurr still
`[operator]`-blocked (`q_20260824T0233Z` unanswered). CYCLE_WORKED (a
real diagnostic against a genuinely new checkpoint on a freshly-synced
idle pod, not a re-verify no-op) — next cycle to see w035-c1's SYNCED
gate/owncfg/mixedsession copy-back should verdict the joint pair per
the pre-registered gate text, reading both n=1 notes as context only.

Prior update, 2026-08-29 ~08:5x triage cycle (no verdict yet — **both sub-stride
window siblings (`coursedisp-w015-c1` 0.15s / `coursedisp-w035-c1` 0.35s)
finished training this cycle; w015-c1's own gate/owncfg/mixedsession
prestage is genuinely computing but VERY slow on its pod (train-2, 3
concurrent eval_checkpoint passes ~850%CPU each contending for the
28-core budget) — only 2/48 gate episodes written in the first ~20 min,
matching this recipe's own established multi-hour ETA; w035-c1 is
another cycle's claimed run this cycle, left untouched per the prompt's
own routing.** Rather than block the cycle on that, ran a fast
preliminary read on w015-c1's own frozen checkpoint: pushed it +
synced fresh code to the genuinely-idle `train-0` (its own gate/owncfg
pods were busy, this did not contend with them) and ran a single
`eval_checkpoint.py --course-trace` det walk episode (seed 91000, the
run's own full cfg-set verbatim, no video). Result, informative but
n=1 (do not treat as the verdict — the official 12-walk-episode
det+sto read is still the one that counts): the harness's own printed
per-tick `dir_err` reads **52.6 deg** (vs long-s0's ~55-65 band and
coursedisp-c1's 60.3 mean — a small, likely-within-noise improvement,
nowhere near the >=15 deg PASS-with-delta bar) and the `k_walk_course_
disp` mechanism's own telemetry fires on only **14.3%** of ticks
(860/6000) — well BELOW the gate's own >=50% activation bar, and much
lower than coursedisp-c1's reported 71% at window=1.5s. Read together
these suggest a specific, new hypothesis for whoever verdicts the
joint pair once the official numbers land: **the 0.15s window may be
short enough that `walk_course_disp_min_speed_m_s=0.02` rarely clears
in a single sub-stride tick (intra-stride net-position cancellation
happening even at the displacement level, not just the old velocity-
EMA level) — i.e. w015 could fail on ACTIVATION alone, independent of
whether the mechanism (when it does fire) helps dir_err.** If the
official w015 report confirms <50% telemetry while w035 clears it,
that pins the useful sub-stride floor closer to 0.35s than 0.15s, a
concrete, useful refinement rather than a flat "both closed." Full
12-pod sweep: all 12 GPU training slots read FREE (capacity.py — the
busy CPUs on train-0/2 are eval-only, not training slots), backlog +
backlog_failed empty of in-scope work; no legal new standwalk arm
exists before this joint pair's official reads land (per the arm's
own pre-registered branches). Other tracks re-swept fresh (byte-
identical STATUS.md headers): joystick/amp/cpg DONE-or-`[operator]`-
maintenance-only, walkcurr still `[operator]`-blocked (`q_2026082
4T0233Z` unanswered). CYCLE_WORKED (a real diagnostic tool run against
a genuinely new checkpoint via a freshly-synced idle pod, not a
re-verify no-op) — next cycle to see w015-c1's SYNCED gate/owncfg/
mixedsession copy-back should verdict the pair per the pre-registered
MECHANISM-HEALTH CANARY gate text, reading this note's n=1 activation-
rate finding as context, not as a substitute for the official n=12
read.)

Prior update, 2026-08-29 ~08:0x deep dig-in cycle (**coursedisp-c1 VERDICTED
CANARY PASS-no-delta; the flagged gate-metric question is ANSWERED BY
MEASUREMENT and the answer overturns the prior cycle's structural-sway
story**). New tool `rl_move/sim/probe_dir_floor.py` (snapshot
e765446a) rolls the scripted tripod teacher through real physics and
measures the per-tick `direction_err` floor under any model family /
cadence. Results (0.08 cmd, DR-0 det, 60 s, harness's own 5 mm/s
validity threshold; teacher verified genuinely stepping — six legs x
exactly 80 touchdowns/60 s at the 1.333 Hz clock, slip/m 1.27):
- primitive @ 25 Hz (1.5 deg/tick): tick mean **31.5 deg** — validates
  the probe against the accepted 25 Hz-era "~35 deg floor";
- primitive @ 100 Hz (0.375 deg/tick): tick mean **13.7 deg**;
- mesh @ 100 Hz (the standwalk judgment condition): tick mean
  **13.5 / med 5.4 deg** (windowed 1.5 s: 1.3 deg; net path 1.3 deg).
So the "~35 deg tick-level structural sway floor" is a 25 Hz slew-
quantization artifact and does NOT transfer to this track's contract.
The unified lineage's 60.3/32.4 per-tick reading is therefore ~47 deg
of REAL stride-to-stride zigzag a clean gait does not have — NOT
honest structure the metric unfairly taxes. RULING (assume-and-go,
recorded in OPERATOR_QUESTIONS.md): `direction_err_mean_deg` is
RETAINED as the track's direction gate metric, judged as a delta vs
the MATCHED mesh/100 Hz teacher floor (13.5 mean / 5.4 med) per the
already-registered joystick-track rule — no windowed/net redefinition
(windowed measures are structurally blind to the excess: every window
>=0.75 s reads ~6 deg on the same failed rollouts). Why coursedisp-c1
read flat despite a live mechanism (08-22 MISALIGNED-not-undertrained
ruling): its 1.5 s displacement window integrates the ~0.375 s
half-stride zigzag away, so it prices a near-saturated quantity.
Launched per the gate's own pre-registered PASS-no-delta branch: the
SUB-STRIDE window sweep `cw-standwalk-unified1-joyfix-coursedisp-
w035-c1` (0.35 s, train-1) + `-w015-c1` (0.15 s, train-2), both
VERIFIED RUNNING, warm from the same long-s0 16M parent, ONLY window_s
changed, bank `test_course_disp_window_semantics.py` 22/22 green at
both windows (obey>skew/stall/park/wrongway orderings hold
sub-stride). Pre-registered: if BOTH read flat at 2M, sub-stride
displacement pricing is CLOSED and the sway fix routes to the stage-2
teacher-distillation line; slip/m >1.5x parent band = the cmdtrack
velocity-tax failure mode = FAIL. Caveat on the c1 verdict: the
mixedsession termination count (<=6/90) was still computing at verdict
time (gate det pass complete on-pod, sto + mixedsession grinding on
contended train-1); all measured criteria PASS + healthy video — the
cycle that sees the SYNCED report should spot-check terminations and
reopen ONLY if >6/90.

Prior update, 2026-08-29 later idle-kick (no ledger verdict yet — official
report.json still genuinely computing; but the coursedisp-c1 canary's
OWN open scientific question is now answered directly from real data,
not inferred). **`cw-standwalk-unified1-joyfix-coursedisp-c1` (2M
canary) reads PASS-with-mechanism-live, PASS-no-delta on the metric
that matters — the k_walk_course_disp lever fires correctly on this
checkpoint's real training run but does NOT move the harness's own
`direction_err_mean_deg` headline, and the reason why is now a clean,
load-bearing finding, not a guess.**

What I did: the standard gate/owncfg/mixedsession prestage passes were
launched by the watcher as usual but are (still, as of this update)
genuinely computing — this recipe's full "walk rise lower hold" x
det+sto x per-mode-6 = 48-episode gate is running at ~2.5-4 min/real-
wall-clock-minute per episode on a contended pod (own-DR + mixedsession
sharing the same box), i.e. hours, not the usual <=45 min budget; ps-
verified alive throughout, not stalled. Rather than block the whole
cycle on that, I ran the DIG-IN's own `--course-trace` diagnostic
(built last cycle, used only against a frozen/local repro of a
DIFFERENT checkpoint until now) directly against THIS run's own live
gate process's real walk rollout on its own pod (kubectl exec,
read-only, killed once enough ticks accumulated so as not to starve
the official gate/owncfg/mixedsession passes further) — 20,838
commanded walk ticks harvested mid-eval, 71% of them with the disp
mechanism active (comfortably clears the gate's own >=50% telemetry
bar; this run's mechanism is confirmed LIVE on this checkpoint's real
eval, not just in the frozen-checkpoint bank replay from last cycle).
**The delta question, answered directly from that same tick stream**:
the mechanism's OWN metric (windowed net-displacement direction error)
reads mean 15.8 / median 4.3 deg when active — genuinely on-course,
matching the DIG-IN's original root-cause finding almost exactly. But
the harness's PER-TICK INSTANTANEOUS direction error over the exact
same ticks reads mean 60.3 / median 32.4 deg — statistically
indistinguishable from long-s0's own pre-existing ~55-65 deg band, i.e.
**flat, no delta, despite the mechanism verifiably pricing gradient
against real training the entire 2M steps.** Two spot-checked det
walk contact sheets (episodes 0 and 3) show clean six-leg alternating
gait, upright, no drag/skate/topple — visually consistent with a
healthy, un-regressed walk, not a collapse.
**Why this makes complete sense, and why it is NOT "mechanism needs a
bigger dose"**: `direction_err_mean_deg` is fundamentally an
INSTANTANEOUS per-tick metric, and this policy's real path was
*already* close to on-course in NET terms before this mechanism ever
existed (the original root-cause diagnostic measured the SAME ~6 deg
windowed error on the OLD, inert-course-term checkpoint). Pricing net
displacement can only ever ask "is the average path roughly right" —
it structurally cannot see or correct INTRA-STRIDE heading sway (the
honest side-to-side wobble every tripod gait exhibits stride-to-
stride), because by construction it integrates that sway away over
its 1.5 s window. **The thing `direction_err_mean_deg` is actually
measuring was never broken by course-tracking in the net sense — it
is dominated by per-tick gait sway that no windowed/net reward term
can ever price down, almost by definition.** This is a stronger,
more specific conclusion than "PASS-no-delta, try a dose sweep" (the
gate's own pre-registered fallback): a dose/window-size sweep on
`k_walk_course_disp` predictably will not move this number either,
for the same structural reason a 10x dose wouldn't have moved it here.
**Flagging as DIG-IN rather than closing unilaterally**, because the
real fix implied is not another reward-mechanism dose but a candidate
METRIC/GATE audit: either (a) build a genuinely PER-TICK course-
pricing term that can see and correct stride-to-stride sway (the
`k_walk_cmd_track` raw-tick lever was the one candidate tried and it
raised slip 2.5x for no dir_err gain — a different, real per-tick
mechanism idea may still exist), or (b) reconsider whether
`direction_err_mean_deg` — an instantaneous per-tick statistic — is
even the right DONE-gate metric for a hexapod gait with structural
per-stride sway, vs. a windowed/net heading measure closer to what
`k_walk_course_disp` itself computes. (b) is a bigger methodological
call (it would mean re-deriving one of the track's own named DONE-gate
metrics) that a deep-model cycle should make deliberately, with the
full semantics-bank/gate-definition toolkit, not as a byproduct of a
mechanism canary triage. Until that lands, do not fund a `k_walk_course
_disp` dose/window sweep — per this cycle's own math it is predicted
to fail for the same structural reason, which would burn budget to
reconfirm a result already implied by the data in hand.
Official ledger verdict on `coursedisp-c1` itself is DEFERRED (not
recorded) pending the still-computing report.json (gait_valid_frac,
sacrificed-leg list, exact slip/m, and the mixedsession termination
count are not yet in-hand) — whichever cycle sees the SYNCED
copy-back should verdict PASS-no-delta-mechanism-confirmed (not FAIL:
reward is not collapsing, video/telemetry both look healthy, this is
squarely the gate's own pre-registered "PASS-no-delta ... not a
mechanism kill" branch) using the official numbers plus this note's
direct measurements, and should read this DIG-IN flag before deciding
what (if anything) to fund next on this lever. Other opens reads this
cycle (all ps-verified genuinely still alive, untouched):
`hdgset1`/`long-s0-cont1` mixedsession `dr0_long` passes on train-4
(180s x N episodes, many hours ETA, unchanged from prior cycles).
Other tracks re-swept: joystick/amp/cpg DONE-or-`[operator]`-
maintenance-only (banners unchanged), walkcurr still `[operator]`-
blocked (`q_20260824T0233Z` unanswered). Backlog+backlog_failed empty
of in-scope work; capacity.py shows all 12 GPU slots free but the only
two items with met preconditions (this canary's own confirmation, and
the two long-running train-4 mixedsessions) are already in flight —
no new arm is launchable until this DIG-IN's methodological question
is resolved (funding another dose sweep now would be exactly the
"invented filler" the standing prompt warns against, given the math
above already predicts its outcome). CYCLE_WORKED (new tool
application + a genuinely new root-cause-level finding from real data,
not a re-verify no-op).

DIG-IN flagged for a deep cycle: is `direction_err_mean_deg` (an
instantaneous per-tick statistic) the right DONE-gate metric for a
hexapod gait with structural per-stride heading sway, given
`k_walk_course_disp` proves the NET path is already on-course
(windowed dir_err 15.8/4.3 deg mean/median) while the per-tick number
stays flat at ~60/32 deg on the exact same real rollout? If yes (gate
metric is fine, sway itself must fall): what per-tick (not windowed)
mechanism could reduce stride sway without the slip blowout
`k_walk_cmd_track` showed? If no: propose a windowed/net replacement
DONE-gate metric and re-derive the joystick/standwalk gate text
against it before funding further course-mechanism arms.

Prior update, 2026-08-29 idle-kick (DIG-IN closed — **built + bank-proved +
launched the k_walk_course fix-lever (b) the prior cycle flagged
(position-displacement course metric)**). Root-cause recap: the
recipe's only heading-pricing term, `reward.k_walk_course`, EMAs
INSTANTANEOUS body velocity (tau=0.75s) and was found completely inert
for the `long-s1-cont1` lineage. New mechanism landed this cycle:
`reward.k_walk_course_disp` (+ its own `_overspeed` twin, since the old
overspeed charge lives nested inside `k_walk_course>0` and would
otherwise silently vanish) prices the NET BODY-POSITION DISPLACEMENT
over a trailing window (default 1.5s) instead of a velocity EMA --
immune to intra-stride sway/zigzag cancellation by construction (it
measures where the body actually ended up, not an average of noisy
per-tick velocity samples). New cfg keys default 0 = off, bit-exact
(confirmed: same 7 pre-existing `test_phasedir_semantics.py` failures
with/without the patch, no new ones). Validation, cheapest-to-strongest:
(1) scripted-teacher parity -- swapping the EMA for the disp mechanism
at matched coefficients reproduces the EXISTING mechanism's pricing of
every scripted class (obey/fastcadence/stall/park) to within ~1 return
unit/bin, and prices skew/wrongway MORE aggressively, never less; (2)
REAL FAILED CHECKPOINT replay (the DIG-IN's own required bar, not just
a scripted proxy) via a new `eval_checkpoint.py --course-trace` CLI
diagnostic: on `long-s1-cont1`'s own real 60s deterministic walk
rollout, the EMA activates on ~4% of commanded ticks (near-inert,
matches the root-cause's 0/5899) while the windowed net-displacement
metric activates on ~97% of ticks reading a mean cos ~0.99 -- the
real PATH is close to on-course (6.2deg net direction error) even
though the per-tick instantaneous view says ~55-62deg (matches the
harness's own `direction_err_mean_deg` headline almost exactly). Bank:
new file `test_course_disp_semantics.py`, 16/16 green (includes the
real-checkpoint test, skipped only if the artifact zip is absent).
Landed + pushed (`exp/exp-course-disp-lever-b`, 620230a5). Launched the
first canary this cycle: `cw-standwalk-unified1-joyfix-coursedisp-c1`
(2M, warm from `long-s0`'s own 16M PASS checkpoint, `k_walk_course`
and `k_walk_cmd_track` both OFF so only the new mechanism prices
course, `--now` VERIFIED RUNNING on train-1) -- open question the
scripted/replay evidence CANNOT answer: does the mechanism actually
MOVE `direction_err_mean_deg` once it's driving gradient updates during
real training, not just read correctly on a frozen checkpoint. Gate:
MECHANISM-HEALTH CANARY at 2M (reward not collapsing, gait_valid>=5/6,
terminations<=6/90, `reward_walk_course_disp` telemetry live) with a
PASS-with-delta bar of >=15deg dir_err drop vs long-s0's own ~55-65deg
band. Other open reads (`hdgset1`, `long-s0-cont1` mixedsession,
train-4, both other cycles' claimed runs) reconfirmed still genuinely
computing via on-pod `ps`, untouched. Other tracks re-swept:
joystick/amp/cpg DONE-or-`[operator]`-maintenance-only (unchanged),
walkcurr still `[operator]`-blocked (`q_20260824T0233Z` unanswered).
CYCLE_WORKED (real tool + mechanism + bank + launch, not a re-verify).

Prior update, 2026-08-29 idle-kick (no verdict yet — **`hdgset1`'s gate+owncfg
DR-0 reads were reaped this cycle (finished on-pod, sitting uncollected
— `ops.sh podeval` copy-back-only reap, idempotent, no relaunch): DR-0
det walk gait_valid 6/6, sac=[], 0 terms — the 2nd of its 4 AND-gated
canary criteria to confirm PASS (probe_cmd_sensitivity already PASSED
last cycle: fwd 0.44/diag_fl 0.314/diag_fr 0.249, all clearing their
bars; reward-recovery also already PASSED last cycle, shallower trough
than the long-s0-cont1 baseline trend). 3 of 4 criteria now CONFIRMED
PASS; only session-terminations (the mixedsession read) remains open,
genuinely still computing on train-4 (started 02:57, `owndr` pass at
~759% CPU, sharing the pod with `long-s0-cont1`'s own still-running
mixedsession `dr0_long` pass, started 03:40 — both ps-verified alive,
not stalled, matching this recipe's known 4-5h mixedsession ETA). Full
12-pod sweep (`train-0/1/2/3/5/6/7/8/9/10/11`) confirms every other pod
genuinely idle (zero eval/train processes) and no orphans anywhere in
the fleet this time. No new arm is launchable: the only two open
standwalk decisions (`hdgset1` canary verdict, `long-s0-cont1` vs
`long-s1-cont1`'s own FAIL — joint cont1 read) both wait on these same
two in-flight mixedsession passes; the DIG-IN-flagged position-
displacement course metric (k_walk_course fix lever (b)) still needs
real design+bank work another (deep-model) cycle owns, correctly left
untouched. Other tracks re-swept fresh: joystick/amp/cpg DONE-or-
[operator]-maintenance-only (banners byte-unchanged since 08-24/08-25),
walkcurr still [operator]-blocked (`q_20260824T0233Z` unanswered).
Backlog + backlog_failed empty of in-scope work. CYCLE_WORKED (a real
reap of finished-but-uncollected eval artifacts, not a re-verify
no-op).

DIG-IN still open (flagged 08-29 ~05:0x, unaddressed): design + build
the position-displacement course-direction metric (k_walk_course fix
lever (b)), validated against `long-s1-cont1`'s real trajectory before
any bank test or launch.

Prior update, 2026-08-29 ~05:0x idle-kick (**joyfix grid now 4/4 closed, all
FAIL — and the ~04:3x root-cause's own pre-registered follow-up is
answered plus a second lever is closed by direct measurement, no safe
fix found yet.**

1. **`cmdtrack-c1` VERDICTED CANARY FAIL - MECHANISM.** This was the
   pre-registered test of the ~04:3x diagnostic's alternate lever
   (`reward.k_walk_cmd_track`, raw per-tick command score, structurally
   immune to the EMA-vector cancellation that makes `k_walk_course`
   inert). Result: direction_err_med_deg is FLAT (66.0 vs parent
   long-s0's own 64.6 — no improvement, the entire point of the lever)
   while slip_per_m_med blows out 2.53x (23.2 vs parent 9.17, cap
   1.5x). The other 4 AND-gated criteria (reward recovery, DR-0
   gait_valid, session terminations, probe fwd speed) all PASS in
   isolation — this is a clean mechanism refutation, not instability.
   **CLOSES the raw-tick scalar-lever fix for k_walk_course**, exactly
   as the diagnostic's own fallback text anticipated.
2. **`velobs3-c1` VERDICTED CANARY FAIL - MECHANISM** (session
   read pulled fresh off-pod this cycle, had gone stale on the
   controller): 4/5 criteria PASS but session terminations
   (mixedsession, 90 eps) land at 10/90 vs the canary's own <=6/90 bar
   (over_current 5 + hold_low_height 5, in rise/hold/walk segments) —
   the SAME pattern as `long-s1-cont1`'s own FAIL: isolated-mode panels
   stay clean, the defect is sequenced-mode-transition-specific and
   only the mixedsession instrument catches it. Closes the plain
   warm-swap of `goal.walk_obs_body_vel` 2->3; per its own gate text,
   any retry needs an annealed/staged introduction, not a one-shot
   swap.
3. **The joyfix grid is now 4/4 closed: bundle-c1 FAIL (08-28),
   hdg-c1 FAIL (08-28), cmdtrack-c1 FAIL, velobs3-c1 FAIL.** Only
   `hdgset1` (the staged heading-SET follow-up) remains open, still
   genuinely computing (mixedsession on train-4, shared with
   `long-s0-cont1`'s own dr0_long pass) — left untouched.
4. **k_walk_course fix-lever (a), "just lower the activation floor",
   is ALSO CLOSED by direct measurement, not assumed safe.** Swept
   `walk_course_min_speed_m_s` through the full existing
   `test_phasedir_semantics.py` bank (the exact stack every unified1
   arm launches with) at 0.01/0.015/0.02: **every value in the
   zigzag-sensitive band (0.004-0.03, the diagnosed activation gap)
   breaks 8 of the bank's own established invariants**
   (`test_obey_beats_fastcadence_every_bin`,
   `test_pd9_ref_floor_spares_ramp_class_prices_real_overspeed`,
   `test_pd9_det_orderings_survive_ref_floor`, plus 5 more) — the 0.04
   floor was deliberately calibrated (phasedir3, 08-22) to stop
   directed wrong-way/fastcadence travel from clearing the bar during
   low-speed ramp ticks, and that protection and the zigzag-activation
   fix share the exact same knob with no daylight between them. A
   temp local repro (reverted, tree clean) also ruled out the tau
   knob: raising `walk_course_tau_s` (0.75s -> up to 6s) does NOT
   raise the achieved EMA magnitude on a synthetic symmetric-zigzag
   drive — it measurably LOWERS it further (0.0338 -> 0.0222 mean
   |EMA| at tau 0.75->6.0s), i.e. more averaging does not rescue this
   failure mode the way period-matched-noise intuition would suggest
   (likely because the synthetic drive's fast direction reversals are
   also damped by gait-tracking lag, not just the EMA). **Net position:
   no single-scalar dose fix exists on the current mechanism** — the
   only lever left standing is (b) from the ~04:3x diagnostic, a
   genuinely different metric (net position displacement over a
   window instead of an EMA of instantaneous velocity), which needs
   real engineering (body-frame projection, a new per-episode state
   buffer wired into `MJX_SNAPSHOT_EXTRA` for the batched vec env, and
   validation against the REAL checkpoint trajectory, not just a
   scripted zigzag proxy whose fidelity to the learned failure mode is
   unconfirmed) plus its own bank proof before any launch — correctly
   DIG-IN scope, not a same-cycle canary. Filed as the track's open
   Next item; do not fund a same-recipe continuation on `long-s1-cont1`
   or launch another scalar-lever canary until this lands.
5. No new launch this cycle: all 12 GPU slots read FREE
   (`capacity.py`), but the only two items with independent
   preconditions met (`hdgset1`, `long-s0-cont1`'s own mixedsession)
   are already running (train-4, confirmed live via on-pod `ps` at
   both the start and end of this cycle), and the position-displacement
   mechanism above is correctly gated behind design+bank work another
   cycle should own, not a rushed same-cycle launch. Re-swept
   joystick/amp/cpg (DONE-or-`[operator]`-maintenance-only, unchanged)
   and walkcurr (`[operator]`-blocked, q_20260824T0233Z still open).
   Backlog+backlog_failed empty of in-scope work. CYCLE_WORKED (2 real
   verdicts + a real, evidence-based mechanism-design finding — not a
   re-verify no-op).

DIG-IN flagged for a deep cycle: design + build the position-
displacement course-direction metric (k_walk_course fix lever (b)),
validated against `long-s1-cont1`'s real trajectory before any bank
test or launch — evidence chain: `long-s1-cont1` FAIL (~03:0x) ->
root-cause (~04:3x) -> `cmdtrack-c1` FAIL + floor/tau dead ends (this
cycle).

Prior update, 2026-08-29 ~04:3x (idle-kick, no verdict — **command-tracking
reward audit (the open lever named by the ~03:0x FAIL below) ROOT-
CAUSED: `reward.k_walk_course` — the ONLY heading/course-tracking
reward term in the base `unified1-mix` recipe — has been COMPLETELY
INERT for `long-s1-cont1`'s entire 16-32M-step lineage.** Reproduced
the exact recipe locally against the FAILed checkpoint
(`ppo_goal_cw_standwalk_unified1_mix_long_s1_cont1.zip`, deterministic,
matched cfg-set stack) with temporary instrumentation (not landed —
reverted, `git status` clean): confirmed `cfg_get(...,"k_walk_course")`
correctly reads 2.0 every tick and the outer guard (`s_ref > 1e-3`,
i.e. a command is active) fires on ~95% of ticks, but the INNER
activation gate — `spd_c >= reward.walk_course_min_speed_m_s` (0.04
m/s), where `spd_c` is the MAGNITUDE of a `tau=0.75s` EXPONENTIAL-
MOVING-AVERAGE of the raw per-tick body-frame velocity VECTOR — never
fired ONCE across a full deterministic 60s episode (0/5899 active
ticks), even though this exact checkpoint's own DR-0 gate report shows
real, non-trivial motion (`speed_mean_m_s=0.031`, `forward_dist_m`
positive, gait_valid, six legs cycling). Root cause: the EMA is
VECTOR, not scalar — a body that's genuinely translating but wanders/
zigzags stride-to-stride (matching the ~62-68deg mean `direction_err`
this whole campaign has been stuck at) has its per-tick velocity
vectors partially CANCEL in the exponential average, so `|EMA(v)|`
stays under the 0.04 m/s floor even when the scalar speed clears it
comfortably. Since `k_walk_course` is the only term pricing HEADING
(not just progress-vs-parking) in this recipe, this cleanly explains
the whole campaign's paradox: slip/drag/idle terms (which don't depend
on a vector EMA clearing a floor) kept optimizing every continuation,
while dir_err never moved, because the one term that could have priced
it was never actually paying or charging anything, the entire time.
Cross-checked the code's OWN alternate lever: `reward.k_walk_cmd_track`
(`walk_cmd_track_score`, `walk_task.py:100`) scores the RAW
instantaneous per-tick velocity against the command with no EMA at
all — structurally immune to this exact cancellation failure (any
positive along-command component pays immediately) at the cost of
reintroducing the stride-sway noise the EMA was originally built
(operator order 2026-08-22, phasedir1 fix) to filter out — a real
tradeoff, not a free fix. **This is exactly what the still-running
`cw-standwalk-unified1-joyfix-cmdtrack-c1` canary (joyfix wave, already
in flight, not launched by this cycle) tests** — no redundant arm
needed; its own pending mixedsession/session-terminations read (dr0_long
in progress on train-1 as of this cycle) is the direct verdict on
whether trading EMA cancellation-immunity for raw-tick gait-sway noise
nets out better for `dir_err`. **Pre-registered follow-up if
`cmdtrack-c1` ALSO fails to move dir_err**: fix `k_walk_course` itself
rather than replace it — either (a) lower `walk_course_min_speed_m_s`
from 0.04 to match this lineage's own achieved sustained-EMA band
(~0.004-0.03 m/s, confirmed via `env/walk_along_ema_m_s`'s training
history and this cycle's local repro — an order of magnitude below the
current floor) so the term activates at all, or (b) replace the
velocity-EMA gate with a longer-baseline net-POSITION-displacement
direction (delta over N seconds, e.g. reusing the anchor/lookahead
machinery already in this file) which is immune to both stride-sway
AND slow-zigzag cancellation by construction, unlike either existing
lever. Do not fund either without checking `test_task_semantics.py`
ranks the fix correctly first (reward/eval alignment gate). Other open
reads this cycle (all still genuinely computing, ps-verified,
untouched): `long-s0-cont1` gate+owncfg+mixedsession-owndr (train-4),
`velobs3-c1`/`cmdtrack-c1` mixedsession-dr0_long (train-0/1), `hdgset1`
gate+owncfg+mixedsession-dr0 (train-4, shared). Other tracks re-swept:
joystick/amp/cpg DONE-or-`[operator]`-maintenance-only (banners
unchanged), walkcurr still `[operator]`-blocked (BC-kickstart ruling,
`q_20260824T0233Z`, still OPEN). Backlog+backlog_failed empty of
in-scope work. CYCLE_WORKED (real root-cause diagnostic landing new,
previously-undocumented evidence — not a re-verify no-op — even though
no code changed and no verdict was recorded this cycle). Prior banner
below.


> Older journal entries (pre-08-29 ~15:2x) plus the SUPERSEDED 08-27-era
> "## Now"/"## Next" sections archived VERBATIM in
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md` (meta 08-30 trim).
> Current state/next items live in the newest Update entries at the TOP
> of this file; do not act on archived Next items.

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
