# rl_only lower-role over_current SYSTEM-ID BASELINE check (2026-10-01)

Scoped item: the stall-corroboration follow-up
(`lowerrole_overcurrent_stallclass_2026-10-01/SUMMARY.md`) named two
unscoped next questions and recommended doing the cheaper one first --
"a current-cap system-ID check: what sustained torque does the
scripted/stance baseline itself draw during an equivalent load phase,
to tell whether 2.6-2.9A is normal-for-this-motion or policy-specific
excess." This item answers that question. Zero GPU spend (CPU MuJoCo
only).

## Tool
New `rl_move/sim/probe_lower_scripted_current_baseline.py` (2 tests),
a thin sibling of `probe_lower_achievability.py` that reuses its exact
env/IK/schedule machinery (same `LAUNCH_OVERRIDES`, same bus 400/20
pin, same HOLD_S=1.0/RAMP_S=5.0 pacing as the trained
`cw-stance50hz-rlonly-lowerrole-scratch-sac-*` recipe) but captures the
FULL per-tick, PER-JOINT `robot_state.over_current_reading` trace
(the exact `over_current_signal` torque-proxy the SafetyLayer trips on
and `trip_summary`/`audit_over_current.py` analyze -- `min(|torque|*
1.2, 3.0)` lowpassed, rails at 2.64 A when actuator torque saturates
its +-2.2 N*m forcerange) instead of `probe_lower_achievability.py`'s
own `servo_current` (the validated mechanical-power model, which reads
~0 A at a quasi-static hold by design and therefore cannot see what the
real trip responds to -- see module docstring). Swept the full
depth range the lineage trains at (15-88mm, `actions.max_height_mm=88`
cap) x 3 seeds (deterministic by construction: `randomize=False`,
`dr_scale=0.0`, pure open-loop IK -- seeds are a no-op control, kept
only to confirm that).

## Finding: the scripted open-loop descent never gets anywhere near rail, at ANY depth -- the policy's 2.6-2.9A sustained current is NOT a system-ID/torque-budget fact of this motion
At the deepest tested depth (88mm, the lineage's own `max_height_mm`
cap -- deeper than any real episode's commanded target), peak per-joint
torque-proxy current across all 18 joints and 3 seeds is **1.258 A**
(`L1_knee`), **43% of the 2.9 A trip threshold**. Every depth from
15-88mm stays flat/monotonically-rising and comfortably sub-rail
(`any_joint_at_rail: false` at every single depth/seed combination, 27/27
rows). Knees dominate hips at every depth (e.g. at 88mm: knees
1.247-1.258A vs hips 0.575-0.579A) and all six legs are near-perfectly
SYMMETRIC at every depth (expected: a pure vertical feet-anchored
descent loads every leg identically by construction) -- in particular
there is **no L1-hip-specific or L5-hip-specific signature at all** in
the scripted baseline; L1 and L5 hips read within 0.003 A of every
other leg's hip at every depth.

This directly answers the system-ID question: supporting the
mesh-model's 3.5 kg body through this ENTIRE depth range, via a
perfectly-tracked trajectory with zero policy noise/instability, is
**not** itself a near-rail load on any joint. The policy's own
2.6-2.9A sustained currents and L1-hip-concentrated corroborated
stalls are therefore **policy-specific excess, not an inherent
torque-budget ceiling of the motion** -- recalibrating
`safety.max_current_a`/the actuator contract would be treating a
control-quality symptom as a system-ID fact it is not.

## What this does and does not change
Does NOT raise the lower_ok pass-rate or alter
`bundle_rlonly_lifecycle_v2`'s EVIDENCE-candidate status (unchanged,
per `todaypolicy/STATUS.md`). Does NOT itself fund a new RL arm --
per the stall-corroboration doc's own build order, this was a gate
BEFORE scoping the other named question, not a replacement for it.

What it DOES change: it CLOSES the "maybe it's just system-ID /
recalibrate the threshold" branch outright (no further dose/threshold
probe needed -- the ~43%-of-rail headroom is decisive, not a close
call), and it STRENGTHENS the case for the OTHER named question (an
L1-hip-specific genuine-stall investigation) by ruling out the
alternative explanation: since the symmetric, physics-only baseline
shows no hip asymmetry anywhere, the real policy's L1-hip
concentration (4/5 corroborated stalls) must come from something the
POLICY does differently on that leg (asymmetric loading, a local
control instability, or a reward/observation-shaping gap specific to
that leg's role in its learned gait), not from unavoidable geometry or
mass distribution. Next (unscoped, next lever): instrument the ACTUAL
`cw-stance50hz-rlonly-lowerrole-scratch-sac-s1` rollouts' per-leg
commanded-vs-achieved q_rad / torque trace specifically on L1 hip
during the CORROBORATED_STALL episodes and compare against this
baseline's L1-hip trace at the same wall-clock point -- if the policy's
L1 hip torque is multiples of this baseline's ~0.58A ceiling while
every other leg tracks near it, that pinpoints a single-leg control
pathology (candidate root causes: per-leg observation asymmetry,
asymmetric reward pricing, or a specific posture the policy adopts that
loads that leg more than the symmetric scripted reference does) worth
a targeted reward/architecture lever design pass. Not yet built.

Evidence: `logs/probe_lower_scripted_current_baseline.json` (27 rows,
3 seeds × 9 depths, bit-identical across seeds as expected for a
deterministic open-loop replay).

## Addendum (same cycle, zero additional eval cost): direct trace comparison confirms the gap on real data, not just a bound
The stall-corroboration item's own per-episode JSON dumps
(`lowerrole_overcurrent_stallclass_2026-10-01/current_trace_*/
direct_*_over_current.json`) already carry the full (T,18)
`current_trace_a` array for every collected episode, including all 5
CORROBORATED_STALL ones -- no new eval needed, pure re-analysis of
already-collected artifacts. Reading the hot-run window directly off
those 5 traces:

| episode | joint | hot_run_ticks (@50Hz) | mean current over hot window |
|---|---|---|---|
| s1_seed0/direct_1 | L1 hip | 88 (1.76s) | 2.62 A |
| s1_seed100/direct_1 | L1 hip | 66 (1.32s) | 2.629 A |
| s1_seed100/direct_7 | L1 hip | 23 (0.46s) | 2.606 A |
| s1_seed100/direct_12 | L1 hip | 59 (1.18s) | 2.626 A |
| s1_seed100/direct_2 | L2 knee | 0 (already hot at capture start) | 2.638 A (max) |

Every one of these sustains **>=4.5x** this doc's scripted-baseline
L1-hip ceiling (0.575-0.579A, measured across the ENTIRE 15-88mm
trained depth range) for anywhere from 0.46 to 1.76 CONTINUOUS
seconds. This is not a borderline or noise-level gap -- it directly
confirms, on the actual failing rollouts (not just an upper-bound
argument), that the policy drives L1 hip to sustained near-rail torque
that the matched-physics scripted reference never approaches at any
depth it's trained to reach.

Next narrower question (still unscoped/unbuilt, a genuine DIG-IN
candidate per RESEARCH_RULES' root-cause-chain discipline before any
reward patch): is L1 hip being driven toward/against its JOINT LIMIT
during these hot windows (an architecture/bias-offset artifact), or is
it fighting an asymmetric LOAD with room to move (a reward-pricing/
coordination artifact)? Answering this needs a per-tick qpos capture
on L1 hip during the hot window (not present in the existing dumps,
which only kept the trip-adjacent current/qvel/height traces) --
a small, cheap follow-on extension of
`eval_lifecycle_handoff_rlonly.py`'s `--current-trace-dir` capture, not
yet built.
