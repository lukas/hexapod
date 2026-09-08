# todaypolicy - working policy bundle for today's demo

Last updated: 2026-09-08 01:5x UTC — LIFT-PHASE-LEAD EXPERIMENT DONE: CLOSED, NO CANARY.

Cycle 20260908T005017 executed the review-scoped experiment on a properly
pinned plant (`mesh_mujoco/hexapod_mesh_mjx.xml` sha256 `a8a5ca8a…`,
4.80573 kg, 100 Hz, contract asserted per rollout: write_speed 400,
write_acc 20, slew 0.375 deg/tick; cont8m ckpt sha `4a902839…`; the frozen
full-STL XML exists only on the operator Mac — the controller's generated
copy is a stale 3.494226 kg build, 20/38 STL hashes mismatched, so the
hash-matched checked-in twin = the exact pod training/qualification plant
was used and recorded). Evidence:
[lift-lead closure](../../../../../artifacts/rl_watchdog/turn_liftlead_20260908/README.md);
controller copies `logs/ckpt_eval/turn_liftlead_20260908/`; runner
committed at `rl_move/sim/probe_turn_liftlead.py`.

MEASURED: baseline reproduces the corrected audit on the pinned plant
(scripted arcs wz ±0.0656 @ vx 0.039, straight 0.0434; cont8m asymmetry
+0.059/−0.035 reproduces). New per-foot lag: contact timing lags the PLAN
by 190–230 ms (median 210), but the executed tangential sweep lags by the
same amount — RELATIVE lag (contact vs executed sweep) is median 0 ms.
The executed gait is ~0.21 s delayed yet internally SELF-ALIGNED; 62–76%
planned-swing contact is symmetric pipeline delay, not lift/sweep
misalignment (during "scuff" the lagged foot is still propelling).

COMPARED (XY path bit-exact preserved, verified; lift dz timing only):
lead 0.21 s (plan-aligned) collapses locomotion (vx 0.039→0.003, wz SIGN
FLIPS both arcs) — causal proof contact must align with the EXECUTED
sweep, which it already does. Lead 0.02 s (execution-relative residual;
honest median selection is 0 = baseline): wz WORSE in BOTH directions,
vx −3..−6%, slip flat. Zero falls everywhere. The review's bar (gain in
BOTH turn directions with retained behavior) is unmet at every dose —
**lift-only phase lead CLOSED; no training canary launched (per the
pre-registered bar, none is justified).** Undertracking at the arcs is
amplitude attenuation of the executed sweep under the unchanged contract,
not a timing defect. Weak residual lever: per-leg DIFFERENTIAL lift
timing (±20–60 ms scatter, legs 1/4 early, 0/2/3/5 late) — measured
uniform-lead sensitivity at that scale is a few % and negative, so not
launch-worthy without a new mechanism argument. Physical
contract/geometry levers remain operator decisions.

--- prior entry (00:52 UTC) below ---

Last updated: 2026-09-08 00:52 UTC — PIPELINE INTERPRETATION CORRECTED.

The 43-rollout pipeline probe establishes undertracking for its two frozen
controllers and tested settings. It does not establish an ANY-controller
impossibility bound. Original qualification criteria and physical limits
remain unchanged; q_20260908T0050Z's assumed command derating and universal
training stop are superseded for this task.

Independent review found that all pipeline rollouts used a 3.494226 kg
model, versus 4.80573 kg in the corrected frozen audit. Both have 34 meshes;
mesh count alone did not preserve model identity. Its nominal-stance arm
is not a workspace-wide bound, and its arc arithmetic does not support a
common 0.040 m/s ceiling. The stage narrative changes planned/actual-contact
selectors; fitted pad/body twist agreement discards per-foot residuals and
does not establish negligible slip. The reported 65–69% contact during
planned swing is a useful contact/actuator timing lead.
[Review and bounded next experiment](../../../../../artifacts/rl_watchdog/turnpipeline_review_20260908.md).
[Original probe and measurements](../../../../../artifacts/rl_watchdog/turnpipeline_20260908/README.md).

