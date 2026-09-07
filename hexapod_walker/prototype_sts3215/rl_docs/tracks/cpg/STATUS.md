# cpg - Berkeley-style parameter gait search

## 2026-09-07 ~03:2x (refill; 11/11 GPU pods free, backlog empty, no completion assigned) — periodmin1 joint search FINISHED (60/60): boundary-pin hypothesis REFUTED, best period re-converges to ~2.1s even with the bound widened to 1.0s

**Plain English:** the prior cycle asked "was the CPG winner's ~2.0s
stride period only picked because the search never let it try faster?"
by widening the lower bound to 1.0s and re-running the full joint
search (period + swing_frac + cmd_tau + lift_m together, not the naive
one-line substitution already refuted). Answer: no — given the freedom
to go as fast as 1.0s, the optimizer still landed on essentially the
SAME period.

`paper-cpg-periodmin1-20260907` completed all 60 iterations (found
finished, no live process at cycle start — `logs/paper_cpg_search/
paper-cpg-periodmin1-20260907.json`, `n_history=60`). Best point
(iteration 14, `gp_ei_numpy`): `period=2.0994`, `cmd_tau=0.2428`,
`lift_m=0.0312`, `swing_frac=0.3` (unchanged), `workspace_margin=0.971`
— i.e. the joint search, with the bound removed, still converges to a
period **slower** than the old winner's exact 2.0 (which was itself
sitting on the OLD bound), not faster. This is a clean, decisive null:
the boundary-pin was not hiding a faster optimum; ~2.0-2.1s is a real
local optimum for this suite/gait/speed, not a search-space artifact.
Closes the "faster cadence" sub-question of todaypolicy's named
cadence-CPG-harvest lever.

**In flight, not yet read:** kicked `eval_cpg_gate.py --params-from
logs/paper_cpg_search/paper-cpg-periodmin1-20260907.json --name
cpg-periodmin1-winner --robust --yaw-trim` (same protocol as the
`robust120-winner-yawtrim` gate this is being compared against) in the
background on the controller pod (PID 2349039, `/tmp/
cpggate_periodmin1.log`, `logs/cpg_gate/cpg-periodmin1-winner/`,
CPU-only, zero GPU/training spend) to get a real held-out comparison
against the incumbent winner's `gate_verdict.json` (dr0 slip_per_m
0.709, heading_progress_frac_mean 0.897, all panels PASS) before
writing any adoption verdict — a ~2.1 vs 2.0 period difference plus
the other re-tuned params could still be a genuine (if modest)
improvement even though the boundary-pin theory itself is refuted.
Still running at cycle end (video-heavy multi-panel robust suite,
~10+ CPU-minutes in and counting via `ps aux`) — **next reader: read
`logs/cpg_gate/cpg-periodmin1-winner/gate_verdict.json` directly, do
not re-launch** (idempotent single run, PID 2349039 or its successor
if it died — check `ps aux | grep eval_cpg_gate` first). If it PASSes
AND beats the incumbent's slip/progress numbers outside noise, that's
a same-family parameter-refresh candidate for `cpg_v1.npz`'s adoption
process (A/B, per this track's own DONE-gate rule) and unblocks
todaypolicy's cadence-harvest lever with a genuine (if modest) delta;
if it merely matches or is worse, the cadence-harvest lever is CLOSED
outright (best achievable is what `robust120-winner-yawtrim` already
has) and todaypolicy's Next list has no further open item from this
side.

No GPU launch this cycle (CPU-only diagnostic work). Full board
re-confirmed unchanged otherwise: joystick/amp DONE, standwalk blocked
on fresh design thinking, assistfade `s0-longbudget` + walkcurr's
item(1) crossgrav-composite fork stay DIG-IN-owned (not touched, model
tiering), walkcurr just launched a fresh mechanism
(`walk_duty_band_gate`) 2-arm canary pair (`dbandgate-{fresh,fix}`) —
both finished training this cycle with no gate kicked yet, found
orphaned and kicked (`ops.sh podeval`, registered via `evalpending`),
left for the next reader per walkcurr's own STATUS. `CYCLE_WORKED`
touched (real diagnostic finding + 3 eval kicks landed: 2 podeval + 1
cpg gate).

Evidence: `logs/paper_cpg_search/paper-cpg-periodmin1-20260907.json`
(`best`/`history`), `logs/cpg_gate/robust120-winner-yawtrim/
gate_verdict.json` (incumbent baseline), `ps aux` PID 2349039/2346780/
2346781, `rl_move/orchestrator/pending_evals.json`.

## 2026-09-07 ~01:5x (this cycle, refill — no GPU launch licensed, feeds todaypolicy's own named "faster motion source / cadence-CPG harvest" next lever)

**Plain English:** the robust-gate CPG winner's `period` (time per
stride cycle) landed exactly at the search's own lower bound (2.0s,
i.e. the fastest cadence it was ever allowed to try) in BOTH prior
searches (contextual-250 and robust120) — a boundary-pinned parameter
is a live sign the true optimum is faster still, unexplored. Widened
the search space and ran a first matched-control check before
committing GPU/wall-clock: **naively halving the period alone (same
swing_frac/lift_m/cmd_tau the search tuned for period=2.0) makes
things WORSE, not better** — `progress_frac_mean` 0.925->0.868 and
`slip_per_m_mean` 0.91->1.98 (more than doubled), 0 falls both
(matched replay, same seeds/suite/speed, `paper_cpg_search.py
--replay-json`, `/tmp/replay_period{2,1}.json`). This makes sense once
named plainly: `period` is stride CADENCE at a fixed COMMANDED
velocity, not top speed — a shorter period means more, choppier steps
covering the same commanded distance, which raises slip without
buying any extra travel unless the other params (swing fraction, foot
lift, workspace margin) are RE-TUNED for the new cadence. The boundary
pin is real evidence something better may exist, but "just lower
period" alone is REFUTED as a one-line fix; it needs the full joint
search the tool was built for.

