# todaypolicy-mlpsf-tuck-v1 — GO/NO-GO (2026-08-30)

## Verdict: GO (MuJoCo bundle delivered; hardware handoff via Robot Lab guarded runner)

Named bundle: `todaypolicy-mlpsf-tuck-v1` — composed controller, not a
single policy. Fresh full-mesh regen this cycle (controller pod, mesh
STL assets rebuilt from CAD tools):
`logs/manual_drive/todaypolicy_mlpsf_tuck_v1_fullmesh/` (drive.mp4,
summary/composition/transfer_manifest copied here durably).

## Composition

| Role | Controller | Export |
|---|---|---|
| Stand (belly→walk_ready) | scripted `tuck` (standup_modes.json, fwd) | n/a (scripted) |
| Walk (joystick) | `cw-walk-allheading-mlp-singleframe-acq1-stdanneal` det | `linux_control/policies/walk_allheading_mlp_singleframe_acq1_stdanneal.json` (obs 74, 100 Hz, parity 1.4e-07) |
| Lower (walk_ready→grounded) | scripted `tuck` (reverse) | n/a (scripted) |

Learned stance alternative (not default; compare when useful):
`linux_control/policies/stand_stancemix_tuckclock_scratch8m{,_s1}.json` (obs 68).

## TODAY bars — all PASS

- falls/terminations: 0 (terminated=false, truncated=false, 50 s) PASS
- model_variant=full_mesh (nmesh 34, 3.494 kg) PASS
- sacrificed legs: none; gait_valid true; 6/6 legs swing (32–37 swings, duty 0.51–0.62) PASS
- course_err_1s med 2.42° (≤6), p90 6.98° (≤15), wrong_course 0.0 PASS
- walk_progress_ratio 0.418 (≥0.40 baseline; stretch 0.60 NOT met — known speed-softness, teacher-ceiling per walkteach acq12m read) PASS
- cur_max 2.64 A (≤2.7), cur_p95 1.886 A (≤2.0) PASS
- stand/lower: no loaded-foot inward drag on video strip; roll peak 1.9°, phase_errors [] PASS

## Browser/controller selector path (existing machinery, no new code)

1. Walk slot: RL tab → policies list → select
   `walk_allheading_mlp_singleframe_acq1_stdanneal.json`;
   `rl_policy_select` routes by obs_dim (74 → walk slot) and atomically
   replaces `rl_walk_weights.json`. Role pinning (optional):
   `~/.hexapod_rl_roles.json` role "walk".
2. Stand/lower: Stand-Up lab → mode `tuck` forward / reverse
   (`BenchAPI.standup`, hardware truth 08-10: tuck peaked 2.48 A).
3. No physical motion was performed; hardware handoff steps + blockers
   are in `transfer_manifest.json` (read-only preflight first, stay in
   trained command envelope, stop on tip/brownout/hot motor).

## Caveats

- Speed authority is the weak axis (course_speed_ratio ~0.42); zero
  turn authority in this walk diet (no wz obs) — turns are composition-
  layer or scripted-teacher-lineage work. If `walkteach acq12m`-lineage
  exports land better UX, swap the walk role JSON via the same selector.
- This bundle does NOT mark `standwalk` green; single-policy work
  continues (dualbc4_walkteach distill in flight).
