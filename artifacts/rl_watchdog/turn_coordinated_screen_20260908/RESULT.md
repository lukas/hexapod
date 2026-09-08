# Coordinated steering causal screen — executed, frozen predicates say STOP

Executed 2026-09-08 (~08:0x UTC) on the controller CPU in the retained
validated full-mesh worktree `/workspace/hexapod_hybrid_fullmesh_20260908`
(no XML/asset regeneration; all 38 mesh assets + 10 helper sources verified
bit-identical to the reviewed bank's recorded hashes and to current main).
Frozen inputs verified before execution: checkpoint `61f9c20f...`, full-mesh
XML `7efb8e8a...` (34 meshes, 4.80573 kg), 64-key cfg `aabf4cc2...`, prereg
spec `847db884...`, frozen templates `7014cf63...` (re-derived bit-exactly in
a scratch copy from `single_joint_inputs.json`; never refit), reviewed source
bank `c922b547...`. Original 400/20/0.375°/350 counts/s contract and 100 Hz
asserted per rollout; seed 0 / DR 0; vx=.08, wz=±.15; starts 0/π; original
1 s hold + 1 s ramp; 5 pulse ticks + 75 unchanged policy ticks, 80-tick
scoring. No training, no robot, no shared-code change, no healthy-job stop.

**Screen decision (frozen rule): STOP.** Neither global amplitude qualifies:
at 0.025 no template meets primary+direction in both starts; at 0.05 exactly
one template (`wz_neg_phase0`) fully qualifies — primary (≥5 mrad actual
positive-vector gain WITH corrected retention), odd>0 direction support, and
opposite-vector retention in BOTH starts — but no wz-positive template
qualifies at either dose, and the prespecified rule requires support for
EACH yaw command sign at ONE global amplitude. Per the frozen scope the
quarter-phase and straight holdouts are NOT licensed and were not run; the
templates were not refit; no PPO canary follows.

## What the screen measured (this is a real, new positive signal)

- 4 continuous baselines reproduced the reviewed bank EXACTLY (P1/P2 600/638,
  window hashes, prefix/endpoint full-state digests, primary yaw equal).
  8/8 zero controls passed full integration/controller/recurrent/obs state +
  trace parity BEFORE any pulse; 32/32 pulse prefixes matched. 0 action-bound
  clip hits anywhere — the full intended coordinated dose was delivered
  (recorded per coordinate per tick in the bank).
- **First supra-threshold pulses of any class:** 5/32 positive-vector
  branches reach ≥5 mrad raw gain (max **7.066 mrad**, wz −.15/start 0/tick
  638/amp .05), 4/32 also pass corrected retention — versus the single-joint
  bank's 0/288 (max 4.10 mrad). The coordinated class is causally stronger,
  as hypothesized (larger total norm; new dose class; single-joint negative
  preserved).
- **Negative yaw is supported, positive yaw is not.** `wz_neg_phase0`
  qualifies at 0.05 in both starts (7.07 / 5.67 mrad; forward ratios
  0.910/0.910; opposite-vector retention clean). At 0.025 its members read
  4.992 (0.008 mrad under the bar — reported as the near-miss it is, bar
  unchanged) and 5.103 mrad. The wz-positive side fails two different ways:
  at 0.025 `wz_pos_phase1` passes at start 0 (5.271 mrad, retention OK) but
  its matched π-start member responds −0.497 mrad (direction fail — the only
  odd<0 state of 16); at 0.05 the two strongest wz-pos members (5.558, 3.253
  mrad) FAIL forward retention (ratios 0.854, 0.891 < 0.9): positive-yaw
  pulses at these phases buy yaw by taxing forward progress.
- **Odd vs even:** odd response range −0.53..+4.30 mrad; even (nondirectional
  facilitation) −0.37..+3.27 mrad — comparable magnitudes, exactly as the
  freeze warned. Direction support (odd>0) held at 15/16 state×amplitude
  points. Stronger ±5 mrad reversal: 0/16 (G_minus never ≤ −5 mrad; extreme
  −3.86 mrad). Central-secant linear predictions (5.2–12.4 mrad) were
  heuristics; measured G_plus max 7.07 mrad confirms they are not authority
  bounds in either direction.
- Retention 30/32 branches (both failures = wz-pos forward ratio, above);
  loaded-foot-seconds and material-slip speed reported separately per branch
  in `screen_summary.json` (slip distance ratios 0.949–1.117).

## Scope and non-claims

Same-state success does not license PPO; this screen's STOP closes THIS
frozen finite proposal (four sign-box templates, 5-tick bursts, 0.025/0.05,
eight discovery states) and nothing else. It does NOT close longer bursts,
recurring/closed-loop schedules, learned steering, or other coordinated
derivations. A recurring controller/burst schedule and the original 15 s
both-yaw-signs + straight validation remain prerequisites before any
justified 2M canary.

## Concrete next mechanism question (recorded, not executed)

The +wz failure pattern is informative: is it (a) a SIGN-BOX DERIVATION
ARTIFACT — the unit-box vote discards the magnitude structure of the mean
central secant (wz-pos templates had 12/18 member sign agreement; the
sign-box also inflates weak axes to full dose), or (b) a PLANT/GAIT
ASYMMETRY — at these phases the plant cannot yaw-positive without paying
forward progress (consistent with the earlier traction-limited conversion
finding and the tripod-asymmetric conversion residual lead)? The cheapest
discriminating experiment is a NEW frozen proposal changing ONE thing:
magnitude-weighted templates (mean-central-secant direction, L2-matched to
the sign-box 0.2121 at 0.05) at the same states/timing/doses/bars. If
magnitude weighting recovers +wz primary+direction in both starts, (a); if
+wz still fails on forward retention, (b) and the recurring-schedule design
must budget a forward-progress cost for positive yaw. Either way the bars
above stay unchanged.

## Artifacts

- `coordinated_screen_bank.py` — runner (copy of the reviewed runner with
  only the pulse mechanism/grid/baseline-identity changed; header documents
  the diff surface). `analyze_coordinated_screen.py` — frozen predicates.
- `full/bank.json` — raw 4 baselines + 40 branches, per-coordinate actual
  doses and clip masks per pulse tick, full state digests.
- `screen_summary.json` — per-state G+/G−/odd/even (primary and endpoint),
  retention checks, qualification table, verdict.
- `controller_run.log`, `manifest.json` — execution receipt + file hashes.
