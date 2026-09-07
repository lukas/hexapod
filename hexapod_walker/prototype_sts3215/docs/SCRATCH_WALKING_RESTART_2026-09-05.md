# Teacher-free walking restart — 2026-09-05

Status: all four initial training launches mechanically verified by 08:32:41 UTC.
Cycle: `20260905T080114_operator-kick` (started 2026-09-05 08:01 UTC).
Owner: operator-directed orchestrator campaign. Training has started; walking success is not yet established.
Launch receipts: `SCRATCH_WALKING_LAUNCH_RECEIPTS_2026-09-05.json`.

**New operator instruction (same day): dedicate the available training hardware
to this campaign.** This supersedes the initial four-lineage/80M pilot-only
ceiling below. Full-fleet allocation was verified by 09:31:45 UTC in orchestrator
cycle `20260905T084400_operator-kick`: **11/11 ready slots running teacher-free
walking, each budgeted for 40M steps (440M allocated), plus three queued 40M
replacements.** Receipts: `SCRATCH_WALKING_FLEET_RECEIPTS_2026-09-05.json`.
Teacher-free easy walking is now the primary GPU campaign; CAPACITY.md, tracks.json,
RL_PLAN.md and the remote walkcurr notes supersede the earlier empty-queue policy.

The launch exposed a CPU-only Torch installation on train-1 and unbootstrapped
train-0/train-4. The orchestrator repaired the environments and changed the bootstrap
to CUDA Torch 2.11.0+cu128 (snapshot `896ea490`). The final two runs each advanced
past 1.5M steps in independent log reads, and all eleven have launcher receipts.

**Allocation is not saturation.** Five one-second samples on active train-9 showed
3–15% GPU SM utilization. Train-6 is blocked by CPU reservations, not an HPC diagnostic:
the two schedulable nodes reserve 98–99% of their 128 CPUs while using 9 of 16 GPUs;
two other nodes are cordoned. Existing node and per-run safeguards remain.
Follow-up `fb_20260905T092735_de1d6c` records the concrete CPU blocker and requests
throughput measurement before any idle-pod reslicing. The useful next comparison is
24 versus 10 host workers with identical checkpoint/task settings, comparing actual
step deltas per wall time and aggregate trainer/worker CPU usage. Reducing workers
alone does not release Kubernetes CPU reservations. The standalone physics benchmark
omits host reward/observation, IPC, resets and PPO, so it cannot answer this comparison.

## Operator objective and scope

Learn sustained forward walking from random policy initialization on flat ground.
The operator explicitly permits physics easier than the robot, no domain randomization,
and no simulated current constraints during initial acquisition. This reopens the
previously retired prior-free walking question with a different task/physics contract.
First establish visible locomotion; turning, robustness, transfer and hardware come later.

No BC, imitation anchor, AMP, pretrained walking model, CPG, gait clock, prescribed
tripod/contact schedule, or prerecorded walking-state resets may enter these runs.
A static standing reset and a symmetric joint-action box around it are allowed.
Full simulator state may be observed: privileged information is not a walking teacher.
No physical robot motion or change to real-robot protections is authorized by this work.

## What the previous campaign actually established

The local ledger contains no walking-gate PASS for the `walkcurr` track.
Its retired status and per-run outcomes are preserved in
`rl_docs/tracks/walkcurr/STATUS.md`, the two archived walkcurr journals, and
`rl_move/orchestrator/experiments.json`. Run names containing “scratch” are not sufficient
evidence of teacher-free learning; several successful all-heading policies used BC anchors.

| Historical run / family | Result relevant to this restart |
| --- | --- |
| `cw-walkcurr-litrep-box-s0`, `-s1` | 150M steps each; deterministic gait-valid 0/6, progress ratio 0.01–0.02, essentially static standing. |
| Centralized/decentralized PPO simple-velocity waves | 20M probes and later 100M population arms mostly remained in standing/quivering basins; changing architecture alone did not solve discovery. |
| `cw-walkcurr-sac-sv-s1` | Training speed reached 0.05–0.08 m/s and all-six-leg stepping appeared, but all 24 held-out episodes fell. Later budget/tilt variants did not establish stable walking. |
| `cw-gait-ease1` | Half-gravity curriculum failed while retaining DR 0.5, changing directions and a large drag charge; this was not a clean simple-physics test. |
| `cw-walkteach-scripted-allhead-acq12m` | Teacher-based success: zero falls/24, slip/m 1.642, direction error 22.54°, course error 5.17°; completion remained near the teacher ceiling. |

