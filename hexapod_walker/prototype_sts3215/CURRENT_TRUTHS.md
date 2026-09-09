# CURRENT TRUTHS - accepted facts and rulings

Last compacted: 2026-08-30 for the `todaypolicy` sixth-track update.
Archive copy: `archive/CURRENT_TRUTHS_2026-08-30_pre_todaypolicy_compaction.md`.
Accepted facts, not narrative. This file wins on factual evidence and run
verdicts; `RL_GOALS.md` owns purpose and priorities, including Lukas's
2026-09-08 clarification. Older mission/allocation prose does not override it.

## assistfade rung3 per-leg reward-shaping repair line CLOSED 6/6, including dose magnitude (2026-09-09 ~07:5x-08:0x)

Every per-leg reward-shaping mechanism-or-dose variant tried against
rung3's chronic single-leg-sacrifice pathology FAILS, 6/6 attempts:
bare `walk_leg_duty_ratio_charge` at its original dose (150),
swing-count-floor, load-slip-ratio at 2 doses, swing-gap-dose10, a
positive swing-initiation income, AND (the last remaining candidate)
recalibrating the base charge itself to dose=10 (matching a dose fix
that worked on the unrelated walkcurr/crutchoff lineage). Each was
independently validated as reward-mechanism-healthy (no order-of-
magnitude reward collapse) — the failure is purely on efficacy. In
every seed of every variant, the named chronically-sacrificed leg
either stays byte-identically unchanged (duty_cycle=1.0,
swing_count=0) or gets measurably worse, and a SECOND leg is
frequently pushed into the same pattern as a side effect. Neither the
CHOICE of mechanism nor its MAGNITUDE moves this pathology. This
convergent pattern points at rung3's residual-fade base recipe's own
already-documented schedule-collision/sway-dominance root cause as
the actual blocker, not the reward stack. Do not launch another
per-leg charge/income/dose variant onto rung3 without first
addressing that structural base (fix the blend schedule/sway-dominance
mechanism itself, or construct a fresh rung-3 base). This is scoped to
rung3's residual-fade lineage only; it does not reopen rung 1/rung 2's
own separately-closed findings, and it does not speak to the unrelated
`walk_leg_loadslip_ratio_charge` closure below (walkcurr's own widen8
lineage, already closed on efficacy grounds independent of this
mechanism-family question).
Evidence: `ops.sh review cw-assistfade-rung3-legdutyratio-swinit-dose2-{s0,s1}`,
`cw-assistfade-rung3-legdutyratio-dose10-{s0,s1}`;
`rl_docs/tracks/assistfade/STATUS.md` 2026-09-09 ~07:5x-08:0x entries.

## `walk_leg_loadslip_ratio_charge` family CLOSED (2026-09-08 ~19:1x)

The excess-cap repair (`reward.walk_leg_loadslip_ratio_excess_cap=0.2`,
tested on the clean confound-isolated `crutchoff-{s0,s1}-widen8-
loadslip-target6-cap02-alone` pair) is CANARY PASS-MECHANISM on both
seeds (reward quarters stay near the healthy scale end-to-end, no
order-of-magnitude collapse) but neither seed clears the pre-
registered >=3/4-held-out-groups efficacy bar (0-1/4 groups clearly
improve). Combined with the already-closed dose (150/45/15), target
recalibration (1.5->6.0), and confound-isolation reads, the ENTIRE
`walk_leg_loadslip_ratio_charge` charge family is closed as a repair
for the widen8 lineage's leg-sacrifice/slip pathology on every
constant (dose/target/cap) tested. Do not relaunch a dose/target/cap
variant of this exact charge shape. The open lead (matches assistfade's
own 09-07 finding) is a structurally different per-leg mechanism -- a
positive swing-initiation income for the most-loaded leg, or a charge
on the fully-planted/no-swing PATTERN/duration directly, not another
scalar-ratio-vs-target charge. Evidence: `ops.sh review cw-walkscratch-
crutchoff-{s0,s1}-widen8-loadslip-target6-cap02-alone`; `rl_docs/
tracks/walkcurr/STATUS.md` 2026-09-08 ~19:1x entry.

## widen8-jointspace-freshinit DR-breadth investigation CLOSED (2026-09-08 ~19:0x)

True zero-DR (`env.dr_stage_ramp_steps=5e10`, `nodrall2m`) still fails
to ignite fresh-init walking on the widen8 8-way-heading composite
(fwd med 0.01m, slip med 73.82, stationary on video) -- the floor
below every previously-tested DR dose/schedule/grouping (1.0x/0.5x/
0.25x fixed, 0->1 staged, 3 single-axis knockouts, discrete/continuous
group split), all of which already failed identically. Combined with
the sister crossgrav-medhead-DR cartfoot-freshinit family's own closed
heading-width and torque bisections, DR magnitude/schedule/breadth is
conclusively ruled out as the fresh-init blocker on this hardened
composite family at ANY setting, on both action spaces, at 2M and 40M
budgets. No further fresh-init launch on this composite family (any
heading width, torque, or DR setting) is licensed without a
structurally different mechanism (e.g. a composite-HARDNESS
curriculum from the already-solved base-acquisition recipe). The
proven ignition path stays warm-start (`crutchoff-s{0,1,2}-widen8-
acq1`). Evidence: `ops.sh review cw-walkscratch-easy0905-widen8-
jointspace-freshinit-nodrall2m`; `rl_docs/tracks/walkcurr/STATUS.md`
2026-09-08 ~19:0x/~19:1x entries.

## `walk_leg_loadslip_ratio_charge` confound correction (2026-09-08 ~15:4x)

Every prior `walk_leg_loadslip_ratio_charge` verdict (target=1.5
closed 0/3; target=6.0 recalibration FAIL; the w15/w45 weight-
reduction bracket both CLOSED FAIL) was trained with
`walk_leg_duty_ratio_charge=150` ALSO active, warm-started from a
checkpoint that already had duty-ratio-charge training baked in.
Duty-ratio-charge ALONE (its own clean 2M canary, no loadslip)
already produces the identical "healthy-then-3-orders-of-magnitude
reward collapse" shape, previously verdicted CANARY PASS there
("fully explained by ep_len growth, not behavioral collapse"). None
of the closed loadslip reads can cleanly separate loadslip's own
contribution to that collapse or to any efficacy gap from this
already-accepted confound — the FAIL verdicts on efficacy grounds
(0/4 groups jointly improving vs the matched parent) still stand
(that comparison is unaffected by the confound), but do not treat the
"reward collapses" half of any of those verdicts as evidence specific
to loadslip. Two isolation canaries (`cw-walkscratch-crutchoff-{s0,
s1}-widen8-loadslip-target6-alone`, duty-ratio-charge=0, init from the
TRUE pre-duty-charge `widen8-acq1` checkpoints) are in flight to give
loadslip-ratio-charge its first clean, unconfounded read. Evidence:
`rl_docs/tracks/walkcurr/STATUS.md` 2026-09-08 ~15:4x entry.

## Active training and interpretation (2026-09-08 10:21 heartbeat)

Lukas's keep-training instruction authorizes bounded, justified scratch
learning and assisted walking/yaw design, simulation, training and routine
recovery on the existing fleet. No operator reply or fleet-contract
change is required to design the next experiment within the existing
physical limits. A failed finite assay closes its tested candidate, not
all steering or all fresh learning. Do not relaunch closed recipes or
fill slots without a recorded hypothesis and gate.

The half-gravity seed7 40M comparison is movement-gate PASS for both
arms, with gait **22/24 ON versus 10/24 OFF**, zero terminations and
lower ON median slip in all four groups. The 2M source counts were
23/24 and 24/24, but their forward movement was negligible. It is
incorrect to call the 40M gait patterns symmetric or both stochastic
panels clean. Preserve original gates and ledger statuses; the result
is one seed, 0.5g/3x torque, not general equivalence or qualification.
Evidence: repository-root
`artifacts/rl_watchdog/fleet_20260908T093214Z/halfgrav_comparison.json`.

Seed10/seed11's own 40M ON reads (2026-09-08 ~11:1x) both clear the
ACQUISITION gate outright (0 falls/24 each, speed 0.20-0.24 m/s, well
above the 0.03 m/s floor) but their gait_valid totals do NOT repeat
seed7's 22/24: seed10 is 17/24, seed11 is 11/24 with a NEW systematic
(not noise-level) leg1 dropout in 100% of BOTH deterministic-mode
panels (12/12 episodes). Do not pool gait_valid across seeds of this
recipe -- 22/24 (s7) / 17/24 (s10) / 11/24 (s11) is real spread on the
identical recipe/budget/gravity/torque. Matched OFF siblings for s10/
s11 finished training but their gate evals were not staged at this
read; both verdicts above are ON-only, no ON/OFF ratio yet for these
two seeds. Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_
halfgrav_{s10,s11}_acq1_gate/report.json`; `rl_docs/tracks/walkcurr/
STATUS.md` 2026-09-08 ~11:1x entry.

Seed11's OFF (joint-space) 50M cont10m read (2026-09-08 ~12:2x) is
PARTIAL, not a clean hold: slip/m 1.76/1.93/1.77/1.74 stays within the
gate's +/-20% noise band of the 40M read (1.82/1.89/1.83/1.94) with 0
new falls, but `gait_valid` collapsed 10/24 -> 3/24, now sacrificing
TWO legs ([1,4]) in every det episode (was one leg at 40M) while
`ep_rew_mean` kept climbing steeply (292->1698 across quarters) — the
08-21 rising-reward/misaligned-eval shape, not a genuine hold. The
paired ON arm's own 50M cont10m read is not in yet; do not treat this
OFF regression as resolving the seed11 ON/OFF gap-at-depth question.
Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_halfgrav_
offctrl_s11_acq1_cont10m_gate/report.json`, W&B `pwphlkog`.

Seed11's matched OFF sibling (2026-09-08 ~11:2x) closes that pair: ACQ
PASS, 0 falls/24, speed 0.17-0.21 m/s, slip/m 1.82/1.89/1.83/1.94
(det/sto/startjitter-det/startjitter-sto) is 1.13-1.22x the ON arm's
1.61/1.58/1.50/1.69 -- same ~1.2x parity band as seed7 (1.08-1.22x).
BUT gait_valid is 10/24 (OFF) vs 11/24 (ON), near-PARITY, not a gap
(both seed11 det panels are 100% single-leg dropout regardless of
action space -- OFF sacrifices leg4 every det episode, ON sacrifices
leg1 every det episode). All 3 ON/OFF pairs are now closed: s7 22/24
vs 10/24 (gap 12), s10 17/24 vs 7/24 (gap 10, `offctrl-s10-acq1`
verdict same window), s11 11/24 vs 10/24 (gap 1, near-parity). Read
as 2-of-3 seeds showing a real cart_foot gait_valid advantage and
seed11 as the outlier, NOT as "the gap doesn't exist" or "the gap is
universal" -- do not pool or average gait_valid across these seeds;
report each pair's own gap. The slip edge (~1.1-1.2x, ON lower) DOES
reproduce in all 3 pairs (s7 0.82-0.93x, s10 0.83-0.89x, s11
0.82-0.89x expressed as ON/OFF), the most seed-robust finding here.
Evidence: `ops.sh review cw-walkscratch-easy0905-cartfoot-halfgrav-
offctrl-{s10,s11}-acq1`; `logs/ckpt_eval/cw_walkscratch_easy0905_
cartfoot_halfgrav_offctrl_{s10,s11}_acq1_gate/report.json`; W&B
`ghd2vc41` (s10 OFF) / `i593jcsf` (s11 OFF).

**Seed12 (4th ON/OFF pair, 2026-09-08 ~13:4x) REVERSES the gait_valid
direction and seed10's own cont10m retention read FAILS.** Both s12
arms clear ACQ (0 falls/24, ~0.15-0.20 m/s): ON `gait_valid` 9/24 (det
0/6, sac leg4 every ep), OFF `gait_valid` 11/24 (det 0/6, sac legs
[1,4] every ep) -- OFF is slightly HEALTHIER than ON on this seed,
opposite the s7/s10 direction and past even s11's near-parity. The
slip edge still reproduces (ON/OFF ratio 0.79-0.88, 4th seed in a row
ON lower). Updated seed tally: 2-of-4 clear ON gait_valid advantage
(s7 gap 12, s10 gap 10), 1-of-4 near-parity favoring ON (s11, gap 1),
1-of-4 favoring OFF (s12, gap -2) -- do not claim a universal
cart_foot gait-health advantage; only the slip edge is 4/4 seed-robust.
Separately, seed10's own cont10m retention read (50M cumulative) is
RETENTION FAIL, not a hold: ON `gait_valid` 17/24 -> 14/24, with
walk/det (the primary gated mode) collapsing from a CLEAN 6/6 at 40M
to 0/6 at 50M, now sacrificing BOTH legs [1,4] every det episode
(was zero-sacrifice at 40M); slip/m held/improved and 0 new falls.
Matched OFF sibling degrades further as its own gate text anticipated
(7/24 -> 4/24). The ON/OFF gap is UNCHANGED at 10 points at both
budgets (17-7=10, 14-4=10) -- more training erodes six-leg health on
both action spaces by a similar amount rather than closing or growing
the cart_foot advantage; reward kept climbing on both arms while
gait_valid fell (08-21 misaligned-reward shape). Do not fund a further
continuation on this exact seed/recipe expecting self-healing; the
per-leg-utilization/load-slip pricing mechanism already in progress on
the walkcurr/assistfade tracks (`walk_leg_loadslip_ratio_charge`) is
the open repair lead, not more raw steps. Evidence: `ops.sh review
cw-walkscratch-easy0905-cartfoot-halfgrav-{s12,offctrl-s12}-acq1`;
`ops.sh review cw-walkscratch-easy0905-cartfoot-halfgrav-{,offctrl-}
s10-acq1-cont10m`; `logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_
halfgrav_{s12,offctrl_s12}_acq1_gate/`, `..._{s10,offctrl_s10}_acq1_
cont10m_gate/report.json`; W&B `hijwfdoc`/`t2r5n3mz`/`s5f2imns`/
`83az85kk`.

The narrowhead/torqueretain fresh-init failures are finite recipe/seed/
budget results. They neither uniquely isolate DR breadth nor exclude
interactions. The completed magnitude-allocation yaw assay is STOP
(0/8 candidates, 0/8 matched box controls pass 5mrad; 32/32 signed
branches retain walking). Preserve its closed outcome and unchanged
limits. New steering design/diagnostics remain agent work.

## Assisted s0 comparator correction (2026-09-08)

The claim that `cw-assistfade-rung3-legdutyratio-s0` repaired
nominal legs [0,3] and improved gait 7/24 -> 15/24 used the wrong
`residualfade-s0-nostdanneal` descendant (policy_std 0.422).
The exact annealed `cw_assistfade_rung3_residualfade_s0_gate`
baseline and candidate both have policy_std 0.052 and the same
4.80573 kg `mesh_mjx_twin`/100 Hz motor contract. Launch argv
match except name, notes and four duty-charge cfg keys. Correct
gait counts are 16/24 -> 15/24; safety terminations 7/24 -> 9/24.
Nominal det and sto are already 6/6 in the baseline; there is no
demonstrated recovery of nominal gait passes. Nominal det progress
and slip improve, while nominal sto does not. No statistical
equivalence or mechanism-class conclusion follows from these counts.

The asserted opposite-seed DIG-IN premise is withdrawn; it does not
license a new seed or automatic continuation. Low-relative-duty
penalties do not directly target fully planted high-duty/no-swing
legs, and zero shortfall is not proof of six-leg walking. The prior
s1 narrative also used a nostdanneal comparator and needs its own
matched audit before causal cross-seed comparison. Full evidence:
`artifacts/rl_watchdog/assistfade_s0_comparator_20260908/comparison.json`
at repository root; corrected interpretation in
`rl_docs/tracks/assistfade/STATUS.md`. This correction does not
change walkcurr's separate prior-free evidence or the formal ledger.

## Mission

Two parallel goals, each with sim and physical deliverables, are defined in
`RL_GOALS.md` (2026-09-08):

- `any_means`: smooth physical joystick walking by any effective means, to
  advance physical builds now. Methods: `joystick`, `amp`, `cpg`, `standwalk`,
  `assistfade`, `todaypolicy`.
- `rl_only`: the same physical outcome with walking learned entirely through
  RL and no demonstrations in its training lineage. Method: `walkcurr`.

The seven stable method IDs and parent mappings live in
`rl_move/orchestrator/tracks.json`. Random initialization with BC/AMP or
scripted-gait assistance still belongs to `any_means`. Physical delivery and
clean RL research proceed in parallel; neither requires every method green.
Historical method gates/verdicts below remain evidence, not a claim of either
parent goal's completion. Each goal also requires its own interactive joystick
sim demo and viewable video; record sim and physical readiness separately.
This clarification does not reopen closed
recipes. Out-of-scope operator runs get honest triage but no agent follow-ups.

## Today Answer
- DELIVERED 2026-08-30: `todaypolicy-mlpsf-tuck-v1` packaged, all TODAY
  bars PASS on a fresh controller-side full-mesh regen; GO for
  controller handoff. Durable evidence + GO/NO-GO + selector path:
  `rl_docs/tracks/todaypolicy/bundle_mlpsf_tuck_v1/`.
- Bundle candidate: `todaypolicy-mlpsf-tuck-v1`.
- Stand/lower role: scripted tuck by default; compare learned
  `stand_stancemix_tuckclock_scratch8m{,_s1}` when useful.
- Walk role: `cw-walk-allheading-mlp-singleframe-acq1-stdanneal`,
  exported as `linux_control/policies/walk_allheading_mlp_singleframe_acq1_stdanneal.json`.
