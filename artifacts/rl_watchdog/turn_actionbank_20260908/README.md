# Assisted-steering action-authority bank — frozen yawref-cigate8m, full-mesh plant

Completed 2026-09-08 ~06:4x UTC (operator focus note 20260908T061629Z,
feedback context `fb_20260908T060614_63099e`). Diagnostic only: no
training, no robot, no shared-code change. Preregistration
(`prereg_spec.json`, sha256 `847db884d21b74b6452704d86ae13f30f7e59892e
e3245df81d7475813cebdba`) was written and hashed BEFORE any data.

## Protocol (as preregistered)

- Frozen checkpoint `ppo_goal_cw_robotwalk_turns_20260907_yawref_cigate8m.zip`
  (sha256 `61f9c20f0f72d892…eb10`), frozen full-mesh XML
  (sha256 `7efb8e8a0cb014c0…6a837`, 34 meshes / 159 geoms / 4.80573 kg,
  verified live by `model_identity` in every rollout). Original motor
  contract: 100 Hz, write_speed 400, write_acc 20, slew 0.375 deg/tick
  (`env.safety.max_dq = 0.0065450 rad`), profile 350 counts/s
  (`speed_counts_s=350` verified). The stale 3.49 kg XML was NOT
  regenerated or used. Isolated workspace `/workspace/hexapod-turnphase-wt`
  @ `f7d00ba5`; runner `probe_action_response_bank.py` (copied here,
  sha256 `ed15d1c6…82a15a`); frozen training cfg replayed in full
  (`cfg_set.json`, 64 keys).
- Cells: (vx=0.08, wz=±0.15), starts 0/π, seed 0, DR-0. 1 s hold + 1 s ramp.
  Two settled states per cell: P1=600 ticks (t=6.0 s) and P2=638 ticks
  (phase separation 3.183 rad ≈ π; half cycle at 1.333 Hz is 37.5 ticks).
- 296 branches = 8 states × (1 zero control + 18 joints × ±0.05
  normalized-action pulse). Pulse: 5 ticks on one action dim (clipped to
  action space — clip never engaged, 0/288), then the unchanged policy
  for 0.75 s. Scoring window 80 ticks from pulse start. Every branch is a
  fresh identical construction + reset + deterministic prefix replay
  (controller history/hidden state preserved by replay; no state
  teleporting, no nominal FK, no population reweighting).
- Exactness gate: **PASS** — all 8 zero branches match the continuous
  baseline bit-exactly (final-qpos float equality at P+80 AND identical
  window trace hash over yaw/xy/pad-xy/contacts).

## Results

Baselines (real integrated yaw over the 0.8 s window vs commanded
0.12 rad): +0.0278/+0.0332/+0.0288/+0.0295 (wz=+0.15) and
−0.0318/−0.0261/−0.0261/−0.0320 (wz=−0.15); forward displacement
0.023–0.025 m vs commanded 0.064 m — the known arc undertracking, now
measured at the branch points themselves.

Pulse branches (`ranking.json`, preregistered criteria, no post-hoc knobs):

- **Effect threshold (≥ +0.005 rad commanded-direction yaw gain): 0 / 288.**
  Max +0.0041; distribution mean +0.00034, sd 0.00104, p5 −0.0009,
  p95 +0.0027.
- Retention (forward ≥ 0.9×, slip ≤ 1.25×, no term, tilt ≤ base+3°, all
  walk ticks): 288 / 288 — pulses are benign but impotent.
- Repeatability: **zero** (joint, sign) pairs have even a consistent
  yaw-gain SIGN across the 8 settled states, let alone threshold-passing
  gains in a matched-phase pair. Top single gains scatter across
  unrelated joints (9, 7, 17, 13, 11…) — chatter, not authority.
- Both-signs qualification: **FALSE**.

## Preregistered decision

The causal preflight does NOT support an assisted-steering residual of
this class. Per the preregistered plan and the focus note: no
state-dependent-residual panel validation, **no 2M assisted canary
launched**, and no new training arm. Recorded as UNSUPPORTED SCOPE.

## Scope — what this does and does not close

CLOSED (this bank only): single-joint, ±0.05 normalized, 5-tick
open-loop action pulses at settled tripod states as a steering lever for
this frozen policy/plant at (0.08, ±0.15), seed 0, DR-0. Through the
real actuation chain (slew 0.375°/tick bounds the realized excursion of
a 5-tick target pulse to ≤ ~1.9°) such pulses produce < 0.29° of
repeatable heading authority per 0.8 s — an order of magnitude below the
~4.6°/0.8 s tracking shortfall.

NOT closed: multi-joint coordinated residuals, larger/longer or
phase-synchronized doses, closed-loop learned residuals, gait-level
mechanisms, other checkpoints/plants. No claim is made that one-cycle
impulse response predicts (or bounds) sustained closed-loop control —
only that THIS pulse class shows no exploitable, repeatable signed-yaw
handle at the preregistered threshold. Physical limits and the
continuous-joystick qualification criteria are unchanged. The
FAIL-QUALIFICATION status of continuous yaw for this lineage is
unchanged.

Raw duplicates (bank + ranking + smoke) also retained on the controller at
`/workspace/hexapod-turnphase-wt/hexapod_walker/prototype_sts3215/logs/ckpt_eval/turn_actionbank_20260908/`.