Cycle 20260908T005017 owns the next simulation-only experiment: pin the
corrected XML/STL/config hashes, mass, 100 Hz and motor model, then compare
baseline against one lift-only phase lead selected from measured per-foot
lag. Preserve XY foot path, cadence, swing duration, neutral stance,
write_speed 400, write_acc 20 and slew 0.375 degrees/tick. Original arc
commands and starts 0/pi remain the evaluation cells. Measure phase-aligned
per-foot motion, fit residuals, material-contact slip, yaw/progress/gait/falls.
Only a gain in both turn directions with retained behavior justifies one
bounded same-seed training canary. No robot work or operator reply is needed
for this already-authorized simulation/training scope.

--- prior entry (00:03 UTC) below ---

Last updated: 2026-09-08 00:03 UTC — CORRECTED FROZEN TURN DIAGNOSTIC COMPLETE.

Codex completed the contact-audit repair (225541854) and the matched frozen
cont8m/cigate8m/scripted matrix using code dbedfdfe9, existing seed 0,
15-second episodes and actual tripod starts 0/pi. Measured full STL model:
34 meshes, 159 geoms, 4.80573 kg, 100 Hz. All 42 rollouts: zero falls, valid
scored-window gait and valid angular-impulse closure with no unaccounted
terms. Worst relative RMS residual 0.150%. Focused physics tests: 29 passed.

Results and reproducible runner/config:
[corrected diagnostic](../../../../../artifacts/rl_watchdog/turnauth_corrected_20260907/README.md).
Controller copies: logs/ckpt_eval/turnauth_repaired_20260907_{scripted,cont8m,cigate8m}/.

Both learned policies AND the scripted control substantially undertrack
combined forward/yaw commands. At vx=0.08, wz=+0.15, achieved median yaw
across starts was scripted +0.063..+0.064, cont8m +0.05795..+0.05802,
cigate8m +0.062..+0.065 rad/s. At wz=-0.15: scripted -0.065..-0.063,
cont8m -0.049..-0.047, cigate8m -0.048..-0.045. The course-income gate
does not consistently improve both turn directions. Qualification remains
FAIL; this diagnostic is not a qualification rerun.

Next bounded work: locate motion loss along desired foot trajectory ->
IK target -> clipped/slew-limited command -> measured joint response ->
body motion, comparing straight, in-place and actual +/-0.15 arc cells.
Use frozen existing policies/scripted control under current limits first.
Only a measured mechanism justifies the next budgeted training arm. This
work is authorized; no fresh seed or operator reply is a prerequisite.
Coordinate around the active scratch owner editing walk_task.py/sim_env.py;
use isolated diagnostic files and immutable snapshots.

The prior 17:0x causal claims remain superseded: no seed-history cause,
placement exoneration or single braking-leg cause has been established.
Use force PLUS contact-couple impulses and actual turn sign; near-zero
net yaw impulse at steady yaw is expected. BC residual remains unavailable
because observation/internal-teacher clocks are not proven aligned.
Scripted/learned phase labels do not prove matched teacher transmission.
Historical "mesh" can mean MJX twin: compare actual model variants.
Original audit artifacts remain archived in logs/ckpt_eval/turnauth_0907/.