- Full-mesh evidence (`logs/manual_drive/cw_walk_allheading_mlp_
  singleframe_stdanneal_hybrid_tuck_ux_human28/`): zero falls, no
  sacrificed legs, progress_ratio 0.418, course_err_1s_med 2.57deg,
  wrong_course_frac 0.0. Stable and obedient, but speed-soft.
- Upgrade candidate: `cw-walkteach-scripted-allhead-acq12m{,-s1}`.

## Model And Control Contracts
- New PPO/MJX launches use mesh-family 100 Hz unless a registered
  legacy exception says otherwise.
- Checkpoints started before the 2026-08-24 mesh flip are
  primitive-family 25 Hz policies. Do not warm-start or evaluate them
  as mesh/100 Hz unless explicitly proven.
- `control_hz` metadata must match the runner; missing metadata means
  legacy 25 Hz. Policies output 18 raw joint targets through SafetyLayer.
- Long PPO acquisition launches should set `--log-std-final` from the
  start; uncapped `train/std` repeatedly ruined stochastic rollouts.
- TURN PIPELINE REVIEW (2026-09-08 00:52 UTC): the 43-rollout probe
  establishes undertracking for the tested controllers/settings, not a
  universal physical ceiling. Its model was 3.494226 kg versus the frozen
  audit's 4.80573 kg despite both having 34 meshes. Nominal-stance yaw arm,
  inconsistent scalar budget arithmetic, mixed planned/actual-contact
  selectors and discarded fit residuals do not establish impossibility
  or negligible slip. Preserve original qualification and physical limits;
  q_20260908T0050Z's assumed derating/universal training stop is superseded.
  Cycle 20260908T005017 owns a bounded SIM-only lift-phase comparison on
  pinned model/config hashes, existing seed and unchanged motor limits.
  See artifacts/rl_watchdog/turnpipeline_review_20260908.md.
  FOLLOW-UP (2026-09-08, on the frozen full-mesh plant, all zero-training):
  three in-limits scripted-gait dial levers were each measured against the
  same pre-registered both-signs-gain bar and all three CLOSED —
  lift-only phase lead (`artifacts/rl_watchdog/turn_liftlead_20260908/`,
  the executed gait is already phase-self-aligned), stance-posture
  yaw-arm extension (`artifacts/rl_watchdog/turn_stancearm_20260908/`,
  +19% arm gain sheds into loaded-pad slip instead of rotation), and
  cadence/`period_scale` (`artifacts/rl_watchdog/turn_cadence_20260908/`,
  BOTH directions regress -14%/-16% at period_scale 1.5 despite a
  confirmed swing-execution improvement — fractional lag -28%, lift
  tracking +272% — plus a NEW straight-line phase-dependent yaw-sign
  bias at the slower cadence). No 2M canary was justified for any of the
  three (bar unmet every time). Each closure's own vx side-finding
  (arm +12-21%, cadence +19%) is a candidate SPEED lever for the
  speed-soft walk stack, not a turn-authority fix — cadence's side-
  finding specifically WORSENS straight drift (unlike the stance-arm
  one, which halved it), so it needs its own bias fix before reuse.
  No further in-limits kinematic/timing/geometry dial remains nominated;
  the next lever (if pursued) needs a genuinely new mechanism (direct
  traction/force-budget diagnostic) or a fleet-wide plant/hardware
  contract change. Bounded simulation diagnostics are already authorized;
  a fleet contract change is a separate decision (q_20260908T0050Z).
  REVIEW CORRECTION (2026-09-08 03:31 UTC; supersedes FOLLOW-UP 2):
  Contact-wrench accounting passed the substep angular-momentum closure check.
  Opposing yaw moments and contact-couple contributions are measured, but do not
  uniquely establish inconsistent commanded stance paths. The original cone
  statistic was a planar slide projection. The completed 12-cell rerun preserves
  all original behavior and uses valid condim6 elliptic full-cone accounting:
  a contact is near the boundary in 48.0-58.5% of slipping-foot samples versus
  4.1-8.4% with the planar projection. Mixed sub-boundary/boundary behavior
  remains; this does not establish a unique cause. Evidence:
  artifacts/rl_watchdog/root_fullcone_20260908/. The isolated torsion dose0.1->0.005 m
  reduced scripted arc yaw magnitude9-14%, increased forward speed about17-20%,
  and changed straight drift, with zero observed falls in its six cells.
  The lower coefficient assumes a uniform-pressure contact patch; it is not
  measured calibration, an established physical cap, or proof that the original
  coefficient is unphysical. Modified-contact sensitivity is separate from
  frozen-plant qualification. No original both-signs/straight-health preflight
  passed, so no canary or fleet-model change follows from this evidence.
  Continue authorized simulation diagnostics without waiting for an operator
  reply on the separate fleet-calibration question.
  See artifacts/rl_watchdog/full_cone_review_20260908/CORRECTION.md.
  TWIST-CONSISTENCY REVIEW (2026-09-08): the six-cell frozen
  command-path measurement did not meet its preregistered support bar:
  commanded yaw gain about0.9998, residual0.015-0.018, and implied-yaw
  spread about0.00015rad/s. The proposed command-side stance-sweep
  correction remains unsupported; no canary follows. The original safe,
  actual-joint and pad summaries are descriptive and do not uniquely
  localize the execution loss. A matching triangular slew-amplitude
  estimate does not establish that the rate cap fully explains body motion
  or that friction-cone engagement is secondary. The repaired probe
  (7ca821fb1;46 tests including full-mesh trajectory parity) samples pad
  transforms at the private endpoint, labels solve-time contacts, adds
  planned-stance AND loaded-contact fits, validates the complete reference
  matrix, and distinguishes common wrong twist from simultaneous
  incompatibility. Original report comparison established exact body
  medians/count/fall parity, not recorded trajectory parity.
  Evidence: artifacts/rl_watchdog/twistfit_review_20260908/ and original
  artifacts/rl_watchdog/turn_twistfit_20260908/. Original continuous
  joystick tracking and qualification gates remain in force.
  Generic command-level walk/turn time slicing is not an executable next
  candidate: an earlier fixed-duty bank was already negative, and a
  transition-free mixture of the current matched endpoints predicts less
  yaw at equal achieved forward progress. A distinct measured transition
  mechanism would be required before revisiting it.

- SHARDED KNEE-FRAME FIX (2026-09-07): before commit dd248bd8/37c8e808,
  `MjxShardedVecEnv` workers stored raw mujoco-frame `q_nom` into
  `_q_nom`/`_cmd`/seq frames (missing `_mujoco_to_logical_q`), so every
  SHARDED-trained walk-task run saw its 6 knee-slot q_nom-relative obs
  shifted by +hip (~0.13 rad at the stand) vs the C/in-process
  reference the evals use. Invisible to the balance-env bitwise suite
  (its obs never read `_q_nom`); caught by
  `rl_move/tests/test_mjx_reverse_handoff.py`'s walk-task bitwise
  check. Fixed (worker now converts; sharded==in-process bitwise on
  walk task, 24/24 legacy MJX suite green). CONTINUITY: resuming a
  sharded walk checkpoint trained BEFORE the fix now sees a small
  obs-frame change at those 6 dims — judge such continuations on
  measured behavior; post-fix training finally matches the CPU eval
  frame (evals were always the correct frame).

## Run Interpretation
- Video and gate eval outrank reward alone.
- Simulated over_current is UNCALIBRATED (operator 09-04,
  fb_20260904T074505): a bit-exact 2.64 A pin is the actuator
  forcerange rail image (2.2 N*m x 1.2 A/N*m), not a measured stall;
  at trip threshold 2.9 the estimator (railing at 2.64) can never
  trip. Rail hits alone never fail a run or close a mechanism —
  corroborate with `audit_over_current.py` (CORROBORATED_STALL vs
  RAIL_MOVING) and report current telemetry separately. Evidence:
  `logs/ckpt_eval/oc_audit_09-04/OC_AUDIT_SUMMARY.md`. Real-robot
  protections stay untouched.
- Compare reward trend to gate/eval trend before spending more. Rising
  reward with flat/bad eval means audit reward, eval, simulator, or
  tooling before same-recipe seed sweeps.
- Bad eval with both reward and eval improving may justify continuation.
- Known exploit on video is a metric/tooling bug to repair, not a
  lineage kill by itself.
