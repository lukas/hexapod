# todaypolicy - working policy bundle for today's demo

Last updated: 2026-08-30. This is the delivery track, not the
single-policy research track.

## Goal

Produce a useful MuJoCo/controller-transfer candidate today by composing
policy plus state explicitly. A valid answer may be a bundle such as:

`scripted-or-learned tuck stand -> exported RL walk policy -> scripted-or-learned tuck lower`

This track may reuse existing learned policies, scripted controllers,
CPG controllers, browser/controller glue, and manifests. It does not
claim the single-policy problem is solved. `standwalk` continues in
parallel until one mesh/100 Hz policy can perform sit -> rise ->
joystick walk -> lower by itself.

## Current Best Bundle

`todaypolicy-mlpsf-tuck-v1` is the best immediate candidate:

- Stand/lower: tuck path, preferably the learned
  `stand_stancemix_tuckclock_scratch8m` family when comparing learned
  stance, otherwise scripted `tuck` as the low-current baseline.
- Walk: `cw-walk-allheading-mlp-singleframe-acq1-stdanneal`, exported
  as `linux_control/policies/walk_allheading_mlp_singleframe_acq1_stdanneal.json`.
- Local full-mesh check, 2026-08-30:
  `logs/manual_drive/cw_walk_allheading_mlp_singleframe_stdanneal_hybrid_tuck_ux_human28/`
  ran stand -> walk -> lower with no termination, no sacrificed legs,
  `walk_progress_ratio=0.418`, `course_err_1s_med_deg=2.57`,
  `wrong_course_frac_1s=0.0`, `cur_max_a=2.64`.

Interpretation: this is usable as a stable demo candidate, but it still
feels underpowered. Joystick direction is good; speed authority is the
weak axis.

## DONE Gate

This track is DONE for the day when a named bundle has:

- full-mesh MuJoCo video for stand -> joystick walk -> lower;
- `summary.json`, `composition.json`, and `transfer_manifest.json`
  checked into a durable path or summarized in docs;
- exported controller-ready policy JSONs for every learned role;
- browser/controller selector path documented or built;
- GO/NO-GO note for hardware handoff, with physical robot work still
  operator-owned.

Minimum demo bars for a TODAY pass:

- zero falls/terminations in the demo;
- `model_variant=full_mesh`;
- no sacrificed legs;
- walk `course_err_1s_med_deg <= 6`, p90 <= 15, wrong-course fraction 0;
- walk `progress_ratio >= 0.40` for today's baseline, with a stretch
  target >= 0.60 for a satisfying joystick feel;
- `cur_max_a <= 2.7`, `cur_p95_a <= 2.0`;
- no loaded-foot inward drag in the stand/lower phase.

## Next

1. Package `todaypolicy-mlpsf-tuck-v1`: regenerate/keep a fresh
   `ops.sh hybriddemo` full-mesh video, write a short GO/NO-GO, and
   make sure the browser/controller can select the bundle.
2. Compare learned tuck stand/lower vs scripted tuck in the same demo
   harness. Keep scripted tuck as the fallback if learned lowering is
   twitchy or drags loaded feet.
3. If the walk still feels too soft, compare against the running
   `cw-walkteach-scripted-allhead-acq12m{,-s1}` outputs as soon as they
   land. Do not spend this track's budget on a monolithic policy unless
   it is the fastest path to a working bundle.
4. Feed any clean result back to `standwalk` as a teacher/source
   candidate, but do not let this track block on the single-policy gate.

## Boundaries

- No physical robot motion from this track unless the operator asks in
  the current turn.
- This track may build glue, exports, manifests, docs, browser UI, and
  short missing-submodel runs.
- The single-policy goal stays in `standwalk`; todaypolicy is allowed to
  ship a composed controller if that is what works.
