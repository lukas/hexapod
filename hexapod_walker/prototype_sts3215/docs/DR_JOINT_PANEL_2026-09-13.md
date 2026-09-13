# DR joint sensitivity panel — 2026-09-13 (speed sim-to-real redirect)

Operator order 2026-09-13 (`rl_docs/tracks/speed/DESIGN.md` "Sim-to-real
robustness direction"; task `hexapod:speed-sim2real-dr`): before training any
robustness arm, test whether JOINTLY sampled, CORRELATED or PER-LEG-ASYMMETRIC
combinations of physically bounded model error reproduce the PS200 hardware
signature (peak roll 16.78°, repeated same-direction ≥5° excursions, no trip)
on the frozen fast parent, where every one-factor probe already failed.

Tool: `rl_move/sim/probe_dr_joint_panel.py` (snapshot `594cd0f7`,
tag `exp/speed-drjointpanel-build`), 7 mechanics tests
(`rl_move/tests/test_probe_dr_joint_panel.py`).

## Evidence inventory (order step 1)

Available on this pod: command protocol
`sysid/protocols/walk_rl_ps200_fwd100_oab_v1.json` (0.10 m/s fwd 12 s,
out-and-back, hardware run 43a6a88a90f9); exported frozen actor
`linux_control/policies/speed50hz_stride_ps200_lift14_massfix_sr105_acq10m.json`
(parity 1.57e-07); summary signature (peak roll 16.78°, matched-sim 3.32°,
closed-loop nominal probe baseline 1.0–2.2°, controls visibly lower-roll).
NOT available (named uncertainties, not blockers): per-joint
position/current/contact traces, exact hardware achieved speed, quantified
control-policy hardware roll. Simulator-supported uncertainty families:
`rl_move/sim/domain_rand.py:RandRanges` (mass/CoM/leg-mass, link length
global+per-leg, friction, contact stiffness, tilt, per-joint kp/kv, torque,
latency, deadband, vel, cmd-drop, encoder/zero/IMU) + panel-added per-foot
friction and per-leg torque saturation (direct MjModel edits).

## Design

48 ensembles = 16 × {independent, correlated(latent: battery-sag, worn-leg,
build-mass, floor), asymmetric(left/right/front/rear/single-leg)} from
panel_seed 20260913 inside `PanelBounds` (conservative engineering bounds,
units + provenance in the dataclass; deliberately wider than training DR,
never absurd). Pre-registered held-out split: index%3==2 (16 ensembles) +
rollout seeds {2,3,4} written to `heldout_manifest.json`, NEVER rolled out or
ranked here — reserved for the trained-arm robustness gate. Search: 32
ensembles × frozen ps200 × seeds {0,1}, 14 s @ 0.10 m/s pin; stage 2 ran both
control policies on the top 12.

## Result: NULL — bounded static parametric error cannot reproduce the signature

Artifacts: `logs/ckpt_eval/dr_joint_panel_20260913/` (panel_spec.json,
heldout_manifest.json, results.json, rows.csv, report.md).

* Nominal baselines: ps200 1.38° / 0.0489 m/s (matches prior probe 1.32°);
  walkteach 1.02°; allheading 1.90°.
* Across all 32 search ensembles: ps200 median peak roll 0.80–3.62°
  (max = `independent_012`, 3.62°, selectivity ratio only 1.24×), zero falls,
  zero recurrent ≥5° excursions anywhere. Best case closes ~2.2° of the ~15°
  closed-loop gap.
* Ensembles clearly bite — achieved speed spans 0.016–0.052 m/s (up to 3×
  speed loss) — so this is a real null, not an inert-dose artifact.

**Conclusion:** within physically bounded static parameters, no interacting,
correlated, or per-leg-asymmetric combination reproduces the 16.78° hardware
roll signature on the frozen policy. Combined with the closed one-factor
probes, the hardware gap is very likely a DYNAMIC, load-coupled mechanism
(series compliance/backlash under load, servo-loop behavior under load,
stick–slip) that the simulator's parametric families do not express. The
decisive unblock for signature replication remains the Robot Lab telemetry
export. This does NOT block the ordered robustness-training comparison — it
re-targets the structured arm at the panel's empirical hard region.

## Hard-region structure (search set, n=33 incl. nominal)

Correlation of ensemble parameters with ps200 peak roll: kp joint-to-joint
spread **+0.84**, frame-coupled zero-bias magnitude **+0.77**, CoM offset
**+0.59**, cmd-drop **+0.53**, ground tilt +0.46, contact stiffness +0.45,
per-foot-friction asymmetry (lower min) −0.59, per-leg-torque asymmetry
(lower min) −0.46. Global scales (mass, friction, latency, vel) are weak roll
drivers. Speed loss is driven by vel/deadband/torque/CoM. Per-joint/per-leg
HETEROGENEITY plus sensing/timing error is the roll axis.

## Pre-registered training comparison (arms launch only after the held-out gate harness exists)

Frozen fast parent = `cw-speed50hz-stride-ps200-lift14-massfix-sr105-acq10m`
(the checkpoint with the hardware evidence; env50dps frontier needs an
unapproved physical envelope change). Gait/reward/actuator envelope held
fixed; ONLY dr.* changes; 2M discovery, one seed, second-seed replication
before acquisition:

* **ARM-CTRL** matched current-DR control (parent recipe continuation).
* **ARM-WIDE** wider independent DR: ranges widened toward `PanelBounds` via
  cfg dr overrides, curriculum-ramped.
* **ARM-STRUCT** structured hard-region DR: correlated/asymmetric sampler
  emphasizing the evidence directions above (kp spread, frame-coupled zero
  bias, CoM, cmd drop, per-foot friction / per-leg torque asymmetry, contact
  stiffness/tilt). Requires new cfg-gated trainer plumbing (default OFF,
  bit-exact when off) — build before launch.

Held-out gate (executable, replaces the literal in-sim 16.78° clause, which
this panel showed is unreachable statically): on `heldout_manifest.json`'s 16
ensembles × seeds {2,3,4} (48 episodes ≥ DESIGN's 48-episode bar), the
candidate must (a) reduce the parent's held-out median peak roll by ≥30% on
the hard decile and overall, (b) zero falls, (c) six-leg gait validity ≥90%
of episodes, (d) robust speed loss ≤20% vs parent on the same ensembles, and
(e) nominal mesh/50 Hz speed ≥90% of parent at the 0.10 pin. The exact failed
physical tape stays out of training/model selection and is replayed only in
the final report.

## Addendum 1 (2026-09-13 ~21:xx, operator task hexapod:speed-sim2real-dr continuation)

Items (a) and (b) of the pre-registration's "Next" list are BUILT and TESTED;
the three arms launch in the same cycle.

* (a) Held-out gate harness `rl_move/sim/eval_dr_robustness_gate.py`
  (previous cycle) now loads RAW SB3 `.zip` checkpoints directly
  (`CkptPolicy` adapter; env contract from the PARENT's exported meta —
  valid because the arms hold the env contract fixed by pre-registration).
  Self-parity smoke: parent export vs parent's own zip on one held-out
  ensemble — roll 2.306 vs 2.306 deg, held-out speed 0.0393 vs 0.0393,
  nominal 0.0434 vs 0.0434 (identical to the reported precision); gate
  correctly fails only clause (a) (a policy cannot beat itself by 30%).
* (b) Trainer-side structured DR plumbing (`rl_move/sim/domain_rand.py`,
  hook in `sim_env.reset`), all default-OFF and bit-exact when off
  (golden-stream test): `dr.foot_friction_scale` / `dr.leg_torque_scale`
  (independent per-foot friction / per-leg torque-saturation asymmetry —
  the two PanelBounds families training DR never had; pure MjModel field
  edits on `geom_friction`+floor cap / `actuator_forcerange`, both in
  `mjx_backend.MODEL_DR_FIELDS`) and `dr.struct_dr_prob` (probability an
  episode's base draw is overlaid with one correlated battery-sag/
  worn-leg/build-mass/floor or per-group asymmetric hard-region ensemble;
  dose menu = frozen `STRUCT_*` constants with PanelBounds provenance,
  frame-coupled zero bias forced on; probability follows the curriculum,
  dose does not). Tests: `rl_move/tests/test_dr_struct_plumbing.py` (8) +
  extended gate/panel suites.

Arm specs as launched (respec of the frozen parent, warm-start
`--init-from-source`, 2M steps, seed 0, everything else verbatim):

* ARM-CTRL `cw-speed50hz-ps200dr-armctrl-disc2m`: no changes — prices the
  pure 2M-continuation effect.
* ARM-WIDE `cw-speed50hz-ps200dr-armwide-disc2m`: independent DR widened to
  PanelBounds via absolute `dr.*` overrides (mass 0.85–1.25, com 0.025,
  leg-mass 0.20, link 0.02/0.02, friction 0.45–1.40, stiffness 0.50–3.00,
  tilt 3.0, kp 0.35, kv 0.40, torque 0.55–1.05, vel 0.70–1.10, latency
  0.70–2.50, deadband 0.50–3.00, cmd-drop 0.08, zero-bias 5.0
  frame-coupled, imu-bias 2.0, foot-friction 0.50–1.10, leg-torque
  0.60–1.05) on the parent's own `--dr-scale 0.0` base (non-overridden
  start-pose/IMU-mount/tipped axes stay at the parent's nominal),
  `env.dr_stage_ramp_steps=1000000`.
* ARM-STRUCT `cw-speed50hz-ps200dr-armstruct-disc2m`:
  `dr.struct_dr_prob=0.6` overlay on the parent's nominal base (0.4 of
  episodes match the parent exactly, 0.6 carry one structured hard-region
  ensemble), `env.dr_stage_ramp_steps=1000000`.

Second-seed replication remains contingent on a held-out-gate winner, per
the order. The held-out manifest stays untouched by training/selection.