**Built** `apply_period_bound_override()` + `--period-min`/
`--period-max` CLI flags in `paper_cpg_search.py` (both `None` =
bit-exact no-op, verified via `test_period_bound_override_*` — 3 new
tests, 7/7 green in `test_paper_cpg_search.py`) so the tetrapod/wave
period bounds (hard-coded `2.0-12.0s` / `5.0-24.0s`) can be widened
without touching the search internals. Smoke-tested (`--iterations 4`
CLI run, `--replay-json` matched-control pair above). Snapshot
`exp/cpg-period-lowerbound-widen` (`09dd496d`).

**Launched** a real joint-tuned search to test the boundary-pin
properly (not another naive substitution): `paper-cpg-periodmin1-
20260907` — same recipe as the `robust120-winner-yawtrim` search
(contextual suite, `--mu-list 0,1.2,0.8`, speed/wz/slip-weight
identical), `--period-min 1.0` (lower bound widened 2.0->1.0s),
warm-started from the current winner AND a period=1.0 twin. Running
DIRECTLY on the controller pod (`hexapod-sweep-friction`, CPU-only,
zero GPU/training spend — this is the eval-harness/design-tool lane,
not an RL launch, no `launch_run.py` involved), PID 2261858 (reparented
to init, survives this cycle), output
`logs/paper_cpg_search/paper-cpg-periodmin1-20260907.json`, log
`/tmp/paper_cpg_periodmin1.log`. **Slower than the 08-23 searches**
(~30-100s+/iteration observed vs that search's ~27s/iteration average)
— almost certainly the 08-24 mesh-model switch (this script always
ran mesh-family scripted rollouts) making the scripted CPU rollout
itself heavier post-mass-audit; budgeted 60 iterations, first 4 landed
within this cycle (2 warm/2 random, period 2.0 best so far at -0.172,
period 1.0 -0.768, matching the replay finding's direction; the two
`random` draws at period 6.43/18.25 score worse still, as expected for
slower-than-baseline cadence). **Left running in background, NOT
polled/slept-on further this cycle** — next reader: read
`logs/paper_cpg_search/paper-cpg-periodmin1-20260907.json`'s `"best"`
field directly (`python3 -c "import json; d=json.load(open(...));
print(d['best'])"`), do not re-launch a duplicate while PID 2261858 (or
its successor if it died) is still alive (`ps aux | grep
paper_cpg_search`). If the joint search's best period stays >=2.0
after 60 iterations, this CLOSES the "faster cadence" hypothesis for
good (both the naive AND joint-tuned variants refuted) and
todaypolicy's stride campaign needs a different alternative than
cadence; if it finds a genuinely better sub-2.0s point, run it through
`eval_cpg_gate.py --robust --yaw-trim` before any adoption claim (same
strict gate the current winner passed), and only THEN does harvesting
a new/faster `cpg_v2` motion-library clip for a BC-anchor GPU arm
become licensed — no GPU launch yet, this is still the design/probe
step.

Full board re-confirmed unchanged otherwise: walkcurr item(1)
(crutch-ON composite) and assistfade `s0-longbudget` both remain
DIG-IN-owned/unverdicted (re-checked via `ops.sh entry`, no new verdict
on either — left for the deep-model cycle, not touched here); item(4)
needs an unscoped new per-leg-utilization/slip mechanism (not this);
standwalk stays blocked pending fresh design thinking (unchanged since
09-05 ~06:3x); joystick/amp DONE/maintenance. 11/11 reachable GPU pods
free, backlog empty — no GPU launch this cycle (the one live design
thread is this CPU probe, not yet resolved into a licensed GPU arm).
`CYCLE_WORKED` touched (real code + tests + snapshot + a genuine
matched-control finding + an in-flight design search).

Evidence: `rl_move/sim/paper_cpg_search.py` (diff), `rl_move/tests/
test_paper_cpg_search.py` (3 new tests), `/tmp/replay_period{2,1}.json`
+ `.log`, `logs/paper_cpg_search/paper-cpg-periodmin1-20260907.json`
(in-flight), W&B n/a (CPU-only, no training run), RL_LOG 09-07 01:5x.

Last updated: 2026-08-24 ~01:3x UTC (**THIRD independent adoption
data point in (pre-registered 8M matched pair that was found stuck
REFUSED and fixed/launched by an earlier cycle) — same result again,
no story change.** `cw-cpg-teacherfork-ab8m-cpgv1r` (PASS) vs
`cw-cpg-teacherfork-ab8m-teacherr` (PASS, baseline): cpg_v1 det prog
1.29/slip 2.68 vs teacher 1.22/slip 2.69, sto prog 0.97/slip 3.27 vs
0.90/3.27; gait_valid 6/6 both arms both modes, zero terms/sacrificed
legs, video-clean. Confirms the already-CLOSED co-equal-style-source
ruling a third time; no new action taken (remaining items stay
maintenance/[operator] only). Evidence:
`logs/ckpt_eval/cw_cpg_teacherfork_ab8m_cpgv1r_gate/`,
`..._teacherr_gate/`. Prior banner below.)

Previous entry (2026-08-23 ~21:1x UTC (**SECOND independent adoption
data point in — gate stays GREEN, adoption answer strengthened.**
Fresh matched-6M A/B pair `cw-cpg-ab6m-cpglib` (PASS) vs
`cw-cpg-ab6m-teachlib` (INFORMATIVE control): cpg_v1 parity-or-better
on every DR-0 axis — det prog 1.28/fwd 0.76m/slip 2.53 vs teacher
1.27/0.71m/2.58, sto prog 0.96/slip 3.10 vs 0.88/3.46, gait_valid
24/24 combined, zero terms, both video-clean. The teacher's NO-SWAP
branch is dead twice over; cpg_v1 now has LOWER slip in both modes on
this pair. Ruling unchanged: co-equal (slightly favored) style source,
no forced teacher_v2 swap at n=6 noise-edge deltas; future amp arms
may pre-register cpg_v1 as the default. The second-data-point Next
item is CLOSED. Remaining items are maintenance/[operator] only.
Evidence: `logs/ckpt_eval/cw_cpg_ab6m_cpglib_gate/`,
`logs/ckpt_eval/cw_cpg_ab6m_teachlib_gate/`. Prior banner below.)

Previous entry (2026-08-23 ~06:3x UTC (**TRACK GATE GREEN — adoption A/B
answered at matched budget; both tracks.json clauses now satisfied.**
The +6M budget pair finished together and was read jointly per its own
pre-registered gate: `cw-cpg-teacherfork-ab-cpgv1-acq1b` (CPG library
side, 8M total) VERDICTED PASS — DR-0 det progress_ratio med 1.35 /
fwd 0.77m (CLOSES-GAP band was >=1.10/>=0.65m; its 2M read was
0.99/0.59), sto prog 0.90, gait_valid 6/6 det+sto, zero terms,
video-clean; reward+eval rose together (textbook 08-21 continuation
payoff). `cw-cpg-teacherfork-ab-style05-budget2` (matched teacher_v2
control) VERDICTED INFORMATIVE — det ~FLAT vs its own 2M numbers
(1.16/0.69 -> 1.21/0.71, inside noise), so the CPG catch-up is REAL
gap-closing, not a shared budget lift (sto improved on both sides,
0.58->0.95 and 0.58->0.90 — that axis was undertrained for both).
ADOPTION DECISION (recorded in both verdicts): `cpg_v1.npz` is
promoted to a CO-EQUAL alternative AMP style source — det deltas
favor CPG but sit at the edge of n=6 noise, sto slip slightly favors
teacher (3.15 vs 3.57): no honest superiority claim, NO forced
teacher_v2 swap, NO joystick slip-bar recalibration; future amp arms
may pre-register either library. With this, the tracks.json cpg gate
is GREEN: (1) held-out contextual robust gate FULL PASS 08-23
(5 panels, zero falls, artifact `cpg_controller_robust120_yawtrim.json`
exported, web-UI + DriveController loaders built); (2) downstream
adoption measured as an A/B fork (2M pair + matched-8M budget pair),
not a silent swap. Remaining items are maintenance/[operator] only:
driving the physical robot on the CPG controller, and any future
teacher-v2 regeneration fork if a later arm shows real superiority.
Evidence: `logs/ckpt_eval/cw_cpg_teacherfork_ab_cpgv1_acq1b_gate/`,
`logs/ckpt_eval/cw_cpg_teacherfork_ab_style05_budget2_gate/`.
Prior banner below.)

Previous entry (2026-08-23 ~06:1x UTC (**SECOND DATA POINT LAUNCHED (matched
+6M budget pair):** a concurrent cycle continued `cw-cpg-teacherfork-ab-
cpgv1` itself (+6M, `-acq1b`, RUNNING train-0, reward still rising at 2M
per the 08-21 ruling); this cycle caught that the matched teacher_v2
control was NOT queued by either side (would confound "CPG gap closes
with budget" against "both sides improve with budget") and launched
`cw-cpg-teacherfork-ab-style05-budget2` (identical +6M single-lever
continuation of the style05 champion, VERIFIED RUNNING train-1,
`logs/experiments/` not yet populated — check both W&B runs jointly at
~8M total for the next triage). Also self-caught and killed a duplicate
launch attempt (own `cpgv1-budget2`, a re-continuation of the exact same
checkpoint `-acq1b` already covers, born from two independent `-cont1`
name collisions with the concurrent cycle) before it wasted a second
GPU slot — see RL_LOG 08-23 06:1x. Prior banner below.

Previous entry (2026-08-23 ~05:5x UTC (**TEACHER-FORK A/B READ: CPG
library WALKS as an AMP style source but isn't yet better than the
scripted teacher.** `cw-cpg-teacherfork-ab-cpgv1` (Next item 3, single
lever vs the PASSED `cw-amp-m2-bcinit-sec5-style05`: `--amp-motion-lib`
teacher_v2.npz -> cpg_v1.npz, same BC-clone init/reward/2M budget)
VERDICTED INFORMATIVE (WORSE-BUT-WALKING, the pre-registered middle
branch): DR-0 gate det+sto gait_valid 6/6, zero falls/sacrificed legs,
no crouch (height_err 1.7-19.1mm, tighter than style05's own healthy
18-31mm range), video-clean six-leg cycling both modes — the CPG
clip's obs_style distribution does NOT collapse this init, refuting
that specific worry. But det margins run ~15-20% softer than style05's
own numbers (progress_ratio med 0.99 vs 1.16, fwd dist med 0.59 vs
0.69m/15s); sto is matched on progress (0.58 vs 0.58) and slightly
better on raw distance (0.30 vs 0.23m). Answer to the track's own
adoption question: the CPG motion library is a VIABLE but not yet
SUPERIOR AMP style source on this one test — no teacher_v1/teacher_v2
swap, no joystick slip-bar recalibration off this single result (per
the item's own pre-registered caveat). A second data point (CPG-clone
init instead of BC-clone init, or matched larger budget) would be
needed before any real adoption fork; not funded this cycle — M4
composition work on the amp track has priority for GPU budget right
now. Evidence: `logs/ckpt_eval/cw_cpg_teacherfork_ab_cpgv1_gate_det/`.
Prior banner below.)

Previous entry (2026-08-23 ~05:2x UTC (**ROBUST GATE FULL PASS — closed-
loop yaw trim built + verified, all 5 panels green.** The 120-iter
robustness-refinement search (Next item 1) converged but could NOT
fix the mu0.8 turn overshoot (best-found params still read 1.33/1.35,
identical to the contextual-250 winner) -- confirming Next item 2's
prediction that this is a friction-dependent GAIN error an open-loop
parameter search structurally cannot reach. Built
`rl_move/sim/yaw_trim.py` (`update_trim`, 8/8 unit tests, pure numeric,
no sim) -- a proportional MULTIPLICATIVE trim on commanded omega from
measured-vs-commanded yaw rate over 1.0s windows, wired into
`eval_cpg_gate.py` as `--yaw-trim` (default off, bit-exact when off,
scoped to turn segments only). Re-ran the SAME robust120-winner
params with `--yaw-trim`: **overall pass=True, all 5 panels
(dr0/dr0_script2/mu1.2/mu0.8/loaded) PASS** -- mu0.8 turn ratio
1.33/1.35 -> 1.07/1.07 (inside [0.70,1.30]), every other panel's turn
tracking also tightened (dr0 1.03/1.05 -> 1.01/1.02) since the trim
corrects small biases everywhere a turn is commanded, not just the
adversarial-friction case; zero falls, zero sacrificed legs, slip/m
0.69-1.36 across all panels (well inside the 1.4-2.9 teacher band),
video-reviewed (all 5 contact sheets: clean six-leg cycling, upright,
no pathologies). Exported
`rl_move/sim/policies/cpg_controller_robust120_yawtrim.json`
(first artifact export on this track). SKILLS.md row added.
**This is the FIRST FULL PASS of the track's behavioral DONE gate**
(zero falls, no sacrificed legs, correct headings, both-direction
turns, stops/restarts, slip inside the teacher band, DR-0 + friction +
servo-profile sweep, video-reviewed, saved parameter artifact) -- but
the gate's own text also asks for a web-UI / teacher-library-generator
loader for the artifact schema, which does NOT exist yet (confirmed,
grep-checked), and the track's own Next item 3 (a controlled A/B
adoption fork vs the current teacher) is unstarted. Track is NOT
declared closed on this evidence alone -- champions/gates are
append-only and adoption needs its own measured fork, same discipline
as the joystick track's stotight45 promotion-pending-integration
precedent. Evidence: `logs/cpg_gate/robust120-winner{,-yawtrim}/`,
`logs/paper_cpg_search/paper-cpg-robust120-20260823.{json,log}`.
Prior banner below.

Previous entry (2026-08-23 ~04:1x UTC (gate harness built + first
held-out gate run, see "Gate results 08-23". Track created same day:
**TRACK CREATED by operator direction:
make the Berkeley/Levine CPG result a third first-class path.** This
track is not PPO and should not be converted into seed sweeps. It
owns deterministic/black-box search over low-dimensional gait
parameters, direct behavioral scoring, and any controlled adoption of
the resulting gait as a controller or teacher source.)

## Why this is working better

The CPG search removes the two failure modes that keep hurting the RL
lines: the controller is a small interpretable parameter vector, and
the score is the eval. There is no hidden learned reward for the
policy to exploit, no stochastic policy noise floor, and no long run
where training reward rises while behavior gets worse. Each trial is a
real MuJoCo walk/turn attempt scored on commanded progress,
cross-track error, loaded-foot slip, falls, tilt/height, and effort.

## Current best

- Straight-50 winner verified real: tetrapod, period 2.0,
  swing_frac 0.18494, lift 0.035 m, cmd_tau 0.65225,
  workspace_margin 0.92865; progress_frac 0.9028, slip/m 0.5369,
  zero falls.
- Contextual-250 winner: tetrapod, period 2.0, swing_frac 0.2961,
  lift 0.0299 m, cmd_tau 0.1, workspace_margin 0.7759.
  Score 0.166 vs the straight winner's 0.033 under the fixed
  contextual scorer. Across 5 headings + 2 turns: heading progress
  0.84-0.89, cross <=0.043, slip roughly 0.56-0.75, yaw tracking
  0.993/1.012 of target, zero falls/terminations.

## Known fixes already made

- `sim_gait_compat.SE2FootGait` keeps the knee-frame boundary correct
  for MuJoCo.
- `paper_cpg_search` now supports replay and warm-started GP search.
- The contextual scorer integrates unwrapped yaw, so turns beyond pi
  no longer look sign-inverted.
- Pure-turn slip is normalized by progress plus a yaw foot-arc term
  instead of dividing by near-zero translation.

## DONE gate

The track is green when a CPG controller passes a held-out contextual
session gate with zero falls, no sacrificed legs, correct headings,
turns in both directions, stops/restarts, and slip better than or at
least competitive with the current teacher band. Required panels:
DR-0 plus a modest own-DR/friction/servo-profile sweep, 60 s command
scripts, video review, and a saved parameter artifact that the web UI
and teacher-library generator can load.

## Gate results 08-23 (`rl_move/sim/eval_cpg_gate.py`, built this cycle)

Held-out 60 s scripted session (seeded held-out headings +/-87/-49/+88/
+57/-20 deg, turns both ways, 3 stops/restarts), panels dr0 /
dr0-script2 / mu1.2 / mu0.8 / loaded-servo. Contextual-250 winner:
**DR-0 PASS decisively** (heading progress mean 0.899, turns yaw_along
1.03/1.05, stop drift <=3 mm, slip/m 0.70, zero falls, 6/6 legs
cycling duty ~0.70, roll/pitch peaks <0.6 deg; video reviewed, no
pathologies). Robustness 3/4: script2 0.899 PASS, mu1.2 PASS, loaded
PASS (0.923, best), **mu0.8 FAIL — open-loop turn overshoot 1.33/1.35
vs the pre-registered [0.70,1.30] band**, plus contact chatter (swing
counts 39-55 vs ~30). Everything else at mu0.8 passes (prog 0.827,
slip 1.35, zero falls). Artifact NOT exported (gate is strict; no
post-hoc threshold loosening). Verdict + videos:
`logs/cpg_gate/contextual250-winner/`. Root cause: the controller is
open-loop, so yaw-per-stride scales with ground friction; the search
never priced friction variation.

**UPDATE 08-23 ~05:2x: 120-iter robustness search done, still FAILS
mu0.8 identically (1.33/1.35, `logs/cpg_gate/robust120-winner/`,
confirms the root cause is a search-unreachable gain error) —
`--yaw-trim` closed-loop fix built and verified: SAME params,
`--robust --yaw-trim`, ALL 5 PANELS PASS (mu0.8 turn ratio ->
1.07/1.07; every panel's turn tracking tightened; zero falls/
sacrificed legs; slip/m 0.69-1.36). Artifact exported:
`rl_move/sim/policies/cpg_controller_robust120_yawtrim.json`. See
banner above for full detail. This closes Next items 1 and 2 below
(kept for the record).**

## Next

1. **DONE 08-23**: TRIAGED the robustness-refinement search
   `paper-cpg-robust120-20260823` (120 GP iters, warm-started from the
   contextual-250 winner) — best-found params still FAIL mu0.8
   identically to the contextual-250 winner (1.33/1.35): confirms the
   defect is not reachable by more open-loop search.
2. **DONE 08-23**: closed-loop yaw trim
   (`rl_move/sim/yaw_trim.py` + `eval_cpg_gate.py --yaw-trim`) built,
   unit-tested (8/8), and verified to fix mu0.8 without regressing any
   other panel — full robust-gate PASS, artifact exported. Not yet
   wired into the web UI (no loader exists for `cpg_controller_*.json`
   anywhere in the repo — grep-confirmed 08-23) or into
   `linux_control/se2_foot_gait.py`/`drive_controller.py` for a real
   hardware path (sim-only fix so far; hardware adoption is an
   [operator] physical-robot item per the standing rules, not blocked
   on anything code-side).
3. **DONE 08-23**: `rl_move/sim/motion_library/cpg_v1.npz` built
   (`build_motion_library.py --controller se2cpg`, new/default-off/
   bit-exact-when-tripod, 3 tests) from the yaw-trim-verified
   `robust120_yawtrim` params, same 15-family command suite as
   `teacher_v1`/`teacher_v2` — 45/45 clips accepted, slip/m 0.27-2.17.
   `cw-cpg-teacherfork-ab-cpgv1` (respec of the PASSED
   `cw-amp-m2-bcinit-sec5-style05`, single lever:
   `--amp-motion-lib` swapped) VERDICTED INFORMATIVE
   (WORSE-BUT-WALKING, see banner): CPG library sustains real walking
   as an AMP style source but det margins run ~15-20% softer than
   teacher_v2 (sto matched/better). ANSWER: viable, not yet superior;
   no teacher swap, no bar recalibration off one result.
   **STALE TEXT CORRECTED 09-03 ~13:2x: the "second data point ...
   not funded this cycle" sentence above is LEFTOVER 08-23 text that
   was never trimmed after the question closed — see the file's TOP
   banner (current state), which shows the matched/larger-budget
   second (and third) data point ALREADY RUN AND READ 08-23/08-24
   (`cw-cpg-ab6m-cpglib`/`-teachlib` @6M, `cw-cpg-teacherfork-ab-
   cpgv1-acq1b`/`-style05-budget2` @8M, `cw-cpg-teacherfork-ab8m-
   cpgv1r`/`-teacherr` @8M — three independent matched pairs, cpg_v1
   co-equal-or-better every time). ADOPTION DECISION RECORDED, cpg
   gate GREEN. Do not re-fund this cell again — a 09-03 cycle did
   exactly that on nothing but this stale bullet (missed the top
   banner) and burned a launch on `cw-cpg-teacherfork-ab-cpgv1-b8m`,
   VERDICTED FAILED (infra: `cpg_v1.npz` predates the 09-02/09-03
   joint-frame-v2 migration and no longer loads --
   `amp_discriminator.MotionLibrary` now hard-requires the
   `joint_frame`/`joint_contract` stamp). If a FUTURE arm has a real
   NEW reason to use `cpg_v1.npz` on current code, it must first be
   rebuilt: `build_motion_library.py --controller se2cpg
   --cpg-params-from rl_move/sim/policies/
   cpg_controller_robust120_yawtrim.json` (regenerates with current
   stamping) — filed as unfunded maintenance, nothing currently
   needs it since the adoption question is closed.**
4. **DONE 08-23**: a loader for `cpg_controller_*.json` in the web UI,
   per the gate's own text. `linux_control/cpg_controller_loader.py`
   (10/10 tests, pure file I/O, no hardware) parses/validates the
   artifact into `SE2FootGait(**gait_kw)`; wired additively into
   `DriveController` as gait id 6 ("SE2 CPG (loaded)") plus new
   `CPGLIST`/`CPGLOAD <name>` commands (swap refused until a
   controller is loaded, refused while walking — same discipline as
   every other gait swap; verified end-to-end via `dry_run=True`, zero
   hardware contact) and a small picker in `linux_control/webui`
   (gait select + controller dropdown showing gate pass/slip + Load
   button, both reusing the existing generic `/cmd` channel — no new
   HTTP route needed). Copied `cpg_controller_robust120_yawtrim.json`
   into `linux_control/policies/` (the deployable location) so it's
   discoverable there too, not just in `rl_move/sim/policies`. This
   was the last named gap in the track's own DONE-gate text. Actually
   driving the physical robot on it is still an [operator] hardware
   decision (no HTTP/SSH/firmware touched by this change). No further
   named Next items remain on this track besides a real A/B adoption
   decision (a second data point beyond the one INFORMATIVE
   teacherfork-ab-cpgv1 read above) whenever amp/joystick GPU budget
   allows it.
