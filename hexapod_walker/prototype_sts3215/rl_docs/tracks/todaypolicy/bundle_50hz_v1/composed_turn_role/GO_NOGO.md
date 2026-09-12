# todaypolicy-50hz-v1 walk_turn_capable (composed) — GO/NO-GO (2026-09-12)

## Verdict: GO for controller handoff (sim, ALTERNATE walk role), NOT physical acceptance

This packages the composed-delivery artifact the `amp` track's 2026-09-12
~10:5x entry named as the last open step before packaging (`rl_docs/tracks/
amp/STATUS.md`): a transfer manifest + demo video pointer for the
`walk_turn_capable` role of `todaypolicy/bundle_50hz_v1`
(`../GO_NOGO.md`, `../composition.json`) run through the validated
turn-in-place composition (`--compose-turn-blend-s 0.15`) rather than raw.

**Why composed, not raw:** the raw checkpoint reproducibly freezes/
sacrifices a leg under SUSTAINED turn-in-place (matched pair: RAW
`gait_valid=False` 4/4 seeds, COMPOSED `gait_valid=True` 4/4, `sacrificed_
legs=[]` every seed, `mean|wz|_turn` back in the passing 0.145-0.159 rad/s
band). A control at zero turn ticks shows raw and composed are byte-
identical, so the composition costs nothing when it isn't needed and is
causally responsible for the fix when it is. Full narrative + evidence
paths: `transfer_manifest.json` in this directory, and `../composition.
json`'s `roles.walk_turn_capable.turn_composition_2026_09_12` field.

**This is an alternate role, not the bundle default** — the default stays
the straight-only walk candidate (`../GO_NOGO.md`'s own tradeoff table:
turn-capable det progress_ratio 0.27 vs 0.41, slip 3.87 vs 2.19, plus
hold-mode falls the straight-only candidates don't show). Load this role
only when a session needs joystick turn authority.

**Demo (this directory):** `drive.mp4`/`drive_sheet.png` — 20 s `human_turn`
script, composed (`blend_s=0.15`): `terminated=false`, `gait_valid=true`,
`sacrificed_legs=[]`, `turn_wz_err_med_rad_s=0.0747` (real tracking, not a
freeze), `cur_max_a=2.573A` (inside the 50 Hz motor contract). `summary.
json` carries the full per-tick record.

**Reproduce:** see `transfer_manifest.json`'s `reproducible_video_capture`/
`reproducible_gate_capture` fields — both are direct CLI invocations
against the checkpoint, no new tooling needed (`--compose-turn-blend-s` is
already wired into `eval_checkpoint.py`/`drive_video.py`).

## Full-session demo (2026-09-12, closes open item 1 below)

`hybrid_demo.py` now takes `--compose-turn-blend-s`/`--stall-substitute-
every-s`/`--stall-substitute-dur-s` (same `_ComposedPolicy` wrap
`eval_checkpoint.py`/`drive_video.py` already used, applied to the
walk-phase controller only; default None/0.0 = no wrap, bit-exact).
Ran the actual single-command learned-stand -> walk_ready align ->
COMPOSED walk (`human_turn` script, 20 s, `blend_s=0.15`) -> pre-lower
align -> learned-lower -> limp session this bundle's own stand/lower
role pairs with:

```
ops.sh hybriddemo cw-turn50hz-standwalk-cap29-stdwalklohi-warmadapt-canary2m-acq1 \
  --stand-controller learned --lower-controller learned \
  --stance-policy linux_control/policies/stand50hz_stance_tuckclock_scratch6m_curhot_b23k12.json \
  --script human_turn --policy-mode deterministic --compose-turn-blend-s 0.15
```

Result (`full_session_demo/summary.json`): `terminated=false`,
`truncated=false`, `sim_seconds=40.02` (learned stand-up, 20 s composed
walk incl. a real turn-in-place segment, learned lower, limp settle),
`walk_gait_valid=true`, `sacrificed_legs_all_phases=[]`,
`walk_progress_ratio=0.246`, `roll_peak_abs_deg=3.71`,
`cur_max_a=2.64A` (inside the 50 Hz motor contract),
`walk_turn_wz_err_med_rad_s=0.0642` (real turn tracking — matches the
standalone drivevideo's 0.0747 within noise), `compose_summary.
turn_ticks=106/1000` (the composition engaged exactly on the
`human_turn` script's turn-in-place phase, as designed). Course-error
stats are noisier than the standalone walk-only drivevideo
(`course_err_2s_med_deg` 16.1 vs 10.1) — expected: this session's walk
phase starts from the stand hand-off's own settle transient rather
than a clean `walk_ready` reset, and the script's frequent direction
reversals make the 1-2 s course window noisy by construction (see
other tracks' own notes on this same metric's sensitivity to reversal-
heavy scripts). No new pathology: video (`full_session_demo/drive_
sheet.png`) shows a clean stand-up, real six-leg tripod cycling
through forward/arc/turn-in-place/crab/diagonal segments (the turn-
left segment's path arcs, not freezes), and a controlled learned
lower with no drag/tip. Artifacts: `full_session_demo/{drive.mp4,
drive_sheet.png,summary.json,composition.json,transfer_manifest.json}`
(durable copies of `logs/manual_drive/cap29_acq1_hybriddemo_composed_
humanturn/`).

**Bug found and fixed en route:** `hybrid_demo.py`'s obs-space sanity
check ran on the ALREADY-WRAPPED `RecurrentPredictor` object for any
GRU/dual-GRU checkpoint (this one included) — `RecurrentPredictor` had
no `observation_space` attribute, so loading ANY recurrent checkpoint
through `hybrid_demo.py` crashed with `AttributeError` before this fix
(every other caller checks obs BEFORE wrapping, so this was latent
until a recurrent checkpoint needed `hybrid_demo.py` specifically).
Fixed by forwarding `observation_space`/`action_space` onto the
wrapper (`rl_move/sim/gru_policy.py`), additive-only, covered by
`test_recurrent_predictor.py`. Snapshot `fb7d6f44` /
`exp/hybrid-demo-compose-turn-wire`.

## Open follow-ups

1. **DONE 2026-09-12** — `hybrid_demo.py` wiring above.
2. H1 (any sustained substitution helps) vs H2 (turn-specific) is not
   isolated on this exact lineage's own matched pair (a separate wrong-
   substitute control on a different lineage found H1 — see `todaypolicy/
   STATUS.md` 2026-09-12 ~13:5x); doesn't change the recommendation.
3. Physical acceptance is Robot Lab's serialized guarded runner per
   `RL_GOALS.md`, independent of this manifest — not scoped here.
