# Maximum sustainable speed — research design

Registered by Lukas on 2026-09-10. This is an `any_means` method serving the
physical walking goal now; it does not replace or contaminate `walkcurr`'s
demonstration-free lineage.

## Question

What is the fastest forward body speed Hexapod 2 can sustain with a real
six-leg lift/place gait, bounded slip and body motion, and a transfer contract
that is safe to test physically? After establishing that frontier, can one
policy cover the useful speed range without losing the fast endpoint?

Speed always means measured forward displacement divided by elapsed time.
Command magnitude, foot speed, cadence, joint travel and training return are
diagnostics, never the answer.

## Evidence carried in

- The current all-heading policy requests 0.08 m/s but realizes roughly
  0.03-0.04 m/s in both full-mesh simulation and hardware. The policy, not the
  now-stable 100 Hz transport, sets that softness.
- `cw-walk50hz-allheading-mlp-singleframe-scratch-acq20m` is the current
  mesh/50 Hz baseline: det progress ratio 0.41, slip 2.19, gait-valid 6/6;
  stochastic progress 0.32, slip 3.13, gait-valid 6/6; no falls.
- `cw-walk50hz-teach-scripted-allhead-scratch-acq10m-cont15m` is a second
  mesh/50 Hz baseline and looked smoother/faster in its physical 100 Hz-family
  predecessor. It may be used because this track is `any_means`.
- `cw-dep-bcgait2-fastbc1` reached 0.117 m/s with clean six-leg stepping in
  simulation, but used the old primitive model and an aggressive
  1500/80/5-degree actuator profile. Its later command-tracking children
  oversped, fell or became command-invariant. It is mechanism evidence only.
- Shortening cadence alone was already refuted in the scripted-teacher and CPG
  searches. Do not rerun a bare period/frequency sweep. A faster cadence is
  admissible only when stride geometry, lift and workspace are retuned with it.
- The clean RL-only speed-band widening to 0.03-0.12 m/s passed three seeds,
  but that track still has high slip/off-axis limitations. It remains under
  `walkcurr`; no assisted weights or targets cross into it.

## Staged program

### 0. Specification and frozen baselines

On the exact mesh/50 Hz configuration, evaluate the two current 50 Hz walkers
at pinned 0.06/0.08/0.10/0.12 m/s commands. Record absolute achieved speed,
progress ratio, slip/m, direction error, gait validity, sacrificed legs,
roll/pitch motion, terminations and video. Reuse or extend an existing harness;
do not hand-score reward or create rollout-ranking tests.

Before PPO, sweep the scripted teacher/controller over stride length, lift and
phase frequency under the conservative 50 Hz transfer slew of 0.75 deg/tick.
This is a CPU/simulator preflight, not an RL result. Reject teacher settings
that fall, bind joint workspace, drag a leg or gain foot speed without body
speed. This prevents spending a GPU on an impossible target.

### 1. Discovery

Launch one bounded batch, up to the ordinary four-arm cycle cap, from the best
preflight-supported mechanism. Prefer clean causal arms such as longer stride
at the existing phase rate and a jointly retuned stride/lift/cadence candidate;
include a frozen-parent control when the evaluator or physics condition
changes. A persistent teacher/BC anchor is allowed. Discovery is at most 2M
steps and answers only whether faster correct motion emerges.

Initial behavioral milestone: median achieved forward speed at least 20%
above the matched current baseline, with zero falls, no chronic sacrificed
leg, and no worsening of slip or body motion large enough to erase the speed
gain. An arm that merely ignores the command, skates, overspeeds blindly or
moves its feet faster is MISALIGNED, even when return rises.

### 2. Acquisition and frontier

Fund 10-40M only after visible discovery. The first named simulation target is
0.08 m/s sustained achieved speed. Do not stop permanently there: record every
passing candidate on a Pareto frontier and advance pinned commands toward
0.10, 0.12 and 0.15 m/s while the quality gates hold. Once a fast endpoint is
real, train the 0.03-to-frontier speed range and verify monotone achieved speed.

A promotable checkpoint needs held-out deterministic and stochastic panels,
at least 12 total 20-second episodes, zero falls, all six legs participating
in at least 10/12, no persistent wrong-way motion, and video that shows real
lift/place rather than paddle-creep. Report slip and roll/pitch quantitatively;
the frontier may retain a faster and a smoother candidate rather than hiding
the tradeoff in one score.

### 3. Transfer

Export at 50 Hz with exact model, observation, checkpoint and actuator
provenance. Cloud cycles never move the robot. Robot Lab verifies the deployed
source and firmware, repairs the presently unreliable walking-current metric,
obtains a usable camera view, and registers command range, duration and stop
criteria before motion. Begin with three observed <=30-second forward trials,
then starts/stops and speed changes. Physical promotion requires measured
speed, synchronized video, six-leg participation, zero falls/trips, and honest
thermal/current evidence.

The physical actuator envelope may be widened only from measured step-response
and loaded-walk evidence. A fast simulation profile is not permission to copy
its settings to the robot.

## Actuator-envelope research path (operator order, 2026-09-11 — sim only)

The stride-geometry program above saturated: period/stride/lift/stance-radius
all plateau at ~0.052 m/s because the 0.75 deg/tick slew contract clips the
teacher every tick (slew_sat_frac = 1.00). On operator order the track now
varies the realizable actuator/slew contract itself, in simulation, as a
causally matched dose ladder off the strongest corrected-mass (3.490 kg) PASS
checkpoint, changing ONLY `safety.max_delta_q_deg`, `bus.write_speed` and the
`bus.servo_vel_max_counts_s=write_speed` ceiling per rung; `bus.write_acc=20`
is held in the first rungs so acceleration is unconfounded. Every rung ramps
the live profile in from the parent contract (400/20/0.75) with bounded
`bus.profile_ramp_steps` leaving majority full-target exposure, is judged at
the full target contract on the pinned-speed panel (real gain outside the
parent's noise floor — never reward), carries falls/gait/slip/current/tilt
and slew-saturation gates plus a retention eval at the parent contract, and
never uses the retired 1500/80 / 2000/80 profiles. First rungs (09-11):
50 deg/s (`cw-speed50hz-env50dps-ps200-sr105-disc2m`) and 65 deg/s
(`cw-speed50hz-env65dps-ps200-sr105-disc2m`); open-loop teacher feasibility
0.0608 / 0.0706 m/s @0.10 cmd (`speed_teacher_sweep_20260911_envelope/`).
Exported envelope checkpoints must carry `bus_write_speed`, `bus_write_acc`
and `safety_max_delta_q_deg` in policy meta (exporter + `rl_policy.py`
already support all three). The transfer rule below is unchanged: the
PHYSICAL envelope is widened only from measured hardware evidence.

## Stop/change rules

- Reward up while achieved speed or video is flat/down: audit alignment; no
  same-recipe continuation or seed grid.
- Two aligned, adequately budgeted misses in one mechanism class: change the
  mechanism or task specification.
- Do not repeat bare cadence shortening, blind speed-command increases, the old
  command-tracking charge continuation, or cross-family warm starts.
- A faster policy that falls, sacrifices a leg, or exceeds the verified
  physical contract is evidence, not a deliverable.