- walkcurr easy0905 bare recipe (freeprog income only,
  k_park_duty/k_walk_idle_charge/k_loadslip_excess all 0) + gSDE
  (`--use-sde`) reliably converges to a SACRIFICED-LEG QUADRUPED
  SHUFFLE at full gravity: 1-2 legs chronically airborne (duty
  0.00-0.23, single-digit ground touches per 20s episode) while the
  remaining legs take ~7mm micro-strides — clears the raw
  >=0.03 m/s floor and racks up near-full-episode reward (0 falls)
  while `gait_valid`-style checks fail and slip/m runs ~1.7-1.8x the
  2.9 teacher band. Confirmed on 3/3 full-gravity sde seeds
  (sde-s0-c4, sde-s1-c2, sde-s2-c2, 09-05) — gSDE-specific: the
  non-gSDE base/halfgrav families train cleanly under the identical
  bare recipe (4/4 ACQ PASS, six-leg video-confirmed). This is the
  SAME behavioral class the `WALKCURR_PF_IDLE_TERM` bank
  (`test_task_semantics.py`, 08-24) already diagnosed on the older
  pf_fwd lineage: soft anti-park prices ALONE leave the degenerate
  stance as PPO's cheapest optimum; the validated fix pairs
  `k_park_duty`/`k_walk_idle_charge`/`k_loadslip_excess` WITH a
  qvel-based `safety.walk_idle_terminate_s` termination. UPDATE 09-05
  ~13:1x: that qvel-idle-terminate port was tried
  (`cw-walkscratch-easy0905-sde-idleterm-{s0,s1}`, 2M canaries) and
  CLOSED — CANARY FAIL, detector-gamed not repaired: W&B scalars look
  escape-shaped (the `walk_idle_terminate` termination reason
  disappears from the final checkpoint's rollout captions,
  `ep_len_mean` triples) but the downloaded final-checkpoint video on
  both seeds shows the SAME static splayed-leg frozen pose as
  `sde-s0-c4` (on-screen speed 0.001-0.032 m/s, no leg mid-swing) —
  enough qvel/servo jitter dodges the specific threshold without the
  underlying pathology resolving into six-leg walking. Do not relaunch
  this qvel-idle-terminate variant on the sde family; the family's
  sole active repair candidate is now the structural
  `reward.walk_gait_gate` (`sde-s1-c3gg`/`sde-s2-c3gg`, already
  funded/training; `sdehalfgrav-remcost-*-gg*` mirrors it for the
  halfgrav+gSDE cell) — if that also fails, no cheap repair variant
  remains untried and a genuinely new per-leg-utilization pricing
  mechanism needs its own design+bank pass before further sde spend.
  Separately: `reward.walk_gait_gate` and
  `reward.k_walk_move_current` were tried against a related
  leg-sacrifice/rigid-tripod-lock exploit on the joystick track's
  harder full-DR `joyfullcurr13` curriculum (RL_LOG 08-25) and BOTH
  were CLOSED (made the fall rate worse, at every dose/architecture
  tried) — do not relaunch either lever here without accounting for
  that prior closure.
  UPDATE 09-05 ~14:3x: the `walk_gait_gate`+`k_step_event` structural
  repair (`sde-s1-c3gg`/`sde-s2-c3gg`) is now CLOSED too — 2/2 seeds
  ACQ FAIL (misaligned). It DOES partially work (multi-leg sacrifice
  narrows to exactly one chronically-parked leg per seed, duty 0.0,
  ~3 swings/20s) but harness `gait_valid` is still 1/24 and 0/24. Root
  cause read directly from `wandb_history.csv`: `env/walk_gait_gate_
  factor` sits at 0.98-0.99 for the ENTIRE back half of training even
  though the harness's stricter duty>0.10 bar flags the same leg as
  sacrificed the whole time — the reward-side gate's "recently
  completed swing" scoring window is satisfied by a rare token swing
  every several seconds and never drives the MIN-over-legs factor down
  the way a true duty-cycle price would. This is the SAME
  rare-token-dodge shape already seen on the qvel-idle-terminate
  lever, just via a different threshold. Both named bare-sde repair
  levers (idle-terminate, gait-gate) are now closed 2/2 each — per the
  09-05 ~13:1x note above, no cheap repair variant remains untried;
  any further sde revival needs a genuinely new per-leg-utilization
  mechanism (e.g. a hard minimum-duty/minimum-swing-count price, not a
  completion-score the policy can satisfy with one swing per many
  seconds) with its own design+bank pass. `sdehalfgrav-remcost-{s0,s1}
  -gg2` (same lever ported onto the remcost recipe) were left running,
  not preemptively killed — read their own report.json before assuming
  the same fate; the remcost recipe already prices term_cost
  differently and may not share the exact failure mode. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_sde_s{1,2}_c3gg_gate/
  report.json`, `logs/experiments/cw-walkscratch-easy0905-sde-s{1,2}-
  c3gg/wandb_history.csv`, W&B notes on `zr5lg756`/`vb2m7gr2`.
  UPDATE 09-05 ~14:4x: those two `sdehalfgrav-remcost-{s0,s1}-gg2`
  arms landed and it does NOT get a pass on remcost's different term
  pricing — both ACQ FAIL (misaligned), the SAME fingerprint (legs
  1/4 chronically parked, duty 0.0-0.03 nearly every episode,
  `gait_valid` 2/24 both seeds, `env/walk_gait_gate_factor` SATURATED
  at 0.985-1.0 for essentially the whole 40M run rather than a real
  ~0->1 climb). Video (`walk_det_0.png` contact sheets, both runs)
  shows the identical splayed-rigid-leg drag as the bare-sde FAILs.
  The `walk_gait_gate`+`k_step_event` lever is now CLOSED 4/4 across
  every recipe tried (bare sde x2, sdehalfgrav+remcost x2) — do not
  relaunch it anywhere in the sde/sdehalfgrav family; the per-leg-
  utilization pricing design question is fully open again pending a
  genuinely new mechanism (hard minimum-duty/swing-count price, not a
  gameable completion score). Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_sdehalfgrav_remcost_s{0,1}_gg2_gate/
  report.json`, `wandb_history.csv` for both runs, W&B notes
  `wrc80ii4`/`dq6gfe29`.
  UPDATE 09-05 ~15:4x: the remaining two bare-sde gg seeds
  (`sde-s0-c4gg`, `sde-s3-c1bgg`) landed and FAIL the same way --
  `gait_valid` 0/24 and 0/24 primary det (1/24 overall for c1bgg),
  legs [1]/[1,4] chronically parked, `env/walk_gait_gate_factor`
  saturated 0.81-1.0 (c1bgg) / 0.97-1.0 (c4gg) despite the sacrifice.
  **The `walk_gait_gate`+`k_step_event` repair is now CLOSED 6/6,
  fully confirmed across every bare-sde/sdehalfgrav-remcost seed
  tried -- do not relaunch it anywhere in this family.** The only
  surviving repair candidate is the newer `reward.walk_duty_gate`
  mechanism (per-leg trailing-duty income gate, built 09-05 ~15:1x,
  bank-proved in `test_walkscratch_easy_pilot.py`); its first 5
  canaries (`headset-base-s0c1-dgate-c1`, `sde-{s1,s2}-dg1`,
  `sdehalfgrav-remcost-{s0,s1}-dg1`) are mid-gate-eval as of this
  update -- read those before trying any further gait-gate variant.
  Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_sde_{s0_c4,
  s3_c1b}gg_gate/report.json`, W&B `q2kox1j4`/`bzf8msie`.
  UPDATE 09-05 ~16:0x, CORRECTED ~16:2x (provenance): 3 of those 5
  `walk_duty_gate` first-canary verdicts landed (`sde-s2-dg1`,
  `sdehalfgrav-remcost-{s0,s1}-dg1`) — all 3 **CANARY FAIL**, but per
  the respec-clone provenance gotcha directly above, NONE of them
  actually warm-started off a mature converged exploiter as first
  written: `sde-s2-dg1`'s real `--init-from` is `sde_s2.zip`, the
  ORIGINAL 2M canary that TERMINATES tilt_pitch (falls) in every
  single eval episode, not the 40M `sde_s2_c2.zip` exploiter; both
  `sdehalfgrav-remcost-{s0,s1}-dg1` carried NO `--init-from` at all —
  fully FROM SCRATCH with `reward.walk_duty_gate=1.0` from step 0.
  Re-reading with the correct ancestry: the gate factor itself
  behaved correctly (declined 0.69-0.92, i.e. penalizing, not
  saturating/gamed) and det-mode `gait_valid`/`sac` genuinely cleared
  (no chronically-parked leg) on all three — the specific one-leg-park
  exploit is prevented from forming at all. What emerged instead
  within the 2M budget was a DIFFERENT non-walking failure, split by
  recipe: `sde-s2-dg1` (from the falls-every-episode 2M ancestor)
  made real progress — stopped falling in det — but ends each episode
  having yawed ~174deg from start with current 0.30A->1.40A (a
  spin/destabilize pattern, not directed travel), falls 5/6 in sto;
  both `sdehalfgrav-remcost-{s0,s1}-dg1` (from scratch, remcost's
  term_cost pricing + duty_gate together) go to a FULL FREEZE (v
  0.001-0.037 m/s, net displacement 0.00-0.01m over the whole 20s det
  episode, slip 20-75x the ~2.9 band from leg micro-vibration with no
  net travel, falls 6/6 in sto) — a leg that never lifts keeps duty
  near 1.0, comfortably clearing the 0.15 floor even cheaper than a
  real gait (which necessarily drops a swinging leg's duty below
  ceiling), so full stasis is a strictly EASIER way to satisfy
  `walk_duty_gate` than walking is, AND this matches the remcost
  recipe's own launch hypothesis, which explicitly predicted "retreat
  to the ~0-income park basin" as its failure mode if term_cost
  pricing over-corrects toward fall-aversion — now confirmed directly
  from scratch, no warm-start confound needed. Reward for the remcost
  pair tracks their UN-gated from-scratch parents' own trajectories at
  matched absolute env steps almost exactly (not a new collapse from
  duty_gate; remcost is already this negative on its own).
  **Diagnosis: closes "walk_duty_gate=1.0 on the early
  falls-every-episode sde_s2 2M checkpoint" (n=1) and "walk_duty_gate
  =1.0 + remcost term_cost pricing, from scratch" (n=2) as repair
  recipes** — do not relaunch either exact combination; still NOT
  proof the `walk_duty_gate` mechanism itself is unsound absent
  remcost's fall-aversion pricing, since remcost's own term_cost is a
  plausible independent contributor to the freeze. Launched the
  disambiguating pair this cycle (from scratch, NO remcost pricing,
  NO inherited checkpoint at all): `cw-walkscratch-easy0905-sde-
  dgfresh-s0` / `-sdehalfgrav-dgfresh-s0` (2M canaries, `reward.
  walk_duty_gate=1.0` from step 0, otherwise identical to `sde-s0`/
  `sdehalfgrav-s0`) — read those before trying any further
  `walk_duty_gate` variant. If fresh init (no remcost) ALSO
  freezes/spins, the mechanism needs an explicit anti-idle complement
  (`reward.k_walk_idle_charge`, already implemented, 0 in every arm so
  far) paired with the duty floor before further spend, per this
  file's own note above that soft anti-park prices alone leave the
  degenerate stance as PPO's cheapest optimum. `sde-s1-dg1` /
  `headset-base-s0c1-dgate-c1` (the remaining 2 of the original
  5-canary batch) were not read this cycle — a concurrent cycle
  appears to own `sde-s1-dg1` (a sibling `cw-walkscratch-easy0905-sde-
  s1-c2-dgatefix` launch was found RUNNING on train-4 at cycle end,
  presumably that cycle's own repair attempt on this same finding —
  read its notes before assuming this entry is the last word; W&B logs
  show it already verdicted `sde-s1-dg1` itself as CANARY PASS
  scope-corrected, escapes LEGPARK in det with all-leg duty>=0.22).
  Evidence: `ops.sh review cw-walkscratch-easy0905-sde-s2-dg1` /
  `cw-walkscratch-easy0905-sdehalfgrav-remcost-s{0,1}-dg1`, W&B notes
  on the three verdicted runs (re-verdicted with FORCE=1 after the
  provenance correction).
  UPDATE 09-05 ~16:3x: the disambiguating fresh pair (+1 name-collision
  duplicate) all landed: `sde-dgfresh-s0`/`-s0b` (2 independent W&B
  runs, same recipe) and `sdehalfgrav-dgfresh-s0`, all **CANARY FAIL -
  MECHANISM (FULL FREEZE)**. `reward.walk_duty_gate=1.0` from step 0,
  NO remcost pricing, NO inherited checkpoint (fresh init) still
  converges to the identical fingerprint as the remcost dg1 pair: det
  walk fwd med 0.02-0.07m/20s, IDENTICAL to 2 decimals across all 6 det
  episodes (video-confirmed static splayed-leg pose, no leg mid-swing
  at any sampled tick), `env/walk_duty_gate_factor` saturated 0.92-1.0
  for the ENTIRE 2M run on all 3, `ep_rew_mean` quarters strictly
  worsening (not the 08-21 rising-reward-bad-eval case). **This closes
  the ambiguity for good: the freeze is intrinsic to `walk_duty_gate`
  itself** (a trailing-duty floor is trivially satisfied by keeping
  ALL SIX legs near-planted with zero net motion — cheaper than any
  real gait, which necessarily drops a swinging leg's duty below
  ceiling) — not an artifact of remcost's term_cost pricing, nor of
  warm-starting from an already-entrenched exploiter; both confounds
  are now independently ruled out. **`walk_duty_gate` alone is CLOSED
  as a from-scratch repair lever for the sde/sdehalfgrav leg-sacrifice
  pathology.** The sole remaining path is pairing it with
  `reward.k_walk_idle_charge` (the anti-park travel floor, already
  implemented, 0 in every arm to date) — this is a genuinely NEW
  design+bank pass (a joint duty-floor + travel-floor mechanism), not
  a relaunch of either lever alone; do not fund another bare
  `walk_duty_gate` arm (fresh OR entrenched-checkpoint) until that
  pass lands. The concurrent entrenched-checkpoint `dgatefix` batch
  (`sde-{s1,s2}-c2-dgatefix`, `sdehalfgrav-remcost-{s0,s1}-dgatefix`)
  is a separate confound (does duty_gate cure an ALREADY-entrenched
  exploiter) and should still be read on its own once it lands.
  Evidence: `ops.sh review cw-walkscratch-easy0905-{sde-dgfresh-s0,
  sde-dgfresh-s0b,sdehalfgrav-dgfresh-s0}`, W&B `8h25tu4l`/`vwnbmgq2`/
  `c3kd1elp`.
  UPDATE 09-05 ~16:4x: the from-scratch disambiguating pair landed —
  `sde-dgfresh-s0`/`-s0b` (accidental duplicate, same fingerprint) and
  `sdehalfgrav-dgfresh-s0` all **CANARY FAIL — FULL FREEZE**, 3/3 (a
  concurrent cycle's verdicts; independently corroborated here for
  `sde-dgfresh-s0`: det fwd 0.06m/20s across all 6 episodes, per-leg
  duty 0.75-0.96 but `stride_m_mean=0.001`/swing_count up to 302 in 20s
  — a high-frequency near-zero-amplitude leg vibration that satisfies
  the duty floor without producing a real step, not literal stillness).
  **Bare `walk_duty_gate` from scratch is now CLOSED**: the mechanism
  correctly prevents the one-leg-park exploit but a six-legs-all-
  planted (or all-vibrating) stance is a strictly cheaper way to clear
  a trailing-DUTY floor than any real gait, confirming the design note
  above. **CROSS-REFERENCE CORRECTION to the "Next: pair with
  k_walk_idle_charge" note every one of these three FAILs carried**:
  that pairing is NOT untested terrain — `cw-walkscratch-easy0905-sde-
  idleterm-{s0,s1}` (09-05 ~14:xx, FAIL) already ran `k_park_duty=4.0`
  + `k_walk_idle_charge=2.0` (`walk_idle_speed_m_s=0.025`, `tau_s=1.0`)
  + a HARD `safety.walk_idle_terminate_s=3.0` qvel-based cutoff on this
  exact sde/easy0905 base recipe, and STILL converged to the same
  static splayed-leg pose (on-screen speed 0.001-0.032 m/s): the
  qvel-based terminate got jitter-dodged (mean|qvel|>=2deg/s satisfied
  by servo micro-vibration with no coherent stepping — the SAME
  vibration-not-stride signature as the bare-duty-gate freeze above)
  and the soft idle-charge was simply paid down as an accepted ongoing
  cost, never escaped, within 2M. **Three independently-designed
  price/termination mechanisms now share one fate on this recipe**
  (`walk_gait_gate`+`k_step_event`; `k_park_duty`+`k_walk_idle_charge`+
  qvel-terminate; bare `walk_duty_gate`) — reward-shaping alone has not
  evicted the sde/easy0905 static-quiver absorbing basin within a 2M
  budget in 6 attempts. A `walk_duty_gate`+`k_walk_idle_charge` combo
  (dropping the dodgeable qvel-terminate, since idle-charge's own
  along-speed EMA prices BODY displacement not joint motion — a
  harder-to-fake signal) is a genuinely new combination and worth one
  more canary pair, but treat a 4th FAIL as closing "price-shaping
  alone" for this recipe and escalate to a structural intervention
  (BC/CPG-seeded init, a higher entropy/exploration schedule, or a
  moving-state curriculum start) rather than a 5th price variant.
  Launched: `cw-walkscratch-easy0905-sde-dgidle-{s0,s1}` (2M canaries).
  Evidence: `ops.sh review cw-walkscratch-easy0905-sde-dgfresh-s0`,
  `cw-walkscratch-easy0905-sde-idleterm-{s0,s1}` verdicts, W&B
  `8h25tu4l`.
  UPDATE 09-05 ~16:5x: 3 of the 4 entrenched-checkpoint `dgatefix` arms
  (`sde-s2-c2-dgatefix`, `sdehalfgrav-remcost-{s0,s1}-dgatefix` —
  `--init-from` verified pointing at each seed's real 40M LEGPARK
  checkpoint, not the provenance-bug-affected early ancestor) landed
  and all 3 are **CANARY FAIL - MECHANISM**, but with a THIRD distinct
  fingerprint, different from both prior closed patterns
  (saturating-factor-despite-sacrifice, and full-freeze): the factor
  genuinely DECLINES across training on all 3 (bare-sde 1.0->0.64,
  remcost-s0 1.0->0.72, remcost-s1 1.0->0.66 — real, ungamed
  penalizing pressure, not saturation) and there is no full-freeze —
  all 3 keep real forward speed (0.09-0.26 m/s) and net displacement
  (1.5-4.6m/20s). The mechanism is applying honest pressure to an
  already-entrenched exploiter; it just isn't enough to escape within
  2M. The two recipes diverge on reward direction though: bare-sde
  (`sde-s2-c2-dgatefix`) has ep_rew_mean quarters RISING throughout
  (94->224->332->406, the 08-21 rising-reward/bad-eval pattern — a
  genuine continue-candidate), while both remcost seeds have
  ep_rew_mean quarters WORSENING (-344->-495, -322->-582 — the
  exploiter absorbing more penalty for the same frozen 2-leg-park
  behavior without any escape appearing). All 3 stay at harness
  walk/det `gait_valid` 0/6 with the SAME 1-2 legs stuck at 0.00-0.01
  duty the whole clip (leg 1 alone for bare-sde; legs 1+4 for both
  remcost seeds — same leg pair both remcost seeds, suggesting a
  structural rather than random exploit). **Read together with the
  concurrent cycle's still-unverdicted `sde-s1-c2-dgatefix` (DIG-IN
  flagged, factor also declining 1.0->0.54, harness pending at time of
  writing) this makes 3/4 (soon 4/4) of the entrenched-checkpoint
  batch FAIL the 2M funding bar** — but unlike the from-scratch
  `dgfresh`/bare-`walk_duty_gate` closures, none of these show the
  mechanism being gamed; they show it working exactly as designed but
  arriving too late against a checkpoint that already spent 40M steps
  entrenching the sacrifice. This argues the next lever for the
  entrenched-checkpoint case specifically is a LONGER continuation of
  the most promising arm (`sde-s2-c2-dgatefix`, rising reward, no
  worsening) rather than a new mechanism — do not relaunch bare
  `walk_duty_gate` variants on these exact checkpoints without either
  (a) a longer budget on the one rising-reward seed, or (b) waiting
  for `sde-s1-c2-dgatefix`'s own harness read to complete the n=4
  picture. Evidence: `ops.sh review cw-walkscratch-easy0905-{sde-s2-
  c2-dgatefix,sdehalfgrav-remcost-s0-dgatefix,sdehalfgrav-remcost-s1-
  dgatefix}`, W&B `jw13d0rn`/`mmbhvbzs`/`m9sj7qzp`.
  UPDATE 09-05 ~17:2x: both `walk_duty_gate`+`k_walk_idle_charge`
  fresh-from-scratch canaries landed — `sde-dgidle-{s0,s1}` 2/2
  **CANARY FAIL — FULL FREEZE/VIBRATION** (s0: det fwd med 0.047m/20s,
  stride_m_mean 0.001m, duty 0.78-0.98 on all six legs via
  high-frequency in-place vibration not stride, slip_per_m 95.97 —
  33x the 2.9 band; sto/startjitter modes fall more, not less, 5-6/6
  terminations). **This closes reward-shaping-alone repair for the
  bare-sde/easy0905 LEGPARK-SKATE pathology for good: 6 independently
  designed price/termination mechanisms now FAIL (walk_gait_gate+
  k_step_event 6/6, k_park_duty+k_walk_idle_charge+qvel-terminate 2/2,
  bare walk_duty_gate fresh 3/3, walk_duty_gate on entrenched
  checkpoints 4/4 below funding bar, walk_duty_gate+k_walk_idle_charge
  fresh 2/2).** No further gSDE price/termination variant should be
  funded. Per this campaign's OWN launch hypothesis (`sde-s0`'s notes,
  verbatim: "ONLY change vs base-s0 is --use-sde"), the controlled A/B
  this closure needs was already run at launch time: the identical
  bare recipe passes ACQ cleanly on the non-gSDE base/halfgrav
  families (4+/4, six-leg video-confirmed) and fails on every gSDE
  seed tried (7+). **gSDE is the confirmed causal ingredient — CLOSE
  the gSDE sub-lineage entirely** (no further from-scratch or repair
  spend); the one live exception is `sde-s2-c2-dgatefix-cont40m`
  (entrenched-checkpoint, genuinely rising reward, 08-21-justified,
  already funded/running) — let it finish as a sunk-cost read, fund no
  NEW gSDE arms after it. Remaining walkcurr GPU budget belongs to the
  working base/halfgrav (Gaussian) curriculum ladder. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_sde_dgidle_s0_gate/
  report.json`, RL_LOG 09-05 17:2x, W&B `4ubnoqq3`.
  UPDATE 09-05 ~17:3x: `sde-dgidle-s1` (seed 1) independently confirms
  the SAME fingerprint — harness det walk fwd=0.10m/20s (IDENTICAL
  across all 6 episodes, deterministic), stride_m_mean 0.001m, duty
  0.72-0.97 on all six legs (high-frequency vibration not stride,
  matching `sde-dgidle-s0`'s own read) — the gSDE sub-lineage closure
  above is now n=2/2 on this exact price combo, not n=1. **Separately,
  the two non-gSDE `headset-{base,halfgrav}-fullhead-c1` full-8-way
  heading canaries (Gaussian families, NOT part of the gSDE closure)
  landed with a verdict CORRECTION worth recording**: the harness
  shows `gait_valid` 22/24 and 24/24 respectively (six legs cycling,
  forward_dist_m 2.3-3.4m/20s in EVERY episode, zero det falls) — a
  real, stable six-leg gait, not a collapse, contrary to what the
  training-rollout W&B averages alone suggested (`env/v_along_cmd_m_s`
  ~0.01 the whole run). The actual failure is course-tracking:
  `success` 0/24 both arms (walkcurr's own bar needs vel_err_mean
  <=0.03) because `direction_err_mean_deg` swings 28-161deg
  episode-to-episode as the 8-way command resamples — episodes near
  the original {0,+-45} training set track well (direrr 28-48deg,
  POSITIVE return, progress_ratio 1.3-2.4) while episodes drawing
  quarter-turn/reversal headings degrade hard (direrr 86-161deg,
  return down to -6416, negative progress_ratio). This is
  distance-graded generalization, not a binary break, and reconciles
  the W&B-only read (batch-averaged across all 8 headings including
  the badly-tracked ones). Both verdicts were corrected in place
  (FORCE=1) after this landed. Built + bank-proved the missing
  intermediate rung: `EASY_HEADING_MED` (5-way: 0,+-45,+-90, NO
  reversal beyond a quarter turn) in `test_walkscratch_easy_pilot.py`,
  5 new tests, 37/37 green (`walkcurr-headingmed-bank-0905` snapshot,
  pushed). Launched 2M canaries warm-started from each family's own
  small-set heading champion: `headset-base-medhead-c1` (train-1),
  `headset-halfgrav-medhead-c1` (train-2), both VERIFIED RUNNING —
  read those before attempting the full 8-way jump again on either
  family. Evidence: `ops.sh review cw-walkscratch-easy0905-sde-dgidle-
  s1`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_{base,halfgrav}
  _fullhead_c1_gate/report.json`, W&B `q3vgzdlu`/`a0zu90u6`/`xiajh8ja`.
  UPDATE 09-05 ~18:2x: `sde-s2-c2-dgatefix-cont40m` (the one live
  gSDE exception kept running as a sunk-cost read per the ~17:2x
  note above) landed at the full 40M budget — **ACQ FAIL**, gait_valid
  1/24, leg 1 (sometimes +4) chronically sacrificed, walk/det episodes
  IDENTICAL across all 6 draws (dead-leg drag, frame-strip-confirmed).
  Crucially, `env/walk_duty_gate_factor` genuinely declined 1.0->0.62
  through the first ~2M (the signal that licensed this continuation)
  but then MONOTONICALLY RE-SATURATED to 0.85-0.94 by 40M despite the
  persisting sacrifice — exactly the disqualifying condition the
  gate named at launch — while `ep_rew_mean` climbed hugely
  (90->2100+) on the other five legs' work and `env/walk_speed` stayed
  flat ~0.13-0.14 m/s throughout. **This closes the last live gSDE
  exception: the gSDE sub-lineage (bare-sde + sdehalfgrav-remcost,
  every repair mechanism tried, fresh-init or entrenched-checkpoint)
  is now CLOSED end-to-end. Fund NO further gSDE arm of any kind.**
  Separately, `headset-halfgrav-medhead-c1` (the halfgrav sibling of
  the base-family medhead canary) landed and independently confirms
  the base sibling's PASS shape: DR-0 harness `gait_valid` TRUE 24/24,
  zero sacrificed legs, zero terminations, slip_per_m med 2.4-3.7 (near
  the 2.9 band) — a genuine CANARY PASS despite `ep_rew_mean` falling
  -24.6->-164.5 (explained by a flat per-tick reward x the same fixed
  ep_len ramp the base sibling's PASS already characterized, not a
  collapse). 40M acquisition continuation `headset-halfgrav-medhead-
  acq1` launched (VERIFIED RUNNING train-2), mirroring
  `headset-base-medhead-acq1`. Evidence: `ops.sh review
  cw-walkscratch-easy0905-{sde-s2-c2-dgatefix-cont40m,headset-halfgrav-
  medhead-c1}`, W&B `66wc8jin`/`uxuboegj`.

  UPDATE 09-05 ~18:3x: `headset-base-s0c1-dgate2-c1` (the STRONGER
  `duty_gate_floor` dose, 0.15->0.35, retrying the DIFFERENT
  non-gSDE "marginal underuse" class -- one leg chronically at duty
  0.03-0.07 on an otherwise-healthy base-family heading walker, not
  the closed gSDE LEGPARK-SKATE pathology) landed: **CANARY FAIL -
  MECHANISM (INERT-DOSE, reconfirmed at 2.3x the prior dose)**. Direct
  parent-matched comparison (`headset-base-s0c1-acq1`'s own gate
  report vs this child, identical eval conditions): walk/det
  `gait_valid` 0/6 both, leg[4] sacrificed in ALL 6 episodes both,
  duty 0.04-0.06 (child) vs 0.03-0.07 (parent) -- statistically
  indistinguishable; walk_startjitter/det is if anything WORSE on the
  child (duty 0.01-0.03, swing_count down to 7-28/20s vs the parent's
  own baseline range). Video (`walk_det_*_sheet.png`,
  `walk_startjitter_det_2_sheet.png`) shows the identical single-leg
  hitched/tucked pose every sampled frame on both. This despite
  `env/walk_duty_gate_factor` genuinely declining in training
  (1.0->0.56, NOT saturated/gamed -- real pricing pressure, unlike the
  original 0.15-floor dose which stayed pinned 0.9-1.0 the whole run)
  and `ep_rew_mean` rising every quarter (27->62->114->124) -- i.e.
  the 08-21 "rising reward" signal IS present here, same shape as the
  gSDE `dgatefix` batch that earned a 40M continuation two entries
  above. **Read together with that continuation's own outcome
  (`sde-s2-c2-dgatefix-cont40m`, immediately above in this same file):
  factor decline + rising reward at a canary checkpoint did NOT
  predict eventual repair there either -- the factor MONOTONICALLY
  RE-SATURATED by 40M with the sacrifice unchanged.** Given (a) this
  child shows literally zero measurable delta from its own parent on
  every det-mode metric (a true null result, not partial progress),
  and (b) the one precedent for granting "more budget" on this exact
  factor-declining/reward-rising shape already played out negatively
  at full budget, this closes "raise `duty_gate_floor` magnitude
  alone" as a repair lever for the marginal-underuse class too (now
  2/2 doses inert: 0.15 never applied real pressure, 0.35 applies real
  training-time pressure but zero transfers to the deterministic
  policy). Root-cause read: `policy_std` is already at its
  end-of-schedule floor (0.135 rad, matching `--log-std-final=-2.0`)
  at 2M, yet stochastic-mode leg-4 duty (0.16-0.23) still diverges
  sharply from deterministic-mode duty (0.04-0.06) -- the training-time
  factor is computed on noisy rollout actions and is satisfied by
  noise-driven duty upticks that never need to move the policy MEAN,
  because the mean's alternative use of that leg apparently costs more
  elsewhere (speed/energy) than accepting the residual penalty. A real
  fix needs to price something the mean itself must satisfy (e.g. a
  much harder floor combined with an explicit per-leg exploration
  anneal so late-training noise stops masking the mean's own duty),
  not a bigger version of the same windowed-average floor -- this is a
  NEW mechanism+bank design question, not a relaunch of this lever. No
  new arm launched off this finding this cycle (sibling
  `headset-base-irr-dgate2-c1`, the irr-timing/1g composition retry of
  the identical dose, was still genuinely computing remotely on
  train-4 at this cycle's end -- registered via `ops.sh evalpending
  add`; read it before drawing the n=2 picture, though this entry's
  own parent-matched null result is already conclusive for the
  base/heading-only cell on its own). Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_base_{s0c1_dgate2_c1,s0c1_acq1}_gate/
  report.json`, `logs/experiments/cw-walkscratch-easy0905-headset-
  base-s0c1-dgate2-c1/wandb_history.csv`, W&B `j41igzz5`.

  UPDATE 09-05 ~19:2x — **`walk_duty_gate` is now CLOSED end-to-end
  on the base/non-gSDE family too, matching gSDE's earlier closure.**
  The one untried provenance variant, baking the strong floor
  (`duty_gate_floor=0.35`, `walk_duty_gate=1.0`) in from a LIGHTLY
  TRAINED 2M checkpoint (`headset-base-s0c1-dgfresh`, warm-started
  from `base_s0_c1.zip` before the leg-4 habit could fully entrench,
  as opposed to retrofitting onto the 40M-entrenched `s0c1-acq1`
  checkpoint) landed CANARY FAIL - MECHANISM: `env/walk_duty_gate_
  factor` genuinely declined 1.0->0.63 (real pricing) but harness
  leg-4 duty in `walk_startjitter/det` stayed statistically
  unchanged vs the undosed twin's own report (0.02-0.07 vs
  0.02-0.05), same leg sacrificed 6/6 both. Combined with the
  entrenched-checkpoint retrofit closure (2/2 FAIL at this same
  dose) and the from-scratch-full-freeze closure (3/3 FAIL, a
  different pathology), **every checkpoint-provenance case (fresh,
  early, entrenched) x every dose (0.15, 0.35) of `walk_duty_gate`
  is now FAIL on this family** — do not fund any further
  `walk_duty_gate`-class arm on ANY lineage; the marginal
  leg-favoritism pathology needs a genuinely new mechanism (explicit
  per-leg swing-count/utilization reward, bank-proven fresh, or a
  structural exploration-anneal change) before further spend.
  Evidence: `ops.sh review cw-walkscratch-easy0905-headset-base-
  s0c1-dgfresh`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  base_s0c1_dgfresh_gate/report.json` vs `..._headset_base_s0c1_
  gate/report.json`, W&B `8q0axo9n`.

  UPDATE 09-05 ~19:2x — the medium-heading-set (5-way) 40M
  acquisition run on the base(1g) family, `headset-base-medhead-
  acq1`, is ACQ FAIL: clears speed (fwd 1.9-2.6m/20s, ~0.09-0.13
  m/s) and falls (0/24 terminations) cleanly, reward still climbing
  every quarter (-279->398), but `gait_valid` is only 10/24 overall
  (det-mode majority sacrifices leg 1 or 4: walk/det 1/6,
  walk_startjitter/det 1/6) — well under the majority bar this
  campaign adopted. `direction_err_mean_deg` is also uniformly poor
  (22-60deg, 0/24 "success") even on the original {0,+-45} subset
  the earlier `fullhead-c1` canary tracked cleanly. This is the
  THIRD confirmation (after `s0c1-acq1`, `irr-acq1`) that the base
  (1g) family's leg-1/4 favoritism hardens into an outright gait
  failure under ANY added axis beyond flat/small-heading, while the
  halfgrav(0.5g) sibling family has cleared the irr-timing axis
  cleanly (its own medhead-acq1 read landed later this same cycle,
  see below). Working hypothesis: the pathology is gravity-linked
  (heavier per-step load at 1g makes the marginal leg's cost
  asymmetry harder to overcome), not heading-set-specific — flagged
  for the next design pass rather than another same-recipe 40M
  continuation on this lineage. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_base_medhead_acq1_gate/
  report.json`, W&B `8dtoak13`.

  UPDATE 09-05 ~19:2x — `headset-halfgrav-medhead-acq1` (the 0.5g
  sibling of the FAIL above, same rung/budget) landed **ACQ PASS**:
  `gait_valid` 22/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/sto
  6/6, walk_startjitter/det 4/6 — meets the majority bar exactly; the
  2 flagged episodes carry leg-4 duty 0.08-0.09, borderline-not-
  chronic, unlike the base sibling's 0.02-0.07-every-episode near-zero
  pattern), 0/24 falls, slip_per_m med 2.10-2.87 (at/under the 2.9
  band in 3/4 scenarios). This is the FIRST acquisition-scale PASS of
  the medhead rung on either gravity cell, confirming (2nd axis after
  irr-timing) that the gravity-linked-robustness-gap hypothesis holds:
  halfgrav clears every added generalization axis this campaign has
  tried, base does not. A root-cause-driven follow-up on the base
  cell (keep exploration noise alive longer alongside `walk_duty_gate`
  — `--log-std-final` -2.0->-1.2, otherwise identical to the just-
  closed `s0c1-dgfresh`) was launched same cycle:
  `headset-base-s0c1-dgnoise-c1` (2M canary, `train-1`, VERIFIED
  RUNNING). Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_
  headset_halfgrav_medhead_acq1_gate/report.json`, W&B `dejrlkhv`.

  UPDATE 09-05 ~20:4x — `headset-base-medhead2-acq1` (the base
  family's SECOND independent seed at the medhead rung, warm-started
  from a different champion than the FAIL above) is ALSO **ACQ FAIL**:
  8/24 gait_valid total (walk/det 0/6 leg 1 or 4 sacrificed every
  episode, walk/sto 6/6, walk_startjitter/det 0/6, walk_startjitter/
  sto 2/6), well under the majority bar; frame strip confirms one leg
  held rigid the whole clip. Reward is still climbing (quarters -238,
  -79,133,366) but per this same family's own established precedent
  (this is now the FOURTH base-family seed/champion — `s0c1-acq1`,
  `irr-acq1`, `medhead-acq1`, now `medhead2-acq1` — to entrench the
  identical leg-1/4 pathology at 40M budget) rising reward is not
  treated as license to continue; the base(1g)+medhead rung reads
  structurally closed pending a genuinely new per-leg-utilization
  mechanism (duty_gate/noise levers already closed separately, see
  above). Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  base_medhead2_acq1_gate/report.json`, W&B `47j1zemx`.

  UPDATE 09-05 ~20:4x — `headset-halfgrav-medhead2-acq1` (the
  halfgrav family's 2nd medhead seed, sibling of the PASS above) reads
  **CONTINUE, not FAIL/PASS**: walk/det clears the gate's own >=4/6
  bar (4/6) but walk_startjitter/det only hits 2/6 (16/24 total).
  Unlike the base family's hard 0.0-0.02 chronic park, the flagged
  legs' duty_cycle in the failing episodes is borderline (0.06-0.11,
  matching the FIRST seed's own accepted-as-PASS 0.08-0.09 range) and
  which leg gets flagged varies episode-to-episode rather than one
  leg parked every time; `ep_rew_mean` is genuinely still climbing
  (quarters -401,-419,-183,+30, net upward in the last ~10M steps)
  with `env/v_along_cmd_m_s` stable/not collapsing — matching this
  gate's own explicit CONTINUE clause. Launched a same-recipe 40M
  continuation from this exact checkpoint,
  `headset-halfgrav-medhead2-acq1-cont40m` (`--init-from-source`,
  VERIFIED RUNNING `train-0`) to let the marginal gait resolve before
  re-judging the halfgrav medhead rung's 2nd-seed status; do not fund
  a further continuation past this one on reward-climbing alone if it
  reads marginal again. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_halfgrav_medhead2_acq1_gate/
  report.json`, W&B `xa9a26bm`.

  UPDATE 09-05 ~20:2x — that noise-revival follow-up,
  `headset-base-s0c1-dgnoise-c1`, landed **CANARY FAIL - MECHANISM**,
  closing the "keep exploration noise alive longer" companion lever
  too. On the pre-registered gated mode `walk_startjitter/det`, leg-4
  duty is statistically IDENTICAL across the undosed twin
  [0.04,0.05,0.05,0.02,0.05,0.02], `dgfresh` (duty_gate, low noise)
  [0.07,0.06,0.06,0.04,0.06,0.02], and `dgnoise-c1` (duty_gate + high
  noise, `policy_std` read back 0.254 confirming the dose landed)
  [0.06,0.05,0.05,0.02,0.06,0.02] — `gait_valid` 0/6 all three, same
  leg sacrificed every episode, frame strip shows the identical
  planted/dragging leg. No regression: `walk/det`/`walk/sto`/
  `walk_startjitter/sto` all stayed 6/6 valid, 0/24 falls. Root cause:
  reviving exploration noise keeps the training-time factor mobile
  (as `dgfresh` already showed) but never reaches the eval-time
  DETERMINISTIC policy mean, which is what actually walks the gate —
  noise around the mean isn't the same as moving the mean. **Both
  named cheap companion levers (bake-in-early, revive-noise) for
  `walk_duty_gate` are now closed on the base/non-gSDE family too,
  matching gSDE's identical fate — no further duty_gate-class or
  noise-schedule-class arm on this marginal-leg-favoritism question.**
  The isolating control `headset-base-s0c1-noiseonly-c1` (noise
  alone, no duty_gate) was still computing at this update; read it
  before concluding noise contributes nothing at all on its own.
  Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_
  s0c1_dgnoise_c1_gate/report.json` vs `..._dgfresh_gate/`,
  `..._s0c1_gate/`, W&B `6b1c6hy4`.

  UPDATE 09-05 ~20:2x — `headset-base-s0c1-noiseonly-c1` (the noise-
  alone isolating control, no `walk_duty_gate`) landed **CANARY FAIL
  - MECHANISM, completing the full 2x2 {duty_gate on/off} x {noise
  low/high} grid.** Leg-4 duty on `walk_startjitter/det`
  [0.06,0.05,0.04,0.02,0.05,0.02] (med ~0.045) is statistically
  IDENTICAL to the undosed `s0c1` baseline (med ~0.045) AND to
  `dgnoise-c1` (duty_gate+noise, med ~0.05); `gait_valid` 0/6, leg
  [4] sacrificed every episode; `policy_std` reads back 0.254,
  matching `dgnoise-c1`'s own readback exactly (the dose landed
  identically in both — this is a genuine null, not underdosing). No
  regression: walk/det, walk/sto, walk_startjitter/sto all 6/6,
  0/24 falls. Full grid: s0c1 (off/low) ~0.045, dgfresh (on/low)
  ~0.06, dgnoise-c1 (on/high) ~0.05, noiseonly-c1 (off/high) ~0.045
  — **noise alone reproduces the undosed baseline exactly (zero
  effect on its own)**, and duty_gate's own small solo bump does not
  survive combination with noise. `walk_duty_gate` and plain
  exploration-noise scheduling are now BOTH fully refuted, every
  combination, on the base/non-gSDE family (matching the already-
  closed gSDE family) — no further duty_gate-class or noise-schedule-
  class arm anywhere in the headset-base family; a genuinely new
  per-leg-utilization mechanism (hard minimum-duty/minimum-swing-count
  price, not a training-time completion score gameable by noise or a
  rare token swing) needs its own design+bank pass before further
  spend on this axis. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_base_s0c1_noiseonly_c1_gate/
  report.json`, W&B `xyz4gzvh`.

## Known Tooling Gotchas
- **A new per-leg contact-bookkeeping mechanism must add its own gate
  flag to the SHARED activation-guard condition** in `sim_env.py`'s
  step() (the `if (... or g_dband > 0.0 or ...) and s_ref > 1e-3:`
  block every `walk_duty_gate`/`walk_swing_gate`/`walk_duty_band_gate`
  price shares) — forgetting it (2026-09-08,
  `reward.walk_leg_duty_ratio_charge`'s first launch) makes the new
  mechanism SILENTLY INERT (bit-identical to its own cfg being 0.0)
  on any recipe where every OTHER listed gate is also off, because the
  whole contact/EMA bookkeeping block never executes. Bank tests that
  inherit `WALK_OVERRIDES` (which already arms `k_step_event`/
  `k_drag_loaded`/`k_park_duty` etc.) will NOT catch this — they keep
  the shared block alive regardless of the new mechanism's own guard
  omission. A dedicated bank test using a SPARSE override dict (every
  other gate explicitly zeroed, matching the real launch recipe) is
  required to expose it; see
  `test_walk_leg_duty_ratio_charge_sparse_launch_activation`
  (`test_task_semantics.py`), added by the operator (commit
  `ebad6d0d`) after catching the omission in 4 already-launched
  canaries ~15 min post-launch. All 4 were verdicted `CANARY FAIL -
  INFRASTRUCTURE` and relaunched as `-guardfix1` twins on the fixed
  code; read those, not the originals.
- Any dedicated MJX assay/cert env built AFTER construction (a fresh
  `MjxVecEnv`/`MjxShardedVecEnv` stood up mid-training by a callback,
  e.g. `train_ppo_mjx._BcAnchorAnnealGateCb._build()`) does NOT
  automatically inherit a pure-walk (or any non-default) goal diet —
  `--goal-mix`/`args.goal_mix` is applied to the MAIN training venv via
  a POST-CONSTRUCTION `venv.env_method("set_goal_mix", gm)` call
  (needed because sharded MJX vec env objects live in worker
  processes); a freshly-built side env never receives that call unless
  the building code explicitly repeats it. Absent that, the env falls
  back to `config.yaml`'s default multi-mode mixture (`p_hold`=0.10/
  `p_lean`=0.15/`p_track`=0.15/`p_unload`=0.20/`p_raise`=0.15/
  `p_rise`=0.35, plus whichever task-specific `p_walk` default that
  task class sets in `__init__`, e.g. 0.70 for
  `SimHexapodJointWalkEnv`) — walk draws end up a MINORITY, not 100%,
  even when the parent run itself passed `--goal-mix walk=1.0` (that
  flag is also only PARTIAL/ADDITIVE — `set_goal_mix` just does
  `setattr(gen, f"p_{mode}", v)` per key given, it never zeroes the
  rest; only `goal.walk_pure=1` (construction-time, zeroes every
  `p_<mode>` then sets `p_walk=1.0`) or `eval_checkpoint.py`'s
  `ALL_MODES` per-mode forcing loop (same zero-then-set pattern)
  actually guarantee a pure single-mode diet). A non-walk goal draw
  has no `.vx` trajectory, so any code that reads `_goal_traj.vx`
  (e.g. walk_task.py's `cmd_dist`/`cmd_prog_m` accumulators) silently
  no-ops for that whole episode — `cmd_prog_frac` reads `nan`
  (division guard `cmd_dist > 0.01`), and `aggregate_walk_probe`'s
  plain-mean (by design — matches `eval_task`'s own nan rules) then
  poisons the ENTIRE round's aggregate to `nan`, independent of the
  real fall rate. Found 2026-09-06 via a standalone GPU repro
  (`MjxShardedVecEnv`, exact rung-2 cfg, zero-action policy: 5-6/8
  episodes nan before isolating goal mix, 0/8 after) while dig-in-ing
  the assistfade rung-2 anneal gate's persistent no-latch mystery
  (`cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m`, both FAIL -
  TOOLING). Fixed in `_BcAnchorAnnealGateCb._build()` (forces the
  zero-then-`p_walk=1.0` isolation via `set_goal_mix`); any FUTURE
  dedicated-assay-env builder in this file (or a new one) must do the
  same unless it genuinely wants a mixed diet. Evidence: 2 new tests
  `test_walkcurr_mjx.py::test_default_goal_mix_is_not_pure_walk_
  without_walk_pure_or_isolation` /
  `test_full_pure_walk_isolation_guarantees_a_walk_trajectory_every_
  reset`, snapshot `exp/bc-anchor-anneal-goalmix-fix`.
- Deferred final artifacts are the LAUNCHER DEFAULT since 09-06 for
  compatible runs (GPU MJX trainer + W&B; never smokes/dynrep/CPU):
  `launch_run.py` injects `--defer-final-artifacts`, the GPU trainer
  exits minutes early and a detached CPU finalizer delivers eval/video
  to the same W&B run (live-verified end-to-end on
  `medhead-widenfwd-c2-acq1`/inb67bzx, 3/3 artifacts, GPU reused
  mid-finalize). Consequences: a deferred run's trainer process
  disappearing does NOT mean artifacts are done — verdict on registry
  phase=evaluated (`ops.sh handoff <run>`) or the watcher's prestage
  evals. Ledger provenance: `checks.defer_final_artifacts`. Rollback:
  `gpu.defer_final_artifacts: false` in guardrails.yaml; per-run
  opt-out sentinel `--no-defer-final-artifacts` (launcher strips it).
- A run's gate podeval can go silently ORPHANED (09-05,
  `headset-base-s0c1-acq1`): the prestage `pullckpt` step can finish
  while `eval_checkpoint` is still computing on the run's own pod; if
  a DIFFERENT concurrent cycle's drain then reuses that same pod for
  its NEXT training launch, the harness keeps computing fine (spare
  CPU, no conflict with the new GPU trainer) but the local supervisor
  that was meant to poll+copy it back is gone, so `logs/ckpt_eval/
  ..._gate/` never appears though nothing crashed. `ops.sh podeval
  <run>` correctly reports the pass `already RUNNING` and won't
  duplicate it, but that alone does not re-attach a poller — follow
  with `ops.sh pollreap <run> [interval_s] [max_min]` (backgrounded)
  to wait for the remote pass and sync it back.
- Recurrent checkpoints must use `rl_move.sim.gru_policy.RecurrentPredictor`;
  raw per-tick `model.predict(obs)` resets hidden state.
- `eval_checkpoint.py`'s `--stochastic` pass never resampled a gSDE
  checkpoint's exploration matrix between episodes (SB3's
  `model.predict()` only samples fresh gSDE noise via
  `collect_rollouts` during TRAINING, never inside `predict()` itself)
  -- so every "sto" episode of a gSDE checkpoint reused ONE frozen
  noise draw for the whole eval process. In any goal mode with no
  per-episode init randomization (plain fixed-forward `walk`, not
  `walk_startjitter`), that made every sto episode bit-identical to
  the others (confirmed 09-05: `sde-s3-c1b`'s `walk_sto_{0..5}.mp4`
  shared one MD5; `walk_startjitter_sto_*`, which DOES randomize the
  start pose, varied normally). This silently turned every gSDE "sto"
  panel across the whole `sde`/`sdehalfgrav`/`sdehalfgrav-remcost`
  09-05 easy-sim cohort into an n=1 noise-draw report dressed up as
  n=6 -- re-read any "6/6 sto fail" claim for those families as "one
  noise draw failed," not "robust failure across draws." Fixed
  09-05 (`_maybe_reset_gsde_noise` in `eval_checkpoint.py`, called at
  the top of every `run_episode`): resamples once per episode for any
  `use_sde=True` model (direct or through a wrapper's inner `.model`,
  e.g. `Rot60Policy`); bit-exact no-op for the non-gSDE default.
  4 new tests, `test_eval_checkpoint_gsde_reset_noise.py`. Any
  PRE-FIX gSDE sto read (every sde/sdehalfgrav gate before this
  commit) should be treated as informationally thin on stochastic
  robustness specifically -- their det-pass gait_valid/sacrificed-leg
  findings are unaffected (deterministic mode never uses gSDE noise).
- Some post-08-24 100 Hz evals before the `pod_eval.py` fixes may have
  wrong timeout/slew-contract evidence; re-run suspicious gates.
- Train pods have non-uniform `/dev/shm`; route obs-heavy launches to
  4.0G pods or let `_check_shm_budget` refuse them.
- Pre-09-02 checkpoints lack the `joint_frame` stamp and get rejected
  by `--init-from`/respec; fleet backfilled via
  `rl_move.sim.stamp_legacy_checkpoint` (bit-exact) — re-run on any
  `joint_frame=None` ckpt, don't relax the check.
- `--activation-fn`/`--use-sde` + a plain `--init-from` warm start is a
  hard `SystemExit` in `train_ppo_mjx.py` (PPO.load already restores
  the checkpoint's own activation/gSDE; the CLI flags only apply to
  from-scratch/transplant builds). Dies in ~2s, `wandb` reports
  `exit_code 0`/`runtime 0` — looks like a clean tiny run, not a crash,
  unless you check for zero logged steps. `respec --init-from-source`
  clones the WHOLE source arg vector including these flags — do not
  use it to continue a gSDE-family checkpoint. Fix: respec from a
  non-gSDE sibling (matching seed) with `--arg='--activation-fn='`
  (blank) + `--arg='--init-from=<ckpt>'` only (09-05, easy0905
  sde-s1-c1/sde-s2-c1 both hit this; sde-s1-c2/sde-s2-c2 fixed).
  **The "non-gSDE sibling" MUST itself never carry a bare `--use-sde`
  flag** — respec'ing from another gSDE arm (e.g. `sde-s1` to continue
  `sde-s0`) and blanking only `--activation-fn` leaves `--use-sde`
  in the cloned vector and re-triggers the SAME SystemExit (recurred
  09-05: `sde-s0-c2` respec'd from `sde-s1`, died in <1s). Always
  respec from the matching-seed `base-*` arm, never from any `sde-*`
  or `sdehalfgrav-*` arm, when building a gSDE-checkpoint continuation.
  **Scope is bigger than gSDE**: ANY non-blank `--activation-fn` (incl.
  plain `elu`) on top of a plain `--init-from` trips the SAME guard —
  `headset-halfgrav-c1` died this way 09-05 (elu, no gSDE at all).
  Always blank `--activation-fn=` on every `--init-from`/
  `--init-from-source` continuation, gSDE or not.
- **`respec` has NO flag-removal primitive** (09-05,
  `sdehalfgrav-remcost-{s0,s1}-gg`): `--arg` can only set/add a flag's
  VALUE or append a missing bare flag — it cannot strip a bare flag
  (e.g. `--use-sde`) the SOURCE run already carries. Two failure modes
  found back-to-back building a gait-gate continuation of the
  `sdehalfgrav-remcost` arms (source carries `--use-sde --activation-fn
  elu`, itself correct since remcost was a from-scratch launch, no
  `--init-from`): (1) plain `respec --from <src>` with no
  `--init-from-source` at all silently queues a FRESH-SCRATCH clone —
  no crash, no error, `wandb` looks like a completely normal run
  (caught here only via `ops.sh procs` showing no `--init-from` in the
  live cmdline); (2) adding `--init-from-source` reproduces the
  documented SystemExit gotcha above, because `--use-sde`/`elu` ride
  along uneditable. **Fix**: when the SOURCE itself is a from-scratch
  gSDE/non-default-activation launch (not itself a clean `--init-from`
  continuation), don't use `respec` for the follow-up at all — pull
  the source's own `extra_args` from the ledger, hand-strip `--use-sde`
  (+ its paired `--sde-sample-freq <n>`) and blank `--activation-fn`
  in a plain Python list, append the new `--cfg-set`s + a fresh
  `--init-from <ckpt>.zip`, then submit via
  `launch_run.py backlog add ... -- <that arg list>` (which accepts a
  fully explicit vector, bypassing clone-and-patch entirely). Always
  confirm post-launch with `ops.sh procs <pod>` that the live cmdline
  has `--init-from` and no `--use-sde`, not just the ledger fields.
- **`respec --from <src>` without `--init-from-source` silently inherits
  the SOURCE's own `--init-from` value verbatim, not the source's own
  trained OUTPUT checkpoint** (09-05, confirmed on the `walk_duty_gate`
  4-arm mechanism-health batch): cloning `sde-s1-c2`'s arg vector for
  `sde-s1-dg1` carried over c2's own `--init-from
  .../ppo_goal_cw_walkscratch_easy0905_sde_s1.zip` (c2's PARENT, the
  original pre-LEGPARK 2M canary) unchanged — nothing in a plain clone
  points at c2's own output (`sde_s1_c2.zip`). `sde-s1-dg1` therefore
  trained duty_gate from an early undifferentiated checkpoint, not a
  cure of the entrenched LEGPARK-SKATE policy its own hypothesis/parent
  field claimed to test. Confirmed on the sibling `sde-s2-dg1` too
  (init-from = `sde_s2.zip`, its grandparent). **Strictly worse** when
  the source itself carries NO `--init-from` at all (e.g. a from-scratch
  gSDE launch like `sdehalfgrav-remcost-{s0,s1}`): the clone then has NO
  `--init-from` either, so `sdehalfgrav-remcost-{s0,s1}-dg1` are running
  FULLY FRESH-FROM-SCRATCH, not continuing the LEGPARK checkpoint — an
  exact recurrence of the earlier-documented "silently queues a
  fresh-scratch clone" gotcha (see the `respec` flag-removal entry
  above), this time via the plain-clone path instead of the
  `--init-from-source` path. **Always verify a respec'd continuation's
  ACTUAL `--init-from` in the ledger `command`/`extra_args` (or live
  `ps`), never assume the note text or `parent` field describes the
  real checkpoint** — either use `--init-from-source` (rewrites
  `--init-from` to the source's own output) or, if the source's own
  vector needs editing anyway (gSDE/non-default-activation sources),
  hand-build the arg vector via `backlog add` with an explicit
  `--init-from <src's own output>.zip`. Read any already-launched
  `*-dg1` result with this in mind before trusting its "does duty_gate
  cure an entrenched checkpoint" framing — `sde-s1-dg1`'s own PASS is
  real evidence duty_gate escapes LEGPARK from an early checkpoint, but
  is NOT yet evidence it cures an already-entrenched skate policy.