The final litrep pair already used `--dr-scale 0`, stance-centered action boxes
(yaw ±11°, hip ±20°, knee ±23°), zero current reward, and
`safety.over_current_trip_s=999999`. Simply removing current termination or DR repeats
tested work. Those runs retained loaded servo dynamics, torque saturation and a restrictive
command profile. Historical over-current claims also predate the later finding that the
simulated current estimate is uncalibrated; do not treat rail hits as proven hardware stalls.

## Plausible obstacles, not established sole causes

1. **Reward scale and reset income.** The final litrep commands set
   `k_walk_freeprog=0.06`. During the hardcoded initial 1 s zero-command hold, the
   legacy velocity Gaussian could still pay up to 2/tick; a further 1 s command ramp
   followed. The bank explicitly recorded park ≈202 versus walking ≈220.
   This strong early stand incentive warrants a cleaner objective. Attribution in an old
   verdict to generic hold/unload/rise income was imprecise: the stop-command Gaussian
   is directly verified in `walk_task.py` and the bank's own explanation.
2. **Exploration versus action-change cost.** The exact final litrep commands explicitly
   set `reward.k_action_delta=0.01`; the base `WALKCURR_SV` bank used 0, while the
   final `WALKCURR_SV_LITREP` variant added 0.01. At initial independent action noise,
   movement cost could be comparable to the small maximum walking income.
3. **Credit assignment in physical time.** These 100 Hz runs inherited γ=0.99 and
   GAE λ=0.95: about 1 s discount horizon and 0.17 s trace scale, against a 0.75 s
   velocity EMA. No audited walkcurr command supplied `--gamma`. Longer physical-time
   credit and a more immediate velocity signal are meaningful new tests.
4. **Hardware difficulty remained.** The fitted loaded servo has substantial latency,
   deadband, limited slew and compliance. High-frequency random action changes may
   produce little useful foot motion. Audit actual joint excursions before blaming PPO.

Code evidence: `rl_move/sim/walk_task.py` (`_sample_walk`, `_post_step`),
`rl_move/sim/train_ppo_mjx.py` (gamma/GAE defaults), and
`rl_move/tests/test_task_semantics.py` (`WALKCURR_SV` and `WALKCURR_SV_LITREP`).

## Literature informing the design

