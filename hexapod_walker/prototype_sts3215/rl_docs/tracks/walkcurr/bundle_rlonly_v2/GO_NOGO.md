# walkcurr-rlonly-widen8-crutchoff-s0-warmadapt-50hz-acq1-v2 — GO/NO-GO (2026-09-10)

## Verdict: GO for sim-demo + export readiness, at the operator-mandated 50Hz deployable control rate. NOT a physical-acceptance verdict.

One plain sentence: this replaces `bundle_rlonly_v1`'s 100Hz candidate with
the SAME recipe family's 50Hz warm-start descendant, because the operator's
2026-09-10 `op_20260910_50hz` order established that control.hz=100 is
undeployable on hexapod2 (trips the MCU-bridge timing fault) — the walk
skill itself was independently re-verified intact after the rate change via
matched-parent-comparison, not just re-exported blind.

Named candidate: `walkcurr-rlonly-widen8-crutchoff-s0-warmadapt-50hz-acq1-v2`
— a SINGLE policy (walk role only, no stand/lower composition), same as v1.

## Why this cycle did this (gap it closes)

`bundle_rlonly_v1` (2026-09-09) packaged the `rl_only` walk champion at
control.hz=100. On 2026-09-10 the operator ordered every deployable policy
retrained at 50Hz (`op_20260910_50hz`, `CURRENT_TRUTHS.md`); `any_means`/
`standwalk`/`amp`-track arms picked this up immediately, but nobody had
queued the analogous retrain for the `rl_only` lineage until a 2026-09-10
~21:3x cycle noticed the gap and launched a warm-start canary + matched-
parent-comparison for all 3 champion seeds (s0/s1/s2). All 3 canaries
PASSED (transfer intact); s0's and s2's +18M-step acquisition continuations
also independently PASSED and were exported (`ops.sh entry
cw-walk50hz-rlonly-crutchoff-{s0,s2}-warmadapt-acq1`). This cycle re-cuts
the transfer package around s0's 50Hz export so the physical-delivery
artifact Robot Lab would pick up is no longer the undeployable 100Hz one.

## What shipped this cycle