- `launch_run.py respec` defaults `--steps` to the SOURCE run's own
  step count, not the intended budget. Respec'ing a 40M continuation
  `--from` a 2M-CANARY-scale sibling (e.g. `base-s0`, the original
  canary, instead of `base-s0-c1`, its 40M acquisition continuation)
  silently trains only 2M steps — no crash, no error, just the wrong
  budget (09-05: `sde-s0-c3` did this, caught by checkup after it
  finished at 2M; fixed as `sde-s0-c4` with an explicit `--steps
  40000000`). Always pass `--steps` explicitly on a respec whose
  source lineage might include a canary-scale entry; never rely on
  "default: same as source."
- Same class again (09-05, `fullhead-widen2-c2`): a "2nd seed" of a
  curriculum arm can silently warm-start from the WRONG sibling's
  checkpoint if the launching cycle names the wrong `--init-from` in
  a hand-built `backlog add` vector — the notes text said "the 2nd-seed
  medhead2 champion" but the actual `--init-from` pointed at
  `medhead2_c1.zip` (a 2M CANARY) instead of `medhead2_acq1.zip` (the
  matching 40M champion `widen2-c1` used). Always diff the ACTUAL
  `--init-from` value in the ledger `command`/`extra_args` against
  what a sibling arm used before reading a "2nd seed" result as a
  clean recipe replication — a checkpoint-maturity confound produces
  a real-looking but uninterpretable divergence (here: 16x worse slip)
  that has nothing to do with the recipe being tested.

