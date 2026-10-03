# Sector-aware `lower`-role composition wrapper: BUILT + tested; panel
# result INCONCLUSIVE at this n; a reproducibility gap in the same-day
# heading-sign forensics table surfaced along the way (2026-10-03)

Scoped item: `walkcurr/STATUS.md` Next(1)'s "concretely scoped, NOT YET
BUILT" sector-aware composition wrapper for the `lower` role (the
heading-SIGN forensics mechanistic hypothesis, same day, earlier
cycle: the walk role is rotation-equivariant via `rot60.Rot60Policy`,
the `lower` role has a fixed real-leg habit with no heading context,
composition misalignment between the two was the leading explanation
for the heading-sign `lower_ok` collapse). Zero GPU spend throughout
(CPU MuJoCo eval only, same harness/pod as the forensics this follows
up on).

## Part 1 — the tool: `rl_move/sim/rot60_lower.py` + `--lower-rot60`

Built `rot60_lower.py` (`Rot60LowerPolicy`, `lower_obs_transform`,
`lower_action_from_canonical`) and wired it into
`eval_lifecycle_handoff_rlonly.py` as a new `--lower-rot60` flag
(default off, requires `--rot60 --lower`; reads the sector k from the
WALK role's own final `Rot60Policy.k` at the walk->lower handoff).

**Course-correction worth recording** (an hour of this cycle, not
wasted but worth naming so the next person doesn't repeat it): a first
read of `goal_task.py` suggested the `lower` role trains on
`SimHexapodGoalEnv`'s 6-wide BODY-IK action space (roll/pitch/height/
x/y/curl) — a whole new transform had to be derived (tilt_rotate vs
plain rot2 for the action, a `FixedFootBodyIK` geometry-equivariance
test, etc.). Loading the ACTUAL registered recipe
(`cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp.py`) and
the real champion checkpoint showed this was wrong: the recipe builds
`SimHexapodJointWalkEnv` (RAW 18-JOINT actions, same contract as the
WALK role), and the real checkpoint's `observation_space.shape ==
(68,)` — q_rel18+qd18+tilt2+gyro3+prev_action18+goal9, i.e. BIT-FOR-BIT
`rot60.FRAME_WALK`'s own 72-wide layout minus its trailing 4-wide
vx/vy-ref/meas command slice. The final module is a thin pad/truncate
shim around the ALREADY-TESTED `rot60.frame_transform`/
`rot60.action_from_canonical` (no new transform math, no new
approximation, inherits `test_rot60.py`'s own raw-MuJoCo-dynamics-
equivariance proof for free) — simpler and more trustworthy than the
first draft would have been. Lesson: check the REGISTERED RECIPE'S
actual env class and the REAL checkpoint's `observation_space.shape`
before deriving a new obs-layout transform by hand from a plausible-
looking but wrong module.

**Tests** (`rl_move/tests/test_rot60_lower.py`, 11 tests, ~2s,
mechanics-only per RESEARCH_RULES): pad/truncate equivalence to
`rot60.frame_transform` on the shared prefix, round-trip identity,
q/qd and prev_action permutation against `rot60.leg_perm`, goal
one-hot permutation, action-is-literally-`rot60.action_from_canonical`,
a real-checkpoint obs-width pin (118 skips gracefully if the policy
file isn't present), and a wrapper-level k=0-passthrough / k!=0
obs-in-action-out check against the module functions directly (no
duplicated logic to drift out of sync). All green;
`test_rot60.py`/`test_eval_lifecycle_handoff_rlonly.py` (35 tests)
unaffected.

**Bit-exactness confirmed operationally**, not just by unit test:
running the harness with `--lower-rot60` at `--heading-deg 0` (k=0)
reproduces the no-flag run byte-for-byte except the new
`lower_rot60` provenance field (diffed full JSON output, see
`evidence_raw/`).

## Part 2 — the panel: no decisive effect at n=64/arm

Ran the SAME 8-heading x {seed 0, seed 100} x 4-episode panel the
heading-sign forensics used (`--stance currentcap29-s5-klrollback05-
acq15m`, `--walk slew_smooth_s0 --rot60`, `--lower
..._s3_drramp_holdonly100_acq1.zip`, zero `--lower-cfg`), once with
`--lower-rot60` and once without (freshly measured THIS session, same
commit, same checkpoint files — see Part 3 for why the OLD table
isn't a safe comparison point). Direct-arm and plant-arm `lower_ok`
counts, n=8/heading/arm (raw JSON in `evidence_raw/{fresh_baseline_now,
rot60lower_treatment}/`):

| heading | base direct | treat direct | base plant | treat plant |
|---|---|---|---|---|
| -135 | 1/8 | 0/8 | 0/8 | 1/8 |
| -90  | 1/8 | 2/8 | 2/8 | 3/8 |
| -45  | 2/8 | 1/8 | 2/8 | 4/8 |
| 0    | 3/8 | 3/8 | 1/8 | 1/8 |
| +45  | 0/8 | 2/8 | 1/8 | 2/8 |
| +90  | 3/8 | 0/8 | 3/8 | 3/8 |
| +135 | 3/8 | 1/8 | 0/8 | 2/8 |
| 180  | 1/8 | 2/8 | 3/8 | 0/8 |
| **TOTAL** | **14/64** | **11/64** | **12/64** | **16/64** |

Deltas (direct -3, plant +4 on n=64) are well inside the ~6pp binomial
SE for p~0.2-0.25 at this n — NOT a decisive result either direction.
Notably, the dramatic negative/positive heading-SIGN split the
forensics documented does NOT show up in this fresh baseline at all:
negative headings (-135/-90/-45) direct 4/24 (17%) vs positive+180
(+45/+90/+135/180) direct 7/32 (22%) — nowhere near the originally
reported 12-25% vs 38-100% split. See Part 3 for why.

**Verdict: INCONCLUSIVE, not FAIL.** This does not refute the frame-
alignment hypothesis (the effect could be real but swamped by
whatever is making this family's eval noisy right now, per Part 3) nor
confirm it (no clean signal either way). The tool is sound and ready;
re-testing it needs either a much larger n or a confirmed-stable
baseline first.

## Part 3 — a reproducibility gap in the same-day heading-sign table
(the more important finding of this cycle)

The forensics item's own raw per-episode JSON files are still present
on the controller pod (`/tmp/fulldir_trip_diag/`, timestamps ~17:0x-
17:14 today; copied into `evidence_raw/original_forensics_tmp/` here
since `/tmp` is explicitly "ephemeral" per that item's own text and may
not survive to the next cycle/pod). Re-running the IDENTICAL documented
repro command (same checkpoint file paths, same commit — no commits
landed between that item and this one) does NOT reproduce those
files' per-episode results:

- `h0.json` (original, heading=0, presumably seed 0 — see below): all
  4 direct episodes `lower_ok=True`, 1/4 plant fails.
- A fresh rerun of the exact same command at `--seed 0` NOW: all 4
  direct episodes `lower_ok=False` (different fall reasons per
  episode). A fresh rerun at `--seed 100` NOW: 3/4 direct `lower_ok`.
  **Neither matches the original `h0.json` episode-by-episode**
  (compared arm+ep+lower_ok+lower_fall tuples directly — totally
  different pattern, not a near-miss).
- Within-session determinism IS confirmed: two back-to-back fresh
  invocations of the same command (same seed, same everything, run
  sequentially) match EXACTLY, episode-by-episode (see
  `evidence_raw/` — `repeat_h0_s0_run{1,2}` are identical). So this
  is not generic floating-point/thread nondeterminism; something
  about the ORIGINAL run differs from what HEAD now reproduces.
- The three referenced checkpoint files' mtimes (`ls -la`, recorded
  here for the next person to cross-check) all PREDATE the forensics
  run and are unchanged since: lower champion `...s3_drramp_
  holdonly100_acq1.zip` Oct 3 15:47 (before the 17:0x panel), walk
  `..._slew_smooth_s0.zip` Sep 20, stance `..._klrollback05_acq15m.zip`
  Sep 14. A simple "someone overwrote the champion checkpoint mid-day"
  explanation does NOT fit the timestamps.
- Also notable: several of the original panel's seed-0 files are
  named WITHOUT a `_s0` suffix (`h0.json`, `h90.json`, `h135.json`,
  `h180.json` vs the suffixed `h-135_s0.json` etc. for other
  headings) — a naming inconsistency in how that item's own ad-hoc
  loop was run, raising the possibility some cells in the ORIGINAL
  table were read from a mismatched/leftover file (the item's own
  text already flags one such near-miss: "a first, discarded probe"
  with `--lower-cfg` present produced differently-named outputs
  before the official zero-`--lower-cfg` protocol reran "to match
  protocol exactly").

**This is flagged, not root-caused** — I did not find a definitive
single cause (checkpoint overwrite is ruled out by mtimes; code
drift is ruled out by the shared commit; the filename inconsistency
is suggestive but not proven to explain the magnitude). Given the
effort already spent chasing it this cycle, further root-causing is
left open rather than rushed. **What matters operationally:** the
specific numeric table in `lowerrole_fulldir_headingsign_forensics_
2026-10-03/SUMMARY.md` ("Finding 1", TOTAL 35/64 both arms) could not
be regenerated from HEAD this cycle, and should not be treated as a
precisely reproducible reference until someone re-derives it cleanly
(new run, consistently-named output files, no ad-hoc probe files
mixed in) — the qualitative mechanistic hypothesis in that item
(walk's rotation-equivariance vs lower's fixed real-leg habit) is
untouched by this and remains the leading explanation worth testing,
just not provably confirmed by that exact table's numbers anymore.
Logged in `OPERATOR_QUESTIONS.md` as a flagged process note (assume-
and-go: treat any single zero-GPU forensics panel in this family as
needing a same-session, re-derivable control from now on, which is
exactly what Part 2 above does).

## Next
1. Re-derive a clean, larger-n (or at minimum internally consistent,
   consistently-named, single-sitting) heading-sign baseline before
   trusting any further single-panel comparison on this lower-role
   family — the retrain-variance-calibration lesson from earlier today
   (seed-to-seed training variance) and this cycle's finding (apparent
   eval/measurement instability even at a fixed seed+checkpoint) are
   now BOTH live concerns for this lineage.
2. Once a stable baseline exists, re-test `--lower-rot60` against it
   at a larger n (e.g. n=16-24/heading/arm instead of 8) for a real
   read on the frame-alignment hypothesis — the tool (Part 1) is built,
   tested, and zero-cost to rerun; no further construction needed.
3. Do not adopt or close the frame-alignment hypothesis off this
   cycle's panel (Part 2) — it is noise-dominated, not a clean
   refutation.

## Repro commands (zero GPU, ~1-2 min/cell on CPU MuJoCo)
```
# baseline
uv run python -m rl_move.sim.eval_lifecycle_handoff_rlonly \
  --stance rl_move/sim/policies/ppo_goal_cw_stance50hz_rlonly_currentcap29_s5_klrollback05_acq15m.zip \
  --walk rl_move/sim/policies/ppo_goal_cw_walk50hz_slew_smooth_s0.zip --walk-recipe slew_smooth_s0 --rot60 \
  --lower rl_move/sim/policies/ppo_goal_cw_stance50hz_rlonly_lowerrole_scratch_sac_s3_drramp_holdonly100_acq1.zip \
  --lower-recipe lowerrole_sac_drramp \
  --episodes 4 --heading-deg <H> --seed <0|100> --out /tmp/<out>.json

# treatment: add --lower-rot60
```
