# Fixed-duty walk/turn mixture: matched evidence review

Review date: 2026-09-08. Read-only calculations; no new simulations, training,
qualification changes, physical actions, or production code changes.

## Inputs and provenance

- `artifacts/rl_watchdog/turnauth_corrected_20260907/scripted.json`
  (source SHA256: **e47ff48ab07ba839246cd0627eb90df5d4ae57b5f4a817087d7344bf877eb4de**).
- Its reproducible measurement definitions are in
  `artifacts/rl_watchdog/turnauth_corrected_20260907/run_frozen_probe.py`,
  lines 109–128; config and frozen asset provenance are in neighboring
  `spec.json` and `README.md`.
- Matching six arc/straight rows are independently preserved in
  `artifacts/rl_watchdog/root_fullcone_20260908/scripted_audit_fm.json`.
- Proposed new mechanism: `hexapod_walker/prototype_sts3215/rl_docs/tracks/todaypolicy/STATUS.md`
  at commit 1e8a6df68, lines 35–42 (time multiplexing, proposed 60 s averaged-course A/B).
- Existing implementation and closure:
  `hexapod_walker/prototype_sts3215/rl_move/sim/command_envelope.py`, lines 34–59,
  126–134 and 189–228;
  `hexapod_walker/prototype_sts3215/rl_docs/tracks/todaypolicy/hardware_delivery/STATUS.md`,
  lines 29–70.

The numerical inputs are the corrected frozen full-STL plant: 34 meshes,
4.80573 kg, seed 0, phases 0/pi, 100 Hz, 15 s episodes with the post-2 s scored window.
Input metadata code SHA is dbedfdfe9f6a8efc33e46de41714d077fd97eb76.
The contaminated 3.494226 kg turnpipeline experiment is NOT used.

## Reproducible calculation

Use integrated quantities rather than mixing temporal medians:

- `V(r) = r.scored_window_gait.body_forward_integral_m / (n_ticks * 0.01)`.
- `W(r) = r.independent_body_yaw.yaw_change_per_s`, the unwrapped chassis Euler
  yaw change divided by `(n_ticks-1)*0.01`, as defined by the source runner.
  This preserves its endpoint convention; V and W differ by one sample in
  their denominator, rather than silently redefining either historical metric.

For each same-phase row, let A be the combined command (0.08,±0.15), L the
straight command (0.08,0), and T the measured pure-turn command (0,±0.30).
A transition-free mixture spending fraction d turning gives
`V_mix=(1-d)*V_L+d*V_T`, `W_mix=(1-d)*W_L+d*W_T`.

At equal achieved forward progress,
`d_v=(V_L-V_A)/(V_L-V_T)`, then evaluate `W_mix(d_v)`.
At equal achieved yaw,
`d_w=(W_A-W_L)/(W_T-W_L)`, then evaluate `V_mix(d_w)`.
The table includes actual pure-turn drift in V and straight drift in W.

| Start | Arc wz request | V_L | W_L | V_T | W_T | V_A | W_A | d_v | W_mix at equal V | yaw ratio | V_mix at equal W | forward loss |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | +0.15 | 0.03515000 | -0.00128531 | -0.00002395 | +0.15849817 | 0.03259290 | +0.03879146 | 0.07269863 | +0.01033073 | 0.2663 | 0.02632770 | 19.22% |
| 0 | -0.15 | 0.03515000 | -0.00128531 | -0.00001758 | -0.15821037 | 0.03258866 | -0.03942702 | 0.07283254 | -0.01271456 | 0.3225 | 0.02660228 | 18.37% |
| pi | +0.15 | 0.03546823 | +0.00002186 | +0.00020354 | +0.15846029 | 0.03237061 | +0.03959590 | 0.08783901 | +0.01393894 | 0.3520 | 0.02665997 | 17.64% |
| pi | -0.15 | 0.03546823 | +0.00002186 | -0.00017159 | -0.15801875 | 0.03239315 | -0.03785990 | 0.08628217 | -0.01361423 | 0.3596 | 0.02692549 | 16.88% |

Speeds are m/s; yaw rates rad/s. Same-progress turn duty is only 7.27–8.78%.
Predicted mixed yaw is 0.01033–0.01394 rad/s in magnitude, 26.6–36.0% of the
existing combined yaw. Matching the existing yaw instead loses 16.9–19.2%
of forward progress. Both starts and both turn signs have the same ordering.

This is a quasi-steady mixing estimate, NOT a theorem about nonlinear
transitions or every controller. The available matched pure-turn rows request
±0.30, not ±0.15. They are a deliberately stronger measured endpoint used to
stress-test the proposal's premise; they do not establish a monotonic bound
on unmeasured ±0.15 pure turns or authorize changing the original request.
No transition-free estimate establishes instantaneous continuous-arc fidelity.

## Prior closure and decision

The existing `time_slice` mode already alternates full-amplitude pure-turn/
pure-translation demands, with unchanged joint limits. A 1.6 s period and turn
duties 0.3/0.5/0.7 were tested on the earlier ±0.25 combo suite. Baseline progress/
yaw ratios were 0.372/0.240; slicing produced 0.317/0.135, 0.227/0.255 and
0.128/0.372, with slip per achieved meter 1.50/1.76/2.15 versus 1.24 baseline.
No slice beat the existing continuous alternatives on their measured frontier.
The short 0.48 s d30 burst did not complete the governor's 0.5 s ramp.
That older model/config context and three doses do NOT prove universal
impossibility or global concavity. They do establish that a generic fixed-duty
recipe is already explored and that switching loss is real.

**Do not launch the saved generic time-multiplexing bank or a canary on this
premise.** The higher pure-turn gain omits the lost translation duty, and the
matched estimates remain unfavorable even before transition costs. Keep original
continuous joystick requests and original qualification gates: a newly proposed
60 s averaged-course criterion cannot replace them.

## Next steering mechanism

No distinct steering intervention currently has enough measured support to
nominate directly for a CPU efficacy preflight. In particular, do not relabel
fixed cadence, lift phase lead, stance radius/arm, omega shaping, continuous
uniform demand scaling, or fixed-duty time slicing as a new mechanism.

One genuinely distinct *hypothesis to screen*, not an approved efficacy arm,
is event-based phase synchronization using measured joint lag/contact events
rather than the wall clock. It would adapt phase timing within a gait cycle,
not merely choose another fixed cadence or phase offset. However, the existing
fixed-cadence and lift-lead interventions already improved contact/lift timing
without increasing yaw; apparent phase mismatch alone is therefore weak support.
The corrected endpoint/contact semantics must first show a reproducible
phase-local loss that such feedback can change without lowering achieved
forward progress. The finite next step, if an owner pursues it, is analysis of
the corrected frozen traces for that specific residual, with no new bank and
no training. If no distinct phase-local mechanism survives that analysis,
record the evidence gap instead of inventing a steering arm to occupy GPUs.
Scratch has independent active work and need not wait for this design decision.
