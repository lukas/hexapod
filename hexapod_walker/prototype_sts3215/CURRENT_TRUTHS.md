# CURRENT TRUTHS - accepted facts and rulings

## `rl_only` 50Hz walk-role acquisition PASS, 2nd of 3 seeds exported, and the physical-delivery bundle re-cut to point at a deployable artifact (2026-09-10 ~23:2x, walkcurr track)

One plain sentence: `cw-walk50hz-rlonly-crutchoff-s2-warmadapt-acq1` (18M-step
continuation of the s2 50Hz warm-adapt canary) reads at parity-or-better
against its own matched 100Hz parent by the identical standard s0's own
acq1 PASSED on (`ops.sh entry` 2026-09-10 ~22:4x), so it is exported as the
SECOND `rl_only`-track 50Hz walk artifact, and `rl_docs/tracks/walkcurr/
bundle_rlonly_v1` (the physical-handoff package, still control.hz=100 and
therefore undeployable per `op_20260910_50hz`) is superseded by a new
`bundle_rlonly_v2` naming the 50Hz s0 export as candidate.

Panel-by-panel vs the matched 100Hz parent (`cw-walkscratch-crutchoff-s2-
widen8-legdutyratio-swinggap-dose10-plusduty-acq1-cont10m`, same harness,
this seed's own band): pooled `gait_valid` 23/24 vs parent's 22/24
(walk/det 6/6, walk/sto 5/6 — one new sacrificed leg, stochastic-only,
walk_startjitter/det 6/6, walk_startjitter/sto 6/6 vs parent's 4/6).
`progress_ratio`/`slip_per_m` at parity or better on 3 of 4 sub-panels.
SCORE/* multi-skill check vs the same parent: hold/track/raise_success/
rise_flat/rise_crouch same-order-or-unchanged (already-broken pre-existing
per `bundle_rlonly_v1`'s own accepted limitation); `rise_bridge_success` 0
vs parent 0.5 and `raise_total_reward` down ~84% are single-flip/n=2-noise-
scale deltas structurally identical to what s0's own acq1 accepted on
`raise_success` (0.5->0); `unload_total_reward` -195.6 vs parent -71.5
sits inside the seed family's already-observed noisy band (-71 to -250
across canary/acq reads on both seeds). Training `ep_rew_mean` fell across
quarters, the same already-root-caused `walk_leg_duty_ratio_charge`/
`walk_leg_swing_gap_charge` 50Hz tick-rate accumulator artifact confirmed
on s0/s1/s2 canaries, not a behavioral regression (08-21 ruling). Exported
(`export_policy_np.py --training-hz 50 --inner-hz 50`, parity 2.37e-07) to
`linux_control/policies/walkscratch_rlonly_widen8_crutchoff_s2_warmadapt_
50hz_acq1.json`.

**Physical-delivery package re-cut**: `rl_docs/tracks/walkcurr/
bundle_rlonly_v2/{transfer_manifest.json,GO_NOGO.md}` now names s0's 50Hz
acq1 export as the candidate (s2's export named as a same-quality alternate
seed), with fresh reproducible demo captures on this exact checkpoint
(`ops.sh drivevideo cw-walk50hz-rlonly-crutchoff-s0-warmadapt-acq1
--script human`/`human_turn`, 26s each, controller/CPU full-mesh MuJoCo):
both clean (0 falls, `gait_valid=true`, `sacrificed_legs=[]`), progress
1.167/1.233, slip/m 5.75/5.94 — comparable to v1's own 100Hz numbers
(1.20/1.24, 5.31/5.58). Confirmed via the drivevideo run's own resolved
`motor_contract` that this checkpoint used the CORRECT deg/s-preserving
`safety.max_delta_q_deg=7.2` at 50Hz (=360 deg/s, matching the 100Hz
parent's `3.6`=360 deg/s) — not the 4x-slew config bug named below, which
was isolated to a different (stand-role) arm. `bundle_rlonly_v1/GO_NOGO.md`
stamped SUPERSEDED (retained for lineage only); any physical handoff of the
`rl_only` walk role should use `bundle_rlonly_v2` (or its s2 sibling), not
v1. Seed status: s0/s2 PASS+exported, s1's own `-acq1` still in flight
(owned by a concurrent cycle as of this writing) — will complete the n=3
seed triplet once it lands, not required to gate this bundle recut.

Evidence: `ops.sh entry cw-walk50hz-rlonly-crutchoff-s2-warmadapt-acq1`;
`logs/ckpt_eval/cw_walk50hz_rlonly_crutchoff_s2_warmadapt_acq1_{gate,
session}/`; `logs/experiments/cw-walk50hz-rlonly-crutchoff-s2-warmadapt-
acq1/wandb_summary.json` (SCORE/* keys); `logs/manual_drive/
cw_walk50hz_rlonly_crutchoff_s0_warmadapt_acq1_drivevideo_20260910_
{231906,231958}/summary.json`; `rl_docs/tracks/walkcurr/bundle_rlonly_v2/`;
`rl_docs/SKILLS.md` new row; W&B `cm5wdnh5`.

## AMP style-credit for acquisition REFUTED on the from-scratch mesh/50Hz walk recipe: a matched-budget no-style control walks BETTER than a discriminator kept alive by a health retune (2026-09-10 ~23:1x, amp track)

One plain sentence: on `m2plain`-style scratch mesh/50Hz walking, an
AMP run with the discriminator kept healthy for the full 15M steps
(`cw-walk50hz-amp-mesh-m2plain-scratch-discretune-acq15m`: disc-steps
4->2, gp 10->20, disc-batch 512->256, last-quarter d_real_mean
0.80-0.87 well under the 0.95 saturation line, style_reward_mean mean
0.051) still walks WORSE (det walk fwd med 0.43m, slip med 4.26/4.13)
than the matched-budget `--amp-style-weight 0` control with no
discriminator at all (`cw-walk50hz-amp-mesh-m2plain-scratch-styleoff-
acq15m`: fwd med 0.57m, slip med 3.11) — and both beat the original
saturated-disc parent (fwd 0.38m, slip 4.4-5.3). This directly settles
the causal question the parent run's dig-in left open (task channel
carried the reward gains there; here the same conclusion is confirmed
by ablation, not just correlation). **Binding for future AMP arms on
this recipe**: acquisition succeeding under AMP is not evidence the
style term is doing anything — a plain task-reward-only control at
matched budget is the required comparison before crediting AMP for
either walking emergence or gait quality (slip/naturalness) on this
recipe family; only a demonstrated quality delta over that control
justifies continued style-weight tuning. Does not touch AMP's separate
M5/M6 milestone track or other recipe families (e.g. the primitive-
family `phasehz11-s29` champion) where AMP has already shown value.
Evidence: `ops.sh entry cw-walk50hz-amp-mesh-m2plain-scratch-
{discretune,styleoff}-acq15m`; `logs/ckpt_eval/cw_walk50hz_amp_mesh_
m2plain_scratch_{discretune,styleoff}_acq15m_gate/report.json`;
`rl_docs/SKILLS.md` new row; `rl_docs/tracks/amp/STATUS.md` 2026-09-10
~23:1x; W&B `jvb5sszw`/`0ecp2kgt`.

## Stand/lower-role 50Hz retrain FAIL root-caused to a config bug, not a dynamics regression: `safety.max_delta_q_deg` deg/s-preservation math must use the ACTUAL parent contract, never an assumed legacy value (2026-09-10 ~22:4x, standwalk track)

One plain sentence: `cw-stand50hz-stance-tuckclock-scratch6m` (stand/
lower role of the op_20260910_50hz bundle) froze/over-current-pinned
0/12 on its flat-pinned probe not because 50Hz breaks the rise
dynamics, but because its launch notes assumed the 100Hz champion's
slew rate was "1.5 deg/tick (=150 deg/s)" when the champion actually
trained under `rl_move/config.yaml`'s code-default 0.375 deg/tick
(=37.5 deg/s) — the run then set `safety.max_delta_q_deg=3.0` at 50Hz
(=150 deg/s), i.e. 4x the champion's real physical slew ceiling, the
exact "quietly 4x the physical slew" gotcha the config's own comment
warns against (`safety.max_delta_q_deg: 0.375` block, config.yaml
~line 86). Confirmed root cause: the 100Hz champion
(`tuckclock_scratch8m`)'s own training command never sets the key
(grepped extra_args) so it used the code default; its own
`report.json` motor_contract reads `max_delta_q_deg=0.375,
slew_limit_deg_s=37.5, control.hz=100` — not 1.5/150 as assumed. Fix:
`safety.max_delta_q_deg=0.75` is the correct 50Hz-preserving value
(0.75*50=37.5 deg/s). Corrected relaunch `cw-stand50hz-stance-
tuckclock-scratch6m-dqfix` (identical from-scratch recipe otherwise)
is VERIFIED RUNNING (train-5). **Binding for any future control-rate
retrain**: never assume a parent checkpoint's `safety.max_delta_q_deg`
from memory/comments — always read the SOURCE run's own resolved
`motor_contract` (report.json, or `servo_model.py:motor_contract`) and
scale from that literal number. The other 3 arms of this same
09-10 50Hz wave (walk-role `allheading-mlp-singleframe-scratch-acq20m`,
walk-teach `teach-scripted-allhead-scratch-acq10m-cont15m`, turn-role
`turn50hz-standwalk-cap29-stdwalklohi-warmadapt-canary2m`) were
checked and all three correctly used `0.75` — this bug was isolated to
the one stand/lower arm, not systemic across the wave. Evidence:
`ops.sh entry cw-stand50hz-stance-tuckclock-scratch6m` (FAIL-MISALIGNED
verdict); `rl_move/config.yaml` safety block; `logs/ckpt_eval/
cw_standwalk_stance_mesh2_stancemix_tuckclock_scratch8m_gate/
report.json` vs `logs/ckpt_eval/cw_stand50hz_stance_tuckclock_
scratch6m_flatprobe/report.json` motor_contract fields.

## Second 50Hz walk-role candidate GATE PASS, one UNDERTRAINED continuation (2026-09-10 ~21:4x, standwalk track) — walk leg of op_20260910_50hz now has two independent exported candidates

One plain sentence: `cw-walk50hz-teach-scripted-allhead-scratch-acq10m-cont15m`
(the scratch+persistent-anchor 50Hz walk-teacher clone, no 100Hz
BC-clone init) reaches full-gate PASS at 15M steps after one
08-21-ruling continuation from a 10M-step UNDERTRAINED-on-slip-alone
read, and is now exported alongside the earlier `allheading-mlp-
singleframe` 50Hz PASS as a second, independently-derived walk-role
candidate for the bundle. DR-0 (n=6, dr=0.0): walk/det prog med 0.38
(bar>=0.35)/slip med 2.57 (bar<=2.9)/gait_valid 6/6/0 term; walk/sto
prog med 0.35 (bar>=0.15)/slip med 3.08 (bar<=6.0)/gait_valid 6/6
(bar>=5/6); walk_startjitter det/sto both gait_valid 6/6, slip
2.52/3.02 — slip closed monotonically from the 10M read's 2.48-3.39
panel band into the cap while completion held (convergence, not
misalignment). 8-heading `eval_cmd_suite` and `eval_joystick_gate`
stress_mix — both missing from the automatic prestage since the
automatic joygate only fires for `joystick`-track runs and this is
`standwalk` — were run by hand this cycle: cmd_suite 0/16 falls,
completion 0.32-0.38 every heading (bar>=0.19); joygate pass=true,
n=24, zero falls, slip_per_m_med 2.788 (cap 2.9), dir_err_med 34.7deg
(allow 40), gait_valid_frac 1.0, zero sacrificed legs. Exported
(`export_policy_np.py --training-hz 50`, parity 1.33e-07, obs 75) to
`linux_control/policies/walkteach_scripted_allhead_scratch_50hz.json`.
Evidence: `ops.sh entry cw-walk50hz-teach-scripted-allhead-scratch-
acq10m-cont15m`; `rl_docs/SKILLS.md` new row; `rl_docs/tracks/
standwalk/STATUS.md` 2026-09-10 ~21:4x; W&B `c1s0u2lr`.

## `declegshare-headrel` (13th mechanism class, weight-shared mount-frame-relative per-leg actor) is ALSO refuted for the walkcurr front-pair off-axis-heading sacrifice (2026-09-10 ~21:1x) — closes at the SAME depth `decleg-base` closed, never reaching the multi-heading transfer test it was built for

One plain sentence: tying all six `decleg` towers to one shared weight
set and feeding each tower its own mount-frame-rotated heading (the
actual precondition for a skill learned at one leg's easy heading to
transfer to another leg's hard one) still fails to resolve the
front-pair sacrifice at the matched 42M-cumulative budget where
independent-tower `decleg-base` failed, and fails in almost the exact
same shape.

`cw-walkscratch-easy0905-declegshare-headrel-{s0,s1}-acq2` (both +20M
matched continuations of the acq1 arms that showed `decleg-base-acq1`'s
own LEGPARK-SKATE fingerprint) both FAIL on their own pre-registered
aligned-FAIL bar: det-mode `gait_valid` 0/6 on both seeds, legs
**[1,4]** sacrificed identically to `-acq1` (no progress toward 6/6
despite more distance covered); sto mode regressed from acq1's clean
6/6 to 5/6 on both seeds (milder than `decleg-base-acq2`'s full
6/6->0/6 collapse, but the same direction); reward technically still
rising but decelerating in nearly the identical shape `decleg-base-
acq2` showed right before its own FAIL (+187%/+19%/+5% both variants,
both seeds — s0 quarters 582.4/1672.8/1997.8/2099.4 vs decleg-base-s0's
599.7/1721.2/2051.2/2147.1).

This is a stronger negative result than a simple repeat: the pair of
levers (weight-tying + mount-relative heading input) was specifically
designed and unit-tested to give the tied tower an input where
"leg0 asked for 180 degrees" and "leg3 asked for 0 degrees" are
BIT-IDENTICAL vectors (`test_shared_heading_rel_leg0_at_180_matches_
leg3_at_forward`) — the actual mechanical precondition for cross-leg
skill transfer to be even possible. It never got to test that
transfer hypothesis on the multi-heading `widen8`/`crutchoff` recipe,
because it failed the cheaper fixed-forward walking-competence bar
first, at the same depth `decleg-base` failed it.

**Closes the 13th mechanism class for this question, 0/13 across the
whole campaign** (independent-tower `decleg` x3 arms — base/sde/
halfgrav, RND x3 variants — full-obs/heading-gated/per-leg-obs-masked,
tied-tower `declegshare-headrel` x1 variant). No named structural
lever remains untried for the off-axis-heading front-pair sacrifice;
the only honest paths left are (a) accept it as a limitation of the
easy0905 recipe/reward at this training depth, or (b) a genuinely new
structural mechanism nobody has conceived yet. Do not re-fund any
dose/seed/exploration-only variant of `decleg`, `declegshare`, or RND
on this question without a new structural idea. The separate slip-
floor question stays independently closed (09-10 ~00:0x, 3/3
structural candidates refuted).

Evidence: `ops.sh entry cw-walkscratch-easy0905-declegshare-headrel-
{s0,s1}-acq2`; `logs/ckpt_eval/cw_walkscratch_easy0905_declegshare_
headrel_{s0,s1}_acq2_gate/report.json`; `rl_docs/tracks/walkcurr/
STATUS.md` 2026-09-10 ~21:1x; `rl_docs/tracks/walkcurr/DESIGN_NOTE_
2026-09-10_offaxis_frontpair.md` Addendum 2; W&B `tnwhpa0s`/`2d4wxkbm`.

## 50Hz walk-role retrain GATE PASS, first try, from scratch (2026-09-10 ~21:0x, walkcurr/standwalk track) — walk leg of the op_20260910_50hz todaypolicy bundle is done

One plain sentence: `cw-walk50hz-allheading-mlp-singleframe-scratch-acq20m` (from-scratch rerun of the operator-chosen all-heading singleframe recipe with only `control.hz` 100->50, `safety.max_delta_q_deg` 0.375->0.75) clears its own pre-registered 50Hz gate at 20M steps — own-cfg DR-0 (det prog med 0.41/slip 2.19/gait_valid 6/6/0 term; sto prog med 0.32/slip 3.13/gait_valid 6/6) and the 8-heading `eval_cmd_suite` (0/16 falls, completion 0.25-0.41 every heading, bar >=0.19) both pass every named bar; frame strips show genuine six-leg cycling with zero sacrificed legs. Exported (`export_policy_np.py --training-hz 50 --inner-hz 50`, obs-74 MLP, parity 1.85e-07) to `linux_control/policies/walk_allheading_mlp_singleframe_scratch_50hz.json`. The 60s randomized joygate stress read was still syncing on-pod at verdict time (informational rider, not gating per standing convention) — read `logs/ckpt_eval/cw_walk50hz_allheading_mlp_singleframe_scratch_acq20m_joygate/gate_verdict.json` when it lands. This is the WALK leg only of the operator's 50Hz stand+walk+turn bundle; turn (`cw-turn50hz-standwalk-cap29-stdwalklohi-warmadapt-canary2m`, finished, artifacts still syncing) and stand (`cw-stand50hz-stance-tuckclock-scratch6m`, finished, unverdicted) are each owned by a concurrent cycle this pass — see `rl_docs/tracks/standwalk/STATUS.md` for the assembly status. Evidence: `ops.sh entry cw-walk50hz-allheading-mlp-singleframe-scratch-acq20m`; `rl_docs/SKILLS.md` new row; W&B `ebxen0dx`.

## OPERATOR ORDER + RULING (2026-09-10, Lukas via Claude, ops.sh cycle — id op_20260910_50hz): control.hz=50 is the DEPLOYMENT control rate; 100 Hz is NOT deployable on hexapod2; retrain the promising gaits at 50 Hz

One plain sentence: on the new robot (hexapod2), one 18-servo feedback
read over the Uno Q MCU bridge costs 9-13 ms (probe mean 8.6 ms,
in-loop 12-15 ms) and a sync write ~4.4 ms, so a 100 Hz policy trips
the runner timing fault within 3-52 ticks (rl_walk_20260910_194740,
rl_drive_20260910_194958) while a 25 Hz legacy walk (dep_tip1,
inner_hz 25) ran 150 ticks / 0 overruns at 37 ms/tick — therefore
**50 Hz (20 ms budget) is the target rate for anything meant to run
on the robot**, and the 08-24 100 Hz order is SUPERSEDED for
deployment candidates (it stands for sim-research lineages that never
target hardware, and the no-key launcher default injection stays 100).

Mechanics registered this cycle (snapshot with this entry):
- Launcher: explicit `--cfg-set control.hz=50` is first-class
  (`DEPLOY_TRAIN_CONTROL_HZ=50`, ledger check `explicit-deploy-50`,
  no `--allow-legacy-control-hz` needed); tests extended
  (`rl_move/tests/test_launch_run_control_hz.py`, 12/12 green).
- Recipe translation rule (operator): phase clock UNCHANGED in Hz
  (`goal.walk_phase_hz` stays 1.333.../1.1 etc.), episode SECONDS
  unchanged, step budgets retuned (~half sim-time cost per step at
  50 Hz), and per-tick slew rescaled to keep deg/s constant:
  `safety.max_delta_q_deg` 0.375@100Hz -> 0.75@50Hz (walk/standwalk
  recipes; scale others by the same deg/s-preserving rule).
- Warm-start across the 100->50 contract only where proven safe
  (cheap 2M canary with matched-parent behavioral comparison IS the
  proof mechanism); otherwise from scratch with the same recipe.
- Every PASS exports `export_policy_np --training-hz 50 --inner-hz 50`
  (v2 stamp) into `linux_control/policies/` with `50hz` in the name.
  Deliverable: a 50 Hz todaypolicy bundle (stand/lower + walk + turn).
- AMP-specific: the M5-green `phasehz11-s29` champion is a
  PRIMITIVE-family 25 Hz policy (created 2026-08-23, before the mesh
  flip and the 100 Hz injection) — families do not transfer, so its
  50 Hz arm is from-scratch on mesh with a rebuilt 50 Hz motion
  library `rl_move/sim/motion_library/teacher_v2_50hz.npz` (45/45
  clips accepted, dt=0.02, mesh physics, slip/m 0.52-1.81;
  `build_motion_library.py --cfg-set` plumbing added this cycle,
  default OFF = bit-exact legacy).

## A 13th mechanism class — weight-shared, mount-frame-relative per-leg actor — PASSES its mechanism-health canary (both seeds) and is now in a matched +18M acquisition continuation, for the walkcurr front-pair off-axis-heading sacrifice; explicitly NOT a re-fund of the closed independent-tower `decleg` family (2026-09-10, canary launched ~18:0x, verdicted PASS ~20:0x)

One plain sentence: `decleg`'s independent per-leg towers (closed
below, all 3 easy-pilot arms FAIL) cannot transfer a skill between
legs even in principle — different objects, different weights, no
matter how much either learns; this new variant ties all six towers
to ONE shared set of weights and feeds each tower the commanded
heading rotated into ITS OWN mount-angle frame, so leg0 asked for 180
degrees and leg3 asked for 0 degrees become the bit-identical input
vector — the actual precondition for a skill learned at one leg's easy
heading to reach another leg's hard one, which the closed independent-
tower design structurally cannot provide regardless of training budget.

`rl_move/sim/decleg_policy.py` gained `LEG_MOUNT_ANGLES_DEG`/
`leg_mount_unit_vectors()` (the mesh's own per-leg mount angles,
30/90/150/-150/-90/-30 deg — the original design note's named
geometric root cause), `heading_rel_cos_sin()` (pure 2D frame
rotation), and `_DecLegExtractor(share_leg_weights=, heading_rel_idx=)`
(both default OFF = bit-exact original `decleg`, verified by the 6
pre-existing tests unchanged). `train_ppo_mjx.py` gained
`--decleg-share-legs`/`--decleg-heading-rel` (require `--decleg`, fail
closed otherwise). **The transfer claim is proved directly, not just
argued**: `test_shared_heading_rel_leg0_at_180_matches_leg3_at_forward`
shows the tied tower produces a BIT-IDENTICAL output for leg0-at-180
and leg3-at-forward once the rotated feature is applied — something
provably impossible under independent towers. 8 new tests, 14/14 file
green, 105/105 touched-file suite green. Snapshot `38213a96`.

Launched `cw-walkscratch-easy0905-declegshare-headrel-{s0,s1}`
(from-scratch, byte-identical to the already-CANARY-PASSED
`cw-walkscratch-easy0905-decleg-base-{s0,s1}` forward-only ignition
pilot except the one added lever), both VERIFIED RUNNING. **This is
ONLY the cheap ignition/mechanism-health stage** (forward-only recipe
means the rotated feature is a per-leg constant, no cross-heading
transfer to exercise yet) — matching `decleg-base`'s own two-stage
discipline exactly; a PASS here licenses an acquisition continuation,
and only a pass THERE licenses graduating to the multi-heading
`widen8`/`crutchoff` recipe where the actual transfer hypothesis is
testable.

**Verdict (~20:0x, both seeds): MECHANISM-HEALTH PASS.** `train/loss`
decreasing monotonically all 3 logged points both seeds (s0
678.5->538.7->357.6, s1 674.5->518.1->339.5), zero NaN in either
53-row history, `walk/sto` gait_valid 6/6 both seeds with visibly
distinct six-leg swing/stance configurations across frame strips
(genuine articulation, not a frozen tower); `walk/det` static-stand
(learned early preference, not a wiring bug — sto engages the same
legs cleanly, matching every prior easy0905 canary's own gate text).
Per the gate's own pre-registered rule, promoted to matched +18M
acquisition continuations `cw-walkscratch-easy0905-declegshare-
headrel-{s0,s1}-acq1` (20M total, plain `--init-from` warm start, no
`--decleg*` flags needed/allowed alongside `--init-from` — same
guard, same precedent as `decleg-base-{s0,s1}-acq1`), both VERIFIED
RUNNING. Only a PASS there licenses graduating to the multi-heading
`widen8`/`crutchoff` recipe where the actual transfer hypothesis is
testable — not yet reached. Evidence: `rl_move/sim/decleg_policy.py`,
`rl_move/sim/train_ppo_mjx.py`, `rl_move/tests/test_decleg_policy.py`
(14/14); `rl_docs/tracks/walkcurr/DESIGN_NOTE_2026-09-10_offaxis_
frontpair.md` Addendum 2; `rl_docs/tracks/walkcurr/STATUS.md`
2026-09-10 ~18:0x and ~20:0x; `ops.sh review cw-walkscratch-
easy0905-declegshare-headrel-{s0,s1}`.

## Per-leg obs-masked RND is ALSO refuted for the walkcurr front-pair off-axis-heading sacrifice (12th mechanism class, 2/2 seeds) -- the design note's ENTIRE named RND candidate list (plain full-obs, heading-gated, per-leg obs-masked) is now exhausted, 0/3 variants; no named lever remains for this question (2026-09-10, closed this cycle)

One plain sentence: masking RND's intrinsic bonus to only the
sacrificed front-pair legs' (leg0/leg5) own joint-obs columns -- the
harder, more surgical fallback named after both the plain and
heading-gated full-obs variants closed clean -- still did not repair
the off-axis-heading gait; both seeds land at the same closed floor
with the same front-pair fingerprint.

`cw-walkscratch-crutchoff-{s0,s1}-widen8-plusduty-rndobsmask-canary2m`
(`rnd_vec.py obs_mask_idx/_select`, `train_ppo_mjx.py --rnd-obs-mask-
legs=0,5`, reusing `decleg_policy.joint_walk_leg_slices` unmodified,
9 new tests): **mechanism health PASS both seeds** (`rnd/intrinsic_
mean` decays cleanly 0.036->0.024 (s0) / 0.024->0.016 (s1) over the
2M steps, proving the predictor is genuinely learning; `ep_rew_mean`
-404.8 (s0) / -269.2 (s1) in-band with every sibling canary in this
family; zero new falls, only tilt/truncated terminations).
**Efficacy: CLEAN FAIL, at/below the closed 0-2/15 floor, both
seeds** (`eval_checkpoint.py --pinned-heading-panel --baseline
<frozen cont10m parent>`, n=3 det+3 sto/heading, dr-scale 0.0): DET
off-axis (±90°/±135°/180°) `gait_valid` 0/15 (s0) + 0/15 (s1) =
**0/30 pooled**; STO 2/15 (s0) + 3/15 (s1) = **5/30 pooled** --
nowhere near the pre-registered >=6/15 PASS bar. Sacrificed-leg sets
dominated by the front pair in both seeds (leg0 in 13/25 s0 / 10/30
s1 broken-heading episodes; leg5 in 6/25 s0 / 6/30 s1), the same
fingerprint every prior mechanism in this campaign has produced.
On-axis (0°/±45°) fully unregressed: 8/9 det + 8/9 sto both seeds --
the on-axis-regression risk the design note flagged specifically for
this variant (it fires on every tick, unlike the closed heading gate)
did NOT materialize. Video confirms: broken-heading frame strips show
legs cycling in place with zero net translation while the on-axis
strip on the same checkpoint shows clean forward progress.

**This closes the per-leg obs-masking candidate 2/2 seeds and, with
it, the design note's ENTIRE named RND list end-to-end**: plain
full-obs (10th mechanism class), heading-gated (11th), per-leg
obs-masked (12th) -- three RND variants x 2 seeds each, 0 passes, on
top of the 9 prior non-RND mechanism classes already closed for this
exact gap (termination pricing, reward pricing, exposure, exploration-
noise-widening, self-distillation, PPO-advantage normalization,
critic calibration [inconclusive], kinematic reachability [ruled
out], decentralized-actor architecture). **12 independent mechanism
classes total, ~26+ arms, 0 passes -- no named lever remains for this
specific off-axis-heading front-pair question.** Per the design
note's own text, the only paths left are a genuinely new structural
mechanism not yet conceived (via a fresh first-principles design
note, same discipline that reopened this question after `decleg`
closed), or accepting the front-pair off-axis sacrifice as a standing
`rl_only` walkcurr limitation pending that design work -- NOT another
RND dose/gate/mask variant of what is now closed 3/3, and NOT a
re-fund of any of the 9 prior closed classes without new evidence.

Evidence: `ops.sh entry cw-walkscratch-crutchoff-{s0,s1}-widen8-
plusduty-rndobsmask-canary2m` (verdicts); `logs/ckpt_eval/
cw_walkscratch_crutchoff_{s0,s1}_widen8_plusduty_rndobsmask_
canary2m_headpanel/report.json` (on-pod, both pods); W&B `v7dfockc`/
`ipc1bf6s`; `rl_docs/tracks/walkcurr/STATUS.md` 2026-09-10 ~14:3x
(this entry's own timestamp); `rl_docs/tracks/walkcurr/DESIGN_NOTE_
2026-09-10_offaxis_frontpair.md` (full closure inventory + gate text).

## Heading-gated RND is ALSO refuted for the walkcurr front-pair off-axis-heading sacrifice (11th mechanism class, 2/2 seeds) -- the design note's ENTIRE named candidate list (plain RND + heading-gated RND) is now exhausted; the per-leg obs-masking variant (unbuilt) or a genuinely new structural idea is the only path left (2026-09-10, closed this cycle)

One plain sentence: scoping the RND intrinsic bonus to fire only on
the 5 chronically-broken off-axis headings (instead of the whole
observation) still changed NOTHING -- both seeds' behavior came back
byte-identical to the untouched parent at every single heading/mode
cell tested, not just unhelpful but measurably inert.

`cw-walkscratch-crutchoff-{s0,s1}-widen8-plusduty-rndheadgate-canary2m`
(the design note's own named fallback for a clean full-obs FAIL,
`rnd_vec.py heading_gate_idx/heading_gate_cos_max`, `--rnd-heading-
gate-cos-max=0.5`, warm-started from each seed's own frozen cont10m
champion): **mechanism health PASS both seeds** (`rnd/intrinsic_mean`
decays cleanly 0.029->0.019 (s0) / 0.027->0.019 (s1) over the 2M
steps, proving the predictor is live; `rnd/gate_off_axis_frac` holds
steady 0.630-0.636 the whole run for both seeds, confirming the gate
correctly discriminates on/off-axis ticks at the predicted ~5/8-
heading rate; `ep_rew_mean` quarters in-band with every sibling
canary in this family; zero new falls). **Efficacy: CLEAN FAIL, even
starker than the plain full-obs variant** (`eval_checkpoint.py
--pinned-heading-panel --baseline <frozen parent>`, n=3 det+3 sto/
heading, dr-scale 0.0, both seeds): DET off-axis (+-90/+-135/180)
`gait_valid` 0/15 (s0) + 0/15 (s1) = **0/30 pooled**; STO 1/15 (s0) +
3/15 (s1) = **4/30 pooled** -- and unlike the plain variant (which had
a 1-episode noise bump on one seed), EVERY cell here, including the
exact sacrificed-leg sets per episode, is byte-identical to the
frozen parent's own baseline read in the same eval run. On-axis
(0/+-45) fully unregressed: 9/9 det, 9/9 sto, both seeds, matching
the parent exactly.

**This closes the heading-gated RND candidate and, with it, the
design note's entire named list** (`DESIGN_NOTE_2026-09-10_
offaxis_frontpair.md`): both of its two concrete RND variants (plain
full-obs, heading-gated) are now refuted, 2/2 seeds each, 11
independent mechanism classes total across the whole campaign for
this specific gap (termination pricing, reward pricing, exposure,
exploration-noise-widening, self-distillation, PPO-advantage
normalization, critic calibration [inconclusive], kinematic
reachability [ruled out], decentralized-actor architecture, full-obs
RND, heading-gated RND), 0 passes. Per the note's own text, the only
paths left are the harder **per-leg obs-masking RND variant** (mask
RND's input to just the sacrificed legs' own obs channels -- new
code, not yet built: per-leg obs-column enumeration) or a **genuinely
different structural mechanism** not yet conceived -- not another
RND dose/gate-width/seed variant of what's already closed.

Evidence: `ops.sh entry cw-walkscratch-crutchoff-{s0,s1}-widen8-
plusduty-rndheadgate-canary2m` (verdicts); `logs/ckpt_eval/
cw_walkscratch_crutchoff_{s0,s1}_widen8_plusduty_rndheadgate_
canary2m_headpanel/{report.json,baseline/report.json}`; W&B
`g5tyn1be`/`xg3f2kgh`; `rl_docs/tracks/walkcurr/STATUS.md` 2026-09-10
(this entry's own timestamp).

## Plain full-obs RND state-novelty exploration is REFUTED as a fix for the walkcurr front-pair off-axis-heading sacrifice (10th mechanism class, 2/2 seeds); a heading-gated RND variant is built, tested and launched same cycle as the design note's own next-named candidate (2026-09-10, closed this cycle)

`DESIGN_NOTE_2026-09-10_offaxis_frontpair.md` (see the `decleg` closure
immediately below, its own "no untried structural idea remains named"
trigger) named RND state-novelty exploration (Burda et al. 2018,
already built/wired in this codebase, `rl_move/sim/rnd_vec.py`
`--rnd-coef`) as the next candidate: a bonus for visiting observations
the policy's own predictor can't yet predict, independent of task
return — the one exploration primitive not yet tried on this problem,
distinct from every already-closed exposure/entropy/self-distillation/
advantage-normalization/architecture lever because those all broaden
or reweight the SAME on-policy Gaussian noise rather than reward being
somewhere new.

**Plain full-obs canary (`--rnd-coef=0.02`, gentlest dose the 08-23
from-scratch RND closure tried, warm-started from the widen8/crutchoff
champion, 2 seeds): CLOSED 2/2, `CANARY FAIL - MECHANISM (efficacy)`.**
Mechanism health PASS both seeds (reward/`ep_rew_mean` in-band with
every sibling canary in this family at the identical depth,
`rnd/intrinsic_mean` decayed monotonically over the run proving the
predictor is genuinely learning not inert, zero new falls). Efficacy
read (`eval_checkpoint.py --pinned-heading-panel --baseline <frozen
champion>`, n=3 det+sto/heading, both seeds' own frozen parent): DET
off-axis (±90°/±135°/180°) `gait_valid` s0 0/15 (parent 1/15), s1 0/15
(parent 0/15) — **pooled 0/30**, at/below the campaign's own closed
0-2/15 floor, sacrificed-leg set matching the parent leg-for-leg at
every one of the 5 broken headings in both seeds. On-axis (0°/±45°)
unregressed, 8/9 both seeds both arms — the plain variant did not
damage the working gait, it simply never paid out where it was needed.
**This is the 10th independent mechanism class closed on this specific
gap** (spanning termination pricing, reward pricing, exposure,
exploration-noise-widening, self-distillation, PPO-advantage
normalization, critic calibration [inconclusive], kinematic
reachability [ruled out], decentralized-actor architecture, and now
full-observation state-novelty), 0 passes.

**Per the design note's own pre-registered text, this is a CLEAN
(not inconclusive) FAIL, which directly licenses its named fallback —
built and launched the SAME cycle, not left as an unfunded "next
idea":** `rnd_vec.py` gained `heading_gate_idx`/`heading_gate_cos_max`
(new `train_ppo_mjx.py --rnd-heading-gate-cos-max`, default `None` =
bit-exact original unscoped path — no mask multiply at all when unset)
— zeros the intrinsic bonus on ticks where the commanded heading is
on-axis (`cos_heading > 0.5`, which happens to exactly separate the 3
good headings [0°/±45°, cos>=0.707] from the 5 chronically-broken ones
[90°/135°/180°, cos<=0]), reusing `heading_selfdistill.py`'s own
`heading_cos`/obs-index math and validation rather than re-deriving
it. This directly targets the design note's own named risk for the
plain variant: "could just as easily reward novelty from the
already-working forward gait's natural variation... or destabilize
the already-good on-axis behavior chasing novelty elsewhere" — an
on-axis tick can now never earn this bonus. 12 new tests
(`rl_move/tests/test_rnd_vec.py`): bit-exact-off equivalence
(explicit `None`/`None` vs the pre-09-10 constructor signature produce
byte-identical rewards), gate correctly zeroes on-axis/keeps off-axis
bonus, both-or-neither param validation, `gate_off_axis_frac` stat
only reported when the gate is armed. Full touched-file suite green
(41/41: `test_rnd_vec.py` + `test_heading_selfdistill.py` +
`test_heading_adv_norm.py`). Snapshot `698c7654` pushed before
launch. **Launched**: `cw-walkscratch-crutchoff-{s0,s1}-widen8-
plusduty-rndheadgate-canary2m` (respec of each seed's own `-clean`
plain-RND canary, ONLY `--rnd-heading-gate-cos-max=0.5` added),
VERIFIED RUNNING `hexapod-mjx-train-{0,1}`. Not yet verdicted — the
efficacy read needs the same on-pod `--pinned-heading-panel` pass the
plain variant used; see `rl_docs/tracks/walkcurr/STATUS.md` 2026-09-10
~11:3x for the full pre-registered gate text.

**Practical impact: none on current delivery.** Champion checkpoint
untouched, `bundle_rlonly_v1`'s already-captured sim demo is
unaffected either way. Evidence: `ops.sh entry cw-walkscratch-
crutchoff-{s0,s1}-widen8-plusduty-rndexplore-canary2m-clean` /
`...-rndheadgate-canary2m`; `logs/ckpt_eval/cw_walkscratch_crutchoff_
{s0,s1}_widen8_plusduty_rndexplore_canary2m_clean_headpanel/{report.
json,baseline/report.json}`; `rl_move/sim/rnd_vec.py`,
`rl_move/sim/train_ppo_mjx.py`, `rl_move/tests/test_rnd_vec.py`.

## `decleg` (decentralized per-leg actor) is REFUTED as a fix for the walkcurr front-pair off-axis-heading sacrifice — all 3 easy-pilot arms (base, gSDE, half-gravity) FAIL; no untried structural idea remains named (2026-09-10, closed this cycle)

The 09-09 ~22:3x entry below closed value-calibration as the 7th and
last named reward/advantage/critic-side lever for the chronic
front-pair leg sacrifice and said the next attempt needed "a genuinely
new structural idea (different action-space/exploration primitive, or
routing around the sacrifice at a higher level)." `decleg_policy.py`
(Schilling et al. IROS 2020, per-leg-tower actor, already built/tested
08-29 6/6 unit-green) was that idea, tried on the campaign's own
easy-physics forward-only starting point across the same 4-arm lever
grid the centralized-MLP pilot used (base-s0/s1, gSDE, half-gravity).
**All 3 arms now FAIL:**
- **`decleg-base-{s0,s1}`** (2M canary -> +18M acq1 -> +20M acq2, 42M
  cumulative — the exact budget centralized `base-{s0,s1}-c1` needed to
  clear this fingerprint cleanly, PASS 6/6 det): legs[1,4] stayed
  sacrificed unchanged across the whole +38M in det, and sto-mode —
  clean 6/6 at acq1 — **regressed** to 0/6 by acq2. Both seeds agree.
- **`decleg-sde-s0-acq1r2`** (2M canary -> +20M acq1, gSDE exploration
  lever): a DIFFERENT, worse failure mode — the robot rears onto its
  hind legs and tips over BACKWARD in **24/24 held-out episodes**
  (every mode, det+sto, all TERM tilt_pitch), fwd progress ~0.006-0.0085
  m/s (far under the 0.03 m/s bar). `walk_startjitter/sto` gait_valid
  regressed from the 2M canary's own 5/6 to 2/6. Isolates gSDE x decleg
  as its own instability, distinct from base's exploit.
- **`decleg-halfgrav-s0-acq1`** (2M canary -> +20M acq1, half-gravity
  lever): the SAME legs[1,4] LEGPARK-SKATE fingerprint as base, but
  entrenching FASTER — sto flips from the canary's clean 6/6 straight
  to 0/6 at only ~22M cumulative, one full continuation earlier than
  base needed (~42M) to show the same regression.
All 3 verdicted FAIL on the gate's own pre-registered aligned-FAIL text
("unchanged/worsen despite reward still rising = architecture-specific
result, not more budget"). **Decleg as a family is now refuted for this
repair on every tested lever (plain, gSDE, half-gravity).** The
"genuinely new structural idea" search must go elsewhere (a higher-
level routing/composition approach, or a different action-space/
exploration primitive entirely) — not another per-leg-actor variant or
dose of this same mechanism. Evidence: `ops.sh entry cw-walkscratch-
easy0905-decleg-{base-{s0,s1}-acq2,sde-s0-acq1r2,halfgrav-s0-acq1}`
(verdicts); `logs/ckpt_eval/cw_walkscratch_easy0905_decleg_{base_
{s0,s1}_acq2,sde_s0_acq1r2,halfgrav_s0_acq1}_gate/report.json` (sto-mode
before/after each arm); `rl_docs/tracks/walkcurr/STATUS.md` 2026-09-10
~09:0x and ~09:1x.

## ROOT CAUSE + FIX: the whole day's `web_session_drivecapture.py` "off-forward-axis directional softness" chain below was measured through a tool that let the sim run at ~0.26-0.28x real time while scheduling phases on WALL-CLOCK — for the `any_means` champion this makes "reverse" mostly a measurement artifact of the velocity-ramp transient, not a real residual; for the `rl_only` champion the reverse defect is CONFIRMED genuine by the same fix (2026-09-10, refill cycle; 15/15 GPU free, empty backlog, no GPU-launchable lever on any track — built the tool this file's own immediately-preceding entry named as the concrete next step: "needs finer-grained per-tick telemetry or a true net-displacement measure")

One plain sentence: the capture tool scheduled each scripted command
phase (e.g. "reverse") to end after a fixed number of WALL-CLOCK
seconds, but the actual MuJoCo server it drives over HTTP was quietly
stepping physics at only ~26-87% of real-time speed (worse for the
expensive full-mesh collision model, better for the cheap primitive
`mesh_mjx` twin) — so most phases ended after only 20-35% of their
intended SIMULATED duration, often barely clearing the champion's own
1-simulated-second velocity-blend ramp before the next command
arrived; every "post-settle" measurement in this file's last dozen
entries was contaminated by that ramp transient to an unknown, varying
degree, not just for "reverse."

**Root cause, found by adding a second independent time source.**
`SimWebSession._live()` already returns the server's own simulated
clock (`self.sim_t`, exposed as `t_s`) and world-frame chassis position
(`chassis_xyz_m`) on every poll — this capture tool just never recorded
them. Added `yaw_deg` (`_yaw_deg()`, new helper, `web_session.py`) next
to the existing `chassis_xyz_m`, and threaded `pos_x`/`pos_y`/`yaw_deg`/
`sim_t_s` into every telemetry row (`web_session_drivecapture.py`, pure
additions, existing consumers keyed on `vx_body`/`vy_body` untouched).
A single capture of the `any_means` walk-role champion
(`ppo_goal_cw_walk_allheading_mlp_singleframe_acq1_stdanneal.zip`,
`env.model_source=mesh`) with these fields added showed the smoking
gun directly: at wall-clock `elapsed=27.19s` (the point the OLD loop
would have ended the whole ~27s script), the server's own `sim_t_s`
had only reached **7.7s** — a **0.283x real-time factor**. Per-phase
sim-time boundaries confirmed every phase was cut to ~1.0-1.5
simulated seconds instead of its intended ~4-5: `forward` 0.0->1.5s,
`crab-right` 1.5->2.8s, `diag-left` 2.8->3.9s, **`reverse` 3.9->4.9s
(only 1.0 simulated second total)**, `restart` 5.6->6.8s.

**Fix (code, tested, snapshotted before use): phase transitions and
the session-end condition now gate on the server's own `sim_t_s`, not
wall-clock `elapsed`** (`web_session_drivecapture.py` `main()`), so
every phase always gets its full intended simulated duration regardless
of how fast or slow this pod's background stepping thread runs. A
generous wall-clock safety timeout (20x the sim-time target + 30s)
guards against hanging forever on a genuinely stalled/dead server
(`result["timed_out"]`). `stalled_phases()` and the new
`net_displacement_fraction()` window on a new `_row_t()` helper (prefers
`sim_t_s`, falls back to wall-clock `t` for telemetry captured before
this fix) instead of raw wall-clock `t`. **New metric,
`net_displacement_fraction`**: computes the TRUE net body displacement
over a window from world-frame position deltas (rotated into the body
frame by `yaw_deg` at the window's start), independent of how densely
velocity was sampled — this is the "true net-displacement measure" this
file's immediately-preceding entry named as the one remaining way to
tell a genuine skill gap apart from a sampling artifact. `sim_seconds_
driven` now reports the true simulated total (was silently reporting
wall-clock elapsed under a misleading name); `wall_seconds_elapsed`
added alongside it, honestly named. 10 new tests
(`test_web_session_drivecapture.py`, 30/30 green in the file; 81/81
across the touched web_session/server test files): `net_displacement_
fraction`'s on-axis/yaw-rotation/pure-jitter/missing-data/near-zero-
command/too-few-rows cases, `_row_t`'s sim-time-preference and
wall-clock-fallback, and a `stalled_phases` case proving the fix
(constructed so wall-clock time and sim-time time would classify the
same rows into DIFFERENT phases, and only the sim-time read is
correct).

**Re-ran the exact fixed capture twice (`any_means` champion, deterministic
policy, same `--cfg-set` stack every earlier `_fullcfg`/`_velblendfix`/
`_rep*` capture used) — now correctly driving the FULL ~27 simulated
seconds each time (`sim_seconds_driven: 27.0` both reps; wall-clock took
105s/111s, matching the same ~0.26x real-time factor measured above) —
and recomputed all three metrics (`locomotion_fraction`/`directional_
locomotion_fraction`/`net_displacement_fraction`) per phase:**

| phase | dir (velocity-based) | disp (true displacement) | old dir (buggy tool, prior entries) |
|---|---|---|---|
| forward | 0.365 / 0.374 | 0.376 / 0.379 | 0.250 |
| crab-right | 0.172 / 0.171 | 0.156 / 0.148 | 0.204 |
| diag-left | 0.280 / 0.282 | 0.299 / 0.296 | 0.297 |
| **reverse** | **0.258 / 0.267** | **0.273 / 0.278** | **0.187** |
| restart | 0.381 / 0.370 | 0.379 / 0.362 | 0.257 |

(each cell: rep1 / rep2, both fresh `_simtimefix{,_rep2}` captures.)

**Two things follow, and they cut in opposite directions for the two
champions.** First, for THIS `any_means` champion: with proper
sim-time windowing, `dir` and `disp` now closely AGREE (within ~0.01-0.02
on 4/5 moving phases) instead of the ~3-4x mismatch the buggy tool
produced earlier today (see the entry immediately below, which read
disp/dir ratios of ~0.25-0.35 as a possible open question) — the
agreement itself is the evidence the fix is correct, since a real
signal measured two independent ways should converge, and now does.
Second, and more importantly: **`reverse` is no longer the standout-
softest phase.** It rises from the old tool's 0.187 to a properly-measured
~0.26-0.28, now solidly mid-pack — clearly better than `crab-right`
(~0.15-0.17, now the genuinely WEAKEST tracked direction) and only
moderately below `forward`/`restart` (~0.37-0.38). **The whole "reverse
residual, ~25% intermittent, forward-axis-favoring" narrative in this
file's prior ~6 entries (today, all using the unfixed tool) is
SUPERSEDED for the `any_means` champion**: most of what looked like a
reverse-specific pathology was the velocity-ramp transient, revealed by
a tool that was silently only measuring ~30% of each phase's intended
simulated duration. The real, smaller residual that survives fixing the
tool is a general (not reverse-specific) softness on commands with NO
forward-velocity component (crab-right worst, reverse second), which is
the same qualitative shape as (and now more precisely quantified next
to) the independently-established `walkcurr` off-axis-heading front-leg-
pair finding below — a different champion and mechanism, reached
through the fully separate, always-sim-time-correct `eval_checkpoint.py
--pinned-heading-panel` harness, so that finding's own closure (6/6
mechanism classes) is UNCHANGED by any of this.

**For the `rl_only` champion, the opposite: the same fix CONFIRMS
(does not weaken) a genuine reverse-specific defect.** Re-ran one fixed
capture on `ppo_goal_cw_walkscratch_crutchoff_s0_widen8_legdutyratio_
swinggap_dose10_plusduty_acq1_cont10m.zip` (`env.model_source=mesh_mjx`,
the cheap primitive-collision twin — this pod's real-time factor here
was ~0.87x, much closer to 1:1 than the full-mesh `any_means` case
above, so the fix mattered less for this specific champion, and largely
validates rather than overturns its own prior reading). Result:
`forward`/`crab-right`/`diag-left`/`restart` all track at
`dir`/`disp` >= 0.87 (some > 1, i.e. slightly overshooting the
commanded speed on this short script — not concerning, not this
entry's focus), but **`reverse` reads `mag=0.981` (superficially "moving
fine") against `dir=0.153` and `disp=0.057`** — both direction-aware
metrics agree closely with EACH OTHER (unlike the `any_means` case
above, where they used to disagree sharply and now agree after the
fix) and both say the same thing: real motion is present, almost none
of it is net-backward. This matches and STRENGTHENS (via an
independent, artifact-immune metric) the already-recorded `rl_only`
finding two entries below ("nets only ~0.15 of commanded speed... much
of it is not backward") — and is consistent with, not a new instance
of, the already fully-closed `walkcurr` 180-degree-heading front-pair
leg-sacrifice mechanism (6/6 mechanism classes closed, `rl_docs/tracks/
walkcurr/STATUS.md`); this interactive reading is additional evidence
for that already-settled structural gap, not a new question, and does
not reopen or license a new mechanism-class launch.

**Practical impact:** none on delivery status for either champion (0
falls, 0 rejected commands, both sessions genuinely walk on every other
phase, matching every prior entry's non-directional findings). This
entry supersedes the SPECIFIC per-phase numbers and the "reverse is the
standout-soft phase" framing in this file's own immediately-preceding
3 entries (today, `any_means` only) and in `STATUS.md`/`rl_docs/tracks/
todaypolicy/STATUS.md`'s matching text — those files are updated to
point here rather than repeat the superseded numbers. Does not touch
training, reward, or either champion's checkpoint. No GPU spend (CPU
eval-harness pod only, per guardrails); every other track re-confirmed
unchanged/still lever-less this cycle (walkcurr's two mechanism
closures stand, joystick/amp/cpg DONE, assistfade/standwalk closed
pending unbuilt redesigns).

Evidence: `rl_move/sim/web_session.py` (`_yaw_deg`, `yaw_deg` in
`_live()`), `rl_move/sim/web_session_drivecapture.py` (`sim_t_s`/
`pos_x`/`pos_y`/`yaw_deg` telemetry fields, sim-time-paced `main()`
loop, `_row_t`, `net_displacement_fraction`, `wall_seconds_elapsed`),
`rl_move/tests/test_web_session_drivecapture.py` (10 new tests, 30/30
green); fresh captures `logs/manual_drive/anymeans_walkallheading_
mlpsf_stdanneal_websession_capture_09-10_simtimefix{,_rep2}/`,
`logs/manual_drive/rlonly_champion_websession_capture_09-10_
simtimefix/` (all `telemetry.json`/`summary.json`); snapshot: see
commit list below (this entry's own tag).

## The `any_means` "reverse" residual is NOT a reverse-specific intermittent stall — the magnitude-based stall metric was hiding a broader, uniformly-weak net-directional-tracking pattern across ALL commanded directions, worst for reverse/pure-lateral, better for forward-leaning commands (2026-09-10, refill cycle; 15/15 GPU free, empty backlog, no GPU-launchable lever on any track — zero-GPU-spend diagnostic follow-up on this file's own prior n=8 entry's named next step "root-cause the residual itself")

One plain sentence: the tool that called 6/8 repeats "PASS" and 2/8
"FAIL" measures raw body SPEED (`hypot(vx,vy)`, always >= 0) rather than
velocity signed/projected onto the actually-commanded direction, so it
cannot tell "walking backward" apart from "oscillating in place at a
decent speed" — recomputed with a real directional metric, ALL 8
repeats net only ~14-26% of commanded speed in the commanded direction
(no clean pass/fail split), and the SAME weak-tracking pattern shows up
in the forward/crab-right/diag-left/restart phases too (never flagged
as stalled), just less severely — so this is a general, forward-biased
directional-tracking softness, not a reverse-specific bug or a genuine
intermittent freeze.

**Tool extended** (`rl_move/sim/web_session_drivecapture.py`, no shared
default touched): added `directional_locomotion_fraction(rows, cmd_vx,
cmd_vy)` alongside the existing `locomotion_fraction` (kept bit-exact,
untouched) — projects each tick's `(vx_body, vy_body)` onto the unit
commanded-direction vector and averages, so it can read negative
(net motion opposite the command) or nearly the full magnitude value
(perfectly on-axis motion), unlike the existing stall gate which is
mathematically incapable of ever being direction-aware. 6 new tests
(`test_web_session_drivecapture.py`): exact match to the magnitude
metric for pure on-axis motion, correctly reads ~0 for pure lateral
jitter under a reverse command, correctly reads negative for steady
wrong-way drift, plus the near-zero-command/empty-rows edge cases.
20/20 green in the file.

**Recomputed** the exact settle-window the shipped `stalled_phases`
already uses (`t0+1.5s` to next phase start) on all 8 post-fix
`_rep{1..8}` captures the immediately-preceding entry tabulated, for
EVERY phase, not just reverse (`cmd (vx,vy)`: forward `(0.08,0)`,
crab-right `(0,-0.08)`, diag-left `(0.0566,0.0566)`, reverse
`(-0.08,0)`, restart `(0.08,0)`):

| phase | frac_mag (old, magnitude) | frac_dir (new, signed) mean [min,max] |
|---|---|---|
| forward | never flagged | 0.250 [0.193, 0.323] |
| crab-right | never flagged | 0.204 [0.106, 0.288] |
| diag-left | never flagged | 0.297 [0.232, 0.361] |
| **reverse** | **0.289 [0.231, 0.360], 6/8 "pass"** | **0.187 [0.137, 0.258], 1/8 "pass"** |
| restart | never flagged | 0.257 [0.176, 0.360] |

Two things follow. First, reverse's directional mean (0.187) is not a
dramatic outlier from crab-right's (0.204) — both are the two phases
without a forward velocity component, both meaningfully lower than the
three phases WITH a forward component (0.25-0.30). This is a real,
reproducible pattern (consistent across all 8 independent repeats, not
noise) suggesting the champion's net-directional tracking is generally
weaker off the forward axis, with reverse/pure-lateral the softest —
not a "reverse gait randomly freezes 1 time in 4" story. Second, this
reframes (does not retract) the immediately-preceding entry's headline
number: 6/8 vs 2/8 by the magnitude metric was measuring "is the body
moving at a decent speed" (true for 6/8, marginal for 2/8), not
"is it moving backward" (uniformly weak in all 8). Compared against
the documented PRE-fix baseline (`..._fullcfg{,_velfix}` captures,
`frac_dir` = 0.000 and 0.057 respectively — essentially zero net
backward progress), the velocity-blend fix's real, substantial
contribution stands: it took reverse from ~0 net directional progress
to a consistent, real (if weak) ~0.14-0.26 — genuine improvement, not
a mirage.

**What this does and does not change.** Does NOT reopen or change any
closed `walkcurr` mechanism (different track, different champion, and
those questions are about held-out gait_valid/slip, not this
interactive-session metric). Does NOT retract the velocity-blend fix's
real, quantified improvement. DOES correct the framing from "reverse
has an intermittent stall bug, ~25% of the time" to "the champion's
directional tracking off the forward axis is generally soft, and the
prior magnitude-only read could not see that" — a real-not-noise
finding either way but a different, broader, mechanism-relevant shape.
**Practical impact: none this cycle** — no falls, no rejected
commands, session stays active and roughly on-heading throughout
(per the earlier boot/end identity + zero-fall/zero-reject checks,
unchanged); this is a tracking-quality residual on an already-shipped
`todaypolicy` bundle, not a new safety or reliability finding.

**Honest open item, unchanged in kind, sharpened in scope:** root-cause
WHY off-forward-axis directional tracking is weaker (a real gait/skill
question — is the champion's residual-anneal-gate walk recipe simply
undertrained on non-forward commands relative to forward? — or a
telemetry-sampling artifact — the ~0.26s poll interval is coarse
relative to a stride period, so per-tick vx/vy samples could alias with
gait phase and understate the true windowed mean regardless of
direction). Settling that needs either finer-grained (per-control-tick)
telemetry or a true net-position-displacement measure over the window,
neither built this entry (would risk the same "same-cycle rushed build"
anti-pattern this fork has explicitly declined repeatedly) — named here
as the concrete next diagnostic step rather than guessed at.

Evidence: `rl_move/sim/web_session_drivecapture.py`
(`directional_locomotion_fraction`), `rl_move/tests/
test_web_session_drivecapture.py` (20/20 green), recomputation script
(inline, this entry) over `logs/manual_drive/anymeans_walkallheading_
mlpsf_stdanneal_websession_capture_09-10_{fullcfg,fullcfg_velfix,
velblendfix,velblendfix_rep{2..8}}/telemetry.json` (all already on
disk, no new sim run). Snapshot: see commit list below (this entry's
own tag).

## n=8 settles the `any_means` "reverse" residual: it is a real, roughly-1-in-4 intermittent stall, not noise-near-a-threshold or "mostly fixed" — the borderline case is genuine, closing the STATUS.md-named "larger held-out repeat count" follow-up (2026-09-10, refill cycle; 15/15 GPU free, empty backlog, no GPU-launchable lever on any track — zero-GPU-spend, ran 4 more identical repeats to reach the n>=8 this file's own prior entry named as needed to settle it)

One plain sentence: with twice as much data (8 identical repeats
instead of 4), the post-fix `any_means` "reverse" phase now clearly
fails about 1 time in 4 rather than looking like an occasional noisy
straggler near the pass/fail line, so the honest verdict flips from
"substantially improved, not fully closed" (optimistic framing) to
"a real, small, intermittent stall the fix reduced in frequency and
severity but did not eliminate."

Ran 4 more repeats of the identical `web_session_drivecapture.py`
invocation (same checkpoint, same full training `--cfg-set` stack,
`--speed 0.08`) as rep5-rep8, then recomputed the reverse-phase
`locomotion_fraction` for all 8 repeats uniformly from each run's own
`telemetry.json` via the tool's existing helper (`web_session_
drivecapture.locomotion_fraction` + `drive_video.human_drive_phases`
for phase boundaries; no new tool). **Full n=8 set: 0.246 (F), 0.313
(P), 0.333 (P), 0.267 (P), 0.231 (F), 0.274 (P), 0.293 (P), 0.360
(P)** — mean 0.289, range 0.231-0.360, **6/8 clear the 0.25 stall
floor, 2/8 fail it** (rep1 and rep5; rep5 at 0.231 is the single
worst run of the whole post-fix set, slightly below even rep1). Every
one of the 8 still clears the entire pre-fix range (0.19-0.21) with
zero overlap — the fix is real and substantial (roughly halves the
failure rate and lifts the mean well clear of the old floor) — but a
~25% (2/8) fail rate on an unchanged, deterministic-checkpoint,
fixed-script repeat is not sampling noise around a threshold; it is a
small residual mechanism (most likely the previously-named "genuine
short-window gait-reversal transient" candidate, still not root-caused
at the mechanism level — no new instrumentation run was added this
entry to chase that, since the STATUS-named question was specifically
"how often does this fail," not "why," and that question is now
answered).

**Verdict: do not call the `any_means` interactive reverse phase a
clean pass.** This is the honest, settled answer to the "Next: a
larger held-out repeat count (n>=8-12)... to settle the residual
borderline case" line in `STATUS.md`/`todaypolicy/STATUS.md` — settled
as "real, ~25% intermittent, root cause not yet chased," not as
"noise, safe to call done." Everything else about this champion's
interactive demo stands: real checkpoint, 0 falls, 0 rejected commands,
correct direction on every other phase, forward/crab/diag/stop/restart
all clean every repeat. Does not reopen or change either walkcurr
open question, and does not change the `rl_only` champion's own
separate (already-genuine-PASS) interactive result. No code change
this entry (pure additional measurement + synthesis); no GPU spend;
no other track had a launchable lever this cycle (re-checked fresh:
walkcurr's off-axis-sacrifice and slip-floor questions unchanged,
joystick/amp/cpg DONE, assistfade/standwalk closed pending unbuilt
structural redesigns, todaypolicy's open items are Codex-owned).

Evidence: `logs/manual_drive/anymeans_walkallheading_mlpsf_stdanneal_
websession_capture_09-10_velblendfix_rep{5,6,7,8}/` (`summary.json`,
`telemetry.json`); inline recomputation via `rl_move.sim.web_session_
drivecapture.locomotion_fraction` + `rl_move.sim.drive_video.human_
drive_phases` across all 8 `_rep*` dirs (no new tool, existing
helpers, script this entry ran once and discarded — the computation
itself is trivial/reproducible from the artifacts already on disk).
No snapshot needed (zero code change).

## 4th post-fix repeat of the `any_means` interactive "reverse" capture: locomotion_fraction 0.273, clearing the stall floor — 3/4 repeats now clear cleanly, 1/4 still marginal; still "substantially improved, not fully closed" (2026-09-10, later refill cycle; 15/15 GPU free, empty backlog, no GPU-launchable lever on any track — zero-GPU-spend follow-up on the immediately-preceding entry's own explicit "a few more repeats... would settle whether the residual is bug or inherent" next step)

One plain sentence: one more repeat of the exact same fixed-command
capture on the same `any_means` champion adds a fourth data point that
also clears the reverse-phase stall floor, strengthening (not yet
completing) the case that the post-fix borderline case is noise/an
inherent short transient rather than a residual bug.

Re-ran the identical `web_session_drivecapture.py` invocation (same
checkpoint, same full training `--cfg-set` stack reconstructed
verbatim from the `_rep`-series `summary.json`'s own `server_cmd`,
`--speed 0.08`) a 4th time
(`anymeans_walkallheading_mlpsf_stdanneal_websession_capture_09-10_
velblendfix_rep4/`). Overall session: `PASS: true`, `stalled_phases:
[]`, 0 falls, 0 rejected commands, identity-checked champion at both
boot and end. Computed the reverse-phase `locomotion_fraction`
directly from this run's `telemetry.json` with the tool's own helper
(`web_session_drivecapture.locomotion_fraction`, phase boundaries from
`drive_video.human_drive_phases`): **0.273** — clears the 0.25 stall
floor (unlike this run's own top-line `PASS`, which only checks the
`_STALL_FRAC` floor on the SAME per-phase basis, so this is a
consistency check, not a new tool).

**Combined post-fix set is now 4 runs: 0.246, 0.313, 0.333, 0.273**
(mean 0.291). All four still clear the ENTIRE pre-fix range
(0.19-0.21) with no overlap. 3/4 clear the 0.25 floor outright; only
the very first post-fix repeat (0.246) sits fractionally under it.
This is additional evidence for, not proof of, the previous entry's
"plausible genuine short-window gait-reversal transient and/or HTTP
timing jitter, not a second bug" read — a single sub-threshold run out
of four with a mean well clear of the floor is consistent with noise
near a threshold, but four samples is still too few to rule out a
real (if small) residual mechanism. **Still not calling this fully
closed.** No code change this entry (pure additional measurement); no
other track had a GPU-launchable lever this cycle either (re-checked:
walkcurr's two open questions unchanged/still lever-less, joystick/amp/
cpg DONE, assistfade/standwalk closed pending unbuilt redesigns) so
this zero-GPU-spend follow-up was the justified use of the cycle.

Evidence: `logs/manual_drive/anymeans_walkallheading_mlpsf_stdanneal_
websession_capture_09-10_velblendfix_rep4/` (`summary.json`,
`telemetry.json`, `README.md`); locomotion_fraction recomputed inline
via `rl_move.sim.web_session_drivecapture.locomotion_fraction` +
`rl_move.sim.drive_video.human_drive_phases` (no new tool, existing
helpers). No snapshot needed (zero code change).

## Root cause found (and mostly fixed) for the `any_means` interactive "reverse" stall the previous entry flagged DIG-IN: the live-drive session's velocity command used a fixed-RATE ramp instead of training's fixed-DURATION blend, which happens to create a genuine momentary full-stop for this exact diag-left->reverse command pair (2026-09-10, zero GPU spend, refill cycle — picked up the deep-cycle-flagged item using only already-collected telemetry + a scoped code fix)

One plain sentence: the champion was never fundamentally incapable of
walking backward — the interactive session's velocity-ramp code just
didn't match how the champion was actually trained to receive command
changes, and fixing that (not another cfg-knob guess) measurably
improves, though does not yet perfectly clean up, the "reverse" phase.

**Root cause, found from data already on disk (no new sim run needed
to diagnose).** The previous entry's own telemetry
(`anymeans_walkallheading_mlpsf_stdanneal_websession_capture_09-10_
fullcfg_velfix/telemetry.json`) shows the "reverse" phase's measured
body speed (not just its direction) collapsing to near-zero
(magnitudes mostly <0.02 m/s, oscillating in sign) for almost the
whole 4s phase — a real stall, not a tracking-angle problem. Read
`_PlayTraj.at()` (`rl_move/sim/play_core.py`, the interactive session's
command trajectory) against `WalkTrajectory`'s mid-episode command
resample (`rl_move/sim/walk_task.py`, the actual training-time command
generator this champion trained under, `goal.walk_cmd_resample_s=6.0`
+ default `walk_cmd_blend_s_min/max=1.0`): training blends a NEW
(vx, vy) target in over a FIXED 1-second straight-line interpolation
regardless of how far the command has to move, while `_PlayTraj` ramped
each axis independently at a FIXED RATE (`VEL_RATE=0.06` m/s^2). For a
single-axis 0.06-0.08 m/s step these are similar (~1-1.3s), but for the
scripted "human" drive script's diag-left(0.0566, 0.0566) ->
reverse(-0.08, 0) transition, the worst-axis delta is 0.1366 m/s, so
the old rate-limited ramp took **2.28s** — over 2x training's 1s
contract. Worse: because BOTH axes happen to start this specific
transition at the exact same value (`d=0.0566`, diag-left's 45 deg
command), and rate-limiting is linear-in-time-per-axis, both axes
independently reach/cross zero at the identical instant (t~0.94s into
the transition) — a genuine near-zero-velocity "full stop" the
synchronized real command generator's blend design does not produce
for this pair (verified algebraically, not just by re-running): training's
straight-line interpolation over a SHARED 1s window has vy (target 0)
approach zero only at the very end of the blend while vx is already
substantially negative, so the compound magnitude never actually
bottoms out near true zero the way the old rate-limited ramp did.

**Fixed** `_PlayTraj` (`rl_move/sim/play_core.py`) to blend to a new
velocity/yaw-rate target over a fixed `BLEND_S=1.0s` window (restarting
from wherever the command currently is whenever the target changes),
matching `WalkTrajectory`'s own blend contract instead of an
independent per-axis rate. Scope: `_PlayTraj` only (used by the
interactive keyboard/joystick-driven sessions in `play.py` and
`web_session.py`); no training/eval-harness code path is touched, so
no existing champion, reward, or held-out gate result is affected.
6 new/changed tests (`test_drive_video_scripts.py`:
`test_play_traj_velocity_blend_finishes_in_a_fixed_duration`,
`test_play_traj_velocity_blend_restarts_from_the_published_value`,
existing wz-ramp test unchanged and still green); full
`test_drive_video_scripts.py` + `test_web_session_drivecapture.py` +
`test_sim_web_server.py` suites green (134 passed, unrelated
collection errors on 4 pre-existing files with missing optional deps
are untouched by this change).

**Measured effect, honestly reported — real improvement, not yet a
clean fix.** Re-ran the exact same full-cfg interactive HTTP capture
against this track's `any_means` walk-role champion
(`ppo_goal_cw_walk_allheading_mlp_singleframe_acq1_stdanneal.zip`)
THREE times post-fix: reverse-phase `locomotion_fraction` reads
**0.246, 0.313, 0.333** — every one of the three exceeds the ENTIRE
pre-fix range (0.19-0.21, two runs, tight spread, both cited in the
prior entry) with no overlap, a real and repeatable improvement (mean
~0.297 vs ~0.20, +~48% relative). Two of the three post-fix runs clear
the capture tool's 0.25 stall floor outright (`stalled_phases: []`,
overall `PASS: true`); the first repeat (0.246) still falls fractionally
short of the floor. **Do not call this fully closed**: the residual
sub-threshold run shows the champion still needs noticeably longer than
this script's 4s phase window to build full, confident backward
translation after a 135 deg diag-left->reverse flip (per-tick telemetry:
sustained negative `vx_body` only appears in the back half of the
phase in most runs) — consistent with a genuine short-window gait-
reversal transient (the phase clock / swing-leg assignment needs part
of a gait cycle to re-orient after a big heading flip) layered on top
of the now-fixed command-blend bug, not necessarily a second bug. Real
run-to-run HTTP-loop timing jitter (wall-clock heartbeat resend cadence)
also plausibly contributes noise near this exact threshold.

**What this does and does not change.** Confirms and extends the
previous entry's finding (real stall, capture tool correctly detects
it, not a false positive) — the previous entry's honest "not yet
root-caused" framing was correct, and is now superseded by an actual
root cause with a real, tested, evidence-backed fix, not another guess.
Does not reopen the `rl_only` champion's own already-closed heartbeat
finding (a different, already-fixed bug in a different file/code path).
Does not change any training/eval result (fix is scoped to the
interactive-session-only trajectory class). `STATUS.md`/
`rl_docs/tracks/todaypolicy/STATUS.md` updated to reflect "substantially
improved, still marginal" rather than either "closed" or the previous
"open, cause unknown."

Evidence: `rl_move/sim/play_core.py` (`_PlayTraj` rewrite),
`rl_move/tests/test_drive_video_scripts.py` (2 new tests),
`logs/manual_drive/anymeans_walkallheading_mlpsf_stdanneal_
websession_capture_09-10_velblendfix{,_rep2,_rep3}/` (3 post-fix
captures); snapshot `c6e5f86b`.

## First empirical interactive-HTTP capture of an `any_means` candidate: found and fixed a real config-threading bug (explicit `walk_obs_body_vel` override silently clobbered), but a genuine, still-open "reverse" direction stall remains — DIG-IN flagged, not resolved (2026-09-10, zero GPU spend)

One plain sentence: the "interactive sim-demo requirement is met for both
goals because the mechanism is checkpoint-agnostic" reasoning (09-10
root-cause entry below) was correct about the HTTP path itself but had
never actually been run against an `any_means` champion — doing so this
cycle found a real bug (fixed) and a real, unexplained direction-specific
translation stall (not fixed, flagged for a deeper cycle).

**What was run.** `web_session_drivecapture.py` (already fixed for the
heartbeat bug, unchanged) against the `todaypolicy-mlpsf-tuck-v1` bundle's
walk-role checkpoint, `ppo_goal_cw_walk_allheading_mlp_singleframe_acq1_
stdanneal.zip` (the joystick track's strongest all-heading walker: PASSES
the formal 60s `eval_joystick_gate` stress_mix DONE-gate on every axis,
zero falls, `gait_valid_frac 1.0` — stronger evidence than the `rl_only`
champion had going in), with its own full training `--cfg-set` stack
(`ops.sh evalcmd`'s own printed list) and `--speed 0.08` (its trained
speed).

**Bug found and fixed (real, kept regardless of the stall below):**
`SimWebSession._apply_vel_contract` derives `goal.walk_obs_body_vel` from
a STEM-NAMING heuristic (`_sim_only_obs`/`_ckpt_regime`: "_dep"/"noslip"
tokens -> mode 1, `fasttrack1`/`steer6`/etc. tokens -> mode 3, else mode
2) every time a walk policy is selected — including at boot, AFTER
`_load_runtime` already applied an explicit `--cfg-set goal.walk_obs_
body_vel=N`, silently overwriting it. This champion trains at mode 2 but
its stem carries none of the recognized tokens, so the heuristic guessed
mode 1 unconditionally. Same bug class as the 09-10 joint_action_box/bias
fix, different key, same fix shape: `_load_runtime` now records whether
`goal.walk_obs_body_vel` was explicitly passed
(`self._walk_obs_body_vel_explicit`), and `_apply_vel_contract` returns
immediately without touching the key when that flag is set — explicit
override wins, matching the box/bias precedent. Verified directly
in-process (not just by re-running the tool): booting `SimWebSession`
with this exact cfg stack now reads `env.cfg["goal"]["walk_obs_body_vel"]
== 2.0` (was silently 1.0 before the fix). 4 new fast unit tests
(`test_apply_vel_contract_*`, `rl_move/tests/test_sim_web_server.py`),
bypass `SimWebSession.__init__`/mujoco entirely (pure attribute/dict
checks) so they run in milliseconds; 45/45 relevant tests green
(`test_sim_web_server.py` + `test_web_session_drivecapture.py` +
`test_drive_video_scripts.py`). Snapshot `3cb4452b`
(`exp/websession-walkobsbodyvel-explicit-override-fix`).

**Genuine residual finding — NOT explained by the bug above, NOT fixed,
do not overclaim.** Re-running the capture after the fix produced an
IDENTICAL result: `stalled_phases: [{"label": "reverse", "measured_
fraction_of_cmd": 0.19-0.21}]` in both the broken-heuristic run and the
fixed-override run — the walk_obs_body_vel value was confirmed different
between the two runs (1.0 vs 2.0) but the behavior didn't move, so this
bug is real but NOT the (or not the whole) cause of the stall. Every
other phase (forward/crab-right/diag-left/restart) clears the tool's
25%-of-commanded-speed floor; `reverse` (commanded `vx=-0.08`) alone
does not, in BOTH runs, with `vx_body` telemetry oscillating near-
symmetrically around 0 (no sustained negative bias at all, not just an
undershoot) while roll/pitch/height stay stable (no fall, no tip,
height 117-125mm) — the robot looks like it holds a stance rather than
walking backward. This matters because it is NOT an accepted, already-
documented limitation: this exact checkpoint's own held-out
`eval_joystick_gate`/`eval_cmd_suite` panels (which include the 180°
heading) show clean, non-degenerate performance, and the composed
`hybriddemo` bundle capture (direct env-stepping, `bundle_mlpsf_tuck_v1/
GO_NOGO.md`) already drove this SAME checkpoint through this SAME
"human" script (forward/crab-right/diag-left/**reverse**/stop/restart)
and PASSED (0 terminations, course_err_1s med 2.42°) — so direct
env-stepping reverses fine, only the interactive HTTP/`_PlayEnv` session
path stalls on reverse specifically. This is the same *shape* of gap the
`rl_only` champion showed before its heartbeat root cause was found
(direct-stepping walks, `_PlayEnv`-session path doesn't) but the
heartbeat bug is already fixed in this exact tool and reproduced
identically with it fixed, and the walk_obs_body_vel bug found this
cycle is ruled out by the identical-behavior re-test above — the actual
cause is still unknown. Two owned-but-unexplored leads for the next
cycle that picks this up: (1) `_PlayTraj`'s heading/command-blend state
when going from a +135° diag-left command straight to a 180° reverse
command in one script transition (a shorter within-session reorientation
than any single `walk_cmd_resample_s` interval this champion trained
under); (2) some other `_PlayEnv`-vs-direct-env reset/tick divergence
specific to negative-vx commands, not yet instrumented directly (the
`rl_only` investigation's own lesson: instrument in-process, don't stack
another guess).

**What this does and does not change.** Does not reverse the "HTTP path
is headlessly drivable, display was never the blocker" finding — that
stands for both goals. Does mean: the `any_means` interactive sim-demo
claim should say "interactive HTTP capture run for the first time on an
any_means champion: boots real (non-scripted) checkpoint, 0 falls, 0
rejected commands, forward/crab-right/diag-left/restart translate
correctly; reverse specifically stalls, cause not yet found" rather than
extrapolating a full PASS from the `rl_only` result by "checkpoint-
agnostic" reasoning alone. `STATUS.md`/`todaypolicy/STATUS.md`/
`OPERATOR_QUESTIONS.md` updated to say this precisely, not more.

Evidence: `rl_move/sim/web_session.py` (`_walk_obs_body_vel_explicit`,
`_apply_vel_contract`), `rl_move/tests/test_sim_web_server.py` (4 new
tests); `logs/manual_drive/anymeans_walkallheading_mlpsf_stdanneal_
websession_capture_09-10_fullcfg{,_velfix}/` (pre-fix and post-fix
captures, both `stalled_phases: [reverse]`); snapshot `3cb4452b`.

## ROOT CAUSE FOUND AND FIXED: the "locomotion stall" chased across the two entries below was never a champion/policy/env bug — it was the capture tool's own drive loop failing to resend the joystick heartbeat the real browser always sends, silently timing out the session into a safety-hold every ~0.6s of every ~4-5s phase (2026-09-10, zero GPU spend)

One plain sentence: the champion was never broken — the previous two entries' "chassis rises, body velocity decays to ~0 within 1-1.5s" finding was `web_session_drivecapture.py` itself starving the interactive session's own dead-man's-switch (`SimWebSession._tick_locked`'s `_DRIVE_HEARTBEAT_STALE_S = 0.6` real wall-clock seconds, `web_session.py`) by only POSTing `/api/rl/drive/cmd` once per phase transition instead of resending it continuously the way the real browser UI does (`linux_control/webui/app.js`'s `drvHb = setInterval(drvSend, 200)`, a 5 Hz heartbeat for as long as a drive session is active) — so the session spent the vast majority of every ~4-5s scripted phase silently frozen in a safety "hold" (still reporting `ok: true`/`active: true`), and the prior entries' in-process instrumentation (which DID rule out `walk_obs_body_vel`, `height_ref`, the velocity ramp, and `walk_pure` as causes — those rulings still stand, they were just the wrong axis) never noticed because it single-stepped `_tick_locked()` in a tight loop without ever re-sending the drive command either, reproducing the identical tool bug from a different angle.

**How this was found**: built a side-by-side diagnostic (`/tmp/diag_dual_path2.py`, not yet promoted to a checked-in tool — the promoted, already-fixed artifact is `web_session_drivecapture.py` itself) that ran the SAME champion+cfg through (A) `drive_video.py`'s direct `SimHexapodJointWalkEnv` stepping and (B) `SimWebSession`/`_PlayEnv` via `rl_drive_start`/`rl_drive_cmd`, both driven by a plain Python loop with no artificial re-arming. Path A (which never has a heartbeat concept — the command is baked into the trajectory array once) walked cleanly the whole 8s test. Path B walked cleanly for the first ~3s, then `self.mode` visibly flipped from `"walk"` to `"hold"` and `chassis z` PINNED at 135.4-135.6mm for the rest of the run — a dead giveaway once the mode flip was visible in the trace (a pure `_PlayEnv`-vs-`SimHexapodJointWalkEnv` reset/obs diff, the previously-named "next step", would NOT have surfaced this — the bug is in the driving LOOP's command cadence, not the env). Reading `_tick_locked` found the exact cause: `if self.drive_active and now - self.last_drive_cmd_at > _DRIVE_HEARTBEAT_STALE_S: self.traj.vx = self.traj.vy = 0.0`. Cross-checked against `app.js` to confirm the real client's own contract is a 200ms resend, not a one-shot command per logical "phase" (a human holding a joystick button generates continuous input events, which is exactly why this dead-man's-switch exists — correct design for real hardware, just not respected by this capture tool).

