# walkcurr-rlonly-widen8-crutchoff-s0-cont10m-v1 — GO/NO-GO (2026-09-09)

**SUPERSEDED for physical handoff (2026-09-10):** this candidate trains at
`control.hz=100`, which the operator's `op_20260910_50hz` order established
trips the hexapod2 MCU-bridge timing fault — NOT deployable. Use
`rl_docs/tracks/walkcurr/bundle_rlonly_v2/` (the 50Hz warm-start + acquisition
descendant of this same checkpoint, matched-parent-verified, exported) for
any physical trial instead. This v1 doc is retained for lineage/history only.

## Verdict: GO for sim-demo + export readiness. NOT a physical-acceptance verdict.

One plain sentence: this is the `rl_only` walking champion (clean, demonstration-free
RL lineage) packaged so Robot Lab can pick it up — a working numpy export, a named
transfer manifest with the physical-safety numbers spelled out, and a registered
bounded-trial plan per `RL_GOALS.md` — no physical motion happened this cycle.

Named candidate: `walkcurr-rlonly-widen8-crutchoff-s0-cont10m-v1` — a SINGLE policy
(walk role only, no stand/lower composition), not a controller stack.

## Why this cycle did this (gap it closes)

`STATUS.md`/`CURRENT_TRUTHS.md` (2026-09-09) already recorded this checkpoint's
sim-demo evidence (reproducible drivevideo, viewer entry) but named the physical
delivery step as needing "the best-supported candidate's measured physical
comparison through Robot Lab, after its contract and readiness checks" — no
transfer manifest existed yet, and the checkpoint's own architecture (net-arch
256,256,128 + ELU) could not even be exported to the robot's torch-free JSON
format: `export_policy_np.py` only supported the legacy 2-layer-tanh shape.
Both gaps are closed this cycle (11/11 GPU pods otherwise idle for lack of a
justified GPU launch — see RL_LOG this cycle for the survey).

## What shipped

1. **New tool capability** (`rl_move/np_policy.py`, `rl_move/sim/export_policy_np.py`):
   a generic N-layer / ELU-or-tanh MLP export+load format
   (`NumpyMLPNLayerModel`, `obj["layers"]`), selected by the presence of
   `"layers"` in the JSON (never by `meta.architecture`, which stays `"mlp"`
   for both formats) so every existing 2-layer-tanh consumer keeps routing
   unchanged. The legacy fixed `W1/b1/W2/b2/Wout/bout` layout is untouched —
   `test_export_obs75_mlp_keeps_legacy_matrix_layout` still passes bit-exact.
   6 new tests (`test_export_policy_np.py` x2, `test_np_policy.py` x5),
   19/20 relevant tests green (the 1 failure,
   `test_dual_gru_numpy_sequence_matches_torch_and_threads_both_cores`, is a
   pre-existing float32-tolerance flake reproduced identically on unmodified
   `main` — not caused by this change).
2. **Export**: `linux_control/policies/walkscratch_rlonly_widen8_crutchoff_s0_cont10m.json`
   (obs 72, hidden [256,256,128], activation elu, parity 2.34e-07 over 200
   random observations against the SB3 checkpoint — bar 1e-5).
3. **`rl_docs/tracks/walkcurr/bundle_rlonly_v1/transfer_manifest.json`**:
   names the single-policy candidate, checksums, the export, and every
   transfer blocker below.

## TODAY bars

- Clean `rl_only` training lineage (no BC/AMP/demo anywhere): PASS (tracks.json contract, CURRENT_TRUTHS 09-09).
- Reproducible non-interactive sim video, 0 falls, `gait_valid=true`, `sacrificed_legs=[]`: PASS (both `human`/`human_turn` scripts, see manifest `demo_metrics`).
- Reproducible interactive launch command: PASS (`sim_viewer/sim_web.sh --walk ...`).
- Exportable to the robot's torch-free runtime: PASS this cycle (was previously blocked — see "What shipped").
- Single sit/rise/walk/lower bundle: NOT CLAIMED — this is the walk role only (`any_means`'s `todaypolicy` is the composed-bundle track; `rl_only` does not require a monolithic actor per `RL_GOALS.md`).
- Physical acceptance: NOT CLAIMED — no robot access from this process; handoff to Robot Lab below.

## Registered bounded physical-trial plan (RL_GOALS.md: "register the command
range, duration and acceptance criteria appropriate to the build" before a
bounded physical trial)

- **Command range**: forward walk at the trained 0.06 m/s only, plus brief
  (<=5 s) diagonal/near-forward heading changes drawn from the trained 8-way
  set (0/+-45/+-90/+-135/180 deg); AVOID sustained (>10 s) off-forward
  headings — a STANDING limitation, not a hidden one. **Correction 2026-09-10:**
  this text originally said "until the in-flight heading self-distillation fix
  lands"; self-distillation itself CLOSED as a repair (09-09 ~19:4x, 2/2 seeds,
  same fingerprint as the untreated baseline) and, with it, all four named
  mechanism classes (termination, price, exposure/PPO-loss, self-distillation/
  critic) for this exact off-axis front-pair leg sacrifice are now closed —
  no successor fix is in flight. Reopening needs a genuinely new structural
  idea (none named as of 09-10); treat this as a standing avoidance rule for
  the bounded trial, not a temporary caveat pending an imminent patch.
- **Duration**: single trial <=30 s continuous per attempt (matches the sim
  demo's 26 s captures), stop/restart once observed clean.
- **Acceptance criteria** (mirrors RL_GOALS.md's physical bar): smooth
  transitions, all six legs lifting/placing with no dragged/sacrificed leg,
  zero falls, requested vs. achieved direction reported even if imperfect
  (sim course error median ~12-21 deg — expect similar or worse on hardware;
  this is a known soft-tracking axis, not a stop condition by itself).
  STOP immediately on tip, brownout, high current, missing servo, or hot
  motor (mirrors every other exported-policy handoff on this project).
- **Safety-contract caution (do not skip)**: the exported JSON's own trained
  bus/slew contract (`bus_write_speed=4096`, `bus_write_acc=1000`,
  `max_delta_q_deg=3.6`/360 deg/s) is far above the physical-safe contract
  used by other exported policies on this project (400/20/0.375). Robot Lab
  must verify/derate before any motion — do not run these numbers as-is.

## Next

Robot Lab: run the read-only preflight, confirm/derate the bus/slew contract
above, then the bounded trial as registered. Cloud side: land the in-flight
heading self-distillation fix (or its successor) and re-cut this bundle if it
changes the off-axis-heading limitation; no other action needed to keep this
candidate current.