1. **Verification already complete before this cut** (prior cycles,
   2026-09-10 ~21:3x through ~23:1x): own-cfg DR-0 panel-by-panel comparison
   of the 50Hz s0 acq1 checkpoint against the SAME harness's read of its
   100Hz parent — pooled `gait_valid` 23/24 vs parent's 22/24,
   `progress_ratio`/`slip_per_m` at parity or better on 3 of 4 sub-panels,
   SCORE/* multi-skill check shows the same pre-existing brokenness as the
   parent (no new large regression). Full text: `ops.sh entry
   cw-walk50hz-rlonly-crutchoff-s0-warmadapt-acq1`, `rl_docs/SKILLS.md`.
2. **Fresh reproducible demo captures on this exact 50Hz checkpoint** (this
   cycle, on the controller, CPU MuJoCo, full-mesh model): `ops.sh drivevideo
   cw-walk50hz-rlonly-crutchoff-s0-warmadapt-acq1 --script human` and
   `--script human_turn`, 26s each — both 0 falls, `gait_valid=true`,
   `sacrificed_legs=[]`, `progress_ratio` 1.167/1.233, `slip_per_m`
   5.75/5.94, `course_err_1s_med_deg` 12.0/6.1 — comparable to v1's own
   100Hz demo numbers (1.20/1.24 progress, 5.31/5.58 slip), confirming the
   rate change did not degrade the joystick-drivable behavior a human
   would actually see.
3. **`rl_docs/tracks/walkcurr/bundle_rlonly_v2/transfer_manifest.json`**:
   names the 50Hz candidate, checksums, the export, the corrected
   deg/s-preserving safety contract (`max_delta_q_deg=7.2` at 50Hz, same
   360 deg/s ceiling as the parent's `3.6` at 100Hz — NOT the 4x-slew
   config bug a sibling stand-role 50Hz retrain briefly hit and had fixed,
   see `CURRENT_TRUTHS.md` 2026-09-10 ~22:4x), and every transfer blocker
   below.

## TODAY bars

- Clean `rl_only` training lineage (no BC/AMP/demo anywhere): PASS (unchanged
  from v1 — warm-start + continuation only touched `control.hz`/
  `safety.max_delta_q_deg`/task-reward-shaping levers, no demonstration
  data entered the lineage).
- Deployable control rate (operator `op_20260910_50hz`): PASS this cycle —
  v1 was NOT deployable (100Hz trips the MCU-bridge fault); this is the fix.
- Reproducible non-interactive sim video, 0 falls, `gait_valid=true`,
  `sacrificed_legs=[]`: PASS (both `human`/`human_turn` scripts, this
  cycle's fresh captures, see manifest `demo_metrics`).
- Reproducible interactive launch command: PASS (`sim_viewer/sim_web.sh
  --walk ...`, same pattern as v1, updated checkpoint path).
- Exportable to the robot's torch-free runtime: PASS (re-used the
  N-layer/ELU export format `v1` built; parity 2.23e-07).
- Single sit/rise/walk/lower bundle: NOT CLAIMED — walk role only, same as
  v1 (`any_means`'s `todaypolicy` track owns the composed-bundle question;
  `rl_only` does not require a monolithic actor per `RL_GOALS.md`).
- Physical acceptance: NOT CLAIMED — no robot access from this process;
  handoff to Robot Lab below.

## Registered bounded physical-trial plan (unchanged in substance from v1;
RL_GOALS.md: "register the command range, duration and acceptance criteria
appropriate to the build" before a bounded physical trial)

- **Command range**: forward walk at the trained 0.06 m/s only, plus brief
  (<=5 s) diagonal/near-forward heading changes drawn from the trained 8-way
  set (0/+-45/+-90/+-135/180 deg); AVOID sustained (>10 s) off-forward
  headings — a STANDING limitation carried unchanged from the 100Hz parent
  (13/13 mechanism classes closed for this exact front-pair sacrifice as of
  2026-09-10, no successor fix in flight).
- **Duration**: single trial <=30 s continuous per attempt (matches the sim
  demo's 26 s captures), stop/restart once observed clean.
- **Acceptance criteria** (mirrors RL_GOALS.md's physical bar): smooth
  transitions, all six legs lifting/placing with no dragged/sacrificed leg,
  zero falls, requested vs. achieved direction reported even if imperfect
  (sim course error median ~6-12 deg on this checkpoint — expect similar or
  worse on hardware; a known soft-tracking axis, not a stop condition by
  itself). STOP immediately on tip, brownout, high current, missing servo,
  or hot motor (mirrors every other exported-policy handoff on this
  project).
- **Safety-contract caution (do not skip)**: the exported JSON's own trained
  bus/slew contract (`bus_write_speed=4096`, `bus_write_acc=1000`,
  `max_delta_q_deg=7.2`/360 deg/s) is far above the physical-safe contract
  used by other exported policies on this project (400/20/0.375). Robot Lab
  must verify/derate before any motion — do not run these numbers as-is.
- **Control rate**: 50Hz (20ms tick) — this IS the operator-mandated
  deployable rate for hexapod2; do not substitute the v1 100Hz artifact.

## Next

Robot Lab: run the read-only preflight, confirm/derate the bus/slew contract
above, then the bounded trial as registered — this v2 candidate (or its
same-quality s2 sibling, `walkscratch_rlonly_widen8_crutchoff_s2_warmadapt_50hz_acq1.json`)
supersedes v1 for any physical handoff. Cloud side: read s1's own `-acq1`
continuation once it finishes (n=3 seed triplet); land a genuinely new
off-axis-heading structural fix if one is ever conceived (none named as of
2026-09-10) and re-cut again if it changes the limitation above.

**UPDATE 2026-09-17:** this walk role is now also composed (not modified —
same checkpoint, same weights) with the separately-trained rise+hold stance
role (`bundle_rlonly_stance_v1`) via a direct, no-scripted-blend handoff —
CLEAN, 0/12 falls. See `rl_docs/tracks/walkcurr/bundle_rlonly_lifecycle_v1/`.

**UPDATE 2026-09-18:** this walk role's own SUSTAINED off-forward-heading
limitation named above ("AVOID sustained (>10s) off-forward headings")
now has a packaged, evidence-backed extension OPTION — wrapping the SAME
checkpoint (no retrain) in the mesh-verified `rot60.Rot60Policy`
exact-symmetry canonicalizer removes the chronic front-leg-sacrifice
failure across a 16-episode sustained (60s) full-heading gate (0 falls,
gait_valid 15/16), with one open item (tracking accuracy not yet measured
at this bundle's own fixed 0.06 m/s point) named plainly. See
`rl_docs/tracks/walkcurr/bundle_rlonly_v2/rot60_fullcircle/{transfer_manifest.json,GO_NOGO.md}`.
This is an OPTION layered on top, not a replacement — the plan above
stays the conservative default.

**UPDATE 2026-09-21 ~03:3x:** the sibling raised-slew-cap candidate
`cw-walk50hz-slew-smooth-s0` (0.375deg->3.5deg `safety.max_delta_q_deg`
+ smoothness-reward retune, warm-started off THIS bundle's checkpoint)
is now the walkcurr 50Hz hardware-transfer REFERENCE (see walkcurr
STATUS.md same timestamp): same-or-better `gait_valid`/speed/roll, and
its one open caution (duty-cycle/torque-margin at the raised cap) is
now checked CLEAN. This bundle's `transfer_manifest.json` and the
`rot60_fullcircle/` sub-bundle still point at the superseded
`crutchoff-s0-warmadapt-acq1` checkpoint/export — repackaging onto
`slew-smooth-s0` (re-run `test_rot60.py`/`test_rot60_mesh.py` against
the new checkpoint, re-export + SB3-parity, re-run the sustained-
multiheading panel and the `bundle_rlonly_lifecycle_v1` handoff panel)
is the next concrete, agent-doable, CPU-only step — not done yet, not
a blocker on the plan above in the meantime.
