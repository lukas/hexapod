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

## Open follow-ups (not built this cycle)

1. Not wired into `hybrid_demo.py` — no single-command full stand->walk
   (composed-turn)->lower session exists yet; today's evidence is the
   walk-mode gate panel plus a standalone drivevideo.
2. H1 (any sustained substitution helps) vs H2 (turn-specific) is not
   isolated on this exact lineage's own matched pair (a separate wrong-
   substitute control on a different lineage found H1 — see `todaypolicy/
   STATUS.md` 2026-09-12 ~13:5x); doesn't change the recommendation.
3. Physical acceptance is Robot Lab's serialized guarded runner per
   `RL_GOALS.md`, independent of this manifest — not scoped here.