- [MuJoCo Playground, 2025](https://arxiv.org/html/2502.08844v1) provides modern
  PPO/MJX locomotion precedent with restricted initial tasks and substantial budgets.
  Its [official Go1 task](https://github.com/google-deepmind/mujoco_playground/blob/main/mujoco_playground/_src/locomotion/go1/joystick.py)
  uses nominal-pose joint targets. Reward bandwidths must be scaled to our slower robot:
  copying `exp(-error²/0.25)` gives standing 0.961 at a 0.1 m/s command.
- [Versatile Locomotion Skills for Hexapod Robots, 2024](https://arxiv.org/html/2412.10628v1)
  is directly relevant: an 18-joint hexapod, joint-angle actions, clipped forward velocity,
  and no human-defined gait prior. Its privileged “teacher” learns from scratch; later
  student distillation is distinct from borrowing a pre-existing walking controller.
- [Learning to Walk in Minutes, CoRL 2021/2022](https://proceedings.mlr.press/v164/rudin22a.html)
  supports simple nominal-pose actions and massively parallel teacher-free PPO.
  Published large budgets make short negative canaries poor evidence of impossibility.
- [Learning Symmetric and Low-energy Locomotion, 2018](https://arxiv.org/abs/1801.08093)
  demonstrates simulated hexapod locomotion without motion examples, using physical
  assistance gradually removed. This supports easier acquisition physics as an experiment.
- [Smooth Exploration for Robotic Reinforcement Learning](https://arxiv.org/abs/2005.05719)
  motivates a gSDE comparison when independent action noise creates ineffective jitter.
- [Towards bridging the gap, 2025; IJRR 2026](https://arxiv.org/html/2509.06342v1)
  supports investigating simpler locomotion rewards. It still uses environmental
  randomization, so it does not establish unrandomized hardware transfer.

These sources motivate adaptations; none proves this exact configuration will work.
CPG-derived trajectories and AMP motion priors are excluded from this teacher-free claim.

## Initial pilot cohort (launched; original budget superseded)

| Run | Difference from shared easy baseline | Current launch status |
| --- | --- | --- |
| `cw-walkscratch-easy0905-base-s0` | Ordinary PPO, seed 0 | Verified on train-7; [W&B](https://wandb.ai/l2k2/hexapod-balance/runs/706y3op2) |
| `cw-walkscratch-easy0905-base-s1` | Identical PPO, seed 1 | Verified on train-8; [W&B](https://wandb.ai/l2k2/hexapod-balance/runs/3ysuqplh) |
| `cw-walkscratch-easy0905-sde-s0` | Temporally correlated gSDE, seed 0 | Verified on train-9; [W&B](https://wandb.ai/l2k2/hexapod-balance/runs/fqwncrsp) |
| `cw-walkscratch-easy0905-halfgrav-s0` | Fixed half gravity, seed 0 | Verified on train-10; [W&B](https://wandb.ai/l2k2/hexapod-balance/runs/0vll8nk4) |

The initial plan was a 2M mechanism canary plus 18M acquisition per healthy
lineage, totaling 80M. The later full-fleet operator order above supersedes that
pilot-only restriction. A healthy canary need not walk.
At verification, both ordinary PPO seeds and half gravity had advanced through
2,097,152 steps; gSDE advanced from 524,288 to 1,048,576 during its verification
window. These are training/launch-health observations, not behavioral PASS verdicts.

Shared design: flat simple geometry, deterministic physics, no sensor noise, relaxed
simulation-only servo limits, no latency/deadband/compliance, bounded position actions,
fixed forward command, stronger immediate forward-velocity income and modest regularizers.
Use longer physical-time credit assignment. Add optional initial hold/ramp configuration
without changing existing defaults, and audit the complete reward rather than its label.
Exact resolved configuration, code revision and launch receipts must be recorded remotely.

Independent CPU probe (08:12 UTC, preliminary 3.49 kg candidate): mesh-MJX geometry,
100 Hz, command ceiling 360°/s, torque multiplier 3, zero latency/deadband/sensor
noise, structural compliance absent, gravity −9.80665 m/s². Correct action center
is robot-absolute [0,20,100]° per leg (knee bias35), equivalent to old relative
[0,20,80]°. Zero actions remained upright for 2 s; mean reward −0.0182/tick,
height drift +12.6 mm, no termination. This verifies the basic mechanism only.
This coordinate correction applies to the present restart after the September
frame change; it is not evidence that the August training failures had that mismatch.

Final preflight: 13/13 tests pass against the committed **4.8057 kg** mesh-MJX
model. The earlier regenerated 3.49 kg asset was preserved separately and excluded
from this experiment snapshot. Code/docs revision: `8c418c1b` (includes code/test
changes captured in concurrent snapshot `e6486106`). Under the final model,
zero-action reward is approximately +0.001/tick and height drift +19 mm in 2 s.
An independent deliberately tipped-state probe at the actual 30° training
threshold terminates at tick 8 with `tilt_roll` and −24 termination reward.
The test bank's static-fold fall check uses a narrower 20° diagnostic threshold;
the independent probe confirms the 30° production path too.
The gSDE arm must report realized action variance/clipping before interpreting its
comparison: equal log-standard-deviation settings do not give equal noise amplitudes
across Gaussian PPO and gSDE. Independent review is saved in orchestrator feedback
`fb_20260905T080341_ef45b6`, including the continuation-argument checks.

## Verification and decisions

- Before launch: prove static action-zero mapping, stable standing, meaningful random-action
  joint/foot excursions, deterministic sampled physics, and reward ranking on complete
  stationary/moving/reverse/falling trajectories including the initial command window.
- Assert absent teacher/checkpoint initialization, BC/AMP losses, gait clocks, motion
  libraries and prerecorded gait resets. Keep training and evaluation physics identical.
- Canary health: finite optimization, actual non-noise weight updates, live reward terms,
  growing rollouts and useful exploration. A crash or frozen optimizer requires repair.
- Acquisition milestone: at least 0.03 m/s median net forward speed in 20 s episodes,
  zero falls in 12 held-out deterministic episodes, and all six legs lifting/placing.
  This is an initial easy-simulation gate, separate from the old full-contextual track goal.
  Report stochastic behavior too. Measure forward displacement/speed, direction, upright duration, body-ground
  contacts and six-leg contact cycles; inspect video for dragging, skating or sacrificed legs.
  Report assisted and nominal-gravity outcomes separately; half-gravity success alone is
  not success under nominal physics. Refine slip/style only after locomotion emerges.
- Reward rising while behavior remains wrong triggers an objective/simulator audit.
  Both improving can justify a separately registered continuation; flat results change the
  mechanism. Launch status and outcomes must be updated only from verified remote evidence.
