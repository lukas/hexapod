# todaypolicy - working policy bundle for today's demo

Last updated: 2026-09-06 ~21:1x (anchorsoft1x/2x canary gates both
CANARY PASS -- softer anchor dose does NOT reproduce arm A's collapse
and shows a real, consistent progress gain over Candidate B in 3/4
modes; both advanced to the full 8M ACQ budget, VERIFIED RUNNING).

## 09-06 ~21:1x — anchorsoft1x/2x CANARY PASS (both dose points); advanced to 8M ACQ

Registered on-pod eval results for both arms of the anchor-dose
bracket (launched ~20:3x below) landed this cycle. Read together, not
independently (matched bracket per the gate's own instruction):

- **`cw-robotwalk-stride-20260906-anchorsoft1x`** (bc_anchor_coef=1.0):
  fresh own-pod gate (n=24, DR-0, det+sto x walk/walk_startjitter) —
  0 falls, 0 sacrificed legs, gait_valid 24/24, no duty-lock
  fingerprint (`duty_cycle` ~0.56-0.62 per leg every episode, nothing
  pinned <0.08 or >0.92 — the exact fingerprint that destroyed arm A
  at coef=0.0 is absent), slip/m 2.07-2.32 (under the 2.9 cap).
  Progress vs Candidate B's own same-4-mode baseline (walk/det 0.314,
  walk/sto 0.180, walk_startjitter/det 0.234, walk_startjitter/sto
  0.296 m/12s, recomputed fresh from `cw_walkteach_scripted_allhead_
  acq12m_gate/report.json`): this arm reads 0.343(+9%), 0.220(+22%),
  0.224(-4%), 0.326(+10%) — a consistent same-direction uptick in 3/4
  modes, not a noise-level wiggle (compare the ~4-8% wiggles called
  "noise" elsewhere on this board — these are larger AND
  one-directional). **CANARY PASS.**
- **`cw-robotwalk-stride-20260906-anchorsoft2x`** (bc_anchor_coef=1.5):
  same fingerprint, essentially indistinguishable from its coef=1.0
  sibling — 0 falls, gait_valid 24/24, no duty-lock, slip/m 2.09-2.37,
  progress 0.354(+13%), 0.202(+12%), 0.232(-1%), 0.342(+16%).
  **CANARY PASS.**

The 1.0-vs-1.5 dose difference does not resolve at canary scale (both
land in the same ballpark, within measurement noise of each other) —
not surprising for a 2M-step read. Per the gate's own pre-registered
resolution (PASS-worth-an-8M-ACQ), **launched both lineages to the
full 8M ACQ budget**, each warmed from its OWN 2M canary checkpoint
(not restarting from Candidate B): `cw-robotwalk-stride-20260906-
anchorsoft1x-acq8m` (VERIFIED RUNNING train-7, W&B `xswk9620`'s
successor) and `-anchorsoft2x-acq8m` (VERIFIED RUNNING train-1, W&B
`jymcz68k` — ledger briefly showed a stale `INTENT`/duplicate-name
`REFUSED` pair from the launcher's own two-phase write racing this
command's background execution; the actual trainer process and W&B
`state=running` with steps climbing off the warm-start confirm it is
genuinely alive, not a phantom). Gate (acquisition, both arms,
matched pair): PASS needs 0 falls, gait_valid>=22/24, slip/m<=2.9, and
det h000 prog_m measurably above (not another ~5% wiggle) each arm's
own canary reading (0.343 / 0.354) and above Candidate B's 0.31-0.33
band. FAIL-PLATEAU if progress sits flat at the canary's own level
with more budget (closes the anchor-dose axis at full budget, next
lever is the hypothesis's own named alternative — faster motion
source / cadence-CPG harvest). FAIL-LATE-COLLAPSE if duty-lock/falls/
slip degrade with more steps despite the clean canary (implicates the
log-std final anneal target or extended over-optimization of the
loadslip/sway gates at longer budget, not anchor dose itself). No code
changed (cfg-only respec of an already-proven mechanism family,
`test_task_semantics.py -k "anchor or footslip"` re-confirmed 6/6
green this cycle). `CYCLE_WORKED` touched (2 verdicts + 2 launches).

Evidence: `ops.sh entry cw-robotwalk-stride-20260906-anchorsoft{1x,
2x}`, `logs/ckpt_eval/cw_robotwalk_stride_20260906_anchorsoft{1x,2x}
_gate/report.json`, `logs/ckpt_eval/cw_walkteach_scripted_allhead_
acq12m_gate/report.json` (Candidate B baseline recomputed fresh
per-mode), W&B `xswk9620`/`0q2s6rbo` (canaries), RL_LOG 09-06 ~21:1x.

## 09-06 ~20:3x — refill (no completion assigned; capacity found 10 free GPU slots, backlog empty): launched the stride arm's own named repair, a 2-point anchor-dose bracket