Previous update 2026-09-07 ~16:2x — cigate8m VERDICTED
FAIL-QUALIFICATION: the `walk_course_income_yaw_gate` mechanism
(cont8m's own follow-up) closes per its PRE-REGISTERED FAIL-flag rule
(arc cells flat-or-worse at 8M with reward rising). Fresh `eval_yaw`/
`eval_cmd_suite`/`eval_joystick_gate` panel (train-1, exact training
cfg, no live claimant found): arc-right wz_err_med 0.1162(cont8m)
-> 0.1149 (still misses <=0.0905, ~1% = noise), arc-left 0.0947
-> 0.0971 (WORSE, misses its own <=0.0947 bar); tip-left improved
(0.0885->0.0825) but tip-right worsened (0.0842->0.1003), net no
tip gain either sign, still far over the 0.076 bar (authority-bound
per the 15:4x `probe_tip_income.py` finding, unaffected by this
mechanism as expected since it targets combined cells not tip).
(ii)/(iii)/(iv) all HOLD/IMPROVE: joygate stress_mix PASS, gv=1.0,
0 falls, slip 2.295->2.25, `course_yawref_err_1s_med` 4.07->3.42
(well under the 5.17 bar); cmd_suite stop v_err near-zero. Reward
rising throughout (quarters 344/1366/2289/2596). **CLOSES the
course-income-yaw-gate mechanism family on this lineage** — 3
successive checkpoints (acq8m/cont8m/cigate8m), 3 different reward
levers (frame fix, course-income-inversion fix), same arc-right/tip
deficit each time. Root suspect is gait-mechanism AUTHORITY (the
scripted-teacher-derived gait's own wz ceiling), not reward pricing;
next move needs an authority-level lever (teacher omega/duty
structure) or a renegotiated tip/arc bar — no further income-knob
arms on this lineage. Evidence: `logs/ckpt_eval/cw_robotwalk_turns_
20260907_yawref_cigate8m_{yaw,joygate_freshcmp}/`, W&B `i2uvpfge`;
RL_LOG 09-07 16:27.

Previous update 2026-09-07 ~15:4x — yawref-cont8m VERDICTED
FAIL-QUALIFICATION (partial): tip missed <0.076 a 2nd time
(pre-registered if-false branch), arc-right regressed +28%; walk
retention/joygate(course_yawref 4.07)/stop all HOLD. Root-caused via
new `probe_tip_income.py`: tip reward is ALIGNED+steep but the gait
mechanism saturates (scripted teacher itself caps at wz_med ~0.224 on
a 0.3 tip command, even 33% overdriven; the policy's 0.21-0.22 is AT
the teacher ceiling); on moderate combined cells (the exact regressed
arc-right cell) the windowed course income STILL pays turn-refusal
428.0 / crabbing 428.7 vs faithful arc 402.1 (deadband forgives
6.4deg/window at wz=0.15) — a strict measured inversion. ONE
dedicated mechanism shipped default-off + bank-proved
(`reward.walk_course_income_yaw_gate`, window-matched achieved/
commanded yaw ratio on course income; test_ci_yaw_gate_* 5/5) and the
smallest bounded arm queued on the EXISTING seed. See ~15:4x entry.

## 09-07 ~15:4x — cont8m FAIL-QUALIFICATION recorded; tip/combined-turn mechanism designed from matched diagnostics; ci_yaw_gate arm launched

Verdict (full per-cell evidence in the ledger/W&B pzu0hc62 note; all
original thresholds preserved, corrected course_yawref key retained):
(a) tip 0.0885/0.0842 vs <0.076 — MISSED again, flat vs acq8m
0.0935/0.0809 (2nd budget increment, band 0.08-0.095 = the run's own
prediction-if-false); (b) arc-left 0.0947 (+5%), arc-right 0.1162
(+28% real regression), arc-maxes 0.2153/0.2243 (better) — MIXED;
(c) retention HOLDS 24/24 gv, 0 terms, fwd med 0.2905, slip 2.6885;
(d) joygate pass, course_yawref 4.33->4.07 (<5.17), 0/24 falls, slip
2.295; (e) stop v_err 0.0013/0.0037. Reward rising (quarters
313/1350/2362/2964) => informative-negative on tip/arc-right, not a
lineage kill. No export, no 3rd identical continuation.

Missing videos captured (drive_video --script turn, full mesh, exact
training cfg, `..._cont8m_turnvideo/`): tip-left/right at 0.3 +
arc-left/right at 0.15 — clean upright six-leg stepping, COM trace
curling smoothly, no falls/stumble => the arc-right regression is
UNDER-ROTATION (tracking), not a gait/stability pathology.

Diagnostics (new `rl_move/sim/probe_tip_income.py`, exact cont8m
stack, scripted omega sweep at the failing cells):
- tip cells: reward strictly monotone toward correct-sign full-rate
  (wrong-sign 24 < refusal 516 < half 1198 < faithful 1836 <
  overdrive 1868) => tip pricing ALIGNED; but achieved wz saturates
  at ~0.147 mean / 0.224 med even scripted at f1.33 => tip deficit is
  AUTHORITY-bound (teacher-mechanism ceiling; the tip bar 0.076
  requires achieved med >=0.224 = exactly that ceiling). Teacher-side
  authority levers are closed on the standwalk track (uniform/
  selective omega boost, yaw_amplify, duty skew — see
  tripod_gait.py docstrings); no reward knob can create authority.
- arc-right cell (vx=0.08, wz=-0.15): course income INVERTED
  (refusal 428.0, crab 428.7 > faithful 402.1) because 0.75s-window
  commanded yaw = 6.4deg ~= the 6deg deadband — the per-window
  re-anchor forgives refusal; linear kernel+walk_prog add ~-48
  anti-turn; k_yaw_prog is the ONLY pro-turn channel. This is the
  measured mechanism behind the arc-right 0.0905->0.1162 regression
  and the thin combined-turn margin generally.

Mechanism shipped (default-off, bit-exact off, bank-proved):
`reward.walk_course_income_yaw_gate` in [0,1] — course income *=
(1-g) + g*clip(dyaw_achieved/dtheta_ref, 0, 1) over the SAME trailing
income window (yaw history already stored by walk_course_ref_yaw=1
rows; inert on legacy rows and on straight/stop ticks by
construction). Refusal/crab score ~0, wrong-sign clips to 0, faithful
arc keeps its income in proportion to achieved rotation — adds the
missing combined-tick gradient toward actually turning. Bank:
`test_course_income_semantics.py::test_ci_yaw_gate_*` (defect pinned
without gate; ordering fixed with gate; wrong-sign floor; forward
bit-exact; explicit-0.0 bit-exact) 5/5 green + full module green.

Launched: `cw-robotwalk-turns-20260907-yawref-cigate8m` — respec of
cont8m, EXISTING seed 0, warm from the cont8m checkpoint (parents
preserved append-only), sole change walk_course_income_yaw_gate=1.0,
8M. Falsification pre-registered: arc cells (esp. arc-right <=0.0905)
must improve with (c)/(d)/(e) holding; combined wz_err flat-or-worse
at 8M with reward rising => the course-income inversion was NOT the
binding combined-cell misalignment, next suspect is pure gait
authority — no further income-knob arms on this lineage. Tip is
secondary here (authority-bound); if tip moves it licenses an
authority-focused follow-up, if not the tip bar needs an
authority-level answer, not budget.

## 09-07 ~13:1x (triage; found this FINISHED+unverdicted orphan with free capacity, ran its own pre-registered panel per the 10:1x precedent) — yawref-cont8m: AMBIGUOUS, none of the 3 pre-registered branches cleanly fires — DIG-IN flagged, not verdicted

`cw-robotwalk-turns-20260907-yawref-cont8m` (the 8M same-recipe
continuation the ~10:1x entry below licensed) had finished its full
budget and its checkpoint had already cleared the deferred-artifacts
finalizer (`phase: evaluated`) but sat unverdicted — this run's
`track:todaypolicy` tag means the watcher's standard walk-retention/
joygate auto-eval never fires for it (same gap the 10:1x entry
named), so no report existed at all yet. Pulled the checkpoint fresh
(`ops.sh pullckpt`, controller copy was missing, fell back to the
training pod) and ran the exact same 3-tool panel the 10:1x entry
used (`eval_yaw`, `eval_cmd_suite`, `eval_joystick_gate`, identical
`--cfg-set`/`--extra-cfg-set` list pulled straight from the ledger's
own `extra_args` so obs/command distribution matches training) on the
run's own pod (`hexapod-mjx-train-1`, free at the time).

**Reading against the run's own 5-criterion pre-registered gate:**
- **(a) tip-turn-in-place wz_err_med <0.076 — STILL NOT CLEARED,
  roughly flat.** cont8m: tip-left 0.0885 (improved from acq8m's
  0.0935), tip-right 0.0842 (WORSE than acq8m's 0.0809). Net: no
  meaningful net change, both signs still well over the 0.076 bar.
  This is the one gap the whole continuation was launched to close,
  and it did not close.
- **(b) combined-cell wz_err at/better than acq8m's
  0.0901/0.0905/0.2216/0.2251 — MIXED, one cell regressed outside
  noise.** cont8m: arc-left 0.0947 (worse, +5%), **arc-right 0.1162
  (worse, +28% relative — the largest single delta in either panel)**,
  arc-left-max 0.2153 (better), arc-right-max 0.2243 (better). Same
  seed/cfg/deterministic env both times, so this is a real policy-
  behavior change from the extra 8M steps, not eval noise — the
  max-arc/tip-left cells improved while plain-arc-right and tip-right
  got worse, a genuine trade-off pattern, not a clean net win.
- **(c) walk retention (DR-0 walk mode, 0 falls, gait valid, slip) —
  HOLDS.** joygate `walk`-mode pass (dr=0, n=24): 0 falls,
  `gait_valid_frac`=1.0, `slip_per_m_med`=2.295 (<=2.9 cap), all 6 legs
  nonzero duty (0.535-0.625) — no new leg sacrifice. (Ran `--modes
  walk` only, not the combined `walk,walk_startjitter` 4-panel the
  original acq8m read used — a narrower but consistent-direction
  check given the time budget; does not contradict retention.)
- **(d) joygate stress_mix pass=true AND course_yawref_err_1s_med
  <=5.17deg — HOLDS, IMPROVED.** cont8m: pass=true,
  `course_yawref_err_1s_med`=**4.07deg** (better than acq8m's
  4.33deg). The frame-fix's own target metric keeps improving with
  more budget.
- **(e) cmd_suite stop cell near-zero v_err (no standing-still
  regression) — HOLDS.** `stop` row: det `v_err_med` 0.0008->0.0013,
  sto 0.0040->0.0037 — both still ~0, no regression.

**None of the run's own three pre-registered branches cleanly fires:**
not PASS (criterion a fails outright), not the stated CONTINUE text
("tip improves ... with (b)-(e) holding" — tip did not clearly
improve and (b) does not fully hold), not the stated FAIL-flag text
("tip flat-or-worse AND (b)/(d) ALSO regress with reward flat" — (d)
improved and reward is emphatically NOT flat: quarters
`[313.1, 1350.4, 2361.9, 2964.4]`, still climbing every quarter).
Per the 08-21 ruling this is closer to "continue" than "stop" (reward
rising, most criteria hold or improve), but the arc-right regression
is a real, reproducible-by-construction anomaly (same seed/cfg/det
env, only the checkpoint differs) that decides a real fork — ship
this lineage's turn behavior as-is for the `todaypolicy` bundle's
walk role, keep training the same recipe hoping consolidation
resolves the trade-off, or design a dedicated tip-in-place income
lever (the `-acq8m` entry's own "if false" prediction, now looking
more likely than "if true"). Flagging DIG-IN rather than forcing a
verdict — the next reader should watch video for both the arc-right
and tip-right cells (none was captured this cycle, `--video` flag not
set on either eval call) before deciding continue-vs-lever-design;
raw numbers alone don't show WHETHER the arc-right degradation is a
gait-quality problem (e.g. a slip/stumble under that specific turn
rate) or just a slower-but-still-clean convergence.

Evidence: `logs/ckpt_eval/cw_robotwalk_turns_20260907_yawref_cont8m_
{yaw,joygate_freshcmp}/{yaw_verdict.json,cmdsuite_verdict.json,
gate_verdict.json}`; comparison baseline pulled fresh from the run's
own training pod's `..._yawref_acq8m_{yaw,joygate_freshcmp}/` dirs
(never synced to the controller before this cycle — same `track:
todaypolicy` sync gap). W&B `pzu0hc62`. RL_LOG 09-07 13:1x.

## 09-07 ~10:1x — yawref-acq8m VERDICTED: frame fix WORKS on its target metric; one pre-existing gap stays open; continuation launched

The 06:1x frame fix's first trained arm finished 8M steps and sat
unverdicted since 07:xx (`track:todaypolicy`, so the watcher's
joystick-only joygate auto-eval never runs for it — the standard
prestage only ran the plain walk-retention gate). Ran the run's own
full pre-registered 4-check panel myself on its own pod
(`hexapod-mjx-train-1`, checkpoint present, `--defer-final-artifacts`
hadn't synced it to the controller yet), reusing the exact training
`--cfg-set` list so obs/command distribution match what was trained:
`eval_yaw` (speed 0.08, wz_max 0.3), `eval_cmd_suite` (`--seconds
12`), `eval_joystick_gate` (`--own-dr-scale 0.0`) — the identical
methodology the 09-06 ~14:5x arcaware precedent used.

**DECISIVE result (criterion d, the metric this whole fix targets):**
joygate `course_yawref_err_1s_med` = **4.33deg, clears the 5.17deg
Candidate-B bar** (pass=true, 0/24 falls, gait_valid_frac 1.0, slip/m
med 2.214). The legacy `course_err_1s_med` keeps "worsening" exactly
as predicted (12.21, vs 11.93/10.2/8.55 on the arcaware/16M/8M
ancestors) — because the policy is turning MORE, not less. This is
the audit's own predicted signature landing cleanly, not a
coincidence. Combined-cell wz tracking (criterion b) improved across
the board vs its own immediate arcaware ancestor on identical
`eval_yaw` cells: arc-left/right (wz=0.15) 0.0901/0.0905 vs
arcaware's 0.104/0.1131; arc-max (wz=0.3) 0.2216/0.2251 vs arcaware's
0.2234/0.229. Walk retention (c) and standing-still (e) both intact
(gait_valid 6/6 all modes, 0 falls, fwd med 0.29m, slip med 2.81;
`stop` cell v_err_med 0.0008-0.004, genuinely holds still).

**One criterion still misses its literal bar:** tip-turn-in-place (a)
wz_err_med 0.0935/0.0809, both over the <0.076 absolute bar — but
essentially FLAT vs the immediate parent `cont8m-resume1`'s own
0.078/0.085 (mixed, not a regression). Tip has vx=0, so the vx+wz
frame confound this fix targets never applies there — this is a
separate, pre-existing, unmoved deficiency, not evidence against the
fix. Reward still climbing every quarter (333.5/1327.4/2220.2/
2744.4, no plateau). **Verdict: ACQ CONTINUE** (08-21 ruling — reward
rising + one open gap = continue, not stop). No export yet (literal
gate needs (a) too).

**Launched:** `cw-robotwalk-turns-20260907-yawref-cont8m` (init-from-
source off this checkpoint, +8M, zero cfg changes) — tests whether
consolidating under the now-correctly-aligned reward also closes the
tip residual, or whether tip needs its own dedicated lever next.
Evidence: `logs/ckpt_eval/cw_robotwalk_turns_20260907_yawref_acq8m_
{yaw,joygate_freshcmp}/`, W&B `3j03b9ro`, RL_LOG 09-07 10:1x.

## 09-07 ~06:1x — combined-frame audit (operator watchdog focus note): the turns lineage's repeated course_err "worsening" was the reward AND the gate metric PAYING turn-refusal; fix shipped, one changed arm launched

Did the focus note's audit (k_walk_course_income/window/deadband/
sigma, yaw rewards, command frame/resampling, kept straight/combined
BC anchor) with a bounded CPU replay on the REAL env + the EXACT
`cw-robotwalk-turns-20260906` reward stack (new tool
`rl_move/sim/probe_combined_frame.py`; combined cell vx=0.08,
wz=+0.25, three scripted drives). **Decisive counterexample:** a
wz-IGNORING straight walker (net body yaw −0.5° vs commanded +114.6°)
out-earned the faithful body-frame arc-follower **2094.5 vs 1959.8
total** (course income +597 vs +438, sway 0 vs −19.6, disp 0 vs −3.1)
AND scored **0.90° vs 12.33°** on the joygate `course_err_1s_med`
gate metric. Root cause: course-income/excess-sway/course-disp and
the eval windowed course metric all integrate (vx_ref, vy_ref) as a
FIXED WORLD CHORD never rotated by wz_ref, while the velocity kernel
is BODY-frame and `walk_obs_body_vel=2` obs carry no world compass —
on combined ticks the reward's optimum was REFUSING to turn, and the
gate's 5.17° bar (Candidate B) measures turn-refusal, not steering.
So cont8m-resume1's 8.55→10.2 and arcaware's →11.93 "worsening" was
the policy genuinely turning MORE (tip wz_err improved exactly where
no linear command conflicts; combined wz_err stuck 0.21/0.23 = PPO
correctly optimizing the misaligned pricing). The bank's sweep_circle
"arc" cases never covered this cell (they rotate the world command
with the body never yawing — the opposite semantics), which is why
the 09-06 17:3x audit read "near-perfect at production rates". The
09-06 13:0x arc-vs-chord finding was the same family but only fixed
sway's bowing, not the frame.

Shipped (default-OFF, bit-exact off, snapshot
`exp/cw-robotwalk-turns-20260907-yawref-acq8m` 5e9ccb96):
`reward.walk_course_ref_yaw=1` — course reference rotated by the
integrated commanded yaw, re-anchored per window at the body's own
window-start heading (body-frame joystick semantics: vx+wz = arc;
income + sway shadow path + course_disp); eval
`windowed_course_stats(wz=,yaw=)` emits additive `course_yawref_*`
keys; joygate reports `course_yawref_err_1s_med` (pass logic
untouched). Bank: `test_course_income_semantics.py` +4 combined-frame
clauses, 18/18 green (plus 63 course/joygate/disp + walk semantics +
bc_anchor suites green). Replayed post-fix optimum with the minimal
measured dose `k_yaw_prog` 1→2 (covers the honest physics cost of
arcing, gap −42.3, dose swing +157): **faithful arc 2204.3 > refusal
2089.2 > crab 2077.5**, and the corrected eval metric orders arc
4.59° < refusal 7.06° (faithful arc would PASS the same 5.17° bar).
Frame semantics decision + gate-metric policy recorded in
`OPERATOR_QUESTIONS.md` 09-07 ~06:1x (body-frame adopted,
assume-and-go; corrected metric gated at the SAME absolute bar —
not a relaxation, it charges refusal where the legacy key paid it).

**Launched (the focus note's ONE justified changed experiment):**
`cw-robotwalk-turns-20260907-yawref-acq8m` — respec of
cont8m-resume1, warm from the recovered 16M checkpoint (operator-
named lineage; walk retention 24/24, 0 falls, best tip 0.078/0.085),
seed 0, 8M, sole changes `walk_course_ref_yaw=1` +
`walk_sway_arc_aware=1` + `k_yaw_prog=2`. Gates preserved absolute
(tip <0.076 both signs; combined cells improved vs BOTH matched
comparators on identical cells; straight ≥0.29 m/12s, slip ≤2.9,
0 falls, six legs; joygate stress_mix pass with
`course_yawref_err_1s_med` ≤5.17° and comparators re-read on the
same corrected key; standing-still = FAIL). Falsification
pre-registered: combined wz_err or course_yawref flat-or-worse at 8M
with reward rising = frame was not the (only) bug — next suspects
PPO convergence at the operating point / command generator; no
same-recipe continuation. VERIFIED RUNNING hexapod-mjx-train-1.
Scratch queue check: backlog empty, walkscratch s0/s1/s2 finished
during this cycle (their triage belongs to the watcher's fan-out).

## 09-07 ~04:2x (cross-track note, no launch here) — cadence-CPG harvest lever CLOSED: `cpg`'s re-tuned winner is worse than the incumbent, nothing to harvest (its "no further open item" claim is superseded by the 06:1x entry above)

The 09-07 ~01:5x entry below left this lever open pending `cpg`'s
background robust-gate comparison of its joint period-search winner
against the incumbent `robust120-winner-yawtrim`. That comparison
landed this cycle (full detail: `rl_docs/tracks/cpg/STATUS.md` 09-07
~04:2x entry): the re-tuned winner PASSES the robust gate but has
WORSE slip/m than the incumbent in all 5 panels (+11% to +53%) for
only a mixed heading-progress delta — not a genuine improvement, the
pre-registered "merely matches or is worse" branch. **No faster/
better CPG motion clip exists to harvest for a BC-anchor arm here.**
Combined with the `robotwalk-stride-20260906` anchor-dose axis
already closed 2/2 (09-06 ~22:1x below), this track's Next list is
now fully closed on the open-arm side — the delivered bundle
(`todaypolicy-mlpsf-tuck-v1`, GO per `CURRENT_TRUTHS.md`) stands as
the answer; no further agent-doable next step remains here pending a
genuinely new idea. No code/launch this cycle.

## 09-07 ~01:5x (cross-track note, no launch here) — cadence-CPG harvest lever: probe started on `cpg`, not yet ready for a todaypolicy GPU arm

The 09-06 ~22:1x closure below named the next lever as "a faster
motion source / cadence-CPG harvest, not another dose point." Picked
this up from the `cpg` side (that track owns `paper_cpg_search.py` and
the CPG motion library `cpg_v1.npz`/`cpg_v1_manifest.json` this lever
would harvest from) rather than duplicating tooling here. Finding so
far (`rl_docs/tracks/cpg/STATUS.md` 09-07 ~01:5x entry, full detail
there): the robust-gate CPG winner's `period` param sits pinned at its
search's own lower bound (2.0s), a real signal a faster cadence might
exist — but a naive matched-control halving (period 2.0->1.0, same
other params) makes things WORSE (slip/m 0.91->1.98, no distance
gain), not better; a proper joint-tuned search (widened bound +
re-optimized swing_frac/cmd_tau/lift_m) is running now in the
background on the controller pod, not yet concluded. **No todaypolicy
GPU launch is licensed from this yet** — only once that search lands
a genuinely faster point that ALSO clears `eval_cpg_gate.py --robust
--yaw-trim` does harvesting a new/faster CPG motion clip for a
BC-anchor arm here become a real option; until then this track's own
Next list stays closed (delivered, nothing else queued) per the
entries below. No code/launch in this file this cycle.

## 09-06 ~22:1x — anchorsoft1x/2x-acq8m BOTH FAIL-PLATEAU (pre-registered branch, matched dose pair 2/2); anchor-dose axis CLOSED

Both full 8M ACQ runs landed this cycle. Read together per the gate's
own instruction (matched dose pair, not independent seeds):

- **`cw-robotwalk-stride-20260906-anchorsoft1x-acq8m`** (bc_anchor_coef=1.0):
  mechanism stays perfectly clean at 8M -- gait_valid 24/24, 0
  falls/terminations, no duty-lock (`duty_cycle` 0.34-0.82, nothing
  pinned), slip/m med 2.37-2.54 all 4 modes (cap 2.9). Reward rose
  cleanly the whole budget (quarters 255/846/1424/1817, no plateau in
  the curve itself) -- but the gate's decisive metric (det h000
  prog_m) moved only 0.343(2M canary)->0.35(8M) = **+2.0%**, inside
  the gate's own "~5% wiggle" disqualifier, with per-episode direction
  mixed (not a real shift). The other 3 modes read FLAT-TO-DOWN vs
  this arm's own canary (sto -4.5%, startjitter/det -6.2%,
  startjitter/sto -8.0%) -- the opposite of the canary-stage's clean
  3/4-up pattern. vs Candidate B's band, this arm is now BELOW
  Candidate B on startjitter/det (0.21 vs 0.234, -10.3%) -- a real
  regression on one submode. **FAIL-PLATEAU.**
- **`cw-robotwalk-stride-20260906-anchorsoft2x-acq8m`** (bc_anchor_coef=1.5):
  same clean-mechanism fingerprint (gait_valid 24/24, 0 falls,
  duty_cycle 0.38-0.79, slip/m med 2.24-2.51). Decisive metric:
  0.354(canary)->0.375(8M) = **+6.1%**, at the edge of the wiggle
  disqualifier, per-episode direction mixed (2 up/2 down/2 flat).
  walk/sto genuinely up (+32%) but the two startjitter modes flat-
  to-down (-3 to -5%) -- a mixed/partial result, not a repeat of the
  canary's clean pattern at scale. Stays above Candidate B in all 4
  modes. **FAIL-PLATEAU.**

Both: video (contact sheets, all sampled modes) confirms clean
continuous six-leg cycling, no drag/flag-leg/paddle-creep -- the gait
itself is fine, it simply doesn't cover more ground than each arm's
own 2M canary did. Reward's continued rise is not converting into net
distance (`env/reward_walk_prog` ~0.18/tick vs `reward_walk` 0.58/tick
on both arms, growth driven by other channels/polish once the
distance ceiling for this reward shape is hit) -- exactly the
hypothesis's own pre-registered FAIL-PLATEAU falsification case, not a
fresh misalignment needing an audit. **2/2 dose points plateau at
full budget -- this CLOSES the anchor-dose-magnitude axis for the
`robotwalk-stride-20260906` campaign.** Per the hypothesis's own named
alternative, the next lever (if revisited) is a faster motion source /
cadence-CPG harvest, not a 3rd dose point or a longer continuation of
either arm. No export (gate not met, no RobotLab handoff triggered).

Evidence: `logs/ckpt_eval/cw_robotwalk_stride_20260906_anchorsoft{1x,
2x}_acq8m_gate/report.json` vs each arm's own `..._gate/report.json`
(2M canary) and `cw_walkteach_scripted_allhead_acq12m_gate/
report.json` (Candidate B), W&B `0e866co5`/`jymcz68k`, RL_LOG 09-06
22:08/22:09.

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
for MuJoCo/controller handoff; hardware steps run through the serialized
guarded agent (read-only preflight first, per transfer_manifest blockers). Remaining
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
- GO/NO-GO note for hardware handoff, with remote physical robot work owned by
  the guarded runner and hands-on correction remaining operator-owned.

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

- Bounded physical motion from this track uses standing campaign authority,
  live camera, three fresh healthy samples, and a remote abort path.
- This track may build glue, exports, manifests, docs, browser UI, and
  short missing-submodel runs.
- The single-policy goal stays in `standwalk`; todaypolicy is allowed to
  ship a composed controller if that is what works.
