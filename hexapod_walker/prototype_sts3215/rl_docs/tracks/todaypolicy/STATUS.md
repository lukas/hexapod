# todaypolicy - working policy bundle for today's demo

Last updated: 2026-09-05 ~08:0x. This is the delivery track, not the
single-policy research track.

## CAMPAIGN robotwalk-smooth-20260906 (operator order fb_20260906T030030_28f422, 09-06) — LAUNCHED

Lukas's explicit request (via Codex MCP note attached to RUN
cw-walkteach-scripted-allhead-acq12m): two bounded PPO arms to improve
the real hexapod's shuffling/rocking (stride) and joystick turn
response, then automatic RobotLab physical trials of promising
completed checkpoints by the LOCAL Codex watchdog (cloud never
operates the robot or enqueues Lab jobs). This note reopens
todaypolicy delivery for exactly these two arms and supersedes the
older no-new-PPO-until-transport-replay note for them.

**Campaign marker: `robotwalk-smooth-20260906`. Exact run names (for
the local completion handoff):**

- `cw-robotwalk-stride-20260906` — 8M, warm from Candidate B, sole
  change `train.bc_anchor_coef=0.0` (+ log-std reopened −3.0→−4.0):
  tests the record's #1 teacher-ceiling suspect (walk BC coef=1). Gate:
  det h000 prog_m ≥0.40 m/12s (Candidate B baseline 0.3248), zero
  falls, slip/m ≤2.9, no heading below 0.29, 6/6 legs. VERIFIED
  RUNNING 09-06 on hexapod-mjx-train-7.
- `cw-robotwalk-turns-20260906` — 8M, warm from Candidate B, yaw
  exposure (`walk_yaw_zero_frac` 1.0→0.5, `turn_in_place_frac` 0.30)
  + bank-proven raw turn-income stack (k_walk_yaw et al.;
  `walk_kernel_yaw_ema` OFF — bank re-run 09-06 on mesh: raw kernel
  clause green, EMA drift clause fails on mesh) +
  `bc_anchor_walk_turn_skip=1` (anchor kept on straight/combined
  ticks). Gate: tip both signs wz_err_med <0.076, combined-cell
  improvement vs Candidate B, straight prog_m ≥0.29, joygate
  course_err_1s_med ≤5.17°, standing-still smoothness = FAIL.
  VERIFIED RUNNING 09-06 on hexapod-mjx-train-1.

**09-06 ~04:1x verdict: `cw-robotwalk-stride-20260906` ACQ FAIL — anchor-
ceiling hypothesis REFUTED, and worse.** Turning `train.bc_anchor_coef`
exactly to 0.0 did not free the policy to cover more distance; it
destroyed the gait. `gait_valid` 0/24 (every one of 4 modes 0/6): a
rigid TRIPOD LOCK, not a stride — legs [1,3,5] pinned at `duty_cycle`
1.0 (never lift) in literally every episode, legs [0,4] near-zero duty
(0.0-0.06), leg 2 alone partially participating (0.03-0.32).
`forward_dist_m` collapses to 0.001-0.036 m/20s (target was >=0.40
m/12s; Candidate B's own baseline is 0.31-0.33 m/12s) — not merely
short of target, essentially zero net travel. `slip_per_m` 16-30 (vs
the <=2.9 gate bound). 4/24 episodes show real safety terminations
(over_current). Video (`walk_det_0`, `walk_det_4`) confirms a static
quivering body, checkerboard grid does not shift frame-to-frame.
Training reward matches the collapse rather than diverging (quarters
168.7->398.9->381.7->171.0, ending negative at -135) — NOT the 08-21
rising-reward/bad-eval case; this is a genuine FAIL both by reward and
by eval. Per the gate's own instruction, no further
`train.bc_anchor_coef=0.0` clone should be launched from this parent;
if the stride-ceiling question is revisited it needs either a SOFTER
anchor reduction (partial coef) or the hypothesis's own named
alternative (a faster motion source/cadence-CPG harvest), not a repeat
of this exact ablation. No export — gate not met. `cw-robotwalk-
turns-20260906` (the campaign's 2nd arm, yaw/turn-income) finished
around the same time but was NOT assigned to this cycle — its gate
eval was found still computing on `hexapod-mjx-train-1` (shared with
this arm's own eval) and is left for whichever cycle picks it up next;
do not assume its outcome from this one (different lever, same
parent). Evidence: `logs/ckpt_eval/cw_robotwalk_stride_20260906_gate/
report.json`, W&B `catovl0h`.

Baseline = Candidate B `cw-walkteach-scripted-allhead-acq12m`
(controller-side training zip sha256 `30ed068e4356d5f42caba2a427f2845a
230d7289a06467684731ec94a1f6f250`; operator-deployed actor sha256
`a813c4a692081978359042f825aaf5c4b43b58f91ffcd6db365a80d6827f4167` —
that actor artifact exists operator-side only, per the 09-05 delivery
verify). Hardware truth: RobotLab experiment
`6ac6754d4c604e7399bf1f84173ce950` (reverse+release+both arcs, 5.5°
active tilt, no fall); the earlier 98.4° post-stop "fall"
(`989e41d37d3d489598b7b3f0d4e83dab`) is DISPROVED (stale-feedback
failure, raw MCU IMU + video) — retain the stale-feedback lesson, not
a physical-fall inference. Do NOT weaken the 0.375 deg/tick cap or
safety limits; do not promote easy/half-gravity results to hardware.

**Completion contract (for whichever cycle triages each arm):**
compare to Candidate B on the SAME short forward/reverse/release/
left+right arc script (100 Hz policy; 50 Hz-writes-compatible state/
filter behavior where supported); if the arm improves its measured
behavior with no unstable/dragged-leg motion in the sim evidence,
export the controller-compatible artifact with the existing exporter
and persist exact run/checkpoint/export SHA, policy/config path,
eval/video locations, and a concise decision in the run ledger/story —
the local RobotLab watchdog discovers those terminal artifacts and
enqueues each candidate ONCE, serially. A failing arm records why and
does not ship. No review/qualification descendants; do not turn 2M
intermediate reads into new experiment families; no same-recipe seed
clones. Stand/lower remain the scripted STEP; learned hold keeps its
existing role.

## REOPENED 09-05: measured hardware-controller delivery sub-track

Operator MCP note `fb_20260905T071610_749846` reopened this track for
smooth-hardware-walking delivery work (local Codex owns transport
replay + linux_control timing; the orchestrator owns the opt-in
command-envelope candidate). See
`rl_docs/tracks/todaypolicy/hardware_delivery/STATUS.md` for the
built+tested `CommandEnvelope` governor and the 09-05 paired CPU
suite verdict (shared-mode throttling refuted; yaw-priority is a real
turn-fidelity candidate at a named −55% progress cost; bundle
`todaypolicy-mlpsf-tuck-v1` retained as primary). The 08-30 DONE
banner below still stands for the sim/controller bundle itself.

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