## Walkcurr Reward Mechanisms (per-leg utilization)
- `reward.walk_leg_duty_ratio_charge` (2026-09-08, built + bank-proved
  this cycle, `test_walk_leg_duty_ratio_charge_*` in
  `test_task_semantics.py`, 9 new tests + 5 adjacent legduty tests
  reconfirmed, 14/14 green, default 0 = off/bit-exact): the mechanism
  scoped since 09-07 ~23:2x/~23:4x as the "duty-balance reward TARGET"
  once BOTH the per-tick-price class (11 arms: `walk_duty_gate`,
  `walk_swing_gate`, `walk_duty_band_gate`, `walk_gait_gate`+
  `k_step_event` — every one an income-MULTIPLYING factor) and the
  termination class (`safety.walk_leg_duty_terminate_s`, 8/8) both
  closed FAIL against the chronic front-pair/middle-pair leg
  sacrifice. Different SHAPE from both: an independent ADDITIVE
  per-tick charge (never multiplies `r_walk`/`r_prog`/`r_cmd_track`,
  so it cannot be "simply outbid" the way every closed multiplicative
  gate could be) with NO episode cutoff (nothing to pay off as
  ambient cost the way the termination class was), keyed on the
  09-07 ~23:4x calibrated peer-excluded-mean duty ratio (target 0.30
  = the passing population's own p10 worst-leg ratio). Answers the
  open question every one of the 19 prior mechanisms' own closure
  notes flagged as never demonstrated — **can a per-tick mechanism
  flip a leg-sacrifice cheat's FULL episode return below the honest
  gait's own return, not just shrink it toward zero** — empirically,
  YES: bank-proved (scripted rollouts, no training) that at a modest
  dose (150.0) the honest six-leg gait's return is BIT-EXACT
  untouched (3113.8, unchanged across a 50x-3000x dose sweep) while
  BOTH the hard flag-leg cheat (1323.9 undosed -> -14785.3 dosed) AND
  a NEW soft/marginal ~10%-duty starvation actor built this cycle
  (`_gait_gate_walk_rollout_softleg`, mimicking the ~0.02-0.11 duty
  real 40M-trained checkpoints actually show, not just the hard
  synthetic every prior bank tested) flip net NEGATIVE, decisively
  below the honest gait's own dosed return. First real-training test:
  4 canaries launched (2M each, phase=canary) — `s0`/`s1`-widen8-acq1-
  legdutyratiofresh (fresh provenance, 2 seeds), `s0`-widen8-acq1-
  legdutyratio1 (`--init-from-source` RETROFIT onto the actual
  entrenched 40M checkpoint), `s0`-widenbis180-legdutyratiofresh
  (fresh, milder 6-way lineage) — all VERIFIED RUNNING/FINISHED
  09-08 ~00:2x. UNVERDICTED as of this entry; read the gate reports
  before funding any further dose/lineage variant. Evidence:
  `rl_move/sim/walk_task.py` (search `walk_leg_duty_ratio`), STATUS.md
  2026-09-08 ~00:2x, snapshot `e24a2ab6`.
  UPDATE 09-08 ~01:5x: all 4 guardfix1 canaries now read. **3/3
  fresh-init arms CANARY PASS** (`s0`/`s1`-widen8-acq1-legdutyratio-
  fresh-guardfix1 both 21/24 `gait_valid`, 0 terminations;
  `s0`-widenbis180-legdutyratiofresh-guardfix1 18/24, exactly clears
  its own bar). These establish activation and mechanism health,
  not causal recovery. Both s0 arms actually initialize from the
  trained `s0_acq1` (21/24 on its own 5-way gate, not a matched
  baseline for the new 8-/6-way tasks); s1 initializes from the
  already-8-way `s1_widen8` (21/24). Matching inert 2M predecessors
  scored 22/24, 22/24 and 18/24 versus corrected 21/24, 21/24 and
  18/24, all with zero terminations. The corrected s0 fresh report
  has 3/24 sacrifice episodes, not 2/24; the latter was the inert
  predecessor. Three arms use two RNGs, and the s0 arms share an
  initialization. Comparisons with longer termination-reward arms
  do not isolate this charge's effect. Exact evidence:
  `artifacts/rl_watchdog/fresh_init_claim_review_20260908.md`.
  **The RETROFIT arm (`s0`-widen8-acq1-legdutyratio1-guardfix1) is
  CANARY FAIL - MECHANISM**, self-corrected mid-cycle: an episode-by-
  episode diff against the undosed `s0-widen8-acq1` baseline shows the
  two share the 20/24 gait-valid and failing-episode/leg pattern;
  identical policies or numerical rollouts are not established.
  Telemetry confirms the charge fires correctly (shortfall
  0.14-0.17) — 2M steps produced no improvement in those gate fields
  on an already-entrenched exploiter. **Do not read this as "the mechanism
  doesn't work"** — it is one short-budget retrofit result, not a
  from-scratch result; the other three canaries establish health,
  not efficacy.
  Methodological note for every arm: `ep_rew_mean` crashes hard
  through training on this reward shape (e.g. 31->63->-903->-3589)
  while `rollout/ep_len_mean` rises. Longer episodes can accumulate
  more negative per-tick charge; that does not by itself establish
  improvement or collapse. Inspect normalized reward and held-out
  gait/fall/progress/slip metrics before attributing the curve.
  A +10M acquisition continuation
  of the fresh-PASS `s1` checkpoint plus a matched charge=0 control
  (`...-acq10m`/`...-offctrl10m`) are in flight (concurrent
  cycle/root) — read those before any further dose/lineage spend;
  the retrofit-onto-entrenched question stays open (1 short-budget
  arm only). Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_
  headset_crossgrav_medhead_dr_allaxis_nokick_crutchoff_{s0,s1}_
  widen8_acq1_legdutyratiofresh_guardfix1_gate/report.json`,
  `..._s0_widenbis180_legdutyratiofresh_guardfix1_gate/report.json`,
  `..._s0_widen8_acq1_legdutyratio1_guardfix1_gate/report.json` vs
  `..._s0_widen8_acq1_gate/report.json`.
- `reward.walk_swing_gate` (09-05, built + bank-proved this cycle,
  `test_walk_swing_gate_*` in `test_task_semantics.py`, 4/4 green,
  default 0 = off/bit-exact): the 6th structural repair attempt for
  the base(1g)-family chronic leg-favoritism pathology, after
  `walk_gait_gate`+`k_step_event` (CLOSED 6/6 FAIL — a rare token
  swing every several seconds keeps a recency-decay score near 1.0
  without a real gait forming) and `walk_duty_gate` (CLOSED
  9/9 FAIL across every provenance x dose — a fully planted OR
  high-frequency in-place-vibrating stance clears a trailing
  contact-DUTY floor more cheaply than any real gait, since a planted
  foot's duty is trivially 1.0) both closed end-to-end earlier the
  same day. `walk_swing_gate` keeps `walk_gait_gate`'s stride-filtered
  qualifying-swing definition (liftoff -> >=2 ticks airborne ->
  touchdown with XY stride >= `gait_gate_stride_mm`, so a chattering/
  vibrating non-displacing "swing" never counts — closes the
  duty_gate exploit by construction) but replaces the recency-decay
  score with a trailing-window COUNT (`swing_gate_min_count`,
  default 2, within `swing_gate_window_s`, default 4.0) — a leg
  stepping once every several seconds cannot clear a >=2-per-window
  count bar the way it cleared a >=1-per-(window+fade) recency floor,
  closing the gait_gate exploit by construction. MIN over support
  legs, same as every prior anti-sacrifice gate in this file. First
  canary batch launched same cycle: fresh-provenance
  `headset-base-s0c1-swinggate-fresh` + three entrenched-checkpoint
  retrofits (`swinggate-fix` on `s0c1_acq1`, `medhead-swinggate-fix`
  on `medhead_acq1`, `irr-swinggate-fix` on `irr_acq1`).
  UPDATE 09-05 ~22:2x: `swinggate-fresh` (the fresh-provenance arm)
  landed **CANARY FAIL — MECHANISM (INERT DOSE)**: harness result is
  statistically indistinguishable from the undosed `dgfresh` twin —
  `walk/det` 6/6, `walk/sto` 6/6 (both match exactly), `walk_startjitter/
  sto` 5/6 with the SAME episode (idx4) failing in both, and
  `walk_startjitter/det` (the canary's own named test mode) stays 0/6
  in both with leg4 duty 0.03-0.06 here vs 0.02-0.07 in `dgfresh` —
  chronically <=0.10 in all 6/6 episodes, the identical fingerprint
  every prior mechanism left. `env/walk_swing_gate_factor` logged
  saturated at 1.0 at every sampled point across the whole 2M run
  despite leg4's chronic near-zero duty the entire time — the gate's
  own pre-registered "gamed-completion-score" clause: leg4 still
  completes enough swing-like liftoffs per 4s window (swing_count
  26-55/20s) to clear the trailing-count floor without ever
  contributing real stance/transport, so the price never engages.
  **Closes the fresh-provenance half of the swing_gate test**:
  pricing the mechanism in before the habit entrenches does not cure
  it when the checkpoint (2M) already exhibits the chronic pattern.
  UPDATE 09-05 ~22:2x-22:3x: all 3 entrenched-checkpoint retrofits
  landed too, same cycle. `swinggate-fix` (on `s0c1_acq1`) **CANARY
  FAIL — MECHANISM (INERT DOSE)**: harness virtually IDENTICAL to the
  undosed `s0c1_acq1` twin on all 4 modes (walk/det 0/6 both,
  walk/sto 6/6 both, walk_startjitter/det 0/6 both, walk_startjitter/
  sto 3/6 both) — an even cleaner null than `swinggate-fresh` since
  this compares directly against its own true parent. `medhead-
  swinggate-fix` (on `medhead_acq1`) **CANARY FAIL — MECHANISM
  (engaged, no repair)**: 11/24 gait_valid vs the undosed twin's own
  10/24 — noise-level, same leg1/4 alternating sacrifice pattern,
  neither det mode majority-clears. `irr-swinggate-fix` (on
  `irr_acq1`) **CANARY FAIL — MECHANISM (engaged, no repair)**: 17/24
  vs the undosed twin's own 18/24 — noise-level, same pattern.
  **`reward.walk_swing_gate` is now CLOSED end-to-end as a per-leg-
  utilization repair lever for the base(1g) family, 4/4 arms FAIL
  (2 cleanly inert, 2 noise-level marginal, zero majority-clearing
  repair anywhere) — the 7th independently-designed mechanism to fail
  after `walk_gait_gate`+`k_step_event` (6/6 FAIL) and `walk_duty_gate`
  (9/9 FAIL across every provenance x dose).** Do not fund ANY further
  reward-price mechanism for base(1g)-family leg favoritism without a
  genuinely new causal theory (not another gate/floor/count variant on
  the same "price the missing behavior" idea — that idea class is now
  exhausted at n=7 designs x every provenance). The next lever must be
  structural: curriculum-widen from a leg-healthy champion (the way
  halfgrav's `widen2` thread is doing, since halfgrav does NOT show
  this pathology), a different exploration/init scheme, or accepting
  the base(1g) family's per-leg pathology as closed and reallocating
  spend to the healthy halfgrav lineage. Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-base-{s0c1,irr}-swinggate-fix`,
  `cw-walkscratch-easy0905-headset-base-medhead-swinggate-fix`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_{s0c1,medhead,
  irr}_swinggate_fix_gate/report.json` vs each one's own `_acq1_gate`
  twin, W&B `3f8el794`/`2vlzxnoh`/`2j266hc8`/`4rnm653m`.
  UPDATE 09-05 ~22:5x: the halfgrav-family confirmation also landed
  and also FAILS. `headset-halfgrav-medhead2-swinggate-fix` (retrofit
  onto the FAILED `headset-halfgrav-medhead2-acq1-cont40m` checkpoint,
  own ACQ FAIL plateaued at `walk_startjitter/det` 2/6 through 80M):
  **CANARY FAIL — MECHANISM (engaged, no repair)** — `env/walk_swing_
  gate_factor` sampled 0.93-1.0 (genuinely live, not saturated-inert)
  but `gait_valid` lands IDENTICAL to the undosed parent on all 4
  modes (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 2/6,
  walk_startjitter/sto 4/6); every failing episode's flagged-leg duty
  stays 0.03-0.09, still under the 0.10 pass bar. **`reward.
  walk_swing_gate` is now CLOSED end-to-end across BOTH gravity
  families, 5/5 arms FAIL** — do not fund it on any further checkpoint/
  family. Refill reallocated to the halfgrav lineage's own validated
  `widen2` heading-widen curriculum, composed with the already
  ACQ-PASS `irr` timing-jitter rung in both orders (`headset-halfgrav-
  irrwiden-c1`, `headset-halfgrav-widenirr-{c1,c2b}`, 3 arms VERIFIED
  RUNNING) — see `rl_docs/tracks/walkcurr/STATUS.md` 09-05 ~22:5x for
  the full hypothesis. Evidence: `ops.sh review cw-walkscratch-
  easy0905-headset-halfgrav-medhead2-swinggate-fix`, `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_halfgrav_medhead2_swinggate_fix_
  gate/report.json`, W&B `jkh3xzb5`.
- **STRUCTURAL DIAGNOSTIC (09-05 ~22:3x, new this cycle, not yet acted
  on): the base(1g)-family chronically-sacrificed leg is NEVER random
  — across every mechanism/checkpoint logged above (`walk_duty_gate`
  remcost seeds: legs [1,4]; `dgatefix`/`dgate2` bare-sde: leg 1;
  `swinggate-fresh`/`swinggate-fix` (s0c1 lineage): leg 4 only;
  `medhead-swinggate-fix`/`irr-swinggate-fix`: legs 1 and 4
  alternating) the flagged leg(s) are ALWAYS L1 and/or L4 — checked
  the mesh model's own leg-mount coordinates
  (`mesh_mujoco/hexapod_mesh.xml`, `L*_yaw` body `pos`): L0=(0.087,
  0.05), L1=(0,0.10), L2=(-0.087,0.05), L3=(-0.087,-0.05),
  L4=(0,-0.10), L5=(0.087,-0.05) — a regular hexagon, and L1/L4 are
  the ONE diametrically-opposite pair with NO close fore/aft
  neighbor (L0/L5 are the front pair, L2/L3 the rear pair, L1/L4 the
  sole left/right MIDDLE pair). A hexapod is statically stable on any
  4+ legs forming a valid support polygon, so a front-pair+rear-pair
  (4-leg) gait that idles exactly the two structurally-redundant
  middle legs is a genuinely cheaper stable gait under 1g's higher
  torque cost — not a random exploit, and not something any of the 7
  MIN-over-all-6-legs anti-sacrifice reward mechanisms tried so far
  could distinguish from a real leg outage, since they all price
  every leg identically regardless of hexagon role. This reframes the
  next design pass concretely: a role-aware mechanism (weight the
  middle-pair's contribution differently, or reward a genuine
  6-leg tripod/alternating-tripod PATTERN rather than any-4-legs
  motion) is a plausible new causal theory, distinct from "price
  harder" (already exhausted at n=7). Not yet built or tested — flag
  for the next design cycle, do not launch a bare cfg tweak on this
  theory without a bank pass proving the new mechanism actually
  distinguishes a real tripod gait from a stable 4-leg one first.
- UPDATE 09-05 ~23:4x: the leg-1/4 chronic-sacrifice fingerprint above
  (previously base(1g)-family only) has now appeared on a HALFGRAV
  (0.5g) seed too: `headset-halfgrav-fullhead-widen2-c2b-acq1` (40M
  acquisition continuation of the widen-from-medhead heading recipe)
  regresses from its own 2M canary's 16/24 gait_valid to 14/24, with
  leg-1 duty 0.01-0.21 (med ~0.11) in ALL 24 episodes, formally
  flagged sacrificed in 10/24 (one episode collapses to 4 legs
  [0,1,3,4] simultaneously). The matched sibling seed
  `widen2-c1-acq1` (same recipe, different parent lineage) ACQ PASSES
  cleanly (21/24, no chronic pattern) — the differentiator found so
  far is PARENT QUALITY, not gravity: `widen2-c2b`'s parent
  (`medhead2_acq1`) was itself only ACQ CONTINUE/borderline, while
  `widen2-c1`'s parent (`medhead_acq1`) was a clean ACQ PASS. Revises
  the gravity-linked-robustness-gap hypothesis (halfgrav is LESS
  PRONE to this fingerprint, not immune) and adds a new candidate
  causal thread (marginal-quality parents propagate/amplify their own
  marginal per-leg habits through further curriculum stages) worth
  testing directly before spending on a repair mechanism. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_fullhead_
  widen2_c2b_acq1_gate/report.json` vs `..._widen2_c1_acq1_gate/`,
  RL_LOG 09-05 23:4x.
- UPDATE 09-06 ~03:1x: the base(1g) leg-1/4 structural-entrenchment
  fingerprint above is not confined to native-1g training -- it can
  also emerge in a CROSS-GRAVITY-TRANSFERRED champion given enough 1g
  steps, even one that passed a clean 2M canary. `headset-crossgrav-
  irracq1-abrupt-c1-acq1` (irr-timing recipe, 2M canary 23/24
  gait_valid, 0 falls) **ACQ FAIL** at 40M: aggregate `gait_valid`
  drops to 14/24, `walk/det` regresses 6/6->4/6 (2 new formal leg-4
  flags), `walk_startjitter/det` collapses 5/6->0/6 (one episode's
  leg-4 swing_count=2/20s vs 91-239 for every other leg) -- despite
  training reward RISING throughout (quarters 717->1359->1507->1635,
  the 08-21 rising-reward/bad-eval shape). This is NOT read as
  "undertrained, continue" per the 08-21 ruling's own escape clause:
  the reward-misalignment class here (base(1g) middle-leg-pair
  favoritism) is the SAME one already closed above after 9 repair
  mechanisms, with the established fix being structural, not more
  training -- more training is exactly what produced this
  entrenchment. This is the FIRST regression in the crossgrav ACQ-
  scale confirmation set (3 prior: medhead-abrupt/ramp, widen2c1, all
  held clean walk/det 6/6). Open question this raises: is a clean 2M
  canary sufficient evidence for crossgrav-transfer durability, or
  does every transferred champion carry a slow-clock risk toward this
  attractor regardless of source health? Follow-ups in flight:
  `irr2acq1-abrupt-c1-acq1` (2nd seed, same recipe, seed-vs-recipe
  discriminator) and `medhead-abrupt-c1-acq1-cont40m` (+40M endurance
  check on the campaign's cleanest ACQ-PASS champion, tests whether
  ANY crossgrav champion entrenches given enough budget). Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_irracq1_
  abrupt_c1_acq1_gate/report.json` vs the 2M canary's own
  `..._abrupt_c1_gate/`, W&B `4n0z9k3b`, RL_LOG 09-06 03:12.
  UPDATE 09-06 ~04:1x, seed-vs-recipe question now CLOSED (RECIPE-
  LEVEL): the flagged follow-up `irr2acq1-abrupt-c1-acq1` (2nd
  independent seed, same irr-timing-first-crossgrav-abrupt recipe,
  own clean 2M canary 22/24) landed **ACQ FAIL** too — 40M aggregate
  `gait_valid` 17/24, leg 4 the sole flagged leg in every low episode
  (duty 0.0-0.10, swing_count as low as 1-63 vs 100-200+ for healthy
  legs), nearly the identical fingerprint to the 1st seed's own
  leg-4 pattern (14/24, duty 0.0-0.16). 0 falls in all 24 episodes;
  reward again rose every quarter (656.7->1207.2->1387.2->1532.2).
  **2/2 seeds now regress at ACQ scale from clean 2M canaries on this
  exact recipe — this is a RECIPE-level attractor, not seed noise. Do
  not fund a 3rd seed of the irr-timing-first-crossgrav-abrupt recipe
  at ACQ scale without a structural per-leg-utilization fix first**
  (the same open design gap already named for the sde family: a hard
  minimum-duty/minimum-swing-count price, not more budget or another
  reward dose). The companion endurance check
  (`medhead-abrupt-c1-acq1-cont40m`, testing whether ANY crossgrav
  champion entrenches given enough budget) is a separate open read —
  do not assume its outcome from this one. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_crossgrav_irr2acq1_abrupt_c1_acq1_
  gate/report.json`, W&B `zsxkfxzz`, RL_LOG 09-06 04:09.
  UPDATE 09-06 ~04:1x: the ACQ-scale entrenchment risk is NOT confined
  to the irr-timing-first-crossgrav recipe named above -- a totally
  different lineage (the `s3acq-abrupt-c1` family, built from an
  independent 3-way-heading champion, no irr/widen composition at
  all) shows the SAME regression. `s3acq-abrupt-c1-acq1` **ACQ FAIL**:
  walk/det and walk/sto (primary modes) stay clean 6/6+6/6, but
  `walk_startjitter/det` collapses to 2/6 (leg-1 flagged `sac=[1]` in
  4/6 episodes) and `walk_startjitter/sto` to 3/6 (leg-1 in 3/6).
  Leg-1 duty across ALL 6 `walk_startjitter/det` episodes:
  0.03/0.20/0.04/0.04/0.14/0.05 -- chronically low in 4/6, and WORSE
  than this run's own 2M canary (leg-1 duty there: 0.07-0.24, median
  ~0.15-0.19, only 3/6 flagged) -- i.e. the same leg got MORE parked
  with more 1g training, matching the "leg-1 in 4/6 and 3/6 episodes"
  numerical fingerprint already closed as ACQ FAIL for the unhealthy-
  source `widen2c2b-abrupt-c1-acq1`, but this time on a source that
  WAS healthy (22/24 clean 2M canary, no prior chronic pattern). 0
  falls; reward net-rising (quarters -400.8,-433.1,-129.3,125.0) but
  per the already-closed structural-repair precedent this does not
  override the FAIL. Meanwhile `s1acq-abrupt-c1-acq1` (the campaign's
  SINGLE CLEANEST source, native 0.5g gait_valid 24/24, 2M canary
  PERFECT 24/24) held ACQ PASS at 23/24 with only one transient
  (non-chronic) leg-4 dip -- so source cleanliness is NOT a reliable
  predictor either: `s3acq` (2nd-cleanest, 22/24 canary) entrenched
  while `s1acq` (cleanest, 24/24 canary) did not, and separately BOTH
  seeds of the irr-timing-first recipe entrenched regardless of their
  own clean canaries. **Updated read: ACQ-scale startjitter-panel
  leg[1,4] entrenchment is a recurring risk across MULTIPLE
  independent recipes/lineages (not one recipe's quirk), hits roughly
  half of tested healthy-source champions (now 3 FAIL: irracq1,
  irr2acq1, s3acq; vs 4 PASS: medhead-abrupt, medhead-ramp, widen2c1,
  s1acq), and is NOT reliably predicted by 2M-canary cleanliness
  alone.** Primary-mode behavior (walk/det, walk/sto -- what most
  gates actually score) stays clean even in the FAIL cases; the
  entrenchment is specifically a startjitter-panel (post-perturbation-
  recovery) phenomenon so far in every observed instance. This
  confirms and generalizes the 09-05 ~22:3x structural diagnostic
  (leg 1/4 are the hexagon's sole redundant middle pair) as a
  cross-recipe attractor, not a per-recipe accident -- raises the
  priority of the flagged-but-unbuilt role-aware repair mechanism
  (weight the middle-pair's contribution differently, or price a real
  alternating-tripod pattern rather than any-4-legs stability) named
  there; still not built or bank-proven as of this update. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_s{1,3}acq_
  abrupt_c1_acq1_gate/report.json` vs each run's own `..._abrupt_c1_
  gate/` 2M canary, W&B `80g9tb6m`/`lp972djl`, RL_LOG 09-06 04:16.
  UPDATE 09-06 ~04:4x: the medhead endurance question raised at ~04:1x
  is now answered -- `medhead-abrupt-c1-acq1-cont40m` (2nd +40M
  helping, 80M cumulative 1g steps on the campaign's cleanest lineage)
  **PASSES/HOLDS**: `gait_valid` 24/24, actually BETTER than its own
  40M parent's 23/24 (the parent's one transient leg-4 dip is gone), 0
  falls, slip/progress flat-to-better on every panel. **Crossgrav
  entrenchment risk is confirmed recipe/source-specific, not a
  universal slow clock every transferred champion is on regardless of
  budget** -- medhead specifically tolerates DOUBLE the budget that
  entrenched `irracq1`/`irr2acq1`/`s3acq` with no degradation at all.
  Its two forward-composed siblings independently corroborate:
  `medhead-widenfwd-c1-acq1` ACQ PASS (21/24, mild non-chronic dip,
  slip/progress mostly improved vs 2M canary) and `medhead-irrfwd-
  c1-acq1` ACQ PASS (21/24, FLAT vs its own 22/24 canary -- same
  leg-2/5 marginal softening at the same episode indices, not
  worsening). medhead is now 5-for-5 across every 40M+ read attempted
  on it (abrupt, abrupt-cont40m, widenfwd, irrfwd, plus the original
  abrupt-c1-acq1) with zero entrenchment in any of them -- the
  campaign's benchmark "this recipe just works" lineage, useful as a
  counterpoint anchor once the flagged role-aware structural repair
  mechanism (09-05 ~22:3x note above) gets built and needs a
  known-clean control to validate against. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_crossgrav_medhead_{abrupt_c1_acq1_
  cont40m,widenfwd_c1_acq1,irrfwd_c1_acq1}_gate/report.json`, W&B
  `kfpu6ku1`/`thsloov1`/`naxsaxqj`, RL_LOG 09-06 04:38-04:39.
  UPDATE 09-06 ~05:3x: the endurance panel's 2nd data point (`s1acq-
  abrupt-c1-acq1-cont40m` and `s3acq-abrupt-c1-acq1-cont40m`, both a
  2nd +40M helping = 80M cumulative) sharpens the "endurance is
  recipe/source-specific, not universal" reading into a REFINED,
  more useful predictor: **cleanliness margin at the FIRST 40M read,
  not total budget, determines whether a 2nd 40M helping helps or
  hurts.** `s1acq-abrupt-c1-acq1-cont40m` (source: the cleanest
  40M read in the whole campaign, 23/24, only one non-chronic
  transient dip) reproduces its own 40M read EXACTLY at 80M (23/24,
  same single transient leg-4 dip, same episode slot, reward still
  rising) -- PASS/HOLDS, matching medhead's own cont40m precedent.
  `s3acq-abrupt-c1-acq1-cont40m` (source: a 40M read that was ALREADY
  entrenching, 21/24 with a chronic leg-1 startjitter softening)
  WORSENS at 80M -- aggregate drops to 16/24, `walk_startjitter/det`
  collapsing further to 1/6, leg-1 duty chronically <=0.27 across
  every episode in BOTH startjitter panels (not just one). **This
  closes the "does endurance ever repair an already-entrenching
  champion" question negatively**: 2 independent healthy-at-2M
  sources that diverged at 40M (one clean, one chronic) diverge
  FURTHER at 80M in the same direction, not toward each other. The
  practical rule going forward: fund cont40m endurance helpings only
  on sources whose first 40M read is already clean (no chronic
  single-leg pattern); a 40M read that already shows one should be
  treated as informative-negative and routed to the still-unbuilt
  structural per-leg-utilization repair, not more of the same
  training. Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  crossgrav_s{1,3}acq_abrupt_c1_acq1_cont40m_gate/report.json`, W&B
  `7i7dzujt`/`z1e7r91v`, RL_LOG 09-06 05:21/05:31.
- UPDATE 09-07 ~04:1x: `reward.walk_duty_band_gate` (two-sided
  trapezoid duty band, priced BOTH tails unlike `walk_duty_gate`'s
  floor-only or `walk_swing_gate`'s count-only design) closed 2/2 on
  the base(1g) `s0c1` leg-4 lineage: `dbandgate-fresh` (dosed from
  step 0) is INERT — `walk_startjitter/det` leg-4 duty median 0.045,
  statistically identical to the undosed twin's own 0.045, gait_valid
  0/6 both, plain `walk/det` stays clean 6/6 either way; `dbandgate-fix`
  (retrofit onto the entrenched `s0c1-acq1` checkpoint) is WORSE — leg-4
  duty falls to median 0.01 and the sacrifice spreads into plain
  `walk/det` too (0/6 vs the undosed twin's clean 6/6). No new falls
  either arm. **This is the 4th independently-designed reward-price
  mechanism class (after `walk_gait_gate`+`k_step_event` 6/6 FAIL,
  `walk_duty_gate` 9/9 FAIL, `walk_swing_gate` 5/5 FAIL) to fail on
  this exact pathology, now 11 arms total — including one (this one)
  specifically designed to price BOTH duty tails at once, closing the
  "the gate only ever penalized one direction" theory too.** This is
  fully consistent with, not a new data point against, the 09-05
  ~22:3x role-aware diagnosis above: L1/L4 (the mesh hexagon's sole
  diametrically-opposite middle pair) idling is a genuinely CHEAPER
  STABLE 4-leg gait, so no per-leg duty price — floor, count, or
  two-sided band — can out-compete it without knowing which legs form
  a valid support role, because all of them price every leg
  identically. **The reward-price mechanism CLASS is now exhausted for
  this pathology; do not fund a 5th design in it (a 3rd duty threshold,
  a swing-timing variant, etc.) without first building the role-aware
  mechanism named in the 09-05 ~22:3x entry** (weight the structural
  middle pair differently, or price a genuine alternating-tripod
  support-polygon pattern rather than any-4-legs motion) — still not
  built as of this update. Evidence: `ops.sh review cw-walkscratch-
  easy0905-headset-base-s0c1-dbandgate-{fresh,fix}`, `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_base_s0c1_dbandgate_{fresh,fix}_
  gate/report.json` vs `..._s0c1_{,acq1_}gate/report.json`, W&B
  `f3wp5pba`/`ndjo2e2i`, RL_LOG 09-07 04:14.
- UPDATE 09-07 ~04:4x (zero-spend diagnostic, scoping the still-unbuilt
  role-aware mechanism before writing any code): pulled real per-leg
  `duty_cycle` VECTORS (not just the aggregate `sacrificed_legs`/
  `gait_valid` flags) from both a FAILING report
  (`dbandgate-fresh_gate`, leg4 chronically sacrificed) and a PASSING
  one (`crossgrav_medhead_abrupt_c1_acq1_gate`, `gait_valid` 23/24)
  to check the most obvious reading of the role-aware idea — a binary
  per-tick match to the canonical `PHASE_TRIPOD_A=(0,2,4)` vs `(1,3,5)`
  template. Two findings, both NEGATIVE for that specific design:
  (1) **worked the arithmetic by hand for a leg-4-always-swing twin**:
  a per-tick `score = max(match_to_tripod_A, match_to_tripod_B)`
  scores ~0.83-1.0 on such a twin (never collapses toward a clear
  penalty), because dropping ONE leg from a 3-leg group still
  coincidentally satisfies the OTHER template's expectation for that
  leg roughly half the time — this exact "max-over-two-rigid-
  templates" formulation would likely be a 4th INERT mechanism, no
  better than `walk_duty_band_gate`, for the reason already proven
  bad (rewards can't out-compete a genuinely cheaper physical basin
  when the pricing has an escape hatch). (2) **real duty spread
  refutes the "clean binary tripod" premise entirely, even in
  PASSING runs**: `crossgrav_medhead_abrupt_c1_acq1`'s own 12
  `walk`+`walk_startjitter`/det episodes show per-leg duty ranging
  0.10-0.74 (e.g. `[0.65,0.39,0.18,0.74,0.29,0.23]`), NOT clustered
  near 0.5 for every leg as a clean alternating-tripod would predict
  — and leg4 is the single lowest-duty leg in 10/12 of those PASSING
  episodes (0.18-0.30, once as low as 0.10 with that episode itself
  flagged `sacrificed=[4]`). **Leg4 being the least-used leg is a
  structural/kinematic fact of this gait at this commanded
  speed/gravity, present in PASSING runs too — the pass/fail
  boundary is a matter of DEGREE (0.10-0.30 passing vs 0.03-0.07
  failing), not of matching or violating some crisp topological
  pattern.** This means a rigid pattern/role-matching reward risks
  charging genuinely-passing gaits along with failing ones (the same
  false-positive risk that sank nothing yet, but would need very
  careful calibration against this exact non-uniform baseline to
  avoid). **Recommendation for whoever designs the role-aware
  mechanism next: do NOT ship the naive max-over-binary-template
  score describe in (1); any support-pattern reward needs to be
  calibrated against a PASSING checkpoint's own graded duty spread
  (this update's numbers) as its zero-charge reference band, not an
  assumed uniform 0.5-per-leg tripod.** Given (2) also shows crossgrav
  transfer is still the only mechanism that has ever measurably moved
  leg4's duty in the right direction (0.03-0.07 direct-1g -> 0.10-0.30
  crossgrav-transferred), the higher-value next step stays what
  item(1) is already pursuing (replicate/extend crossgrav-transfer),
  not a fresh reward class. No code changed, no launch — pure
  read of already-synced `report.json` files, zero GPU/training spend.
  Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s0c1_
  dbandgate_fresh_gate/report.json`, `logs/ckpt_eval/cw_walkscratch_
  easy0905_headset_crossgrav_medhead_abrupt_c1_acq1_gate/report.json`
  (`episodes.duty_cycle` fields), RL_LOG 09-07 04:4x.
- UPDATE 09-07 ~05:1x: item(1)'s `allaxis-nokick-c1-acq1` fork (the
  full ~30-axis realism composite, crutch `dr.torque_scale=3x` ON,
  kick fully off) is VERDICTED ACQ FAIL - PUSH-RECOVERY FRAGILE
  (2/24 falls, both tilt_roll immediately after a push marker).
  Root cause CONFIRMED via a matched-parent-control ablation (same
  checkpoint/seed, only `dr.walk_push_prob`/`dr.ext_push_prob`
  0.3->0.0): 0/24 falls, gait_valid/slip unchanged otherwise — push,
  dosed at a constant 0.3 for the whole 40M run with no curriculum/
  anneal, is sufficient by itself to reproduce the fragility with the
  crutch still on. A concurrent crutch-isolation pair
  (`...-crutchoff-{s1,s2}`, `dr.torque_scale` 3->1, push left ON) was
  launched the same window to test whether torque assist is ALSO/
  INSTEAD a driver — the two axes are not mutually exclusive; read
  both before generalizing. Do not assume kick-removal or crutch-
  removal alone is a sufficient fix for this composite; push-recovery
  under full DR is now a NAMED open axis, not an unexplained gap.
  Evidence: `logs/ckpt_eval/walkcurr_item1_pushablation_nopush/
  report.json` vs `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  crossgrav_medhead_dr_allaxis_nokick_c1_acq1_gate/report.json`.
  UPDATE 09-07 ~05:4x: the crutch-isolation pair above landed —
  `crutchoff-{s1,s2}` (single-lever `dr.torque_scale` 3,3->1,1, push
  left ON, same seeds that already fell with crutch ON) both CANARY
  PASS, 0 falls/24 eps, `gait_valid` 20/24 each. **Crutch IS a real,
  confirmed driver of the push-recovery fragility (2/2 seeds), not
  seed noise** — complementary to, not competing with, the push-
  ablation finding above (both axes independently sufficient at their
  joint dose). One of the original 3 seeds (`s0`) only fell at 40M
  ACQ, not its own 2M canary, so a canary PASS alone doesn't prove
  scale durability — a matched `crutchoff-s0` canary plus
  `crutchoff-{s1,s2}-acq1` 40M continuations are in flight. Full
  writeup: `rl_docs/tracks/walkcurr/STATUS.md` 09-07 ~05:4x.
  UPDATE 09-07 ~09:5x: the crutch-off lineage's own `widen8` heading-
  widening extension (8-way headings incl. 3 new rear/diagonal-rear
  directions vs the base 5-way medium set) CLOSES its ACQ trio 3/3
  FAIL with a NEW leg-pair fingerprint that GENERALIZES this section's
  L1/L4 diagnosis rather than repeating it. All 3 seeds develop the
  SAME two new chronic sacrifices at the SAME held-out episode indices
  once trained to 40M (clean/near-clean at each seed's own 2M canary):
  `walk/det` ep0 (`sac=[5]`) and ep5 (`sac=[0,5]`), 0 falls throughout,
  reward rising every quarter on every seed (misaligned, not
  under-trained, per 08-21). Checked `mesh_mujoco/hexapod_mesh.xml`
  leg-mount coords directly: legs 0 and 5 are the FRONT pair (both
  `x=+0.087`), NOT the L1/L4 middle pair every reward-price mechanism
  above was designed against. Reading: the "diametrically-opposite
  pair with no fore/aft neighbor is a cheaper stable 4-leg gait"
  theory is HEADING-DEPENDENT, not a fixed structural pair — for a
  forward command the redundant pair is the L1/L4 middle pair; for a
  REAR-ish command (widen8's 3 new headings are the only rear/
  diagonal-rear ones in its 8-way set) the redundant pair becomes the
  FRONT pair by the same logic. **Any future role-aware/support-margin
  mechanism design must be heading-conditioned (know which pair is
  structurally redundant for THIS episode's commanded direction, not
  assume a fixed pair) or it will only ever cover the forward-command
  half of this pathology.** No repair attempted this cycle (per the
  09-07 ~04:4x recommendation directly above, this needs a proper
  design+bank pass, not a rushed dose); do not relaunch widen8 at ACQ
  depth without either that mechanism or a heading-bisected narrower
  widen. Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  crossgrav_medhead_dr_allaxis_nokick_crutchoff_s{0,1,2}_widen8{,
  _acq1}_gate/report.json`, `mesh_mujoco/hexapod_mesh.xml` (`L0_yaw`/
  `L5_yaw` body `pos`), `rl_docs/tracks/walkcurr/STATUS.md` 09-07 ~09:5x.
- UPDATE 09-07 ~20:3x: the whole DIRECT-SLIP-PRICING reward class
  (charge foot slip directly, whether whole-episode, ratio-windowed,
  overspeed-interaction-corrected, or touchdown/liftoff-phase-
  targeted) is now CLOSED, 9 arms total, all converging on the same
  ~5-6/m slip floor on the crutch-off/allaxis mesh/100Hz lineage:
  4 solo direct-slip doses (CLOSED 09-07 ~17:3x, every one escaped
  its own charge by speeding up), the `lswin` overspeed-interaction
  canary (CLOSED 09-07 18:07, escape closed, floor unmoved), and now
  the touchdown/liftoff transition-window charge (`reward.
  k_walk_transition_slip`, 4 arms: 2 lineages x buggy/fixed
  touchdown-accounting, all `CANARY FAIL - MECHANISM`, slip/m flat
  vs each lineage's own baseline in every one). **Do not fund a 10th
  reward-pricing design against this exact slip floor.** Every one of
  these arms' own gate text independently named the same escalation:
  a STRUCTURAL (non-reward) lever — contact/friction-model fidelity,
  foot-pad/geometry, or a genuine foot-placement policy change — not
  another charge/dose/window. Evidence: `rl_docs/tracks/walkcurr/
  STATUS.md` 09-07 ~20:3x, W&B `x5r1ktgp`/`vmczkhfx`/`si7rindk`/
  `o8pi2qe6`, RL_LOG 09-07 20:3x.
- UPDATE 09-08 ~03:5x: measured the walkcurr-specific structural-lever
  candidate the 09-07 20:3x closure (above) demanded and the
  todaypolicy turn-traction diagnostic separately nominated
  (`artifacts/rl_watchdog/turn_traction_20260908/`, mesh-family foot
  torsional mu_t=0.1 m ~20x a physical boot estimate): re-evaluated
  the SAME `crossgrav_medhead_dr_allaxiskickhalf_nocrutch1x_c1_acq1_
  cont40m` checkpoint/panel/seed with ONLY `env.foot_friction_torsion`
  overridden 0.1->0.005 (new probe-local cfg key, default 0 = bit-
  exact off, `sim_env.set_foot_ground_torsion_friction`, tested).
  Result: slip/m is FLAT-TO-SLIGHTLY-WORSE in every one of the 4
  groups (det 4.98->5.19 +4%, sto 5.17->5.41 +5%, sj/det 5.10->5.14
  +1%, sj/sto 5.42->5.93 +9%), `gait_valid` identical 22/24 (same 2
  sacrificed episodes, sto/4 leg2 + sj/det/1 leg2), 0 falls/
  terminations both. **Unlike the turning case (where the same dose
  measurably reduced yaw authority deficit), the torsional-friction
  fidelity gap does NOT explain walkcurr's straight-walk slip floor
  — it is refuted as the structural lever for THIS floor.** The 9-arm
  reward-pricing family's own escalation stands unanswered by this
  candidate; the remaining structural options (foot-pad geometry,
  genuine foot-placement policy change) are still unbuilt/unscoped.
  No canary funded (negative diagnostic result, not a lever). Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_
  dr_allaxiskickhalf_nocrutch1x_c1_acq1_cont40m_{gate,
  torsion005_probe}/report.json`, W&B `v6wmk0lv`, `rl_docs/tracks/
  walkcurr/STATUS.md` 09-08 ~03:5x.
- UPDATE 09-07 ~21:0x: the narrowest possible test of the widen8 fork
  — add ONLY the single 180deg rear heading (not widen8's full 3-new-
  heading jump) to each crutch-off seed's own ACQ-passed 40M champion,
  2M canary — CLOSES the "incremental one-heading-at-a-time widening
  dodges the role-aware mechanism" branch. `crutchoff-{s1,s2}-
  widenrear180` (2/2 independently-trained seeds; `s0` owned by a
  concurrent cycle) both `CANARY FAIL - MECHANISM` with an IDENTICAL
  fingerprint at IDENTICAL episode indices: `walk/det` `gait_valid`
  3/6 (below the required majority), chronic leg-0 sacrifice (duty
  ~0.06-0.25 vs 0.4-0.8 elsewhere) at episodes 0/1/5 in both seeds,
  same sac pattern in `walk/sto` and `walk_startjitter/sto` too. Cross-
  seed identity at matched indices (the eval env's RNG assigns the
  same heading to the same index regardless of training seed) rules
  out seed noise: **this is heading-content-driven** — training even
  ONE new rear heading, gradually, still reproduces a chronic single-
  leg sacrifice. **No further `walk_heading_set` expansion, incremental
  or otherwise, is licensed on this lineage until the heading-
  conditioned role-aware mechanism (still unbuilt — see the 09-05
  ~22:3x / 09-07 ~04:1x / ~04:4x entries) exists.** Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_
  dr_allaxis_nokick_crutchoff_s{1,2}_widenrear180_gate/report.json`,
  W&B `j7a0gr9b`/`692tv6qc`, `rl_docs/tracks/walkcurr/STATUS.md`
  09-07 ~21:0x, RL_LOG 09-07 20:50.
- UPDATE 09-07 ~21:2x: `crutchoff-s0-widenrear180`'s own verdict lands,
  CLOSING the trio 3/3 (identical fingerprint to s1/s2 above) — and
  the still-unbuilt heading-conditioned role-aware mechanism named
  since 09-05 ~22:3x is now BUILT and bank-proved: `safety.walk_leg_
  duty_terminate_s` (`walk_task.py`/`sim_env.py`), a heading-UNIFORM
  per-LEG minimum-duty TERMINATION (not another per-tick price) — end
  the episode like a fall if any leg's own ground-contact EMA stays
  below a floor (default 0.05, calibrated below the passing-checkpoint
  low-duty band the 09-07 ~04:4x entry measured) for N seconds. Same
  validated pattern as `hold_min_load_terminate`/`walk_idle_terminate`
  ("absorbing states beat prices; must come WITH a termination"), now
  applied per-leg instead of whole-robot/whole-hold — and deliberately
  uniform across all 6 legs so it needs no heading-conditioned role
  table (a termination doesn't need to know WHICH pair is redundant
  for the current command, only that no single leg may go chronically
  idle). Bank `WALKCURR_LEGDUTY_TERM` 4/4 green (bit-exact off, honest
  six-leg gait untouched, the flag-leg one-leg-sacrifice cheat cut
  short well inside its own dose arithmetic, dedicated penalty stays
  clear of the anti-suicide term_penalty). **NOT YET VALIDATED as a
  fix** — 4 repair canaries launched this cycle (continuations off the
  already-entrenched `widen8-acq1` x3 seeds + `widenbis180` x1, single
  lever added, `--init-from-source`); read their gate reports before
  treating this gap as closed or funding a dose/lineage variant.
  Evidence: `rl_docs/tracks/walkcurr/STATUS.md` 09-07 ~21:2x,
  `rl_move/tests/test_task_semantics.py` (`test_walk_legduty_
  terminate_*`), W&B `kwbx6jtk` (+3 siblings).
  UPDATE 09-07 ~21:5x: all 4 of those retrofit-onto-entrenched-
  checkpoint canaries landed — `s1`/`s2`-widen8-acq1-legdutyterm1 and
  `s0`-widenbis180-legdutyterm1 all **CANARY FAIL - MECHANISM**,
  matching `s0`-widen8-acq1-legdutyterm1's already-closed shape exactly:
  `gait_valid` WORSENS vs each seed's own pre-mechanism baseline
  (widen8: 20/24->12/24 s1, 20/24->11/24 s2; widenbis180: 18/24->13/24)
  and `walk_leg_duty_terminate` is still firing in the clear majority
  of episodes at the END of the 2M (19/24, 20/24, 15/24) — never
  converging away, the run's own pre-registered FAIL branch, in all 4.
  **Closes the retrofit-onto-an-already-40M-entrenched-checkpoint
  approach 4/4 FAIL**: a hard per-leg duty TERMINATION raises the cost
  of an already-baked-in sacrifice but does not unlearn a 40M-step
  habit within a 2M budget — a genuinely different failure mode than
  the 11-arm per-tick-price closure (those were gamed/saturated; this
  one applies honest pressure that simply arrives too late). Still
  OPEN and untested: whether the same termination, present from the
  START of training (before the habit entrenches), prevents the
  sacrifice from forming at all. Launched the cheap disambiguator —
  `respec --from <seed>-widen8-acq1` (the ORIGINAL 40M widen8 run,
  itself already a from-scratch-relative-to-widen8 warm-start off each
  seed's pre-widen8 medhead champion) with ONLY the 5
  `walk_leg_duty_terminate*` cfg-sets added from step 0, otherwise
  byte-identical (same seed/parent/40M budget) — a clean single-lever
  A/B against the already-known undosed widen8-acq1 ACQ-FAIL baseline.
  `s0`/`s1`-widen8-acq1-legdutyfresh VERIFIED RUNNING (train-2/train-0,
  40M each = 80M, the cycle's default gpu-steps cap); `s2` queued to
  backlog for the next drain. If this ALSO fails (leg still parks
  regardless of firing rate), the termination-mechanism family closes
  outright (12+ price/termination designs, 0 wins) and the
  heading-conditioned role-aware mechanism named since 09-05 ~22:3x
  becomes the only untried lever — do not fund a 13th
  price/termination dose variant before that read lands. Evidence:
  `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-
  allaxis-nokick-crutchoff-{s1,s2}-widen8-acq1-legdutyterm1`,
  `...-s0-widenbis180-legdutyterm1`, `rl_docs/tracks/walkcurr/
  STATUS.md` 09-07 ~21:5x, W&B `i66lls8h`/`5r1zed2h`/`dnpmd5tp`.
  UPDATE 09-07 ~22:5x-23:2x: the from-scratch disambiguator lands
  8/8 dead: `s0`/`s1`/`s2`-widen8-acq1-legdutyfresh (12/24, 13/24,
  13/24 `gait_valid`, identical legs-0/5 fingerprint) and
  `s0`-widenbis180-legdutyfresh (a DIG-IN-resolved FAIL — its
  apparent 20/24-vs-18/24-baseline improvement is inside eval noise,
  Fisher exact p=0.72) all FAIL. **`safety.walk_leg_duty_terminate_s`
  is now CLOSED 0/8** (4 legdutyterm1 retrofits + 4 legdutyfresh
  from-scratch arms), on top of the 11-arm per-tick-price class —
  15+ price/termination designs, 0 wins on this pathology. Working
  read: TERMINATION-AS-PRICE IS THE WRONG MECHANISM SHAPE HERE, not
  just under-dosed or under-trained — the policy pays a chronic
  termination as an ambient tax (firing rate keeps RISING through
  40M, e.g. ~80->132-143/log-interval) rather than ever unlearning
  the sacrifice. Do not fund a 9th termination-shaped variant without
  an explicit argument for why it changes the incentive SHAPE, not
  just the floor arithmetic (this already tripped up the `walk_leg_
  duty_terminate_floor_rel_frac` add-on below).
- **CALIBRATION FINDING (2026-09-07 ~23:4x, zero-spend, no code/
  launch): a PEER-EXCLUDED-MEAN relative duty floor cleanly separates
  sacrificed legs from a passing gait's naturally-uneven worst leg**
  — the missing calibration every prior scoping pass (09-07 ~04:4x,
  ~21:0x, ~23:2x) named as the prerequisite before building the
  still-open "role-aware/heading-conditioned per-leg utilization
  TARGET (continuous reward gradient, no termination)" lever. Method:
  pulled `duty_cycle` (already in every gate `report.json`, per-leg
  6-vector) from 288 episodes across 12 already-synced reports
  spanning the whole front-pair-pathology campaign (widen8-acq1 x3
  seeds pre/post-legdutyfresh, widenbis180 pre/post-legdutyfresh,
  widenrear180 x3 seeds, plus the independently-PASSING `crossgrav-
  medhead-abrupt-c1-acq1`). For each leg compute
  `ratio = leg_duty / mean(the OTHER 5 legs' duty)` (peer-excluded,
  NOT team-mean-including-self — this matters, see below) per
  episode: **87 gate-flagged-sacrificed-leg ratios**: min 0.000,
  p10 0.021, median 0.075, **p90 0.179, max 0.249**. **213
  `gait_valid==True` (passing) episodes' OWN worst-leg ratio**: min
  0.222, p10 0.302, median 0.537, max 0.889. The two distributions
  overlap in only a hair's-breadth band (0.222-0.249, 1 episode on
  each side of a 0.235 cut out of 300); a threshold anywhere in
  0.22-0.24 correctly classifies >=299/300 episodes (e.g. `thr=0.20`:
  0 false-positives, 6/87 sac-escapes; `thr=0.25`: 0/87 escapes,
  7/213 false-positives — the crossover sits right around 0.22-0.24).
  Peer-excluded matters: using an ALL-6-legs-including-self mean (the
  shape the just-built `walk_leg_duty_terminate_floor_rel_frac`
  add-on implements) is measurably muddier (sac p90 0.205/max 0.284
  vs pass min 0.255/p10 0.342 — a wider, less clean overlap) because
  a starved leg still drags its OWN mean down, partially hiding
  itself; excluding the leg from its own reference average removes
  that self-dilution and sharpens the cut by roughly 2x. **Actionable
  spec for the next build** (not yet built, no code changed this
  entry): a continuous per-tick reward charge
  `k_walk_legduty_target * sum_over_legs(relu(0.22..0.24 *
  peer_excluded_mean_duty_ema - own_duty_ema))`, EMA-smoothed (reuse
  the existing `tau_s`-style smoothing so a single-tick swing dip
  doesn't fire), summed (not maxed) over legs so it prices the
  observed multi-leg (front-PAIR) starvation shape, and — critically
  — computed independent of `safety.walk_leg_duty_terminate_s` (today
  the EMA state is only tracked inside that termination's own `if
  walk_ldt_s > 0.0` gate in `sim_env.py`; a reward-only deployment
  needs the tracking un-gated from the termination toggle). This is
  a genuinely different SHAPE from the closed reward-price class
  (11 arms: `walk_duty_gate`/`walk_swing_gate`/`walk_duty_band_gate`/
  `walk_gait_gate`+`k_step_event`, all fixed-absolute-threshold or
  event-based) in the same sense the termination mechanism was
  argued to differ from it — but a NEW price design still needs its
  own semantics-bank proof that a scripted flagleg-cheat twin's FULL
  undocked episode return (no termination cutting it short this
  time) reads LOWER than the honest six-leg gait's, at whatever dose
  is chosen; that ordering-flip is the exact property all 11 closed
  price arms failed to achieve against an entrenched habit, and this
  calibration only fixes the FLOOR PLACEMENT, not the dose/ordering
  question. Deliberately NOT built this entry — the wiring (decoupling
  the EMA tracker from the termination gate) touches the same shared
  `sim_env.py` step()/`walk_task.py` reward path every track's
  training depends on, and every other scoping pass at this exact
  fork (09-07 ~04:1x/~04:4x/~21:0x, and the immediately-prior cycle's
  `3bced209`) reached the same "real design pass, not a rushed same-
  cycle build" judgment; rushing the wiring change on top of an
  already-long investigative cycle risks a subtle bug in shared
  training code for a speculative payoff. Evidence: this entry's own
  python one-liners over `logs/ckpt_eval/cw_walkscratch_easy0905_
  headset_crossgrav_medhead_{abrupt_c1_acq1,dr_allaxis_nokick_
  crutchoff_s{0,1,2}_{widen8_acq1,widen8_acq1_legdutyfresh,
  widenbis180,widenbis180_legdutyfresh,widenrear180}}_gate/
  report.json` (`duty_cycle`/`sacrificed_legs`/`gait_valid` fields);
  RL_LOG 09-07 23:4x.

- **2026-09-08 ~14:5x: two closures land together.** (1) The 3-arm
  DR-axis-knockout ablation (bisecting WHICH single DR axis blocks
  fresh-init ignition on the widen8 full-DR composite) closes 3/3
  FAIL: removing `dr.bad_start_prob`, `dr.fault_prob`, or
  `dr.ext_push_prob`+`dr.walk_push_prob` ALONE each still leaves the
  policy thrashing in place (fwd med 0.01-0.02m/20s episode, i.e.
  ~0.0005-0.001 m/s, ~30-60x under the 0.03 m/s PASS floor; slip med
  69-74/m, matching the closed-4/4 fingerprint; contact sheets show
  zero body translation across all 10 frames). No single named DR
  axis explains the fresh-init ignition failure — confirms DR breadth
  itself (the sum of many small-disruption axes) as the blocker.
  Single-axis knockout is now closed as a productive lever on this
  composite; the two remaining licensed moves are narrowing the DR
  composite itself, or a genuinely new per-leg mechanism (below).
  (2) The `walk_leg_loadslip_ratio_charge` recalibration (target
  1.5->6.0, moving from the wrong side/p10 to the correct side/p90 of
  the passing population's own worst-leg load-slip-ratio distribution)
  fixes the SATURATION diagnosis (excess reads 0.02-0.025, not stuck
  at a fixed 0.86-1.0 ceiling like the closed target=1.5 batch) on
  both tested lineages, but still does not clear the efficacy bar:
  `crutchoff-s0-widen8` (n=1) reads only 2/4 groups improved (short of
  the >=3/4 CONTINUE bar) with its own training reward collapsing
  hugely in the back half (quarters 34/56/-1058/-6806, same
  charge-dominates-raw-PPO-scale shape as the closed target=1.5
  sibling, not a new anomaly — the exported best-checkpoint's held-out
  behavior is roughly parity with its parent); `assistfade-rung3-s0`
  reads a clean FAIL-MECHANISM per its own gate text (slip WORSE on
  det: 12.67->15.80, +25%; indistinguishable on sto: 16.71->17.17) with
  no new falls. Recalibration alone does not rescue this lever;
  further loadslip-charge spend on either lineage needs either a much
  lower charge weight (so it stops dominating the PPO reward scale) or
  should be abandoned in favor of a genuinely different per-leg
  mechanism. Evidence: `ops.sh review cw-walkscratch-easy0905-widen8-
  jointspace-freshinit-{nobadstart2m,nofault2m,nopush2m}`; `ops.sh
  review cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-
  target6`; `ops.sh review cw-assistfade-rung3-legdutyratio-loadslip-
  s0-target6`; `rl_docs/tracks/walkcurr/STATUS.md` 2026-09-08 ~14:5x.

## Real Robot Boundary
- The robot remains physically owned by the operator, but the active Robot Lab
  campaign grants guarded agents standing authority for bounded observed
  motion, necessary deployment, and routine recovery. Live camera plus three
  fresh healthy samples counts as supervision; reserve hands-on requests for a
  persistent or inconclusive physical condition.
- Prefer HTTP/dev-loop helpers:
  `make robot-check`, `robot-unit-check`, `robot-status`, `robot-deploy`.

## Startup And Status
- Orchestrator dashboard: `https://hexapod.cwd1f0-new-cluster.coreweave.app`.
- Startup packet: `STATUS.md`, this file, `RL_PLAN.md`, the relevant
  `rl_docs/tracks/<track>/STATUS.md`, `RESEARCH_RULES.md`,
  `RUN_INTERPRETATION_RULES.md`, and `rl_docs/COMMANDS.md`.
- Budgets: `STATUS.md` <=100 lines, track STATUS <=120,
  `RL_PLAN.md` <=150, this file <=80. Long audits go to `archive/`.
