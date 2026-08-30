# todaypolicy - working policy bundle for today's demo

Last updated: 2026-08-30 ~17:4x. This is the delivery track, not the
single-policy research track.

## DONE (2026-08-30): `todaypolicy-mlpsf-tuck-v1` PACKAGED, ALL TODAY BARS PASS

Fresh full-mesh regen on the controller (mesh STL assets rebuilt from
the CAD tools — `make_xtool_hex_mount_plate.py` +
`make_xtool_hex_raised_platform.py` were needed first; the gitignored
electronics-stack STLs did not exist here):
`logs/manual_drive/todaypolicy_mlpsf_tuck_v1_fullmesh/` — scripted tuck
stand → 28 s human joystick script on the exported MLP-singleframe walk
(det) → scripted tuck lower. Every TODAY bar passed: 0 terminations,
`model_variant=full_mesh` (3.494 kg), no sacrificed legs (6/6 legs
swing 32–37x, duty 0.51–0.62), course_err_1s med 2.42° / p90 6.98° /
wrong 0.0, progress_ratio 0.418 (≥0.40; 0.60 stretch not met —
teacher-ceiling), cur_max 2.64 A / cur_p95 1.886 A, video strip clean
(level body, roll peak 1.9°, no loaded-foot drag in stand/lower).
Durable copies + GO/NO-GO + browser/controller selector path:
`rl_docs/tracks/todaypolicy/bundle_mlpsf_tuck_v1/` (GO_NOGO.md,
summary/composition/transfer_manifest.json, drive.mp4). Verdict: **GO**
for MuJoCo/controller handoff; hardware steps remain operator-owned
(read-only preflight first, per transfer_manifest blockers). Remaining
optional upgrade (not a blocker): swap walk role to a walkteach-acq12m
lineage export if its UX beats MLP-singleframe on the identical
12 s-hold suite.

Next #2 CLOSED same cycle — learned-vs-scripted tuck A/B (identical
harness, seed, script; only stand/lower controller swapped,
`stancemix_tuckclock_scratch8m` learned stance):
`logs/manual_drive/todaypolicy_mlpsf_learnedtuck_ab/`. Learned tuck
completes all phases (0 terminations, no sac legs, video clean) but is
strictly worse on the deciding bars: **cur_p95 2.153 A BREACHES the
≤2.0 bar** (scripted 1.886), slip total 3.61 vs 2.72 m, course p90
8.31° vs 6.98°; progress/course-med equal (walk role identical).
Ruling: **scripted tuck stays the bundle primary**; learned tuck is a
working but hotter/slippier fallback. No further stance submodel spend
for this track.

Next #3 CLOSED (2026-08-30 ~19:5x, idle-kick — no other track had
runnable GPU work; standwalk's own dualbc4 canary read was genuinely
mid-flight): ran the exact swap the "Remaining optional upgrade" line
asked for — `ops.sh hybriddemo cw-walkteach-scripted-allhead-acq12m
--script human --walk-seconds 28 --speed 0.08 --policy-mode
deterministic` (same script/speed/seconds as the bundle's own demo,
only the walk-role checkpoint swapped; stand controller defaulted to
`step` not `tuck` for this check, a harmless mismatch since stand
happens before the walk-phase metrics that decide this and both
finish clean) — `logs/manual_drive/todaypolicy_walkteach_acq12m_swap_check/`.
Result: **does NOT beat the bundle, keep MLP-singleframe primary.**
Head-to-head on the identical harness (current bundle's own
`bundle_mlpsf_tuck_v1/summary.json` vs this run's `summary.json`):
`walk_progress_ratio` 0.418 (current) vs **0.38 (candidate, MISSES
the todaypolicy 0.40 floor)**; `course_err_1s_med_deg` **2.42 vs 6.15**
(candidate is 2.5x worse and marginally breaches the <=6 bar);
`course_err_1s_p90_deg` 6.98 vs 12.09 (also worse). Candidate DOES win
on current draw (`cur_p95_a` 1.886 vs **1.073**, big thermal margin)
and total slip (3.951 vs 2.799) and, per the earlier per-heading
`eval_cmd_suite` read (`logs/ckpt_eval/cw_walkteach_scripted_allhead_acq12m_cmdsuite.json`
vs `..._mlp_singleframe_acq1_stdanneal_cmdsuite12.json`, both 12s
holds), has real turn authority the MLP-singleframe walk role
structurally lacks (`tip_ccw`/`tip_cw` `wz_err_med` 0.076-0.106 vs
0.30/0.30 — MLP-singleframe has zero wz obs channel, so it literally
cannot respond to a turn command). But turn authority is not a
todaypolicy DONE-gate axis today (the demo `script=human` only ever
issues vx/vy, never wz), and the two bars that ARE gated
(progress_ratio, course tracking) both favor the CURRENT bundle by a
wide margin on the harness that matters (the real 28 s composed demo,
not the per-heading fixed-command suite — the per-heading suite's
"comparable completion, much lower slip" read undersold how much
worse walkteach-acq12m's course-following gets once the script
actually changes direction repeatedly, a fair warning that per-heading
cmdsuite parity does not transfer to human-script parity). **Ruling:
no bundle swap.** Recorded as a viable alternate walk role for a
future turn-capable bundle (its own turn authority is real and
unique), not a replacement for today's candidate. This closes the
track's own last open Next item; nothing else is queued here.

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

1. **DONE 08-30.** Package `todaypolicy-mlpsf-tuck-v1`: regenerate/keep
   a fresh `ops.sh hybriddemo` full-mesh video, write a short GO/NO-GO,
   and make sure the browser/controller can select the bundle.
2. **DONE 08-30.** Compare learned tuck stand/lower vs scripted tuck in
   the same demo harness. Scripted tuck stays the fallback (learned
   breaches the current bar).
3. **DONE 08-30 ~19:5x — NO SWAP.** Compared
   `cw-walkteach-scripted-allhead-acq12m` as a walk-role swap on the
   identical hybriddemo harness: it MISSES the progress_ratio (0.38 <
   0.40) and course_err_1s (6.15 > 6) bars the current bundle clears
   cleanly, despite better current draw/slip and real (unused) turn
   authority. Bundle stays `todaypolicy-mlpsf-tuck-v1` unchanged. See
   the dated entry above for full numbers.
4. Feed any clean result back to `standwalk` as a teacher/source
   candidate, but do not let this track block on the single-policy gate.
   Nothing further queued for this track right now — it is DELIVERED
   and its own Next list is closed 1-3; only a future clean
   walk/stand/lower improvement elsewhere in the fleet would reopen it.

## Boundaries

- No physical robot motion from this track unless the operator asks in
  the current turn.
- This track may build glue, exports, manifests, docs, browser UI, and
  short missing-submodel runs.
- The single-policy goal stays in `standwalk`; todaypolicy is allowed to
  ship a composed controller if that is what works.
