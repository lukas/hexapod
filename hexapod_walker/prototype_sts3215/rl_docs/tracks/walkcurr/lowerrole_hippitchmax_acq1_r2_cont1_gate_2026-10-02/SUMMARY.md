# s0+s1 hippitchmax-acq1-r2-cont1 composed gate result (2026-10-02)

## Harness bug found and fixed first
Ran this ledger entry's own registered gate (`eval_lifecycle_handoff_rlonly.py`,
det, n=18 episodes x seeds {0,100}, stance `currentcap29-s5-klrollback05-acq15m`
/ walk `slew_smooth_s0` / this seed's own `...hippitchmax_acq1_r2_cont1.zip`) --
the pasted triage only carried the isolated DR-0/owncfg gate (own-reset lower,
n=6), not the composed protocol this entry's gate text names (same situation
as the jointlimitlower-acq1-cont1-r2 precedent this same cycle's predecessor
hit).

First pass (`seed{0,100}_s{0,1}_n18_report.json`, no `--lower-cfg`): composed
direct-arm `lower_ok` **0/36 for BOTH seeds**, and -- the tell -- the `plant`
arm (walk champion's own clean reset -> lower handoff, not even touching the
stance role) ALSO failed 100% of the time. A checkpoint that passes ~70-90%
of its own isolated gate failing literally every plant-arm episode is not a
training-quality signal, it's an environment-construction bug: `env_lower` is
always built from `cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp.
CFG_ARGS`, a FIXED verbatim list frozen at the original `drramp-acq1` launch
command -- it has no `safety.hip_pitch_max_deg` entry, so every composed-gate
run of ANY hippitchmax-trained lower checkpoint was silently evaluating it
under the OLD/legacy (uncapped, +40 deg) hip-pitch clip instead of the +29.8
deg clip it was actually trained under. A genuine train/eval cfg mismatch,
not a verdict on the policy.

Fixed `eval_lifecycle_handoff_rlonly.py`: new `--lower-cfg` (repeatable
`k=v`, default `None` = bit-exact old behavior) appends extra overrides on
top of the recipe module's own `CFG_ARGS` when building `env_lower`
(`_compose_lower_cfg_args`, unit-tested). Re-ran with
`--lower-cfg safety.hip_pitch_max_deg=29.8` (`*_fixed.json` / 
`current_trace_seed*_fixed/`).

## Result (fixed harness)
Composed direct-arm `lower_ok`:
- s0: seed0 4/18, seed100 3/18 = **7/36**, vs s0's own matched-parent
  baseline (`drramp-acq1`) of **24/36** -- sharp regression.
- s1: seed0 1/18, seed100 1/18 = **2/36**, vs s1's own matched-parent
  baseline of **16/36** -- sharp regression, worse than s0's.

`trip_summary.stall_classification` on all over_current traces across BOTH
seeds, BOTH arms, BOTH checkpoints (119 traces total): **0 CORROBORATED_
STALL, 100% RAIL_MOVING, 0 traces flag `near_joint_limit` / joint `L1_hip`**.
The specific mechanism this cfg key targets (a policy resting at/past the
mesh model's own +0.52 rad hip-pitch wall, demanding sustained restoring
torque) is CONFIRMED gone on both seeds, under the corrected (fixed-harness)
composed eval -- not just isolated-gate noise.

## Verdict feeding into ledger (per this entry's own registered gate text)
"PASS if lower_ok beats baseline AND zero CORROBORATED_STALL. PARTIAL if
only one holds. FAIL if neither holds or training regresses." Here: the
CORROBORATED_STALL clause HOLDS (confirmed zero, both seeds); the lower_ok
clause does NOT hold (both seeds regress sharply instead of improving).
Training itself did not regress (reward quarters s0 [402.6,641.8,631.6,
674.1], s1 [412.5,649.2,646.7,628.4], both recovering/rising through the
full budget, matching the pre-prune curve's own recovery shape). Exactly
one condition holds on both seeds -> **PARTIAL** (s0 and s1 both).

This reproduces the SAME composed-robustness gap the entrybank020 closure
and the jointlimitlower closure already found: fixing an isolated-gate
failure mode (stall-vs-load false positive for jointlimitlower; the L1-hip
dead-zone exploit for hippitchmax) does not by itself fix control quality
under composed walk-exit entry diversity -- here the tighter hip-pitch
envelope plausibly removes actuation headroom the policy was otherwise
using (even if illegitimately, by fighting the soft limit) to recover from
off-nominal composed entry poses, trading a safety/exploit bug for worse
composed generalization.

## Code: ADOPTED (not left as an opt-in gate)
`safety.hip_pitch_max_deg` is a MODEL FACT (mesh/mesh_mjx's own CAD hip-pitch
stop is +29.8 deg; primitive's own MJCF really does extend to +40 deg), not
a tunable reward lever like the mechanisms RESEARCH_RULES' adopt-or-delete
binary was written for -- so "adopt" here means: `SafetyLayer.__init__` now
derives the unset-key default from `env.model_source` automatically (mesh/
mesh_mjx -> 29.8 deg, primitive -> untouched legacy servo ceiling, bit-exact
for the CONTINUITY RULE's primitive-pinned resumes). No launch command needs
`--cfg-set safety.hip_pitch_max_deg=29.8` going forward on mesh; the explicit
key remains as an override escape hatch (used by `--lower-cfg` above, and by
`test_hardware_envelope.py`'s explicit-value tests). This is a genuine
correctness fix (removes a real exploitable dead zone from EVERY future
mesh-sourced lower-role AND any other role that happens to drive hip-pitch
that high) independent of this run's own composed-robustness regression,
which is a separate, still-open problem.

## Next
NOT another dose of entry-state exposure during training (entrybank020,
already closed) and NOT reflexively reverting the hip-pitch fix (it is a
correct model-geometry constraint, not an optional knob -- removing it would
reopen a confirmed real exploit). Composed walk-exit robustness for the
`lower` role remains open per the jointlimitlower closure's own framing:
(a) a structurally different off-policy scheme, or (b) accept the plain
`drramp-acq1` lower role (91.7% isolated, ~68% composed under the OLD wide
hip-pitch clip) as the working candidate, now knowing its composed number
benefited from an exploit this cycle closed -- its own true composed number
under the NEW correct safety envelope has never been measured and would be
the fair baseline for any future lower-role composed-robustness work.
