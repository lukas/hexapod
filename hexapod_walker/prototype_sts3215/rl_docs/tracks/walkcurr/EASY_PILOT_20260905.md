# walkcurr EASY-SIM PILOT — operator-authorized bounded reopening (2026-09-05)

Operator focus note 2026-09-05 (Lukas): "see if you can kick off some
experiments to learn to walk... It could be easier than real physics, it
doesn't need domain randomization to begin with or limits on amps etc."
This note is the durable evidence/citation record for the cohort
`cw-walkscratch-easy0905-{base-s0,base-s1,sde-s0,halfgrav-s0}`.

## What is actually NEW vs the retired litrep wave (Codex audit confirmed)

The final litrep-box arms already ran no-DR with over-current clamped.
What they RETAINED and this pilot removes/changes:

| lever | litrep-box (retired) | easy pilot |
|---|---|---|
| servo latency | loaded fit ~85-106 ms | 0 (dr.latency_scale=0,0) |
| deadband | loaded fit | 0 |
| velocity ceiling | ~35 deg/s cruise / 37.5 slew | 360 deg/s (bus.write_speed=4096 + vel override), slew 3.6 deg/tick |
| torque | 2.2 N*m rail | 6.6 N*m (dr.torque_scale=3,3) |
| sensor noise floors | full (dr-scale 0 keeps them) | 0 (explicit dr.* overrides) |
| opening command | hardcoded 1 s stop + 1 s ramp -> ~+200 K_WALK windfall for standing | goal.walk_cmd_hold_s=0 / walk_cmd_ramp_s=0 (NEW keys, default-preserving) |
| income scale | k_freeprog=0.06 (~0.06/tick cap) vs 2/tick stop windfall | k_freeprog=2.0, cap=0.06 m/s, EMA tau 0.1 s (near-raw) |
| tilt trip | 15 deg default | 30 deg (roll+pitch), safety_termination_penalty=24 |
| action smoothing | k_action_delta=0.01 | same (only regularizer) |
| horizon | gamma .99 / lam .95 / n_steps 96 | gamma .995 / lam .97 / n_steps 128 |
| net | 128,64,32 tanh | 256,256,128 ELU |
| box center | knee bias 15 -> knee_abs 80 (~20 deg OFF the real plant since the 09-02 robot_abs unification) | knee bias 35 -> knee_abs 100 = true settled plant (probe-verified) |

No teacher/BC/AMP/CPG/gait-clock/phase/motion-prior anywhere (rule (a)
holds); scripted tripod used ONLY as offline bank comparator.

## Literature basis (operator-supplied)
1. Qu et al. 2024, hexapod RL stage-1: privileged sim info + clipped
   forward velocity, gait learned before distillation
   (arxiv.org/html/2412.10628v1).
2. MuJoCo Playground 2025 Go1 joystick: nominal-pose action targets,
   plain PPO, restricted commands first (arxiv.org/html/2502.08844v1).
   NOTE their Gaussian tracking bandwidth is useless at our 0.06 m/s
   (exp(-0.1^2/0.25)=0.96 for standing) — freeprog linear income used
   instead.
3. Yu et al. 2018 (arxiv 1801.08093): assistive/easier physics as a
   removable crutch — our halfgrav arm is the diagnostic analog.

## Pre-launch proof (rl_move/tests/test_walkscratch_easy_pilot.py, 13/13 PASS)

Run against the EXACT resolved recipe on the COMMITTED as-built mesh
twin (mesh_mjx, 4.8057 kg — operator commit a55173ab 09-03; the old
3.49 kg twin numbers in older docs are superseded):

- new hold/ramp keys bit-exact at default; command on from tick 0 at 0.
- windfall probe: legacy hold/ramp park earns >+50 in 2 s under the
  same diet; pilot recipe park earns ~0 (+0.001/tick). REMOVED.
- mechanisms resolved: latency/deadband/noise 0, torque 3x, 360 deg/s
  ceiling + slew (measured ~395 deg/s peak joint speed, no hidden
  35 deg/s limiter), struct comp off, degenerate DR = identical
  episode dynamics, halfgrav arm scales ONLY gravity (-4.903).
- action box center (0/20/100 robot_abs) within 12.4 deg of the true
  settled stance (hip sag under 4.81 kg); zero-action reset stable
  200 ticks (no term, +19 mm, income-neutral).
- bank ranking (10 s, mesh twin, exact diet): gait(0.059 m/s) +1876 >
  creep(0.029) +944 > crawl > park +0.2 ~ stall -0.3 > belly_sit -43
  (real backward-drift charge) >> reverse -1914; overspeed rolls off
  (cap=command) but stays >> park; no stationary pose out-earns park.
- termination: NO static fold exceeds ~26.5 deg on the 4.81 kg twin
  (chassis catches ground) -> at the 30 deg pilot envelope only
  DYNAMIC falls terminate; trip+penalty pathway proven at a
  test-scoped 20 deg envelope (topple terminates, priced 24 below
  park). This is an exploration choice, deliberate.

## Cohort + budget (bounded; no expansion into an unbounded sweep)

4 arms x 2M canary now; healthy canaries get +18M acquisition FROM
THEIR OWN CHECKPOINT ONLY (pre-registered continuation, normal
next-cycle budget; initial total 80M across 4 lineages). Arms differ in
ONE lever each: base-s0/base-s1 (seeds), sde-s0 (--use-sde,
resample 0.2 s = 20 ticks), halfgrav-s0 (ease.gravity_scale=0.5,
evaluated at its own gravity + diagnostic full-gravity later).

Canary gate (2M): finite losses, weights changing, real joint/foot
excursion beyond the settle pose, no hidden limiter in telemetry,
reward/tick in [park~0, moving>0] agreeing with the bank. NO WALKING AT
2M IS NOT A FAILURE. Stop/rework only for nonfinite training,
ineffective action delivery, implementation failure, proven exploit.

Acquisition milestone (NOT the old contextual DONE): held-out 20 s
fixed-forward episodes at OWN easy physics, >=0.03 m/s median net
forward speed, 0 falls in 12 det episodes, all six legs repeatedly
lift/place, no belly-drag/sacrificed leg on video; report sto too.
Diagnostics: distance, survival, foot contacts, slip. No amps gate.
The retired hard contextual goal remains separate and unclaimed.

## Explicit non-goals / boundaries
- No physical robot, no controller/CAD changes, no existing-default
  changes (all new cfg keys default-preserving; suite green).
- Not hardware-relevant physics: NOTHING from this cohort transfers a
  performance claim to the real robot or to nominal sim.
- Past negative evidence (15+ mechanism classes -> static-stand basin
  under REAL-physics prior-free PPO) stands unmodified.