Full board re-checked fresh (all 7 STATUS docs): walkcurr's live axes
are the in-flight `footslip-c1-lowdose-{s0,s1}` dose-scale probe
(another cycle's assignment, left alone) and item(1) crutch-ON
(DIG-IN owned, awaiting a deep-model bisection-axis pick); assistfade's
rung-3 grid is 3/4 closed with the sole open thread
(`s0-longbudget`) a pre-existing DIG-IN also not mine to resolve;
joystick/amp/cpg confirmed DONE/maintenance-only; standwalk confirmed
blocked pending fresh design thinking (item 3's own text: "no
agent-doable next step identified... beyond flagging the axis needs
fresh thinking"). That left todaypolicy's own `robotwalk-smooth-20260906`
campaign as the one track with a concrete, not-yet-attempted,
already-licensed next step: arm A (`cw-robotwalk-stride-20260906`,
`train.bc_anchor_coef` 3.0->0.0) ACQ FAILed at 04:1x with a rigid
TRIPOD LOCK (legs 1/3/5 permanently planted at duty=1.0, near-zero
travel, 4/24 falls) -- but that FAIL's own verdict text explicitly
names the untried repair: **"a SOFTER anchor-reduction (partial coef,
not exactly 0)... not a repeat of this exact ablation."** No cycle had
launched that repair yet (checked `experiments.json` + RL_LOG for any
"stride" follow-up -- none).

**Launched the dose bracket** (respec of `cw-robotwalk-stride-20260906`,
warm from the SAME Candidate B checkpoint as arm A -- never from arm
A's own destroyed end, since `--from` clones its already-baked
`--init-from` without adding `--init-from-source`): single lever
`train.bc_anchor_coef` at two points bracketing the 0.0-3.0 span,
everything else (log-std reopen/anneal, mesh/100Hz, 0.08 m/s fixed
command, safety limits) byte-identical to the failed arm, 2M-step
CANARY phase (mechanism-health only -- do not spend the full 8M ACQ
budget on a second dose point until at least one reads clean):

- `cw-robotwalk-stride-20260906-anchorsoft1x` (coef=1.0, 1/3 of
  Candidate B's full 3.0) -- VERIFIED RUNNING hexapod-mjx-train-7
  (W&B `xswk9620`), finished its 2M budget within-cycle. Reward
  quarters `[81.0, 149.4, 277.7, 480.7]` -- clean monotonic RISE, a
  qualitatively different shape from arm A's rise-then-collapse
  (`[168.7, 398.9, 381.7, 171.0]`, ending at -135). Encouraging but
  NOT a verdict -- no harness gate report yet, own-pod eval kicked
  (`ops.sh podeval`, backgrounded) + registered via `evalpending`.
- `cw-robotwalk-stride-20260906-anchorsoft2x` (coef=1.5, half of
  Candidate B's full 3.0) -- VERIFIED RUNNING hexapod-mjx-train-1
  (W&B `0q2s6rbo`), also finished within-cycle. Reward quarters
  `[80.6, 144.1, 268.1, 465.3]` -- same clean-rise shape as its
  sibling. Same status: eval kicked + registered, unverdicted.

Gate (canary, both arms, pre-registered): PASS-worth-an-8M-ACQ needs
no chronic duty-lock fingerprint + 0 falls + slip/m<=2.9 + det h000
prog_m at/above Candidate B's 0.31-0.33 m/12s band on a fresh own-pod
cmdsuite/joygate read (not yet landed for either). FAIL-STILL-COLLAPSES
(same tripod-lock/fall pattern even with the anchor partially restored)
would point at the log-std reopening as an unindicted confound, not
anchor dose. FAIL-NO-GAIN on BOTH (clean/safe gait but progress still
flat at Candidate B's exact band) closes the anchor-dose axis for
stride entirely and hands the lever to the hypothesis's own named
alternative -- a faster motion source / cadence-CPG harvest -- not a
3rd dose point. Next reader: read both `report.json`s together, do not
verdict one without the other (they're a matched bracket, not
independent seeds). No code changed this cycle (cfg-only respec of an
already-proven mechanism family -- bc_anchor_coef dose, not a new
mechanism -- so no new semantics-bank precondition applies).
`CYCLE_WORKED` touched (2 launches landed).

Evidence: `ops.sh entry cw-robotwalk-stride-20260906`, `ops.sh review
cw-robotwalk-stride-20260906-anchorsoft{1x,2x}`, W&B `xswk9620`/
`0q2s6rbo`, RL_LOG 09-06 20:3x.

## 09-06 ~17:3x — course_income_semantics recalibration CLOSED; does NOT explain the arcaware regression (research note, no operator action needed)

The ~16:1x entry below named "the already-deferred
`k_walk_course_income` window/deadband/sigma dose audit + plant-
geometry recalibration (`OPERATOR_QUESTIONS.md` 2026-09-02 entry)"
as the precondition before another turn-income training attempt.
Did that audit this cycle: `test_course_income_semantics.py`'s 2
stale failures (arc-moderate ratio/angle_f, overdrive total-reward)
root-caused and closed (14/14 green) -- both were genuine 08-29-vs-
09-02-physics calibration drift, not mechanism bugs (full writeup:
`OPERATOR_QUESTIONS.md` 2026-09-06 ~17:3x). **Decisive extra check:**
swept the test's synthetic turn rate 18/36/60/120 deg/s -- at 18
deg/s (matching production's real `goal.walk_yaw_max_rad_s=0.30
rad/s` envelope) the mechanism reads income ratio 0.982, angle_f
mean 0.9996 (near-perfect); it only degrades at 60+ deg/s, 3-4x
faster than any real joystick command ever asks for. **This means
the recalibration precondition is now satisfied, but it does NOT
explain `-arcaware`'s regression** (`course_err_1s_med` 8.55->11.93
deg at production rates, where this mechanism is already clean) --
the real bug for that lineage is still open. Do NOT launch a 3rd
same-mechanism turn-income training arm assuming this audit fixed
the underlying issue; the next toucher should look elsewhere first
(candidates: the eval-side `windowed_1s` course_err metric itself, a
training-time PPO-convergence issue at the operating point, or the
per-episode command generator at production rates -- none of which
this audit touches). Evidence: `rl_move/tests/
test_course_income_semantics.py` diff, `OPERATOR_QUESTIONS.md`
2026-09-06 ~17:3x.

## 09-06 ~16:1x — arcaware VERDICTED: FAIL - MISALIGNMENT (2nd confirmation, sway-chord fix ruled out as sole cause)

The ~14:5x gate reads (below) had all landed on-pod (train-0) but were
unsynced/unverdicted at cycle start; pulled all 4 artifact dirs to the
controller and read them against this run's own pre-registered gate
text. **Decisive number: `course_err_1s_med` got WORSE again** — 8.55°
(parent, pre-arc-aware) -> 11.93° with the arc-aware fix ON, actually
past the prior misaligned continuation's own 10.2° (`-cont8m-resume1`,
already-verdicted FAIL-MISALIGNMENT without the fix). Reward is still
rising every quarter (343.8/1120.8/1920.9/2457.9, no plateau) with no
exploit signature (0 falls, 0 sacrificed legs, gait_valid 24/24 on the
DR-0 gate) — this is the run's own literally pre-registered
FAIL/misaligned branch ("would mean the sway-chord artifact was not
the (or not the only) cause and the deadband/sigma dose itself needs
the deferred plant recalibration first"), now confirmed a SECOND time
on an independent fix attempt. Other clauses: (a) walk retention PASS
(24/24 gait_valid all 4 modes, 0 falls); (c) tip wz_err_med ~flat
(0.082/0.080/0.121/0.116, median ~0.099 vs parent's 0.108/0.100); (d)
straight-fwd cmd_suite prog_m 0.234-0.247 m/12s, misses the 0.29 bar
(slip/m 2.73-2.89, at/under the 2.9 cap). `eval_yaw`'s own absolute
gate also independently reads FAIL (turn_wz_err_med 0.155 > 0.1).
Contact-sheet video confirms clean six-leg gait (no drag/paddle, 0
falls) but the on-screen COM trace visibly curls into a loop instead
of holding a course — a course-tracking defect, not a gait pathology,
matching the metric. **Conclusion: the arc-aware chord-projection fix
is not the (or not the only) bug.** Do not attempt a third
same-recipe continuation or another reward-shape tweak on this exact
lever — the next move is the already-deferred `k_walk_course_income`
window/deadband/sigma dose audit + plant-geometry recalibration
(`OPERATOR_QUESTIONS.md` 2026-09-02 entry) before another turn-income
attempt on this lineage. Retained value: this lineage still proves
the turn-income mechanism does not destabilize walking (clean gait,
zero falls throughout 3 generations of this experiment) — useful
evidence, just not yet a calibrated turn-tracking result. No export.
Evidence: `logs/ckpt_eval/cw_robotwalk_turns_20260906_arcaware_
{gate,joygate_freshcmp,yaw}/*`, RL_LOG 09-06 16:12, W&B `nr57brps`.

## 09-06 ~14:5x — arcaware finished training, gate reads kicked (no verdict yet)

`cw-robotwalk-turns-20260906-arcaware` (the arc-aware sway fix arm
from ~13:4x below) finished its 8M steps (`state=finished`,
`ep_rew_mean` 2539.7, reward quarters 343.8/1120.8/1920.9/2457.9 —
still rising every quarter) but none of its 4 pre-registered gate
reads had been started (`--defer-final-artifacts`, no live trainer,
checkpoint present on-pod only, ledger still `status=FINISHED` with
no verdict/report). Launched all 4 directly on its own pod
(`hexapod-mjx-train-0`, idle, checkpoint already local), reusing the
exact `--cfg-set`/envelope values from this run's own training
command (own-DR=0.0, speed 0.08 fixed, wz_max 0.3, arc-aware flag on)
so nothing changes obs width or command distribution versus what was
trained: (a) standard DR-0 gate (`eval_checkpoint`, matches the
prestage the watcher would have run) -> `..._arcaware_gate/`; (b) the
run's own pre-registered `eval_joystick_gate` stress_mix fresh
comparison (60s episodes, own-DR=0.0, seed-base 90000) -> `
..._arcaware_joygate_freshcmp/gate_verdict.json` — this is THE
number that answers the arc-aware hypothesis (`course_err_1s_med`
vs the parent's 8.55deg reading and the 5.17deg Candidate-B bar); (c)
`eval_cmd_suite` (12s holds, default 9-command panel, matching the
parent's own fresh-read params) -> `..._arcaware_yaw/
cmdsuite_verdict.json`; (d) `eval_yaw` (speed 0.08, wz_max 0.3,
matching the parent's own envelope) -> `..._arcaware_yaw/
yaw_verdict.json` — this is the tip-turn wz_err_med regression check
(bar: no worse than the parent's 0.108/0.100). All 4 confirmed
running via `ps aux` on-pod (first `eval_yaw`/`eval_joystick_gate`
attempts silently no-op'd — `/usr/local/bin/python -m rl_move...`
inside a chained `&&`/`&` bash -c lost the uv venv's module path;
fixed by giving each its own single `kubectl exec` invocation).
Registered all 4 via `ops.sh evalpending add` rather than polling
(joygate's 24x60s episodes alone is ~20-40 min). **Next reader:
verdict against this run's own pre-registered gate text (in the
ledger) once these land — do not re-launch, do not re-derive the
cfg-set list (copy it from the training command in `experiments.json`
if extending further).** Evidence: `ops.sh entry
cw-robotwalk-turns-20260906-arcaware`, `rl_move/orchestrator/
pending_evals.json`.

## 09-06 ~13:4x — arc-aware sway FIX built, bank-proved, relaunched (closes step (a), executes step (c) of the ~13:0x hand-off)

The ~13:0x audit below named 3 concrete next steps: (a) design +
bank-test an arc-aware course reference; (b) re-measure the separate
moderate_arc/overdrive margin debts against it; (c) relaunch from
`cw-robotwalk-turns-20260906` (the clean 8M checkpoint, not the
misaligned `-cont8m-resume1`). Did (a) and (c) this cycle; (b) is
explicitly OUT of scope (a different, already-deferred plant-geometry
recalibration question per OPERATOR_QUESTIONS 2026-09-02 ~23:1x/23:5x
— conflating it would risk masking that debt or locking in an
unmeasured number).

**Root cause, restated precisely:** `reward.k_walk_excess_sway`
projects every sample in its trailing window against ONE global chord
(the window's own start->end command displacement). That projection
is exact for a straight/near-straight command but an ARC bows away
from its own chord even when perfectly tracked — the tight-turn
semantics-bank cell (`test_wz_arc_tight_turn_gracefully_discounted_
not_exploited`) decomposes to `reward_walk_course_income=+165` vs
`reward_walk_excess_sway=-1177`, a 7x mismatch, purely from this
artifact (course_income is immune: it only compares window start/end
points, which coincide for a perfectly-tracked path regardless of
curvature — sway is not, because it compares every INTERMEDIATE
sample to the same fixed chord).

**Fix (`rl_move/sim/walk_task.py`, new key `reward.walk_sway_arc_aware`,
default 0.0 = legacy chord math, bit-exact when off):** when armed,
each sample's deviation is measured against a "shadow" reference path
that starts at the body's own window-start position and replays the
SAME per-tick reference displacement the mechanism already
accumulates (the `_walk_course_win_cum` columns already stored in
`whist` for `k_walk_course_income` — no new state needed), projected
onto the LOCAL per-tick tangent (not the one global chord) so an
along-track completion lag — already priced by `k_walk_course_income`'s
own speed_factor — never leaks into this lateral-only charge.
Bit-exact-off verified TWO ways in `test_course_income_semantics.py`
(not just the trivial straight-command case, where legacy chord and
local tangent are identical by construction): the existing 8-drive
base-STACK bank produces byte-identical numbers with the flag on vs
off (no drive in that stack curves the REFERENCE, only the robot's
own response to it), and a NEW dedicated test locks the exact
pre-fix regression numbers on a genuinely curving command
(`test_arc_aware_default_off_matches_legacy_chord_on_a_curving_cmd`).

**Measured fix (tight-turn cell, same semantics-bank fixture):**
income unchanged (164.9, confirms the fix is isolated to the sway
term); sway -1177 -> -198; total episode reward 138.8 -> 1117.2 —
comfortably clears `test_wz_arc_tight_turn_gracefully_discounted_
not_exploited`'s own `r_tight > r_park + 500` bar (was failing by
~450 before the fix). Full bank re-run: 12/14 green (was 9/12 before
adding 2 new tests) — the 2 remaining reds are `test_wz_arc_moderate_
turn_earns_near_full_income` and `test_overdrive_clean_completion_
legitimately_wins`, BOTH pre-existing, both confirmed by the ~13:0x
audit as the separate plant-geometry recalibration debt, untouched by
this fix (their income numbers are bit-identical before/after —
verified this cycle). 2 new tests added, both green.

**Relaunched:** `cw-robotwalk-turns-20260906-arcaware` (respec of the
clean 8M `cw-robotwalk-turns-20260906` checkpoint, NOT the misaligned
`-cont8m-resume1` continuation, `+reward.walk_sway_arc_aware=1.0` the
ONLY change, 8M steps, VERIFIED RUNNING train-0). Pre-registered gate:
PASS if DR-0 gait_valid/falls hold, joygate `course_err_1s_med`
improves vs this run's own 8M parent's 8.55deg reading (toward/under
the 5.17deg Candidate-B bar), tip wz_err_med does not regress vs
0.108/0.100, straight prog_m stays >=0.29m/12s. FAIL/still-misaligned
if `course_err_1s_med` is flat-or-worse with reward still rising
(would mean the chord-vs-arc sway artifact was not the sole cause and
the deadband/sigma dose needs the deferred plant recalibration
first). Full hypothesis/gate text in the ledger entry itself
(`launch_run.py status` / `experiments.json`).

Snapshot: committed as part of a concurrent cycle's own snapshot
commit (confirmed HEAD==origin/main, `caef1a54`) — no separate push
needed. Evidence: `rl_move/tests/test_course_income_semantics.py`
(diff + new tests), `rl_move/sim/walk_task.py` (`walk_sway_arc_aware`
block), W&B run for `cw-robotwalk-turns-20260906-arcaware` (see
ledger for id once checked up).

## CAMPAIGN robotwalk-smooth-20260906 (operator order fb_20260906T030030_28f422, 09-06) — LAUNCHED

Lukas's explicit request (via Codex MCP note attached to RUN
cw-walkteach-scripted-allhead-acq12m): two bounded PPO arms to improve
the real hexapod's shuffling/rocking (stride) and joystick turn
response, then automatic RobotLab physical trials of promising
completed checkpoints by the LOCAL Codex watchdog (cloud never
operates the robot or enqueues Lab jobs). This note reopens
todaypolicy delivery for exactly these two arms and supersedes the
older no-new-PPO-until-transport-replay note for them.

**Campaign marker: `robotwalk-smooth-20260906`. Exact run names (for
the local completion handoff):**

- `cw-robotwalk-stride-20260906` — 8M, warm from Candidate B, sole
  change `train.bc_anchor_coef=0.0` (+ log-std reopened −3.0→−4.0):
  tests the record's #1 teacher-ceiling suspect (walk BC coef=1). Gate:
  det h000 prog_m ≥0.40 m/12s (Candidate B baseline 0.3248), zero
  falls, slip/m ≤2.9, no heading below 0.29, 6/6 legs. VERIFIED
  RUNNING 09-06 on hexapod-mjx-train-7.
- `cw-robotwalk-turns-20260906` — 8M, warm from Candidate B, yaw
  exposure (`walk_yaw_zero_frac` 1.0→0.5, `turn_in_place_frac` 0.30)
  + bank-proven raw turn-income stack (k_walk_yaw et al.;
  `walk_kernel_yaw_ema` OFF — bank re-run 09-06 on mesh: raw kernel
  clause green, EMA drift clause fails on mesh) +
  `bc_anchor_walk_turn_skip=1` (anchor kept on straight/combined
  ticks). Gate: tip both signs wz_err_med <0.076, combined-cell
  improvement vs Candidate B, straight prog_m ≥0.29, joygate
  course_err_1s_med ≤5.17°, standing-still smoothness = FAIL.
  VERIFIED RUNNING 09-06 on hexapod-mjx-train-1.

**09-06 ~04:1x verdict: `cw-robotwalk-stride-20260906` ACQ FAIL — anchor-
ceiling hypothesis REFUTED, and worse.** Turning `train.bc_anchor_coef`
exactly to 0.0 did not free the policy to cover more distance; it
destroyed the gait. `gait_valid` 0/24 (every one of 4 modes 0/6): a
rigid TRIPOD LOCK, not a stride — legs [1,3,5] pinned at `duty_cycle`
1.0 (never lift) in literally every episode, legs [0,4] near-zero duty
(0.0-0.06), leg 2 alone partially participating (0.03-0.32).
`forward_dist_m` collapses to 0.001-0.036 m/20s (target was >=0.40
m/12s; Candidate B's own baseline is 0.31-0.33 m/12s) — not merely
short of target, essentially zero net travel. `slip_per_m` 16-30 (vs
the <=2.9 gate bound). 4/24 episodes show real safety terminations
(over_current). Video (`walk_det_0`, `walk_det_4`) confirms a static
quivering body, checkerboard grid does not shift frame-to-frame.
Training reward matches the collapse rather than diverging (quarters
168.7->398.9->381.7->171.0, ending negative at -135) — NOT the 08-21
rising-reward/bad-eval case; this is a genuine FAIL both by reward and
by eval. Per the gate's own instruction, no further
`train.bc_anchor_coef=0.0` clone should be launched from this parent;
if the stride-ceiling question is revisited it needs either a SOFTER
anchor reduction (partial coef) or the hypothesis's own named
alternative (a faster motion source/cadence-CPG harvest), not a repeat
of this exact ablation. No export — gate not met. `cw-robotwalk-
turns-20260906` (the campaign's 2nd arm, yaw/turn-income) finished
around the same time but was NOT assigned to this cycle — its gate
eval was found still computing on `hexapod-mjx-train-1` (shared with
this arm's own eval) and is left for whichever cycle picks it up next;
do not assume its outcome from this one (different lever, same
parent). Evidence: `logs/ckpt_eval/cw_robotwalk_stride_20260906_gate/
report.json`, W&B `catovl0h`.

**09-06 ~04:4x verdict: `cw-robotwalk-turns-20260906` ACQ CONTINUE —
gate not yet met but mechanism healthy, reward still rising.**
Unlike its sibling stride arm, this one did NOT break the walk:
prestaged DR-0 gate gait_valid 6/6 all 4 modes, ZERO falls/terms, no
sacrificed legs. Ran the run's own literal extra clauses fresh this
cycle (not in the standard prestage): `eval_joystick_gate` stress_mix
PASSES its own internal checks (0 falls, gait_valid_frac 1.0, slip_med
2.094, dir_err_med 28.7° <=40 allow) but **course_err_1s_med=8.55° is
WORSE than the gate's cited Candidate-B bar (5.17°) — criterion (c)
FAILS outright.** Matched fresh `eval_cmd_suite`/`eval_yaw` runs on
THIS checkpoint AND a freshly re-evaluated Candidate B on identical
cells (Candidate B's own historical verdict numbers turned out to be
unreproducible today — see `OPERATOR_QUESTIONS.md`
q_20260906T0448Z, resolved assume-and-go: fresh same-day numbers are
the real comparator) show: tip-left/tip-right wz_err_med 0.108/0.100
here vs 0.124/0.155 fresh-Candidate-B — a modest edge, not a clear
win, neither clears the literal <0.076 bar; but cmd_suite slip/m
1.49-1.94 here vs 2.70-3.74 fresh-Candidate-B across every
translating cell — walking quality genuinely improved, roughly half
the slip. Reward is still climbing every quarter (337.3->1135.9->
1916.5->2417.5, +501 in the last quarter, no plateau) with no
exploit signature — the 08-21 "keep going" case, not a stop-and-
realign one. Queued `cw-robotwalk-turns-20260906-cont8m` (+8M,
init-from-source, backlog) to see whether more budget closes the
course_err/tip-wz_err gap. No export yet — gate not met. Evidence:
`logs/ckpt_eval/cw_robotwalk_turns_20260906_gate/report.json`,
`logs/ckpt_eval/cw_robotwalk_turns_20260906_joygate_freshcmp/
gate_verdict.json`, `logs/ckpt_eval/cw_robotwalk_turns_20260906_yaw/`,
`logs/ckpt_eval/cw_walkteach_scripted_allhead_acq12m_yaw_freshcmp/`,
W&B `ms5xltim`.

**09-06 ~06:5x verdict: `cw-robotwalk-turns-20260906-cont8m-resume1` ACQ FAIL -
MISALIGNMENT (closes the deferred final assessment).** Recovery run
completed the SAME planned +8M (16M cumulative). Walk retention
perfect: DR-0 gate gait_valid 24/24 all 4 modes, 0 falls, 0
sacrificed legs. Fresh matched eval_cmd_suite/eval_yaw/joygate on
identical cells to the 8M read: tip-turn wz_err_med improved modestly
(0.108/0.100 -> 0.078/0.085, still misses the absolute <0.076 bar);
yaw aggregate turn_wz_err_med ~flat (0.1489->0.1454); arc-max
tracking unchanged. **The decisive number went the WRONG way**:
joygate stress_mix `course_err_1s_med` 8.55deg (8M) -> 10.2deg (16M)
— worse than both the absolute 5.17deg bar AND this run's own prior
baseline, while reward kept rising every quarter (154.6->1232.8, no
plateau). Per this run's own pre-registered fallback ("flat-or-worse
on course_err with reward still rising = misalignment, audit the yaw
reward terms next"): textbook 08-21 misalignment, not a budget
ceiling. No 3rd same-recipe continuation funded. Next: audit
`k_walk_course_income`/window/deadband/sigma reward terms for why
they don't price course-holding the way `course_err_1s_med` measures
it, before any further turn-income dose. No export (gate not met).
Evidence: `logs/ckpt_eval/cw_robotwalk_turns_20260906_cont8m_resume1_
{gate,yaw,joygate_freshcmp}/`, W&B `2p93pife`, RL_LOG 09-06 06:56.

**09-06 ~13:0x — audit DONE (zero training spend), root cause found:
NOT a quick sigma/deadband dose, hand off DIG-IN.** Did the "audit
`k_walk_course_income`/deadband/sigma" ask above. (1) At the LIVE
recipe's own values (deadband=6, sigma=20deg), `angle_f` is 1.0000 at
the gate's own 5.17deg bar (inside the deadband — zero gradient at
the pass/fail line) and still 0.9782 at the run's own worse 10.2deg
reading vs 0.9919 at the better 8.55deg one — a **1.4% reward
difference between "passes" and "fails" the eval**, against a reward
whose quarters were rising ~+1000 each: the mechanism cannot express
what the eval gates on. (2) The obvious fix (tighten sigma) is
refuted by the mechanism's OWN already-banked arc invariant
(`test_wz_arc_moderate_turn_earns_near_full_income`): tightening
sigma 20->10->6 drops a legitimate 6s-period turn's income share
0.795x->0.518x->0.256x of straight-line income — the SAME knob that
would fix (1) actively breaks affordable turning. (3) Found
`test_course_income_semantics.py` is CURRENTLY 3/12 RED on
unmodified HEAD — the same 3 arc/overdrive margin tests
`OPERATOR_QUESTIONS.md` 2026-09-02 ~23:1x/~23:5x already flagged and
deferred as "genuine recalibration, not a bug," still unfixed. Ran
the deferred old-vs-new-plant recalibration check: 2/3
(`moderate_arc`, `overdrive`) DO flip PASS under the pre-09-02-fix
plant, confirming those two really are geometry-recalibration debt;
but the THIRD (`tight_arc`, turn radius 0.038m) fails under BOTH
plants and decomposes to `reward_walk_course_income`=+165 vs
`reward_walk_excess_sway`=**-1177** — the sway CHARGE alone
outweighs income 7x because it measures deviation from a STRAIGHT
CHORD while the command is a genuine tight circle; this one was
mis-filed as "recalibration," it is a real arc-vs-chord confound in
the course reference, unrelated to the plant-literal cascade.
**Conclusion: both the deadband/sigma dose AND the sway allowance
need an arc-aware course reference (compare to the integrated CURVED
command path implied by `wz_ref`, not its chord) before any further
turn-income dose — a mechanism change, not a retune.** Did not touch
`walk_task.py`/`reward.py` or bump any test threshold (would either
mask the tight-arc defect or lock in a not-yet-remeasured geometry
number); did not launch a 3rd `robotwalk-turns` arm (would reproduce
the same misalignment on the unrepaired mechanism). Full derivation +
numbers: `OPERATOR_QUESTIONS.md` 2026-09-06 ~13:0x. **Next (concrete,
for whoever next touches this): (a) design + bank-test the arc-aware
course reference; (b) re-measure `moderate_arc`/`overdrive` margins
against it; (c) THEN relaunch from `cw-robotwalk-turns-20260906`
(the 8M checkpoint, not the misaligned `-cont8m-resume1`).**
`DIG-IN: test_course_income_semantics.py / todaypolicy robotwalk-turns
reward audit — arc-vs-chord course reference confound.` No GPU spend
this entry (walkcurr's own frontier independently confirmed exhausted
this cycle — every clean composition-line ACQ_PASS source already has
a cont40m read in flight or verdicted; standwalk unchanged since
09-05; nothing else registered-track-launchable this cycle).

Baseline = Candidate B `cw-walkteach-scripted-allhead-acq12m`
(controller-side training zip sha256 `30ed068e4356d5f42caba2a427f2845a
230d7289a06467684731ec94a1f6f250`; operator-deployed actor sha256
`a813c4a692081978359042f825aaf5c4b43b58f91ffcd6db365a80d6827f4167` —
that actor artifact exists operator-side only, per the 09-05 delivery
verify). Hardware truth: RobotLab experiment
`6ac6754d4c604e7399bf1f84173ce950` (reverse+release+both arcs, 5.5°
active tilt, no fall); the earlier 98.4° post-stop "fall"
(`989e41d37d3d489598b7b3f0d4e83dab`) is DISPROVED (stale-feedback
failure, raw MCU IMU + video) — retain the stale-feedback lesson, not
a physical-fall inference. Do NOT weaken the 0.375 deg/tick cap or
safety limits; do not promote easy/half-gravity results to hardware.

**Completion contract (for whichever cycle triages each arm):**
compare to Candidate B on the SAME short forward/reverse/release/
left+right arc script (100 Hz policy; 50 Hz-writes-compatible state/
filter behavior where supported); if the arm improves its measured
behavior with no unstable/dragged-leg motion in the sim evidence,
export the controller-compatible artifact with the existing exporter
and persist exact run/checkpoint/export SHA, policy/config path,
eval/video locations, and a concise decision in the run ledger/story —
the local RobotLab watchdog discovers those terminal artifacts and
enqueues each candidate ONCE, serially. A failing arm records why and
does not ship. No review/qualification descendants; do not turn 2M
intermediate reads into new experiment families; no same-recipe seed
clones. Stand/lower remain the scripted STEP; learned hold keeps its
existing role.

## REOPENED 09-05: measured hardware-controller delivery sub-track

Operator MCP note `fb_20260905T071610_749846` reopened this track for
smooth-hardware-walking delivery work (local Codex owns transport
replay + linux_control timing; the orchestrator owns the opt-in
command-envelope candidate). See
`rl_docs/tracks/todaypolicy/hardware_delivery/STATUS.md` for the
built+tested `CommandEnvelope` governor and the 09-05 paired CPU
suite verdict (shared-mode throttling refuted; yaw-priority is a real
turn-fidelity candidate at a named −55% progress cost; bundle
`todaypolicy-mlpsf-tuck-v1` retained as primary). The 08-30 DONE
banner below still stands for the sim/controller bundle itself.

## DONE (2026-08-30): `todaypolicy-mlpsf-tuck-v1` PACKAGED, ALL TODAY BARS PASS

Fresh full-mesh regen on the controller (mesh STL assets rebuilt from
the CAD tools — `make_xtool_hex_mount_plate.py` +
`make_xtool_hex_raised_platform.py` were needed first; the gitignored
electronics-stack STLs did not exist here):
`logs/manual_drive/todaypolicy_mlpsf_tuck_v1_fullmesh/` — scripted tuck
stand → 28 s human joystick script on the exported MLP-singleframe walk
(det) → scripted tuck lower. Every TODAY bar passed: 0 terminations,
`model_variant=full_mesh` (3.494 kg), no sacrificed legs (6/6 legs
swing 32–37x, duty 0.51–0.62), course_err_1s med 2.42° / p90 6.98° /
wrong 0.0, progress_ratio 0.418 (≥0.40; 0.60 stretch not met —
teacher-ceiling), cur_max 2.64 A / cur_p95 1.886 A, video strip clean
(level body, roll peak 1.9°, no loaded-foot drag in stand/lower).
Durable copies + GO/NO-GO + browser/controller selector path:
`rl_docs/tracks/todaypolicy/bundle_mlpsf_tuck_v1/` (GO_NOGO.md,
summary/composition/transfer_manifest.json, drive.mp4). Verdict: **GO**
for MuJoCo/controller handoff; hardware steps remain operator-owned
(read-only preflight first, per transfer_manifest blockers). Remaining
optional upgrade (not a blocker): swap walk role to a walkteach-acq12m
lineage export if its UX beats MLP-singleframe on the identical
12 s-hold suite.

Next #2 CLOSED same cycle — learned-vs-scripted tuck A/B (identical
harness, seed, script; only stand/lower controller swapped,
`stancemix_tuckclock_scratch8m` learned stance):
`logs/manual_drive/todaypolicy_mlpsf_learnedtuck_ab/`. Learned tuck
completes all phases (0 terminations, no sac legs, video clean) but is
strictly worse on the deciding bars: **cur_p95 2.153 A BREACHES the
≤2.0 bar** (scripted 1.886), slip total 3.61 vs 2.72 m, course p90
8.31° vs 6.98°; progress/course-med equal (walk role identical).
Ruling: **scripted tuck stays the bundle primary**; learned tuck is a
working but hotter/slippier fallback. No further stance submodel spend
for this track.

Next #3 CLOSED (2026-08-30 ~19:5x, idle-kick — no other track had
runnable GPU work; standwalk's own dualbc4 canary read was genuinely
mid-flight): ran the exact swap the "Remaining optional upgrade" line
asked for — `ops.sh hybriddemo cw-walkteach-scripted-allhead-acq12m
--script human --walk-seconds 28 --speed 0.08 --policy-mode
deterministic` (same script/speed/seconds as the bundle's own demo,
only the walk-role checkpoint swapped; stand controller defaulted to
`step` not `tuck` for this check, a harmless mismatch since stand
happens before the walk-phase metrics that decide this and both
finish clean) — `logs/manual_drive/todaypolicy_walkteach_acq12m_swap_check/`.
Result: **does NOT beat the bundle, keep MLP-singleframe primary.**
Head-to-head on the identical harness (current bundle's own
`bundle_mlpsf_tuck_v1/summary.json` vs this run's `summary.json`):
`walk_progress_ratio` 0.418 (current) vs **0.38 (candidate, MISSES
the todaypolicy 0.40 floor)**; `course_err_1s_med_deg` **2.42 vs 6.15**
(candidate is 2.5x worse and marginally breaches the <=6 bar);
`course_err_1s_p90_deg` 6.98 vs 12.09 (also worse). Candidate DOES win
on current draw (`cur_p95_a` 1.886 vs **1.073**, big thermal margin)
and total slip (3.951 vs 2.799) and, per the earlier per-heading
`eval_cmd_suite` read (`logs/ckpt_eval/cw_walkteach_scripted_allhead_acq12m_cmdsuite.json`
vs `..._mlp_singleframe_acq1_stdanneal_cmdsuite12.json`, both 12s
holds), has real turn authority the MLP-singleframe walk role
structurally lacks (`tip_ccw`/`tip_cw` `wz_err_med` 0.076-0.106 vs
0.30/0.30 — MLP-singleframe has zero wz obs channel, so it literally
cannot respond to a turn command). But turn authority is not a
todaypolicy DONE-gate axis today (the demo `script=human` only ever
issues vx/vy, never wz), and the two bars that ARE gated
(progress_ratio, course tracking) both favor the CURRENT bundle by a
wide margin on the harness that matters (the real 28 s composed demo,
not the per-heading fixed-command suite — the per-heading suite's
"comparable completion, much lower slip" read undersold how much
worse walkteach-acq12m's course-following gets once the script
actually changes direction repeatedly, a fair warning that per-heading
cmdsuite parity does not transfer to human-script parity). **Ruling:
no bundle swap.** Recorded as a viable alternate walk role for a
future turn-capable bundle (its own turn authority is real and
unique), not a replacement for today's candidate. This closes the
track's own last open Next item; nothing else is queued here.

## Goal

Produce a useful MuJoCo/controller-transfer candidate today by composing
policy plus state explicitly. A valid answer may be a bundle such as:

`scripted-or-learned tuck stand -> exported RL walk policy -> scripted-or-learned tuck lower`

This track may reuse existing learned policies, scripted controllers,
CPG controllers, browser/controller glue, and manifests. It does not
claim the single-policy problem is solved. `standwalk` continues in
parallel until one mesh/100 Hz policy can perform sit -> rise ->
joystick walk -> lower by itself.

## Current Best Bundle

`todaypolicy-mlpsf-tuck-v1` is the best immediate candidate:

- Stand/lower: tuck path, preferably the learned
  `stand_stancemix_tuckclock_scratch8m` family when comparing learned
  stance, otherwise scripted `tuck` as the low-current baseline.
- Walk: `cw-walk-allheading-mlp-singleframe-acq1-stdanneal`, exported
  as `linux_control/policies/walk_allheading_mlp_singleframe_acq1_stdanneal.json`.
- Local full-mesh check, 2026-08-30:
  `logs/manual_drive/cw_walk_allheading_mlp_singleframe_stdanneal_hybrid_tuck_ux_human28/`
  ran stand -> walk -> lower with no termination, no sacrificed legs,
  `walk_progress_ratio=0.418`, `course_err_1s_med_deg=2.57`,
  `wrong_course_frac_1s=0.0`, `cur_max_a=2.64`.

Interpretation: this is usable as a stable demo candidate, but it still
feels underpowered. Joystick direction is good; speed authority is the
weak axis.

## DONE Gate

This track is DONE for the day when a named bundle has:

- full-mesh MuJoCo video for stand -> joystick walk -> lower;
- `summary.json`, `composition.json`, and `transfer_manifest.json`
  checked into a durable path or summarized in docs;
- exported controller-ready policy JSONs for every learned role;
- browser/controller selector path documented or built;
- GO/NO-GO note for hardware handoff, with physical robot work still
  operator-owned.

Minimum demo bars for a TODAY pass:

- zero falls/terminations in the demo;
- `model_variant=full_mesh`;
- no sacrificed legs;
- walk `course_err_1s_med_deg <= 6`, p90 <= 15, wrong-course fraction 0;
- walk `progress_ratio >= 0.40` for today's baseline, with a stretch
  target >= 0.60 for a satisfying joystick feel;
- `cur_max_a <= 2.7`, `cur_p95_a <= 2.0`;
- no loaded-foot inward drag in the stand/lower phase.

## Next

1. **DONE 08-30.** Package `todaypolicy-mlpsf-tuck-v1`: regenerate/keep
   a fresh `ops.sh hybriddemo` full-mesh video, write a short GO/NO-GO,
   and make sure the browser/controller can select the bundle.
2. **DONE 08-30.** Compare learned tuck stand/lower vs scripted tuck in
   the same demo harness. Scripted tuck stays the fallback (learned
   breaches the current bar).
3. **DONE 08-30 ~19:5x — NO SWAP.** Compared
   `cw-walkteach-scripted-allhead-acq12m` as a walk-role swap on the
   identical hybriddemo harness: it MISSES the progress_ratio (0.38 <
   0.40) and course_err_1s (6.15 > 6) bars the current bundle clears
   cleanly, despite better current draw/slip and real (unused) turn
   authority. Bundle stays `todaypolicy-mlpsf-tuck-v1` unchanged. See
   the dated entry above for full numbers.
4. Feed any clean result back to `standwalk` as a teacher/source
   candidate, but do not let this track block on the single-policy gate.
   Nothing further queued for this track right now — it is DELIVERED
   and its own Next list is closed 1-3; only a future clean
   walk/stand/lower improvement elsewhere in the fleet would reopen it.

## Boundaries

- No physical robot motion from this track unless the operator asks in
  the current turn.
- This track may build glue, exports, manifests, docs, browser UI, and
  short missing-submodel runs.
- The single-policy goal stays in `standwalk`; todaypolicy is allowed to
  ship a composed controller if that is what works.