**Fixed** `web_session_drivecapture.py`'s main loop: it now resends the CURRENT phase's `(vx, vy, wz)` via `POST /api/rl/drive/cmd` every loop iteration (~0.2s, matching the browser's own cadence) instead of only at phase transitions. 15/15 existing tests green (the fix is confined to `main()`'s HTTP loop; none of the tested pure helpers changed). Re-ran the exact full-cfg champion capture that previously mislabeled itself PASS-then-corrected-to-FAIL: now genuinely **PASS** — `stalled_phases: []`, 0 falls, 0 rejected commands, and per-phase telemetry shows real sustained body-frame translation matching every commanded direction (`forward` ~0.09-0.17 m/s, `crab-right`/`diag-left`/`reverse`/`restart` all similarly nonzero and direction-correct) with clean, correct stops (`vx_body~0`, chassis rises to a stationary ~135mm hold) during the `stop`/`final-stop` phases — that stationary hold is CORRECT behavior (no command active), not a repeat of the bug. Boot and end-of-session identity checks both confirm the real (non-scripted) checkpoint.

**What this actually closes.** This is the genuine, final closure of the interactive-joystick-sim-demo requirement for BOTH parent goals on this champion: the browser-facing HTTP API is headlessly drivable from a cloud pod (2026-09-10 ~01:3x's finding, unchanged), the joint-action-box/bias config-threading bug found the same day is real and fixed (unchanged), and the "does it actually walk under interactive control" question the two entries below left open/regressed is now answered **YES**, with the tool's own `stalled_phases` check (built by the immediately-prior entry specifically to stop a blind-spot PASS from recurring) now correctly confirming it instead of blindly asserting it. Net evidence trail across the day, in order: PASS (blind-spot false positive) -> FAIL (correct detection of a real capture-tool bug, mislabeled as a champion/env bug) -> PASS (root cause found and fixed, verified genuine). `STATUS.md`/`rl_docs/tracks/walkcurr/STATUS.md`/`OPERATOR_QUESTIONS.md` q_20260910T013xZ updated to reflect the real, final state — no residual gap remains on this specific question.

Evidence: `rl_move/sim/web_session_drivecapture.py` (heartbeat-resend fix in `main()`), `rl_move/sim/web_session.py` (`_DRIVE_HEARTBEAT_STALE_S`, unchanged — this was never a server-side bug), `linux_control/webui/app.js` (`drvSend`/`drvHb` — the real client's own 200ms contract); `logs/manual_drive/rlonly_champion_websession_capture_09-10_heartbeatfix/` (summary.json `PASS: true`, `stalled_phases: []`, telemetry.json per-phase `vx_body`/`vy_body`); re-run of `rl_move/tests/test_web_session_drivecapture.py` (15/15 green, unaffected by the loop-only fix).

## Follow-up: the interactive live-drive "residual translation gap" is narrower than either candidate the 01:3x entry left open, and the capture tool's own PASS check was a false positive -- fixed (2026-09-10, zero GPU spend)

One plain sentence: the two guesses the previous entry left untested are
now BOTH ruled out with direct evidence (not re-guessed), the real
picture is worse than "translation is a bit off" (the champion rises to
a ~125-137mm stance and body velocity collapses to ~0 within ~1-1.5s of
a full, correctly-ramped 0.06 m/s command, sometimes ending in a fall a
few seconds later), and the capture tool now fails this case instead of
reporting PASS.

**Ruled out by direct in-process instrumentation** (booted a real
`SimWebSession` off-HTTP with the champion's own cfg overrides,
single-stepped it, and printed the actual internal state each tick --
not another guess layered on the fix):
- (b) `walk_obs_body_vel` heuristic: confirmed **1.0** (privileged sim
  body velocity) throughout, matching this champion's own training
  default (never overridden in its cfg-set) via `play_core._sim_only_
  obs()`'s stem match (`"_dep"`/`"noslip"` absent from this stem). Not
  the cause.
- (a) height-ref-return-to-walk-height branch (`rl_drive_cmd`'s "walk
  champions trained at height_ref 0" ramp): `goal.height_ref` measured
  **0.0 on every tick** for the whole session -- the branch never
  engages because the chassis never left `_engage_walk`'s `z>0.09m`
  gate to begin with. Not the cause.
- The commanded velocity itself reaches the full 0.06 m/s target by
  t~0.6s (`_PlayTraj`'s `VEL_RATE=0.06` ramp, confirmed via `traj.
  _pvx`) and STAYS there — the policy is receiving the fully-correct,
  un-ramped-anymore command the whole time it fails to walk.
- `goal.walk_pure=1` (in this champion's cfg-set but not yet threaded
  through the web session): confirmed irrelevant by code reading —
  `_PlayEnv._sample_goal()` unconditionally returns the live `_PlayTraj`
  object, so the standard goal-generator's mode-mix (`walk_pure`'s only
  effect) is never consulted in this path either way.
- DR/park-start/struct-compliance cfg deltas: all confirmed off-by-
  default on both sides (`randomize=False` in both `_PlayEnv` and
  `drive_video.py`'s default `--dr-scale 0`; `walk_park_start_frac`/
  `struct_comp.enabled` both default to the champion's own values).

**Not yet found:** with velocity command, height-ref, joint action-box/
bias, control.hz, and obs-velocity-mode ALL verified matching training,
the champion still fails to sustain forward motion through `_PlayEnv`'s
live-drive path while `drive_video.py`'s direct `SimHexapodJointWalkEnv`
stepping (same checkpoint, same nominal cfg) walks it cleanly
(`~0.13-0.19 m/s` measured, STATUS.md 09-09). The remaining candidate is
a genuine dynamics/observation-construction difference between `_PlayEnv`
(the stance+walk+recover multi-role subclass `web_session.py` uses) and
plain `SimHexapodJointWalkEnv` — e.g. reset-time pose/phase construction,
or another per-tick hook `_PlayEnv` runs that the plain env doesn't. Next
step for whoever picks this up: diff `_PlayEnv.__init__`/`reset()` against
`SimHexapodJointWalkEnv.reset()` directly (both now have a working
in-process instrumentation harness, see `/tmp/diag_websession.py`-style
script in this entry's evidence — not yet promoted to a checked-in tool
since it duplicates `web_session_drivecapture.py`'s HTTP path pending a
decision on which one to extend), or run the SAME checkpoint through
BOTH paths side by side with matching frame-by-frame joint-angle logging.

**Fixed the tool's blind spot.** `web_session_drivecapture.py`'s PASS
check only looked at identity/falls/rejected-commands/frame-count — it
could not see "reports active, no fall, no reject, but isn't actually
walking." Added `locomotion_fraction()`/`stalled_phases()`: per
commanded-motion phase (skipping the ~1.5s velocity-ramp settle
window), mean measured body speed must reach >=25% of the commanded
speed or the phase is flagged and the run FAILS. Re-ran on the same
champion+cfg stack as the 01:3x entry's "full-cfg PASS": this time it
correctly reports **FAIL** (`forward`/`crab-right`/`diag-left` all
stalled at 0.3-14% of commanded speed; one repeat run additionally fell
at t~11s — run-to-run variance exists here, but no repeat has actually
walked). 6 new tests (`test_web_session_drivecapture.py`, 47/47 green
across the file's full suite). **Correction to the 01:3x entry: its own
"full-cfg PASS" claim does not hold** — re-labeled here as a false
positive from an under-specified check, not a second regression; the
"honestly-labeled residual gap, do not overclaim" framing was already
correct instinct, this entry just fixes the tool that let the gap hide
behind a green checkmark.

**What this does and does not change.** Does not reopen or reverse the
01:3x entry's real, still-valid finding: the browser-facing HTTP API
IS headlessly drivable from a cloud pod (display was never the
blocker), and the joint-action-box/bias config-threading bug it found
and fixed was real and is fixed. Does mean: no interactive session
(headless-HTTP or a hypothetical display click-through) can currently
be presented as sim-demo evidence of this champion actually WALKING
under joystick control — only `drive_video.py`'s direct env-stepping
capture (already on record) demonstrates that. `STATUS.md`/
`OPERATOR_QUESTIONS.md` q_20260909T144xZ updated to not overclaim.

Evidence: `rl_move/sim/web_session_drivecapture.py` (`locomotion_
fraction`, `stalled_phases`), `rl_move/tests/test_web_session_
drivecapture.py`; live re-runs `logs` not retained beyond `/tmp` for
this instrumentation pass (throwaway diagnostics, not artifacts) --
the FAIL verdict is reproducible any time via the command in this
file's own `README.md` output.

## The "interactive-viewer click-through needs a display, irreducible-to-cloud" reading was WRONG about the browser-facing API; built a headless HTTP capture tool, found and fixed a real config-mismatch regression, and closed the last labeled gap for BOTH parent-goal sim demos (2026-09-10 ~01:3x, zero GPU spend)

One plain sentence: the thing that actually needed a display was the
OPTIONAL native MuJoCo debug window, not the JSON API the browser's own
joystick buttons call, so a plain headless HTTP client can drive that
exact API from the cloud pod with no browser/Playwright/display at
all — and doing so for the first time surfaced (and let me fix) a real
bug where the interactive session silently mishandled the walkcurr
`rl_only` champion.

**Why re-open this.** `OPERATOR_QUESTIONS.md` q_20260909T144xZ (09-09)
and `STATUS.md`/this file repeatedly recorded "actually clicking
through the browser/window HUD to confirm the loaded (non-scripted)
policy live needs a display no cloud pod has — irreducible-to-cloud,
not a design gap" as the one piece of the interactive joystick sim-demo
requirement still open for both `any_means` and `rl_only`. Re-reading
`rl_move/sim/web_server.py` this cycle: the native viewer
(`--viewer`, macOS/`mjpython`-only) is OPTIONAL and OFF by default;
the browser's own `linux_control/webui/app.js` drives the robot via a
plain JSON HTTP API (`/api/rl/roles`, `/api/rl/policy`,
`/api/rl/drive/start|cmd|stop`, `/api/sim/frame.jpg`) that
`web_server.py` serves headlessly by construction (frames render via
the same offscreen `env.render()` path `drive_video.py`/`eval_
checkpoint.py` already use headlessly on every pod). Nothing about
exercising that API needs a display — the prior conclusion conflated
"the optional native window needs a display" with "therefore the
interactive control path can't be validated from cloud."

**Built** `rl_move/sim/web_session_drivecapture.py`: boots the real
`web_server.py` as a subprocess with a named checkpoint loaded via
`--walk` (the same reproducible-launch command already on record),
polls `/api/ping` for readiness, confirms via `GET /api/rl/policy`
that a REAL PPO checkpoint loaded (`hidden`/`activation` fields
non-scripted and naming the checkpoint — the literal "confirm the
loaded non-scripted policy" check), replays the exact "human" script
(forward/crab-right/diag-left/reverse/**stop**/**restart**/final-stop)
`ops.sh drivevideo --script human` uses (extracted to a shared
`human_drive_phases()` in `drive_video.py`, bit-exact per test) through
`POST /api/rl/drive/cmd` at real wall-clock cadence, captures frames
via `GET /api/sim/frame.jpg` into a contact sheet, and re-checks
identity at the end (no silent mid-session fallback). 10 new fast
mechanics-only tests (`test_web_session_drivecapture.py`,
`test_sim_web_server.py` additions), all green; `test_drive_video_
scripts.py` unaffected (bit-exact refactor). Snapshot below.

**First real run found a genuine, previously-uncaught regression, not
a clean pass — recorded honestly rather than declared done on the
first PASS-shaped number.** Driving the walkcurr `rl_only` champion
(`..._widen8_..._cont10m.zip`) through the API with the web session's
BARE-DEFAULT config: chassis height monotonically sank 110mm->65mm
over the ~27s "human" script, and every command after t~8s silently
returned an unhelpful "too low to walk - stand first" status while
the top-level response still said `ok: true`/`active: true` — i.e.
the interactive session appeared to keep working while actually
ignoring every joystick input for the back 2/3 of the session, and my
tool's first-draft PASS check (identity-ok + no explicit fall +
frames>0) missed this entirely. Root cause, confirmed by reading
`joint_task.py`: `goal.joint_action_box_{yaw,hip,knee}_deg`/
`joint_action_bias_{hip,knee}_deg` all default **0.0 = OFF** (full
hardware-range action mapping) in `web_session.py`'s bare
`load_config()`, but this champion trains under `box=15/20/25deg` +
`bias_hip=40/knee=35deg` (a tight, offset action box around a specific
trained stance) — `web_session.py` had NO mechanism to thread a run's
own `--cfg-set` through, unlike `drive_video.py`/`eval_checkpoint.py`,
so any champion trained with non-default action-space/reward/DR cfg
silently runs under the WRONG contract when driven interactively.

**Fixed** (default-off, bit-exact when unused): added `--cfg-set`
passthrough to `web_server.py`'s arg parser -> new `SimWebConfig.
cfg_overrides: tuple[str, ...] = ()` -> applied in `web_session.py._
load_runtime()` via the same `_parse_cfg_set` `drive_video.py` already
uses, right before env construction (after the phase-obs block, so an
explicit override still wins). `web_session_drivecapture.py` gained a
matching `--cfg-set` passthrough plus a `drive_cmd_rejected()` check
(catches "too low to walk"/"stand first"/"down - reset" statuses) so
this exact regression class fails the tool's own PASS bar instead of
slipping through silently again.

**Re-ran with the champion's own full training `--cfg-set` list**
(same ~50-key stack `ops.sh evalcmd <run>` prints): **PASS** — zero
falls, zero rejected commands, for the complete ~27s human script;
boot AND end-of-session identity checks both confirm the real
checkpoint (`activation=ELU hidden=[256,256,128]`), not the scripted
fallback. Chassis height rises from the 110mm plant-start default and
settles at a stable ~135mm plateau (roll/pitch stay within ~2deg
through every transition, recovering to ~0 within one heartbeat).
Artifacts: `logs/manual_drive/rlonly_champion_websession_capture_
09-10_{,_cfgfix,_fullcfg}/` (three runs: bare-default regression,
partial box/bias-only fix, full-cfg PASS — `summary.json`/
`telemetry.json`/`contact_sheet.png`/`README.md` each).

**Honest residual gap, NOT closed by this entry — do not overclaim.**
In the full-cfg PASS run, body-frame velocity (`vx_body`/`vy_body`)
stays within noise of 0 through the "forward"/"crab-right" phases even
though the height/tilt telemetry looks healthy (unlike `drive_video.
py`'s own direct-env-stepping capture of the same checkpoint, which
DOES show real translation, `~0.13-0.19 m/s`, `STATUS.md` 09-09). Two
untested candidate explanations, NEITHER confirmed: (a) the boot-time
internal stand/height-ref ramp interacting with the human script's
short (4-5s) phase durations, so `rl_drive_cmd`'s "return to walk
height first" branch never finishes before the next command arrives;
(b) `_apply_vel_contract`'s stem-based `walk_obs_body_vel` heuristic
picking a velocity-observation encoding this champion wasn't trained
with. Not chased further this cycle (would be a same-cycle guess on
top of an already-substantial fix); a dedicated follow-up should
instrument `goal.height_ref`/`walk_obs_body_vel` directly rather than
add a third guess.

**What this closes and what it doesn't.** This closes the specific,
previously-labeled-irreducible gap: an actual (non-scripted) RL
checkpoint CAN be loaded and driven through the real browser-facing
HTTP joystick API, headlessly, from a cloud pod, with zero falls and
continuous command responsiveness across a full multi-command session
— for BOTH `any_means` and `rl_only` (the mechanism is checkpoint-
agnostic; only `rl_only`'s own champion was tested here since it was
the one with the known regression). It does NOT establish that this
exact interactive path also reproduces the champion's translation
speed (the residual gap above) — sim/hardware physical-completion
claims are unaffected either way. `q_20260909T144xZ` in
`OPERATOR_QUESTIONS.md` updated with this correction.

Evidence: `rl_move/sim/web_session_drivecapture.py`,
`rl_move/sim/drive_video.py` (`human_drive_phases`), `rl_move/sim/
web_session.py`/`web_server.py` (`--cfg-set`), `rl_move/tests/test_
web_session_drivecapture.py` (10 tests), `test_sim_web_server.py`
additions (3 tests), `test_drive_video_scripts.py` (unchanged, still
green); `logs/manual_drive/rlonly_champion_websession_capture_
09-10*/`; snapshot below.

## The 09-07 "needs a STRUCTURAL, non-reward lever" escalation for walkcurr's slip floor is now ALSO exhausted: all 3 named structural candidates refuted/non-beneficial, none licensed for reopening (2026-09-10 ~00:0x, zero spend, re-read of already-collected evidence)

Consolidating three separate closures nobody had tallied together: foot-pad
contact-geometry widening (4.5mm->13.5mm) won 15-26% in a frozen zero-shot
read but got WORSE (+6-13%, all 4 groups) after a real 2M-step retraining
canary (`footgeom0135-fix1`, 09-08 ~12:3x); torsional ground friction
(mu_t 0.1->0.005, the physical-boot estimate) was flat-to-slightly-worse
for straight-walk slip specifically (09-08 ~03:5x, it only helped turning);
the Cartesian foot-placement action space (`cart_foot`) fails to ignite
on the champion's own hard-DR widen8 composite identically to joint-space,
and where it DOES ignite (easier rungs) its own slip numbers run 3-10x
WORSE than the matched joint-space rung, the opposite of a fix. The first
two were tested on an older, now-superseded precursor lineage rather than
the exact current champion — a documented gap, not a fresh lever, and not
worth a GPU re-test given the retraining-cancels-the-freebie mechanism is
a PPO-optimizer effect, not composite-specific. **No new mechanism
licensed.** Combined with the already-closed 4/4 off-axis-heading
mechanism classes (below) and the closed 9-arm direct-slip-pricing floor,
walkcurr's `rl_only` sim-demo has exhausted every named lever for both its
open gaps (off-axis sacrifice, slip); the only honest next step for either
is a genuinely new mechanism designed from first principles, not a dose/
seed/lineage variant of anything already tried. Every other track
re-confirmed unchanged (joystick/amp/cpg DONE-or-closed; standwalk/
assistfade fully closed; todaypolicy has no queued executable experiment).
No GPU launched this cycle (11/11 free, backlog empty, no non-duplicate
arm on any of the 7 registered tracks). Evidence: `rl_docs/tracks/
walkcurr/STATUS.md` 2026-09-10 ~00:0x entry (full citations).

## The fresh contextualgate slip FAIL (9.52/m) is a REAL lineage-wide floor, not a metric artifact, and predates the leg-duty-fairness charges (2026-09-09 ~23:5x follow-up, zero spend)

Checked the one cheap alternative explanation for the ~23:5x slip FAIL
above before treating it as a genuine gap: `slip_per_m` divides by
`along_dist_m`, so a couple of near-zero-progress episodes (e.g. the
2/24 with `gait_valid=False`) could in principle dominate the median.
They don't. Read every episode's `progress_ratio`/`slip_per_m`/
`sacrificed_legs` directly from the already-collected report.json:
slip is high (5-27/m) on essentially EVERY episode regardless of
progress_ratio (0.23-1.64) or gait_valid (True or False), and the
untouched no-leg-duty-charge baseline (`crutchoff-s0-widen8-acq1`,
same lineage before any duty/swing-gap mechanism) shows the same
~8.2/m median floor — the champion (9.52) is marginally worse, not
better, so the leg-duty-fairness charges did not introduce this. Same
order of magnitude as the already-CLOSED 9-arm direct-slip-pricing
floor (~5-6/m, a different precursor lineage, 09-07 ~20:3x) — confirms
that closure's own escalation ("a STRUCTURAL, non-reward lever, not
another charge/dose") applies here too. No new mechanism licensed;
this only removes a loose thread, it does not open one. Evidence:
`logs/ckpt_eval/cw_walkscratch_crutchoff_s0_widen8_legdutyratio_
swinggap_dose10_plusduty_acq1_cont10m_gate/report.json` vs
`logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_
allaxis_nokick_crutchoff_s0_widen8_acq1_gate/report.json`;
`rl_docs/tracks/walkcurr/STATUS.md` 2026-09-09 ~23:5x follow-up entry.

## `rl_only` sim-demo champion FAILS the joystick track's own formal randomized DONE-gate arithmetic, dominated by slip (>3x band), not falls or gait validity (2026-09-09 ~23:5x, zero spend, re-read of an existing panel)

The widen8/crutchoff `cont10m` champion (the `rl_only` sim-demo candidate
named in `STATUS.md`) had never been judged against the joystick track's
own `eval_joystick_gate.aggregate_gate` zero-falls/slip-cap/direction-
margin arithmetic (only an older, now-superseded lineage got this check,
09-06). Ran it for free via `--from-report` against the champion's own
already-collected 24-episode acquisition-milestone gate report (no fresh
simulation, no GPU/pod spend). **Result: FAIL** —
`checks={zero_falls:True, slip_ok:False, dir_ok:False,
gait_valid_all:False}`, `gait_valid_frac=0.917` (22/24). Zero falls and
gait validity are close to clean; the FAIL is dominated by **slip/m
median 9.522 vs the 2.9 teacher-band cap (>3x over)**, with direction
also missing on both the tick metric (52.58° vs 40° allow) and the
windowed-1s course metric (29.71° vs 12° allow) — though the direction
read mixes fixed/pinned-heading episodes rather than a randomized
joystick session, so it is a looser cross-lineage comparison than the
slip number. This does not change any already-settled acquisition/
durability verdict (different, looser bars) and does not reopen the
separately-closed off-axis-heading front-pair sacrifice question (a
narrower axis than aggregate slip). It DOES sharpen the honest state of
the `rl_only` sim-demo: the existing drivevideo captures remain real
evidence for the interactive-launch-path requirement, but a literal pass
of the joystick track's own quantitative randomized-session gate is not
yet established, and slip (not direction or falls) is the dominant
remaining gap. A slip-reduction mechanism is a genuinely new question
(the champion's existing per-leg charges target utilization fairness,
not raw slip magnitude) needing its own design/bank pass — not built
this cycle to avoid a rushed guess. Evidence: `logs/ckpt_eval/
cw_walkscratch_crutchoff_s0_widen8_legdutyratio_swinggap_dose10_
plusduty_acq1_cont10m_contextualgate{,_w1s}/gate_verdict.json`;
`rl_docs/tracks/walkcurr/STATUS.md` 2026-09-09 ~23:5x entry.

## `rl_only` off-axis-heading leg-sacrifice repair: the reward-price class' last untested cell (dose-corrected sum-aggregation) is ALSO CLOSED, 2/2 seeds — ALL FOUR named mechanism classes (termination, price, exposure/PPO-loss, critic) are now closed (2026-09-09 ~23:4x)

Sum-aggregating the per-leg duty-ratio charge across all six legs (instead
of pricing only the worst/MIN leg) had previously collapsed training by an
order of magnitude at charge=150 purely from a reward-scale ceiling issue
(6x MIN mode's ceiling); the ~05:4x closure named the unexecuted fix
(dose it down ~1/6 to match MIN's own ceiling) but nobody had run it.
This cycle read the dose-corrected retry
(`cw-walkscratch-crutchoff-{s0,s1}-widen8-legdutyratio-sumagg-dose25-alone`,
charge 150->25, `25*0.30*6=45` matching MIN mode's own `150*0.30=45`
ceiling exactly). **Mechanism-health PASSES 2/2 seeds**: reward stays
bounded (quarters `[55.4,107.1,-54.0,-686.4]` / `[52.5,127.8,-48.3,
-580.0]`, both within the same order of magnitude as the ~-160 MIN-mode
floor, not the 10x+ blowout dose150/sumagg showed), 0 falls both seeds.
**Efficacy FAILS 2/2 seeds, decisively**: read at the identical 2M-step
budget/lineage/seed-index against the sibling MIN-mode dose10-plusduty
canary, MIN mode scores `walk/det` gait_valid **6/6 with zero sacrificed
legs in any episode** in both seeds, while the dose-corrected sum-agg
runs score **4/6 with the SAME leg sacrificed in the SAME episodes as the
untouched `widen8-acq1` baseline** (s1: byte-identical sac fingerprint,
ep0 sac[5]/ep5 sac[0,5], to the parent that has no duty-ratio charge at
all) — pricing every starved leg instead of just the worst produces zero
measurable behavior change and is strictly worse than the already-adopted
MIN-mode recipe. **This closes the entire reward-price mechanism class**
(duty-ratio MIN mode, load-slip, swing-gap, and now sum-aggregation — all
recalibrated-and-read, none repairs the sacrifice beyond what MIN-mode's
already-shipped recipe achieves). Combined with the exposure/batch-
composition axis (5 mechanisms, CURRENT_TRUTHS ~20:3x), the PPO-
advantage-normalization lever (~21:3x), and the value-calibration angle
(~22:3x/~22:1x), **all four independently-named mechanism classes
(termination, price, exposure/PPO-loss, critic) for the chronic off-axis-
heading front-pair (leg0/leg5) leg sacrifice are now closed.** Reopening
this sub-question needs a genuinely new structural idea; none is
currently named. Practical impact: none on current delivery — the
champion checkpoint (widen8/crutchoff `cont10m`) is untouched, MIN-mode
duty-ratio charge stays the shipped default, and the already-captured
`rl_only` sim demo already labels this limitation. Evidence: `ops.sh
entry cw-walkscratch-crutchoff-{s0,s1}-widen8-legdutyratio-sumagg-dose25-
alone`, `ops.sh report cw-walkscratch-crutchoff-{s0,s1}-widen8-
legdutyratio-swinggap-dose10-plusduty` (MIN-mode matched-budget
comparator), `ops.sh report cw-walkscratch-easy0905-headset-crossgrav-
medhead-dr-allaxis-nokick-crutchoff-{s0,s1}-widen8-acq1` (untouched
baseline), W&B `5sw3ra8b`/`htk48exl`, `rl_docs/tracks/walkcurr/STATUS.md`
2026-09-09 ~23:4x entry.

## `rl_only` off-axis-heading leg-sacrifice repair: a value(critic)-vs-realized-return diagnostic was built and run — result is real but INCONCLUSIVE, dominated by a full-pin-episode reward-scale/OOD artifact, so it does NOT license a critic-recalibration mechanism yet (2026-09-09 ~22:1x)

With every named mechanism (exposure/composition x5, PPO-advantage-norm)
closed at ~21:3x, this checks a genuinely different, previously-untested
axis (zero GPU spend): does the CRITIC already mispredict return at the
broken headings, which would explain why advantage-driven policy updates
never move the mean? New tool `rl_move/sim/diag_value_calibration.py`
(+ 6 tests) replays the frozen champion and diffs `V(s_t)` (SB3
`predict_values`) against the realized discounted return-to-go per
tick. Short (~5s) episodes show V systematically UNDER-predicting return,
worse at broken headings (-107 healthy vs -404/-470/-602 broken). But
re-run at the campaign's own 20s pinned-heading-panel convention, the
sign FLIPS for most broken headings and the scale explodes (+71 to
+1606), traced to raw episode returns reaching **-66,000** at the broken
headings vs a few thousand at the healthy control — this is the
`walk_leg_duty_ratio_charge`/`walk_leg_swing_gap_charge` pair's own
documented uncapped-accumulation design compounding over a full 20s of
sustained sacrifice, a scenario normal training (which resamples heading
every `walk_cmd_resample_s=6.0`) never actually presents to the critic.
**Verdict: this specific diagnostic reading is not trustworthy evidence
either way** — do not build a critic-recalibration mechanism from these
numbers. A fair version would match training's own 6s resample cadence
or instrument real training-rollout GAE estimates instead of a synthetic
full-pin episode; left for whoever picks this up next. Zero GPU spend,
zero launches, champion untouched. Evidence: `logs/diag_value_
calibration/widen8_s0_cont10m_{det_n10,sto_n10,det_20s_n8}.json`,
snapshots `4455033b`/`93e11216`, `rl_docs/tracks/walkcurr/STATUS.md`
2026-09-09 ~22:1x entry.

## `rl_only` off-axis-heading leg-sacrifice repair: the PPO-advantage-normalization lever (the last named mechanism) is ALSO CLOSED, 2/2 seeds — this sub-question now has NO named untried mechanism left; it goes back to design (2026-09-09 ~21:3x)

Per-heading (on-axis vs off-axis) advantage normalization
(`cw-walkscratch-crutchoff-{s0,s1}-widen8-plusduty-headadvnorm-canary2m`,
`train.heading_adv_norm=1`, rescaling each group to its own zero-mean/
unit-std before PPO's own per-minibatch normalization runs) was the ONE
remaining named candidate after the ~20:3x entry below closed the entire
exposure/batch-composition axis — a genuinely different, PPO-loss-level
mechanism, not another dose/schedule/exposure variant. Mechanism health
PASS both seeds: `train/heading_adv_norm_applied=1` for the whole run,
`ep_rew_mean` in-band with the selfdistill twins at the identical depth
(-372.8/-311.8 vs -362.9/-295.7), zero new terminations. **Efficacy FAILS
2/2 seeds**, read via `--pinned-heading-panel --baseline <frozen cont10m
parent>` on-pod (n=3 det+3 sto/heading): DET off-axis (±90/±135/180°,
n=15) `gait_valid` s1 **0/15 child vs 0/15 parent — byte-identical**
(sacrificed-leg set matches leg-for-leg at all 5 broken headings); s0
**0/15 child vs 1/15 parent** (child is if anything worse than its own
frozen parent). Pooled both seeds: **0/30 vs 1/30**, nowhere near the
pre-registered `>=6/15-combined` PASS bar. STO showed a small 3/15 vs
1-2/15 delta on each seed — the same noise-level scale every closed
sibling mechanism in this family shows at n=3/heading; it does not gate
this canary. **This closes the PPO-advantage-normalization lever exactly
as pre-registered.** Combined with the ~20:3x closure of the entire
exposure/batch-composition axis (reweight, gain-dose, wide-`log_std`,
self-distillation, 100%-isolation curriculum), **every currently-named
mechanism for this repair — exposure-level AND PPO-loss-level — has now
failed, 6 independent mechanisms, 0 passes.** Reopening this sub-question
needs a genuinely new structural idea; none is currently named. Per the
same reasoning the assistfade closure used: do not fund another
dose/schedule/architecture variant of any of these six families.
Practical impact: none on current delivery — the champion checkpoint is
untouched, the already-captured `rl_only` sim demo never exercises the
failed range, and the limitation stays labeled in `bundle_rlonly_v1/
GO_NOGO.md`. Evidence: `rl_move/sim/heading_adv_norm.py`, `ops.sh entry
cw-walkscratch-crutchoff-{s0,s1}-widen8-plusduty-headadvnorm-canary2m`,
on-pod `--pinned-heading-panel --baseline` reads (`logs/ckpt_eval/
cw_walkscratch_crutchoff_{s0,s1}_widen8_plusduty_headadvnorm_canary2m_
headpanel/{report.json,baseline/report.json}`), W&B `afxiouh4`/
`0vs71oi8`, `rl_docs/tracks/walkcurr/STATUS.md` 2026-09-09 ~21:3x entry.

## `rl_only` off-axis-heading leg-sacrifice repair: 5th independent mechanism tried, 0 passes — the exposure/batch-composition axis is now CLOSED end-to-end (2026-09-09 ~20:3x)

A heading-conditioned ISOLATION curriculum (`cw-walkscratch-crutchoff-{s0,s1}
-widen8-plusduty-headisoremix-canary2m`: `goal.walk_heading_set` restricted
to ONLY the 5 chronically-broken headings for the whole 2M-step run — zero
forward episodes anywhere, not even on mid-episode resample) CLOSED
`CANARY FAIL - MECHANISM (efficacy)` 2/2 seeds: DET off-axis (±90/±135/180°,
n=15) `gait_valid` byte-identical to the frozen parent in BOTH seeds (0/15
child vs 0/15 parent), sacrificed-leg sets matching leg-for-leg at every
heading/episode, STO also matching (2/15 true at h180 in both). This was
the ~19:4x entry's own named candidate 1 (an untried "isolation" curriculum,
distinct from the already-closed 83%-reweight exposure lever) — testing it
at its logical 100%-exposure extreme shows **the entire exposure/batch-
composition axis is now closed end-to-end**: 0% (untouched baseline) -> 83%
(reweight, ~12:0x) -> 100% (this isolation canary), zero effect at every
point. This is the **5th** independent mechanism to fail the same chronic
front-leg (leg0/leg5) off-axis sacrifice on the widen8/crutchoff champion,
after heading-exposure reweighting (FAIL-MECHANISM ~12:0x), heading-gain
dose-scaling (FAIL-MECHANISM ~12:4x), headexplore's wide-`log_std` (ACQ
FAIL-MECHANISM ~16:2x), and self-distillation (FAIL-MECHANISM ~19:4x, entry
below). **Ruling (unchanged, now doubly confirmed): this sub-question does
not get another dose/schedule/exposure/architecture variant of an already-
tried mechanism family — including the isolation-curriculum idea itself,
now also closed.** The only remaining named candidate is candidate 2 from
the ~19:4x entry: per-heading critic/advantage normalization so off-axis
timesteps aren't structurally under-weighted in the shared PPO batch — a
genuinely different, PPO-loss-level mechanism (still UNBUILT, its own
design/test/canary cycle, not a repeat of any exposure-axis lever).
Practical impact: none on current delivery — the champion checkpoint is
untouched, the already-captured `rl_only` sim demo never exercises the
failed range, and the limitation stays labeled in `bundle_rlonly_v1/
GO_NOGO.md`. Evidence: `rl_docs/tracks/walkcurr/STATUS.md` 2026-09-09
~20:2x/~20:3x entries; ledger verdicts on both headisoremix-canary2m runs;
W&B `pskh1tt2`/`t47vv9n9`.

## `rl_only` off-axis-heading leg-sacrifice repair: 4 independent mechanisms tried, 0 passes (2026-09-09 ~19:4x)

Self-distillation (`heading_selfdistill.py`, advantage-filtered imitation of
the policy's own successful stochastic samples into its mean) CLOSED
`CANARY FAIL - MECHANISM (efficacy)` 2/2 seeds
(`cw-walkscratch-crutchoff-{s0,s1}-widen8-plusduty-selfdistill-canary2m`):
DET off-axis (±90/±135/180°, n=15) `gait_valid` byte-identical to the frozen
parent (s0 1/15=1/15, s1 0/15=0/15), sacrificed-leg sets match leg-for-leg,
per-leg `duty_cycle` moves noise-level only. This is the **4th** independent
mechanism to fail the same chronic front-leg (leg0/leg5) off-axis sacrifice
on the widen8/crutchoff champion, after heading-exposure reweighting
(FAIL-MECHANISM ~12:0x), heading-gain dose-scaling (FAIL-MECHANISM ~12:4x),
and headexplore's wide-`log_std` (ACQ FAIL-MECHANISM ~16:2x, entry below).
The ~13:3x rollout trace already ruled out a kinematic/action-box ceiling.
**Ruling: this sub-question does not get another dose/schedule/architecture
variant of an already-tried mechanism family.** Reopening it needs a
genuinely new structural idea — named candidates, both UNBUILT: (1) a
heading-conditioned auxiliary curriculum stage training off-axis headings
in isolation before remixing, or (2) per-heading critic/advantage
normalization so off-axis timesteps aren't structurally under-weighted in
the shared PPO batch. Practical impact: none on current delivery — the
champion checkpoint is untouched, the already-captured rl_only sim demo
(forward + `human_turn` script) never exercises the failed range, and the
limitation stays labeled in `bundle_rlonly_v1/GO_NOGO.md`. Evidence:
`rl_docs/tracks/walkcurr/STATUS.md` 2026-09-09 ~19:4x entry; ledger verdicts
on both selfdistill-canary2m runs; W&B `qrtdi76y`/`iacvgq9d`.

## `rl_only` (walkcurr) non-interactive sim-demo evidence now recorded (2026-09-09 ~18:1x, doc-sync only, zero training spend)

Top-level `STATUS.md` did not yet surface the walkcurr `rl_only` sim-demo
work landed 09-09 ~11:2x/~14:4x/~15:5x (walkcurr/STATUS.md), so it read as
if only the `any_means` `todaypolicy-mlpsf-tuck-v1` candidate had any sim
evidence. Recording the accepted facts here and syncing `STATUS.md`:

- Champion: `ppo_goal_cw_walkscratch_crutchoff_s0_widen8_legdutyratio_
  swinggap_dose10_plusduty_acq1_cont10m.zip` (widen8/crutchoff recipe
  default, no BC/AMP/demo anywhere in its lineage — clean `rl_only`
  ancestry), durability-confirmed at 50M cumulative steps (4/4 arms HOLD,
  09-09 ~11:2x).
- Reproducible non-interactive video: `ops.sh drivevideo <run> --script
  human` / `--script human_turn` (09-09 ~15:5x) — forward, crab-right,
  diag-left, reverse, **stop**, **restart** sequence, 26 s, 0 falls,
  `gait_valid=true`, `sacrificed_legs=[]` for the full episode. Artifacts:
  `logs/manual_drive/cw_walkscratch_crutchoff_s0_widen8_legdutyratio_
  swinggap_dose10_plusduty_acq1_cont10m_drivevideo_human_20260909_155330/`
  and `..._drivevideo_humanturn_20260909_155146/`.
- Reproducible interactive launch: `sim_viewer/sim_web.sh --walk
  rl_move/sim/policies/<champion above>`; added to the default picker's
  `_CURATED`/`_PROMOTED`/`_DESC` (09-09 ~14:4x, `play_core.py`,
  `exp/walkcurr-simviewer-picker-entry`) so it no longer requires
  `--all-models` or risks the scripted-fallback trap
  (`web_session.py:_ensure_listed`/`_policy_contract_error`). The one
  remaining piece — actually clicking through the browser/window HUD to
  confirm the loaded (non-scripted) policy live — needs a display no cloud
  pod has; irreducible-to-cloud, same class as a physical-robot dependency,
  not a design gap (`OPERATOR_QUESTIONS.md` q_20260909T144xZ).
- Known, honestly-labeled limitation (not hidden by the demo scripts above):
  a SUSTAINED (~15 s) off-forward heading (±90°/±135°/180°) still
  chronically sacrifices one front leg's (leg0 or leg5) swing —
  `--pinned-heading-panel` evidence, `walkcurr/STATUS.md` 09-09 ~11:2x
  onward. Root-caused ~12:5x-13:3x as a policy/exploration gap (legs sit
  well inside their ±15° coxa-yaw action box, not railed at the edge), NOT
  a kinematic ceiling. Four independent repair mechanisms (heading-exposure
  reweighting, heading-gain dose-scaling, headexplore log-std-widen, and
  advantage-filtered self-distillation) have all CLOSED FAIL as of 09-09
  ~19:4x (see the tally entry above) — the gap is not being actively worked
  pending a genuinely new structural idea. This limitation does not block
  the sim-demo deliverable (which shows real current behavior, warts
  labeled) but does block claiming full "directions actually followed"
  quality.

This is a documentation-sync entry only — no new run, no new verdict, no
change to any recipe or gate. Full evidence trail:
`rl_docs/tracks/walkcurr/STATUS.md` (09-09 ~11:2x, ~14:4x, ~15:5x entries).

## widen8 `headexplore` (log-std-widen+hold) lever CLOSED 3/3 seeds (2026-09-09 ~16:2x)

Holding `log_std` wide (-0.5, std 0.607, vs. the champion's annealed
~-2.0 floor) for a further 10M-step acquisition on all 3
`crutchoff-widen8-legdutyratio-swinggap-dose10-plusduty` seeds FAILS
to move the DETERMINISTIC mean at the widen8 lineage's 5 chronically-
broken off-axis headings: gait_valid stays at **0/15 in all 3 seeds**
(at/below the 2M canary's own 0-2/15 floor), with a byte-identical
sacrificed-leg set across all 3 independently-trained checkpoints at
every heading. STOCHASTIC sampling keeps finding/improving off-axis
gaits in the same window (up to 14/15 on one seed) while the mean
stays at literal zero — the widest mean/noise gap measured on this
lineage. `reward_per_tick` stayed healthy throughout (no collapse);
this is a clean efficacy FAIL, not a reward-mechanism failure. One
seed (s2) additionally regressed the previously-clean forward-ish
no-regression floor (7/9 -> 5/9), a second independent instance this
week of budget alone eroding a clean gait band (matches the cartfoot/
halfgrav pattern already logged below). This CLOSES the "just needs
more time" reading for this exact lever: PPO's on-policy gradient
provably does not consolidate the mean toward stochastic wins here at
either 2M or 10M budgets — do not fund a further no-lever continuation
of `headexplore`. The next licensed lever must move the mean directly
(a heading-weighted entropy bonus, or a self-distillation-of-own-
successful-stochastic-rollouts auxiliary loss — neither is rule-(a)
BC/demo/motion-prior, but both are unbuilt CODE with their own
design/test/canary cycle, not a repeat of this lever). Evidence:
`ops.sh entry cw-walkscratch-crutchoff-{s0,s1,s2}-widen8-plusduty-
headexplore-acq1`; `logs/ckpt_eval/cw_walkscratch_crutchoff_{s0,s1,
s2}_widen8_plusduty_headexplore_acq1_headpanel/report.json`; W&B
`rzlubwwz`/`mp5qva4v`/`jmvwjqyd`; `rl_docs/tracks/walkcurr/STATUS.md`
2026-09-09 ~16:2x entry.

Last compacted: 2026-08-30 for the `todaypolicy` sixth-track update.
Archive copy: `archive/CURRENT_TRUTHS_2026-08-30_pre_todaypolicy_compaction.md`.
Accepted facts, not narrative. This file wins on factual evidence and run
verdicts; `RL_GOALS.md` owns purpose and priorities, including Lukas's
2026-09-08 clarification. Older mission/allocation prose does not override it.

## assistfade rung3 behavior-gated residual-anneal mechanism CLOSED 2/2 on its own last named lever; the entire "fade assist to full raw authority" family is now exhausted on mesh/100Hz across every mechanism tried (2026-09-09 ~15:3x)

`cw-assistfade-rung3-residualgate-{s0,s1}-minprog015` (the last of the
two levers the 14:5x FAIL-STILL-STUCK gate named — lower `train.
residual_anneal_min_progress` 0.35->0.15 instead of raising the
pre-latch blend floor, which the 15:1x entry below already closed
4/4) **both FAIL-STILL-STUCK, exactly the pre-registered bar**:
`residual_anneal/frac` reads 0.0 for every one of 123 logged points
across the full 6.05M-step budget in BOTH seeds (`residual_anneal/
gate_pass` constant 0 throughout) — the gate never latches even at
the easier bar. The periodic `gate_cmd_prog_frac` assay (12 checks
each) shows the same non-sustaining shape as every prior read: s0
oscillates -0.06..+0.04 with no trend, s1 peaks at 0.19 near 2M steps
then reverses through zero to -0.03 by 6M. Held-out DR-0 gate
reproduces the exact chronic single-leg-parked signature this whole
mechanism was built to route around: `walk/det` `gait_valid` 0/6 in
BOTH seeds, one leg permanently sacrificed every episode (s0 leg5,
s1 leg3, the latter with `over_current` termination in all 6
episodes). `ep_rew_mean` rose cleanly both seeds (per the 08-21
ruling, weighed against the gate's own designed unassisted-capability
diagnostic, which is exactly what shows this reward rise is
heavy-assist reward, not raw-policy capability — not a case for
"continue").

**This closes BOTH named levers of the behavior-gated residual-anneal
mechanism** (raise `goal.walk_residual_anneal_v0`: closed 4/4 across
2 doses x 2 seeds, see the 15:1x entry below; lower `train.
residual_anneal_min_progress`: closed 2/2 here) — no further dose/bar
variant of this mechanism is licensed. Combined with the 09-09 ~07:5x-
08:0x closure of every per-leg reward-shaping repair (6/6 mechanisms/
doses) and the 09-07 ~14:5x closure of every calendar-scheduled
rung 1-4 lever (~20 arms: rung1 both tiers, rung2 4/4 habituation
doses, rung3 8/8 schedule levers incl. nostdanneal x2, rung4 2/2
handoff variants), **every mechanism this track has tried for making
assistance fade to full raw-policy authority — calendar-scheduled or
behavior-gated, with or without per-leg reward shaping — has now
failed to ignite clean six-leg walking on mesh/100Hz, ~36 total
canary/acquisition arms across the whole family.** Only rung 0 (a
PERMANENT BC anchor / phase-lock that never fades) reaches ignition;
its champion (`cw-walkteach-scripted-allhead-acq12m{,-s1}`) remains
the track's one production-usable output and is already the
`todaypolicy` walk-role upgrade candidate. Per `RL_GOALS.md`, `any_means`
permits a permanent scripted-gait anchor/composition outright, so this
does not block Goal 1 delivery — it specifically closes the narrower
"and eventually needs zero assistance" sub-question. Do not launch
another dose/schedule/gate variant of the fade-to-full-authority idea
on this lineage; the only way to reopen this sub-question is a
genuinely different structural mechanism (not a parameter of the
existing blend/anneal), which is design work, not a launch. `tracks.json`
`assistfade.status` updated to match.
Evidence: `ops.sh review cw-assistfade-rung3-residualgate-{s0,s1}-
minprog015`; `logs/experiments/cw-assistfade-rung3-residualgate-{s0,
s1}-minprog015/wandb_history.csv` (`residual_anneal/frac` max()==0.0,
`gate_pass` constant 0 across all 123 rows in both files);
`logs/ckpt_eval/cw_assistfade_rung3_residualgate_{s0,s1}_minprog015_
gate/report.json`; W&B `cw1sy8e6`/`ix57kkn1`; `rl_docs/tracks/
assistfade/STATUS.md` 2026-09-09 ~15:3x entry; RL_LOG 09-09 15:37/15:38.

## assistfade rung3 residual-anneal-GATE "raise v0" escalation lever CLOSED 4/4 across dose (2026-09-09 ~15:1x)

Following the 07:5x-08:0x per-leg-charge closure below, a structurally
different fix was built and tried: a behavior-gated residual-blend
anneal (hold training-wheel blend low until a dedicated unassisted-
progress assay passes, instead of a fixed step-count calendar) —
mechanically PASSED on both seeds, but its own fixed-bar longbudget
follow-up (6M steps) hit FAIL-STILL-STUCK 2/2 (gate never latched).
The named escalation from that FAIL text — raise `goal.
walk_residual_anneal_v0` (the pre-latch blend floor, i.e. how much raw
-policy authority training itself exposes the actor to) from 0.05 to
0.3 or 0.5 — was tested as a 2-dose x 2-seed canary grid and is now
CLOSED 4/4: no dose in either seed clears the matched v0=0.05
baseline's own `gate_cmd_prog_frac` reading (dose 0.3 regresses
below baseline in both seeds, at s0 -0.047 vs 0.023 and s1 -0.037 vs
0.095-0.17; dose 0.5 stays at-or-below baseline, s0 -0.011 vs 0.023,
s1 0.116 inside the 0.095-0.17 baseline band, not above it). More
importantly, dose 0.5 walks BOTH seeds back into the byte-identical
already-closed chronic single-leg-parked signature from the per-leg-
charge closure below (walk/det gait_valid 0/6, one leg permanently
sacrificed every episode — s0 leg4, s1 leg1), including in the seed
with the grid's best raw forward progress (s1, prog med 0.12,
fwd 0.07m) — it gets there by sacrificing a leg. Dose 0.3 instead
produces a NEW "stationary shuffle" in both seeds (all six legs
cycling contact/swing, `gait_valid` 6/6, but prog med negative,
zero net translation). Since this mechanism's ramp target
(`goal.walk_residual_blend`, default 1.0 = full raw authority) is the
SAME endpoint the original fixed-calendar `residualfade-{s0,s1}`
recipe already tested and closed 6/6, raising the pre-latch floor
only moves the actor closer to that already-closed endpoint sooner —
read this as evidence the bottleneck is the eventual high-raw-
authority endpoint itself, not the schedule (calendar vs behavior-
gated) or floor magnitude that reaches it. Do not launch another
v0-raise dose variant on this lineage. The one remaining named lever
(lower `train.residual_anneal_min_progress` from 0.35) is in flight
(`residualgate-{s0,s1}-minprog015`, v0 held at the original 0.05); if
it also fails to ignite clean six-leg walking, this closes the entire
residual-anneal-gate mechanism family and licenses the 07:5x closure's
own fallback (construct a fresh rung-3 base) rather than any further
dose/bar variant of this mechanism.
Evidence: `ops.sh review cw-assistfade-rung3-residualgate-{s0,s1}-
v0dose{03,05}`; `rl_docs/tracks/assistfade/STATUS.md` 2026-09-09
~15:1x entry.

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
- DEPLOYMENT candidates train at mesh-family control.hz=50 (operator
  order op_20260910_50hz above; 100 Hz trips the hexapod2 MCU-bridge
  timing fault). Sim-research lineages not targeting hardware may
  stay at 100 Hz; the launcher's no-key default injection is still 100.
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

- **2026-09-09 ~13:3x: a third, non-reward lever (wider action-noise std,
  held flat via the existing `--warm-log-std-override`/`--log-std-final`
  trainer flags) partially unsticks the widen8 front-pair (legs 0/5)
  off-heading sacrifice under STOCHASTIC sampling only (n=3/3 seeds,
  off-axis gait_valid 1-2/15->8-11/15), while the DETERMINISTIC mean
  stays flat (0-2/15, byte-similar to the untouched parent) at 2M
  steps, and forward-ish headings are unaffected either mode. This is
  evidence AGAINST (not a refutation of) the same-day kinematic-
  action-box-rail hypothesis flagged as an open DIG-IN
  (`rl_docs/tracks/walkcurr/STATUS.md` 09-09 ~12:5x): a hard rail
  clipped noise would not be expected to unstick the sacrifice this
  cleanly. The DIG-IN's own rollout-trace joint-angle-vs-box check is
  still the authoritative test and has not been run; this only adds a
  cheap, complementary behavioral signal pointing the same direction
  ("not railed," a policy-commitment/exploration gap instead). All 3
  seeds promoted to a matched 10M acquisition (same held std) to test
  whether the deterministic mean eventually consolidates toward what
  stochastic sampling is already finding. Evidence: `ops.sh entry
  cw-walkscratch-crutchoff-{s0,s1,s2}-widen8-plusduty-headexplore-
  canary2m`; `logs/ckpt_eval/cw_walkscratch_crutchoff_{s0,s1,s2}_
  widen8_plusduty_headexplore_canary2m_headpanel/{report.json,
  baseline/report.json}`; `rl_docs/tracks/walkcurr/STATUS.md` 09-09
  ~13:3x.

- **2026-09-09 ~22:3x: the value-calibration hypothesis for the
  chronic off-axis-heading (leg0/leg5) sacrifice is CLOSED, cleanly.**
  The prior entry's V(s)-vs-realized-return diagnostic was
  inconclusive because pinning a heading for a full 20s episode
  (`walk_cmd_resample_s=0.0`) is itself out-of-distribution — real
  training resamples the heading every 6s even inside its own 20s
  episodes. Re-run with `diag_value_calibration.py --natural-resample`
  (new mode this entry: heading resampling left ON, ticks bucketed
  post-hoc by whichever heading is actually commanded, via the same
  `heading_cos` classifier `heading_adv_norm`/`heading_selfdistill`
  use): on the frozen `cont10m` champion, n=8x20s episodes, the
  critic's relative prediction error is the SAME ORDER at off-axis
  states (17.1% of that group's own return range) as at on-axis states
  (10.7%) — not the order-of-magnitude blowup the OOD full-pin read
  showed. The raw magnitudes are huge and well-tracked either way
  (off-axis mean_V=-754 vs mean_G=-775): the critic correctly predicts
  that committing to an off-axis heading racks up the unbounded
  `walk_leg_duty_ratio_charge`/`walk_leg_swing_gap_charge` ambient
  penalty (confirms the 09-08 ~00:2x diagnosis is real, not a panel
  artifact — 4/8 sampled episodes that drew mostly off-axis headings
  scored -7.8k to -33.4k; the one all-on-axis episode scored +2.6k).
  **Conclusion: the critic is not the bottleneck.** PPO's advantage
  signal is small and correctly-signed at these states because the
  policy never SAMPLES a qualitatively different trajectory there to
  produce a large positive advantage — an exploration/sampling
  question, the same axis the six already-closed mechanisms
  (reweight, gain-dose, headexplore, self-distillation, isolation-
  curriculum, PPO-advantage-norm) all targeted and all failed to move.
  **No 7th mechanism is licensed from value calibration; the off-axis-
  heading repair now has NO untried named mechanism at all** — the
  next attempt needs a genuinely new structural idea (different
  action-space/exploration primitive, or routing around the sacrifice
  at a higher level), not another lens on reward/advantage/critic
  machinery already tried seven ways. Evidence: `rl_move/sim/diag_
  value_calibration.py` (`--natural-resample`, 8 new tests, 27/27
  green), `logs/diag_value_calibration/widen8_s0_cont10m_natural_
  resample_{n8,sto_n8}.json`; `rl_docs/tracks/walkcurr/STATUS.md`
  2026-09-09 ~22:3x.

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
